"""
SAFAR Closed-Loop UE5 Simulation & Chaos Vehicle Test Harness
Tests the complete end-to-end stack:
1. TCP 9001: Virtual Camera & IMU Streaming (SFRM Packets from USAFARSensorComponent)
2. TCP 9002: Python AI Perception Detection Stream
3. UDP 9003: C++ SAFAR Core Real-Time Decision & Chaos Actuator Override
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Fix Windows DLL path resolution
if sys.platform == "win32":
    for p in [os.path.dirname(sys.executable), os.path.join(os.path.dirname(sys.executable), "Library", "bin")]:
        if os.path.exists(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass

import time
import socket
import struct
import json
import subprocess
import cv2
import numpy as np


class ClosedLoopUE5SimulatorTest:
    def __init__(self, core_exe_path: str = None):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.core_exe = core_exe_path or os.path.join(self.project_root, "safar_core", "build", "Release", "safar_core.exe")
        
        self.tcp_host = "127.0.0.1"
        self.perception_port = 9001
        self.control_port = 9003

        self.tcp_socket = None
        self.udp_socket = None
        
        self.core_proc = None
        self.perception_proc = None

        # Simulated Chaos Vehicle Kinematics
        self.ego_speed_mps = 14.0  # ~50 km/h
        self.ego_heading_deg = 0.0
        self.throttle_input = 1.0
        self.brake_input = 0.0
        self.handbrake_input = False
        self.override_active = False
        self.threat_score = 0.0
        self.hud_status = "SAFAR: INITIALIZING"

    def start_backend_services(self) -> bool:
        """Starts C++ safar_core and Python perception node if not already running."""
        print("=" * 80)
        print(" 🚗 SAFAR CLOSED-LOOP UE5 SIMULATION & CHAOS VEHICLE TEST HARNESS")
        print("=" * 80)

        # 1. Start C++ Core
        if os.path.exists(self.core_exe):
            print(f"[1/3] Launching C++ SAFAR Real-Time Core: {os.path.basename(self.core_exe)}...")
            self.core_proc = subprocess.Popen(
                [self.core_exe],
                cwd=os.path.join(self.project_root, "safar_core"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(0.5)
        else:
            print(f"[1/3] [WARNING] {self.core_exe} not found. Ensure safar_core is built or running.")

        # 2. Start Python Perception Node
        print("[2/3] Launching Python Perception Node (YOLOv8 + Multi-Hazard Pipeline)...")
        perception_env = os.environ.copy()
        perception_env["PYTHONPATH"] = self.project_root
        
        self.perception_proc = subprocess.Popen(
            [sys.executable, "-m", "safar_perception.perception_node"],
            cwd=self.project_root,
            env=perception_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(1.2)

        # 3. Setup UDP Control Listener (Port 9003)
        print("[3/3] Binding UDP Receiver Socket on Port 9003...")
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(("0.0.0.0", self.control_port))
        self.udp_socket.setblocking(False)

        # 4. Connect TCP Sensor Stream (Port 9001)
        print(f"[LINK] Connecting TCP Sensor Stream to Python Perception at {self.tcp_host}:{self.perception_port}...")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        connected = False
        for attempt in range(10):
            try:
                self.tcp_socket.connect((self.tcp_host, self.perception_port))
                connected = True
                print(" ✅ [LINK ESTABLISHED] Virtual Camera & IMU stream connected.\n")
                break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.5)

        if not connected:
            print(" ❌ [ERROR] Could not connect to Python Perception on port 9001.")
            return False

        return True

    def generate_virtual_camera_frame(self, frame_idx: int, total_frames: int) -> np.ndarray:
        """Generates dynamic synthetic driving scene with approaching lead vehicle & road hazards."""
        w, h = 640, 480
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Sky & Road
        img[:int(h * 0.45), :] = [65, 50, 35]
        img[int(h * 0.45):, :] = [45, 45, 45]

        horizon_y = int(h * 0.45)
        cx = w // 2

        # Perspective lane lines
        cv2.line(img, (cx - 30, horizon_y), (int(w * 0.15), h), (255, 255, 255), 3)
        cv2.line(img, (cx + 30, horizon_y), (int(w * 0.85), h), (255, 255, 255), 3)
        cv2.line(img, (cx, horizon_y), (cx, h), (0, 220, 255), 2)

        # Simulate vehicle closing in on obstacle from frame 15 onwards
        if frame_idx >= 10:
            progress = (frame_idx - 10) / float(total_frames - 10)
            # Distance factor: 0.85 (far) -> 0.15 (imminent collision)
            dist_factor = max(0.15, 0.85 - progress * 0.70)
            
            y_pos = int(horizon_y + (h - horizon_y) * (1.0 - dist_factor * 0.7))
            car_w = int(w * 0.12 * (1.0 + (1.0 - dist_factor) * 2.2))
            car_h = int(car_w * 0.75)

            x1 = cx - car_w // 2
            y1 = y_pos - car_h
            x2 = cx + car_w // 2
            y2 = y_pos

            # Lead car body
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 210), -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 100), 2)

            # Roof
            rx1 = cx - int(car_w * 0.35)
            ry1 = y1 - int(car_h * 0.45)
            rx2 = cx + int(car_w * 0.35)
            cv2.rectangle(img, (rx1, ry1), (rx2, y1), (25, 25, 25), -1)

            # Taillights
            tl_w = max(4, int(car_w * 0.15))
            tl_h = max(3, int(car_h * 0.2))
            cv2.rectangle(img, (x1 + 4, y2 - tl_h - 4), (x1 + 4 + tl_w, y2 - 4), (0, 0, 255), -1)
            cv2.rectangle(img, (x2 - 4 - tl_w, y2 - tl_h - 4), (x2 - 4, y2 - 4), (0, 0, 255), -1)

        return img

    def send_sensor_packet(self, frame_id: int, img: np.ndarray) -> bool:
        """Constructs SFRM framed packet conforming to interfaces/protocols.md."""
        ret, jpeg_bytes = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            return False

        raw_bytes = jpeg_bytes.tobytes()
        meta = {
            "timestamp_us": int(time.time() * 1e6),
            "frame_id": frame_id,
            "ego_speed_mps": round(self.ego_speed_mps, 2),
            "ego_heading_deg": round(self.ego_heading_deg, 2),
            "image_format": "jpeg",
            "image_bytes_len": len(raw_bytes)
        }

        meta_json = json.dumps(meta).encode("utf-8") + b"\0"
        payload = meta_json + raw_bytes

        # Header: Magic "SFRM" + Big-endian Length
        header = struct.pack("!4sI", b"SFRM", len(payload))
        
        try:
            self.tcp_socket.sendall(header + payload)
            return True
        except Exception:
            return False

    def poll_and_apply_control_command(self):
        """Polls UDP port 9003 and simulates USAFARSensorComponent / USAFARControlComponent actuation."""
        try:
            while True:
                data, _ = self.udp_socket.recvfrom(4096)
                if not data:
                    break

                payload = json.loads(data.decode("utf-8").strip())
                self.threat_score = payload.get("threat_score", 0.0)
                decision = payload.get("decision", "CONTINUE")
                ctrl = payload.get("control", {})
                self.hud_status = payload.get("hud_message", payload.get("hud_status", "SAFAR: ACTIVE"))

                cmd_throttle = ctrl.get("throttle", payload.get("throttle", 1.0))
                cmd_brake = ctrl.get("brake", payload.get("brake", 0.0))
                cmd_emergency = ctrl.get("emergency_stop", ctrl.get("emergency_brake", payload.get("emergency_brake", False)))

                # Passive Driver Principle Evaluation
                if self.threat_score >= 0.70 or cmd_emergency or cmd_brake > 0.65:
                    self.override_active = True
                    # Reverse-Protection Logic
                    if self.ego_speed_mps > 0.5:
                        self.throttle_input = cmd_throttle
                        self.brake_input = cmd_brake
                        self.handbrake_input = False
                        # Apply physical deceleration
                        self.ego_speed_mps = max(0.0, self.ego_speed_mps - 6.5 * 0.05)
                    else:
                        # Near-zero speed -> Lock handbrake
                        self.throttle_input = 0.0
                        self.brake_input = 1.0
                        self.handbrake_input = True
                        self.ego_speed_mps = 0.0
                else:
                    self.override_active = False
                    self.throttle_input = 1.0
                    self.brake_input = 0.0
                    self.handbrake_input = False
                    # Normal driving acceleration
                    self.ego_speed_mps = min(20.0, self.ego_speed_mps + 0.5 * 0.05)

        except (BlockingIOError, socket.error):
            pass

    def run_simulation(self, total_frames: int = 40):
        print(f" ▶ Running {total_frames} Frames of Closed-Loop Chaos Vehicle Simulation at 20 FPS...\n")
        print("-" * 80)
        print(f" {'FRAME':<7} | {'SPEED':<10} | {'THREAT':<8} | {'MODE':<24} | {'THROTTLE':<9} | {'BRAKE':<8} | {'HANDBRAKE'}")
        print("-" * 80)

        for f in range(1, total_frames + 1):
            t_start = time.time()

            # 1. Render virtual sensor frame
            frame_img = self.generate_virtual_camera_frame(f, total_frames)

            # 2. Transmit sensor frame via TCP 9001 (USAFARSensorComponent / USAFARCommunicationComponent)
            self.send_sensor_packet(f, frame_img)

            # 3. Allow backend processing time & poll UDP 9003 for control decisions
            time.sleep(0.035)
            self.poll_and_apply_control_command()

            mode_str = "🔴 AUTONOMOUS OVERRIDE" if self.override_active else "🟢 PASSIVE DRIVER"
            hb_str = "🔒 LOCKED" if self.handbrake_input else "RELEASED"
            print(f" #{f:<6} | {self.ego_speed_mps*3.6:5.1f} km/h | {self.threat_score:6.2f} | {mode_str:<24} | {self.throttle_input:8.2f} | {self.brake_input:7.2f} | {hb_str}")

            dt = time.time() - t_start
            if dt < 0.05:
                time.sleep(0.05 - dt)

        print("-" * 80)
        print("\n ✅ CLOSED-LOOP SIMULATION RUN COMPLETE.")
        print(f"    Final Vehicle Speed : {self.ego_speed_mps*3.6:.1f} km/h")
        print(f"    Final Threat Score  : {self.threat_score:.2f}")
        print(f"    Final Override Mode : {'ACTIVE (SAFAR Collision Avoidance Override)' if self.override_active else 'PASSIVE (Manual Control)'}")
        print(f"    Final Handbrake     : {'LOCKED (Reverse Anti-Roll Protected)' if self.handbrake_input else 'RELEASED'}")
        print("=" * 80 + "\n")

    def cleanup(self):
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.udp_socket:
            self.udp_socket.close()
        if self.perception_proc:
            self.perception_proc.terminate()
        if self.core_proc:
            self.core_proc.terminate()


def main():
    sim = ClosedLoopUE5SimulatorTest()
    try:
        if sim.start_backend_services():
            sim.run_simulation(total_frames=35)
    finally:
        sim.cleanup()


if __name__ == "__main__":
    main()
