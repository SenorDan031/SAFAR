#pragma once

#include "../Core/SAFARTypes.hpp"
#include "../Core/SAFARConfig.hpp"
#include <vector>

namespace safar {

class SAFARGeometry {
public:
    explicit SAFARGeometry(const SAFARConfig& config = SAFARConfig());

    // Evaluates spatial metrics (distance, lateral offset, in_ego_path, TTC) for all active tracks
    void evaluateSpatialMetrics(std::vector<TrackedObject>& tracks, const IMUData& ego_imu, float dt_seconds);

    // Checks if a bounding box lies within the ego lane corridor trapezoid
    bool isBoxInEgoCorridor(const BoundingBox2D& bbox, float& out_lateral_offset) const;

    // Estimates distance to object based on visual pinhole projection
    float estimateDistanceMeters(const BoundingBox2D& bbox, const std::string& class_name) const;

    // Computes Time-To-Collision (TTC = distance / closing_velocity)
    float computeTTC(float distance_m, float closing_speed_mps) const;

    // Validates estimate against ground truth
    ValidationMetrics compareWithGroundTruth(const TrackedObject& track, const GroundTruthObject& gt) const;

    const SAFARConfig& getConfig() const { return config_; }
    void setConfig(const SAFARConfig& config) { config_ = config; }

private:
    SAFARConfig config_;
};

} // namespace safar
