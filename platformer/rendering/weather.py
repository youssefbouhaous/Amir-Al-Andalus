"""Ambient weather in screen space: petals, sunlit motes, snow, fireflies, embers.

Particles live in a virtual screen-sized box and are drawn with a parallax
factor ``z`` (their depth), wrapping around as the camera moves, so a fixed
number of particles can fill an endless level. Deep ones (z < 1) are drawn
behind the world, near ones in front of it.
"""

import math
import random

import pygame

from core.settings import Color
from rendering.glow import blit_glow

MARGIN = 40
PETAL_COLORS: tuple[Color, ...] = ((244, 150, 170), (255, 214, 224), (255, 244, 246), (236, 110, 136))


class _Flake:
    __slots__ = ("x", "y", "z", "vx", "vy", "phase", "color", "size")

    def __init__(self, x: float, y: float, z: float, vx: float, vy: float, phase: float, color: Color, size: float) -> None:
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy = vx, vy
        self.phase = phase
        self.color = color
        self.size = size


class Weather:
    def __init__(self, kinds: tuple[str, ...], screen_size: tuple[int, int], seed: int = 5) -> None:
        self._size = screen_size
        self._kinds = kinds
        self._rng = random.Random(seed)
        self._time = 0.0
        self.wind = 0.0
        self._flakes: dict[str, list[_Flake]] = {kind: self._spawn(kind) for kind in kinds}

    def _spawn(self, kind: str) -> list[_Flake]:
        width, height = self._size
        rng = self._rng
        flakes = []
        count = {"petals": 34, "motes": 40, "snow": 150, "fireflies": 26, "embers": 40, "leaves": 26}.get(kind, 20)
        for _ in range(count):
            z = rng.uniform(0.4, 1.6)
            x, y = rng.uniform(0, width), rng.uniform(0, height)
            phase = rng.uniform(0, math.tau)
            if kind == "petals":
                flakes.append(_Flake(x, y, z, -rng.uniform(15, 40), rng.uniform(22, 44), phase, rng.choice(PETAL_COLORS), rng.uniform(1.8, 3.0)))
            elif kind == "motes":
                flakes.append(_Flake(x, y, z, rng.uniform(-6, 6), rng.uniform(-8, -2), phase, (255, 236, 180), rng.uniform(1.0, 2.2)))
            elif kind == "snow":
                flakes.append(_Flake(x, y, z, -rng.uniform(5, 20), rng.uniform(30, 70), phase, (250, 252, 255), rng.uniform(0.8, 2.4)))
            elif kind == "fireflies":
                flakes.append(_Flake(x, y, z, 0.0, 0.0, phase, (220, 255, 140), rng.uniform(1.4, 2.4)))
            elif kind == "embers":
                flakes.append(_Flake(x, y, z, rng.uniform(-10, 10), -rng.uniform(20, 55), phase, (255, 150, 60), rng.uniform(1.2, 2.6)))
            else:
                flakes.append(_Flake(x, y, z, -rng.uniform(20, 50), rng.uniform(30, 60), phase, (200, 120, 40), rng.uniform(2.0, 3.2)))
        return flakes

    def update(self, dt: float) -> None:
        self._time += dt
        width, height = self._size
        for kind, flakes in self._flakes.items():
            for f in flakes:
                if kind == "fireflies":
                    f.x += math.cos(self._time * 0.6 + f.phase) * 14 * dt
                    f.y += math.sin(self._time * 0.9 + f.phase * 1.7) * 10 * dt
                else:
                    sway = math.sin(self._time * 1.6 + f.phase) * (18 if kind in ("petals", "leaves", "snow") else 6)
                    f.x += (f.vx + sway + self.wind * (1.0 if kind in ("snow", "petals", "leaves") else 0.3)) * f.z * dt
                    f.y += f.vy * f.z * dt
                if f.y > height + MARGIN:
                    f.y -= height + MARGIN * 2
                elif f.y < -MARGIN:
                    f.y += height + MARGIN * 2

    def draw(self, surface: pygame.Surface, offset: tuple[float, float], front: bool) -> None:
        width, height = self._size
        span_x = width + MARGIN * 2
        span_y = height + MARGIN * 2
        ox, oy = offset
        for kind, flakes in self._flakes.items():
            for f in flakes:
                if (f.z >= 1.0) != front:
                    continue
                sx = (f.x - ox * f.z * 0.6) % span_x - MARGIN
                sy = (f.y - oy * f.z * 0.3) % span_y - MARGIN
                size = f.size * (0.6 + 0.4 * f.z)
                if kind == "petals" or kind == "leaves":
                    turn = abs(math.cos(self._time * 4.0 + f.phase))
                    w = max(1, int(size * 2 * (0.3 + 0.7 * turn)))
                    h = max(1, int(size * 1.3))
                    pygame.draw.ellipse(surface, f.color, (int(sx - w / 2), int(sy - h / 2), w, h))
                elif kind == "snow":
                    s = max(1, int(size))
                    if s <= 1:
                        surface.fill(f.color, (int(sx), int(sy), 1, 1))
                    else:
                        pygame.draw.circle(surface, f.color, (int(sx), int(sy)), s)
                elif kind == "motes":
                    twinkle = 0.5 + 0.5 * math.sin(self._time * 2.0 + f.phase)
                    blit_glow(surface, (sx, sy), int(4 + size * 2), f.color, 0.35 + 0.4 * twinkle)
                elif kind == "fireflies":
                    pulse = max(0.0, math.sin(self._time * 2.4 + f.phase))
                    if pulse > 0.05:
                        blit_glow(surface, (sx, sy), int(6 + size * 3), f.color, pulse)
                        surface.fill((255, 255, 210), (int(sx), int(sy), 2, 2))
                elif kind == "embers":
                    flicker = 0.6 + 0.4 * math.sin(self._time * 7.0 + f.phase)
                    blit_glow(surface, (sx, sy), int(3 + size * 2), f.color, flicker)
