#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <cmath>

namespace safar {

enum class CameraID : uint8_t {
    FRONT = 0,
    LEFT = 1,
    RIGHT = 2
};

inline std::string toString(CameraID cam) {
    switch (cam) {
        case CameraID::FRONT: return "FRONT";
        case CameraID::LEFT: return "LEFT";
        case CameraID::RIGHT: return "RIGHT";
        default: return "UNKNOWN";
    }
}

enum class ThreatState : uint8_t {
    LOW = 0,
    MEDIUM = 1,
    HIGH = 2,
    CRITICAL = 3
};

inline std::string toString(ThreatState state) {
    switch (state) {
        case ThreatState::LOW: return "LOW";
        case ThreatState::MEDIUM: return "MEDIUM";
        case ThreatState::HIGH: return "HIGH";
        case ThreatState::CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

enum class DecisionAction : uint8_t {
    CONTINUE = 0,
    MONITOR = 1,
    WARN = 2,
    BRAKE = 3,
    STEER = 4
};

inline std::string toString(DecisionAction action) {
    switch (action) {
        case DecisionAction::CONTINUE: return "CONTINUE";
        case DecisionAction::MONITOR: return "MONITOR";
        case DecisionAction::WARN: return "WARN";
        case DecisionAction::BRAKE: return "BRAKE";
        case DecisionAction::STEER: return "STEER";
        default: return "UNKNOWN";
    }
}

inline DecisionAction parseDecisionAction(const std::string& str) {
    if (str == "MONITOR") return DecisionAction::MONITOR;
    if (str == "WARN") return DecisionAction::WARN;
    if (str == "BRAKE") return DecisionAction::BRAKE;
    if (str == "STEER") return DecisionAction::STEER;
    return DecisionAction::CONTINUE;
}

struct Vector3D {
    float x{0.0f};
    float y{0.0f};
    float z{0.0f};

    float length() const { return std::sqrt(x * x + y * y + z * z); }
    float length2D() const { return std::sqrt(x * x + y * y); }
};

struct Rotator3D {
    float pitch{0.0f};
    float yaw{0.0f};
    float roll{0.0f};
};

struct IMUData {
    uint64_t timestamp_us{0};
    Vector3D position;
    Rotator3D rotation;
    Vector3D velocity;
    float speed_mps{0.0f};
    Vector3D acceleration;
    Vector3D angular_velocity;
};

struct BoundingBox2D {
    float xmin{0.0f};
    float ymin{0.0f};
    float xmax{0.0f};
    float ymax{0.0f};

    float centerX() const { return (xmin + xmax) * 0.5f; }
    float centerY() const { return (ymin + ymax) * 0.5f; }
    float bottomY() const { return ymax; }
    float width() const { return xmax - xmin; }
    float height() const { return ymax - ymin; }
    float area() const { return width() * height(); }
};

struct Detection {
    uint64_t timestamp_us{0};
    CameraID camera_id{CameraID::FRONT};
    int class_id{0};
    std::string class_name{"unknown"};
    float confidence{0.0f};
    BoundingBox2D bbox;
    float center_x{0.0f};
    float bottom_y{0.0f};
};

struct TrackedObject {
    int tracking_id{0};
    CameraID camera_id{CameraID::FRONT};
    std::string class_name{"unknown"};
    float confidence{0.0f};
    BoundingBox2D bbox;
    float estimated_distance_m{100.0f};
    float relative_velocity_mps{0.0f};
    float ttc_seconds{999.0f};
    float lateral_offset{0.0f};
    bool in_ego_path{false};
    uint32_t age_frames{0};
    uint32_t missed_frames{0};
    uint64_t last_seen_us{0};
};

struct ThreatAssessment {
    ThreatState state{ThreatState::LOW};
    float threat_score{0.0f}; // 0.0 to 1.0
    int primary_hazard_id{-1};
    std::string primary_hazard_class{"none"};
    float min_ttc_seconds{999.0f};
    float primary_hazard_distance_m{100.0f};
    std::string explanation{"Path clear"};
};

struct ControlCommand {
    uint64_t timestamp_us{0};
    uint32_t frame_id{0};
    float throttle{1.0f};          // 0.0 to 1.0
    float brake{0.0f};             // 0.0 to 1.0
    float steering{0.0f};          // -1.0 to 1.0
    bool emergency_brake{false};
    DecisionAction decision{DecisionAction::CONTINUE};
    std::string hud_status{"SAFAR: ACTIVE"};
    float latency_ms{0.0f};
    bool failsafe_active{false};
};

struct GroundTruthObject {
    int actor_id{0};
    std::string class_name;
    Vector3D world_position;
    Vector3D relative_position;
    float actual_distance_m{0.0f};
    Vector3D world_velocity;
    float actual_closing_speed_mps{0.0f};
    float actual_ttc_seconds{999.0f};
};

struct ValidationMetrics {
    float distance_error_m{0.0f};
    float distance_error_pct{0.0f};
    float ttc_error_seconds{0.0f};
    bool detection_matched{false};
};

} // namespace safar
