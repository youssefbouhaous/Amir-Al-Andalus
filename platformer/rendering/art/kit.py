"""Drawing toolkit for procedural art.

pygame.draw has no anti-aliasing for filled shapes, so sprites are drawn on a
``Canvas`` at several times their final size and smooth-scaled down at the
end (supersampling). Coordinates are given in final-size "design units" and
converted internally, so art code reads naturally at sprite scale.

Every shape can take an ``outline`` colour: the shape is drawn once expanded
in the outline colour, then filled. Drawing parts back-to-front this way
gives the cartoon look of outlined limbs overlapping each other.
"""

import math
import random
from collections.abc import Sequence

import pygame

from core.settings import Color

SUPERSAMPLE = 4
Point = tuple[float, float]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(a: Color, b: Color, t: float) -> Color:
    return (round(lerp(a[0], b[0], t)), round(lerp(a[1], b[1], t)), round(lerp(a[2], b[2], t)))


def shade(color: Color, amount: float) -> Color:
    """amount < 0 darkens toward black, > 0 lightens toward white."""
    if amount < 0:
        return mix(color, (0, 0, 0), -amount)
    return mix(color, (255, 255, 255), amount)


def rotate(point: Point, degrees: float) -> Point:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return point[0] * c - point[1] * s, point[0] * s + point[1] * c


def limb(start: Point, degrees: float, length: float) -> Point:
    """End of a limb hanging from ``start``; 0 deg = straight down, +90 = forward (+x)."""
    angle = math.radians(degrees)
    return start[0] + math.sin(angle) * length, start[1] + math.cos(angle) * length


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


class Canvas:
    def __init__(self, width: int, height: int, scale: int = SUPERSAMPLE, fringe: Color = (40, 26, 22)) -> None:
        self.width = width
        self.height = height
        self.scale = scale
        self.surface = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
        # Transparent pixels carry the outline colour, so smoothscale blends
        # edges toward it instead of toward black.
        self.surface.fill((*fringe, 0))

    # --- coordinate helpers ---------------------------------------------------
    def _p(self, point: Point) -> tuple[int, int]:
        return round(point[0] * self.scale), round(point[1] * self.scale)

    def _pts(self, points: Sequence[Point]) -> list[tuple[int, int]]:
        return [self._p(p) for p in points]

    def _r(self, value: float) -> int:
        return max(1, round(value * self.scale))

    # --- primitives -------------------------------------------------------------
    def circle(self, color: Color, center: Point, radius: float, outline: Color | None = None, width: float = 1.0) -> None:
        if outline is not None:
            pygame.draw.circle(self.surface, outline, self._p(center), self._r(radius + width))
        pygame.draw.circle(self.surface, color, self._p(center), self._r(radius))

    def ring(self, color: Color, center: Point, radius: float, width: float) -> None:
        pygame.draw.circle(self.surface, color, self._p(center), self._r(radius), self._r(width))

    def ellipse(self, color: Color, rect: tuple[float, float, float, float], outline: Color | None = None, width: float = 1.0) -> None:
        x, y, w, h = rect
        if outline is not None:
            pygame.draw.ellipse(
                self.surface, outline,
                (self._r(x - width), self._r(y - width), self._r(w + 2 * width), self._r(h + 2 * width)),
            )
        pygame.draw.ellipse(self.surface, color, (round(x * self.scale), round(y * self.scale), self._r(w), self._r(h)))

    def polygon(self, color: Color, points: Sequence[Point], outline: Color | None = None, width: float = 1.0) -> None:
        if len(points) < 3:
            return
        if outline is not None:
            self._outline_polygon(outline, points, width)
        pygame.draw.polygon(self.surface, color, self._pts(points))

    def _outline_polygon(self, color: Color, points: Sequence[Point], width: float) -> None:
        # A thick closed stroke plus round joints approximates an expanded shape.
        scaled = self._pts(points)
        stroke = self._r(width * 2)
        pygame.draw.polygon(self.surface, color, scaled)
        pygame.draw.lines(self.surface, color, True, scaled, stroke)
        radius = self._r(width)
        for point in scaled:
            pygame.draw.circle(self.surface, color, point, radius)

    def line(self, color: Color, start: Point, end: Point, width: float = 1.0) -> None:
        pygame.draw.line(self.surface, color, self._p(start), self._p(end), self._r(width))

    def lines(self, color: Color, points: Sequence[Point], width: float = 1.0, closed: bool = False) -> None:
        if len(points) >= 2:
            pygame.draw.lines(self.surface, color, closed, self._pts(points), self._r(width))

    def capsule(self, color: Color, start: Point, end: Point, radius: float, outline: Color | None = None, width: float = 1.0) -> None:
        """Thick line with round caps: the basic limb shape."""
        if outline is not None:
            self._capsule(outline, start, end, radius + width)
        self._capsule(color, start, end, radius)

    def _capsule(self, color: Color, start: Point, end: Point, radius: float) -> None:
        a, b = self._p(start), self._p(end)
        r = self._r(radius)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length > 0.5:
            nx, ny = -dy / length * r, dx / length * r
            pygame.draw.polygon(
                self.surface, color,
                ((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)),
            )
        pygame.draw.circle(self.surface, color, a, r)
        pygame.draw.circle(self.surface, color, b, r)

    def tapered(self, color: Color, points: Sequence[Point], start_radius: float, end_radius: float) -> None:
        """A polyline whose thickness shrinks along its length (tails, flames)."""
        count = len(points)
        for index in range(count - 1):
            t0 = index / max(1, count - 1)
            t1 = (index + 1) / max(1, count - 1)
            self._capsule(color, points[index], points[index + 1], lerp(start_radius, end_radius, (t0 + t1) / 2))

    def rect(self, color: Color, rect: tuple[float, float, float, float], radius: float = 0, outline: Color | None = None, width: float = 1.0) -> None:
        x, y, w, h = rect
        if outline is not None:
            pygame.draw.rect(
                self.surface, outline,
                (round((x - width) * self.scale), round((y - width) * self.scale),
                 self._r(w + 2 * width), self._r(h + 2 * width)),
                border_radius=self._r(radius + width) if radius else 0,
            )
        pygame.draw.rect(
            self.surface, color,
            (round(x * self.scale), round(y * self.scale), self._r(w), self._r(h)),
            border_radius=self._r(radius) if radius else 0,
        )

    def star(self, color: Color, center: Point, radius: float, points: int = 8, inner: float = 0.765,
             rotation: float = 0.0, outline: Color | None = None, width: float = 1.0) -> None:
        verts = star_polygon(center, radius, points, inner, rotation)
        self.polygon(color, verts, outline, width)

    def blit(self, image: pygame.Surface, topleft: Point) -> None:
        """Blit a final-size image, upscaled to canvas resolution."""
        scaled = pygame.transform.scale(image, (image.get_width() * self.scale, image.get_height() * self.scale))
        self.surface.blit(scaled, self._p(topleft))

    def finish(self) -> pygame.Surface:
        return pygame.transform.smoothscale(self.surface, (self.width, self.height))


def star_polygon(center: Point, radius: float, points: int = 8, inner: float = 0.765, rotation: float = 0.0) -> list[Point]:
    cx, cy = center
    verts = []
    for index in range(points * 2):
        angle = math.radians(rotation) + index * math.pi / points - math.pi / 2
        r = radius if index % 2 == 0 else radius * inner
        verts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    return verts


def horseshoe_arch(center_x: float, spring_y: float, radius: float, bottom_y: float, segments: int = 28) -> list[Point]:
    """Outline of a Moorish horseshoe arch opening: a circle continuing past
    its equator (the 'horseshoe'), then straight jambs down to ``bottom_y``."""
    points: list[Point] = []
    # The arc spans about 240 degrees: from lower-left, over the top, to lower-right.
    start = math.radians(210)
    end = math.radians(-30)
    for index in range(segments + 1):
        angle = start + (end - start) * index / segments
        points.append((center_x + math.cos(angle) * radius, spring_y - math.sin(angle) * radius))
    jamb = radius * math.cos(math.radians(30)) * 0.86
    points.append((center_x + jamb, bottom_y))
    points.append((center_x - jamb, bottom_y))
    return points


def vertical_gradient(size: tuple[int, int], stops: Sequence[tuple[float, Color]]) -> pygame.Surface:
    """Multi-stop top-to-bottom gradient, rendered once."""
    width, height = size
    column = pygame.Surface((1, max(1, height)))
    stops = sorted(stops)
    for y in range(height):
        t = y / max(1, height - 1)
        for index in range(len(stops) - 1):
            t0, c0 = stops[index]
            t1, c1 = stops[index + 1]
            if t0 <= t <= t1:
                local = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                column.set_at((0, y), mix(c0, c1, local))
                break
        else:
            column.set_at((0, y), stops[-1][1] if t > stops[-1][0] else stops[0][1])
    return pygame.transform.scale(column, (width, height))


def noise_texture(size: tuple[int, int], base: Color, variation: int, seed: int, grain: int = 1) -> pygame.Surface:
    """Flat colour with subtle per-pixel variation (stone, sand, parchment)."""
    width, height = size
    rng = random.Random(seed)
    surface = pygame.Surface(size)
    surface.fill(base)
    for y in range(0, height, grain):
        for x in range(0, width, grain):
            delta = rng.randint(-variation, variation)
            if delta:
                color = tuple(max(0, min(255, c + delta)) for c in base)
                surface.fill(color, (x, y, grain, grain))
    return surface


def hash01(*values: int) -> float:
    """Deterministic pseudo-random number in [0, 1) from integers (tile coords)."""
    h = 2166136261
    for value in values:
        h = ((h ^ (value & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFFFF) / 0x1000000
