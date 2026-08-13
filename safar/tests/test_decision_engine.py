from safar.core.models import (
    Decision,
    RiskAssessment,
    RiskLevel,
    ActionType,
)

from safar.core.decision_engine import DecisionEngine


def test_safe_decision():
    engine = DecisionEngine()

    assessment = RiskAssessment(
        level=RiskLevel.SAFE,
        score=0.0,
        reason="No danger.",
    )

    decision = engine.decide(
        assessment,
        current_speed_mps=10.0,
    )

    assert decision.action == ActionType.NONE
    assert decision.brake == 0.0


def test_warning_decision():
    engine = DecisionEngine()

    assessment = RiskAssessment(
        level=RiskLevel.MEDIUM,
        score=0.5,
        reason="Developing hazard.",
    )

    decision = engine.decide(
        assessment,
        current_speed_mps=10.0,
    )

    assert decision.action == ActionType.WARN


def test_slowdown_decision():
    engine = DecisionEngine()

    assessment = RiskAssessment(
        level=RiskLevel.HIGH,
        score=0.8,
        reason="High collision risk.",
    )

    decision = engine.decide(
        assessment,
        current_speed_mps=10.0,
    )

    assert decision.action == ActionType.SLOWDOWN
    assert decision.brake > 0.0
    assert decision.target_speed_mps < 10.0


def test_emergency_braking():
    engine = DecisionEngine()

    assessment = RiskAssessment(
        level=RiskLevel.CRITICAL,
        score=1.0,
        reason="Immediate collision risk.",
    )

    decision = engine.decide(
        assessment,
        current_speed_mps=10.0,
    )

    assert decision.action == ActionType.EMERGENCY_BRAKE
    assert decision.brake == 1.0
    assert decision.target_speed_mps == 0.0