"""
SAFAR Core Safety Intelligence Platform
Contains the high-performance C++ calculation engine, Python perception layer,
and complete pothole/road surface safety subsystem.
"""

from .risk_engine import RiskEngine, HazardRiskEngine, calculate_ttc_s
from .decision_engine import DecisionEngine, ThreatArbiter, HazardPolicy
from .pothole_system import PotholeSpeedManager, PotholeClassifier, simulate_road

__all__ = [
    "RiskEngine",
    "HazardRiskEngine",
    "calculate_ttc_s",
    "DecisionEngine",
    "ThreatArbiter",
    "HazardPolicy",
    "PotholeSpeedManager",
    "PotholeClassifier",
    "simulate_road",
]
