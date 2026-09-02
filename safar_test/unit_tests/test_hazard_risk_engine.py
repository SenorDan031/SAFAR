"""Deterministic tests for source-neutral HZ relevance, risk, and decisions."""

from safar.hazard.adapters import carla_detection_to_object, image_detection_to_object
from safar.hazard.models import DecisionState, PerceptionObject, VehicleSnapshot
from safar.hazard.policy import HazardPolicy
from safar.hazard.risk_engine import HazardRiskEngine
from safar.perception.types import Detection, SAFARDetection


def object_in_path(distance=22.0, closing=10.0, category="vehicle", object_id="hazard"):
    return PerceptionObject(object_id, category, 0.9, "test", True, distance, closing)


def evaluate_twice(engine, vehicle, observation):
    engine.evaluate(vehicle, [observation])
    return engine.evaluate(vehicle, [observation])[1]


def test_irrelevant_and_flying_objects_do_not_become_hazards():
    engine = HazardRiskEngine()
    result = evaluate_twice(engine, VehicleSnapshot(25.0), object_in_path(category="other"))
    assert result[0].state == DecisionState.NORMAL
    outside = PerceptionObject("outside", "vehicle", 0.9, "test", False, 6.0, 30.0)
    assert evaluate_twice(HazardRiskEngine(), VehicleSnapshot(25.0), outside)[0].state == DecisionState.NORMAL


def test_persistent_pedestrian_vehicle_and_wall_are_hazards():
    for category in ("pedestrian", "vehicle", "wall", "blockage"):
        assessment, _ = evaluate_twice(HazardRiskEngine(), VehicleSnapshot(18.0), object_in_path(category=category))
        assert assessment.state == DecisionState.WARNING


def test_city_policy_warning_then_slowdown():
    vehicle = VehicleSnapshot(18.0)
    assert evaluate_twice(HazardRiskEngine(), vehicle, object_in_path(22.0, 8.0))[0].state == DecisionState.WARNING
    assert evaluate_twice(HazardRiskEngine(), vehicle, object_in_path(12.0, 8.0))[0].state == DecisionState.SLOWDOWN


def test_mid_and_high_speed_policy_slow_down_gradually():
    assert evaluate_twice(HazardRiskEngine(), VehicleSnapshot(30.0), object_in_path(23.0, 8.0))[0].state == DecisionState.SLOWDOWN
    assert evaluate_twice(HazardRiskEngine(), VehicleSnapshot(80.0), object_in_path(70.0, 10.0))[0].state == DecisionState.SLOWDOWN


def test_120_kmh_hazard_at_farthest_awareness_range_requests_gradual_slowdown():
    engine = HazardRiskEngine()
    vehicle = VehicleSnapshot(120.0)
    farthest_range = engine.policy.awareness_distance_m(vehicle.speed_kmh)
    assessment, decision = evaluate_twice(engine, vehicle, object_in_path(farthest_range, 120.0))
    assert assessment.state == DecisionState.SLOWDOWN
    assert decision.action == "REDUCE_SPEED"
    assert decision.state != DecisionState.EMERGENCY_BRAKE


def test_stable_nearby_traffic_does_not_emergency_brake_but_rapid_closing_can():
    stable = evaluate_twice(HazardRiskEngine(), VehicleSnapshot(30.0), object_in_path(6.0, 0.0))[0]
    rapid = evaluate_twice(HazardRiskEngine(), VehicleSnapshot(30.0), object_in_path(6.0, 30.0))[0]
    assert stable.state != DecisionState.EMERGENCY_BRAKE
    assert rapid.state == DecisionState.EMERGENCY_BRAKE


def test_single_frame_noise_missing_distance_and_missing_perception_are_safe_or_explicit():
    engine = HazardRiskEngine()
    _, (_, first) = engine.evaluate(VehicleSnapshot(20.0), [object_in_path()])
    assert first.state == DecisionState.NORMAL
    unknown = evaluate_twice(HazardRiskEngine(), VehicleSnapshot(20.0), object_in_path(distance=None, closing=None))[0]
    assert unknown.state == DecisionState.CAUTION
    _, (_, fault) = HazardRiskEngine().evaluate(VehicleSnapshot(20.0), None)
    assert fault.state == DecisionState.FAULT
    _, (_, malformed) = HazardRiskEngine().evaluate(VehicleSnapshot(20.0), ["not an observation"])
    assert malformed.state == DecisionState.FAULT


def test_camera_only_hazard_has_unknown_physical_risk_not_low_risk():
    engine = HazardRiskEngine()
    observation = PerceptionObject("camera-car", "vehicle", 0.9, "yolo", True)
    engine.evaluate_without_vehicle_state([observation])
    _, (_, decision) = engine.evaluate_without_vehicle_state([observation])
    assert decision.risk_level == "UNKNOWN"
    assert decision.action == "WARN"


def test_hysteresis_holds_a_deescalating_state():
    engine = HazardRiskEngine(HazardPolicy(deescalation_frames=3))
    evaluate_twice(engine, VehicleSnapshot(18.0), object_in_path(12.0, 8.0))
    _, (_, decision) = engine.evaluate(VehicleSnapshot(18.0), [])
    assert decision.state == DecisionState.SLOWDOWN


def test_carla_and_image_adapters_supply_common_engine_inputs():
    policy = HazardPolicy()
    vehicle = VehicleSnapshot(18.0)
    carla = carla_detection_to_object(Detection("car", "vehicle", (22.0, 0.0, 0.0)), vehicle, policy)
    image = image_detection_to_object(
        SAFARDetection("car", 0.9, (450, 10, 650, 300), "vehicle"), 1000, "image-car", policy,
        distance_m=22.0, closing_speed_kmh=18.0,
    )
    assert isinstance(carla, PerceptionObject) and isinstance(image, PerceptionObject)
    assert evaluate_twice(HazardRiskEngine(), vehicle, carla)[0].state == DecisionState.WARNING
    assert evaluate_twice(HazardRiskEngine(), vehicle, image)[0].state == DecisionState.WARNING


def test_carla_path_relevance_uses_ego_heading_not_world_x_axis():
    policy = HazardPolicy()
    vehicle = VehicleSnapshot(18.0)
    # Relative +Y is directly ahead when the ego is heading along +Y.
    detection = Detection("heading-car", "vehicle", (0.0, 22.0, 0.0))
    result = carla_detection_to_object(detection, vehicle, policy, ego_forward_xy=(0.0, 1.0))
    assert result.in_path is True
