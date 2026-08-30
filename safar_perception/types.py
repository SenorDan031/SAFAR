"""
SAFAR Perception Layer — Data Types and Canonical Contracts
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class BoundingBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def center_x(self) -> float:
        return (self.xmin + self.xmax) * 0.5

    @property
    def bottom_y(self) -> float:
        return self.ymax

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class DetectionObject:
    track_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "confidence": round(float(self.confidence), 4),
            "bbox_normalized": [
                round(float(self.bbox.xmin), 4),
                round(float(self.bbox.ymin), 4),
                round(float(self.bbox.xmax), 4),
                round(float(self.bbox.ymax), 4),
            ],
            "center_x": round(float(self.bbox.center_x), 4),
            "bottom_y": round(float(self.bbox.bottom_y), 4),
        }


@dataclass
class SensorFrame:
    timestamp_us: int
    frame_id: int
    ego_speed_mps: float
    ego_heading_deg: float
    image: any  # numpy.ndarray (RGB / BGR)


@dataclass
class DetectionPayload:
    timestamp_us: int
    frame_id: int
    ego_speed_mps: float
    detections: List[DetectionObject] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp_us": self.timestamp_us,
            "frame_id": self.frame_id,
            "ego_speed_mps": round(float(self.ego_speed_mps), 2),
            "detections": [d.to_dict() for d in self.detections],
        }
