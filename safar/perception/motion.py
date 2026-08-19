"""Qualitative image motion only; no pixel motion is converted to km/h."""
from enum import Enum


class TrafficState(str, Enum):
    MOVING = "MOVING"
    SLOWING = "SLOWING"
    STATIONARY = "STATIONARY"
    UNKNOWN = "UNKNOWN"


class ApparentMotion(str, Enum):
    APPROACHING = "APPROACHING"
    RECEDING = "RECEDING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


def _bbox_area(bbox) -> float:
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])


def apparent_motion(track) -> ApparentMotion:
    """Determine qualitative visual approach / receding / stability based on track history."""
    if not track or getattr(track, "age", 0) < 2:
        return ApparentMotion.UNKNOWN

    history = getattr(track, "history", None)
    if not history or len(history) < 2:
        return ApparentMotion.STABLE

    first_det = history[0]
    curr_det = history[-1]
    first_bbox = getattr(first_det, "bbox", None)
    curr_bbox = getattr(curr_det, "bbox", None)
    if not first_bbox or not curr_bbox:
        return ApparentMotion.STABLE

    first_area = _bbox_area(first_bbox)
    curr_area = _bbox_area(curr_bbox)
    if first_area <= 0:
        return ApparentMotion.STABLE

    area_ratio = curr_area / first_area
    bottom_delta = curr_bbox[3] - first_bbox[3]  # moving lower in frame = visually closer

    # Expanding bounding box or dropping significantly down the image plane
    if area_ratio > 1.08 or (bottom_delta > 8 and area_ratio > 1.02):
        return ApparentMotion.APPROACHING
    elif area_ratio < 0.92 or (bottom_delta < -8 and area_ratio < 0.98):
        return ApparentMotion.RECEDING
    return ApparentMotion.STABLE


def traffic_state(track) -> TrafficState:
    """Determine qualitative traffic state from track history and apparent motion."""
    if not track or getattr(track, "age", 0) < 3:
        return TrafficState.UNKNOWN

    history = getattr(track, "history", None)
    if not history or len(history) < 2:
        return TrafficState.STATIONARY

    first_det = history[0]
    curr_det = history[-1]
    first_bbox = getattr(first_det, "bbox", None)
    curr_bbox = getattr(curr_det, "bbox", None)
    if not first_bbox or not curr_bbox:
        return TrafficState.STATIONARY

    first_cx = (first_bbox[0] + first_bbox[2]) / 2.0
    first_cy = (first_bbox[1] + first_bbox[3]) / 2.0
    curr_cx = (curr_bbox[0] + curr_bbox[2]) / 2.0
    curr_cy = (curr_bbox[1] + curr_bbox[3]) / 2.0

    disp = ((curr_cx - first_cx) ** 2 + (curr_cy - first_cy) ** 2) ** 0.5
    motion = apparent_motion(track)

    if motion == ApparentMotion.APPROACHING or motion == ApparentMotion.RECEDING or disp > 15.0:
        return TrafficState.MOVING
    return TrafficState.STATIONARY
