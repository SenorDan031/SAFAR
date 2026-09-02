"""Multi-threat priority arbitration between simultaneous hazards."""

from typing import List, Dict, Any, Optional
from safar.core.models import RiskLevel, RiskAssessment


class ThreatArbiter:
    """Arbitrates among vehicle, pedestrian, and pothole hazards to produce a single authoritative action."""

    PRIORITY = {
        RiskLevel.CRITICAL: 3,
        RiskLevel.HIGH: 2,
        RiskLevel.MEDIUM: 1,
        RiskLevel.SAFE: 0,
    }

    def arbitrate(self, assessments: List[RiskAssessment]) -> RiskAssessment:
        if not assessments:
            return RiskAssessment(RiskLevel.SAFE, 0.0, "Corridor clear.")
        return max(assessments, key=lambda a: (self.PRIORITY.get(a.level, 0), a.score))
