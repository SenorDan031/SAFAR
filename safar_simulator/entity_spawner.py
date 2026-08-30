"""
SAFAR Simulator — Dynamic Random Entity & Traffic Spawner Engine
Dynamically spawns and manages moving cars, motorcycles, buses, trucks, pedestrians, and bicycles
around the player vehicle with autonomous lane/sidewalk behaviors and random seed support.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any
import random
import time
import math

class EntityClass(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"
    PEDESTRIAN = "pedestrian"
    BICYCLE = "bicycle"

class EntityBehavior(str, Enum):
    CRUISING = "CRUISING"
    SUDDEN_BRAKE = "SUDDEN_BRAKE"
    LANE_CUT_IN = "LANE_CUT_IN"
    CROSSING_PATH = "CROSSING_PATH"
    OPPOSITE_TRAFFIC = "OPPOSITE_TRAFFIC"
    SIDEWALK_WALK = "SIDEWALK_WALK"

@dataclass
class SimulatedEntity:
    id: int
    entity_class: EntityClass
    behavior: EntityBehavior
    distance_m: float           # Distance along road ahead of ego vehicle
    lateral_offset_m: float     # Negative = left lane (driving), Positive = right lane (opposite/sidewalk)
    speed_kmh: float
    dimensions_m: Tuple[float, float, float] # (length, width, height)
    heading_deg: float = 0.0
    is_hazard: bool = False
    spawn_time_s: float = 0.0
    lifetime_s: float = 60.0
    trajectory_state: str = "OUTSIDE" # "OUTSIDE", "NEAR", "INTERSECTING", "DIRECTLY_AHEAD"

class EntitySpawnerConfig:
    def __init__(
        self,
        density_preset: str = "MEDIUM", # "LOW" (10), "MEDIUM" (30), "HIGH" (60)
        random_seed: Optional[int] = None,
        min_spawn_dist_m: float = 15.0,
        max_spawn_dist_m: float = 100.0,
        despawn_dist_m: float = 130.0,
        hazard_probability: float = 0.35
    ):
        self.density_preset = density_preset
        self.random_seed = random_seed
        self.min_spawn_dist_m = min_spawn_dist_m
        self.max_spawn_dist_m = max_spawn_dist_m
        self.despawn_dist_m = despawn_dist_m
        self.hazard_probability = hazard_probability

        if density_preset == "LOW":
            self.target_entity_count = 10
        elif density_preset == "HIGH":
            self.target_entity_count = 60
        else: # MEDIUM
            self.target_entity_count = 30


class DynamicEntitySpawner:
    """Manages spawning, movement simulation, and dynamic pooling around the ego vehicle."""

    DIMENSION_MAP = {
        EntityClass.CAR: (4.5, 1.8, 1.5),
        EntityClass.MOTORCYCLE: (2.0, 0.8, 1.2),
        EntityClass.BUS: (11.0, 2.5, 3.2),
        EntityClass.TRUCK: (9.0, 2.4, 3.0),
        EntityClass.PEDESTRIAN: (0.5, 0.5, 1.75),
        EntityClass.BICYCLE: (1.8, 0.6, 1.4)
    }

    SPEED_RANGES = {
        EntityClass.CAR: (30.0, 55.0),
        EntityClass.MOTORCYCLE: (35.0, 60.0),
        EntityClass.BUS: (20.0, 35.0),
        EntityClass.TRUCK: (20.0, 40.0),
        EntityClass.PEDESTRIAN: (3.0, 5.0),
        EntityClass.BICYCLE: (10.0, 18.0)
    }

    def __init__(self, config: Optional[EntitySpawnerConfig] = None):
        self.config = config or EntitySpawnerConfig()
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)

        self.entities: Dict[int, SimulatedEntity] = {}
        self.next_entity_id = 1
        self.start_time = time.time()
        self.total_spawned_count = 0

    def seed(self, seed_val: int):
        self.config.random_seed = seed_val
        random.seed(seed_val)

    def spawn_entity(self, force_hazard: bool = False, entity_type: Optional[EntityClass] = None) -> SimulatedEntity:
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        self.total_spawned_count += 1

        if entity_type is None:
            weights = [0.45, 0.25, 0.08, 0.07, 0.10, 0.05]
            entity_type = random.choices(list(EntityClass), weights=weights)[0]

        is_hazard = force_hazard or (random.random() < self.config.hazard_probability)

        # Determine behavior and lane placement
        if is_hazard:
            hazard_behaviors = [
                EntityBehavior.SUDDEN_BRAKE,
                EntityBehavior.LANE_CUT_IN,
                EntityBehavior.CROSSING_PATH
            ]
            behavior = random.choice(hazard_behaviors)
            # Spawn in front of ego path (distance 15m to 40m)
            dist_m = random.uniform(15.0, 45.0)
            if behavior == EntityBehavior.CROSSING_PATH:
                lat_m = random.uniform(-4.0, 4.0)
            elif behavior == EntityBehavior.LANE_CUT_IN:
                lat_m = random.uniform(1.8, 3.5) # Starts from adjacent lane
            else: # SUDDEN_BRAKE
                lat_m = random.uniform(-0.5, 0.5) # Directly in ego lane
        else:
            # Ambient regular traffic
            normal_behaviors = [
                EntityBehavior.CRUISING,
                EntityBehavior.OPPOSITE_TRAFFIC,
                EntityBehavior.SIDEWALK_WALK
            ]
            behavior = random.choice(normal_behaviors)
            dist_m = random.uniform(self.config.min_spawn_dist_m, self.config.max_spawn_dist_m)
            if behavior == EntityBehavior.OPPOSITE_TRAFFIC:
                lat_m = random.uniform(2.5, 4.5) # Opposite right-side lane
            elif behavior == EntityBehavior.SIDEWALK_WALK:
                lat_m = random.uniform(-4.5, -3.2) # Sidewalk
            else: # CRUISING
                lat_m = random.uniform(-0.8, 0.8) # Left driving lane

        speed_range = self.SPEED_RANGES[entity_type]
        speed = random.uniform(speed_range[0], speed_range[1])
        dims = self.DIMENSION_MAP[entity_type]

        entity = SimulatedEntity(
            id=entity_id,
            entity_class=entity_type,
            behavior=behavior,
            distance_m=dist_m,
            lateral_offset_m=lat_m,
            speed_kmh=speed,
            dimensions_m=dims,
            is_hazard=is_hazard,
            spawn_time_s=time.time() - self.start_time
        )
        self.entities[entity_id] = entity
        return entity

    def update(self, ego_speed_kmh: float, dt: float) -> List[SimulatedEntity]:
        """Steps entity kinematics relative to ego vehicle."""
        ego_speed_mps = (ego_speed_kmh / 3.6)
        despawn_ids = []

        for e_id, ent in self.entities.items():
            ent_speed_mps = (ent.speed_kmh / 3.6)

            # Update distance relative to ego
            if ent.behavior == EntityBehavior.OPPOSITE_TRAFFIC:
                # Approaching from opposite direction
                relative_v = ego_speed_mps + ent_speed_mps
                ent.distance_m -= relative_v * dt
            else:
                # Same direction traffic
                relative_v = ego_speed_mps - ent_speed_mps
                ent.distance_m -= relative_v * dt

            # Update lateral movement for cut-in and crossing
            if ent.behavior == EntityBehavior.LANE_CUT_IN:
                # Merges toward center (lat_m -> 0.0)
                if ent.lateral_offset_m > 0.0:
                    ent.lateral_offset_m = max(0.0, ent.lateral_offset_m - 1.2 * dt)
            elif ent.behavior == EntityBehavior.CROSSING_PATH:
                # Pedestrian crosses across lane
                ent.lateral_offset_m += 1.5 * dt

            # Check despawn bounds (too far ahead or passed behind)
            if ent.distance_m < -15.0 or ent.distance_m > self.config.despawn_dist_m:
                despawn_ids.append(e_id)

        for d_id in despawn_ids:
            del self.entities[d_id]

        # Maintain target entity count by spawning new entities ahead
        while len(self.entities) < self.config.target_entity_count:
            self.spawn_entity()

        return list(self.entities.values())

    def clear(self):
        self.entities.clear()
        self.next_entity_id = 1
