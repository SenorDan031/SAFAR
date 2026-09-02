from safar.core.models import (
    VehicleState,
    Obstacle,
    RiskLevel,
)

from safar.core.risk_engine import RiskEngine


def test_irrelevant_obstacle_is_safe():
    engine = RiskEngine()

    vehicle = VehicleState(speed_mps=10.0)

    obstacle = Obstacle(
        obstacle_id="car_01",
        distance_m=10.0,
        relative_speed_mps=5.0,
        in_path=False,
    )

    result = engine.assess(vehicle, obstacle)

    assert result.level == RiskLevel.SAFE


def test_medium_risk():
    engine = RiskEngine()

    vehicle = VehicleState(speed_mps=10.0)

    obstacle = Obstacle(
        obstacle_id="car_01",
        distance_m=30.0,
        relative_speed_mps=10.0,
        in_path=True,
    )

    result = engine.assess(vehicle, obstacle)

    assert result.level == RiskLevel.MEDIUM


def test_critical_risk():
    engine = RiskEngine()

    vehicle = VehicleState(speed_mps=15.0)

    obstacle = Obstacle(
        obstacle_id="wall",
        distance_m=5.0,
        relative_speed_mps=5.0,
        in_path=True,
        object_type="wall",
    )

    result = engine.assess(vehicle, obstacle)

    assert result.level == RiskLevel.CRITICAL