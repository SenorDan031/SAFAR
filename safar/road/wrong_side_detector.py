"""Classify potentially wrong-side vehicles from lane and motion context."""

import math
from dataclasses import dataclass
from enum import Enum

from .lane_analyzer import LaneContext


class WrongSideStatus(str, Enum):
    WRONG_SIDE = "wrong_side"
    SAME_SIDE = "same_side"
    ADJACENT = "adjacent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VehicleRoadState:
    object_id: str
    lane: LaneContext
    position_m: tuple
    velocity_mps: tuple
    heading_deg: float


@dataclass(frozen=True)
class WrongSideResult:
    status: WrongSideStatus
    distance_m: float
    relative_speed_mps: float
    ttc_s: object
    path_conflict: bool
    reason: str


def heading_alignment(first_deg, second_deg):
    return math.cos(math.radians(first_deg - second_deg))


class WrongSideDetector:
    """Conservative warning classifier; it makes no driving decisions."""

    def classify(self, ego, other):
        if ego.lane is None or other.lane is None:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Lane context unavailable.")
        if not ego.lane.is_driving_lane or not other.lane.is_driving_lane:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Actor is outside a driving lane.")
        if ego.lane.is_junction or other.lane.is_junction:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Junction lane direction is ambiguous.")

        same_road = ego.lane.road_id == other.lane.road_id
        same_lane = same_road and ego.lane.lane_id == other.lane.lane_id
        other_follows_lane = heading_alignment(other.heading_deg, other.lane.heading_deg) >= 0.5
        opposing_ego_heading = heading_alignment(other.heading_deg, ego.lane.heading_deg) <= -0.5
        conflict = same_lane and self._approaching(ego, other)

        if same_lane and opposing_ego_heading:
            return self._result(WrongSideStatus.WRONG_SIDE, ego, other, conflict, "Vehicle is against this lane's expected direction.")
        if same_lane and other_follows_lane:
            return self._result(WrongSideStatus.SAME_SIDE, ego, other, conflict, "Vehicle follows the same lane direction.")
        if same_road:
            return self._result(WrongSideStatus.ADJACENT, ego, other, False, "Vehicle is in a separate road lane.")
        return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Vehicle is on a different road.")

    def _approaching(self, ego, other):
        dx = other.position_m[0] - ego.position_m[0]
        dy = other.position_m[1] - ego.position_m[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            return True
        relative_x = ego.velocity_mps[0] - other.velocity_mps[0]
        relative_y = ego.velocity_mps[1] - other.velocity_mps[1]
        return (relative_x * dx + relative_y * dy) / distance > 0.1

    def _result(self, status, ego, other, conflict, reason):
        dx = other.position_m[0] - ego.position_m[0]
        dy = other.position_m[1] - ego.position_m[1]
        distance = math.hypot(dx, dy)
        relative_x = ego.velocity_mps[0] - other.velocity_mps[0]
        relative_y = ego.velocity_mps[1] - other.velocity_mps[1]
        relative_speed = (relative_x * dx + relative_y * dy) / distance if distance else 0.0
        relative_speed = max(0.0, relative_speed)
        ttc = distance / relative_speed if conflict and relative_speed > 0 else None
        return WrongSideResult(status, distance, relative_speed, ttc, conflict, reason)
