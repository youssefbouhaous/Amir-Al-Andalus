"""The Sky-Noria of level 4: a water-wheel that pours the aqueduct's river into the sky.

Al-Jazari describes water-raising machines worked by a beast walking round a
platform: its horizontal gear turns a vertical one on the axle of a wheel of
pots, and the pots lift the water into an aqueduct. (In one of them a wooden
cow seems to do the work while a hidden stream does it in secret.) The thief's
copy is colossal and enchanted: a noria taller than the palace walls, turned by
a brass ox on a tower, whose pots throw the water not into the aqueduct but up
into the sky, where it flows away as a river among the clouds.

Coordinates are relative to the wheel's foot: x = 0 under the hub, y = 0 on
the stage floor (negative is up). Static parts are painted once (supersampled)
and cached; the wheel turns through cached rotations of one painted image,
because its 24 pots, spokes and braces repeat every 15 degrees.
"""

import math
import random
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas, horseshoe_arch, shade
from rendering.glow import blit_glow

Color = tuple[int, int, int]
Point = tuple[float, float]

OUTLINE: Color = (52, 32, 24)
WOOD: Color = (112, 70, 42)
WOOD_DARK: Color = (78, 46, 28)
WOOD_LIGHT: Color = (156, 104, 62)
BRASS: Color = (208, 152, 68)
BRASS_DARK: Color = (148, 96, 40)
BRASS_LIGHT: Color = (255, 222, 148)
GOLD: Color = (250, 204, 96)
TURQUOISE: Color = (40, 184, 178)
TURQUOISE_LIGHT: Color = (130, 236, 222)
LAPIS: Color = (44, 76, 164)
CLAY: Color = (198, 106, 64)
CLAY_DARK: Color = (148, 72, 42)
CLAY_LIGHT: Color = (232, 150, 98)
GLAZE: Color = (238, 232, 214)
STONE: Color = (222, 200, 162)
STONE_DARK: Color = (180, 152, 116)
STONE_LIGHT: Color = (242, 228, 198)
BRICK: Color = (184, 78, 58)
RIVER: Color = (96, 196, 232)
RIVER_DEEP: Color = (36, 112, 168)
RIVER_LIGHT: Color = (214, 246, 255)
MAGIC: Color = (110, 236, 230)      # the enchantment's glow (eyes, hub stone, the lifted water)
FREED: Color = (255, 206, 110)      # the ox's eyes once it is free

# --- where things are, relative to the wheel's foot -------------------------------------------------
HUB: Point = (0.0, -150.0)
RIM = 128.0              # outer rim of the wheel
POT_R = 140.0            # where the pots hang
POTS = 24
PERIOD = 360.0 / POTS    # the wheel looks the same every 15 degrees
STEPS = 30               # cached rotations within one period (0.5 degrees apart)
WHEEL_SIZE = 320
PINION: Point = (186.0, -150.0)
PINION_R = 24.0
CROWN: Point = (258.0, -124.0)     # the ox's horizontal gear, on the tower's platform
CROWN_RX, CROWN_RY = 62.0, 14.0
PLATFORM: Point = (258.0, -122.0)
PLATFORM_RX, PLATFORM_RY = 92.0, 20.0
OX_PATH: Point = (258.0, -120.0)
OX_RX, OX_RY = 78.0, 15.0
TOWER_LEFT, TOWER_RIGHT, TOWER_TOP = 182.0, 334.0, -116.0
SHAFT_TOP = -214.0

# The river in the sky: (x, y, width) along its course, from the pots that throw it to the horizon.
RIVER_COURSE: tuple[tuple[float, float, float], ...] = (
    (46.0, -286.0, 8.0), (60.0, -318.0, 14.0), (96.0, -350.0, 26.0), (170.0, -368.0, 40.0),
    (280.0, -364.0, 52.0), (400.0, -344.0, 58.0), (527.0, -330.0, 60.0), (640.0, -338.0, 58.0),
    (760.0, -360.0, 54.0), (880.0, -390.0, 48.0), (1000.0, -420.0, 40.0), (1120.0, -452.0, 30.0),
)


def wheel_point(angle: float, radius: float) -> Point:
    """A point on the wheel (relative to the hub) at ``angle`` degrees clockwise from the top."""
    a = math.radians(angle)
    return math.sin(a) * radius, -math.cos(a) * radius


def pot_mouth(angle: float) -> tuple[Point, Point]:
    """(mouth position relative to the hub, mouth direction) of the pot at ``angle``."""
    a = math.radians(angle)
    tangent = (math.cos(a), math.sin(a))
    outward = (math.sin(a), -math.cos(a))
    lead = math.radians(35)
    direction = (tangent[0] * math.cos(lead) + outward[0] * math.sin(lead),
                 tangent[1] * math.cos(lead) + outward[1] * math.sin(lead))
    cx, cy = wheel_point(angle, POT_R)
    return (cx + direction[0] * 10, cy + direction[1] * 10), direction


# --- the wheel ----------------------------------------------------------------------------------------
def _pot(c: Canvas, center: Point, direction: Point, scale: float) -> None:
    """A round glazed clay pot whose mouth faces ``direction`` (lashed to the rim by two ropes)."""
    dx, dy = direction
    nx, ny = -dy, dx
    cx, cy = center

    def at(along: float, across: float) -> Point:
        return cx + (dx * along + nx * across) * scale, cy + (dy * along + ny * across) * scale

    belly = at(-1.5, 0)
    c.circle(OUTLINE, belly, 8.4 * scale)
    c.circle(CLAY, belly, 7.6 * scale)
    c.circle(CLAY_DARK, at(-2.6, 2.6), 5.0 * scale)
    c.circle(CLAY, at(-0.6, -0.8), 5.0 * scale)
    c.circle(CLAY_LIGHT, at(-3.4, -3.6), 2.0 * scale)
    # A turquoise glaze band with white dots, as on Andalusi water jars.
    c.polygon(TURQUOISE, [at(-2.4, -7.2), at(0.6, -7.4), at(0.6, 7.4), at(-2.4, 7.2)])
    for k in (-4.4, 0.0, 4.4):
        c.circle(GLAZE, at(-0.9, k), 0.8 * scale)
    # Neck and flared lip, the dark mouth showing.
    c.polygon(CLAY, [at(5, -3.4), at(8.4, -3.0), at(8.4, 3.0), at(5, 3.4)], OUTLINE, 0.7 * scale)
    c.polygon(CLAY_LIGHT, [at(8.0, -4.6), at(10.2, -4.8), at(10.2, 4.8), at(8.0, 4.6)], OUTLINE, 0.7 * scale)
    c.polygon((60, 30, 22), [at(9.4, -3.2), at(10.4, -3.2), at(10.4, 3.2), at(9.4, 3.2)])


@lru_cache(maxsize=None)
def wheel_base() -> pygame.Surface:
    """The whole wheel at twice its size (it is turned and halved for each cached rotation)."""
    k = 2.0
    size = WHEEL_SIZE * 2
    c = Canvas(size, size, scale=2, fringe=OUTLINE)
    cx = cy = size / 2

    def P(angle: float, radius: float) -> Point:
        x, y = wheel_point(angle, radius * k)
        return cx + x, cy + y

    # Back ring of the rim, in shadow.
    c.circle(OUTLINE, (cx, cy), (RIM + 3) * k)
    c.circle(WOOD_DARK, (cx, cy), (RIM + 1.5) * k)
    # Clear the middle: the sky shows between the spokes.
    hole = pygame.Surface(c.surface.get_size(), pygame.SRCALPHA)
    hole.fill((255, 255, 255, 255))
    pygame.draw.circle(hole, (255, 255, 255, 0), (round(cx * 2), round(cy * 2)), round((RIM - 15) * k * 2))
    c.surface.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    # Spokes: 24, alternately heavy and light, from the hub to the rim.
    for s in range(POTS):
        a = s * PERIOD
        heavy = s % 2 == 0
        width = (2.8 if heavy else 1.7) * k
        c.capsule(WOOD_DARK if heavy else WOOD, P(a, 20), P(a, RIM - 10), width, OUTLINE, 0.6 * k)
        if heavy:
            c.line(WOOD_LIGHT, P(a - 0.8, 26), P(a - 0.5, RIM - 14), 0.7 * k)
    # Rings and the lattice of braces between them (the norias of Hama are a web of timber).
    for radius, width in ((68, 2.6), (104, 2.8)):
        c.ring(OUTLINE, (cx, cy), radius * k, (width + 1.2) * k)
        c.ring(WOOD, (cx, cy), radius * k, width * k)
    for s in range(POTS):
        a = s * PERIOD
        c.capsule(WOOD, P(a, 70), P(a + PERIOD, 102), 1.2 * k, OUTLINE, 0.4 * k)
        c.capsule(WOOD, P(a + PERIOD, 70), P(a, 102), 1.2 * k, OUTLINE, 0.4 * k)
    # The rim: a band of timber sheathed in brass, with a turquoise enamel line that glows.
    c.ring(OUTLINE, (cx, cy), (RIM - 6) * k, 15 * k)
    c.ring(WOOD, (cx, cy), (RIM - 6) * k, 12.5 * k)
    c.ring(WOOD_LIGHT, (cx, cy), (RIM - 1.5) * k, 2.4 * k)
    c.ring(TURQUOISE, (cx, cy), (RIM - 7.5) * k, 1.6 * k)
    for s in range(POTS):
        a = s * PERIOD
        plate = [P(a - 2.6, RIM - 12.6), P(a + 2.6, RIM - 12.6), P(a + 2.4, RIM + 0.4), P(a - 2.4, RIM + 0.4)]
        c.polygon(BRASS, plate, OUTLINE, 0.5 * k)
        c.circle(BRASS_LIGHT, P(a - 1.2, RIM - 9), 0.9 * k)
        c.circle(BRASS_LIGHT, P(a + 1.2, RIM - 3), 0.9 * k)
        # A paddle board on the outside, to bite the current.
        c.polygon(WOOD_DARK, [P(a + 6.6, RIM), P(a + 8.4, RIM), P(a + 8.0, RIM + 7), P(a + 6.8, RIM + 7)], OUTLINE, 0.4 * k)
    # The pots, each tied to the rim, mouths leading the turn.
    for s in range(POTS):
        a = s * PERIOD + PERIOD / 2
        center = P(a, POT_R)
        rad = math.radians(a)
        tangent = (math.cos(rad), math.sin(rad))
        outward = (math.sin(rad), -math.cos(rad))
        lead = math.radians(35)
        direction = (tangent[0] * math.cos(lead) + outward[0] * math.sin(lead),
                     tangent[1] * math.cos(lead) + outward[1] * math.sin(lead))
        for rope in (-6.0, 5.0):
            end = P(a + rope * 0.5, RIM)
            start = (center[0] + direction[0] * rope * k * 0.9, center[1] + direction[1] * rope * k * 0.9)
            c.line((70, 48, 30), start, end, 0.7 * k)
        _pot(c, center, direction, k)
    return c.finish()


@lru_cache(maxsize=None)
def wheel_frame(step: int) -> pygame.Surface:
    """The wheel turned clockwise by ``step`` half-degrees (0 <= step < STEPS)."""
    return pygame.transform.rotozoom(wheel_base(), -step * PERIOD / STEPS, 0.5)


def wheel_for(angle: float) -> pygame.Surface:
    phase = angle % PERIOD
    return wheel_frame(int(phase / PERIOD * STEPS) % STEPS)


@lru_cache(maxsize=None)
def _hub_base() -> pygame.Surface:
    size = 64
    c = Canvas(size, size, scale=4, fringe=OUTLINE)
    m = size / 2
    c.circle(OUTLINE, (m, m), 23.5)
    c.circle(BRASS_DARK, (m, m), 22)
    c.circle(BRASS, (m, m), 19)
    for k in range(8):
        a = math.radians(k * 45)
        tip = (m + math.sin(a) * 17, m - math.cos(a) * 17)
        left = (m + math.sin(a - 0.32) * 8, m - math.cos(a - 0.32) * 8)
        right = (m + math.sin(a + 0.32) * 8, m - math.cos(a + 0.32) * 8)
        c.polygon(GOLD, [left, tip, right, (m, m)], OUTLINE, 0.5)
        c.circle(BRASS_LIGHT, (m + math.sin(a + 0.4) * 19.6, m - math.cos(a + 0.4) * 19.6), 1.2)
    c.circle(OUTLINE, (m, m), 7.4)
    c.circle(TURQUOISE, (m, m), 6.2)
    c.circle(TURQUOISE_LIGHT, (m - 1.6, m - 1.8), 2.2)
    return c.finish()


def hub_image(angle: float) -> pygame.Surface:
    return _rotated(_hub_base(), angle, 64)


@lru_cache(maxsize=None)
def _pinion_base() -> pygame.Surface:
    """The vertical gear on the noria's axle: a lantern of brass pegs between two discs."""
    size = 64
    c = Canvas(size, size, scale=4, fringe=OUTLINE)
    m = size / 2
    for k in range(12):
        a = math.radians(k * 30)
        c.capsule(BRASS_DARK, (m + math.sin(a) * 19, m - math.cos(a) * 19), (m + math.sin(a) * 27.5, m - math.cos(a) * 27.5),
                  2.6, OUTLINE, 0.7)
    c.circle(OUTLINE, (m, m), 22)
    c.circle(WOOD, (m, m), 20.6)
    c.ring(BRASS, (m, m), 17.6, 2.2)
    for k in range(6):
        a = math.radians(k * 60)
        c.capsule(WOOD_DARK, (m, m), (m + math.sin(a) * 17, m - math.cos(a) * 17), 1.6)
    c.circle(BRASS, (m, m), 5.4, OUTLINE, 0.8)
    return c.finish()


def pinion_image(angle: float) -> pygame.Surface:
    return _rotated(_pinion_base(), angle, 64, period=30.0)


_rotations: dict[tuple[int, int], pygame.Surface] = {}


def _rotated(image: pygame.Surface, angle: float, key: int, period: float = 45.0) -> pygame.Surface:
    step = int((angle % period) / period * 40) % 40
    cache_key = (key * 1000 + int(period), step)
    frame = _rotations.get(cache_key)
    if frame is None:
        frame = pygame.transform.rotozoom(image, -step * period / 40, 1.0)
        _rotations[cache_key] = frame
    return frame


# --- the tower the ox walks on --------------------------------------------------------------------------------
TOWER_SIZE = (200, 320)
TOWER_ORIGIN = (14, 300)      # (x = TOWER_LEFT, y = 0) inside the sprite


@lru_cache(maxsize=None)
def tower() -> pygame.Surface:
    """A square stone tower with a horseshoe arch, its platform of planks on top."""
    w, h = TOWER_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = TOWER_ORIGIN

    def P(x: float, y: float) -> Point:
        return ox + x - TOWER_LEFT, oy + y

    left, right, top = TOWER_LEFT, TOWER_RIGHT, TOWER_TOP
    c.polygon(STONE, [P(left, 20), P(right, 20), P(right, top + 12), P(left, top + 12)], OUTLINE, 1.4)
    c.polygon(STONE_DARK, [P(right - 34, 20), P(right, 20), P(right, top + 12), P(right - 34, top + 12)])
    # Courses of ashlar.
    for row, y in enumerate(range(int(top) + 26, 20, 16)):
        c.line(STONE_DARK, P(left + 2, y), P(right - 2, y), 0.8)
        for col in range(5):
            x = left + 14 + col * 32 + (row % 2) * 16
            if x < right - 4:
                c.line(STONE_DARK, P(x, y), P(x, y + 16), 0.7)
    # A horseshoe arch with red and white voussoirs, dark within (the gear-house).
    arch_cx, spring, radius = (left + right) / 2, -58.0, 30.0
    outer = horseshoe_arch(arch_cx, spring, radius + 12, 20)
    c.polygon(STONE_LIGHT, [P(x, y) for x, y in outer], OUTLINE, 1.0)
    for k in range(12):
        a0 = math.radians(210 - k * 20)
        a1 = math.radians(210 - (k + 1) * 20)
        quad = [(arch_cx + math.cos(a0) * radius, spring - math.sin(a0) * radius),
                (arch_cx + math.cos(a0) * (radius + 12), spring - math.sin(a0) * (radius + 12)),
                (arch_cx + math.cos(a1) * (radius + 12), spring - math.sin(a1) * (radius + 12)),
                (arch_cx + math.cos(a1) * radius, spring - math.sin(a1) * radius)]
        c.polygon(BRICK if k % 2 else STONE_LIGHT, [P(x, y) for x, y in quad], OUTLINE, 0.6)
    opening = horseshoe_arch(arch_cx, spring, radius, 20)
    c.polygon((40, 28, 30), [P(x, y) for x, y in opening], OUTLINE, 1.0)
    c.polygon((60, 42, 40), [P(arch_cx - 22, 20), P(arch_cx + 22, 20), P(arch_cx + 18, -40), P(arch_cx - 18, -40)])
    # Two small windows and a band of carved stars.
    for wx in (left + 26, right - 26):
        win = horseshoe_arch(wx, top + 42, 7, top + 62)
        c.polygon((44, 30, 30), [P(x, y) for x, y in win], OUTLINE, 0.8)
    c.rect(STONE_LIGHT, (*P(left - 3, top + 12), right - left + 6, 9), 1, OUTLINE, 0.9)
    for k in range(8):
        c.star(BRICK, P(left + 12 + k * 18.6, top + 16.5), 3.4, 8, 0.5, 0, None)
    # The round platform of planks, seen from a little above, with a brass edge.
    px, py = PLATFORM
    c.ellipse(OUTLINE, (*P(px - PLATFORM_RX - 1.5, py - PLATFORM_RY - 1.5), PLATFORM_RX * 2 + 3, PLATFORM_RY * 2 + 10))
    c.ellipse(WOOD_DARK, (*P(px - PLATFORM_RX, py - PLATFORM_RY + 5), PLATFORM_RX * 2, PLATFORM_RY * 2 + 3))
    c.ellipse(WOOD, (*P(px - PLATFORM_RX, py - PLATFORM_RY), PLATFORM_RX * 2, PLATFORM_RY * 2))
    for k in range(-5, 6):
        x = px + k * 15
        half = PLATFORM_RY * math.sqrt(max(0.0, 1 - (k * 15 / PLATFORM_RX) ** 2))
        c.line(WOOD_DARK, P(x, py - half + 1), P(x, py + half - 1), 0.8)
    c.ellipse(BRASS, (*P(px - PLATFORM_RX + 1, py - PLATFORM_RY + 1), PLATFORM_RX * 2 - 2, PLATFORM_RY * 2 - 2), None)
    c.ellipse(WOOD, (*P(px - PLATFORM_RX + 4, py - PLATFORM_RY + 3), PLATFORM_RX * 2 - 8, PLATFORM_RY * 2 - 6))
    for k in range(-5, 6):
        x = px + k * 15
        half = (PLATFORM_RY - 3) * math.sqrt(max(0.0, 1 - (k * 15 / (PLATFORM_RX - 4)) ** 2))
        c.line(WOOD_DARK, P(x, py - half + 1), P(x, py + half - 1), 0.8)
    # The trough the ox drinks from, at the front edge.
    c.rect(STONE_DARK, (*P(px + 34, py + 10), 40, 10), 2, OUTLINE, 0.8)
    c.rect(RIVER_DEEP, (*P(px + 37, py + 11), 34, 4), 1)
    return c.finish()


def draw_crown(surface: pygame.Surface, center: tuple[float, float], angle: float, glow: float) -> None:
    """The horizontal gear on the platform: a ring of pegs going round (live, it is cheap)."""
    cx, cy = center
    rect = pygame.Rect(0, 0, CROWN_RX * 2, CROWN_RY * 2)
    rect.center = (round(cx), round(cy))
    pygame.draw.ellipse(surface, OUTLINE, rect.inflate(6, 6))
    pygame.draw.ellipse(surface, WOOD_DARK, rect.inflate(2, 2))
    pygame.draw.ellipse(surface, WOOD, rect.inflate(-6, -4))
    pygame.draw.ellipse(surface, BRASS, rect.inflate(-6, -4), 2)
    pegs = []
    for k in range(20):
        a = math.radians(angle + k * 18)
        x = cx + math.cos(a) * (CROWN_RX - 4)
        y = cy + math.sin(a) * (CROWN_RY - 1)
        pegs.append((math.sin(a), x, y))
    for depth, x, y in sorted(pegs):
        color = BRASS_LIGHT if depth > 0 else BRASS_DARK
        pygame.draw.line(surface, OUTLINE, (x, y), (x, y - 7), 4)
        pygame.draw.line(surface, color, (x, y), (x, y - 6), 2)
    # The shaft rising from the gear's heart, with a finial that glows with the spell.
    top = cy + SHAFT_TOP - CROWN[1]
    pygame.draw.line(surface, OUTLINE, (cx, cy), (cx, top), 9)
    pygame.draw.line(surface, WOOD, (cx, cy), (cx, top), 6)
    for y in (cy - 20, cy - 50, top + 12):
        pygame.draw.line(surface, BRASS, (cx - 4, y), (cx + 4, y), 3)
    finial = [(cx, top - 22), (cx + 7, top - 8), (cx + 4, top), (cx - 4, top), (cx - 7, top - 8)]
    pygame.draw.polygon(surface, OUTLINE, [(x, y + 1) for x, y in finial])
    pygame.draw.polygon(surface, GOLD, finial)
    blit_glow(surface, (cx, top - 10), 16, MAGIC, 0.35 + 0.4 * glow)
    pygame.draw.circle(surface, MAGIC if glow > 0.05 else FREED, (round(cx), round(top - 10)), 3)


# --- the brass ox ------------------------------------------------------------------------------------------
OX_SIZE = (172, 142)
OX_FOOT = (76, 136)          # between its hooves, inside the sprite
OX_PIVOT = (48.0, -78.0)     # where the head turns on the neck (relative to the foot, facing right)
OX_EYE = (70.0, -82.0)       # these three are given for the head at rest; see ``ox_point``
OX_MOUTH = (92.0, -58.0)
OX_YOKE = (40.0, -88.0)
OX_ANIMS = {"walk": 8, "drink": 4, "bellow": 3, "rest": 2}


def _ox_head(anim: str, frame: int) -> tuple[float, float, float]:
    """(dx, dy, tilt in radians) of the head in this frame."""
    if anim == "drink":
        u = min(1.0, (frame + 1) / 3)
        return 10 * u, 30 * u + (frame == 3) * 2.5, 0.62 * u
    if anim == "bellow":
        u = (0.55, 1.0, 0.85)[frame % 3]
        return -2 * u, -8 * u, -0.42 * u
    if anim == "rest":
        return -4.0, 2.0, -0.05
    return 0.0, 1.6 * math.sin(frame / 8 * math.tau * 2), 0.04


def ox_point(point: Point, anim: str, frame: int) -> Point:
    """Where a point of the head (the eye, the mouth) is in this frame: the head dips to drink, lifts to bellow."""
    dx, dy, tilt = _ox_head(anim, frame)
    px, py = OX_PIVOT
    x, y = point[0] - px, point[1] - py
    sink = 20.0 if anim == "rest" else 0.0
    return (px + dx + x * math.cos(tilt) - y * math.sin(tilt),
            py + dy + x * math.sin(tilt) + y * math.cos(tilt) + sink)


@lru_cache(maxsize=None)
def ox(anim: str, frame: int) -> pygame.Surface:
    """The brass ox facing right: a deep-chested beast of engraved brass under a turquoise blanket."""
    w, h = OX_SIZE
    c = Canvas(w, h, scale=4, fringe=OUTLINE)
    fx, fy = OX_FOOT
    rest = anim == "rest"
    sink = 20.0 if rest else 0.0

    def P(x: float, y: float) -> Point:
        return fx + x, fy + y + sink

    phase = frame / 8 * math.tau if anim == "walk" else 0.0
    # --- legs: far pair first, darker (a four-beat walk) ---------------------------------------------
    legs = ((30.0, math.pi * 0.5, True), (-38.0, 0.0, True), (36.0, math.pi * 1.5, False), (-32.0, math.pi, False))
    for x, offset, far in legs:
        color = BRASS_DARK if far else BRASS
        if rest:
            top = P(x, -44)
            knee = P(x + (12 if x > 0 else -10), -24)
            hoof = P(x + (-6 if x > 0 else 8), -22)
        else:
            swing = math.sin(phase + offset) * 10 if anim == "walk" else 0.0
            lift = max(0.0, math.cos(phase + offset)) * 6 if anim == "walk" else 0.0
            top = P(x, -46)
            knee = P(x + swing * 0.35 + (2 if x > 0 else -3), -22 - lift * 0.5)
            hoof = P(x + swing, -3 - lift)
        c.capsule(color, top, knee, 7.6 if x < 0 else 6.8, OUTLINE, 1.1)
        c.capsule(color, knee, hoof, 4.2, OUTLINE, 1.0)
        c.polygon((54, 40, 34), [(hoof[0] - 5, hoof[1] + 2.6), (hoof[0] + 5.6, hoof[1] + 2.6), (hoof[0] + 4.4, hoof[1] - 2.4),
                                 (hoof[0] - 4.4, hoof[1] - 2.4)], OUTLINE, 0.8)
        if not far:
            c.line(BRASS_LIGHT, (knee[0] - 2, knee[1] + 2), (hoof[0] - 2, hoof[1] - 4), 0.9)
            c.ring(GOLD, (hoof[0], hoof[1] - 4), 3.6, 0.9)
    # --- tail -------------------------------------------------------------------------------------
    swish = math.sin(phase * 0.5 + 1.0) * 6
    tail = [P(-56, -74), P(-64, -62), P(-66 + swish * 0.4, -46), P(-64 + swish, -32)]
    c.tapered(OUTLINE, tail, 3.2, 2.2)
    c.tapered(BRASS_DARK, tail, 2.4, 1.4)
    tip = tail[-1]
    c.polygon(GOLD, [(tip[0] - 4, tip[1]), (tip[0] + 4, tip[1]), (tip[0] + 2.6, tip[1] + 11), (tip[0] - 2.6, tip[1] + 11)], OUTLINE, 0.7)
    # --- body: deep in the chest, a rise at the withers ---------------------------------------------
    outline = [(-50, -80), (-26, -84), (6, -86), (26, -92), (40, -84), (46, -66), (44, -46), (34, -36),
               (6, -32), (-26, -34), (-46, -38), (-58, -50), (-60, -68)]
    c.polygon(BRASS_DARK, [P(x, y) for x, y in outline], OUTLINE, 1.6)
    inner = [(-46, -78), (-24, -81), (6, -83), (24, -88), (36, -81), (40, -64), (36, -48), (6, -40), (-28, -42), (-50, -52), (-54, -68)]
    c.polygon(BRASS, [P(x, y) for x, y in inner])
    c.polygon(BRASS_LIGHT, [P(-38, -78), P(-6, -81), P(22, -86), P(30, -82), P(-4, -76), P(-36, -74)])
    for k in range(6):
        x = -46 + k * 15
        c.lines(BRASS_DARK, [P(x, -66), P(x - 2, -54), P(x + 1, -42)], 0.9)
    for k in range(13):
        c.circle(BRASS_LIGHT, P(-50 + k * 7.6, -38 + math.sin(k * 0.9) * 0.8), 0.9)
    # The blanket: lapis and turquoise, a golden eight-pointed star, a fringe of gold.
    blanket = [P(-40, -82), P(20, -88), P(28, -58), P(-44, -54)]
    c.polygon(LAPIS, blanket, OUTLINE, 1.0)
    c.polygon(TURQUOISE, [P(-34, -78), P(16, -83), P(22, -62), P(-38, -58)])
    c.star(GOLD, P(-8, -70), 9.5, 8, 0.55, 0, OUTLINE, 0.6)
    c.circle(LAPIS, P(-8, -70), 3.2)
    for k in range(10):
        x = -42 + k * 7.6
        y = -55 - k * 0.35
        c.line(GOLD, P(x, y), P(x - 0.4, y + 5), 1.0)
        c.circle(GOLD, P(x - 0.4, y + 5.6), 1.1)
    # --- neck, dewlap, yoke --------------------------------------------------------------------------
    hx, hy, tilt = _ox_head(anim, frame)
    px, py = OX_PIVOT
    neck = [P(24, -90), P(px + hx * 0.6 + 4, py + hy * 0.6 - 10), P(px + hx * 0.8 + 8, py + hy * 0.8 + 16), P(40, -46)]
    c.polygon(BRASS_DARK, neck, OUTLINE, 1.2)
    c.polygon(BRASS, [P(28, -86), P(px + hx * 0.6 + 2, py + hy * 0.6 - 6), P(px + hx * 0.8 + 4, py + hy * 0.8 + 12), P(38, -52)])
    dewlap = [P(36, -50), P(px + hx * 0.8 + 6, py + hy * 0.8 + 18), P(px + hx * 0.7 - 2, py + hy * 0.7 + 30), P(30, -40)]
    c.polygon(BRASS_DARK, dewlap, OUTLINE, 0.9)
    yx, yy = OX_YOKE
    c.capsule(WOOD_DARK, P(yx - 6, yy - 6), P(yx + 2, yy + 26), 3.4, OUTLINE, 0.9)
    c.circle(BRASS, P(yx - 4, yy - 2), 2.0, OUTLINE, 0.6)
    bell = P(px + hx * 0.7 + 4, py + hy * 0.7 + 30)
    c.line(WOOD_DARK, (bell[0], bell[1] - 8), bell, 1.0)
    c.polygon(GOLD, [(bell[0] - 4, bell[1]), (bell[0] + 4, bell[1]), (bell[0] + 5.8, bell[1] + 8.6), (bell[0] - 5.8, bell[1] + 8.6)], OUTLINE, 0.8)
    c.circle(BRASS_DARK, (bell[0], bell[1] + 9.4), 1.6)

    # --- the head, turned on its pivot ----------------------------------------------------------------
    def H(x: float, y: float) -> Point:
        x -= px
        y -= py
        return P(px + hx + x * math.cos(tilt) - y * math.sin(tilt), py + hy + x * math.sin(tilt) + y * math.cos(tilt))

    # Horns first (the far one behind the head), lyre-shaped and gold, tipped with turquoise.
    def horn(side: float, color: Color) -> None:
        points = [H(56 + side, -88), H(48 + side, -100), H(52 + side * 2, -112), H(64 + side * 2, -116)]
        c.tapered(OUTLINE, points, 4.6, 2.0)
        c.tapered(color, points, 3.5, 1.1)
        c.circle(TURQUOISE, points[-1], 1.5)

    horn(-4, BRASS_DARK)
    skull = [H(46, -84), H(58, -92), H(72, -90), H(84, -78), H(94, -62), H(90, -52), H(78, -50), H(62, -58), H(48, -64)]
    c.polygon(BRASS_DARK, skull, OUTLINE, 1.3)
    c.polygon(BRASS, [H(50, -82), H(60, -89), H(71, -87), H(82, -76), H(88, -64), H(76, -58), H(60, -62)])
    c.polygon(BRASS_LIGHT, [H(56, -86), H(68, -86), H(66, -82), H(56, -80)])
    # Muzzle, nostril and a gold ring.
    c.ellipse((96, 66, 46), (H(86, -60)[0] - 8.6, H(86, -60)[1] - 7.4, 17.2, 14.0), OUTLINE, 0.9)
    c.circle(OUTLINE, H(91, -61), 1.5)
    c.ring(GOLD, H(92, -53), 3.4, 1.2)
    if anim == "bellow":
        c.polygon((80, 24, 30), [H(80, -54), H(94, -54), H(92, -44), H(80, -48)], OUTLINE, 0.8)
    # Ear, swept back, turquoise within.
    c.polygon(BRASS_DARK, [H(54, -86), H(44, -88), H(34, -84), H(44, -80), H(52, -79)], OUTLINE, 0.9)
    c.polygon(TURQUOISE, [H(50, -84), H(43, -85.4), H(38, -84), H(44, -82)])
    horn(4, GOLD)
    # Brow, and the socket where the eye burns (drawn live).
    ex, ey = H(*OX_EYE)
    c.ellipse((40, 26, 22), (ex - 4.8, ey - 3.6, 9.6, 7.2), OUTLINE, 0.8)
    c.line(BRASS_LIGHT, H(64, -88), H(76, -86), 1.0)
    return c.finish()


# --- the river in the sky --------------------------------------------------------------------------------
def _spline(points: list[tuple[float, float, float]], samples: int) -> list[tuple[float, float, float]]:
    """Catmull-Rom through (x, y, width) points."""
    out = []
    count = len(points)
    for k in range(samples + 1):
        u = k / samples * (count - 1)
        i = min(count - 2, int(u))
        t = u - i
        p0 = points[max(0, i - 1)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(count - 1, i + 2)]
        out.append(tuple(
            0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
            for a, b, c, d in zip(p0, p1, p2, p3)
        ))
    return out


@lru_cache(maxsize=None)
def river_course() -> tuple[tuple[float, float, float, float, float], ...]:
    """Samples along the river: (x, y, width, tangent x, tangent y), relative to the wheel's foot."""
    pts = _spline(list(RIVER_COURSE), 160)
    out = []
    for k, (x, y, w) in enumerate(pts):
        a = pts[max(0, k - 1)]
        b = pts[min(len(pts) - 1, k + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = max(1e-6, math.hypot(dx, dy))
        out.append((x, y, w, dx / d, dy / d))
    return tuple(out)


RIVER_PAD = 40


@lru_cache(maxsize=None)
def river_body() -> tuple[pygame.Surface, tuple[float, float]]:
    """The river's water, painted once: (image, top-left relative to the wheel's foot)."""
    course = river_course()
    xs = [x for x, *_ in course]
    ys = [y for _, y, *_ in course]
    left, top = min(xs) - RIVER_PAD, min(ys) - RIVER_PAD
    w = round(max(xs) - left + RIVER_PAD)
    h = round(max(ys) - top + RIVER_PAD)
    image = pygame.Surface((w, h), pygame.SRCALPHA)

    def band(offset_from: float, offset_to: float, color: tuple[int, int, int, int], grow: float = 0.0) -> None:
        upper, lower = [], []
        for x, y, width, tx, ty in course:
            nx, ny = -ty, tx
            half = width / 2 + grow
            upper.append((x - left + nx * half * offset_from, y - top + ny * half * offset_from))
            lower.append((x - left + nx * half * offset_to, y - top + ny * half * offset_to))
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(layer, color, upper + lower[::-1])
        image.blit(layer, (0, 0))

    band(-1.0, 1.0, (*RIVER_LIGHT, 34), grow=12)        # a haze of spray around it
    band(-1.0, 1.0, (*RIVER, 150))
    band(0.15, 1.0, (*RIVER_DEEP, 110))                 # the deeper underside
    band(-1.0, -0.62, (*RIVER_LIGHT, 120))              # the bright surface catching the dawn
    band(-0.5, -0.38, (255, 255, 255, 60))
    image = pygame.transform.smoothscale(pygame.transform.smoothscale(image, (w // 2, h // 2)), (w, h))
    return image, (left, top)


def river_at(u: float) -> tuple[float, float, float, float, float]:
    """Position along the river, ``u`` from 0 (the wheel) to 1 (the horizon)."""
    course = river_course()
    f = max(0.0, min(1.0, u)) * (len(course) - 1)
    i = min(len(course) - 2, int(f))
    t = f - i
    a, b = course[i], course[i + 1]
    return tuple(p + (q - p) * t for p, q in zip(a, b))


@lru_cache(maxsize=None)
def fish_image(kind: int, frame: int) -> pygame.Surface:
    """A small carp facing right (gold, silver or red), tail beating."""
    w, h = 26, 14
    c = Canvas(w, h, scale=4, fringe=(30, 40, 60))
    color = ((250, 180, 70), (220, 230, 240), (236, 96, 70))[kind % 3]
    beat = math.sin(frame / 4 * math.tau) * 2.2
    c.polygon(shade(color, -0.25), [(5, 7), (0.5, 2 + beat), (1.5, 7), (0.5, 12 + beat)], (30, 40, 60), 0.5)
    c.ellipse(color, (4, 3, 18, 8), (30, 40, 60), 0.6)
    c.ellipse(shade(color, 0.3), (8, 3.6, 10, 3))
    c.polygon(shade(color, -0.2), [(12, 3.4), (15, 0.8), (16, 3.6)])
    c.circle((20, 24, 40), (18.6, 6.2), 0.9)
    return c.finish()


def draw_river(surface: pygame.Surface, foot: tuple[float, float], t: float, strength: float, fish_seed: int = 4) -> None:
    """The river and everything alive in it: streaks of current, carp, glints."""
    if strength <= 0.01:
        return
    image, (left, top) = river_body()
    fx, fy = foot
    if strength < 0.99:
        image = image.copy()
        image.set_alpha(round(255 * strength))
    surface.blit(image, (round(fx + left), round(fy + top)))
    rng = random.Random(fish_seed)
    # Streaks of current running along it.
    for k in range(46):
        lane = rng.uniform(-0.8, 0.8)
        speed = rng.uniform(0.05, 0.09)
        u = (rng.random() + t * speed) % 1.0
        x, y, width, tx, ty = river_at(u)
        nx, ny = -ty, tx
        px, py = fx + x + nx * width * 0.5 * lane, fy + y + ny * width * 0.5 * lane
        length = 6 + 10 * (1 - abs(lane))
        color = RIVER_LIGHT if lane < 0 else (170, 226, 246)
        pygame.draw.line(surface, color, (px, py), (px + tx * length, py + ty * length), 1)
    # Carp swimming upstream and down.
    for k in range(7):
        kind = rng.randrange(3)
        lane = rng.uniform(-0.45, 0.45)
        speed = rng.uniform(0.012, 0.03) * (1 if k % 3 else -0.6)
        u = (rng.random() + t * speed) % 1.0
        if u < 0.08 or u > 0.96:
            continue
        x, y, width, tx, ty = river_at(u)
        nx, ny = -ty, tx
        wiggle = math.sin(t * 6 + k) * 2
        px, py = fx + x + nx * (width * 0.5 * lane + wiggle), fy + y + ny * (width * 0.5 * lane + wiggle)
        heading = math.atan2(ty, tx) + (math.pi if speed < 0 else 0.0)
        img = fish_image(kind, int(t * 10 + k) % 4)
        if math.cos(heading) < 0:
            img = pygame.transform.flip(img, False, True)     # keep the belly down when swimming left
        rotated = pygame.transform.rotate(img, -math.degrees(heading))
        rotated.set_alpha(round(200 * strength))
        surface.blit(rotated, rotated.get_rect(center=(round(px), round(py))))
    # Glints where the dawn catches the surface.
    for k in range(14):
        u = (rng.random() + t * 0.02) % 1.0
        x, y, width, tx, ty = river_at(u)
        nx, ny = -ty, tx
        if int(t * 8 + k * 3) % 5 == 0:
            gx, gy = fx + x - nx * width * 0.4, fy + y - ny * width * 0.4
            pygame.draw.line(surface, (255, 255, 255), (gx - 3, gy), (gx + 3, gy), 1)
            pygame.draw.line(surface, (255, 255, 255), (gx, gy - 2), (gx, gy + 2), 1)


# --- light through the river: caustics -----------------------------------------------------------------------
CAUSTIC_SIZE = 96
CAUSTIC_FRAMES = 12


@lru_cache(maxsize=None)
def caustic(frame: int) -> pygame.Surface:
    """A tileable net of light, as thrown through moving water (``frame`` of a looping set)."""
    import numpy as np

    n = CAUSTIC_SIZE
    phase = frame / CAUSTIC_FRAMES * math.tau
    y, x = np.mgrid[0:n, 0:n] / n * math.tau
    value = np.zeros((n, n))
    for kx, ky, speed, offset in ((2, 1, 1, 0.0), (1, 3, -1, 1.7), (3, -2, 1, 2.9), (-1, 2, -1, 4.1)):
        value += np.sin(kx * x + ky * y + speed * phase + offset + 0.8 * np.sin(ky * x - kx * y + phase))
    ridge = np.clip(1.0 - np.abs(value) / 0.9, 0, 1) ** 3
    level = (ridge * 255).astype(np.uint8)
    surface = pygame.Surface((n, n))
    rgb = np.stack([level * 0.55, level * 0.9, level], axis=-1).astype(np.uint8)
    pygame.surfarray.blit_array(surface, rgb.transpose(1, 0, 2))
    return surface
