import carla


def main():
    print("=" * 60)
    print("SAFAR × CARLA CONNECTION TEST")
    print("=" * 60)

    print("\n[1] Importing CARLA...")
    print("    CARLA Python API imported successfully.")

    print("\n[2] Creating CARLA client...")
    client = carla.Client("localhost", 2000)

    print("[3] Setting timeout...")
    client.set_timeout(10.0)

    print("[4] Connecting to CARLA...")
    world = client.get_world()

    print("    Connection successful.")

    print("\n[5] Reading world information...")

    world_name = world.get_map().name
    actors = world.get_actors()

    print(f"    Map: {world_name}")
    print(f"    Actors: {len(actors)}")

    print("\n[6] Checking CARLA server version...")

    try:
        server_version = client.get_server_version()
        print(f"    Server version: {server_version}")
    except Exception as exc:
        print(f"    Could not read server version: {exc}")

    print("\n" + "=" * 60)
    print("CARLA CONNECTION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()