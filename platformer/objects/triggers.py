"""Trigger areas: checkpoints, the level goal and doors (wells)."""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from entities.player_controller import PlayerIntent
from rendering import emitters
from rendering.art import objects as art
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

_images: dict[str, pygame.Surface] = {}
_flames: list[pygame.Surface] = []


def _image(key: str) -> pygame.Surface:
    image = _images.get(key)
    if image is None:
        factories = {
            "post": lambda: art.lantern_post(False),
            "lantern_off": lambda: art.lantern(False),
            "lantern_on": lambda: art.lantern(True),
            "brazier_off": lambda: art.brazier(False),
            "brazier_on": lambda: art.brazier(True),
            "gate": art.arch_gate,
            "gate_glow": art.arch_glow_interior,
            "sword": art.sword_shrine,
        }
        image = factories[key]()
        _images[key] = image
    return image


def flames() -> list[pygame.Surface]:
    if not _flames:
        _flames.extend(art.flame_frames())
    return _flames


class Checkpoint:
    """A lantern (or a brazier in the fortress) that lights up when reached.

    Dying afterwards respawns the prince here.
    """

    def __init__(self, checkpoint_id: int, midbottom: tuple[int, int], size: tuple[int, int],
                 style: str = "lantern", active: bool = False) -> None:
        self.checkpoint_id = checkpoint_id
        self.rect = pygame.Rect((0, 0), size)
        self.rect.midbottom = midbottom
        self.active = active
        self.style = style
        self._time = 0.0
        self._flash = 0.0

    @property
    def respawn_point(self) -> tuple[int, int]:
        return self.rect.midbottom

    def activate(self, world: "World") -> None:
        if self.active:
            return
        self.active = True
        self._flash = 1.0
        x, y = self._light_point()
        emitters.sparkle_burst(world.particles, x, y, (255, 220, 120), 16, 170)
        emitters.shockwave(world.particles, x, y, 70, (255, 230, 170))
        emitters.embers(world.particles, x, y, 8, 6)
        world.events.emit(EventType.CHECKPOINT_REACHED, self.rect.midtop, self.checkpoint_id)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        self._flash = max(0.0, self._flash - dt * 2)
        if self.active and self.style == "brazier" and int(self._time * 20) % 3 == 0:
            x, y = self._light_point()
            emitters.embers(world.particles, x, y - 6, 1, 6)

    def _swing(self) -> float:
        return math.sin(self._time * 2.0 + self.rect.x * 0.01) * (6.0 if self.active else 3.0)

    def _light_point(self) -> tuple[float, float]:
        if self.style == "brazier":
            return self.rect.centerx, self.rect.bottom - 26
        swing = math.radians(self._swing())
        pivot = (self.rect.centerx + 9, self.rect.bottom - 51)
        return pivot[0] + math.sin(swing) * 12, pivot[1] + math.cos(swing) * 12

    def lights(self) -> list[Light]:
        if not self.active:
            return []
        x, y = self._light_point()
        radius = 170 + 60 * self._flash
        return [Light(x, y, radius, (255, 190, 110), 1.0, flicker=0.7 if self.style == "brazier" else 0.25, bloom=0.4)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        bottom = camera.to_screen(self.rect.centerx, self.rect.bottom)
        if self.style == "brazier":
            image = _image("brazier_on" if self.active else "brazier_off")
            surface.blit(image, image.get_rect(midbottom=bottom))
            if self.active:
                frames = flames()
                flame = frames[int(self._time * 12) % len(frames)]
                surface.blit(flame, flame.get_rect(midbottom=(bottom[0], bottom[1] - 20)))
            return
        post = _image("post")
        surface.blit(post, post.get_rect(midbottom=bottom))
        lantern = _image("lantern_on" if self.active else "lantern_off")
        angle = self._swing()
        rotated = pygame.transform.rotate(lantern, -angle)
        x, y = self._light_point()
        center = camera.to_screen(x, y)
        if self.active:
            blit_glow(surface, center, 30, (255, 180, 80), 0.7 + 0.3 * self._flash)
        surface.blit(rotated, rotated.get_rect(center=center))


class Goal:
    """End of the level. The trigger spans the full height above the object
    so the player can't jump over it."""

    def __init__(self, object_rect: pygame.Rect, style: str = "gate") -> None:
        self.rect = pygame.Rect(object_rect.x, 0, object_rect.width, object_rect.bottom)
        self.style = style
        self.reached = False
        self._time = 0.0
        self._glow = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if self.reached:
            self._glow = min(1.0, self._glow + dt * 1.5)
            if int(self._time * 30) % 2 == 0:
                rng = world.particles.rng
                emitters.aura(world.particles, self.rect.centerx + rng.uniform(-24, 24), self.rect.bottom - rng.uniform(10, 90),
                              (255, 230, 160), 4)

    def lights(self) -> list[Light]:
        if self.style == "sword":
            return [Light(self.rect.centerx, self.rect.bottom - 70, 200, (255, 236, 170), 1.0, flicker=0.1, bloom=0.5)]
        if self._glow > 0:
            return [Light(self.rect.centerx, self.rect.bottom - 50, 90 + 160 * self._glow, (255, 220, 150), 1.0, bloom=0.4)]
        return [Light(self.rect.centerx, self.rect.bottom - 60, 90, (255, 210, 160), 0.5)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        bottom = camera.to_screen(self.rect.centerx, self.rect.bottom)
        if self.style == "sword":
            pulse = 0.7 + 0.3 * math.sin(self._time * 2.4)
            blit_glow(surface, (bottom[0], bottom[1] - 70), 70, (255, 210, 110), pulse)
            image = _image("sword")
            surface.blit(image, image.get_rect(midbottom=bottom))
            return
        image = _image("gate")
        rect = image.get_rect(midbottom=bottom)
        surface.blit(image, rect)
        if self._glow > 0:
            glow = _image("gate_glow").copy()
            glow.set_alpha(round(230 * self._glow))
            surface.blit(glow, rect)


class Door:
    """Invisible warp trigger, usually placed on top of a pipe.

    A door without ``target_door`` is only an arrival point.
    """

    def __init__(
        self,
        name: str,
        rect: pygame.Rect,
        target_door: str | None,
        target_level: str | None,
        enter_direction: str,
    ) -> None:
        self.name = name
        self.rect = rect
        self.target_door = target_door
        self.target_level = target_level
        self.enter_direction = enter_direction

    @property
    def arrival_point(self) -> tuple[int, int]:
        return self.rect.midbottom

    def can_enter(self, player: "Player") -> bool:
        if not self.target_door:
            return False
        body = player.body
        centered = self.rect.left <= body.centerx <= self.rect.right
        return body.on_ground and centered and player.rect.colliderect(self.rect)

    def wants_enter(self, intent: PlayerIntent) -> bool:
        return intent.up_held if self.enter_direction == "up" else intent.down_held
