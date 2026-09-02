"""
Unit tests for SAFAR Pothole Speed Manager, Road Simulator, and Multi-Threat Arbitration.
"""

from safar.pothole.speed_manager import PotholeSpeedManager, PotholeActionPlan
from safar.pothole.road_simulator import simulate_road
from safar.decision.arbitration import ThreatArbiter
from safar.core.models import Decision, ActionType, RiskAssessment, RiskLevel


def test_drivable_path_maintains_speed():
    manager = PotholeSpeedManager()
    speed, action = manager.manage_speed(current_speed=20.0, pothole_type=0)
    assert speed == 20.0
    assert "driver" in action.lower()


def test_small_pothole_smooth_slowdown():
    manager = PotholeSpeedManager()
    speed, action = manager.manage_speed(current_speed=20.0, pothole_type=1)
    assert speed == 18.0  # 20.0 - 2.0
    assert "smooth" in action.lower()

    # Already below 12.0 -> maintains
    speed2, action2 = manager.manage_speed(current_speed=10.0, pothole_type=1)
    assert speed2 == 10.0
    assert "maintain" in action2.lower()


def test_mid_pothole_moderate_slowdown():
    manager = PotholeSpeedManager()
    speed, action = manager.manage_speed(current_speed=20.0, pothole_type=2)
    assert speed == 16.0  # 20.0 - 4.0
    assert "slow down" in action.lower()

    # Ceiling is 7.0
    speed2, _ = manager.manage_speed(current_speed=8.0, pothole_type=2)
    assert speed2 == 7.0  # clamped to target


def test_crater_emergency_braking():
    manager = PotholeSpeedManager()
    speed, action = manager.manage_speed(current_speed=20.0, pothole_type=3)
    assert speed == 12.0  # 20.0 - 8.0
    assert "emergency" in action.lower()

    # Final step down to 0
    speed2, action2 = manager.manage_speed(current_speed=5.0, pothole_type=3)
    assert speed2 == 0.0
    assert "stopped" in action2.lower()


def test_stopped_vehicle_state():
    manager = PotholeSpeedManager()
    speed, action = manager.manage_speed(current_speed=0.0, pothole_type=2)
    assert speed == 0.0
    assert "STOPPED waiting for driver to take action!!!" == action


def test_wheel_strike_and_straddle():
    manager = PotholeSpeedManager(track_width_m=1.60, tire_width_m=0.25, ground_clearance_m=0.16)

    # Hazard directly at left wheel (-0.80m)
    hit_left, loc = manager.check_wheel_strike(width_m=0.30, depth_m=0.05, lateral_offset_m=-0.80)
    assert hit_left is True
    assert loc == "LEFT_WHEEL"

    # Hazard straddled between wheels (center 0.0m) with 5cm depth -> Clear undercarriage
    hit_center, loc = manager.check_wheel_strike(width_m=0.40, depth_m=0.05, lateral_offset_m=0.0)
    assert hit_center is False
    assert loc == "CLEAR"

    # Deep crater in center exceeding 16cm ground clearance -> Undercarriage strike!
    hit_deep, loc = manager.check_wheel_strike(width_m=0.60, depth_m=0.22, lateral_offset_m=0.0)
    assert hit_deep is True
    assert loc == "UNDERCARRIAGE_STRIKE"


def test_road_simulator_run():
    road = [
        [0.1, 0.1, 0.001],
        [0.2, 0.7, 0.015],
        [1.5, 2.0, 0.150]
    ]
    history = simulate_road(road, starting_speed=20.0, verbose=False)
    assert len(history) == 3
    assert history[0]["detected_type"] == 0
    assert history[2]["detected_type"] == 3


def test_arbitration_with_pothole():
    arbiter = ThreatArbiter()
    manager = PotholeSpeedManager()

    # Safe obstacle + Class 3 Crater -> Emergency Brake
    obs_decision = Decision(ActionType.NONE, 20.0, 0.0, 0.45, "Clear")
    crater_plan = manager.evaluate_with_physics(20.0, pothole_type=3, width_m=1.5, length_m=2.0, depth_m=0.15, distance_forward_m=10.0)
    final_decision = arbiter.arbitrate_with_road_hazard(obs_decision, crater_plan)
    assert final_decision.action == ActionType.EMERGENCY_BRAKE
    assert final_decision.brake > 0.5


def run_all():
    test_drivable_path_maintains_speed()
    test_small_pothole_smooth_slowdown()
    test_mid_pothole_moderate_slowdown()
    test_crater_emergency_braking()
    test_stopped_vehicle_state()
    test_wheel_strike_and_straddle()
    test_road_simulator_run()
    test_arbitration_with_pothole()
    print("All Pothole Speed Manager and Arbitration tests PASS!")


if __name__ == "__main__":
    run_all()
