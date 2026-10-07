"""The River-Thieves' animations: poses for Yusuf, Nur and Hamida.

Like the other finales' people, every animation is a function from (frame,
frame count) to a ``Pose`` on the prince's rig, rendered once into a sprite
sheet. Props - Yusuf's goatskin and brass cups, Nur's net, spear and line,
Hamida's parasol and bells - are drawn by the entities at the hand points
given here, so they can swell, spin and splash freely.
"""

import math
from collections.abc import Callable
from functools import lru_cache

import pygame

from rendering.art.people import HAMIDA, NUR, YUSUF, Costume, draw_person, hand_points, head_point
from rendering.art.prince import HIP_Y, Pose
from rendering.art.thieves import _land, _leap
from rendering.art.troupe import _defeated, _hurt
from rendering.sprite_library import AnimationSpec, SheetSpec

PoseFn = Callable[[int, int], Pose]


def _wave(i: int, n: int, phase: float = 0.0) -> float:
    return math.sin(math.tau * i / max(1, n) + phase)


def _ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# --- shared ------------------------------------------------------------------------------------
def _flail(i: int, n: int) -> Pose:
    """Lifted off his feet by a fountain: arms windmilling, legs kicking at nothing."""
    w = _wave(i, n)
    return Pose(
        lean=-10 + 4 * w, head_tilt=-14, front_thigh=30 * w, front_knee=40, back_thigh=-30 * w, back_knee=50,
        front_upper=130 + 50 * w, front_elbow=30, back_upper=150 - 50 * w, back_elbow=20,
        hem=24 * w, plume=40 * w, eyes="wide", mouth="open",
    )


def _dizzy(i: int, n: int) -> Pose:
    """Set down hard in the wet: wobbling, seeing stars."""
    w = _wave(i, n)
    return Pose(
        hip_y=HIP_Y + 1.5, lean=8 * w, head_tilt=14 * w, front_thigh=18, front_knee=26, back_thigh=-14, back_knee=24,
        front_upper=40 + 20 * w, front_elbow=40, back_upper=-30 - 20 * w, back_elbow=30, hem=6 * w, plume=10 * w,
        eyes="x", mouth="o",
    )


def _run(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=14, head_dy=0.6 * abs(math.sin(w)), front_thigh=48 * math.sin(w), back_thigh=48 * math.sin(w + math.pi),
        front_knee=20 + 60 * max(0.0, math.cos(w)), back_knee=20 + 60 * max(0.0, math.cos(w + math.pi)),
        front_upper=-50 * math.sin(w), front_elbow=60, back_upper=50 * math.sin(w), back_elbow=60,
        hem=12 * math.sin(w), plume=26,
    )


def _bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(lean=22 * u, head_tilt=14 * u, front_thigh=8, front_knee=6, back_thigh=-8, back_knee=6,
                front_upper=30 + 60 * u, front_elbow=90, back_upper=-40 - 30 * u, back_elbow=20, plume=12, mouth="smile")


# --- Yusuf, the water-seller ---------------------------------------------------------------------
def _yusuf_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.4 * w, lean=-2 + w, front_thigh=16, front_knee=10, back_thigh=-14, back_knee=12,
        front_upper=36 + 4 * w, front_elbow=112, back_upper=-24 - 6 * w, back_elbow=30, hem=3 * w, plume=6 * w,
        mouth="smile",
    )


def _yusuf_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=-1 + 4 * math.sin(w), head_dy=0.4 * abs(math.sin(w)), front_thigh=22 * math.sin(w),
        back_thigh=22 * math.sin(w + math.pi), front_knee=10 + 30 * max(0.0, math.cos(w)),
        back_knee=10 + 30 * max(0.0, math.cos(w + math.pi)), front_upper=36, front_elbow=110,
        back_upper=-26 * math.sin(w), back_elbow=30, hem=6 * math.sin(w), plume=8,
    )


def _yusuf_squeeze(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(
        lean=-10 * u, head_tilt=-10 * u, front_thigh=20, front_knee=14, back_thigh=-18, back_knee=16,
        front_upper=50 + 20 * u, front_elbow=100, back_upper=40 + 20 * u, back_elbow=110, hem=2,
        eyes="closed", mouth="o",
    )


def _yusuf_jet(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=12 + w, head_tilt=4, front_thigh=30, front_knee=20, back_thigh=-30, back_knee=24,
                front_upper=82 + 2 * w, front_elbow=24, back_upper=70, back_elbow=60, hem=10, plume=20,
                eyes="wide", mouth="grit")


def _yusuf_fling(i: int, n: int) -> Pose:
    u = _ease(i / max(1, n - 1))
    return Pose(lean=-6 + 16 * u, head_tilt=-4, front_thigh=24, front_knee=16, back_thigh=-22, back_knee=18,
                front_upper=-70 + 190 * u, front_elbow=50 - 46 * u, back_upper=-40 + 20 * u, back_elbow=30,
                hem=8 * u, plume=20 * u, mouth="smile")


def _yusuf_hop(i: int, n: int) -> Pose:
    return Pose(hip_y=HIP_Y - 1, lean=-6, head_tilt=-10, front_thigh=70, front_knee=90, back_thigh=50, back_knee=90,
                front_upper=150, front_elbow=20, back_upper=140, back_elbow=30, hem=14, plume=30, eyes="wide", mouth="open")


def _yusuf_flop(i: int, n: int) -> Pose:
    return Pose(lean=62, head_tilt=-30, front_thigh=-40, front_knee=10, back_thigh=-60, back_knee=20,
                front_upper=150, front_elbow=10, back_upper=130, back_elbow=10, hem=20, plume=36, eyes="closed", mouth="open")


def _yusuf_refill(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(hip_y=HIP_Y + 4, lean=30 + 2 * w, head_tilt=10, front_thigh=60, front_knee=90, back_thigh=10, back_knee=70,
                front_upper=24 + 4 * w, front_elbow=12, back_upper=10, back_elbow=20, hem=4, plume=6, mouth="smile")


# --- Nur, the net-fisher -------------------------------------------------------------------------
def _nur_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.3 * w, lean=3 + w, front_thigh=20, front_knee=16, back_thigh=-16, back_knee=18,
        front_upper=30 + 4 * w, front_elbow=50, back_upper=14, back_elbow=70, hem=4 * w, plume=12 + 10 * w,
    )


def _nur_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=7, head_dy=0.4 * abs(math.sin(w)), front_thigh=32 * math.sin(w), back_thigh=32 * math.sin(w + math.pi),
        front_knee=12 + 44 * max(0.0, math.cos(w)), back_knee=12 + 44 * max(0.0, math.cos(w + math.pi)),
        front_upper=30, front_elbow=50, back_upper=14, back_elbow=70, hem=8 * math.sin(w), plume=20,
    )


def _nur_twirl(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=-2 + 3 * w, head_tilt=-12, front_thigh=26, front_knee=20, back_thigh=-22, back_knee=22,
                front_upper=170, front_elbow=10, back_upper=20, back_elbow=60, hem=12 * w, plume=30 * w, mouth="grit")


def _nur_cast(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(lean=-4 + 18 * u, head_tilt=-6 + 6 * u, front_thigh=20 + 14 * u, front_knee=18, back_thigh=-24, back_knee=24,
                front_upper=170 - 100 * u, front_elbow=10 - 10 * u, back_upper=20 - 50 * u, back_elbow=40,
                hem=16 * u, plume=34 * u, mouth="open")


def _nur_angle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=-6, head_tilt=-26, front_thigh=18, front_knee=14, back_thigh=-20, back_knee=16,
                front_upper=150 + 3 * w, front_elbow=20, back_upper=140 + 3 * w, back_elbow=30, plume=14 * w, eyes="wide")


def _nur_reel(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(lean=-14 * u, head_tilt=-20, front_thigh=30, front_knee=24, back_thigh=-28, back_knee=26,
                front_upper=150 - 60 * u, front_elbow=20 + 70 * u, back_upper=140 - 60 * u, back_elbow=30 + 70 * u,
                hem=10 * u, plume=-20 * u, mouth="grit")


def _nur_plant(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(hip_y=HIP_Y + 3 * u, lean=20 * u, head_tilt=4, front_thigh=40 * u, front_knee=50 * u, back_thigh=-10, back_knee=40 * u,
                front_upper=60, front_elbow=30, back_upper=50, back_elbow=40, hem=6, plume=10)


def _nur_vault(i: int, n: int) -> Pose:
    return Pose(hip_y=HIP_Y - 1, lean=-24, head_tilt=-6, front_thigh=100, front_knee=50, back_thigh=80, back_knee=60,
                front_upper=120, front_elbow=10, back_upper=110, back_elbow=20, hem=24, plume=40, mouth="open")


def _nur_strike(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(lean=14 * u, head_tilt=10, front_thigh=40 - 20 * u, front_knee=30, back_thigh=-20, back_knee=30,
                front_upper=150 - 60 * u, front_elbow=20 - 20 * u, back_upper=130 - 60 * u, back_elbow=20,
                hem=18, plume=30, eyes="wide", mouth="grit")


# --- Hamida, the rain-caller ---------------------------------------------------------------------
def _hamida_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.3 * w, lean=9 + w, head_tilt=-6, front_thigh=10, front_knee=8, back_thigh=-8, back_knee=8,
        front_upper=34, front_elbow=40, back_upper=-10 - 6 * w, back_elbow=40, hem=3 * w, plume=6 * w,
    )


def _hamida_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=10, head_tilt=-6, head_dy=0.3 * abs(math.sin(w)), front_thigh=14 * math.sin(w),
        back_thigh=14 * math.sin(w + math.pi), front_knee=10, back_knee=10, front_upper=34 + 6 * math.sin(w),
        front_elbow=40, back_upper=-12, back_elbow=40, hem=5 * math.sin(w), plume=6,
    )


def _hamida_raise(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=-4, head_tilt=-22, front_thigh=12, front_knee=8, back_thigh=-10, back_knee=8,
                front_upper=168, front_elbow=6, back_upper=96 + 14 * w, back_elbow=30, hem=8 * w, plume=16 * w,
                eyes="closed", mouth="open")


def _hamida_glide(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=-2 + 2 * w, head_tilt=-10, front_thigh=10 + 4 * w, front_knee=12, back_thigh=4 - 4 * w, back_knee=14,
                front_upper=172, front_elbow=0, back_upper=162, back_elbow=10, hem=20 + 8 * w, plume=24 * w, mouth="smile")


def _hamida_spin(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=2, head_tilt=-4, front_thigh=16, front_knee=12, back_thigh=-14, back_knee=12,
                front_upper=92, front_elbow=2, back_upper=-20, back_elbow=60, hem=6 * w, plume=10 * w, mouth="grit")


RiverAnims = dict[str, tuple[PoseFn, int, float, bool]]

_SHARED: RiverAnims = {
    "stunned": (_dizzy, 4, 0.12, True), "hurt": (_hurt, 1, 1.0, True), "defeated": (_defeated, 5, 0.1, False),
    "leap": (_leap, 1, 1.0, True), "land": (_land, 4, 0.08, False), "flail": (_flail, 4, 0.07, True),
    "run": (_run, 6, 0.07, True), "bow": (_bow, 6, 0.12, False),
}
YUSUF_ANIMS: RiverAnims = {
    "idle": (_yusuf_idle, 8, 0.12, True), "walk": (_yusuf_walk, 8, 0.09, True),
    "squeeze": (_yusuf_squeeze, 3, 0.15, False), "jet": (_yusuf_jet, 2, 0.08, True),
    "fling": (_yusuf_fling, 3, 0.06, False), "hop": (_yusuf_hop, 1, 1.0, True), "flop": (_yusuf_flop, 1, 1.0, True),
    "refill": (_yusuf_refill, 4, 0.14, True), **_SHARED,
}
NUR_ANIMS: RiverAnims = {
    "idle": (_nur_idle, 8, 0.1, True), "walk": (_nur_walk, 8, 0.07, True), "twirl": (_nur_twirl, 4, 0.07, True),
    "cast": (_nur_cast, 3, 0.06, False), "angle": (_nur_angle, 4, 0.12, True), "reel": (_nur_reel, 3, 0.07, False),
    "plant": (_nur_plant, 3, 0.06, False), "vault": (_nur_vault, 1, 1.0, True), "strike": (_nur_strike, 3, 0.06, False),
    **_SHARED,
}
HAMIDA_ANIMS: RiverAnims = {
    "idle": (_hamida_idle, 8, 0.14, True), "walk": (_hamida_walk, 8, 0.12, True), "raise": (_hamida_raise, 4, 0.1, True),
    "glide": (_hamida_glide, 4, 0.16, True), "spin": (_hamida_spin, 4, 0.08, True), **_SHARED,
}
ANIMS = {"yusuf": YUSUF_ANIMS, "nur": NUR_ANIMS, "hamida": HAMIDA_ANIMS}
COSTUMES = {"yusuf": YUSUF, "nur": NUR, "hamida": HAMIDA}


def _painter(costume: Costume, anims: RiverAnims):  # noqa: ANN202
    def paint(surface: pygame.Surface, animation: str, frame: int) -> None:
        pose_fn, count, _, _ = anims[animation]
        surface.blit(draw_person(pose_fn(frame, count), costume), (0, 0))
    return paint


def _spec(path: str, costume: Costume, anims: RiverAnims) -> SheetSpec:
    layout = {name: AnimationSpec(row=row, frame_count=count, frame_duration=duration, loop=loop)
              for row, (name, (_, count, duration, loop)) in enumerate(anims.items())}
    return SheetSpec(path, 48, 48, layout, _painter(costume, anims))


YUSUF_SHEET = _spec("river_yusuf.png", YUSUF, YUSUF_ANIMS)
NUR_SHEET = _spec("river_nur.png", NUR, NUR_ANIMS)
HAMIDA_SHEET = _spec("river_hamida.png", HAMIDA, HAMIDA_ANIMS)


@lru_cache(maxsize=None)
def hands(kind: str, animation: str, frame: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """(back hand, front hand) relative to the feet, facing right."""
    anims = ANIMS[kind]
    pose_fn, count, _, _ = anims[animation] if animation in anims else anims["idle"]
    return hand_points(pose_fn(frame % count, count))


@lru_cache(maxsize=None)
def head(kind: str, animation: str, frame: int) -> tuple[float, float]:
    anims = ANIMS[kind]
    pose_fn, count, _, _ = anims[animation] if animation in anims else anims["idle"]
    return head_point(pose_fn(frame % count, count))


@lru_cache(maxsize=64)
def portrait(kind: str, animation: str, frame: int, size: int) -> pygame.Surface:
    """One frame at any size (the manuscript's painted miniatures)."""
    pose_fn, count, _, _ = ANIMS[kind][animation]
    return draw_person(pose_fn(frame % count, count), COSTUMES[kind], size)
