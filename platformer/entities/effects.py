"""Short-lived visual effects. They never affect gameplay."""

import math
from collections.abc import Mapping
from typing import TYPE_CHECKING

import pygame

from core import settings
from entities.entity import Entity
from rendering import emitters
from rendering.animation import Animation, Animator
from rendering.camera import Camera
from rendering.draw import blit_midbottom

if TYPE_CHECKING:
    from world.world import World


class Effect(Entity):
    def __init__(self, position: tuple[float, float], lifetime: float) -> None:
        super().__init__()
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2()
        self._age = 0.0
        self._lifetime = lifetime

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.position.x), round(self.position.y), 1, 1)

    @property
    def progress(self) -> float:
        return min(1.0, self._age / self._lifetime)

    def update(self, dt: float, world: "World") -> None:
        self._age += dt
        if self._age >= self._lifetime:
            self.alive = False
            self._finish(world)
        self._move(dt)

    def _finish(self, world: "World") -> None:
        pass

    def _move(self, dt: float) -> None:
        self.position += self.velocity * dt


class CoinPopEffect(Effect):
    """A coin that jumps out of a question block and vanishes in a sparkle."""

    def __init__(self, midbottom: tuple[float, float], animations: Mapping[str, Animation]) -> None:
        super().__init__(midbottom, settings.ITEMS.coin_pop_duration)
        self.velocity.y = -settings.ITEMS.coin_pop_velocity
        self._animator = Animator(animations, "spin")

    def _move(self, dt: float) -> None:
        self.velocity.y += settings.ITEMS.coin_pop_gravity * dt
        super()._move(dt)
        self._animator.update(dt, speed=2.0)

    def _finish(self, world: "World") -> None:
        emitters.sparkle_burst(world.particles, self.position.x, self.position.y - 8, emitters.SPARKLE_GOLD, 6, 90)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        blit_midbottom(surface, self._animator.image(), camera, self.position)


class DebrisEffect(Effect):
    """A tumbling chunk of a broken brick."""

    def __init__(
        self, center: tuple[float, float], velocity: tuple[float, float], image: pygame.Surface
    ) -> None:
        super().__init__(center, settings.BLOCKS.debris_lifetime)
        self.velocity.update(velocity)
        self._image = image
        self._angle = 0.0
        self._spin = 720.0 if velocity[0] > 0 else -720.0

    def _move(self, dt: float) -> None:
        self.velocity.y += settings.BLOCKS.debris_gravity * dt
        self._angle += self._spin * dt
        super()._move(dt)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        screen = camera.to_screen(self.position.x, self.position.y)
        image = pygame.transform.rotate(self._image, self._angle)
        surface.blit(image, image.get_rect(center=screen))


class ScorePopup(Effect):
    """Floating "+200" text that pops in, rises and fades."""

    def __init__(self, midbottom: tuple[float, float], text: pygame.Surface, lifetime: float = settings.SCORE_POPUP_DURATION) -> None:
        super().__init__(midbottom, lifetime)
        self.velocity.y = -settings.SCORE_POPUP_RISE_SPEED
        self._text = text

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        t = self.progress
        # Overshooting pop: 0 -> 1.25 -> 1.0 in the first fifth of its life.
        pop = min(1.0, t / 0.2)
        scale = 1.0 + 0.25 * math.sin(pop * math.pi) if pop < 1.0 else 1.0
        scale *= 0.4 + 0.6 * min(1.0, pop * 2)
        image = self._text
        if abs(scale - 1.0) > 0.02:
            width, height = image.get_size()
            image = pygame.transform.smoothscale(image, (max(1, round(width * scale)), max(1, round(height * scale))))
        if t > 0.7:
            image = image.copy()
            image.set_alpha(round(255 * (1.0 - (t - 0.7) / 0.3)))
        blit_midbottom(surface, image, camera, self.position)
