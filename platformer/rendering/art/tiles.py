"""Tile art for every theme, plus the auto-tiling decorations.

Tiles are painted crisp (no supersampling) so neighbouring tiles line up
pixel-perfectly. Each *terrain* tile also has a style that the terrain
renderer uses when baking a level: exposed tops get a cap (grass tufts,
snow drifts, crenellations, cornices...), exposed bottoms may get icicles or
shadows, exposed sides get a darker rim, and buried tiles darken with depth.
That turns grids of identical squares into shapes that look hand-drawn.
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

import pygame

from core.settings import TILE_SIZE, Color
from rendering.art.kit import hash01, mix, shade

T = TILE_SIZE
TRANSPARENT = (0, 0, 0, 0)

# --- Palette ------------------------------------------------------------------
OUTLINE = (40, 26, 22)
SAND = (214, 176, 118)
SAND_DARK = (182, 140, 88)
TERRACOTTA = (186, 86, 52)
TERRACOTTA_LIGHT = (214, 118, 76)
TERRACOTTA_DARK = (138, 58, 34)
GROUT = (238, 222, 190)
TAPIAL = (178, 124, 76)
TAPIAL_DARK = (146, 98, 56)
IVORY = (228, 214, 182)
IVORY_LIGHT = (248, 240, 218)
IVORY_DARK = (176, 158, 124)
BRICK_RED = (168, 72, 46)
MORTAR = (232, 204, 160)
ZELLIGE_BLUE = (28, 86, 168)
ZELLIGE_DARK = (18, 50, 108)
ZELLIGE_GREEN = (36, 138, 96)
ZELLIGE_WHITE = (242, 240, 232)
ZELLIGE_YELLOW = (232, 186, 60)
ZELLIGE_BLACK = (34, 30, 40)
GOLD = (226, 172, 52)
GOLD_LIGHT = (255, 224, 128)
GOLD_DARK = (160, 108, 24)
CEDAR = (132, 80, 44)
CEDAR_LIGHT = (172, 114, 64)
CEDAR_DARK = (90, 52, 28)
STUCCO = (242, 234, 216)
STUCCO_DARK = (184, 170, 146)
AZULEJO = (40, 100, 180)
LEAF = (52, 120, 60)
LEAF_LIGHT = (96, 168, 84)
LEAF_DARK = (32, 84, 44)
MARBLE = (238, 234, 226)
MARBLE_VEIN = (200, 196, 190)
MARBLE_SHADE = (206, 200, 190)
ROSE = (196, 110, 110)
ROOF = (184, 82, 50)
ROOF_LIGHT = (214, 116, 72)
ROOF_DARK = (124, 50, 30)
PLASTER = (244, 238, 226)
PLASTER_SHADE = (214, 204, 186)
WOOD = (112, 72, 44)
WOOD_LIGHT = (146, 98, 60)
WOOD_DARK = (72, 44, 28)
ROCK = (132, 128, 136)
ROCK_LIGHT = (164, 160, 168)
ROCK_DARK = (92, 88, 100)
SNOW = (246, 250, 255)
SNOW_SHADE = (196, 214, 236)
ICE = (190, 226, 246)
ICE_LIGHT = (236, 250, 255)
ICE_DARK = (128, 180, 220)
RED_WALL = (178, 84, 58)
RED_WALL_LIGHT = (204, 112, 80)
RED_WALL_DARK = (132, 56, 40)
AWNING_A = (196, 40, 48)
AWNING_B = (246, 238, 222)
SPIKE = (190, 196, 210)
SPIKE_DARK = (96, 100, 118)
SUN = (246, 190, 60)
SUN_DARK = (180, 118, 30)
MOON = (120, 150, 230)
MOON_DARK = (60, 80, 160)
WHITE = (255, 255, 255)
MARKER_POWERUP = (200, 30, 50)
MARKER_LIFE = (250, 200, 60)
MARKER_STAR = (80, 150, 255)


def _surface(width: int = T, height: int = T) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def _bevel(s: pygame.Surface, light: Color, dark: Color, width: int = 2) -> None:
    w, h = s.get_size()
    s.fill(light, (0, 0, w, width))
    s.fill(light, (0, 0, width, h))
    s.fill(dark, (0, h - width, w, width))
    s.fill(dark, (w - width, 0, width, h))


def _diamond(s: pygame.Surface, color: Color, center: tuple[int, int], radius: int, width: int = 0) -> None:
    x, y = center
    pygame.draw.polygon(s, color, ((x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)), width)


def eight_point_star(s: pygame.Surface, color: Color, center: tuple[float, float], radius: float) -> None:
    """The classic zellige star: two overlapping squares, one turned 45 deg."""
    x, y = center
    half = radius * 0.72
    pygame.draw.polygon(s, color, ((x - half, y - half), (x + half, y - half), (x + half, y + half), (x - half, y + half)))
    _diamond(s, color, (round(x), round(y)), round(radius))


def _speckle(s: pygame.Surface, color: Color, seed: int, count: int = 7, top: int = 10) -> None:
    rng = random.Random(seed)
    for _ in range(count):
        s.fill(color, (rng.randrange(1, T - 3), rng.randrange(top, T - 2), rng.choice((2, 3)), 2))


# --- Terrain tiles ---------------------------------------------------------------
def _paint_ground(s: pygame.Surface) -> None:
    """Sandy garden path edged with a row of terracotta tiles."""
    s.fill(SAND)
    _speckle(s, SAND_DARK, 3)
    s.fill(TERRACOTTA, (0, 0, T, 9))
    s.fill(TERRACOTTA_LIGHT, (0, 0, T, 2))
    for x in range(0, T, 8):
        s.fill(GROUT, (x, 1, 1, 8))
    s.fill(TERRACOTTA_DARK, (0, 9, T, 2))


def _paint_dirt(s: pygame.Surface) -> None:
    """Rammed earth (tapial) with its horizontal pour lines."""
    s.fill(TAPIAL)
    for y in (7, 18, 29):
        s.fill(TAPIAL_DARK, (0, y, T, 2))
    _speckle(s, TAPIAL_DARK, 5, 4, 2)


def _paint_stone(s: pygame.Surface) -> None:
    """Carved limestone block with a lozenge motif."""
    s.fill(IVORY)
    _bevel(s, IVORY_LIGHT, IVORY_DARK, 3)
    _diamond(s, IVORY_DARK, (T // 2, T // 2), 9, 1)
    _diamond(s, IVORY_DARK, (T // 2, T // 2), 4, 1)


def _paint_marble(s: pygame.Surface) -> None:
    """Madinat al-Zahra marble with a rose inlay and gold fillets."""
    s.fill(MARBLE)
    pygame.draw.line(s, MARBLE_VEIN, (3, 20), (14, 12), 1)
    pygame.draw.line(s, MARBLE_VEIN, (14, 12), (22, 16), 1)
    pygame.draw.line(s, MARBLE_VEIN, (18, 28), (29, 22), 1)
    _diamond(s, ROSE, (T // 2, T // 2 + 2), 6)
    _diamond(s, MARBLE, (T // 2, T // 2 + 2), 3)
    s.fill(GOLD, (0, 0, T, 2))
    s.fill(MARBLE_SHADE, (0, T - 2, T, 2))
    s.fill(MARBLE_SHADE, (T - 1, 0, 1, T))


def _paint_ashlar(s: pygame.Surface) -> None:
    """Warm dressed stone in offset courses (fill below marble floors)."""
    s.fill((214, 190, 150))
    for row, y in enumerate((0, 16)):
        s.fill((178, 150, 110), (0, y, T, 1))
        for x in ((0, 16) if row == 0 else (8, 24)):
            s.fill((178, 150, 110), (x, y, 1, 16))
    _speckle(s, (196, 170, 130), 11, 5, 2)


def _paint_roof(s: pygame.Surface) -> None:
    """Terracotta roof: two rows of curved barrel tiles."""
    s.fill(ROOF_DARK)
    for row in range(2):
        y = row * 16
        for col in range(-1, 5):
            x = col * 8 + (4 if row % 2 else 0)
            pygame.draw.ellipse(s, ROOF, (x, y - 2, 8, 18))
            pygame.draw.line(s, ROOF_LIGHT, (x + 2, y + 1), (x + 2, y + 12))
            pygame.draw.arc(s, ROOF_DARK, (x, y + 8, 8, 8), math.pi, 2 * math.pi, 1)


def _paint_plaster(s: pygame.Surface) -> None:
    """Whitewashed wall of the Sevillian houses."""
    s.fill(PLASTER)
    _speckle(s, PLASTER_SHADE, 17, 5, 1)
    pygame.draw.line(s, PLASTER_SHADE, (20, 6), (24, 11))
    pygame.draw.line(s, PLASTER_SHADE, (24, 11), (23, 15))


def _paint_wood(s: pygame.Surface) -> None:
    """Dark timber of the clock tower: planks with iron studs."""
    s.fill(WOOD)
    for y in (0, 11, 22):
        s.fill(WOOD_LIGHT, (0, y, T, 2))
        s.fill(WOOD_DARK, (0, y + 9, T, 2))
    for x, y in ((4, 5), (27, 5), (4, 16), (27, 16), (4, 27), (27, 27)):
        s.fill((60, 60, 70), (x, y, 2, 2))
    pygame.draw.line(s, WOOD_DARK, (13, 3), (19, 3))


def _paint_mudejar(s: pygame.Surface) -> None:
    """Toledo's Mudejar brickwork: thin bricks, thick mortar, a green glaze accent."""
    s.fill((170, 88, 58))
    for course in range(4):
        y = course * 8
        s.fill((228, 202, 164), (0, y, T, 2))
        offset = 0 if course % 2 == 0 else 8
        for x in range(offset, T + 8, 16):
            s.fill((228, 202, 164), (x % T, y, 2, 8))
    s.fill(ZELLIGE_GREEN, (10, 11, 6, 3))


def _paint_rock(s: pygame.Surface) -> None:
    """Sierra Nevada granite with facets and cracks."""
    s.fill(ROCK)
    pygame.draw.polygon(s, ROCK_LIGHT, ((0, 0), (18, 0), (10, 10), (0, 12)))
    pygame.draw.polygon(s, ROCK_DARK, ((32, 18), (32, 32), (14, 32), (22, 22)))
    pygame.draw.line(s, ROCK_DARK, (10, 10), (22, 22))
    pygame.draw.line(s, ROCK_DARK, (22, 22), (20, 30))
    _speckle(s, ROCK_LIGHT, 23, 4, 2)


def _paint_ice(s: pygame.Surface) -> None:
    s.fill(ICE)
    pygame.draw.line(s, ICE_LIGHT, (3, 26), (26, 3), 2)
    pygame.draw.line(s, ICE_LIGHT, (12, 29), (29, 12), 1)
    s.fill(ICE_DARK, (0, T - 2, T, 2))
    s.fill(ICE_DARK, (T - 2, 0, 2, T))


def _paint_red_wall(s: pygame.Surface) -> None:
    """The Alhambra's red rammed earth, with pour lines and putlog holes."""
    s.fill(RED_WALL)
    for y in (0, 16):
        s.fill(RED_WALL_DARK, (0, y, T, 1))
        s.fill(RED_WALL_LIGHT, (0, y + 1, T, 1))
    s.fill(RED_WALL_DARK, (6, 7, 3, 3))
    s.fill(RED_WALL_DARK, (22, 23, 3, 3))
    _speckle(s, RED_WALL_DARK, 29, 4, 2)


def _paint_palace(s: pygame.Surface) -> None:
    """A zellige wainscot panel: interlaced stars in the Nasrid palette."""
    s.fill(ZELLIGE_WHITE)
    colors = (ZELLIGE_BLUE, ZELLIGE_GREEN, ZELLIGE_BLACK, ZELLIGE_YELLOW)
    for index, (cx, cy) in enumerate(((0, 0), (32, 0), (0, 32), (32, 32), (16, 16))):
        eight_point_star(s, colors[index % 4], (cx, cy), 9)
    for cx, cy in ((16, 0), (0, 16), (32, 16), (16, 32)):
        _diamond(s, ZELLIGE_DARK, (cx, cy), 3)
    eight_point_star(s, ZELLIGE_WHITE, (16, 16), 4)
    pygame.draw.rect(s, ZELLIGE_DARK, (0, 0, T, T), 1)


def _paint_court(s: pygame.Surface) -> None:
    """Pale marble paving of the Court of the Lions."""
    s.fill((232, 230, 226))
    s.fill((212, 208, 204), (0, 15, T, 2))
    s.fill((212, 208, 204), (15, 0, 2, 15))
    s.fill((212, 208, 204), (7, 17, 2, 15))
    s.fill((248, 248, 246), (0, 0, T, 2))
    _speckle(s, (216, 214, 210), 31, 5, 2)


# --- One-way platforms -------------------------------------------------------------
def _paint_platform(s: pygame.Surface) -> None:
    """Carved cedar beam with brass studs."""
    s.fill(CEDAR, (0, 0, T, 12))
    s.fill(CEDAR_LIGHT, (0, 0, T, 3))
    s.fill(CEDAR_DARK, (0, 10, T, 2))
    for x in range(2, T, 8):
        pygame.draw.polygon(s, CEDAR_DARK, ((x, 12), (x + 4, 12), (x + 2, 15)))
    for x in (4, T - 7):
        s.fill(GOLD, (x, 5, 3, 3))


def _paint_awning(s: pygame.Surface) -> None:
    """Striped market awning with a scalloped edge."""
    for x in range(0, T, 8):
        s.fill(AWNING_A if (x // 8) % 2 == 0 else AWNING_B, (x, 0, 8, 10))
    s.fill(shade(AWNING_A, -0.3), (0, 0, T, 2))
    for x in range(0, T, 8):
        color = AWNING_A if (x // 8) % 2 == 0 else AWNING_B
        pygame.draw.ellipse(s, color, (x, 6, 8, 8))


def _paint_shelf(s: pygame.Surface) -> None:
    """A library shelf plank on a carved bracket."""
    s.fill(WOOD_LIGHT, (0, 0, T, 8))
    s.fill(WOOD_DARK, (0, 6, T, 2))
    s.fill((180, 130, 80), (0, 0, T, 2))
    pygame.draw.polygon(s, WOOD_DARK, ((12, 8), (20, 8), (16, 16)))


def _paint_ledge(s: pygame.Surface) -> None:
    """A marble ledge with a moulded underside."""
    s.fill(MARBLE, (0, 0, T, 7))
    s.fill(GOLD, (0, 0, T, 2))
    s.fill(MARBLE_SHADE, (0, 7, T, 3))
    for x in range(1, T, 6):
        s.fill(MARBLE_SHADE, (x, 10, 3, 3))


def _paint_bridge(s: pygame.Surface) -> None:
    """Mountain footbridge: planks lashed with rope."""
    for x in range(0, T, 8):
        s.fill(WOOD_LIGHT, (x + 1, 2, 6, 7))
        s.fill(WOOD_DARK, (x + 1, 8, 6, 2))
    pygame.draw.line(s, (200, 180, 130), (0, 3), (T, 3), 1)


# --- Special / spawn tiles ------------------------------------------------------------
def _paint_brick(s: pygame.Surface) -> None:
    """Mudejar brick: thin red bricks, thick pale mortar."""
    s.fill(BRICK_RED)
    course_height = T // 4
    for course in range(4):
        y = course * course_height
        s.fill(MORTAR, (0, y, T, 2))
        offset = 0 if course % 2 == 0 else T // 4
        for x in range(offset, T, T // 2):
            s.fill(MORTAR, (x, y, 2, course_height))
    s.fill(shade(BRICK_RED, 0.2), (2, 2, T - 4, 1))


def _paint_zellige(s: pygame.Surface) -> None:
    """Mystery block: a glazed zellige tile with an eight-pointed star."""
    s.fill(ZELLIGE_WHITE)
    for corner in (((0, 0), (9, 0), (0, 9)), ((T, 0), (T - 9, 0), (T, 9)),
                   ((0, T), (9, T), (0, T - 9)), ((T, T), (T - 9, T), (T, T - 9))):
        pygame.draw.polygon(s, ZELLIGE_GREEN, corner)
    center = (T // 2, T // 2)
    eight_point_star(s, ZELLIGE_BLUE, center, 12)
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


def _paint_crumble(s: pygame.Surface) -> None:
    """Sandstone slab riddled with cracks: it gives way when stood on."""
    s.fill((210, 170, 110))
    _bevel(s, (236, 204, 150), (160, 118, 70), 2)
    for a, b in (((6, 4), (12, 14)), ((12, 14), (9, 24)), ((12, 14), (22, 12)), ((22, 12), (27, 22)), ((18, 26), (26, 30))):
        pygame.draw.line(s, (130, 92, 52), a, b, 1)


def _paint_switch(color: Color, dark: Color, sun: bool) -> Callable[[pygame.Surface], None]:
    def paint(s: pygame.Surface) -> None:
        s.fill(color)
        _bevel(s, shade(color, 0.35), dark, 3)
        center = (T // 2, T // 2)
        if sun:
            for k in range(8):
                a = k * math.pi / 4
                pygame.draw.line(s, dark, (16 + math.cos(a) * 6, 16 + math.sin(a) * 6),
                                 (16 + math.cos(a) * 11, 16 + math.sin(a) * 11), 2)
            pygame.draw.circle(s, shade(color, 0.5), center, 6)
            pygame.draw.circle(s, dark, center, 6, 1)
        else:
            pygame.draw.circle(s, shade(color, 0.6), center, 9)
            pygame.draw.circle(s, color, (20, 13), 8)
            for x, y in ((8, 8), (24, 24), (26, 8)):
                s.fill(WHITE, (x, y, 2, 2))
    return paint


def switch_outline(sun: bool) -> pygame.Surface:
    """Ghost outline of a switch block while it is inactive."""
    s = _surface()
    color = SUN_DARK if sun else MOON_DARK
    for x in range(0, T, 6):
        s.fill(color, (x, 0, 3, 2))
        s.fill(color, (x, T - 2, 3, 2))
    for y in range(0, T, 6):
        s.fill(color, (0, y, 2, 3))
        s.fill(color, (T - 2, y, 2, 3))
    return s


def _paint_spikes(s: pygame.Surface) -> None:
    """Iron spikes on a stone sill."""
    s.fill(SPIKE_DARK, (0, T - 6, T, 6))
    s.fill(shade(SPIKE_DARK, 0.25), (0, T - 6, T, 1))
    for x in range(0, T, 8):
        pygame.draw.polygon(s, SPIKE, ((x + 1, T - 6), (x + 4, T - 20), (x + 7, T - 6)))
        pygame.draw.line(s, WHITE, (x + 4, T - 19), (x + 4, T - 9))
        pygame.draw.polygon(s, SPIKE_DARK, ((x + 1, T - 6), (x + 4, T - 20), (x + 7, T - 6)), 1)


def _paint_coin_tile(s: pygame.Surface) -> None:
    from rendering.art.items import make_coin_icon

    s.blit(make_coin_icon(16), (8, 8))


# --- Wells (pipes) -----------------------------------------------------------------------
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


# --- Small decorations -------------------------------------------------------------------
def _make_cloud() -> pygame.Surface:
    cloud = _surface(T * 2, T)
    for center, radius in (((18, 20), 10), ((32, 14), 13), ((46, 20), 10)):
        pygame.draw.circle(cloud, (255, 250, 242), center, radius)
    cloud.fill((255, 250, 242), (10, 20, 44, 10))
    cloud.fill((236, 222, 214), (10, 27, 44, 3))
    return cloud


def _paint_orange_tree(s: pygame.Surface) -> None:
    s.fill((108, 70, 40), (14, 20, 4, 12))
    pygame.draw.circle(s, LEAF, (16, 13), 11)
    pygame.draw.circle(s, LEAF_LIGHT, (12, 9), 4)
    for center in ((9, 16), (21, 11), (19, 19), (13, 6), (24, 17)):
        pygame.draw.circle(s, (242, 142, 30), center, 2)


def _paint_myrtle(s: pygame.Surface) -> None:
    pygame.draw.rect(s, (40, 100, 56), (1, 16, 30, 16), border_radius=7)
    for x in (6, 14, 22):
        pygame.draw.circle(s, (72, 138, 78), (x, 20), 2)


def _paint_geranium_pot(s: pygame.Surface) -> None:
    pygame.draw.polygon(s, TERRACOTTA, ((9, 22), (23, 22), (21, T), (11, T)))
    s.fill(TERRACOTTA_DARK, (8, 20, 16, 3))
    s.fill(AZULEJO, (10, 25, 12, 2))
    for center in ((11, 17), (21, 17), (16, 15)):
        pygame.draw.circle(s, LEAF, center, 4)
    for center in ((10, 13), (16, 10), (22, 13)):
        pygame.draw.circle(s, (222, 40, 62), center, 3)


def _paint_arcade(s: pygame.Surface) -> None:
    """Low balustrade with two little horseshoe arches."""
    s.fill(IVORY, (0, 11, T, 21))
    s.fill(IVORY_DARK, (0, 11, T, 2))
    for cx in (8, 24):
        pygame.draw.ellipse(s, TRANSPARENT, (cx - 5, 15, 11, 11))
        s.fill(TRANSPARENT, (cx - 4, 20, 9, 8))
    s.fill(IVORY_DARK, (0, T - 4, T, 4))


def _paint_grass_tuft(s: pygame.Surface) -> None:
    for x, h in ((5, 8), (9, 12), (13, 7), (19, 10), (24, 13), (28, 6)):
        pygame.draw.line(s, LEAF_DARK, (x, T), (x - 1, T - h), 2)
        pygame.draw.line(s, LEAF_LIGHT, (x + 1, T), (x + 1, T - h + 3), 1)


def _paint_rock_small(s: pygame.Surface) -> None:
    pygame.draw.ellipse(s, ROCK_DARK, (4, 18, 24, 14))
    pygame.draw.ellipse(s, ROCK, (5, 18, 20, 11))
    pygame.draw.ellipse(s, SNOW, (7, 17, 14, 5))


def _paint_books(s: pygame.Surface) -> None:
    colors = ((150, 40, 40), (40, 90, 140), (50, 120, 70), (180, 140, 60), (90, 50, 110))
    x = 3
    for index, color in enumerate(colors):
        h = 14 + (index * 5) % 9
        s.fill(color, (x, T - h, 5, h))
        s.fill(GOLD, (x + 1, T - h + 3, 3, 1))
        x += 5
    pygame.draw.polygon(s, (170, 120, 60), ((x, T), (x + 4, T - 16), (x + 8, T - 15), (x + 4, T)))


def _paint_vase(s: pygame.Surface) -> None:
    pygame.draw.ellipse(s, AZULEJO, (8, 12, 16, 18))
    s.fill(AZULEJO, (12, 6, 8, 8))
    s.fill(ZELLIGE_WHITE, (8, 19, 16, 3))
    s.fill(ZELLIGE_DARK, (11, 5, 10, 2))
    pygame.draw.ellipse(s, (120, 170, 230), (11, 14, 4, 6))


def _paint_cracked(s: pygame.Surface) -> None:
    """Sandstone with a star-shaped fracture: breakable by dash or pound."""
    s.fill(SAND)
    _bevel(s, (236, 206, 150), SAND_DARK)
    _speckle(s, SAND_DARK, 5, 6)
    center = (15, 16)
    for end in ((3, 4), (27, 6), (29, 25), (6, 28), (16, 1), (1, 17)):
        pygame.draw.line(s, (110, 76, 44), center, end, 2)
        pygame.draw.line(s, (250, 226, 180), (center[0] + 1, center[1] + 1), (end[0] + 1, end[1] + 1), 1)
    pygame.draw.circle(s, (110, 76, 44), center, 3)
    pygame.draw.rect(s, OUTLINE, s.get_rect(), 1)


def _paint_unknown(s: pygame.Surface) -> None:
    s.fill((255, 0, 255))


TILE_PAINTERS: dict[str, Callable[[pygame.Surface], None]] = {
    # original ids 0-19 (keep order stable; see tools/build_assets.py)
    "ground": _paint_ground,
    "dirt": _paint_dirt,
    "stone": _paint_stone,
    "brick": _paint_brick,
    "question": _paint_zellige,
    "question_powerup": _paint_zellige_marked(MARKER_POWERUP),
    "question_life": _paint_zellige_marked(MARKER_LIFE),
    "coin": _paint_coin_tile,
    "used_block": _paint_used_block,
    "platform": _paint_platform,
    "pipe_top_left": _paint_well(left=True, top=True),
    "pipe_top_right": _paint_well(left=False, top=True),
    "pipe_left": _paint_well(left=True, top=False),
    "pipe_right": _paint_well(left=False, top=False),
    "cloud_left": lambda s: s.blit(_make_cloud(), (0, 0)),
    "cloud_right": lambda s: s.blit(_make_cloud(), (-T, 0)),
    "bush": _paint_orange_tree,
    "grass": _paint_myrtle,
    "flower": _paint_geranium_pot,
    "fence": _paint_arcade,
    # new tiles
    "marble": _paint_marble,
    "ashlar": _paint_ashlar,
    "roof": _paint_roof,
    "plaster": _paint_plaster,
    "wood": _paint_wood,
    "mudejar": _paint_mudejar,
    "rock": _paint_rock,
    "ice": _paint_ice,
    "red_wall": _paint_red_wall,
    "palace": _paint_palace,
    "court": _paint_court,
    "awning": _paint_awning,
    "shelf": _paint_shelf,
    "ledge": _paint_ledge,
    "bridge": _paint_bridge,
    "question_star": _paint_zellige_marked(MARKER_STAR),
    "crumble": _paint_crumble,
    "sun_block": _paint_switch(SUN, SUN_DARK, True),
    "moon_block": _paint_switch(MOON, MOON_DARK, False),
    "spikes": _paint_spikes,
    "tuft": _paint_grass_tuft,
    "rock_small": _paint_rock_small,
    "books": _paint_books,
    "vase": _paint_vase,
    "cracked": _paint_cracked,
}


def make_tile(name: str) -> pygame.Surface:
    surface = _surface()
    TILE_PAINTERS.get(name, _paint_unknown)(surface)
    return surface


def make_debris(size: int, color: Color = BRICK_RED) -> pygame.Surface:
    s = _surface(size, size)
    s.fill(color)
    s.fill(MORTAR, (0, size // 2, size, 2))
    return s


# --- Auto-tiling decorations ---------------------------------------------------------------
# A cap is drawn above a terrain tile whose top is exposed. It receives the
# target surface, the tile's top-left, whether the left/right sides are also
# exposed, and a deterministic random number for variety.
Cap = Callable[[pygame.Surface, int, int, bool, bool, float], None]


def _cap_grass(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    s.fill(LEAF_DARK, (x, y - 2, T, 3))
    s.fill(LEAF, (x, y - 3, T, 2))
    rng = random.Random(int(r * 1e6))
    for _ in range(9):
        bx = x + rng.randrange(0, T)
        h = rng.randrange(3, 8)
        color = LEAF_LIGHT if rng.random() < 0.5 else LEAF
        pygame.draw.line(s, color, (bx, y - 1), (bx + rng.choice((-1, 0, 1)), y - h), 1)
    if r > 0.72:
        fx = x + 6 + int(r * 17) % 20
        pygame.draw.line(s, LEAF_DARK, (fx, y - 1), (fx, y - 7))
        color = ((236, 70, 90), (250, 220, 90), (240, 240, 255))[int(r * 97) % 3]
        pygame.draw.circle(s, color, (fx, y - 8), 2)
    if left:
        pygame.draw.circle(s, LEAF, (x + 1, y - 1), 3)
    if right:
        pygame.draw.circle(s, LEAF, (x + T - 2, y - 1), 3)


def _cap_marble(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    s.fill(GOLD_DARK, (x, y - 3, T, 3))
    s.fill(GOLD_LIGHT, (x, y - 3, T, 1))
    for dx in range(2, T, 6):
        s.fill(MARBLE_SHADE, (x + dx, y + 2, 3, 2))


def _cap_roof(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    for dx in range(0, T, 8):
        pygame.draw.ellipse(s, ROOF_DARK, (x + dx, y - 5, 9, 8))
        pygame.draw.ellipse(s, ROOF_LIGHT, (x + dx + 1, y - 5, 7, 6))


def _cap_plaster(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    lip = 2
    s.fill(TERRACOTTA_DARK, (x - (lip if left else 0), y - 4, T + (lip if left else 0) + (lip if right else 0), 5))
    s.fill(TERRACOTTA_LIGHT, (x - (lip if left else 0), y - 4, T + (lip if left else 0) + (lip if right else 0), 2))


def _cap_mudejar(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    for dx in range(0, T, 6):
        s.fill((150, 70, 44), (x + dx, y - 4, 5, 5))
        s.fill((196, 110, 76), (x + dx, y - 4, 5, 1))


def _cap_snow(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    rng = random.Random(int(r * 1e6))
    s.fill(SNOW_SHADE, (x, y - 1, T, 4))
    for k in range(5):
        cx = x + k * 8 + rng.randrange(-2, 3)
        radius = rng.randrange(4, 7)
        pygame.draw.circle(s, SNOW, (cx, y + 1), radius)
    s.fill(SNOW, (x, y - 2, T, 4))
    if left:
        pygame.draw.circle(s, SNOW, (x + 1, y + 2), 4)
    if right:
        pygame.draw.circle(s, SNOW, (x + T - 2, y + 2), 4)


def _cap_fortress(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    """Merlons: the crenellated parapet crowning every exposed wall top."""
    s.fill(RED_WALL_DARK, (x, y - 2, T, 2))
    for dx in (1, 17):
        s.fill(RED_WALL, (x + dx, y - 10, 12, 9))
        s.fill(RED_WALL_LIGHT, (x + dx, y - 10, 12, 2))
        s.fill(RED_WALL_DARK, (x + dx + 10, y - 8, 2, 7))


def _cap_palace(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    s.fill(MARBLE, (x, y - 3, T, 4))
    s.fill(GOLD, (x, y + 1, T, 1))
    s.fill(MARBLE_SHADE, (x, y - 3, T, 1))


def _cap_court(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    s.fill((250, 250, 248), (x, y - 2, T, 3))
    s.fill((200, 196, 190), (x, y + 1, T, 1))


def _cap_stone(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    s.fill(IVORY_LIGHT, (x, y - 1, T, 2))


def _cap_ivy(s: pygame.Surface, x: int, y: int, left: bool, right: bool, r: float) -> None:
    """Stone with a little moss/ivy on top in the gardens."""
    _cap_stone(s, x, y, left, right, r)
    if r > 0.55:
        rng = random.Random(int(r * 1e6))
        for _ in range(5):
            pygame.draw.circle(s, LEAF if rng.random() < 0.6 else LEAF_LIGHT,
                               (x + rng.randrange(2, T - 2), y + rng.randrange(-1, 2)), 2)


Bottom = Callable[[pygame.Surface, int, int, float], None]


def _bottom_icicles(s: pygame.Surface, x: int, y: int, r: float) -> None:
    rng = random.Random(int(r * 1e6) + 7)
    for _ in range(rng.randrange(1, 4)):
        ix = x + rng.randrange(3, T - 3)
        length = rng.randrange(4, 12)
        pygame.draw.polygon(s, ICE_LIGHT, ((ix - 2, y), (ix + 2, y), (ix, y + length)))
        pygame.draw.line(s, WHITE, (ix - 1, y), (ix - 1, y + length // 2))


def _bottom_moulding(s: pygame.Surface, x: int, y: int, r: float) -> None:
    for dx in range(0, T, 8):
        pygame.draw.polygon(s, MARBLE_SHADE, ((x + dx, y), (x + dx + 8, y), (x + dx + 4, y + 4)))


def _bottom_roots(s: pygame.Surface, x: int, y: int, r: float) -> None:
    if r > 0.5:
        rng = random.Random(int(r * 1e6) + 3)
        rx = x + rng.randrange(4, T - 4)
        pygame.draw.lines(s, LEAF_DARK, False, ((rx, y), (rx + 2, y + 4), (rx, y + 8)), 1)


@dataclass(frozen=True)
class TerrainStyle:
    cap: Cap | None = None
    bottom: Bottom | None = None
    rim: Color = OUTLINE
    rim_width: int = 1
    # Buried tiles darken this much per tile of depth (0 = no depth shading).
    depth_shade: float = 0.1
    max_depth: int = 4


TERRAIN_STYLES: dict[str, TerrainStyle] = {
    "ground": TerrainStyle(cap=_cap_grass, bottom=_bottom_roots, rim=(96, 60, 36)),
    "dirt": TerrainStyle(cap=_cap_grass, bottom=_bottom_roots, rim=(96, 60, 36)),
    "stone": TerrainStyle(cap=_cap_ivy, rim=(120, 104, 80), depth_shade=0.06),
    "marble": TerrainStyle(cap=_cap_marble, bottom=_bottom_moulding, rim=(150, 140, 126), depth_shade=0.05),
    "ashlar": TerrainStyle(cap=_cap_marble, rim=(140, 116, 84), depth_shade=0.07),
    "roof": TerrainStyle(cap=_cap_roof, rim=ROOF_DARK, depth_shade=0.05),
    "plaster": TerrainStyle(cap=_cap_plaster, rim=(170, 156, 132), depth_shade=0.04),
    "wood": TerrainStyle(rim=WOOD_DARK, depth_shade=0.08),
    "mudejar": TerrainStyle(cap=_cap_mudejar, rim=(110, 50, 30), depth_shade=0.08),
    "rock": TerrainStyle(cap=_cap_snow, bottom=_bottom_icicles, rim=ROCK_DARK, depth_shade=0.08),
    "ice": TerrainStyle(cap=_cap_snow, bottom=_bottom_icicles, rim=ICE_DARK, depth_shade=0.04),
    "red_wall": TerrainStyle(cap=_cap_fortress, rim=RED_WALL_DARK, depth_shade=0.07),
    "palace": TerrainStyle(cap=_cap_palace, rim=ZELLIGE_DARK, depth_shade=0.04),
    "court": TerrainStyle(cap=_cap_court, rim=(170, 166, 160), depth_shade=0.05),
}

# Terrain tiles that visually merge with each other (a dirt tile under a
# ground tile is "buried", not exposed).
SOLID_TERRAIN = frozenset(TERRAIN_STYLES)
