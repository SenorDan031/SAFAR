#This file will allow the system to analyze CARLA lane information and provide lane context!

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
        return self.lane_type.lower() == "driving"  #Checks if the current lane is a driving lane


class LaneAnalyzer:
    """Reads only the CARLA map boundary; other layers receive LaneContext."""

    def __init__(self, carla_map):
        self.carla_map = carla_map  #Stores the CARLA map for lane analysis

    def analyze(self, actor):
        waypoint = self.carla_map.get_waypoint(actor.get_location(), project_to_road=True)  #Gets the nearest road waypoint for the actor
        if waypoint is None:
            return None  #Returns no lane information if the actor is not on a valid road
        return LaneContext(
            road_id=waypoint.road_id,  #Gets the road ID from the CARLA waypoint
            lane_id=waypoint.lane_id,  #Gets the lane ID from the CARLA waypoint
            lane_type=str(waypoint.lane_type).split(".")[-1].lower(),  #Gets the lane type and converts it into a simple format
            lane_width_m=float(waypoint.lane_width),  #Gets the width of the current lane
            is_junction=bool(waypoint.is_junction),  #Checks if the actor is currently inside a junction
            heading_deg=float(waypoint.transform.rotation.yaw),  #Gets the direction of the current lane
        )
