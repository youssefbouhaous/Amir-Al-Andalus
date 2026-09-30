"""A lightweight particle system for purely visual effects.

Particles are plain slotted objects in two lists: one drawn behind the
entities (dust at the feet, splashes) and one in front (sparkles, embers).
They never affect gameplay, so they are free to be numerous and short-lived.
Presets that build common effects (dust puffs, sparkles, smoke...) live in
``rendering/emitters.py``; this module only simulates and draws.
"""

import math
import random
from enum import IntEnum

import pygame

from core import settings
from core.settings import Color
from rendering.glow import blit_glow, soft_circle

CULL_MARGIN = 64
ROTATION_STEPS = 16


class Kind(IntEnum):
    DOT = 0      # solid circle that shrinks
    SQUARE = 1   # solid square (chunky pixel debris)
    GLOW = 2     # additive radial light
    SPARK = 3    # streak along the velocity
    SMOKE = 4    # translucent soft puff that grows and fades
    IMAGE = 5    # rotating sprite (debris, leaves)
    TWINKLE = 6  # four-pointed sparkle star
    PETAL = 7    # tumbling ellipse (petals, confetti, snow)
    RING = 8     # expanding circle outline (shockwaves)


class Particle:
    __slots__ = (
        "x", "y", "vx", "vy", "gravity", "drag", "life", "age", "size", "size_end",
        "color", "color_end", "kind", "angle", "spin", "image", "alpha", "wobble", "phase",
    )

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.gravity = self.drag = 0.0
        self.life = 1.0
        self.age = 0.0
        self.size = self.size_end = 1.0
        self.color: Color = (255, 255, 255)
        self.color_end: Color = (255, 255, 255)
        self.kind = Kind.DOT
        self.angle = self.spin = 0.0
        self.image: pygame.Surface | None = None
        self.alpha = 1.0
        self.wobble = 0.0
        self.phase = 0.0


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    if a is b:
        return a
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


_rotation_cache: dict[tuple[int, int], pygame.Surface] = {}


def _rotated(image: pygame.Surface, angle: float) -> pygame.Surface:
    step = int(angle / 360.0 * ROTATION_STEPS) % ROTATION_STEPS
    key = (id(image), step)
    rotated = _rotation_cache.get(key)
    if rotated is None:
        if len(_rotation_cache) > 2000:
            _rotation_cache.clear()
        rotated = pygame.transform.rotate(image, step * 360.0 / ROTATION_STEPS)
        _rotation_cache[key] = rotated
    return rotated


class ParticleSystem:
    def __init__(self, max_particles: int = settings.MAX_PARTICLES) -> None:
        self.back: list[Particle] = []
        self.front: list[Particle] = []
        self._max = max_particles
        self.rng = random.Random()

    def __len__(self) -> int:
        return len(self.back) + len(self.front)

    def spawn(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        *,
        life: float = 0.6,
        kind: Kind = Kind.DOT,
        size: float = 3.0,
        size_end: float | None = None,
        color: Color = (255, 255, 255),
        color_end: Color | None = None,
        gravity: float = 0.0,
        drag: float = 0.0,
        front: bool = True,
        angle: float = 0.0,
        spin: float = 0.0,
        image: pygame.Surface | None = None,
        alpha: float = 1.0,
        wobble: float = 0.0,
    ) -> Particle | None:
        if len(self.back) + len(self.front) >= self._max:
            return None
        p = Particle()
        p.x, p.y, p.vx, p.vy = x, y, vx, vy
        p.life = max(0.01, life)
        p.kind = kind
        p.size = size
        p.size_end = 0.0 if size_end is None else size_end
        p.color = color
        p.color_end = color if color_end is None else color_end
        p.gravity, p.drag = gravity, drag
        p.angle, p.spin = angle, spin
        p.image = image
        p.alpha = alpha
        p.wobble = wobble
        p.phase = self.rng.random() * math.tau
        (self.front if front else self.back).append(p)
        return p

    def clear(self) -> None:
        self.back.clear()
        self.front.clear()

    def update(self, dt: float) -> None:
        self.back = self._update_list(self.back, dt)
        self.front = self._update_list(self.front, dt)

    @staticmethod
    def _update_list(particles: list[Particle], dt: float) -> list[Particle]:
        alive = []
        for p in particles:
            p.age += dt
            if p.age >= p.life:
                continue
            if p.drag:
                factor = max(0.0, 1.0 - p.drag * dt)
                p.vx *= factor
                p.vy *= factor
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            if p.wobble:
                p.x += math.sin(p.age * 3.0 + p.phase) * p.wobble * dt
            p.y += p.vy * dt
            p.angle += p.spin * dt
            alive.append(p)
        return alive

    def draw(self, surface: pygame.Surface, offset: tuple[int, int], front: bool) -> None:
        particles = self.front if front else self.back
        if not particles:
            return
        ox, oy = offset
        width, height = surface.get_size()
        draw_circle = pygame.draw.circle
        fill = surface.fill
        for p in particles:
            sx = p.x - ox
            sy = p.y - oy
            if sx < -CULL_MARGIN or sy < -CULL_MARGIN or sx > width + CULL_MARGIN or sy > height + CULL_MARGIN:
                continue
            t = p.age / p.life
            size = p.size + (p.size_end - p.size) * t
            kind = p.kind
            if kind == Kind.DOT:
                if size < 0.5:
                    continue
                color = _lerp_color(p.color, p.color_end, t)
                if size < 1.5:
                    fill(color, (int(sx), int(sy), 2, 2))
                else:
                    draw_circle(surface, color, (int(sx), int(sy)), int(size))
            elif kind == Kind.SQUARE:
                if size < 0.5:
                    continue
                s = max(1, int(size))
                fill(_lerp_color(p.color, p.color_end, t), (int(sx - s / 2), int(sy - s / 2), s, s))
            elif kind == Kind.GLOW:
                strength = p.alpha * (1.0 - t) if p.size_end == p.size else p.alpha * (1.0 - t * 0.6)
                blit_glow(surface, (sx, sy), max(2, int(size)), _lerp_color(p.color, p.color_end, t), strength)
            elif kind == Kind.SPARK:
                length = 0.02 * size
                end = (sx - p.vx * length, sy - p.vy * length)
                pygame.draw.line(
                    surface, _lerp_color(p.color, p.color_end, t), (sx, sy), end, max(1, int(size * 0.25))
                )
            elif kind == Kind.SMOKE:
                image = soft_circle(max(2, int(size)), _lerp_color(p.color, p.color_end, t), p.alpha * (1.0 - t))
                if image is not None:
                    radius = image.get_width() // 2
                    surface.blit(image, (int(sx) - radius, int(sy) - radius))
            elif kind == Kind.IMAGE and p.image is not None:
                image = _rotated(p.image, p.angle) if p.spin else p.image
                if p.alpha < 1.0 or t > 0.7:
                    fade = p.alpha * min(1.0, (1.0 - t) / 0.3)
                    image.set_alpha(int(255 * fade))
                    surface.blit(image, image.get_rect(center=(int(sx), int(sy))))
                    # Not set_alpha(None): that strips per-pixel alpha from the (cached) image.
                    image.set_alpha(255)
                else:
                    surface.blit(image, image.get_rect(center=(int(sx), int(sy))))
            elif kind == Kind.TWINKLE:
                pulse = abs(math.sin(p.age * 14.0 + p.phase))
                arm = size * (0.4 + 0.6 * pulse) * (1.0 - t * 0.5)
                if arm < 0.8:
                    continue
                color = _lerp_color(p.color, p.color_end, t)
                ix, iy = int(sx), int(sy)
                pygame.draw.line(surface, color, (ix - arm, iy), (ix + arm, iy))
                pygame.draw.line(surface, color, (ix, iy - arm), (ix, iy + arm))
                blit_glow(surface, (sx, sy), max(3, int(arm * 1.6)), color, 0.6 * (1.0 - t))
            elif kind == Kind.PETAL:
                if size < 0.5:
                    continue
                turn = abs(math.cos(p.age * 5.0 + p.phase))
                w = max(1, int(size * 2 * (0.25 + 0.75 * turn)))
                h = max(1, int(size * 1.3))
                pygame.draw.ellipse(
                    surface, _lerp_color(p.color, p.color_end, t), (int(sx - w / 2), int(sy - h / 2), w, h)
                )
            elif kind == Kind.RING:
                radius = int(size)
                if radius >= 1:
                    thickness = max(1, int(3 * (1.0 - t)) + 1)
                    draw_circle(surface, _lerp_color(p.color, p.color_end, t), (int(sx), int(sy)), radius, thickness)
