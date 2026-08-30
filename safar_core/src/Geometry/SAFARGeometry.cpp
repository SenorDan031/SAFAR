#include "safar/Geometry/SAFARGeometry.hpp"
#include <algorithm>
#include <cmath>

namespace safar {

SAFARGeometry::SAFARGeometry(const SAFARConfig& config)
    : config_(config) {}

bool SAFARGeometry::isBoxInEgoCorridor(const BoundingBox2D& bbox, float& out_lateral_offset) const {
    float x = bbox.centerX();
    float y = bbox.bottomY();

    if (y < config_.horizon_y || y > 1.0f) {
        out_lateral_offset = 1.0f;
        return false;
    }

    float t = (y - config_.horizon_y) / (1.0f - config_.horizon_y);
    t = std::clamp(t, 0.0f, 1.0f);

    float current_width = config_.lane_width_top + t * (config_.lane_width_bottom - config_.lane_width_top);
    float half_w = current_width * 0.5f;

    float center_x = 0.5f;
    float left_bound = center_x - half_w;
    float right_bound = center_x + half_w;

    out_lateral_offset = (x - center_x) / (half_w > 0.001f ? half_w : 1.0f);

    return (x >= left_bound && x <= right_bound);
}

float SAFARGeometry::estimateDistanceMeters(const BoundingBox2D& bbox, const std::string& class_name) const {
    float obj_height_m = (class_name == "person" || class_name == "pedestrian")
                             ? config_.nominal_pedestrian_height_m
                             : config_.nominal_vehicle_height_m;

    float box_h_norm = std::clamp(bbox.height(), 0.01f, 1.0f);
    // Pin-hole distance approximation: d = (f * H_real) / H_pixel
    float distance = (config_.camera_focal_length_px * obj_height_m) / (box_h_norm * 480.0f);
    return std::clamp(distance, 1.0f, 150.0f);
}

float SAFARGeometry::computeTTC(float distance_m, float closing_speed_mps) const {
    if (closing_speed_mps <= 0.1f) {
        return 999.0f; // Not closing or moving away
    }
    return distance_m / closing_speed_mps;
}

void SAFARGeometry::evaluateSpatialMetrics(std::vector<TrackedObject>& tracks, const IMUData& ego_imu, float dt_seconds) {
    for (auto& trk : tracks) {
        // 1. Ego-corridor check
        trk.in_ego_path = isBoxInEgoCorridor(trk.bbox, trk.lateral_offset);

        // 2. Distance estimation
        float prev_dist = trk.estimated_distance_m;
        trk.estimated_distance_m = estimateDistanceMeters(trk.bbox, trk.class_name);

        // 3. Relative velocity
        if (trk.age_frames > 1 && dt_seconds > 0.001f) {
            float visual_delta_v = (prev_dist - trk.estimated_distance_m) / dt_seconds;
            trk.relative_velocity_mps = visual_delta_v;
        } else {
            trk.relative_velocity_mps = ego_imu.speed_mps;
        }

        // 4. Time-to-Collision
        trk.ttc_seconds = computeTTC(trk.estimated_distance_m, trk.relative_velocity_mps);
    }
}

ValidationMetrics SAFARGeometry::compareWithGroundTruth(const TrackedObject& track, const GroundTruthObject& gt) const {
    ValidationMetrics m;
    m.detection_matched = true;
    m.distance_error_m = std::abs(track.estimated_distance_m - gt.actual_distance_m);
    m.distance_error_pct = (gt.actual_distance_m > 0.1f) ? (m.distance_error_m / gt.actual_distance_m) * 100.0f : 0.0f;
    m.ttc_error_seconds = std::abs(track.ttc_seconds - gt.actual_ttc_seconds);
    return m;
}

} // namespace safar
