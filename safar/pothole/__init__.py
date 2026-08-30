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
    "CONFIDENCE_THRESHOLD",
    "CLASS_ID_TO_LABEL",
    "CLASS_LABEL_TO_ID"
]
