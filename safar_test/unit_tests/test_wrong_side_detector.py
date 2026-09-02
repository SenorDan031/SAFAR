from safar.core.models import Obstacle, RiskLevel, VehicleState
from safar.core.risk_engine import RiskEngine
from safar.road.lane_analyzer import LaneContext
from safar.road.wrong_side_detector import (
    VehicleRoadState,
    WrongSideDetector,
    WrongSideStatus,
)


def lane(lane_id):
    return LaneContext(road_id=1, lane_id=lane_id, lane_type="driving", lane_width_m=3.5, is_junction=False, heading_deg=0.0)


def state(object_id, lane_id, position, velocity, heading):
    return VehicleRoadState(object_id, lane(lane_id), position, velocity, heading)


def test_normal_same_direction_vehicle():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (8, 0), 0), state("car", 1, (30, 0), (5, 0), 0))
    assert result.status == WrongSideStatus.SAME_SIDE


def test_opposing_vehicle_in_its_correct_lane_is_adjacent():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (8, 0), 0), state("car", -1, (30, 0), (-8, 0), 180))
    assert result.status == WrongSideStatus.ADJACENT
    assert not result.path_conflict


def test_genuine_wrong_side_approaching_vehicle():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (8, 0), 0), state("car", 1, (30, 0), (-8, 0), 180))
    assert result.status == WrongSideStatus.WRONG_SIDE
    assert result.path_conflict


def test_wrong_side_vehicle_far_away_keeps_large_ttc():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (5, 0), 0), state("car", 1, (200, 0), (-5, 0), 180))
    assert result.status == WrongSideStatus.WRONG_SIDE
    assert result.ttc_s > 10.0


def test_wrong_side_vehicle_without_trajectory_conflict():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (0, 0), 0), state("car", 1, (30, 0), (5, 0), 180))
    assert result.status == WrongSideStatus.WRONG_SIDE
    assert not result.path_conflict
    assert result.ttc_s is None


def test_wrong_side_critical_ttc_reaches_existing_risk_engine():
    result = WrongSideDetector().classify(state("ego", 1, (0, 0), (12, 0), 0), state("car", 1, (10, 0), (-12, 0), 180))
    assessment = RiskEngine().assess(VehicleState(12), Obstacle("car", result.distance_m, result.relative_speed_mps, result.path_conflict))
    assert result.status == WrongSideStatus.WRONG_SIDE
    assert result.ttc_s < 1.5
    assert assessment.level == RiskLevel.CRITICAL
