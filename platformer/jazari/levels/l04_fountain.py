"""The Rose Fountain, the power taught by the three pages of level 4.

Al-Jazari's fountains hold a ball dancing on their crest and change their
shape at intervals. Amir rebuilds one as a brass rose: press POWER and he
throws it, and where it lands it blooms into a column of water.

* The column lifts whatever stands on it. A River-Thief is held kicking in
  the middle of the water, out of the stolen flood - and out of the noria's
  strength - until the fountain sinks and drops him, dazed.
* The prince rides it to the crest, higher than any jump: a lift wherever he
  needs one (stand still, or jump, and it blooms beneath him).
* Ordinary creatures are tossed senseless; the thieves' missiles stop at it -
  a jet of water splits on it, nets are flung away, carp are thrown home.
"""

import math
import random
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from jazari import art as ink_art
from jazari.base import Power, ground_below
from rendering import emitters
from rendering.art import fountain as art
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = 32
AQUA = (110, 226, 255)


class Jet:
    """A column of water sprung from the brass rose."""

    RISE = 0.24
    HOLD = 2.0
    SINK = 0.4
    HEIGHT = 168.0        # how high it carries the prince
    HOLD_AT = 86.0        # where it holds a thief (and anything it catches), above the ground
    WIDTH = 30
    FLIGHT = 0.18         # the rose's flight from the prince's hand

    def __init__(self, x: float, ground: float, shape: int, hand: tuple[float, float]) -> None:
        self.x = x
        self.ground = ground
        self.shape = shape
        self.hand = hand
        self.age = -self.FLIGHT
        self.alive = True
        self.burst = False

    # --- what the thieves (and the guardian) ask --------------------------------------------------
    @property
    def level(self) -> float:
        if self.age < 0:
            return 0.0
        if self.age < self.RISE:
            u = self.age / self.RISE
            return u * u * (3 - 2 * u)
        if self.age < self.RISE + self.HOLD:
            return 1.0
        return max(0.0, 1.0 - (self.age - self.RISE - self.HOLD) / self.SINK)

    @property
    def holding(self) -> bool:
        return self.RISE * 0.4 <= self.age < self.RISE + self.HOLD

    @property
    def top(self) -> float:
        return self.ground - self.HEIGHT * self.level

    @property
    def crest(self) -> float:
        """Where a thief hangs in the water (it bobs a little)."""
        return self.ground - self.HOLD_AT * min(1.0, self.level * 1.4)

    def column(self) -> pygame.Rect:
        top = self.top
        return pygame.Rect(round(self.x - self.WIDTH / 2), round(top - 6), self.WIDTH, round(self.ground - top + 6))

    # --- life ---------------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.age += dt
        if self.age >= 0 and not self.burst:
            self.burst = True
            emitters.splash(world.particles, self.x, self.ground, 1.4)
            world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.ground), "fountain_rise")
        if self.age > self.RISE + self.HOLD + self.SINK:
            self.alive = False
            return
        if self.age < 0:
            return
        rng = world.particles.rng
        top = self.top
        if self.level > 0.1 and world.on_screen(self.column(), 64):
            for _ in range(2):
                emitters.droplet(world.particles, self.x + rng.uniform(-14, 14), top, rng.uniform(-110, 110), -rng.uniform(40, 180))
            if rng.random() < 0.3:
                world.particles.spawn(self.x + rng.uniform(-16, 16), self.ground - 4, rng.uniform(-30, 30), -rng.uniform(10, 40),
                                      life=0.8, kind=Kind.SMOKE, size=6, size_end=18, color=(220, 244, 255), alpha=0.35)
        if not self.holding:
            return
        column = self.column()
        player = world.player
        if player.is_controllable and column.colliderect(player.rect):
            # Up the column, easing to a hover at its crest - like the aqueduct's own fountains.
            distance = player.body.bottom - (top - 4)
            player.apply_lift(-min(420.0, max(0.0, distance) * 7.5), 3600.0)
        for enemy in world.enemies:
            if enemy.alive and enemy.is_dangerous and column.colliderect(enemy.rect):
                enemy.knock_out(world, 1 if enemy.body.centerx > self.x else -1)
                emitters.splash(world.particles, enemy.body.centerx, enemy.body.centery, 0.8)
        for projectile in world.projectiles:
            if projectile.alive and not projectile.friendly and column.colliderect(projectile.rect):
                projectile.expire(world)
        if world.wonder is not None:
            world.wonder.guardian.on_power("fountain", self, world)

    # --- drawing ------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera, t: float) -> None:
        if self.age < 0:
            # The rose in flight, spinning, from the prince's hand to where it will bloom.
            u = 1 + self.age / self.FLIGHT
            (hx, hy), (gx, gy) = self.hand, (self.x, self.ground - 4)
            x = hx + (gx - hx) * u
            y = hy + (gy - hy) * u - math.sin(u * math.pi) * 36
            rose = art.rose_image(18, 1)
            rotated = pygame.transform.rotate(rose, u * 540)
            sx, sy = camera.to_screen(x, y)
            surface.blit(rotated, rotated.get_rect(center=(sx, sy)))
            blit_glow(surface, (sx, sy), 12, AQUA, 0.6)
            return
        bx, by = camera.to_screen(self.x, self.ground)
        level = self.level
        height = self.HEIGHT * level
        art.draw_column(surface, (bx, by - 2), height, t + self.x * 0.01, strength=min(1.0, level * 1.5))
        if level > 0.2:
            art.draw_crown(surface, (bx, by - height), self.shape, t, level)
            if 0.3 < self.age < self.RISE + self.HOLD:
                fade = min(1.0, (self.age - 0.3) / 0.4)
                art.draw_rainbow(surface, (bx + 26, by - height * 0.55), 34, 0.8 * fade * level)
        rose = art.rose_image(30, 4)
        surface.blit(rose, rose.get_rect(center=(bx, by - 2)))

    def lights(self) -> list[Light]:
        if self.age < 0 or self.level <= 0.05:
            return []
        return [Light(self.x, self.top + 10, 90, AQUA, 0.8 * self.level, bloom=0.3),
                Light(self.x, self.ground - 30, 70, AQUA, 0.6 * self.level)]


class RoseFountain(Power):
    key = "fountain"
    name = "Rose Fountain"
    arabic = "فوارة الوردة"
    summary = "Blooms into a fountain: it lifts the river-thieves out of their stolen water, and lifts you"
    color = AQUA
    cooldown = 2.6
    REACH = 6.5 * T

    def __init__(self, director) -> None:  # noqa: ANN001
        super().__init__(director)
        self.jets: list[Jet] = []
        self.shape = 0
        self.throw = 0.0

    def activate(self, world: "World", player: "Player") -> bool:
        x = self._target(world, player)
        ground = ground_below(world, x, player.body.top - 2 * T)
        if ground >= world.collision.pixel_height or ground < player.body.bottom - 6 * T:
            return False
        hand = (player.body.centerx + player.facing * 10, player.body.top + 12)
        self.jets.append(Jet(x, ground, self.shape, hand))
        self.jets = self.jets[-2:]
        self.shape += 1
        self.throw = 0.3
        world.events.emit(EventType.MACHINE_CLUNK, hand, "rose_throw")
        return True

    def _target(self, world: "World", player: "Player") -> float:
        """Under the nearest foe ahead; else under the prince if he stands still or is in the air; else ahead."""
        best, best_d = None, self.REACH
        candidates = [(e.body.centerx, e.body.bottom) for e in world.enemies if e.alive and e.is_dangerous]
        guardian = world.wonder.guardian if world.wonder is not None else None
        for performer in getattr(guardian, "cast", []):
            if performer.targetable:
                candidates.append((performer.body.centerx, performer.body.bottom))
        for x, bottom in candidates:
            ahead = (x - player.body.centerx) * player.facing
            if -12 <= ahead <= self.REACH and abs(bottom - player.body.bottom) < 2.5 * T and ahead < best_d:
                best, best_d = x, ahead
        if best is not None:
            return best
        if player.intent.move_axis == 0 or not player.body.on_ground:
            return player.body.centerx
        return player.body.centerx + player.facing * 3 * T

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.throw = max(0.0, self.throw - dt)
        for jet in self.jets:
            jet.update(dt, world)
        self.jets = [jet for jet in self.jets if jet.alive]

    def lights(self) -> list[Light]:
        lights = []
        for jet in self.jets:
            lights += jet.lights()
        return lights

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        # Behind the people: a thief held in the water, or the prince riding it, shows in front of the column.
        for jet in self.jets:
            jet.draw(surface, camera, self.time)

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.throw <= 0:
            return
        player = self.director.world.player
        hand = camera.to_screen(player.body.centerx + player.facing * 10, player.body.top + 12)
        blit_glow(surface, hand, 12, AQUA, self.throw * 2)

    # --- visual identity -----------------------------------------------------------------------------
    @classmethod
    def icon(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        art.draw_icon(surface, rect, t)

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        art.draw_miniature(surface, rect, t, ink_art.INK)

    @classmethod
    def ceremony(cls, surface: pygame.Surface, center: tuple[float, float], t: float) -> None:
        """The pages' ink runs together into a sphere of water; a brass rose blooms in it, raises a fountain
        with a golden ball dancing on its crest and a rainbow beside it, then closes and flies to Amir's hand."""
        cx, cy = center
        well = (cx, cy - 110)
        rng = random.Random(44)

        def sphere(radius: float, swirl: float) -> None:
            if radius < 1:
                return
            blit_glow(surface, well, round(radius * 2.2), AQUA, 0.5)
            pygame.draw.circle(surface, art.WATER_DEEP, (round(well[0]), round(well[1])), round(radius) + 2)
            pygame.draw.circle(surface, art.WATER, (round(well[0]), round(well[1])), round(radius))
            for k in range(3):
                points = []
                for j in range(12):
                    u = j / 11
                    a = swirl + k * math.tau / 3 + u * 3.0
                    points.append((well[0] + math.cos(a) * radius * 0.85 * u, well[1] + math.sin(a) * radius * 0.85 * u))
                pygame.draw.lines(surface, art.WATER_LIGHT, False, points, 1)

        if t < 0.25:
            u = t / 0.25
            for k in range(40):
                a0 = rng.uniform(0, math.tau)
                r0 = rng.uniform(150, 280)
                a = a0 + u * 2.6
                r = r0 * (1 - u) ** 1.3
                x, y = well[0] + math.cos(a) * r, well[1] + math.sin(a) * r * 0.7
                pygame.draw.circle(surface, art.WATER_DEEP, (round(x), round(y)), 3)
                pygame.draw.circle(surface, art.WATER_LIGHT, (round(x - 1), round(y - 1)), 1)
            sphere(28 * u, t * 10)
        elif t < 0.45:
            u = (t - 0.25) / 0.2
            sphere(28 * (1 - u), t * 10)
            rose = art.rose_image(round(26 + 30 * u), min(4, int(u * 5)))
            surface.blit(rose, rose.get_rect(center=(round(well[0]), round(well[1] + 20 * u))))
            for k in range(8):
                a = k * math.tau / 8 + t * 4
                pygame.draw.circle(surface, art.BRASS_LIGHT, (round(well[0] + math.cos(a) * 40 * u), round(well[1] + math.sin(a) * 14 * u)), 2)
        elif t < 0.82:
            u = (t - 0.45) / 0.37
            base = (well[0], well[1] + 20)
            rise = min(1.0, u * 3)
            height = 120 * rise
            art.draw_column(surface, base, height, t * 4)
            art.draw_crown(surface, (base[0], base[1] - height), 0, t * 4)
            ball = (round(base[0]), round(base[1] - height - 16 + math.sin(t * 30) * 3))
            pygame.draw.circle(surface, (90, 56, 20), ball, 9)
            pygame.draw.circle(surface, (250, 204, 96), ball, 8)
            pygame.draw.circle(surface, (255, 240, 190), (ball[0] - 3, ball[1] - 3), 3)
            art.draw_rainbow(surface, (base[0] + 40, base[1] - height * 0.5), 60, min(1.0, u * 2))
            rose = art.rose_image(56, 4)
            surface.blit(rose, rose.get_rect(center=(round(base[0]), round(base[1]))))
            for k in range(14):
                f = (t * 3 + k / 14) % 1.0
                x = base[0] + math.sin(k * 2.3) * 50 * f
                y = base[1] - height + f * f * 130
                pygame.draw.circle(surface, art.WATER_LIGHT, (round(x), round(y)), 2)
        else:
            u = (t - 0.82) / 0.18
            e = u * u * (3 - 2 * u)
            start = (well[0], well[1] + 20)
            end = (cx + 4, cy + 2)
            x = start[0] + (end[0] - start[0]) * e + math.sin(e * math.pi) * 50
            y = start[1] + (end[1] - start[1]) * e
            rose = art.rose_image(round(56 - 34 * e), 4 - int(e * 3))
            rotated = pygame.transform.rotate(rose, e * 360)
            surface.blit(rotated, rotated.get_rect(center=(round(x), round(y))))
            for k in range(5):
                lag = k * 0.06
                if e > lag:
                    pygame.draw.circle(surface, art.WATER_LIGHT, (round(x - (end[0] - start[0]) * lag), round(y - (end[1] - start[1]) * lag)), 2)
            if u > 0.9:
                blit_glow(surface, end, 26, AQUA, 0.7)
