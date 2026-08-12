"""Keyboard input for manual CARLA driving."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualControl:
    """CARLA-independent driver command, kept easy to test."""

    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    hand_brake: bool = False
    reverse: bool = False
    manual_gear_shift: bool = False
    gear: int = 1


class KeyboardController:
    """Read pygame keys without embedding CARLA control logic."""

    def __init__(self, pygame_module=None):
        if pygame_module is None:
            import pygame as pygame_module
        self.pygame = pygame_module
        self.pygame.init()
        self.clock = self.pygame.time.Clock()
        self._throttle = 0.0
        self._steer = 0.0
        # A tiny input window ensures pygame receives keyboard focus.
        self.pygame.display.set_mode((360, 90))
        self.pygame.display.set_caption("SAFAR Manual Drive - click here for keyboard input")

    def poll(self, speed_mps=0.0):
        delta_seconds = self.clock.tick(60) / 1000.0
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                return None

        keys = self.pygame.key.get_pressed()
        if keys[self.pygame.K_ESCAPE]:
            return None

        accelerating = keys[self.pygame.K_w]
        braking_or_reversing = keys[self.pygame.K_s]
        reversing = braking_or_reversing and speed_mps < 0.25
        if accelerating:
            self._throttle = min(0.8, self._throttle + 1.8 * delta_seconds)
        elif reversing:
            self._throttle = min(0.5, self._throttle + 1.5 * delta_seconds)
        else:
            self._throttle = max(0.0, self._throttle - 3.0 * delta_seconds)

        steer_direction = (1 if keys[self.pygame.K_d] else 0) - (1 if keys[self.pygame.K_a] else 0)
        if steer_direction:
            self._steer = max(-0.7, min(0.7, self._steer + steer_direction * 2.5 * delta_seconds))
        else:
            self._steer *= max(0.0, 1.0 - 6.0 * delta_seconds)
        return ManualControl(
            throttle=self._throttle,
            brake=0.7 if braking_or_reversing and not reversing else 0.0,
            steer=self._steer,
            hand_brake=bool(keys[self.pygame.K_SPACE]),
            reverse=reversing,
            manual_gear_shift=reversing,
            gear=-1 if reversing else 1,
        )

    def close(self):
        self.pygame.quit()
