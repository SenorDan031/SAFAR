"""Phase 1B boundary from YOLO output to SAFAR's image perception model."""

from typing import Iterable, List

from .types import SAFARDetection


class YOLOPerceptionAdapter:
    """Map detector objects with class/confidence/bbox into SAFAR detections."""

    _CATEGORIES = {
        "car": "vehicle", "bus": "vehicle", "truck": "vehicle",
        "motorcycle": "two_wheeler", "bicycle": "two_wheeler", "person": "pedestrian",
    }

    def adapt(self, detections: Iterable[object]) -> List[SAFARDetection]:
        """Standardize raw YOLO detections without adding distance or velocity."""
        return [
            SAFARDetection(
                class_name=detection.class_name,
                confidence=detection.confidence,
                bbox=detection.bbox,
                category=self._CATEGORIES.get(detection.class_name.lower(), "other"),
            )
            for detection in detections
        ]
