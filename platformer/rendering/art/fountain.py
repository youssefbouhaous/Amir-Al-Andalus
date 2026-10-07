"""The Rose Fountain's art: the brass rose, the water column it raises, and its crowns.

Al-Jazari's fountains change their shape at intervals; the rose remembers
three crowns - a lily, a fan and a turning rose of drops - and wears the next
one each time it blooms. In the manuscript it is drawn holding a ball upon its
crest, the famous trick of fountain-makers.
"""

import math
import random
from functools import lru_cache

import pygame

from rendering.art.kit import Canvas
from rendering.glow import blit_glow

Color = tuple[int, int, int]

OUTLINE: Color = (52, 32, 24)
BRASS: Color = (214, 160, 72)
BRASS_DARK: Color = (150, 96, 40)
BRASS_LIGHT: Color = (255, 226, 150)
TURQUOISE: Color = (40, 190, 184)
WATER: Color = (110, 214, 248)
WATER_DEEP: Color = (46, 132, 196)
WATER_LIGHT: Color = (224, 250, 255)
RAINBOW: tuple[Color, ...] = ((255, 90, 90), (255, 170, 70), (255, 236, 110), (120, 230, 120), (90, 170, 255), (150, 110, 240))


@lru_cache(maxsize=None)
def rose_image(size: int, open_amount: int = 4) -> pygame.Surface:
    """The brass rose seen from the side and a little above: eight petals round a turquoise heart."""
    c = Canvas(size, size, scale=4, fringe=OUTLINE)
    m = size / 2
    u = open_amount / 4
    rx, ry = size * (0.24 + 0.2 * u), size * (0.12 + 0.08 * u)
    for k in range(8):
        a = k * math.tau / 8 + 0.2
        px = m + math.cos(a) * rx
        py = m + math.sin(a) * ry
        petal_r = size * 0.13 * (0.6 + 0.4 * u)
        color = BRASS_LIGHT if math.sin(a) > 0 else BRASS
        c.circle(color, (px, py), petal_r, OUTLINE, size * 0.025)
    c.ellipse(BRASS_DARK, (m - rx * 0.6, m - ry * 0.6, rx * 1.2, ry * 1.2), OUTLINE, size * 0.02)
    c.ellipse(TURQUOISE, (m - rx * 0.32, m - ry * 0.4, rx * 0.64, ry * 0.7), OUTLINE, size * 0.015)
    c.circle((200, 250, 250), (m - rx * 0.1, m - ry * 0.2), size * 0.03)
    return c.finish()


@lru_cache(maxsize=None)
def column_texture(width: int, height: int = 64) -> pygame.Surface:
    """A tileable strip of rushing water: streaks and bubbles over translucent blue."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    rng = random.Random(width)
    for x in range(width):
        edge = abs(x - width / 2) / (width / 2)
        alpha = round(150 + 70 * (1 - edge ** 2))
        color = WATER if 0.2 < edge < 0.75 else (WATER_DEEP if edge >= 0.75 else (170, 232, 252))
        pygame.draw.line(surface, (*color, alpha), (x, 0), (x, height))
    for _ in range(width * 2):
        x = rng.randrange(1, width - 1)
        y = rng.randrange(height)
        length = rng.randint(6, 18)
        light = rng.random() < 0.6
        color = (*WATER_LIGHT, 200) if light else (*WATER_DEEP, 140)
        for dy in range(length):
            surface.set_at((x, (y + dy) % height), color)
    return surface


def draw_column(surface: pygame.Surface, base: tuple[float, float], height: float, t: float, width: int = 26,
                strength: float = 1.0) -> None:
    """The rushing column from ``base`` up ``height`` pixels, twisting as it climbs."""
    if height < 2:
        return
    bx, by = base
    texture = column_texture(width)
    tex_h = texture.get_height()
    top = by - height
    offset = int(t * 420) % tex_h
    y = top
    while y < by:
        chunk = min(tex_h - offset, by - y)
        wobble = math.sin(t * 13 + y * 0.07) * 1.5
        narrow = 1.0 - 0.18 * (by - y) / max(1.0, height)
        strip = texture.subsurface(pygame.Rect(0, offset, width, max(1, int(chunk))))
        if narrow < 0.99:
            strip = pygame.transform.smoothscale(strip, (max(2, round(width * narrow)), strip.get_height()))
        if strength < 0.99:
            strip = strip.copy()
            strip.set_alpha(round(255 * strength))
        surface.blit(strip, (round(bx - strip.get_width() / 2 + wobble), round(y)))
        y += chunk
        offset = 0
    # Two white threads spiralling up the column.
    for strand in range(2):
        points = []
        for k in range(16):
            f = k / 15
            yy = by - height * f
            a = f * 7 + t * 9 + strand * math.pi
            points.append((bx + math.sin(a) * width * 0.34 * (1 - 0.2 * f), yy))
        pygame.draw.lines(surface, WATER_LIGHT, False, points, 1)


def draw_crown(surface: pygame.Surface, top: tuple[float, float], shape: int, t: float, strength: float = 1.0) -> None:
    """The fountain's crown: a lily, a fan, or a turning rose of drops."""
    tx, ty = top
    blit_glow(surface, (tx, ty), 26, WATER_LIGHT, 0.6 * strength)
    if shape % 3 == 0:
        # A lily: five jets curving out and falling back like petals.
        for k in range(5):
            spread = (k - 2) / 2
            points = []
            for j in range(9):
                u = j / 8
                x = tx + spread * 30 * u
                y = ty - 18 * math.sin(u * math.pi * 0.9) + 26 * u * u * abs(spread) - 4 * (1 - abs(spread)) * u
                points.append((x, y))
            pygame.draw.lines(surface, WATER, False, points, 3)
            pygame.draw.lines(surface, WATER_LIGHT, False, points, 1)
            end = points[-1]
            for d in range(2):
                f = (t * 2 + k * 0.3 + d * 0.5) % 1.0
                pygame.draw.circle(surface, WATER_LIGHT, (round(end[0]), round(end[1] + f * 30)), 2)
    elif shape % 3 == 1:
        # A fan: seven straight jets opening like a peacock's tail.
        for k in range(7):
            a = math.radians(-90 + (k - 3) * 17 + math.sin(t * 6) * 3)
            length = 26 + 6 * math.sin(t * 9 + k)
            end = (tx + math.cos(a) * length, ty + math.sin(a) * length)
            pygame.draw.line(surface, WATER, (tx, ty), end, 3)
            pygame.draw.line(surface, WATER_LIGHT, (tx, ty), end, 1)
            pygame.draw.circle(surface, WATER_LIGHT, (round(end[0]), round(end[1])), 3)
    else:
        # A rose of drops turning on the crest.
        for ring, (radius, count) in enumerate(((10, 6), (18, 9), (26, 12))):
            for k in range(count):
                a = t * (3 - ring) * (1 if ring % 2 == 0 else -1) + k * math.tau / count
                x = tx + math.cos(a) * radius
                y = ty - 6 + math.sin(a) * radius * 0.35
                pygame.draw.circle(surface, WATER if ring else WATER_LIGHT, (round(x), round(y)), 3 - ring // 2)
    # Foam bubbling at the top of the column.
    for k in range(5):
        a = t * 8 + k * 1.3
        pygame.draw.circle(surface, (240, 252, 255), (round(tx + math.sin(a) * 8), round(ty + math.cos(a) * 2)), 4)


def draw_rainbow(surface: pygame.Surface, center: tuple[float, float], radius: float, strength: float) -> None:
    """A little dawn rainbow standing in the spray."""
    if strength <= 0.02:
        return
    size = round(radius * 2 + 20)
    layer = pygame.Surface((size, size // 2 + 10), pygame.SRCALPHA)
    for k, color in enumerate(RAINBOW):
        r = round(radius - k * 3)
        if r < 4:
            break
        rect = pygame.Rect(size // 2 - r, size // 2 - r, r * 2, r * 2)
        pygame.draw.arc(layer, (*color, round(110 * strength)), rect, 0.15, math.pi - 0.15, 3)
    surface.blit(layer, (round(center[0] - size / 2), round(center[1] - size / 2)))


def draw_icon(surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    """The HUD emblem: a brass rose and the jet it raises, with a drop riding the crest."""
    size = min(rect.width, rect.height)
    rose = rose_image(round(size * 0.8))
    base = (rect.centerx, rect.bottom - size * 0.22)
    height = size * (0.52 + 0.06 * math.sin(t * 4))
    pygame.draw.line(surface, WATER_DEEP, base, (base[0], base[1] - height), 6)
    pygame.draw.line(surface, WATER, base, (base[0], base[1] - height), 4)
    pygame.draw.line(surface, WATER_LIGHT, (base[0] - 1, base[1]), (base[0] - 1, base[1] - height), 1)
    top = (base[0], base[1] - height)
    for k in range(3):
        a = math.radians(-90 + (k - 1) * 40)
        end = (top[0] + math.cos(a) * size * 0.2, top[1] + math.sin(a) * size * 0.2 + size * 0.1)
        pygame.draw.line(surface, WATER_LIGHT, top, end, 2)
    pygame.draw.circle(surface, (255, 230, 120), (round(top[0]), round(top[1] - size * 0.12 + math.sin(t * 5) * 2)), max(2, round(size * 0.09)))
    surface.blit(rose, rose.get_rect(center=(round(base[0]), round(base[1] + size * 0.05))))


def draw_miniature(surface: pygame.Surface, rect: pygame.Rect, t: float, ink: Color) -> None:
    """The rose as painted in the book: a fountain holding a golden ball upon its crest."""
    size = min(rect.width, rect.height)
    base = (rect.centerx, rect.bottom - size * 0.16)
    height = size * 0.6
    top = (base[0], base[1] - height)
    pygame.draw.line(surface, WATER_DEEP, base, top, max(3, round(size * 0.1)))
    pygame.draw.line(surface, WATER, base, top, max(2, round(size * 0.06)))
    for k in range(4):
        a = math.radians(-90 + (k - 1.5) * 34)
        end = (top[0] + math.cos(a) * size * 0.28, top[1] + math.sin(a) * size * 0.18 + size * 0.22)
        pygame.draw.arc(surface, WATER, pygame.Rect(min(top[0], end[0]), top[1] - size * 0.08, abs(end[0] - top[0]) + 2,
                                                     size * 0.4), 0.3 if end[0] > top[0] else 1.6,
                        1.6 if end[0] > top[0] else 2.9, 2)
    ball = (round(top[0]), round(top[1] - size * 0.1 + math.sin(t * 3) * 2))
    pygame.draw.circle(surface, ink, ball, max(3, round(size * 0.09)) + 1)
    pygame.draw.circle(surface, (236, 186, 70), ball, max(3, round(size * 0.09)))
    rose = rose_image(max(8, round(size * 0.55)))
    surface.blit(rose, rose.get_rect(center=(round(base[0]), round(base[1]))))
    pygame.draw.line(surface, ink, (rect.left + 6, rect.bottom - 3), (rect.right - 6, rect.bottom - 3), 1)
