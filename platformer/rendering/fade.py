from collections.abc import Callable
from enum import Enum, auto

import pygame

from core import settings

MAX_ALPHA = 255


class FadePhase(Enum):
    IDLE = auto()
    OUT = auto()  # getting darker
    IN = auto()   # getting lighter


class ScreenFade:
    """Fade to black, run a callback while the screen is black, fade back in.

    Hides jarring cuts like teleporting through a pipe or respawning.
    """

    def __init__(self, size: tuple[int, int], duration: float = settings.FADE_DURATION) -> None:
        self._overlay = pygame.Surface(size)
        self._overlay.fill(settings.FADE_COLOR)
        self._speed = MAX_ALPHA / duration
        self._alpha = 0.0
        self._phase = FadePhase.IDLE
        self._on_black: Callable[[], None] | None = None

    @property
    def is_fading_out(self) -> bool:
        return self._phase == FadePhase.OUT

    @property
    def active(self) -> bool:
        return self._phase != FadePhase.IDLE

    def fade_out_then(self, on_black: Callable[[], None]) -> None:
        if self._phase == FadePhase.OUT:
            return
        self._on_black = on_black
        self._phase = FadePhase.OUT

    def fade_in(self) -> None:
        self._alpha = MAX_ALPHA
        self._phase = FadePhase.IN

    def update(self, dt: float) -> None:
        if self._phase == FadePhase.OUT:
            self._alpha = min(MAX_ALPHA, self._alpha + self._speed * dt)
            if self._alpha >= MAX_ALPHA:
                self._phase = FadePhase.IN
                callback, self._on_black = self._on_black, None
                if callback is not None:
                    callback()
        elif self._phase == FadePhase.IN:
            self._alpha = max(0.0, self._alpha - self._speed * dt)
            if self._alpha <= 0:
                self._phase = FadePhase.IDLE

    def draw(self, surface: pygame.Surface) -> None:
        if self._alpha > 0:
            self._overlay.set_alpha(round(self._alpha))
            surface.blit(self._overlay, (0, 0))
