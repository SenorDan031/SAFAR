"""
SAFAR Pothole Safety Intelligence Module
Physics-Aware, ML-Classified Road Surface Analysis and Intervention System
"""

from .config import (
    CONFIDENCE_THRESHOLD,
    CLASS_ID_TO_LABEL,
    CLASS_LABEL_TO_ID
)
from .validation import PotholeDataValidator
from .classifier import PotholeClassifier, PotholeObservation
from .physics import PotholePhysicsEngine
from .path import PotholePathGeometry, PathIntersectionStatus
from .risk import PotholeRiskEngine, PotholeRiskAssessment, PotholeSeverity
from .decision import PotholeDecisionEngine, PotholeDecision, PotholeAction
from .speed_manager import PotholeSpeedManager, PotholeActionPlan
from .road_simulator import simulate_road

__all__ = [
    "PotholeDataValidator",
    "PotholeClassifier",
    "PotholeObservation",
    "PotholePhysicsEngine",
    "PotholePathGeometry",
    "PathIntersectionStatus",
    "PotholeRiskEngine",
    "PotholeRiskAssessment",
    "PotholeSeverity",
    "PotholeDecisionEngine",
    "PotholeDecision",
    "PotholeAction",
    "PotholeSpeedManager",
    "PotholeActionPlan",
    "simulate_road",
    "CONFIDENCE_THRESHOLD",
    "CLASS_ID_TO_LABEL",
    "CLASS_LABEL_TO_ID"
]
