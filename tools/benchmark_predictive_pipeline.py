"""
SAFAR Simulator — Predictive Response Pipeline Benchmark & Stress Test
Benchmarks the predictive pipeline across multiple speeds (30, 45, 60, 75, 90 km/h)
verifying stopping-distance calculation, early threat escalation, and collision avoidance.
"""
from safar_simulator.predictive_threat import PredictiveThreatEngine
from safar.perception.continuous_predictor import ContinuousKinematicPredictor, TrackedKinematicObject
from safar_simulator.latency_profiler import LatencyProfiler
import time

def benchmark_predictive_pipeline():
    print("======================================================================")
    print(" BENCHMARKING PREDICTIVE SAFAR PIPELINE & STOPPING-DISTANCE AWARENESS")
    print("======================================================================")

    test_speeds = [30.0, 45.0, 60.0, 75.0, 90.0]
    threat_engine = PredictiveThreatEngine(nominal_deceleration_mps2=8.0, reaction_time_s=0.18)
    profiler = LatencyProfiler()

    for speed in test_speeds:
        d_stop = threat_engine.compute_stopping_distance(speed)
        print(f"\n[TEST CASE] Speed: {speed:4.1f} km/h | Required Stopping Distance: {d_stop:4.1f} m")

        # Simulate vehicle starting 70m away and approaching a stopped car in lane
        predictor = ContinuousKinematicPredictor()
        ego_dist = 70.0
        ego_speed = speed
        is_braking = False
        min_clearance = 70.0
        collision_occurred = False

        # Ingest initial detection
        predictor.update_from_perception([{
            "track_id": "lead-01",
            "class_name": "car",
            "distance_m": ego_dist,
            "lateral_offset_m": 0.0,
            "relative_speed_kmh": speed,
            "confidence": 0.95
        }])

        # Run 60 Hz simulation loop
        for tick in range(240): # 4 seconds @ 60 Hz
            dt = 0.0166

            # 1. Physical World Kinematics
            ego_dist -= (ego_speed / 3.6) * dt

            # 2. Perception Frame Arrival (~15 Hz = every 4 ticks)
            profiler.mark_capture()
            if tick % 4 == 0:
                profiler.mark_perception()
                predictor.update_from_perception([{
                    "track_id": "lead-01",
                    "class_name": "car",
                    "distance_m": ego_dist,
                    "lateral_offset_m": 0.0,
                    "relative_speed_kmh": ego_speed,
                    "confidence": 0.95
                }])
            else:
                # 3. Inter-frame 60 Hz Dead Reckoning
                profiler.mark_tracking()
                predictor.step_dead_reckoning(dt)

            tracks = predictor.get_all_tracks()
            if not tracks:
                continue
            trk = tracks[0]

            # 4. Predictive Threat Evaluation (60 Hz)
            profiler.mark_threat_decision()
            assessment = threat_engine.evaluate_track(trk, ego_speed_kmh=ego_speed, lookahead_s=1.2)
            profiler.mark_actuation()

            if assessment.decision_action == "EMERGENCY_BRAKE":
                is_braking = True

            if is_braking:
                ego_speed = max(0.0, ego_speed - (8.0 * 3.6 * dt))

            min_clearance = min(min_clearance, ego_dist)

            if ego_dist <= 0.0 and ego_speed > 1.0:
                collision_occurred = True
                break

            if ego_speed <= 0.1 and ego_dist > 0.0:
                break

        print(f" -> Result: {'COLLISION!' if collision_occurred else 'SUCCESSFULLY STOPPED'}")
        print(f" -> Final Stopped Clearance: {min_clearance:4.2f} m (Target: >= 1.50 m)")
        assert not collision_occurred, f"Collision occurred at {speed} km/h!"
        assert min_clearance >= 1.5, f"Clearance too small: {min_clearance}m"

    stats = profiler.get_stats_summary()
    print("\n======================================================================")
    print(" PREDICTIVE PIPELINE BENCHMARK PASSED (100% SUCCESS)")
    print(f" End-to-End Latency: {stats['avg_total_ms']:.2f} ms | Tracking: {stats['avg_tracking_ms']:.2f} ms | Decision: {stats['avg_decision_ms']:.2f} ms")
    print("======================================================================")

if __name__ == "__main__":
    benchmark_predictive_pipeline()
