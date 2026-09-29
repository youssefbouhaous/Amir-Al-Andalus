"""Collectibles, projectiles and HUD icons."""

import math

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, mix, shade, star_polygon

OUTLINE: Color = (46, 26, 20)
GOLD: Color = (232, 178, 56)
GOLD_LIGHT: Color = (255, 230, 140)
GOLD_DARK: Color = (164, 110, 26)
WHITE: Color = (255, 255, 255)
POMEGRANATE: Color = (196, 32, 54)
POMEGRANATE_LIGHT: Color = (250, 116, 128)
POMEGRANATE_DARK: Color = (122, 16, 32)
FLAME: Color = (255, 158, 40)
FLAME_CORE: Color = (255, 240, 170)
SAPPHIRE: Color = (80, 150, 255)
SAPPHIRE_LIGHT: Color = (200, 230, 255)
PARCHMENT: Color = (240, 226, 188)
PARCHMENT_DARK: Color = (196, 168, 118)
INK: Color = (74, 44, 30)
HEART: Color = (228, 56, 86)


def paint_dinar(surface: pygame.Surface, _animation: str, frame: int) -> None:
    """A gold dinar spinning on its vertical axis (8 frames)."""
    size = surface.get_width()
    c = Canvas(size, size, fringe=GOLD_DARK)
    turn = math.cos(frame / 8 * math.tau)
    width = max(1.6, abs(turn) * (size - 3))
    face = turn >= 0
    x = size / 2 - width / 2
    c.ellipse(GOLD_DARK, (x, 1.2, width, size - 2.4), OUTLINE, 0.6)
    if width > 4:
        c.ellipse(GOLD if face else shade(GOLD, -0.1), (x + 0.9, 1.9, width - 1.8, size - 3.8))
        c.ellipse(GOLD_DARK, (x + 2.4, 3.4, width - 4.8, size - 6.8))
        c.ellipse(GOLD, (x + 2.9, 3.9, width - 5.8, size - 7.8))
        # Stylised inscription: a few strokes, squeezed with the turn.
        cx = size / 2
        for k, dy in enumerate((-2.0, 0.0, 2.0)):
            half = (width - 7) / 2 * (1.0 - abs(dy) * 0.12)
            if half > 0.6:
                c.line(GOLD_DARK, (cx - half, size / 2 + dy), (cx + half, size / 2 + dy), 0.6)
        c.ellipse(GOLD_LIGHT, (x + width * 0.22, 3.0, max(1.0, width * 0.18), size * 0.3))
    surface.blit(c.finish(), (0, 0))


def make_coin_icon(size: int = 18) -> pygame.Surface:
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    paint_dinar(icon, "spin", 0)
    return icon


def paint_pomegranate(surface: pygame.Surface, _animation: str, frame: int) -> None:
    size = surface.get_width()
    c = Canvas(size, size, fringe=OUTLINE)
    pulse = math.sin(frame / 4 * math.tau)
    cx, cy = size / 2, size / 2 + 2
    radius = 8.2 + pulse * 0.5
    c.circle(POMEGRANATE, (cx, cy), radius, OUTLINE, 0.9)
    c.circle(POMEGRANATE_DARK, (cx + 2.2, cy + 2.4), radius * 0.62)
    c.circle(POMEGRANATE, (cx - 0.6, cy - 0.4), radius * 0.72)
    c.ellipse(POMEGRANATE_LIGHT, (cx - 5.4, cy - 5.4, 4.2, 3.2))
    top = cy - radius
    crown = [(cx - 3.2, top + 1.6), (cx - 4.2, top - 2.8), (cx - 1.4, top - 0.8), (cx, top - 3.8),
             (cx + 1.4, top - 0.8), (cx + 4.2, top - 2.8), (cx + 3.2, top + 1.6)]
    c.polygon(POMEGRANATE_DARK, crown, OUTLINE, 0.7)
    if frame % 4 == 1:
        c.star(WHITE, (cx + 4.5, cy - 4.5), 2.0, points=4, inner=0.3)
    surface.blit(c.finish(), (0, 0))


def paint_oil_lamp(surface: pygame.Surface, _animation: str, frame: int) -> None:
    size = surface.get_width()
    c = Canvas(size, size, fringe=OUTLINE)
    flicker = math.sin(frame / 4 * math.tau)
    # Handle, body, spout.
    c.ring(GOLD_DARK, (4.5, 14.5), 2.8, 1.1)
    c.ellipse(GOLD, (3.5, 12, 15, 8), OUTLINE, 0.8)
    c.polygon(GOLD, [(15, 13.5), (22.5, 11), (21.5, 13), (17, 18)], OUTLINE, 0.7)
    c.ellipse(GOLD_LIGHT, (6.5, 13, 6, 2.2))
    c.rect(GOLD, (8, 9, 6, 3.4), radius=1, outline=OUTLINE, width=0.6)
    c.rect(GOLD_DARK, (7.5, 19, 7, 3), radius=1, outline=OUTLINE, width=0.6)
    # Flame.
    height = 6.5 + flicker * 1.6
    c.polygon(FLAME, [(20.0, 11.0), (22.0 + flicker * 0.6, 11.0 - height), (23.8, 11.0)])
    c.polygon(FLAME_CORE, [(20.9, 11.0), (22.0 + flicker * 0.4, 12.5 - height * 0.8), (23.0, 11.0)])
    surface.blit(c.finish(), (0, 0))


def paint_star_power(surface: pygame.Surface, _animation: str, frame: int) -> None:
    """The Najma: a glowing eight-pointed star that grants star throwing."""
    size = surface.get_width()
    c = Canvas(size, size, fringe=(30, 50, 110))
    rotation = frame / 4 * 45
    center = (size / 2, size / 2)
    c.circle(mix(SAPPHIRE, WHITE, 0.6), center, 10.5)
    c.star(SAPPHIRE, center, 10.5, rotation=rotation, outline=(24, 40, 100), width=0.8)
    c.star(SAPPHIRE_LIGHT, center, 6.4, rotation=rotation + 22.5)
    c.circle(WHITE, center, 2.4)
    surface.blit(c.finish(), (0, 0))


def paint_page(surface: pygame.Surface, _animation: str, frame: int) -> None:
    """A golden-edged manuscript page: the hidden collectibles."""
    size = surface.get_width()
    c = Canvas(size, size, fringe=OUTLINE)
    tilt = math.sin(frame / 4 * math.tau) * 1.5
    x0, y0 = 5 + tilt * 0.3, 3
    w, h = 14, 18
    sheet = [(x0, y0 + tilt * 0.2), (x0 + w, y0 - tilt * 0.2), (x0 + w, y0 + h - tilt * 0.2), (x0, y0 + h + tilt * 0.2)]
    c.polygon(GOLD, [(p[0] + (1 if i in (1, 2) else -1), p[1] + (1 if i >= 2 else -1)) for i, p in enumerate(sheet)], OUTLINE, 0.7)
    c.polygon(PARCHMENT, sheet)
    for k in range(5):
        y = y0 + 3.5 + k * 3
        c.line(INK, (x0 + 2.4 + (k % 2), y), (x0 + w - 2.4, y + 0.2), 0.7)
    c.circle((200, 40, 50), (x0 + w - 3, y0 + h - 3.2), 1.6)
    surface.blit(c.finish(), (0, 0))


def make_page_icon(size: int = 22, collected: bool = True) -> pygame.Surface:
    icon = pygame.Surface((24, 24), pygame.SRCALPHA)
    paint_page(icon, "float", 0)
    if not collected:
        dark = pygame.Surface(icon.get_size(), pygame.SRCALPHA)
        dark.fill((40, 30, 50, 255))
        icon.blit(dark, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        icon.set_alpha(150)
    return pygame.transform.smoothscale(icon, (size, size))


def paint_star_projectile(surface: pygame.Surface, _animation: str, frame: int) -> None:
    size = surface.get_width()
    c = Canvas(size, size, fringe=(30, 50, 110))
    rotation = frame / 4 * 45
    center = (size / 2, size / 2)
    c.star(SAPPHIRE_LIGHT, center, size / 2 - 0.8, rotation=rotation, outline=(40, 70, 160), width=0.6)
    c.star(WHITE, center, size / 4, rotation=rotation + 22.5)
    surface.blit(c.finish(), (0, 0))


def paint_fireball(surface: pygame.Surface, _animation: str, frame: int) -> None:
    size = surface.get_width()
    c = Canvas(size, size, fringe=(120, 30, 10))
    flick = math.sin(frame / 3 * math.tau)
    cx, cy = size / 2 + 1, size / 2
    c.polygon((210, 60, 20), [(cx - 7.5, cy + flick), (cx - 1, cy - 4.5), (cx + 4.5, cy), (cx - 1, cy + 4.5)])
    c.circle((255, 120, 30), (cx, cy), 4.6)
    c.circle(FLAME_CORE, (cx + 0.8, cy - 0.4), 2.6)
    surface.blit(c.finish(), (0, 0))


def make_heart_icon(full: bool = True, size: int = 22) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    color = HEART if full else (70, 50, 70)
    s = size / 22
    c.circle(OUTLINE, (7.5 * s, 8.5 * s), 5.6 * s)
    c.circle(OUTLINE, (14.5 * s, 8.5 * s), 5.6 * s)
    c.polygon(OUTLINE, [(2.0 * s, 10.5 * s), (20.0 * s, 10.5 * s), (11.0 * s, 20.5 * s)])
    c.circle(color, (7.5 * s, 8.5 * s), 4.6 * s)
    c.circle(color, (14.5 * s, 8.5 * s), 4.6 * s)
    c.polygon(color, [(3.2 * s, 10.0 * s), (18.8 * s, 10.0 * s), (11.0 * s, 19.0 * s)])
    if full:
        c.circle(WHITE, (6.2 * s, 7.2 * s), 1.4 * s)
    return c.finish()
