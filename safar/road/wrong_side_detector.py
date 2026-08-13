#This file will allow the system to detect vehicles driving on the wrong side of the road!

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
    return math.cos(math.radians(first_deg - second_deg))  #Calculates how closely two vehicle headings are aligned


class WrongSideDetector:
    """Conservative warning classifier; it makes no driving decisions."""

    def classify(self, ego, other):
        if ego.lane is None or other.lane is None:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Lane context unavailable.")  #Returns unknown status when lane information is unavailable
        if not ego.lane.is_driving_lane or not other.lane.is_driving_lane:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Actor is outside a driving lane.")  #Returns unknown status when either actor is outside a driving lane
        if ego.lane.is_junction or other.lane.is_junction:
            return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Junction lane direction is ambiguous.")  #Returns unknown status because lane direction can be unclear inside junctions

        same_road = ego.lane.road_id == other.lane.road_id  #Checks if both vehicles are on the same road
        same_lane = same_road and ego.lane.lane_id == other.lane.lane_id  #Checks if both vehicles are in the same lane
        other_follows_lane = heading_alignment(other.heading_deg, other.lane.heading_deg) >= 0.5  #Checks if the other vehicle follows its lane direction
        opposing_ego_heading = heading_alignment(other.heading_deg, ego.lane.heading_deg) <= -0.5  #Checks if the other vehicle is moving against the ego lane direction
        conflict = same_lane and self._approaching(ego, other)  #Checks if both vehicles share a lane and are approaching each other

        if same_lane and opposing_ego_heading:
            return self._result(WrongSideStatus.WRONG_SIDE, ego, other, conflict, "Vehicle is against this lane's expected direction.")  #Marks the vehicle as wrong side when it moves against the lane direction
        if same_lane and other_follows_lane:
            return self._result(WrongSideStatus.SAME_SIDE, ego, other, conflict, "Vehicle follows the same lane direction.")  #Marks the vehicle as same side when it follows the lane direction
        if same_road:
            return self._result(WrongSideStatus.ADJACENT, ego, other, False, "Vehicle is in a separate road lane.")  #Marks the vehicle as adjacent when it is on another lane of the same road
        return self._result(WrongSideStatus.UNKNOWN, ego, other, False, "Vehicle is on a different road.")  #Returns unknown status when vehicles are on different roads

    def _approaching(self, ego, other):
        dx = other.position_m[0] - ego.position_m[0]  #Calculates the horizontal distance between both vehicles
        dy = other.position_m[1] - ego.position_m[1]  #Calculates the vertical distance between both vehicles
        distance = math.hypot(dx, dy)  #Calculates the total distance between both vehicles
        if distance == 0:
            return True  #Treats vehicles at the same position as approaching
        relative_x = ego.velocity_mps[0] - other.velocity_mps[0]  #Calculates the relative velocity on the X axis
        relative_y = ego.velocity_mps[1] - other.velocity_mps[1]  #Calculates the relative velocity on the Y axis
        return (relative_x * dx + relative_y * dy) / distance > 0.1  #Checks if both vehicles are moving towards each other

    def _result(self, status, ego, other, conflict, reason):
        dx = other.position_m[0] - ego.position_m[0]  #Calculates the horizontal distance between both vehicles
        dy = other.position_m[1] - ego.position_m[1]  #Calculates the vertical distance between both vehicles
        distance = math.hypot(dx, dy)  #Calculates the total distance between both vehicles
        relative_x = ego.velocity_mps[0] - other.velocity_mps[0]  #Calculates the relative velocity on the X axis
        relative_y = ego.velocity_mps[1] - other.velocity_mps[1]  #Calculates the relative velocity on the Y axis
        relative_speed = (relative_x * dx + relative_y * dy) / distance if distance else 0.0  #Calculates the relative speed between both vehicles
        relative_speed = max(0.0, relative_speed)  #Prevents relative speed from becoming negative
        ttc = distance / relative_speed if conflict and relative_speed > 0 else None  #Calculates the estimated time before collision
        return WrongSideResult(status, distance, relative_speed, ttc, conflict, reason)  #Returns the final wrong-side assessment
