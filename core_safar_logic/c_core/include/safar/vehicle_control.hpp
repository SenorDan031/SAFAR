#pragma once

#include "types.hpp"
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace safar {

class VehicleControl {
public:
    VehicleControl() = default;

    // Translates the decision and threat assessment into actuator control commands
    ControlResponse generateCommand(const DetectionFrame& frame,
                                    const ThreatAssessment& threat,
                                    DecisionAction decision,
                                    float latency_ms) const {
        ControlResponse resp;
        resp.timestamp_us = frame.timestamp_us;
        resp.frame_id = frame.frame_id;
        resp.threat_score = threat.threat_score;
        resp.decision = decision;
        resp.latency_ms = latency_ms;

        // Default baseline control (player/cruise maintains full throttle)
        resp.control.throttle = 1.0f;
        resp.control.brake = 0.0f;
        resp.control.steering = 0.0f;
        resp.control.emergency_stop = false;

        std::ostringstream msg;

        switch (decision) {
            case DecisionAction::CONTINUE:
                resp.control.throttle = 1.0f;
                resp.control.brake = 0.0f;
                resp.hud_message = "";
                break;

            case DecisionAction::WARN:
                resp.control.throttle = 1.0f;
                resp.control.brake = 0.0f;
                resp.hud_message = "";
                break;

            case DecisionAction::SLOWDOWN:
                // Reduce throttle and apply moderate braking intervention
                resp.control.throttle = 0.0f;
                resp.control.brake = std::clamp((threat.threat_score - 0.50f) * 1.5f, 0.25f, 0.60f);
                resp.hud_message = "";
                break;

            case DecisionAction::EMERGENCY_BRAKE:
                // Override throttle completely and apply full emergency braking
                resp.control.throttle = 0.0f;
                resp.control.brake = 1.0f;
                resp.control.emergency_stop = true;
                resp.hud_message = "";
                break;
        }

        return resp;
    }
};

} // namespace safar
