"""Run a CARLA scene that exercises every Logic_Engine Phase 2 perception label.

Start CARLA first, then run from the repository root:
    python -m scenarios.phase2_perception_scene
"""

import time
from typing import Iterable, List

import carla

from Logic_Engine.perception import CarlaPerception


HOST = "localhost"
PORT = 2000
SCENE_SECONDS = 20


def first_blueprint(blueprints: carla.BlueprintLibrary, patterns: Iterable[str]) -> carla.ActorBlueprint:
    """Return the first blueprint found from the supplied patterns."""
    for pattern in patterns:
        matches = blueprints.filter(pattern)
        if matches:
            return matches[0]
    raise RuntimeError("No CARLA blueprint matched: {}".format(", ".join(patterns)))


def offset_transform(base: carla.Transform, forward_m: float, right_m: float = 0.0) -> carla.Transform:
    forward = base.get_forward_vector()
    right = base.get_right_vector()
    location = base.location + forward * forward_m + right * right_m
    location.z += 0.5
    return carla.Transform(location, base.rotation)


def spawn(world: carla.World, blueprint: carla.ActorBlueprint, transform: carla.Transform, name: str) -> carla.Actor:
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", name)
    actor = world.try_spawn_actor(blueprint, transform)
    if actor is None:
        raise RuntimeError("Could not spawn {}. Try a different CARLA map or spawn point.".format(name))
    return actor


def spawn_scene(world: carla.World) -> List[carla.Actor]:
    """Create ego, vehicle, pedestrian, two-wheeler, and static-prop actors."""
    blueprints = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("The active CARLA map has no vehicle spawn points.")

    ego_blueprint = first_blueprint(blueprints, ("vehicle.tesla.model3", "vehicle.*"))
    for spawn_point in spawn_points:
        spawned: List[carla.Actor] = []
        try:
            ego = spawn(world, ego_blueprint, spawn_point, "Logic_Engine_perception_ego")
            spawned.append(ego)
            spawned.append(spawn(world, first_blueprint(blueprints, ("vehicle.audi.tt", "vehicle.*")), offset_transform(spawn_point, 18), "Logic_Engine_lead_vehicle"))
            spawned.append(spawn(world, first_blueprint(blueprints, ("walker.pedestrian.*",)), offset_transform(spawn_point, 11, 4), "Logic_Engine_pedestrian"))
            spawned.append(spawn(world, first_blueprint(blueprints, ("vehicle.*bike*", "vehicle.*motorcycle*", "vehicle.*")), offset_transform(spawn_point, 14, -3.5), "Logic_Engine_two_wheeler"))
            spawned.append(spawn(world, first_blueprint(blueprints, ("static.prop.trafficcone01", "static.prop.*")), offset_transform(spawn_point, 8, 2), "Logic_Engine_road_hazard"))
            return spawned
        except RuntimeError:
            for actor in reversed(spawned):
                actor.destroy()
    raise RuntimeError("Unable to find clear space for the Phase 2 perception scene.")


def report(frame) -> None:
    observed = ", ".join("{}:{} ({:.1f} m)".format(item.object_id, item.label, item.distance_m) for item in frame.detections)
    print("Detections [{}] | active tracks={}".format(observed, len(frame.tracks)))


def follow_ego_vehicle(world: carla.World, ego: carla.Actor) -> None:
    """Place the CARLA spectator behind the ego vehicle for scene visibility."""
    transform = ego.get_transform()
    camera_location = (
        transform.location
        - transform.get_forward_vector() * 10.0
        + carla.Location(z=5.0)
    )
    world.get_spectator().set_transform(
        carla.Transform(
            camera_location,
            carla.Rotation(pitch=-18.0, yaw=transform.rotation.yaw),
        )
    )


def start_motion(actors: List[carla.Actor]) -> None:
    """Drive the vehicle actors slowly so perception can observe motion."""
    ego, lead_vehicle, _pedestrian, two_wheeler, _hazard = actors
    ego.apply_control(carla.VehicleControl(throttle=0.24))
    lead_vehicle.apply_control(carla.VehicleControl(throttle=0.28))
    two_wheeler.apply_control(carla.VehicleControl(throttle=0.22))


def main() -> None:
    client = carla.Client(HOST, PORT)
    client.set_timeout(10.0)
    world = client.get_world()
    perception = CarlaPerception()
    actors: List[carla.Actor] = []

    try:
        actors = spawn_scene(world)
        ego = actors[0]
        start_motion(actors)
        print("Phase 2 perception scene started. Press Ctrl+C to stop early.")
        end_time = time.time() + SCENE_SECONDS
        while time.time() < end_time:
            follow_ego_vehicle(world, ego)
            report(perception.perceive(world, ego))
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Scene stopped by user.")
    finally:
        for actor in reversed(actors):
            if actor.is_alive:
                actor.destroy()
        print("Phase 2 scene actors cleaned up.")


if __name__ == "__main__":
    main()
