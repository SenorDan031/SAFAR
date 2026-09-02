"""
SAFAR — Unreal Engine 5 Vehicle Cockpit & Chaos Control Bridge
Runs in the background of UE5, continuously transmitting virtual sensor data
to the embedded C++ SAFAR Logic Engine (Port 8888) and injecting physical Chaos Vehicle overrides.
"""
import socket
import struct
import time
import math
from typing import List, Dict, Tuple, Optional, Any

from safar.perception.stereo_depth import StereoDepthEngine, StereoDetection
from safar_simulator.urban_traffic_manager import UrbanTrafficManager, UrbanActor

# Binary Struct Packets matching safar_core C++ UE5VehicleBridge.hpp
# UE5VehicleSensorPacket: 7 floats + 1 uint32 = 32 bytes
SENSOR_PACKET_FORMAT = "=fffffffI"
# UE5DetectionItem: int32, int32, 4 floats = 24 bytes
DETECTION_ITEM_FORMAT = "=iiffff"
# SAFARControlResponse: uint8, 2 floats, 2 uint8, 2 floats, int32 = 25 bytes
CONTROL_RESPONSE_FORMAT = "=BffBBffi"


class UE5CockpitBridge:
    """High-speed 60Hz binary bridge connecting UE5 Vehicle Pawn to C++ SAFAR Engine."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.04) # 40ms timeout

        self.stereo_engine = StereoDepthEngine(baseline_m=0.25, focal_length_px=650.0)
        self.traffic_manager = UrbanTrafficManager(target_actor_count=20, hazard_frequency_s=8.0)

    def pack_and_send(
        self,
        speed_mps: float,
        throttle: float,
        brake: float,
        steering: float,
        yaw_rate: float,
        imu_ax: float,
        imu_ay: float,
        detections: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Transmits sensor packet and receives C++ SAFAR control decision."""
        det_bytes = bytearray()
        count = min(len(detections), 32)

        for i in range(count):
            d = detections[i]
            # Class type mapping: 0: Car, 1: Motorcycle, 2: Truck, 3: Bus, 4: AutoRickshaw, 5: Pedestrian
            cls_name = str(d.get("class_name", "car")).lower()
            cls_id = 0
            if "motorcycle" in cls_name or "bike" in cls_name: cls_id = 1
            elif "truck" in cls_name: cls_id = 2
            elif "bus" in cls_name: cls_id = 3
            elif "auto" in cls_name or "rickshaw" in cls_name: cls_id = 4
            elif "pedestrian" in cls_name or "person" in cls_name: cls_id = 5

            actor_id = int(d.get("actor_id", d.get("id", i + 1)))
            disparity = float(d.get("disparity_px", 16.0))
            lat_offset = float(d.get("lateral_offset_m", 0.0))
            rel_vx = float(d.get("relative_vx_mps", 0.0))
            conf = float(d.get("confidence", 0.95))

            det_bytes.extend(struct.pack(
                DETECTION_ITEM_FORMAT,
                actor_id,
                cls_id,
                disparity,
                lat_offset,
                rel_vx,
                conf
            ))

        header = struct.pack(
            SENSOR_PACKET_FORMAT,
            speed_mps,
            steering,
            throttle,
            brake,
            yaw_rate,
            imu_ax,
            imu_ay,
            count
        )

        try:
            self.sock.sendto(header + det_bytes, (self.host, self.port))
            data, _ = self.sock.recvfrom(512)
            if len(data) >= struct.calcsize(CONTROL_RESPONSE_FORMAT):
                override_active, throttle_ovr, brake_ovr, handbrake_ovr, warning_led, d_stop, ttc, hazard_id = struct.unpack(
                    CONTROL_RESPONSE_FORMAT,
                    data[:struct.calcsize(CONTROL_RESPONSE_FORMAT)]
                )
                return {
                    "is_override_active": bool(override_active),
                    "throttle_override": throttle_ovr,
                    "brake_override": brake_ovr,
                    "handbrake_override": bool(handbrake_ovr),
                    "warning_led": bool(warning_led),
                    "stopping_distance_m": d_stop,
                    "ttc_seconds": ttc,
                    "primary_hazard_id": hazard_id
                }
        except socket.timeout:
            pass
        except Exception:
            pass

        return None
