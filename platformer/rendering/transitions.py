"""Screen transitions that hide cuts (respawns, warps, scene changes).

Every transition has the same small interface as the original ScreenFade:
``fade_out_then(callback)`` covers the screen and runs the callback while it
is fully covered, then the screen is revealed again.

* ``ScreenFade``: plain fade through a dark colour.
* ``StarWipe``: the screen fills with eight-pointed zellige stars that grow
  in a diagonal sweep until they tile the whole screen, then shrink away.
* ``IrisWipe``: a circle closing on a point (the player), used for deaths.
"""

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum, auto

import pygame

from core import settings
from core.settings import Color

STAR_CELL = 60
STAR_SPREAD = 0.9  # how much of the duration the sweep's stagger takes
STAR_EDGE: Color = (214, 160, 60)


class FadePhase(Enum):
    IDLE = auto()
    OUT = auto()  # covering the screen
    IN = auto()   # revealing it again


class Transition(ABC):
    def __init__(self, duration: float) -> None:
        self._duration = max(0.01, duration)
        self._progress = 0.0  # 0 = clear, 1 = fully covered
        self._phase = FadePhase.IDLE
        self._on_black: Callable[[], None] | None = None

    @property
    def is_fading_out(self) -> bool:
        return self._phase == FadePhase.OUT

    @property
    def active(self) -> bool:
        return self._phase != FadePhase.IDLE

    @property
    def coverage(self) -> float:
        return self._progress

    def fade_out_then(self, on_black: Callable[[], None]) -> None:
        if self._phase == FadePhase.OUT:
            return
        self._on_black = on_black
        self._phase = FadePhase.OUT

    def fade_in(self) -> None:
        self._progress = 1.0
        self._phase = FadePhase.IN

    def update(self, dt: float) -> None:
        step = dt / self._duration
        if self._phase == FadePhase.OUT:
            self._progress = min(1.0, self._progress + step)
            if self._progress >= 1.0:
                self._phase = FadePhase.IN
                callback, self._on_black = self._on_black, None
                if callback is not None:
                    callback()
        elif self._phase == FadePhase.IN:
            self._progress = max(0.0, self._progress - step)
            if self._progress <= 0:
                self._phase = FadePhase.IDLE

    def draw(self, surface: pygame.Surface) -> None:
        if self._progress > 0:
            self._draw(surface, self._progress, self._phase == FadePhase.IN)

    @abstractmethod
    def _draw(self, surface: pygame.Surface, coverage: float, revealing: bool) -> None: ...


class ScreenFade(Transition):
    def __init__(self, size: tuple[int, int], duration: float = settings.FADE_DURATION) -> None:
        super().__init__(duration)
        self._overlay = pygame.Surface(size)
        self._overlay.fill(settings.FADE_COLOR)

    def _draw(self, surface: pygame.Surface, coverage: float, revealing: bool) -> None:
        self._overlay.set_alpha(round(255 * coverage))
        surface.blit(self._overlay, (0, 0))


def star_points(center: tuple[float, float], radius: float, rotation: float = 0.0) -> list[tuple[float, float]]:
    """Eight-pointed star (two overlapping squares) as a 16-vertex polygon."""
    cx, cy = center
    inner = radius * 0.765
    points = []
    for index in range(16):
        angle = rotation + index * math.pi / 8
        r = radius if index % 2 == 0 else inner
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    return points


class StarWipe(Transition):
    def __init__(
        self, size: tuple[int, int], duration: float = settings.TRANSITION_DURATION,
        color: Color = settings.FADE_COLOR,
    ) -> None:
        super().__init__(duration)
        self._size = size
        self._color = color
        width, height = size
        cols = width // STAR_CELL + 2
        rows = height // STAR_CELL + 2
        diagonal = width + height * 0.6
        self._cells = []
        for row in range(rows):
            for col in range(cols):
                # Offset every other row so the stars interlock like tiles.
                x = col * STAR_CELL + (STAR_CELL / 2 if row % 2 else 0)
                y = row * STAR_CELL * 0.87
                delay = (x + y * 0.6) / diagonal
                self._cells.append((x, y, delay))

    def _draw(self, surface: pygame.Surface, coverage: float, revealing: bool) -> None:
        eased = coverage * coverage * (3 - 2 * coverage)
        full_radius = STAR_CELL * 0.98
        edge_width = 2
        for x, y, delay in self._cells:
            d = 1.0 - delay if revealing else delay
            local = (eased * (1 + STAR_SPREAD) - d * STAR_SPREAD)
            if local <= 0:
                continue
            local = min(1.0, local)
            radius = full_radius * local
            rotation = (1.0 - local) * math.pi / 4
            points = star_points((x, y), radius, rotation)
            pygame.draw.polygon(surface, self._color, points)
            if local < 0.98:
                pygame.draw.polygon(surface, STAR_EDGE, points, edge_width)


class IrisWipe(Transition):
    """Circle closing on ``focus`` (screen coordinates)."""

    def __init__(self, size: tuple[int, int], duration: float = settings.TRANSITION_DURATION) -> None:
        super().__init__(duration)
        self._size = size
        self._overlay = pygame.Surface(size)
        self._key = (255, 0, 255)
        self._overlay.set_colorkey(self._key)
        self.focus = (size[0] / 2, size[1] / 2)

    def _draw(self, surface: pygame.Surface, coverage: float, revealing: bool) -> None:
        width, height = self._size
        fx, fy = self.focus
        max_radius = math.hypot(max(fx, width - fx), max(fy, height - fy)) + 4
        eased = 1.0 - (1.0 - coverage) ** 2
        radius = max(0.0, max_radius * (1.0 - eased))
        self._overlay.fill(settings.FADE_COLOR)
        if radius > 0.5:
            pygame.draw.circle(self._overlay, self._key, (round(fx), round(fy)), round(radius))
            pygame.draw.circle(self._overlay, STAR_EDGE, (round(fx), round(fy)), round(radius) + 2, 2)
        surface.blit(self._overlay, (0, 0))
