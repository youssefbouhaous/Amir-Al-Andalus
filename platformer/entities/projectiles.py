"""Thrown things: the prince's stars and the fireballs of lions and the Ifrit."""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import PROJECTILES
from entities.entity import Entity
from physics.body import Body
from physics.collision import move_body
from rendering import emitters, sprite_specs
from rendering.animation import Animator
from rendering.camera import Camera
from rendering.draw import blit_midbottom
from rendering.lighting import Light
from rendering.sprite_library import SpriteLibrary

if TYPE_CHECKING:
    from world.world import World


class Projectile(Entity):
    friendly = False  # thrown by the player (hurts enemies) or not (hurts the player)

    def __init__(self, center: tuple[float, float], size: float, lifetime: float) -> None:
        super().__init__()
        self.body = Body(center[0] - size / 2, center[1] - size / 2, size, size)
        self._age = 0.0
        self._lifetime = lifetime

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect()

    def expire(self, world: "World") -> None:
        self.alive = False

    def _tick(self, dt: float, world: "World") -> bool:
        self._age += dt
        if self._age >= self._lifetime or self.body.top > world.collision.pixel_height + 64:
            self.alive = False
        return self.alive

    def lights(self) -> list[Light]:
        return []


class StarProjectile(Projectile):
    """Bounces along the ground like a skipping stone; breaks on walls."""

    friendly = True

    def __init__(self, hand: tuple[float, float], direction: int, sprites: SpriteLibrary) -> None:
        super().__init__(hand, PROJECTILES.star_size, PROJECTILES.star_lifetime)
        self.body.velocity.update(direction * PROJECTILES.star_speed, 60.0)
        self._animator = Animator(sprites.animations(sprite_specs.STAR_PROJECTILE), "spin")
        self._trail_timer = 0.0

    def update(self, dt: float, world: "World") -> None:
        if not self._tick(dt, world):
            return
        body = self.body
        body.velocity.y = min(body.velocity.y + PROJECTILES.star_gravity * dt, 700.0)
        speed_x = body.velocity.x
        move_body(body, dt, world.collision)
        if body.on_ground:
            body.velocity.y = -PROJECTILES.star_bounce_velocity
        if body.hit_wall or body.hit_ceiling:
            world.events.emit(EventType.PROJECTILE_BLOCKED, (body.centerx, body.centery))
            self.expire(world)
            return
        body.velocity.x = speed_x
        self._animator.update(dt)
        self._trail_timer -= dt
        if self._trail_timer <= 0:
            self._trail_timer = 0.03
            emitters.magic_trail(world.particles, body.centerx, body.centery)

    def expire(self, world: "World") -> None:
        if self.alive:
            emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (160, 210, 255), 8, 110)
        self.alive = False

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery, 70, (140, 190, 255), 0.9, bloom=0.3)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        blit_midbottom(surface, self._animator.image(), camera, self.body.midbottom)


class Fireball(Projectile):
    """Flies in a straight line (optionally arcing under gravity)."""

    def __init__(
        self, center: tuple[float, float], velocity: tuple[float, float], sprites: SpriteLibrary,
        gravity: float = 0.0, lifetime: float = PROJECTILES.fireball_lifetime, passes_walls: bool = False,
    ) -> None:
        super().__init__(center, PROJECTILES.fireball_size, lifetime)
        self.body.velocity.update(velocity)
        self._gravity = gravity
        self._passes_walls = passes_walls
        self._animator = Animator(sprites.animations(sprite_specs.FIREBALL), "burn")
        self._trail_timer = 0.0

    def update(self, dt: float, world: "World") -> None:
        if not self._tick(dt, world):
            return
        body = self.body
        body.velocity.y += self._gravity * dt
        if self._passes_walls:
            body.x += body.velocity.x * dt
            body.y += body.velocity.y * dt
        else:
            velocity = pygame.Vector2(body.velocity)
            move_body(body, dt, world.collision)
            if body.hit_wall or body.hit_ceiling or body.on_ground:
                self.expire(world)
                return
            body.velocity.update(velocity)
        self._animator.update(dt)
        self._trail_timer -= dt
        if self._trail_timer <= 0:
            self._trail_timer = 0.025
            emitters.fire_trail(world.particles, body.centerx, body.centery)

    def expire(self, world: "World") -> None:
        if self.alive:
            emitters.embers(world.particles, self.body.centerx, self.body.centery, 6, 8)
        self.alive = False

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery, 90, (255, 150, 70), 1.0, flicker=0.6, bloom=0.35)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        image = self._animator.image(flip_x=self.body.velocity.x < 0)
        angle = math.degrees(math.atan2(-self.body.velocity.y, abs(self.body.velocity.x) + 1e-6))
        if abs(angle) > 8:
            image = pygame.transform.rotate(image, angle if self.body.velocity.x >= 0 else -angle)
        screen = camera.to_screen(self.body.centerx, self.body.centery)
        surface.blit(image, image.get_rect(center=screen))
