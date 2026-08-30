"""
SAFAR Perception Protocol — Wire Format & Message Serialization
"""
import json
import time
from typing import List, Dict, Any

class PerceptionProtocol:
    """
    Serializes and formats detection messages sent from Python to C++ SAFAR Core.
    """
    @staticmethod
    def format_detection_message(
        detections: List[Dict[str, Any]],
        timestamp_us: int = None,
        frame_id: int = 0
    ) -> str:
        if timestamp_us is None:
            timestamp_us = int(time.time() * 1e6)

        payload = {
            "timestamp_us": timestamp_us,
            "frame_id": frame_id,
            "detections": detections
        }
        return json.dumps(payload) + "\n"

    @staticmethod
    def create_detection_dict(
        camera_id: int,
        class_name: str,
        confidence: float,
        bbox_norm: List[float],
        class_id: int = 0
    ) -> Dict[str, Any]:
        """
        bbox_norm: [xmin, ymin, xmax, ymax] normalized to [0.0, 1.0]
        """
        center_x = (bbox_norm[0] + bbox_norm[2]) * 0.5
        bottom_y = bbox_norm[3]

        return {
            "camera_id": camera_id,
            "class_id": class_id,
            "class_name": class_name,
            "confidence": round(float(confidence), 4),
            "bbox_normalized": [round(float(c), 4) for c in bbox_norm],
            "center_x": round(float(center_x), 4),
            "bottom_y": round(float(bottom_y), 4)
        }
