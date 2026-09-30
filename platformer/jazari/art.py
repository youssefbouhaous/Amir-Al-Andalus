"""Drawing kit for al-Jazari's machines and for the pages of his book.

Two visual languages live here:

* *Brass*: the machines as they stand in the world - gears, chains,
  pulleys, float bowls, tanks with visible waterlines, cylinders, dials.
  Everything is drawn from simple shapes each frame so moving parts
  (the part the player reads and interferes with) can be animated freely.
* *Ink*: the manuscript pages - iron-gall ink on parchment with lapis,
  vermilion and gold-leaf fills, like the 13th-century copies of
  "The Book of Knowledge of Ingenious Mechanical Devices".
"""

import math
import random

import pygame

from core.settings import Color

BRASS: Color = (214, 166, 72)
BRASS_LIGHT: Color = (255, 226, 140)
BRASS_DARK: Color = (120, 82, 30)
COPPER: Color = (190, 104, 60)
COPPER_DARK: Color = (104, 50, 28)
IRON: Color = (86, 88, 100)
IRON_LIGHT: Color = (150, 154, 170)
WOOD: Color = (120, 76, 42)
WOOD_DARK: Color = (72, 44, 24)
ROPE: Color = (186, 150, 96)
WATER: Color = (80, 170, 220)
WATER_LIGHT: Color = (190, 236, 255)
OUTLINE: Color = (40, 24, 16)

PARCHMENT: Color = (238, 220, 178)
PARCHMENT_DARK: Color = (206, 180, 128)
INK: Color = (52, 34, 26)
LAPIS: Color = (38, 72, 158)
VERMILION: Color = (196, 58, 36)
GOLD_LEAF: Color = (218, 170, 60)
VERDIGRIS: Color = (70, 150, 120)


def lerp_color(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


# --- brass primitives -----------------------------------------------------------------
def gear(surface: pygame.Surface, center: tuple[float, float], radius: float, teeth: int, angle: float,
         color: Color = BRASS, missing: tuple[int, int] | None = None, hub: bool = True) -> None:
    """A spur gear. ``missing`` = (first, count) teeth left out (segmental gears)."""
    cx, cy = center
    points = []
    steps = teeth * 4
    for k in range(steps):
        tooth = k // 4
        a = angle + k * math.tau / steps
        out = k % 4 in (1, 2)
        if missing is not None and missing[0] <= tooth < missing[0] + missing[1]:
            out = False
        r = radius + (radius * 0.16 if out else 0)
        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.polygon(surface, OUTLINE, points)
    inner = [(cx + (x - cx) * 0.9, cy + (y - cy) * 0.9) for x, y in points]
    pygame.draw.polygon(surface, color, inner)
    pygame.draw.circle(surface, lerp_color(color, OUTLINE, 0.35), (round(cx), round(cy)), max(2, round(radius * 0.62)), 2)
    for k in range(4):
        a = angle + k * math.pi / 2
        pygame.draw.line(surface, lerp_color(color, OUTLINE, 0.4), (cx, cy),
                         (cx + math.cos(a) * radius * 0.6, cy + math.sin(a) * radius * 0.6), 3)
    if hub:
        pygame.draw.circle(surface, OUTLINE, (round(cx), round(cy)), max(3, round(radius * 0.22)))
        pygame.draw.circle(surface, BRASS_LIGHT, (round(cx), round(cy)), max(2, round(radius * 0.14)))


def rope(surface: pygame.Surface, a: tuple[float, float], b: tuple[float, float], color: Color = ROPE,
         width: int = 3, twist: float = 0.0) -> None:
    pygame.draw.line(surface, OUTLINE, a, b, width + 2)
    pygame.draw.line(surface, color, a, b, width)
    length = math.dist(a, b)
    if length < 1:
        return
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    for d in range(0, int(length), 6):
        x = a[0] + ux * (d + twist % 6)
        y = a[1] + uy * (d + twist % 6)
        pygame.draw.line(surface, lerp_color(color, OUTLINE, 0.4), (x - uy * 1.5, y + ux * 1.5), (x + uy * 1.5 + ux * 2, y - ux * 1.5 + uy * 2), 1)


def chain(surface: pygame.Surface, points: list[tuple[float, float]], phase: float, color: Color = IRON_LIGHT,
          link: float = 9.0, twist: bool = False) -> None:
    """A chain of oval links along a polyline; ``twist`` flips links as a Möbius band."""
    if len(points) < 2:
        return
    total = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
    d = -(phase % (link * 2))
    index = 0
    segment_start = 0.0
    count = 0
    while d < total:
        while index < len(points) - 2 and d > segment_start + math.dist(points[index], points[index + 1]):
            segment_start += math.dist(points[index], points[index + 1])
            index += 1
        p, q = points[index], points[index + 1]
        seg = math.dist(p, q) or 1.0
        t = max(0.0, min(1.0, (d - segment_start) / seg))
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        angle = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        flat = count % 2 == 0
        if twist:
            flat = math.sin(d / total * math.pi * 2) > 0 if count % 2 else not (math.sin(d / total * math.pi * 2) > 0)
        w, h = (link + 3, 7) if flat else (link + 3, 3)
        oval = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(oval, OUTLINE, (0, 0, w + 2, h + 2))
        pygame.draw.ellipse(oval, color, (1, 1, w, h), 2 if flat else 0)
        rotated = pygame.transform.rotate(oval, -angle)
        surface.blit(rotated, rotated.get_rect(center=(round(x), round(y))))
        d += link
        count += 1


def pulley(surface: pygame.Surface, center: tuple[float, float], radius: float, angle: float) -> None:
    gear(surface, center, radius, 8, angle, WOOD, hub=True)
    pygame.draw.circle(surface, OUTLINE, (round(center[0]), round(center[1])), round(radius), 2)


def tank(surface: pygame.Surface, rect: pygame.Rect, level: float, time: float, color: Color = WATER,
         frame: Color = BRASS, marks: tuple[float, ...] = ()) -> None:
    """A glass-fronted tank with a visible, rippling waterline (0..1) and float marks."""
    pygame.draw.rect(surface, OUTLINE, rect.inflate(6, 6), border_radius=5)
    pygame.draw.rect(surface, (30, 28, 40), rect, border_radius=3)
    fill = round(rect.height * max(0.0, min(1.0, level)))
    if fill > 0:
        water = pygame.Rect(rect.x, rect.bottom - fill, rect.width, fill)
        pygame.draw.rect(surface, color, water, border_radius=3)
        points = [(x, water.top + math.sin(time * 4 + x * 0.25) * 1.5) for x in range(rect.left, rect.right + 1, 4)]
        if len(points) > 1:
            pygame.draw.lines(surface, WATER_LIGHT, False, points, 2)
    for mark in marks:
        y = rect.bottom - rect.height * mark
        pygame.draw.line(surface, VERMILION, (rect.left - 5, y), (rect.left + 4, y), 3)
        pygame.draw.line(surface, VERMILION, (rect.right - 4, y), (rect.right + 5, y), 3)
    pygame.draw.rect(surface, frame, rect.inflate(6, 6), 3, border_radius=5)
    pygame.draw.line(surface, (255, 255, 255), (rect.left + 4, rect.top + 4), (rect.left + 4, rect.bottom - 6), 1)


def cylinder(surface: pygame.Surface, rect: pygame.Rect, color: Color = COPPER, swell: float = 0.0,
             vertical: bool = False) -> None:
    r = rect.inflate(round(rect.width * swell * 0.12), round(rect.height * swell * 0.12))
    pygame.draw.rect(surface, OUTLINE, r.inflate(4, 4), border_radius=10)
    pygame.draw.rect(surface, color, r, border_radius=9)
    light = lerp_color(color, (255, 255, 255), 0.35)
    dark = lerp_color(color, OUTLINE, 0.45)
    if vertical:
        pygame.draw.rect(surface, light, (r.x + 4, r.y + 4, 5, r.height - 8), border_radius=3)
        for y in range(r.top + 10, r.bottom - 6, 14):
            pygame.draw.line(surface, dark, (r.left, y), (r.right, y), 2)
    else:
        pygame.draw.rect(surface, light, (r.x + 6, r.y + 3, r.width - 12, 5), border_radius=3)
        for x in range(r.left + 12, r.right - 6, 16):
            pygame.draw.line(surface, dark, (x, r.top), (x, r.bottom), 2)


def dial(surface: pygame.Surface, center: tuple[float, float], radius: float, value: float, glyphs: str,
         font: pygame.font.Font | None = None, color: Color = BRASS) -> None:
    """A rotating letter dial; ``value`` is a glyph index (fractional while turning)."""
    cx, cy = center
    pygame.draw.circle(surface, OUTLINE, (round(cx), round(cy)), round(radius + 3))
    pygame.draw.circle(surface, color, (round(cx), round(cy)), round(radius))
    pygame.draw.circle(surface, lerp_color(color, OUTLINE, 0.3), (round(cx), round(cy)), round(radius * 0.72), 2)
    count = len(glyphs)
    for k in range(count):
        a = -math.pi / 2 + (k - value) * math.tau / count
        x, y = cx + math.cos(a) * radius * 0.84, cy + math.sin(a) * radius * 0.84
        pygame.draw.circle(surface, OUTLINE if k else VERMILION, (round(x), round(y)), 2)
    pygame.draw.polygon(surface, VERMILION, ((cx - 4, cy - radius - 6), (cx + 4, cy - radius - 6), (cx, cy - radius + 2)))
    if font is not None:
        index = round(value) % count
        glyph = font.render(glyphs[index], True, OUTLINE)
        surface.blit(glyph, glyph.get_rect(center=(round(cx), round(cy))))


def emblem_frame(surface: pygame.Surface, center: tuple[float, float], radius: float, color: Color) -> None:
    """The eight-pointed brass rondel every guardian bears: its 'lock'."""
    cx, cy = center
    pts = []
    for k in range(16):
        a = -math.pi / 2 + k * math.pi / 8
        r = radius if k % 2 == 0 else radius * 0.78
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.polygon(surface, OUTLINE, [(cx + (x - cx) * 1.12, cy + (y - cy) * 1.12) for x, y in pts])
    pygame.draw.polygon(surface, BRASS, pts)
    pygame.draw.circle(surface, color, (round(cx), round(cy)), round(radius * 0.6))
    pygame.draw.circle(surface, OUTLINE, (round(cx), round(cy)), round(radius * 0.6), 1)


# --- ink / manuscript primitives --------------------------------------------------------
def parchment(size: tuple[int, int], seed: int) -> pygame.Surface:
    """A leaf of aged parchment: warm fibres, foxing and a ruled border."""
    width, height = size
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill((*PARCHMENT, 255))
    rng = random.Random(seed)
    for _ in range(width * height // 90):
        x, y = rng.randrange(width), rng.randrange(height)
        tone = rng.randrange(-18, 8)
        s.fill((PARCHMENT[0] + tone, PARCHMENT[1] + tone, PARCHMENT[2] + tone, 255), (x, y, rng.choice((1, 2, 3)), 1))
    for _ in range(9):
        x, y, r = rng.randrange(width), rng.randrange(height), rng.randrange(5, 22)
        spot = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(spot, (150, 110, 60, 28), (r, r), r)
        s.blit(spot, (x - r, y - r))
    # Darkened, slightly torn edges.
    for k in range(0, width, 3):
        tear = rng.randrange(0, 5)
        s.fill((0, 0, 0, 0), (k, 0, 3, tear))
        s.fill((0, 0, 0, 0), (k, height - rng.randrange(0, 5), 3, 5))
    edge = pygame.Surface(size, pygame.SRCALPHA)
    for i in range(10):
        pygame.draw.rect(edge, (120, 80, 40, 14), (i, i, width - i * 2, height - i * 2), 1)
    s.blit(edge, (0, 0))
    pygame.draw.rect(s, VERMILION, (14, 14, width - 28, height - 28), 2)
    pygame.draw.rect(s, GOLD_LEAF, (18, 18, width - 36, height - 36), 1)
    return s


def ink_line(surface: pygame.Surface, a: tuple[float, float], b: tuple[float, float], width: int = 2,
             color: Color = INK) -> None:
    pygame.draw.line(surface, color, a, b, width)


def label(surface: pygame.Surface, font: pygame.font.Font, text: str, at: tuple[float, float],
          color: Color = VERMILION) -> None:
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=(round(at[0]), round(at[1]))))


def arrow(surface: pygame.Surface, a: tuple[float, float], b: tuple[float, float], color: Color = VERMILION,
          width: int = 2) -> None:
    pygame.draw.line(surface, color, a, b, width)
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    for side in (-1, 1):
        tip = (b[0] - math.cos(angle + side * 0.45) * 8, b[1] - math.sin(angle + side * 0.45) * 8)
        pygame.draw.line(surface, color, b, tip, width)
