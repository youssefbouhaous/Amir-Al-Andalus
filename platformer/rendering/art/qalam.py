"""The Night Qalam: a scribe's reed pen whose ink is a piece of the night sky.

Its strokes are deep indigo with a violet rim and stars that twinkle inside
them. A stroke is written like a calligrapher's kashida - the long level
stroke that stretches a word - with a square dot where the nib bites in, a
gently breathing body, and a flick at the end. As it dries it dulls, cracks
and flakes away, and its stars drift up out of it.
"""

import math
import random
from functools import lru_cache

import pygame

from core import settings
from rendering.art.kit import Canvas, mix
from rendering.glow import blit_glow

Color = tuple[int, int, int]
Point = tuple[float, float]

INK: Color = (20, 16, 42)
INK_DEEP: Color = (10, 8, 26)
INK_SHEEN: Color = (74, 68, 150)
INK_RIM: Color = (132, 104, 232)
DRY: Color = (84, 76, 104)
STAR: Color = (255, 252, 236)
STAR_GOLD: Color = (255, 222, 140)
PEN_GOLD: Color = (240, 190, 84)
PEN_DARK: Color = (138, 88, 34)
REED: Color = (206, 166, 104)
OUTLINE: Color = (40, 26, 20)


def thickness(u: float) -> float:
    """Half-thickness of a kashida stroke along its length (0 = where the nib bit in)."""
    if u < 0.07:
        return 5.5
    swell = 3.2 + 0.9 * math.sin(u * math.pi * 1.6)
    taper = 1.0 if u < 0.72 else max(0.2, 1.0 - (u - 0.72) / 0.28)
    return swell * taper


def centre_offset(u: float, phase: float) -> float:
    """The stroke breathes a little up and down, and flicks up at its end."""
    wave = math.sin(u * math.tau * 1.3 + phase) * 1.8
    flick = -max(0.0, (u - 0.86) / 0.14) ** 2 * 7
    return wave + flick


def draw_stroke(surface: pygame.Surface, start: Point, length: float, direction: int, t: float, age: float,
                life: float, phase: float, stars: list[tuple[float, float, float]], written: float = 1.0) -> None:
    """One night-ink stroke on screen: ``start`` is where the nib bit in, ``written`` how much is drawn."""
    if length < 2:
        return
    sx, sy = start
    drawn = length * max(0.0, min(1.0, written))
    samples = max(2, int(drawn / 6))
    dry = max(0.0, (age - (life - 1.2)) / 1.2)
    body = mix(INK, DRY, dry * 0.8)
    rim = mix(INK_RIM, DRY, dry)
    top: list[Point] = []
    bottom: list[Point] = []
    for k in range(samples + 1):
        d = drawn * k / samples
        u = d / length
        y = sy + centre_offset(u, phase)
        half = thickness(u)
        x = sx + direction * d
        top.append((x, y - half))
        bottom.append((x, y + half))
    outline = top + bottom[::-1]
    if len(outline) >= 3:
        glow_strength = 0.35 * (1 - dry)
        for k in range(0, samples + 1, max(1, samples // 6)):
            blit_glow(surface, ((top[k][0] + bottom[k][0]) / 2, (top[k][1] + bottom[k][1]) / 2), 14, INK_RIM, glow_strength)
        pygame.draw.polygon(surface, rim, [(x, y - 1) for x, y in top] + [(x, y + 1) for x, y in bottom[::-1]])
        pygame.draw.polygon(surface, body, outline)
        # The wet sheen along the upper edge.
        if dry < 0.8 and samples > 3:
            sheen = [(x, y + 1.2) for x, y in top[1:max(2, int(samples * 0.7))]]
            if len(sheen) >= 2:
                pygame.draw.lines(surface, mix(INK_SHEEN, DRY, dry), False, sheen, 1)
        # Cracks as it dries.
        if dry > 0.3:
            rng = random.Random(int(phase * 1000))
            for _ in range(int(6 * dry)):
                k = rng.randrange(1, samples)
                x, y = (top[k][0] + bottom[k][0]) / 2, (top[k][1] + bottom[k][1]) / 2
                pygame.draw.line(surface, INK_DEEP, (x - 2, y - 2), (x + 2, y + 2), 1)
    # The square dot where the nib bit in (the calligrapher's rhombus).
    dot = 6.5
    pygame.draw.polygon(surface, rim, [(sx, sy - dot - 1), (sx + dot + 1, sy), (sx, sy + dot + 1), (sx - dot - 1, sy)])
    pygame.draw.polygon(surface, body, [(sx, sy - dot), (sx + dot, sy), (sx, sy + dot), (sx - dot, sy)])
    # Stars shining inside the ink.
    for su, sv, sp in stars:
        d = su * length
        if d > drawn:
            continue
        u = su
        x = sx + direction * d
        y = sy + centre_offset(u, phase) + sv * thickness(u) * 0.7
        twinkle = 0.5 + 0.5 * math.sin(t * (3 + sp) + sp * 7)
        if twinkle < 0.25 or dry > 0.9:
            continue
        color = STAR if sp < 2.2 else STAR_GOLD
        if twinkle > 0.85:
            pygame.draw.line(surface, color, (x - 2, y), (x + 2, y))
            pygame.draw.line(surface, color, (x, y - 2), (x, y + 2))
        else:
            surface.fill(color, (round(x), round(y), 1, 1))


def draw_comet(surface: pygame.Surface, center: Point, direction: int, t: float) -> None:
    """The flying head of a stroke: a drop of night with a violet halo and sparks."""
    x, y = center
    blit_glow(surface, center, 20, INK_RIM, 0.8)
    pygame.draw.circle(surface, INK_RIM, (round(x), round(y)), 7)
    pygame.draw.circle(surface, INK, (round(x), round(y)), 6)
    pygame.draw.circle(surface, STAR, (round(x + direction * 2), round(y - 2)), 1)
    for k in range(3):
        a = t * 20 + k * 2.1
        pygame.draw.circle(surface, STAR_GOLD, (round(x - direction * (8 + k * 5)), round(y + math.sin(a) * 4)), 1)


def make_stars(seed: int, count: int = 16) -> list[tuple[float, float, float]]:
    rng = random.Random(seed)
    return [(rng.uniform(0.04, 0.95), rng.uniform(-0.8, 0.8), rng.uniform(0.0, 3.0)) for _ in range(count)]


# --- the pen ------------------------------------------------------------------------------------------------
def paint_pen(c: Canvas, tip: Point, angle: float, length: float, width: float, glow: float = 0.0) -> None:
    """A reed pen with a brass cap: the nib at ``tip``, the reed running back at ``angle`` (radians)."""
    tx, ty = tip
    dx, dy = math.cos(angle), math.sin(angle)
    nx, ny = -dy, dx

    def at(along: float, side: float) -> Point:
        return tx + dx * along + nx * side, ty + dy * along + ny * side

    nib = [at(0, 0), at(length * 0.16, width * 0.5), at(length * 0.16, -width * 0.5)]
    c.polygon(INK, nib, OUTLINE, max(0.4, width * 0.08))
    c.polygon(REED, [at(length * 0.14, width * 0.5), at(length * 0.8, width * 0.55), at(length * 0.8, -width * 0.55),
                     at(length * 0.14, -width * 0.5)], OUTLINE, max(0.4, width * 0.1))
    c.line(mix(REED, (255, 255, 255), 0.3), at(length * 0.18, width * 0.2), at(length * 0.78, width * 0.25), max(0.4, width * 0.12))
    c.polygon(PEN_GOLD, [at(length * 0.72, width * 0.62), at(length, width * 0.5), at(length * 1.04, 0), at(length, -width * 0.5),
                         at(length * 0.72, -width * 0.62)], OUTLINE, max(0.4, width * 0.1))
    for f in (0.76, 0.84, 0.92):
        c.line(PEN_DARK, at(length * f, width * 0.55), at(length * f, -width * 0.55), max(0.3, width * 0.08))
    c.circle((224, 44, 70), at(length * 1.04, 0), max(0.6, width * 0.22))


@lru_cache(maxsize=16)
def pen_image(size: int, angle_deg: int) -> pygame.Surface:
    """The pen at ``size`` px long, pointing its nib along ``angle_deg`` (0 = right)."""
    c = Canvas(size + 8, size + 8, fringe=OUTLINE)
    angle = math.radians(angle_deg)
    centre = (size / 2 + 4, size / 2 + 4)
    tip = (centre[0] + math.cos(angle) * size / 2, centre[1] + math.sin(angle) * size / 2)
    paint_pen(c, tip, angle + math.pi, size, max(2.0, size * 0.1))
    return c.finish()


@lru_cache(maxsize=4)
def inkwell_image(size: int) -> pygame.Surface:
    """A small brass inkwell brimming with night."""
    c = Canvas(size, size, fringe=OUTLINE)
    s = size / 20
    c.ellipse(PEN_DARK, (4 * s, 11 * s, 12 * s, 7 * s), OUTLINE, 0.6 * s)
    c.ellipse(PEN_GOLD, (4 * s, 9 * s, 12 * s, 7 * s), OUTLINE, 0.6 * s)
    c.ellipse(INK, (6 * s, 9.6 * s, 8 * s, 3.4 * s))
    c.circle(STAR, (8 * s, 10.8 * s), 0.5 * s)
    c.circle(STAR_GOLD, (11.6 * s, 11.2 * s), 0.4 * s)
    return c.finish()


def draw_icon(surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    """HUD emblem: the pen over its inkwell, writing a tiny stroke of night."""
    well = inkwell_image(rect.width)
    surface.blit(well, well.get_rect(midbottom=(rect.centerx - 2, rect.bottom + 2)))
    u = (t % 2.4) / 2.4
    stroke_x = rect.left + 4
    pygame.draw.line(surface, INK_RIM, (stroke_x, rect.top + 9), (stroke_x + round(18 * min(1.0, u * 1.6)), rect.top + 9), 3)
    pygame.draw.line(surface, INK, (stroke_x, rect.top + 9), (stroke_x + round(18 * min(1.0, u * 1.6)), rect.top + 9), 2)
    pen = pen_image(round(rect.width * 0.8), 135)
    tip = (stroke_x + 18 * min(1.0, u * 1.6), rect.top + 9)
    surface.blit(pen, pen.get_rect(center=(tip[0] + rect.width * 0.26, tip[1] - rect.width * 0.26)))
    if int(t * 5) % 3 == 0:
        surface.fill(STAR, (round(tip[0]), round(tip[1]) - 3, 1, 1))


# --- the name written in night, for the grant ceremony ---------------------------------------------------------
@lru_cache(maxsize=2)
def name_in_night(size: int) -> pygame.Surface:
    """أمير (Amir) in the calligraphy font, filled with a starry night."""
    from ui.text import TextStyle, render_arabic

    path = settings.FONTS_DIR / settings.FONT_FILES.get("arabic", "")
    try:
        font = pygame.font.Font(path, size) if path.is_file() else pygame.font.Font(None, size)
    except (pygame.error, OSError):
        font = pygame.font.Font(None, size)
    glyphs = render_arabic(font, "أمير", TextStyle(color=(255, 255, 255), shadow=None))
    w, h = glyphs.get_size()
    night = pygame.Surface((w, h), pygame.SRCALPHA)
    night.fill((*INK, 255))
    rng = random.Random(9)
    for _ in range(w * h // 90):
        x, y = rng.randrange(w), rng.randrange(h)
        night.fill(STAR if rng.random() < 0.8 else STAR_GOLD, (x, y, 1 + (rng.random() < 0.2), 1))
    night.blit(glyphs, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    rim = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    halo = glyphs.copy()
    halo.fill((*INK_RIM, 0), special_flags=pygame.BLEND_RGB_MULT)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        rim.blit(halo, (2 + dx, 2 + dy))
    rim.blit(night, (2, 2))
    return rim
