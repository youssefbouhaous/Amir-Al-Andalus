"""Dynamic 2D lighting for dusk and night levels.

Technique (a classic "light map"):

1. Fill an off-screen surface with the ambient colour (dark blue at night).
2. Add every light as a radial gradient with additive blending.
3. Multiply the finished light map onto the rendered scene.

Where no light reaches, the scene takes on the ambient colour; under a torch
it keeps its true colours. Very bright sources additionally get a faint
additive "bloom" drawn directly onto the scene after the multiply, so flames
seem to glow rather than just being unshadowed.
"""

import math
from dataclasses import dataclass

import pygame

from core.settings import Color
from rendering.glow import blit_glow


@dataclass(frozen=True)
class Light:
    x: float
    y: float
    radius: float
    color: Color = (255, 214, 150)
    strength: float = 1.0
    # 0 = steady, 1 = strong flame flicker.
    flicker: float = 0.0
    bloom: float = 0.0


def flicker_factor(x: float, time: float, amount: float) -> float:
    """Cheap organic flicker: a few incommensurate sines keyed by position."""
    if amount <= 0:
        return 1.0
    seed = x * 0.013
    wave = (
        math.sin(time * 9.1 + seed * 7.0) * 0.5
        + math.sin(time * 15.7 + seed * 3.0) * 0.3
        + math.sin(time * 23.3 + seed) * 0.2
    )
    return 1.0 + wave * 0.12 * amount


class LightLayer:
    def __init__(self, size: tuple[int, int]) -> None:
        self._map = pygame.Surface(size)
        self._blooms: list[tuple[float, float, int, Color, float]] = []
        self.ambient: Color = (255, 255, 255)

    def begin(self, ambient: Color) -> None:
        self.ambient = ambient
        self._map.fill(ambient)
        self._blooms.clear()

    def add(self, light: Light, offset: tuple[int, int], time: float) -> None:
        factor = flicker_factor(light.x, time, light.flicker)
        sx, sy = light.x - offset[0], light.y - offset[1]
        radius = int(light.radius * factor)
        width, height = self._map.get_size()
        if sx + radius < 0 or sy + radius < 0 or sx - radius > width or sy - radius > height:
            return
        blit_glow(self._map, (sx, sy), radius, light.color, min(1.0, light.strength * factor))
        if light.bloom > 0:
            self._blooms.append((sx, sy, max(4, int(radius * 0.45)), light.color, light.bloom * factor))

    def apply(self, target: pygame.Surface) -> None:
        target.blit(self._map, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        for sx, sy, radius, color, strength in self._blooms:
            blit_glow(target, (sx, sy), radius, color, min(1.0, strength))
