"""
SAFAR Simulator — Dynamic Random Entity Spawner Test
"""
from safar_simulator.entity_spawner import DynamicEntitySpawner, EntitySpawnerConfig, EntityClass

def test_entity_spawner():
    print("======================================================================")
    print(" TESTING DYNAMIC RANDOM ENTITY SPAWNER")
    print("======================================================================")

    # Test with 30 entities (Medium density)
    cfg = EntitySpawnerConfig(density_preset="MEDIUM", random_seed=42)
    spawner = DynamicEntitySpawner(cfg)

    # Pre-spawn
    for _ in range(cfg.target_entity_count):
        spawner.spawn_entity()

    assert len(spawner.entities) == 30, f"Expected 30 entities, got {len(spawner.entities)}"
    print(f" [PASS] Initialized {len(spawner.entities)} random moving entities around ego vehicle.")

    # Verify class distribution
    classes = {e.entity_class for e in spawner.entities.values()}
    print(f" [PASS] Spawned diverse entity classes: {[c.value for c in classes]}")
    assert len(classes) >= 3, "Entity spawner lacked class diversity!"

    # Simulate 5 seconds of movement @ 45 km/h
    for _ in range(150):
        entities = spawner.update(ego_speed_kmh=45.0, dt=0.033)

    assert len(entities) == 30, "Dynamic pool failed to maintain target entity count during movement!"
    print(" [PASS] Dynamic spawn/despawn pooling successfully maintained 30 active entities.")
    print("======================================================================")
    print(" DYNAMIC ENTITY SPAWNER TEST PASSED (100% SUCCESS)")
    print("======================================================================")

if __name__ == "__main__":
    test_entity_spawner()
