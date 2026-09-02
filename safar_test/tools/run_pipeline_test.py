"""
SAFAR Automated End-to-End Phase 1 Pipeline Verification Harness
Spawns C++ Core, Python Perception, and UE5 Simulation Streamer to verify the complete loop:
UE5 -> Python YOLO -> C++ SAFAR Core -> Threat / Decision -> UE5 Receiver
"""
import subprocess
import time
import sys
import os
import socket
import json
import threading

def run_pipeline_test():
    print("======================================================================")
    print(" STARTING SAFAR PHASE 1 END-TO-END PIPELINE VERIFICATION")
    print("======================================================================")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_exe = os.path.join(root_dir, "safar_core", "build", "Release", "safar_core.exe")
    python_exe = sys.executable

    if not os.path.exists(cpp_exe):
        print(f"[ERROR] C++ SAFAR Core executable not found at: {cpp_exe}")
        print("Please build C++ core first: cmake --build safar_core/build --config Release")
        return False

    # 1. Start C++ SAFAR Core
    print(f"\n[STEP 1] Spawning C++ SAFAR Core Daemon...")
    cpp_proc = subprocess.Popen(
        [cpp_exe],
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(1.0)  # Allow socket to bind

    # 2. Start Python Perception Node
    print(f"[STEP 2] Spawning Python Perception Node (YOLO11)...")
    py_proc = subprocess.Popen(
        [python_exe, "-m", "safar_perception.perception_node", "--mode", "ue5", "--ue5-port", "9001", "--cpp-port", "9002"],
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    time.sleep(2.5)  # Allow YOLO model to load and bind port 9001

    # 3. Setup UE5 UDP Receiver on Port 9003 to capture C++ decisions
    print(f"[STEP 3] Setting up UE5 Control Command Receiver on UDP port 9003...")
    received_decisions = []
    receiver_running = True

    def udp_listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 9003))
        sock.settimeout(0.5)

        while receiver_running:
            try:
                data, addr = sock.recvfrom(4096)
                if data:
                    payload = json.loads(data.decode("utf-8").strip())
                    received_decisions.append(payload)
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()

    # 4. Stream simulated UE5 frames from MockUE5Streamer
    print(f"[STEP 4] Streaming simulated virtual camera frames to Python Perception...")
    from ue5_adapter.mock_ue5_streamer import MockUE5Streamer

    streamer = MockUE5Streamer(host="127.0.0.1", port=9001)
    connected = streamer.connect(retries=20, retry_delay_s=0.5)

    if not connected:
        print("[ERROR] Failed to connect to Python perception sensor interface.")
        cpp_proc.kill()
        py_proc.kill()
        return False

    num_test_frames = 15
    for i in range(num_test_frames):
        # Progressively move vehicle toward obstacle
        dist_factor = max(0.2, 0.7 - (i / num_test_frames) * 0.4)
        speed = 15.0 - (i / num_test_frames) * 3.0
        frame_img = streamer.generate_simulated_frame(obstacle_distance_factor=dist_factor)

        ok = streamer.send_frame(frame_img, speed_mps=speed)
        if not ok:
            print(f"[WARN] Failed to send test frame #{i}")
        time.sleep(0.06)

    streamer.close()

    # Wait for pipeline to drain
    time.sleep(1.5)
    receiver_running = False
    listener_thread.join(timeout=1.0)

    # Terminate background processes
    cpp_proc.terminate()
    py_proc.terminate()
    try:
        cpp_proc.wait(timeout=2.0)
        py_proc.wait(timeout=2.0)
    except Exception:
        cpp_proc.kill()
        py_proc.kill()

    # 5. Evaluate Results
    print("\n======================================================================")
    print(" PIPELINE VERIFICATION RESULTS")
    print("======================================================================")
    print(f" Total Frames Streamed from UE5:        {num_test_frames}")
    print(f" Total Decisions Received by UE5:       {len(received_decisions)}")

    assert len(received_decisions) > 0, "No decisions reached UE5 receiver!"

    sample = received_decisions[-1]
    print(f"\n[FINAL RECEIVED DECISION CONTRACT]")
    print(f" • Frame ID:      #{sample.get('frame_id')}")
    print(f" • Threat Score:  {sample.get('threat_score'):.2f}")
    print(f" • Action:        {sample.get('decision')}")
    print(f" • HUD Message:   \"{sample.get('hud_message')}\"")
    print(f" • Actuators:     Throttle={sample.get('control', {}).get('throttle'):.2f}, Brake={sample.get('control', {}).get('brake'):.2f}")
    print(f" • Core Latency:  {sample.get('latency_ms', 0.0):.2f} ms")

    # Assert correctness
    assert sample.get("threat_score") > 0.0, "Threat score must be positive for in-path obstacle"
    assert sample.get("decision") in ["WARN", "SLOWDOWN", "EMERGENCY_BRAKE"], "Decision must elevate for closing hazard"
    assert "SAFAR:" in sample.get("hud_message"), "HUD alert format must match SAFAR standard"

    print("\n======================================================================")
    print(" >>> PHASE 1 COMPLETE END-TO-END PIPELINE VALIDATED SUCCESSFULLY (100%) <<<")
    print("======================================================================")
    return True


if __name__ == "__main__":
    success = run_pipeline_test()
    sys.exit(0 if success else 1)
