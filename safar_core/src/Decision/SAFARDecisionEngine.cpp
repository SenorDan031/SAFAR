#include "safar/Decision/SAFARDecisionEngine.hpp"
#include <algorithm>

namespace safar {

SAFARDecisionEngine::SAFARDecisionEngine(const SAFARConfig& config)
    : config_(config) {}

DecisionResult SAFARDecisionEngine::decide(const ThreatAssessment& threat, const IMUData& ego_imu) {
    DecisionResult result;

    switch (threat.state) {
        case ThreatState::CRITICAL:
            result.action = DecisionAction::BRAKE;
            result.reason = "CRITICAL IMMINENT COLLISION RISK";
            result.recommended_throttle = 0.0f;
            result.recommended_brake = config_.emergency_brake_value;
            result.emergency_stop = true;
            break;

        case ThreatState::HIGH:
            result.action = DecisionAction::BRAKE;
            result.reason = "HIGH HAZARD PROXIMITY — ACTIVE SLOWDOWN";
            result.recommended_throttle = 0.0f;
            result.recommended_brake = std::clamp((threat.threat_score - config_.threat_warn_threshold) * 2.0f, 0.40f, 0.85f);
            result.emergency_stop = false;
            break;

        case ThreatState::MEDIUM:
            result.action = DecisionAction::WARN;
            result.reason = "FORWARD HAZARD DETECTED — THROTTLE RESTRAINED";
            result.recommended_throttle = config_.warning_throttle_limit;
            result.recommended_brake = 0.0f;
            result.emergency_stop = false;
            break;

        case ThreatState::LOW:
            result.action = DecisionAction::MONITOR;
            result.reason = "DISTANT OBSTACLE MONITORED";
            result.recommended_throttle = 1.0f;
            result.recommended_brake = 0.0f;
            result.emergency_stop = false;
            break;

        default:
            result.action = DecisionAction::CONTINUE;
            result.reason = "PATH CLEAR";
            result.recommended_throttle = 1.0f;
            result.recommended_brake = 0.0f;
            result.emergency_stop = false;
            break;
    }

    return result;
}

} // namespace safar
