"""Collectible items: coins, power-ups, extra lives and manuscript pages."""

import logging
import math
from abc import abstractmethod
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import ITEMS
from entities.effects import CoinPopEffect
from entities.entity import Entity
from physics.body import Body
from physics.collision import apply_gravity, move_body
from rendering import emitters, sprite_specs
from rendering.animation import Animation, Animator
from rendering.camera import Camera
from rendering.draw import blit_midbottom
from rendering.glow import blit_glow
from rendering.lighting import Light

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

logger = logging.getLogger(__name__)


class Item(Entity):
    def __init__(
        self, midbottom: tuple[float, float], size: float, animations: Mapping[str, Animation]
    ) -> None:
        super().__init__()
        self.body = Body.from_midbottom(midbottom, size, size)
        self._animator = Animator(animations, next(iter(animations)))

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect()

    @property
    def collectible(self) -> bool:
        return True

    @abstractmethod
    def collect(self, player: "Player", world: "World") -> None: ...

    def lights(self) -> list[Light]:
        return []

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        blit_midbottom(surface, self._animator.image(), camera, self.body.midbottom)


class Coin(Item):
    def __init__(self, midbottom: tuple[float, float], animations: Mapping[str, Animation]) -> None:
        super().__init__(midbottom, ITEMS.coin_hitbox_size, animations)
        # Offset the spin so rows of coins shimmer instead of spinning in sync.
        self._animator.update((midbottom[0] * 0.013) % 1.0)

    def update(self, dt: float, world: "World") -> None:
        self._animator.update(dt)

    def collect(self, player: "Player", world: "World") -> None:
        self.alive = False
        emitters.coin_collect(world.particles, self.body.centerx, self.body.centery)
        world.events.emit(EventType.COIN_COLLECTED, (self.body.centerx, self.body.centery))

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery, 28, (255, 210, 110), 0.5)]


class Page(Item):
    """A lost manuscript page, three hidden per level.

    Pages already found in an earlier visit appear as faint outlines; taking
    them again only plays a sound.
    """

    def __init__(self, center: tuple[float, float], index: int, animations: Mapping[str, Animation],
                 already_found: bool = False) -> None:
        super().__init__((center[0], center[1] + 12), 24, animations)
        self.index = index
        self.already_found = already_found
        self._time = index * 1.3
        self._base_y = self.body.y

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        self._animator.update(dt)
        self.body.y = self._base_y + math.sin(self._time * 2.2) * 3
        if not self.already_found and int(self._time * 10) % 4 == 0:
            emitters.aura(world.particles, self.body.centerx, self.body.centery, (255, 230, 150), 14)

    def collect(self, player: "Player", world: "World") -> None:
        self.alive = False
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (255, 230, 150), 16, 180)
        emitters.shockwave(world.particles, self.body.centerx, self.body.centery, 50)
        world.events.emit(
            EventType.PAGE_COLLECTED, (self.body.centerx, self.body.top), -1 if self.already_found else self.index
        )

    def lights(self) -> list[Light]:
        if self.already_found:
            return []
        return [Light(self.body.centerx, self.body.centery, 80, (255, 220, 140), 0.8, bloom=0.25)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        center = camera.to_screen(self.body.centerx, self.body.centery)
        image = self._animator.image()
        if self.already_found:
            ghost = image.copy()
            ghost.set_alpha(90)
            surface.blit(ghost, ghost.get_rect(center=center))
            return
        blit_glow(surface, center, 26, (160, 120, 50), 0.6 + 0.2 * math.sin(self._time * 3))
        surface.blit(image, image.get_rect(center=center))


class MovingItem(Item):
    """Rises out of a block, then slides along the ground and turns at walls."""

    def __init__(
        self, block_rect: pygame.Rect, animations: Mapping[str, Animation], direction: int = 1,
        bouncy: bool = False,
    ) -> None:
        super().__init__(block_rect.midbottom, ITEMS.hitbox_size, animations)
        self._rise_from = self.body.y
        self._rise_to = block_rect.top - self.body.height
        self._rise_time = 0.0
        self._direction = direction
        self._bouncy = bouncy

    @property
    def collectible(self) -> bool:
        return self._rise_time >= ITEMS.rise_duration

    def update(self, dt: float, world: "World") -> None:
        self._animator.update(dt)
        if not self.collectible:
            self._rise_time += dt
            progress = min(1.0, self._rise_time / ITEMS.rise_duration)
            self.body.y = self._rise_from + (self._rise_to - self._rise_from) * progress
            return

        self.body.velocity.x = self._direction * ITEMS.powerup_speed
        apply_gravity(self.body, ITEMS.gravity, ITEMS.terminal_velocity, dt)
        move_body(self.body, dt, world.collision, world.platforms)
        if self._bouncy and self.body.on_ground:
            self.body.velocity.y = -420
        if self.body.hit_wall:
            self._direction = -self.body.hit_wall
        if self.body.top > world.collision.pixel_height:
            self.alive = False

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery, 60, (255, 200, 150), 0.7)]


class PowerUp(MovingItem):
    def collect(self, player: "Player", world: "World") -> None:
        from entities.player import PowerLevel

        self.alive = False
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (255, 120, 140), 14, 160)
        player.power_up(world, PowerLevel.POMEGRANATE)


class StarPowerUp(MovingItem):
    """The Najma: bounces along, grants the star robe and star throwing."""

    def __init__(self, block_rect: pygame.Rect, animations: Mapping[str, Animation], direction: int = 1) -> None:
        super().__init__(block_rect, animations, direction, bouncy=True)

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        if self.collectible and int(self._rise_time * 1000) % 3 == 0:
            emitters.magic_trail(world.particles, self.body.centerx, self.body.centery)

    def collect(self, player: "Player", world: "World") -> None:
        from entities.player import PowerLevel

        self.alive = False
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (150, 200, 255), 18, 200)
        player.power_up(world, PowerLevel.STAR)

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery, 90, (140, 190, 255), 0.9, bloom=0.3)]


class ExtraLife(MovingItem):
    def collect(self, player: "Player", world: "World") -> None:
        self.alive = False
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (255, 220, 120), 14, 160)
        world.events.emit(EventType.EXTRA_LIFE, self.body.midbottom)


# --- Block contents -------------------------------------------------------------
# Maps a question block's "contents" property to what happens when it's hit.
BlockContents = Callable[[pygame.Rect, "World"], None]


def release_coin(block_rect: pygame.Rect, world: "World") -> None:
    world.events.emit(EventType.COIN_COLLECTED, block_rect.midtop)
    world.spawn_effect(CoinPopEffect(block_rect.midtop, world.sprites.animations(sprite_specs.COIN)))


def _release_powerup(block_rect: pygame.Rect, world: "World") -> None:
    direction = 1 if world.player.body.centerx <= block_rect.centerx else -1
    world.spawn_item(PowerUp(block_rect, world.sprites.animations(sprite_specs.POWERUP), direction))
    world.events.emit(EventType.ITEM_SPAWNED, block_rect.midtop)


def _release_star(block_rect: pygame.Rect, world: "World") -> None:
    direction = 1 if world.player.body.centerx <= block_rect.centerx else -1
    world.spawn_item(StarPowerUp(block_rect, world.sprites.animations(sprite_specs.STAR_POWER), direction))
    world.events.emit(EventType.ITEM_SPAWNED, block_rect.midtop)


def _release_extra_life(block_rect: pygame.Rect, world: "World") -> None:
    world.spawn_item(ExtraLife(block_rect, world.sprites.animations(sprite_specs.EXTRA_LIFE)))
    world.events.emit(EventType.ITEM_SPAWNED, block_rect.midtop)


BLOCK_CONTENTS: dict[str, BlockContents] = {
    "coin": release_coin,
    "powerup": _release_powerup,
    "star": _release_star,
    "extra_life": _release_extra_life,
}


def release_block_contents(contents: str, block_rect: pygame.Rect, world: "World") -> None:
    release = BLOCK_CONTENTS.get(contents)
    if release is None:
        logger.warning("Unknown block contents %r; releasing a coin", contents)
        release = release_coin
    release(block_rect, world)
