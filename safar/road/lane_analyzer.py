"""Convert CARLA waypoints into small, framework-neutral lane contexts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LaneContext:
    road_id: int
    lane_id: int
    lane_type: str
    lane_width_m: float
    is_junction: bool
    heading_deg: float

    @property
    def is_driving_lane(self):
        return self.lane_type.lower() == "driving"


class LaneAnalyzer:
    """Reads only the CARLA map boundary; other layers receive LaneContext."""

    def __init__(self, carla_map):
        self.carla_map = carla_map

    def analyze(self, actor):
        waypoint = self.carla_map.get_waypoint(actor.get_location(), project_to_road=True)
        if waypoint is None:
            return None
        return LaneContext(
            road_id=waypoint.road_id,
            lane_id=waypoint.lane_id,
            lane_type=str(waypoint.lane_type).split(".")[-1].lower(),
            lane_width_m=float(waypoint.lane_width),
            is_junction=bool(waypoint.is_junction),
            heading_deg=float(waypoint.transform.rotation.yaw),
        )
