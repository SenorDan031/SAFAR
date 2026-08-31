"""
SAFAR Real-World Image Vision & Safety Intelligence Test Pipeline
With Full P0 & P1 Enhancements:
1. P0: Transparent Causal Intervention Reason logging
2. P0: Wheel Track & Undercarriage Geometry Intersection
3. P0: Continuous Stopping Distance Risk Coupling
4. P0: Kinematic Time-To-Pothole (TTC) Calculation
5. P0: Confidence-Gated Risk Modulation
6. P1: Cohesive Road Surface Candidate Filtering (Morphological Patch Merging)
7. P1: Temporal Multi-Frame Pothole Tracking
8. P1: Multi-Threat Priority Arbitration Engine
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
from safar.pothole.tracker import PotholeTemporalTracker, TrackedPothole
from safar.pothole.arbitration import MultiThreatArbitrationEngine, UnifiedThreatItem

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


class SAFARImageVisionTester:
    def __init__(self, output_dir: str = "logs/image_test_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.yolo_model = YOLO("yolo11n.pt")
        self.pothole_classifier = PotholeClassifier()
        self.physics = PotholePhysicsEngine()
        self.path_geometry = PotholePathGeometry()
        self.risk_engine = PotholeRiskEngine(self.physics, self.path_geometry)
        self.decision_engine = PotholeDecisionEngine()
        self.tracker = PotholeTemporalTracker()
        self.arbitrator = MultiThreatArbitrationEngine()

    def is_contained_or_overlapping(self, rider_box: Tuple[int, int, int, int], bike_box: Tuple[int, int, int, int]) -> bool:
        rx1, ry1, rx2, ry2 = rider_box
        bx1, by1, bx2, by2 = bike_box
        overlap_x = max(0, min(rx2, bx2) - max(rx1, bx1))
        min_w = min(rx2 - rx1, bx2 - bx1)
        x_overlap_ratio = overlap_x / max(1, min_w)
        rider_center_x = (rx1 + rx2) * 0.5
        bike_center_x = (bx1 + bx2) * 0.5
        return (x_overlap_ratio > 0.40) and abs(rider_center_x - bike_center_x) < max(rx2-rx1, bx2-bx1)

    def remap_indian_vehicles(self, raw_detections: List[Dict[str, Any]], img: np.ndarray) -> List[Dict[str, Any]]:
        people = [d for d in raw_detections if d["class"] == "person"]
        bikes = [d for d in raw_detections if d["class"] in ["motorcycle", "bicycle"]]
        others = [d for d in raw_detections if d["class"] not in ["person", "motorcycle", "bicycle"]]

        fused_bikes = []
        used_people = set()

        for bike in bikes:
            bx1, by1, bx2, by2 = bike["bbox"]
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
            bw, bh = x2 - x1, y2 - y1
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

    def estimate_3d_position(self, bbox: Tuple[int, int, int, int], class_name: str, img_w: int) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        box_h = max(1, y2 - y1)
        real_h = REAL_HEIGHTS_M.get(class_name, 1.50)
        dist_z = max(1.5, min(80.0, (CAMERA_FOCAL_LENGTH_PX * real_h) / box_h))
        center_x = (x1 + x2) * 0.5
        lat_x = ((center_x - img_w * 0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX
        return float(dist_z), float(lat_x)

    def detect_potholes_cohesive(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        P1 Enhanced Road Surface Candidate Filtering:
        Uses multi-scale morphological merging to form clean, cohesive puddle and crater candidates.
        """
        h, w = img.shape[:2]
        road_roi = img[int(h * 0.45):h, :]
        roi_h, roi_w = road_roi.shape[:2]

        gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        # Dual threshold for water reflections & shadow depressions
        _, dark_th = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        _, bright_th = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        raw_mask = cv2.bitwise_or(dark_th, bright_th)

        # Large elliptical closing kernel to merge adjacent disconnected water puddles into cohesive craters
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 15))
        merged_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, close_kernel)
        
        # Small opening kernel to remove high-frequency speckle noise
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cleaned_mask = cv2.morphologyEx(merged_mask, cv2.MORPH_OPEN, open_kernel)

        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cohesive_potholes = []

        for c in contours:
            area = cv2.contourArea(c)
            # Filter out tiny noise (< 1500 px) or full-screen artifacts (> 40% of road ROI)
            if area < 1500 or area > (roi_w * roi_h * 0.40):
                continue

            x, y, bw, bh = cv2.boundingRect(c)
            global_y = int(h * 0.45) + y
            bottom_y = global_y + bh

            norm_y = max(0.01, min(1.0, (bottom_y - h * 0.45) / (h * 0.55)))
            dist_z = 2.0 + (1.0 - norm_y) * 28.0

            est_w = (bw * dist_z) / CAMERA_FOCAL_LENGTH_PX
            est_l = (bh * dist_z * 1.5) / CAMERA_FOCAL_LENGTH_PX
            
            roi_patch = gray[y:y+bh, x:x+bw]
            std_dev = float(np.std(roi_patch)) if roi_patch.size > 0 else 20.0
            est_d = min(0.22, max(0.015, (area / (roi_w * roi_h)) * 0.38 + (std_dev / 255.0) * 0.09))

            center_x = x + bw * 0.5
            lat_x = ((center_x - (w * 0.5)) * dist_z) / CAMERA_FOCAL_LENGTH_PX

            cohesive_potholes.append({
                "bbox": (x, global_y, x + bw, global_y + bh),
                "width": float(est_w),
                "length": float(est_l),
                "depth": float(est_d),
                "distance_forward": float(dist_z),
                "distance_lateral": float(lat_x)
            })

        return cohesive_potholes

    def process_image(self, image_path: str, image_idx: int, ego_speed_mps: float = 12.0) -> Dict[str, Any]:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot load image from {image_path}")

        img_h, img_w = img.shape[:2]
        annotated_img = img.copy()

        # 1. Dynamic Vision Pipeline
        yolo_res = self.yolo_model.predict(img, conf=0.25, verbose=False)[0]
        raw_dets = []
        for box in yolo_res.boxes:
            cls_id = int(box.cls[0])
            raw_dets.append({
                "class": self.yolo_model.names[cls_id].lower(),
                "confidence": float(box.conf[0]),
                "bbox": tuple(map(int, box.xyxy[0].tolist()))
            })

        refined_dets = self.remap_indian_vehicles(raw_dets, img)

        dynamic_objects = []
        for d in refined_dets:
            dist_z, lat_x = self.estimate_3d_position(d["bbox"], d["class"], img_w)
            in_corr = abs(lat_x) <= 1.85
            ttc = dist_z / ego_speed_mps if in_corr and ego_speed_mps > 0.1 else 99.0

            dynamic_objects.append({
                "id": len(dynamic_objects) + 1,
                "class": d["class"],
                "confidence": d["confidence"],
                "bbox": d["bbox"],
                "distance_forward_m": round(dist_z, 2),
                "distance_lateral_m": round(lat_x, 2),
                "in_corridor": in_corr,
                "ttc_s": round(ttc, 2) if ttc < 90.0 else None
            })

        # 2. Cohesive Road Surface Segmentation & Risk Evaluation
        raw_potholes = self.detect_potholes_cohesive(img)
        pothole_observations = []
        for idx, p in enumerate(raw_potholes, 1):
            obs = self.pothole_classifier.classify(
                width=p["width"],
                length=p["length"],
                depth=p["depth"],
                distance_forward=p["distance_forward"],
                distance_lateral=p["distance_lateral"],
                pothole_id=idx
            )
            pothole_observations.append(obs)

        # 3. P1 Temporal Tracking Step
        tracked_potholes = self.tracker.update(pothole_observations, vehicle_speed_mps=ego_speed_mps, current_timestamp=time.time())

        # 4. Pothole Risk Engine Evaluation
        pothole_assessments = []
        for idx, obs in enumerate(pothole_observations):
            risk_eval = self.risk_engine.assess_risk(obs, vehicle_speed_mps=ego_speed_mps)
            pothole_assessments.append(risk_eval)

        # 5. P1 Multi-Threat Arbitration Engine
        d_stop = self.physics.calculate_stopping_distance(ego_speed_mps)
        primary_threat, all_unified_threats, decision = self.arbitrator.arbitrate(
            dynamic_objects=dynamic_objects,
            pothole_assessments=pothole_assessments,
            ego_speed_mps=ego_speed_mps,
            stopping_distance_m=d_stop
        )

        # 6. Draw Visual HUD & Bounding Boxes
        for d in dynamic_objects:
            x1, y1, x2, y2 = d["bbox"]
            is_threat = d["in_corridor"] and d["distance_forward_m"] <= d_stop * 1.25
            col = (0, 0, 255) if is_threat else (0, 255, 255) if d["in_corridor"] else (0, 255, 0)
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), col, 2)
            lbl = f"{d['class'].upper().replace('_', ' ')} {d['confidence']*100:.0f}% | {d['distance_forward_m']:.1f}m (lat:{d['distance_lateral_m']:+.1f}m)"
            cv2.putText(annotated_img, lbl, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(annotated_img, lbl, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1)

        for p_eval, p_raw in zip(pothole_assessments, raw_potholes):
            px1, py1, px2, py2 = p_raw["bbox"]
            p_col = (0, 0, 255) if p_eval.severity in [PotholeSeverity.CRITICAL, PotholeSeverity.HIGH] else (0, 165, 255) if p_eval.severity == PotholeSeverity.MEDIUM else (0, 255, 0)
            cv2.rectangle(annotated_img, (px1, py1), (px2, py2), p_col, 2)
            plbl = f"POTHOLE: {p_eval.pothole_name} | {p_eval.distance_forward_m:.1f}m (Depth:{p_raw['depth']*100:.0f}cm, TTC:{p_eval.time_to_pothole_s:.1f}s)"
            cv2.putText(annotated_img, plbl, (px1, max(25, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(annotated_img, plbl, (px1, max(25, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, p_col, 1)

        # Draw Telemetry Cockpit HUD
        hud = np.zeros((80, img_w, 3), dtype=np.uint8)
        hud_col = (0, 0, 255) if decision.has_intervention else (0, 255, 0)
        cv2.putText(hud, f"SAFAR ADAS COCKPIT | STATE: {decision.state.value} | BRAKE: {'[ACTIVE OVERRIDE]' if decision.has_intervention else '[PASSIVE]'}", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, hud_col, 2)
        cv2.putText(hud, f"Speed: {ego_speed_mps*3.6:.0f} km/h | d_stop: {d_stop:.1f}m | Primary: {primary_threat.class_name.upper()} at {primary_threat.distance_forward_m:.1f}m (TTC: {primary_threat.ttc_s:.1f}s)", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        final_composite = np.vstack([hud, annotated_img])
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
            "pothole_detections": [
                {
                    "id": p.pothole_id,
                    "type": p.pothole_name,
                    "confidence": round(p.confidence, 3),
                    "distance_forward_m": round(p.distance_forward_m, 2),
                    "distance_lateral_m": round(p.distance_lateral_m, 2),
                    "strike_location": p.strike_location,
                    "ttc_s": round(p.time_to_pothole_s, 2),
                    "stopping_distance_m": round(p.stopping_distance_m, 2),
                    "required_decel_mps2": round(p.required_decel_mps2, 2),
                    "safety_ratio": round(p.safety_ratio, 2),
                    "risk_score": round(p.risk_score, 3),
                    "severity": p.severity.value,
                    "reason": p.reason
                } for p in pothole_assessments
            ],
            "primary_threat": {
                "source": primary_threat.source_type.value,
                "class_name": primary_threat.class_name,
                "distance_forward_m": primary_threat.distance_forward_m,
                "ttc_s": primary_threat.ttc_s,
                "risk_score": round(primary_threat.risk_score, 3),
                "severity": primary_threat.severity,
                "reason": primary_threat.reason
            },
            "safar_decision": {
                "state": decision.state.value,
                "has_intervention": decision.has_intervention,
                "action_reason": decision.reason
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
    print(" SAFAR MULTI-HAZARD EVALUATION WITH P0/P1 REFINEMENTS")
    print("=" * 75)

    for idx, img_p in enumerate(images, 1):
        entry = tester.process_image(img_p, idx, ego_speed_mps=12.0)
        full_logs.append(entry)
        dec = entry["safar_decision"]
        pt = entry["primary_threat"]
        print(f"\nImage {idx}: {os.path.basename(img_p)}")
        print(f"  -> Dynamic Objects : {len(entry['dynamic_detections'])}")
        print(f"  -> Potholes/Craters: {len(entry['pothole_detections'])}")
        print(f"  -> Primary Threat  : {pt['class_name'].upper()} at {pt['distance_forward_m']:.1f}m (Risk: {pt['risk_score']:.2f}, Severity: {pt['severity']})")
        print(f"  -> SAFAR Decision  : State = {dec['state']} | Intervention = {dec['has_intervention']}")
        print(f"  -> Causal Reason   : {dec['action_reason']}")

    log_file_path = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\logs\safar_image_test_log.json"
    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(full_logs, f, indent=2)

    print("\n" + "=" * 75)
    print(f" [SUCCESS] Complete P0/P1 pipeline logs saved to: {log_file_path}")
    print("=" * 75)


if __name__ == "__main__":
    run_test()
