#pragma once

#include "types.hpp"
#include "geometry.hpp"
#include <algorithm>
#include <cmath>

namespace safar {

class ThreatEngine {
public:
    explicit ThreatEngine(const EgoPathGeometry& geometry = EgoPathGeometry())
        : geometry_(geometry) {}

    // Evaluates a detection frame and returns the highest priority threat
    ThreatAssessment assess(const DetectionFrame& frame) {
        ThreatAssessment result;
        result.threat_score = 0.0f;
        result.in_path = false;
        result.lead_track_id = -1;
        result.lead_class = "none";
        result.reason = "Path clear";

        if (frame.detections.empty()) {
            return result;
        }

        float max_threat = 0.0f;
        const Detection* worst_hazard = nullptr;
        float worst_offset = 0.0f;

        for (const auto& det : frame.detections) {
            float lateral_offset = 0.0f;
            bool in_corridor = geometry_.isBoxInPath(det.bbox, lateral_offset);

            if (!in_corridor) {
                continue; // Ignore obstacles in adjacent lanes/off-road for forward hazard
            }

            // Proximity heuristic: In camera projection, lower on screen (larger bottom_y) means closer to vehicle
            float proximity_factor = std::clamp((det.bottom_y - geometry_.getConfig().horizon_y) / 
                                                (1.0f - geometry_.getConfig().horizon_y), 0.0f, 1.0f);

            // Size heuristic: Larger bounding box area indicates closer obstacle
            float size_factor = std::clamp(det.bbox.area() * 4.0f, 0.0f, 1.0f);

            // Centeredness heuristic: closer to lane center gives higher relevance
            float center_factor = 1.0f - std::clamp(std::abs(lateral_offset), 0.0f, 1.0f) * 0.4f;

            // Speed amplification: higher ego speed increases risk for the same forward object
            float speed_factor = std::clamp(frame.ego_speed_mps / 25.0f, 0.5f, 1.5f);

            // Combined Threat Score
            float score = (proximity_factor * 0.60f + size_factor * 0.40f) * center_factor * speed_factor;
            score = std::clamp(score, 0.0f, 1.0f);

            if (score > max_threat) {
                max_threat = score;
                worst_hazard = &det;
                worst_offset = lateral_offset;
            }
        }

        if (worst_hazard != nullptr) {
            result.threat_score = max_threat;
            result.in_path = true;
            result.path_lateral_offset = worst_offset;
            result.lead_track_id = worst_hazard->track_id;
            result.lead_class = worst_hazard->class_name;

            if (max_threat >= 0.85f) {
                result.reason = "Imminent forward obstacle";
            } else if (max_threat >= 0.60f) {
                result.reason = "Closing obstacle in path";
            } else if (max_threat >= 0.35f) {
                result.reason = "Forward vehicle detected";
            } else {
                result.reason = "Distant object in lane";
            }
        }

        return result;
    }

private:
    EgoPathGeometry geometry_;
};

} // namespace safar
