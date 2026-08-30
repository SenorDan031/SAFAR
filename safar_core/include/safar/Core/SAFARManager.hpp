#pragma once

#include "SAFARTypes.hpp"
#include "SAFARConfig.hpp"
#include "../Sensors/SAFARSensorManager.hpp"
#include "../Tracking/SAFARTracking.hpp"
#include "../Geometry/SAFARGeometry.hpp"
#include "../Threat/SAFARThreatAssessment.hpp"
#include "../Decision/SAFARDecisionEngine.hpp"
#include "../Control/SAFARVehicleController.hpp"
#include "../Communication/SAFARCommunication.hpp"

#include <chrono>
#include <mutex>
#include <atomic>

namespace safar {

class SAFARManager {
public:
    explicit SAFARManager(const SAFARConfig& config = SAFARConfig());
    ~SAFARManager();

    bool initialize(int perception_port = 9002, int ue5_port = 9003);
    void updateIMU(const IMUData& imu);
    void processDetections(const std::vector<Detection>& detections, uint64_t timestamp_us);

    // Watchdog check called periodically
    ControlCommand checkWatchdogAndStep();

    // Direct synchronous evaluation for unit testing / mock testing
    ControlCommand evaluateStep(const std::vector<Detection>& detections, const IMUData& imu, uint64_t timestamp_us);

    const ThreatAssessment& getLatestThreat() const { return latest_threat_; }
    const DecisionResult& getLatestDecision() const { return latest_decision_; }
    const std::vector<TrackedObject>& getActiveTracks() const { return tracking_.getActiveTracks(); }
    const SAFARConfig& getConfig() const { return config_; }

    static uint64_t getCurrentTimeUs();

private:
    SAFARConfig config_;
    SAFARSensorManager sensors_;
    SAFARTracking tracking_;
    SAFARGeometry geometry_;
    SAFARThreatAssessment threat_assessment_;
    SAFARDecisionEngine decision_engine_;
    SAFARVehicleController vehicle_controller_;
    SAFARCommunication communication_;

    std::mutex state_mutex_;
    ThreatAssessment latest_threat_;
    DecisionResult latest_decision_;
    ControlCommand latest_command_;
    uint32_t frame_counter_{0};
    std::atomic<uint64_t> last_perception_time_us_{0};
};

} // namespace safar
