#pragma once

#include "types.hpp"

namespace safar {

class DecisionEngine {
public:
    explicit DecisionEngine(float warn_threshold = 0.40f,
                            float slowdown_threshold = 0.65f,
                            float emergency_threshold = 0.85f)
        : warn_thresh_(warn_threshold),
          slowdown_thresh_(slowdown_threshold),
          emergency_thresh_(emergency_threshold) {}

    // Deterministically maps a threat assessment to a high-level safety decision
    DecisionAction decide(const ThreatAssessment& assessment) const {
        if (!assessment.in_path || assessment.threat_score < warn_thresh_) {
            return DecisionAction::CONTINUE;
        }

        if (assessment.threat_score >= emergency_thresh_) {
            return DecisionAction::EMERGENCY_BRAKE;
        }

        if (assessment.threat_score >= slowdown_thresh_) {
            return DecisionAction::SLOWDOWN;
        }

        return DecisionAction::WARN;
    }

private:
    float warn_thresh_;
    float slowdown_thresh_;
    float emergency_thresh_;
};

} // namespace safar
