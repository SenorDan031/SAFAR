"""Backward-compatibility facade for safar.hazard.models."""

from safar.risk.models import (
    DecisionState,
    VehicleSnapshot,
    PerceptionObject,
    HazardCandidate,
    HazardRiskAssessment,
    HazardDecision,
)

__all__ = [
    "DecisionState",
    "VehicleSnapshot",
    "PerceptionObject",
    "HazardCandidate",
    "HazardRiskAssessment",
    "HazardDecision",
]
