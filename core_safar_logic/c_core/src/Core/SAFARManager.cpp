#include "safar/Core/SAFARManager.hpp"
#include <iostream>

namespace safar {

uint64_t SAFARManager::getCurrentTimeUs() {
    auto now = std::chrono::high_resolution_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::microseconds>(now).count();
}

SAFARManager::SAFARManager(const SAFARConfig& config)
    : config_(config),
      tracking_(config),
      geometry_(config),
      threat_assessment_(config),
      decision_engine_(config),
      vehicle_controller_(config) {}

SAFARManager::~SAFARManager() {
    communication_.stopServer();
}

bool SAFARManager::initialize(int perception_port, int ue5_port) {
    return communication_.startServer([this](const std::vector<Detection>& detections, uint64_t timestamp_us) {
        processDetections(detections, timestamp_us);
    });
}

void SAFARManager::updateIMU(const IMUData& imu) {
    sensors_.getIMU().update(imu);
}

void SAFARManager::processDetections(const std::vector<Detection>& detections, uint64_t timestamp_us) {
    uint64_t t_start = getCurrentTimeUs();
    last_perception_time_us_ = t_start;

    IMUData ego_imu = sensors_.getIMU().getLatest();
    if (ego_imu.speed_mps <= 0.01f) {
        ego_imu.speed_mps = 12.0f; // Default baseline driving speed if IMU not yet streamed
    }

    ControlCommand cmd = evaluateStep(detections, ego_imu, timestamp_us);

    // Send control command to UE5
    communication_.sendControlCommand(cmd);
}

ControlCommand SAFARManager::evaluateStep(
    const std::vector<Detection>& detections,
    const IMUData& imu,
    uint64_t timestamp_us
) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    uint64_t t_start = getCurrentTimeUs();
    frame_counter_++;

    // 1. Multi-Object Tracking
    auto tracks = tracking_.update(detections, timestamp_us);

    // 2. Spatial Geometry & Corridor Evaluation
    geometry_.evaluateSpatialMetrics(tracks, imu, 0.033f);

    // 3. Explainable Threat Assessment
    latest_threat_ = threat_assessment_.assess(tracks, imu);

    // 4. Policy Decision Engine
    latest_decision_ = decision_engine_.decide(latest_threat_, imu);

    // 5. Vehicle Actuator Command Generation
    uint64_t t_end = getCurrentTimeUs();
    float latency_ms = static_cast<float>(t_end - t_start) / 1000.0f;

    latest_command_ = vehicle_controller_.generateCommand(
        latest_decision_,
        latest_threat_,
        imu,
        timestamp_us,
        frame_counter_,
        latency_ms
    );

    return latest_command_;
}

ControlCommand SAFARManager::checkWatchdogAndStep() {
    std::lock_guard<std::mutex> lock(state_mutex_);
    uint64_t now = getCurrentTimeUs();
    uint64_t last = last_perception_time_us_.load();

    if (last > 0 && (now - last) > (config_.watchdog_timeout_ms * 1000)) {
        // Failsafe condition: perception data is stale!
        latest_command_.failsafe_active = true;
        latest_command_.decision = DecisionAction::CONTINUE;
        latest_command_.throttle = 1.0f; // Return to manual/normal throttle
        latest_command_.brake = 0.0f;    // Disengage autonomous emergency brake
        latest_command_.emergency_brake = false;
        latest_command_.hud_status = "";

        // Broadcast failsafe release to vehicle
        communication_.sendControlCommand(latest_command_);
    }

    return latest_command_;
}

} // namespace safar
