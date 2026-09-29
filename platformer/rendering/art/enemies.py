"""Enemy sprites: desert scorpion, haunted clay jar, jinn wisp, hedgehog,
bat and ghul. All face right; the game mirrors them.

Each painter follows the SheetSpec painter signature (surface, animation,
frame) and draws on a supersampled Canvas for smooth edges.
"""

import math

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, limb, mix, shade

OUTLINE: Color = (40, 22, 26)
WHITE: Color = (255, 255, 255)
EYE_GLOW: Color = (255, 232, 120)

SCORPION: Color = (196, 128, 60)
SCORPION_LIGHT: Color = (228, 170, 96)
SCORPION_DARK: Color = (124, 72, 32)
STINGER: Color = (70, 34, 26)

TERRACOTTA: Color = (192, 92, 54)
TERRACOTTA_LIGHT: Color = (224, 132, 86)
TERRACOTTA_DARK: Color = (134, 58, 34)
AZULEJO: Color = (40, 104, 186)
AZULEJO_LIGHT: Color = (120, 178, 236)

JINN: Color = (150, 92, 230)
JINN_LIGHT: Color = (214, 184, 255)
JINN_DARK: Color = (92, 48, 170)

HEDGEHOG: Color = (142, 100, 70)
HEDGEHOG_SPINE: Color = (94, 62, 44)
HEDGEHOG_FACE: Color = (228, 196, 160)

BAT: Color = (86, 58, 110)
BAT_WING: Color = (120, 84, 150)
BAT_DARK: Color = (54, 34, 72)

GHUL: Color = (200, 214, 206)
GHUL_SHADE: Color = (130, 150, 150)
GHUL_EYES: Color = (120, 255, 190)


def _angry_eye(c: Canvas, center: tuple[float, float], size: float = 1.0, color: Color = WHITE) -> None:
    x, y = center
    c.circle(color, (x, y), 1.8 * size, OUTLINE, 0.6)
    c.circle(OUTLINE, (x + 0.5 * size, y + 0.2), 0.9 * size)
    c.circle(WHITE, (x + 0.2, y - 0.4), 0.35)


def _x_eye(c: Canvas, center: tuple[float, float]) -> None:
    x, y = center
    c.line(OUTLINE, (x - 1.2, y - 1.2), (x + 1.2, y + 1.2), 0.7)
    c.line(OUTLINE, (x - 1.2, y + 1.2), (x + 1.2, y - 1.2), 0.7)


# --- Scorpion ---------------------------------------------------------------------
def paint_scorpion(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 32, fringe=OUTLINE)
    if animation == "squashed":
        c.ellipse(SCORPION, (3, 26.5, 26, 5), OUTLINE, 0.8)
        c.lines(SCORPION_DARK, [(5, 28.5), (2, 27), (0.5, 29)], 1.2)
        _x_eye(c, (22, 27.5))
        _x_eye(c, (26, 27.5))
        surface.blit(c.finish(), (0, 0))
        return

    phase = frame / 4 * math.tau
    # Legs: four pairs alternating like a real scuttle.
    for index, x in enumerate((9.0, 13.0, 17.0, 21.0)):
        swing = math.sin(phase + index * math.pi / 2) * 2.4
        lift = max(0.0, math.cos(phase + index * math.pi / 2)) * 1.2
        knee = (x + swing * 0.5, 24.5 - lift)
        c.lines(OUTLINE, [(x, 24), knee, (x + swing - 1.5, 31.2 - lift)], 1.6)
        c.lines(SCORPION_DARK, [(x, 24), knee, (x + swing - 1.5, 31.2 - lift)], 0.8)
    # Tail: segments curling over the back, swaying.
    sway = math.sin(phase) * 3
    tail = [(8, 23), (4.5, 19.5), (3.5 + sway * 0.3, 14.5), (5.5 + sway * 0.6, 10), (10 + sway, 7.5)]
    for index, point in enumerate(tail):
        c.circle(SCORPION if index % 2 else SCORPION_LIGHT, point, 3.0 - index * 0.25, OUTLINE, 0.7)
    tip = tail[-1]
    c.polygon(STINGER, [(tip[0] + 1, tip[1] - 2.2), (tip[0] + 6, tip[1] + 0.5), (tip[0] + 1.5, tip[1] + 2.4)], OUTLINE, 0.6)
    # Body.
    c.ellipse(SCORPION, (6.5, 18.5, 20, 9), OUTLINE, 0.9)
    c.ellipse(SCORPION_LIGHT, (9, 19.5, 13, 3.5))
    for x in (11.5, 15.5, 19.5):
        c.line(SCORPION_DARK, (x, 19.8), (x - 0.8, 26.5), 0.7)
    # Pincers open and close.
    pinch = (math.sin(phase * 2) + 1) * 0.9
    for y, arm_y in ((16.5, 20.0), (25.5, 24.0)):
        c.capsule(SCORPION, (24, arm_y), (27.5, y), 1.4, OUTLINE, 0.6)
        c.polygon(SCORPION_DARK, [(26.5, y - 2.4 - pinch), (31.5, y - 1.2), (29, y), (31.5, y + 1.2), (26.5, y + 2.4 + pinch)], OUTLINE, 0.6)
    # Head and eyes.
    c.circle(SCORPION, (25, 22), 4.2, OUTLINE, 0.8)
    _angry_eye(c, (24.8, 20.8), 0.8)
    _angry_eye(c, (27.4, 21.2), 0.8)
    c.line(OUTLINE, (23.2, 18.6), (26, 19.6), 0.6)
    surface.blit(c.finish(), (0, 0))


# --- Haunted clay jar --------------------------------------------------------------
def paint_clay_jar(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 32, fringe=OUTLINE)
    if animation == "squashed":
        for shard, color in (
            ([(3, 31), (9, 26), (12, 31)], TERRACOTTA),
            ([(12, 31), (15, 25), (19, 27), (19, 31)], TERRACOTTA_LIGHT),
            ([(20, 31), (23, 26.5), (29, 31)], TERRACOTTA),
        ):
            c.polygon(color, shard, OUTLINE, 0.7)
        c.line(AZULEJO, (13.5, 29), (18.5, 29), 1.0)
        c.circle(EYE_GLOW, (16, 22), 1.4)
        surface.blit(c.finish(), (0, 0))
        return

    if animation == "jump":
        width, height = 16.0, 22.0
    elif animation == "crouch":
        width, height = 23.0, 15.0
    else:
        breathe = math.sin(frame / 2 * math.tau)
        width, height = 19.0 + breathe * 0.8, 19.0 - breathe * 0.8
    cx = 16.0
    bottom = 31.5
    top = bottom - height
    # Body: a round belly and a narrow neck with a lip.
    c.ellipse(TERRACOTTA, (cx - width / 2, top + height * 0.22, width, height * 0.78), OUTLINE, 0.9)
    c.rect(TERRACOTTA, (cx - width * 0.24, top + 1.4, width * 0.48, height * 0.3), outline=OUTLINE, width=0.8)
    c.ellipse(TERRACOTTA_LIGHT, (cx - width * 0.34, top - 0.2, width * 0.68, 3.2), OUTLINE, 0.8)
    c.ellipse(TERRACOTTA_DARK, (cx - width * 0.22, top + 0.3, width * 0.44, 1.6))
    c.ellipse(TERRACOTTA_LIGHT, (cx - width * 0.36, top + height * 0.34, width * 0.26, height * 0.24))
    # Azulejo band with little diamonds.
    band_y = top + height * 0.66
    c.rect(AZULEJO, (cx - width * 0.46, band_y, width * 0.92, 3.4))
    for k in range(-2, 3):
        dx = k * width * 0.18
        c.polygon(AZULEJO_LIGHT, [(cx + dx, band_y + 0.4), (cx + dx + 1.4, band_y + 1.7), (cx + dx, band_y + 3.0), (cx + dx - 1.4, band_y + 1.7)])
    # Glowing haunted eyes.
    eye_y = top + height * 0.46
    for dx in (1.2, 6.0):
        c.circle((60, 20, 16), (cx + dx, eye_y), 2.2)
        c.circle(EYE_GLOW, (cx + dx, eye_y), 1.3)
    c.line(OUTLINE, (cx - 0.4, eye_y - 3.0), (cx + 3.0, eye_y - 1.8), 0.7)
    c.line(OUTLINE, (cx + 7.6, eye_y - 3.0), (cx + 4.4, eye_y - 1.8), 0.7)
    surface.blit(c.finish(), (0, 0))


# --- Jinn wisp --------------------------------------------------------------------
def paint_jinn(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 32, fringe=OUTLINE)
    phase = frame / 4 * math.tau
    if animation == "squashed":
        c.ellipse(JINN_DARK, (6, 20, 20, 9), OUTLINE, 0.8)
        _x_eye(c, (14, 24))
        _x_eye(c, (20, 24))
        surface.blit(c.finish(), (0, 0))
        return
    # Wispy tail curling beneath.
    tail = []
    for k in range(6):
        t = k / 5
        tail.append((15 - t * 8 + math.sin(phase + t * 3.0) * 2.5 * t, 18 + t * 12))
    c.tapered(OUTLINE, tail, 5.4, 1.4)
    c.tapered(JINN_DARK, tail, 4.4, 0.6)
    # Flame tuft on top flickering.
    flick = math.sin(phase * 2) * 1.5
    c.polygon(JINN, [(10, 11), (14 + flick, 1.5), (16.5, 8), (19 - flick, 3), (22, 11)], OUTLINE, 0.8)
    c.polygon(JINN_LIGHT, [(13, 10), (14.5 + flick * 0.5, 5), (17, 9.5)])
    # Head.
    c.circle(JINN, (16, 15), 8.2, OUTLINE, 0.9)
    c.circle(JINN_LIGHT, (13, 12), 3.6)
    for dx in (14.5, 20.0):
        c.circle(WHITE, (dx, 15), 2.3, OUTLINE, 0.5)
        c.circle(OUTLINE, (dx + 0.7, 15.3), 1.1)
        c.circle(WHITE, (dx + 0.3, 14.4), 0.4)
    c.lines(OUTLINE, [(14, 19.4), (16.5, 20.6), (19.5, 19.2)], 0.6)  # grin
    surface.blit(c.finish(), (0, 0))


# --- Hedgehog -----------------------------------------------------------------------
def paint_hedgehog(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 32, fringe=OUTLINE)
    if animation in ("curled", "squashed"):
        c.circle(HEDGEHOG, (16, 23), 8.5, OUTLINE, 0.9)
        for k in range(12):
            a = math.tau * k / 12 + 0.3
            base = (16 + math.cos(a) * 7, 23 + math.sin(a) * 7)
            tip = (16 + math.cos(a) * 12, 23 + math.sin(a) * 12)
            side = (-math.sin(a) * 1.8, math.cos(a) * 1.8)
            c.polygon(HEDGEHOG_SPINE, [(base[0] + side[0], base[1] + side[1]), tip, (base[0] - side[0], base[1] - side[1])], OUTLINE, 0.5)
        c.circle(HEDGEHOG, (16, 23), 7.0)
        if animation == "squashed":
            _x_eye(c, (18, 22))
        surface.blit(c.finish(), (0, 0))
        return
    phase = frame / 4 * math.tau
    bob = abs(math.sin(phase)) * 0.8
    # Feet.
    for index, x in enumerate((10.0, 15.0, 19.0)):
        dx = math.sin(phase + index * 2.1) * 1.4
        c.ellipse(OUTLINE, (x + dx - 1.8, 28.5, 4.0, 3.0))
        c.ellipse(HEDGEHOG_FACE, (x + dx - 1.4, 28.8, 3.2, 2.2))
    # Spines along the back.
    for k in range(9):
        a = math.pi * (1.02 + 0.9 * k / 8)
        base = (15 + math.cos(a) * 8, 23 - bob + math.sin(a) * 7)
        tip = (15 + math.cos(a) * 13.5 - 1.0, 23 - bob + math.sin(a) * 12)
        side = (-math.sin(a) * 2.0, math.cos(a) * 2.0)
        c.polygon(HEDGEHOG_SPINE, [(base[0] + side[0], base[1] + side[1]), tip, (base[0] - side[0], base[1] - side[1])], OUTLINE, 0.6)
    c.ellipse(HEDGEHOG, (5, 15 - bob, 21, 15), OUTLINE, 0.9)
    # Face.
    c.ellipse(HEDGEHOG_FACE, (18, 19 - bob, 11, 9), OUTLINE, 0.8)
    c.circle(OUTLINE, (29, 23.2 - bob), 1.4)
    c.circle(OUTLINE, (22.8, 21.5 - bob), 1.2)
    c.circle(WHITE, (23.2, 21.0 - bob), 0.4)
    c.circle((240, 150, 150), (24.5, 24.5 - bob), 1.0)
    surface.blit(c.finish(), (0, 0))


# --- Bat ------------------------------------------------------------------------------
def paint_bat(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 32, fringe=OUTLINE)
    if animation == "hang":
        breathe = frame * 0.6
        # Upside down, wings wrapped: feet at the top of the frame.
        c.line(OUTLINE, (14, 0), (14, 3), 1.2)
        c.line(OUTLINE, (18, 0), (18, 3), 1.2)
        c.ellipse(BAT_WING, (9 - breathe * 0.3, 3, 14 + breathe * 0.6, 17), OUTLINE, 0.9)
        c.ellipse(BAT, (11, 5, 10, 12))
        c.circle(BAT, (16, 19), 4.4, OUTLINE, 0.8)
        c.polygon(BAT, [(12.5, 21.5), (11.5, 25.5), (14.5, 22.5)], OUTLINE, 0.5)
        c.polygon(BAT, [(19.5, 21.5), (20.5, 25.5), (17.5, 22.5)], OUTLINE, 0.5)
        c.line(OUTLINE, (13.8, 18.4), (15.2, 18.4), 0.6)
        c.line(OUTLINE, (16.8, 18.4), (18.2, 18.4), 0.6)
        surface.blit(c.finish(), (0, 0))
        return
    if animation == "squashed":
        c.ellipse(BAT, (8, 24, 16, 6), OUTLINE, 0.8)
        c.polygon(BAT_WING, [(8, 26), (1, 29), (8, 29)], OUTLINE, 0.5)
        c.polygon(BAT_WING, [(24, 26), (31, 29), (24, 29)], OUTLINE, 0.5)
        _x_eye(c, (14, 26))
        _x_eye(c, (18, 26))
        surface.blit(c.finish(), (0, 0))
        return
    flap = math.sin(frame / 4 * math.tau)
    wing_y = 14 - flap * 9
    for side in (-1, 1):
        root = (16 + side * 3, 16)
        elbow = (16 + side * 9, wing_y)
        tip = (16 + side * 15, wing_y + 3 + flap * 2)
        membrane = [root, elbow, tip, (16 + side * 12, 19 + flap), (16 + side * 8, 17.5 + flap), (16 + side * 5, 19)]
        c.polygon(BAT_WING, membrane, OUTLINE, 0.8)
        c.line(BAT_DARK, root, elbow, 0.7)
        c.line(BAT_DARK, elbow, tip, 0.6)
    c.ellipse(BAT, (11.5, 12, 9, 10), OUTLINE, 0.9)
    c.polygon(BAT, [(12.5, 13.5), (12, 8.5), (15, 12)], OUTLINE, 0.5)
    c.polygon(BAT, [(19.5, 13.5), (20, 8.5), (17, 12)], OUTLINE, 0.5)
    for dx in (14.2, 17.8):
        c.circle((255, 220, 120), (dx, 15.5), 1.2)
        c.circle(OUTLINE, (dx + 0.3, 15.6), 0.5)
    c.polygon(WHITE, [(14.8, 18.6), (15.4, 20.2), (16.0, 18.6)])
    c.polygon(WHITE, [(16.4, 18.6), (17.0, 20.2), (17.6, 18.6)])
    surface.blit(c.finish(), (0, 0))


# --- Ghul ----------------------------------------------------------------------------
def paint_ghul(surface: pygame.Surface, animation: str, frame: int) -> None:
    c = Canvas(32, 40, fringe=OUTLINE)
    phase = frame / 4 * math.tau
    bob = math.sin(phase) * 1.0
    # Tattered robe hem.
    hem = []
    for k in range(7):
        x = 7 + k * 3
        hem.append((x, 36 + bob + (2.5 if k % 2 else 0) + math.sin(phase + k) * 1.2))
    body = [(10, 14 + bob), (22, 14 + bob), (25.5, 30 + bob)] + list(reversed(hem)) + [(6.5, 30 + bob)]
    c.polygon(GHUL, body, OUTLINE, 0.9)
    c.polygon(GHUL_SHADE, [(10, 16 + bob), (13, 16 + bob), (12, 34 + bob), (8, 33 + bob)])
    # Hood.
    c.ellipse(GHUL, (7.5, 3 + bob, 17, 17), OUTLINE, 0.9)
    c.ellipse((34, 30, 44), (11, 7 + bob, 11.5, 11))
    if animation == "shy":
        # Hands over its face.
        for dx in (12.5, 19.0):
            c.ellipse(GHUL, (dx - 3, 9.5 + bob, 6, 6.5), OUTLINE, 0.7)
            for f in range(3):
                c.line(GHUL_SHADE, (dx - 1.6 + f * 1.4, 10 + bob), (dx - 1.8 + f * 1.4, 13 + bob), 0.4)
        c.circle(GHUL_EYES, (22.5, 13 + bob), 0.8)
    else:
        for dx in (14.0, 19.0):
            c.ellipse(GHUL_EYES, (dx - 1.2, 11 + bob, 2.6, 3.2))
        c.lines(GHUL_EYES, [(14, 16.5 + bob), (15.5, 15.6 + bob), (17, 16.5 + bob), (18.5, 15.6 + bob), (20, 16.5 + bob)], 0.5)
        # Reaching claws.
        reach = math.sin(phase) * 1.5
        c.capsule(GHUL, (21, 18 + bob), (28 + reach, 21 + bob), 1.6, OUTLINE, 0.7)
        for k in range(3):
            c.line(OUTLINE, (28 + reach, 20 + bob + k), (30.5 + reach, 19.5 + bob + k * 1.4), 0.5)
    surface.blit(c.finish(), (0, 0))
