"""Offline driver-POV video analysis using the existing SAFAR image pipeline.

This tool logs only what a plain video can support.  It deliberately records
speed, distance, relative speed, TTC, and safe target speed as ``UNKNOWN``.
"""

import argparse
import csv
from pathlib import Path

import cv2

from safar.hazard import HazardRiskEngine, image_detection_to_object
from safar.hazard.lead import select_lead
from safar.perception.ego_path import EgoPathModel
from safar.perception.image_tracker import ImageTracker
from safar.perception.motion import apparent_motion, traffic_state
from safar.perception.yolo_adapter import YOLOPerceptionAdapter
from safar.perception.yolo_detector import YOLODetector


def _describe_tracks(tracks, relevance) -> str:
    """Log every active track, including irrelevant traffic, for explainability."""
    values = []
    for track in tracks:
        if track.missed:
            continue
        detection = track.detection
        values.append(
            f"#{track.track_id} {detection.class_name} conf={detection.confidence:.2f} "
            f"bbox={detection.bbox} path={relevance[track.track_id].level.value} "
            f"traffic={traffic_state(track).value} motion={apparent_motion(track).value}"
        )
    return " | ".join(values) or "none"


def main() -> None:
    """Sample a video and write an explainable SAFAR perception log to CSV."""
    parser = argparse.ArgumentParser(description="Offline SAFAR driver-POV video analysis")
    parser.add_argument("--video", required=True, help="Path to a driver-POV video")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO model path")
    parser.add_argument("--confidence", type=float, default=0.25, help="YOLO confidence threshold")
    parser.add_argument("--sample-fps", type=float, default=5.0, help="Frames per second to analyse")
    parser.add_argument("--output", default="logs/video_safar_log.csv", help="CSV output path")
    args = parser.parse_args()

    if args.sample_fps <= 0:
        raise ValueError("--sample-fps must be greater than zero")
    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    sample_interval = max(1, int(round(source_fps / args.sample_fps)))
    detector = YOLODetector(args.model, args.confidence)
    adapter = YOLOPerceptionAdapter()
    engine = HazardRiskEngine()
    tracker = ImageTracker()
    ego_path = EgoPathModel()
    frame_index = 0
    logged_frames = 0
    try:
        with output_path.open("w", newline="", encoding="utf-8") as stream:
            fields = [
                "timestamp_s", "frame_index", "active_tracks", "lead_track_id", "lead_class",
                "lead_path_relevance", "lead_traffic_state", "lead_apparent_motion", "hz_present",
                "risk_level", "decision", "reason", "distance_m", "ego_speed_kmh",
                "closing_speed_kmh", "ttc_seconds",
            ]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % sample_interval:
                    frame_index += 1
                    continue
                raw = detector.detect(frame)
                detections = adapter.adapt(raw)
                height, width = frame.shape[:2]
                tracks = tracker.update(detections)
                relevance = {
                    track.track_id: ego_path.relevance_for_bbox(track.bbox, width, height)
                    for track in tracks if not track.missed
                }
                objects = [
                    image_detection_to_object(track.detection, width, track.track_id)
                    for track in tracks if not track.missed and relevance[track.track_id].in_path
                ]
                candidates, (_, decision) = engine.evaluate_without_vehicle_state(objects)
                lead = select_lead(candidates)
                lead_track = next((track for track in tracks if lead and track.track_id == lead.perception.object_id), None)
                writer.writerow({
                    "timestamp_s": f"{frame_index / source_fps:.2f}",
                    "frame_index": frame_index,
                    "active_tracks": _describe_tracks(tracks, relevance),
                    "lead_track_id": lead_track.track_id if lead_track else "NONE",
                    "lead_class": lead_track.detection.class_name if lead_track else "NONE",
                    "lead_path_relevance": relevance[lead_track.track_id].level.value if lead_track else "NONE",
                    "lead_traffic_state": traffic_state(lead_track).value if lead_track else "UNKNOWN",
                    "lead_apparent_motion": apparent_motion(lead_track).value if lead_track else "UNKNOWN",
                    "hz_present": "YES" if lead else "NO",
                    "risk_level": decision.risk_level,
                    "decision": decision.action,
                    "reason": decision.reason,
                    "distance_m": "UNKNOWN",
                    "ego_speed_kmh": "UNKNOWN",
                    "closing_speed_kmh": "UNKNOWN",
                    "ttc_seconds": "UNKNOWN",
                })
                logged_frames += 1
                print(
                    f"{frame_index / source_fps:6.2f}s | LEAD=#{lead_track.track_id if lead_track else 'NONE'} "
                    f"{lead_track.detection.class_name if lead_track else 'NONE'} | "
                    f"PATH={relevance[lead_track.track_id].level.value if lead_track else 'NONE'} | "
                    f"TRAFFIC={traffic_state(lead_track).value if lead_track else 'UNKNOWN'} | "
                    f"MOTION={apparent_motion(lead_track).value if lead_track else 'UNKNOWN'} | "
                    f"HZ={'YES' if lead else 'NO'} | DIST=UNKNOWN | CLOSING=UNKNOWN | TTC=UNKNOWN | "
                    f"RISK={decision.risk_level} | DECISION={decision.action}"
                )
                frame_index += 1
    finally:
        capture.release()
    print(f"\nAnalysis complete: {logged_frames} sampled frames written to {output_path}")


if __name__ == "__main__":
    main()
