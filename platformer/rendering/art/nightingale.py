"""The Brass Nightingale: the singing automaton taught by level 1's pages.

One vector model drawn at any size - tiny on Amir's shoulder, large in the
grant ceremony - and the same silhouette folded out of paper before it is
gilded. Coordinates are "bird units" (the body is about 11 long, facing
right, origin at the middle of the body, y down); ``scale`` turns units into
pixels.
"""

import math
from dataclasses import dataclass, replace
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas, mix

Point = tuple[float, float]
Color = tuple[int, int, int]

BRASS: Color = (228, 174, 74)
BRASS_DARK: Color = (150, 96, 36)
BRASS_LIGHT: Color = (255, 236, 168)
OUTLINE: Color = (62, 34, 18)
ENAMEL: Color = (46, 204, 192)
ENAMEL_DEEP: Color = (30, 96, 186)
ENAMEL_LIGHT: Color = (176, 252, 238)
PAPER: Color = (250, 240, 216)
PAPER_SHADE: Color = (206, 186, 150)
INK: Color = (86, 62, 46)
EYE: Color = (24, 14, 22)
RUBY: Color = (232, 58, 84)
NOTE_GOLD: Color = (255, 222, 130)

BODY: tuple[Point, ...] = (
    (-4.8, -0.2), (-3.4, -2.6), (-0.8, -3.9), (2.2, -4.0), (4.4, -3.0), (5.6, -1.2),
    (5.8, 0.6), (4.8, 2.4), (2.8, 3.6), (0.2, 3.9), (-2.4, 3.2), (-4.2, 1.6),
)
BACK_SHADE: tuple[Point, ...] = ((-3.4, -2.6), (-0.8, -3.9), (2.2, -4.0), (1.6, -2.7), (-1.0, -2.4), (-3.0, -1.4))
NECK: Point = (4.0, -3.0)
SHOULDER: Point = (1.7, -1.3)
TAIL_BASE: Point = (-4.4, 0.4)
# The outline of the whole bird, for the paper stage (same number of points as the square).
SILHOUETTE: tuple[Point, ...] = (
    (-12.0, 0.9), (-10.4, -1.8), (-3.4, -2.8), (-0.4, -4.3), (3.4, -5.8), (4.8, -7.8),
    (7.0, -6.6), (10.8, -4.8), (7.4, -3.2), (5.8, 0.8), (2.6, 3.8), (-4.4, 1.8),
)


@dataclass(frozen=True)
class BirdPose:
    wing: float = 0.0      # -1 downstroke, 0 folded, 1 raised high
    beak: float = 0.0      # 0 closed .. 1 wide open
    tail: float = 0.0      # -1 lowered .. 1 cocked up
    head: float = 0.0      # head tilt in degrees (negative looks up)
    gear: float = 0.0      # chest gear rotation, radians
    bob: float = 0.0       # body offset in units (breathing, hops)
    perched: bool = True   # legs down
    gild: float = 1.0      # 0 paper .. 1 brass
    enamel: float = 1.0    # 0 bare wing .. 1 enamelled (feather by feather)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _rot(point: Point, pivot: Point, degrees: float) -> Point:
    a = math.radians(degrees)
    x, y = point[0] - pivot[0], point[1] - pivot[1]
    return pivot[0] + x * math.cos(a) - y * math.sin(a), pivot[1] + x * math.sin(a) + y * math.cos(a)


def _feather(base: Point, angle: float, length: float, width: float) -> list[Point]:
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    def at(along: float, side: float) -> Point:
        return base[0] + dx * length * along + nx * width * side, base[1] + dy * length * along + ny * width * side
    return [at(0, 0.35), at(0.35, 1.0), at(0.8, 0.8), at(1.0, 0.0), at(0.8, -0.8), at(0.35, -1.0), at(0, -0.35)]


# Wing feather angles (screen degrees: 180 points back, 270 points up) for the three key poses.
_WING_DOWN = ((140, 8.8), (152, 8.4), (164, 7.6), (176, 6.8))
_WING_FOLDED = ((172, 7.8), (180, 7.0), (188, 6.0), (196, 4.9))
_WING_UP = ((236, 9.8), (250, 9.2), (264, 8.4), (278, 7.4))


def wing_feathers(wing: float) -> list[tuple[float, float]]:
    if wing >= 0:
        return [(_lerp(a0, a1, wing), _lerp(l0, l1, wing)) for (a0, l0), (a1, l1) in zip(_WING_FOLDED, _WING_UP)]
    t = -wing
    return [(_lerp(a0, a1, t), _lerp(l0, l1, t)) for (a0, l0), (a1, l1) in zip(_WING_FOLDED, _WING_DOWN)]


def paint(c: Canvas, origin: Point, scale: float, pose: BirdPose, facing: int = 1) -> None:
    """Draw the bird on ``c`` with its body centre at ``origin`` (canvas pixels)."""
    ox, oy = origin
    oy += pose.bob * scale

    def P(point: Point) -> Point:
        return ox + point[0] * scale * facing, oy + point[1] * scale

    def PS(points) -> list[Point]:  # noqa: ANN001
        return [P(p) for p in points]

    gild = pose.gild
    body = mix(PAPER, BRASS, gild)
    dark = mix(PAPER_SHADE, BRASS_DARK, gild)
    light = mix((255, 252, 240), BRASS_LIGHT, gild)
    line = mix(INK, OUTLINE, gild)
    ow = max(0.45, 0.32 * scale)
    feathers = wing_feathers(pose.wing)

    # The far wing peeks out behind the body when the wings are raised.
    if pose.wing > 0.25:
        far = [(angle + 10, length * 0.9) for angle, length in feathers]
        for k, (angle, length) in reversed(list(enumerate(far))):
            base = (SHOULDER[0] - 0.5 - 0.5 * k, SHOULDER[1] - 0.4 + 0.3 * k)
            fill = mix(dark, shade_enamel(k, 0.55), _enamel_amount(pose.enamel, k))
            c.polygon(fill, PS(_feather(base, angle, length, 1.25)), line, ow)

    # Tail: a fan of three feathers, enamel eyes at the tips.
    base_angle = 168 + 20 * pose.tail
    for k, (spread, length) in enumerate(((-15, 7.0), (15, 6.8), (0, 7.8))):
        angle = base_angle + spread
        c.polygon(dark if k < 2 else body, PS(_feather(TAIL_BASE, angle, length, 1.3)), line, ow)
        a = math.radians(angle)
        tip = (TAIL_BASE[0] + math.cos(a) * length * 0.72, TAIL_BASE[1] + math.sin(a) * length * 0.72)
        if pose.enamel > 0.2:
            c.circle(mix(dark, ENAMEL, pose.enamel), P(tip), 0.75 * scale)
            c.circle(mix(dark, ENAMEL_DEEP, pose.enamel), P(tip), 0.38 * scale)

    if pose.perched:
        for hip, foot in (((0.0, 3.4), (-0.4, 6.1)), ((1.9, 3.2), (2.1, 6.1))):
            c.line(dark, P(hip), P(foot), max(0.5, 0.45 * scale))
            for toe in (-1.2, 0.2, 1.3):
                c.line(dark, P(foot), P((foot[0] + toe, foot[1] + 0.35)), max(0.4, 0.35 * scale))

    # Body, with a darker back and a bright breast.
    c.polygon(body, PS(BODY), line, ow)
    c.polygon(dark, PS(BACK_SHADE))
    c.ellipse(light, _rect(P((1.4, -1.6)), P((5.0, 3.0))))
    if gild < 1.0:
        # Paper creases left over from the fold.
        crease = mix(PAPER_SHADE, BRASS_DARK, gild)
        c.line(crease, P((-4.6, -0.2)), P((5.6, -1.0)), max(0.4, 0.25 * scale))
        c.line(crease, P((-0.8, -3.8)), P((0.4, 3.8)), max(0.4, 0.25 * scale))

    # The clockwork heart: a small gear set with a ruby, turning as it sings.
    gear_center = P((2.9, 0.9))
    teeth = []
    for k in range(16):
        a = pose.gear + k * math.tau / 16
        r = (1.55 if k % 2 == 0 else 1.15) * scale
        teeth.append((gear_center[0] + math.cos(a) * r, gear_center[1] + math.sin(a) * r))
    c.polygon(dark, teeth)
    c.circle(light, gear_center, 0.85 * scale)
    c.circle(mix(dark, RUBY, pose.enamel), gear_center, 0.45 * scale)

    # Near wing: cloisonne feathers, lapis and turquoise between brass wires.
    for k, (angle, length) in enumerate(feathers):
        base = (SHOULDER[0] - 0.3 * k, SHOULDER[1] + 0.5 * k)
        fill = mix(body, shade_enamel(k, 1.0), _enamel_amount(pose.enamel, k))
        c.polygon(fill, PS(_feather(base, angle, length, 1.55)), mix(line, BRASS_DARK, gild * 0.6), ow)
        if pose.enamel > 0 and scale > 2.2:
            a = math.radians(angle)
            c.line(mix(body, BRASS_LIGHT, gild), P(base), P((base[0] + math.cos(a) * length * 0.9, base[1] + math.sin(a) * length * 0.9)),
                   max(0.4, 0.14 * scale))
    mean = sum(angle for angle, _ in feathers) / len(feathers)
    c.polygon(body, PS(_feather((SHOULDER[0] + 1.0, SHOULDER[1] - 0.3), mean, 3.0, 1.45)), line, ow)
    c.polygon(light, PS(_feather((SHOULDER[0] + 0.9, SHOULDER[1] - 0.55), mean - 4, 1.9, 0.55)))

    # Head (tilts about the neck): crest, eye, enamel cheek, and the beak.
    tilt = pose.head

    def H(point: Point) -> Point:
        return P(_rot(point, NECK, tilt))

    crest = [H(p) for p in ((4.5, -6.8), (3.8, -8.0), (4.4, -8.9), (5.4, -8.6), (5.4, -7.9))]
    c.lines(light, crest, max(0.5, 0.42 * scale))
    c.circle(mix(light, ENAMEL, pose.enamel), crest[-1], 0.45 * scale)
    c.circle(body, H((5.2, -4.5)), 2.75 * scale, line, ow)
    c.circle(light, H((4.7, -5.3)), 1.1 * scale)
    c.circle(mix(light, ENAMEL, pose.enamel), H((5.1, -3.5)), 0.7 * scale)
    upper = [H((7.1, -5.4)), H((10.8, -4.9 - 1.0 * pose.beak)), H((7.5, -4.3 - 0.25 * pose.beak))]
    lower = [H((7.5, -4.2 + 0.3 * pose.beak)), H((9.9, -4.0 + 1.5 * pose.beak)), H((7.0, -3.6))]
    if pose.beak > 0.05:
        c.polygon((120, 30, 40), [H((7.3, -4.5)), H((9.4, -4.7 - 0.7 * pose.beak)), H((8.9, -4.0 + 1.0 * pose.beak)), H((7.2, -3.9))])
    c.polygon(dark, lower, line, ow * 0.8)
    c.polygon(mix(dark, BRASS, 0.5), upper, line, ow * 0.8)
    c.circle(light, H((6.2, -5.1)), 1.15 * scale)
    c.circle(EYE, H((6.25, -5.1)), 0.8 * scale)
    c.circle((255, 255, 255), H((6.5, -5.4)), 0.28 * scale)


def shade_enamel(index: int, amount: float) -> Color:
    base = ENAMEL_DEEP if index % 2 == 0 else ENAMEL
    return mix(BRASS_DARK, base, amount)


def _enamel_amount(enamel: float, index: int) -> float:
    """Feathers enamel one after another as ``enamel`` goes 0 -> 1."""
    return max(0.0, min(1.0, enamel * 4.0 - (3 - index)))


def _rect(a: Point, b: Point) -> tuple[float, float, float, float]:
    return min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])


# --- paper stage -------------------------------------------------------------------------------
def paint_paper(c: Canvas, origin: Point, scale: float, fold: float, gild: float, glint: float, spin: float) -> None:
    """The leaf folding into a faceted paper bird (``fold`` 0..1), then gilding (``gild`` 0..1)."""
    ox, oy = origin
    count = len(SILHOUETTE)
    half = 6.5
    pivot = (0.0, -1.0)
    square = []
    for bx, by in SILHOUETTE:
        # Each corner of the bird starts where its ray from the centre meets the leaf's edge,
        # so the fold slides every point straight inward or outward.
        dx, dy = bx - pivot[0], by - pivot[1]
        reach = half / max(abs(dx), abs(dy), 1e-6)
        square.append(_rot((pivot[0] + dx * reach, pivot[1] + dy * reach), pivot, spin))
    ease = fold * fold * (3 - 2 * fold)
    points = [(_lerp(s[0], b[0], ease), _lerp(s[1], b[1], ease)) for s, b in zip(square, SILHOUETTE)]
    # The leaf turns over once while it folds.
    turn = 0.3 + 0.7 * abs(math.cos(fold * math.pi))
    points = [(pivot[0] + (x - pivot[0]) * turn, y) for x, y in points]
    center = (_lerp(0.0, 0.8, ease) * turn, _lerp(-1.0, -1.4, ease))

    def P(point: Point) -> Point:
        return ox + point[0] * scale, oy + point[1] * scale

    for k in range(count):
        a, b = points[k], points[(k + 1) % count]
        # Facets catch the light differently: that is what makes it read as folded paper.
        mid_x = (a[0] + b[0] + center[0]) / 3
        facing_light = 0.5 + 0.5 * math.cos(math.atan2(b[1] - a[1], b[0] - a[0]) - 0.8)
        paper = mix(PAPER_SHADE, PAPER, 0.35 + 0.65 * facing_light * (0.6 + 0.4 * (k % 2)))
        brass = mix(BRASS_DARK, BRASS_LIGHT, 0.2 + 0.8 * facing_light * (0.55 + 0.45 * (k % 2)))
        sweep = max(0.0, min(1.0, gild * 26 - (mid_x + 13)))
        c.polygon(mix(paper, brass, sweep), [P(center), P(a), P(b)])
    c.lines(mix(INK, OUTLINE, gild), [P(p) for p in points], max(0.6, 0.22 * scale), closed=True)
    for p in points[::2]:
        c.line(mix(PAPER_SHADE, BRASS_DARK, gild), P(center), P(p), max(0.4, 0.12 * scale))
    if 0.0 < glint < 1.0:
        x = -13 + 26 * glint
        c.line((255, 255, 236), P((x - 2.0, 5.0)), P((x + 2.0, -8.0)), max(0.8, 0.5 * scale))


# --- cached small frames for the shoulder bird --------------------------------------------------------
FRAME = 36
ORIGIN = (18.0, 20.0)
SMALL = 0.82

PERCH_POSES = (
    BirdPose(),
    BirdPose(bob=-0.25, tail=0.15),
    BirdPose(head=-16, tail=0.3),                     # looks up at the sky
    BirdPose(head=28, tail=0.4, wing=0.1),            # preens its wing
    BirdPose(head=-22, beak=0.8, tail=0.5),           # a little chirp
    BirdPose(tail=0.9, bob=-0.3),                     # tail flick
)
FLY_POSES = tuple(BirdPose(wing=w, perched=False, tail=-0.2, head=-4) for w in (-1.0, -0.2, 1.0, 0.4))
SING_POSES = tuple(BirdPose(head=-24, beak=b, tail=0.6, wing=w, perched=False, gear=g)
                   for b, w, g in ((0.4, 0.8, 0.0), (1.0, 1.0, 0.4), (0.6, 0.7, 0.8), (1.0, 0.9, 1.2)))
PECK_POSES = (BirdPose(head=40, beak=0.5, perched=False, wing=0.5), BirdPose(head=55, beak=0.0, perched=False, wing=-0.4),
              BirdPose(head=20, beak=0.7, perched=False, wing=0.6))


def _render(pose: BirdPose, scale: float = SMALL, size: int = FRAME, origin: Point = ORIGIN) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    paint(c, origin, scale, pose)
    return c.finish()


@lru_cache(maxsize=None)
def frames() -> dict[str, tuple[pygame.Surface, ...]]:
    """Small frames facing right; the body centre sits at ``ORIGIN``."""
    return {
        "perch": tuple(_render(p) for p in PERCH_POSES),
        "fly": tuple(_render(p) for p in FLY_POSES),
        "sing": tuple(_render(p) for p in SING_POSES),
        "peck": tuple(_render(p) for p in PECK_POSES),
    }


@lru_cache(maxsize=None)
def flipped() -> dict[str, tuple[pygame.Surface, ...]]:
    return {name: tuple(pygame.transform.flip(f, True, False) for f in group) for name, group in frames().items()}


@lru_cache(maxsize=64)
def icon_frame(size: int, beak: int) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    pose = BirdPose(head=-14 if beak else 0, beak=0.9 if beak else 0.0, tail=0.4)
    paint(c, (size * 0.56, size * 0.56), size / 25.0, pose)
    return c.finish()


def draw_icon(surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    """HUD emblem: the bird on its perch, singing now and then."""
    singing = (t % 3.0) > 2.4
    image = icon_frame(rect.width, 1 if singing and int(t * 8) % 2 == 0 else 0)
    surface.blit(image, image.get_rect(center=rect.center))
    if singing:
        u = ((t % 3.0) - 2.4) / 0.6
        note(surface, (rect.right - 2, rect.top + 6 - u * 6), 5, round(255 * (1 - u)))


def note(surface: pygame.Surface, center: Point, size: float, alpha: int = 255, color: Color = NOTE_GOLD) -> None:
    """A little eighth note (head, stem, flag)."""
    x, y = center
    s = size
    layer = pygame.Surface((round(s * 3), round(s * 4)), pygame.SRCALPHA)
    hx, hy = s * 0.9, s * 3.0
    pygame.draw.ellipse(layer, (*color, alpha), (hx - s * 0.8, hy - s * 0.55, s * 1.6, s * 1.1))
    pygame.draw.line(layer, (*color, alpha), (hx + s * 0.7, hy), (hx + s * 0.7, hy - s * 2.6), max(1, round(s * 0.28)))
    pygame.draw.line(layer, (*color, alpha), (hx + s * 0.7, hy - s * 2.6), (hx + s * 1.7, hy - s * 1.7), max(1, round(s * 0.28)))
    surface.blit(layer, (round(x - hx), round(y - hy)))


@lru_cache(maxsize=8)
def note_image(size: int, color: Color = NOTE_GOLD) -> pygame.Surface:
    layer = pygame.Surface((size * 3, size * 4), pygame.SRCALPHA)
    note(layer, (size * 0.9, size * 3.0), size, 255, color)
    return layer


def big(pose: BirdPose, scale: float, facing: int = 1) -> pygame.Surface:
    """A large one-off render (ceremony); the body centre is the image centre."""
    size = round(scale * 26)
    c = Canvas(size, size, fringe=OUTLINE)
    paint(c, (size / 2, size / 2), scale, pose, facing)
    return c.finish()


def pose_with(pose: BirdPose, **changes: float) -> BirdPose:
    return replace(pose, **changes)
