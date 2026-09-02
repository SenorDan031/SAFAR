"""
SAFAR Pipeline Latency Benchmark Tool
Measures end-to-end and component latency:
UE5 -> Python YOLO Perception -> C++ SAFAR Core -> UE5 Vehicle Control
"""
import subprocess
import time
import sys
import os
import socket
import json
import threading
import numpy as np

def run_benchmark(num_frames: int = 50):
    print("======================================================================")
    print(" SAFAR PIPELINE LATENCY & THROUGHPUT BENCHMARK")
    print("======================================================================")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_exe = os.path.join(root_dir, "safar_core", "build", "Release", "safar_core.exe")
    python_exe = sys.executable

    # 1. Start C++ SAFAR Core
    cpp_proc = subprocess.Popen(
        [cpp_exe],
        cwd=root_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1.0)

    # 2. Start Python Perception Node
    py_proc = subprocess.Popen(
        [python_exe, "-m", "safar_perception.perception_node", "--mode", "ue5", "--ue5-port", "9001", "--cpp-port", "9002"],
        cwd=root_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2.5)

    # 3. Setup UE5 Receiver to record timestamps
    sent_timestamps = {}
    round_trip_latencies = []
    core_latencies = []
    receiver_running = True

    def udp_listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 9003))
        sock.settimeout(0.5)

        while receiver_running:
            try:
                data, addr = sock.recvfrom(4096)
                recv_time_us = int(time.time() * 1e6)
                if data:
                    payload = json.loads(data.decode("utf-8").strip())
                    fid = payload.get("frame_id")
                    core_lat = payload.get("latency_ms", 0.0)
                    core_latencies.append(core_lat)

                    if fid in sent_timestamps:
                        e2e_ms = (recv_time_us - sent_timestamps[fid]) / 1000.0
                        round_trip_latencies.append(e2e_ms)
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()

    # 4. Stream benchmark frames
    from ue5_adapter.mock_ue5_streamer import MockUE5Streamer
    streamer = MockUE5Streamer(host="127.0.0.1", port=9001)
    if not streamer.connect(retries=10, retry_delay_s=0.5):
        cpp_proc.kill()
        py_proc.kill()
        return

    print(f"Streaming {num_frames} frames for benchmark...")
    for i in range(num_frames):
        frame_img = streamer.generate_simulated_frame(obstacle_distance_factor=0.5)
        sent_timestamps[streamer.frame_id + 1] = int(time.time() * 1e6)
        streamer.send_frame(frame_img, speed_mps=15.0)
        time.sleep(0.033)  # ~30 FPS

    streamer.close()
    time.sleep(1.5)
    receiver_running = False
    listener_thread.join(timeout=1.0)

    cpp_proc.terminate()
    py_proc.terminate()

    # 5. Calculate Metrics
    if round_trip_latencies:
        p50 = np.percentile(round_trip_latencies, 50)
        p90 = np.percentile(round_trip_latencies, 90)
        p99 = np.percentile(round_trip_latencies, 99)
        avg_core = np.mean(core_latencies) if core_latencies else 0.0

        print("\n======================================================================")
        print(" BENCHMARK RESULTS")
        print("======================================================================")
        print(f" Total Frames Evaluated:       {len(round_trip_latencies)}")
        print(f" C++ SAFAR Core Latency (Avg): {avg_core:.3f} ms")
        print(f" End-to-End Latency (p50):     {p50:.2f} ms")
        print(f" End-to-End Latency (p90):     {p90:.2f} ms")
        print(f" End-to-End Latency (p99):     {p99:.2f} ms")
        print("======================================================================")


if __name__ == "__main__":
    run_benchmark(50)
