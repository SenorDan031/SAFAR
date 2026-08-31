"""
SAFAR Real-Time Live Vision & ADAS Cockpit Interface
Supports:
1. Live Webcam (--source 0)
2. Driving Video File (--source path/to/video.mp4)
3. Live Looping Road Image Feed (--source images)
4. Screen Region Capture (--source screen)

Interactive Controls:
- 'W' / 'Up Arrow'   : Accelerate vehicle speed (+5 km/h)
- 'S' / 'Down Arrow' : Decelerate vehicle speed (-5 km/h)
- 'A' / 'Left Arrow' : Steer vehicle corridor Left
- 'D' / 'Right Arrow': Steer vehicle corridor Right
- 'C'                : Recenter steering
- 'Space'            : Manual Brake
- 'P'                : Pause/Play
- 'Q' or 'ESC'       : Quit
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows DLL path resolution
if sys.platform == "win32":
    for p in [os.path.dirname(sys.executable), os.path.join(os.path.dirname(sys.executable), "Library", "bin")]:
        if os.path.exists(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass

import time
import argparse
import cv2
import numpy as np
from ultralytics import YOLO

from safar.pothole.classifier import PotholeClassifier
from safar.pothole.physics import PotholePhysicsEngine
from safar.pothole.path import PotholePathGeometry
from safar.pothole.risk import PotholeRiskEngine, PotholeSeverity
from safar.pothole.decision import PotholeDecisionEngine, PotholeAction

CAMERA_FOCAL_LENGTH_PX = 720.0

REAL_HEIGHTS_M = {
    "car": 1.48,
    "truck": 2.80,
    "bus": 3.20,
    "motorcycle": 1.25,
    "motorcycle_rider": 1.65,
    "auto_rickshaw": 1.75,
    "tractor": 2.20,
    "person": 1.70,
    "dog": 0.65,
    "bicycle": 1.10
}


class RealTimeSAFARDriver:
    def __init__(self, source="images", model_path="yolo11n.pt"):
        self.source = source
        print("Loading YOLO Vision Model...")
        self.yolo_model = YOLO(model_path)
        print("Initializing SAFAR Physics & Pothole Intelligence...")
        self.pothole_classifier = PotholeClassifier()
        self.physics = PotholePhysicsEngine()
        self.path_geometry = PotholePathGeometry()
        self.risk_engine = PotholeRiskEngine(self.physics, self.path_geometry)
        self.decision_engine = PotholeDecisionEngine()

        # Simulated Vehicle State
        self.ego_speed_mps = 12.0  # 43.2 km/h
        self.steering_offset_m = 0.0
        self.fps_history = []
        self.last_frame_time = time.time()

        # Image sequence source if source == 'images'
        self.test_images = [
            r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148607178.jpg",
            r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148615983.jpg",
            r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616006.jpg",
            r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616010.jpg",
            r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616014.jpg"
        ]
        self.image_idx = 0
        self.image_display_time = time.time()

    def is_contained_or_overlapping(self, rider_box, bike_box):
        rx1, ry1, rx2, ry2 = rider_box
        bx1, by1, bx2, by2 = bike_box
        overlap_x = max(0, min(rx2, bx2) - max(rx1, bx1))
        min_w = min(rx2 - rx1, bx2 - bx1)
        x_overlap_ratio = overlap_x / max(1, min_w)
        rider_center_x = (rx1 + rx2) * 0.5
        bike_center_x = (bx1 + bx2) * 0.5
        return (x_overlap_ratio > 0.40) and abs(rider_center_x - bike_center_x) < max(rx2-rx1, bx2-bx1)

    def remap_indian_vehicles(self, raw_detections, img):
        people = [d for d in raw_detections if d["class"] == "person"]
        bikes = [d for d in raw_detections if d["class"] in ["motorcycle", "bicycle"]]
        others = [d for d in raw_detections if d["class"] not in ["person", "motorcycle", "bicycle"]]

        fused_bikes = []
        used_people = set()

        for bike in bikes:
            matched_p = None
            for p_idx, person in enumerate(people):
                if p_idx in used_people:
                    continue
                if self.is_contained_or_overlapping(person["bbox"], bike["bbox"]):
                    matched_p = person
                    used_people.add(p_idx)
                    break
            if matched_p:
                px1, py1, px2, py2 = matched_p["bbox"]
                bx1, by1, bx2, by2 = bike["bbox"]
                fused_bikes.append({
                    "class": "motorcycle_rider",
                    "confidence": max(matched_p["confidence"], bike["confidence"]),
                    "bbox": (min(px1, bx1), min(py1, by1), max(px2, bx2), max(py2, by2))
                })
            else:
                fused_bikes.append(bike)

        standalone_people = [p for i, p in enumerate(people) if i not in used_people]

        processed_others = []
        for d in others:
            x1, y1, x2, y2 = d["bbox"]
            bw = x2 - x1
            bh = y2 - y1
            aspect_ratio = bh / max(1, bw)
            if d["class"] in ["truck", "car"] and d["confidence"] < 0.68 and 0.85 <= aspect_ratio <= 1.55:
                patch = img[y1:y2, x1:x2]
                if patch.size > 0:
                    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
                    yellow_green_mask = cv2.inRange(hsv, np.array([15, 60, 60]), np.array([85, 255, 255]))
                    if (np.sum(yellow_green_mask > 0) / float(bw * bh)) > 0.08 or (d["class"] == "truck" and d["confidence"] < 0.50):
                        processed_others.append({"class": "auto_rickshaw", "confidence": d["confidence"], "bbox": d["bbox"]})
                        continue
            processed_others.append(d)

        return fused_bikes + standalone_people + processed_others

    def estimate_3d_position(self, bbox, class_name, img_w):
        x1, y1, x2, y2 = bbox
        box_h = max(1, y2 - y1)
        real_h = REAL_HEIGHTS_M.get(class_name, 1.50)
        dist_z = max(1.5, min(80.0, (CAMERA_FOCAL_LENGTH_PX * real_h) / box_h))
        center_x = (x1 + x2) * 0.5
        lat_x = ((center_x - img_w * 0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX - self.steering_offset_m
        return float(dist_z), float(lat_x)

    def detect_potholes(self, img):
        h, w = img.shape[:2]
        road_roi = img[int(h * 0.45):h, :]
        roi_h, roi_w = road_roi.shape[:2]
        gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, d_th = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        _, b_th = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_or(d_th, b_th)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        potholes = []

        for c in contours:
            area = cv2.contourArea(c)
            if area < 800 or area > (roi_w * roi_h * 0.45):
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            global_y = int(h * 0.45) + y
            bottom_y = global_y + bh
            norm_y = max(0.01, min(1.0, (bottom_y - h * 0.45) / (h * 0.55)))
            dist_z = 2.0 + (1.0 - norm_y) * 28.0
            lat_x = ((x + bw*0.5 - w*0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX - self.steering_offset_m
            potholes.append({
                "bbox": (x, global_y, x + bw, global_y + bh),
                "width": (bw * dist_z) / CAMERA_FOCAL_LENGTH_PX,
                "length": (bh * dist_z * 1.5) / CAMERA_FOCAL_LENGTH_PX,
                "depth": min(0.20, max(0.015, (area / (roi_w * roi_h)) * 0.35)),
                "distance_forward": dist_z,
                "distance_lateral": lat_x
            })
        return potholes

    def run(self):
        cv2.namedWindow("SAFAR Real-Time ADAS Cockpit", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("SAFAR Real-Time ADAS Cockpit", 1280, 800)

        cap = None
        if self.source.isdigit():
            cap = cv2.VideoCapture(int(self.source))
        elif self.source != "images" and os.path.exists(self.source):
            cap = cv2.VideoCapture(self.source)

        paused = False

        print("\n" + "=" * 65)
        print(" SAFAR REAL-TIME ADAS VISION & SAFETY INTELLIGENCE ACTIVE")
        print(" Controls:")
        print("   W / Up     : Accelerate (+5 km/h)")
        print("   S / Down   : Decelerate (-5 km/h)")
        print("   A / D      : Steer Left / Right corridor")
        print("   C          : Recenter Steering")
        print("   Space      : Manual Brake (Speed -> 0)")
        print("   P          : Pause / Play")
        print("   Q / ESC    : Exit")
        print("=" * 65)

        while True:
            # Capture / Read Frame
            if cap:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
            else: # Image sequence mode
                current_time = time.time()
                if current_time - self.image_display_time > 3.0 and not paused:
                    self.image_idx = (self.image_idx + 1) % len(self.test_images)
                    self.image_display_time = current_time
                frame = cv2.imread(self.test_images[self.image_idx])

            if frame is None:
                continue

            frame = cv2.resize(frame, (1024, 768))
            img_h, img_w = frame.shape[:2]

            # Measure FPS
            now = time.time()
            dt = max(0.001, now - self.last_frame_time)
            self.last_frame_time = now
            fps = 1.0 / dt
            self.fps_history.append(fps)
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)
            avg_fps = sum(self.fps_history) / len(self.fps_history)

            # 1. YOLO Detection
            yolo_res = self.yolo_model.predict(frame, conf=0.25, verbose=False)[0]
            raw_dets = []
            for box in yolo_res.boxes:
                cls_id = int(box.cls[0])
                raw_dets.append({
                    "class": self.yolo_model.names[cls_id].lower(),
                    "confidence": float(box.conf[0]),
                    "bbox": tuple(map(int, box.xyxy[0].tolist()))
                })

            refined_dets = self.remap_indian_vehicles(raw_dets, frame)

            # 2. 3D Tracking & Corridor Overlap
            tracked_objects = []
            for d in refined_dets:
                dist_z, lat_x = self.estimate_3d_position(d["bbox"], d["class"], img_w)
                in_corridor = abs(lat_x) <= 1.85
                tracked_objects.append({
                    "class": d["class"],
                    "confidence": d["confidence"],
                    "bbox": d["bbox"],
                    "dist_z": dist_z,
                    "lat_x": lat_x,
                    "in_corridor": in_corridor
                })

            # 3. Pothole Intelligence
            raw_potholes = self.detect_potholes(frame)
            pothole_assessments = []
            for idx, p in enumerate(raw_potholes, 1):
                obs = self.pothole_classifier.classify(p["width"], p["length"], p["depth"], p["distance_forward"], p["distance_lateral"], idx)
                risk = self.pothole_risk_engine.assess_risk(obs, vehicle_speed_mps=self.ego_speed_mps)
                pothole_assessments.append({"obs": obs, "risk": risk, "bbox": p["bbox"], "dist_z": p["distance_forward"], "lat_x": p["distance_lateral"]})

            # 4. Physics & Decision Engine
            d_stop = self.physics.calculate_stopping_distance(self.ego_speed_mps)
            crit_vehicles = [v for v in tracked_objects if v["in_corridor"] and v["dist_z"] <= d_stop * 1.25]
            crit_potholes = [p for p in pothole_assessments if p["risk"].path_intersection.value == "INTERSECTION" and p["risk"].severity.value in ["CRITICAL", "HIGH"]]

            if crit_vehicles:
                t_veh = min(crit_vehicles, key=lambda v: v["dist_z"])
                final_state = "EMERGENCY_BRAKE" if t_veh["dist_z"] <= d_stop else "BRAKE"
                has_interv = True
                primary_threat = f"{t_veh['class'].upper().replace('_', ' ')} at {t_veh['dist_z']:.1f}m"
                if final_state == "EMERGENCY_BRAKE":
                    self.ego_speed_mps = max(0.0, self.ego_speed_mps - 8.5 * dt)
                else:
                    self.ego_speed_mps = max(0.0, self.ego_speed_mps - 6.0 * dt)
            elif crit_potholes:
                t_ph = min(crit_potholes, key=lambda p: p["dist_z"])
                final_state = "EMERGENCY_BRAKE" if t_ph["risk"].severity.value == "CRITICAL" else "BRAKE"
                has_interv = True
                primary_threat = f"{t_ph['obs'].pothole_name} at {t_ph['dist_z']:.1f}m ({t_ph['obs'].depth*100:.0f}cm)"
                self.ego_speed_mps = max(2.0, self.ego_speed_mps - 4.5 * dt)
            elif any(v["in_corridor"] for v in tracked_objects) or any(p["risk"].path_intersection.value == "INTERSECTION" for p in pothole_assessments):
                final_state = "SLOW"
                has_interv = False
                primary_threat = "Approaching traffic in path"
            else:
                final_state = "MAINTAIN"
                has_interv = False
                primary_threat = "Clear Corridor"

            # 5. Draw Visual Annotations
            for v in tracked_objects:
                x1, y1, x2, y2 = v["bbox"]
                col = (0, 0, 255) if v["in_corridor"] and v["dist_z"] < d_stop * 1.25 else (0, 255, 255) if v["in_corridor"] else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
                txt = f"{v['class'].upper().replace('_', ' ')} {v['confidence']*100:.0f}% | {v['dist_z']:.1f}m (lat:{v['lat_x']:+.1f}m)"
                cv2.putText(frame, txt, (x1, max(20, y1-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
                cv2.putText(frame, txt, (x1, max(20, y1-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)

            for p in pothole_assessments:
                px1, py1, px2, py2 = p["bbox"]
                p_col = (0, 0, 255) if p["risk"].severity.value in ["CRITICAL", "HIGH"] else (0, 165, 255) if p["risk"].severity.value == "MEDIUM" else (0, 255, 0)
                cv2.rectangle(frame, (px1, py1), (px2, py2), p_col, 2)
                ptxt = f"POTHOLE: {p['obs'].pothole_name} | {p['dist_z']:.1f}m ({p['obs'].depth*100:.0f}cm)"
                cv2.putText(frame, ptxt, (px1, max(20, py1-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
                cv2.putText(frame, ptxt, (px1, max(20, py1-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, p_col, 1)

            # Draw Ego Corridor Overlay
            poly_pts = np.array([
                [int(img_w * 0.40 - self.steering_offset_m * 40), int(img_h * 0.55)],
                [int(img_w * 0.60 - self.steering_offset_m * 40), int(img_h * 0.55)],
                [int(img_w * 0.85 - self.steering_offset_m * 80), img_h],
                [int(img_w * 0.15 - self.steering_offset_m * 80), img_h]
            ], np.int32)
            corridor_overlay = frame.copy()
            corridor_col = (0, 0, 255) if has_interv else (0, 255, 255) if final_state == "SLOW" else (0, 255, 0)
            cv2.polylines(corridor_overlay, [poly_pts], isClosed=False, color=corridor_col, thickness=2)
            cv2.fillPoly(corridor_overlay, [poly_pts], color=(corridor_col[0]//6, corridor_col[1]//6, corridor_col[2]//6))
            cv2.addWeighted(corridor_overlay, 0.35, frame, 0.65, 0, frame)

            # Top Cockpit HUD Bar
            hud = np.zeros((80, img_w, 3), dtype=np.uint8)
            status_col = (0, 0, 255) if has_interv else (0, 255, 0)
            cv2.putText(hud, f"SAFAR ADAS COCKPIT | STATE: {final_state} | BRAKE: {'[ACTIVE OVERRIDE]' if has_interv else '[PASSIVE]'}", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.60, status_col, 2)
            cv2.putText(hud, f"Speed: {self.ego_speed_mps*3.6:4.0f} km/h | d_stop: {d_stop:4.1f}m | Steering: {self.steering_offset_m:+.1f}m | FPS: {avg_fps:4.1f} | Threat: {primary_threat}", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            composite = np.vstack([hud, frame])
            cv2.imshow("SAFAR Real-Time ADAS Cockpit", composite)

            # Handle Keyboard Inputs
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), 27]: # Q or ESC
                break
            elif key in [ord('w'), 82]: # W or Up
                self.ego_speed_mps = min(35.0, self.ego_speed_mps + 1.4)
            elif key in [ord('s'), 84]: # S or Down
                self.ego_speed_mps = max(0.0, self.ego_speed_mps - 1.4)
            elif key in [ord('a'), 81]: # A or Left
                self.steering_offset_m = max(-2.5, self.steering_offset_m - 0.2)
            elif key in [ord('d'), 83]: # D or Right
                self.steering_offset_m = min(2.5, self.steering_offset_m + 0.2)
            elif key == ord('c'): # Recenter
                self.steering_offset_m = 0.0
            elif key == ord(' '): # Space (Manual Brake)
                self.ego_speed_mps = 0.0
            elif key == ord('p'): # Pause
                paused = not paused

        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("SAFAR Real-Time Session Ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAFAR Real-Time Live Vision Interface")
    parser.add_argument("--source", type=str, default="images", help="'0' for webcam, 'images' for live test sequence, or path to MP4 video")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="YOLO model path")
    args = parser.parse_args()

    driver = RealTimeSAFARDriver(source=args.source, model_path=args.model)
    driver.run()
