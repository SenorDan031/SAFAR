#pragma once

#include "../Core/SAFARTypes.hpp"
#include "../Core/SAFARConfig.hpp"
#include <vector>
#include <map>

namespace safar {

class SAFARTracking {
public:
    explicit SAFARTracking(const SAFARConfig& config = SAFARConfig());

    // Updates tracks with new detections from perception
    std::vector<TrackedObject> update(const std::vector<Detection>& detections, uint64_t timestamp_us);

    const std::vector<TrackedObject>& getActiveTracks() const { return active_tracks_; }
    void reset();

private:
    float computeDistance(const BoundingBox2D& b1, const BoundingBox2D& b2) const;

    SAFARConfig config_;
    int next_tracking_id_{1};
    std::vector<TrackedObject> active_tracks_;
    uint64_t last_timestamp_us_{0};
};

} // namespace safar
