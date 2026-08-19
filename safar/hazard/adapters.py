"""Adapt CARLA or image observations into the common hazard input model."""

from typing import Optional, Tuple

from .models import PerceptionObject, VehicleSnapshot
from .policy import HazardPolicy


def carla_detection_to_object(
    detection,
    vehicle: VehicleSnapshot,
    policy: HazardPolicy,
    ego_forward_xy: Optional[Tuple[float, float]] = None,
) -> PerceptionObject:
    """Adapt existing CARLA ``Detection`` without placing CARLA logic in risk code.

    ``Detection.position_m`` is world-axis relative in the legacy CARLA
    adapter. Passing CARLA's ego forward vector lets this boundary rotate that
    vector into forward/lateral vehicle coordinates before relevance testing.
    """
    relative_x, relative_y, _ = detection.position_m
    if ego_forward_xy is None:
        forward_m, lateral_m = relative_x, abs(relative_y)
    else:
        forward_x, forward_y = ego_forward_xy
        forward_m = relative_x * forward_x + relative_y * forward_y
        lateral_m = abs(relative_x * -forward_y + relative_y * forward_x)
    closing_mps = max(0.0, vehicle.speed_kmh / 3.6 - detection.velocity_mps[0])
    return PerceptionObject(
        object_id=detection.object_id,
        category=detection.label,
        confidence=detection.confidence,
        source=detection.source,
        in_path=forward_m > 0.0 and lateral_m <= policy.path_half_width_m,
        distance_m=detection.distance_m,
        closing_speed_kmh=closing_mps * 3.6,
    )


def image_detection_to_object(
    detection,
    image_width: int,
    object_id: Optional[str] = None,
    policy: Optional[HazardPolicy] = None,
    distance_m: Optional[float] = None,
    closing_speed_kmh: Optional[float] = None,
) -> PerceptionObject:
    """Adapt a Phase 1B ``SAFARDetection`` without inventing metric distance.

    Optional metric values may only come from a future validated sensor/source;
    plain YOLO callers leave them as ``None``.
    """
    active_policy = policy or HazardPolicy()
    x1, _, x2, _ = detection.bbox
    centre_ratio = ((x1 + x2) / 2.0) / image_width
    return PerceptionObject(
        object_id=object_id or f"image:{detection.class_name}:{detection.bbox}",
        category=detection.category,
        confidence=detection.confidence,
        source=detection.source,
        in_path=active_policy.image_path_left_ratio <= centre_ratio <= active_policy.image_path_right_ratio,
        distance_m=distance_m,
        closing_speed_kmh=closing_speed_kmh,
        bbox=detection.bbox,
    )
