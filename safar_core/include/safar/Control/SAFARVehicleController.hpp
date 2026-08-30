#pragma once

#include "../Core/SAFARTypes.hpp"
#include "../Core/SAFARConfig.hpp"
#include "../Decision/SAFARDecisionEngine.hpp"

namespace safar {

class SAFARVehicleController {
public:
    explicit SAFARVehicleController(const SAFARConfig& config = SAFARConfig());

    // Generates final ControlCommand from DecisionResult and threat info
    ControlCommand generateCommand(
        const DecisionResult& decision,
        const ThreatAssessment& threat,
        const IMUData& ego_imu,
        uint64_t timestamp_us,
        uint32_t frame_id,
        float latency_ms
    );

    const SAFARConfig& getConfig() const { return config_; }

private:
    SAFARConfig config_;
};

} // namespace safar
