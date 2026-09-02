"""
SAFAR Real Perception Detector (Ultralytics YOLO11)
"""
import os
import time
from typing import List, Dict, Any
import numpy as np

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

from .protocol import PerceptionProtocol

class YoloPerceptionDetector:
    DEFAULT_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "person"}

    def __init__(self, model_path: str = "yolo11n.pt", conf_threshold: float = 0.28):
        self.conf_threshold = conf_threshold
        if not HAS_YOLO:
            print("[WARN] Ultralytics YOLO not installed. Falling back to Mock Perception.")
            self.model = None
            return

        if not os.path.exists(model_path):
            root_model = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
            if os.path.exists(root_model):
                model_path = root_model

        self.model = YOLO(model_path)

    def detect(self, image_np: np.ndarray, camera_id: int = 0) -> List[Dict[str, Any]]:
        if self.model is None or image_np is None:
            return []

        h, w = image_np.shape[:2]
        results = self.model.predict(source=image_np, conf=self.conf_threshold, verbose=False)

        detections: List[Dict[str, Any]] = []
        if results and len(results) > 0:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                class_name = self.model.names.get(cls_id, "unknown")

                if class_name not in self.DEFAULT_CLASSES:
                    continue

                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                # Normalize to [0.0, 1.0]
                norm_xmin = max(0.0, min(1.0, xyxy[0] / w))
                norm_ymin = max(0.0, min(1.0, xyxy[1] / h))
                norm_xmax = max(0.0, min(1.0, xyxy[2] / w))
                norm_ymax = max(0.0, min(1.0, xyxy[3] / h))

                det = PerceptionProtocol.create_detection_dict(
                    camera_id=camera_id,
                    class_name=class_name,
                    confidence=conf,
                    bbox_norm=[norm_xmin, norm_ymin, norm_xmax, norm_ymax],
                    class_id=cls_id
                )
                detections.append(det)

        return detections
