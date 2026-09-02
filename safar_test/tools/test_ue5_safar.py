"""
SAFAR Autonomous UE5 Vehicle Controller & Perception Loop
Fully Automated:
1. Captures live camera feed from Unreal Engine 5
2. Runs YOLO11 AI Object Perception
3. Evaluates real-time threat scores & safety decisions in C++ SAFAR Core
4. AUTOMATIC VEHICLE INTERVENTION: Actively applies emergency brakes in UE5 using DirectInput hardware controls!
"""
import time
import sys
import os
import argparse
import socket
import json
import threading
import queue
import cv2
import numpy as np

# Windows API & DirectInput Hardware Scancodes
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

from safar_perception.detector import YoloDetector
from safar_perception.types import SensorFrame
from safar_perception.ipc_sender import IpcSender

# DirectInput Scancodes for Unreal Engine Driving Controls
DIK_W = 0x11         # Throttle
DIK_S = 0x1F         # Foot Brake / Reverse
DIK_SPACE = 0x39     # Handbrake
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

class DirectInputKeySender:
    """
    Sends hardware-level DirectInput scancodes to Unreal Engine 5 to brake or cut throttle.
    """
    @staticmethod
    def press_key(scan_code: int):
        extra = ctypes.c_ulong(0)
        ii_ = ctypes.c_ulong(0)
        x = ctypes.c_ulong(0)
        # Send keydown scancode
        user32.keybd_event(0, scan_code, KEYEVENTF_SCANCODE, 0)

    @staticmethod
    def release_key(scan_code: int):
        # Send keyup scancode
        user32.keybd_event(0, scan_code, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0)

    @classmethod
    def apply_emergency_brake(cls):
        cls.press_key(DIK_S)
        cls.press_key(DIK_SPACE)

    @classmethod
    def release_all_brakes(cls):
        cls.release_key(DIK_S)
        cls.release_key(DIK_SPACE)


class AsyncUE5Capture:
    """
    Dedicated background capture worker that constantly grabs the freshest frame
    from the Unreal Engine 5 viewport into a single-frame queue, dropping old frames.
    """
    def __init__(self, target_title: str = "SAFAR_Sim", target_fps: float = 30.0):
        self.target_title = target_title
        self.target_fps = target_fps
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.hwnd = None
        self.worker_thread = None

    def find_window(self) -> bool:
        def enum_windows_callback(hwnd, extra):
            if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if self.target_title.lower() in title.lower() or "unreal editor" in title.lower():
                        self.hwnd = hwnd
                        return False
            return True

        self.hwnd = None
        cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_windows_callback)
        user32.EnumWindows(cb, 0)
        return self.hwnd is not None

    def start(self):
        self.running = True
        self.find_window()
        self.worker_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.worker_thread.start()

    def _capture_worker(self):
        sct = mss.mss() if HAS_MSS else None
        delay = 1.0 / self.target_fps

        while self.running:
            t0 = time.perf_counter()

            if not self.hwnd or not user32.IsWindow(self.hwnd):
                if not self.find_window():
                    time.sleep(0.1)
                    continue

            rect = wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            x, y = rect.left, rect.top
            w, h = rect.right - rect.left, rect.bottom - rect.top

            if w <= 100 or h <= 100:
                time.sleep(0.05)
                continue

            # Focus on central viewport area
            vp_top = int(y + h * 0.10)
            vp_left = int(x + w * 0.02)
            vp_width = int(w * 0.76)
            vp_height = int(h * 0.82)

            frame = None
            if sct is not None:
                monitor = {
                    "left": vp_left,
                    "top": vp_top,
                    "width": max(100, vp_width),
                    "height": max(100, vp_height)
                }
                try:
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img, dtype=np.uint8)[:, :, :3]
                except Exception:
                    frame = None

            if frame is not None:
                frame_resized = cv2.resize(frame, (640, 384))

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                try:
                    self.frame_queue.put_nowait(frame_resized)
                except queue.Full:
                    pass

            elapsed = time.perf_counter() - t0
            sleep_time = max(0.001, delay - elapsed)
            time.sleep(sleep_time)

        if sct is not None:
            sct.close()

    def get_latest_frame(self, timeout_s: float = 0.5) -> np.ndarray:
        try:
            return self.frame_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)


def run_ue5_live_safar():
    parser = argparse.ArgumentParser(description="SAFAR Live Autonomous Controller for UE5")
    parser.add_argument("--window-title", type=str, default="SAFAR_Sim", help="UE5 window title substring")
    parser.add_argument("--cpp-port", type=int, default=9002, help="C++ Core TCP port")
    parser.add_argument("--ue5-port", type=int, default=9003, help="UE5 UDP decision port")
    parser.add_argument("--conf", type=float, default=0.28, help="YOLO confidence threshold")
    parser.add_argument("--enable-auto-brake", action="store_true", default=True, help="Enable active vehicle braking intervention")
    parser.add_argument("--hud", action="store_true", default=False, help="Show graphical debug overlay (default: False/Headless)")
    args = parser.parse_args()

    print("======================================================================")
    print(" SAFAR LIVE AUTONOMOUS DRIVING & INTERVENTION CONTROLLER")
    print("======================================================================")
    print(" Connecting to Unreal Engine 5 Simulation...")

    # 1. Start Async Screen Capture Worker
    capture = AsyncUE5Capture(target_title=args.window_title, target_fps=30.0)
    capture.start()

    # 2. Initialize YOLO Detector & IPC Sender
    detector = YoloDetector(conf_threshold=args.conf)
    ipc_sender = IpcSender(host="127.0.0.1", port=args.cpp_port)

    # 3. Decision Listener from C++ Core
    latest_decision = {
        "threat_score": 0.0,
        "decision": "CONTINUE",
        "hud_message": "SAFAR: PATH CLEAR | ACTION: CONTINUE",
        "control": {"throttle": 1.0, "brake": 0.0, "emergency_stop": False},
        "latency_ms": 0.0
    }
    receiver_running = True

    def udp_listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", args.ue5_port))
        sock.settimeout(0.3)

        while receiver_running:
            try:
                data, addr = sock.recvfrom(4096)
                if data:
                    payload = json.loads(data.decode("utf-8").strip())
                    latest_decision.update(payload)
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()

    if not ipc_sender.connect(retries=5, retry_delay_s=0.2):
        print("[WARN] C++ SAFAR Core daemon not connected. Starting standalone perception mode.")
    else:
        print("[INFO] Connected to C++ SAFAR Core.")

    print("\n[READY] Autonomous Safety Interventions Active.")
    print("Driving your vehicle in UE5 will now automatically brake on hazards!")
    print("Press 'Q' on the HUD window to exit.\n")

    frame_id = 0
    fps_time = time.time()
    fps_count = 0
    display_fps = 30.0
    is_braking_active = False

    try:
        while True:
            t0 = time.perf_counter()
            frame_img = capture.get_latest_frame(timeout_s=0.1)

            if frame_img is None:
                time.sleep(0.005)
                continue

            h, w = frame_img.shape[:2]
            frame_id += 1

            sensor_frame = SensorFrame(
                timestamp_us=int(time.time() * 1e6),
                frame_id=frame_id,
                ego_speed_mps=15.0,
                ego_heading_deg=0.0,
                image=frame_img
            )

            # A. Run YOLO AI Perception
            payload = detector.detect(sensor_frame)

            # B. Transmit to C++ Core
            ipc_sender.send_detections(payload)

            # C. Real-time Vehicle Actuator Intervention
            action = latest_decision.get("decision", "CONTINUE")
            threat = latest_decision.get("threat_score", 0.0)

            if action in ["EMERGENCY_BRAKE", "SLOWDOWN"] and threat >= 0.70:
                if not is_braking_active and args.enable_auto_brake:
                    DirectInputKeySender.apply_emergency_brake()
                    is_braking_active = True
            else:
                if is_braking_active:
                    DirectInputKeySender.release_all_brakes()
                    is_braking_active = False

            # FPS calculation
            fps_count += 1
            if time.time() - fps_time >= 1.0:
                display_fps = fps_count / (time.time() - fps_time)
                fps_count = 0
                fps_time = time.time()

            t_end = time.perf_counter()
            latency_ms = (t_end - t0) * 1000.0

            # Render Overlay HUD
            # Terminal Live Diagnostics
            if frame_id % 15 == 0 or is_braking_active:
                status_str = f"AUTO-BRAKE: {'ENGAGED' if is_braking_active else 'STANDBY'} | FPS: {display_fps:.1f} | Latency: {latency_ms:.1f}ms"
                msg = latest_decision.get("hud_status", latest_decision.get("hud_message", "SAFAR: ACTIVE"))
                print(f"[SAFAR ADAS] {msg} | {status_str}")

            if args.hud:
                hud = frame_img.copy()
                pts = np.array([
                    [int(w * 0.40), int(h * 0.45)],
                    [int(w * 0.60), int(h * 0.45)],
                    [int(w * 0.85), h],
                    [int(w * 0.15), h]
                ], np.int32)
                cv2.polylines(hud, [pts], isClosed=True, color=(0, 230, 118), thickness=2)
                cv2.imshow("SAFAR Debug HUD", hud)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        DirectInputKeySender.release_all_brakes()
        receiver_running = False
        listener_thread.join(timeout=0.5)
        capture.stop()
        ipc_sender.close()
        cv2.destroyAllWindows()
        print("\n[INFO] SAFAR Autonomous Controller session closed.")


if __name__ == "__main__":
    run_ue5_live_safar()
