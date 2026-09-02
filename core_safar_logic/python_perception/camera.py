"""OpenCV-backed local-network camera input with no YOLO or safety logic."""

from typing import Callable, Optional
from urllib.parse import urlparse


class CameraStreamError(RuntimeError):
    """Raised when a local camera stream cannot provide usable frames."""


class PhoneCamera:
    """Small reusable wrapper for an Android IP-camera HTTP/MJPEG stream."""

    def __init__(self, stream_url: str, capture_factory: Optional[Callable] = None) -> None:
        self.stream_url = stream_url
        self._capture_factory = capture_factory
        self._capture = None

    def connect(self) -> None:
        """Open the configured stream and raise a useful error on failure."""
        parsed = urlparse(self.stream_url)
        if parsed.scheme not in ("http", "https", "rtsp", "rtsps") or not parsed.netloc:
            raise CameraStreamError("Invalid stream URL. Expected HTTP/MJPEG or rtsp://PHONE_IP:PORT/path")
        if self._capture_factory is None:
            try:
                import cv2
            except ImportError as error:
                raise CameraStreamError("OpenCV is unavailable. Install requirements-yolo.txt.") from error
            self._capture_factory = cv2.VideoCapture
        self._capture = self._capture_factory(self.stream_url)
        if not self.is_opened():
            self.release()
            raise CameraStreamError(
                "Could not connect to phone camera. Check Wi-Fi, the camera app, and the stream URL."
            )

    def is_opened(self) -> bool:
        """Return whether OpenCV reports an open stream."""
        return self._capture is not None and bool(self._capture.isOpened())

    def read(self):
        """Return the next OpenCV/Numpy frame or raise when the stream stops."""
        if not self.is_opened():
            raise CameraStreamError("Phone camera is not connected.")
        success, frame = self._capture.read()
        if not success or frame is None or not hasattr(frame, "shape"):
            raise CameraStreamError("Phone camera frame was unavailable or malformed.")
        return frame

    def release(self) -> None:
        """Release the OpenCV resource safely; this method is idempotent."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
