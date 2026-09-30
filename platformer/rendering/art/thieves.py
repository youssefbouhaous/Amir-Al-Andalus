"""The Gilded Thieves' animations: poses for Tariq, Samira and Hakim.

Every animation is a function from (frame, frame count) to a ``Pose`` on the
prince's rig, rendered once into a sprite sheet (like the prince's own
frames). Props - Tariq's mirror, Samira's torch and fire poi, Hakim's gourd
flute and baskets - are drawn by the entities at the hand points given here,
so they can glint, burn and move freely.
"""

import math
from collections.abc import Callable
from functools import lru_cache

import pygame

from rendering.art.people import HAKIM, SAMIRA, TARIQ, Costume, draw_person, hand_points, head_point
from rendering.art.prince import HIP_Y, Pose
from rendering.art.troupe import _defeated, _hurt
from rendering.sprite_library import AnimationSpec, SheetSpec

PoseFn = Callable[[int, int], Pose]


def _wave(i: int, n: int, phase: float = 0.0) -> float:
    return math.sin(math.tau * i / max(1, n) + phase)


def _ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# --- shared ------------------------------------------------------------------------------------
def _blinded(i: int, n: int) -> Pose:
    """Night-ink in the eyes: rubbing them with both hands, staggering."""
    w = _wave(i, n)
    return Pose(
        lean=10 + 4 * w, head_tilt=16 + 6 * w, head_dy=0.5,
        front_thigh=14 + 8 * w, front_knee=18, back_thigh=-10 - 8 * w, back_knee=20,
        front_upper=112 + 10 * w, front_elbow=88, back_upper=104 - 10 * w, back_elbow=96,
        hem=6 * w, plume=16 * w, eyes="closed", mouth="grit",
    )


def _leap(i: int, n: int) -> Pose:
    """Tucked for a somersault (the entity spins the sprite)."""
    return Pose(hip_y=HIP_Y - 2, lean=20, head_tilt=20, front_thigh=110, front_knee=130, back_thigh=96, back_knee=126,
                front_upper=70, front_elbow=70, back_upper=60, back_elbow=80, hem=18, plume=30, eyes="closed")


def _land(i: int, n: int) -> Pose:
    u = i / max(1, n - 1)
    crouch = 1 - _ease(u)
    return Pose(
        hip_y=HIP_Y + 5 * crouch, lean=18 * crouch,
        front_thigh=20 + 50 * crouch, front_knee=10 + 90 * crouch, back_thigh=-10 + 40 * crouch, back_knee=10 + 80 * crouch,
        front_upper=40 + 80 * u, front_elbow=20, back_upper=-40 - 60 * u, back_elbow=20,
        hem=10 * crouch, plume=20, mouth="smile" if u > 0.6 else "none",
    )


# --- Tariq, the mirror-thief ---------------------------------------------------------------------
def _tariq_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.3 * w, lean=2 + w, front_thigh=18, front_knee=14, back_thigh=-16, back_knee=16,
        front_upper=64 + 3 * w, front_elbow=38, back_upper=-18 - 4 * w, back_elbow=28, hem=2 * w, plume=10 + 8 * w,
    )


def _tariq_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=6, head_dy=0.4 * abs(math.sin(w)), front_thigh=28 * math.sin(w), back_thigh=28 * math.sin(w + math.pi),
        front_knee=10 + 40 * max(0.0, math.cos(w)), back_knee=10 + 40 * max(0.0, math.cos(w + math.pi)),
        front_upper=62, front_elbow=38, back_upper=-20 * math.sin(w), back_elbow=24, hem=6 * math.sin(w), plume=14,
    )


def _tariq_raise(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(
        lean=-4 * u, head_tilt=-18 * u, front_thigh=16, front_knee=12, back_thigh=-18, back_knee=16,
        front_upper=64 + 96 * u, front_elbow=38 - 30 * u, back_upper=-20 - 20 * u, back_elbow=30, plume=16,
    )


def _tariq_aim(i: int, n: int) -> Pose:
    return Pose(lean=-3, head_tilt=-4, front_thigh=24, front_knee=16, back_thigh=-22, back_knee=18,
                front_upper=92, front_elbow=2, back_upper=-40, back_elbow=40, plume=18, eyes="wide")


def _tariq_fire(i: int, n: int) -> Pose:
    kick = 1 - i / max(1, n - 1)
    return Pose(lean=-10 * kick, head_tilt=-8, front_thigh=26, front_knee=18, back_thigh=-24, back_knee=22,
                front_upper=96 + 10 * kick, front_elbow=0, back_upper=-50, back_elbow=40, hem=8 * kick, plume=28 * kick,
                mouth="grit")


def _tariq_dash(i: int, n: int) -> Pose:
    return Pose(hip_y=HIP_Y + 3, lean=26, head_tilt=8, front_thigh=70, front_knee=60, back_thigh=-50, back_knee=20,
                front_upper=80, front_elbow=20, back_upper=-80, back_elbow=10, hem=18, plume=40)


def _tariq_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(lean=24 * u, head_tilt=14 * u, front_thigh=10, front_knee=6, back_thigh=-8, back_knee=6,
                front_upper=30 + 10 * u, front_elbow=110, back_upper=-40 - 40 * u, back_elbow=20, plume=12, mouth="smile")


# --- Samira, the fire-eater ------------------------------------------------------------------------
def _samira_idle(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        head_dy=0.4 * w, lean=2 * w, front_thigh=14 + 6 * w, front_knee=10, back_thigh=-10 + 6 * w, back_knee=12,
        front_upper=70 + 45 * w, front_elbow=20, back_upper=70 - 45 * w, back_elbow=20,
        hem=10 * w, plume=24 * w, mouth="smile",
    )


def _samira_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=4, head_dy=0.5 * abs(math.sin(w)), front_thigh=32 * math.sin(w), back_thigh=32 * math.sin(w + math.pi),
        front_knee=12 + 44 * max(0.0, math.cos(w)), back_knee=12 + 44 * max(0.0, math.cos(w + math.pi)),
        front_upper=80 + 40 * math.sin(w), front_elbow=20, back_upper=80 - 40 * math.sin(w), back_elbow=20,
        hem=14 * math.sin(w), plume=26 * math.sin(w),
    )


def _samira_inhale(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(lean=-12 * u, head_tilt=-22 * u, front_thigh=16, front_knee=12, back_thigh=-14, back_knee=16,
                front_upper=60, front_elbow=100 - 10 * u, back_upper=-30 - 20 * u, back_elbow=30, hem=4, plume=-10 * u,
                eyes="closed", mouth="o")


def _samira_breathe(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(lean=14 + 2 * w, head_tilt=6, front_thigh=30, front_knee=20, back_thigh=-26, back_knee=18,
                front_upper=78, front_elbow=40, back_upper=-60, back_elbow=30, hem=12, plume=30, eyes="wide", mouth="open")


def _samira_whirl(i: int, n: int) -> Pose:
    front = i % 3 == 1
    w = _wave(i, n)
    return Pose(
        view="front" if front else "side", lean=0 if front else 6 * w,
        front_thigh=20 + 20 * w, front_knee=30, back_thigh=-10, back_knee=20,
        front_upper=96, front_elbow=0, back_upper=96, back_elbow=0, hem=40 * w, plume=50 * w, mouth="smile",
    )


def _samira_kick(i: int, n: int) -> Pose:
    u = math.sin(math.pi * (i + 1) / (n + 1))
    return Pose(lean=-14 * u, head_tilt=-6 * u, front_thigh=20 + 90 * u, front_knee=30 - 24 * u, back_thigh=-8, back_knee=8,
                front_upper=40 + 60 * u, front_elbow=20, back_upper=-70 * u, back_elbow=20, hem=30 * u, plume=30 * u,
                mouth="smile")


def _samira_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(hip_y=HIP_Y + 2 * u, lean=12 * u, head_tilt=12 * u, front_thigh=-10, front_knee=40 * u, back_thigh=10,
                back_knee=50 * u, front_upper=40, front_elbow=20, back_upper=40, back_elbow=20, hem=18 * u, mouth="smile")


# --- Hakim, the snake-charmer ---------------------------------------------------------------------
def _hakim_play(i: int, n: int) -> Pose:
    w = _wave(i, n)
    return Pose(
        lean=5 * w, head_tilt=-6 + 4 * w, head_dy=0.3 * w, front_thigh=10, front_knee=8, back_thigh=-8, back_knee=8,
        front_upper=62, front_elbow=104, back_upper=54, back_elbow=110, hem=6 * w, plume=18 * w, eyes="closed",
    )


def _hakim_walk(i: int, n: int) -> Pose:
    w = math.tau * i / n
    return Pose(
        lean=6, head_dy=0.3 * abs(math.sin(w)), front_thigh=18 * math.sin(w), back_thigh=18 * math.sin(w + math.pi),
        front_knee=10, back_knee=10, front_upper=62, front_elbow=104, back_upper=54, back_elbow=110,
        hem=6 * math.sin(w), plume=12 * math.sin(w),
    )


def _hakim_summon(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(lean=-8 * u, head_tilt=-20 * u, front_thigh=12, front_knee=8, back_thigh=-10, back_knee=8,
                front_upper=62 + 100 * u, front_elbow=104 - 94 * u, back_upper=54 + 90 * u, back_elbow=110 - 100 * u,
                hem=10 * u, plume=30 * u, eyes="wide", mouth="open")


def _hakim_dive(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(hip_y=HIP_Y + 8 * u, lean=20 * u, head_tilt=20 * u, front_thigh=20 + 70 * u, front_knee=20 + 100 * u,
                back_thigh=10 + 60 * u, back_knee=20 + 100 * u, front_upper=160 * u, front_elbow=10, back_upper=150 * u,
                back_elbow=10, hem=10, eyes="closed")


def _hakim_pop(i: int, n: int) -> Pose:
    u = _ease((i + 1) / n)
    return Pose(hip_y=HIP_Y + 6 * (1 - u), lean=-6 * u, head_tilt=-10 * u, front_thigh=40 * (1 - u), front_knee=60 * (1 - u),
                back_thigh=30 * (1 - u), back_knee=60 * (1 - u), front_upper=150, front_elbow=10, back_upper=140,
                back_elbow=10, hem=16 * u, plume=30 * u, eyes="wide", mouth="open")


def _hakim_bow(i: int, n: int) -> Pose:
    u = math.sin(math.pi * i / max(1, n - 1))
    return Pose(lean=22 * u, head_tilt=14 * u, front_thigh=8, front_knee=6, back_thigh=-8, back_knee=6,
                front_upper=100 + 20 * u, front_elbow=90, back_upper=-30, back_elbow=20, plume=10, mouth="smile")


ThiefAnims = dict[str, tuple[PoseFn, int, float, bool]]

_SHARED: ThiefAnims = {
    "stunned": (_blinded, 4, 0.12, True), "hurt": (_hurt, 1, 1.0, True), "defeated": (_defeated, 5, 0.1, False),
    "leap": (_leap, 1, 1.0, True), "land": (_land, 4, 0.08, False),
}
TARIQ_ANIMS: ThiefAnims = {
    "idle": (_tariq_idle, 8, 0.11, True), "walk": (_tariq_walk, 8, 0.08, True), "raise": (_tariq_raise, 3, 0.08, False),
    "aim": (_tariq_aim, 1, 1.0, True), "fire": (_tariq_fire, 3, 0.06, False), "dash": (_tariq_dash, 1, 1.0, True),
    "bow": (_tariq_bow, 6, 0.12, False), **_SHARED,
}
SAMIRA_ANIMS: ThiefAnims = {
    "idle": (_samira_idle, 8, 0.09, True), "walk": (_samira_walk, 8, 0.07, True), "inhale": (_samira_inhale, 3, 0.15, False),
    "breathe": (_samira_breathe, 2, 0.08, True), "whirl": (_samira_whirl, 6, 0.05, True), "kick": (_samira_kick, 4, 0.07, False),
    "bow": (_samira_bow, 6, 0.12, False), **_SHARED,
}
HAKIM_ANIMS: ThiefAnims = {
    "idle": (_hakim_play, 8, 0.13, True), "walk": (_hakim_walk, 8, 0.11, True), "summon": (_hakim_summon, 4, 0.1, False),
    "dive": (_hakim_dive, 4, 0.07, False), "pop": (_hakim_pop, 4, 0.07, False), "bow": (_hakim_bow, 6, 0.12, False),
    **_SHARED,
}
ANIMS = {"tariq": TARIQ_ANIMS, "samira": SAMIRA_ANIMS, "hakim": HAKIM_ANIMS}
COSTUMES = {"tariq": TARIQ, "samira": SAMIRA, "hakim": HAKIM}


def _painter(costume: Costume, anims: ThiefAnims):  # noqa: ANN202
    def paint(surface: pygame.Surface, animation: str, frame: int) -> None:
        pose_fn, count, _, _ = anims[animation]
        image = draw_person(pose_fn(frame, count), costume)
        if animation == "whirl" and frame % 3 == 2:
            image = pygame.transform.flip(image, True, False)
        surface.blit(image, (0, 0))
    return paint


def _spec(path: str, costume: Costume, anims: ThiefAnims) -> SheetSpec:
    layout = {name: AnimationSpec(row=row, frame_count=count, frame_duration=duration, loop=loop)
              for row, (name, (_, count, duration, loop)) in enumerate(anims.items())}
    return SheetSpec(path, 48, 48, layout, _painter(costume, anims))


TARIQ_SHEET = _spec("thief_tariq.png", TARIQ, TARIQ_ANIMS)
SAMIRA_SHEET = _spec("thief_samira.png", SAMIRA, SAMIRA_ANIMS)
HAKIM_SHEET = _spec("thief_hakim.png", HAKIM, HAKIM_ANIMS)


@lru_cache(maxsize=None)
def hands(kind: str, animation: str, frame: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """(back hand, front hand) relative to the feet, facing right."""
    pose_fn, count, _, _ = ANIMS[kind][animation]
    return hand_points(pose_fn(frame % count, count))


@lru_cache(maxsize=None)
def head(kind: str, animation: str, frame: int) -> tuple[float, float]:
    pose_fn, count, _, _ = ANIMS[kind][animation]
    return head_point(pose_fn(frame % count, count))


@lru_cache(maxsize=64)
def portrait(kind: str, animation: str, frame: int, size: int) -> pygame.Surface:
    """One thief frame at any size (the manuscript's painted miniatures)."""
    pose_fn, count, _, _ = ANIMS[kind][animation]
    return draw_person(pose_fn(frame % count, count), COSTUMES[kind], size)
