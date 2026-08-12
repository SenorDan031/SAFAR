"""Run SAFAR's risk engine and decision engine in live CARLA scenarios."""

import argparse
import math
import time

import carla

from safar.core.decision_engine import DecisionEngine
from safar.core.models import Obstacle, VehicleState
from safar.core.risk_engine import RiskEngine
from safar.vehicle.carla_adapter import to_carla_control
from safar.vehicle.manual_controller import KeyboardController
from safar.vehicle.safety_override import SafetyOverride


# CARLA 0.9.15 on this Windows setup listens on IPv4, not IPv6 localhost.
HOST = "127.0.0.1"
PORT = 2000
SCENARIO_SECONDS = 25
LEAD_GAP_M = 25.0
MANUAL_LEAD_GAP_M = 45.0


def speed_mps(vehicle):
    velocity = vehicle.get_velocity()
    return math.sqrt(
        velocity.x ** 2
        + velocity.y ** 2
        + velocity.z ** 2
    )


def distance_m(first_vehicle, second_vehicle):
    return first_vehicle.get_location().distance(
        second_vehicle.get_location()
    )


def closing_speed_mps(ego, lead):
    """Return the ego speed component directed toward the lead vehicle."""
    ego_location = ego.get_location()
    lead_location = lead.get_location()
    delta_x = lead_location.x - ego_location.x
    delta_y = lead_location.y - ego_location.y
    separation = math.sqrt(delta_x ** 2 + delta_y ** 2)
    if separation == 0.0:
        return 0.0

    ego_velocity = ego.get_velocity()
    lead_velocity = lead.get_velocity()
    relative_velocity_x = ego_velocity.x - lead_velocity.x
    relative_velocity_y = ego_velocity.y - lead_velocity.y
    return max(
        0.0,
        (relative_velocity_x * delta_x + relative_velocity_y * delta_y) / separation,
    )


def set_role_name(blueprint, role_name):
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", role_name)


def spawn_scenario(world, lead_gap_m=LEAD_GAP_M):
    """Spawn a SAFAR ego vehicle behind a stopped lead vehicle."""
    blueprints = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()

    if not spawn_points:
        raise RuntimeError("The current CARLA map has no vehicle spawn points.")

    for spawn_transform in spawn_points:
        ego_blueprint = blueprints.filter("vehicle.tesla.model3")[0]
        set_role_name(ego_blueprint, "safar_ego")

        ego = world.try_spawn_actor(ego_blueprint, spawn_transform)
        if ego is None:
            continue

        forward = spawn_transform.get_forward_vector()
        lead_location = carla.Location(
            x=spawn_transform.location.x + forward.x * lead_gap_m,
            y=spawn_transform.location.y + forward.y * lead_gap_m,
            z=spawn_transform.location.z + 0.5,
        )

        lead_transform = carla.Transform(
            lead_location,
            spawn_transform.rotation,
        )

        lead_blueprint = blueprints.filter("vehicle.tesla.model3")[0]
        set_role_name(lead_blueprint, "safar_lead")

        lead = world.try_spawn_actor(lead_blueprint, lead_transform)

        if lead is not None:
            return ego, lead

        ego.destroy()

    raise RuntimeError(
        "Could not find a valid road location for both SAFAR vehicles."
    )


def follow_ego_vehicle(world, ego):
    """Move CARLA's spectator camera behind the ego vehicle."""
    transform = ego.get_transform()

    camera_location = (
        transform.location
        - transform.get_forward_vector() * 8
        + carla.Location(z=4)
    )

    world.get_spectator().set_transform(
        carla.Transform(
            camera_location,
            carla.Rotation(
                pitch=-15,
                yaw=transform.rotation.yaw,
                roll=0,
            ),
        )
    )


def assess_lead(risk_engine, decision_engine, ego, lead):
    ego_speed = speed_mps(ego)
    gap = distance_m(ego, lead)
    obstacle = Obstacle(
        obstacle_id=str(lead.id),
        distance_m=gap,
        relative_speed_mps=closing_speed_mps(ego, lead),
        in_path=True,
        object_type="vehicle",
    )
    assessment = risk_engine.assess(VehicleState(speed_mps=ego_speed), obstacle)
    return ego_speed, gap, assessment, decision_engine.decide(assessment, ego_speed)


def run_automatic_scenario():
    client = carla.Client(HOST, PORT)
    client.set_timeout(10.0)

    world = client.get_world()
    risk_engine = RiskEngine()
    decision_engine = DecisionEngine()

    ego = None
    lead = None

    try:
        ego, lead = spawn_scenario(world)

        # The lead vehicle is deliberately stationary.
        lead.apply_control(
            carla.VehicleControl(
                throttle=0.0,
                brake=1.0,
                hand_brake=True,
            )
        )

        print("SAFAR scenario started.")
        print("Ego vehicle is approaching a stopped lead vehicle.")
        print("Press Ctrl+C to stop early.\n")

        start_time = time.time()

        while time.time() - start_time < SCENARIO_SECONDS:
            ego_speed, gap, assessment, decision = assess_lead(
                risk_engine, decision_engine, ego, lead
            )

            ego.apply_control(
                carla.VehicleControl(
                    throttle=decision.throttle,
                    brake=decision.brake,
                )
            )

            follow_ego_vehicle(world, ego)

            print(
                "Distance={:.1f}m | Ego={:.1f}m/s | "
                "Risk={} | Action={} | {}".format(
                    gap,
                    ego_speed,
                    assessment.level.value,
                    decision.action.value,
                    decision.reason,
                )
            )

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nScenario stopped by user.")

    finally:
        if ego is not None:
            ego.destroy()

        if lead is not None:
            lead.destroy()

        print("SAFAR vehicles cleaned up.")


def run_manual_drive_scenario():
    """Let a driver control the ego vehicle while SAFAR enforces braking."""
    client = carla.Client(HOST, PORT)
    client.set_timeout(10.0)
    world = client.get_world()
    risk_engine = RiskEngine()
    decision_engine = DecisionEngine()
    safety_override = SafetyOverride()
    keyboard = None
    ego = None
    lead = None
    override_was_active = False

    try:
        ego, lead = spawn_scenario(world, MANUAL_LEAD_GAP_M)
        lead.apply_control(carla.VehicleControl(brake=1.0, hand_brake=True))
        keyboard = KeyboardController()
        print("SAFAR manual-drive scenario started.")
        print("Click the SAFAR Manual Drive window, then use W/S/A/D/SPACE. ESC quits.\n")

        while True:
            manual_control = keyboard.poll(speed_mps(ego))
            if manual_control is None:
                break

            ego_speed, gap, assessment, decision = assess_lead(
                risk_engine, decision_engine, ego, lead
            )
            result = safety_override.apply(manual_control, decision)
            ego.apply_control(to_carla_control(result.control, carla))
            follow_ego_vehicle(world, ego)

            print(
                "Speed={:.1f}m/s | Distance={:.1f}m | Risk={} | Action={}".format(
                    ego_speed, gap, assessment.level.value, decision.action.value
                )
            )
            if result.active and not override_was_active:
                print(">>> SAFAR SAFETY OVERRIDE ACTIVE <<<")
            elif override_was_active and not result.active:
                print(">>> Manual control restored <<<")
            override_was_active = result.active
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nScenario stopped by user.")
    finally:
        if keyboard is not None:
            keyboard.close()
        if ego is not None:
            ego.destroy()
        if lead is not None:
            lead.destroy()
        print("SAFAR vehicles cleaned up.")


def main():
    parser = argparse.ArgumentParser(description="Run SAFAR CARLA scenarios.")
    parser.add_argument(
        "--scenario",
        choices=("automatic", "manual_drive"),
        default="automatic",
        help="Scenario to launch (default: automatic).",
    )
    args = parser.parse_args()
    if args.scenario == "manual_drive":
        run_manual_drive_scenario()
    else:
        run_automatic_scenario()


if __name__ == "__main__":
    main()
