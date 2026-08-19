"""Unit tests for The Crew 2 simulation adapter components."""
import pytest
from safar.integrations.the_crew2 import (
    BrakeState,
    ConfirmationState,
    ControlState,
    LeadHazardResult,
    LeadHazardSelector,
    TemporalConfirmationTracker,
    TheCrew2Capture,
    TheCrew2Config,
    TheCrew2Controller,
    TheCrew2EgoPathConfig,
    TheCrew2HazardEngine,
)
from safar.perception.ego_path import EgoPathModel, PathLevel, PathRelevance
from safar.perception.image_tracker import ImageTrack
from safar.perception.motion import ApparentMotion, TrafficState
from safar.perception.types import SAFARDetection


def _dummy_track(track_id="image-1", bbox=(450, 300, 650, 500), class_name="car", age=3, history=None):
    detection = SAFARDetection(class_name=class_name, confidence=0.85, bbox=bbox, category="vehicle")
    hist = history or [detection] * age
    return ImageTrack(track_id=track_id, detection=detection, age=age, missed=0, history=hist)


def test_the_crew2_config_defaults():
    config = TheCrew2Config()
    assert "The Crew 2" in config.window_titles
    assert config.target_fps == 30.0
    assert config.ego_path.horizon_y == 0.46
    assert config.max_override_duration_s == 3.0
    assert config.enabled is False  # Safe default


def test_capture_mock_mode_when_window_not_found():
    config = TheCrew2Config(window_titles=("NonExistentWindow_12345",))
    capture = TheCrew2Capture(config)
    found = capture.locate_window()
    assert found is False
    assert capture.hwnd is None
    ts, frame = capture.grab_frame()
    assert frame is not None
    assert frame.shape == (720, 1280, 3)
    capture.release()


def test_lead_hazard_selector_picks_in_path_object():
    selector = LeadHazardSelector()
    track_in_path = _dummy_track("in-path", bbox=(500, 350, 600, 500))
    track_off_path = _dummy_track("off-path", bbox=(50, 350, 150, 500))

    rel_in = PathRelevance(score=0.9, level=PathLevel.HIGH, in_path=True, reason="in corridor")
    rel_off = PathRelevance(score=0.0, level=PathLevel.NONE, in_path=False, reason="off corridor")

    rel_map = {"in-path": rel_in, "off-path": rel_off}
    result = selector.select([track_in_path, track_off_path], rel_map, 1280, 720)

    assert result is not None
    best_track, best_rel, best_motion, best_traffic = result
    assert best_track.track_id == "in-path"
    assert best_rel.in_path is True


def test_temporal_confirmation_tracker_progression_and_hysteresis():
    config = TheCrew2Config(confirm_frames=2, hazard_frames=3, missed_grace_frames=2)
    tracker = TemporalConfirmationTracker(config)

    # Frame 1: Candidate
    state, seen = tracker.update("target-1")
    assert state == ConfirmationState.CANDIDATE
    assert seen == 1

    # Frame 2: Confirmed
    state, seen = tracker.update("target-1")
    assert state == ConfirmationState.CONFIRMED
    assert seen == 2

    # Frame 3: Hazard
    state, seen = tracker.update("target-1")
    assert state == ConfirmationState.HAZARD
    assert seen == 3

    # Frame 4 (Missed 1): Hysteresis holds HAZARD
    state, seen = tracker.update(None)
    assert state == ConfirmationState.HAZARD

    # Frame 5 (Missed 2): Hysteresis holds HAZARD
    state, seen = tracker.update(None)
    assert state == ConfirmationState.HAZARD

    # Frame 6 (Missed 3 > grace): Transitions to CLEARED
    state, seen = tracker.update(None)
    assert state == ConfirmationState.CLEARED

    # Frame 7: Transitions to NONE
    state, seen = tracker.update(None)
    assert state == ConfirmationState.NONE


def test_controller_state_machine_and_override_releases():
    config = TheCrew2Config(enabled=False, max_override_duration_s=1.0)
    controller = TheCrew2Controller(config, is_foreground_check=lambda: True)

    # 1. Candidate lead -> No override
    cand = LeadHazardResult(
        lead_track_id="t1", lead_class="car", path_relevance="HIGH",
        traffic_state="MOVING", apparent_motion="APPROACHING", reason="",
        confirmation_state=ConfirmationState.CANDIDATE, risk_level="LOW", decision="CAUTION",
    )
    evt = controller.update(cand)
    assert evt.state == ControlState.HAZARD_CANDIDATE
    assert evt.is_overriding is False

    # 2. Slowdown decision -> SLOWDOWN_OVERRIDE
    slow = LeadHazardResult(
        lead_track_id="t1", lead_class="car", path_relevance="HIGH",
        traffic_state="MOVING", apparent_motion="APPROACHING", reason="",
        confirmation_state=ConfirmationState.CONFIRMED, risk_level="HIGH", decision="SLOWDOWN",
    )
    evt = controller.update(slow)
    assert evt.state == ControlState.SLOWDOWN_OVERRIDE
    assert evt.brake_state == BrakeState.LIGHT
    assert evt.is_overriding is True

    # 3. Emergency brake decision -> BRAKE_OVERRIDE
    emg = LeadHazardResult(
        lead_track_id="t1", lead_class="car", path_relevance="HIGH",
        traffic_state="MOVING", apparent_motion="APPROACHING", reason="",
        confirmation_state=ConfirmationState.HAZARD, risk_level="CRITICAL", decision="EMERGENCY_BRAKE",
    )
    evt = controller.update(emg)
    assert evt.state == ControlState.BRAKE_OVERRIDE
    assert evt.brake_state == BrakeState.STRONG
    assert evt.is_overriding is True

    # 4. Clear road -> HAZARD_CLEAR then PLAYER_CONTROL
    clear = LeadHazardResult(
        lead_track_id=None, lead_class=None, path_relevance="NONE",
        traffic_state="UNKNOWN", apparent_motion="UNKNOWN", reason="",
        confirmation_state=ConfirmationState.NONE, risk_level="SAFE", decision="CONTINUE",
    )
    evt = controller.update(clear)
    assert evt.state == ControlState.HAZARD_CLEAR
    assert evt.is_overriding is False

    evt2 = controller.update(clear)
    assert evt2.state == ControlState.PLAYER_CONTROL
    assert evt2.is_overriding is False


def test_controller_foreground_safety_releases_override():
    is_fg = True
    config = TheCrew2Config(enabled=False, require_foreground_window=True)
    controller = TheCrew2Controller(config, is_foreground_check=lambda: is_fg)

    emg = LeadHazardResult(
        lead_track_id="t1", lead_class="car", path_relevance="HIGH",
        traffic_state="MOVING", apparent_motion="APPROACHING", reason="",
        confirmation_state=ConfirmationState.HAZARD, risk_level="CRITICAL", decision="EMERGENCY_BRAKE",
    )
    evt = controller.update(emg)
    assert evt.is_overriding is True

    # Player Alt-Tabs away
    is_fg = False
    evt = controller.update(emg)
    assert evt.is_overriding is False
    assert evt.state == ControlState.PLAYER_CONTROL
