#pragma once

#include "../Core/SAFARTypes.hpp"
#include "../Core/SAFARConfig.hpp"

namespace safar {

struct DecisionResult {
    DecisionAction action{DecisionAction::CONTINUE};
    std::string reason;
    float recommended_throttle{1.0f};
    float recommended_brake{0.0f};
    float recommended_steering{0.0f};
    bool emergency_stop{false};
};

class SAFARDecisionEngine {
public:
    explicit SAFARDecisionEngine(const SAFARConfig& config = SAFARConfig());

    // Evaluates safety policy based on ThreatAssessment and vehicle state
    DecisionResult decide(const ThreatAssessment& threat, const IMUData& ego_imu);

    const SAFARConfig& getConfig() const { return config_; }
    void setConfig(const SAFARConfig& config) { config_ = config; }

private:
    SAFARConfig config_;
};

} // namespace safar
