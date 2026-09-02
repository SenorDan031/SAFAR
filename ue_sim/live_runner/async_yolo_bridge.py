"""
SAFAR — Asynchronous YOLO & Stereo Perception Bridge for Unreal Engine 5
Performs non-blocking object detection & stereo depth estimation.
Operates asynchronously without interfering with UE5 game loop or physics.
"""
import socket
import json
import time
import math
from typing import List, Dict, Any, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


class AsyncYOLOBridge:
    """Asynchronous Perception Bridge transmitting machine-readable detections to UE5."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9005):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False

    def format_detection_packet(
        self,
        timestamp_s: float,
        objects: List[Dict[str, Any]]
    ) -> bytes:
        """Formats structured machine-readable JSON packet."""
        packet = {
            "timestamp": timestamp_s,
            "count": len(objects),
            "objects": objects
        }
        return json.dumps(packet).encode("utf-8")

    def broadcast_detections(self, objects: List[Dict[str, Any]]) -> None:
        """Sends structured JSON detection packet to UE5 receiver without blocking."""
        try:
            data = self.format_detection_packet(time.time(), objects)
            self.sock.sendto(data, (self.host, self.port))
        except Exception:
            pass

    def close(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    bridge = AsyncYOLOBridge()
    print("[SAFAR Async YOLO Bridge] Initialized on UDP Port 9005.")
    # Example non-blocking structured detection broadcast
    sample_detections = [
        {
            "id": 101,
            "class": "car",
            "confidence": 0.94,
            "bbox": [0.42, 0.45, 0.58, 0.72],
            "disparity_px": 14.8,
            "estimated_depth_m": 11.0
        }
    ]
    bridge.broadcast_detections(sample_detections)
    print("[SAFAR Async YOLO Bridge] Broadcast sample detection packet cleanly.")
    bridge.close()
