"""The Night Qalam, the power taught by the three pages of level 2.

The scribe of al-Jazari's elephant clock writes the hours; the thief's
elephant has the setting sun, so Amir takes the scribe's other pen - one
whose ink is the night itself. Press POWER and he flicks it: a drop of night
flies ahead of him and writes a long level stroke through the air.

* The stroke is solid for a few seconds: a road written in the air that the
  prince can land on and run along (one stroke per jump).
* Night stops sunlight: a stroke between the stolen sun and a thief cuts the
  beam that gilds him, and cuts Tariq's lance and Samira's flame short.
* The drop splashes whatever it hits: a thief it strikes (or who walks into
  the wet ink) is blinded for a moment and inked - the sun can't gild him
  until it wears off. Ordinary creatures are knocked senseless, and enemy
  missiles are swallowed.
"""

import math
import random
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from jazari import art as ink_art
from jazari.base import Power
from objects.platforms import Platform
from rendering import emitters
from rendering.art import qalam
from rendering.art.kit import Canvas
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = 32
VIOLET = (170, 150, 255)


class InkRoad(Platform):
    """A stroke of night-ink hanging in the air; a man can stand on it until it dries."""

    SPEED = 780.0
    RANGE = 250.0
    LIFE = 4.5

    def __init__(self, start: tuple[float, float], direction: int) -> None:
        super().__init__(start[0], start[1] - 4, 1, 8)
        self.x0, self.y = start
        self.direction = direction
        self.length = 0.0
        self.flying = True
        self.age = 0.0
        self.alive = True
        self.phase = random.uniform(0, math.tau)
        self.stars = qalam.make_stars(random.randrange(10_000))
        self.splat: tuple[float, float] | None = None
        self.touched: set[int] = set()
        self._resize()

    # --- geometry ------------------------------------------------------------------------------------
    @property
    def head(self) -> tuple[float, float]:
        return self.x0 + self.direction * self.length, self.y

    @property
    def wet(self) -> bool:
        return self.age < self.LIFE - 1.2

    def span(self) -> tuple[float, float]:
        a = self.x0
        b = self.x0 + self.direction * self.length
        return min(a, b), max(a, b)

    def blocks(self, a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
        """Where the segment a->b crosses this stroke (it stops light), if it does."""
        if self.length < 4:
            return None
        (ax, ay), (bx, by) = a, b
        if (ay - self.y) * (by - self.y) > 0 or ay == by:
            return None
        u = (self.y - ay) / (by - ay)
        x = ax + (bx - ax) * u
        left, right = self.span()
        if left - 4 <= x <= right + 4:
            return x, self.y
        return None

    def overlaps(self, rect: pygame.Rect) -> bool:
        left, right = self.span()
        return rect.clipline((left, self.y), (right, self.y)) != ()

    def _resize(self) -> None:
        left, right = self.span()
        self.position.update(left, self.y - 4)
        self.width = max(1, round(right - left))
        self._previous_top = self.position.y

    # --- life --------------------------------------------------------------------------------------------
    def stop(self, world: "World", length: float, splash: bool = True) -> None:
        self.length = max(0.0, min(self.length, length))
        self.flying = False
        self._resize()
        if splash:
            self.splat = self.head
            x, y = self.head
            rng = world.particles.rng
            for _ in range(14):
                a = rng.uniform(0, math.tau)
                speed = rng.uniform(60, 200)
                world.particles.spawn(x, y, math.cos(a) * speed, math.sin(a) * speed - 60, life=rng.uniform(0.4, 0.8),
                                      kind=Kind.DOT, size=rng.uniform(1.5, 3.0), color=qalam.INK, color_end=qalam.INK_RIM,
                                      gravity=700)
            for _ in range(5):
                world.particles.spawn(x + rng.uniform(-8, 8), y + rng.uniform(-8, 8), 0, -24, life=0.8,
                                      kind=Kind.TWINKLE, size=3, color=qalam.STAR, color_end=qalam.INK_RIM)

    def update(self, dt: float, world: "World") -> None:
        self.age += dt
        if self.flying:
            before = self.length
            self.length = min(self.RANGE, self.length + self.SPEED * dt)
            self._sweep(world, before)
            if self.flying and self.length >= self.RANGE:
                self.flying = False
            self._resize()
            if world.particles.rng.random() < 0.6:
                x, y = self.head
                world.particles.spawn(x, y + world.particles.rng.uniform(-4, 4), -self.direction * 30, 10, life=0.4,
                                      kind=Kind.DOT, size=1.6, color=qalam.INK_RIM, color_end=qalam.INK)
        if self.wet and world.wonder is not None:
            world.wonder.guardian.on_power("ink", self, world)
        if self.age >= self.LIFE:
            self.alive = False

    def _sweep(self, world: "World", before: float) -> None:
        """Whatever the flying drop passed through since the last step."""
        collision = world.collision
        step = 4.0
        d = before
        while d <= self.length:
            x = self.x0 + self.direction * d
            tx, ty = collision.tile_at(x, self.y)
            if collision.get(tx, ty).name == "SOLID":
                self.stop(world, d)
                world.events.emit(EventType.MACHINE_CLUNK, (x, self.y), "ink_splat")
                return
            d += step
        segment = ((self.x0 + self.direction * before, self.y), self.head)
        for enemy in world.enemies:
            if enemy.alive and enemy.is_dangerous and enemy.rect.clipline(*segment):
                enemy.knock_out(world, self.direction)
                self.stop(world, abs(enemy.body.centerx - self.x0))
                world.events.emit(EventType.MACHINE_CLUNK, self.head, "ink_splat")
                return
        for projectile in world.projectiles:
            if projectile.alive and not projectile.friendly and projectile.rect.inflate(8, 8).clipline(*segment):
                projectile.expire(world)

    # --- drawing -------------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        start = camera.to_screen(self.x0, self.y)
        qalam.draw_stroke(surface, start, self.length, self.direction, self.age + self.phase, self.age, self.LIFE,
                          self.phase, self.stars)
        if self.splat is not None and self.age < self.LIFE - 0.3:
            x, y = camera.to_screen(*self.splat)
            r = 7 + 2 * math.sin(self.phase)
            points = []
            for k in range(14):
                a = k * math.tau / 14 + self.phase
                rr = r * (1.0 if k % 2 else 0.55) * (1.0 + 0.2 * math.sin(k * 2.3 + self.phase))
                points.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
            pygame.draw.polygon(surface, qalam.INK_RIM, [(px + 1, py + 1) for px, py in points])
            pygame.draw.polygon(surface, qalam.INK, points)
        if self.flying:
            qalam.draw_comet(surface, camera.to_screen(*self.head), self.direction, self.age * 10)

    def lights(self) -> list[Light]:
        if self.length < 8:
            return []
        left, right = self.span()
        fade = 1.0 if self.wet else max(0.0, (self.LIFE - self.age) / 1.2)
        return [Light(left + (right - left) * f, self.y, 44, VIOLET, 0.5 * fade) for f in (0.15, 0.5, 0.85)]


class NightQalam(Power):
    key = "qalam"
    name = "Night Qalam"
    arabic = "قلم الليل"
    summary = "Writes a road of night: it stops the stolen sun and blots the thieves"
    color = VIOLET
    cooldown = 3.5

    def __init__(self, director) -> None:  # noqa: ANN001
        super().__init__(director)
        self.roads: list[InkRoad] = []
        self.flourish = 0.0
        self.air_used = False

    def activate(self, world: "World", player: "Player") -> bool:
        if not player.body.on_ground:
            if self.air_used:
                return False
            self.air_used = True
        hand = (player.body.centerx + player.facing * 12, player.body.top + 12)
        road = InkRoad(hand, player.facing)
        world.platforms.append(road)
        self.roads.append(road)
        self.flourish = 0.35
        rng = world.particles.rng
        for _ in range(8):
            world.particles.spawn(hand[0], hand[1], player.facing * rng.uniform(40, 140), rng.uniform(-80, 20),
                                  life=0.4, kind=Kind.DOT, size=1.8, color=qalam.INK_RIM, color_end=qalam.INK)
        world.events.emit(EventType.MACHINE_CLUNK, hand, "ink_flick")
        return True

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        if world.player.body.on_ground and world.player.body.ground_platform not in self.roads:
            self.air_used = False
        self.flourish = max(0.0, self.flourish - dt)
        for road in self.roads:
            if not road.alive:
                if road in world.platforms:
                    world.platforms.remove(road)
                self._flake(world, road)
        self.roads = [road for road in self.roads if road.alive]

    @staticmethod
    def _flake(world: "World", road: InkRoad) -> None:
        """The dried stroke breaks into flakes, and its stars drift up out of it."""
        rng = world.particles.rng
        left, right = road.span()
        for _ in range(int((right - left) / 8) + 4):
            x = rng.uniform(left, right)
            world.particles.spawn(x, road.y + rng.uniform(-3, 3), rng.uniform(-20, 20), rng.uniform(-10, 40), life=rng.uniform(0.5, 1.0),
                                  kind=Kind.SQUARE, size=rng.uniform(1.5, 3.0), color=qalam.DRY, color_end=qalam.INK, gravity=400)
        for su, _sv, _sp in road.stars[:8]:
            x = road.x0 + road.direction * su * road.length
            world.particles.spawn(x, road.y, rng.uniform(-10, 10), -rng.uniform(30, 60), life=1.2, kind=Kind.TWINKLE,
                                  size=2.5, color=qalam.STAR, color_end=qalam.INK_RIM, drag=1.0)
        world.events.emit(EventType.MACHINE_CLUNK, (road.x0, road.y), "ink_dry")

    def lights(self) -> list[Light]:
        return []

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.flourish <= 0:
            return
        player = self.director.world.player
        u = 1 - self.flourish / 0.35
        hand = camera.to_screen(player.body.centerx + player.facing * 12, player.body.top + 12)
        angle = (-40 + 110 * u) if player.facing > 0 else (220 - 110 * u)
        pen = qalam.pen_image(22, round(angle) % 360)
        surface.blit(pen, pen.get_rect(center=hand))
        blit_glow(surface, hand, 12, VIOLET, 0.6 * (1 - u))

    # --- visual identity --------------------------------------------------------------------------------------
    @classmethod
    def icon(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        qalam.draw_icon(surface, rect, t)

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        """The pen and its inkwell of night, as painted in the book, with a stroke it has written."""
        size = min(rect.width, rect.height)
        well = qalam.inkwell_image(round(size * 0.55))
        surface.blit(well, well.get_rect(midbottom=(rect.left + rect.width * 0.3, rect.bottom - 4)))
        y = rect.top + rect.height * 0.42
        length = rect.width * 0.62
        qalam.draw_stroke(surface, (rect.left + rect.width * 0.24, y), length, 1, t, 0.0, 99.0, 0.7, qalam.make_stars(4, 8))
        pen = qalam.pen_image(round(size * 0.7), 140)
        surface.blit(pen, pen.get_rect(center=(rect.left + rect.width * 0.24 + length + size * 0.18, y - size * 0.2)))
        pygame.draw.line(surface, ink_art.INK, (rect.left + 6, rect.bottom - 3), (rect.right - 6, rect.bottom - 3), 1)

    @classmethod
    def ceremony(cls, surface: pygame.Surface, center: tuple[float, float], t: float) -> None:
        """The pages' ink lifts off into a sphere of night; a golden pen dips in, writes Amir's name in
        starlight, drinks the letters back, and flies to his sash."""
        cx, cy = center
        book = (cx, cy - 90)
        rng = random.Random(21)
        name = qalam.name_in_night(104)
        nw, nh = name.get_size()
        name_rect = name.get_rect(center=(round(book[0]), round(book[1] - 10)))
        well_pos = (book[0] + nw * 0.62, book[1] + 40)

        def sphere(radius: float, swirl: float) -> None:
            if radius < 1:
                return
            blit_glow(surface, well_pos, round(radius * 2.4), qalam.INK_RIM, 0.55)
            pygame.draw.circle(surface, qalam.INK_RIM, (round(well_pos[0]), round(well_pos[1])), round(radius) + 2)
            pygame.draw.circle(surface, qalam.INK, (round(well_pos[0]), round(well_pos[1])), round(radius))
            for k in range(3):
                points = []
                for j in range(14):
                    u = j / 13
                    a = swirl + k * math.tau / 3 + u * 3.2
                    r = radius * 0.9 * u
                    points.append((well_pos[0] + math.cos(a) * r, well_pos[1] + math.sin(a) * r * 0.8))
                pygame.draw.lines(surface, qalam.INK_SHEEN, False, points, 1)
            for k in range(12):
                a = k * 2.4 + swirl * 0.5
                r = radius * (0.2 + 0.7 * ((k * 37) % 10) / 10)
                if int(t * 40 + k) % 4:
                    surface.fill(qalam.STAR if k % 3 else qalam.STAR_GOLD,
                                 (round(well_pos[0] + math.cos(a) * r), round(well_pos[1] + math.sin(a) * r * 0.8), 1, 1))

        def pen_at(tip: tuple[float, float], angle_deg: int, size: int = 44) -> None:
            image = qalam.pen_image(size, angle_deg % 360)
            a = math.radians(angle_deg)
            surface.blit(image, image.get_rect(center=(round(tip[0] - math.cos(a) * size / 2), round(tip[1] - math.sin(a) * size / 2))))
            blit_glow(surface, tip, 10, qalam.STAR_GOLD, 0.8)

        if t < 0.22:
            u = t / 0.22
            # The ink lifts from the three pages as little strokes and spirals together.
            for k in range(46):
                a0 = rng.uniform(0, math.tau)
                r0 = rng.uniform(160, 300)
                a = a0 + u * 3.0
                r = r0 * (1 - u) ** 1.4
                x, y = well_pos[0] + math.cos(a) * r, well_pos[1] + math.sin(a) * r * 0.7
                length = 6 + 6 * (1 - u)
                pygame.draw.line(surface, qalam.INK_RIM, (x, y), (x + math.cos(a + 1.6) * length, y + math.sin(a + 1.6) * length), 3)
                pygame.draw.line(surface, qalam.INK, (x, y), (x + math.cos(a + 1.6) * length, y + math.sin(a + 1.6) * length), 2)
            sphere(30 * u, t * 12)
        elif t < 0.34:
            u = (t - 0.22) / 0.12
            sphere(30, t * 12)
            dip = math.sin(u * math.pi)
            tip = (well_pos[0] + 6, well_pos[1] - 60 + 58 * dip)
            pen_at(tip, 250)
            if dip > 0.8:
                for k in range(3):
                    r = 30 + k * 8 + u * 20
                    pygame.draw.ellipse(surface, qalam.INK_RIM, (well_pos[0] - r, well_pos[1] - r * 0.3, r * 2, r * 0.6), 1)
        elif t < 0.74:
            u = (t - 0.34) / 0.40
            sphere(30 * (1 - 0.6 * u), t * 12)
            # Writing right to left, as Arabic is written.
            reveal = max(1, round(nw * u))
            part = name.subsurface((nw - reveal, 0, reveal, nh))
            surface.blit(part, (name_rect.right - reveal, name_rect.top))
            nib = (name_rect.right - reveal, name_rect.top + nh * (0.45 + 0.25 * math.sin(u * 23)))
            pen_at(nib, 235)
            for k in range(3):
                surface.fill(qalam.STAR_GOLD, (round(nib[0] + rng.uniform(-6, 6)), round(nib[1] + rng.uniform(-6, 6)), 1, 1))
        elif t < 0.88:
            u = (t - 0.74) / 0.14
            sphere(12 * (1 - u), t * 12)
            fade = name.copy()
            fade.set_alpha(round(255 * (1 - u)))
            surface.blit(fade, name_rect)
            glint = name_rect.left + name_rect.width * u
            pygame.draw.line(surface, qalam.STAR_GOLD, (glint, name_rect.top + 4), (glint - 10, name_rect.bottom - 4), 2)
            pen_tip = (name_rect.centerx, name_rect.bottom + 34)
            pen_at(pen_tip, 270)
            # The letters flow back into the pen.
            for k in range(34):
                sx = name_rect.left + rng.uniform(0, name_rect.width)
                sy = name_rect.top + rng.uniform(0.2, 0.8) * name_rect.height
                f = min(1.0, u * 1.4 - rng.uniform(0, 0.4))
                if f <= 0:
                    continue
                x = sx + (pen_tip[0] - sx) * f
                y = sy + (pen_tip[1] - sy) * f
                pygame.draw.circle(surface, qalam.INK_RIM, (round(x), round(y)), 2)
                surface.fill(qalam.STAR, (round(x), round(y), 1, 1))
        else:
            u = (t - 0.88) / 0.12
            e = u * u * (3 - 2 * u)
            start = (name_rect.centerx, name_rect.bottom + 34)
            end = (cx + 4, cy + 2)
            x = start[0] + (end[0] - start[0]) * e + math.sin(e * math.pi) * 60
            y = start[1] + (end[1] - start[1]) * e
            pen_at((x, y), round(270 + 720 * e), round(44 - 24 * e))
            for k in range(5):
                lag = k * 0.06
                if e > lag:
                    pygame.draw.circle(surface, qalam.STAR_GOLD, (round(x - (end[0] - start[0]) * lag), round(y - (end[1] - start[1]) * lag)), 1)
            if u > 0.9:
                blit_glow(surface, end, 26, qalam.STAR_GOLD, 0.7)
