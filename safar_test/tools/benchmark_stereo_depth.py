"""
SAFAR — Stereo Vision & Physical Depth Estimation Benchmark
Validates mathematical stereo depth calculation Z = (f * B) / d
against calibrated distances (5m to 80m) under realistic sensor noise.
"""
from safar.perception.stereo_depth import StereoDepthEngine

def benchmark_stereo_depth():
    print("======================================================================")
    print(" BENCHMARKING PHYSICAL STEREO VISION & MATHEMATICAL DEPTH (Z = fB/d)")
    print("======================================================================")

    engine = StereoDepthEngine(baseline_m=0.25, focal_length_px=650.0, enable_sensor_noise=True)
    test_distances = [5.0, 10.0, 20.0, 35.0, 50.0, 75.0]

    for true_z in test_distances:
        # Theoretical disparity
        true_d = engine.compute_disparity_from_depth(true_z)
        
        # Process detection through stereo engine
        raw_det = [{
            "track_id": f"obj-{int(true_z)}",
            "class_name": "car",
            "distance_m": true_z,
            "lateral_offset_m": 0.0,
            "confidence": 0.95
        }]

        results = engine.process_stereo_pair(raw_det)
        est_z = results[0].estimated_depth_m
        disp = results[0].disparity_px
        error_pct = (abs(est_z - true_z) / true_z) * 100.0

        print(f" True Distance: {true_z:4.1f}m | Disparity: {disp:5.1f}px | Estimated Depth: {est_z:4.1f}m | Error: {error_pct:4.1f}%")
        max_allowed_error = 10.0 if true_z <= 50.0 else 30.0
        assert error_pct <= max_allowed_error, f"Stereo error too high at {true_z}m: {error_pct:.1f}%"

    print("\n[SENSOR RIG VALIDATION]")
    for name, spec in engine.sensors.items():
        print(f" • {spec.name:<25} | Pos: {spec.mount_position_xyz_m} | FOV: {spec.fov_deg}° | Rate: {spec.frame_rate_hz}Hz")

    print("======================================================================")
    print(" STEREO DEPTH ESTIMATION BENCHMARK PASSED (100% SUCCESS)")
    print("======================================================================")

if __name__ == "__main__":
    benchmark_stereo_depth()
