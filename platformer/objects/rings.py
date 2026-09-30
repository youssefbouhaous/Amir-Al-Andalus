"""Golden swing rings hanging from ropes.

A ring is a pendulum: an anchor, a rope length and an angle. Left alone it
sways gently; when the prince grabs it, his momentum becomes the swing's
angular velocity and LEFT/RIGHT pump it higher. Jumping off keeps the swing's
velocity plus a kick upward, which is how chains of rings fling him across
chasms.
"""

import math
from typing import TYPE_CHECKING

import pygame

from objects.prop import Prop
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light

if TYPE_CHECKING:
    from world.world import World

MAX_ANGLE = 2.2  # radians: the swing never goes over the top
IDLE_DAMPING = 1.6
SWING_DAMPING = 0.12
GOLD = (236, 184, 64)
GOLD_LIGHT = (255, 236, 150)
ROPE = (120, 84, 48)
ROPE_LIGHT = (176, 132, 80)


class Ring(Prop):
    layer = "mid"

    def __init__(self, anchor: tuple[float, float], length: float, phase: float = 0.0) -> None:
        super().__init__(pygame.Rect(anchor[0] - length, anchor[1], length * 2, length + 20))
        self.anchor = pygame.Vector2(anchor)
        self.length = max(24.0, length)
        self.angle = 0.25 * math.sin(phase)
        self.angular_velocity = 0.0
        self.held = False
        self._cooldown = 0.0
        self._time = phase

    @property
    def position(self) -> tuple[float, float]:
        return (self.anchor.x + math.sin(self.angle) * self.length,
                self.anchor.y + math.cos(self.angle) * self.length)

    @property
    def velocity(self) -> pygame.Vector2:
        speed = self.angular_velocity * self.length
        return pygame.Vector2(math.cos(self.angle) * speed, -math.sin(self.angle) * speed)

    @property
    def can_grab(self) -> bool:
        return not self.held and self._cooldown <= 0

    def grab(self, velocity: pygame.Vector2) -> None:
        # Project the arriving velocity onto the swing's tangent.
        tangent = pygame.Vector2(math.cos(self.angle), -math.sin(self.angle))
        self.angular_velocity = velocity.dot(tangent) / self.length
        self.held = True

    def release(self) -> None:
        self.held = False
        self._cooldown = 0.25

    def bonk(self) -> None:
        self.angular_velocity *= -0.3

    def pump(self, dt: float, axis: int, gravity: float, pump: float) -> None:
        acceleration = -(gravity / self.length) * math.sin(self.angle)
        # Pumping works like on a playground swing: push in the direction of travel.
        acceleration += axis * pump * math.cos(self.angle)
        self.angular_velocity += acceleration * dt
        self.angular_velocity *= max(0.0, 1.0 - SWING_DAMPING * dt)
        self.angle += self.angular_velocity * dt
        if abs(self.angle) > MAX_ANGLE:
            self.angle = math.copysign(MAX_ANGLE, self.angle)
            self.angular_velocity = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        self._cooldown = max(0.0, self._cooldown - dt)
        if not self.held:
            # Swing back to rest, with a faint breeze sway.
            acceleration = -(2100 / self.length) * math.sin(self.angle) - IDLE_DAMPING * self.angular_velocity
            acceleration += math.sin(self._time * 1.3) * 0.6
            self.angular_velocity += acceleration * dt
            self.angle += self.angular_velocity * dt

    def lights(self) -> list[Light]:
        x, y = self.position
        return [Light(x, y, 50, (255, 210, 130), 0.5)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        ax, ay = camera.to_screen(self.anchor.x, self.anchor.y)
        x, y = camera.to_screen(*self.position)
        pygame.draw.line(surface, ROPE, (ax, ay), (x, y - 6), 3)
        pygame.draw.line(surface, ROPE_LIGHT, (ax, ay), (x, y - 6), 1)
        pygame.draw.circle(surface, (70, 50, 40), (ax, ay), 4)
        pygame.draw.circle(surface, GOLD, (ax, ay), 2)
        if not self.held:
            blit_glow(surface, (x, y), 18, (255, 190, 90), 0.45 + 0.2 * math.sin(self._time * 3))
        pygame.draw.circle(surface, (90, 56, 20), (x, y), 8, 4)
        pygame.draw.circle(surface, GOLD, (x, y), 7, 3)
        pygame.draw.arc(surface, GOLD_LIGHT, (x - 7, y - 7, 14, 14), 1.8, 3.4, 2)
