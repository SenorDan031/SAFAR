"""Deterministic validation of the 8 Step 12 simulation scenarios for The Crew 2."""
import pytest
from safar.integrations.the_crew2 import (
    BrakeState,
    ConfirmationState,
    ControlState,
    TheCrew2Config,
    TheCrew2Controller,
    TheCrew2EgoPathConfig,
    TheCrew2HazardEngine,
)
from safar.perception.ego_path import EgoPathModel, PathLevel
from safar.perception.image_tracker import ImageTracker
from safar.perception.motion import ApparentMotion
from safar.perception.types import SAFARDetection


@pytest.fixture
def test_setup():
    config = TheCrew2Config(
        confirm_frames=2,
        hazard_frames=3,
        missed_grace_frames=2,
        enabled=False,  # Dry run
        ego_path=TheCrew2EgoPathConfig(horizon_y=0.46, bottom_width=0.70, top_width=0.16),
    )
    tracker = ImageTracker()
    ego_path = EgoPathModel(
        bottom_width=config.ego_path.bottom_width,
        top_width=config.ego_path.top_width,
        horizon_y=config.ego_path.horizon_y,
        center_offset=config.ego_path.center_offset,
    )
    hazard_engine = TheCrew2HazardEngine(config)
    controller = TheCrew2Controller(config, is_foreground_check=lambda: True)
    return config, tracker, ego_path, hazard_engine, controller


def _run_frame(detections, tracker, ego_path, hazard_engine, controller, width=1280, height=720):
    tracks = tracker.update(detections)
    relevance_map = {
        track.track_id: ego_path.relevance_for_bbox(track.bbox, width, height)
        for track in tracks if not track.missed
    }
    lead_res = hazard_engine.evaluate_frame(tracks, relevance_map, width, height)
    ctrl_evt = controller.update(lead_res)
    return lead_res, ctrl_evt


def test_scenario_1_clear_road(test_setup):
    """Scenario 1: Clear road -> CONTINUE, no input override."""
    config, tracker, ego_path, hazard_engine, controller = test_setup
    for _ in range(5):
        lead_res, ctrl_evt = _run_frame([], tracker, ego_path, hazard_engine, controller)
        assert lead_res.decision == "CONTINUE"
        assert lead_res.risk_level == "SAFE"
        assert lead_res.confirmation_state == ConfirmationState.NONE
        assert ctrl_evt.state == ControlState.PLAYER_CONTROL
        assert ctrl_evt.is_overriding is False


def test_scenario_2_adjacent_lane_vehicle(test_setup):
    """Scenario 2: Vehicle in adjacent lane -> PATH=LOW/NONE, no intervention."""
    config, tracker, ego_path, hazard_engine, controller = test_setup
    side_car = SAFARDetection("car", 0.90, (50, 350, 200, 480), "vehicle")
    for _ in range(5):
        lead_res, ctrl_evt = _run_frame([side_car], tracker, ego_path, hazard_engine, controller)
        assert lead_res.path_relevance in ("NONE", "LOW")
        assert ctrl_evt.state == ControlState.PLAYER_CONTROL
        assert ctrl_evt.is_overriding is False


def test_scenario_3_vehicle_directly_ahead(test_setup):
    """Scenario 3: Vehicle directly ahead -> PATH=HIGH, lead hazard selected."""
    config, tracker, ego_path, hazard_engine, controller = test_setup
    center_car = SAFARDetection("car", 0.90, (560, 350, 720, 470), "vehicle")
    for _ in range(3):
        lead_res, ctrl_evt = _run_frame([center_car], tracker, ego_path, hazard_engine, controller)

    assert lead_res.lead_track_id is not None
    assert lead_res.path_relevance == "HIGH"
    assert lead_res.lead_class == "car"


def test_scenario_4_vehicle_becomes_visually_closer(test_setup):
    """Scenario 4: Vehicle becomes visually closer -> Apparent motion=APPROACHING, Risk increases."""
    config, tracker, ego_path, hazard_engine, controller = test_setup

    # Progressive approach over frames
    f1 = SAFARDetection("car", 0.90, (580, 340, 700, 420), "vehicle")
    f2 = SAFARDetection("car", 0.90, (560, 350, 720, 460), "vehicle")
    f3 = SAFARDetection("car", 0.90, (540, 360, 740, 500), "vehicle")
    f4 = SAFARDetection("car", 0.90, (520, 370, 760, 540), "vehicle")

    _run_frame([f1], tracker, ego_path, hazard_engine, controller)
    _run_frame([f2], tracker, ego_path, hazard_engine, controller)
    _run_frame([f3], tracker, ego_path, hazard_engine, controller)
    lead_res, ctrl_evt = _run_frame([f4], tracker, ego_path, hazard_engine, controller)

    assert lead_res.apparent_motion == ApparentMotion.APPROACHING.value
    assert lead_res.risk_level in ("HIGH", "CRITICAL")
    assert lead_res.decision in ("SLOWDOWN", "EMERGENCY_BRAKE")
    assert ctrl_evt.is_overriding is True


def test_scenario_5_sudden_cut_in(test_setup):
    """Scenario 5: Vehicle suddenly cuts into ego path -> Hazard confirmation, risk escalation."""
    config, tracker, ego_path, hazard_engine, controller = test_setup

    # Frame 1: Vehicle on side
    side = SAFARDetection("car", 0.90, (200, 350, 350, 480), "vehicle")
    _run_frame([side], tracker, ego_path, hazard_engine, controller)

    # Frame 2: Cut-in into center
    cut_in = SAFARDetection("car", 0.90, (500, 380, 780, 580), "vehicle")
    lead_res1, ctrl_evt1 = _run_frame([cut_in], tracker, ego_path, hazard_engine, controller)
    assert lead_res1.confirmation_state == ConfirmationState.CANDIDATE
    assert ctrl_evt1.is_overriding is False  # No intervention on 1st frame

    # Frame 3-4: Persistent cut-in
    _run_frame([cut_in], tracker, ego_path, hazard_engine, controller)
    lead_res3, ctrl_evt3 = _run_frame([cut_in], tracker, ego_path, hazard_engine, controller)
    assert lead_res3.confirmation_state in (ConfirmationState.CONFIRMED, ConfirmationState.HAZARD)
    assert lead_res3.decision in ("SLOWDOWN", "EMERGENCY_BRAKE")
    assert ctrl_evt3.is_overriding is True


def test_scenario_6_traffic_pileup(test_setup):
    """Scenario 6: Traffic pileup -> Persistent path hazards, lead hazard selected, risk escalation."""
    config, tracker, ego_path, hazard_engine, controller = test_setup

    car_far = SAFARDetection("truck", 0.85, (600, 340, 680, 400), "vehicle")
    car_near = SAFARDetection("car", 0.92, (520, 380, 760, 560), "vehicle")
    car_side = SAFARDetection("motorcycle", 0.80, (100, 380, 180, 480), "two_wheeler")

    for _ in range(4):
        lead_res, ctrl_evt = _run_frame([car_far, car_near, car_side], tracker, ego_path, hazard_engine, controller)

    # Nearest centered car is selected as lead hazard
    assert lead_res.lead_class == "car"
    assert lead_res.path_relevance == "HIGH"
    assert lead_res.confirmation_state == ConfirmationState.HAZARD
    assert lead_res.risk_level in ("HIGH", "CRITICAL")
    assert ctrl_evt.is_overriding is True


def test_scenario_7_false_one_frame_detection(test_setup):
    """Scenario 7: False one-frame detection -> No emergency action."""
    config, tracker, ego_path, hazard_engine, controller = test_setup

    glitch = SAFARDetection("car", 0.70, (560, 400, 720, 550), "vehicle")
    lead_res1, ctrl_evt1 = _run_frame([glitch], tracker, ego_path, hazard_engine, controller)

    assert lead_res1.confirmation_state == ConfirmationState.CANDIDATE
    assert lead_res1.decision == "CAUTION"
    assert ctrl_evt1.is_overriding is False  # NO control override on single frame glitch!

    # Next frame glitch is gone
    lead_res2, ctrl_evt2 = _run_frame([], tracker, ego_path, hazard_engine, controller)
    assert ctrl_evt2.is_overriding is False


def test_scenario_8_hazard_disappears(test_setup):
    """Scenario 8: Hazard disappears -> SAFAR returns control to player."""
    config, tracker, ego_path, hazard_engine, controller = test_setup

    hazard_car = SAFARDetection("car", 0.90, (540, 380, 740, 540), "vehicle")
    # Build up confirmed hazard
    for _ in range(3):
        _run_frame([hazard_car], tracker, ego_path, hazard_engine, controller)

    # Hazard is active and overriding
    lead_active, ctrl_active = _run_frame([hazard_car], tracker, ego_path, hazard_engine, controller)
    assert ctrl_active.is_overriding is True

    # Hazard disappears for multiple frames
    _run_frame([], tracker, ego_path, hazard_engine, controller)
    _run_frame([], tracker, ego_path, hazard_engine, controller)
    lead_cleared, ctrl_cleared = _run_frame([], tracker, ego_path, hazard_engine, controller)

    assert lead_cleared.confirmation_state in (ConfirmationState.CLEARED, ConfirmationState.NONE)
    assert ctrl_cleared.is_overriding is False

    # Control returns cleanly to player
    lead_final, ctrl_final = _run_frame([], tracker, ego_path, hazard_engine, controller)
    assert ctrl_final.state == ControlState.PLAYER_CONTROL
    assert ctrl_final.brake_state == BrakeState.RELEASED
    assert ctrl_final.is_overriding is False
