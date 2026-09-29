"""Ready-made particle effects.

Each function describes one effect (a landing dust cloud, a sparkle burst...)
in terms of the generic ParticleSystem, so gameplay code can say
``emitters.landing_dust(world.particles, x, y)`` without knowing particle
physics. All randomness comes from the system's RNG.
"""

import math

from core.settings import Color
from rendering.particles import Kind, ParticleSystem

DUST: Color = (226, 206, 170)
DUST_DARK: Color = (190, 162, 124)
SPARKLE_GOLD: Color = (255, 226, 120)
SPARKLE_WHITE: Color = (255, 250, 230)
SMOKE: Color = (200, 190, 210)
WATER: Color = (170, 220, 255)
WATER_DEEP: Color = (90, 160, 220)
EMBER: Color = (255, 150, 50)
EMBER_HOT: Color = (255, 236, 150)
PETAL_COLORS: tuple[Color, ...] = ((236, 96, 120), (250, 170, 190), (255, 240, 244), (230, 60, 80))


def landing_dust(ps: ParticleSystem, x: float, y: float, strength: float = 1.0, color: Color = DUST) -> None:
    rng = ps.rng
    count = int(6 + 8 * strength)
    for index in range(count):
        side = -1 if index % 2 else 1
        speed = rng.uniform(40, 130) * (0.6 + 0.6 * strength)
        ps.spawn(
            x + side * rng.uniform(2, 8), y - rng.uniform(0, 3),
            side * speed, -rng.uniform(10, 60),
            life=rng.uniform(0.3, 0.55), kind=Kind.SMOKE, size=rng.uniform(3, 5), size_end=rng.uniform(7, 10),
            color=color, drag=5.0, gravity=-30, alpha=0.8, front=False,
        )


def run_dust(ps: ParticleSystem, x: float, y: float, facing: int, color: Color = DUST) -> None:
    rng = ps.rng
    ps.spawn(
        x - facing * 6, y - 2, -facing * rng.uniform(20, 60), -rng.uniform(15, 45),
        life=rng.uniform(0.25, 0.4), kind=Kind.SMOKE, size=2.5, size_end=6,
        color=color, drag=4.0, alpha=0.65, front=False,
    )


def skid_dust(ps: ParticleSystem, x: float, y: float, facing: int, color: Color = DUST) -> None:
    rng = ps.rng
    for _ in range(2):
        ps.spawn(
            x + facing * 8, y - 2, facing * rng.uniform(40, 90), -rng.uniform(20, 70),
            life=rng.uniform(0.25, 0.45), kind=Kind.SMOKE, size=3, size_end=7,
            color=color, drag=5.0, alpha=0.7, front=False,
        )


def jump_puff(ps: ParticleSystem, x: float, y: float, color: Color = DUST) -> None:
    rng = ps.rng
    for side in (-1, 1):
        for _ in range(3):
            ps.spawn(
                x + side * 4, y, side * rng.uniform(30, 80), -rng.uniform(0, 25),
                life=rng.uniform(0.2, 0.35), kind=Kind.SMOKE, size=2.5, size_end=6,
                color=color, drag=6.0, alpha=0.7, front=False,
            )


def wall_dust(ps: ParticleSystem, x: float, y: float, side: int, color: Color = DUST) -> None:
    rng = ps.rng
    ps.spawn(
        x + side * 2, y + rng.uniform(-6, 6), -side * rng.uniform(10, 40), rng.uniform(-30, 10),
        life=rng.uniform(0.2, 0.4), kind=Kind.SMOKE, size=2, size_end=5,
        color=color, drag=4.0, alpha=0.7,
    )


def wall_jump_burst(ps: ParticleSystem, x: float, y: float, side: int, color: Color = DUST) -> None:
    rng = ps.rng
    for _ in range(7):
        angle = rng.uniform(-0.9, 0.9)
        speed = rng.uniform(60, 150)
        ps.spawn(
            x, y + rng.uniform(-8, 8), -side * math.cos(angle) * speed, math.sin(angle) * speed,
            life=rng.uniform(0.25, 0.45), kind=Kind.SMOKE, size=2.5, size_end=6,
            color=color, drag=5.0, alpha=0.75,
        )


def sparkle_burst(
    ps: ParticleSystem, x: float, y: float, color: Color = SPARKLE_GOLD, count: int = 10, speed: float = 140.0
) -> None:
    rng = ps.rng
    for index in range(count):
        angle = math.tau * index / count + rng.uniform(-0.3, 0.3)
        velocity = rng.uniform(0.4, 1.0) * speed
        ps.spawn(
            x, y, math.cos(angle) * velocity, math.sin(angle) * velocity,
            life=rng.uniform(0.35, 0.7), kind=Kind.TWINKLE, size=rng.uniform(3, 5),
            color=color, color_end=SPARKLE_WHITE, drag=3.5, gravity=60,
        )


def coin_collect(ps: ParticleSystem, x: float, y: float) -> None:
    sparkle_burst(ps, x, y, SPARKLE_GOLD, 8, 110)
    ps.spawn(x, y, life=0.35, kind=Kind.GLOW, size=22, size_end=22, color=(255, 200, 80), alpha=0.9)
    ps.spawn(x, y, life=0.3, kind=Kind.RING, size=4, size_end=18, color=SPARKLE_GOLD)


def smoke_poof(ps: ParticleSystem, x: float, y: float, color: Color = SMOKE, count: int = 12) -> None:
    rng = ps.rng
    for index in range(count):
        angle = math.tau * index / count + rng.uniform(-0.2, 0.2)
        speed = rng.uniform(40, 110)
        ps.spawn(
            x, y, math.cos(angle) * speed, math.sin(angle) * speed - 20,
            life=rng.uniform(0.35, 0.6), kind=Kind.SMOKE, size=rng.uniform(4, 6), size_end=rng.uniform(9, 13),
            color=color, drag=4.0, gravity=-40, alpha=0.85,
        )
    sparkle_burst(ps, x, y, SPARKLE_WHITE, 5, 90)


def stomp_impact(ps: ParticleSystem, x: float, y: float) -> None:
    rng = ps.rng
    ps.spawn(x, y, life=0.22, kind=Kind.RING, size=4, size_end=26, color=(255, 255, 255))
    for side in (-1, 1):
        for _ in range(3):
            ps.spawn(
                x, y, side * rng.uniform(80, 160), -rng.uniform(20, 90),
                life=rng.uniform(0.2, 0.35), kind=Kind.SPARK, size=rng.uniform(8, 12),
                color=(255, 250, 220), color_end=(255, 200, 120), drag=6.0,
            )


def debris(ps: ParticleSystem, x: float, y: float, colors: tuple[Color, ...], count: int = 10, power: float = 1.0) -> None:
    rng = ps.rng
    for _ in range(count):
        angle = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
        speed = rng.uniform(120, 300) * power
        ps.spawn(
            x + rng.uniform(-10, 10), y + rng.uniform(-10, 10),
            math.cos(angle) * speed, math.sin(angle) * speed,
            life=rng.uniform(0.6, 1.1), kind=Kind.SQUARE, size=rng.uniform(3, 7), size_end=2,
            color=rng.choice(colors), gravity=1400,
        )


def splash(ps: ParticleSystem, x: float, y: float, strength: float = 1.0, color: Color = WATER) -> None:
    rng = ps.rng
    for _ in range(int(14 * strength) + 4):
        angle = rng.uniform(-math.pi * 0.85, -math.pi * 0.15)
        speed = rng.uniform(100, 320) * strength
        ps.spawn(
            x + rng.uniform(-8, 8), y, math.cos(angle) * speed, math.sin(angle) * speed,
            life=rng.uniform(0.45, 0.8), kind=Kind.DOT, size=rng.uniform(2, 3.5), size_end=1,
            color=color, color_end=WATER_DEEP, gravity=1200,
        )
    ps.spawn(x, y, life=0.45, kind=Kind.RING, size=4, size_end=30 * strength, color=(220, 240, 255))


def droplet(ps: ParticleSystem, x: float, y: float, vx: float, vy: float, color: Color = WATER) -> None:
    ps.spawn(
        x, y, vx, vy, life=ps.rng.uniform(0.5, 0.9), kind=Kind.DOT, size=2.2, size_end=1,
        color=color, color_end=WATER_DEEP, gravity=900,
    )


def embers(ps: ParticleSystem, x: float, y: float, count: int = 1, spread: float = 6.0) -> None:
    rng = ps.rng
    for _ in range(count):
        ps.spawn(
            x + rng.uniform(-spread, spread), y, rng.uniform(-15, 15), -rng.uniform(40, 90),
            life=rng.uniform(0.5, 1.1), kind=Kind.GLOW, size=rng.uniform(3, 6), size_end=2,
            color=EMBER_HOT, color_end=EMBER, wobble=30, alpha=0.9,
        )


def fire_trail(ps: ParticleSystem, x: float, y: float) -> None:
    rng = ps.rng
    ps.spawn(
        x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), rng.uniform(-20, 20), -rng.uniform(10, 50),
        life=rng.uniform(0.25, 0.45), kind=Kind.GLOW, size=rng.uniform(5, 8), size_end=2,
        color=EMBER_HOT, color_end=(200, 60, 20), alpha=0.9,
    )


def magic_trail(ps: ParticleSystem, x: float, y: float, color: Color = (140, 200, 255)) -> None:
    rng = ps.rng
    ps.spawn(
        x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), rng.uniform(-15, 15), rng.uniform(-15, 15),
        life=rng.uniform(0.25, 0.45), kind=Kind.TWINKLE, size=rng.uniform(2, 4),
        color=color, color_end=SPARKLE_WHITE, drag=2.0,
    )


def petal_shower(ps: ParticleSystem, x: float, y: float, count: int = 30) -> None:
    rng = ps.rng
    for _ in range(count):
        angle = rng.uniform(-math.pi * 0.9, -math.pi * 0.1)
        speed = rng.uniform(150, 380)
        ps.spawn(
            x, y, math.cos(angle) * speed, math.sin(angle) * speed,
            life=rng.uniform(1.4, 2.4), kind=Kind.PETAL, size=rng.uniform(2.5, 4), size_end=2,
            color=rng.choice(PETAL_COLORS), gravity=260, drag=1.6, wobble=60,
        )


def shockwave(ps: ParticleSystem, x: float, y: float, radius: float = 60.0, color: Color = (255, 240, 200)) -> None:
    ps.spawn(x, y, life=0.4, kind=Kind.RING, size=6, size_end=radius, color=color)


def aura(ps: ParticleSystem, x: float, y: float, color: Color, spread: float = 12.0) -> None:
    rng = ps.rng
    ps.spawn(
        x + rng.uniform(-spread, spread), y + rng.uniform(-spread, spread), 0, -rng.uniform(20, 50),
        life=rng.uniform(0.4, 0.8), kind=Kind.TWINKLE, size=rng.uniform(1.5, 3), color=color,
        color_end=SPARKLE_WHITE,
    )
