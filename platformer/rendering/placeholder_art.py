"""Procedurally drawn placeholder graphics in an Andalusian style.

Original designs inspired by the architecture and gardens of al-Andalus:
zellige mosaic stars, Mudéjar brick, horseshoe arches, orange trees,
geranium pots and crenellated walls. Everything is drawn with pygame.draw
onto transparent Surfaces. The AssetManager falls back to these when a PNG is
missing, and ``tools/build_assets.py`` exports them as PNG templates.
Nothing here calls convert(), so it works before a display exists.
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

import pygame

from core.settings import TILE_SIZE, Color

T = TILE_SIZE
Painter = Callable[[pygame.Surface, str, int], None]
TRANSPARENT = (0, 0, 0, 0)

# --- Palette ------------------------------------------------------------------
OUTLINE = (40, 26, 22)
SAND = (214, 172, 112)
SAND_DARK = (178, 136, 84)
TERRACOTTA = (186, 86, 52)
TERRACOTTA_DARK = (138, 58, 34)
GROUT = (238, 222, 190)
TAPIAL = (184, 130, 80)
TAPIAL_DARK = (148, 100, 58)
IVORY = (228, 214, 182)
IVORY_LIGHT = (248, 240, 218)
IVORY_DARK = (176, 158, 124)
BRICK_RED = (168, 72, 46)
MORTAR = (232, 204, 160)
ZELLIGE_BLUE = (28, 86, 168)
ZELLIGE_DARK = (18, 50, 108)
ZELLIGE_GREEN = (36, 138, 96)
ZELLIGE_WHITE = (242, 240, 232)
GOLD = (226, 172, 52)
GOLD_LIGHT = (255, 224, 128)
GOLD_DARK = (160, 108, 24)
CEDAR = (132, 80, 44)
CEDAR_LIGHT = (172, 114, 64)
CEDAR_DARK = (90, 52, 28)
STUCCO = (242, 234, 216)
STUCCO_DARK = (170, 158, 136)
AZULEJO = (40, 100, 180)
CLOUD = (255, 250, 242)
CLOUD_SHADE = (236, 222, 214)
LEAF = (52, 120, 60)
LEAF_LIGHT = (90, 162, 84)
ORANGE_FRUIT = (242, 142, 30)
TRUNK = (108, 70, 40)
MYRTLE = (40, 100, 56)
MYRTLE_LIGHT = (72, 138, 78)
GERANIUM = (222, 40, 62)
SILVER = (214, 224, 236)
SILVER_DARK = (140, 150, 170)
RUBY = (200, 30, 60)
WHITE = (255, 255, 255)
MARKER_POWERUP = (200, 30, 50)
MARKER_LIFE = (250, 200, 60)


def _surface(width: int, height: int) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def _bevel(surface: pygame.Surface, light: Color, dark: Color, width: int = 3) -> None:
    w, h = surface.get_size()
    surface.fill(light, (0, 0, w, width))
    surface.fill(light, (0, 0, width, h))
    surface.fill(dark, (0, h - width, w, width))
    surface.fill(dark, (w - width, 0, width, h))


def _diamond(surface: pygame.Surface, color: Color, center: tuple[int, int], radius: int, width: int = 0) -> None:
    x, y = center
    points = ((x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y))
    pygame.draw.polygon(surface, color, points, width)


def _eight_point_star(surface: pygame.Surface, color: Color, center: tuple[int, int], radius: int) -> None:
    """The classic zellige star: two overlapping squares, one turned 45°."""
    x, y = center
    half = round(radius * 0.72)
    pygame.draw.rect(surface, color, (x - half, y - half, half * 2 + 1, half * 2 + 1))
    _diamond(surface, color, center, radius)


# --- Tiles --------------------------------------------------------------------
def _speckle(s: pygame.Surface, color: Color, count: int = 7) -> None:
    for i in range(count):
        x = (i * 13 + 5) % (T - 4) + 2
        y = (i * 7 + 13) % (T - 14) + 12
        s.fill(color, (x, y, 3, 2))


def _paint_ground(s: pygame.Surface) -> None:
    """Sandy garden path edged with a row of terracotta tiles."""
    s.fill(SAND)
    _speckle(s, SAND_DARK)
    s.fill(TERRACOTTA, (0, 0, T, 9))
    s.fill(GROUT, (0, 0, T, 1))
    for x in range(0, T, 8):
        s.fill(GROUT, (x, 1, 1, 8))
    s.fill(TERRACOTTA_DARK, (0, 9, T, 2))


def _paint_dirt(s: pygame.Surface) -> None:
    """Rammed earth (tapial) with its horizontal pour lines."""
    s.fill(TAPIAL)
    for y in (7, 18, 29):
        s.fill(TAPIAL_DARK, (0, y, T, 2))
    s.fill(TAPIAL_DARK, (6, 11, 3, 3))
    s.fill(TAPIAL_DARK, (22, 22, 3, 3))


def _paint_stone(s: pygame.Surface) -> None:
    """Carved limestone block with a lozenge motif."""
    s.fill(IVORY)
    _bevel(s, IVORY_LIGHT, IVORY_DARK)
    _diamond(s, IVORY_DARK, (T // 2, T // 2), 9, 1)
    _diamond(s, IVORY_DARK, (T // 2, T // 2), 4, 1)


def _paint_brick(s: pygame.Surface) -> None:
    """Mudéjar brick: thin red bricks, thick pale mortar."""
    s.fill(BRICK_RED)
    course_height = T // 4
    for course in range(4):
        y = course * course_height
        s.fill(MORTAR, (0, y, T, 2))
        offset = 0 if course % 2 == 0 else T // 4
        for x in range(offset, T, T // 2):
            s.fill(MORTAR, (x, y, 2, course_height))


def _paint_zellige(s: pygame.Surface) -> None:
    """Mystery block: a glazed zellige tile with an eight-pointed star."""
    s.fill(ZELLIGE_WHITE)
    for corner in (((0, 0), (9, 0), (0, 9)), ((T, 0), (T - 9, 0), (T, 9)),
                   ((0, T), (9, T), (0, T - 9)), ((T, T), (T - 9, T), (T, T - 9))):
        pygame.draw.polygon(s, ZELLIGE_GREEN, corner)
    center = (T // 2, T // 2)
    _eight_point_star(s, ZELLIGE_BLUE, center, 12)
    pygame.draw.circle(s, ZELLIGE_GREEN, center, 5)
    pygame.draw.circle(s, GOLD_LIGHT, center, 2)
    pygame.draw.rect(s, ZELLIGE_DARK, (0, 0, T, T), 2)


def _paint_zellige_marked(color: Color) -> Callable[[pygame.Surface], None]:
    """Zellige block with a coloured corner dot so designers can tell block
    contents apart in Tiled. The game always draws the plain version."""

    def paint(s: pygame.Surface) -> None:
        _paint_zellige(s)
        pygame.draw.circle(s, color, (T - 7, T - 7), 4)

    return paint


def _paint_used_block(s: pygame.Surface) -> None:
    s.fill(TERRACOTTA)
    _bevel(s, (206, 110, 72), TERRACOTTA_DARK)
    _diamond(s, TERRACOTTA_DARK, (T // 2, T // 2), 6, 2)


def _paint_platform(s: pygame.Surface) -> None:
    """Carved cedar beam with brass studs."""
    s.fill(CEDAR, (0, 0, T, 12))
    s.fill(CEDAR_LIGHT, (0, 0, T, 3))
    s.fill(CEDAR_DARK, (0, 10, T, 2))
    for x in range(2, T, 8):
        pygame.draw.polygon(s, CEDAR_DARK, ((x, 12), (x + 4, 12), (x + 2, 15)))
    for x in (4, T - 7):
        s.fill(GOLD, (x, 5, 3, 3))


def _paint_well(left: bool, top: bool) -> Callable[[pygame.Surface], None]:
    """White stucco shaft with an azulejo band: the Andalusian "pipe"."""

    def paint(s: pygame.Surface) -> None:
        inset = 2 if top else 6
        x0 = inset if left else 0
        width = T - inset
        s.fill(STUCCO, (x0, 0, width, T))
        edge_x = x0 if left else x0 + width - 2
        s.fill(STUCCO_DARK, (edge_x, 0, 2, T))
        center_x = x0 + width // 2
        if top:
            s.fill(AZULEJO, (x0, 10, width, 11))
            for cx in range(x0 + 4, x0 + width, 8):
                _diamond(s, ZELLIGE_WHITE, (cx, 15), 3)
            s.fill(STUCCO_DARK, (x0, 0, width, 2))
            s.fill(STUCCO_DARK, (x0, T - 2, width, 2))
        else:
            for cy in (8, 24):
                _diamond(s, AZULEJO, (center_x, cy), 5)

    return paint


def _make_cloud() -> pygame.Surface:
    cloud = _surface(T * 2, T)
    for center, radius in (((18, 20), 10), ((32, 14), 13), ((46, 20), 10)):
        pygame.draw.circle(cloud, CLOUD, center, radius)
    cloud.fill(CLOUD, (10, 20, 44, 10))
    cloud.fill(CLOUD_SHADE, (10, 27, 44, 3))
    return cloud


def _paint_cloud_left(s: pygame.Surface) -> None:
    s.blit(_make_cloud(), (0, 0))


def _paint_cloud_right(s: pygame.Surface) -> None:
    s.blit(_make_cloud(), (-T, 0))


def _paint_orange_tree(s: pygame.Surface) -> None:
    s.fill(TRUNK, (14, 20, 4, 12))
    pygame.draw.circle(s, LEAF, (16, 13), 11)
    pygame.draw.circle(s, LEAF_LIGHT, (12, 9), 4)
    for center in ((9, 16), (21, 11), (19, 19), (13, 6), (24, 17)):
        pygame.draw.circle(s, ORANGE_FRUIT, center, 2)


def _paint_myrtle(s: pygame.Surface) -> None:
    pygame.draw.rect(s, MYRTLE, (1, 16, 30, 16), border_radius=7)
    for x in (6, 14, 22):
        pygame.draw.circle(s, MYRTLE_LIGHT, (x, 20), 2)


def _paint_geranium_pot(s: pygame.Surface) -> None:
    pygame.draw.polygon(s, TERRACOTTA, ((9, 22), (23, 22), (21, T), (11, T)))
    s.fill(TERRACOTTA_DARK, (8, 20, 16, 3))
    s.fill(AZULEJO, (10, 25, 12, 2))
    for center in ((11, 17), (21, 17), (16, 15)):
        pygame.draw.circle(s, LEAF, center, 4)
    for center in ((10, 13), (16, 10), (22, 13)):
        pygame.draw.circle(s, GERANIUM, center, 3)


def _paint_arcade(s: pygame.Surface) -> None:
    """Low balustrade with two little horseshoe arches."""
    s.fill(IVORY, (0, 11, T, 21))
    s.fill(IVORY_DARK, (0, 11, T, 2))
    for cx in (8, 24):
        pygame.draw.ellipse(s, TRANSPARENT, (cx - 5, 15, 11, 11))
        s.fill(TRANSPARENT, (cx - 4, 20, 9, 8))
    s.fill(IVORY_DARK, (0, T - 4, T, 4))


def _paint_unknown(s: pygame.Surface) -> None:
    s.fill((255, 0, 255))


TILE_PAINTERS: dict[str, Callable[[pygame.Surface], None]] = {
    "ground": _paint_ground,
    "dirt": _paint_dirt,
    "stone": _paint_stone,
    "brick": _paint_brick,
    "question": _paint_zellige,
    "question_powerup": _paint_zellige_marked(MARKER_POWERUP),
    "question_life": _paint_zellige_marked(MARKER_LIFE),
    "coin": lambda s: s.blit(make_coin_icon(), (8, 8)),
    "used_block": _paint_used_block,
    "platform": _paint_platform,
    "pipe_top_left": _paint_well(left=True, top=True),
    "pipe_top_right": _paint_well(left=False, top=True),
    "pipe_left": _paint_well(left=True, top=False),
    "pipe_right": _paint_well(left=False, top=False),
    "cloud_left": _paint_cloud_left,
    "cloud_right": _paint_cloud_right,
    "bush": _paint_orange_tree,
    "grass": _paint_myrtle,
    "flower": _paint_geranium_pot,
    "fence": _paint_arcade,
}


def make_tile(name: str) -> pygame.Surface:
    surface = _surface(T, T)
    TILE_PAINTERS.get(name, _paint_unknown)(surface)
    return surface


# --- The prince ---------------------------------------------------------------
@dataclass(frozen=True)
class PrincePalette:
    robe: Color
    robe_shade: Color
    sash: Color
    trousers: Color
    trousers_back: Color
    skin: Color
    turban: Color
    turban_shade: Color
    jewel: Color
    slipper: Color
    eye: Color


PRINCE_PALETTE = PrincePalette(
    robe=(30, 120, 100),
    robe_shade=(20, 84, 70),
    sash=(200, 40, 50),
    trousers=(236, 226, 204),
    trousers_back=(204, 192, 168),
    skin=(212, 158, 110),
    turban=(246, 242, 232),
    turban_shade=(206, 198, 184),
    jewel=(210, 36, 60),
    slipper=(176, 40, 40),
    eye=(34, 24, 22),
)

# After eating the pomegranate: golden robe, emerald jewel.
PRINCE_POWERED_PALETTE = PrincePalette(
    robe=(222, 170, 40),
    robe_shade=(170, 120, 20),
    sash=(120, 30, 110),
    trousers=(240, 232, 212),
    trousers_back=(210, 198, 174),
    skin=(212, 158, 110),
    turban=(250, 244, 222),
    turban_shade=(214, 200, 164),
    jewel=(30, 170, 110),
    slipper=(120, 30, 110),
    eye=(34, 24, 22),
)

# (back_leg_dx, front_leg_dx, back_leg_lift, front_leg_lift)
_LEG_POSES: dict[tuple[str, int], tuple[int, int, int, int]] = {
    ("run", 0): (-4, 4, 0, 0),
    ("run", 1): (-1, 1, 3, 0),
    ("run", 2): (4, -4, 0, 0),
    ("run", 3): (1, -1, 0, 3),
    ("jump", 0): (-3, 3, 4, 2),
    ("fall", 0): (-4, 4, 0, 0),
}


def prince_painter(palette: PrincePalette) -> Painter:
    def paint(surface: pygame.Surface, animation: str, frame: int) -> None:
        if animation == "death":
            _paint_prince_front(surface, frame, palette)
        else:
            _paint_prince_side(surface, animation, frame, palette)

    return paint


def _paint_leg(s: pygame.Surface, x: int, lift: int, trousers: Color, slipper: Color) -> None:
    h = s.get_height()
    s.fill(trousers, (x, h - 9 - lift, 5, 7))
    s.fill(slipper, (x, h - 2 - lift, 6, 2))
    s.fill(slipper, (x + 6, h - 3 - lift, 1, 1))  # upturned toe


def _paint_prince_side(s: pygame.Surface, animation: str, frame: int, p: PrincePalette) -> None:
    cx = s.get_width() // 2
    bob = 1 if animation == "idle" and frame == 1 else 0
    back_dx, front_dx, back_lift, front_lift = _LEG_POSES.get((animation, frame), (-2, 2, 0, 0))

    # Cape streams further back while moving.
    cape_reach = 12 if animation in ("run", "jump", "fall") else 9
    pygame.draw.polygon(
        s, p.robe_shade,
        ((cx - 5, 13 + bob), (cx - cape_reach, 26 + bob), (cx - 3, 25 + bob)),
    )
    _paint_leg(s, cx - 5 + back_dx, back_lift, p.trousers_back, p.slipper)
    _paint_leg(s, cx + front_dx, front_lift, p.trousers, p.slipper)

    s.fill(p.robe, (cx - 6, 13 + bob, 12, 12))
    s.fill(p.sash, (cx - 6, 18 + bob, 12, 2))
    s.fill(GOLD, (cx - 6, 23 + bob, 12, 1))

    if animation == "jump":
        s.fill(p.robe_shade, (cx + 3, 6 + bob, 4, 9))
        s.fill(p.skin, (cx + 3, 5 + bob, 4, 2))
    elif animation == "fall":
        s.fill(p.robe_shade, (cx - 9, 8 + bob, 3, 8))
        s.fill(p.robe_shade, (cx + 6, 8 + bob, 3, 8))
    else:
        s.fill(p.robe_shade, (cx - 1, 15 + bob, 4, 7))
        s.fill(p.skin, (cx - 1, 22 + bob, 4, 2))

    pygame.draw.circle(s, p.skin, (cx + 1, 9 + bob), 5)
    pygame.draw.ellipse(s, p.turban, (cx - 5, 0 + bob, 12, 8))
    pygame.draw.line(s, p.turban_shade, (cx - 4, 5 + bob), (cx + 6, 2 + bob))
    pygame.draw.circle(s, p.jewel, (cx + 4, 4 + bob), 1)
    s.fill(p.eye, (cx + 3, 8 + bob, 2, 2))


def _paint_prince_front(s: pygame.Surface, frame: int, p: PrincePalette) -> None:
    w, h = s.get_size()
    cx = w // 2
    arm_y = 10 + frame * 2
    s.fill(p.robe_shade, (cx - 10, arm_y, 3, 9))
    s.fill(p.robe_shade, (cx + 7, arm_y, 3, 9))
    _paint_leg(s, cx - 5, 0, p.trousers, p.slipper)
    _paint_leg(s, cx + 1, 0, p.trousers, p.slipper)
    s.fill(p.robe, (cx - 6, 16, 12, 9))
    s.fill(p.sash, (cx - 6, 20, 12, 2))
    pygame.draw.circle(s, p.skin, (cx, 11), 6)
    pygame.draw.ellipse(s, p.turban, (cx - 7, 1, 14, 8))
    pygame.draw.circle(s, p.jewel, (cx, 4), 1)
    for eye_x in (cx - 4, cx + 2):
        pygame.draw.line(s, p.eye, (eye_x, 10), (eye_x + 2, 13))
        pygame.draw.line(s, p.eye, (eye_x + 2, 10), (eye_x, 13))


# --- Enemies ------------------------------------------------------------------
SCORPION = (176, 108, 48)
SCORPION_DARK = (110, 62, 26)
JINN = (150, 90, 220)
JINN_LIGHT = (214, 180, 255)
JINN_DARK = (96, 50, 160)


def paint_scorpion(s: pygame.Surface, animation: str, frame: int) -> None:
    """Desert scorpion (walker). Faces right."""
    if animation == "squashed":
        pygame.draw.ellipse(s, SCORPION, (2, 26, 28, 6))
        pygame.draw.line(s, SCORPION_DARK, (6, 28), (26, 28))
        return
    for index, x in enumerate((9, 14, 19)):
        offset = 1 if (index + frame) % 2 == 0 else -1
        pygame.draw.line(s, SCORPION_DARK, (x, 24), (x - 2 + offset, 31), 2)
    pygame.draw.ellipse(s, SCORPION, (6, 17, 20, 10))
    for x in (12, 17):
        pygame.draw.line(s, SCORPION_DARK, (x, 18), (x, 26))
    sway = frame
    for center in ((7, 19), (4 + sway, 14), (5 + sway, 9), (9 + sway, 6)):
        pygame.draw.circle(s, SCORPION, center, 3)
    pygame.draw.polygon(s, SCORPION_DARK, ((11 + sway, 4), (15 + sway, 7), (11 + sway, 9)))
    pygame.draw.circle(s, SCORPION, (25, 21), 4)
    for claw_y in (16, 26):
        pygame.draw.circle(s, SCORPION_DARK, (29, claw_y), 3)
        s.fill(TRANSPARENT, (30, claw_y - 1, 2, 2))
    s.fill(OUTLINE, (26, 19, 2, 2))


def paint_clay_jar(s: pygame.Surface, animation: str, frame: int) -> None:
    """A haunted terracotta jar that hops (hopper). Faces right."""
    if animation == "squashed":
        for shard in ((4, 28, 8, 4), (14, 27, 6, 5), (22, 28, 7, 4)):
            s.fill(TERRACOTTA, shard)
        s.fill(AZULEJO, (15, 29, 4, 1))
        return
    if animation == "jump":
        body = pygame.Rect(8, 8, 16, 24)
    else:
        body = pygame.Rect(6, 12, 20, 20) if frame == 0 else pygame.Rect(5, 14, 22, 18)
    s.fill(TERRACOTTA_DARK, (body.centerx - 5, body.y - 4, 10, 5))
    s.fill(TERRACOTTA, (body.centerx - 7, body.y - 6, 14, 3))
    pygame.draw.ellipse(s, TERRACOTTA, body)
    s.fill(AZULEJO, (body.x + 3, body.centery + 3, body.width - 6, 3))
    eye_y = body.centery - 3
    for eye_x in (body.centerx + 1, body.centerx + 6):
        s.fill(OUTLINE, (eye_x, eye_y, 2, 3))
    pygame.draw.line(s, OUTLINE, (body.centerx, eye_y - 3), (body.centerx + 3, eye_y - 1))
    pygame.draw.line(s, OUTLINE, (body.centerx + 8, eye_y - 3), (body.centerx + 5, eye_y - 1))


def paint_jinn(s: pygame.Surface, animation: str, frame: int) -> None:
    """A mischievous jinn wisp (flyer). Faces right."""
    flicker = frame * 2
    pygame.draw.polygon(s, JINN_DARK, ((9, 19), (14, 31 - flicker), (23, 19)))
    pygame.draw.polygon(s, JINN, ((10, 11), (16, 1 + flicker), (22, 11)))
    pygame.draw.circle(s, JINN, (16, 15), 8)
    pygame.draw.circle(s, JINN_LIGHT, (14, 13), 4)
    for eye_x in (15, 21):
        pygame.draw.circle(s, WHITE, (eye_x, 15), 2)
        s.fill(OUTLINE, (eye_x + 1, 15, 1, 1))


# --- Items --------------------------------------------------------------------
COIN_WIDTHS = (12, 8, 3, 8)
POMEGRANATE = (190, 30, 50)
POMEGRANATE_LIGHT = (250, 120, 130)
POMEGRANATE_DARK = (120, 16, 30)
FLAME = (255, 160, 40)
FLAME_CORE = (255, 236, 150)


def paint_dinar(s: pygame.Surface, _animation: str, frame: int) -> None:
    """Spinning gold dinar."""
    w, h = s.get_size()
    coin_width = COIN_WIDTHS[frame % len(COIN_WIDTHS)]
    rect = pygame.Rect(0, 1, coin_width, h - 2)
    rect.centerx = w // 2
    pygame.draw.ellipse(s, GOLD_DARK, rect)
    pygame.draw.ellipse(s, GOLD, rect.inflate(-2, -2))
    if coin_width > 6:
        pygame.draw.ellipse(s, GOLD_DARK, rect.inflate(-6, -6), 1)
        s.fill(GOLD_LIGHT, (rect.centerx - 1, rect.y + 5, 2, h - 12))


def make_coin_icon() -> pygame.Surface:
    icon = _surface(16, 16)
    paint_dinar(icon, "spin", 0)
    return icon


def paint_pomegranate(s: pygame.Surface, _animation: str, frame: int) -> None:
    """Power-up. Granada's own fruit."""
    w, h = s.get_size()
    cx, cy = w // 2, h // 2 + 2
    radius = 9 - frame
    pygame.draw.circle(s, POMEGRANATE, (cx, cy), radius)
    pygame.draw.circle(s, POMEGRANATE_LIGHT, (cx - 3, cy - 3), 2)
    top = cy - radius
    crown = ((cx - 3, top + 1), (cx - 4, top - 3), (cx - 1, top - 1), (cx, top - 4),
             (cx + 1, top - 1), (cx + 4, top - 3), (cx + 3, top + 1))
    pygame.draw.polygon(s, POMEGRANATE_DARK, crown)


def paint_oil_lamp(s: pygame.Surface, _animation: str, frame: int) -> None:
    """Extra life: a magic oil lamp."""
    flame_height = 7 + frame * 2
    pygame.draw.circle(s, GOLD_DARK, (4, 14), 3, 1)
    pygame.draw.ellipse(s, GOLD, (3, 12, 16, 8))
    pygame.draw.polygon(s, GOLD, ((16, 14), (23, 11), (17, 18)))
    s.fill(GOLD_LIGHT, (8, 9, 6, 3))
    s.fill(GOLD_DARK, (8, 19, 6, 3))
    pygame.draw.polygon(s, FLAME, ((20, 11), (22, 11 - flame_height), (24, 11)))
    pygame.draw.polygon(s, FLAME_CORE, ((21, 11), (22, 13 - flame_height), (23, 11)))


def _paint_heart(s: pygame.Surface) -> None:
    color = (230, 60, 90)
    pygame.draw.circle(s, color, (8, 10), 5)
    pygame.draw.circle(s, color, (16, 10), 5)
    pygame.draw.polygon(s, color, ((3, 12), (21, 12), (12, 21)))
    pygame.draw.circle(s, WHITE, (7, 9), 1)


def make_heart_icon() -> pygame.Surface:
    icon = _surface(24, 24)
    _paint_heart(icon)
    return icon


# --- Level objects ------------------------------------------------------------
GLASS_DARK = (70, 70, 84)
GLASS_LIT = (255, 214, 96)
LANTERN_GLOW = (255, 200, 80, 70)
ARCH_INTERIOR = (44, 26, 30)
SWORD_GLOW_OUTER = (255, 200, 70, 80)
SWORD_GLOW_INNER = (255, 236, 150, 130)


def make_checkpoint(active: bool) -> pygame.Surface:
    """A post with a hanging lantern that lights up when reached."""
    s = _surface(T, T * 2)
    if active:
        pygame.draw.circle(s, LANTERN_GLOW, (24, 25), 10)
    s.fill(CEDAR, (8, 10, 4, T * 2 - 10))
    s.fill(CEDAR, (8, 10, 18, 3))
    s.fill(IVORY_DARK, (3, T * 2 - 6, 14, 6))
    pygame.draw.line(s, GOLD_DARK, (24, 13), (24, 17))
    pygame.draw.polygon(s, GOLD, ((18, 19), (24, 14), (30, 19)))
    s.fill(GOLD, (19, 19, 10, 13))
    s.fill(GLASS_LIT if active else GLASS_DARK, (21, 21, 6, 9))
    pygame.draw.polygon(s, GOLD, ((19, 32), (29, 32), (24, 36)))
    return s


def make_arch_gate() -> pygame.Surface:
    """Level exit: a horseshoe arch with alternating red and white voussoirs,
    framed by an alfiz, like the arches of Córdoba."""
    width, height = 96, 128
    s = _surface(width, height)
    center = (48, 44)

    arch = _surface(width, 92)
    wedge_count = 24
    for index in range(wedge_count):
        a0 = math.tau * index / wedge_count
        a1 = math.tau * (index + 1) / wedge_count
        far = 80
        points = (
            center,
            (center[0] + far * math.cos(a0), center[1] + far * math.sin(a0)),
            (center[0] + far * math.cos(a1), center[1] + far * math.sin(a1)),
        )
        pygame.draw.polygon(arch, BRICK_RED if index % 2 else IVORY_LIGHT, points)
    mask = _surface(width, 92)
    pygame.draw.ellipse(mask, WHITE, (6, 2, 84, 84))
    arch.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(arch, (0, 0))

    pygame.draw.ellipse(s, ARCH_INTERIOR, (20, 16, 56, 56))
    s.fill(ARCH_INTERIOR, (24, 50, 48, height - 50))
    for x in (4, 76):
        s.fill(IVORY, (x, 64, 16, height - 64))
        s.fill(IVORY_DARK, (x - 2, 60, 20, 5))
    pygame.draw.rect(s, IVORY_DARK, (0, 0, width, 64), 3)
    return s


def make_sword_shrine() -> pygame.Surface:
    """The final goal: the Sword of Light resting in a stone pedestal."""
    width, height = 64, 128
    s = _surface(width, height)
    pygame.draw.circle(s, SWORD_GLOW_OUTER, (32, 56), 30)
    pygame.draw.circle(s, SWORD_GLOW_INNER, (32, 56), 18)
    s.fill(IVORY, (12, 100, 40, 28))
    s.fill(IVORY_DARK, (8, 96, 48, 6))
    s.fill(ZELLIGE_WHITE, (20, 107, 24, 16))
    _eight_point_star(s, ZELLIGE_BLUE, (32, 115), 6)
    s.fill(SILVER, (29, 40, 6, 58))
    s.fill(SILVER_DARK, (32, 40, 1, 58))
    s.fill(GOLD, (20, 36, 24, 4))
    s.fill((96, 44, 32), (30, 22, 4, 14))
    pygame.draw.circle(s, GOLD, (32, 20), 3)
    pygame.draw.circle(s, RUBY, (32, 38), 2)
    return s


def make_debris(size: int) -> pygame.Surface:
    s = _surface(size, size)
    s.fill(BRICK_RED)
    s.fill(MORTAR, (0, size // 2, size, 2))
    return s


# --- Background ---------------------------------------------------------------
def make_skyline(width: int, height: int, color: Color) -> pygame.Surface:
    """A horizontally tileable silhouette of an Andalusian city: crenellated
    walls and towers, domed pavilions, cypresses and palms."""
    s = _surface(width, height)
    scale = width / 960

    def x_at(value: float) -> int:
        return round(value * scale)

    def tower(x: float, tower_width: int, tower_height: int) -> None:
        left = x_at(x)
        s.fill(color, (left, height - tower_height, tower_width, tower_height))
        for mx in range(left, left + tower_width, 8):
            s.fill(color, (mx, height - tower_height - 6, 5, 6))

    def pavilion(x: float) -> None:
        left = x_at(x)
        s.fill(color, (left, height - 56, 64, 56))
        pygame.draw.ellipse(s, color, (left + 12, height - 86, 40, 60))
        s.fill(color, (left + 31, height - 96, 2, 12))

    def cypress(x: float, cypress_height: int) -> None:
        pygame.draw.ellipse(s, color, (x_at(x), height - cypress_height, 14, cypress_height))

    def palm(x: float) -> None:
        base = (x_at(x), height)
        top = (base[0] + 8, height - 90)
        pygame.draw.line(s, color, base, top, 4)
        for dx, dy in ((-26, 14), (-16, 22), (26, 14), (16, 22), (0, -10)):
            pygame.draw.line(s, color, top, (top[0] + dx, top[1] + dy), 4)

    # Every shape sits well inside [0, width), and the wall spans the full
    # width, so the strip tiles seamlessly.
    s.fill(color, (0, height - 26, width, 26))
    for mx in range(0, width, 14):
        s.fill(color, (mx, height - 32, 8, 6))
    tower(60, 40, 120)
    cypress(140, 90)
    cypress(158, 70)
    pavilion(220)
    palm(330)
    tower(420, 52, 150)
    cypress(500, 96)
    pavilion(560)
    palm(690)
    tower(770, 36, 110)
    cypress(850, 84)
    cypress(868, 64)
    return s


def add_stars(sky: pygame.Surface, count: int, seed: int = 7) -> None:
    rng = random.Random(seed)
    width, height = sky.get_size()
    for _ in range(count):
        x = rng.randrange(width)
        y = rng.randrange(height * 2 // 3)
        brightness = rng.randrange(170, 256)
        sky.fill((brightness, brightness, brightness * 9 // 10), (x, y, 2 if rng.random() < 0.2 else 1, 1))
