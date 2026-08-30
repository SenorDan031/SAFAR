"""
SAFAR Simulator — Indian Urban Road Environment & Scenario Generator
Generates realistic Indian road parameters:
- Left-Hand Traffic (LHT / Drive on the Left)
- Mixed vehicle categories (Motorcycles, Auto-Rickshaws, City Buses, Trucks, Pedestrians)
- Roadside infrastructure (Barricades, Concrete Kerbs, Divider Markings, Streetlights)
- Dynamic hazard obstacle tables with left-side lane filtering
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
import json
import math

@dataclass
class IndianRoadLane:
    lane_id: int
    lane_type: str         # "left_driving_lane", "right_opposing_lane", "shoulder"
    center_offset_m: float # Negative = left lane (driving), Positive = right lane (opposing)
    width_m: float = 3.5
    speed_limit_kmh: float = 50.0

@dataclass
class IndianRoadObstacle:
    id: int
    class_name: str        # "motorcycle", "auto_rickshaw", "car", "bus", "pedestrian", "barricade"
    lane_id: int
    spawn_distance_m: float
    target_speed_kmh: float
    behavior: str          # "stationary", "cruising", "sudden_brake", "lane_cut_in", "crossing"
    dimensions_m: Tuple[float, float, float] # (length, width, height)

@dataclass
class IndianUrbanEnvironment:
    road_name: str = "MG_Road_Urban_Corridor"
    traffic_direction: str = "LEFT_HAND_DRIVE" # India standard LHT
    surface_condition: str = "ASPHALT_MIXED"
    lighting_preset: str = "GOLDEN_HOUR_SUNSET"
    ambient_temperature_c: float = 32.0
    lanes: List[IndianRoadLane] = field(default_factory=list)
    active_obstacles: List[IndianRoadObstacle] = field(default_factory=list)

    @classmethod
    def create_default_corridor(cls) -> "IndianUrbanEnvironment":
        env = cls()
        # 1. Lanes (2-lane urban road with left-hand traffic)
        env.lanes = [
            IndianRoadLane(lane_id=1, lane_type="left_driving_lane", center_offset_m=-1.75, width_m=3.5, speed_limit_kmh=50.0),
            IndianRoadLane(lane_id=2, lane_type="right_opposing_lane", center_offset_m=1.75, width_m=3.5, speed_limit_kmh=50.0),
        ]

        # 2. Authentic Indian Traffic Obstacles
        env.active_obstacles = [
            IndianRoadObstacle(
                id=1,
                class_name="auto_rickshaw",
                lane_id=1,
                spawn_distance_m=35.0,
                target_speed_kmh=30.0,
                behavior="cruising",
                dimensions_m=(2.6, 1.3, 1.7)
            ),
            IndianRoadObstacle(
                id=2,
                class_name="motorcycle",
                lane_id=1,
                spawn_distance_m=18.0,
                target_speed_kmh=40.0,
                behavior="lane_cut_in",
                dimensions_m=(2.0, 0.8, 1.2)
            ),
            IndianRoadObstacle(
                id=3,
                class_name="pedestrian",
                lane_id=1,
                spawn_distance_m=22.0,
                target_speed_kmh=4.0,
                behavior="crossing",
                dimensions_m=(0.5, 0.5, 1.75)
            ),
            IndianRoadObstacle(
                id=4,
                class_name="bus",
                lane_id=1,
                spawn_distance_m=45.0,
                target_speed_kmh=25.0,
                behavior="sudden_brake",
                dimensions_m=(10.5, 2.5, 3.2)
            ),
            IndianRoadObstacle(
                id=5,
                class_name="barricade",
                lane_id=1,
                spawn_distance_m=14.0,
                target_speed_kmh=0.0,
                behavior="stationary",
                dimensions_m=(2.0, 0.5, 1.0)
            )
        ]
        return env

    def to_json(self) -> str:
        data = {
            "road_name": self.road_name,
            "traffic_direction": self.traffic_direction,
            "surface_condition": self.surface_condition,
            "lighting_preset": self.lighting_preset,
            "lanes": [l.__dict__ for l in self.lanes],
            "obstacles": [
                {
                    "id": o.id,
                    "class_name": o.class_name,
                    "lane_id": o.lane_id,
                    "spawn_distance_m": o.spawn_distance_m,
                    "target_speed_kmh": o.target_speed_kmh,
                    "behavior": o.behavior,
                    "dimensions": list(o.dimensions_m)
                } for o in self.active_obstacles
            ]
        }
        return json.dumps(data, indent=2)

if __name__ == "__main__":
    corridor = IndianUrbanEnvironment.create_default_corridor()
    print("======================================================================")
    print(" INDIAN URBAN ROAD CORRIDOR SPECIFICATION")
    print("======================================================================")
    print(corridor.to_json())
