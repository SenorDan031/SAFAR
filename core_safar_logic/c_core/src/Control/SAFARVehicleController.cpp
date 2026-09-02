#include "safar/Control/SAFARVehicleController.hpp"
#include <sstream>
#include <iomanip>

namespace safar {

SAFARVehicleController::SAFARVehicleController(const SAFARConfig& config)
    : config_(config) {}

ControlCommand SAFARVehicleController::generateCommand(
    const DecisionResult& decision,
    const ThreatAssessment& threat,
    const IMUData& ego_imu,
    uint64_t timestamp_us,
    uint32_t frame_id,
    float latency_ms
) {
    ControlCommand cmd;
    cmd.timestamp_us = timestamp_us;
    cmd.frame_id = frame_id;
    cmd.throttle = decision.recommended_throttle;
    cmd.brake = decision.recommended_brake;
    cmd.steering = decision.recommended_steering;
    cmd.emergency_brake = decision.emergency_stop;
    cmd.decision = decision.action;
    cmd.latency_ms = latency_ms;
    cmd.failsafe_active = false;
    cmd.hud_status = ""; // 100% clean gameplay: no debug print text
    return cmd;
}

} // namespace safar
