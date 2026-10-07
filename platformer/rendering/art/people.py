"""People of al-Andalus, drawn on the prince's own skeletal rig.

The thief's servants - level 1's masked Moon Troupe, level 2's Gilded
Thieves - are real people like Amir: the same bones, joints and proportions
(see ``rendering/art/prince.py``), rendered on the same supersampled canvas,
but in their own clothes and headwear.

A ``Costume`` chooses colours and two shapes: the torso (``dress``, ``vest``,
``cloak``, ``scale``, ``robe``, ``apron`` or ``tunic``) and the head
(``dancer``, ``juggler``, ``weaver``, ``veiled``, ``firebraid``, ``elder``,
``saqqa``, ``fisher`` or ``crone``).
Poses are ordinary ``prince.Pose`` values, so every animation below is just
a function from a frame index to joint angles.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, shade
from rendering.art.prince import (
    FOREARM, FRAME, GROUND_Y, HEAD_RADIUS, HIP_Y, OUTLINE, SHIN, THIGH, TORSO, UPPER_ARM,
    Pose, PrincePalette, Skeleton, _arm, _eye, _leg, _mouth, skeleton,
)

MASK_GOLD: Color = (236, 190, 74)
BEARD: Color = (242, 240, 232)
BEARD_SHADE: Color = (196, 192, 184)
RUBY: Color = (214, 38, 62)
MASK_SHADE: Color = (176, 124, 40)
COIN: Color = (250, 214, 110)


@dataclass(frozen=True)
class Costume:
    name: str
    skin: Color
    top: Color
    top_shade: Color
    trim: Color
    accent: Color
    lower: Color
    lower_shade: Color
    shoe: Color
    hair: Color
    body: str        # "dress" | "vest" | "cloak" | "scale" | "robe" | "apron" | "tunic"
    head: str        # "dancer" | "juggler" | "weaver" | "veiled" | "firebraid" | "elder" | "saqqa" | "fisher" | "crone"
    eye: Color = (34, 22, 24)
    glow: Color | None = None
    mask: bool = True

    def palette(self) -> PrincePalette:
        """Adapter so the prince's limb painters can draw this costume's limbs."""
        return PrincePalette(
            robe=self.top, robe_shade=self.top_shade, trim=self.trim, sash=self.accent,
            trousers=self.lower, skin=self.skin, turban=self.hair, turban_shade=self.hair,
            jewel=self.accent, plume=self.trim, slipper=self.shoe, eye=self.eye,
        )


DANCER = Costume(
    "dancer", skin=(222, 170, 124), top=(214, 72, 92), top_shade=(160, 44, 66), trim=(250, 214, 110),
    accent=(250, 150, 60), lower=(252, 214, 196), lower_shade=(214, 168, 150), shoe=(214, 72, 92),
    hair=(46, 26, 30), body="dress", head="dancer",
)
JUGGLER = Costume(
    "juggler", skin=(190, 134, 92), top=(246, 238, 220), top_shade=(206, 196, 176), trim=(236, 190, 74),
    accent=(36, 124, 84), lower=(122, 60, 110), lower_shade=(86, 40, 80), shoe=(150, 60, 40),
    hair=(40, 26, 22), body="vest", head="juggler",
)
WEAVER = Costume(
    "weaver", skin=(206, 156, 116), top=(60, 70, 168), top_shade=(38, 42, 112), trim=(214, 230, 255),
    accent=(80, 214, 230), lower=(86, 112, 206), lower_shade=(56, 72, 150), shoe=(34, 34, 96),
    hair=(24, 20, 40), body="cloak", head="weaver", eye=(120, 250, 250), glow=(90, 230, 255),
)

# Level 2: the Gilded Thieves of the Amber Market.
TARIQ = Costume(
    "tariq", skin=(176, 116, 78), top=(236, 226, 206), top_shade=(196, 184, 162), trim=(222, 178, 84),
    accent=(176, 116, 56), lower=(62, 54, 86), lower_shade=(40, 34, 60), shoe=(92, 58, 38),
    hair=(46, 58, 124), body="scale", head="veiled", mask=False,
)
SAMIRA = Costume(
    "samira", skin=(206, 146, 104), top=(206, 40, 52), top_shade=(146, 22, 38), trim=(252, 204, 92),
    accent=(252, 134, 40), lower=(255, 176, 66), lower_shade=(214, 114, 40), shoe=(146, 22, 38),
    hair=(34, 20, 22), body="dress", head="firebraid", mask=False,
)
HAKIM = Costume(
    "hakim", skin=(166, 108, 74), top=(240, 232, 214), top_shade=(202, 192, 172), trim=(224, 182, 84),
    accent=(42, 124, 84), lower=(228, 220, 202), lower_shade=(190, 180, 160), shoe=(122, 72, 42),
    hair=(40, 146, 96), body="robe", head="elder", mask=False,
)
# Level 4: the River-Thieves of the Singing Aqueduct.
YUSUF = Costume(
    "yusuf", skin=(186, 124, 84), top=(242, 236, 222), top_shade=(204, 194, 174), trim=(232, 186, 84),
    accent=(146, 90, 50), lower=(58, 70, 128), lower_shade=(40, 48, 92), shoe=(150, 50, 40),
    hair=(244, 238, 226), body="apron", head="saqqa", mask=False,
)
NUR = Costume(
    "nur", skin=(204, 146, 104), top=(40, 150, 140), top_shade=(26, 106, 100), trim=(240, 220, 160),
    accent=(214, 184, 120), lower=(222, 200, 152), lower_shade=(184, 160, 116), shoe=(190, 130, 92),
    hair=(52, 92, 170), body="tunic", head="fisher", mask=False,
)
HAMIDA = Costume(
    "hamida", skin=(178, 122, 90), top=(40, 46, 108), top_shade=(26, 30, 74), trim=(214, 224, 244),
    accent=(70, 196, 200), lower=(58, 66, 140), lower_shade=(38, 44, 98), shoe=(40, 34, 50),
    hair=(236, 236, 240), body="cloak", head="crone", mask=False,
)
LONG_ROBES = ("cloak", "robe")


# --- torso shapes ---------------------------------------------------------------------------
def _axes(sk: Skeleton, pose: Pose):  # noqa: ANN202
    lean = math.radians(pose.lean)
    ux, uy = math.sin(lean), -math.cos(lean)
    rx, ry = -uy, ux

    def at(forward: float, up: float, base: tuple[float, float] = sk.hip) -> tuple[float, float]:
        return base[0] + rx * forward + ux * up, base[1] + ry * forward + uy * up

    return at


def _dress(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    # Two layers of skirt flaring from the hips to mid-calf, swinging with the dance.
    for layer, (color, spread, length) in enumerate(((k.lower, 8.4, 10.2), (k.top, 7.2, 8.6))):
        waist_back, waist_front = at(-3.4, 1.4), at(3.4, 1.4)
        def hem(forward: float) -> tuple[float, float]:
            base = at(forward * 0.35, 0.0)
            return (base[0] + forward - math.sin(swing) * length * 0.6,
                    base[1] + math.cos(swing * 0.7) * length)
        points = [waist_back, waist_front]
        steps = 7
        for s in range(steps + 1):
            u = 1 - s / steps
            forward = -spread + u * spread * 2
            points.append(hem(forward) if s % 2 == 0 else (hem(forward)[0], hem(forward)[1] - 0.9))
        c.polygon(color if layer else shade(color, -0.05), points, OUTLINE, 0.8)
        if layer == 1:
            for s in range(0, steps + 1, 2):
                u = 1 - s / steps
                c.circle(k.trim, hem(-spread + u * spread * 2), 0.8)
    # Fitted bodice and a jingling coin belt.
    bodice = [at(-3.0, TORSO - 0.6), at(3.2, TORSO - 0.6), at(3.7, TORSO - 3.2), at(2.8, 1.6), at(-3.2, 1.6), at(-3.8, TORSO - 3.2)]
    c.polygon(k.top, bodice, OUTLINE, 0.9)
    c.polygon(k.top_shade, [at(-3.0, TORSO - 0.6), at(-0.6, TORSO - 0.6), at(-1.2, 1.6), at(-3.2, 1.6), at(-3.8, TORSO - 3.2)])
    c.polygon(k.trim, [at(-1.0, TORSO - 0.4), at(2.6, TORSO - 0.4), at(1.0, TORSO - 2.4)])
    belt = [at(-3.9, 2.6), at(3.6, 2.6), at(3.8, 0.8), at(-4.0, 0.8)]
    c.polygon(k.accent, belt, OUTLINE, 0.6)
    for s in range(6):
        x, y = at(-3.4 + s * 1.3, 0.6)
        c.circle(COIN, (x, y + 0.8 + (s % 2) * 0.4), 0.7)


def _vest(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    # A loose shirt to the hips...
    hem_back = (at(-4.6, 0)[0] - math.sin(swing) * 2.0, at(-4.6, 0)[1] + math.cos(swing) * 2.4)
    hem_front = (at(4.4, 0)[0] - math.sin(swing) * 2.0, at(4.4, 0)[1] + math.cos(swing) * 2.4)
    shirt = [at(-3.8, TORSO - 0.4), at(3.9, TORSO - 0.4), at(4.6, TORSO - 3.4), at(4.2, 1.0), hem_front, hem_back, at(-4.2, 1.0), at(-4.4, TORSO - 3.4)]
    c.polygon(k.top, shirt, OUTLINE, 0.9)
    # ...an open striped vest over it, and a wide sash.
    vest_back = [at(-4.2, TORSO - 0.4), at(-0.2, TORSO - 0.6), at(0.6, 1.4), at(-4.4, 1.4)]
    c.polygon(k.accent, vest_back, OUTLINE, 0.7)
    vest_front = [at(1.4, TORSO - 0.8), at(4.0, TORSO - 0.6), at(4.6, TORSO - 3.2), at(4.2, 1.4), at(2.4, 1.4)]
    c.polygon(k.accent, vest_front, OUTLINE, 0.7)
    for s in range(3):
        c.line(k.trim, at(-3.8 + s * 1.3, TORSO - 0.8), at(-3.6 + s * 1.3, 1.6), 0.55)
    c.line(k.trim, at(1.6, TORSO - 1.0), at(2.6, 1.4), 0.7)
    sash = [at(-4.4, 2.6), at(4.3, 2.6), at(4.3, 0.4), at(-4.4, 0.4)]
    c.polygon((200, 60, 44), sash, OUTLINE, 0.6)
    knot = at(4.0, 1.4)
    c.capsule((200, 60, 44), knot, (knot[0] + 1.6, knot[1] + 3.4), 0.9, OUTLINE, 0.5)


def _cloak(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    length = HIP_Y - sk.hip[1] + (GROUND_Y - HIP_Y) - 0.6
    def hem(forward: float) -> tuple[float, float]:
        base = at(forward * 0.4, 0)
        wave = math.sin(forward * 0.9 + pose.hem * 0.05) * 0.8
        return base[0] + forward - math.sin(swing) * length * 0.5, base[1] + length * 0.95 + wave
    # The long cloak, open at the front over a lighter robe.
    inner = [at(0.6, TORSO - 1.0), at(3.4, TORSO - 1.4), hem(4.8), hem(0.8)]
    c.polygon(k.lower, inner, OUTLINE, 0.7)
    outer = [at(-3.8, TORSO - 0.2), at(1.2, TORSO + 0.2), at(1.6, TORSO - 3.0), hem(1.8), hem(-2.0), hem(-6.4), at(-4.8, TORSO - 3.4)]
    c.polygon(k.top, outer, OUTLINE, 0.9)
    c.polygon(k.top_shade, [at(-3.8, TORSO - 0.2), at(-1.4, TORSO), hem(-2.8), hem(-6.4), at(-4.8, TORSO - 3.4)])
    c.line(k.trim, hem(-6.2), hem(1.8), 0.8)
    c.line(k.trim, at(1.2, TORSO + 0.2), hem(1.8), 0.6)
    # Silver crescents embroidered down the cloak.
    for s in range(3):
        x, y = at(-2.4, TORSO - 3.0 - s * 3.2)
        c.ring(k.trim, (x, y), 1.1, 0.35)
        c.circle(k.top, (x + 0.5, y - 0.3), 0.85)


def _scale(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    # A long tunic to mid-thigh...
    hem_back = (at(-4.8, 0)[0] - math.sin(swing) * 2.6, at(-4.8, 0)[1] + math.cos(swing) * 4.4)
    hem_front = (at(4.6, 0)[0] - math.sin(swing) * 2.6, at(4.6, 0)[1] + math.cos(swing) * 4.4)
    tunic = [at(-3.8, TORSO - 0.4), at(3.9, TORSO - 0.4), at(4.6, TORSO - 3.4), at(4.4, 0.6), hem_front, hem_back,
             at(-4.4, 0.6), at(-4.4, TORSO - 3.4)]
    c.polygon(k.top, tunic, OUTLINE, 0.9)
    # ...under a coat of bronze scales, with a pauldron at the shoulder.
    coat = [at(-4.0, TORSO - 0.6), at(3.8, TORSO - 0.6), at(4.4, TORSO - 3.2), at(4.0, 1.8), at(-4.2, 1.8), at(-4.4, TORSO - 3.2)]
    c.polygon(k.accent, coat, OUTLINE, 0.8)
    for row in range(4):
        for col in range(4):
            x, y = at(-3.1 + col * 2.1 + (row % 2) * 1.0, TORSO - 1.9 - row * 2.1)
            c.circle(shade(k.accent, 0.22), (x, y), 0.8)
            c.circle(shade(k.accent, -0.2), (x, y + 0.55), 0.45)
    sash = [at(-4.4, 2.2), at(4.3, 2.2), at(4.3, 0.1), at(-4.4, 0.1)]
    c.polygon((170, 38, 44), sash, OUTLINE, 0.6)
    c.line(k.trim, at(-4.2, 1.2), at(4.2, 1.2), 0.5)
    c.ellipse(shade(k.accent, 0.1), (sk.shoulder[0] - 3.0, sk.shoulder[1] - 1.2, 6.0, 3.6), OUTLINE, 0.6)


def _robe(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    length = HIP_Y - sk.hip[1] + (GROUND_Y - HIP_Y) - 0.6

    def hem(forward: float) -> tuple[float, float]:
        base = at(forward * 0.4, 0)
        wave = math.sin(forward * 0.9 + pose.hem * 0.05) * 0.6
        return base[0] + forward - math.sin(swing) * length * 0.45, base[1] + length * 0.97 + wave

    # A long closed robe to the ankles, with a gold band at the hem...
    robe = [at(-3.8, TORSO - 0.2), at(3.8, TORSO - 0.2), at(4.4, TORSO - 3.2), hem(5.4), hem(0.0), hem(-5.8), at(-4.6, TORSO - 3.2)]
    c.polygon(k.top, robe, OUTLINE, 0.9)
    c.polygon(k.top_shade, [at(-3.8, TORSO - 0.2), at(-1.2, TORSO), hem(-2.4), hem(-5.8), at(-4.6, TORSO - 3.2)])
    c.line(k.trim, hem(-5.6), hem(5.2), 0.8)
    # ...and a sleeveless green waistcoat stitched with gold.
    coat_back = [at(-4.2, TORSO - 0.3), at(-0.4, TORSO - 0.4), at(0.2, -1.2), at(-4.6, -1.2)]
    coat_front = [at(1.2, TORSO - 0.6), at(4.0, TORSO - 0.5), at(4.6, TORSO - 3.0), at(4.4, -1.2), at(2.0, -1.2)]
    c.polygon(k.accent, coat_back, OUTLINE, 0.7)
    c.polygon(k.accent, coat_front, OUTLINE, 0.7)
    c.line(k.trim, at(1.3, TORSO - 0.8), at(2.1, -1.0), 0.5)
    c.line(k.trim, at(-0.5, TORSO - 0.6), at(0.1, -1.0), 0.5)
    for s in range(3):
        c.circle(k.trim, at(-2.6, TORSO - 2.2 - s * 2.4), 0.5)
    c.polygon(shade(k.accent, -0.25), [at(-4.6, 1.6), at(4.5, 1.6), at(4.5, 0.2), at(-4.6, 0.2)], OUTLINE, 0.5)


def _apron(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    """The water-seller: a loose shirt over a round belly, a leather apron, brass cups on the sash."""
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)

    def swung(point: tuple[float, float], amount: float) -> tuple[float, float]:
        return point[0] - math.sin(swing) * amount, point[1] + math.cos(swing) * amount * 0.4

    shirt = [at(-3.8, TORSO - 0.4), at(3.4, TORSO - 0.4), at(5.0, TORSO - 3.0), at(6.6, 3.6), swung(at(5.8, -0.6), 2.0),
             swung(at(-4.8, -0.6), 2.0), at(-4.8, 1.4), at(-4.4, TORSO - 3.4)]
    c.polygon(k.top, shirt, OUTLINE, 0.9)
    c.polygon(k.top_shade, [at(-3.8, TORSO - 0.4), at(-1.4, TORSO - 0.4), at(-1.8, 1.0), swung(at(-4.8, -0.6), 2.0),
                            at(-4.8, 1.4), at(-4.4, TORSO - 3.4)])
    # A leather apron from the chest to the knees, swinging as he waddles.
    apron = [at(0.8, TORSO - 1.2), at(4.4, TORSO - 1.4), at(6.2, 3.0), swung(at(5.6, -6.2), 3.0), swung(at(0.6, -6.2), 3.0), at(0.4, 1.0)]
    c.polygon(k.accent, apron, OUTLINE, 0.8)
    c.lines(shade(k.accent, -0.25), [at(1.6, TORSO - 2.4), at(2.0, 1.2), swung(at(1.6, -5.4), 3.0)], 0.4)
    c.line(k.accent, at(1.0, TORSO - 1.0), at(-1.6, TORSO + 0.4), 0.7)
    # A red sash, and the brass cups he clinks to call his customers.
    c.polygon((196, 52, 48), [at(-4.8, 2.4), at(6.2, 2.8), at(6.2, 0.8), at(-4.8, 0.4)], OUTLINE, 0.6)
    for s in range(3):
        cup = at(-3.8 + s * 1.9, -0.4 - (s % 2) * 0.5)
        c.circle((232, 186, 84), cup, 1.0, OUTLINE, 0.35)
        c.circle((255, 232, 160), (cup[0] - 0.3, cup[1] - 0.3), 0.4)


def _tunic(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    """The fisher: a short sleeveless tunic, a rope belt, a necklace of shells."""
    at = _axes(sk, pose)
    swing = math.radians(pose.hem)
    hem_back = (at(-4.6, -2.4)[0] - math.sin(swing) * 2.6, at(-4.6, -2.4)[1] + math.cos(swing) * 1.4)
    hem_front = (at(4.8, -2.4)[0] - math.sin(swing) * 2.6, at(4.8, -2.4)[1] + math.cos(swing) * 1.4)
    tunic = [at(-3.6, TORSO - 0.4), at(3.6, TORSO - 0.4), at(4.2, TORSO - 3.2), at(4.4, 0.4), hem_front, hem_back,
             at(-4.4, 0.4), at(-4.2, TORSO - 3.2)]
    c.polygon(k.top, tunic, OUTLINE, 0.9)
    c.polygon(k.top_shade, [at(-3.6, TORSO - 0.4), at(-1.2, TORSO - 0.4), at(-1.4, 0.4), hem_back, at(-4.4, 0.4), at(-4.2, TORSO - 3.2)])
    # A band of woven waves at the hem.
    c.line(k.trim, hem_back, hem_front, 0.7)
    for s in range(4):
        u = (s + 0.5) / 4
        x = hem_back[0] + (hem_front[0] - hem_back[0]) * u
        y = hem_back[1] + (hem_front[1] - hem_back[1]) * u
        c.circle(k.trim, (x, y - 0.9), 0.45)
    c.lines(k.accent, [at(-4.4, 1.8), at(0.0, 1.6), at(4.4, 2.0)], 0.8)
    knot = at(3.6, 1.6)
    c.capsule(k.accent, knot, (knot[0] + 0.8, knot[1] + 3.0), 0.5)
    for s in range(5):
        c.circle((250, 244, 230), at(-1.4 + s * 1.0, TORSO - 1.4 - abs(s - 2) * 0.35), 0.5)


TORSOS: dict[str, Callable[[Canvas, Skeleton, Pose, Costume], None]] = {
    "dress": _dress, "vest": _vest, "cloak": _cloak, "scale": _scale, "robe": _robe,
    "apron": _apron, "tunic": _tunic,
}


# --- heads ------------------------------------------------------------------------------------
def _face(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> tuple[float, float]:
    hx, hy = sk.head
    p = k.palette()
    c.capsule(k.skin, sk.shoulder, (hx - 0.4, hy + 2.0), 1.6, OUTLINE, 0.8)
    nose = (hx + HEAD_RADIUS - 0.1, hy + 1.0)
    c.circle(OUTLINE, (hx, hy), HEAD_RADIUS + 0.9)
    c.circle(OUTLINE, nose, 1.8)
    c.circle(k.skin, (hx, hy), HEAD_RADIUS)
    c.circle(k.skin, nose, 1.1)
    c.circle(shade(k.skin, -0.12), (hx - 2.2, hy + 1.2), 1.4)
    c.circle((236, 140, 130), (hx + 2.3, hy + 2.5), 1.0)
    _mouth(c, (hx + 3.4, hy + 3.2), p, pose.mouth)
    return hx, hy


def _mask(c: Canvas, hx: float, hy: float) -> None:
    """The troupe's golden half-mask, with a swept wing at the temple."""
    points = [(hx + 5.6, hy - 1.0), (hx + 5.2, hy + 1.2), (hx + 2.4, hy + 1.6), (hx - 0.6, hy + 0.8),
              (hx - 3.4, hy - 1.6), (hx - 2.2, hy - 2.6), (hx + 1.0, hy - 2.0)]
    c.polygon(MASK_GOLD, points, OUTLINE, 0.6)
    c.line(MASK_SHADE, (hx - 2.8, hy - 1.6), (hx + 0.4, hy + 0.9), 0.5)
    c.circle((255, 246, 200), (hx + 0.6, hy - 1.2), 0.45)


def _eyes_and_brow(c: Canvas, hx: float, hy: float, pose: Pose, k: Costume) -> None:
    p = k.palette()
    if k.glow is not None and pose.eyes not in ("x", "closed"):
        c.circle(shade(k.glow, -0.4), (hx + 2.7, hy + 0.3), 1.7)
        c.circle(k.glow, (hx + 2.7, hy + 0.3), 1.1)
        c.circle((255, 255, 255), (hx + 3.0, hy), 0.4)
        return
    _eye(c, (hx + 2.7, hy + 0.3), p, pose.eyes)
    if pose.eyes not in ("x", "happy"):
        c.line(k.hair, (hx + 1.6, hy - 1.9), (hx + 3.8, hy - 1.6), 0.6)


def _head_dancer(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    # Dark hair swept back into a bun, a band of coins across the brow.
    c.ellipse(k.hair, (hx - 6.0, hy - 6.8, 9.4, 7.4), OUTLINE, 0.7)
    c.circle(k.hair, (hx - 6.0, hy - 3.2), 2.6, OUTLINE, 0.6)
    c.polygon(k.hair, [(hx - 5.4, hy - 1.0), (hx - 6.4, hy + 4.6), (hx - 3.0, hy + 2.0)], OUTLINE, 0.5)
    c.lines(COIN, [(hx - 4.6, hy - 4.4), (hx - 0.6, hy - 5.2), (hx + 3.6, hy - 4.4)], 0.6)
    for s in range(5):
        c.circle(COIN, (hx - 3.8 + s * 1.8, hy - 4.2 + abs(s - 2) * 0.3), 0.55)
    if k.mask:
        _mask(c, hx, hy)
    _eyes_and_brow(c, hx, hy, pose, k)
    # A jewel where the veil is pinned.
    c.circle(k.accent, (hx - 5.2, hy - 5.0), 1.0, OUTLINE, 0.4)


def _head_juggler(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    # A red felt tarbush with a black silk tassel.
    cap = [(hx - 4.8, hy - 3.4), (hx + 4.4, hy - 3.4), (hx + 3.4, hy - 9.6), (hx - 3.8, hy - 9.8)]
    c.polygon((188, 36, 44), cap, OUTLINE, 0.8)
    c.polygon((140, 24, 34), [(hx - 4.8, hy - 3.4), (hx - 1.6, hy - 3.4), (hx - 1.4, hy - 9.7), (hx - 3.8, hy - 9.8)])
    c.line((236, 190, 74), (hx - 4.6, hy - 4.6), (hx + 4.2, hy - 4.6), 0.7)
    sway = math.radians(pose.plume * 0.5)
    top = (hx - 0.2, hy - 9.8)
    end = (top[0] - 3.0 - math.sin(sway) * 1.5, top[1] + 3.2)
    c.capsule((24, 20, 26), top, end, 0.5)
    c.circle((24, 20, 26), end, 1.1)
    c.circle(k.hair, (hx - 4.4, hy - 1.4), 1.6)
    if k.mask:
        _mask(c, hx, hy)
    _eyes_and_brow(c, hx, hy, pose, k)
    # A splendid curled moustache.
    c.polygon(k.hair, [(hx + 5.4, hy + 2.0), (hx + 2.6, hy + 2.4), (hx + 1.2, hy + 3.4), (hx + 2.4, hy + 3.0), (hx + 4.4, hy + 2.8)], OUTLINE, 0.3)
    c.circle(k.hair, (hx + 1.3, hy + 2.8), 0.7)


def _head_weaver(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    # A deep hood with a pointed back, and a veil over the lower face.
    hood = [(hx + 4.6, hy - 5.6), (hx + 1.0, hy - 8.0), (hx - 4.4, hy - 7.2), (hx - 8.2, hy - 1.6),
            (hx - 7.4, hy + 5.4), (hx - 3.0, hy + 6.2), (hx - 3.2, hy + 1.0)]
    c.polygon(k.top, hood, OUTLINE, 0.9)
    c.polygon(k.top_shade, [(hx - 4.4, hy - 7.2), (hx - 8.2, hy - 1.6), (hx - 7.4, hy + 5.4), (hx - 5.4, hy + 4.0)])
    c.line(k.trim, (hx + 4.4, hy - 5.4), (hx - 2.8, hy - 7.2), 0.6)
    veil = [(hx + 6.2, hy + 0.8), (hx + 5.6, hy + 5.6), (hx + 1.0, hy + 6.4), (hx - 1.2, hy + 1.4)]
    c.polygon(k.top, veil, OUTLINE, 0.6)
    c.line(k.trim, (hx + 6.2, hy + 0.8), (hx - 1.2, hy + 1.4), 0.5)
    # A silver circlet with a moonstone.
    c.circle(k.trim, (hx + 3.6, hy - 3.4), 1.3, OUTLINE, 0.4)
    c.circle((190, 240, 255), (hx + 3.6, hy - 3.4), 0.8)
    _eyes_and_brow(c, hx, hy, pose, k)


def _kohl_eyes(c: Canvas, hx: float, hy: float, pose: Pose, k: Costume, brow: Color) -> None:
    """Eyes lined with kohl, and a brow in its own colour (hair hidden by cloth or grey)."""
    _eye(c, (hx + 2.7, hy + 0.3), k.palette(), pose.eyes)
    if pose.eyes not in ("x", "happy", "closed"):
        c.line(OUTLINE, (hx + 1.5, hy - 0.5), (hx + 4.1, hy - 0.3), 0.45)
    if pose.eyes != "x":
        c.line(brow, (hx + 1.5, hy - 2.0), (hx + 4.0, hy - 1.6), 0.8)


def _head_veiled(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    sway = math.radians(pose.plume * 0.6)
    # The turban's tail streams behind...
    tail = [(hx - 4.4, hy - 3.2), (hx - 7.0 - math.sin(sway) * 2.0, hy + 1.8), (hx - 8.2 - math.sin(sway) * 3.6, hy + 7.0)]
    c.tapered(k.hair, tail, 1.6, 0.9)
    # ...a tall indigo turban wound round and round...
    c.ellipse(k.hair, (hx - 5.8, hy - 9.4, 11.4, 8.0), OUTLINE, 0.8)
    c.polygon(shade(k.hair, 0.18), [(hx - 5.2, hy - 5.4), (hx + 5.2, hy - 7.2), (hx + 5.4, hy - 5.6), (hx - 4.6, hy - 3.6)])
    c.line(shade(k.hair, -0.25), (hx - 5.0, hy - 7.6), (hx + 4.6, hy - 5.0), 0.5)
    c.circle(k.trim, (hx + 3.4, hy - 6.0), 0.8, OUTLINE, 0.3)
    # ...and the litham drawn across nose and mouth: only the eyes are bare.
    veil = [(hx + 6.2, hy + 0.3), (hx + 5.8, hy + 5.4), (hx + 0.4, hy + 6.2), (hx - 3.0, hy + 2.8), (hx - 2.6, hy - 0.2)]
    c.polygon(k.hair, veil, OUTLINE, 0.6)
    c.line(shade(k.hair, 0.25), (hx + 6.0, hy + 1.3), (hx - 2.4, hy + 0.9), 0.45)
    _kohl_eyes(c, hx, hy, pose, k, OUTLINE)


def _head_firebraid(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    sway = math.radians(pose.plume)
    # A thick black braid swinging down her back, ringed with gold.
    braid = []
    for step in range(7):
        u = step / 6
        braid.append((hx - 4.6 - u * 3.4 - math.sin(sway) * u * 5.0, hy - 2.4 + u * 12.0))
    for index, (x, y) in enumerate(braid):
        radius = 1.9 - index * 0.14
        c.circle(k.hair, (x, y), radius, OUTLINE, 0.5)
        if index in (2, 4):
            c.ring(COIN, (x, y), radius + 0.2, 0.5)
    c.circle(k.accent, braid[-1], 1.0, OUTLINE, 0.4)
    c.ellipse(k.hair, (hx - 5.8, hy - 7.2, 10.8, 7.2), OUTLINE, 0.7)
    c.polygon(k.hair, [(hx - 1.0, hy - 4.8), (hx + 4.8, hy - 3.4), (hx + 4.4, hy - 2.2), (hx + 0.4, hy - 3.2)])
    # A gold circlet with a ruby over the brow, and a great hoop earring.
    c.lines(COIN, [(hx - 4.4, hy - 4.2), (hx + 0.2, hy - 5.0), (hx + 4.2, hy - 4.4)], 0.6)
    c.circle(RUBY, (hx + 2.6, hy - 4.6), 0.9, OUTLINE, 0.3)
    c.ring(COIN, (hx - 0.6, hy + 3.0), 1.3, 0.45)
    _eyes_and_brow(c, hx, hy, pose, k)


def _head_elder(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    hx, hy = _face(c, sk, pose, k)
    # A long white beard and moustache...
    beard = [(hx + 5.2, hy + 1.8), (hx + 5.0, hy + 5.8), (hx + 2.8, hy + 11.4), (hx + 0.6, hy + 6.6),
             (hx - 1.8, hy + 3.2), (hx - 0.8, hy + 1.2)]
    c.polygon(BEARD, beard, OUTLINE, 0.6)
    for x0 in (1.4, 2.8, 4.0):
        c.line(BEARD_SHADE, (hx + x0, hy + 3.2), (hx + x0 - 0.6, hy + 8.4 - abs(x0 - 2.8)), 0.4)
    c.polygon(BEARD, [(hx + 6.0, hy + 2.0), (hx + 3.0, hy + 1.6), (hx + 1.4, hy + 3.2), (hx + 3.6, hy + 3.4)], OUTLINE, 0.3)
    # ...under a great round green turban with a jewel and a heron's feather.
    c.ellipse(k.hair, (hx - 6.6, hy - 10.2, 13.2, 9.0), OUTLINE, 0.8)
    for step in range(3):
        c.line(shade(k.hair, -0.25), (hx - 6.0 + step * 1.0, hy - 5.6 - step * 1.3), (hx + 5.8, hy - 7.8 + step * 1.1), 0.5)
    c.circle(k.trim, (hx + 4.0, hy - 6.6), 1.1, OUTLINE, 0.4)
    c.circle(RUBY, (hx + 4.0, hy - 6.6), 0.6)
    plume = math.radians(pose.plume * 0.4)
    c.tapered(BEARD, [(hx + 3.6, hy - 7.6), (hx + 2.4 - math.sin(plume) * 2, hy - 12.0), (hx + 0.4 - math.sin(plume) * 3, hy - 14.6)], 0.8, 0.3)
    _kohl_eyes(c, hx, hy, pose, k, BEARD)


def _head_saqqa(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    """The water-seller: a white cloth wound round a red felt cap, a moustache like a pair of oars."""
    hx, hy = _face(c, sk, pose, k)
    c.circle(shade(k.skin, -0.08), (hx + 1.6, hy + 3.6), 2.6)
    c.polygon((182, 44, 48), [(hx - 3.6, hy - 6.6), (hx + 3.2, hy - 6.8), (hx + 2.4, hy - 10.8), (hx - 2.8, hy - 10.8)], OUTLINE, 0.7)
    c.ellipse(k.hair, (hx - 6.2, hy - 8.4, 12.2, 6.2), OUTLINE, 0.8)
    for step in range(3):
        c.line(shade(k.hair, -0.18), (hx - 5.6 + step * 1.2, hy - 4.0 - step * 1.4), (hx + 5.4, hy - 6.6 + step * 1.0), 0.45)
    c.circle(k.trim, (hx + 3.8, hy - 5.8), 0.8, OUTLINE, 0.3)
    _eyes_and_brow(c, hx, hy, pose, k)
    c.line(OUTLINE, (hx + 1.4, hy - 2.2), (hx + 4.0, hy - 2.0), 0.8)
    c.polygon((34, 24, 22), [(hx + 5.6, hy + 2.0), (hx + 3.0, hy + 2.6), (hx + 0.4, hy + 3.4), (hx + 1.0, hy + 2.2),
                             (hx + 3.2, hy + 1.6)], OUTLINE, 0.3)
    c.circle((34, 24, 22), (hx + 0.6, hy + 2.9), 0.8)


def _head_fisher(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    """The fisher: a blue headscarf knotted at the nape, its tails blowing, a shell at the ear."""
    hx, hy = _face(c, sk, pose, k)
    sway = math.radians(pose.plume)
    for lift in (0.0, 1.6):
        tail = [(hx - 5.4, hy - 0.6), (hx - 8.0 - math.sin(sway) * 1.6, hy + 2.6 - lift), (hx - 10.2 - math.sin(sway) * 3.2, hy + 4.6 - lift * 1.6)]
        c.tapered(k.hair if lift else shade(k.hair, -0.2), tail, 1.3, 0.6)
    scarf = [(hx + 4.6, hy - 4.4), (hx + 1.2, hy - 7.2), (hx - 4.4, hy - 6.6), (hx - 6.9, hy - 2.0), (hx - 6.2, hy + 2.8),
             (hx - 3.2, hy + 1.6), (hx + 0.8, hy - 3.0)]
    c.polygon(k.hair, scarf, OUTLINE, 0.8)
    c.polygon(shade(k.hair, -0.2), [(hx - 4.4, hy - 6.6), (hx - 6.9, hy - 2.0), (hx - 6.2, hy + 2.8), (hx - 4.6, hy + 1.6)])
    c.line(k.trim, (hx + 4.4, hy - 4.2), (hx - 4.6, hy - 5.8), 0.55)
    for s in range(3):
        c.circle(k.trim, (hx + 3.0 - s * 2.6, hy - 4.6 - s * 0.4), 0.4)
    c.circle((44, 26, 26), (hx + 3.8, hy - 3.4), 0.9)
    c.circle((250, 244, 230), (hx - 1.0, hy + 2.6), 0.8, OUTLINE, 0.3)
    _eyes_and_brow(c, hx, hy, pose, k)


def _head_crone(c: Canvas, sk: Skeleton, pose: Pose, k: Costume) -> None:
    """The rain-caller: an old woman in a starry hooded shawl fringed with silver beads."""
    hx, hy = _face(c, sk, pose, k)
    for y0 in (0.4, 2.0):
        c.line(shade(k.skin, -0.25), (hx + 1.2, hy + y0 + 0.6), (hx + 2.6, hy + y0 + 1.4), 0.3)
    c.lines(k.hair, [(hx + 3.8, hy - 3.6), (hx + 2.4, hy - 2.0), (hx + 2.8, hy - 0.4)], 0.6)
    hood = [(hx + 4.8, hy - 5.0), (hx + 0.8, hy - 8.2), (hx - 4.8, hy - 7.4), (hx - 8.2, hy - 2.0), (hx - 7.8, hy + 6.2),
            (hx - 3.2, hy + 7.0), (hx - 2.8, hy + 1.4), (hx + 1.2, hy - 3.6)]
    c.polygon(k.top, hood, OUTLINE, 0.9)
    c.polygon(k.top_shade, [(hx - 4.8, hy - 7.4), (hx - 8.2, hy - 2.0), (hx - 7.8, hy + 6.2), (hx - 5.6, hy + 4.6)])
    for x0, y0 in ((-3.0, -4.6), (-5.6, 1.0), (-1.0, -6.6)):
        c.star(k.trim, (hx + x0, hy + y0), 0.9, 4, 0.4)
    for s in range(5):
        u = s / 4
        c.circle(k.trim, (hx + 4.6 - 7.6 * u, hy - 4.4 + 6.4 * u), 0.5)    # beads along the hood's edge
    _kohl_eyes(c, hx, hy, pose, k, k.hair)


HEADS = {
    "dancer": _head_dancer, "juggler": _head_juggler, "weaver": _head_weaver,
    "veiled": _head_veiled, "firebraid": _head_firebraid, "elder": _head_elder,
    "saqqa": _head_saqqa, "fisher": _head_fisher, "crone": _head_crone,
}


# --- whole figures ---------------------------------------------------------------------------
def _draw_side(c: Canvas, pose: Pose, k: Costume) -> None:
    sk = skeleton(pose)
    p = k.palette()
    arm_root = (sk.shoulder[0], sk.shoulder[1] + 1.4)
    _arm(c, (arm_root[0] - 1.0, arm_root[1]), sk.back_elbow, sk.back_hand, p, back=True)
    if k.body not in LONG_ROBES:
        back_foot = -(pose.back_thigh - pose.back_knee) * 0.7
        front_foot = -(pose.front_thigh - pose.front_knee) * 0.7
        _leg(c, (sk.hip[0] - 1.2, sk.hip[1]), sk.back_knee, sk.back_ankle, p, True, back_foot)
        _leg(c, (sk.hip[0] + 1.2, sk.hip[1]), sk.front_knee, sk.front_ankle, p, False, front_foot)
    else:
        for ankle in (sk.back_ankle, sk.front_ankle):
            c.ellipse(k.shoe, (ankle[0] - 1.6, ankle[1] - 1.0, 4.2, 2.0), OUTLINE, 0.5)
    TORSOS[k.body](c, sk, pose, k)
    HEADS[k.head](c, sk, pose, k)
    _arm(c, (arm_root[0] + 0.6, arm_root[1]), sk.front_elbow, sk.front_hand, p, back=False, glow=pose.hand_glow)


def _draw_front(c: Canvas, pose: Pose, k: Costume) -> None:
    """Facing the viewer: used for bows and the middle of a pirouette."""
    cx = FRAME / 2
    hip_y = pose.hip_y
    p = k.palette()
    shoulder_y = hip_y - TORSO
    for side, thigh in ((-1, pose.back_thigh), (1, pose.front_thigh)):
        lift = max(0.0, math.sin(math.radians(thigh))) * 3.0
        hip = (cx + side * 1.8, hip_y)
        knee = (cx + side * 2.4, hip_y + THIGH - lift)
        ankle = (cx + side * 2.6, hip_y + THIGH + SHIN - lift * 1.6)
        if k.body not in LONG_ROBES:
            c.capsule(k.lower, hip, knee, 2.0, OUTLINE, 0.8)
            c.capsule(k.lower, knee, ankle, 1.8, OUTLINE, 0.8)
        c.ellipse(k.shoe, (ankle[0] - 2.0, ankle[1] - 0.6, 4.0, 2.0), OUTLINE, 0.6)
    for side, upper, elbow in ((-1, pose.back_upper, pose.back_elbow), (1, pose.front_upper, pose.front_elbow)):
        root = (cx + side * 4.0, shoulder_y + 1.6)
        a = math.radians(upper)
        e = (root[0] + side * math.sin(a) * UPPER_ARM, root[1] + math.cos(a) * UPPER_ARM)
        a2 = math.radians(upper + elbow)
        h = (e[0] + side * math.sin(a2) * FOREARM, e[1] + math.cos(a2) * FOREARM)
        c.capsule(k.top_shade, root, e, 1.8, OUTLINE, 0.8)
        c.capsule(k.top, e, h, 1.6, OUTLINE, 0.8)
        c.circle(k.skin, h, 1.6, OUTLINE, 0.7)
    if k.body == "dress":
        flare = 7.5 + abs(pose.hem) * 0.12
        skirt = [(cx - 3.4, hip_y - 0.6), (cx + 3.4, hip_y - 0.6), (cx + flare, hip_y + 8.6), (cx - flare, hip_y + 8.6)]
        c.polygon(k.lower, [(x, y + 1) for x, y in skirt], OUTLINE, 0.8)
        c.polygon(k.top, skirt, OUTLINE, 0.8)
        for s in range(7):
            c.circle(k.trim, (cx - flare + s * flare / 3, hip_y + 8.6), 0.7)
        c.polygon(k.top, [(cx - 3.8, shoulder_y), (cx + 3.8, shoulder_y), (cx + 3.2, hip_y), (cx - 3.2, hip_y)], OUTLINE, 0.8)
        c.rect(k.accent, (cx - 4.0, hip_y - 1.6, 8.0, 2.0), outline=OUTLINE, width=0.5)
    elif k.body == "scale":
        c.polygon(k.top, [(cx - 4.8, shoulder_y), (cx + 4.8, shoulder_y), (cx + 5.6, hip_y + 4.4), (cx - 5.6, hip_y + 4.4)], OUTLINE, 0.8)
        c.polygon(k.accent, [(cx - 4.6, shoulder_y + 0.4), (cx + 4.6, shoulder_y + 0.4), (cx + 4.8, hip_y + 1.4), (cx - 4.8, hip_y + 1.4)], OUTLINE, 0.7)
        for row in range(4):
            for col in range(4):
                c.circle(shade(k.accent, 0.22), (cx - 3.0 + col * 2.0 + (row % 2) * 1.0, shoulder_y + 2.0 + row * 2.2), 0.75)
        c.rect((170, 38, 44), (cx - 5.0, hip_y - 1.2, 10.0, 2.2), outline=OUTLINE, width=0.5)
    elif k.body == "robe":
        c.polygon(k.top, [(cx - 4.6, shoulder_y - 0.4), (cx + 4.6, shoulder_y - 0.4), (cx + 6.6, GROUND_Y - 1.2), (cx - 6.6, GROUND_Y - 1.2)], OUTLINE, 0.9)
        for side in (-1, 1):
            c.polygon(k.accent, [(cx + side * 4.6, shoulder_y), (cx + side * 1.4, shoulder_y), (cx + side * 1.8, hip_y + 1.0), (cx + side * 5.0, hip_y + 1.0)], OUTLINE, 0.6)
        c.line(k.trim, (cx - 6.4, GROUND_Y - 2.0), (cx + 6.4, GROUND_Y - 2.0), 0.7)
    elif k.body == "vest":
        c.polygon(k.top, [(cx - 4.8, shoulder_y), (cx + 4.8, shoulder_y), (cx + 5.2, hip_y + 2.4), (cx - 5.2, hip_y + 2.4)], OUTLINE, 0.8)
        for side in (-1, 1):
            c.polygon(k.accent, [(cx + side * 4.8, shoulder_y), (cx + side * 1.2, shoulder_y), (cx + side * 2.0, hip_y + 1.4), (cx + side * 5.2, hip_y + 1.4)], OUTLINE, 0.6)
        c.rect((200, 60, 44), (cx - 5.2, hip_y - 1.4, 10.4, 2.4), outline=OUTLINE, width=0.5)
    else:
        c.polygon(k.top, [(cx - 4.6, shoulder_y - 0.4), (cx + 4.6, shoulder_y - 0.4), (cx + 7.4, GROUND_Y - 1.2), (cx - 7.4, GROUND_Y - 1.2)], OUTLINE, 0.9)
        c.polygon(k.lower, [(cx - 1.4, shoulder_y + 1.0), (cx + 1.4, shoulder_y + 1.0), (cx + 2.8, GROUND_Y - 1.4), (cx - 2.8, GROUND_Y - 1.4)])
    head = (cx, shoulder_y - HEAD_RADIUS - 0.6)
    c.circle(k.skin, head, HEAD_RADIUS, OUTLINE, 0.9)
    for side in (-1, 1):
        if k.glow is not None:
            c.circle(k.glow, (head[0] + side * 2.2, head[1] + 0.2), 1.0)
        else:
            _eye(c, (head[0] + side * 2.2, head[1] + 0.2), p, pose.eyes)
    _mouth(c, (head[0], head[1] + 3.1), p, pose.mouth)
    if k.head == "dancer":
        c.ellipse(k.hair, (head[0] - 6.0, head[1] - 6.8, 12.0, 6.6), OUTLINE, 0.7)
        c.circle(k.hair, (head[0], head[1] - 7.4), 2.6, OUTLINE, 0.6)
        for s in range(5):
            c.circle(COIN, (head[0] - 3.6 + s * 1.8, head[1] - 4.6), 0.55)
    elif k.head == "veiled":
        c.ellipse(k.hair, (head[0] - 6.0, head[1] - 10.0, 12.0, 8.4), OUTLINE, 0.8)
        c.circle(k.trim, (head[0], head[1] - 6.2), 0.8)
        c.polygon(k.hair, [(head[0] - 4.8, head[1] + 1.0), (head[0] + 4.8, head[1] + 1.0), (head[0] + 3.8, head[1] + 5.8), (head[0] - 3.8, head[1] + 5.8)], OUTLINE, 0.5)
    elif k.head == "firebraid":
        c.ellipse(k.hair, (head[0] - 5.8, head[1] - 7.0, 11.6, 6.4), OUTLINE, 0.7)
        c.lines(COIN, [(head[0] - 4.2, head[1] - 3.8), (head[0], head[1] - 4.6), (head[0] + 4.2, head[1] - 3.8)], 0.6)
        c.circle(RUBY, (head[0], head[1] - 4.4), 0.8)
        for side in (-1, 1):
            c.ring(COIN, (head[0] + side * 5.0, head[1] + 2.4), 1.2, 0.45)
    elif k.head == "elder":
        c.polygon(BEARD, [(head[0] - 3.8, head[1] + 1.8), (head[0] + 3.8, head[1] + 1.8), (head[0] + 1.6, head[1] + 10.0), (head[0] - 1.6, head[1] + 10.0)], OUTLINE, 0.6)
        c.ellipse(k.hair, (head[0] - 6.8, head[1] - 10.8, 13.6, 9.0), OUTLINE, 0.8)
        c.circle(k.trim, (head[0], head[1] - 6.8), 1.0, OUTLINE, 0.4)
    elif k.head == "juggler":
        c.polygon((188, 36, 44), [(head[0] - 4.6, head[1] - 3.8), (head[0] + 4.6, head[1] - 3.8), (head[0] + 3.6, head[1] - 10.2), (head[0] - 3.6, head[1] - 10.2)], OUTLINE, 0.8)
        c.polygon(k.hair, [(head[0] - 3.6, head[1] + 2.0), (head[0] + 3.6, head[1] + 2.0), (head[0] + 4.8, head[1] + 3.2), (head[0], head[1] + 2.6), (head[0] - 4.8, head[1] + 3.2)], OUTLINE, 0.3)
    elif k.head == "weaver":
        c.polygon(k.top, [(head[0] - 6.4, head[1] + 5.0), (head[0] - 6.6, head[1] - 4.0), (head[0], head[1] - 8.6), (head[0] + 6.6, head[1] - 4.0), (head[0] + 6.4, head[1] + 5.0), (head[0] + 4.0, head[1] - 1.0), (head[0] - 4.0, head[1] - 1.0)], OUTLINE, 0.9)
        c.polygon(k.top, [(head[0] - 4.0, head[1] + 1.4), (head[0] + 4.0, head[1] + 1.4), (head[0] + 3.0, head[1] + 5.8), (head[0] - 3.0, head[1] + 5.8)], OUTLINE, 0.5)
    if k.mask and k.head in ("dancer", "juggler"):
        c.polygon(MASK_GOLD, [(head[0] - 5.6, head[1] - 1.4), (head[0] + 5.6, head[1] - 1.4), (head[0] + 4.4, head[1] + 1.4), (head[0], head[1] + 0.6), (head[0] - 4.4, head[1] + 1.4)], OUTLINE, 0.5)
        for side in (-1, 1):
            _eye(c, (head[0] + side * 2.2, head[1] + 0.2), p, pose.eyes)


def draw_person(pose: Pose, costume: Costume, size: int = FRAME) -> pygame.Surface:
    """A 48x48 frame; ``size`` renders it larger straight from the supersampled canvas (sharp)."""
    canvas = Canvas(FRAME, FRAME, scale=max(4, -(-size // FRAME) * 2), fringe=OUTLINE)
    if pose.view == "front":
        _draw_front(canvas, pose, costume)
    else:
        _draw_side(canvas, pose, costume)
    if size == FRAME:
        return canvas.finish()
    return pygame.transform.smoothscale(canvas.surface, (size, size))


def hand_points(pose: Pose) -> tuple[tuple[float, float], tuple[float, float]]:
    """(back hand, front hand) relative to the frame's bottom-centre, facing right."""
    sk = skeleton(pose)
    return ((sk.back_hand[0] - FRAME / 2, sk.back_hand[1] - GROUND_Y),
            (sk.front_hand[0] - FRAME / 2, sk.front_hand[1] - GROUND_Y))


def head_point(pose: Pose) -> tuple[float, float]:
    sk = skeleton(pose)
    return sk.head[0] - FRAME / 2, sk.head[1] - GROUND_Y


def veil_anchor(pose: Pose) -> tuple[float, float]:
    """Where the dancer's veil is pinned (back of the bun)."""
    sk = skeleton(pose)
    if pose.view == "front":
        return 0.0, sk.head[1] - GROUND_Y - 7.0
    return sk.head[0] - 6.2 - FRAME / 2, sk.head[1] - 4.0 - GROUND_Y

