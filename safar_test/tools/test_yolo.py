"""Run Phase 1A YOLO directly on the project test image."""

from pathlib import Path

from safar.perception.yolo_detector import YOLODetector


def main() -> None:
    """Print the raw YOLO detections for ``test_image.jpg``."""
    image_path = Path(__file__).resolve().parents[1] / "test_image.jpg"
    for detection in YOLODetector().detect(str(image_path)):
        print(f"{detection.class_name:15} confidence={detection.confidence:.2f} bbox={detection.bbox}")


if __name__ == "__main__":
    main()
