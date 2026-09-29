"""Cached soft sprites: additive glows and translucent soft circles.

Per-pixel alpha shapes are expensive to draw every frame in pygame, so each
distinct (radius, color, strength) combination is rendered once and reused.
Strength is quantized to a few levels to keep the cache small.
"""

import pygame

from core.settings import Color

GLOW_LEVELS = 10
SOFT_LEVELS = 12
MAX_CACHE = 1200

_glows: dict[tuple[int, Color, int], pygame.Surface] = {}
_soft: dict[tuple[int, Color, int], pygame.Surface] = {}


def _quantize(strength: float, levels: int) -> int:
    return max(0, min(levels, round(strength * levels)))


def glow(radius: int, color: Color, strength: float = 1.0) -> pygame.Surface | None:
    """A radial gradient on black, meant for ``BLEND_RGB_ADD``.

    Returns None when fully faded, so callers can skip the blit.
    """
    radius = max(1, int(radius))
    level = _quantize(strength, GLOW_LEVELS)
    if level == 0:
        return None
    key = (radius, color, level)
    surface = _glows.get(key)
    if surface is None:
        if len(_glows) > MAX_CACHE:
            _glows.clear()
        scale = level / GLOW_LEVELS
        size = radius * 2
        surface = pygame.Surface((size, size))
        surface.fill((0, 0, 0))
        for r in range(radius, 0, -1):
            # Quadratic falloff: bright core, long soft tail.
            falloff = (1.0 - r / radius) ** 2 * scale
            pygame.draw.circle(
                surface,
                (round(color[0] * falloff), round(color[1] * falloff), round(color[2] * falloff)),
                (radius, radius),
                r,
            )
        _glows[key] = surface
    return surface


def soft_circle(radius: int, color: Color, alpha: float = 1.0) -> pygame.Surface | None:
    """A translucent disc with a feathered edge (smoke, mist, shadows)."""
    radius = max(1, int(radius))
    level = _quantize(alpha, SOFT_LEVELS)
    if level == 0:
        return None
    key = (radius, color, level)
    surface = _soft.get(key)
    if surface is None:
        if len(_soft) > MAX_CACHE:
            _soft.clear()
        peak = 255 * level / SOFT_LEVELS
        size = radius * 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            edge = r / radius
            a = peak * (1.0 - edge ** 2.2)
            pygame.draw.circle(surface, (*color, round(a)), (radius, radius), r)
        _soft[key] = surface
    return surface


def blit_glow(
    target: pygame.Surface, center: tuple[float, float], radius: int, color: Color, strength: float = 1.0
) -> None:
    image = glow(radius, color, strength)
    if image is not None:
        target.blit(
            image, (round(center[0]) - radius, round(center[1]) - radius),
            special_flags=pygame.BLEND_RGB_ADD,
        )
