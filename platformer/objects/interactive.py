"""Objects the prince uses: drums (springs), fountain jets and signs."""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import TILE_SIZE
from objects.prop import Prop
from rendering import emitters
from rendering.art import objects as art
from rendering.camera import Camera
from rendering.particles import Kind

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = TILE_SIZE
_drum_frames: list[pygame.Surface] = []


def _drums() -> list[pygame.Surface]:
    if not _drum_frames:
        for squash in (1.0, 0.62, 0.8, 1.12, 0.94):
            _drum_frames.append(art.drum(squash))
    return _drum_frames


class Drum(Prop):
    """A darbuka: land on its head to be launched high (hold jump for more)."""

    layer = "mid"
    touchable = True
    ANIMATION = (0.0, 0.05, 0.11, 0.19, 0.27)

    def __init__(self, midbottom: tuple[float, float]) -> None:
        rect = pygame.Rect(0, 0, 30, 24)
        rect.midbottom = (round(midbottom[0]), round(midbottom[1]))
        super().__init__(rect)
        self._since_bounce = 10.0

    @property
    def top(self) -> float:
        return self.rect.bottom - 24

    def touch_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.top - 4, self.rect.width, 18)

    def on_touch(self, player: "Player", world: "World") -> None:
        if player.body.velocity.y <= 0 or player.previous_bottom > self.top + 12:
            return
        player.body.y = self.top - player.body.height
        player.spring_bounce()
        self._since_bounce = 0.0
        world.particles.spawn(self.rect.centerx, self.top, life=0.35, kind=Kind.RING, size=6, size_end=34,
                              color=(255, 236, 190))
        emitters.sparkle_burst(world.particles, self.rect.centerx, self.top, (255, 230, 170), 6, 90)
        world.events.emit(EventType.SPRING_BOUNCED, (self.rect.centerx, self.top))

    def update(self, dt: float, world: "World") -> None:
        self._since_bounce += dt

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        frames = _drums()
        index = 0
        for k, start in enumerate(self.ANIMATION):
            if self._since_bounce >= start:
                index = k
        if self._since_bounce > 0.4:
            index = 0
        image = frames[index]
        x, y = camera.to_screen(self.rect.centerx, self.rect.bottom)
        surface.blit(image, image.get_rect(midbottom=(x, y + 2)))


_column_texture: pygame.Surface | None = None
_basin: pygame.Surface | None = None


class Fountain(Prop):
    """A jet of water that lifts the prince while it runs.

    It rises on a rhythm (``on``/``off`` seconds, ``phase`` offset) and
    sputters for a moment before each burst, so timing can be read.
    """

    layer = "mid"
    touchable = True
    WARMUP = 0.6
    LIFT_SPEED = 330.0
    LIFT_ACCELERATION = 3000.0

    def __init__(self, midbottom: tuple[float, float], height_tiles: float, on_time: float, off_time: float,
                 phase: float = 0.0) -> None:
        self.height = height_tiles * T
        rect = pygame.Rect(0, 0, 28, round(self.height))
        rect.midbottom = (round(midbottom[0]), round(midbottom[1]))
        super().__init__(rect)
        self._on = on_time
        self._off = off_time
        self._phase = phase
        self._time = 0.0
        self.level = 0.0  # 0..1 of the full height currently reached
        global _column_texture, _basin
        if _column_texture is None:
            _column_texture = art.water_column_texture()
            _basin = art.fountain_basin()

    def _cycle(self, time: float) -> tuple[bool, bool]:
        """(running, warming_up) at a given time."""
        if self._off <= 0:
            return True, False
        cycle = self._on + self._off
        t = (time + self._phase) % cycle
        running = t < self._on
        warming = not running and t > cycle - self.WARMUP
        return running, warming

    def top_y(self) -> float:
        return self.rect.bottom - self.height * self.level

    def touch_rect(self) -> pygame.Rect:
        top = self.top_y()
        return pygame.Rect(self.rect.x - 2, top - 8, self.rect.width + 4, self.rect.bottom - top + 8)

    def on_touch(self, player: "Player", world: "World") -> None:
        if self.level < 0.15 or not player.is_controllable:
            return
        # Push up hard in the column, easing to a hover at the top of the jet.
        distance = player.body.bottom - (self.top_y() - 6)
        target = -min(self.LIFT_SPEED, max(0.0, distance) * 7.0)
        player.apply_lift(target, self.LIFT_ACCELERATION)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        running, warming = self._cycle(self._time)
        target = 1.0 if running else 0.0
        speed = 2.8 if running else 3.5
        self.level += (target - self.level) * min(1.0, dt * speed * 2)
        if abs(self.level - target) < 0.01:
            self.level = target
        if not world.on_screen(self.rect, 64):
            return
        rng = world.particles.rng
        top = self.top_y()
        if self.level > 0.1:
            for _ in range(2):
                emitters.droplet(world.particles, self.rect.centerx + rng.uniform(-10, 10), top,
                                 rng.uniform(-90, 90), -rng.uniform(80, 200))
        elif warming and rng.random() < 0.5:
            emitters.droplet(world.particles, self.rect.centerx + rng.uniform(-5, 5), self.rect.bottom - 12,
                             rng.uniform(-40, 40), -rng.uniform(60, 160))

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        assert _column_texture is not None and _basin is not None
        bottom_x, bottom_y = camera.to_screen(self.rect.centerx, self.rect.bottom)
        column_height = round(self.height * self.level)
        if column_height > 2:
            tex_h = _column_texture.get_height()
            scroll = int(self._time * 260) % tex_h
            top = bottom_y - column_height
            x = bottom_x - _column_texture.get_width() // 2
            y = top
            offset = scroll
            while y < bottom_y - 8:
                chunk = min(tex_h - offset, bottom_y - 8 - y)
                wobble = round(math.sin(self._time * 11 + y * 0.08) * 1.5)
                surface.blit(_column_texture, (x + wobble, y), pygame.Rect(0, offset, _column_texture.get_width(), chunk))
                y += chunk
                offset = 0
            # Foam crown.
            for k in range(5):
                a = self._time * 7 + k * 1.3
                pygame.draw.circle(surface, (240, 250, 255), (bottom_x + round(math.sin(a) * 9), top + round(math.cos(a) * 2)), 5)
        surface.blit(_basin, _basin.get_rect(midbottom=(bottom_x, bottom_y)))


class Sign(Prop):
    """A wooden sign; walking past shows its message in a speech bubble."""

    layer = "back"

    def __init__(self, midbottom: tuple[float, float], bubble: pygame.Surface) -> None:
        rect = pygame.Rect(0, 0, 32, 32)
        rect.midbottom = (round(midbottom[0]), round(midbottom[1]))
        super().__init__(rect)
        self._image = art.sign_post()
        self._bubble = bubble
        self._show = 0.0
        self._near = False

    def update(self, dt: float, world: "World") -> None:
        self._near = world.player.rect.colliderect(self.rect.inflate(48, 80))
        target = 1.0 if self._near else 0.0
        self._show += (target - self._show) * min(1.0, dt * 10)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self._image, camera.to_screen(self.rect.x, self.rect.y))

    def draw_overlay(self, surface: pygame.Surface, camera: Camera) -> None:
        if self._show < 0.03:
            return
        scale = 0.6 + 0.4 * self._show
        bubble = self._bubble
        if scale < 0.99:
            bubble = pygame.transform.smoothscale(bubble, (round(bubble.get_width() * scale), round(bubble.get_height() * scale)))
        bubble = bubble.copy()
        bubble.set_alpha(round(255 * self._show))
        x, y = camera.to_screen(self.rect.centerx, self.rect.top - 6)
        rect = bubble.get_rect(midbottom=(x, y))
        screen = surface.get_rect()
        rect.clamp_ip(screen.inflate(-8, -8))
        surface.blit(bubble, rect)
