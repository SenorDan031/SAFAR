"""Modular screen-capture adapter for The Crew 2 game window on Windows."""
import ctypes
import ctypes.wintypes as wintypes
import queue
import threading
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .config import TheCrew2Config


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


def find_game_window(titles: Tuple[str, ...]) -> Optional[int]:
    """Search for an open window matching any of the candidate titles."""
    user32 = ctypes.windll.user32
    matched_hwnd: List[int] = []

    def _enum_windows_callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            window_title = buff.value
            for candidate in titles:
                if candidate.lower() in window_title.lower():
                    matched_hwnd.append(hwnd)
                    return False
        return True

    wndproc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_enum_windows_callback)
    user32.EnumWindows(wndproc, 0)
    return matched_hwnd[0] if matched_hwnd else None


class TheCrew2Capture:
    """High-performance window capture with timestamp preservation and zero backlog."""

    def __init__(self, config: Optional[TheCrew2Config] = None):
        self.config = config or TheCrew2Config()
        self.hwnd: Optional[int] = None
        self.window_name: str = "Unknown"
        self._user32 = ctypes.windll.user32
        self._gdi32 = ctypes.windll.gdi32
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[Tuple[float, np.ndarray]] = None
        self._frame_lock = threading.Lock()
        self._fps_count = 0
        self._last_fps_time = time.perf_counter()
        self._current_fps = 0.0
        self._mock_mode = False

    def locate_window(self) -> bool:
        """Locate the target game window handle."""
        self.hwnd = find_game_window(tuple(self.config.window_titles))
        if self.hwnd:
            buff = ctypes.create_unicode_buffer(256)
            self._user32.GetWindowTextW(self.hwnd, buff, 256)
            self.window_name = buff.value
            self._mock_mode = False
            return True
        else:
            self.hwnd = None
            self.window_name = "Mock/Synthetic Source"
            self._mock_mode = True
            return False

    def is_game_running(self) -> bool:
        """Check if the game window handle exists and is valid."""
        return self.hwnd is not None and bool(self._user32.IsWindow(self.hwnd))

    def is_foreground(self) -> bool:
        """Verify whether The Crew 2 is currently the active foreground window."""
        if not self.hwnd:
            return False
        return self._user32.GetForegroundWindow() == self.hwnd

    def grab_frame(self) -> Tuple[float, np.ndarray]:
        """Synchronously capture a single frame from the game window or fallback."""
        timestamp = time.perf_counter()

        if not self.is_game_running():
            # If game window is not present, generate a clean synthetic placeholder frame
            width = self.config.capture_width or 1280
            height = self.config.capture_height or 720
            mock_frame = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.putText(
                mock_frame,
                "SAFAR - The Crew 2 (Waiting for window...)",
                (int(width * 0.15), int(height * 0.48)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 180, 255),
                2,
            )
            self._update_fps()
            return timestamp, mock_frame

        # Get client rect coordinates
        rect = wintypes.RECT()
        self._user32.GetClientRect(self.hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            # Fallback to window rect
            self._user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top

        if width <= 0 or height <= 0:
            width, height = self.config.capture_width, self.config.capture_height
            return timestamp, np.zeros((height, width, 3), dtype=np.uint8)

        # GDI capture
        hwnd_dc = self._user32.GetDC(self.hwnd)
        mem_dc = self._gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = self._gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        self._gdi32.SelectObject(mem_dc, bitmap)

        # Try PrintWindow first for hardware-accelerated / layered window rendering, fallback to BitBlt
        pw_rendered = self._user32.PrintWindow(self.hwnd, mem_dc, 2)  # PW_RENDERFULLCONTENT = 2
        if not pw_rendered:
            self._gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, 0x00CC0020)  # SRCCOPY

        bi = _BITMAPINFO()
        bi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bi.bmiHeader.biWidth = width
        bi.bmiHeader.biHeight = -height  # Top-down bitmap
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        bi.bmiHeader.biCompression = 0  # BI_RGB

        buffer_size = width * height * 4
        buf = (ctypes.c_char * buffer_size)()
        self._gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bi), 0)

        # Cleanup GDI handles
        self._gdi32.DeleteObject(bitmap)
        self._gdi32.DeleteDC(mem_dc)
        self._user32.ReleaseDC(self.hwnd, hwnd_dc)

        # Convert raw BGRA buffer to BGR numpy array
        raw_arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
        frame_bgr = cv2.cvtColor(raw_arr, cv2.COLOR_BGRA2BGR)

        # Resize if configured and dimensions differ
        if self.config.capture_width and self.config.capture_height:
            if (width, height) != (self.config.capture_width, self.config.capture_height):
                frame_bgr = cv2.resize(frame_bgr, (self.config.capture_width, self.config.capture_height))

        self._update_fps()
        return timestamp, frame_bgr

    def start_async(self) -> None:
        """Start background capture thread to ensure zero queue delay."""
        if self._running:
            return
        self.locate_window()
        self._running = True
        self._thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._thread.start()

    def _capture_worker(self) -> None:
        target_interval = 1.0 / max(1.0, self.config.target_fps)
        while self._running:
            loop_start = time.perf_counter()
            if not self.is_game_running():
                # Periodically re-check for game window
                self.locate_window()

            ts, frame = self.grab_frame()
            with self._frame_lock:
                self._latest_frame = (ts, frame)

            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def read(self) -> Tuple[float, np.ndarray]:
        """Read the latest captured frame, non-blocking and latency-free."""
        if self._running:
            with self._frame_lock:
                if self._latest_frame is not None:
                    return self._latest_frame
        return self.grab_frame()

    def _update_fps(self) -> None:
        self._fps_count += 1
        now = time.perf_counter()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self._current_fps = self._fps_count / elapsed
            self._fps_count = 0
            self._last_fps_time = now

    @property
    def fps(self) -> float:
        return self._current_fps

    def release(self) -> None:
        """Stop capture thread and release resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
