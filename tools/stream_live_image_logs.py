"""
SAFAR Real-Time Console Telemetry Streamer
Streams live frame-by-frame diagnostic and safety decision logs for the uploaded images.
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
import cv2
import numpy as np
from ultralytics import YOLO

from safar.pothole.classifier import PotholeClassifier
from safar.pothole.physics import PotholePhysicsEngine
from safar.pothole.path import PotholePathGeometry, PathIntersectionStatus
from safar.pothole.risk import PotholeRiskEngine, PotholeSeverity
from safar.pothole.decision import PotholeDecisionEngine

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


def print_divider(char="=", length=80):
    print(char * length)


def stream_logs():
    image_paths = [
        (1, "Wet Intersection with Surface Depressions & Pedestrians", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148607178.jpg"),
        (2, "Narrow Lane with Multi-Class Traffic & Roadside Mud Trench", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148615983.jpg"),
        (3, "Corridor with Yellow Truck, Tractor, Silver Car & Water Ruts", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616006.jpg"),
        (4, "Wet Asphalt Road with Oncoming Scooter & Road Craters", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616010.jpg"),
        (5, "Flooded Monsoon Road with Auto-Rickshaw & Deep Craters", r"C:/Users/shrey/.gemini/antigravity/brain/4bb433f6-55ac-41c9-951b-c1ec39074f17/.user_uploaded/media_1788148616014.jpg")
    ]

    print("\n" + "=" * 80)
    print(" 🚀 SAFAR REAL-TIME TELEMETRY & MULTI-HAZARD SAFETY REASONING ENGINE")
    print("=" * 80)
    print(" [INIT] Initializing Computer Vision Models...")
    yolo_model = YOLO("yolo11n.pt")
    print(" [INIT] Initializing Gradient Boosting Pothole Classifier...")
    pothole_classifier = PotholeClassifier()
    print(" [INIT] Initializing Kinematic Physics & Path Geometry Engines...")
    physics = PotholePhysicsEngine()
    path_geometry = PotholePathGeometry()
    risk_engine = PotholeRiskEngine(physics, path_geometry)
    decision_engine = PotholeDecisionEngine()
    print(" [INIT] System Ready. Streaming live telemetry logs for 5 frames...\n")

    ego_speed_mps = 12.0  # 43.2 km/h
    d_stop = physics.calculate_stopping_distance(ego_speed_mps)

    for frame_idx, scene_title, img_path in image_paths:
        t0 = time.time()
        print_divider("-", 80)
        print(f" ▶ FRAME #{frame_idx} | SCENE: {scene_title}")
        print(f"   Timestamp: {time.strftime('%H:%M:%S')}.{int((t0 % 1) * 1000):03d} | File: {os.path.basename(img_path)}")
        print(f"   Ego Kinematics: Speed = {ego_speed_mps*3.6:.1f} km/h ({ego_speed_mps:.1f} m/s) | Stopping Distance d_stop = {d_stop:.2f} m")
        print_divider("-", 80)

        # 1. Image Ingestion
        img = cv2.imread(img_path)
        if img is None:
            print(f"   [ERROR] Failed to load image: {img_path}")
            continue
        h, w = img.shape[:2]
        print(f"   [1. CAMERA ACQUISITION] Resolution: {w}x{h} px | Camera Mount: H = 1.35m, Focal = 720px")

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
        dynamic_threats = []
        for idx, d in enumerate(refined_dets, 1):
            x1, y1, x2, y2 = d["bbox"]
            box_h = max(1, y2 - y1)
            real_h = REAL_HEIGHTS_M.get(d["class"], 1.50)
            dist_z = max(1.5, min(80.0, (CAMERA_FOCAL_LENGTH_PX * real_h) / box_h))
            center_x = (x1 + x2) * 0.5
            lat_x = ((center_x - w * 0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX
            in_corridor = abs(lat_x) <= 1.85
            ttc = dist_z / ego_speed_mps if in_corridor else 99.0

            status_tag = "🔴 [IN CORRIDOR - THREAT]" if (in_corridor and dist_z < d_stop * 1.25) else "🟡 [IN PATH - MONITOR]" if in_corridor else "🟢 [PATH CLEAR]"
            print(f"      #{idx:<2} {d['class'].upper():<16} | Conf: {d['confidence']*100:4.1f}% | Dist: {dist_z:5.1f}m | Lat: {lat_x:+5.2f}m | TTC: {ttc:4.1f}s | {status_tag}")

            if in_corridor:
                dynamic_threats.append({"class": d["class"], "dist_z": dist_z, "lat_x": lat_x, "ttc": ttc})

        # 3. Pothole / Surface Optical Segmentation & Risk
        road_roi = img[int(h * 0.45):h, :]
        gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, d_th = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        _, b_th = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_or(d_th, b_th)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        pothole_threats = []
        print(f"   [3. ROAD SURFACE ANALYSIS] Segmented {len(contours)} candidate surface regions:")
        for p_idx, c in enumerate(contours, 1):
            area = cv2.contourArea(c)
            if area < 800 or area > (w * (h * 0.55) * 0.45):
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            global_y = int(h * 0.45) + y
            bottom_y = global_y + bh
            norm_y = max(0.01, min(1.0, (bottom_y - h * 0.45) / (h * 0.55)))
            dist_z = 2.0 + (1.0 - norm_y) * 28.0
            lat_x = ((x + bw*0.5 - w*0.5) * dist_z) / CAMERA_FOCAL_LENGTH_PX
            est_w = (bw * dist_z) / CAMERA_FOCAL_LENGTH_PX
            est_l = (bh * dist_z * 1.5) / CAMERA_FOCAL_LENGTH_PX
            est_d = min(0.20, max(0.015, (area / (w * (h * 0.55))) * 0.35))

            obs = pothole_classifier.classify(est_w, est_l, est_d, dist_z, lat_x, p_idx)
            risk = risk_engine.assess_risk(obs, vehicle_speed_mps=ego_speed_mps)

            p_tag = "🔴 [CRITICAL CRATER]" if risk.severity == PotholeSeverity.CRITICAL else "🟠 [HIGH RISK]" if risk.severity == PotholeSeverity.HIGH else "🟢 [DRIVABLE/SAFE]"
            print(f"      P#{p_idx:<2} {obs.pothole_name:<14} | Dim: {est_w:.1f}x{est_l:.1f}m (Depth:{est_d*100:.0f}cm) | Dist: {dist_z:5.1f}m | Lat: {lat_x:+5.2f}m | Risk: {risk.risk_score:4.2f} ({risk.severity.value}) | {p_tag}")

            if risk.path_intersection == PathIntersectionStatus.INTERSECTION and risk.severity in [PotholeSeverity.CRITICAL, PotholeSeverity.HIGH]:
                pothole_threats.append({"type": obs.pothole_name, "dist_z": dist_z, "depth_cm": est_d*100, "severity": risk.severity.value, "risk_score": risk.risk_score})

        # 4. Multi-Hazard Arbitration & Decision
        crit_dyn = [v for v in dynamic_threats if v["dist_z"] <= d_stop * 1.25]
        crit_ph = [p for p in pothole_threats if p["dist_z"] <= d_stop * 1.25]

        if crit_dyn:
            target_veh = min(crit_dyn, key=lambda v: v["dist_z"])
            state = "EMERGENCY_BRAKE" if target_veh["dist_z"] <= d_stop else "BRAKE"
            override = True
            primary = f"{target_veh['class'].upper()} in corridor at {target_veh['dist_z']:.1f}m"
            reason = f"Imminent collision threat in driving corridor (Distance: {target_veh['dist_z']:.1f}m <= d_stop: {d_stop:.1f}m, TTC: {target_veh['ttc']:.1f}s)"
        elif crit_ph:
            target_ph = min(crit_ph, key=lambda p: p["dist_z"])
            state = "EMERGENCY_BRAKE" if target_ph["severity"] == "CRITICAL" else "BRAKE"
            override = True
            primary = f"{target_ph['type']} in path at {target_ph['dist_z']:.1f}m ({target_ph['depth_cm']:.0f}cm deep)"
            reason = f"Severe road surface hazard in driving path (Distance: {target_ph['dist_z']:.1f}m <= d_stop: {d_stop:.1f}m, Risk: {target_ph['risk_score']:.2f})"
        elif dynamic_threats or pothole_threats:
            state = "SLOW"
            override = False
            primary = "Approaching traffic / road anomaly"
            reason = "Moderating approach speed to safe margin for surface/traffic conditions."
        else:
            state = "MAINTAIN"
            override = False
            primary = "Path Clear"
            reason = "Corridor clear. Player retains 100% authoritative manual control."

        total_latency_ms = (time.time() - t0) * 1000
        print(f"\n   [4. SAFAR DECISION ARBITRATION]")
        print(f"      ► SYSTEM STATE   : {state}")
        print(f"      ► CONTROL MODE   : {'⚠️ ACTIVE OVERRIDE (Brake = 1.0, Throttle = 0.0)' if override else '✅ PASSIVE (Driver in Full Control)'}")
        print(f"      ► PRIMARY THREAT : {primary}")
        print(f"      ► ACTION REASON  : {reason}")
        print(f"      ► PIPELINE TIME  : {total_latency_ms:.1f} ms ({1000.0/total_latency_ms:.1f} FPS equivalent)\n")
        time.sleep(0.4)

    print("=" * 80)
    print(" ✅ ALL 5 FRAMES PROCESSED IN REAL TIME. FULL TELEMETRY STREAM COMPLETE.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    stream_logs()
