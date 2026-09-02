#include "safar/Core/SAFARManager.hpp"
#include "safar/Core/SAFARTypes.hpp"
#include "safar/Core/SAFARConfig.hpp"
#include "safar/Bridge/UE5VehicleBridge.hpp"

#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>

std::atomic<bool> g_running{true};

void signalHandler(int signum) {
    std::cout << "\n[SAFAR C++ CORE] Signal (" << signum << ") received. Safely terminating...\n";
    g_running = false;
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);

    int perception_port = 9002;
    int ue5_port = 9003;

    std::cout << "======================================================================\n";
    std::cout << " SAFAR MODULAR REAL-TIME REASONING & SAFETY CORE v2.0\n";
    std::cout << "======================================================================\n";
    std::cout << " [PIPELINE] Multi-Object Tracking -> Geometry & TTC -> Threat -> Decision -> Actuators\n";
    std::cout << " [INPUT]    TCP Port " << perception_port << " (Perception Stream)\n";
    std::cout << " [OUTPUT]   UDP Port " << ue5_port << " (UE5 Chaos Vehicle Control Bridge)\n";
    std::cout << " [WATCHDOG] Active (250ms Timeout Protection)\n";
    std::cout << "======================================================================\n\n";

    safar::SAFARConfig config;
    safar::SAFARManager manager(config);
    safar::UE5VehicleBridge ue5_bridge(config, 8888);
    ue5_bridge.start();

    if (!manager.initialize(perception_port, ue5_port)) {
        std::cerr << "[ERROR] Failed to start SAFAR C++ Core IPC Communication Server on port " << perception_port << "\n";
        return 1;
    }

    std::cout << "[SAFAR C++ CORE] Real-Time Supervisor & UE5 Vehicle Bridge Active on UDP Port 8888.\n";

    // Watchdog background supervisor thread
    std::thread watchdog_thread([&]() {
        while (g_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            manager.checkWatchdogAndStep();
        }
    });

    while (g_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    if (watchdog_thread.joinable()) {
        watchdog_thread.join();
    }

    std::cout << "[SAFAR C++ CORE] SAFAR Real-Time Core Shutdown Cleanly.\n";
    return 0;
}
