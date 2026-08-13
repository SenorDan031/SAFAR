#This code file/model defines the terms and data our system uses for threat detection.

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):       #These labels are used to term the CRITICALITY of the risk/threat.
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):        #These labels are used to define the actions executed by the system.
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
class RiskAssessment:     #This code file is used by the system to classify the risk and it's possible cause. 
    level: RiskLevel
    score: float
    reason: str


@dataclass
class Decision:         #This code is from where the system derives most of it's decision making capabilities.
    action: ActionType
    target_speed_mps: float
    brake: float
    throttle: float
    reason: str
