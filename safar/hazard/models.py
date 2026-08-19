"""Source-neutral models used by the SAFAR hazardous-object prototype."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class DecisionState(str, Enum):
    """Ordered, non-actuating states emitted by the prototype decision layer."""

    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    SLOWDOWN = "SLOWDOWN"
    EMERGENCY_BRAKE = "EMERGENCY_BRAKE"
    FAULT = "FAULT"


@dataclass(frozen=True)
class VehicleSnapshot:
    """Only vehicle data required for source-neutral hazard evaluation."""

    speed_kmh: float
    timestamp_s: float = 0.0


@dataclass(frozen=True)
class PerceptionObject:
    """A source-neutral observation; unavailable physical values stay ``None``."""

    object_id: str
    category: str
    confidence: float
    source: str
    in_path: bool
    distance_m: Optional[float] = None
    closing_speed_kmh: Optional[float] = None
    bbox: Optional[Tuple[int, int, int, int]] = None


@dataclass(frozen=True)
class HazardCandidate:
    """A relevant object enriched with temporal persistence information."""

    perception: PerceptionObject
    persistence_frames: int
    is_hazard: bool
    reason: str


@dataclass(frozen=True)
class HazardRiskAssessment:
    """Explainable risk result; unknown measurements remain explicitly unknown."""

    state: DecisionState
    hazard_id: Optional[str]
    reason: str
    distance_m: Optional[float]
    closing_speed_kmh: Optional[float]
    persistence_frames: int


@dataclass(frozen=True)
class HazardDecision:
    """Non-actuating command for a later, separate vehicle-control layer."""

    state: DecisionState
    action: str
    reason: str
    risk_level: str
