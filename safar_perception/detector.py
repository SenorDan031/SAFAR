"""
SAFAR Perception Layer — YOLO Object Detector
"""
import time
import os
from typing import List, Optional
import numpy as np
from ultralytics import YOLO

from .types import BoundingBox, DetectionObject, DetectionPayload, SensorFrame


class YoloDetector:
    """
    Wraps YOLO model for real-time inference with normalized bounding boxes
    and class filtering for road vehicles and vulnerable road users.
    """
    DEFAULT_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "person"}

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        conf_threshold: float = 0.35,
        target_classes: Optional[set] = None,
        device: str = "cpu"
    ):
        if not os.path.exists(model_path):
            # Fallback to base filename if in root
            root_model = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
            if os.path.exists(root_model):
                model_path = root_model

        self.conf_threshold = conf_threshold
        self.target_classes = target_classes or self.DEFAULT_CLASSES
        self.model = YOLO(model_path)
        self.device = device
        self._next_track_id = 1

    def detect(self, sensor_frame: SensorFrame) -> DetectionPayload:
        """
        Runs YOLO inference on a SensorFrame and returns a normalized DetectionPayload.
        """
        img = sensor_frame.image
        h, w = img.shape[:2]

        t0 = time.perf_counter()
        results = self.model.predict(
            source=img,
            conf=self.conf_threshold,
            verbose=False,
            device=self.device
        )
        inference_time_ms = (time.perf_counter() - t0) * 1000.0

        detections: List[DetectionObject] = []

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                class_name = self.model.names.get(cls_id, "unknown")

                if class_name not in self.target_classes:
                    continue

                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                # Normalize to [0.0, 1.0]
                norm_xmin = max(0.0, min(1.0, xyxy[0] / w))
                norm_ymin = max(0.0, min(1.0, xyxy[1] / h))
                norm_xmax = max(0.0, min(1.0, xyxy[2] / w))
                norm_ymax = max(0.0, min(1.0, xyxy[3] / h))

                bbox = BoundingBox(
                    xmin=norm_xmin,
                    ymin=norm_ymin,
                    xmax=norm_xmax,
                    ymax=norm_ymax
                )

                det_obj = DetectionObject(
                    track_id=self._next_track_id,
                    class_name=class_name,
                    confidence=conf,
                    bbox=bbox
                )
                self._next_track_id += 1
                detections.append(det_obj)

        return DetectionPayload(
            timestamp_us=sensor_frame.timestamp_us,
            frame_id=sensor_frame.frame_id,
            ego_speed_mps=sensor_frame.ego_speed_mps,
            detections=detections
        )
