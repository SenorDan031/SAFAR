import carla
import math


def distance(a, b):
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2 +
        (a.z - b.z) ** 2
    )


def main():
    print("=" * 60)
    print("SAFAR × CARLA PERCEPTION TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # Connect to CARLA
    # ---------------------------------------------------------

    print("\n[1] Connecting to CARLA...")

    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)

    world = client.get_world()

    print("    Connected.")
    print(f"    Map: {world.get_map().name}")

    # ---------------------------------------------------------
    # Find vehicles
    # ---------------------------------------------------------

    print("\n[2] Searching for vehicles...")

    vehicles = world.get_actors().filter("vehicle.*")

    print(f"    Vehicles found: {len(vehicles)}")

    if len(vehicles) == 0:
        print("\nWARNING: No vehicles currently exist in CARLA.")
        print("Spawn an ego vehicle before continuing.")
        return

    # ---------------------------------------------------------
    # Select an ego vehicle
    # ---------------------------------------------------------

    ego = vehicles[0]

    print("\n[3] Using vehicle as ego vehicle...")

    print(f"    Actor ID: {ego.id}")
    print(f"    Type: {ego.type_id}")

    # ---------------------------------------------------------
    # Vehicle state
    # ---------------------------------------------------------

    transform = ego.get_transform()
    velocity = ego.get_velocity()
    acceleration = ego.get_acceleration()

    speed_ms = math.sqrt(
        velocity.x ** 2 +
        velocity.y ** 2 +
        velocity.z ** 2
    )

    speed_kmh = speed_ms * 3.6

    acceleration_ms2 = math.sqrt(
        acceleration.x ** 2 +
        acceleration.y ** 2 +
        acceleration.z ** 2
    )

    print("\n[4] Ego vehicle state")

    print(f"    Location:")
    print(f"        X: {transform.location.x:.2f}")
    print(f"        Y: {transform.location.y:.2f}")
    print(f"        Z: {transform.location.z:.2f}")

    print(f"\n    Rotation:")
    print(f"        Pitch: {transform.rotation.pitch:.2f}")
    print(f"        Yaw:   {transform.rotation.yaw:.2f}")
    print(f"        Roll:  {transform.rotation.roll:.2f}")

    print(f"\n    Speed:")
    print(f"        {speed_ms:.2f} m/s")
    print(f"        {speed_kmh:.2f} km/h")

    print(f"\n    Acceleration:")
    print(f"        {acceleration_ms2:.2f} m/s²")

    # ---------------------------------------------------------
    # Nearby vehicles
    # ---------------------------------------------------------

    print("\n[5] Detecting nearby vehicles...")

    nearby = []

    ego_location = transform.location

    for vehicle in vehicles:
        if vehicle.id == ego.id:
            continue

        vehicle_location = vehicle.get_transform().location
        dist = distance(ego_location, vehicle_location)

        if dist <= 50.0:
            nearby.append((vehicle, dist))

    print(f"    Nearby vehicles within 50m: {len(nearby)}")

    for vehicle, dist in nearby:
        print(
            f"        ID={vehicle.id} "
            f"type={vehicle.type_id} "
            f"distance={dist:.2f}m"
        )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("CARLA PERCEPTION SMOKE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()