"""Book II mechanisms built around the new moves.

* ``DashLantern``: a floating blue star-lamp; touching it refills the air
  dash, then it relights a moment later. Chains of them become paths in
  the sky that only a dashing prince can walk.
* ``Updraft``: warm air rising from vents; gliding inside it carries the
  prince upward.
* ``PoundPlate`` + ``Gate``: a bronze plate that only a ground pound can
  press. It opens every gate sharing its ``group``, for good or for
  ``timer`` seconds (a race against the portcullis).
* ``RisingFlood``: water that rises behind the prince and never lets him
  dawdle. It creeps up faster when he is far above it, slower when close,
  so the chase stays tense without becoming unfair.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import TILE_SIZE
from objects.hazards import Water
from objects.prop import Prop
from rendering import emitters
from rendering.art.kit import Canvas
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from world.collision_map import TileCollision

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = TILE_SIZE
_cache: dict[str, pygame.Surface] = {}


def _lantern_image(lit: bool) -> pygame.Surface:
    key = f"lantern{lit}"
    if key not in _cache:
        c = Canvas(26, 26, fringe=(20, 30, 60))
        body = (110, 190, 255) if lit else (70, 80, 110)
        core = (235, 250, 255) if lit else (120, 130, 160)
        c.star(body, (13, 13), 11, outline=(20, 40, 90), width=1.2)
        c.star(core, (13, 13), 6, rotation=math.pi / 8)
        _cache[key] = c.finish()
    return _cache[key]


class DashLantern(Prop):
    layer = "mid"
    touchable = True
    RELIGHT = 2.2

    def __init__(self, center: tuple[float, float]) -> None:
        super().__init__(pygame.Rect(center[0] - 14, center[1] - 14, 28, 28))
        self._timer = 0.0
        self._time = center[0] * 0.01

    @property
    def lit(self) -> bool:
        return self._timer <= 0

    def on_touch(self, player: "Player", world: "World") -> None:
        if not self.lit or not player.refill_dash():
            return
        self._timer = self.RELIGHT
        emitters.sparkle_burst(world.particles, *self.rect.center, (150, 210, 255), 14, 170)
        emitters.shockwave(world.particles, *self.rect.center, 40, (190, 230, 255))
        world.events.emit(EventType.DASH_REFILLED, self.rect.center)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if self._timer > 0:
            self._timer -= dt
            if self._timer <= 0:
                emitters.sparkle_burst(world.particles, *self.rect.center, (150, 210, 255), 6, 60)

    def lights(self) -> list[Light]:
        if not self.lit:
            return []
        return [Light(self.rect.centerx, self.rect.centery, 90, (130, 190, 255), 0.9, bloom=0.3)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        bob = math.sin(self._time * 2.6) * 3
        x, y = camera.to_screen(self.rect.centerx, self.rect.centery + bob)
        if self.lit:
            blit_glow(surface, (x, y), 30, (80, 150, 255), 0.7 + 0.2 * math.sin(self._time * 5))
            image = pygame.transform.rotate(_lantern_image(True), (self._time * 40) % 360)
        else:
            image = _lantern_image(False)
            refill = 1.0 - self._timer / self.RELIGHT
            pygame.draw.arc(surface, (150, 200, 255), (x - 16, y - 16, 32, 32), math.pi / 2,
                            math.pi / 2 + math.tau * refill, 2)
        surface.blit(image, image.get_rect(center=(x, y)))


class Updraft(Prop):
    """Rising warm air. Only a gliding prince is light enough to ride it."""

    layer = "front"

    def __init__(self, rect: pygame.Rect, strength: float = 260.0) -> None:
        super().__init__(rect)
        self.strength = strength
        self._time = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if not world.on_screen(self.rect, 32):
            return
        rng = world.particles.rng
        for _ in range(2 if self.rect.width > 64 else 1):
            if rng.random() < 0.6:
                x = rng.uniform(self.rect.left + 4, self.rect.right - 4)
                y = rng.uniform(self.rect.centery, self.rect.bottom)
                world.particles.spawn(
                    x, y, rng.uniform(-6, 6), -rng.uniform(140, 260), life=rng.uniform(0.8, 1.4),
                    kind=Kind.SPARK, size=rng.uniform(8, 14), color=(255, 250, 235), color_end=(255, 200, 150),
                    front=False,
                )

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        # Shimmering heat columns.
        rect = camera.apply(self.rect)
        for k in range(0, rect.width, 14):
            wave = math.sin(self._time * 3 + k * 0.3) * 3
            x = rect.left + k + wave
            length = 18 + (k * 7) % 22
            y = rect.bottom - ((self._time * 120 + k * 37) % max(1, rect.height))
            pygame.draw.line(surface, (255, 246, 226), (x, y), (x + wave * 0.4, y - length), 1)


def _plate_image(pressed: bool) -> pygame.Surface:
    key = f"plate{pressed}"
    if key not in _cache:
        c = Canvas(T, 12, fringe=(40, 26, 20))
        top = 7 if pressed else 2
        c.rect((90, 60, 40), (0, 8, T, 4))
        c.rect((200, 146, 60) if not pressed else (150, 110, 50), (3, top, T - 6, 12 - top - 2), radius=2,
               outline=(60, 40, 20), width=1)
        c.star((255, 220, 120) if not pressed else (190, 150, 70), (T / 2, top + 2.5), 2.6)
        _cache[key] = c.finish()
    return _cache[key]


class PoundPlate(Prop):
    """A bronze plate sunk in the floor. Only a ground pound presses it."""

    layer = "mid"

    def __init__(self, midbottom: tuple[float, float], group: str, timer: float = 0.0) -> None:
        super().__init__(pygame.Rect(midbottom[0] - T // 2, midbottom[1] - 12, T, 12))
        self.group = group
        self.timer = timer
        self.pressed = False
        self._left = 0.0
        self._time = 0.0

    def press(self, world: "World") -> None:
        if self.pressed and self.timer <= 0:
            return
        self.pressed = True
        self._left = self.timer
        for gate in world.gates_in(self.group):
            gate.set_open(True, world)
        emitters.sparkle_burst(world.particles, self.rect.centerx, self.rect.top, (255, 220, 120), 10, 120)
        world.events.emit(EventType.PLATE_PRESSED, self.rect.midtop)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if self.pressed and self.timer > 0:
            before = self._left
            self._left -= dt
            # Tick in the last seconds, like a clock running out.
            if int(before) != int(self._left) and self._left < 3:
                world.events.emit(EventType.SWITCH_WARNING, self.rect.midtop, 0)
            if self._left <= 0:
                self.pressed = False
                for gate in world.gates_in(self.group):
                    gate.set_open(False, world)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        image = _plate_image(self.pressed)
        x, y = camera.to_screen(self.rect.x, self.rect.y)
        surface.blit(image, (x, y))
        if self.pressed and self.timer > 0:
            fraction = max(0.0, self._left / self.timer)
            pygame.draw.rect(surface, (40, 24, 20), (x, y - 8, T, 4))
            pygame.draw.rect(surface, (255, 200, 90), (x, y - 8, round(T * fraction), 4))
        elif not self.pressed:
            pulse = 0.4 + 0.3 * math.sin(self._time * 4)
            blit_glow(surface, (x + T // 2, y + 4), 16, (255, 200, 90), pulse)


def _gate_bar() -> pygame.Surface:
    if "bar" not in _cache:
        s = pygame.Surface((T, T), pygame.SRCALPHA)
        for bx in (4, 14, 24):
            pygame.draw.rect(s, (40, 30, 30), (bx, 0, 5, T))
            pygame.draw.rect(s, (120, 110, 120), (bx + 1, 0, 3, T))
        pygame.draw.rect(s, (40, 30, 30), (0, 12, T, 6))
        pygame.draw.rect(s, (150, 140, 150), (0, 13, T, 3))
        _cache["bar"] = s
    return _cache["bar"]


class Gate(Prop):
    """An iron portcullis spanning ``rect`` (whole tiles). Solid while shut."""

    layer = "mid"
    SPEED = 5.0  # of its height per second

    def __init__(self, rect: pygame.Rect, group: str, start_open: bool = False) -> None:
        super().__init__(rect)
        self.group = group
        self.open = start_open
        self._openness = 1.0 if start_open else 0.0
        self._cells = [
            (tx, ty)
            for tx in range(rect.left // T, rect.right // T)
            for ty in range(rect.top // T, rect.bottom // T)
        ]
        self._pending_close = False

    def register(self, world: "World") -> None:
        self._apply(world, solid=not self.open)

    def _apply(self, world: "World", solid: bool) -> None:
        for cell in self._cells:
            world.collision.set(*cell, TileCollision.SOLID if solid else TileCollision.EMPTY)

    def set_open(self, value: bool, world: "World") -> None:
        if value == self.open:
            return
        self.open = value
        if value:
            self._pending_close = False
            self._apply(world, solid=False)
            world.events.emit(EventType.GATE_OPENED, self.rect.midbottom)
        else:
            self._pending_close = True

    def update(self, dt: float, world: "World") -> None:
        if self._pending_close and not world.anything_overlaps(self.rect):
            self._pending_close = False
            self._apply(world, solid=True)
            world.events.emit(EventType.GATE_CLOSED, self.rect.midbottom)
        target = 1.0 if self.open or self._pending_close else 0.0
        step = self.SPEED * dt * (0.6 if target > self._openness else 1.4)
        if self._openness < target:
            self._openness = min(target, self._openness + step)
        else:
            self._openness = max(target, self._openness - step)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        visible = round(self.rect.height * (1.0 - self._openness))
        if visible <= 0:
            return
        bar = _gate_bar()
        x, y = camera.to_screen(self.rect.x, self.rect.y)
        clip = surface.get_clip()
        surface.set_clip(pygame.Rect(x, y, self.rect.width, visible).clip(clip))
        offset = visible - self.rect.height
        for tx in range(0, self.rect.width, T):
            for ty in range(0, self.rect.height, T):
                surface.blit(bar, (x + tx, y + ty + offset))
        surface.set_clip(clip)
        # Spikes along the bottom edge.
        for tx in range(0, self.rect.width, 10):
            px = x + tx + 5
            pygame.draw.polygon(surface, (150, 140, 150), ((px - 3, y + visible - 2), (px + 3, y + visible - 2),
                                                            (px, y + visible + 5)))


class RisingFlood(Water):
    """Water that chases the prince upward through a vertical level."""

    def __init__(self, rect: pygame.Rect, speed: float, top_limit: float, delay: float = 2.0,
                 lag: float = 7 * T) -> None:
        super().__init__(rect, (40, 110, 170), reflective=False)
        self.speed = speed
        self.top_limit = top_limit
        self._delay = delay
        self._lag = lag
        self._bottom = rect.bottom
        self._level = float(rect.top)
        self._tint_cache: pygame.Surface | None = None
        self._announced = False

    def settle_below(self, bottom: float) -> None:
        """After a respawn higher up, start the water a fair distance below."""
        self._level = min(self._level, bottom + 5 * T)

    def update(self, dt: float, world: "World") -> None:
        if self._delay > 0:
            self._delay -= dt
        elif self._level > self.top_limit:
            player_bottom = world.player.body.bottom
            gap = self._level - player_bottom
            # Rubber band: creep when close, surge when far behind.
            factor = 0.55 if gap < 3 * T else (1.0 if gap < self._lag else 2.6)
            self._level = max(self.top_limit, self._level - self.speed * factor * dt)
            if not self._announced:
                self._announced = True
                world.events.emit(EventType.FLOOD_RISING, world.player.body.midbottom)
        top = round(self._level)
        self.rect = pygame.Rect(self.rect.x, top, self.rect.width, max(1, self._bottom - top))
        super().update(dt, world)
        if world.on_screen(self.rect, 0) and world.particles.rng.random() < 0.5:
            rng = world.particles.rng
            view = world.view
            x = rng.uniform(max(self.rect.left, view.left), min(self.rect.right, view.right))
            world.particles.spawn(x, top + rng.uniform(0, 30), 0, -rng.uniform(20, 50), life=1.0,
                                  kind=Kind.DOT, size=2.5, color=(200, 235, 255), front=True)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        visible = self.rect.clip(view)
        if visible.width <= 0 or visible.height <= 0:
            return
        screen = camera.apply(visible)
        if self._tint_cache is None:
            width, height = surface.get_size()
            self._tint_cache = pygame.Surface((width, height + 40), pygame.SRCALPHA)
            for y in range(height + 40):
                t = min(1.0, y / 140)
                pygame.draw.line(self._tint_cache, (int(40 * (1 - 0.4 * t)), int(110 * (1 - 0.35 * t)),
                                                    int(170 * (1 - 0.25 * t)), int(150 + 90 * t)),
                                 (0, y), (width, y))
        surface.blit(self._tint_cache, screen.topleft, pygame.Rect(0, 0, screen.width, screen.height))
        surface_y = camera.to_screen(0, self.rect.top)[1]
        if screen.top == surface_y:
            points = [(x, surface_y + math.sin(self._time * 4 + x * 0.06) * 2.5)
                      for x in range(screen.left, screen.right + 8, 8)]
            if len(points) > 1:
                pygame.draw.lines(surface, (220, 245, 255), False, points, 3)


class BladeTrap(Prop):
    """Twin scimitars spinning at head height under a low beam.

    Their hurt band sits 16-30 px above the floor: a standing prince is cut,
    a sliding one (14 px tall) slips underneath. Jumping over them only
    works where there's no ceiling.
    """

    layer = "mid"
    touchable = True

    def __init__(self, rect: pygame.Rect, speed: float = 9.0) -> None:
        super().__init__(rect)
        self._speed = speed
        self._time = rect.x * 0.05
        floor = rect.bottom
        self._hurt = pygame.Rect(rect.x + 3, floor - 30, rect.width - 6, 14)

    def touch_rect(self) -> pygame.Rect:
        return self._hurt

    def on_touch(self, player: "Player", world: "World") -> None:
        if player.body.height < player.physics.hitbox_height:
            return  # sliding underneath
        player.take_damage(world)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.rect.centerx, self._hurt.centery)
        top = camera.to_screen(0, self.rect.top)[1]
        pygame.draw.line(surface, (60, 44, 40), (x, top), (x, y), 3)
        pygame.draw.line(surface, (150, 130, 120), (x - 1, top), (x - 1, y), 1)
        angle = self._time * self._speed
        half = self.rect.width // 2 - 1
        for k in range(2):
            a = angle + k * math.pi
            # A horizontal spin seen from the side: the blade's length foreshortens.
            reach = math.cos(a) * half
            tip = (x + reach, y + math.sin(a) * 2)
            back = (x - reach * 0.15, y)
            glint = (230, 236, 250) if math.sin(a) > 0 else (150, 160, 180)
            pygame.draw.polygon(surface, glint, (back, (x + reach * 0.55, y - 5), tip, (x + reach * 0.5, y + 1)))
            pygame.draw.polygon(surface, (50, 50, 70), (back, (x + reach * 0.55, y - 5), tip, (x + reach * 0.5, y + 1)), 1)
        pygame.draw.circle(surface, (214, 160, 60), (x, y), 3)
