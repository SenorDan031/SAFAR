from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    NONE = "none"
    WARN = "warn"
    SLOWDOWN = "slowdown"
    EMERGENCY_BRAKE = "emergency_brake"


@dataclass
class VehicleState:
    speed_mps: float


@dataclass
class Obstacle:
    obstacle_id: str
    distance_m: float
    relative_speed_mps: float
    in_path: bool
    object_type: str = "vehicle"


@dataclass
class RiskAssessment:
    level: RiskLevel
    score: float
    reason: str


@dataclass
class Decision:
    action: ActionType
    target_speed_mps: float
    brake: float
    throttle: float
    reason: str