"""
SAFAR Mock Perception Detector
Generates deterministic synthetic obstacle detections for testing and CI
without requiring GPU or YOLO dependencies.
"""
import time
import math
from typing import List, Dict, Any
from .protocol import PerceptionProtocol

class MockDetector:
    """
    Simulates various test scenarios:
    1. approaching_vehicle: A lead vehicle closing in from 45m to 5m.
    2. stationary_barrier: A barrier at fixed 12m.
    3. pedestrian_cross: Pedestrian walking across ego lane.
    4. clear_road: Empty detections.
    """
    def __init__(self, scenario: str = "approaching_vehicle"):
        self.scenario = scenario
        self.frame_id = 0
        self.start_time = time.time()

    def generate_detections(self, timestamp_us: int = None) -> List[Dict[str, Any]]:
        self.frame_id += 1
        elapsed = time.time() - self.start_time

        if self.scenario == "clear_road":
            return []

        elif self.scenario == "approaching_vehicle":
            # Progressively moves from far (small box at horizon) to near (large box at bottom)
            t = (self.frame_id % 60) / 60.0  # 2 second cycle @ 30fps
            # Distance closes from 45m (t=0) to 6m (t=1.0)
            box_w = 0.08 + t * 0.35
            box_h = box_w * 0.75
            center_x = 0.50 + 0.02 * math.sin(self.frame_id * 0.1)
            bottom_y = 0.55 + t * 0.40

            x1 = max(0.0, center_x - box_w / 2.0)
            y1 = max(0.0, bottom_y - box_h)
            x2 = min(1.0, center_x + box_w / 2.0)
            y2 = min(1.0, bottom_y)

            det = PerceptionProtocol.create_detection_dict(
                camera_id=0,
                class_name="car",
                confidence=0.94,
                bbox_norm=[x1, y1, x2, y2]
            )
            return [det]

        elif self.scenario == "stationary_barrier":
            # Stationary obstacle at 12m
            det = PerceptionProtocol.create_detection_dict(
                camera_id=0,
                class_name="truck",
                confidence=0.96,
                bbox_norm=[0.38, 0.58, 0.62, 0.88]
            )
            return [det]

        elif self.scenario == "pedestrian_cross":
            # Pedestrian moving laterally from left (x=0.2) to right (x=0.8)
            x_pos = 0.20 + (self.frame_id % 45) / 45.0 * 0.60
            det = PerceptionProtocol.create_detection_dict(
                camera_id=0,
                class_name="person",
                confidence=0.91,
                bbox_norm=[x_pos - 0.04, 0.52, x_pos + 0.04, 0.82]
            )
            return [det]

        return []
