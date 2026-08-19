"""Run Phase 1A/1B image perception, independent of CARLA."""

from pathlib import Path

from safar.perception.yolo_adapter import YOLOPerceptionAdapter
from safar.perception.yolo_detector import YOLODetector


def main() -> None:
    """Print standardized visual detections for the root ``test_image.jpg``."""
    root = Path(__file__).resolve().parents[1]
    image = root / "test_image.jpg"
    if not image.exists():
        raise FileNotFoundError(f"Add a traffic image at: {image}")
    raw = YOLODetector(root / "yolo11n.pt").detect(str(image))
    detections = YOLOPerceptionAdapter().adapt(raw)
    print(f"YOLO detected {len(raw)} objects.")
    print(f"SAFAR received {len(detections)} standardized detections.")
    for detection in detections:
        print(f"{detection.category:12} class={detection.class_name:12} confidence={detection.confidence:.2f} bbox={detection.bbox}")


if __name__ == "__main__":
    main()
