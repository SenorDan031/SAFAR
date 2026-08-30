#pragma once

#include "types.hpp"
#include <algorithm>

namespace safar {

class EgoPathGeometry {
public:
    explicit EgoPathGeometry(const EgoPathConfig& config = EgoPathConfig())
        : config_(config) {}

    // Evaluates whether a point (norm_x, norm_y) lies within the ego corridor trapezoid
    bool isPointInPath(float x, float y, float& out_lateral_offset) const {
        if (y < config_.horizon_y || y > 1.0f) {
            out_lateral_offset = 1.0f;
            return false;
        }

        // Interpolate half-width from horizon to bottom
        float t = (y - config_.horizon_y) / (1.0f - config_.horizon_y);
        t = std::clamp(t, 0.0f, 1.0f);

        float current_width = config_.top_width + t * (config_.bottom_width - config_.top_width);
        float half_w = current_width * 0.5f;

        float center_x = 0.5f;
        float left_bound = center_x - half_w;
        float right_bound = center_x + half_w;

        out_lateral_offset = (x - center_x) / (half_w > 0.001f ? half_w : 1.0f);

        return (x >= left_bound && x <= right_bound);
    }

    bool isBoxInPath(const BoundingBox& bbox, float& out_lateral_offset) const {
        // Evaluate the ground-contact point (bottom-center)
        return isPointInPath(bbox.centerX(), bbox.bottomY(), out_lateral_offset);
    }

    const EgoPathConfig& getConfig() const { return config_; }
    void setConfig(const EgoPathConfig& config) { config_ = config; }

private:
    EgoPathConfig config_;
};

} // namespace safar
