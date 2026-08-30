#pragma once

#include "../Core/SAFARTypes.hpp"
#include "../Core/SAFARConfig.hpp"
#include <vector>

namespace safar {

class SAFARThreatAssessment {
public:
    explicit SAFARThreatAssessment(const SAFARConfig& config = SAFARConfig());

    // Evaluates all tracked objects and computes global threat assessment
    ThreatAssessment assess(const std::vector<TrackedObject>& tracks, const IMUData& ego_imu);

    const SAFARConfig& getConfig() const { return config_; }
    void setConfig(const SAFARConfig& config) { config_ = config; }

private:
    float computeIndividualThreat(const TrackedObject& track, const IMUData& ego_imu) const;

    SAFARConfig config_;
};

} // namespace safar
