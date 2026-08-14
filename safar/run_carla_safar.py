import argparse
import math
import random
import sys
import time

import carla
import pygame


HOST = "localhost"
PORT = 2000

MAX_SPEED = 15.0
BRAKE_DISTANCE = 8.0
CRITICAL_TTC = 1.5


#Essential utilities and tools used by Carla for vehicle movement logic

def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2 +
        (a.z - b.z) ** 2
    )


def speed(vehicle):
    velocity = vehicle.get_velocity()

    return math.sqrt(
        velocity.x ** 2 +
        velocity.y ** 2 +
        velocity.z ** 2
    )


def forward_speed(ego):
    velocity = ego.get_velocity()
    forward = ego.get_transform().get_forward_vector()

    return (
        velocity.x * forward.x +
        velocity.y * forward.y +
        velocity.z * forward.z
    )


def is_in_front(ego, actor, max_distance=60.0):
    ego_transform = ego.get_transform()

    ego_location = ego_transform.location
    actor_location = actor.get_transform().location

    direction = actor_location - ego_location
    distance_value = direction.length()

    if distance_value > max_distance:
        return False, distance_value

    forward = ego_transform.get_forward_vector()

    dot = (
        direction.x * forward.x +
        direction.y * forward.y +
        direction.z * forward.z
    )

    # Actor must be in front of ego.
    if dot <= 0:
        return False, distance_value

    # Rough lane/path validation.
    right = ego_transform.get_right_vector()

    lateral = abs(
        direction.x * right.x +
        direction.y * right.y +
        direction.z * right.z
    )

    if lateral > 4.0:
        return False, distance_value

    return True, distance_value


# Connects our backend with the CARLA for system simulation

def connect():
    client = carla.Client(HOST, PORT)
    client.set_timeout(10.0)

    world = client.get_world()

    print("Connected to CARLA")
    print("Map:", world.get_map().name)

    return client, world


#The below logic will be responsible for spawing entities while simulatiom

def spawn_ego(world):
    blueprint_library = world.get_blueprint_library()

    candidates = blueprint_library.filter("vehicle.tesla.model3")

    if not candidates:
        candidates = blueprint_library.filter("vehicle.*")

    blueprint = candidates[0]

    spawn_points = world.get_map().get_spawn_points()

    random.shuffle(spawn_points)

    for transform in spawn_points:
        vehicle = world.try_spawn_actor(blueprint, transform)

        if vehicle:
            print("Ego vehicle spawned:", vehicle.type_id)
            return vehicle

    raise RuntimeError("Could not spawn ego vehicle")


def spawn_vehicle_ahead(world, ego, distance_ahead=25.0):
    blueprint_library = world.get_blueprint_library()

    candidates = blueprint_library.filter("vehicle.*")

    blueprint = random.choice(candidates)

    ego_transform = ego.get_transform()

    forward = ego_transform.get_forward_vector()

    location = ego_transform.location + forward * distance_ahead

    transform = carla.Transform(
        location,
        ego_transform.rotation
    )

    vehicle = world.try_spawn_actor(blueprint, transform)

    if vehicle:
        vehicle.set_simulate_physics(True)

        print(
            "Stopped vehicle spawned:",
            vehicle.id,
            "distance:",
            distance_ahead
        )

    return vehicle


def spawn_bike(world, ego):
    blueprint_library = world.get_blueprint_library()

    bikes = (
        blueprint_library.filter("vehicle.bh.crossbike")
        or blueprint_library.filter("vehicle.*")
    )

    blueprint = random.choice(bikes)

    ego_transform = ego.get_transform()

    forward = ego_transform.get_forward_vector()
    right = ego_transform.get_right_vector()

    location = (
        ego_transform.location
        + forward * 25
        + right * 3
    )

    rotation = carla.Rotation(
        pitch=0,
        yaw=ego_transform.rotation.yaw + 90,
        roll=0
    )

    transform = carla.Transform(location, rotation)

    bike = world.try_spawn_actor(blueprint, transform)

    if bike:
        print("Two-wheeler spawned:", bike.id)

    return bike


def spawn_pedestrian(world, ego):
    blueprint_library = world.get_blueprint_library()

    walkers = blueprint_library.filter("walker.pedestrian.*")

    if not walkers:
        return None

    blueprint = random.choice(walkers)

    ego_transform = ego.get_transform()

    forward = ego_transform.get_forward_vector()
    right = ego_transform.get_right_vector()

    location = (
        ego_transform.location
        + forward * 25
        + right * 5
    )

    transform = carla.Transform(location)

    walker = world.try_spawn_actor(
        blueprint,
        transform
    )

    if walker:
        print("Pedestrian spawned:", walker.id)

    return walker


#This code block is used for seting up the simulation space/scenario.

def setup_scenario(world, ego, scenario):
    actors = []

    if scenario == "stopped_car":
        actor = spawn_vehicle_ahead(
            world,
            ego,
            25.0
        )

        if actor:
            actors.append(actor)

    elif scenario == "bike":
        actor = spawn_bike(world, ego)

        if actor:
            actors.append(actor)

    elif scenario == "pedestrian":
        actor = spawn_pedestrian(world, ego)

        if actor:
            actors.append(actor)

    elif scenario == "mixed":
        actor = spawn_vehicle_ahead(
            world,
            ego,
            30.0
        )

        if actor:
            actors.append(actor)

        actor = spawn_bike(world, ego)

        if actor:
            actors.append(actor)

        actor = spawn_pedestrian(world, ego)

        if actor:
            actors.append(actor)

    return actors


#This allows our system to evaluate risk and make decision based on on-road events

def evaluate_hazards(ego, actors):
    ego_speed = max(forward_speed(ego), 0.0)

    closest = None
    closest_distance = float("inf")

    for actor in actors:

        if not actor.is_alive:
            continue

        if not hasattr(actor, "get_transform"):
            continue

        in_front, dist = is_in_front(
            ego,
            actor
        )

        if not in_front:
            continue

        if dist < closest_distance:
            closest_distance = dist
            closest = actor

    if closest is None:
        return {
            "risk": "safe",
            "score": 0.0,
            "distance": None,
            "ttc": None,
            "brake": False,
        }

    # Estimate relative closing speed.
    relative_speed = ego_speed

    if hasattr(closest, "get_velocity"):
        other_velocity = closest.get_velocity()

        ego_velocity = ego.get_velocity()

        rel_x = ego_velocity.x - other_velocity.x
        rel_y = ego_velocity.y - other_velocity.y
        rel_z = ego_velocity.z - other_velocity.z

        relative_speed = math.sqrt(
            rel_x ** 2 +
            rel_y ** 2 +
            rel_z ** 2
        )

    if relative_speed > 0.1:
        ttc = closest_distance / relative_speed
    else:
        ttc = float("inf")

    # SAFAR-style risk classification.
    if closest_distance <= BRAKE_DISTANCE:
        risk = "critical"
        score = 1.0
        brake = True

    elif ttc <= CRITICAL_TTC:
        risk = "critical"
        score = 1.0
        brake = True

    elif ttc <= 3.0:
        risk = "high"
        score = 0.8
        brake = False

    elif closest_distance <= 25.0:
        risk = "medium"
        score = 0.5
        brake = False

    else:
        risk = "safe"
        score = 0.0
        brake = False

    return {
        "risk": risk,
        "score": score,
        "distance": closest_distance,
        "ttc": ttc,
        "brake": brake,
        "actor": closest,
    }


#Allows to manually manuevar the car

def control_vehicle(ego, keys, safety):
    control = ego.get_control()

#Applies emergency brakes based on assesed risk

    if safety["brake"]:
        control.throttle = 0.0
        control.brake = 1.0
        control.hand_brake = False

        ego.apply_control(control)

        return "SAFAR EMERGENCY BRAKE"

    #Manual  control


    control.throttle = 0.0
    control.brake = 0.0
    control.steer = 0.0

    if keys[pygame.K_w]:
        control.throttle = 0.65

    if keys[pygame.K_s]:
        control.brake = 0.7

    if keys[pygame.K_a]:
        control.steer = -0.35

    if keys[pygame.K_d]:
        control.steer = 0.35

    if keys[pygame.K_SPACE]:
        control.brake = 1.0

    ego.apply_control(control)

    return "MANUAL CONTROL"




def draw_text(screen, font, text, x, y):
    surface = font.render(
        text,
        True,
        (255, 255, 255)
    )

    screen.blit(surface, (x, y))


def update_hud(screen, font, safety, mode, ego):
    screen.fill((10, 10, 10))

    draw_text(
        screen,
        font,
        "SAFAR - Smart Autonomous Framework for Accident Reduction",
        20,
        20
    )

    draw_text(
        screen,
        font,
        "WASD = Drive | SPACE = Brake | ESC = Exit",
        20,
        60
    )

    draw_text(
        screen,
        font,
        "Control: " + mode,
        20,
        110
    )

    ego_speed = speed(ego) * 3.6

    draw_text(
        screen,
        font,
        "Ego speed: %.1f km/h" % ego_speed,
        20,
        150
    )

    risk = safety["risk"]

    draw_text(
        screen,
        font,
        "SAFAR Risk: " + risk.upper(),
        20,
        190
    )

    if safety["distance"] is not None:

        draw_text(
            screen,
            font,
            "Hazard distance: %.1f m"
            % safety["distance"],
            20,
            230
        )

    if safety["ttc"] is not None:

        if math.isinf(safety["ttc"]):
            ttc_text = "TTC: inf"
        else:
            ttc_text = "TTC: %.2f s" % safety["ttc"]

        draw_text(
            screen,
            font,
            ttc_text,
            20,
            270
        )

    if safety["brake"]:

        draw_text(
            screen,
            font,
            "!!! SAFAR OVERRIDE: EMERGENCY BRAKING !!!",
            20,
            330
        )

    pygame.display.flip()


# Main

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=[
            "stopped_car",
            "bike",
            "pedestrian",
            "mixed",
        ],
        default="stopped_car"
    )

    args = parser.parse_args()

    client, world = connect()

    ego = None
    scenario_actors = []

    pygame.init()

    screen = pygame.display.set_mode(
        (700, 400)
    )

    pygame.display.set_caption(
        "SAFAR CARLA Safety Test"
    )

    font = pygame.font.SysFont(
        "Arial",
        20
    )

    try:

        ego = spawn_ego(world)

        scenario_actors = setup_scenario(
            world,
            ego,
            args.scenario
        )

        print()
        print("=" * 60)
        print("SAFAR CARLA TEST")
        print("=" * 60)
        print("Scenario:", args.scenario)
        print("WASD  -> drive")
        print("SPACE -> manual brake")
        print("ESC   -> exit")
        print()
        print("SAFAR will automatically brake")
        print("when the detected hazard becomes critical.")
        print("=" * 60)

        clock = pygame.time.Clock()

        running = True

        while running:

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:
                        running = False

            keys = pygame.key.get_pressed()

            safety = evaluate_hazards(
                ego,
                scenario_actors
            )

            mode = control_vehicle(
                ego,
                keys,
                safety
            )

            update_hud(
                screen,
                font,
                safety,
                mode,
                ego
            )

            clock.tick(30)

    finally:

        print("Cleaning up SAFAR actors...")

        if ego and ego.is_alive:
            ego.destroy()

        for actor in scenario_actors:

            if actor and actor.is_alive:
                actor.destroy()

        pygame.quit()


if __name__ == "__main__":
    main()
