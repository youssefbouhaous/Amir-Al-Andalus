"""The Moon Troupe's animations: poses for the juggler, the dancer and the weaver.

Every animation is a function from (frame, frame count) to a ``Pose`` on the
prince's rig, turned into sprite sheets by ``SheetSpec`` painters so they are
rendered once and cached like the prince's own frames.
"""

import math
from collections.abc import Callable
from functools import lru_cache

import pygame

from rendering.art.people import DANCER, JUGGLER, WEAVER, Costume, draw_person, hand_points, veil_anchor
from rendering.art.prince import HIP_Y, Pose
from rendering.sprite_library import AnimationSpec, SheetSpec

PoseFn = Callable[[int, int], Pose]


def _wave(i: int, n: int, phase: float = 0.0) -> float:
    return math.sin(math.tau * i / max(1, n) + phase)


# --- shared --------------------------------------------------------------------------------
def _stunned(i: int, n: int) -> Pose:
    wobble = _wave(i, n)
    return Pose(
        lean=4 * wobble, head_tilt=10 * wobble, head_dy=0.4 * abs(wobble),
        front_thigh=10 + 6 * wobble, front_knee=16, back_thigh=-8 - 6 * wobble, back_knee=18,
        front_upper=165, front_elbow=-8, back_upper=182, back_elbow=-14,
        hem=8 * wobble, plume=20 * wobble, eyes="x" if i % 2 else "wide", mouth="o",
    )


def _hurt(i: int, n: int) -> Pose:
    return Pose(lean=-16, head_tilt=-12, front_thigh=30, front_knee=40, back_thigh=-10, back_knee=30,
                front_upper=120, front_elbow=30, back_upper=-110, back_elbow=30, hem=14, eyes="x", mouth="open")


def _defeated(i: int, n: int) -> Pose:
    u = i / max(1, n - 1)
    return Pose(
        hip_y=HIP_Y + 6.0 * u, lean=-28 - 58 * u, head_tilt=-10 * u,
        front_thigh=30 + 50 * u, front_knee=30 - 20 * u, back_thigh=10 + 40 * u, back_knee=40,
        front_upper=110 + 40 * u, front_elbow=20, back_upper=-120 - 30 * u, back_elbow=20,
        hem=20 * u, eyes="x", mouth="open",
    )


# --- the juggler ------------------------------------------------------------------------------
def _juggle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        hip_y=HIP_Y + 0.4, lean=1, head_tilt=-12, head_dy=0.3 * w,
        front_thigh=16, front_knee=8, back_thigh=-14, back_knee=8,
        front_upper=46 + 20 * w, front_elbow=74, back_upper=46 - 20 * w, back_elbow=74,
        hem=2 * w, plume=12 * w, eyes="open", mouth="smile",
    )


def _juggler_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    base = _juggle(i, n)
    return Pose(
        hip_y=HIP_Y + 0.6 - 1.0 * abs(math.cos(w)), lean=3, head_tilt=-10,
        front_thigh=24 * math.sin(w), front_knee=10 + 34 * max(0.0, math.cos(w)),
        back_thigh=24 * math.sin(w + math.pi), back_knee=10 + 34 * max(0.0, math.cos(w + math.pi)),
        front_upper=base.front_upper, front_elbow=74, back_upper=base.back_upper, back_elbow=74,
        hem=6 * math.sin(w), plume=16 * math.sin(w), mouth="smile",
    )


def _juggler_throw(i: int, n: int) -> Pose:
    arms = ((-70, 40, -8), (150, 8, 10), (116, 20, 6), (70, 50, 2))[min(i, 3)]
    return Pose(lean=arms[2], head_tilt=-14, front_thigh=24, front_knee=10, back_thigh=-18, back_knee=10,
                front_upper=arms[0], front_elbow=arms[1], back_upper=-30, back_elbow=40, hem=-arms[2],
                mouth="open" if i == 1 else "smile")


def _juggler_rain(i: int, n: int) -> Pose:
    if i == 0:
        return Pose(hip_y=HIP_Y + 2.2, lean=6, front_thigh=40, front_knee=70, back_thigh=10, back_knee=60,
                    front_upper=24, front_elbow=40, back_upper=30, back_elbow=40, mouth="grit")
    lift = (170, 176, 150)[min(i - 1, 2)]
    return Pose(hip_y=HIP_Y - 0.8, lean=-4, head_tilt=-24, front_thigh=6, front_knee=0, back_thigh=-6, back_knee=0,
                front_upper=lift, front_elbow=0, back_upper=lift + 8, back_elbow=0, mouth="open", eyes="happy")


def _juggler_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(hip_y=HIP_Y + 0.6 * u, lean=30 * u, head_tilt=10 * u, front_thigh=10, front_knee=6,
                back_thigh=-24 * u, back_knee=30 * u, front_upper=150 - 30 * u, front_elbow=60, back_upper=-60, back_elbow=70,
                mouth="smile", eyes="happy" if u > 0.5 else "open")


# --- the dancer ------------------------------------------------------------------------------
def _dancer_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        hip_x=24.0 + 0.8 * w, lean=4 * w, head_tilt=-6 * w,
        front_thigh=22, front_knee=4, back_thigh=-6, back_knee=12,
        front_upper=140 + 12 * w, front_elbow=-34, back_upper=-108 - 8 * w, back_elbow=34,
        hem=10 * w, eyes="open", mouth="smile",
    )


def _dancer_run(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        hip_y=HIP_Y + 0.6 - 1.6 * abs(math.cos(w)), lean=10, head_tilt=-6,
        front_thigh=44 * math.sin(w), front_knee=10 + 60 * max(0.0, math.cos(w)),
        back_thigh=44 * math.sin(w + math.pi), back_knee=10 + 60 * max(0.0, math.cos(w + math.pi)),
        front_upper=-50 - 10 * math.sin(w), front_elbow=20, back_upper=-80, back_elbow=16,
        hem=22 + 8 * abs(math.sin(w)), mouth="smile",
    )


def _dancer_spin(i: int, n: int) -> Pose:
    # Side, front, (mirrored) side, front...: the painter mirrors frames 2 and 5.
    front = i % 3 == 1
    return Pose(
        hip_y=HIP_Y - 1.2, lean=0, front_thigh=70, front_knee=130, back_thigh=0, back_knee=0,
        front_upper=170, front_elbow=-30, back_upper=172, back_elbow=-26,
        hem=36, view="front" if front else "side", eyes="closed", mouth="smile",
    )


def _dancer_kick(i: int, n: int) -> Pose:
    frames = (
        dict(lean=12, front_thigh=-34, front_knee=40, front_upper=40, back_upper=-40, hem=-10),
        dict(lean=-22, front_thigh=112, front_knee=0, front_upper=100, back_upper=-126, hem=34),
        dict(lean=-26, front_thigh=120, front_knee=4, front_upper=96, back_upper=-130, hem=40),
        dict(lean=-6, front_thigh=40, front_knee=30, front_upper=60, back_upper=-80, hem=14),
    )
    f = frames[min(i, 3)]
    return Pose(back_thigh=-4, back_knee=6, front_elbow=0, back_elbow=10, eyes="open", mouth="grit", **f)


def _dancer_vanish(i: int, n: int) -> Pose:
    u = i / max(1, n - 1)
    return Pose(hip_y=HIP_Y - 1.6 * u, lean=-2, head_tilt=-16 * u, front_thigh=4, front_knee=0, back_thigh=-4, back_knee=0,
                front_upper=120 + 55 * u, front_elbow=-20, back_upper=120 + 60 * u, back_elbow=-20,
                hem=20 * u, eyes="closed", mouth="smile")


def _dancer_appear(i: int, n: int) -> Pose:
    u = i / max(1, n - 1)
    return Pose(hip_y=HIP_Y + 3.0 * (1 - u), lean=14 * (1 - u), front_thigh=60 * (1 - u) + 10, front_knee=100 * (1 - u),
                back_thigh=-10, back_knee=90 * (1 - u), front_upper=100, front_elbow=-10, back_upper=-100, back_elbow=10,
                hem=30 * (1 - u), eyes="open", mouth="grit")


def _dancer_throw(i: int, n: int) -> Pose:
    arm = (-90, 104, 66)[min(i, 2)]
    return Pose(lean=(-6, 10, 4)[min(i, 2)], front_thigh=20, front_knee=6, back_thigh=-16, back_knee=12,
                front_upper=arm, front_elbow=0 if i == 1 else 20, back_upper=-110, back_elbow=30, hem=-10 + i * 10,
                mouth="open" if i == 1 else "smile")


def _dancer_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(hip_y=HIP_Y + 2.0 * u, lean=22 * u, head_tilt=8 * u, front_thigh=18, front_knee=30 * u,
                back_thigh=-30 * u, back_knee=50 * u, front_upper=40, front_elbow=-20, back_upper=-40, back_elbow=10,
                hem=-6 * u, eyes="closed" if u > 0.6 else "open", mouth="smile")


# --- the weaver --------------------------------------------------------------------------------
def _weaver_float(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.5 * w, lean=2 * w, front_thigh=10, front_knee=24, back_thigh=0, back_knee=30,
        front_upper=52 + 8 * w, front_elbow=-24, back_upper=-40 - 8 * w, back_elbow=24,
        hem=12 * w, eyes="open",
    )


def _weaver_whip(i: int, n: int) -> Pose:
    arm = ((-116, 40, -8), (40, 12, 4), (96, 0, 12), (74, 6, 8), (56, -20, 2))[min(i, 4)]
    return Pose(lean=arm[2], front_thigh=12, front_knee=20, back_thigh=-4, back_knee=24,
                front_upper=arm[0], front_elbow=arm[1], back_upper=-50, back_elbow=30, hem=-arm[2] * 1.5,
                hand_glow=i in (1, 2))


def _weaver_cast(i: int, n: int) -> Pose:
    u = min(1.0, i / 2)
    return Pose(lean=-4 * u, head_tilt=-14 * u, front_thigh=8, front_knee=20, back_thigh=-4, back_knee=24,
                front_upper=60 + 100 * u, front_elbow=-20, back_upper=60 + 110 * u, back_elbow=-24,
                hem=16 * u, hand_glow=True)


def _weaver_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(lean=14 * u, head_tilt=16 * u, front_thigh=8, front_knee=20, back_thigh=0, back_knee=24,
                front_upper=30, front_elbow=-60, back_upper=-30, back_elbow=40, hem=4 * u)


# --- sheets ------------------------------------------------------------------------------------
TroupeAnims = dict[str, tuple[PoseFn, int, float, bool]]  # name -> (pose, frames, duration, loop)

JUGGLER_ANIMS: TroupeAnims = {
    "idle": (_juggle, 8, 0.09, True), "walk": (_juggler_walk, 8, 0.09, True),
    "throw": (_juggler_throw, 4, 0.07, False), "rain": (_juggler_rain, 4, 0.12, False),
    "bow": (_juggler_bow, 6, 0.12, False), "stunned": (_stunned, 4, 0.12, True),
    "hurt": (_hurt, 1, 1.0, True), "defeated": (_defeated, 5, 0.1, False),
}
DANCER_ANIMS: TroupeAnims = {
    "idle": (_dancer_idle, 8, 0.11, True), "walk": (_dancer_run, 8, 0.07, True),
    "spin": (_dancer_spin, 6, 0.05, True), "kick": (_dancer_kick, 4, 0.07, False),
    "vanish": (_dancer_vanish, 4, 0.08, False), "appear": (_dancer_appear, 4, 0.07, False),
    "throw": (_dancer_throw, 3, 0.07, False), "bow": (_dancer_bow, 6, 0.12, False),
    "stunned": (_stunned, 4, 0.12, True), "hurt": (_hurt, 1, 1.0, True), "defeated": (_defeated, 5, 0.1, False),
}
WEAVER_ANIMS: TroupeAnims = {
    "idle": (_weaver_float, 8, 0.12, True), "walk": (_weaver_float, 8, 0.09, True),
    "whip": (_weaver_whip, 5, 0.08, False), "cast": (_weaver_cast, 4, 0.1, False),
    "bow": (_weaver_bow, 6, 0.12, False), "stunned": (_stunned, 4, 0.12, True),
    "hurt": (_hurt, 1, 1.0, True), "defeated": (_defeated, 5, 0.1, False),
}


def _painter(costume: Costume, anims: TroupeAnims):  # noqa: ANN202
    def paint(surface: pygame.Surface, animation: str, frame: int) -> None:
        pose_fn, count, _, _ = anims[animation]
        image = draw_person(pose_fn(frame, count), costume)
        if animation == "spin" and frame % 3 == 2:
            image = pygame.transform.flip(image, True, False)
        surface.blit(image, (0, 0))
    return paint


def _spec(path: str, costume: Costume, anims: TroupeAnims) -> SheetSpec:
    layout = {name: AnimationSpec(row=row, frame_count=count, frame_duration=duration, loop=loop)
              for row, (name, (_, count, duration, loop)) in enumerate(anims.items())}
    return SheetSpec(path, 48, 48, layout, _painter(costume, anims))


JUGGLER_SHEET = _spec("troupe_juggler.png", JUGGLER, JUGGLER_ANIMS)
DANCER_SHEET = _spec("troupe_dancer.png", DANCER, DANCER_ANIMS)
WEAVER_SHEET = _spec("troupe_weaver.png", WEAVER, WEAVER_ANIMS)


@lru_cache(maxsize=None)
def hands(kind: str, animation: str, frame: int) -> tuple[tuple[float, float], tuple[float, float]]:
    anims = {"juggler": JUGGLER_ANIMS, "dancer": DANCER_ANIMS, "weaver": WEAVER_ANIMS}[kind]
    pose_fn, count, _, _ = anims[animation]
    return hand_points(pose_fn(frame, count))


@lru_cache(maxsize=None)
def veil(animation: str, frame: int) -> tuple[float, float]:
    pose_fn, count, _, _ = DANCER_ANIMS[animation]
    x, y = veil_anchor(pose_fn(frame, count))
    if animation == "spin" and frame % 3 == 2:
        x = -x
    return x, y




@lru_cache(maxsize=64)
def portrait(kind: str, animation: str, frame: int, size: int) -> pygame.Surface:
    """One performer frame at any size (for the manuscript's painted miniatures)."""
    costume, anims = {"juggler": (JUGGLER, JUGGLER_ANIMS), "dancer": (DANCER, DANCER_ANIMS),
                      "weaver": (WEAVER, WEAVER_ANIMS)}[kind]
    pose_fn, count, _, _ = anims[animation]
    return draw_person(pose_fn(frame % count, count), costume, size)
