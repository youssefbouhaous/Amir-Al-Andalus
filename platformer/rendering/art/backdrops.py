"""Backdrops: large painted walls behind the playfield for interior areas.

A level marks a rectangle as a backdrop zone (object type ``backdrop`` with
a ``style``). The terrain renderer asks this module to paint the whole zone
once and bakes it behind the tiles. Backdrops are deliberately darker and
lower in contrast than the foreground so the playable tiles stay readable.
"""

import math
import random
from collections.abc import Callable

import pygame

from core.settings import TILE_SIZE, Color
from rendering.art.kit import horseshoe_arch, mix, shade
from rendering.art.tiles import eight_point_star

T = TILE_SIZE


def _dim(surface: pygame.Surface, tint: Color = (150, 140, 170)) -> None:
    """Push a painted wall back: multiply toward a cool, dark tint."""
    surface.fill(tint, special_flags=pygame.BLEND_RGB_MULT)


def _zellige_dado(s: pygame.Surface, top: int, height: int, seed: int = 0) -> None:
    width = s.get_width()
    s.fill((236, 232, 220), (0, top, width, height))
    colors = ((28, 86, 168), (36, 138, 96), (34, 30, 40), (220, 170, 50))
    cell = 24
    for cy in range(top + cell // 2, top + height, cell):
        for index, cx in enumerate(range(cell // 2, width + cell, cell)):
            eight_point_star(s, colors[(index + cy // cell + seed) % 4], (cx, cy), 8)
            eight_point_star(s, (236, 232, 220), (cx, cy), 3)
    s.fill((140, 100, 60), (0, top, width, 3))
    s.fill((140, 100, 60), (0, top + height - 2, width, 2))


def _sebka(s: pygame.Surface, rect: pygame.Rect, color: Color, cell: int = 16) -> None:
    """Sebka: the lozenge lattice carved in Almohad and Nasrid stucco."""
    clip = s.get_clip()
    s.set_clip(rect)
    for x in range(rect.left - rect.height, rect.right + cell, cell):
        pygame.draw.line(s, color, (x, rect.bottom), (x + rect.height, rect.top), 2)
        pygame.draw.line(s, color, (x, rect.top), (x + rect.height, rect.bottom), 2)
    s.set_clip(clip)


def _arcade(s: pygame.Surface, floor: int, span: int, arch_radius: int, wall: Color, interior: Color,
            voussoirs: tuple[Color, Color] | None = None, column: Color = (230, 220, 196)) -> None:
    width = s.get_width()
    spring = floor - arch_radius * 2 - 18
    for index, cx in enumerate(range(span // 2, width + span, span)):
        opening = horseshoe_arch(cx, spring, arch_radius, floor)
        if voussoirs is not None:
            # Alternating red and white wedges, as in the Mezquita of Cordoba.
            outer = arch_radius + 9
            for k in range(20):
                a0 = math.radians(210 - k * 12)
                a1 = math.radians(210 - (k + 1) * 12)
                wedge = [
                    (cx + math.cos(a0) * (arch_radius - 1), spring - math.sin(a0) * (arch_radius - 1)),
                    (cx + math.cos(a0) * outer, spring - math.sin(a0) * outer),
                    (cx + math.cos(a1) * outer, spring - math.sin(a1) * outer),
                    (cx + math.cos(a1) * (arch_radius - 1), spring - math.sin(a1) * (arch_radius - 1)),
                ]
                pygame.draw.polygon(s, voussoirs[k % 2], wedge)
        else:
            pygame.draw.polygon(s, shade(wall, 0.12), [
                (x + (x - cx) * 0.18, y - 6 * (1 if y < spring else 0)) for x, y in opening
            ])
        pygame.draw.polygon(s, interior, opening)
        # Columns between the arches with capitals.
        col_x = cx + span // 2
        s.fill(column, (col_x - 4, spring - 4, 8, floor - spring + 4))
        s.fill(shade(column, -0.2), (col_x + 2, spring - 4, 2, floor - spring + 4))
        s.fill(shade(column, 0.1), (col_x - 7, spring - 10, 14, 6))
        s.fill(shade(column, -0.1), (col_x - 6, floor - 5, 12, 5))


def _paint_arcade(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    wall = (232, 216, 184)
    s.fill(wall)
    floor = height
    _zellige_dado(s, floor - T, T, seed)
    _arcade(s, floor - T, 128, 34, wall, (70, 52, 60))
    _sebka(s, pygame.Rect(0, 0, width, max(0, floor - T - 150)), shade(wall, -0.12))
    s.fill((196, 170, 130), (0, max(0, floor - T - 150), width, 4))
    _dim(s)


def _paint_salon(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    wall = (226, 196, 150)
    s.fill(wall)
    rng = random.Random(seed)
    # Ataurique: vegetal carving suggested by scrolls.
    for _ in range(width * height // 900):
        x, y = rng.randrange(width), rng.randrange(height)
        pygame.draw.arc(s, shade(wall, -0.12), (x, y, 14, 14), 0, math.pi * 1.4, 2)
    _arcade(s, height - 16, 112, 32, wall, (60, 38, 40), voussoirs=((176, 54, 44), (240, 226, 196)))
    s.fill((190, 150, 90), (0, height - 16, width, 16))
    s.fill((150, 110, 60), (0, height - 16, width, 3))
    _dim(s, (170, 150, 150))


def _paint_library(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    rng = random.Random(seed)
    s.fill((70, 44, 30))
    shelf_h = 40
    colors = ((150, 40, 40), (40, 90, 140), (50, 120, 70), (190, 150, 60), (100, 56, 120), (170, 100, 50))
    for y in range(height % shelf_h, height, shelf_h):
        s.fill((104, 68, 42), (0, y + shelf_h - 6, width, 6))
        s.fill((130, 88, 56), (0, y + shelf_h - 6, width, 2))
        x = 0
        while x < width:
            if rng.random() < 0.06:
                x += rng.randrange(8, 20)
                continue
            w = rng.randrange(4, 8)
            h = rng.randrange(20, 32)
            color = shade(rng.choice(colors), rng.uniform(-0.2, 0.1))
            if rng.random() < 0.08:
                pygame.draw.polygon(s, color, ((x, y + shelf_h - 6), (x + 4, y + shelf_h - 6 - h), (x + 4 + w, y + shelf_h - 6 - h + 2), (x + w, y + shelf_h - 6)))
            else:
                s.fill(color, (x, y + shelf_h - 6 - h, w, h))
                s.fill((210, 170, 80), (x + 1, y + shelf_h - 6 - h + 4, w - 2, 1))
            x += w + (1 if rng.random() < 0.3 else 0)
    # Vertical uprights every few metres.
    for x in range(0, width, 192):
        s.fill((90, 58, 36), (x, 0, 10, height))
        s.fill((120, 80, 50), (x, 0, 3, height))
    _dim(s, (170, 150, 150))


def _paint_clockwork(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    s.fill((96, 58, 44))
    for course in range(0, height, 10):
        offset = 0 if (course // 10) % 2 else 12
        s.fill((120, 72, 52), (0, course, width, 1))
        for x in range(offset, width, 24):
            s.fill((120, 72, 52), (x, course, 1, 10))
    rng = random.Random(seed)
    for _ in range(max(1, width // 220)):
        cx, cy = rng.randrange(width), rng.randrange(height)
        radius = rng.randrange(40, 90)
        _gear(s, (cx, cy), radius, (72, 46, 36), rng.uniform(0, 1))
    for x in range(64, width, 256):
        s.fill((64, 40, 28), (x, 0, 16, height))
        s.fill((84, 54, 38), (x, 0, 4, height))
    _dim(s, (160, 140, 150))


def _gear(s: pygame.Surface, center: tuple[float, float], radius: float, color: Color, phase: float = 0.0) -> None:
    cx, cy = center
    teeth = max(8, int(radius / 6))
    points = []
    for k in range(teeth * 2):
        a = phase + k * math.pi / teeth
        r = radius if k % 2 == 0 else radius * 0.84
        a2 = a + math.pi / teeth * 0.7
        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        points.append((cx + math.cos(a2) * r, cy + math.sin(a2) * r))
    pygame.draw.polygon(s, color, points)
    pygame.draw.circle(s, shade(color, 0.2), (round(cx), round(cy)), round(radius * 0.62))
    pygame.draw.circle(s, color, (round(cx), round(cy)), round(radius * 0.52))
    for k in range(6):
        a = phase + k * math.pi / 3
        pygame.draw.line(s, shade(color, 0.2), (cx, cy), (cx + math.cos(a) * radius * 0.55, cy + math.sin(a) * radius * 0.55), 5)
    pygame.draw.circle(s, shade(color, 0.3), (round(cx), round(cy)), round(radius * 0.14))


def _paint_houses(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    rng = random.Random(seed)
    x = 0
    walls = ((244, 238, 226), (248, 226, 170), (240, 214, 196), (236, 236, 230))
    while x < width:
        w = rng.randrange(128, 224)
        wall = rng.choice(walls)
        top = rng.randrange(0, 40)
        s.fill(wall, (x, top, w, height - top))
        s.fill((190, 120, 60), (x, top, w, 6))  # ochre cornice
        s.fill(shade(wall, -0.1), (x + w - 4, top, 4, height - top))
        # Windows with iron grilles and flowerpots.
        for wy in range(top + 30, height - 70, 76):
            for wx in range(x + 24, x + w - 30, 64):
                s.fill((60, 44, 48), (wx, wy, 22, 32))
                pygame.draw.ellipse(s, (60, 44, 48), (wx, wy - 8, 22, 18))
                for gx in range(wx + 4, wx + 22, 5):
                    pygame.draw.line(s, (30, 26, 30), (gx, wy - 4), (gx, wy + 32))
                s.fill((30, 26, 30), (wx - 3, wy + 30, 28, 3))
                for fx in range(wx - 1, wx + 22, 6):
                    pygame.draw.circle(s, (200, 40, 60) if rng.random() < 0.6 else (240, 200, 60), (fx + 2, wy + 28), 2)
        # A door at street level.
        if height > 96:
            dx = x + w // 2 - 16
            s.fill((110, 60, 40), (dx, height - 64, 32, 64))
            pygame.draw.ellipse(s, (110, 60, 40), (dx, height - 80, 32, 32))
            s.fill((80, 42, 28), (dx + 15, height - 64, 2, 64))
        x += w
    _dim(s, (170, 150, 160))


def _paint_cave(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    rng = random.Random(seed)
    s.fill((64, 58, 70))
    for _ in range(width * height // 500):
        x, y = rng.randrange(width), rng.randrange(height)
        r = rng.randrange(6, 22)
        pygame.draw.circle(s, shade((64, 58, 70), rng.uniform(-0.25, 0.15)), (x, y), r)
    for _ in range(width // 60):
        x = rng.randrange(width)
        pygame.draw.polygon(s, (50, 46, 56), ((x - 8, 0), (x + 8, 0), (x, rng.randrange(20, 60))))
    _dim(s, (170, 170, 190))


def _paint_cistern(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    s.fill((140, 80, 56))
    for course in range(0, height, 8):
        offset = 0 if (course // 8) % 2 else 10
        s.fill((170, 110, 80), (0, course, width, 1))
        for x in range(offset, width, 20):
            s.fill((170, 110, 80), (x, course, 1, 8))
    span = 96
    for cx in range(span // 2, width + span, span):
        pygame.draw.circle(s, (40, 24, 26), (cx, 44), 34)
        s.fill((40, 24, 26), (cx - 34, 44, 68, height))
        pygame.draw.circle(s, (200, 150, 100), (cx, 44), 36, 3)
        s.fill((110, 64, 44), (cx + span // 2 - 7, 0, 14, height))
    _dim(s, (150, 140, 170))


def _paint_palace_wall(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    wall = (222, 196, 160)
    s.fill(wall)
    dado = min(height // 3, 48)
    _zellige_dado(s, height - dado, dado, seed)
    _sebka(s, pygame.Rect(0, 36, width, max(0, height - dado - 60)), shade(wall, -0.14), 20)
    # Muqarnas frieze along the top: rows of little niches.
    for row in range(3):
        y = row * 10
        for x in range((row % 2) * 8, width, 16):
            pygame.draw.ellipse(s, shade(wall, -0.18 + row * 0.05), (x, y, 14, 12))
    s.fill((150, 110, 70), (0, 30, width, 4))
    # Tall pointed windows with lattice.
    for x in range(120, width - 60, 320):
        rect = pygame.Rect(x, 70, 44, max(40, height - dado - 110))
        pygame.draw.rect(s, (40, 30, 60), rect)
        pygame.draw.ellipse(s, (40, 30, 60), (x, 50, 44, 44))
        _sebka(s, rect, (120, 100, 90), 10)
    _dim(s, (150, 140, 180))


def _paint_court_arcade(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    wall = (230, 214, 186)
    s.fill((36, 28, 54))
    floor = height
    span = 72
    top = floor - 150
    s.fill(wall, (0, 0, width, max(0, top)))
    _sebka(s, pygame.Rect(0, 0, width, max(0, top - 10)), shade(wall, -0.15), 14)
    for cx in range(span // 2, width + span, span):
        # Lobed arch: a big arc with scalloped edge.
        pygame.draw.circle(s, wall, (cx, top), span // 2 + 2)
        pygame.draw.circle(s, (36, 28, 54), (cx, top + 10), span // 2 - 8)
        for k in range(7):
            a = math.pi + k * math.pi / 6
            pygame.draw.circle(s, wall, (round(cx + math.cos(a) * (span // 2 - 8)), round(top + 10 + math.sin(a) * (span // 2 - 8))), 5)
        s.fill(wall, (cx - span // 2, top, 4, 20))
        # Slender paired columns.
        for dx in (-3, 3):
            col = cx + span // 2 + dx
            s.fill((240, 236, 226), (col - 2, top + 16, 4, floor - top - 16))
        s.fill((220, 210, 190), (cx + span // 2 - 8, top + 10, 16, 8))
    _dim(s, (150, 140, 180))


def _paint_fortress(s: pygame.Surface, seed: int) -> None:
    width, height = s.get_size()
    base = (150, 70, 50)
    s.fill(base)
    for y in range(0, height, 16):
        s.fill(shade(base, -0.15), (0, y, width, 1))
    rng = random.Random(seed)
    for x in range(40, width, 150):
        y = rng.randrange(20, max(21, height - 80))
        s.fill((30, 20, 30), (x, y, 6, 30))
        s.fill((30, 20, 30), (x - 6, y + 12, 18, 6))
    _dim(s, (140, 130, 170))


BACKDROP_PAINTERS: dict[str, Callable[[pygame.Surface, int], None]] = {
    "arcade": _paint_arcade,
    "salon": _paint_salon,
    "library": _paint_library,
    "clockwork": _paint_clockwork,
    "houses": _paint_houses,
    "cave": _paint_cave,
    "cistern": _paint_cistern,
    "palace_wall": _paint_palace_wall,
    "court_arcade": _paint_court_arcade,
    "fortress": _paint_fortress,
}


def paint_backdrop(style: str, size: tuple[int, int], seed: int = 0) -> pygame.Surface:
    surface = pygame.Surface(size)
    painter = BACKDROP_PAINTERS.get(style, _paint_cave)
    painter(surface, seed)
    return surface


def gear_image(radius: int, color: Color) -> pygame.Surface:
    """A standalone gear for animated decor (rotated at runtime)."""
    size = radius * 2 + 4
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    _gear(s, (size / 2, size / 2), radius, color)
    return s
