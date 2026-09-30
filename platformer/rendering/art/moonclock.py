"""The Moon-Clock Fountain of level 1.

Al-Jazari's castle clock had a zodiac that turned and a moon that waxed and
waned; the Court of the Lions in the Alhambra has a basin carried by marble
lions. The thief's troupe built both into one enchanted fountain: the
orchard's water climbs a brass column in a glowing spiral and gathers into a
floating moon of living water, cradled by brass crescents and circled by an
armillary of the zodiac. Two brass automata play on the rim.

Static parts are painted once, supersampled, and cached; the moon, the rings
and the water are drawn every frame (on a small 2x surface, then smoothed).
All positions are relative to the fountain's foot: x = 0 at the centre,
y = 0 on the floor, negative y upward.
"""

import math
import random
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas, mix

Color = tuple[int, int, int]

OUTLINE: Color = (56, 36, 30)
MARBLE: Color = (242, 236, 226)
MARBLE_SHADE: Color = (208, 198, 188)
MARBLE_DARK: Color = (160, 148, 142)
VEIN: Color = (226, 218, 210)
BRASS: Color = (226, 172, 72)
BRASS_DARK: Color = (146, 94, 36)
BRASS_LIGHT: Color = (255, 234, 166)
GOLD: Color = (246, 198, 88)
LAPIS: Color = (40, 74, 162)
TURQUOISE: Color = (46, 192, 186)
WATER: Color = (84, 196, 238)
WATER_DEEP: Color = (28, 92, 150)
WATER_LIGHT: Color = (208, 246, 255)
GLASS: Color = (176, 228, 242)
MOON_CORE: Color = (214, 246, 255)
MOON_EDGE: Color = (34, 104, 168)
RUBY: Color = (224, 60, 84)

RIM_Y = -44            # the basin's rim (and water) height above the floor
RIM_RX, RIM_RY = 134, 11
WATER_RX, WATER_RY = 122, 7
LION_XS = (-84, 0, 84)
MUSICIAN_XS = (-104, 104)
COLUMN_TOP = -196       # the top of the column, just under the lotus cup
MOON_RADIUS = 30
MOON_Y = -250          # the moon's centre when it floats


# --- static sprites ----------------------------------------------------------------------------------
BASIN_SIZE = (284, 64)
BASIN_ORIGIN = (142, 60)   # the fountain's foot inside the basin sprite


@lru_cache(maxsize=None)
def basin() -> pygame.Surface:
    """Lions, pedestal and the carved bowl, with the rim left open for the water."""
    w, h = BASIN_SIZE
    ox, oy = BASIN_ORIGIN
    c = Canvas(w, h, fringe=OUTLINE)

    def P(x: float, y: float) -> tuple[float, float]:
        return ox + x, oy + y

    # The pedestal the lions stand before: fluted marble with little horseshoe arches.
    c.rect(MARBLE_SHADE, (*P(-66, -26), 132, 26), 2, OUTLINE, 1)
    for k in range(-5, 6):
        x = k * 11
        c.line(MARBLE_DARK, P(x, -22), P(x, -3), 1.0)
    # The bowl: a shallow twelve-sided cup, lighter where the light falls.
    bowl = [P(math.cos(a) * (RIM_RX - 4), RIM_Y + 2 + math.sin(a) * 26) for a in _arc(0, math.pi, 24)]
    bowl = [P(-RIM_RX + 4, RIM_Y + 2)] + bowl[::-1] + [P(RIM_RX - 4, RIM_Y + 2)]
    c.polygon(MARBLE, bowl, OUTLINE, 1.2)
    for k in range(1, 12):
        a = math.pi * k / 12
        x = math.cos(a) * (RIM_RX - 4)
        top = P(x, RIM_Y + 4)
        bottom = P(x * 0.96, RIM_Y + 2 + math.sin(a) * 26 - 1)
        c.line(MARBLE_SHADE if k % 2 else VEIN, top, bottom, 1.0)
    shade = [P(math.cos(a) * (RIM_RX - 6), RIM_Y + 2 + math.sin(a) * 24) for a in _arc(math.pi * 0.55, math.pi * 0.98, 10)]
    c.polygon(MARBLE_SHADE, [P(-40, RIM_Y + 20)] + shade + [P(-RIM_RX + 8, RIM_Y + 6)])
    # The inscription band under the rim (the Court of the Lions has a poem there).
    band = [P(math.cos(a) * (RIM_RX - 3), RIM_Y + 6 + math.sin(a) * 6) for a in _arc(0.08, math.pi - 0.08, 30)]
    c.lines(GOLD, band, 3.2)
    c.lines(BRASS_DARK, [(x, y + 1.8) for x, y in band], 0.8)
    rng = random.Random(9)
    for k in range(34):
        a = 0.12 + (math.pi - 0.24) * k / 33
        x, y = P(math.cos(a) * (RIM_RX - 3), RIM_Y + 6 + math.sin(a) * 6)
        c.line(LAPIS, (x, y - 1.2), (x + rng.uniform(-1.5, 1.5), y + 1.0), 0.7)
    # The rim, open in the middle (the water is drawn live).
    c.ellipse(MARBLE_SHADE, (ox - RIM_RX, oy + RIM_Y - RIM_RY + 1, RIM_RX * 2, RIM_RY * 2), OUTLINE, 1.2)
    c.ellipse(MARBLE, (ox - RIM_RX + 2, oy + RIM_Y - RIM_RY, RIM_RX * 2 - 4, RIM_RY * 2 - 3))
    c.ellipse(WATER_DEEP, (ox - WATER_RX, oy + RIM_Y - WATER_RY - 1, WATER_RX * 2, WATER_RY * 2))
    # Three marble lions carry it, facing out.
    for x in LION_XS:
        _lion(c, P(x, 0))
    return c.finish()



def _lion(c: Canvas, foot: tuple[float, float]) -> None:
    x, y = foot
    c.ellipse(MARBLE_SHADE, (x - 11, y - 12, 22, 12), OUTLINE, 1)          # haunches
    for px in (-5.5, 5.5):
        c.rect(MARBLE, (x + px - 3, y - 8, 6, 8), 1.5, OUTLINE, 0.9)     # forelegs
        c.line(MARBLE_DARK, (x + px - 1, y - 1), (x + px - 1, y - 2.5), 0.6)
        c.line(MARBLE_DARK, (x + px + 1, y - 1), (x + px + 1, y - 2.5), 0.6)
    mane = (x, y - 15)
    for k in range(14):
        a = k * math.tau / 14
        c.circle(MARBLE_SHADE, (mane[0] + math.cos(a) * 8.5, mane[1] + math.sin(a) * 8.5), 3.2, OUTLINE, 0.8)
    c.circle(MARBLE_SHADE, mane, 9.0)
    c.circle(MARBLE, (x, y - 14.5), 6.2, OUTLINE, 0.8)                   # face
    for side in (-1, 1):
        c.circle(MARBLE_SHADE, (x + side * 4.6, y - 19.5), 1.8, OUTLINE, 0.6)  # ears
        c.circle(OUTLINE, (x + side * 2.3, y - 16.0), 0.8)                # eyes
    c.polygon(MARBLE_DARK, [(x - 1.6, y - 13.8), (x + 1.6, y - 13.8), (x, y - 12.2)])
    c.ellipse((70, 60, 70), (x - 2.2, y - 11.6, 4.4, 3.0))                 # the spout of its mouth


def _arc(a0: float, a1: float, steps: int) -> list[float]:
    return [a0 + (a1 - a0) * k / steps for k in range(steps + 1)]


COLUMN_SIZE = (34, 152)


@lru_cache(maxsize=None)
def column() -> pygame.Surface:
    """A brass column with a glass window; its bottom sits on the water, top under the capital."""
    w, h = COLUMN_SIZE
    c = Canvas(w, h, fringe=OUTLINE)
    cx = w / 2
    c.rect(BRASS, (cx - 8, 2, 16, h - 4), 3, OUTLINE, 1.2)
    c.rect(BRASS_DARK, (cx + 3, 4, 4, h - 8))
    c.rect(BRASS_LIGHT, (cx - 6, 4, 2, h - 8))
    c.rect(GLASS, (cx - 4, 8, 8, h - 16), 3, OUTLINE, 0.8)
    c.rect(mix(GLASS, WATER_DEEP, 0.5), (cx + 1, 10, 2.5, h - 20), 1)
    for y in range(4, h - 2, 34):
        c.ellipse(BRASS, (cx - 11, y - 3, 22, 7), OUTLINE, 1.0)
        c.ellipse(BRASS_LIGHT, (cx - 8, y - 2.4, 12, 2.6))
        for side in (-1, 1):
            c.circle(TURQUOISE, (cx + side * 6.5, y + 0.4), 1.2)
    return c.finish()


CRADLE_SIZE = (132, 126)
CRADLE_ORIGIN = (66, 60)   # the moon's resting centre inside the cradle sprite


@lru_cache(maxsize=None)
def cradle() -> pygame.Surface:
    """The lotus capital and the two brass crescents that hold the moon."""
    w, h = CRADLE_SIZE
    ox, oy = CRADLE_ORIGIN
    c = Canvas(w, h, fringe=OUTLINE)
    r = MOON_RADIUS
    cup_y = oy + r + 12
    # Lotus capital: petals opening up from the column.
    for k, (dx, lean) in enumerate(((-15, -0.5), (15, 0.5), (-8, -0.2), (8, 0.2), (0, 0.0))):
        base = (ox + dx * 0.3, cup_y + 12)
        tip = (ox + dx + lean * 6, cup_y - 6)
        side = 4.5
        petal = [base, (base[0] - side, (base[1] + tip[1]) / 2), tip, (base[0] + side, (base[1] + tip[1]) / 2)]
        c.polygon(BRASS if k < 4 else BRASS_LIGHT, petal, OUTLINE, 1.0)
    c.ellipse(BRASS_DARK, (ox - 12, cup_y + 9, 24, 7), OUTLINE, 1.0)
    # Two crescents rising from the cup, tapering to jewelled horns round the moon.
    for side in (-1, 1):
        outer = []
        inner = []
        for k in range(19):
            u = k / 18
            a = math.radians(90 + side * (6 + k * 7.0))
            thick = 2.0 + 8.0 * (1 - u) ** 0.8
            outer.append((ox + math.cos(a) * (r + 4 + thick), oy + math.sin(a) * (r + 4 + thick)))
            inner.append((ox + math.cos(a) * (r + 3), oy + math.sin(a) * (r + 3)))
        c.polygon(BRASS, outer + inner[::-1], OUTLINE, 1.1)
        c.lines(BRASS_LIGHT, [(x + side * 0.6, y - 0.8) for x, y in outer[1:16]], 1.0)
        c.lines(BRASS_DARK, inner[1:17], 0.9)
        for k in (3, 7, 11):
            a = math.radians(90 + side * (6 + k * 7.0))
            thick = 2.0 + 8.0 * (1 - k / 18) ** 0.8
            spot = (ox + math.cos(a) * (r + 4 + thick * 0.55), oy + math.sin(a) * (r + 4 + thick * 0.55))
            c.circle(TURQUOISE if k != 7 else LAPIS, spot, 1.5 if k < 11 else 1.1, OUTLINE, 0.5)
        tip = outer[-1]
        c.circle(BRASS_LIGHT, tip, 3.2, OUTLINE, 0.9)
        c.circle(RUBY, tip, 1.4)
    return c.finish()


# --- the zodiac medallions --------------------------------------------------------------------------
@lru_cache(maxsize=None)
def medallions() -> tuple[pygame.Surface, ...]:
    """Twelve little brass discs, each with its own enamelled sign."""
    images = []
    for k in range(12):
        c = Canvas(14, 14, fringe=OUTLINE)
        c.circle(BRASS, (7, 7), 5.4, OUTLINE, 0.9)
        c.circle(BRASS_LIGHT, (6.2, 6.2), 3.6)
        color = TURQUOISE if k % 2 else LAPIS
        _glyph(c, k, (7, 7), color)
        images.append(c.finish())
    return tuple(images)


def _glyph(c: Canvas, k: int, center: tuple[float, float], color: Color) -> None:
    x, y = center
    kind = k % 6
    if kind == 0:
        c.circle(color, (x, y), 2.2)
        c.circle(BRASS_LIGHT, (x, y), 0.9)
    elif kind == 1:
        c.circle(color, (x, y), 2.6)
        c.circle(BRASS_LIGHT, (x + 1.2, y - 0.6), 2.2)
    elif kind == 2:
        c.lines(color, [(x - 2.6, y - 1), (x - 1.3, y - 2), (x, y - 1), (x + 1.3, y - 2), (x + 2.6, y - 1)], 0.9)
        c.lines(color, [(x - 2.6, y + 1.2), (x - 1.3, y + 0.2), (x, y + 1.2), (x + 1.3, y + 0.2), (x + 2.6, y + 1.2)], 0.9)
    elif kind == 3:
        c.star(color, (x, y), 2.9, 5, 0.45)
    elif kind == 4:
        c.polygon(color, [(x, y - 2.8), (x + 2.6, y + 2), (x - 2.6, y + 2)])
    else:
        c.lines(color, [(x - 2.4, y + 2.2), (x - 2.4, y - 1.4), (x, y + 0.6), (x + 2.4, y - 1.4), (x + 2.4, y + 2.2)], 0.9)


# --- the automaton musicians ----------------------------------------------------------------------------
MUSICIAN_SIZE = (26, 32)
MUSICIAN_ORIGIN = (13, 31)  # the base of its little plinth


@lru_cache(maxsize=None)
def musician_frames(kind: str) -> tuple[pygame.Surface, ...]:
    """Drummer: four beats and a bow. Ney player: four sways and a bow. Both face the moon."""
    frames = []
    for frame in range(5):
        c = Canvas(*MUSICIAN_SIZE, fringe=OUTLINE)
        _musician(c, kind, frame)
        frames.append(c.finish())
    return tuple(frames)


def _musician(c: Canvas, kind: str, frame: int) -> None:
    bx, by = MUSICIAN_ORIGIN
    bow = frame == 4
    c.rect(MARBLE_SHADE, (bx - 7, by - 5, 14, 5), 1, OUTLINE, 0.8)                # plinth
    lean = (-3.0 if bow else 0.0) + ((frame % 2) * 0.8 if kind == "ney" and not bow else 0.0)
    hip = (bx, by - 6)
    neck = (bx + lean, by - 17)
    # A seated brass figure in a flaring robe, enamel sash and turban.
    c.polygon(BRASS, [(bx - 7, by - 5), (bx + 7, by - 5), (neck[0] + 3.5, neck[1] + 1), (neck[0] - 3.5, neck[1] + 1)], OUTLINE, 0.9)
    c.polygon(BRASS_DARK, [(bx + 2, by - 5), (bx + 7, by - 5), (neck[0] + 3.5, neck[1] + 1), (neck[0] + 1.2, neck[1] + 1)])
    c.line(TURQUOISE, (hip[0] - 5, hip[1] - 4), (hip[0] + 5, hip[1] - 4), 1.4)
    head = (neck[0] + (1.5 if bow else 0.4), neck[1] - 3.6 + (2.2 if bow else 0))
    c.circle(BRASS_LIGHT, head, 3.3, OUTLINE, 0.8)
    c.ellipse(TURQUOISE, (head[0] - 3.8, head[1] - 5.2, 7.6, 3.6), OUTLINE, 0.6)
    c.circle(RUBY, (head[0], head[1] - 4.6), 0.8)
    c.circle(OUTLINE, (head[0] + 1.4, head[1] - 0.2), 0.55)
    shoulder = (neck[0] + 0.5, neck[1] + 2.5)
    if kind == "drum":
        drum = (bx + 6, by - 9)
        c.polygon(BRASS_DARK, [(drum[0] - 3, drum[1] + 3), (drum[0] + 3, drum[1] + 3), (drum[0] + 1.3, drum[1] - 2), (drum[0] - 1.3, drum[1] - 2)], OUTLINE, 0.7)
        c.ellipse(LAPIS, (drum[0] - 4.2, drum[1] - 4.2, 8.4, 3.2), OUTLINE, 0.7)
        c.ellipse(MARBLE, (drum[0] - 3.2, drum[1] - 3.8, 6.4, 2.2))
        if bow:
            hands = ((shoulder[0] + 3, shoulder[1] + 5), (shoulder[0] + 2, shoulder[1] + 6))
        else:
            up = frame in (0, 2)
            right = (drum[0] + (1.5 if frame < 2 else -1.5), drum[1] - (8 if up else 3.5))
            left = (drum[0] - 2.5, drum[1] - 3.2)
            hands = (right, left) if frame < 2 else (left, right)
        for hand in hands:
            c.line(BRASS, shoulder, hand, 1.5)
            c.circle(BRASS_LIGHT, hand, 1.2, OUTLINE, 0.5)
    else:
        mouth = (head[0] + 3.0, head[1] + 1.0)
        end = (mouth[0] + 9.5, mouth[1] + 9.0 - (frame % 2) * 1.0) if not bow else (mouth[0] + 7, mouth[1] + 11)
        c.line(BRASS_DARK, mouth, end, 1.3)
        for f in (0.45, 0.7):
            c.circle(OUTLINE, (mouth[0] + (end[0] - mouth[0]) * f, mouth[1] + (end[1] - mouth[1]) * f), 0.45)
        for f in (0.35, 0.75):
            hand = (mouth[0] + (end[0] - mouth[0]) * f, mouth[1] + (end[1] - mouth[1]) * f + 0.6)
            c.line(BRASS, shoulder, hand, 1.4)
            c.circle(BRASS_LIGHT, hand, 1.1, OUTLINE, 0.5)


# --- the moon, drawn live ------------------------------------------------------------------------------
_masks: dict[int, pygame.Surface] = {}


def _circle_mask(size: int, radius: int) -> pygame.Surface:
    mask = _masks.get(size * 1000 + radius)
    if mask is None:
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), radius)
        _masks[size * 1000 + radius] = mask
    return mask


def render_moon(radius: float, phase: float, t: float, swell: float = 0.0, crack: float = 0.0,
                pearl: float = 0.0) -> pygame.Surface:
    """A sphere of living water: light-fish swim in it, bubbles rise, a shadow wanes it.

    ``phase`` 1 = full .. 0 = new; ``pearl`` 0..1 turns it into the calm pearl in the basin.
    """
    S = 2
    R = max(3, round(radius * S))
    size = R * 2 + 8
    c = size // 2
    sphere = pygame.Surface((size, size), pygame.SRCALPHA)
    core = mix(MOON_CORE, (255, 255, 255), swell * 0.5)
    edge = mix(MOON_EDGE, (255, 244, 220), pearl * 0.6)
    for r in range(R, 0, -2):
        u = r / R
        color = mix(core, edge, u ** 1.7)
        shift = (1 - u) * R * 0.28
        pygame.draw.circle(sphere, color, (round(c - shift), round(c - shift)), r)
    inner = pygame.Surface((size, size), pygame.SRCALPHA)
    # The sea inside the moon, sloshing.
    level = c + R * (0.12 - 0.05 * math.sin(t * 1.3))
    wave = [(x, level + math.sin(x * 0.09 + t * 2.4) * R * 0.06 + math.sin(x * 0.05 - t * 1.7) * R * 0.04)
            for x in range(0, size + 1, 4)]
    pygame.draw.polygon(inner, (*mix(WATER, WATER_DEEP, 0.55), 150), wave + [(size, size), (0, size)])
    pygame.draw.lines(inner, (*WATER_LIGHT, 170), False, wave, max(1, S))
    # Light-fish.
    for k in range(3):
        a = t * (0.7 + 0.13 * k) + k * 2.1
        fx = c + math.cos(a) * R * 0.52
        fy = c + math.sin(a * 1.6 + k) * R * 0.34 + R * 0.08
        heading = -1 if math.sin(a) > 0 else 1
        body = pygame.Rect(0, 0, 7 * S, 3 * S)
        body.center = (round(fx), round(fy))
        pygame.draw.ellipse(inner, (255, 236, 170, 230), body)
        tail_x = fx - heading * 4.5 * S
        wag = math.sin(t * 12 + k) * 1.4 * S
        pygame.draw.polygon(inner, (255, 196, 120, 220), [(fx - heading * 3 * S, fy), (tail_x, fy - 2 * S + wag), (tail_x, fy + 2 * S + wag)])
        pygame.draw.circle(inner, (255, 255, 240, 120), (round(fx), round(fy)), 5 * S, 1)
    # Bubbles rising.
    for k in range(6):
        by = c + R - ((t * 22 * S + k * 23 * S) % (2 * R))
        bx = c + math.sin(k * 2.3 + t * 1.4) * R * 0.5
        pygame.draw.circle(inner, (230, 252, 255, 170), (round(bx), round(by)), max(1, round((1 + k % 3) * S * 0.8)), 1)
    # The waning shadow: limb on the left, terminator ellipse inside.
    lit = max(0.0, min(1.0, phase))
    if lit < 0.995:
        k = 2 * lit - 1
        shadow = []
        for i in range(25):
            a = -math.pi / 2 + math.pi * i / 24
            shadow.append((c - R * math.cos(a), c + R * math.sin(a)))
        for i in range(24, -1, -1):
            a = -math.pi / 2 + math.pi * i / 24
            shadow.append((c - k * R * math.cos(a), c + R * math.sin(a)))
        pygame.draw.polygon(inner, (10, 22, 56, round(190 * (1 - pearl))), shadow)
    # Cracks spreading as it breaks.
    if crack > 0:
        rng = random.Random(4)
        for _ in range(7):
            a = rng.uniform(0, math.tau)
            x, y = c + math.cos(a) * R, c + math.sin(a) * R
            points = [(x, y)]
            length = R * crack * rng.uniform(0.6, 1.1)
            step = length / 4
            heading = a + math.pi + rng.uniform(-0.4, 0.4)
            for _ in range(4):
                heading += rng.uniform(-0.6, 0.6)
                x += math.cos(heading) * step
                y += math.sin(heading) * step
                points.append((x, y))
            pygame.draw.lines(inner, (255, 255, 255, 230), False, points, max(1, S))
    inner.blit(_circle_mask(size, R), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sphere.blit(inner, (0, 0))
    # Rim light and a window of reflected sky.
    pygame.draw.circle(sphere, (*WATER_LIGHT, 200), (c, c), R, max(1, S))
    highlight = pygame.Rect(0, 0, round(R * 1.2), round(R * 1.2))
    highlight.center = (round(c - R * 0.22), round(c - R * 0.22))
    pygame.draw.arc(sphere, (255, 255, 255, 220), highlight, math.radians(100), math.radians(170), max(2, 2 * S))
    pygame.draw.circle(sphere, (255, 255, 255, 235), (round(c - R * 0.45), round(c - R * 0.42)), max(1, round(R * 0.08)))
    return pygame.transform.smoothscale(sphere, (size // S, size // S))


def ring_points(center: tuple[float, float], rx: float, ry: float, tilt: float, steps: int = 64):
    """Points of a tilted ellipse with their depth (+1 nearest the viewer)."""
    cx, cy = center
    ct, st = math.cos(tilt), math.sin(tilt)
    for k in range(steps + 1):
        a = k * math.tau / steps
        x, y = math.cos(a) * rx, math.sin(a) * ry
        yield (cx + x * ct - y * st, cy + x * st + y * ct), math.sin(a)


def draw_armillary(surface: pygame.Surface, center: tuple[float, float], radius: float, zodiac: float,
                   meridian: float, front: bool, glow: float) -> None:
    """Half of the moon's armillary: the far half before the moon is drawn, the near half after."""
    cx, cy = center
    shade = 1.0 if front else 0.62
    band_dark = mix(BRASS_DARK, (20, 16, 26), 1 - shade)
    band = mix(BRASS, (40, 30, 40), 1 - shade)
    band_light = mix(BRASS_LIGHT, (60, 50, 60), 1 - shade)
    # The meridian: a vertical ring spinning about the moon's axis.
    R = radius + 20
    points = []
    for k in range(49):
        phi = k * math.tau / 48
        x = R * math.cos(phi) * math.cos(meridian)
        z = R * math.cos(phi) * math.sin(meridian)
        points.append(((cx + x, cy + R * math.sin(phi)), z >= 0))
    _draw_band(surface, points, front, band_dark, band, band_light, 4)
    # The zodiac band, tilted, carrying its twelve medallions.
    rx, ry = radius + 38, 13
    points = [(p, depth >= 0) for p, depth in ring_points(center, rx, ry, -0.2)]
    _draw_band(surface, points, front, band_dark, band, band_light, 5)
    images = medallions()
    ct, st = math.cos(-0.2), math.sin(-0.2)
    for k in range(12):
        a = zodiac + k * math.tau / 12
        near = math.sin(a) >= 0
        if near != front:
            continue
        x, y = math.cos(a) * rx, math.sin(a) * ry
        px, py = cx + x * ct - y * st, cy + x * st + y * ct
        image = images[k]
        if not front:
            image = pygame.transform.smoothscale(image, (10, 10))
        surface.blit(image, image.get_rect(center=(round(px), round(py))))
        if front and glow > 0.05 and math.sin(a) > 0.92:
            # The sign passing the front catches the moonlight.
            pygame.draw.circle(surface, (255, 250, 220), (round(px) - 1, round(py) - 2), 1)


def _draw_band(surface: pygame.Surface, points, front: bool, dark: Color, mid: Color, light: Color, width: int) -> None:  # noqa: ANN001
    run: list[tuple[float, float]] = []
    runs = []
    for point, near in points:
        if near == front:
            run.append(point)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    for run in runs:
        if len(run) < 2:
            continue
        pygame.draw.lines(surface, dark, False, run, width + 2)
        pygame.draw.lines(surface, mid, False, run, width)
        pygame.draw.lines(surface, light, False, [(x, y - 1) for x, y in run], 1)
