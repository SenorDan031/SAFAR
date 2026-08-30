"""
SAFAR Core Unreal Engine 5 Live Simulation Runner
Directly connects the production SAFAR Risk Engine, Temporal Confirmation Tracker,
Safety Override Controller, and YOLO Perception to the live Unreal Engine 5 vehicle.
"""
import time
import sys
import os
import argparse
import threading
import queue
import cv2
import numpy as np

# Windows DirectInput API
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

from safar.core.models import Obstacle, VehicleState, RiskLevel, RiskAssessment
from safar.core.risk_engine import RiskEngine
from safar.core.safety_override import SafetyOverrideController
from safar.integrations.the_crew2.hazard import LeadHazardSelector, TemporalConfirmationTracker, ConfirmationState
from safar.perception.yolo_detector import YoloDetector
from safar.road.lane_analyzer import LaneContext

# Hardware DirectInput Scancodes
DIK_W = 0x11         # Throttle
DIK_S = 0x1F         # Foot Brake / Reverse
DIK_SPACE = 0x39     # Handbrake
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002


class DirectInputActuator:
    """
    Sends hardware-level DirectInput override commands to Unreal Engine 5.
    """
    @staticmethod
    def press(scan_code: int):
        user32.keybd_event(0, scan_code, KEYEVENTF_SCANCODE, 0)

    @staticmethod
    def release(scan_code: int):
        user32.keybd_event(0, scan_code, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0)

    @classmethod
    def apply_override(cls, brake_intensity: float):
        if brake_intensity >= 0.85:
            # Full emergency stop
            cls.press(DIK_S)
            cls.press(DIK_SPACE)
        elif brake_intensity > 0.3:
            # Moderate slowdown
            cls.press(DIK_S)
            cls.release(DIK_SPACE)
        else:
            cls.release(DIK_S)
            cls.release(DIK_SPACE)

    @classmethod
    def release_all(cls):
        cls.release(DIK_S)
        cls.release(DIK_SPACE)


class AsyncUE5Capture:
    def __init__(self, target_title: str = "SAFAR_Sim", target_fps: float = 30.0):
        self.target_title = target_title
        self.target_fps = target_fps
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.hwnd = None
        self.worker_thread = None

    def find_window(self) -> bool:
        def enum_cb(hwnd, extra):
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
        cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb)
        user32.EnumWindows(cb, 0)
        return self.hwnd is not None

    def start(self):
        self.running = True
        self.find_window()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
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
            time.sleep(max(0.001, delay - elapsed))

        if sct is not None:
            sct.close()

    def get_latest_frame(self, timeout_s: float = 0.5) -> np.ndarray:
        try:
            return self.frame_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False


class SAFAR_UE5_LiveSystem:
    """
    Integrates the full SAFAR Decision & Intervention System:
    - YOLO Perception Detector
    - Lead Hazard Selector (Corridor Filtering)
    - Temporal Confirmation Tracker (5-State Confirmation: NONE -> CANDIDATE -> CONFIRMED -> HAZARD -> CLEARED)
    - RiskEngine (Policy Evaluation)
    - SafetyOverrideController (Brake/Throttle Interventions)
    """
    def __init__(self, target_title: str = "SAFAR_Sim", conf_threshold: float = 0.28):
        self.capture = AsyncUE5Capture(target_title=target_title, target_fps=30.0)
        self.detector = YoloDetector(conf_threshold=conf_threshold)
        self.lead_selector = LeadHazardSelector()
        self.tracker = TemporalConfirmationTracker(required_confirmations=2, clearance_frames=3)
        self.risk_engine = RiskEngine()
        self.override_controller = SafetyOverrideController()
        self.actuator = DirectInputActuator()

    def run(self):
        print("======================================================================")
        print(" SAFAR PRODUCTION CORE — UNREAL ENGINE 5 LIVE ADAPTER")
        print("======================================================================")
        print(" [ENGINE] RiskEngine + TemporalConfirmationTracker Active")
        print(" [INTERVENTION] Hardware DirectInput Override Armed")
        print("======================================================================\n")

        self.capture.start()
        fps_time = time.time()
        fps_count = 0
        display_fps = 30.0

        try:
            while True:
                t0 = time.perf_counter()
                frame_img = self.capture.get_latest_frame(timeout_s=0.1)
                if frame_img is None:
                    time.sleep(0.005)
                    continue

                h, w = frame_img.shape[:2]

                # 1. Perception Layer (YOLO)
                raw_detections = self.detector.detect_frame(frame_img)

                # 2. Lead Hazard Selection (Ego Path Filter)
                lead_candidate = self.lead_selector.select_lead_hazard(raw_detections, (w, h))

                # 3. Temporal Confirmation State Machine (Eliminates False Positives)
                confirmed_hazard, track_state = self.tracker.update(lead_candidate)

                # 4. Ego Vehicle State
                lane = LaneContext(road_id=1, lane_id=1, lane_type="driving", lane_width_m=3.5, is_junction=False)
                ego_state = VehicleState(speed_mps=15.0, position=(0.0, 0.0), velocity=(0.0, 15.0), heading_deg=0.0, lane=lane)

                # 5. SAFAR Risk Engine Assessment
                obstacles = [confirmed_hazard] if confirmed_hazard else []
                risk_assessment = self.risk_engine.evaluate(ego_state, obstacles)

                # 6. Safety Override Controller
                driver_throttle = 1.0
                driver_brake = 0.0
                command = self.override_controller.compute_intervention(
                    risk_assessment.level,
                    driver_throttle,
                    driver_brake
                )

                # 7. Apply Physical Vehicle Intervention to UE5
                if command.override_active:
                    self.actuator.apply_override(command.brake)
                else:
                    self.actuator.release_all()

                # FPS and Latency
                fps_count += 1
                if time.time() - fps_time >= 1.0:
                    display_fps = fps_count / (time.time() - fps_time)
                    fps_count = 0
                    fps_time = time.time()

                t_end = time.perf_counter()
                latency_ms = (t_end - t0) * 1000.0

                # Render Diagnostic HUD
                hud = frame_img.copy()

                # Draw Ego Path Corridor
                pts = np.array([
                    [int(w * 0.40), int(h * 0.45)],
                    [int(w * 0.60), int(h * 0.45)],
                    [int(w * 0.85), h],
                    [int(w * 0.15), h]
                ], np.int32)
                cv2.polylines(hud, [pts], isClosed=True, color=(0, 230, 118), thickness=2)

                # Draw Detected Objects
                for det in raw_detections:
                    bx1, by1, bx2, by2 = det.bbox_pixels
                    is_lead = (confirmed_hazard and det.id == confirmed_hazard.id)

                    box_color = (0, 230, 118)  # Green
                    if is_lead:
                        if risk_assessment.level == RiskLevel.CRITICAL:
                            box_color = (0, 0, 255)  # Red
                        elif risk_assessment.level == RiskLevel.HIGH:
                            box_color = (0, 165, 255)  # Orange
                        elif risk_assessment.level == RiskLevel.MEDIUM:
                            box_color = (0, 255, 255)  # Yellow

                    cv2.rectangle(hud, (bx1, by1), (bx2, by2), box_color, 2 if not is_lead else 3)
                    lbl = f"{det.class_name} ({det.confidence:.2f})"
                    if is_lead:
                        lbl += f" [STATE: {track_state.name}]"
                    cv2.putText(hud, lbl, (bx1, max(20, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 2)

                # Diagnostic Banner
                banner_color = (20, 25, 30)
                if command.override_active:
                    banner_color = (0, 0, 160)  # Red Alert
                elif risk_assessment.level == RiskLevel.MEDIUM:
                    banner_color = (0, 120, 160)

                cv2.rectangle(hud, (0, 0), (w, 55), banner_color, -1)

                risk_str = f"SAFAR: {risk_assessment.level.name} | STATE: {track_state.name} | ACTION: {risk_assessment.action}"
                cv2.putText(hud, risk_str, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

                ctrl_str = f"OVERRIDE: {'ENGAGED (BRAKE: 1.0)' if command.override_active else 'STANDBY'} | FPS: {display_fps:.1f} | Latency: {latency_ms:.1f}ms"
                ctrl_color = (0, 0, 255) if command.override_active else (0, 230, 118)
                cv2.putText(hud, ctrl_str, (12, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.42, ctrl_color, 1)

                cv2.imshow("SAFAR Core Production - Unreal Engine 5 Live Safety Override", hud)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            self.actuator.release_all()
            self.capture.stop()
            cv2.destroyAllWindows()
            print("\n[INFO] SAFAR UE5 session cleanly released and terminated.")


if __name__ == "__main__":
    runner = SAFAR_UE5_LiveSystem()
    runner.run()
