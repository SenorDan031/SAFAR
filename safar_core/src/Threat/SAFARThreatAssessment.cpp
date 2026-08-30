#include "safar/Threat/SAFARThreatAssessment.hpp"
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace safar {

SAFARThreatAssessment::SAFARThreatAssessment(const SAFARConfig& config)
    : config_(config) {}

float SAFARThreatAssessment::computeIndividualThreat(const TrackedObject& track, const IMUData& ego_imu) const {
    if (!track.in_ego_path) {
        // Off-path obstacles in adjacent lanes/sidewalks receive minimal threat
        return 0.10f * std::clamp(1.0f - track.estimated_distance_m / 30.0f, 0.0f, 1.0f);
    }

    // Dynamic Stopping Distance Calculation: d_stop = v * t_react + v^2 / (2 * a)
    float v_mps = std::max(0.0f, ego_imu.speed_mps);
    float d_stop = (v_mps * 0.20f) + ((v_mps * v_mps) / (2.0f * 8.0f));

    // 1. Proximity vs Stopping Distance Factor
    float safety_ratio = track.estimated_distance_m / std::max(3.0f, d_stop);
    float proximity_factor = std::clamp(1.30f - safety_ratio, 0.0f, 1.0f);

    // 2. TTC Risk Factor (0.0 if TTC > 5s, 1.0 if TTC < 1.5s)
    float ttc_factor = 0.0f;
    if (track.ttc_seconds < 6.0f) {
        ttc_factor = std::clamp((4.5f - track.ttc_seconds) / 3.5f, 0.0f, 1.0f);
    }

    // 3. Lane Centeredness (1.0 at center, 0.6 at edge)
    float center_factor = 1.0f - std::clamp(std::abs(track.lateral_offset), 0.0f, 1.0f) * 0.4f;

    // 4. Ego Speed Amplification
    float speed_factor = std::clamp(ego_imu.speed_mps / 15.0f, 0.6f, 1.3f);

    // 5. Confidence Weight
    float conf_factor = std::clamp(track.confidence, 0.5f, 1.0f);

    // Combined explainable formula:
    // Threat = (Proximity * 0.50 + TTC * 0.50) * Centeredness * Speed * Confidence
    float raw_score = (proximity_factor * 0.50f + ttc_factor * 0.50f) * center_factor * speed_factor * conf_factor;
    
    // Guaranteed Critical escalation if distance <= 1.15 * d_stop
    if (track.estimated_distance_m <= (1.15f * d_stop) || (track.ttc_seconds <= 2.0f && track.estimated_distance_m <= 25.0f)) {
        raw_score = std::max(raw_score, 0.88f);
    }

    return std::clamp(raw_score, 0.0f, 1.0f);
}

ThreatAssessment SAFARThreatAssessment::assess(const std::vector<TrackedObject>& tracks, const IMUData& ego_imu) {
    ThreatAssessment result;
    result.state = ThreatState::LOW;
    result.threat_score = 0.0f;
    result.primary_hazard_id = -1;
    result.primary_hazard_class = "none";
    result.min_ttc_seconds = 999.0f;
    result.primary_hazard_distance_m = 100.0f;
    result.explanation = "Ego path is clear";

    if (tracks.empty()) {
        return result;
    }

    float max_threat = 0.0f;
    const TrackedObject* worst_obj = nullptr;

    for (const auto& trk : tracks) {
        float score = computeIndividualThreat(trk, ego_imu);
        if (score > max_threat) {
            max_threat = score;
            worst_obj = &trk;
        }
    }

    if (worst_obj != nullptr && max_threat > 0.05f) {
        result.threat_score = max_threat;
        result.primary_hazard_id = worst_obj->tracking_id;
        result.primary_hazard_class = worst_obj->class_name;
        result.min_ttc_seconds = worst_obj->ttc_seconds;
        result.primary_hazard_distance_m = worst_obj->estimated_distance_m;

        // Map numeric threat score to explainable discrete ThreatState
        if (max_threat >= config_.threat_critical_threshold || result.min_ttc_seconds <= config_.ttc_critical_seconds) {
            result.state = ThreatState::CRITICAL;
        } else if (max_threat >= config_.threat_brake_threshold || result.min_ttc_seconds <= config_.ttc_brake_seconds) {
            result.state = ThreatState::HIGH;
        } else if (max_threat >= config_.threat_warn_threshold || result.min_ttc_seconds <= config_.ttc_warn_seconds) {
            result.state = ThreatState::MEDIUM;
        } else if (max_threat >= config_.threat_monitor_threshold) {
            result.state = ThreatState::LOW;
        }

        std::ostringstream ss;
        ss << worst_obj->class_name << " #" << worst_obj->tracking_id 
           << " at " << std::fixed << std::setprecision(1) << worst_obj->estimated_distance_m << "m"
           << " (TTC: " << std::fixed << std::setprecision(1) << worst_obj->ttc_seconds << "s)";
        result.explanation = ss.str();
    }

    return result;
}

} // namespace safar
