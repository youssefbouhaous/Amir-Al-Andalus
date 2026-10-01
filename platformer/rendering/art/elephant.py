"""The Elephant Clock of level 2, and the setting sun it has stolen.

Al-Jazari's most famous machine is a clock carried by an elephant: a castle
on its back, a mahout on its neck, a scribe who writes the hours, falcons
that drop brass balls into the mouths of serpents, and a phoenix that turns
on the dome. The thief's version is colossal and enchanted. It stands in the
market street behind the last rooftop and holds the setting sun in its
trunk, so that sundown never comes.

Coordinates are relative to the elephant's foot: x = 0 under the middle of
its body, y = 0 on the rooftop line (negative is up); it faces left. Static
parts are painted once (supersampled) and cached; the ear, trunk, serpent,
phoenix, falcons, mahout and the sun are drawn per frame from cached poses.
"""

import math
import random
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas, mix, shade
from rendering.glow import blit_glow

Color = tuple[int, int, int]
Point = tuple[float, float]

OUTLINE: Color = (58, 34, 22)
BRASS: Color = (214, 160, 72)
BRASS_DARK: Color = (150, 96, 40)
BRASS_DEEP: Color = (110, 66, 30)
BRASS_LIGHT: Color = (255, 224, 150)
GOLD: Color = (250, 204, 96)
IVORY: Color = (246, 236, 212)
IVORY_SHADE: Color = (212, 196, 164)
CRIMSON: Color = (176, 34, 48)
CRIMSON_DARK: Color = (120, 20, 34)
TURQUOISE: Color = (48, 190, 186)
LAPIS: Color = (40, 74, 162)
RUBY: Color = (224, 44, 70)
PEARL: Color = (250, 246, 236)
SUN_EDGE: Color = (255, 150, 54)
SUN_CORE: Color = (255, 252, 226)

# Where things are, relative to the foot.
EYE: Point = (-198.0, -134.0)
TRUNK_ROOT: Point = (-226.0, -104.0)
EAR_ROOT: Point = (-160.0, -178.0)
MAHOUT: Point = (-122.0, -176.0)
HOWDAH_X = 50.0
WINDOWS: tuple[Point, ...] = ((0.0, -216.0), (50.0, -220.0), (100.0, -216.0))
FALCONS: tuple[Point, ...] = ((-34.0, -286.0), (134.0, -286.0))
SERPENT_PIVOT: Point = (-40.0, -262.0)
PHOENIX: Point = (50.0, -372.0)
SUN_RADIUS = 34.0

BASE_SIZE = (560, 460)
BASE_ORIGIN = (330, 420)      # the foot inside the static sprite


def _sp(points, dx: float, dy: float) -> list[Point]:  # noqa: ANN001
    return [(x + dx, y + dy) for x, y in points]


def _superellipse(center: Point, rx: float, ry: float, steps: int = 40, power: float = 0.8) -> list[Point]:
    cx, cy = center
    out = []
    for k in range(steps):
        a = k * math.tau / steps
        c, s = math.cos(a), math.sin(a)
        out.append((cx + rx * math.copysign(abs(c) ** power, c), cy + ry * math.copysign(abs(s) ** power, s)))
    return out


def _arch(cx: float, bottom: float, width: float, height: float) -> list[Point]:
    """A pointed (Andalusian) arch outline."""
    half = width / 2
    spring = bottom - height * 0.55
    points = [(cx - half, bottom), (cx - half, spring)]
    for k in range(1, 7):
        u = k / 7
        points.append((cx - half + half * math.sin(u * math.pi / 2) * 1.0, spring - (bottom - spring) * 0.82 * math.sin(u * math.pi / 2) ** 0.8 * u ** 0.2))
    points.append((cx, bottom - height))
    for x, y in reversed(points[2:-1]):
        points.append((2 * cx - x, y))
    points += [(cx + half, spring), (cx + half, bottom)]
    return points


@lru_cache(maxsize=None)
def base() -> pygame.Surface:
    """Body, caparison, castle, head, headdress and tusks - everything that doesn't move."""
    w, h = BASE_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = BASE_ORIGIN

    def P(x: float, y: float) -> Point:
        return ox + x, oy + y

    def PS(points) -> list[Point]:  # noqa: ANN001
        return [P(x, y) for x, y in points]

    # --- the body: a great brass barrel, lit from the sun it holds (up and to the left) -----------
    body = _superellipse((40, -70), 178, 98, 48, 0.82)
    c.polygon(BRASS_DARK, PS(body), OUTLINE, 1.6)
    c.polygon(BRASS, PS(_superellipse((30, -84), 166, 82, 48, 0.82)))
    c.polygon(BRASS_LIGHT, PS(_superellipse((-10, -128), 120, 26, 36, 0.9)))
    # Hind leg and rump (the rest stands in the street below).
    c.capsule(BRASS_DARK, P(178, -58), P(180, 60), 30, OUTLINE, 1.4)
    c.capsule(BRASS, P(170, -54), P(172, 60), 20)
    c.rect(GOLD, (*P(148, -14), 62, 9), 3, OUTLINE, 1.0)
    for k in range(5):
        c.circle(TURQUOISE if k % 2 else RUBY, P(156 + k * 11, -9.5), 2.0)
    # Tail with a brass tassel.
    c.tapered(BRASS_DARK, PS([(212, -120), (226, -96), (230, -64)]), 2.6, 1.6)
    c.circle(GOLD, P(231, -58), 4.0, OUTLINE, 0.8)
    # Engraved panels and rivets on the flank.
    for k in range(5):
        x = -60 + k * 52
        c.lines(BRASS_DEEP, PS([(x, -150 + abs(k - 2) * 6), (x - 6, -100), (x - 4, -40)]), 1.0)
    for k in range(18):
        x = -80 + k * 16
        c.circle(BRASS_LIGHT, P(x, -38 + math.sin(k) * 2), 1.4)
    for k in range(3):
        cx = -30 + k * 80
        c.lines(BRASS_DEEP, PS([(cx + 18 * math.cos(a), -70 + 12 * math.sin(a) + 4 * math.sin(3 * a)) for a in
                                (i * math.tau / 20 for i in range(21))]), 1.0)
    # --- the caparison: crimson cloth with a gold border, turquoise stars and tassels ---------
    top = [(-58, -160), (-10, -168), (60, -170), (120, -166), (156, -154)]
    scallops = []
    for k in range(9):
        x = 156 - k * 26.75
        scallops += [(x, -62 - (k % 2) * 4), (x - 13.4, -46 - (k % 2) * 4)]
    cloth = top + scallops + [(-58, -60)]
    c.polygon(CRIMSON, PS(cloth), OUTLINE, 1.2)
    inner = [(-48, -152), (60, -160), (146, -146), (146, -74), (-48, -72)]
    c.lines(GOLD, PS(inner + inner[:1]), 2.2)
    c.lines(CRIMSON_DARK, PS([(-40, -140), (60, -146), (138, -134)]), 1.0)
    for k, x in enumerate((-8, 50, 108)):
        c.star(TURQUOISE if k != 1 else LAPIS, P(x, -108), 12, 8, 0.6, 0.2, GOLD, 1.0)
        c.circle(GOLD, P(x, -108), 3.4)
        c.circle(RUBY, P(x, -108), 1.8)
    for k in range(9):
        x = 156 - k * 26.75 - 13.4
        tip = P(x, -44 - (k % 2) * 4)
        c.line(GOLD, tip, (tip[0], tip[1] + 8), 1.4)
        c.circle(GOLD, (tip[0], tip[1] + 10), 2.4, OUTLINE, 0.6)
    # --- the castle on its back ---------------------------------------------------------------
    hx = HOWDAH_X
    c.rect(GOLD, (*P(hx - 96, -178), 192, 14), 2, OUTLINE, 1.0)
    for k in range(13):
        c.circle(GOLD, P(hx - 90 + k * 15, -162), 2.2, OUTLINE, 0.6)
    wall = [(hx - 82, -178), (hx + 82, -178), (hx + 82, -264), (hx - 82, -264)]
    c.polygon(BRASS, PS(wall), OUTLINE, 1.2)
    c.polygon(BRASS_DARK, PS([(hx + 40, -178), (hx + 82, -178), (hx + 82, -264), (hx + 40, -264)]))
    # Three pointed windows, cut through (the stolen sun glows behind them), with lattice.
    for wx, wy in WINDOWS:
        arch = _arch(wx, wy + 32, 28, 58)
        c.polygon(OUTLINE, PS(_sp(arch, 0, 0)))
        c.lines(GOLD, PS(arch), 1.4, closed=True)
    # (the openings are punched out below, after the rest is painted)
    for x in (hx - 82, hx + 82):
        c.rect(BRASS_LIGHT if x < hx else BRASS_DARK, (*P(x - 8, -268), 16, 92), 2, OUTLINE, 1.0)
        c.polygon(GOLD, PS([(x - 11, -268), (x + 11, -268), (x + 7, -284), (x, -292), (x - 7, -284)]), OUTLINE, 0.9)
    c.rect(GOLD, (*P(hx - 86, -272), 172, 9), 1, OUTLINE, 1.0)
    for k in range(11):
        c.rect(GOLD, (*P(hx - 78 + k * 15, -281), 8, 9), 1, OUTLINE, 0.7)
    # The dome: an onion of ribbed gold, with a turquoise band and a finial.
    profile = ((58, -276), (68, -290), (70, -302), (62, -316), (48, -328), (30, -338), (12, -346), (0, -352))
    dome = [(hx - x, y) for x, y in profile] + [(hx + x, y) for x, y in reversed(profile)]
    c.polygon(GOLD, PS(dome), OUTLINE, 1.2)
    for k in range(1, 8):
        f = (k - 4) / 4
        c.lines(BRASS_DARK, PS([(hx + x * f, y) for x, y in profile]), 1.0)
    c.polygon(BRASS_LIGHT, PS([(hx - 52, -290), (hx - 50, -306), (hx - 34, -324), (hx - 26, -318), (hx - 40, -298)]))
    c.rect(TURQUOISE, (*P(hx - 58, -288), 116, 7), 2, OUTLINE, 0.8)
    for k in range(8):
        c.circle(GOLD, P(hx - 50 + k * 14.3, -284.5), 1.4)
    c.line(GOLD, P(hx, -346), P(hx, -358), 2.4)
    c.circle(RUBY, P(hx, -350), 3.0, OUTLINE, 0.6)
    # --- the head -------------------------------------------------------------------------------
    head_parts = (((-168, -122), 66), ((-188, -150), 44), ((-196, -98), 44), ((-140, -96), 50))
    for (x, y), r in head_parts:
        c.circle(OUTLINE, P(x, y), r + 1.6)
    for (x, y), r in head_parts:
        c.circle(BRASS, P(x, y), r)
    c.circle(BRASS_LIGHT, P(-196, -166), 24)
    c.circle(mix(BRASS, BRASS_LIGHT, 0.5), P(-176, -150), 30)
    c.circle(BRASS_DARK, P(-130, -84), 34)
    c.circle(BRASS, P(-150, -104), 40)
    # Mouth and the root of the tusks.
    c.polygon(BRASS_DEEP, PS([(-214, -84), (-196, -70), (-176, -74), (-190, -88)]), OUTLINE, 0.8)
    far = [(-186, -72), (-218, -62), (-244, -76), (-256, -100)]
    c.tapered(IVORY_SHADE, PS(far), 5.4, 2.0)
    c.circle(GOLD, P(far[-1][0], far[-1][1]), 2.6, OUTLINE, 0.6)
    # The headdress: a gold chanfron with a ruby, and strings of pearls.
    plate = [(-226, -186), (-178, -192), (-176, -170), (-196, -118), (-214, -126)]
    c.polygon(GOLD, PS(plate), OUTLINE, 1.0)
    c.polygon(BRASS_LIGHT, PS([(-220, -182), (-196, -186), (-202, -160), (-212, -150)]))
    c.circle(RUBY, P(-200, -158), 6.0, OUTLINE, 1.0)
    c.circle((255, 180, 190), P(-202, -160), 2.0)
    for k in range(4):
        x0 = -222 + k * 12
        for j in range(4):
            c.circle(PEARL, P(x0 - j * 0.6, -180 + 18 + j * 5 + k), 1.6)
    # The eye socket (the eye itself glows, drawn live).
    c.ellipse(BRASS_DEEP, (*P(EYE[0] - 10, EYE[1] - 7), 20, 14), OUTLINE, 1.0)
    c.lines(BRASS_DARK, PS([(-212, -146), (-198, -150), (-184, -144)]), 1.6)
    # Wrinkled brass at the root of the trunk.
    for k in range(4):
        c.lines(BRASS_DARK, PS([(-232 + k * 3, -120 + k * 9), (-220 + k * 3, -118 + k * 9), (-208 + k * 3, -122 + k * 9)]), 1.0)
    image = c.finish()
    # Punch the window openings through, so the glow painted behind shows between the lattice bars.
    holes = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    holes.fill((255, 255, 255, 255))
    for wx, wy in WINDOWS:
        arch = _arch(wx, wy + 30, 24, 54)
        pygame.draw.polygon(holes, (255, 255, 255, 0), PS(arch))
    image.blit(holes, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    lattice = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    for wx, wy in WINDOWS:
        clip = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(clip, (255, 255, 255, 255), PS(_arch(wx, wy + 30, 24, 54)))
        bars = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        for k in range(-6, 7):
            x = ox + wx + k * 6
            pygame.draw.line(bars, (*BRASS_DEEP, 255), (x - 30, oy + wy - 30), (x + 30, oy + wy + 30), 2)
            pygame.draw.line(bars, (*BRASS_DEEP, 255), (x + 30, oy + wy - 30), (x - 30, oy + wy + 30), 2)
        bars.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        lattice.blit(bars, (0, 0))
    image.blit(lattice, (0, 0))
    return image


TUSK_SIZE = (110, 70)
TUSK_ORIGIN = (100, 40)   # where the tusk leaves the jaw, inside its sprite
TUSK_ROOT: Point = (-206.0, -82.0)


@lru_cache(maxsize=None)
def tusk() -> pygame.Surface:
    """The near tusk, ivory banded with gold, drawn in front of the trunk."""
    w, h = TUSK_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = TUSK_ORIGIN
    curve = [(ox, oy), (ox - 34, oy + 12), (ox - 66, oy + 2), (ox - 86, oy - 26)]
    c.tapered(OUTLINE, curve, 8.4, 3.4)
    c.tapered(IVORY, curve, 7.0, 2.4)
    c.tapered((255, 252, 240), [(x, y - 2.2) for x, y in curve[:3]], 2.0, 0.8)
    for x, y in (curve[0], (ox - 20, oy + 8)):
        c.line(GOLD, (x, y - 7), (x, y + 7), 2.4)
    c.circle(GOLD, curve[-1], 3.6, OUTLINE, 0.7)
    c.circle(RUBY, curve[-1], 1.4)
    return c.finish()


# --- the ear -------------------------------------------------------------------------------------------
EAR_SIZE = (140, 170)
EAR_ORIGIN = (12, 22)  # the ear's root inside its sprite


@lru_cache(maxsize=None)
def ear(frame: int) -> pygame.Surface:
    """The great fan of the ear, spreading back over the neck; eight frames of a slow flap."""
    w, h = EAR_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = EAR_ORIGIN
    flap = 0.86 + 0.16 * (0.5 + 0.5 * math.cos(frame / 8 * math.tau))
    shape = [(0, 0), (40, -12), (88, 4), (108, 58), (96, 122), (60, 140), (22, 124), (4, 68)]

    def P(x: float, y: float) -> Point:
        return ox + x * flap, oy + y

    c.polygon(BRASS_DARK, [P(x, y) for x, y in shape], OUTLINE, 1.4)
    inner = [(10, 8), (40, -2), (80, 12), (96, 58), (86, 112), (58, 128), (26, 114), (12, 66)]
    c.polygon(BRASS, [P(x, y) for x, y in inner])
    c.polygon(mix(BRASS, BRASS_LIGHT, 0.45), [P(x, y) for x, y in ((14, 12), (40, 6), (64, 16), (44, 44), (20, 38))])
    # Gold filigree veins fanning from the root, and a jewelled rim.
    for k in range(5):
        a = 0.15 + k * 0.3
        c.lines(GOLD, [P(8, 14), P(8 + 44 * math.cos(a), 14 + 44 * math.sin(a)), P(8 + 86 * math.cos(a), 14 + 86 * math.sin(a))], 1.0)
    for x, y in shape[1:7]:
        c.circle(GOLD, P(x * 0.96, y * 0.96 + 2), 1.9)
    c.circle(TURQUOISE, P(52, 64), 4.4, OUTLINE, 0.8)
    c.circle(RUBY, P(52, 64), 1.8)
    return c.finish()


# --- the trunk ----------------------------------------------------------------------------------------
TRUNK_SIZE = (220, 330)
TRUNK_ORIGIN = (200, 300)  # the trunk's root inside its sprite


def trunk_curve(sway: float, lift: float) -> list[Point]:
    """Centre line of the trunk, relative to its root. ``lift`` 0 = holding the sun, 1 = raised high, -1 = bowed."""
    root = (0.0, 0.0)
    if lift >= 0:
        c1 = (-80 - 10 * sway, 46 - 30 * lift)
        c2 = (-110 + 6 * sway - 20 * lift, -150 - 60 * lift)
        tip = (-62 + 4 * sway - 30 * lift, -196 - 70 * lift)
    else:
        b = -lift
        c1 = (-60, 40 + 20 * b)
        c2 = (-110 + 30 * b, -150 + 220 * b)
        tip = (-62 - 10 * b, -196 + 290 * b)
    points = []
    for k in range(25):
        u = k / 24
        x = (1 - u) ** 3 * root[0] + 3 * (1 - u) ** 2 * u * c1[0] + 3 * (1 - u) * u * u * c2[0] + u ** 3 * tip[0]
        y = (1 - u) ** 3 * root[1] + 3 * (1 - u) ** 2 * u * c1[1] + 3 * (1 - u) * u * u * c2[1] + u ** 3 * tip[1]
        points.append((x, y))
    return points


def sun_hold(sway: float, lift: float) -> Point:
    """Where the held sun sits, relative to the trunk root."""
    points = trunk_curve(sway, lift)
    (x1, y1), (x2, y2) = points[-2], points[-1]
    heading = math.atan2(y2 - y1, x2 - x1)
    return x2 + math.cos(heading) * 10 + math.sin(heading) * 6, y2 + math.sin(heading) * 10 - SUN_RADIUS * 0.8


@lru_cache(maxsize=None)
def trunk(sway_step: int, lift_step: int) -> pygame.Surface:
    """Cached trunk poses: sway -4..4 and lift -4..4 (quarters)."""
    sway, lift = sway_step / 4, lift_step / 4
    w, h = TRUNK_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = TRUNK_ORIGIN
    points = [(ox + x, oy + y) for x, y in trunk_curve(sway, lift)]
    count = len(points)
    for index in range(count - 1):
        u = index / (count - 1)
        r = 18 - 11 * u
        c._capsule(OUTLINE, points[index], points[index + 1], r + 1.6)
    for index in range(count - 1):
        u = index / (count - 1)
        r = 18 - 11 * u
        c._capsule(BRASS, points[index], points[index + 1], r)
    for index in range(count - 1):
        u = index / (count - 1)
        r = 18 - 11 * u
        (x1, y1), (x2, y2) = points[index], points[index + 1]
        heading = math.atan2(y2 - y1, x2 - x1)
        nx, ny = -math.sin(heading), math.cos(heading)
        c._capsule(BRASS_LIGHT, (x1 - nx * r * 0.45, y1 - ny * r * 0.45), (x2 - nx * r * 0.45, y2 - ny * r * 0.45), r * 0.28)
        if index % 2 == 0:
            # The rings of a trunk, as bands of darker brass.
            c.line(BRASS_DARK, (x1 + nx * r * 0.9, y1 + ny * r * 0.9), (x1 - nx * r * 0.9, y1 - ny * r * 0.9), 1.2)
    # Gold bands at the root and a curled tip gripping the sun.
    x, y = points[3]
    c.circle(GOLD, (x, y), 4.0, OUTLINE, 0.8)
    (x1, y1), (x2, y2) = points[-2], points[-1]
    heading = math.atan2(y2 - y1, x2 - x1)
    for side in (-1, 1):
        a = heading + side * 1.1
        c.tapered(BRASS, [(x2, y2), (x2 + math.cos(a) * 9, y2 + math.sin(a) * 9), (x2 + math.cos(a - side * 0.9) * 14, y2 + math.sin(a - side * 0.9) * 14)], 4.0, 1.6)
    return c.finish()


# --- the serpent, phoenix, falcons, mahout and scribe -------------------------------------------------
SERPENT_SIZE = (120, 190)
SERPENT_ORIGIN = (90, 16)   # the pivot at the top


@lru_cache(maxsize=None)
def serpent(mouth: int) -> pygame.Surface:
    """A brass serpent hanging from the castle, mouth up to catch the falcon's ball."""
    w, h = SERPENT_SIZE
    c = Canvas(w, h, scale=3, fringe=OUTLINE)
    ox, oy = SERPENT_ORIGIN
    body = []
    for k in range(20):
        u = k / 19
        body.append((ox - 18 * math.sin(u * math.pi * 1.6) - 36 * u, oy + 130 * u))
    c.tapered(OUTLINE, body, 8.6, 5.6)
    c.tapered(BRASS_DARK, body, 7.4, 4.4)
    for k in range(0, 19, 2):
        x, y = body[k]
        c.circle(TURQUOISE if k % 4 == 0 else GOLD, (x + 2, y), 2.0)
    hx, hy = body[-1]
    open_ = 0.3 + 0.5 * mouth
    c.polygon(BRASS, [(hx - 6, hy - 4), (hx - 26, hy + 2 - 10 * open_), (hx - 22, hy + 8), (hx + 4, hy + 8)], OUTLINE, 1.0)
    c.polygon(CRIMSON_DARK, [(hx - 8, hy + 4), (hx - 24, hy + 2 - 6 * open_), (hx - 22, hy + 8 + 8 * open_)])
    c.polygon(BRASS_DARK, [(hx - 4, hy + 6), (hx - 24, hy + 10 + 10 * open_), (hx - 18, hy + 14 + 8 * open_), (hx + 4, hy + 12)], OUTLINE, 1.0)
    c.circle(RUBY, (hx - 10, hy - 2), 2.2)
    for k in range(3):
        c.line(GOLD, (hx - 2 + k * 3, hy - 6), (hx + 6 + k * 3, hy - 14), 1.2)
    return c.finish()


def serpent_mouth(angle: float) -> Point:
    """The serpent's mouth relative to its pivot, when swung by ``angle`` degrees."""
    x, y = -36.0 - 18 * math.sin(1.6 * math.pi) - 18, 138.0
    a = math.radians(-angle)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


@lru_cache(maxsize=None)
def phoenix(frame: int) -> pygame.Surface:
    """The phoenix on the dome, turning on its spindle (eight frames of one turn)."""
    c = Canvas(64, 56, scale=4, fringe=OUTLINE)
    cx, cy = 32.0, 34.0
    turn = math.cos(frame / 8 * math.tau)
    span = 22 * abs(turn) + 5
    for side in (-1, 1):
        wing = [(cx, cy - 2), (cx + side * span, cy - 16), (cx + side * span * 0.8, cy - 6), (cx + side * span * 0.55, cy + 2)]
        c.polygon(GOLD if side * turn > 0 else BRASS_DARK, wing, OUTLINE, 0.8)
        for k in range(3):
            c.line(RUBY if k == 1 else TURQUOISE, (cx + side * span * (0.4 + 0.2 * k), cy - 6 - 3 * k), (cx + side * span * (0.2 + 0.2 * k), cy - 1), 0.8)
    for k in range(3):
        c.tapered(GOLD, [(cx, cy + 4), (cx + (k - 1) * 6 * turn, cy + 14), (cx + (k - 1) * 9 * turn, cy + 20)], 2.0, 0.8)
    c.ellipse(GOLD, (cx - 5, cy - 8, 10, 14), OUTLINE, 0.8)
    c.circle(GOLD, (cx + 2 * turn, cy - 12), 4.2, OUTLINE, 0.8)
    c.polygon(BRASS_DARK, [(cx + 5 * turn + 3 * (1 if turn >= 0 else -1), cy - 12), (cx + 10 * turn + 5 * (1 if turn >= 0 else -1), cy - 11), (cx + 5 * turn + 3 * (1 if turn >= 0 else -1), cy - 10)])
    c.lines(RUBY, [(cx, cy - 16), (cx - 3, cy - 21), (cx + 1, cy - 24)], 1.0)
    return c.finish()


@lru_cache(maxsize=None)
def falcon(lean: int, holding: bool) -> pygame.Surface:
    """A brass falcon on a turret; ``lean`` 0..3 tips it forward to drop its ball."""
    c = Canvas(40, 40, scale=4, fringe=OUTLINE)
    angle = lean * 16
    cx, cy = 20.0, 26.0

    def R(x: float, y: float) -> Point:
        a = math.radians(angle)
        dx, dy = x - cx, y - cy
        return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)

    c.polygon(BRASS_DARK, [R(22, 22), R(34, 30), R(32, 34), R(20, 30)], OUTLINE, 0.7)          # tail
    c.ellipse(BRASS, (cx - 8, cy - 8, 16, 14), OUTLINE, 0.8)
    c.polygon(BRASS_DARK, [R(20, 20), R(30, 22), R(26, 30), R(16, 28)], OUTLINE, 0.6)          # wing
    c.circle(BRASS, R(12, 16), 5.0, OUTLINE, 0.8)
    c.polygon(GOLD, [R(7, 15), R(2, 18), R(7, 19)], OUTLINE, 0.5)
    c.circle(OUTLINE, R(11, 15), 1.0)
    if holding:
        c.circle(GOLD, R(2, 21), 3.2, OUTLINE, 0.7)
        c.circle((255, 250, 200), R(1.2, 20.2), 1.0)
    for x in (16, 22):
        c.line(BRASS_DEEP, R(x, 33), R(x, 38), 1.0)
    return c.finish()


@lru_cache(maxsize=None)
def mahout(frame: int) -> pygame.Surface:
    """The brass mahout on the neck; frames 0..2 raise and strike his hammer, 3 bows."""
    c = Canvas(40, 44, scale=4, fringe=OUTLINE)
    bx, by = 20.0, 40.0
    bow = frame == 3
    lean = 6 if bow else 0
    c.polygon(BRASS, [(bx - 7, by), (bx + 7, by), (bx + 4 - lean, by - 16), (bx - 4 - lean, by - 16)], OUTLINE, 0.8)
    c.line(TURQUOISE, (bx - 6, by - 6), (bx + 6, by - 6), 1.4)
    head = (bx - 1 - lean, by - 21 + (3 if bow else 0))
    c.circle(BRASS_LIGHT, head, 4.4, OUTLINE, 0.8)
    c.ellipse(CRIMSON, (head[0] - 5, head[1] - 7.4, 10, 5), OUTLINE, 0.6)
    c.circle(GOLD, (head[0], head[1] - 6.6), 1.0)
    c.circle(OUTLINE, (head[0] - 2, head[1]), 0.6)
    shoulder = (bx - 2 - lean, by - 14)
    angle = (-150, -100, -40, -20)[frame]
    a = math.radians(angle)
    hand = (shoulder[0] + math.cos(a) * 9, shoulder[1] + math.sin(a) * 9)
    c.line(BRASS, shoulder, hand, 1.8)
    head_a = a - 1.4
    c.line(BRASS_DEEP, hand, (hand[0] + math.cos(head_a) * 4, hand[1] + math.sin(head_a) * 4), 1.4)
    c.rect(GOLD, (hand[0] - 3.4, hand[1] - 2.2, 6.8, 4.4), 0.8, OUTLINE, 0.6)
    return c.finish()


@lru_cache(maxsize=None)
def scribe(frame: int) -> pygame.Surface:
    """The scribe in the castle's middle window, writing the hours (four frames)."""
    c = Canvas(24, 30, scale=4, fringe=OUTLINE)
    c.polygon(BRASS_LIGHT, [(6, 30), (18, 30), (16, 16), (8, 16)], OUTLINE, 0.6)
    c.circle(BRASS_LIGHT, (12, 12), 4.0, OUTLINE, 0.6)
    c.ellipse(IVORY, (7, 5, 10, 5), OUTLINE, 0.5)
    c.rect(IVORY, (2, 22, 10, 6), 0.5, OUTLINE, 0.5)
    pen = (4 + (frame % 2) * 3, 22 - (frame // 2) * 2)
    c.line(BRASS, (14, 18), pen, 1.4)
    c.line(OUTLINE, pen, (pen[0] - 2, pen[1] + 3), 0.8)
    return c.finish()


# --- the stolen sun ----------------------------------------------------------------------------------------
_GRANULES = [(random.Random(3 + k).uniform(0, math.tau), random.Random(5 + k).uniform(0.1, 0.85),
              random.Random(7 + k).uniform(1.2, 3.0)) for k in range(22)]


def draw_sun(surface: pygame.Surface, center: Point, radius: float, t: float, strength: float = 1.0,
             setting: float = 0.0) -> None:
    """The setting sun, caught: a molten disc, flame tongues, and a great warm glow.

    ``setting`` 0..1 deepens it toward the red of the last moment before it goes down.
    """
    cx, cy = center
    edge = mix(SUN_EDGE, (240, 80, 60), setting)
    core = mix(SUN_CORE, (255, 190, 120), setting)
    blit_glow(surface, center, round(radius * 4.2), mix((255, 140, 60), (255, 80, 70), setting), 0.45 * strength)
    blit_glow(surface, center, round(radius * 2.3), mix((255, 200, 110), (255, 130, 90), setting), 0.85 * strength)
    S = 2
    size = round(radius * 2 * 1.9 * S)
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    R = radius * S
    # Flame tongues licking out of the rim, slowly turning.
    for k in range(18):
        a = t * 0.25 + k * math.tau / 18
        flick = 0.5 + 0.5 * math.sin(t * 5 + k * 1.7)
        length = R * (1.18 + 0.26 * flick + 0.1 * (k % 3 == 0))
        width = 0.2
        tongue = [(c + math.cos(a - width) * R * 0.92, c + math.sin(a - width) * R * 0.92),
                  (c + math.cos(a + 0.04 * math.sin(t * 3 + k)) * length, c + math.sin(a + 0.04 * math.sin(t * 3 + k)) * length),
                  (c + math.cos(a + width) * R * 0.92, c + math.sin(a + width) * R * 0.92)]
        pygame.draw.polygon(layer, (*mix(edge, (255, 220, 120), flick * 0.5), 235), tongue)
    for r in range(round(R), 0, -2):
        u = r / R
        pygame.draw.circle(layer, (*mix(core, edge, u ** 1.8), 255), (round(c - (1 - u) * R * 0.18), round(c - (1 - u) * R * 0.18)), r)
    # Slowly churning granules on the molten face.
    for angle, dist, size_ in _GRANULES:
        a = angle + t * 0.15 * (1 if dist < 0.5 else -1)
        x = c + math.cos(a) * dist * R
        y = c + math.sin(a) * dist * R
        pygame.draw.circle(layer, (*mix(core, edge, 0.35 + 0.3 * dist), 180), (round(x), round(y)), max(1, round(size_ * S)))
    pygame.draw.circle(layer, (255, 255, 240, 200), (round(c - R * 0.35), round(c - R * 0.35)), max(1, round(R * 0.16)))
    image = pygame.transform.smoothscale(layer, (size // S, size // S))
    surface.blit(image, image.get_rect(center=(round(cx), round(cy))))
