"""
SAFAR Perception Layer — IPC Sender to C++ Core
"""
import socket
import json
import time
from typing import Optional

from .types import DetectionPayload


class IpcSender:
    """
    High-speed TCP client that transmits serialized DetectionPayload packets to the C++ SAFAR Core.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 9002):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.is_connected = False

    def connect(self, retries: int = 5, retry_delay_s: float = 0.5) -> bool:
        for attempt in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.is_connected = True
                return True
            except ConnectionRefusedError:
                time.sleep(retry_delay_s)
            except Exception:
                pass
        self.is_connected = False
        return False

    def send_detections(self, payload: DetectionPayload) -> bool:
        if not self.is_connected or self.sock is None:
            if not self.connect(retries=1):
                return False

        try:
            json_str = json.dumps(payload.to_dict()) + "\n"
            self.sock.sendall(json_str.encode("utf-8"))
            return True
        except Exception:
            self.is_connected = False
            return False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.is_connected = False
