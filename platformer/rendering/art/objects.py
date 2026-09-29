"""Art for level objects: drums, fountains, lily pads, lanterns, braziers,
gates, signs, the lion-head turret, the Sword of Light, trees and props.

Static images are rendered once (callers cache them); a few objects expose
frame functions so their animation can be baked into short loops.
"""

import math
import random

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, horseshoe_arch, mix, shade, star_polygon
from rendering.art.tiles import eight_point_star

OUTLINE: Color = (42, 26, 22)
GOLD: Color = (226, 172, 52)
GOLD_LIGHT: Color = (255, 226, 130)
GOLD_DARK: Color = (160, 108, 24)
IVORY: Color = (232, 218, 186)
IVORY_DARK: Color = (180, 160, 124)
TERRACOTTA: Color = (190, 90, 54)
TERRACOTTA_DARK: Color = (136, 58, 34)
AZULEJO: Color = (40, 104, 186)
ZELLIGE_GREEN: Color = (36, 138, 96)
CEDAR: Color = (132, 80, 44)
CEDAR_LIGHT: Color = (172, 114, 64)
CEDAR_DARK: Color = (88, 50, 28)
BRICK_RED: Color = (170, 70, 46)
WHITE: Color = (255, 255, 255)
LEAF: Color = (52, 124, 62)
LEAF_LIGHT: Color = (98, 170, 86)
LEAF_DARK: Color = (30, 84, 44)
STONE: Color = (196, 186, 170)
STONE_DARK: Color = (130, 120, 108)


# --- Darbuka drum (spring) ----------------------------------------------------------
def drum(squash: float = 1.0) -> pygame.Surface:
    """A goblet drum; ``squash`` < 1 compresses the head when bounced on."""
    width, height = 34, 32
    c = Canvas(width, height, fringe=OUTLINE)
    top = height - 26 * squash
    # Hourglass body.
    body = [(6, top + 4), (28, top + 4), (22, top + 13 * squash), (25, height - 1), (9, height - 1), (12, top + 13 * squash)]
    c.polygon(TERRACOTTA, body, OUTLINE, 0.9)
    c.polygon(TERRACOTTA_DARK, [(20, top + 4), (28, top + 4), (22, top + 13 * squash), (25, height - 1), (20, height - 1)])
    # Mosaic band.
    band_y = top + 7 * squash
    c.rect(AZULEJO, (8.5, band_y, 17, 3 * squash))
    for k in range(4):
        c.circle(GOLD_LIGHT, (10.5 + k * 4.3, band_y + 1.5 * squash), 0.9)
    c.rect(GOLD, (8, height - 5, 18, 2))
    # Drumhead with lacing.
    c.ellipse(IVORY, (4, top, 26, 7), OUTLINE, 0.9)
    c.ellipse((246, 236, 212), (7, top + 1, 20, 4))
    for k in range(6):
        x = 6.5 + k * 4.2
        c.line(CEDAR_DARK, (x, top + 6), (x + 1.5, top + 9 * squash), 0.6)
    return c.finish()


# --- Fountain nozzle ---------------------------------------------------------------------
def fountain_basin() -> pygame.Surface:
    width, height = 44, 18
    c = Canvas(width, height, fringe=OUTLINE)
    c.polygon(IVORY, [(2, 4), (42, 4), (38, 17), (6, 17)], OUTLINE, 0.9)
    c.rect(IVORY_DARK, (4, 12, 36, 5))
    c.ellipse((90, 160, 220), (6, 2, 32, 5), OUTLINE, 0.6)
    for k in range(4):
        eight_star = star_polygon((10 + k * 8, 10), 2.2)
        c.polygon(AZULEJO, eight_star)
    c.rect(STONE_DARK, (19, 0, 6, 4), outline=OUTLINE, width=0.6)
    return c.finish()


def water_column_texture(width: int = 26, height: int = 64) -> pygame.Surface:
    """Vertically tileable translucent water with streaks, for fountain jets."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    for x in range(width):
        edge = min(x, width - 1 - x) / (width / 2)
        alpha = int(90 + 110 * min(1.0, edge * 2.2))
        pygame.draw.line(s, (150, 210, 250, alpha), (x, 0), (x, height))
    rng = random.Random(4)
    for _ in range(22):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(height)
        length = rng.randrange(6, 18)
        for dy in range(length):
            s.set_at((x, (y + dy) % height), (240, 250, 255, 200))
    return s


# --- Lily pad ------------------------------------------------------------------------------
def lily_pad(width: int, flower: bool) -> pygame.Surface:
    height = 16
    c = Canvas(width, height, fringe=LEAF_DARK)
    c.ellipse(LEAF_DARK, (0, 5, width, 10))
    c.ellipse(LEAF, (1, 3, width - 2, 10))
    c.polygon(LEAF_DARK, [(width / 2, 8), (width / 2 + 8, 3), (width / 2 + 3, 3)])
    for k in range(5):
        a = math.pi * (0.1 + k * 0.2)
        c.line(LEAF_LIGHT, (width / 2, 8), (width / 2 + math.cos(a) * width * 0.4, 8 + math.sin(a) * 3.5 - 2), 0.5)
    if flower:
        cx, cy = width * 0.3, 4
        for k in range(6):
            a = k * math.pi / 3
            c.ellipse((246, 170, 196), (cx + math.cos(a) * 2.6 - 2.2, cy + math.sin(a) * 1.4 - 2.6, 4.4, 5.2))
        c.circle((255, 226, 120), (cx, cy), 1.5)
    return c.finish()


# --- Flying carpet --------------------------------------------------------------------------
def carpet_texture(width: int, height: int = 12) -> pygame.Surface:
    """Flat, un-waved carpet; the game slices and waves it at draw time."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    red, deep, gold, blue, cream = (170, 30, 44), (110, 20, 34), (230, 180, 70), (40, 70, 150), (240, 226, 190)
    s.fill(red)
    s.fill(deep, (0, 0, width, 2))
    s.fill(deep, (0, height - 2, width, 2))
    s.fill(gold, (0, 2, width, 1))
    s.fill(gold, (0, height - 3, width, 1))
    for x in range(4, width - 4, 12):
        pygame.draw.polygon(s, blue, ((x, height // 2), (x + 5, 3), (x + 10, height // 2), (x + 5, height - 3)))
        pygame.draw.polygon(s, cream, ((x + 3, height // 2), (x + 5, 5), (x + 7, height // 2), (x + 5, height - 5)))
    s.fill(gold, (0, 0, 2, height))
    s.fill(gold, (width - 2, 0, 2, height))
    return s


# --- Lantern / brazier (checkpoints) -----------------------------------------------------------
def lantern_post(lit: bool) -> pygame.Surface:
    """A cedar post with an arm; the lantern itself is drawn swinging at runtime."""
    width, height = 32, 64
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(CEDAR, (8, 10, 5, height - 10), outline=OUTLINE, width=0.8)
    c.rect(CEDAR_LIGHT, (9, 10, 1.5, height - 12))
    c.rect(CEDAR, (8, 9, 19, 4), outline=OUTLINE, width=0.8)
    c.rect(IVORY_DARK, (3, height - 6, 15, 6), outline=OUTLINE, width=0.8)
    c.polygon(GOLD, [(24, 13), (26, 13), (25.5, 16), (24.5, 16)])
    return c.finish()


def lantern(lit: bool) -> pygame.Surface:
    width, height = 14, 22
    c = Canvas(width, height, fringe=OUTLINE)
    c.line(GOLD_DARK, (7, 0), (7, 3), 0.8)
    c.polygon(GOLD, [(1.5, 6), (7, 2), (12.5, 6)], OUTLINE, 0.6)
    c.rect(GOLD, (2, 6, 10, 11), outline=OUTLINE, width=0.6)
    glass = (255, 214, 96) if lit else (70, 70, 88)
    c.rect(glass, (3.6, 7.4, 6.8, 8.2))
    c.line(GOLD_DARK, (7, 7), (7, 16), 0.6)
    if lit:
        c.ellipse((255, 250, 220), (5.5, 9, 3, 5))
    c.polygon(GOLD, [(2, 17), (12, 17), (7, 21)], OUTLINE, 0.6)
    return c.finish()


def brazier(lit: bool) -> pygame.Surface:
    width, height = 32, 40
    c = Canvas(width, height, fringe=OUTLINE)
    c.polygon((70, 60, 64), [(4, 18), (28, 18), (23, 27), (9, 27)], OUTLINE, 0.9)
    c.rect((80, 70, 74), (14, 27, 4, 10), outline=OUTLINE, width=0.6)
    c.polygon((80, 70, 74), [(8, 39), (24, 39), (20, 35), (12, 35)], OUTLINE, 0.6)
    c.line(GOLD, (5, 20), (27, 20), 0.8)
    if not lit:
        for k in range(4):
            c.circle((40, 30, 30), (9 + k * 4.5, 17), 2.2)
    return c.finish()


def flame_frames(count: int = 6, width: int = 20, height: int = 26, color: Color = (255, 150, 40)) -> list[pygame.Surface]:
    """A licking flame loop (drawn on braziers and torches)."""
    frames = []
    for k in range(count):
        c = Canvas(width, height, fringe=(120, 30, 10))
        t = k / count * math.tau
        cx = width / 2
        for layer, (col, scale) in enumerate(((color, 1.0), ((255, 210, 90), 0.66), ((255, 250, 210), 0.36))):
            h = (height - 2) * scale * (0.9 + 0.1 * math.sin(t * 2 + layer))
            w = width * 0.42 * scale
            sway = math.sin(t + layer * 0.7) * 2.4 * scale
            points = [(cx - w, height - 1), (cx - w * 0.8, height - 1 - h * 0.45), (cx + sway, height - 1 - h),
                      (cx + w * 0.8, height - 1 - h * 0.45), (cx + w, height - 1)]
            c.polygon(col, points)
        frames.append(c.finish())
    return frames


# --- Lion head turret ------------------------------------------------------------------------------
def lion_head(open_mouth: bool, glowing: bool) -> pygame.Surface:
    """Stone lion of the Court of the Lions, facing right, on a small plinth."""
    size = 32
    c = Canvas(size, size, fringe=OUTLINE)
    c.rect(STONE_DARK, (0, 24, 32, 8), outline=OUTLINE, width=0.8)
    c.circle(STONE, (14, 14), 11, OUTLINE, 0.9)      # mane
    for k in range(9):
        a = math.pi * 0.55 + k * math.pi * 1.1 / 8
        c.circle(STONE_DARK, (14 + math.cos(a) * 10, 14 + math.sin(a) * 10), 2.4)
    c.ellipse((214, 204, 188), (13, 7, 16, 14), OUTLINE, 0.8)  # face
    c.ellipse(STONE, (22, 11, 9, 8), OUTLINE, 0.7)  # snout
    eye = (255, 60, 40) if glowing else OUTLINE
    c.circle(eye, (21, 11), 1.5)
    if open_mouth:
        c.polygon((60, 20, 20), [(23, 17), (31, 16), (31, 22), (24, 21)])
        c.polygon(WHITE, [(26, 17), (27, 19), (28, 17)])
    else:
        c.line(OUTLINE, (24, 18.5), (30.5, 18), 0.7)
    return c.finish()


# --- Sign ------------------------------------------------------------------------------------------
def sign_post() -> pygame.Surface:
    width, height = 32, 32
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(CEDAR_DARK, (14, 14, 4, 18), outline=OUTLINE, width=0.7)
    c.rect(CEDAR, (3, 3, 26, 14), radius=2, outline=OUTLINE, width=0.9)
    c.rect(CEDAR_LIGHT, (5, 5, 22, 2))
    for k, w in enumerate((16, 12, 18)):
        c.line((70, 40, 24), (7, 8.5 + k * 3), (7 + w, 8.5 + k * 3), 0.7)
    return c.finish()


# --- Gates and goals -------------------------------------------------------------------------------
def arch_gate() -> pygame.Surface:
    """Level exit: a horseshoe arch with red and white voussoirs in an alfiz."""
    width, height = 104, 136
    c = Canvas(width, height, fringe=OUTLINE)
    cx, spring = width / 2, 52
    # Alfiz frame and wall.
    c.rect(IVORY, (0, 0, width, 78), outline=OUTLINE, width=1.0)
    c.rect(IVORY_DARK, (4, 4, width - 8, 70))
    c.rect(IVORY, (6, 6, width - 12, 66))
    # Voussoirs.
    for k in range(22):
        a0 = math.radians(215 - k * (250 / 22))
        a1 = math.radians(215 - (k + 1) * (250 / 22))
        wedge = [(cx + math.cos(a0) * 30, spring - math.sin(a0) * 30), (cx + math.cos(a0) * 44, spring - math.sin(a0) * 44),
                 (cx + math.cos(a1) * 44, spring - math.sin(a1) * 44), (cx + math.cos(a1) * 30, spring - math.sin(a1) * 30)]
        c.polygon(BRICK_RED if k % 2 else (246, 238, 220), wedge)
    opening = horseshoe_arch(cx, spring, 30, height)
    c.polygon((44, 26, 36), opening)
    # Jambs.
    for x in (4, width - 22):
        c.rect(IVORY, (x, 76, 18, height - 76), outline=OUTLINE, width=0.9)
        c.rect(IVORY_DARK, (x + 12, 78, 4, height - 78))
        c.rect(GOLD, (x - 2, 72, 22, 5), outline=OUTLINE, width=0.6)
    # Spandrels with stars.
    for sx in (14, width - 14):
        c.star(AZULEJO, (sx, 14), 6.5)
        c.star(GOLD_LIGHT, (sx, 14), 3)
    return c.finish()


def arch_glow_interior() -> pygame.Surface:
    """The light seen through the gate when the level is finished."""
    width, height = 104, 136
    c = Canvas(width, height, fringe=(255, 220, 150))
    c.polygon((255, 236, 180), horseshoe_arch(width / 2, 52, 29, height))
    return c.finish()


def sword_shrine() -> pygame.Surface:
    """The Sword of Light resting in a zellige pedestal."""
    width, height = 64, 128
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(IVORY, (10, 98, 44, 30), outline=OUTLINE, width=1.0)
    c.rect(IVORY_DARK, (6, 94, 52, 6), outline=OUTLINE, width=0.8)
    c.rect((242, 240, 232), (18, 104, 28, 18))
    c.star(AZULEJO, (32, 113), 7)
    c.star(GOLD_LIGHT, (32, 113), 3)
    # Blade, guard, grip, pommel.
    c.polygon((226, 234, 246), [(28.5, 44), (35.5, 44), (35.5, 94), (32, 99), (28.5, 94)], OUTLINE, 0.8)
    c.line((170, 180, 200), (32, 46), (32, 96), 0.8)
    c.rect(GOLD, (18, 38, 28, 5), radius=2, outline=OUTLINE, width=0.8)
    c.rect((96, 44, 32), (29.5, 24, 5, 14), outline=OUTLINE, width=0.7)
    c.circle(GOLD, (32, 22), 3.5, OUTLINE, 0.7)
    c.circle((210, 30, 60), (32, 40.5), 1.8)
    return c.finish()


# --- Pendulum / wheel / platforms ------------------------------------------------------------------
def pendulum_lamp(width: int) -> pygame.Surface:
    """A great brass lamp you can stand on (the pendulum platform)."""
    height = 26
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(GOLD, (0, 0, width, 6), radius=2, outline=OUTLINE, width=0.8)
    c.rect(GOLD_LIGHT, (2, 1, width - 4, 1.5))
    body = [(4, 6), (width - 4, 6), (width / 2 + 7, 18), (width / 2 + 3, 25), (width / 2 - 3, 25), (width / 2 - 7, 18)]
    c.polygon(GOLD_DARK, body, OUTLINE, 0.8)
    for k in range(5):
        x = 8 + k * (width - 16) / 4
        c.circle((255, 220, 120), (x, 9.5), 1.4)
    c.star(GOLD_LIGHT, (width / 2, 14), 3.5)
    return c.finish()


def wheel_seat(width: int) -> pygame.Surface:
    height = 14
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(CEDAR, (0, 0, width, 8), radius=2, outline=OUTLINE, width=0.8)
    c.rect(CEDAR_LIGHT, (2, 1, width - 4, 2))
    c.polygon(CEDAR_DARK, [(width / 2 - 5, 8), (width / 2 + 5, 8), (width / 2, 13)])
    return c.finish()


def platform_strip(style: str, width: int) -> pygame.Surface:
    """Artwork for a moving platform of any width (tiles are 32 wide)."""
    from rendering.art.tiles import make_tile

    tile_name = {"beam": "platform", "marble": "ledge", "shelf": "shelf", "awning": "awning", "bridge": "bridge"}.get(style, "platform")
    tile = make_tile(tile_name)
    strip = pygame.Surface((width, 32), pygame.SRCALPHA)
    for x in range(0, width, 32):
        strip.blit(tile, (x, 0))
    return strip


# --- Trees and decorative props ----------------------------------------------------------------------
def orange_tree(size: int = 1) -> pygame.Surface:
    width, height = 72 * size, 88 * size
    s = size
    c = Canvas(width, height, fringe=LEAF_DARK)
    c.polygon((110, 72, 42), [(width / 2 - 4 * s, height), (width / 2 + 4 * s, height), (width / 2 + 2 * s, height - 36 * s), (width / 2 - 2 * s, height - 36 * s)], OUTLINE, 0.8)
    rng = random.Random(9)
    blobs = [(width / 2 + rng.uniform(-20, 20) * s, height - 50 * s + rng.uniform(-18, 14) * s, rng.uniform(13, 19) * s) for _ in range(9)]
    for x, y, r in blobs:
        c.circle(LEAF_DARK, (x, y + 2), r)
    for x, y, r in blobs:
        c.circle(LEAF, (x, y), r * 0.9)
    for x, y, r in blobs[:5]:
        c.circle(LEAF_LIGHT, (x - r * 0.3, y - r * 0.35), r * 0.35)
    for _ in range(16):
        x, y, r = rng.choice(blobs)
        c.circle((246, 146, 32), (x + rng.uniform(-r, r) * 0.7, y + rng.uniform(-r, r) * 0.7), 2.6 * s, OUTLINE, 0.5)
    return c.finish()


def cypress(height: int = 110) -> pygame.Surface:
    width = max(24, height // 4)
    c = Canvas(width, height, fringe=LEAF_DARK)
    c.ellipse(LEAF_DARK, (0, 0, width, height - 4))
    c.ellipse((40, 100, 56), (width * 0.15, height * 0.04, width * 0.6, height * 0.9))
    for k in range(7):
        y = height * (0.12 + k * 0.11)
        c.ellipse((58, 124, 70), (width * 0.3, y, width * 0.28, height * 0.06))
    c.rect((90, 60, 40), (width / 2 - 2, height - 8, 4, 8))
    return c.finish()


def palm(height: int = 120) -> pygame.Surface:
    width = height
    c = Canvas(width, height, fringe=LEAF_DARK)
    base = (width / 2, height)
    top = (width / 2 + height * 0.1, height * 0.22)
    trunk = [(base[0] + math.sin(t * 1.4) * 4 + (top[0] - base[0]) * t, base[1] + (top[1] - base[1]) * t) for t in [k / 8 for k in range(9)]]
    c.tapered(OUTLINE, trunk, 5.2, 3.6)
    c.tapered((140, 100, 60), trunk, 4.2, 2.8)
    for k in range(1, 8):
        p = trunk[k]
        c.line((110, 76, 44), (p[0] - 3.5, p[1]), (p[0] + 3.5, p[1] - 1), 0.8)
    for angle in (-170, -140, -110, -70, -40, -10, -90):
        a = math.radians(angle)
        length = height * 0.42
        tip = (top[0] + math.cos(a) * length, top[1] - math.sin(a) * length * 0.55 + length * 0.3)
        mid = ((top[0] + tip[0]) / 2, (top[1] + tip[1]) / 2 - length * 0.18)
        c.tapered(LEAF_DARK, [top, mid, tip], 3.4, 0.6)
        c.tapered(LEAF, [top, mid, tip], 2.4, 0.3)
    for k in range(3):
        c.circle((120, 70, 30), (top[0] - 3 + k * 3, top[1] + 3), 2.2)
    return c.finish()


def column(height: int = 96) -> pygame.Surface:
    width = 24
    c = Canvas(width, height, fringe=OUTLINE)
    c.rect(IVORY, (7, 10, 10, height - 18), outline=OUTLINE, width=0.8)
    c.rect(IVORY_DARK, (13, 12, 3, height - 22))
    c.rect(IVORY, (2, 0, 20, 10), radius=2, outline=OUTLINE, width=0.8)
    for k in range(3):
        c.line(IVORY_DARK, (4, 3 + k * 2.4), (20, 3 + k * 2.4), 0.5)
    c.rect(IVORY, (4, height - 9, 16, 9), outline=OUTLINE, width=0.8)
    return c.finish()


def urn() -> pygame.Surface:
    c = Canvas(28, 34, fringe=OUTLINE)
    c.ellipse(AZULEJO, (3, 9, 22, 22), OUTLINE, 0.8)
    c.rect(AZULEJO, (9, 3, 10, 8), outline=OUTLINE, width=0.7)
    c.rect((240, 238, 228), (4, 17, 20, 4))
    for k in range(4):
        c.star(GOLD_LIGHT, (7 + k * 4.7, 19), 1.4)
    c.rect(GOLD, (8, 1, 12, 3), outline=OUTLINE, width=0.6)
    c.rect(GOLD, (9, 30, 10, 4), outline=OUTLINE, width=0.6)
    return c.finish()


def lion_statue() -> pygame.Surface:
    """A lion of the Fountain of the Lions (seen from the side)."""
    c = Canvas(40, 36, fringe=OUTLINE)
    c.rect(STONE, (8, 16, 24, 12), radius=4, outline=OUTLINE, width=0.8)
    for x in (10, 16, 24, 29):
        c.rect(STONE, (x, 24, 4, 12), outline=OUTLINE, width=0.7)
    c.circle(STONE, (31, 14), 8, OUTLINE, 0.8)
    for k in range(7):
        a = math.pi * 0.6 + k * 0.28
        c.circle(STONE_DARK, (31 + math.cos(a) * 7, 14 + math.sin(a) * 7), 2)
    c.ellipse((220, 212, 198), (31, 9, 8, 9), OUTLINE, 0.6)
    c.circle(OUTLINE, (35, 12), 0.9)
    c.lines(STONE_DARK, [(8, 18), (3, 14), (4, 10)], 1.6)
    return c.finish()


def lion_fountain() -> pygame.Surface:
    """The Fountain of the Lions: twelve lions under a twelve-sided basin."""
    width, height = 200, 110
    c = Canvas(width, height, fringe=OUTLINE)
    c.ellipse(STONE_DARK, (10, height - 18, width - 20, 18))
    c.ellipse((70, 120, 170), (18, height - 16, width - 36, 12))
    lion = lion_statue()
    for k, x in enumerate((24, 58, 92, 126, 150)):
        img = lion if k % 2 == 0 else pygame.transform.flip(lion, True, False)
        c.blit(img, (x, height - 50))
    c.polygon(IVORY, [(40, 58), (160, 58), (150, 68), (50, 68)], OUTLINE, 0.9)
    c.ellipse((230, 222, 204), (46, 50, 108, 14), OUTLINE, 0.8)
    c.rect(IVORY, (92, 22, 16, 30), outline=OUTLINE, width=0.8)
    c.ellipse((230, 222, 204), (74, 16, 52, 10), OUTLINE, 0.8)
    c.rect(IVORY, (97, 4, 6, 14), outline=OUTLINE, width=0.6)
    return c.finish()


def hanging_lamp() -> pygame.Surface:
    c = Canvas(24, 30, fringe=OUTLINE)
    c.polygon(GOLD, [(4, 8), (12, 2), (20, 8)], OUTLINE, 0.6)
    c.polygon(GOLD_DARK, [(3, 8), (21, 8), (16, 22), (8, 22)], OUTLINE, 0.7)
    for k in range(4):
        c.circle((255, 220, 120), (7 + k * 3.4, 12), 1.1)
    c.polygon(GOLD, [(8, 22), (16, 22), (12, 29)], OUTLINE, 0.6)
    return c.finish()


def banner(width: int = 20, height: int = 40, color: Color = (170, 30, 44)) -> pygame.Surface:
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    s.fill(color)
    s.fill(GOLD, (0, 0, width, 3))
    pygame.draw.polygon(s, GOLD, ((width // 2, 10), (width - 5, height // 2), (width // 2, height - 12), (5, height // 2)), 2)
    eight_point_star(s, GOLD_LIGHT, (width / 2, height / 2 - 1), 4)
    return s


def astrolabe_ring(radius: int, color: Color = GOLD) -> pygame.Surface:
    size = radius * 2 + 6
    c = Canvas(size, size, fringe=OUTLINE)
    center = (size / 2, size / 2)
    c.ring(OUTLINE, center, radius + 1.5, 4.5)
    c.ring(color, center, radius, 2.6)
    for k in range(12):
        a = k * math.pi / 6
        c.line(GOLD_DARK, (center[0] + math.cos(a) * (radius - 2), center[1] + math.sin(a) * (radius - 2)),
               (center[0] + math.cos(a) * (radius + 2), center[1] + math.sin(a) * (radius + 2)), 0.8)
    c.line(color, (center[0] - radius, center[1]), (center[0] + radius, center[1]), 1.4)
    c.star(color, center, radius * 0.35, rotation=10)
    return c.finish()


def water_clock_face(radius: int = 40) -> pygame.Surface:
    size = radius * 2 + 8
    c = Canvas(size, size, fringe=OUTLINE)
    center = (size / 2, size / 2)
    c.circle(GOLD_DARK, center, radius + 2, OUTLINE, 1.2)
    c.circle((240, 228, 196), center, radius - 2)
    for k in range(12):
        a = k * math.pi / 6
        inner = radius - (8 if k % 3 == 0 else 5)
        c.line(OUTLINE, (center[0] + math.cos(a) * inner, center[1] + math.sin(a) * inner),
               (center[0] + math.cos(a) * (radius - 3), center[1] + math.sin(a) * (radius - 3)), 1.0)
    c.star(AZULEJO, center, radius * 0.32)
    return c.finish()
