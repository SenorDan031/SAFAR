"""Spawn randomized CARLA entities to exercise SAFAR perception.

Start CARLA, then run:
    python -m scenarios.random_entities_scene
"""

import random
import time

import carla

from safar.perception import CarlaPerception


HOST = "127.0.0.1"
PORT = 2000
SCENE_SECONDS = 45
ENTITY_COUNT = 18
RANDOM_SEED = 42


def first_blueprint(blueprints, patterns):
    for pattern in patterns:
        matches = blueprints.filter(pattern)
        if matches:
            return matches[0]
    raise RuntimeError("No CARLA blueprint matched: {}".format(", ".join(patterns)))


def spawn_actor(world, blueprint, transform, role_name):
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", role_name)
    return world.try_spawn_actor(blueprint, transform)


def offset_transform(base, forward_m, right_m):
    location = (
        base.location
        + base.get_forward_vector() * forward_m
        + base.get_right_vector() * right_m
    )
    location.z += 0.5
    return carla.Transform(location, base.rotation)


def spawn_random_entities(world, ego, count=ENTITY_COUNT, seed=RANDOM_SEED):
    """Create a repeatable mix of traffic, walkers, bikes, and hazards."""
    rng = random.Random(seed)
    blueprints = world.get_blueprint_library()
    points = list(world.get_map().get_spawn_points())
    rng.shuffle(points)
    actors = []
    vehicle_blueprints = blueprints.filter("vehicle.*")
    walker_blueprint = first_blueprint(blueprints, ("walker.pedestrian.*",))
    bike_blueprint = first_blueprint(
        blueprints, ("vehicle.*bike*", "vehicle.*motorcycle*", "vehicle.*")
    )
    hazard_blueprint = first_blueprint(
        blueprints, ("static.prop.trafficcone01", "static.prop.*")
    )

    for index in range(count):
        kind = index % 4
        if kind == 0 and points:
            blueprint = rng.choice(vehicle_blueprints)
            actor = spawn_actor(world, blueprint, points.pop(), "safar_random_vehicle")
            if actor is not None:
                actor.apply_control(carla.VehicleControl(throttle=0.22))
        else:
            base = ego.get_transform() if index < 8 else rng.choice(points)
            forward_m = rng.uniform(12.0, 55.0)
            right_m = rng.choice((-5.0, -3.0, 3.0, 5.0))
            if kind == 1:
                actor = spawn_actor(world, walker_blueprint, offset_transform(base, forward_m, right_m), "safar_random_pedestrian")
            elif kind == 2:
                actor = spawn_actor(world, bike_blueprint, offset_transform(base, forward_m, right_m), "safar_random_two_wheeler")
                if actor is not None:
                    actor.apply_control(carla.VehicleControl(throttle=0.2))
            else:
                actor = spawn_actor(world, hazard_blueprint, offset_transform(base, forward_m, right_m), "safar_random_hazard")
        if actor is not None:
            actors.append(actor)
    return actors


def follow_ego_vehicle(world, ego):
    transform = ego.get_transform()
    location = transform.location - transform.get_forward_vector() * 10.0 + carla.Location(z=5.0)
    world.get_spectator().set_transform(
        carla.Transform(location, carla.Rotation(pitch=-18.0, yaw=transform.rotation.yaw))
    )


def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(15.0)
    world = client.get_world()
    blueprints = world.get_blueprint_library()
    ego = None
    actors = []
    try:
        ego_blueprint = first_blueprint(blueprints, ("vehicle.tesla.model3", "vehicle.*"))
        for transform in world.get_map().get_spawn_points():
            ego = spawn_actor(world, ego_blueprint, transform, "safar_random_ego")
            if ego is not None:
                break
        if ego is None:
            raise RuntimeError("Could not spawn the random-scene ego vehicle.")
        actors = spawn_random_entities(world, ego)
        perception = CarlaPerception()
        print("Random entity scene started: {} actors (seed {}).".format(len(actors), RANDOM_SEED))
        end_time = time.time() + SCENE_SECONDS
        while time.time() < end_time:
            frame = perception.perceive(world, ego)
            labels = {}
            for detection in frame.detections:
                labels[detection.label] = labels.get(detection.label, 0) + 1
            follow_ego_vehicle(world, ego)
            print("Detected={} | tracks={}".format(labels, len(frame.tracks)))
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Random scene stopped by user.")
    finally:
        for actor in reversed(actors):
            if actor.is_alive:
                actor.destroy()
        if ego is not None and ego.is_alive:
            ego.destroy()
        print("Random scene actors cleaned up.")


if __name__ == "__main__":
    main()
