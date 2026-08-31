"""
SAFAR Real-Time Console Telemetry Streamer
With Full P0 & P1 Enhancements:
- Exact Causal Reason Chains (threat -> distance -> TTC -> d_stop -> required decel -> intervention)
- Left/Right Wheel Track Geometry Overlap
- Continuous Stopping Distance Risk Scaling
- Pothole Kinematic TTC
- Cohesive Candidate Filtering
- Unified Multi-Threat Arbitration
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
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from safar.pothole.classifier import PotholeClassifier, PotholeObservation
from safar.pothole.physics import PotholePhysicsEngine
from safar.pothole.path import PotholePathGeometry, PathIntersectionStatus
from safar.pothole.risk import PotholeRiskEngine, PotholeSeverity
from safar.pothole.decision import PotholeDecisionEngine
from safar.pothole.tracker import PotholeTemporalTracker
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


def print_divider(char="=", length=85):
    print(char * length)


def stream_logs():
    image_paths = [
        (1, "Wet Intersection with Surface Depressions & Pedestrians", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148607178.jpg"),
        (2, "Narrow Lane with Multi-Class Traffic & Roadside Mud Trench", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148615983.jpg"),
        (3, "Corridor with Yellow Truck, Tractor, Silver Car & Water Ruts", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616006.jpg"),
        (4, "Wet Asphalt Road with Oncoming Scooter & Road Craters", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616010.jpg"),
        (5, "Flooded Monsoon Road with Auto-Rickshaw & Deep Craters", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616014.jpg")
    ]

    print("\n" + "=" * 85)
    print(" 🚀 SAFAR REAL-TIME TELEMETRY STREAM WITH P0/P1 REASONING ENGINE")
    print("=" * 85)
    print(" [INIT] Initializing Computer Vision Models...")
    yolo_model = YOLO("yolo11n.pt")
    print(" [INIT] Initializing Gradient Boosting Pothole Classifier...")
    pothole_classifier = PotholeClassifier()
    print(" [INIT] Initializing Kinematic Physics, Path Geometry & Arbitration Engines...")
    physics = PotholePhysicsEngine()
    path_geometry = PotholePathGeometry()
    risk_engine = PotholeRiskEngine(physics, path_geometry)
    decision_engine = PotholeDecisionEngine()
    tracker = PotholeTemporalTracker()
    arbitrator = MultiThreatArbitrationEngine()
    print(" [INIT] Pipeline Active. Streaming live diagnostic telemetry...\n")

    ego_speed_mps = 12.0  # 43.2 km/h
    d_stop = physics.calculate_stopping_distance(ego_speed_mps)

    for frame_idx, scene_title, img_path in image_paths:
        t0 = time.time()
        print_divider("-", 85)
        print(f" ▶ FRAME #{frame_idx} | SCENE: {scene_title}")
        print(f"   Timestamp: {time.strftime('%H:%M:%S')}.{int((t0 % 1) * 1000):03d} | File: {os.path.basename(img_path)}")
        print(f"   Ego Kinematics: Speed = {ego_speed_mps*3.6:.1f} km/h ({ego_speed_mps:.1f} m/s) | Stopping Distance d_stop = {d_stop:.2f} m")
        print_divider("-", 85)

        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        print(f"   [1. CAMERA ACQUISITION] Resolution: {w}x{h} px | Mount: H = 1.35m, Focal = 720px")

        # 2. YOLO Object Detection
        t_yolo_start = time.time()
        yolo_res = yolo_model.predict(img, conf=0.25, verbose=False)[0]
        t_yolo_dur = (time.time() - t_yolo_start) * 1000

        raw_dets = []
        for box in yolo_res.boxes:
            cls_id = int(box.cls[0])
            raw_dets.append({
                "class": yolo_model.names[cls_id].lower(),
                "confidence": float(box.conf[0]),
                "bbox": tuple(map(int, box.xyxy[0].tolist()))
            })

        # Remap / Indian Vehicle Refinements
        people = [d for d in raw_dets if d["class"] == "person"]
        bikes = [d for d in raw_dets if d["class"] in ["motorcycle", "bicycle"]]
        others = [d for d in raw_dets if d["class"] not in ["person", "motorcycle", "bicycle"]]

        refined_dets = []
        used_p = set()
        for bike in bikes:
            bx1, by1, bx2, by2 = bike["bbox"]
            matched_p = None
            for p_idx, person in enumerate(people):
                if p_idx in used_p:
                    continue
                px1, py1, px2, py2 = person["bbox"]
                if max(0, min(rx2 := px2, bx2) - max(rx1 := px1, bx1)) / max(1, min(rx2 - rx1, bx2 - bx1)) > 0.40:
                    matched_p = person
                    used_p.add(p_idx)
                    break
            if matched_p:
                px1, py1, px2, py2 = matched_p["bbox"]
                refined_dets.append({
                    "class": "motorcycle_rider",
                    "confidence": max(matched_p["confidence"], bike["confidence"]),
                    "bbox": (min(px1, bx1), min(py1, by1), max(px2, bx2), max(py2, by2))
                })
            else:
                refined_dets.append(bike)

        for i, p in enumerate(people):
            if i not in used_p:
                refined_dets.append(p)

        for d in others:
            x1, y1, x2, y2 = d["bbox"]
            bw, bh = x2 - x1, y2 - y1
            if d["class"] in ["truck", "car"] and d["confidence"] < 0.68 and 0.85 <= (bh / max(1, bw)) <= 1.55:
                patch = img[y1:y2, x1:x2]
                if patch.size > 0:
                    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
                    if np.sum(cv2.inRange(hsv, np.array([15, 60, 60]), np.array([85, 255, 255])) > 0) / float(bw * bh) > 0.08 or (d["class"] == "truck" and d["confidence"] < 0.50):
                        refined_dets.append({"class": "auto_rickshaw", "confidence": d["confidence"], "bbox": d["bbox"]})
                        continue
            refined_dets.append(d)

        print(f"   [2. DYNAMIC PERCEPTION] Detected {len(refined_dets)} entities (Inference Time: {t_yolo_dur:.1f}ms):")
        dynamic_objects = []
        for idx, d in enumerate(refined_dets, 1):
            x1, y1, x2, y2 = d["bbox"]
            box_h = max(1, y2 - y1)
            real_h = REAL_HEIGHTS_M.get(d["class"], 1.50)
            dist_z = max(1.5, min(80.0, (CAMERA_FOCAL_LENGTH_PX * real_h) / box_h))
            center_x = (x1 + x2) * 0.5
            lat_x = ((center_x - w * 0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX
            in_corridor = abs(lat_x) <= 1.85
            ttc = dist_z / ego_speed_mps if in_corridor else 99.0

            status_tag = "🔴 [IN CORRIDOR - THREAT]" if (in_corridor and dist_z <= d_stop * 1.25) else "🟡 [IN PATH - MONITOR]" if in_corridor else "🟢 [PATH CLEAR]"
            print(f"      #{idx:<2} {d['class'].upper():<16} | Conf: {d['confidence']*100:4.1f}% | Dist: {dist_z:5.1f}m | Lat: {lat_x:+5.2f}m | TTC: {ttc:4.1f}s | {status_tag}")

            dynamic_objects.append({
                "id": idx,
                "class": d["class"],
                "confidence": d["confidence"],
                "distance_forward_m": dist_z,
                "distance_lateral_m": lat_x,
                "in_corridor": in_corridor,
                "ttc_s": ttc
            })

        # 3. P1 Cohesive Road Surface Candidate Filtering
        road_roi = img[int(h * 0.45):h, :]
        gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        _, d_th = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        _, b_th = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        raw_mask = cv2.bitwise_or(d_th, b_th)
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 15))
        merged_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, close_kernel)
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cleaned_mask = cv2.morphologyEx(merged_mask, cv2.MORPH_OPEN, open_kernel)
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        pothole_obs_list = []
        pothole_assessments = []
        print(f"   [3. ROAD SURFACE ANALYSIS] Segmented {len(contours)} cohesive candidate surface regions:")

        for p_idx, c in enumerate(contours, 1):
            area = cv2.contourArea(c)
            if area < 1500 or area > (w * (h * 0.55) * 0.40):
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            global_y = int(h * 0.45) + y
            bottom_y = global_y + bh
            norm_y = max(0.01, min(1.0, (bottom_y - h * 0.45) / (h * 0.55)))
            dist_z = 2.0 + (1.0 - norm_y) * 28.0
            lat_x = ((x + bw*0.5 - w*0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX
            est_w = (bw * dist_z) / CAMERA_FOCAL_LENGTH_PX
            est_l = (bh * dist_z * 1.5) / CAMERA_FOCAL_LENGTH_PX
            
            roi_patch = gray[y:y+bh, x:x+bw]
            std_dev = float(np.std(roi_patch)) if roi_patch.size > 0 else 20.0
            est_d = min(0.22, max(0.015, (area / (w * (h * 0.55))) * 0.38 + (std_dev / 255.0) * 0.09))

            obs = pothole_classifier.classify(est_w, est_l, est_d, dist_z, lat_x, p_idx)
            pothole_obs_list.append(obs)

            risk = risk_engine.assess_risk(obs, vehicle_speed_mps=ego_speed_mps)
            pothole_assessments.append(risk)

            p_tag = "🔴 [CRITICAL CRATER]" if risk.severity == PotholeSeverity.CRITICAL else "🟠 [HIGH RISK]" if risk.severity == PotholeSeverity.HIGH else "🟢 [DRIVABLE/SAFE]"
            print(f"      P#{p_idx:<2} {obs.pothole_name:<14} | Dim: {est_w:4.1f}x{est_l:4.1f}m (Depth:{est_d*100:2.0f}cm) | Dist: {dist_z:5.1f}m | Lat: {lat_x:+5.2f}m | TTC: {risk.time_to_pothole_s:4.1f}s | Strike: {risk.strike_location:<11} | {p_tag}")

        # 4. P1 Temporal Tracking Step
        active_tracks = tracker.update(pothole_obs_list, vehicle_speed_mps=ego_speed_mps, current_timestamp=time.time())

        # 5. P1 Multi-Threat Arbitration Engine
        primary_threat, all_unified, decision = arbitrator.arbitrate(
            dynamic_objects=dynamic_objects,
            pothole_assessments=pothole_assessments,
            ego_speed_mps=ego_speed_mps,
            stopping_distance_m=d_stop
        )

        total_latency_ms = (time.time() - t0) * 1000
        print(f"\n   [4. SAFAR MULTI-THREAT ARBITRATION & DECISION]")
        print(f"      ► SYSTEM STATE   : {decision.state.value}")
        print(f"      ► CONTROL MODE   : {'⚠️ ACTIVE OVERRIDE (Brake = 1.0, Throttle = 0.0)' if decision.has_intervention else '✅ PASSIVE (Driver in Full Control)'}")
        print(f"      ► PRIMARY THREAT : [{primary_threat.source_type.value}] {primary_threat.class_name.upper()} at {primary_threat.distance_forward_m:.1f}m (TTC: {primary_threat.ttc_s:.2f}s, Risk: {primary_threat.risk_score:.2f})")
        print(f"      ► CAUSAL REASON  : {decision.reason}")
        print(f"      ► PIPELINE TIME  : {total_latency_ms:.1f} ms ({1000.0/total_latency_ms:.1f} FPS equivalent)\n")
        time.sleep(0.4)

    print("=" * 85)
    print(" ✅ FULL MULTI-HAZARD REAL-TIME TELEMETRY STREAM COMPLETE.")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    stream_logs()
