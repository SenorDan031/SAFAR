#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace safar {

enum class DecisionAction {
    CONTINUE,
    WARN,
    SLOWDOWN,
    EMERGENCY_BRAKE
};

inline std::string toString(DecisionAction action) {
    switch (action) {
        case DecisionAction::CONTINUE: return "CONTINUE";
        case DecisionAction::WARN: return "WARN";
        case DecisionAction::SLOWDOWN: return "SLOWDOWN";
        case DecisionAction::EMERGENCY_BRAKE: return "EMERGENCY_BRAKE";
        default: return "UNKNOWN";
    }
}

inline DecisionAction parseDecisionAction(const std::string& str) {
    if (str == "WARN") return DecisionAction::WARN;
    if (str == "SLOWDOWN") return DecisionAction::SLOWDOWN;
    if (str == "EMERGENCY_BRAKE") return DecisionAction::EMERGENCY_BRAKE;
    return DecisionAction::CONTINUE;
}

struct BoundingBox {
    float xmin{0.0f};
    float ymin{0.0f};
    float xmax{0.0f};
    float ymax{0.0f};

    float centerX() const { return (xmin + xmax) * 0.5f; }
    float bottomY() const { return ymax; }
    float width() const { return xmax - xmin; }
    float height() const { return ymax - ymin; }
    float area() const { return width() * height(); }
};

struct Detection {
    int track_id{0};
    std::string class_name{"unknown"};
    float confidence{0.0f};
    BoundingBox bbox;
    float center_x{0.0f};
    float bottom_y{0.0f};
};

struct DetectionFrame {
    uint64_t timestamp_us{0};
    uint32_t frame_id{0};
    float ego_speed_mps{0.0f};
    std::vector<Detection> detections;
};

struct ThreatAssessment {
    float threat_score{0.0f}; // 0.0 (Safe) to 1.0 (Critical)
    bool in_path{false};
    float path_lateral_offset{0.0f};
    int lead_track_id{-1};
    std::string lead_class{"none"};
    std::string reason{"No obstacles detected"};
};

struct VehicleActuatorControl {
    float throttle{1.0f};     // 0.0 to 1.0
    float brake{0.0f};        // 0.0 to 1.0
    float steering{0.0f};     // -1.0 to 1.0
    bool emergency_stop{false};
};

struct ControlResponse {
    uint64_t timestamp_us{0};
    uint32_t frame_id{0};
    float threat_score{0.0f};
    DecisionAction decision{DecisionAction::CONTINUE};
    VehicleActuatorControl control;
    std::string hud_message;
    float latency_ms{0.0f};
};

struct EgoPathConfig {
    float horizon_y{0.45f};       // Vertical horizon line in normalized coords
    float bottom_width{0.70f};    // Lane width at the bottom of the image (y=1.0)
    float top_width{0.16f};       // Lane width at the horizon (y=horizon_y)
};

} // namespace safar
