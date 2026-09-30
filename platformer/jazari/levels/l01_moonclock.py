"""Level 1's finale: the Moon-Clock Fountain and the Moon Troupe.

The thief's players have turned the orchard's fountain into a clock that
pours the orchard's water up into a floating moon. Three performers are
poured down from it one after another, each held in a bubble of moon-water
and hung from the moon on a glowing string, like a marionette.

* Rashid the Juggler lobs oranges; slash one in the air and it flies back.
* Zahra the Blossom Dancer steps through petals to kick from behind.
* Layla the Water-Weaver lashes a water whip and calls the moon's tide.

Every few seconds the moon itself swells and pours: geysers burst from the
shimmering spots on the ground (they throw the prince up; they don't hurt).

The hard way: cut a performer's string with a jumping slash (the bubble can
no longer heal), burst the bubble with three blows, then strike before it
heals. The Brass Nightingale's song bursts every bubble in reach, snaps the
strings, stuns the performers and cancels a gathering tide.

Each performer beaten wanes the moon. When the last one falls, the moon
cracks and drops into the basin, and the water runs home to the orchard.
"""

import math
import random
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from entities.troupe import Dancer, Juggler, Performer, Weaver
from jazari import art as ink
from jazari.base import Guardian, ground_below, shove
from rendering import emitters
from rendering.art import moonclock as art
from rendering.art.troupe import portrait
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from jazari.director import WonderDirector
    from world.world import World

T = 32
PHASES = (1.0, 0.72, 0.44, 0.14)
TIDE_EVERY = 8.0
SNAP_TIME = 7.0        # a string snapped by the song stays broken this long
CUT_TIME = 4.0         # ...and one cut by a blade
STUN_TIME = 2.4
CURTAIN = 3.2
INTERLUDE = 1.8
POUR_TIME = 0.75
GEYSER_HEIGHT = 170.0
DUSK_RATE = 0.55
STRING: tuple[int, int, int] = (150, 236, 246)
STRING_CORE: tuple[int, int, int] = (236, 255, 255)
MOONLIGHT: tuple[int, int, int] = (150, 210, 255)
BUBBLE_TINT: tuple[int, int, int] = (150, 226, 240)
RAINBOW = ((255, 90, 90), (255, 170, 70), (255, 236, 110), (120, 230, 120), (90, 190, 255), (120, 110, 240), (190, 110, 230))


# --- the machine ------------------------------------------------------------------------------------------
class MoonClock:
    """State and drawing of the fountain: moon, rings, column, basin, musicians, water."""

    def __init__(self, x: float, floor: float, phase: float) -> None:
        self.x = x
        self.floor = floor
        self.time = 0.0
        self.radius = float(art.MOON_RADIUS)
        self.moon_y = floor + art.MOON_Y
        self.phase = self.phase_target = phase
        self.power = self.power_target = 0.2
        self.swell = self.swell_target = 0.0
        self.shiver = 0.0
        self.crack = 0.0
        self.falling = False
        self.fall_speed = 0.0
        self.fallen = False
        self.pearl = 0.0
        self.flow = 0.0
        self.rainbow = -1.0
        self.zodiac = 0.0
        self.meridian = 0.8
        self.helix = 0.0
        self.drips: list[list[float]] = []
        self.ripples: list[list[float]] = []
        self.drip_timer = 0.6
        self.playing = False
        self.bow = 0.0

    @property
    def moon(self) -> tuple[float, float]:
        shake = math.sin(self.time * 47) * 2.5 * self.shiver
        return self.x + shake, self.moon_y

    @property
    def water_y(self) -> float:
        return self.floor + art.RIM_Y

    def update(self, dt: float) -> None:
        self.time += dt
        self.power += (self.power_target - self.power) * min(1.0, dt * 1.4)
        self.swell += (self.swell_target - self.swell) * min(1.0, dt * 5)
        self.shiver = max(0.0, self.shiver - dt * 1.6)
        self.phase += (self.phase_target - self.phase) * min(1.0, dt * 1.5)
        spin = 0.12 + 0.88 * self.power
        self.zodiac += dt * spin * 0.7
        self.meridian += dt * spin * 0.45
        self.helix += dt * (0.25 + 0.9 * self.power) * (-1.0 if self.fallen else 1.0)
        if self.falling:
            self.fall_speed += 1500 * dt
            self.moon_y += self.fall_speed * dt
        elif self.fallen:
            self.pearl = min(1.0, self.pearl + dt * 0.9)
            self.radius = art.MOON_RADIUS + (12 - art.MOON_RADIUS) * self.pearl
            self.moon_y = self.water_y - 3 + math.sin(self.time * 1.6) * 1.5
            self.flow = min(1.0, self.flow + dt * 0.6)
        else:
            self.moon_y = self.floor + art.MOON_Y + math.sin(self.time * 1.1) * 4 - self.swell * 6
        if self.rainbow >= 0:
            self.rainbow += dt
        if not self.falling and not self.fallen:
            self.drip_timer -= dt * (0.5 + self.power)
            if self.drip_timer <= 0:
                self.drip_timer = 0.8
                self.drips.append([self.x + random.uniform(-10, 10), self.moon_y + self.radius, 0.0])
        for drip in self.drips:
            drip[2] += 900 * dt
            drip[1] += drip[2] * dt
            if drip[1] >= self.water_y:
                self.ripples.append([drip[0] - self.x, 0.0])
        self.drips = [d for d in self.drips if d[1] < self.water_y]
        for ripple in self.ripples:
            ripple[1] += dt
        self.ripples = [r for r in self.ripples if r[1] < 1.3]
        if self.bow > 0:
            self.bow = max(0.0, self.bow - dt)

    # --- drawing ---------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera, dusk: float) -> None:
        fx, fy = camera.to_screen(self.x, self.floor)
        if 0 <= self.rainbow < 5.5:
            self._draw_rainbow(surface, (fx, fy - 40))
        column = art.column()
        top = fy + art.COLUMN_TOP
        surface.blit(column, (fx - column.get_width() // 2, top))
        self._draw_helix(surface, fx, top + 10, fy + art.RIM_Y - 3)
        mx, my = camera.to_screen(*self.moon)
        cradle_x, cradle_y = fx, fy + art.MOON_Y
        if self.fallen or self.falling:
            art.draw_armillary(surface, (cradle_x, cradle_y), art.MOON_RADIUS, self.zodiac, self.meridian, False, 0.0)
            cradle = art.cradle()
            surface.blit(cradle, (cradle_x - art.CRADLE_ORIGIN[0], cradle_y - art.CRADLE_ORIGIN[1]))
            art.draw_armillary(surface, (cradle_x, cradle_y), art.MOON_RADIUS, self.zodiac, self.meridian, True, 0.0)
            if self.falling:
                self._draw_moon(surface, (mx, my), dusk)
        else:
            art.draw_armillary(surface, (mx, my), art.MOON_RADIUS, self.zodiac, self.meridian, False, self.power)
            self._draw_moon(surface, (mx, my), dusk)
            cradle = art.cradle()
            surface.blit(cradle, (cradle_x - art.CRADLE_ORIGIN[0], cradle_y - art.CRADLE_ORIGIN[1]))
            art.draw_armillary(surface, (mx, my), art.MOON_RADIUS, self.zodiac, self.meridian, True, self.power)
        for drip in self.drips:
            dx, dy = camera.to_screen(drip[0], drip[1])
            pygame.draw.line(surface, art.WATER_LIGHT, (dx, dy - 5), (dx, dy), 2)
        basin = art.basin()
        surface.blit(basin, (fx - art.BASIN_ORIGIN[0], fy - art.BASIN_ORIGIN[1]))
        self._draw_water(surface, fx, fy + art.RIM_Y, dusk)
        if self.fallen:
            self._draw_moon(surface, (mx, my), dusk)
        self._draw_musicians(surface, fx, fy + art.RIM_Y + 4)
        if self.flow > 0:
            self._draw_flow(surface, camera, fx, fy)

    def _draw_moon(self, surface: pygame.Surface, center: tuple[float, float], dusk: float) -> None:
        glow = 0.25 + 0.35 * self.power + 0.45 * self.swell + 0.2 * dusk
        blit_glow(surface, center, round(self.radius * 2.6 + 20 * self.swell), MOONLIGHT, min(1.0, glow))
        image = art.render_moon(self.radius + 3 * self.swell, self.phase, self.time, self.swell, self.crack, self.pearl)
        surface.blit(image, image.get_rect(center=(round(center[0]), round(center[1]))))

    def _draw_helix(self, surface: pygame.Surface, x: float, top: float, bottom: float) -> None:
        height = bottom - top
        for k in range(16):
            for strand in (0.0, math.pi):
                u = (self.helix + k / 16) % 1.0
                y = bottom - u * height
                a = u * 16 + strand
                front = math.cos(a) > 0
                px = x + math.sin(a) * 3
                color = art.WATER_LIGHT if front else art.WATER
                pygame.draw.circle(surface, color, (round(px), round(y)), 2 if front else 1)

    def _draw_water(self, surface: pygame.Surface, x: float, y: float, dusk: float) -> None:
        rx, ry = art.WATER_RX - 2, art.WATER_RY - 1
        rect = pygame.Rect(0, 0, rx * 2, ry * 2)
        rect.center = (round(x), round(y))
        pygame.draw.ellipse(surface, art.WATER, rect)
        pygame.draw.ellipse(surface, art.WATER_LIGHT, rect.inflate(-6, -4), 1)
        # Moonlight lying on the water in broken strokes.
        for k in range(7):
            wx = x + (k - 3) * 9 + math.sin(self.time * 2 + k) * 3
            width = 10 - abs(k - 3) * 2
            pygame.draw.line(surface, (236, 252, 255), (wx - width / 2, y + math.sin(self.time * 3 + k) * 1.5),
                             (wx + width / 2, y + math.sin(self.time * 3 + k) * 1.5), 1)
        for dx, age in self.ripples:
            r = 4 + age * 26
            ring = pygame.Rect(0, 0, round(r * 2), round(r * 0.6))
            ring.center = (round(x + dx), round(y))
            shade = max(0.0, 1.0 - age / 1.3)
            color = tuple(round(a + (b - a) * (1 - shade)) for a, b in zip(art.WATER_LIGHT, art.WATER))
            pygame.draw.ellipse(surface, color, ring, 1)

    def _draw_musicians(self, surface: pygame.Surface, x: float, rim_y: float) -> None:
        tempo = 6.5 if self.playing else 0.0
        for kind, dx in (("drum", art.MUSICIAN_XS[0]), ("ney", art.MUSICIAN_XS[1])):
            frames = art.musician_frames(kind)
            index = 4 if self.bow > 0 else (int(self.time * tempo) % 4 if tempo else 0)
            image = frames[index]
            if dx > 0:
                image = pygame.transform.flip(image, True, False)
            surface.blit(image, (round(x + dx - art.MUSICIAN_ORIGIN[0]), round(rim_y - art.MUSICIAN_ORIGIN[1])))

    def _draw_flow(self, surface: pygame.Surface, camera: Camera, fx: float, fy: float) -> None:
        """Water pours from the lions' mouths and runs home along the ground."""
        flow = self.flow
        for lion in art.LION_XS:
            mouth = (fx + lion, fy - 11)
            direction = -1 if lion <= 0 else 1
            points = []
            for k in range(9):
                u = k / 8 * flow
                points.append((mouth[0] + direction * u * 26, mouth[1] + u * u * 11 + u * 2))
            if len(points) > 1:
                pygame.draw.lines(surface, art.WATER, False, points, 4)
                pygame.draw.lines(surface, art.WATER_LIGHT, False, points, 1)
        # A shining stream along the ground, flowing left toward the orchard.
        length = 900 * flow
        left = fx - 150 - length
        stream = pygame.Rect(round(left), fy - 3, round(length + 150), 4)
        pygame.draw.rect(surface, art.WATER, stream)
        for k in range(int(length / 26) + 6):
            sx = fx - 140 - ((self.time * 70 + k * 26) % (length + 140))
            pygame.draw.line(surface, art.WATER_LIGHT, (sx, fy - 2), (sx - 8, fy - 2), 1)

    def _draw_rainbow(self, surface: pygame.Surface, center: tuple[float, float]) -> None:
        t = self.rainbow
        strength = min(1.0, t / 0.8) * min(1.0, max(0.0, (5.5 - t) / 1.5))
        if strength <= 0.01:
            return
        radius = 240
        layer = pygame.Surface((radius * 2 + 40, radius + 30), pygame.SRCALPHA)
        c = (radius + 20, radius + 20)
        for k, color in enumerate(RAINBOW):
            r = radius - k * 6
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = c
            pygame.draw.arc(layer, (*color, round(110 * strength)), rect, 0.05, math.pi - 0.05, 6)
        surface.blit(layer, (round(center[0] - c[0]), round(center[1] - c[1])))

    def lights(self) -> list[Light]:
        mx, my = self.moon
        lights = [Light(self.x, self.water_y, 150, (120, 200, 240), 0.3 + 0.25 * self.power)]
        if self.fallen:
            lights.append(Light(mx, my, 130, (220, 244, 255), 0.7, bloom=0.3))
        else:
            lights.append(Light(mx, my, 240 + 40 * self.swell, MOONLIGHT, min(1.0, 0.45 + 0.35 * self.power + 0.3 * self.swell),
                                bloom=0.35 * self.power + 0.3 * self.swell))
        return lights


# --- strings, tides and entrances --------------------------------------------------------------------------
class Tether:
    """The glowing string from the moon to a performer's bubble: while attached, the bubble heals."""

    def __init__(self, performer: Performer) -> None:
        self.performer = performer
        self.grow = 0.0
        self.cut = 0.0
        self.recoil = 0.0
        self.retract = False
        self.snap_at = 0.5
        self.time = random.uniform(0, 10)

    @property
    def attached(self) -> bool:
        return self.cut <= 0 and self.grow >= 1.0 and not self.retract

    def update(self, dt: float) -> None:
        self.time += dt
        self.recoil = max(0.0, self.recoil - dt * 1.4)
        if self.retract:
            self.grow = max(0.0, self.grow - dt / 0.7)
        elif self.cut > 0:
            self.cut -= dt
            if self.cut <= 0:
                self.grow = 0.0
        else:
            self.grow = min(1.0, self.grow + dt / 0.8)
        self.performer.tethered = self.attached

    def curve(self, moon: tuple[float, float], radius: float, steps: int = 16) -> list[tuple[float, float]]:
        """From the moon's belly, out sideways, then straight down onto the performer's crown."""
        mx, my = moon[0], moon[1] + radius * 0.8
        ex, ey = self.performer.tether_point
        cx, cy = ex, my + 20
        sway = math.sin(self.time * 1.7) * 6
        points = []
        for k in range(steps + 1):
            u = k / steps
            x = (1 - u) ** 2 * mx + 2 * (1 - u) * u * (cx + sway) + u * u * ex
            y = (1 - u) ** 2 * my + 2 * (1 - u) * u * cy + u * u * ey
            points.append((x, y))
        return points

    def snap(self, world: "World", moon: tuple[float, float], radius: float, at: float = 0.5,
             duration: float = SNAP_TIME) -> None:
        if not self.attached:
            return
        points = self.curve(moon, radius)
        index = max(1, min(len(points) - 2, round(at * (len(points) - 1))))
        x, y = points[index]
        self.cut = duration
        self.recoil = 1.0
        self.snap_at = index / (len(points) - 1)
        rng = world.particles.rng
        for _ in range(14):
            world.particles.spawn(x, y, rng.uniform(-150, 150), rng.uniform(-160, 60), life=rng.uniform(0.4, 0.8),
                                  kind=Kind.DOT, size=rng.uniform(1.5, 2.6), color=STRING_CORE, color_end=art.WATER, gravity=700)
        world.particles.spawn(x, y, life=0.3, kind=Kind.GLOW, size=26, size_end=26, color=STRING, alpha=0.9)
        world.events.emit(EventType.MACHINE_CLUNK, (x, y), "tether_snap")

    def draw(self, surface: pygame.Surface, camera: Camera, moon: tuple[float, float], radius: float) -> None:
        if self.performer.gone:
            return
        points = [camera.to_screen(x, y) for x, y in self.curve(moon, radius)]
        count = len(points)
        if self.cut > 0 or (self.recoil > 0 and self.grow < 1):
            # Snapped: the upper end springs back toward the moon; the lower end drips over the bubble.
            cut_index = max(1, round(self.snap_at * (count - 1)))
            spring = 1.0 - self.recoil
            upper = points[:max(2, round(cut_index * (1 - 0.6 * spring)) + 1)]
            lower = points[min(count - 2, cut_index + round((count - cut_index) * 0.7 * spring)):]
            for part in (upper, lower):
                if len(part) >= 2:
                    wobble = [(x + math.sin(self.time * 18 + i) * 3 * self.recoil, y) for i, (x, y) in enumerate(part)]
                    pygame.draw.lines(surface, (40, 110, 150), False, wobble, 3)
                    pygame.draw.lines(surface, STRING, False, wobble, 1)
            return
        visible = max(2, round(count * self.grow))
        part = points[:visible]
        pygame.draw.lines(surface, (30, 96, 140), False, part, 4)
        pygame.draw.lines(surface, STRING, False, part, 2)
        pygame.draw.lines(surface, STRING_CORE, False, part, 1)
        # Beads of light run down the string; quickly while it is healing a bubble.
        performer = self.performer
        healing = self.attached and performer.shield <= 0
        speed = 1.6 if healing else 0.45
        for k in range(3 if healing else 2):
            u = (self.time * speed + k / 3) % 1.0
            if u > self.grow:
                continue
            index = min(visible - 1, int(u * (count - 1)))
            blit_glow(surface, part[index], 9 if healing else 6, STRING, 0.9 if healing else 0.5)


class Tide:
    """The moon swells, then pours: geysers burst from the shimmering spots."""

    SWELL = 1.05
    POUR = 0.3
    GUSH = 0.75
    FALL = 0.35

    def __init__(self, spots: list[float], big: bool = False, intro: bool = False) -> None:
        self.spots = spots
        self.big = big
        self.intro = intro
        self.time = 0.0
        self.cancelled = False
        self.launched: set[int] = set()
        self.started = False

    @property
    def stage(self) -> str:
        t = self.time
        if t < self.SWELL:
            return "swell"
        if t < self.SWELL + self.POUR:
            return "pour"
        if t < self.SWELL + self.POUR + self.GUSH:
            return "gush"
        if t < self.SWELL + self.POUR + self.GUSH + self.FALL:
            return "fall"
        return "done"

    @property
    def height(self) -> float:
        u = self.time - self.SWELL - self.POUR
        if u <= 0:
            return 0.0
        if u < 0.12:
            return u / 0.12
        if u < self.GUSH:
            return 1.0 + math.sin(u * 30) * 0.03
        return max(0.0, 1.0 - (u - self.GUSH) / self.FALL)

    def column(self, x: float, floor: float) -> pygame.Rect:
        h = GEYSER_HEIGHT * (1.15 if self.big else 1.0) * self.height
        return pygame.Rect(round(x - 20), round(floor - h), 40, round(h))


class Pour:
    """A drop of moon-water carrying the next performer down to the ground."""

    def __init__(self, performer: Performer, start: tuple[float, float], end: tuple[float, float]) -> None:
        self.performer = performer
        self.start = start
        self.end = end
        self.time = 0.0

    @property
    def done(self) -> bool:
        return self.time >= POUR_TIME

    @property
    def position(self) -> tuple[float, float]:
        u = min(1.0, self.time / POUR_TIME)
        x = self.start[0] + (self.end[0] - self.start[0]) * (1 - (1 - u) ** 2)
        y = self.start[1] + (self.end[1] - self.start[1]) * u * u - math.sin(u * math.pi) * 40
        return x, y


# --- the encounter --------------------------------------------------------------------------------------------
class MoonTroupe(Guardian):
    name = "The Moon Troupe"
    device = "The Moon-Clock Fountain"
    lethal = True
    reach = 15
    intro = "The Moon Troupe! They are pouring the orchard's last water into their moon!"
    farewell = "The moon falls, and the stolen water runs home to the orchard."
    music = "troupe"

    def __init__(self, director: "WonderDirector", x: float, floor: float) -> None:
        super().__init__(director, x, floor)
        world = director.world
        self.left, self.right = self._measure(world)
        self.arena = pygame.Rect(self.left, round(floor - 12 * T), self.right - self.left, 12 * T)
        bounds = (self.left + 10.0, self.right - 10.0)
        sprites = world.sprites
        self.cast: list[Performer] = [Juggler(x, floor, sprites, bounds), Dancer(x, floor, sprites, bounds),
                                      Weaver(x, floor, sprites, bounds)]
        self.act = max(0, min(3, getattr(director, "progress", 0)))
        for performer in self.cast[:self.act]:
            performer.gone = True
        self.clock = MoonClock(x, floor, PHASES[self.act])
        self.stage = "sleep"
        self.stage_time = 0.0
        self.tethers: list[Tether] = []
        self.tides: list[Tide] = []
        self.tide_timer = TIDE_EVERY
        self.pour: Pour | None = None
        self.dusk = 0.0
        self.dusk_target = 0.0
        self.intro_tide = False
        rng = random.Random(int(x))
        moon_x, moon_y = x, floor + art.MOON_Y
        self.stars = []
        while len(self.stars) < 44:
            sx = rng.uniform(self.left, self.left + 30 * T)
            sy = rng.uniform(floor - 410, floor - 300)
            if math.hypot(sx - moon_x, sy - moon_y) > 110:
                self.stars.append((sx, sy, rng.uniform(0, math.tau), rng.random() < 0.25))

    def _measure(self, world: "World") -> tuple[int, int]:
        """The flat stretch of floor around the fountain, up to the (locked) exit."""
        floor = self.floor
        col = int(self.x // T)
        left = col
        while left > 0 and ground_below(world, (left - 1) * T + T / 2, floor - 2 * T) == floor:
            left -= 1
        goals = list(world.goals) + list(getattr(self.director, "_held_goals", []))
        right = min((goal.rect.left - 8 for goal in goals if goal.rect.left > self.x), default=world.collision.pixel_width)
        return left * T, round(right)

    # --- queries used by the director and the nightingale --------------------------------------------------
    @property
    def fighting(self) -> bool:
        return self.stage in ("curtain", "pour", "act", "interlude", "finale")

    @property
    def camera_focus(self) -> tuple[float, float] | None:
        player = self.director.world.player
        if not self.fighting or not (self.left - 48 <= player.body.centerx <= self.right + 96):
            return None
        return self.left + 480.0, self.floor - 142.0

    def peck_target(self, point: tuple[float, float]) -> Performer | None:
        best, best_distance = None, 14 * T
        for performer in self.cast:
            if performer.state == "stunned" and performer.targetable:
                distance = math.hypot(performer.body.centerx - point[0], performer.body.centery - point[1])
                if distance < best_distance:
                    best, best_distance = performer, distance
        return best

    def lock_rect(self) -> pygame.Rect:
        mx, my = self.clock.moon
        return pygame.Rect(round(mx) - 30, round(my) - 30, 60, 60)

    # --- the song -------------------------------------------------------------------------------------------------
    def on_power(self, kind: str, thing: object, world: "World") -> bool:
        if kind != "song":
            return False
        song = thing
        reacted = False
        for performer in self.cast:
            if performer.gone or performer.state in ("offstage", "defeated"):
                continue
            performer.silence(world, song)
            point = performer.step_target if performer.state == "vanished" else performer.center
            if song.reaches(*point) and song.first_time(performer):
                performer.stun(world, STUN_TIME)
                reacted = True
        clock = self.clock
        for tether in self.tethers:
            if not tether.attached:
                continue
            points = tether.curve(clock.moon, clock.radius)
            for index, (x, y) in enumerate(points):
                if song.reaches(x, y):
                    if song.first_time(tether):
                        tether.snap(world, clock.moon, clock.radius, index / (len(points) - 1))
                        reacted = True
                    break
        mx, my = clock.moon
        if song.reaches(mx, my + clock.radius) and song.first_time(clock):
            clock.shiver = 1.0
            for tide in self.tides:
                if tide.stage in ("swell", "pour") and not tide.intro:
                    tide.cancelled = True
                    reacted = True
                    self._rain_down(world, tide)
        return reacted

    def _rain_down(self, world: "World", tide: Tide) -> None:
        """A cancelled tide: its gathered water falls from the moon as harmless rain."""
        mx, my = self.clock.moon
        rng = world.particles.rng
        for _ in range(30):
            world.particles.spawn(mx + rng.uniform(-40, 40), my + rng.uniform(0, 30), rng.uniform(-90, 90), rng.uniform(-40, 60),
                                  life=rng.uniform(0.6, 1.1), kind=Kind.DOT, size=rng.uniform(1.5, 2.5),
                                  color=art.WATER_LIGHT, color_end=art.WATER, gravity=800)
        world.events.emit(EventType.MACHINE_CLUNK, (mx, my), "tide_cancel")

    # --- update ------------------------------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.flash = max(0.0, self.flash - dt * 3)
        self.stage_time += dt
        clock = self.clock
        player = world.player
        if self.resolved and self.stage not in ("done", "finale"):
            self._settle()
        engaged = self.left - 16 <= player.body.centerx <= self.right + 32 and player.is_controllable
        stage = self.stage
        if stage == "sleep":
            if player.is_controllable and self.left + 4.5 * T < player.body.centerx < self.right + 64:
                self._wake(world)
        elif stage == "curtain":
            if self.stage_time > 1.0 and not self.intro_tide:
                self.intro_tide = True
                self._start_intro_tide(world)
            if self.stage_time > CURTAIN:
                self._pour_next(world)
        elif stage == "pour":
            pour = self.pour
            if pour is not None:
                pour.time += dt
                if pour.done:
                    self._land(world, pour)
        elif stage == "act":
            performer = self.cast[self.act]
            fighting = performer.state not in ("defeated", "enter") and not performer.gone
            if self.act >= 1 and engaged and fighting:
                self.tide_timer -= dt
                if self.tide_timer <= 0 and not self.tides:
                    self.tide_timer = TIDE_EVERY
                    self._start_tide(world, big=False)
            if isinstance(performer, Weaver) and performer.called_tide and not self.tides and fighting:
                self._start_tide(world, big=True)
            if performer.state == "defeated":
                for tether in self.tethers:
                    if tether.performer is performer and not tether.retract:
                        tether.retract = True
                        clock.phase_target = PHASES[self.act + 1]
                        clock.shiver = 0.8
                        # The moon loses its hold: any tide it was gathering rains away.
                        for tide in self.tides:
                            if tide.stage in ("swell", "pour") and not tide.cancelled:
                                tide.cancelled = True
                                self._rain_down(world, tide)
            if performer.gone:
                self.act += 1
                self.director.progress = self.act
                self.tethers = [t for t in self.tethers if t.performer is not performer]
                self._set_stage("finale" if self.act >= 3 else "interlude")
                if self.act >= 3:
                    clock.playing = False
                    world.events.emit(EventType.MACHINE_CLUNK, clock.moon, "moon_crack")
        elif stage == "interlude":
            if self.stage_time > INTERLUDE:
                self._pour_next(world)
        elif stage == "finale":
            self._update_finale(dt, world)
        for performer in self.cast:
            if performer.state != "offstage" or performer.gone:
                performer.engaged = engaged
                performer.update(dt, world)
        for tether in self.tethers:
            tether.update(dt)
            if tether.attached and not tether.retract:
                self._check_string_cut(world, tether)
        self._update_tides(dt, world)
        clock.update(dt)
        self.dusk += (self.dusk_target - self.dusk) * min(1.0, dt * DUSK_RATE * 2)

    def _set_stage(self, stage: str) -> None:
        self.stage = stage
        self.stage_time = 0.0

    def _wake(self, world: "World") -> None:
        self.awake = True
        self._set_stage("curtain")
        self.dusk_target = 1.0
        self.clock.power_target = 1.0
        self.clock.playing = True
        world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), self.intro)
        world.events.emit(EventType.MACHINE_CLUNK, self.clock.moon, "moon_wake")
        if self.act >= 3:
            self._set_stage("finale")

    def _settle(self) -> None:
        """Already beaten (or beaten on an earlier visit): the fountain runs for the orchard."""
        self._set_stage("done")
        clock = self.clock
        clock.fallen = True
        clock.falling = False
        clock.pearl = 1.0
        clock.radius = 12.0
        clock.flow = 1.0
        clock.power_target = 0.15
        clock.playing = True
        clock.phase = clock.phase_target = 1.0
        for performer in self.cast:
            performer.gone = True
        self.tethers = []
        self.tides = []
        self.dusk_target = 0.0

    # --- entrances ---------------------------------------------------------------------------------------------------
    def _pour_next(self, world: "World") -> None:
        performer = self.cast[self.act]
        player = world.player
        middle = (self.left + self.right) / 2
        side = 1 if player.body.centerx < middle else -1
        x = self.x + side * 5 * T if side > 0 else self.left + 5 * T
        x = max(self.left + 2 * T, min(self.right - 2 * T, x))
        mx, my = self.clock.moon
        self.pour = Pour(performer, (mx, my + self.clock.radius), (x, self.floor))
        self._set_stage("pour")
        world.events.emit(EventType.MACHINE_CLUNK, (mx, my), "pour")

    def _land(self, world: "World", pour: Pour) -> None:
        performer = pour.performer
        x, y = pour.end
        performer.body.place_midbottom((x, y))
        performer.body.velocity.update(0, 0)
        performer.facing = 1 if world.player.body.centerx > x else -1
        performer.enter(world)
        emitters.splash(world.particles, x, y, 1.6)
        rng = world.particles.rng
        for k in range(20):
            a = -math.pi * (0.1 + 0.8 * k / 19)
            speed = rng.uniform(160, 300)
            world.particles.spawn(x, y - 4, math.cos(a) * speed, math.sin(a) * speed, life=rng.uniform(0.5, 0.9),
                                  kind=Kind.DOT, size=rng.uniform(1.8, 3.0), color=art.WATER_LIGHT, color_end=art.WATER, gravity=900)
        world.particles.spawn(x, y - 20, life=0.5, kind=Kind.GLOW, size=50, size_end=10, color=performer.element, alpha=0.9)
        self.tethers.append(Tether(performer))
        self.pour = None
        self.tide_timer = TIDE_EVERY * 0.6
        self._set_stage("act")
        world.events.emit(EventType.MACHINE_CLUNK, (x, y), "land")
        world.events.emit(EventType.GUARDIAN_AWAKE, (x, y), performer.title + "!")

    # --- strings cut by a blade ----------------------------------------------------------------------------------------
    def _check_string_cut(self, world: "World", tether: Tether) -> None:
        attack = world.player.attack_rect
        if attack is None:
            return
        clock = self.clock
        points = tether.curve(clock.moon, clock.radius)
        zone = attack.inflate(8, 8)
        for index, (x, y) in enumerate(points[:-2]):
            if zone.collidepoint(x, y):
                tether.snap(world, clock.moon, clock.radius, index / (len(points) - 1), CUT_TIME)
                return

    # --- tides ---------------------------------------------------------------------------------------------------------
    def _clamp_spot(self, x: float) -> float:
        return max(self.left + 28, min(self.right - 28, x))

    def _start_tide(self, world: "World", big: bool) -> None:
        player = world.player
        aim = player.body.centerx + player.body.velocity.x * 0.35
        offsets = (-220, -110, 0, 110, 220) if big else (-120, 0, 120)
        spots = [self._clamp_spot(aim + dx) for dx in offsets]
        self.tides.append(Tide(spots, big=big))
        self.clock.swell_target = 1.0
        world.events.emit(EventType.MACHINE_CLUNK, self.clock.moon, "tide_swell")

    def _start_intro_tide(self, world: "World") -> None:
        """The moon's first tide washes the stage clear of the orchard's creatures."""
        player = world.player
        spots = [enemy.body.centerx for enemy in world.enemies
                 if enemy.alive and enemy.is_dangerous and self.arena.collidepoint(enemy.body.centerx, enemy.body.centery)]
        for x in (self.x - 3 * T, self.x + 4 * T):
            if abs(x - player.body.centerx) > 90 and all(abs(x - s) > 60 for s in spots):
                spots.append(x)
        spots = [self._clamp_spot(s) for s in spots if abs(s - player.body.centerx) > 70]
        self.tides.append(Tide(spots, intro=True))
        self.clock.swell_target = 1.0
        world.events.emit(EventType.MACHINE_CLUNK, self.clock.moon, "tide_swell")

    def _update_tides(self, dt: float, world: "World") -> None:
        clock = self.clock
        player = world.player
        for tide in self.tides:
            tide.time += dt
            stage = tide.stage
            if tide.cancelled:
                tide.time = max(tide.time, Tide.SWELL + Tide.POUR + Tide.GUSH + Tide.FALL)
                continue
            if stage == "gush" and not tide.started:
                tide.started = True
                world.events.emit(EventType.MACHINE_CLUNK, (tide.spots[0] if tide.spots else self.x, self.floor), "geyser")
                if tide.intro:
                    for enemy in world.enemies:
                        if enemy.alive and enemy.is_dangerous and self.arena.collidepoint(enemy.body.centerx, enemy.body.centery):
                            tide.spots.append(self._clamp_spot(enemy.body.centerx))
                            enemy.knock_out(world, 1 if enemy.body.centerx > self.x else -1)
                for x in tide.spots:
                    emitters.splash(world.particles, x, self.floor, 1.4)
            if stage in ("gush", "fall") and tide.height > 0.3:
                rng = world.particles.rng
                for index, x in enumerate(tide.spots):
                    column = tide.column(x, self.floor)
                    if rng.random() < dt * 30:
                        world.particles.spawn(x + rng.uniform(-14, 14), column.top + 6, rng.uniform(-90, 90), rng.uniform(-160, -40),
                                              life=rng.uniform(0.4, 0.7), kind=Kind.DOT, size=rng.uniform(1.6, 2.8),
                                              color=art.WATER_LIGHT, color_end=art.WATER, gravity=900)
                    if index not in tide.launched and column.colliderect(player.rect):
                        tide.launched.add(index)
                        direction = 1 if player.body.centerx >= x else -1
                        if shove(world, direction * 90, -900, lock=0.3):
                            emitters.splash(world.particles, player.body.centerx, player.body.bottom, 1.0)
        self.tides = [tide for tide in self.tides if tide.stage != "done"]
        swelling = any(t.stage in ("swell", "pour") and not t.cancelled for t in self.tides)
        clock.swell_target = 1.0 if swelling else 0.0

    # --- the finale ------------------------------------------------------------------------------------------------------
    def _update_finale(self, dt: float, world: "World") -> None:
        clock = self.clock
        t = self.stage_time
        if t < 1.1:
            clock.crack = min(1.0, t / 1.0)
            clock.shiver = max(clock.shiver, 0.6)
            clock.power_target = 0.4
            if world.particles.rng.random() < dt * 20:
                mx, my = clock.moon
                emitters.droplet(world.particles, mx + world.particles.rng.uniform(-20, 20), my + clock.radius,
                                 world.particles.rng.uniform(-30, 30), 40)
        elif not clock.falling and not clock.fallen:
            clock.falling = True
            clock.fall_speed = -120.0
            world.events.emit(EventType.MACHINE_CLUNK, clock.moon, "moon_fall")
        if clock.falling and clock.moon_y >= clock.water_y - 6:
            self._splashdown(world)

    def _splashdown(self, world: "World") -> None:
        clock = self.clock
        clock.falling = False
        clock.fallen = True
        clock.crack = 0.0
        clock.rainbow = 0.0
        clock.bow = 1.6
        clock.playing = True
        clock.power_target = 0.2
        x, y = self.x, clock.water_y
        rng = world.particles.rng
        for k in range(46):
            a = -math.pi * (0.06 + 0.88 * k / 45)
            speed = rng.uniform(260, 560)
            world.particles.spawn(x + math.cos(a) * 20, y, math.cos(a) * speed, math.sin(a) * speed, life=rng.uniform(0.7, 1.3),
                                  kind=Kind.DOT, size=rng.uniform(2.0, 3.6), color=art.WATER_LIGHT, color_end=art.WATER, gravity=950)
        for _ in range(16):
            world.particles.spawn(x + rng.uniform(-110, 110), y - rng.uniform(0, 20), rng.uniform(-30, 30), rng.uniform(-60, -20),
                                  life=rng.uniform(1.0, 1.8), kind=Kind.SMOKE, size=8, size_end=26, color=(220, 240, 255), alpha=0.5)
        world.particles.spawn(x, y, life=0.6, kind=Kind.RING, size=10, size_end=160, color=(230, 250, 255))
        world.particles.spawn(x, y - 30, life=0.8, kind=Kind.GLOW, size=160, size_end=40, color=(200, 236, 255), alpha=1.0)
        emitters.petal_shower(world.particles, x, y - 120, 40)
        self.dusk_target = 0.0
        self._set_stage("done")
        self.resolve(world, "moon")

    # --- drawing -------------------------------------------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        lights = self.clock.lights()
        for performer in self.cast:
            lights += performer.lights()
        clock = self.clock
        for tether in self.tethers:
            if tether.grow > 0.3 and tether.cut <= 0 and not tether.performer.gone:
                points = tether.curve(clock.moon, clock.radius, 6)
                for x, y in points[1:-1:2]:
                    lights.append(Light(x, y, 34, STRING, 0.35 * tether.grow))
        if self.dusk > 0.05:
            for sx, sy, phase, bright in self.stars:
                if bright:
                    lights.append(Light(sx, sy, 10, (255, 255, 240), self.dusk, bloom=0.5 * self.dusk))
        for tide in self.tides:
            for x in tide.spots:
                if tide.stage == "swell":
                    lights.append(Light(x, self.floor - 10, 60, MOONLIGHT, 0.5 * tide.time / Tide.SWELL))
                elif tide.stage in ("gush", "fall"):
                    lights.append(Light(x, self.floor - 70, 90, MOONLIGHT, 0.7 * tide.height))
        if self.pour is not None:
            px, py = self.pour.position
            lights.append(Light(px, py, 80, MOONLIGHT, 0.8, bloom=0.4))
        return lights

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.dusk > 0.02:
            self._draw_stars(surface, camera)
        self.clock.draw(surface, camera, self.dusk)
        for tide in self.tides:
            self._draw_tide_back(surface, camera, tide)
        clock = self.clock
        for tether in self.tethers:
            tether.draw(surface, camera, clock.moon, clock.radius)
        for performer in self.cast:
            performer.draw_back(surface, camera)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for performer in self.cast:
            performer.draw(surface, camera)
        for tide in self.tides:
            self._draw_tide_front(surface, camera, tide)
        if self.pour is not None:
            self._draw_pour(surface, camera, self.pour)

    def _draw_stars(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        for sx, sy, phase, bright in self.stars:
            if not view.collidepoint(sx, sy):
                continue
            x, y = camera.to_screen(sx, sy)
            twinkle = 0.55 + 0.45 * math.sin(self.time * (2.0 + phase) + phase * 3)
            strength = self.dusk * twinkle
            if strength < 0.08:
                continue
            color = tuple(round(255 * min(1.0, strength + 0.2)) for _ in range(3))
            if bright:
                arm = 2 + round(2 * twinkle)
                pygame.draw.line(surface, color, (x - arm, y), (x + arm, y))
                pygame.draw.line(surface, color, (x, y - arm), (x, y + arm))
                blit_glow(surface, (x, y), 6, (200, 220, 255), 0.5 * strength)
            else:
                surface.fill(color, (x, y, 1 + (phase > 3), 1 + (phase > 3)))

    def _draw_tide_back(self, surface: pygame.Surface, camera: Camera, tide: Tide) -> None:
        if tide.cancelled:
            return
        stage = tide.stage
        mx, my = camera.to_screen(*self.clock.moon)
        for x in tide.spots:
            sx, sy = camera.to_screen(x, self.floor)
            if stage == "swell":
                u = tide.time / Tide.SWELL
                # A shimmering pool of light gathers on the ground where it will burst...
                for k in range(3):
                    r = (18 + 10 * k) * (0.5 + 0.5 * ((u * 2 + k * 0.33) % 1.0))
                    ring = pygame.Rect(0, 0, round(r * 2), max(2, round(r * 0.45)))
                    ring.center = (sx, sy - 1)
                    pygame.draw.ellipse(surface, STRING if k else STRING_CORE, ring, 1)
                blit_glow(surface, (sx, sy - 6), round(16 + 16 * u), MOONLIGHT, 0.3 + 0.5 * u)
                # ...and a dotted line of light joins it to the moon.
                steps = 14
                for k in range(steps):
                    f = k / steps
                    if (f * 6 + tide.time * 3) % 1.0 < 0.5:
                        px = mx + (sx - mx) * f
                        py = my + (sy - my) * f - math.sin(f * math.pi) * 30
                        surface.fill(STRING, (round(px), round(py), 2, 2))

    def _draw_tide_front(self, surface: pygame.Surface, camera: Camera, tide: Tide) -> None:
        if tide.cancelled:
            return
        stage = tide.stage
        mx, my = camera.to_screen(*self.clock.moon)
        if stage == "pour":
            u = (tide.time - Tide.SWELL) / Tide.POUR
            for x in tide.spots:
                sx, sy = camera.to_screen(x, self.floor)
                points = []
                for k in range(13):
                    f = k / 12 * u
                    points.append((mx + (sx - mx) * f, my + 26 + (sy - my - 26) * f * f - math.sin(f * math.pi) * 30))
                if len(points) > 1:
                    pygame.draw.lines(surface, (30, 96, 150), False, points, 6)
                    pygame.draw.lines(surface, art.WATER, False, points, 4)
                    pygame.draw.lines(surface, art.WATER_LIGHT, False, points, 1)
        elif stage in ("gush", "fall"):
            for x in tide.spots:
                column = tide.column(x, self.floor)
                if column.height < 3:
                    continue
                rect = camera.apply(column)
                self._draw_geyser(surface, rect, tide.time)

    def _draw_geyser(self, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        left: list[tuple[float, float]] = []
        right: list[tuple[float, float]] = []
        for k in range(11):
            u = k / 10
            y = rect.bottom - rect.height * u
            half = 16 - 5 * u + math.sin(t * 22 + u * 9) * 2
            left.append((rect.centerx - half, y))
            right.append((rect.centerx + half, y))
        body = left + right[::-1]
        pygame.draw.polygon(surface, (40, 120, 180), body)
        inner = [(x + 3, y) for x, y in left] + [(x - 3, y) for x, y in right[::-1]]
        pygame.draw.polygon(surface, art.WATER, inner)
        for k in range(4):
            u = (t * 2.4 + k / 4) % 1.0
            y = rect.bottom - rect.height * u
            pygame.draw.line(surface, art.WATER_LIGHT, (rect.centerx - 6 + k * 4, y), (rect.centerx - 6 + k * 4, y - 12), 2)
        for k in range(5):
            a = t * 8 + k * 1.3
            pygame.draw.circle(surface, (230, 250, 255), (round(rect.centerx + math.cos(a) * 11), round(rect.top + math.sin(a) * 4)), 5)
        blit_glow(surface, (rect.centerx, rect.top + 6), 28, MOONLIGHT, 0.6)

    def _draw_pour(self, surface: pygame.Surface, camera: Camera, pour: Pour) -> None:
        x, y = camera.to_screen(*pour.position)
        mx, my = camera.to_screen(*self.clock.moon)
        u = min(1.0, pour.time / POUR_TIME)
        # The falling drop draws a thread of water behind it from the moon.
        points = []
        for k in range(9):
            f = k / 8
            t_back = pour.time - (1 - f) * 0.25
            if t_back < 0:
                continue
            back = Pour(pour.performer, pour.start, pour.end)
            back.time = t_back
            points.append(camera.to_screen(*back.position))
        if len(points) > 1:
            pygame.draw.lines(surface, art.WATER, False, points, 3)
            pygame.draw.lines(surface, art.WATER_LIGHT, False, points, 1)
        blit_glow(surface, (x, y), 30, MOONLIGHT, 0.9)
        r = round(9 + 3 * math.sin(u * 20))
        pygame.draw.circle(surface, (30, 96, 150), (x, y), r + 1)
        pygame.draw.circle(surface, art.WATER, (x, y), r)
        pygame.draw.circle(surface, art.WATER_LIGHT, (x - 3, y - 3), 3)
        # A glimpse of the performer curled inside it.
        blit_glow(surface, (x, y), 10, pour.performer.element, 0.8)
        del mx, my

    # --- the manuscript -----------------------------------------------------------------------------------------------------
    @classmethod
    def _figure(cls, rect: pygame.Rect) -> tuple[float, float, float, float]:
        """Layout of the miniature: fountain foot x, floor y, scale, and the player's x."""
        scale = min(rect.height / 300, rect.width / 520)
        return rect.left + rect.width * 0.34, rect.bottom - 8, scale, rect.left + rect.width * 0.78

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float, solved: float) -> None:
        """The fountain as painted in the book, and a masked player hung from its moon in a bubble.

        ``solved`` 0..1: the song reaches the bubble - it bursts, the string breaks, he covers his ears.
        """
        fx, floor, scale, px = cls._figure(rect)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        ox, oy = rect.topleft
        lx, lfloor = fx - ox, floor - oy
        basin = _scaled(art.basin, scale)
        layer.blit(basin, (lx - art.BASIN_ORIGIN[0] * scale, lfloor - art.BASIN_ORIGIN[1] * scale))
        column = _scaled(art.column, scale)
        layer.blit(column, (lx - column.get_width() / 2, lfloor + art.COLUMN_TOP * scale))
        water = pygame.Rect(0, 0, round(art.WATER_RX * 2 * scale), max(3, round(art.WATER_RY * 2 * scale)))
        water.center = (round(lx), round(lfloor + art.RIM_Y * scale))
        pygame.draw.ellipse(layer, art.WATER, water)
        moon = (lx, lfloor + art.MOON_Y * scale)
        image = art.render_moon(art.MOON_RADIUS * scale, 1.0, t)
        layer.blit(image, image.get_rect(center=(round(moon[0]), round(moon[1]))))
        cradle = _scaled(art.cradle, scale)
        layer.blit(cradle, (moon[0] - art.CRADLE_ORIGIN[0] * scale, moon[1] - art.CRADLE_ORIGIN[1] * scale))
        # The player, twice life size so the page can show his mask.
        size = round(96 * scale * 1.6)
        stunned = solved > 0.5
        frame = int(t * (8 if stunned else 10))
        figure = portrait("juggler", "stunned" if stunned else "idle", frame, size)
        plx = px - ox
        layer.blit(figure, figure.get_rect(midbottom=(round(plx), round(lfloor + 2))))
        center = (plx, lfloor - size * 0.3)
        radius = size * 0.4
        crown = (plx, center[1] - radius)
        if solved < 0.5:
            points = [(moon[0] + (1 - u) ** 2 * 0 + 2 * (1 - u) * u * (plx - moon[0]) + u * u * (plx - moon[0]),
                       moon[1] + 2 * (1 - u) * u * 20 + u * u * (crown[1] - moon[1])) for u in (k / 12 for k in range(13))]
            pygame.draw.lines(layer, (40, 110, 150), False, points, 3)
            pygame.draw.lines(layer, STRING, False, points, 1)
        else:
            pygame.draw.line(layer, (40, 110, 150), moon, (moon[0] + 30, moon[1] + 16), 2)
            pygame.draw.line(layer, (40, 110, 150), crown, (crown[0], crown[1] - 12), 2)
        if solved < 0.35:
            bubble = pygame.Surface((round(radius * 2 + 6),) * 2, pygame.SRCALPHA)
            c = bubble.get_width() // 2
            wobble = 1 + 0.08 * math.sin(t * 30) * solved * 3
            pygame.draw.circle(bubble, (*BUBBLE_TINT, 60), (c, c), round(radius * wobble))
            pygame.draw.circle(bubble, (230, 255, 255, 230), (c, c), round(radius * wobble), 2)
            pygame.draw.arc(bubble, (255, 255, 255, 230), (c - radius + 5, c - radius + 5, radius * 2 - 10, radius * 2 - 10), 1.9, 2.7, 2)
            layer.blit(bubble, (round(center[0] - c), round(center[1] - c)))
        elif solved < 0.9:
            # Shards of the burst bubble flying out.
            spread = (solved - 0.35) / 0.55
            for k in range(12):
                a = k * math.tau / 12 + 0.3
                r = radius * (1 + spread * 0.9)
                x, y = center[0] + math.cos(a) * r, center[1] + math.sin(a) * r
                pygame.draw.line(layer, (230, 255, 255), (x, y), (x + math.cos(a) * 5, y + math.sin(a) * 5), 2)
        # Paint it the way the copyists did: warm, flat, a little faded.
        layer.fill((252, 234, 198, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(layer, rect.topleft)
        pygame.draw.line(surface, ink.INK, (rect.left + 6, floor), (rect.right - 6, floor), 2)
        for k in range(10):
            x = rect.left + 14 + k * (rect.width - 28) / 9
            pygame.draw.line(surface, ink.INK, (x, floor + 2), (x - 6, floor + 7), 1)

    @classmethod
    def miniature_lock(cls, rect: pygame.Rect) -> tuple[float, float]:
        fx, floor, scale, px = cls._figure(rect)
        size = round(96 * scale * 1.6)
        radius = size * 0.4
        # The rim of the bubble, on the side the song comes from.
        return px - radius * 0.72, floor - size * 0.3 - radius * 0.7


_scaled_cache: dict[tuple[str, float], pygame.Surface] = {}


def _scaled(sprite, scale: float) -> pygame.Surface:  # noqa: ANN001
    """A machine part shrunk for the manuscript page (cached per size)."""
    key = (sprite.__name__, round(scale, 3))
    image = _scaled_cache.get(key)
    if image is None:
        full = sprite()
        image = pygame.transform.smoothscale(full, (max(1, round(full.get_width() * scale)), max(1, round(full.get_height() * scale))))
        _scaled_cache[key] = image
    return image
