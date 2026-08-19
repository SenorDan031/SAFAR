"""Isolated game control adapter for The Crew 2 with DirectInput scancodes and safety fail-safes."""
import atexit
import ctypes
import ctypes.wintypes as wintypes
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional, Tuple

from .config import TheCrew2Config
from .hazard import ConfirmationState, LeadHazardResult


class ControlState(str, Enum):
    PLAYER_CONTROL = "PLAYER_CONTROL"
    HAZARD_CANDIDATE = "HAZARD_CANDIDATE"
    HAZARD_CONFIRMED = "HAZARD_CONFIRMED"
    WARNING = "WARNING"
    SLOWDOWN_OVERRIDE = "SLOWDOWN_OVERRIDE"
    BRAKE_OVERRIDE = "BRAKE_OVERRIDE"
    HAZARD_CLEAR = "HAZARD_CLEAR"


class BrakeState(str, Enum):
    RELEASED = "RELEASED"
    LIGHT = "LIGHT"
    STRONG = "STRONG"


@dataclass(frozen=True)
class ControlEvent:
    """Record of a control action or state transition for logging and verification."""
    timestamp_s: float
    state: ControlState
    brake_state: BrakeState
    is_overriding: bool
    reason: str
    target_window: str


# Windows SendInput structure definitions
class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUT_UNION)]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


class TheCrew2Controller:
    """Safely manages reversible game input interventions for The Crew 2."""

    def __init__(
        self,
        config: Optional[TheCrew2Config] = None,
        is_foreground_check: Optional[Callable[[], bool]] = None,
    ):
        self.config = config or TheCrew2Config()
        self._is_foreground_fn = is_foreground_check
        self.state = ControlState.PLAYER_CONTROL
        self.brake_state = BrakeState.RELEASED
        self.override_start_time: Optional[float] = None
        self.last_event: Optional[ControlEvent] = None
        self.event_log: List[ControlEvent] = []
        self.manual_emergency_triggered = False
        self.timed_out = False

        self._user32 = ctypes.windll.user32
        self._keys_currently_down = set()

        # Register cleanup to ensure keys are always released on shutdown
        atexit.register(self.release_all)

    def _check_emergency_hotkey(self) -> bool:
        """Poll VK_F8 emergency release key."""
        vk = self.config.emergency_release_vk
        key_state = self._user32.GetAsyncKeyState(vk)
        if bool(key_state & 0x8000):
            if not self.manual_emergency_triggered:
                self.manual_emergency_triggered = True
                self.release_all()
                self._record_event(
                    ControlState.PLAYER_CONTROL,
                    BrakeState.RELEASED,
                    False,
                    "Emergency release hotkey (F8) pressed by driver. Control unlocked.",
                )
            return True
        return self.manual_emergency_triggered

    def reset_emergency_lock(self) -> None:
        """Reset emergency manual release state."""
        self.manual_emergency_triggered = False
        self.timed_out = False

    def _send_scancode(self, scancode: int, is_up: bool) -> bool:
        """Send DirectInput hardware scancode using SendInput."""
        if not self.config.enabled:
            # Dry-run / mock mode
            return True

        if self.config.require_foreground_window and self._is_foreground_fn:
            if not self._is_foreground_fn():
                # Game is not active foreground window; safety inhibit
                return False

        flags = KEYEVENTF_SCANCODE
        if is_up:
            flags |= KEYEVENTF_KEYUP

        extra = ctypes.c_ulonglong(0)
        ki = _KEYBDINPUT(0, scancode, flags, 0, extra)
        inp = _INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki))

        result = self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
        if is_up:
            self._keys_currently_down.discard(scancode)
        else:
            self._keys_currently_down.add(scancode)
        return result == 1

    def release_all(self) -> None:
        """Immediately release all simulated pressed keys and return to player control."""
        for scancode in list(self._keys_currently_down):
            self._send_scancode(scancode, is_up=True)
        self._keys_currently_down.clear()
        self.brake_state = BrakeState.RELEASED
        self.override_start_time = None

    def release_throttle(self) -> None:
        """Release simulated throttle key ('W')."""
        self._send_scancode(self.config.throttle_scancode, is_up=True)

    def apply_light_brake(self) -> None:
        """Apply light slowdown brake."""
        self.release_throttle()
        self._send_scancode(self.config.brake_scancode, is_up=False)
        self.brake_state = BrakeState.LIGHT

    def apply_strong_brake(self) -> None:
        """Apply strong emergency braking."""
        self.release_throttle()
        self._send_scancode(self.config.brake_scancode, is_up=False)
        self._send_scancode(self.config.handbrake_scancode, is_up=False)
        self.brake_state = BrakeState.STRONG

    def release_brake(self) -> None:
        """Release all braking keys ('S' and Handbrake)."""
        self._send_scancode(self.config.brake_scancode, is_up=True)
        self._send_scancode(self.config.handbrake_scancode, is_up=True)
        self.brake_state = BrakeState.RELEASED

    def update(self, lead_result: LeadHazardResult) -> ControlEvent:
        """Advance controller state machine based on perception decision and safety watchdog."""
        now = time.perf_counter()

        # 1. Check emergency hotkey
        if self._check_emergency_hotkey():
            self.state = ControlState.PLAYER_CONTROL
            return self._record_event(
                ControlState.PLAYER_CONTROL,
                BrakeState.RELEASED,
                False,
                "Emergency release hotkey (F8) active. Player has exclusive control.",
            )

        # 2. Check window focus safety
        if self.config.require_foreground_window and self._is_foreground_fn:
            if not self._is_foreground_fn():
                if self.is_overriding:
                    self.release_all()
                    return self._record_event(
                        ControlState.PLAYER_CONTROL,
                        BrakeState.RELEASED,
                        False,
                        "Game window lost focus; control returned to player.",
                    )

        # 3. Check watchdog timeout
        if self.is_overriding and self.override_start_time:
            if now - self.override_start_time > self.config.max_override_duration_s:
                self.release_all()
                self.timed_out = True
                self.state = ControlState.PLAYER_CONTROL
                return self._record_event(
                    ControlState.PLAYER_CONTROL,
                    BrakeState.RELEASED,
                    False,
                    f"Override timeout exceeded ({self.config.max_override_duration_s}s); control returned to player.",
                )

        decision = lead_result.decision
        conf_state = lead_result.confirmation_state

        # If timed out, stay in PLAYER_CONTROL until hazard clears
        if self.timed_out:
            if decision == "CONTINUE" or conf_state in (ConfirmationState.NONE, ConfirmationState.CLEARED):
                self.timed_out = False
            else:
                return self._record_event(
                    ControlState.PLAYER_CONTROL,
                    BrakeState.RELEASED,
                    False,
                    "Override inhibited due to watchdog timeout; waiting for hazard clear.",
                )

        # 4. State transitions based on SAFAR Decision
        if decision == "CONTINUE" or conf_state == ConfirmationState.NONE:
            if self.state in (ControlState.SLOWDOWN_OVERRIDE, ControlState.BRAKE_OVERRIDE):
                self.release_all()
                event = self._record_event(
                    ControlState.HAZARD_CLEAR,
                    BrakeState.RELEASED,
                    False,
                    "Hazard cleared; releasing override and returning control to player.",
                )
                self.state = ControlState.PLAYER_CONTROL
                return event
            else:
                self.state = ControlState.PLAYER_CONTROL
                return self._record_event(
                    ControlState.PLAYER_CONTROL,
                    BrakeState.RELEASED,
                    False,
                    lead_result.reason,
                )

        elif decision == "CAUTION" or conf_state == ConfirmationState.CANDIDATE:
            if self.is_overriding:
                self.release_all()
            self.state = ControlState.HAZARD_CANDIDATE
            return self._record_event(
                ControlState.HAZARD_CANDIDATE,
                BrakeState.RELEASED,
                False,
                lead_result.reason,
            )

        elif decision == "WARN":
            if self.is_overriding:
                self.release_all()
            self.state = ControlState.WARNING
            return self._record_event(
                ControlState.WARNING,
                BrakeState.RELEASED,
                False,
                lead_result.reason,
            )

        elif decision == "SLOWDOWN":
            if not self.is_overriding:
                self.override_start_time = now
            self.state = ControlState.SLOWDOWN_OVERRIDE
            self.apply_light_brake()
            return self._record_event(
                ControlState.SLOWDOWN_OVERRIDE,
                self.brake_state,
                True,
                lead_result.reason,
            )

        elif decision == "EMERGENCY_BRAKE":
            if not self.is_overriding:
                self.override_start_time = now
            self.state = ControlState.BRAKE_OVERRIDE
            self.apply_strong_brake()
            return self._record_event(
                ControlState.BRAKE_OVERRIDE,
                self.brake_state,
                True,
                lead_result.reason,
            )

        # Default fallback
        self.state = ControlState.PLAYER_CONTROL
        return self._record_event(
            ControlState.PLAYER_CONTROL,
            BrakeState.RELEASED,
            False,
            lead_result.reason,
        )

    @property
    def is_overriding(self) -> bool:
        return self.state in (ControlState.SLOWDOWN_OVERRIDE, ControlState.BRAKE_OVERRIDE)

    def _record_event(
        self,
        state: ControlState,
        brake_state: BrakeState,
        is_overriding: bool,
        reason: str,
    ) -> ControlEvent:
        event = ControlEvent(
            timestamp_s=time.perf_counter(),
            state=state,
            brake_state=brake_state,
            is_overriding=is_overriding,
            reason=reason,
            target_window="The Crew 2",
        )
        self.last_event = event
        self.event_log.append(event)
        return event
