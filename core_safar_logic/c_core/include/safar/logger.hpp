#pragma once

#include <iostream>
#include <chrono>
#include <string>
#include <iomanip>

namespace safar {

class Logger {
public:
    static uint64_t getCurrentTimeUs() {
        auto now = std::chrono::high_resolution_clock::now().time_since_epoch();
        return std::chrono::duration_cast<std::chrono::microseconds>(now).count();
    }

    static void logInfo(const std::string& tag, const std::string& message) {
        auto now_ms = getCurrentTimeUs() / 1000.0;
        std::cout << "[C++ SAFAR CORE] [" << tag << "] " << message << std::endl;
    }

    static void logBoundary(const std::string& from, const std::string& to, const std::string& details) {
        std::cout << ">>> PIPELINE: [" << from << " -> " << to << "] " << details << std::endl;
    }
};

} // namespace safar
