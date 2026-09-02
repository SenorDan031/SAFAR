"""
SAFAR Sensor Interface — Abstraction layer for virtual and physical sensor sources
"""
from abc import ABC, abstractmethod
import time
import socket
import struct
import json
from typing import Optional, Generator
import cv2
import numpy as np

from .types import SensorFrame


class BaseSensorSource(ABC):
    """
    Abstract interface for sensor sources.
    SAFAR does not care whether frames come from UE5 or a physical camera.
    """
    @abstractmethod
    def read_frame(self) -> Optional[SensorFrame]:
        pass

    @abstractmethod
    def close(self):
        pass


class UE5SocketStreamSource(BaseSensorSource):
    """
    Receives live virtual camera frames and vehicle telemetry from Unreal Engine 5 over TCP.
    """
    def __init__(self, port: int = 9001):
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(1)
        self.client_socket: Optional[socket.socket] = None
        self.is_connected = False

    def wait_for_ue5_connection(self, timeout_s: float = 5.0) -> bool:
        self.server_socket.settimeout(timeout_s)
        try:
            self.client_socket, addr = self.server_socket.accept()
            self.is_connected = True
            return True
        except socket.timeout:
            return False

    def read_frame(self) -> Optional[SensorFrame]:
        if not self.is_connected or self.client_socket is None:
            return None

        try:
            # Header: 4 bytes Magic ("SFRM") + 4 bytes payload length
            header = self.client_socket.recv(8)
            if len(header) < 8:
                return None

            magic, length = struct.unpack("!4sI", header)
            if magic != b"SFRM":
                return None

            # Read payload
            data = bytearray()
            while len(data) < length:
                packet = self.client_socket.recv(length - len(data))
                if not packet:
                    return None
                data.extend(packet)

            # Metadata is null-terminated JSON before image bytes
            null_pos = data.find(b"\0")
            if null_pos == -1:
                return None

            meta_json = data[:null_pos].decode("utf-8")
            meta = json.loads(meta_json)

            image_bytes = data[null_pos + 1:]
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            return SensorFrame(
                timestamp_us=meta.get("timestamp_us", int(time.time() * 1e6)),
                frame_id=meta.get("frame_id", 0),
                ego_speed_mps=meta.get("ego_speed_mps", 0.0),
                ego_heading_deg=meta.get("ego_heading_deg", 0.0),
                image=img
            )
        except Exception:
            return None

    def close(self):
        if self.client_socket:
            self.client_socket.close()
        self.server_socket.close()


class PhysicalCameraSource(BaseSensorSource):
    """
    Reads from physical USB camera / RTSP dashcam stream.
    """
    def __init__(self, camera_index: int = 0, default_speed_mps: float = 12.0):
        self.cap = cv2.VideoCapture(camera_index)
        self.default_speed = default_speed_mps
        self.frame_counter = 0

    def read_frame(self) -> Optional[SensorFrame]:
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        self.frame_counter += 1
        return SensorFrame(
            timestamp_us=int(time.time() * 1e6),
            frame_id=self.frame_counter,
            ego_speed_mps=self.default_speed,
            ego_heading_deg=0.0,
            image=frame
        )

    def close(self):
        self.cap.release()
