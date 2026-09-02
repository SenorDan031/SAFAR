#pragma once

#include "../Core/SAFARTypes.hpp"
#include <vector>
#include <functional>

namespace safar {

class SAFARPerceptionInterface {
public:
    virtual ~SAFARPerceptionInterface() = default;

    // Ingests incoming detections from Python Perception service or Mock Perception
    virtual void onDetectionsReceived(const std::vector<Detection>& detections, uint64_t timestamp_us) = 0;
};

} // namespace safar
