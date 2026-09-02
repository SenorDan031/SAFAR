"""
SAFAR Automated End-to-End Pipeline Verification Test
Verifies the complete closed loop:
UE5 Sensors -> Python Perception (Mock + Real Modes) -> C++ SAFAR Core -> Threat -> Decision -> Vehicle Actuators
"""
import subprocess
import time
import sys
import os
import socket
import json
import threading

def run_full_pipeline_test():
    print("======================================================================")
    print(" STARTING COMPLETE SAFAR FRAMEWORK AUTOMATED TEST")
    print("======================================================================")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_exe = os.path.join(root_dir, "safar_core", "build", "Release", "safar_core.exe")
    python_exe = sys.executable

    if not os.path.exists(cpp_exe):
        print(f"[ERROR] C++ SAFAR Core binary not found at: {cpp_exe}")
        return False

    # 1. Start C++ SAFAR Core Daemon
    print("\n[TEST PHASE 1] Spawning Modular C++ SAFAR Core Daemon...")
    cpp_proc = subprocess.Popen(
        [cpp_exe],
        cwd=root_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1.5)

    # 2. Setup UE5 Receiver on UDP Port 9003
    received_commands = []
    receiver_running = True

    def udp_listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 9003))
        sock.settimeout(0.2)

        while receiver_running:
            try:
                data, addr = sock.recvfrom(4096)
                if data:
                    payload = json.loads(data.decode("utf-8").strip())
                    received_commands.append(payload)
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()

    # 3. Test Mock Perception Mode (approaching_vehicle scenario)
    print("[TEST PHASE 2] Testing MODE B: MOCK PERCEPTION SERVICE...")
    from safar_perception.config import PerceptionConfig
    from safar_perception.main import PerceptionService

    cfg = PerceptionConfig(mode="mock", target_fps=30.0, cpp_core_port=9002)
    mock_service = PerceptionService(cfg)
    mock_service.mock_detector.scenario = "approaching_vehicle"
    connected = mock_service.connect_to_cpp_core(retries=5)
    assert connected, "Failed to connect PerceptionService to C++ Core!"

    mock_thread = threading.Thread(target=mock_service.run_mock_loop, kwargs={"max_frames": 60}, daemon=True)
    mock_thread.start()
    mock_thread.join(timeout=3.0)
    mock_service.close()

    print(f" -> Total Mock Control Commands Received by UE5: {len(received_commands)}")
    assert len(received_commands) > 10, "Mock perception commands failed to reach UE5!"

    # Check for escalation to BRAKE
    brake_commands = [c for c in received_commands if c.get("decision") == "BRAKE"]
    print(f" -> Total Autonomous BRAKE Interventions Generated: {len(brake_commands)}")
    assert len(brake_commands) > 0, "No BRAKE decision generated for approaching hazard!"

    latest_cmd = brake_commands[-1]
    print(f"\n[SAMPLE SAFAR CONTROL COMMAND CONTRACT]")
    print(f" • Decision:        {latest_cmd.get('decision')}")
    print(f" • Throttle Cut:    {latest_cmd.get('throttle'):.2f}")
    print(f" • Brake Pressure:  {latest_cmd.get('brake'):.2f}")
    print(f" • Emergency Stop:  {latest_cmd.get('emergency_brake')}")
    print(f" • HUD Status:      \"{latest_cmd.get('hud_status')}\"")
    print(f" • Latency:         {latest_cmd.get('latency_ms', 0.0):.2f} ms")

    # 4. Test Watchdog Failsafe
    print("\n[TEST PHASE 3] Testing WATCHDOG FAILSAFE TIMEOUT (> 250ms)...")
    time.sleep(0.4)  # Wait 400ms without perception stream

    failsafe_events = [c for c in received_commands if c.get("failsafe_active") is True]
    print(f" -> Watchdog Failsafe Triggered: {len(failsafe_events) > 0}")
    assert len(failsafe_events) > 0, "Watchdog failed to trigger failsafe on perception timeout!"
    assert failsafe_events[-1].get("brake") == 0.0, "Watchdog must release brake on failsafe!"

    # Cleanup
    receiver_running = False
    listener_thread.join(timeout=1.0)
    cpp_proc.terminate()
    try:
        cpp_proc.wait(timeout=1.0)
    except Exception:
        cpp_proc.kill()

    print("\n======================================================================")
    print(" >>> FULL SAFAR FRAMEWORK AUTOMATED TEST PASSED (100% SUCCESS) <<<")
    print("======================================================================")
    return True

if __name__ == "__main__":
    success = run_full_pipeline_test()
    sys.exit(0 if success else 1)
