"""A fixed golden rosette: the prince supplies the scarf/pendulum rope."""

import math

import pygame

from objects.rings import Ring, GOLD, GOLD_LIGHT
from rendering.glow import blit_glow
from rendering.lighting import Light


class GrappleHook(Ring):
    is_grapple_hook = True
    REACH = 210.0

    def __init__(self, anchor):
        super().__init__(anchor, 80)
        self.rect = pygame.Rect(round(anchor[0]) - 16, round(anchor[1]) - 16, 32, 32)

    def prepare(self, hand):
        delta = pygame.Vector2(hand) - self.anchor
        self.length = max(30, delta.length())
        self.angle = math.atan2(delta.x, delta.y)

    def update(self, dt, world):
        self._time += dt
        self._cooldown = max(0.0, self._cooldown - dt)

    def lights(self):
        return [Light(*self.anchor, 65, GOLD_LIGHT, .65)]

    def draw(self, surface, camera):
        x, y = camera.to_screen(*self.anchor)
        blit_glow(surface, (x, y), 24, GOLD, .45 + .15 * math.sin(self._time * 3))
        for i in range(8):
            a = i * math.pi / 4 + self._time * .15
            point = (round(x + math.cos(a) * 11), round(y + math.sin(a) * 11))
            pygame.draw.line(surface, GOLD, (x, y), point, 3)
        pygame.draw.circle(surface, (55, 40, 49), (x, y), 8)
        pygame.draw.circle(surface, GOLD_LIGHT, (x, y), 7, 2)
        pygame.draw.circle(surface, GOLD, (x, y), 3)
