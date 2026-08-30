"""
SAFAR Autonomous Vehicle Behavior Controller (Headless ADAS Engine)
No HUD windows, no UI clutter — purely modifies the vehicle's physical driving behavior in Unreal Engine 5:
1. Normal Driving: Full driver throttle and acceleration.
2. Forward Obstacle Approach: Automatically restricts throttle / applies gentle deceleration.
3. Imminent Hazard (AEB): Fully overrides driver and locks emergency brakes to prevent collision.
4. Auto-Release: Restores driver control once path is clear.
"""
import time
import sys
import os
import argparse
import threading
import queue
import cv2
import numpy as np
import ctypes
from ctypes import wintypes

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

from safar.perception.yolo_detector import YOLODetector
from safar.perception.image_tracker import ImageTracker
from safar.perception.ego_path import EgoPathModel
from safar.integrations.the_crew2.config import TheCrew2Config
from safar.integrations.the_crew2.hazard import TheCrew2HazardEngine, ConfirmationState
from safar.integrations.the_crew2.controller import TheCrew2Controller, ControlState

user32 = ctypes.windll.user32


class AsyncUE5CaptureWorker:
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


class HeadlessSAFARVehicleBehavior:
    def __init__(self, target_title: str = "SAFAR_Sim", conf_threshold: float = 0.28):
        self.config = TheCrew2Config()
        self.capture = AsyncUE5CaptureWorker(target_title=target_title, target_fps=30.0)
        self.detector = YOLODetector(confidence_threshold=conf_threshold)
        self.tracker = ImageTracker()
        self.ego_path = EgoPathModel()
        self.hazard_engine = TheCrew2HazardEngine(self.config)
        self.controller = TheCrew2Controller(self.config)

    def run(self):
        print("======================================================================")
        print(" SAFAR ADAS — AUTONOMOUS VEHICLE BEHAVIOR ENGINE (HEADLESS)")
        print("======================================================================")
        print(" [STATUS] Monitoring Unreal Engine 5 Vehicle Viewport...")
        print(" [BEHAVIOR MODES]")
        print("  • PATH CLEAR:         100% Responsive Driver Control")
        print("  • APPROACHING HAZARD: Active Slowdown (Throttle Restrained)")
        print("  • IMMINENT HAZARD:    Autonomous Emergency Braking (AEB Override)")
        print("======================================================================\n")

        self.capture.start()
        frame_idx = 0
        last_state = ""

        try:
            while True:
                frame_img = self.capture.get_latest_frame(timeout_s=0.1)
                if frame_img is None:
                    time.sleep(0.005)
                    continue

                h, w = frame_img.shape[:2]
                frame_idx += 1

                # 1. Perception
                detections = self.detector.detect(frame_img)

                # 2. Tracking
                tracks = self.tracker.update(detections)

                # 3. Path Relevance
                relevance_map = {}
                for trk in tracks:
                    rel = self.ego_path.evaluate(trk.bbox, w, h)
                    relevance_map[trk.track_id] = rel

                # 4. Lead Hazard Selection & Risk Evaluation
                hazard_result = self.hazard_engine.evaluate_frame(tracks, relevance_map, w, h)

                # 5. Direct Physical Actuation into Unreal Engine 5 Vehicle
                control_event = self.controller.update(hazard_result)

                # Print clean live behavior state whenever state changes or during alerts
                is_override = self.controller.is_overriding
                current_state = f"RISK: {hazard_result.risk_level:<8} | ACTION: {hazard_result.decision:<15} | BEHAVIOR: {'[AEB EMERGENCY BRAKE LOCKED]' if is_override else '[NORMAL CRUISE / DRIVER ACTIVE]'}"
                
                if current_state != last_state or is_override:
                    lead_info = f" (Hazard: {hazard_result.lead_class} #{hazard_result.lead_track_id})" if hazard_result.lead_class else ""
                    print(f"[SAFAR BEHAVIOR] {current_state}{lead_info}")
                    last_state = current_state

        except KeyboardInterrupt:
            pass
        finally:
            self.controller.release_all()
            self.capture.stop()
            print("\n[INFO] SAFAR Behavior Engine safely disengaged.")


def main():
    parser = argparse.ArgumentParser(description="SAFAR Headless Vehicle Behavior Engine")
    parser.add_argument("--window", type=str, default="SAFAR_Sim", help="Target UE5 window substring")
    parser.add_argument("--conf", type=float, default=0.28, help="YOLO confidence threshold")
    args = parser.parse_args()

    app = HeadlessSAFARVehicleBehavior(target_title=args.window, conf_threshold=args.conf)
    app.run()


if __name__ == "__main__":
    main()
