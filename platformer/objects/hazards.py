"""Things that hurt or push: spikes, deep water, wind, fire-spitting lions."""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import PROJECTILES, TILE_SIZE, Color
from objects.prop import Prop
from rendering import emitters
from rendering.art import objects as art
from rendering.art.tiles import make_tile
from rendering.camera import Camera
from rendering.lighting import Light
from rendering.particles import Kind
from world.collision_map import TileCollision

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = TILE_SIZE


class Spikes(Prop):
    layer = "mid"
    touchable = True

    def __init__(self, rect: pygame.Rect, direction: str = "up") -> None:
        super().__init__(rect)
        self.direction = direction
        tile = make_tile("spikes")
        angle = {"up": 0, "down": 180, "left": 90, "right": -90}.get(direction, 0)
        self._image = pygame.transform.rotate(tile, angle)
        inset = 6
        if direction == "up":
            self._hurt = pygame.Rect(rect.x + 3, rect.bottom - 18, rect.width - 6, 18 - inset // 2)
        elif direction == "down":
            self._hurt = pygame.Rect(rect.x + 3, rect.top + inset // 2, rect.width - 6, 18 - inset // 2)
        elif direction == "left":
            self._hurt = pygame.Rect(rect.right - 18, rect.y + 3, 18 - inset // 2, rect.height - 6)
        else:
            self._hurt = pygame.Rect(rect.left + inset // 2, rect.y + 3, 18 - inset // 2, rect.height - 6)

    def touch_rect(self) -> pygame.Rect:
        return self._hurt

    def on_touch(self, player: "Player", world: "World") -> None:
        player.take_damage(world)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for x in range(self.rect.left, self.rect.right, T):
            for y in range(self.rect.top, self.rect.bottom, T):
                surface.blit(self._image, camera.to_screen(x, y))


class Water(Prop):
    """Deep water: falling in is fatal. The surface reflects the scene above
    it with a rippling distortion."""

    layer = "front"
    touchable = True
    REFLECTION_DEPTH = 90
    DROWN_DEPTH = 12

    def __init__(self, rect: pygame.Rect, color: Color = (60, 130, 190), reflective: bool = True) -> None:
        super().__init__(rect)
        self.color = color
        self.reflective = reflective
        self._time = 0.0
        self._tint: pygame.Surface | None = None
        self._splashed: set[int] = set()

    def touch_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.y + self.DROWN_DEPTH, self.rect.width, self.rect.height)

    def on_touch(self, player: "Player", world: "World") -> None:
        if player.is_controllable:
            emitters.splash(world.particles, player.body.centerx, self.rect.top, 1.3)
            world.events.emit(EventType.SPLASH, (player.body.centerx, self.rect.top))
            player.die(world, fell=True)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        for enemy in world.enemies:
            if id(enemy) not in self._splashed and enemy.body.bottom > self.rect.top + 4 and self.rect.colliderect(enemy.rect):
                self._splashed.add(id(enemy))
                emitters.splash(world.particles, enemy.body.centerx, self.rect.top, 0.8)
                enemy.alive = False
        # Glints dancing on the surface.
        if world.particles.rng.random() < self.rect.width / 2400:
            rng = world.particles.rng
            world.particles.spawn(rng.uniform(self.rect.left, self.rect.right), self.rect.top + rng.uniform(1, 4),
                                  life=rng.uniform(0.3, 0.7), kind=Kind.TWINKLE, size=rng.uniform(2, 3.5),
                                  color=(255, 255, 255), front=True)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        visible = self.rect.clip(view)
        if visible.width <= 0 or visible.height <= 0:
            return
        screen = camera.apply(visible)
        surface_y = camera.to_screen(0, self.rect.top)[1]
        if self.reflective and screen.top == surface_y:
            depth = min(self.REFLECTION_DEPTH, screen.height, surface_y)
            if depth > 2:
                source = pygame.Rect(screen.x, surface_y - depth, screen.width, depth).clip(surface.get_rect())
                if source.height > 0:
                    mirror = pygame.transform.flip(surface.subsurface(source).copy(), False, True)
                    for row in range(0, mirror.get_height(), 2):
                        shift = math.sin(self._time * 2.4 + row * 0.35) * (1.0 + row * 0.04)
                        surface.blit(mirror, (source.x + round(shift), surface_y + row),
                                     pygame.Rect(0, row, source.width, 2))
        if self._tint is None or self._tint.get_size() != (screen.width, screen.height):
            self._tint = pygame.Surface((screen.width, screen.height), pygame.SRCALPHA)
            height = screen.height
            for y in range(height):
                t = min(1.0, y / 120)
                alpha = int(120 + 100 * t)
                r = int(self.color[0] * (1 - 0.35 * t))
                g = int(self.color[1] * (1 - 0.3 * t))
                b = int(self.color[2] * (1 - 0.2 * t))
                pygame.draw.line(self._tint, (r, g, b, alpha), (0, y), (screen.width, y))
        surface.blit(self._tint, screen.topleft)
        if screen.top == surface_y:
            points = []
            for x in range(screen.left, screen.right + 8, 8):
                points.append((x, surface_y + math.sin(self._time * 3 + x * 0.05) * 1.5))
            if len(points) > 1:
                pygame.draw.lines(surface, (220, 240, 255), False, points, 2)


class WindZone(Prop):
    """A gusty area pushing everything sideways. Gusts come and go on a
    rhythm, telegraphed by streaks of wind."""

    layer = "front"

    def __init__(self, rect: pygame.Rect, strength: float, on_time: float, off_time: float, phase: float = 0.0) -> None:
        super().__init__(rect)
        self.strength = strength
        self._on = on_time
        self._off = off_time
        self._phase = phase
        self.current = 0.0
        self._was_blowing = False

    def _level(self, time: float) -> float:
        if self._off <= 0:
            return 1.0
        cycle = self._on + self._off
        t = (time + self._phase) % cycle
        ramp = 0.45
        if t < ramp:
            return t / ramp
        if t < self._on:
            return 1.0
        if t < self._on + ramp:
            return 1.0 - (t - self._on) / ramp
        return 0.0

    def update(self, dt: float, world: "World") -> None:
        self.current = self.strength * self._level(world.time)
        blowing = abs(self.current) > abs(self.strength) * 0.5
        if blowing and not self._was_blowing and world.on_screen(self.rect, 64):
            world.events.emit(EventType.WIND_GUST, world.player.body.midbottom)
        self._was_blowing = blowing
        player = world.player
        if self.rect.collidepoint(player.body.centerx, player.body.centery) and player.is_controllable:
            player.body.external.x += self.current
        if abs(self.current) > 5 and world.on_screen(self.rect, 0):
            rng = world.particles.rng
            view = world.view.clip(self.rect)
            if view.width > 0 and rng.random() < abs(self.current) / 260:
                direction = 1 if self.current > 0 else -1
                x = view.left if direction > 0 else view.right
                world.particles.spawn(
                    x + rng.uniform(-40, 40), rng.uniform(view.top, view.bottom),
                    self.current * rng.uniform(3.0, 4.2), rng.uniform(-10, 10),
                    life=rng.uniform(0.5, 0.9), kind=Kind.SPARK, size=rng.uniform(10, 18),
                    color=(255, 255, 255), color_end=(200, 210, 240),
                )


class FireLion(Prop):
    """A cursed stone lion that spits fireballs on a steady beat."""

    layer = "mid"
    WARNING = 0.45

    def __init__(self, cell: tuple[int, int], facing: int, interval: float, phase: float, arc: bool) -> None:
        super().__init__(pygame.Rect(cell[0] * T, cell[1] * T, T, T))
        self.cell = cell
        self.facing = facing
        self._interval = max(0.6, interval)
        self._timer = self._interval - (phase % self._interval)
        self._arc = arc
        closed = art.lion_head(False, False)
        warning = art.lion_head(True, True)
        self._images = {
            (False, 1): closed, (True, 1): warning,
            (False, -1): pygame.transform.flip(closed, True, False),
            (True, -1): pygame.transform.flip(warning, True, False),
        }

    def register(self, world: "World") -> None:
        world.collision.set(*self.cell, TileCollision.SOLID)

    def update(self, dt: float, world: "World") -> None:
        if not world.on_screen(self.rect, 160):
            return
        self._timer -= dt
        if self._timer <= 0:
            self._timer += self._interval
            from entities.projectiles import Fireball

            mouth = (self.rect.centerx + self.facing * 18, self.rect.top + 18)
            speed = PROJECTILES.fireball_speed
            velocity = (self.facing * speed, -320.0) if self._arc else (self.facing * speed, 0.0)
            world.spawn_projectile(Fireball(mouth, velocity, world.sprites, gravity=700.0 if self._arc else 0.0))
            emitters.embers(world.particles, mouth[0], mouth[1], 5, 4)
            world.events.emit(EventType.FIRE_SHOT, mouth)

    @property
    def warning(self) -> bool:
        return self._timer < self.WARNING

    def lights(self) -> list[Light]:
        if self.warning:
            return [Light(self.rect.centerx + self.facing * 10, self.rect.top + 12, 60, (255, 90, 50), 0.8, flicker=0.5)]
        return []

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self._images[(self.warning, self.facing)], camera.to_screen(self.rect.x, self.rect.y))
