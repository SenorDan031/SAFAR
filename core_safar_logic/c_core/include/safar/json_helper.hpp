#pragma once

#include "types.hpp"
#include <string>
#include <sstream>
#include <iomanip>
#include <vector>
#include <regex>

namespace safar {

class JsonHelper {
public:
    // Serializes ControlResponse into valid JSON
    static std::string serializeControlResponse(const ControlResponse& resp) {
        std::ostringstream ss;
        ss << "{"
           << "\"timestamp_us\":" << resp.timestamp_us << ","
           << "\"frame_id\":" << resp.frame_id << ","
           << "\"threat_score\":" << std::fixed << std::setprecision(4) << resp.threat_score << ","
           << "\"decision\":\"" << toString(resp.decision) << "\","
           << "\"control\":{"
           << "\"throttle\":" << std::fixed << std::setprecision(3) << resp.control.throttle << ","
           << "\"brake\":" << std::fixed << std::setprecision(3) << resp.control.brake << ","
           << "\"steering\":" << std::fixed << std::setprecision(3) << resp.control.steering << ","
           << "\"emergency_stop\":" << (resp.control.emergency_stop ? "true" : "false")
           << "},"
           << "\"hud_message\":\"" << resp.hud_message << "\","
           << "\"latency_ms\":" << std::fixed << std::setprecision(2) << resp.latency_ms
           << "}\n";
        return ss.str();
    }

    // Parses a detection JSON payload into a DetectionFrame struct
    static bool parseDetectionFrame(const std::string& json_str, DetectionFrame& out_frame) {
        out_frame.detections.clear();

        // Extract timestamp_us
        std::smatch match;
        std::regex ts_regex("\"timestamp_us\"\\s*:\\s*([0-9]+)");
        if (std::regex_search(json_str, match, ts_regex) && match.size() > 1) {
            out_frame.timestamp_us = std::stoull(match[1].str());
        }

        // Extract frame_id
        std::regex frame_regex("\"frame_id\"\\s*:\\s*([0-9]+)");
        if (std::regex_search(json_str, match, frame_regex) && match.size() > 1) {
            out_frame.frame_id = std::stoul(match[1].str());
        }

        // Extract ego_speed_mps
        std::regex speed_regex("\"ego_speed_mps\"\\s*:\\s*([0-9]*\\.?[0-9]+)");
        if (std::regex_search(json_str, match, speed_regex) && match.size() > 1) {
            out_frame.ego_speed_mps = std::stof(match[1].str());
        }

        // Extract detection objects: {"track_id":..., "class_name":..., "confidence":..., "bbox_normalized":[...], ...}
        // Match each detection object substring
        std::regex det_regex("\\{\\s*\"track_id\"\\s*:\\s*([0-9]+)\\s*,\\s*\"class_name\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"confidence\"\\s*:\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*\"bbox_normalized\"\\s*:\\s*\\[\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*,\\s*([0-9]*\\.?[0-9]+)\\s*\\]");
        
        auto words_begin = std::sregex_iterator(json_str.begin(), json_str.end(), det_regex);
        auto words_end = std::sregex_iterator();

        for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
            std::smatch m = *i;
            if (m.size() >= 8) {
                Detection det;
                det.track_id = std::stoi(m[1].str());
                det.class_name = m[2].str();
                det.confidence = std::stof(m[3].str());
                det.bbox.xmin = std::stof(m[4].str());
                det.bbox.ymin = std::stof(m[5].str());
                det.bbox.xmax = std::stof(m[6].str());
                det.bbox.ymax = std::stof(m[7].str());
                det.center_x = det.bbox.centerX();
                det.bottom_y = det.bbox.bottomY();
                out_frame.detections.push_back(det);
            }
        }

        return true;
    }
};

} // namespace safar
