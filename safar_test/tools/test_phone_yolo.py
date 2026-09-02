"""Live local phone camera → YOLO → SAFAR perception/HZ demonstration."""

import argparse
import time
from pathlib import Path

import cv2

from safar.hazard import HazardRiskEngine, image_detection_to_object
from safar.hazard.lead import select_lead
from safar.perception.camera import CameraStreamError, PhoneCamera
from safar.perception.image_tracker import ImageTracker
from safar.perception.ego_path import EgoPathModel
from safar.perception.motion import apparent_motion, traffic_state
from safar.perception.yolo_adapter import YOLOPerceptionAdapter
from safar.perception.yolo_detector import YOLODetector


def _camera_object_id(detection, width: int, height: int) -> str:
    """Use a coarse image grid ID to preserve HZ state across small box motion."""
    x1, y1, x2, y2 = detection.bbox
    cell_x = min(7, max(0, int(((x1 + x2) / 2.0) / width * 8)))
    cell_y = min(4, max(0, int(((y1 + y2) / 2.0) / height * 5)))
    return f"camera:{detection.class_name}:{cell_x}:{cell_y}"


def _draw(frame, detection) -> None:
    """Draw one class/confidence bounding box without displaying fake distance."""
    x1, y1, x2, y2 = detection.bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
    cv2.putText(frame, f"{detection.class_name} {detection.confidence:.2f}", (x1, max(22, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)


def main() -> None:
    """Run the existing YOLO/adapter pipeline on each local phone-camera frame."""
    parser = argparse.ArgumentParser(description="SAFAR live phone YOLO test")
    parser.add_argument("--url", required=True, help="Local HTTP/MJPEG or RTSP URL, e.g. rtsp://PHONE_IP:8554/path")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO model path")
    parser.add_argument("--confidence", type=float, default=0.25, help="YOLO confidence threshold")
    parser.add_argument("--summary-interval", type=float, default=2.0, help="Seconds between console summaries")
    args = parser.parse_args()

    camera = PhoneCamera(args.url)
    adapter = YOLOPerceptionAdapter()
    engine = HazardRiskEngine(); tracker = ImageTracker(); ego_path = EgoPathModel()
    last_summary = 0.0
    try:
        camera.connect()
        detector = YOLODetector(Path(args.model), args.confidence)
        print("Camera and YOLO connected. Press Q in the video window to exit.")
        while True:
            try:
                frame = camera.read()
                raw_detections = detector.detect(frame)
            except (CameraStreamError, RuntimeError) as error:
                print(f"ERROR: {error}")
                break
            detections = adapter.adapt(raw_detections)
            height, width = frame.shape[:2]
            tracks = tracker.update(detections)
            relevance = {track.track_id: ego_path.relevance_for_bbox(track.bbox, width, height) for track in tracks if not track.missed}
            objects = [image_detection_to_object(track.detection, width, track.track_id) for track in tracks if not track.missed and relevance[track.track_id].in_path]
            candidates, (assessment, decision) = engine.evaluate_without_vehicle_state(objects)
            lead = select_lead(candidates)
            for track in tracks:
                if track.missed: continue
                item=track.detection; _draw(frame, item)
                info=f"ID {track.track_id} {relevance[track.track_id].level.value} {traffic_state(track).value} {apparent_motion(track).value}"
                cv2.putText(frame, info, (item.bbox[0], min(height-8,item.bbox[3]+18)), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,180,0), 1)
            hz_present = any(item.is_hazard for item in candidates)
            lines = (
                f"HZ: {'YES' if hz_present else 'NO'}",
                f"Risk: {decision.risk_level}",
                f"Decision: {decision.action}",
                "Distance: UNKNOWN",
                f"Lead: {lead.perception.object_id if lead else 'NONE'}",
            )
            for index, line in enumerate(lines):
                cv2.putText(frame, line, (15, 30 + index * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)
            cv2.imshow("SAFAR Live Camera", frame)
            if time.monotonic() - last_summary >= args.summary_interval:
                print(f"SAFAR | HZ={'YES' if hz_present else 'NO'} | Risk={decision.risk_level} | Decision={decision.action} | {decision.reason}")
                for item in detections:
                    print(f"  {item.category} class={item.class_name} confidence={item.confidence:.2f} bbox={item.bbox} source={item.source}")
                last_summary = time.monotonic()
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                break
    except (CameraStreamError, RuntimeError) as error:
        print(f"ERROR: {error}")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
