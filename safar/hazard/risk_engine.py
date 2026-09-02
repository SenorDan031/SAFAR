"""Backward-compatibility facade for safar.hazard.risk_engine."""

from safar.risk.risk_engine import HazardRiskEngine, RiskEngine

__all__ = ["HazardRiskEngine", "RiskEngine"]
