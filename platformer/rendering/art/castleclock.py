"""The Castle of Borrowed Hours: level 3's enchanted castle clock, and its keeper.

After al-Jazari's castle clock (1206): a gateway of twelve doors, one opening
each hour; a zodiac arch along which the sun and the moon ride the same
track; falcons that drop balls onto cymbals; and twelve glass discs that
light, one by one, through the hours of the night. Al-Muqallid has made it
borrow hours from whoever stands before it, and chained the library's keeper
- a gentle automaton made like a book - into its works.

Coordinates are relative to the keeper's feet: x = 0 at the keeper, y = 0 on
the floor, negative y up. The great facade is painted once (supersampled)
and drawn behind the level's tiles; everything that moves is drawn live.
"""

import math
import random
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas, mix
from rendering.glow import blit_glow

Color = tuple[int, int, int]
Point = tuple[float, float]

EDGE: Color = (23, 22, 29)
BONE: Color = (241, 229, 200)
PAPER: Color = (255, 248, 225)
SHADE: Color = (151, 137, 118)
RED: Color = (174, 43, 59)
RED_DARK: Color = (85, 28, 40)
IRON: Color = (42, 39, 48)
STEEL: Color = (115, 112, 118)
BRASS: Color = (166, 127, 83)
GOLD: Color = (232, 190, 96)
GOLD_DARK: Color = (150, 108, 46)
STONE: Color = (176, 166, 152)
STONE_LIGHT: Color = (214, 206, 190)
STONE_DARK: Color = (112, 102, 98)
LAPIS: Color = (34, 52, 120)
LAPIS_DEEP: Color = (18, 26, 70)
TURQUOISE: Color = (60, 176, 176)
WALNUT: Color = (70, 42, 30)
WALNUT_DARK: Color = (40, 24, 20)
MOON: Color = (220, 232, 255)
MOONLIGHT: Color = (150, 184, 255)
SUN: Color = (255, 206, 110)
LAMP: Color = (255, 196, 110)

ARCH_CENTER: Point = (0.0, -250.0)
ARCH_OUTER, ARCH_INNER = 214.0, 186.0
TRACK = 200.0                                  # the groove the sun and moon ride in
LAMP_RADIUS = 162.0
DOOR_XS = tuple(-242.0 + 44.0 * k for k in range(12))
DOOR_TOP, DOOR_BOTTOM = -252.0, -188.0
COLUMNS = (-284.0, 284.0)
FALCON_Y = -312.0
TREADLES = (-96.0, 0.0, 96.0)

FACADE_SIZE = (780, 560)
FACADE_ORIGIN = (390, 540)


def smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lamp_points() -> list[Point]:
    """Twelve glass discs on an arc inside the zodiac arch (first hour on the left)."""
    cx, cy = ARCH_CENTER
    points = []
    for k in range(12):
        a = math.radians(196 + k * (148 / 11))
        points.append((cx + math.cos(a) * LAMP_RADIUS, cy + math.sin(a) * LAMP_RADIUS))
    return points


def track_point(angle: float) -> Point:
    """A point on the sun-and-moon track; ``angle`` in degrees, 270 = top of the arch."""
    cx, cy = ARCH_CENTER
    a = math.radians(angle)
    return cx + math.cos(a) * TRACK, cy + math.sin(a) * TRACK


def _arch_points(cx: float, cy: float, radius: float, steps: int = 40) -> list[Point]:
    return [(cx + math.cos(math.pi + math.pi * k / steps) * radius, cy + math.sin(math.pi + math.pi * k / steps) * radius)
            for k in range(steps + 1)]


def _pointed_arch(cx: float, bottom: float, width: float, height: float) -> list[Point]:
    half = width / 2
    spring = bottom - height * 0.6
    left = [(cx - half, bottom), (cx - half, spring)]
    for k in range(1, 8):
        u = k / 8
        left.append((cx - half + half * math.sin(u * math.pi / 2), spring - (height * 0.4) * math.sin(u * math.pi / 2) ** 1.4))
    right = [(2 * cx - x, y) for x, y in reversed(left)]
    return left + [(cx, bottom - height)] + right


@lru_cache(maxsize=None)
def facade() -> pygame.Surface:
    """Bookcases, columns, the gallery of doors, the zodiac arch and the carved plinth."""
    w, h = FACADE_SIZE
    ox, oy = FACADE_ORIGIN
    c = Canvas(w, h, scale=3, fringe=EDGE)

    def P(x: float, y: float) -> Point:
        return ox + x, oy + y

    def PS(points) -> list[Point]:  # noqa: ANN001
        return [P(x, y) for x, y in points]

    rng = random.Random(1206)
    # --- the library: tall bookcases full of books on both sides ----------------------------------
    for side in (-1, 1):
        x0 = side * 300 - (72 if side > 0 else 0)
        x0 = -374 if side < 0 else 302
        c.rect(WALNUT_DARK, (*P(x0, -396), 72, 396), 2, EDGE, 1.4)
        c.polygon(WALNUT, PS([(x0 - 4, -396), (x0 + 76, -396), (x0 + 36, -424)]), EDGE, 1.2)
        c.circle(GOLD, P(x0 + 36, -412), 4, EDGE, 0.8)
        for shelf in range(7):
            top = -388 + shelf * 55
            c.rect(WALNUT, (*P(x0 + 4, top + 46), 64, 5), 0, EDGE, 0.6)
            bx = x0 + 7
            while bx < x0 + 64:
                bw = rng.uniform(5, 9)
                bh = rng.uniform(30, 44)
                lean = rng.random() < 0.12
                color = rng.choice((RED, RED_DARK, LAPIS, (52, 96, 70), (170, 120, 50), (96, 60, 90), BONE))
                if lean:
                    c.polygon(color, PS([(bx, top + 46), (bx + bw, top + 46), (bx + bw + 8, top + 46 - bh + 2), (bx + 8, top + 46 - bh)]), EDGE, 0.6)
                    bx += bw + 9
                else:
                    c.rect(color, (*P(bx, top + 46 - bh), bw, bh), 0.6, EDGE, 0.5)
                    c.line(GOLD, P(bx + 1, top + 46 - bh + 5), P(bx + bw - 1, top + 46 - bh + 5), 0.7)
                    c.line(GOLD, P(bx + 1, top + 40), P(bx + bw - 1, top + 40), 0.7)
                    bx += bw + 0.6
    # --- the gallery wall: lapis tiles with a faint star lattice ----------------------------------------
    c.rect(LAPIS_DEEP, (*P(-272, -268), 544, 210), 0, EDGE, 1.4)
    for row in range(5):
        for col in range(13):
            x = -264 + col * 44 + (row % 2) * 22
            y = -246 + row * 42
            if -268 < x < 268:
                c.star(mix(LAPIS, LAPIS_DEEP, 0.3), P(x, y), 11, 8, 0.6, 0.39)
    # Twelve door frames, each a pointed arch with a gilt border (the doors swing live).
    for x in DOOR_XS:
        arch = _pointed_arch(x, DOOR_BOTTOM, 34, DOOR_BOTTOM - DOOR_TOP)
        c.polygon(GOLD_DARK, PS([(px + (2 if px > x else -2) if py > DOOR_TOP + 4 else px, py + (2 if py > DOOR_TOP + 4 else -2))
                                 for px, py in arch]))
        c.polygon(LAPIS_DEEP, PS(arch))
        c.lines(GOLD, PS(arch), 1.2, closed=True)
    c.rect(GOLD, (*P(-272, -186), 544, 6), 0, EDGE, 0.8)
    c.rect(GOLD, (*P(-272, -272), 544, 6), 0, EDGE, 0.8)
    # --- the zodiac arch: a band of lapis between gilt rims, twelve enamel signs ---------------------------
    cx, cy = ARCH_CENTER
    outer = _arch_points(cx, cy, ARCH_OUTER + 8)
    inner = _arch_points(cx, cy, ARCH_INNER - 6)
    c.polygon(STONE, PS(outer + list(reversed(inner))), EDGE, 1.4)
    band_outer = _arch_points(cx, cy, ARCH_OUTER)
    band_inner = _arch_points(cx, cy, ARCH_INNER)
    c.polygon(LAPIS, PS(band_outer + list(reversed(band_inner))))
    c.lines(GOLD, PS(band_outer), 1.6)
    c.lines(GOLD, PS(band_inner), 1.6)
    c.lines(GOLD_DARK, PS(_arch_points(cx, cy, TRACK)), 1.0)
    # The tympanum inside the arch: night sky with a few painted stars.
    sky = _arch_points(cx, cy, ARCH_INNER - 7)
    c.polygon((14, 20, 52), PS(sky))
    for _ in range(40):
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        r = rng.uniform(40, ARCH_INNER - 14)
        c.circle((210, 214, 255) if rng.random() < 0.7 else GOLD, P(cx + math.cos(a) * r, cy + math.sin(a) * r), rng.uniform(0.6, 1.4))
    for k in range(12):
        a = math.pi + math.pi * (k + 0.5) / 12
        px, py = cx + math.cos(a) * (TRACK + 0.5), cy + math.sin(a) * (TRACK + 0.5)
        c.circle(GOLD, P(px, py), 8.5, EDGE, 0.8)
        c.circle(TURQUOISE if k % 2 else RED, P(px, py), 6.2)
        _sign(c, k, P(px, py))
    # Two marble columns that carry the falcons, with gilt capitals.
    for x in COLUMNS:
        c.rect(STONE_LIGHT, (*P(x - 12, FALCON_Y + 12), 24, -FALCON_Y - 76), 2, EDGE, 1.2)
        c.rect(STONE, (*P(x + 4, FALCON_Y + 14), 6, -FALCON_Y - 80))
        for k in range(5):
            c.line(STONE_DARK, P(x - 7 + k * 3.5, FALCON_Y + 22), P(x - 7 + k * 3.5, -72), 0.6)
        c.polygon(GOLD, PS([(x - 18, FALCON_Y + 12), (x + 18, FALCON_Y + 12), (x + 12, FALCON_Y + 2), (x - 12, FALCON_Y + 2)]), EDGE, 1.0)
        c.rect(GOLD_DARK, (*P(x - 14, FALCON_Y + 2), 28, 5), 1, EDGE, 0.6)
    # --- the plinth: carved stone, an inscription band, and three arched niches for the drives -------------
    c.rect(STONE, (*P(-304, -68), 608, 68), 2, EDGE, 1.4)
    c.rect(STONE_LIGHT, (*P(-300, -66), 600, 7), 0)
    c.rect(GOLD, (*P(-304, -60), 608, 4), 0)
    for k in range(48):
        x = -296 + k * 12.4
        c.lines(LAPIS, PS([(x, -50), (x + 3, -54), (x + 6, -50), (x + 9, -54)]), 0.8)
    for x in TREADLES:
        niche = _pointed_arch(x, 0, 74, 62)
        c.polygon(IRON, PS(niche), EDGE, 1.2)
        c.lines(GOLD, PS(niche), 1.0)
    return c.finish()


def _sign(c: Canvas, k: int, center: Point) -> None:
    """Tiny gold marks standing for the twelve signs."""
    x, y = center
    kind = k % 4
    if kind == 0:
        c.circle(GOLD, (x, y), 2.4)
    elif kind == 1:
        c.circle(GOLD, (x - 1, y), 2.8)
        c.circle(TURQUOISE if k % 2 else RED, (x + 0.6, y - 0.4), 2.4)
    elif kind == 2:
        c.star(GOLD, (x, y), 3.2, 5, 0.45)
    else:
        c.lines(GOLD, [(x - 3, y + 2), (x, y - 3), (x + 3, y + 2)], 0.9)


# --- moving parts of the clock ------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def door_leaf(open_step: int) -> pygame.Surface:
    """A door leaf seen swinging open (0 = shut .. 4 = wide open, edge-on)."""
    width = 32
    height = round(DOOR_BOTTOM - DOOR_TOP) - 2
    c = Canvas(width + 4, height + 4, scale=4, fringe=EDGE)
    squash = 1.0 - open_step / 4 * 0.85
    leaf_w = max(3.0, width * squash)
    arch = _pointed_arch(2 + leaf_w / 2, height + 2, leaf_w, height)
    c.polygon(RED_DARK, arch, EDGE, 0.9)
    c.lines(GOLD, [(x, y) for x, y in arch], 0.7, closed=True)
    if squash > 0.4:
        c.star(GOLD, (2 + leaf_w / 2, height * 0.55), min(7.0, leaf_w * 0.24), 8, 0.6)
        c.circle(GOLD, (2 + leaf_w * 0.85, height * 0.62), 1.3)
    return c.finish()


@lru_cache(maxsize=None)
def falcon(lean: int, holding: bool) -> pygame.Surface:
    """A gilt falcon on its column; ``lean`` 0..3 tips it to drop its ball."""
    c = Canvas(44, 44, scale=4, fringe=EDGE)
    angle = math.radians(lean * 15)
    cx, cy = 22.0, 30.0

    def R(x: float, y: float) -> Point:
        dx, dy = x - cx, y - cy
        return cx + dx * math.cos(angle) - dy * math.sin(angle), cy + dx * math.sin(angle) + dy * math.cos(angle)

    c.polygon(GOLD_DARK, [R(24, 26), R(38, 34), R(36, 38), R(22, 34)], EDGE, 0.7)
    c.ellipse(GOLD, (cx - 9, cy - 9, 18, 16), EDGE, 0.8)
    c.polygon(GOLD_DARK, [R(22, 22), R(33, 25), R(28, 34), R(18, 31)], EDGE, 0.6)
    c.circle(GOLD, R(13, 18), 5.4, EDGE, 0.8)
    c.polygon(BONE, [R(8, 17), R(3, 20), R(8, 21)], EDGE, 0.5)
    c.circle(EDGE, R(12, 17), 1.1)
    if holding:
        c.circle(BONE, R(3, 24), 3.4, EDGE, 0.7)
    return c.finish()


def draw_cymbal(surface: pygame.Surface, center: Point, ring: float) -> None:
    x, y = center
    shake = math.sin(ring * 60) * 3 * ring
    pygame.draw.ellipse(surface, EDGE, (x - 17, y - 5 + shake, 34, 10))
    pygame.draw.ellipse(surface, GOLD, (x - 16, y - 4 + shake, 32, 8))
    pygame.draw.ellipse(surface, (255, 236, 170), (x - 8, y - 3 + shake, 10, 3))
    if ring > 0:
        for k in range(3):
            r = 14 + k * 9 + (1 - ring) * 30
            pygame.draw.ellipse(surface, (255, 236, 170), (x - r, y - r * 0.4, r * 2, r * 0.8), 1)


def draw_disc(surface: pygame.Surface, center: Point, kind: str, t: float, strength: float = 1.0) -> None:
    """The sun or the moon riding the arch."""
    x, y = center
    if kind == "moon":
        blit_glow(surface, center, 42, MOONLIGHT, 0.55 * strength)
        pygame.draw.circle(surface, EDGE, (round(x), round(y)), 15)
        pygame.draw.circle(surface, MOON, (round(x), round(y)), 14)
        pygame.draw.circle(surface, (176, 190, 226), (round(x + 4), round(y + 3)), 4)
        pygame.draw.circle(surface, (190, 204, 236), (round(x - 5), round(y - 2)), 3)
        pygame.draw.circle(surface, (255, 255, 255), (round(x - 6), round(y - 6)), 2)
    else:
        blit_glow(surface, center, 46, SUN, 0.7 * strength)
        for k in range(12):
            a = t * 0.6 + k * math.tau / 12
            r1, r2 = 15, 21 + 3 * math.sin(t * 4 + k)
            pygame.draw.line(surface, (255, 180, 80), (x + math.cos(a) * r1, y + math.sin(a) * r1),
                             (x + math.cos(a) * r2, y + math.sin(a) * r2), 3)
        pygame.draw.circle(surface, EDGE, (round(x), round(y)), 15)
        pygame.draw.circle(surface, SUN, (round(x), round(y)), 14)
        pygame.draw.circle(surface, (255, 246, 210), (round(x - 4), round(y - 4)), 6)


def draw_lamp(surface: pygame.Surface, center: Point, lit: float, t: float, urgent: bool = False) -> None:
    x, y = center
    if lit > 0.02:
        pulse = 0.85 + 0.15 * math.sin(t * (12 if urgent else 4) + x)
        blit_glow(surface, center, round(16 + 6 * lit), LAMP if not urgent else (255, 120, 90), 0.8 * lit * pulse)
    pygame.draw.circle(surface, EDGE, (round(x), round(y)), 8)
    pygame.draw.circle(surface, GOLD_DARK, (round(x), round(y)), 7)
    glass = mix((40, 46, 90), (255, 226, 160) if not urgent else (255, 150, 120), lit)
    pygame.draw.circle(surface, glass, (round(x), round(y)), 5)
    pygame.draw.circle(surface, (255, 255, 255), (round(x - 2), round(y - 2)), 1)


def draw_chain(surface: pygame.Surface, a: Point, b: Point, t: float, strength: float, sag: float = 26.0) -> None:
    """A chain of glowing script: little letters linked hand to anchor, light running along it."""
    (ax, ay), (bx, by) = a, b
    mx, my = (ax + bx) / 2, max(ay, by) + sag
    count = max(4, int(math.hypot(bx - ax, by - ay) / 11))
    points = []
    for k in range(count + 1):
        u = k / count
        points.append(((1 - u) ** 2 * ax + 2 * (1 - u) * u * mx + u * u * bx,
                       (1 - u) ** 2 * ay + 2 * (1 - u) * u * my + u * u * by))
    for k in range(count):
        (x1, y1), (x2, y2) = points[k], points[k + 1]
        x, y = (x1 + x2) / 2, (y1 + y2) / 2
        glow = 0.5 + 0.5 * math.sin(t * 5 - k * 0.7)
        color = mix((90, 110, 190), (210, 226, 255), glow * strength)
        kind = k % 3
        blit_glow(surface, (x, y), 10, MOONLIGHT, (0.25 + 0.45 * glow) * strength)
        if kind == 0:
            pygame.draw.ellipse(surface, EDGE, (x - 6, y - 4, 12, 8), 4)
            pygame.draw.ellipse(surface, color, (x - 5, y - 3, 10, 6), 2)
        elif kind == 1:
            pygame.draw.line(surface, EDGE, (x - 2, y - 6), (x + 2, y + 6), 4)
            pygame.draw.line(surface, color, (x - 2, y - 5), (x + 2, y + 5), 2)
            pygame.draw.circle(surface, color, (round(x + 4), round(y - 4)), 1)
        else:
            pygame.draw.arc(surface, EDGE, (x - 6, y - 6, 12, 12), 0.3, 2.8, 4)
            pygame.draw.arc(surface, color, (x - 5, y - 5, 10, 10), 0.3, 2.8, 2)


# --- the keeper -------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def keeper_body() -> pygame.Surface:
    """The keeper's body: a great closed codex standing upright, tooled in gold."""
    c = Canvas(110, 150, scale=4, fringe=EDGE)
    # Page edges on the right, spine bands on the left, the oxblood cover between.
    c.rect(PAPER, (78, 12, 12, 120), 2, EDGE, 1.0)
    for k in range(10):
        c.line(SHADE, (80, 16 + k * 12), (88, 16 + k * 12), 0.5)
    c.rect(RED_DARK, (14, 6, 68, 132), 4, EDGE, 1.2)
    c.rect(RED, (20, 12, 56, 120), 3)
    c.rect(GOLD, (24, 16, 48, 112), 2)
    c.rect(RED, (26, 18, 44, 108), 2)
    c.star(GOLD, (48, 66), 16, 8, 0.6, 0.39, GOLD_DARK, 0.8)
    c.star(RED_DARK, (48, 66), 9, 8, 0.6, 0.39)
    c.circle(TURQUOISE, (48, 66), 3.4, EDGE, 0.6)
    for y in (30, 102):
        c.lines(GOLD, [(30, y), (40, y - 6), (48, y), (56, y - 6), (66, y)], 1.0)
    c.rect(IRON, (8, 8, 9, 128), 2, EDGE, 0.8)
    for y in (24, 52, 80, 108):
        c.rect(GOLD, (7, y, 11, 5), 1, EDGE, 0.5)
    return c.finish()


@lru_cache(maxsize=None)
def keeper_head(blink: int) -> pygame.Surface:
    """A crescent-moon mask with two lantern eyes; ``blink`` 0 open, 1 half, 2 shut."""
    c = Canvas(80, 76, scale=4, fringe=EDGE)
    cx, cy = 40.0, 44.0
    c.circle(BONE, (cx, cy), 27, EDGE, 1.4)
    c.circle(PAPER, (cx - 12, cy - 4), 10)
    c.lines(GOLD, [(cx - 23, cy + 10), (cx - 12, cy + 19), (cx + 2, cy + 22)], 1.2)
    for ex, ey in ((cx - 14, cy + 1), (cx - 3, cy + 9)):
        c.polygon(IRON, [(ex - 4, ey + 4), (ex - 4, ey - 1), (ex, ey - 6), (ex + 4, ey - 1), (ex + 4, ey + 4)], EDGE, 0.6)
        if blink < 2:
            c.polygon(LAMP if blink == 0 else GOLD_DARK, [(ex - 2.6, ey + 3), (ex - 2.6, ey), (ex, ey - (4 if blink == 0 else 1.5)),
                                                          (ex + 2.6, ey), (ex + 2.6, ey + 3)])
    c.circle(GOLD, (cx - 22, cy - 18), 2.4, EDGE, 0.5)
    image = c.finish()
    # Cut the crescent: the moon's dark bite is truly empty, so the clock shows through it.
    bite = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    bite.fill((255, 255, 255, 255))
    pygame.draw.circle(bite, (255, 255, 255, 0), (round(cx + 15), round(cy - 9)), 21)
    image.blit(bite, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    rim = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    pygame.draw.arc(rim, (*GOLD, 255), (cx + 15 - 22, cy - 9 - 22, 44, 44), math.radians(150), math.radians(290), 2)
    rim_mask = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(rim_mask, (255, 255, 255, 255), (round(cx), round(cy)), 27)
    rim.blit(rim_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    image.blit(rim, (0, 0))
    return image


def draw_book_crown(surface: pygame.Surface, center: Point, t: float, open_: float = 0.0) -> None:
    """An open book worn as a crown; its pages riffle in the clock's draught."""
    x, y = center
    spread = 24 + 10 * open_
    pygame.draw.polygon(surface, EDGE, [(x - spread - 2, y - 2), (x, y + 6), (x + spread + 2, y - 2), (x + spread, y + 5), (x, y + 12), (x - spread, y + 5)])
    pygame.draw.polygon(surface, RED_DARK, [(x - spread, y), (x, y + 7), (x + spread, y), (x + spread - 1, y + 4), (x, y + 10), (x - spread + 1, y + 4)])
    for k in range(5):
        lift = math.sin(t * 3 + k * 0.9) * 0.5 + 0.5
        for side in (-1, 1):
            tip = (x + side * (spread - 3 - k * 2), y - 12 - lift * 10 - k)
            pygame.draw.polygon(surface, PAPER if k % 2 else BONE, [(x, y + 6), (x + side * (spread - 2 - k * 3), y + 1), tip])
            pygame.draw.line(surface, SHADE, (x, y + 6), tip, 1)


def keeper_arm(surface: pygame.Surface, root: Point, tip: Point, side: int, closed: float, strength: float) -> None:
    """Two gilt links (the same reach as the clock's hands) and a hand of page-fingers at ``tip``."""
    a, b = pygame.Vector2(root), pygame.Vector2(tip)
    delta = b - a
    distance = max(1.0, delta.length())
    normal = pygame.Vector2(-delta.y, delta.x) / distance
    # Elbows lift up and outward, like long arms reaching down from the shoulders.
    elbow = (a + b) * 0.5 - normal * side * math.sqrt(max(0.0, 119 ** 2 - (distance / 2) ** 2))
    for start, end in ((a, elbow), (elbow, b)):
        pygame.draw.line(surface, EDGE, start, end, 11)
        pygame.draw.line(surface, GOLD_DARK, start, end, 8)
        pygame.draw.line(surface, GOLD, start, end, 3)
        for f in (0.3, 0.7):
            p = start.lerp(end, f)
            pygame.draw.circle(surface, RED_DARK, (round(p.x), round(p.y)), 3)
    for p, r in ((a, 7), (elbow, 6)):
        pygame.draw.circle(surface, EDGE, (round(p.x), round(p.y)), r + 1)
        pygame.draw.circle(surface, GOLD, (round(p.x), round(p.y)), r)
        pygame.draw.circle(surface, RED, (round(p.x), round(p.y)), max(2, r // 2))
    # The hand: a cuff and five long page-fingers (the hitbox is the whole hand).
    x, y = b
    pygame.draw.rect(surface, EDGE, (x - 26, y - 12, 52, 24), border_radius=6)
    pygame.draw.rect(surface, RED_DARK, (x - 24, y - 10, 48, 20), border_radius=5)
    pygame.draw.line(surface, GOLD, (x - 22, y - 6), (x + 22, y - 6), 2)
    if strength > 0:
        blit_glow(surface, (x, y), 22, MOONLIGHT, 0.35 * strength)
    for k in range(5):
        px = x - 20 + k * 10
        extension = 9 + 9 * (1 - closed)
        tip_x, tip_y = px + side * 3, y + extension
        pygame.draw.polygon(surface, EDGE, [(px - 4, y - 2), (px + 4, y - 2), (tip_x + 2, tip_y + 1), (tip_x - 2, tip_y + 1)])
        pygame.draw.polygon(surface, PAPER if k % 2 else BONE, [(px - 3, y - 1), (px + 3, y - 1), (tip_x + 1, tip_y), (tip_x - 1, tip_y)])
