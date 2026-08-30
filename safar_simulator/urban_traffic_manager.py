"""
SAFAR Simulator — Dynamic Urban Traffic & Pedestrian AI System
Manages realistic multi-lane urban traffic (Left-Hand Traffic / Indian Road Dynamics)
with heterogeneous vehicle archetypes, intersection navigation, and natural hazard events.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
import random
import math
import time

class TrafficArchetype(str, Enum):
    SEDAN = "sedan"
    SUV = "suv"
    AUTO_RICKSHAW = "auto_rickshaw"
    MOTORCYCLE = "motorcycle"
    CITY_BUS = "city_bus"
    DELIVERY_TRUCK = "truck"
    BICYCLE = "bicycle"
    PEDESTRIAN = "pedestrian"


@dataclass
class UrbanActor:
    id: int
    archetype: TrafficArchetype
    distance_m: float
    lateral_offset_m: float
    speed_kmh: float
    target_speed_kmh: float
    length_m: float
    width_m: float
    lane_id: int              # -1: Left Sidewalk, 0: Left Lane (Ego), 1: Right Lane, 2: Opposite Lane
    lateral_speed_mps: float = 0.0
    is_hazard_event: bool = False
    hazard_event_type: str = "none" # "CUT_IN", "HARD_BRAKE", "CROSSING", "JUNCTION_TURN"
    turn_signal: str = "OFF"        # "LEFT", "RIGHT", "HAZARDS", "OFF"
    brake_lights: bool = False


class UrbanTrafficManager:
    """Simulates realistic ambient urban traffic following left-hand traffic rules."""

    ARCHETYPE_SPECS = {
        TrafficArchetype.SEDAN: {"speed_range": (35.0, 55.0), "length": 4.5, "width": 1.8, "weight": 0.30},
        TrafficArchetype.SUV: {"speed_range": (35.0, 50.0), "length": 4.8, "width": 2.0, "weight": 0.20},
        TrafficArchetype.AUTO_RICKSHAW: {"speed_range": (25.0, 38.0), "length": 2.8, "width": 1.3, "weight": 0.15},
        TrafficArchetype.MOTORCYCLE: {"speed_range": (35.0, 60.0), "length": 2.0, "width": 0.8, "weight": 0.15},
        TrafficArchetype.CITY_BUS: {"speed_range": (25.0, 40.0), "length": 10.5, "width": 2.5, "weight": 0.08},
        TrafficArchetype.DELIVERY_TRUCK: {"speed_range": (25.0, 42.0), "length": 7.0, "width": 2.4, "weight": 0.05},
        TrafficArchetype.BICYCLE: {"speed_range": (12.0, 20.0), "length": 1.7, "width": 0.6, "weight": 0.04},
        TrafficArchetype.PEDESTRIAN: {"speed_range": (3.5, 5.5), "length": 0.5, "width": 0.5, "weight": 0.03},
    }

    # Left-Hand Traffic (LHT) Lane Offsets (meters from center divider)
    LANE_OFFSETS = {
        -1: -4.5,  # Left Sidewalk (Pedestrians)
         0: -1.8,  # Left Driving Lane (Ego / Slow Traffic)
         1: +1.8,  # Right Driving Lane (Overtaking)
         2: +5.4,  # Opposite Direction Lane (Oncoming Traffic)
    }

    def __init__(self, target_actor_count: int = 24, hazard_frequency_s: float = 8.0):
        self.target_actor_count = target_actor_count
        self.hazard_frequency_s = hazard_frequency_s
        self.actors: Dict[int, UrbanActor] = {}
        self.next_actor_id = 100
        self.last_hazard_time_s = time.time()

        # Seed initial ambient traffic distribution
        self._populate_initial_traffic()

    def _pick_random_archetype(self) -> TrafficArchetype:
        keys = list(self.ARCHETYPE_SPECS.keys())
        weights = [self.ARCHETYPE_SPECS[k]["weight"] for k in keys]
        return random.choices(keys, weights=weights, k=1)[0]

    def _populate_initial_traffic(self):
        for _ in range(self.target_actor_count):
            self.spawn_actor(
                min_dist_m=12.0,
                max_dist_m=130.0
            )

    def spawn_actor(
        self,
        min_dist_m: float = 25.0,
        max_dist_m: float = 120.0,
        forced_archetype: Optional[TrafficArchetype] = None,
        forced_lane: Optional[int] = None
    ) -> UrbanActor:
        arch = forced_archetype or self._pick_random_archetype()
        spec = self.ARCHETYPE_SPECS[arch]

        # Determine appropriate lane
        if arch == TrafficArchetype.PEDESTRIAN:
            lane = -1 if forced_lane is None else forced_lane
        elif arch in (TrafficArchetype.BICYCLE, TrafficArchetype.AUTO_RICKSHAW):
            lane = 0 if forced_lane is None else forced_lane
        else:
            lane = random.choice([0, 1, 2]) if forced_lane is None else forced_lane

        base_lat = self.LANE_OFFSETS[lane] + random.uniform(-0.25, 0.25)
        dist = random.uniform(min_dist_m, max_dist_m)
        spd = random.uniform(*spec["speed_range"])

        # Oncoming traffic has negative relative direction
        if lane == 2:
            spd = -spd

        actor = UrbanActor(
            id=self.next_actor_id,
            archetype=arch,
            distance_m=dist,
            lateral_offset_m=base_lat,
            speed_kmh=spd,
            target_speed_kmh=spd,
            length_m=spec["length"],
            width_m=spec["width"],
            lane_id=lane
        )
        self.actors[self.next_actor_id] = actor
        self.next_actor_id += 1
        return actor

    def trigger_natural_hazard(self) -> Optional[UrbanActor]:
        """Injects a realistic unpredictable road event ahead of the player."""
        event_types = ["CUT_IN", "LEAD_HARD_BRAKE", "CROSSING_PEDESTRIAN"]
        event = random.choice(event_types)

        if event == "CUT_IN":
            # Motorcycle or car cut-in from adjacent lane
            actor = self.spawn_actor(
                min_dist_m=20.0,
                max_dist_m=35.0,
                forced_archetype=TrafficArchetype.MOTORCYCLE,
                forced_lane=1
            )
            actor.is_hazard_event = True
            actor.hazard_event_type = "CUT_IN"
            actor.lateral_speed_mps = -1.2 # Move left into ego lane
            actor.turn_signal = "LEFT"
            return actor

        elif event == "LEAD_HARD_BRAKE":
            # Vehicle directly ahead brakes suddenly
            actor = self.spawn_actor(
                min_dist_m=18.0,
                max_dist_m=28.0,
                forced_archetype=TrafficArchetype.SEDAN,
                forced_lane=0
            )
            actor.is_hazard_event = True
            actor.hazard_event_type = "HARD_BRAKE"
            actor.target_speed_kmh = 0.0
            actor.brake_lights = True
            return actor

        elif event == "CROSSING_PEDESTRIAN":
            # Pedestrian stepping off sidewalk across road
            actor = self.spawn_actor(
                min_dist_m=15.0,
                max_dist_m=24.0,
                forced_archetype=TrafficArchetype.PEDESTRIAN,
                forced_lane=-1
            )
            actor.is_hazard_event = True
            actor.hazard_event_type = "CROSSING"
            actor.lateral_speed_mps = +1.1 # Walk right across ego path
            return actor

        return None

    def update(self, ego_speed_kmh: float, dt: float) -> List[UrbanActor]:
        """Advances traffic state at 60 Hz and pools actors seamlessly."""
        now = time.time()

        # Check for natural periodic hazard trigger
        if now - self.last_hazard_time_s >= self.hazard_frequency_s:
            self.trigger_natural_hazard()
            self.last_hazard_time_s = now + random.uniform(-2.0, 3.0)

        ego_v_mps = ego_speed_kmh / 3.6
        to_despawn = []

        for a_id, actor in self.actors.items():
            actor_v_mps = actor.speed_kmh / 3.6
            relative_v_mps = ego_v_mps - actor_v_mps

            # Update longitudinal distance relative to ego vehicle
            actor.distance_m -= relative_v_mps * dt

            # Update lateral movement (cut-ins, lane changes, pedestrian crossing)
            if actor.lateral_speed_mps != 0.0:
                actor.lateral_offset_m += actor.lateral_speed_mps * dt
                # Clamp lane change when reaching target lane center
                if actor.hazard_event_type == "CUT_IN" and actor.lateral_offset_m <= self.LANE_OFFSETS[0]:
                    actor.lateral_offset_m = self.LANE_OFFSETS[0]
                    actor.lateral_speed_mps = 0.0
                    actor.turn_signal = "OFF"
                elif actor.hazard_event_type == "CROSSING" and actor.lateral_offset_m >= self.LANE_OFFSETS[1]:
                    actor.lateral_speed_mps = 0.0

            # Handle hard brake deceleration
            if actor.hazard_event_type == "HARD_BRAKE":
                actor.speed_kmh = max(0.0, actor.speed_kmh - (7.0 * 3.6 * dt))

            # Despawn actors that pass far behind (-20m) or get too far ahead (+140m)
            if actor.distance_m < -20.0 or actor.distance_m > 140.0:
                to_despawn.append(a_id)

        for a_id in to_despawn:
            del self.actors[a_id]

        # Maintain ambient traffic density pool
        while len(self.actors) < self.target_actor_count:
            self.spawn_actor(min_dist_m=60.0, max_dist_m=125.0)

        return list(self.actors.values())
