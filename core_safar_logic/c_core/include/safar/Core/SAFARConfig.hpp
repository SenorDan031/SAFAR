#pragma once

#include <cstdint>

namespace safar {

struct SAFARConfig {
    // Threat Thresholds (Configurable, transparent, explainable)
    float threat_monitor_threshold{0.25f};
    float threat_warn_threshold{0.50f};
    float threat_brake_threshold{0.75f};
    float threat_critical_threshold{0.88f};

    // Time-To-Collision (TTC) Policy Thresholds in seconds
    float ttc_warn_seconds{4.0f};
    float ttc_brake_seconds{2.2f};
    float ttc_critical_seconds{1.2f};

    // Ego Path Geometry (Trapezoidal corridor in normalized screen coordinates)
    float horizon_y{0.45f};
    float lane_width_top{0.16f};
    float lane_width_bottom{0.70f};

    // Visual Distance Approximation Model (focal ratio / box height)
    float camera_focal_length_px{700.0f};
    float nominal_vehicle_height_m{1.50f};
    float nominal_pedestrian_height_m{1.75f};

    // Tracking Parameters
    float max_association_distance_norm{0.18f};
    uint32_t max_missed_frames{5};
    uint32_t min_confirmation_frames{2};

    // Failsafe Watchdog Parameter (milliseconds)
    uint64_t watchdog_timeout_ms{250};

    // Actuator Limits & Safety Overrides
    float max_brake_pressure{1.0f};
    float warning_throttle_limit{0.40f};
    float emergency_brake_value{1.0f};
};

} // namespace safar
