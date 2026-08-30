#pragma once

#include "../Core/SAFARTypes.hpp"
#include <string>
#include <vector>
#include <functional>
#include <thread>
#include <atomic>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

namespace safar {

class SAFARCommunication {
public:
    using DetectionCallback = std::function<void(const std::vector<Detection>&, uint64_t)>;

    explicit SAFARCommunication(int perception_port = 9002, int ue5_port = 9003);
    ~SAFARCommunication();

    bool startServer(DetectionCallback callback);
    void stopServer();

    bool sendControlCommand(const ControlCommand& cmd, const std::string& host = "127.0.0.1");

    static std::string serializeControlCommand(const ControlCommand& cmd);
    static bool parseDetections(const std::string& json_str, std::vector<Detection>& out_detections, uint64_t& out_timestamp_us);

private:
    void listenLoop();

    int perception_port_;
    int ue5_port_;
    std::atomic<bool> running_{false};
    SOCKET server_fd_{INVALID_SOCKET};
    SOCKET ue5_fd_{INVALID_SOCKET};
    DetectionCallback callback_;
    std::thread listen_thread_;
};

} // namespace safar
