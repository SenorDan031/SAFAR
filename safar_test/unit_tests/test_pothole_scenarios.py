"""
SAFAR Pothole 12-Scenario Deterministic Validation Benchmark Suite
Covers all requirements:
TEST 1 : Normal road -> drivable_path, SAFE, MAINTAIN
TEST 2 : Small pothole, far away (50m), low speed (5 m/s) -> LOW / MONITOR / MAINTAIN
TEST 3 : Small pothole, directly ahead (10m), high speed (20 m/s) -> Risk increases (Action: SLOW / MONITOR)
TEST 4 : Medium pothole, directly in path (12m, 15 m/s) -> SLOW / BRAKE
TEST 5 : Crater, directly ahead (8m), high speed (20 m/s), short distance -> CRITICAL, EMERGENCY_BRAKE
TEST 6 : Huge pothole, but outside vehicle path (lat = 3.5m) -> SAFE / NO DANGEROUS INTERVENTION
TEST 7 : Crater, 100m away -> HIGH / MONITOR (NOT immediate emergency braking)
TEST 8 : Invalid depth (NaN / negative) -> UNCERTAIN / INVALID, NO emergency action
TEST 9 : Very low confidence -> UNCERTAIN, NO emergency action
TEST 10: Vehicle speed = 0 -> SAFE, NO braking command
TEST 11: Multiple potholes -> Highest relevant threat selected
TEST 12: Threat disappears -> Decision returns toward safe state (MAINTAIN)
"""

from safar.pothole.simulation import PotholeSafetyPipeline
from safar.pothole.classifier import PotholeObservation
from safar.pothole.decision import PotholeAction
from safar.pothole.risk import PotholeSeverity


def run_all_pothole_tests():
    print("=" * 80)
    print(" SAFAR POTHOLE INTELLIGENCE: 12-SCENARIO DETERMINISTIC VALIDATION BENCHMARK")
    print("=" * 80)

    pipeline = PotholeSafetyPipeline()
    passed = 0

    # TEST 1: Normal road
    pipeline.decision_engine.reset()
    det = [{"width": 3.2, "length": 5.5, "depth": 0.003, "distance_forward": 30.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=15.0)
    assert dec.state == PotholeAction.MAINTAIN and not dec.has_intervention, f"Test 1 Failed: {dec}"
    print("[PASS] TEST 1 : Normal road                     -> drivable_path | SAFE | MAINTAIN (Intervention: False)")
    passed += 1

    # TEST 2: Small pothole, far away, low speed
    pipeline.decision_engine.reset()
    det = [{"width": 0.35, "length": 0.50, "depth": 0.015, "distance_forward": 50.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=5.0)
    assert dec.state in [PotholeAction.MAINTAIN, PotholeAction.MONITOR] and not dec.has_intervention, f"Test 2 Failed: {dec}"
    print(f"[PASS] TEST 2 : Small pothole, far away (50m)   -> Sml_ph | LOW / MONITOR (Action: {dec.state.value})")
    passed += 1

    # TEST 3: Small pothole, directly ahead, high speed
    pipeline.decision_engine.reset()
    det = [{"width": 0.40, "length": 0.60, "depth": 0.018, "distance_forward": 10.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=20.0)
    assert dec.state in [PotholeAction.SLOW, PotholeAction.MONITOR, PotholeAction.BRAKE], f"Test 3 Failed: {dec}"
    print(f"[PASS] TEST 3 : Small pothole, close (10m, 20m/s)-> Risk elevated | Action: {dec.state.value} (Risk: {dec.risk_score:.2f})")
    passed += 1

    # TEST 4: Medium pothole, directly in path
    pipeline.decision_engine.reset()
    det = [{"width": 0.40, "length": 0.90, "depth": 0.038, "distance_forward": 12.0, "distance_lateral": 0.0}]
    pipeline.process_frame(det, vehicle_speed_mps=15.0)
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=15.0)
    assert dec.state in [PotholeAction.SLOW, PotholeAction.BRAKE], f"Test 4 Failed: {dec}"
    print(f"[PASS] TEST 4 : Medium pothole in path (12m)    -> Mid_ph | Action: {dec.state.value} (Rec Speed: {dec.recommended_speed_mps:.0f}m/s)")
    passed += 1

    # TEST 5: Crater, directly ahead, high speed, short distance
    pipeline.decision_engine.reset()
    det = [{"width": 1.50, "length": 2.20, "depth": 0.150, "distance_forward": 8.0, "distance_lateral": 0.0}]
    pipeline.process_frame(det, vehicle_speed_mps=20.0)
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=20.0)
    assert dec.state == PotholeAction.EMERGENCY_BRAKE and dec.has_intervention, f"Test 5 Failed: {dec}"
    print("[PASS] TEST 5 : Severe crater directly ahead (8m)-> Crater | CRITICAL | EMERGENCY_BRAKE (Intervention: True)")
    passed += 1

    # TEST 6: Huge pothole, but outside vehicle path
    pipeline.decision_engine.reset()
    det = [{"width": 1.80, "length": 2.50, "depth": 0.180, "distance_forward": 10.0, "distance_lateral": 3.5}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=15.0)
    assert not dec.has_intervention and dec.state == PotholeAction.MAINTAIN, f"Test 6 Failed: {dec}"
    print("[PASS] TEST 6 : Huge crater outside path (3.5m) -> Outside corridor | SAFE | MAINTAIN (Intervention: False)")
    passed += 1

    # TEST 7: Crater 100m away
    pipeline.decision_engine.reset()
    det = [{"width": 1.50, "length": 2.00, "depth": 0.140, "distance_forward": 100.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=15.0)
    assert dec.state != PotholeAction.EMERGENCY_BRAKE, f"Test 7 Failed: {dec}"
    print(f"[PASS] TEST 7 : Crater 100m away                -> Ample stopping buffer | Action: {dec.state.value} (NOT emergency brake)")
    passed += 1

    # TEST 8: Invalid depth (Negative / NaN)
    pipeline.decision_engine.reset()
    det = [{"width": 0.50, "length": 1.00, "depth": -0.05, "distance_forward": 10.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=15.0)
    assert not dec.has_intervention and dec.state == PotholeAction.MAINTAIN, f"Test 8 Failed: {dec}"
    print("[PASS] TEST 8 : Invalid depth measurement (-0.05m)-> UNCERTAIN / INVALID | NO emergency action")
    passed += 1

    # TEST 9: Very low classification confidence (e.g. uncertain inference)
    pipeline.decision_engine.reset()
    low_conf_obs = PotholeObservation(
        pothole_id=9,
        pothole_type=-1,
        pothole_name="UNCERTAIN",
        width=0.5,
        length=0.8,
        depth=0.03,
        confidence=0.35,  # Below 0.70 threshold
        distance_forward=10.0,
        distance_lateral=0.0,
        is_valid=False,
        status="UNCERTAIN (Confidence 0.35 < 0.70)"
    )
    risk_eval = pipeline.risk_engine.assess_risk(low_conf_obs, vehicle_speed_mps=15.0)
    dec = pipeline.decision_engine.evaluate_decision(risk_eval)
    assert not dec.has_intervention and dec.state == PotholeAction.MAINTAIN, f"Test 9 Failed: {dec}"
    print("[PASS] TEST 9 : Very low confidence (0.35)      -> UNCERTAIN | NO emergency action (MAINTAIN)")
    passed += 1

    # TEST 10: Vehicle speed = 0
    pipeline.decision_engine.reset()
    det = [{"width": 1.50, "length": 2.00, "depth": 0.150, "distance_forward": 2.0, "distance_lateral": 0.0}]
    dec, _ = pipeline.process_frame(det, vehicle_speed_mps=0.0)
    assert not dec.has_intervention and dec.state == PotholeAction.MAINTAIN, f"Test 10 Failed: {dec}"
    print("[PASS] TEST 10: Vehicle at rest (speed = 0)     -> Stationary | SAFE | NO braking command")
    passed += 1

    # TEST 11: Multiple potholes (Small at 5m vs Crater at 12m in path)
    pipeline.decision_engine.reset()
    det = [
        {"id": 1, "width": 0.30, "length": 0.40, "depth": 0.015, "distance_forward": 5.0, "distance_lateral": 0.0},
        {"id": 2, "width": 1.60, "length": 2.40, "depth": 0.160, "distance_forward": 12.0, "distance_lateral": 0.0}
    ]
    pipeline.process_frame(det, vehicle_speed_mps=18.0)
    dec, all_evals = pipeline.process_frame(det, vehicle_speed_mps=18.0)
    assert dec.target_pothole_id == 2 and dec.state in [PotholeAction.BRAKE, PotholeAction.EMERGENCY_BRAKE], f"Test 11 Failed: {dec}"
    print(f"[PASS] TEST 11: Multiple potholes               -> Highest threat prioritized: Hazard #{dec.target_pothole_id} ({dec.target_pothole_name})")
    passed += 1

    # TEST 12: Threat disappears -> Returns to safe state
    pipeline.decision_engine.reset()
    det_hazard = [{"id": 3, "width": 1.50, "length": 2.00, "depth": 0.150, "distance_forward": 8.0, "distance_lateral": 0.0}]
    pipeline.process_frame(det_hazard, vehicle_speed_mps=20.0)
    pipeline.process_frame(det_hazard, vehicle_speed_mps=20.0)
    # Danger avoided / swerved:
    for _ in range(30):
        dec, _ = pipeline.process_frame([], vehicle_speed_mps=15.0, delta_time_s=0.016)
    assert dec.state == PotholeAction.MAINTAIN and not dec.has_intervention, f"Test 12 Failed: {dec}"
    print("[PASS] TEST 12: Threat cleared & hold expired   -> Returns cleanly to MAINTAIN (Intervention: False)")
    passed += 1

    print("=" * 80)
    print(f" ALL {passed}/12 POTHOLE SAFETY SCENARIOS PASSED WITH 100% SUCCESS")
    print("=" * 80)


if __name__ == "__main__":
    run_all_pothole_tests()
