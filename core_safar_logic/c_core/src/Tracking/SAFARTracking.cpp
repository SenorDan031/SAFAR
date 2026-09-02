#include "safar/Tracking/SAFARTracking.hpp"
#include <algorithm>
#include <cmath>

namespace safar {

SAFARTracking::SAFARTracking(const SAFARConfig& config)
    : config_(config) {}

float SAFARTracking::computeDistance(const BoundingBox2D& b1, const BoundingBox2D& b2) const {
    float dx = b1.centerX() - b2.centerX();
    float dy = b1.centerY() - b2.centerY();
    return std::sqrt(dx * dx + dy * dy);
}

std::vector<TrackedObject> SAFARTracking::update(const std::vector<Detection>& detections, uint64_t timestamp_us) {
    float dt = (last_timestamp_us_ > 0 && timestamp_us > last_timestamp_us_)
                   ? static_cast<float>(timestamp_us - last_timestamp_us_) / 1e6f
                   : 0.033f;
    last_timestamp_us_ = timestamp_us;

    std::vector<bool> detection_matched(detections.size(), false);
    std::vector<bool> track_matched(active_tracks_.size(), false);

    // 1. Associate detections with existing tracks (Greedy centroid match)
    for (size_t t = 0; t < active_tracks_.size(); ++t) {
        float best_dist = config_.max_association_distance_norm;
        int best_det_idx = -1;

        for (size_t d = 0; d < detections.size(); ++d) {
            if (detection_matched[d]) continue;
            if (detections[d].camera_id != active_tracks_[t].camera_id) continue;

            float dist = computeDistance(active_tracks_[t].bbox, detections[d].bbox);
            if (dist < best_dist) {
                best_dist = dist;
                best_det_idx = static_cast<int>(d);
            }
        }

        if (best_det_idx >= 0) {
            const auto& det = detections[best_det_idx];
            // Update track state
            active_tracks_[t].confidence = det.confidence;
            active_tracks_[t].class_name = det.class_name;
            active_tracks_[t].bbox = det.bbox;
            active_tracks_[t].age_frames += 1;
            active_tracks_[t].missed_frames = 0;
            active_tracks_[t].last_seen_us = timestamp_us;

            detection_matched[best_det_idx] = true;
            track_matched[t] = true;
        } else {
            active_tracks_[t].missed_frames += 1;
        }
    }

    // 2. Spawn new tracks for unmatched detections
    for (size_t d = 0; d < detections.size(); ++d) {
        if (!detection_matched[d]) {
            TrackedObject new_track;
            new_track.tracking_id = next_tracking_id_++;
            new_track.camera_id = detections[d].camera_id;
            new_track.class_name = detections[d].class_name;
            new_track.confidence = detections[d].confidence;
            new_track.bbox = detections[d].bbox;
            new_track.age_frames = 1;
            new_track.missed_frames = 0;
            new_track.last_seen_us = timestamp_us;
            active_tracks_.push_back(new_track);
        }
    }

    // 3. Filter out stale tracks (missed > max_missed_frames)
    auto it = std::remove_if(active_tracks_.begin(), active_tracks_.end(), [&](const TrackedObject& trk) {
        return trk.missed_frames > config_.max_missed_frames;
    });
    active_tracks_.erase(it, active_tracks_.end());

    return active_tracks_;
}

void SAFARTracking::reset() {
    active_tracks_.clear();
    next_tracking_id_ = 1;
    last_timestamp_us_ = 0;
}

} // namespace safar
