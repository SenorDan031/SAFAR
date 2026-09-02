"""
SAFAR Simulator — Ego-Path Trajectory Relevance Filtering Test
Verifies that opposite-lane and sidewalk traffic are filtered out (zero false braking),
while in-lane cut-ins and obstacles trigger AEB interventions.
"""
from safar_simulator.trajectory_filter import TrajectoryFilterEngine

def test_trajectory_relevance():
    print("======================================================================")
    print(" TESTING EGO-PATH TRAJECTORY RELEVANCE & FALSE BRAKING REJECTION")
    print("======================================================================")

    # 1. Opposite Lane Traffic (Lateral offset +3.5m) -> MUST BE IGNORED
    opp_car = TrajectoryFilterEngine.evaluate(distance_m=20.0, lateral_offset_m=3.5, relative_speed_kmh=80.0, entity_class="car")
    print(f" [TEST 1] Opposite Lane Car: {opp_car.state} | Action: {opp_car.decision_action} | Score: {opp_car.threat_score:.2f}")
    assert opp_car.state == "OUTSIDE_PATH", f"Expected OUTSIDE_PATH, got {opp_car.state}"
    assert opp_car.decision_action == "CONTINUE", f"Expected CONTINUE, got {opp_car.decision_action}"

    # 2. Sidewalk Pedestrian (Lateral offset -4.0m) -> MUST BE IGNORED
    side_ped = TrajectoryFilterEngine.evaluate(distance_m=15.0, lateral_offset_m=-4.0, relative_speed_kmh=40.0, entity_class="pedestrian")
    print(f" [TEST 2] Sidewalk Pedestrian: {side_ped.state} | Action: {side_ped.decision_action} | Score: {side_ped.threat_score:.2f}")
    assert side_ped.state == "OUTSIDE_PATH", f"Expected OUTSIDE_PATH, got {side_ped.state}"
    assert side_ped.decision_action == "CONTINUE", f"Expected CONTINUE, got {side_ped.decision_action}"

    # 3. Adjacent Lane Vehicle (Lateral offset +1.8m) -> MUST BE MONITORED ONLY
    adj_car = TrajectoryFilterEngine.evaluate(distance_m=25.0, lateral_offset_m=1.8, relative_speed_kmh=10.0, entity_class="car")
    print(f" [TEST 3] Adjacent Lane Car: {adj_car.state} | Action: {adj_car.decision_action} | Score: {adj_car.threat_score:.2f}")
    assert adj_car.state == "NEAR_PATH", f"Expected NEAR_PATH, got {adj_car.state}"
    assert adj_car.decision_action == "MONITOR", f"Expected MONITOR, got {adj_car.decision_action}"

    # 4. Critical In-Path Hazard (Lateral offset 0.0m, Distance 12m) -> MUST TRIGGER EMERGENCY BRAKE
    inpath_bike = TrajectoryFilterEngine.evaluate(distance_m=12.0, lateral_offset_m=0.0, relative_speed_kmh=35.0, entity_class="motorcycle")
    print(f" [TEST 4] In-Path Motorcycle: {inpath_bike.state} | Action: {inpath_bike.decision_action} | Score: {inpath_bike.threat_score:.2f}")
    assert inpath_bike.state == "DIRECTLY_AHEAD", f"Expected DIRECTLY_AHEAD, got {inpath_bike.state}"
    assert inpath_bike.threat_level == "CRITICAL", f"Expected CRITICAL, got {inpath_bike.threat_level}"
    assert inpath_bike.decision_action == "EMERGENCY_BRAKE", f"Expected EMERGENCY_BRAKE, got {inpath_bike.decision_action}"

    print("======================================================================")
    print(" TRAJECTORY FILTER TEST PASSED (100% SUCCESS — ZERO FALSE OVER-BRAKING)")
    print("======================================================================")

if __name__ == "__main__":
    test_trajectory_relevance()
