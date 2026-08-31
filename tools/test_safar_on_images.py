"""
SAFAR Real-World Image Vision & Safety Intelligence Test Pipeline
With Indian Road Vehicle Enhancements:
1. Rider-Vehicle Spatial IoU Fusion (Merges overlapping Person + Motorcycle into unified Two-Wheeler)
2. Auto-Rickshaw / Three-Wheeler Detection & Remapping (Corrects COCO Truck/Car misclassifications)
3. Pothole / Crater Optical Segmentation & Physics Risk Assessment
4. Stopping Distance & State Machine Decision Generation
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

import json
import math
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from safar.pothole.classifier import PotholeClassifier, PotholeObservation
from safar.pothole.physics import PotholePhysicsEngine
from safar.pothole.path import PotholePathGeometry, PathIntersectionStatus
from safar.pothole.risk import PotholeRiskEngine, PotholeSeverity
from safar.pothole.decision import PotholeDecisionEngine, PotholeAction

# Camera Calibration Parameters
CAMERA_FOCAL_LENGTH_PX = 720.0

# Real-world physical heights (meters) for accurate distance estimation
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


class SAFARImageVisionTester:
    def __init__(self, output_dir: str = "logs/image_test_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.yolo_model = YOLO("yolo11n.pt")
        self.pothole_classifier = PotholeClassifier()
        self.physics = PotholePhysicsEngine()
        self.path_geometry = PotholePathGeometry()
        self.pothole_risk_engine = PotholeRiskEngine(self.physics, self.path_geometry)
        self.pothole_decision_engine = PotholeDecisionEngine()

    def calculate_iou(self, boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        """Calculates Intersection-over-Union (IoU) between two bounding boxes."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

        return interArea / float(boxAArea + boxBArea - interArea)

    def is_contained_or_overlapping(self, rider_box: Tuple[int, int, int, int], bike_box: Tuple[int, int, int, int]) -> bool:
        """Checks if a person is seated on or overlapping with a motorcycle."""
        rx1, ry1, rx2, ry2 = rider_box
        bx1, by1, bx2, by2 = bike_box

        # Horizontal overlap
        overlap_x = max(0, min(rx2, bx2) - max(rx1, bx1))
        min_w = min(rx2 - rx1, bx2 - bx1)
        x_overlap_ratio = overlap_x / max(1, min_w)

        # Rider's bottom is near bike center or top
        rider_center_x = (rx1 + rx2) * 0.5
        bike_center_x = (bx1 + bx2) * 0.5
        center_dist = abs(rider_center_x - bike_center_x)

        return (x_overlap_ratio > 0.40 or self.calculate_iou(rider_box, bike_box) > 0.20) and center_dist < max(rx2-rx1, bx2-bx1)

    def remap_indian_vehicles(self, raw_detections: List[Dict[str, Any]], img: np.ndarray) -> List[Dict[str, Any]]:
        """
        1. Fuses person + motorcycle into a single MOTORCYCLE_RIDER entity.
        2. Remaps misclassified Auto-Rickshaws (often detected as low-confidence truck/car).
        """
        people = [d for d in raw_detections if d["class"] == "person"]
        bikes = [d for d in raw_detections if d["class"] in ["motorcycle", "bicycle"]]
        others = [d for d in raw_detections if d["class"] not in ["person", "motorcycle", "bicycle"]]

        fused_bikes = []
        used_people_indices = set()
        used_bike_indices = set()

        for b_idx, bike in enumerate(bikes):
            matched_person = None
            matched_p_idx = -1
            for p_idx, person in enumerate(people):
                if p_idx in used_people_indices:
                    continue
                if self.is_contained_or_overlapping(person["bbox"], bike["bbox"]):
                    matched_person = person
                    matched_p_idx = p_idx
                    break

            if matched_person:
                # Merge into unified MOTORCYCLE_RIDER bounding box
                px1, py1, px2, py2 = matched_person["bbox"]
                bx1, by1, bx2, by2 = bike["bbox"]
                merged_bbox = (min(px1, bx1), min(py1, by1), max(px2, bx2), max(py2, by2))
                merged_conf = max(matched_person["confidence"], bike["confidence"])

                fused_bikes.append({
                    "class": "motorcycle_rider",
                    "confidence": merged_conf,
                    "bbox": merged_bbox
                })
                used_people_indices.add(matched_p_idx)
                used_bike_indices.add(b_idx)
            else:
                fused_bikes.append(bike)

        # Retain standalone pedestrians not riding vehicles
        standalone_people = [p for i, p in enumerate(people) if i not in used_people_indices]

        # Auto-Rickshaw remapping logic
        processed_others = []
        for d in others:
            x1, y1, x2, y2 = d["bbox"]
            bw = x2 - x1
            bh = y2 - y1
            aspect_ratio = bh / max(1, bw)

            # Auto-rickshaw signature: compact 3-wheeler boxy cabin (aspect ~ 1.0 - 1.4), front windshield + canopy
            # Frequently misdetected by standard COCO as truck (confidence < 0.65) or car (confidence < 0.65)
            if d["class"] in ["truck", "car"] and d["confidence"] < 0.68 and 0.85 <= aspect_ratio <= 1.55:
                # Inspect patch color (Indian auto-rickshaws are typically Green/Yellow or Black/Yellow)
                patch = img[y1:y2, x1:x2]
                if patch.size > 0:
                    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
                    # Check for yellow/green hue
                    yellow_green_mask = cv2.inRange(hsv, np.array([15, 60, 60]), np.array([85, 255, 255]))
                    yg_ratio = np.sum(yellow_green_mask > 0) / float(bw * bh)
                    
                    if yg_ratio > 0.08 or (d["class"] == "truck" and d["confidence"] < 0.50):
                        processed_others.append({
                            "class": "auto_rickshaw",
                            "confidence": d["confidence"],
                            "bbox": d["bbox"]
                        })
                        continue

            processed_others.append(d)

        return fused_bikes + standalone_people + processed_others

    def estimate_3d_position(
        self,
        bbox: Tuple[int, int, int, int],
        class_name: str,
        img_w: int,
        img_h: int
    ) -> Tuple[float, float]:
        """
        Estimates longitudinal distance (forward Z in meters) and lateral offset (X in meters).
        """
        x1, y1, x2, y2 = bbox
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        real_h = REAL_HEIGHTS_M.get(class_name, 1.50)

        # Distance estimation: Z = (f * H) / h_px
        distance_z = (CAMERA_FOCAL_LENGTH_PX * real_h) / box_h
        distance_z = max(1.5, min(80.0, distance_z))

        # Lateral position estimation: X = (center_x - img_w/2) * Z / f
        center_x = (x1 + x2) * 0.5
        cx = img_w * 0.5
        lateral_x = ((center_x - cx) * distance_z) / CAMERA_FOCAL_LENGTH_PX

        return float(distance_z), float(lateral_x)

    def detect_potholes_optically(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """Extracts road surface waterlogged puddles and depressions."""
        h, w = img.shape[:2]
        road_roi = img[int(h * 0.45):h, :]
        roi_h, roi_w = road_roi.shape[:2]

        gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        _, dark_thresh = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        _, bright_thresh = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        pothole_mask = cv2.bitwise_or(dark_thresh, bright_thresh)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        cleaned = cv2.morphologyEx(pothole_mask, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pothole_regions = []

        for c in contours:
            area = cv2.contourArea(c)
            if area < 800 or area > (roi_w * roi_h * 0.45):
                continue

            x, y, bw, bh = cv2.boundingRect(c)
            global_y = int(h * 0.45) + y
            bottom_y = global_y + bh

            norm_y = max(0.01, min(1.0, (bottom_y - h * 0.45) / (h * 0.55)))
            distance_z = 2.0 + (1.0 - norm_y) * 28.0

            est_width = (bw * distance_z) / CAMERA_FOCAL_LENGTH_PX
            est_length = (bh * distance_z * 1.5) / CAMERA_FOCAL_LENGTH_PX
            
            roi_patch = gray[y:y+bh, x:x+bw]
            std_dev = float(np.std(roi_patch))
            est_depth = min(0.20, max(0.015, (area / (roi_w * roi_h)) * 0.35 + (std_dev / 255.0) * 0.08))

            center_x = x + bw * 0.5
            lateral_x = ((center_x - (w * 0.5)) * distance_z) / CAMERA_FOCAL_LENGTH_PX

            pothole_regions.append({
                "bbox": (x, global_y, x + bw, global_y + bh),
                "width": float(est_width),
                "length": float(est_length),
                "depth": float(est_depth),
                "distance_forward": float(distance_z),
                "distance_lateral": float(lateral_x)
            })

        return pothole_regions

    def process_image(self, image_path: str, image_idx: int, ego_speed_mps: float = 12.0) -> Dict[str, Any]:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot load image from {image_path}")

        img_h, img_w = img.shape[:2]
        annotated_img = img.copy()

        # 1. Raw YOLO Vision
        yolo_res = self.yolo_model.predict(img, conf=0.25, verbose=False)[0]
        raw_detections = []

        for box in yolo_res.boxes:
            cls_id = int(box.cls[0])
            name = self.yolo_model.names[cls_id].lower()
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            raw_detections.append({
                "class": name,
                "confidence": conf,
                "bbox": (x1, y1, x2, y2)
            })

        # 2. Indian Road Specialization: Rider-Bike Fusion & Auto-Rickshaw Remapping
        refined_detections = self.remap_indian_vehicles(raw_detections, img)

        dynamic_objects = []
        for d in refined_detections:
            name = d["class"]
            conf = d["confidence"]
            x1, y1, x2, y2 = d["bbox"]

            dist_z, lat_x = self.estimate_3d_position((x1, y1, x2, y2), name, img_w, img_h)
            in_corridor = abs(lat_x) <= 1.85

            closing_speed = ego_speed_mps
            ttc = dist_z / closing_speed if closing_speed > 0.1 and in_corridor else -1.0

            dynamic_objects.append({
                "id": len(dynamic_objects) + 1,
                "class": name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "distance_forward_m": round(dist_z, 2),
                "distance_lateral_m": round(lat_x, 2),
                "in_corridor": in_corridor,
                "ttc_s": round(ttc, 2) if ttc > 0 else None
            })

            # Draw visual bounding box
            color = (0, 0, 255) if in_corridor and dist_z < 15.0 else (0, 255, 255) if in_corridor else (0, 255, 0)
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)
            label_text = f"{name.upper().replace('_', ' ')} {conf*100:.0f}% | {dist_z:.1f}m (lat:{lat_x:+.1f}m)"
            cv2.putText(annotated_img, label_text, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(annotated_img, label_text, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        # 3. Pothole / Road Surface Analysis
        raw_potholes = self.detect_potholes_optically(img)
        pothole_evaluations = []

        for p_idx, p in enumerate(raw_potholes, 1):
            obs = self.pothole_classifier.classify(
                width=p["width"],
                length=p["length"],
                depth=p["depth"],
                distance_forward=p["distance_forward"],
                distance_lateral=p["distance_lateral"],
                pothole_id=p_idx
            )

            risk_eval = self.pothole_risk_engine.assess_risk(obs, vehicle_speed_mps=ego_speed_mps)
            
            pothole_evaluations.append({
                "id": p_idx,
                "type": obs.pothole_name,
                "confidence": round(obs.confidence, 3),
                "dimensions_m": {
                    "width": round(p["width"], 2),
                    "length": round(p["length"], 2),
                    "depth_cm": round(p["depth"] * 100, 1)
                },
                "distance_forward_m": round(p["distance_forward"], 2),
                "distance_lateral_m": round(p["distance_lateral"], 2),
                "corridor_status": risk_eval.path_intersection.value,
                "risk_severity": risk_eval.severity.value,
                "risk_score": round(risk_eval.risk_score, 3),
                "recommended_speed_mps": round(risk_eval.recommended_speed_mps, 1),
                "recommended_action": risk_eval.recommended_action,
                "reason": risk_eval.reason
            })

            px1, py1, px2, py2 = p["bbox"]
            p_color = (0, 0, 255) if risk_eval.severity in [PotholeSeverity.CRITICAL, PotholeSeverity.HIGH] else (0, 165, 255) if risk_eval.severity == PotholeSeverity.MEDIUM else (0, 255, 0)
            cv2.rectangle(annotated_img, (px1, py1), (px2, py2), p_color, 2)
            ph_text = f"POTHOLE: {obs.pothole_name} | {p['distance_forward']:.1f}m ({p['depth']*100:.0f}cm deep)"
            cv2.putText(annotated_img, ph_text, (px1, max(25, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(annotated_img, ph_text, (px1, max(25, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, p_color, 1)

        # 4. Decision Arbitration
        d_stop = self.physics.calculate_stopping_distance(ego_speed_mps)
        critical_vehicles = [v for v in dynamic_objects if v["in_corridor"] and v["distance_forward_m"] <= d_stop * 1.25]
        critical_potholes = [p for p in pothole_evaluations if p["corridor_status"] == "INTERSECTION" and p["risk_severity"] in ["CRITICAL", "HIGH"]]

        if critical_vehicles:
            target_veh = min(critical_vehicles, key=lambda v: v["distance_forward_m"])
            final_state = "EMERGENCY_BRAKE" if target_veh["distance_forward_m"] <= d_stop else "BRAKE"
            has_intervention = True
            primary_hazard_desc = f"{target_veh['class'].upper().replace('_', ' ')} #{target_veh['id']} in corridor at {target_veh['distance_forward_m']}m"
            action_reason = f"Imminent collision risk with {target_veh['class']} in driving path (Distance: {target_veh['distance_forward_m']}m <= d_stop: {d_stop:.1f}m)"
        elif critical_potholes:
            target_ph = min(critical_potholes, key=lambda p: p["distance_forward_m"])
            final_state = "EMERGENCY_BRAKE" if target_ph["risk_severity"] == "CRITICAL" else "BRAKE"
            has_intervention = True
            primary_hazard_desc = f"{target_ph['type']} #{target_ph['id']} in path at {target_ph['distance_forward_m']}m ({target_ph['dimensions_m']['depth_cm']}cm deep)"
            action_reason = target_ph["reason"]
        elif any(p["corridor_status"] == "INTERSECTION" for p in pothole_evaluations) or any(v["in_corridor"] for v in dynamic_objects):
            final_state = "SLOW"
            has_intervention = False
            primary_hazard_desc = "Approaching traffic / road surface anomaly ahead"
            action_reason = "Moderating speed to safe threshold for road conditions"
        else:
            final_state = "MAINTAIN"
            has_intervention = False
            primary_hazard_desc = "Path Clear"
            action_reason = "Corridor clear. 100% manual driver control."

        hud_bg = np.zeros((70, img_w, 3), dtype=np.uint8)
        hud_color = (0, 0, 255) if has_intervention else (0, 255, 0)
        cv2.putText(hud_bg, f"SAFAR SAFETY SYSTEM | State: {final_state} | Override: {'ACTIVE (BRAKE)' if has_intervention else 'PASSIVE (MONITORING)'}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, hud_color, 2)
        cv2.putText(hud_bg, f"Ego Speed: {ego_speed_mps*3.6:.0f} km/h ({ego_speed_mps:.1f} m/s) | d_stop: {d_stop:.1f}m | Primary: {primary_hazard_desc}", (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        final_composite = np.vstack([hud_bg, annotated_img])
        output_image_path = os.path.join(self.output_dir, f"safar_annotated_img_{image_idx}.jpg")
        cv2.imwrite(output_image_path, final_composite)

        return {
            "image_index": image_idx,
            "source_path": image_path,
            "annotated_output_path": output_image_path,
            "ego_vehicle_state": {
                "speed_mps": ego_speed_mps,
                "speed_kmh": round(ego_speed_mps * 3.6, 1),
                "stopping_distance_m": round(d_stop, 2)
            },
            "dynamic_detections": dynamic_objects,
            "pothole_detections": pothole_evaluations,
            "safar_decision": {
                "state": final_state,
                "has_intervention": has_intervention,
                "primary_hazard": primary_hazard_desc,
                "reason": action_reason
            }
        }


def run_test():
    images = [
        r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148607178.jpg",
        r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148615983.jpg",
        r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616006.jpg",
        r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616010.jpg",
        r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616014.jpg"
    ]

    tester = SAFARImageVisionTester(output_dir=r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\logs\image_test_results")
    full_logs = []

    print("=" * 75)
    print(" SAFAR VISION PIPELINE WITH INDIAN ROAD VEHICLE REFINEMENTS")
    print("=" * 75)

    for idx, img_p in enumerate(images, 1):
        entry = tester.process_image(img_p, idx, ego_speed_mps=12.0)
        full_logs.append(entry)
        dec = entry["safar_decision"]
        print(f"\nImage {idx}: {os.path.basename(img_p)}")
        for d in entry["dynamic_detections"]:
            print(f"  -> Detected: {d['class'].upper()} (Conf: {d['confidence']*100:.0f}%, Dist: {d['distance_forward_m']}m, Lat: {d['distance_lateral_m']}m)")
        print(f"  SAFAR Decision: State = {dec['state']} | Primary: {dec['primary_hazard']}")

    log_file_path = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\logs\safar_image_test_log.json"
    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(full_logs, f, indent=2)

    print("\n" + "=" * 75)
    print(f" [SUCCESS] Output generated with Bike+Rider Fusion and Auto-Rickshaw Remapping.")
    print("=" * 75)


if __name__ == "__main__":
    run_test()
