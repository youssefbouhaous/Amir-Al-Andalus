"""The prince, drawn from a tiny skeletal rig.

Instead of hand-placing pixels for every frame, the character is a set of
limbs (capsules) hanging from joints. An animation is just a function from
time to joint angles (a ``Pose``); frames are rendered from poses on a
supersampled canvas, which makes smooth 10-12 frame cycles cheap to produce
and keeps proportions consistent across every pose.

Angle convention for limbs: 0 deg points straight down, +90 points forward
(the direction the prince faces), 180 points up. Knees bend backwards
(``shin = thigh - knee``), elbows forwards (``forearm = upper + elbow``).

Frames face right; the game mirrors them for facing left. The turban's tail
is *not* part of the frames: it is a simulated rope (``entities/scarf.py``)
attached at ``turban_anchor``.
"""

import math
from dataclasses import dataclass, replace

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, limb, mix, shade

FRAME = 48
GROUND_Y = 48.0
HIP_Y = 35.8
THIGH = 5.5
SHIN = 5.5
TORSO = 9.2
HEAD_RADIUS = 5.6
UPPER_ARM = 4.6
FOREARM = 4.4
OUTLINE: Color = (42, 24, 26)


@dataclass(frozen=True)
class PrincePalette:
    robe: Color
    robe_shade: Color
    trim: Color
    sash: Color
    trousers: Color
    skin: Color
    turban: Color
    turban_shade: Color
    jewel: Color
    plume: Color
    slipper: Color
    eye: Color = (34, 22, 24)
    scarf: Color = (200, 44, 56)
    scarf_tip: Color = (240, 190, 70)
    aura: Color | None = None


PRINCE_PALETTE = PrincePalette(
    robe=(34, 128, 112), robe_shade=(22, 88, 78), trim=(236, 190, 78), sash=(204, 46, 58),
    trousers=(238, 228, 206), skin=(214, 160, 112), turban=(248, 244, 234),
    turban_shade=(204, 196, 182), jewel=(214, 34, 62), plume=(250, 246, 236),
    slipper=(182, 44, 44),
)
# After eating the pomegranate: a golden robe and an emerald.
PRINCE_POWERED_PALETTE = PrincePalette(
    robe=(228, 172, 44), robe_shade=(172, 118, 22), trim=(255, 240, 180), sash=(124, 36, 116),
    trousers=(242, 234, 214), skin=(214, 160, 112), turban=(252, 246, 224),
    turban_shade=(216, 202, 166), jewel=(30, 172, 112), plume=(124, 36, 116),
    slipper=(124, 36, 116), scarf=(124, 36, 116), scarf_tip=(255, 214, 90),
)
# Star power: midnight-blue robe with silver trim and a sapphire.
PRINCE_STAR_PALETTE = PrincePalette(
    robe=(40, 70, 170), robe_shade=(26, 44, 116), trim=(226, 236, 255), sash=(236, 186, 64),
    trousers=(234, 238, 250), skin=(214, 160, 112), turban=(240, 246, 255),
    turban_shade=(180, 196, 226), jewel=(90, 170, 255), plume=(236, 186, 64),
    slipper=(236, 186, 64), scarf=(236, 186, 64), scarf_tip=(255, 255, 255),
    aura=(140, 200, 255),
)


@dataclass(frozen=True)
class Pose:
    hip_x: float = 24.0
    hip_y: float = HIP_Y
    lean: float = 0.0
    head_tilt: float = 0.0
    head_dy: float = 0.0
    back_thigh: float = -4.0
    back_knee: float = 4.0
    front_thigh: float = 6.0
    front_knee: float = 4.0
    back_upper: float = -6.0
    back_elbow: float = 12.0
    front_upper: float = 6.0
    front_elbow: float = 12.0
    hem: float = 0.0
    plume: float = 0.0
    eyes: str = "open"     # open | closed | happy | x | wide
    mouth: str = "none"    # none | smile | open | o | grit
    view: str = "side"     # side | front
    hand_glow: bool = False


# --- Animations ----------------------------------------------------------------
def _idle(i: int, n: int) -> Pose:
    t = i / n
    s = math.sin(math.tau * t)
    return Pose(
        head_dy=0.45 * s, lean=0.6 * s,
        back_upper=-5 - 1.5 * s, front_upper=5 + 1.5 * s,
        back_elbow=10 + 3 * s, front_elbow=10 + 3 * s,
        plume=8 + 6 * math.sin(math.tau * t + 1.2), hem=0.8 * s,
        eyes="closed" if i == n - 2 else "open",
    )


def _run(i: int, n: int) -> Pose:
    w = math.tau * i / n
    front = 40 * math.sin(w)
    back = 40 * math.sin(w + math.pi)
    front_knee = 12 + 62 * max(0.0, math.cos(w)) ** 0.8
    back_knee = 12 + 62 * max(0.0, math.cos(w + math.pi)) ** 0.8
    return Pose(
        hip_y=HIP_Y + 0.8 - 1.8 * abs(math.cos(w)),
        lean=11, head_tilt=-5,
        front_thigh=front, front_knee=front_knee, back_thigh=back, back_knee=back_knee,
        front_upper=-38 * math.sin(w), back_upper=38 * math.sin(w),
        front_elbow=75, back_elbow=75,
        hem=12 + 6 * abs(math.sin(w)), plume=32 + 6 * math.sin(2 * w),
        mouth="none",
    )


def _skid(i: int, n: int) -> Pose:
    return Pose(
        hip_y=HIP_Y + 0.5, lean=-14, head_tilt=6,
        front_thigh=38, front_knee=4, back_thigh=-12, back_knee=34,
        front_upper=62, front_elbow=18, back_upper=-48, back_elbow=30,
        hem=-14, plume=-10, mouth="o",
    )


def _jump(i: int, n: int) -> Pose:
    if i == 0:
        return Pose(
            lean=6, front_thigh=58, front_knee=84, back_thigh=-24, back_knee=22,
            front_upper=70, front_elbow=40, back_upper=150, back_elbow=20,
            hem=6, plume=26, mouth="grit",
        )
    return Pose(
        lean=3, front_thigh=46, front_knee=76, back_thigh=-6, back_knee=58,
        front_upper=48, front_elbow=50, back_upper=162, back_elbow=12,
        hem=8, plume=30,
    )


def _apex(i: int, n: int) -> Pose:
    return Pose(
        lean=2, front_thigh=26, front_knee=52, back_thigh=-6, back_knee=42,
        front_upper=104, front_elbow=24, back_upper=-86, back_elbow=24,
        hem=2, plume=8, mouth="none",
    )


def _fall(i: int, n: int) -> Pose:
    f = 1 if i % 2 else -1
    return Pose(
        lean=-2, front_thigh=16, front_knee=12, back_thigh=-16, back_knee=26,
        front_upper=142 + 10 * f, front_elbow=18, back_upper=-136 + 10 * f, back_elbow=18,
        hem=6 * f, plume=-10 + 6 * f, eyes="wide", mouth="o",
    )


def _wall_slide(i: int, n: int) -> Pose:
    return Pose(
        hip_x=26.0, hip_y=HIP_Y - 0.5 + 0.4 * i, lean=-6, head_tilt=-6,
        front_thigh=72, front_knee=74, back_thigh=8, back_knee=24,
        front_upper=150, front_elbow=24, back_upper=-26, back_elbow=26,
        hem=10, plume=-6 - 3 * i, mouth="grit",
    )


def _throw(i: int, n: int) -> Pose:
    base = dict(front_thigh=22, front_knee=10, back_thigh=-16, back_knee=12)
    if i == 0:
        return Pose(**base, lean=-4, front_upper=-72, front_elbow=64, back_upper=40, back_elbow=30,
                    hand_glow=True, mouth="grit", plume=10)
    if i == 1:
        return Pose(**base, lean=9, front_upper=96, front_elbow=0, back_upper=-40, back_elbow=20,
                    mouth="open", plume=-12, hem=-6)
    return Pose(**base, lean=5, front_upper=66, front_elbow=18, back_upper=-26, back_elbow=20, plume=-6)


def _hurt(i: int, n: int) -> Pose:
    return Pose(
        lean=-16, head_tilt=-12, front_thigh=34, front_knee=42, back_thigh=-10, back_knee=30,
        front_upper=122, front_elbow=30, back_upper=-118, back_elbow=30,
        hem=12, plume=30, eyes="x", mouth="open",
    )


def _death(i: int, n: int) -> Pose:
    f = 1 if i % 2 else -1
    return Pose(
        view="front", eyes="x", mouth="open",
        front_upper=150 + 16 * f, back_upper=150 - 16 * f, front_elbow=20, back_elbow=20,
        plume=12 * f,
    )


def _victory(i: int, n: int) -> Pose:
    if i == 0:
        return Pose(hip_y=HIP_Y + 1.5, front_thigh=30, front_knee=40, back_thigh=-10, back_knee=36,
                    front_upper=30, back_upper=-20, eyes="closed", mouth="smile")
    if i == 1:
        return Pose(back_upper=130, back_elbow=40, front_upper=30, front_elbow=60, eyes="happy", mouth="smile")
    wave = math.sin(i * 1.3) * 4
    return Pose(
        lean=-3, head_tilt=-8, front_thigh=18, front_knee=8, back_thigh=-18, back_knee=8,
        back_upper=172 + wave, back_elbow=0, front_upper=20, front_elbow=110,
        eyes="happy", mouth="smile", plume=10 + wave, hem=2,
    )


def _door(i: int, n: int) -> Pose:
    return Pose(view="front", front_upper=12, back_upper=12, eyes="open", mouth="smile")


def _sit(i: int, n: int) -> Pose:
    s = math.sin(math.tau * i / max(1, n))
    return Pose(
        hip_y=GROUND_Y - 4.5, lean=2 + s, head_dy=0.4 * s,
        front_thigh=84, front_knee=158, back_thigh=78, back_knee=150,
        front_upper=34, front_elbow=40, back_upper=24, back_elbow=44,
        hem=-4, plume=4 + 3 * s,
    )


POSES = {
    "idle": _idle, "run": _run, "skid": _skid, "jump": _jump, "apex": _apex, "fall": _fall,
    "wall_slide": _wall_slide, "throw": _throw, "hurt": _hurt, "death": _death,
    "victory": _victory, "door": _door, "sit": _sit,
}


def pose_for(animation: str, frame: int, frame_count: int) -> Pose:
    return POSES.get(animation, _idle)(frame, max(1, frame_count))


# --- Geometry ---------------------------------------------------------------------
@dataclass(frozen=True)
class Skeleton:
    hip: tuple[float, float]
    shoulder: tuple[float, float]
    head: tuple[float, float]
    back_knee: tuple[float, float]
    back_ankle: tuple[float, float]
    front_knee: tuple[float, float]
    front_ankle: tuple[float, float]
    back_elbow: tuple[float, float]
    back_hand: tuple[float, float]
    front_elbow: tuple[float, float]
    front_hand: tuple[float, float]


def skeleton(pose: Pose) -> Skeleton:
    lean = math.radians(pose.lean)
    hip = (pose.hip_x, pose.hip_y)
    shoulder = (hip[0] + math.sin(lean) * TORSO, hip[1] - math.cos(lean) * TORSO)
    tilt = math.radians(pose.lean + pose.head_tilt)
    neck = HEAD_RADIUS + 0.8
    head = (shoulder[0] + math.sin(tilt) * neck + 0.8, shoulder[1] - math.cos(tilt) * neck + pose.head_dy)
    back_hip = (hip[0] - 1.2, hip[1])
    front_hip = (hip[0] + 1.2, hip[1])
    back_knee = limb(back_hip, pose.back_thigh, THIGH)
    back_ankle = limb(back_knee, pose.back_thigh - pose.back_knee, SHIN)
    front_knee = limb(front_hip, pose.front_thigh, THIGH)
    front_ankle = limb(front_knee, pose.front_thigh - pose.front_knee, SHIN)
    arm_root = (shoulder[0], shoulder[1] + 1.4)
    back_elbow = limb((arm_root[0] - 1.0, arm_root[1]), pose.back_upper, UPPER_ARM)
    back_hand = limb(back_elbow, pose.back_upper + pose.back_elbow, FOREARM)
    front_elbow = limb((arm_root[0] + 0.6, arm_root[1]), pose.front_upper, UPPER_ARM)
    front_hand = limb(front_elbow, pose.front_upper + pose.front_elbow, FOREARM)
    return Skeleton(hip, shoulder, head, back_knee, back_ankle, front_knee, front_ankle,
                    back_elbow, back_hand, front_elbow, front_hand)


def turban_anchor(animation: str, frame: int, frame_count: int) -> tuple[float, float]:
    """Where the turban tail attaches, relative to the frame's bottom-centre
    (the sprite's anchor in the world), for a right-facing frame."""
    pose = pose_for(animation, frame, frame_count)
    sk = skeleton(pose)
    if pose.view == "front":
        x, y = sk.head[0] + 5.5, sk.head[1] - 4.0
    else:
        x, y = sk.head[0] - 5.8, sk.head[1] - 4.4
    return x - FRAME / 2, y - GROUND_Y


# --- Drawing --------------------------------------------------------------------------
def _slipper(c: Canvas, ankle: tuple[float, float], p: PrincePalette, back: bool, angle: float) -> None:
    color = shade(p.slipper, -0.25) if back else p.slipper
    rad = math.radians(angle)
    fx, fy = math.cos(rad), math.sin(rad)  # along the foot
    ux, uy = fy, -fx                        # up from the sole
    def at(along: float, up: float) -> tuple[float, float]:
        return ankle[0] + fx * along + ux * up, ankle[1] + fy * along + uy * up
    shape_points = [at(-1.8, 1.6), at(2.6, 1.4), at(4.8, 2.6), at(4.2, 0.2), at(3.0, -1.1), at(-1.8, -1.1)]
    c.polygon(color, shape_points, OUTLINE, 0.8)


def _leg(c: Canvas, hip: tuple[float, float], knee: tuple[float, float], ankle: tuple[float, float],
         p: PrincePalette, back: bool, foot_angle: float) -> None:
    trousers = shade(p.trousers, -0.2) if back else p.trousers
    # Baggy sirwal trousers: wide at the knee, gathered at the ankle.
    c.capsule(trousers, hip, knee, 2.3, OUTLINE, 0.8)
    c.capsule(trousers, knee, ankle, 2.1, OUTLINE, 0.8)
    c.circle(trousers, knee, 2.4)
    cuff = (ankle[0] + (knee[0] - ankle[0]) * 0.18, ankle[1] + (knee[1] - ankle[1]) * 0.18)
    c.circle(shade(p.trim, -0.35) if back else shade(p.trim, -0.1), cuff, 1.6, OUTLINE, 0.5)
    _slipper(c, ankle, p, back, foot_angle)


def _arm(c: Canvas, root: tuple[float, float], elbow: tuple[float, float], hand: tuple[float, float],
         p: PrincePalette, back: bool, glow: bool = False) -> None:
    sleeve = p.robe_shade if back else p.robe
    skin = shade(p.skin, -0.18) if back else p.skin
    c.capsule(sleeve, root, elbow, 1.9, OUTLINE, 0.8)
    wrist = (elbow[0] + (hand[0] - elbow[0]) * 0.7, elbow[1] + (hand[1] - elbow[1]) * 0.7)
    c.capsule(sleeve, elbow, wrist, 1.7, OUTLINE, 0.8)
    c.circle(p.trim if not back else shade(p.trim, -0.3), wrist, 1.5, OUTLINE, 0.6)
    c.circle(skin, hand, 1.7, OUTLINE, 0.8)
    if glow:
        c.circle((190, 230, 255), hand, 2.8)
        c.star((255, 255, 255), hand, 2.6, rotation=20)


def _robe(c: Canvas, sk: Skeleton, pose: Pose, p: PrincePalette) -> None:
    hip, shoulder = sk.hip, sk.shoulder
    lean = math.radians(pose.lean)
    # Local axes of the torso.
    ux, uy = math.sin(lean), -math.cos(lean)   # up the spine
    rx, ry = -uy, ux                            # toward the front
    def at(forward: float, up: float, base=hip) -> tuple[float, float]:
        return base[0] + rx * forward + ux * up, base[1] + ry * forward + uy * up
    hem_swing = math.radians(pose.hem)
    hem_len = 3.6
    def hem_point(forward: float) -> tuple[float, float]:
        # Hangs from the hips, pivoting backward for positive ``pose.hem``.
        base = at(forward * 0.8, 0)
        return (base[0] + forward * 0.35 - math.sin(hem_swing) * hem_len,
                base[1] + math.cos(hem_swing) * hem_len)
    back_top, front_top = at(-3.4, TORSO - 0.6), at(3.6, TORSO - 0.6)
    back_waist, front_waist = at(-3.6, 1.6), at(3.4, 1.6)
    hem_back, hem_front = hem_point(-5.2), hem_point(5.0)
    body = [back_top, front_top, at(4.2, TORSO - 3.5), front_waist, hem_front, hem_back, back_waist, at(-4.0, TORSO - 3.5)]
    c.polygon(p.robe, body, OUTLINE, 0.9)
    # Shading on the back half and a gold hem border.
    shade_poly = [back_top, at(-0.6, TORSO - 0.6), at(-1.2, 1.4), hem_point(-1.6), hem_back, back_waist, at(-4.0, TORSO - 3.5)]
    c.polygon(p.robe_shade, shade_poly)
    c.line(p.trim, hem_back, hem_front, 1.1)
    c.line(p.trim, at(0.9, TORSO - 0.8), at(0.4, 2.2), 0.9)  # placket
    c.polygon(p.trim, [at(-1.2, TORSO - 0.5), at(2.8, TORSO - 0.5), at(1.0, TORSO - 3.0)])  # collar
    # Sash with a knot and a trailing end.
    sash = [at(-3.8, 3.2), at(3.6, 3.2), at(3.6, 1.2), at(-3.8, 1.2)]
    c.polygon(p.sash, sash, OUTLINE, 0.6)
    knot = at(-3.6, 2.2)
    tail_angle = math.radians(pose.hem * 1.6 - 20)
    tail_end = (knot[0] - 3.2 - math.sin(tail_angle) * 1.5, knot[1] + 3.2 + math.cos(tail_angle) * 0.6)
    c.capsule(p.sash, knot, tail_end, 0.9, OUTLINE, 0.6)


def _eye(c: Canvas, center: tuple[float, float], p: PrincePalette, state: str) -> None:
    x, y = center
    if state == "closed":
        c.line(p.eye, (x - 1.0, y + 0.2), (x + 1.0, y + 0.2), 0.8)
    elif state == "happy":
        c.lines(p.eye, [(x - 1.1, y + 0.6), (x, y - 0.4), (x + 1.1, y + 0.6)], 0.7)
    elif state == "x":
        c.line(p.eye, (x - 1.0, y - 1.0), (x + 1.0, y + 1.0), 0.7)
        c.line(p.eye, (x - 1.0, y + 1.0), (x + 1.0, y - 1.0), 0.7)
    else:
        size = 1.25 if state == "wide" else 1.0
        c.ellipse((252, 250, 246), (x - 1.2 * size, y - 1.4 * size, 2.4 * size, 2.8 * size))
        c.ellipse(p.eye, (x - 0.5 * size, y - 1.1 * size, 1.5 * size, 2.3 * size))
        c.circle((255, 255, 255), (x + 0.3, y - 0.6), 0.35)


def _mouth(c: Canvas, center: tuple[float, float], p: PrincePalette, state: str) -> None:
    x, y = center
    dark = (110, 40, 40)
    if state == "smile":
        c.lines(dark, [(x - 1.2, y - 0.3), (x - 0.2, y + 0.5), (x + 0.8, y - 0.2)], 0.6)
    elif state == "open":
        c.ellipse(dark, (x - 0.9, y - 0.7, 1.8, 1.6))
    elif state == "o":
        c.ellipse(dark, (x - 0.6, y - 0.6, 1.2, 1.3))
    elif state == "grit":
        c.line(dark, (x - 1.0, y), (x + 0.8, y), 0.6)


def _plume(c: Canvas, base: tuple[float, float], angle: float, p: PrincePalette) -> None:
    """A curved feather: its tip lags further back than its middle."""
    a = math.radians(angle)
    a2 = math.radians(angle * 1.6 + 8)
    mid = (base[0] - math.sin(a) * 4.0, base[1] - math.cos(a) * 4.0)
    tip = (mid[0] - math.sin(a2) * 4.4, mid[1] - math.cos(a2) * 4.4)
    c.tapered(OUTLINE, [base, mid, tip], 2.1, 1.1)
    c.tapered(p.plume, [base, mid, tip], 1.4, 0.45)
    c.circle(p.trim, tip, 0.7)


def _head_side(c: Canvas, sk: Skeleton, pose: Pose, p: PrincePalette) -> None:
    hx, hy = sk.head
    tilt = pose.lean + pose.head_tilt
    c.capsule(p.skin, sk.shoulder, (hx - 0.4, hy + 2.0), 1.6, OUTLINE, 0.8)
    # Head and nose as one silhouette: both outlines first, then both fills.
    nose = (hx + HEAD_RADIUS - 0.1, hy + 1.0)
    c.circle(OUTLINE, (hx, hy), HEAD_RADIUS + 0.9)
    c.circle(OUTLINE, nose, 1.1 + 0.7)
    c.circle(p.skin, (hx, hy), HEAD_RADIUS)
    c.circle(p.skin, nose, 1.1)
    c.circle(shade(p.skin, -0.12), (hx - 2.2, hy + 1.2), 1.4)       # ear
    c.circle((236, 140, 130), (hx + 2.3, hy + 2.5), 1.0)              # cheek
    _eye(c, (hx + 2.7, hy + 0.3), p, pose.eyes)
    if pose.eyes not in ("x", "happy"):
        c.line(p.eye, (hx + 1.6, hy - 1.7), (hx + 3.8, hy - 1.5), 0.6)  # brow
    _mouth(c, (hx + 3.4, hy + 3.2), p, pose.mouth)
    # Turban: a wrapped dome and band above the brow, a jewel and a plume.
    c.ellipse(p.turban, (hx - 6.2, hy - 10.4, 12.2, 8.2), OUTLINE, 0.9)
    for k in range(3):
        y = hy - 8.6 + k * 1.8
        c.line(p.turban_shade, (hx - 4.6 + k * 0.5, y + 1.5), (hx + 4.2 - k * 0.7, y - 0.4), 0.55)
    c.ellipse(p.turban, (hx - 6.6, hy - 5.6, 13.0, 3.6), OUTLINE, 0.8)
    c.ellipse(p.turban_shade, (hx - 6.4, hy - 4.2, 5.2, 1.8))
    jewel = (hx + 4.6, hy - 4.1)
    _plume(c, (jewel[0] - 0.5, jewel[1] - 1.3), pose.plume - tilt, p)
    c.circle(p.trim, jewel, 1.7, OUTLINE, 0.6)
    c.circle(p.jewel, jewel, 1.1)
    c.circle((255, 255, 255), (jewel[0] - 0.4, jewel[1] - 0.4), 0.35)


def _draw_side(c: Canvas, pose: Pose, p: PrincePalette) -> None:
    sk = skeleton(pose)
    arm_root = (sk.shoulder[0], sk.shoulder[1] + 1.4)
    _arm(c, (arm_root[0] - 1.0, arm_root[1]), sk.back_elbow, sk.back_hand, p, back=True)
    back_foot = -(pose.back_thigh - pose.back_knee) * 0.7
    front_foot = -(pose.front_thigh - pose.front_knee) * 0.7
    _leg(c, (sk.hip[0] - 1.2, sk.hip[1]), sk.back_knee, sk.back_ankle, p, True, back_foot)
    _leg(c, (sk.hip[0] + 1.2, sk.hip[1]), sk.front_knee, sk.front_ankle, p, False, front_foot)
    _robe(c, sk, pose, p)
    _head_side(c, sk, pose, p)
    _arm(c, (arm_root[0] + 0.6, arm_root[1]), sk.front_elbow, sk.front_hand, p, back=False, glow=pose.hand_glow)


def _draw_front(c: Canvas, pose: Pose, p: PrincePalette) -> None:
    cx = FRAME / 2
    hip_y = pose.hip_y
    # Legs.
    for side in (-1, 1):
        hip = (cx + side * 2.0, hip_y)
        knee = (cx + side * 2.6, hip_y + THIGH)
        ankle = (cx + side * 2.8, hip_y + THIGH + SHIN)
        c.capsule(p.trousers, hip, knee, 2.1, OUTLINE, 0.8)
        c.capsule(p.trousers, knee, ankle, 1.9, OUTLINE, 0.8)
        c.ellipse(p.slipper, (ankle[0] - 2.2, ankle[1] - 0.6, 4.4, 2.2), OUTLINE, 0.7)
    shoulder_y = hip_y - TORSO
    # Arms (behind the robe at the shoulders).
    for side, upper in ((-1, pose.back_upper), (1, pose.front_upper)):
        root = (cx + side * 4.2, shoulder_y + 1.6)
        a = math.radians(upper)
        elbow = (root[0] + side * math.sin(a) * UPPER_ARM, root[1] + math.cos(a) * UPPER_ARM)
        hand = (elbow[0] + side * math.sin(a) * FOREARM * 0.9, elbow[1] + math.cos(a) * FOREARM * 0.9)
        c.capsule(p.robe_shade, root, elbow, 1.9, OUTLINE, 0.8)
        c.capsule(p.robe, elbow, hand, 1.7, OUTLINE, 0.8)
        c.circle(p.skin, hand, 1.7, OUTLINE, 0.8)
    body = [(cx - 4.4, shoulder_y), (cx + 4.4, shoulder_y), (cx + 4.8, hip_y + 1), (cx + 6.0, hip_y + 5.2),
            (cx - 6.0, hip_y + 5.2), (cx - 4.8, hip_y + 1)]
    c.polygon(p.robe, body, OUTLINE, 0.9)
    c.line(p.trim, (cx - 6.0, hip_y + 5.0), (cx + 6.0, hip_y + 5.0), 1.1)
    c.line(p.trim, (cx, shoulder_y + 0.5), (cx, hip_y + 4.6), 0.9)
    c.rect(p.sash, (cx - 4.8, hip_y - 1.8, 9.6, 2.2), outline=OUTLINE, width=0.6)
    head = (cx, shoulder_y - HEAD_RADIUS - 0.6)
    c.circle(p.skin, head, HEAD_RADIUS, OUTLINE, 0.9)
    for side in (-1, 1):
        _eye(c, (head[0] + side * 2.2, head[1] + 0.2), p, pose.eyes)
        c.circle((236, 140, 130), (head[0] + side * 3.4, head[1] + 2.3), 0.9)
    _mouth(c, (head[0], head[1] + 3.1), p, pose.mouth)
    c.ellipse(p.turban, (head[0] - 6.6, head[1] - 10.6, 13.2, 8.4), OUTLINE, 0.9)
    c.ellipse(p.turban, (head[0] - 7.0, head[1] - 5.8, 14.0, 3.8), OUTLINE, 0.8)
    jewel = (head[0], head[1] - 4.3)
    _plume(c, (jewel[0], jewel[1] - 1.3), pose.plume, p)
    c.circle(p.trim, jewel, 1.7, OUTLINE, 0.6)
    c.circle(p.jewel, jewel, 1.1)


def draw_pose(pose: Pose, palette: PrincePalette) -> pygame.Surface:
    canvas = Canvas(FRAME, FRAME, fringe=OUTLINE)
    if pose.view == "front":
        _draw_front(canvas, pose, palette)
    else:
        _draw_side(canvas, pose, palette)
    return canvas.finish()


def prince_painter(palette: PrincePalette, frame_counts: dict[str, int]):
    """A SheetSpec painter: paints ``animation``/``frame`` into a sheet cell."""

    def paint(surface: pygame.Surface, animation: str, frame: int) -> None:
        pose = pose_for(animation, frame, frame_counts.get(animation, 1))
        surface.blit(draw_pose(pose, palette), (0, 0))

    return paint


def portrait(palette: PrincePalette, size: int = 40) -> pygame.Surface:
    """Head-and-shoulders icon for the HUD."""
    pose = replace(_idle(0, 12), eyes="open", mouth="smile")
    frame = draw_pose(pose, palette)
    crop = frame.subsurface((8, 6, 32, 32)).copy()
    return pygame.transform.smoothscale(crop, (size, size))
