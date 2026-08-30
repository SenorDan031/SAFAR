cmake_minimum_required(VERSION 3.15)
project(safar_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

set(SAFAR_CORE_SOURCES
    src/Tracking/SAFARTracking.cpp
    src/Geometry/SAFARGeometry.cpp
    src/Threat/SAFARThreatAssessment.cpp
    src/Decision/SAFARDecisionEngine.cpp
    src/Control/SAFARVehicleController.cpp
    src/Communication/SAFARCommunication.cpp
    src/Core/SAFARManager.cpp
    src/Bridge/UE5VehicleBridge.cpp
)

# Standalone Real-Time Daemon Executable
add_executable(safar_core
    src/main.cpp
    ${SAFAR_CORE_SOURCES}
)

if (WIN32)
    target_link_libraries(safar_core ws2_32)
endif()

# Full Framework Unit Test Executable
add_executable(test_safar_framework
    tests/test_safar_framework.cpp
    ${SAFAR_CORE_SOURCES}
)

if (WIN32)
    target_link_libraries(test_safar_framework ws2_32)
endif()
