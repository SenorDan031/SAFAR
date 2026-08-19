"""Optional Phase 1A Ultralytics YOLO backend for real-image perception."""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class YOLODetection:
    """Backend output deliberately reduced to the fields SAFAR needs at Phase 1B."""

    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]


class YOLODetector:
    """Lazy Ultralytics wrapper so CARLA-only SAFAR use needs no YOLO import."""

    def __init__(self, model_path: str = "yolo11n.pt", confidence_threshold: float = 0.25) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError("Install the optional Phase 1B dependencies from requirements-yolo.txt.") from error
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame) -> List[YOLODetection]:
        """Return raw visual detections; no depth or physical distance is inferred."""
        results = self.model.predict(source=frame, conf=self.confidence_threshold, verbose=False)
        if not results or results[0].boxes is None:
            return []
        output = []
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            output.append(YOLODetection(self.model.names[class_id], float(box.conf[0]), (int(x1), int(y1), int(x2), int(y2))))
        return output
