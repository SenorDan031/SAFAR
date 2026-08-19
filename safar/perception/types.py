"""Shared data models for SAFAR Phase 2 perception."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple


Point3D = Tuple[float, float, float]
BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class SAFARDetection:
    """Image-level Phase 1B detection with no invented world measurements."""

    class_name: str
    confidence: float
    bbox: BBox
    category: str
    source: str = "yolo"


@dataclass(frozen=True)
class Detection:
    """A single object observation in ego-relative coordinates."""

    object_id: str
    label: str
    position_m: Point3D
    velocity_mps: Point3D = (0.0, 0.0, 0.0)
    confidence: float = 1.0
    source: str = "actor"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def distance_m(self) -> float:
        """Planar distance from the ego vehicle in metres."""
        return (self.position_m[0] ** 2 + self.position_m[1] ** 2) ** 0.5


@dataclass(frozen=True)
class TrackedObject:
    """A detection with a stable tracker identifier and age."""

    track_id: str
    detection: Detection
    age_frames: int = 1
    missed_frames: int = 0


@dataclass(frozen=True)
class PerceptionFrame:
    """Result produced for one simulation or sensor tick."""

    timestamp_s: float
    detections: Tuple[Detection, ...]
    tracks: Tuple[TrackedObject, ...]


def as_point3d(location: Any) -> Point3D:
    """Convert a CARLA-like location object or a three-value sequence."""
    if hasattr(location, "x"):
        return (float(location.x), float(location.y), float(getattr(location, "z", 0.0)))
    return (float(location[0]), float(location[1]), float(location[2]))
