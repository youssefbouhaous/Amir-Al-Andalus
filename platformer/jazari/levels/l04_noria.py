"""Level 4's finale: the Sky-Noria and the River-Thieves.

At the end of the Singing Aqueduct, al-Muqallid's noria stands where the
water should be lifted into the aqueduct - but its pots throw the water up
into the sky, where it flows away as a river among the clouds, carp and all.
The city's fountains run dry; the thieves sell the water back by the cup. A
brass ox turns the wheel from a tower beside it, as in al-Jazari's water-
raising machines, its eyes burning with the spell.

The noria floods the stage with the water it does not steal. Whoever stands
in that stolen water borrows the noria's patient strength (see
``entities.river_thieves``), so the three thieves who run down the wheel's
rim are unshakable while their feet are wet. Every so often the ox stops to
drink: the wheel halts, the flood drains through the grates, and the thieves
are only people - until the ox bellows and the river comes back as a wave.
The Rose Fountain lifts a thief out of the water whenever the prince likes.

When the last thief falls the ox shakes off its harness, the wheel turns
back, and the river comes down out of the sky: the dawn returns, a rainbow
stands over the aqueduct, and its fountains sing again.
"""

import math
import random
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from entities.river_thieves import NetFisher, RainCaller, Rooted, WaterSeller
from jazari import art as ink
from jazari.base import Guardian, ground_below, shove
from rendering import emitters
from rendering.art import fountain as fountain_art
from rendering.art import noria as art
from rendering.art.river_thieves import portrait
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from jazari.director import WonderDirector
    from world.world import World

T = 32
STOLEN = (118, 178, 206)     # the light under a river that hangs in the sky
WARM = (255, 220, 178)       # the dawn flooding back
WATER = (96, 200, 236)
WATER_LIGHT = (214, 246, 255)
CURTAIN = 3.0
RIDE = 0.9                   # a thief running down the wheel's rim
LEAP = 0.75
INTERLUDE = 1.6
EBB_FIRST = 6.0              # the ox's first drink comes early, to show how it goes
EBB_EVERY = 18.0
EBB_DRY = 2.0
BELLOW = 0.7
DEPTH = 15.0
SPEED_SLEEP = 7.0            # the wheel, in degrees per second
SPEED_AWAKE = 16.0
OX_LAP = 6.0                 # seconds for the ox to walk once round at full speed


# --- the machine -------------------------------------------------------------------------------------
class SkyNoria:
    def __init__(self, x: float, floor: float) -> None:
        self.x = x
        self.floor = floor
        self.time = 0.0
        self.angle = 0.0
        self.speed = SPEED_SLEEP
        self.speed_target = SPEED_SLEEP
        self.phi = math.pi / 2         # where the ox is on its walk round the platform
        self.ox_state = "walk"         # walk | drink | bellow | rest
        self.ox_time = 0.0
        self.walk_clock = 0.0
        self.river = 0.6
        self.river_target = 0.6
        self.eyes = 1.0                # the spell in the ox's eyes (0 once it is free)
        self.freed = False
        self.laps = 0.0
        # Everything is painted at level load (it takes a moment, not a hitch in the fight).
        art.wheel_base()
        for step in range(art.STEPS):
            art.wheel_frame(step)
        art.tower()
        art.river_body()
        for anim, count in art.OX_ANIMS.items():
            for frame in range(count):
                art.ox(anim, frame)

    def at(self, point: tuple[float, float]) -> tuple[float, float]:
        return self.x + point[0], self.floor + point[1]

    @property
    def hub(self) -> tuple[float, float]:
        return self.at(art.HUB)

    # --- the ox ----------------------------------------------------------------------------------------
    def ox_frame(self) -> tuple[str, int]:
        if self.ox_state == "walk":
            return "walk", int(self.walk_clock * 8) % 8
        if self.ox_state == "drink":
            lowering = int(self.ox_time / 0.16)
            if lowering < 3:
                return "drink", lowering
            return "drink", 2 + int(self.ox_time * 3) % 2        # gulping
        if self.ox_state == "bellow":
            return "bellow", min(2, int(self.ox_time / 0.12))
        return "rest", int(self.ox_time * 1.5) % 2

    def ox_foot(self) -> tuple[float, float]:
        cx, cy = self.at(art.OX_PATH)
        return cx + math.cos(self.phi) * art.OX_RX, cy + math.sin(self.phi) * art.OX_RY

    @property
    def ox_front(self) -> bool:
        return math.sin(self.phi) > 0

    @property
    def ox_facing(self) -> int:
        return 1 if self.ox_front else -1

    @property
    def ox_squash(self) -> float:
        return max(0.55, abs(math.sin(self.phi)))

    def ox_world(self, point: tuple[float, float]) -> tuple[float, float]:
        """A point of the ox (relative to its foot, facing right) in the world, as it walks round."""
        anim, frame = self.ox_frame()
        px, py = art.ox_point(point, anim, frame)
        fx, fy = self.ox_foot()
        return fx + px * self.ox_facing * self.ox_squash, fy + py

    def yoke(self) -> tuple[float, float]:
        fx, fy = self.ox_foot()
        sink = 20.0 if self.ox_state == "rest" else 0.0
        return fx + art.OX_YOKE[0] * self.ox_facing * self.ox_squash, fy + art.OX_YOKE[1] + 14 + sink

    def drink(self) -> None:
        self.ox_state, self.ox_time = "drink", 0.0
        self.speed_target = 0.0

    def bellow(self) -> None:
        self.ox_state, self.ox_time = "bellow", 0.0

    def resume(self) -> None:
        self.ox_state, self.ox_time = "walk", 0.0
        self.speed_target = SPEED_AWAKE

    def wake(self) -> None:
        self.bellow()
        self.speed_target = SPEED_AWAKE
        self.river_target = 1.0

    def release(self) -> None:
        """Free: the ox shakes off its harness, the wheel turns back and the river comes down."""
        self.freed = True
        self.bellow()
        self.speed_target = -SPEED_SLEEP
        self.river_target = 0.0

    def settle(self) -> None:
        self.freed = True
        self.ox_state, self.ox_time = "rest", 0.0
        self.speed = self.speed_target = -SPEED_SLEEP * 0.6
        self.river = self.river_target = 0.0
        self.eyes = 0.0

    def update(self, dt: float) -> list[str]:
        events = []
        self.time += dt
        self.ox_time += dt
        rate = 14.0 if self.speed_target != 0 else 24.0
        if self.speed < self.speed_target:
            self.speed = min(self.speed_target, self.speed + rate * dt)
        else:
            self.speed = max(self.speed_target, self.speed - rate * dt)
        self.angle += self.speed * dt
        self.river += (self.river_target - self.river) * min(1.0, dt * (0.5 if self.freed else 1.2))
        self.eyes += ((0.0 if self.freed else 1.0) - self.eyes) * min(1.0, dt * 2)
        if self.ox_state == "walk":
            pace = abs(self.speed) / SPEED_AWAKE
            step = dt * math.tau / OX_LAP * pace
            self.phi -= step
            self.walk_clock += dt * max(0.3, pace)
            before = int(self.laps)
            self.laps += step / math.tau
            if int(self.laps) != before:
                events.append("ox_bell")
        elif self.ox_state == "bellow" and self.ox_time >= BELLOW:
            if self.freed:
                self.ox_state, self.ox_time = "rest", 0.0
            else:
                self.ox_state, self.ox_time = "walk", 0.0
        return events

    def pots(self) -> list[tuple[float, tuple[float, float], tuple[float, float]]]:
        """(angle, mouth world position, mouth direction) for every pot, matching the drawn wheel."""
        step = int((self.angle % art.PERIOD) / art.PERIOD * art.STEPS) % art.STEPS
        phase = step * art.PERIOD / art.STEPS
        hx, hy = self.hub
        out = []
        for k in range(art.POTS):
            angle = (phase + k * art.PERIOD + art.PERIOD / 2) % 360
            (mx, my), direction = art.pot_mouth(angle)
            out.append((angle, (hx + mx, hy + my), direction))
        return out

    # --- drawing -------------------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        fx, fy = camera.to_screen(self.x, self.floor)
        art.draw_river(surface, (fx, fy), self.time, self.river)
        tower = art.tower()
        surface.blit(tower, (fx + art.TOWER_LEFT - art.TOWER_ORIGIN[0], fy - art.TOWER_ORIGIN[1]))
        if not self.ox_front:
            self._draw_ox(surface, camera)
        crown = camera.to_screen(*self.at(art.CROWN))
        art.draw_crown(surface, crown, math.degrees(-self.phi) * 2.2, self.eyes)
        if self.ox_front:
            self._draw_ox(surface, camera)
        # The noria's axle reaching across to the lantern gear on the tower.
        hx, hy = camera.to_screen(*self.hub)
        px, py = camera.to_screen(*self.at(art.PINION))
        pygame.draw.line(surface, art.OUTLINE, (hx, hy), (px, py), 12)
        pygame.draw.line(surface, art.WOOD, (hx, hy - 1), (px, py - 1), 8)
        for k in range(1, 4):
            x = hx + (px - hx) * k / 4
            pygame.draw.line(surface, art.BRASS, (x, hy - 5), (x, hy + 4), 3)
        wheel = art.wheel_for(self.angle)
        surface.blit(wheel, wheel.get_rect(center=(hx, hy)))
        hub = art.hub_image(self.angle)
        surface.blit(hub, hub.get_rect(center=(hx, hy)))
        blit_glow(surface, (hx, hy), 18, art.MAGIC if self.eyes > 0.1 else art.FREED, 0.3 + 0.3 * self.eyes)
        pinion = art.pinion_image(-self.angle * 5.3)
        surface.blit(pinion, pinion.get_rect(center=(px, py)))
        self._draw_water(surface, camera)

    def _draw_ox(self, surface: pygame.Surface, camera: Camera) -> None:
        anim, frame = self.ox_frame()
        image = art.ox(anim, frame)
        if self.ox_facing < 0:
            image = pygame.transform.flip(image, True, False)
        squash = self.ox_squash
        if squash < 0.99:
            image = pygame.transform.smoothscale(image, (max(1, round(image.get_width() * squash)), image.get_height()))
        if not self.ox_front:
            image = image.copy()
            image.fill((214, 214, 222), special_flags=pygame.BLEND_RGB_MULT)
        fx, fy = camera.to_screen(*self.ox_foot())
        foot_x = art.OX_FOOT[0] * squash if self.ox_facing > 0 else image.get_width() - art.OX_FOOT[0] * squash
        # The sweep-beam from the gear's shaft to the ox's yoke.
        shaft = camera.to_screen(*self.at((art.CROWN[0], art.CROWN[1] - 30)))
        yoke = camera.to_screen(*self.yoke())
        if not self.freed:
            pygame.draw.line(surface, art.OUTLINE, shaft, yoke, 7)
            pygame.draw.line(surface, art.WOOD_LIGHT, shaft, yoke, 4)
        surface.blit(image, (round(fx - foot_x), round(fy - art.OX_FOOT[1])))
        ex, ey = camera.to_screen(*self.ox_world(art.OX_EYE))
        color = art.MAGIC if self.eyes > 0.4 else art.FREED
        blit_glow(surface, (ex, ey), 12, color, 0.55 + 0.35 * self.eyes)
        pygame.draw.circle(surface, color, (round(ex), round(ey)), 2)

    def _draw_water(self, surface: pygame.Surface, camera: Camera) -> None:
        """Water in the pots that are full, and the pots at the top throwing it up into the sky."""
        stealing = self.river > 0.05 and not self.freed
        for angle, mouth, direction in self.pots():
            x, y = camera.to_screen(*mouth)
            if 195 <= angle <= 352:
                pygame.draw.ellipse(surface, WATER, (x - 4, y - 2, 8, 4))
                pygame.draw.line(surface, WATER_LIGHT, (x - 3, y - 1), (x + 2, y - 1), 1)
            elif angle < 40 or angle > 352:
                pour = 1.0 - abs((angle if angle < 180 else angle - 360) - 14) / 26
                if pour <= 0:
                    continue
                if stealing:
                    # Magic: the water leaps upward into the river instead of falling.
                    for k in range(5):
                        f = (self.time * 1.6 + k / 5 + angle * 0.01) % 1.0
                        px = x + direction[0] * 6 + f * 14
                        py = y - f * 46 - f * f * 10
                        pygame.draw.circle(surface, WATER_LIGHT if k % 2 else WATER, (round(px), round(py)), 2)
                elif abs(self.speed) > 1:
                    for k in range(5):
                        f = (self.time * 2 + k / 5) % 1.0
                        pygame.draw.circle(surface, WATER, (round(x + direction[0] * 8 + f * 6), round(y + f * f * 60)), 2)

    def lights(self) -> list[Light]:
        lights = []
        ex, ey = self.ox_world(art.OX_EYE)
        lights.append(Light(ex, ey, 40, art.MAGIC if self.eyes > 0.4 else art.FREED, 0.7))
        hx, hy = self.hub
        lights.append(Light(hx, hy, 70, art.MAGIC if self.eyes > 0.1 else art.FREED, 0.5))
        cx, cy = self.at((art.CROWN[0], art.SHAFT_TOP - 10))
        lights.append(Light(cx, cy, 50, art.MAGIC if self.eyes > 0.1 else art.FREED, 0.6))
        if self.river > 0.05:
            for u in (0.08, 0.3, 0.5, 0.7, 0.9):
                x, y, w, _, _ = art.river_at(u)
                lights.append(Light(self.x + x, self.floor + y, 120, WATER, 0.45 * self.river, bloom=0.15 * self.river))
        return lights


# --- the stolen flood on the stage -------------------------------------------------------------------------
class Wave:
    SPEED = 330.0
    HEIGHT = 30.0

    def __init__(self, x: float, direction: int) -> None:
        self.x = x
        self.direction = direction
        self.alive = True
        self.hit = False
        self.age = 0.0

    @property
    def height(self) -> float:
        return self.HEIGHT * max(0.45, 1.0 - self.age * 0.25)


class Flood:
    STEP = 8

    def __init__(self, left: float, right: float, floor: float, source: float) -> None:
        self.left, self.right, self.floor = left, right, floor
        self.source = source
        self.levels = [0.0] * (int((right - left) / self.STEP) + 2)
        self.full = False
        self.reach = [source, source]       # how far the returning water has run, left and right
        self.waves: list[Wave] = []
        self.time = 0.0

    def _index(self, x: float) -> int:
        return max(0, min(len(self.levels) - 1, int((x - self.left) / self.STEP)))

    def level(self, x: float) -> float:
        return self.levels[self._index(x)]

    def covered(self, x: float) -> bool:
        return self.level(x) > 0.35

    def coverage(self) -> float:
        return sum(self.levels) / len(self.levels)

    def depth(self, x: float) -> float:
        depth = self.level(x) * DEPTH
        for wave in self.waves:
            d = (x - wave.x) * wave.direction
            if -40 < d < 10:
                profile = math.exp(-((d + 12) / 16) ** 2)
                depth = max(depth, wave.height * profile)
        return depth

    def surge(self) -> None:
        """The river comes back: a wave runs out from the foot of the wheel each way, filling behind it."""
        self.full = True
        self.reach = [self.source, self.source]
        self.waves += [Wave(self.source, -1), Wave(self.source, 1)]

    def drain(self) -> None:
        self.full = False

    def fill_now(self) -> None:
        self.full = True
        self.reach = [self.left, self.right]
        self.levels = [1.0] * len(self.levels)

    def update(self, dt: float, world: "World") -> list[str]:
        events = []
        self.time += dt
        for wave in self.waves:
            wave.age += dt
            wave.x += wave.direction * Wave.SPEED * dt
            if wave.direction < 0:
                self.reach[0] = min(self.reach[0], wave.x)
            else:
                self.reach[1] = max(self.reach[1], wave.x)
            if not self.left - 40 < wave.x < self.right + 40:
                wave.alive = False
                continue
            player = world.player
            if not wave.hit and abs(player.body.centerx - wave.x) < 16 and player.body.bottom > self.floor - wave.height * 0.8:
                wave.hit = True
                if shove(world, wave.direction * 340, -260, lock=0.3):
                    events.append("wave_hit")
            for enemy in world.enemies:
                if enemy.alive and enemy.is_dangerous and abs(enemy.body.centerx - wave.x) < 14 \
                        and enemy.body.bottom > self.floor - 40:
                    enemy.knock_out(world, wave.direction)
            rng = world.particles.rng
            if rng.random() < dt * 40:
                world.particles.spawn(wave.x, self.floor - wave.height * 0.8, wave.direction * rng.uniform(40, 140),
                                      -rng.uniform(60, 200), life=0.5, kind=Kind.DOT, size=2.4, color=WATER_LIGHT,
                                      color_end=WATER, gravity=800)
        self.waves = [wave for wave in self.waves if wave.alive]
        for i in range(len(self.levels)):
            x = self.left + i * self.STEP
            if self.full and self.reach[0] - 6 <= x <= self.reach[1] + 6:
                self.levels[i] = min(1.0, self.levels[i] + dt * 5)
            elif not self.full:
                # It drains away fastest by the grates, last in the hollows.
                speed = 1.4 + 0.5 * math.sin(x * 0.05)
                self.levels[i] = max(0.0, self.levels[i] - dt * speed)
        return events

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        left = max(self.left, view.left - self.STEP)
        right = min(self.right, view.right + self.STEP)
        if right <= left:
            return
        _, floor_y = camera.to_screen(0, self.floor)
        top_pad = 48
        width = round(right - left) + 2
        layer = pygame.Surface((width, top_pad + 8), pygame.SRCALPHA)
        x0 = camera.to_screen(left, 0)[0]
        surface_line = []
        x = left
        while x <= right:
            depth = self.depth(x)
            ripple = math.sin(self.time * 4 + x * 0.09) * 0.8 * min(1.0, depth / 4)
            surface_line.append((x - left, top_pad - depth + ripple))
            x += 4
        if all(top_pad - y < 0.6 for _, y in surface_line):
            return
        polygon = surface_line + [(width, top_pad + 4), (0, top_pad + 4)]
        pygame.draw.polygon(layer, (84, 186, 228, 140), polygon)
        for k in range(len(surface_line) - 1):
            (ax, ay), (bx, by) = surface_line[k], surface_line[k + 1]
            if top_pad - ay > 0.8:
                pygame.draw.line(layer, (150, 220, 246, 200), (ax, ay + 2), (bx, by + 2), 1)
                pygame.draw.line(layer, (236, 252, 255, 235), (ax, ay), (bx, by), 2)
                # Glints of the sky caught on the surface.
                if (k * 7 + int(self.time * 6)) % 23 == 0:
                    pygame.draw.line(layer, (255, 255, 255, 255), (ax - 2, ay + 2), (ax + 3, ay + 2), 1)
        for wave in self.waves:
            wx = wave.x - left
            if 0 <= wx <= width:
                crest_y = top_pad - wave.height
                curl = [(wx - wave.direction * 18, crest_y + 10), (wx - wave.direction * 6, crest_y - 1),
                        (wx + wave.direction * 6, crest_y + 2), (wx + wave.direction * 9, crest_y + 9),
                        (wx + wave.direction * 2, crest_y + 7)]
                pygame.draw.polygon(layer, (240, 252, 255, 230), curl)
        surface.blit(layer, (x0, floor_y - top_pad))


# --- the encounter ------------------------------------------------------------------------------------------------
class RiverThieves(Guardian):
    name = "The River-Thieves"
    device = "The Sky-Noria"
    lethal = True
    reach = 16
    intro = "The River-Thieves! Their noria pours the river into the sky!"
    farewell = "The river comes down from the sky. The aqueduct sings again!"
    music = "river"

    def __init__(self, director: "WonderDirector", x: float, floor: float) -> None:
        super().__init__(director, x, floor)
        world = director.world
        self.left, self.right = self._measure(world)
        self.arena = pygame.Rect(round(self.left), round(floor - 12 * T), round(self.right - self.left), 12 * T)
        self._clear_hazards(world)
        bounds = (self.left + 10.0, self.right - 10.0)
        sprites = world.sprites
        self.cast: list[Rooted] = [WaterSeller(x, floor, sprites, bounds), NetFisher(x, floor, sprites, bounds),
                                   RainCaller(x, floor, sprites, bounds)]
        for performer in self.cast:
            performer.river_y = self.river_y
        self.act = max(0, min(3, getattr(director, "progress", 0)))
        for performer in self.cast[:self.act]:
            performer.gone = True
        self.machine = SkyNoria(x, floor)
        self.flood = Flood(self.left, self.right, floor, x + 20)
        self.stage = "sleep"
        self.stage_time = 0.0
        self.dusk = 0.0
        self.dusk_target = 0.0
        self.sky = STOLEN
        self.rider: Rooted | None = None
        self.ride_from = (0.0, 0.0)
        self.ride_to = (0.0, 0.0)
        self.ebb = ""
        self.ebb_time = 0.0
        self.ebb_timer = EBB_FIRST
        self.song = 0.0          # the aqueduct's fountains, once the river is home
        self.rainbow = 0.0
        self.spots = [(sx, self._ground(world, sx)) for sx in
                      (self.left + 4 * T, x + 5 * T, x + 10 * T, self.right - 3 * T)]
        self._splash_timer = 0.0

    def _measure(self, world: "World") -> tuple[float, float]:
        """The flat stretch of floor under the noria, up to the (locked) exit."""
        floor = self.floor
        col = int(self.x // T)
        left = col
        while left > 0 and ground_below(world, (left - 1) * T + T / 2, floor - 2 * T) == floor:
            left -= 1
        goals = list(world.goals) + list(getattr(self.director, "_held_goals", []))
        right = min((goal.rect.left - 8 for goal in goals if goal.rect.left > self.x), default=self.x + 20 * T)
        return float(left * T), float(right)

    def _clear_hazards(self, world: "World") -> None:
        """The level's old spikes over the last run would hang in the fountains' way: the noria's spray washed them off."""
        from objects.hazards import Spikes

        world.props = [prop for prop in world.props if not (isinstance(prop, Spikes) and self.arena.colliderect(prop.rect))]

    def _ground(self, world: "World", x: float) -> float:
        return ground_below(world, x, self.floor - 4 * T)

    def river_y(self, x: float) -> float:
        """The underside of the sky river above world ``x`` (or the nearest stretch of it)."""
        course = art.river_course()
        rx = x - self.x
        best = min(course, key=lambda sample: abs(sample[0] - rx))
        return self.floor + best[1] + best[2] * 0.45

    # --- what the director and powers ask --------------------------------------------------------------
    @property
    def fighting(self) -> bool:
        return self.stage in ("curtain", "ride", "act", "interlude", "finale")

    @property
    def camera_focus(self) -> tuple[float, float] | None:
        player = self.director.world.player
        if not self.fighting or not (self.left - 48 <= player.body.centerx <= self.right + 96):
            return None
        return min(self.left + 492.0, (self.left + self.right) / 2), self.floor - 142.0

    @property
    def night(self) -> tuple[int, int, int]:
        return self.sky

    def lock_rect(self) -> pygame.Rect:
        hx, hy = self.machine.hub
        return pygame.Rect(round(hx) - 30, round(hy) - 30, 60, 60)

    def on_power(self, kind: str, thing: object, world: "World") -> bool:
        if kind != "fountain":
            return False
        jet = thing
        column = jet.column()
        reacted = False
        for performer in self.cast:
            if not performer.targetable or performer.lifted:
                continue
            feet = pygame.Rect(round(performer.body.centerx) - 10, round(performer.body.bottom) - 8, 20, 12)
            if column.colliderect(feet) and performer.lift(world, jet):
                reacted = True
        return reacted

    # --- update ----------------------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.stage_time += dt
        player = world.player
        if self.resolved and self.stage not in ("done", "finale"):
            self._settle()
        engaged = self.left - 16 <= player.body.centerx <= self.right + 40 and player.is_controllable
        stage = self.stage
        if stage == "sleep":
            if player.is_controllable and self.left + 4 * T < player.body.centerx < self.right + 64:
                self._wake(world)
        elif stage == "curtain":
            if self.stage_time > CURTAIN:
                self._ride_next(world)
        elif stage == "ride":
            self._update_ride(world)
        elif stage == "act":
            self._update_act(dt, world, engaged)
        elif stage == "interlude":
            if self.stage_time > INTERLUDE:
                self._ride_next(world)
        elif stage == "finale":
            self._update_finale(dt, world)
        for sound in self.machine.update(dt):
            if self.fighting:       # (machine sounds carry across the level: only during the fight)
                world.events.emit(EventType.MACHINE_CLUNK, self.machine.ox_world(art.OX_MOUTH), sound)
        if self.machine.ox_state == "bellow" and self.machine.ox_time < 0.4 and world.particles.rng.random() < dt * 30:
            mx, my = self.machine.ox_world(art.OX_MOUTH)
            world.particles.spawn(mx, my, self.machine.ox_facing * 40, -30, life=0.8, kind=Kind.SMOKE, size=4,
                                  size_end=14, color=(230, 240, 250), alpha=0.5)
        for sound in self.flood.update(dt, world):
            world.events.emit(EventType.MACHINE_CLUNK, player.body.midbottom, sound)
        jets = list(getattr(self.director.power, "jets", []))
        for performer in self.cast:
            if performer is self.rider:
                performer.time += dt
                performer.animator.update(dt)       # carried by the ride, not by physics
                continue
            if performer.state != "offstage" or performer.gone:
                performer.flooded = self.flood.covered(performer.body.centerx)
                performer.jets = jets
                performer.engaged = engaged
                performer.update(dt, world)
        self._splash_feet(dt, world)
        self._update_song(dt, world)
        self.dusk += (self.dusk_target - self.dusk) * min(1.0, dt * 1.1)

    def _set_stage(self, stage: str) -> None:
        self.stage = stage
        self.stage_time = 0.0

    def _wake(self, world: "World") -> None:
        self.awake = True
        self.machine.wake()
        self.flood.surge()
        self.dusk_target = 0.72
        self.sky = STOLEN
        self._set_stage("curtain" if self.act < 3 else "finale")
        world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), self.intro)
        world.events.emit(EventType.MACHINE_CLUNK, self.machine.hub, "noria_wake")

    def _settle(self) -> None:
        """Beaten already: the ox rests, the wheel turns gently back, the aqueduct's fountains play."""
        self._set_stage("done")
        self.machine.settle()
        self.flood.drain()
        self.flood.levels = [0.0] * len(self.flood.levels)
        for performer in self.cast:
            performer.gone = True
        self.dusk_target = 0.0
        self.song = 1.0

    # --- the ebb: the ox stops to drink --------------------------------------------------------------------
    def _update_act(self, dt: float, world: "World", engaged: bool) -> None:
        thief = self.cast[self.act]
        fighting = thief.state not in ("defeated", "enter") and not thief.gone
        if self.ebb:
            self.ebb_time += dt
        if self.ebb == "" and engaged and fighting:
            self.ebb_timer -= dt
            if self.ebb_timer <= 0:
                self.ebb, self.ebb_time = "dry", 0.0
                self.machine.drink()
                self.flood.drain()
                world.events.emit(EventType.MACHINE_CLUNK, self.machine.ox_world(art.OX_MOUTH), "ox_drink")
        elif self.ebb == "dry" and self.ebb_time > EBB_DRY:
            self.ebb = "bellow"
            self.machine.bellow()
            world.events.emit(EventType.MACHINE_CLUNK, self.machine.ox_world(art.OX_MOUTH), "ox_bellow")
        elif self.ebb == "bellow" and self.ebb_time > EBB_DRY + BELLOW:
            self._end_ebb(world)
        if thief.gone:
            self.act += 1
            self.director.progress = self.act
            if self.ebb:
                self._end_ebb(world)
            if self.act >= 3:
                self._set_stage("finale")
            else:
                self._set_stage("interlude")

    def _end_ebb(self, world: "World") -> None:
        self.ebb = ""
        self.ebb_timer = EBB_EVERY
        self.machine.resume()
        self.flood.surge()
        world.events.emit(EventType.MACHINE_CLUNK, (self.flood.source, self.floor), "flood_surge")

    # --- a thief runs down the wheel's rim and leaps onto the stage ------------------------------------------
    def _ride_next(self, world: "World") -> None:
        thief = self.cast[self.act]
        player = world.player
        spots = sorted(self.spots, key=lambda s: -abs(s[0] - player.body.centerx))
        self.ride_to = spots[0] if random.random() < 0.7 else spots[1]
        self.rider = thief
        thief.state = "enter"
        thief.facing = 1
        thief.animator.play("run")
        self._set_stage("ride")
        self._place_rider(0.0)
        world.events.emit(EventType.MACHINE_CLUNK, self.machine.hub, "rim_run")

    def _place_rider(self, u: float) -> None:
        hx, hy = self.machine.hub
        angle = -8 + 82 * u
        px, py = art.wheel_point(angle, art.POT_R + 10)
        self.rider.body.place_midbottom((hx + px, hy + py))
        self.rider.body.velocity.update(0, 0)
        self.ride_from = (hx + px, hy + py)

    def _update_ride(self, world: "World") -> None:
        thief = self.rider
        if thief is None:
            return
        t = self.stage_time
        if t < RIDE:
            self._place_rider(t / RIDE)
            return
        u = min(1.0, (t - RIDE) / LEAP)
        if thief.animator.current != "leap":
            thief.animator.play("leap")
            world.events.emit(EventType.MACHINE_CLUNK, thief.center, "leap")
        hx, hy = self.machine.hub
        sx, sy = art.wheel_point(74, art.POT_R + 10)
        (x0, y0), (x1, y1) = (hx + sx, hy + sy), self.ride_to
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u - math.sin(u * math.pi) * 90
        thief.body.place_midbottom((x, y))
        thief.facing = 1 if x1 > x0 else -1
        if u >= 1.0:
            thief.body.velocity.update(0, 0)
            thief.body.on_ground = True
            thief.enter(world)
            thief.animator.play("land", restart=True)
            thief.facing = 1 if world.player.body.centerx > x1 else -1
            emitters.splash(world.particles, x1, y1, 1.3)
            self.rider = None
            self.ebb_timer = EBB_FIRST if self.act == 0 else EBB_EVERY * 0.75
            self._set_stage("act")
            world.events.emit(EventType.MACHINE_CLUNK, (x1, y1), "land")
            world.events.emit(EventType.GUARDIAN_AWAKE, (x1, y1), thief.title + "!")

    # --- the finale: the river comes home ------------------------------------------------------------------------
    def _update_finale(self, dt: float, world: "World") -> None:
        machine = self.machine
        t = self.stage_time
        if not machine.freed:
            machine.release()
            self.flood.drain()
            world.events.emit(EventType.MACHINE_CLUNK, machine.ox_world(art.OX_MOUTH), "ox_freed")
            hx, hy = machine.hub
            emitters.sparkle_burst(world.particles, hx, hy, WATER_LIGHT, 20, 200)
        if t > 0.5:
            # The river falls out of the sky: a glittering rain all along its course.
            rng = world.particles.rng
            count = dt * 160 * machine.river
            for _ in range(int(count) + (rng.random() < count - int(count))):
                u = rng.uniform(0.05, 0.95)
                x, y, w, _, _ = art.river_at(u)
                world.particles.spawn(self.x + x + rng.uniform(-w / 2, w / 2), self.floor + y, rng.uniform(-20, 20),
                                      rng.uniform(40, 140), life=1.6, kind=Kind.DOT, size=2.2, size_end=1.2,
                                      color=WATER_LIGHT, color_end=WATER, gravity=500)
        if t < 1.2:
            self.sky = _mix(STOLEN, WARM, t / 1.2)
        else:
            self.sky = WARM
            self.dusk_target = 0.0
        self.rainbow = min(1.0, max(0.0, (t - 0.8) / 1.5))
        if t > 1.2 and not self.resolved:
            self.resolve(world, "river")
            world.events.emit(EventType.MACHINE_CLUNK, machine.hub, "river_home")
        if t > 6.0:
            self._set_stage("done")

    def _update_song(self, dt: float, world: "World") -> None:
        """Once the river is home, the fountains along the aqueduct spring up and play."""
        if self.stage in ("finale", "done") and (self.resolved or self.machine.freed):
            before = self.song
            self.song = min(1.0, self.song + dt * 0.5)
            if before < 0.05 <= self.song:
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "aqueduct_song")

    def _splash_feet(self, dt: float, world: "World") -> None:
        """Wading: little splashes at the prince's feet as he runs through the stolen river."""
        player = world.player
        self._splash_timer -= dt
        if self._splash_timer <= 0 and player.body.on_ground and abs(player.body.velocity.x) > 60 \
                and self.flood.covered(player.body.centerx):
            self._splash_timer = 0.12
            rng = world.particles.rng
            for _ in range(3):
                emitters.droplet(world.particles, player.body.centerx + rng.uniform(-6, 6), player.body.bottom - 2,
                                 -player.body.velocity.x * rng.uniform(0.1, 0.3), -rng.uniform(80, 180))

    # --- drawing -------------------------------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        lights = self.machine.lights()
        for performer in self.cast:
            lights += performer.lights()
        player = self.director.world.player
        if self.dusk > 0.2 and self.arena.collidepoint(player.body.centerx, player.body.centery):
            lights.append(Light(player.body.centerx, player.body.centery, 70, (255, 246, 230), 0.6 * self.dusk))
        if self.song > 0.05:
            for k, x in enumerate(self._song_xs()):
                lights.append(Light(x, self.floor - 40, 70, WATER_LIGHT, 0.45 * self.song))
        return lights

    def _song_xs(self) -> list[float]:
        return [self.left + 60 + k * (self.right - self.left - 120) / 4 for k in range(5)]

    def draw_scenery(self, surface: pygame.Surface, camera: Camera) -> None:
        self.machine.draw(surface, camera)
        coverage = self.flood.coverage()
        if coverage > 0.05:
            self._draw_reflections(surface, camera, coverage)
        if self.rainbow > 0.01:
            hx, hy = camera.to_screen(*self.machine.hub)
            fountain_art.draw_rainbow(surface, (hx + 300, hy + 80), 330, self.rainbow * 0.9)
        if self.song > 0.01:
            for k, x in enumerate(self._song_xs()):
                base = camera.to_screen(x, self.floor)
                height = (40 + 26 * math.sin(self.time * 2.4 + k * 1.7)) * self.song
                fountain_art.draw_column(surface, base, height, self.time + k, width=14, strength=0.8 * self.song)
                fountain_art.draw_crown(surface, (base[0], base[1] - height), k, self.time, 0.6 * self.song)

    def _draw_reflections(self, surface: pygame.Surface, camera: Camera, coverage: float) -> None:
        """Light thrown up off the flood dances on the wheel, the tower and the walls."""
        band = _reflection_band(int(self.time * 10) % art.CAUSTIC_FRAMES)
        _, floor_y = camera.to_screen(0, self.floor)
        view = camera.view_rect
        x0 = camera.to_screen(self.left, 0)[0]
        start = max(x0, 0) - ((max(x0, 0) - x0) % band.get_width())
        end = min(camera.to_screen(self.right, 0)[0], view.width)
        if coverage < 0.98:
            band = band.copy()
            band.fill((round(255 * coverage),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        x = start
        while x < end:
            surface.blit(band, (x, floor_y - band.get_height()), special_flags=pygame.BLEND_RGB_ADD)
            x += band.get_width()

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        for performer in self.cast:
            performer.draw_back(surface, camera)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for performer in self.cast:
            if performer is self.rider and self.stage_time >= RIDE:
                self._draw_leaper(surface, camera, performer)
            else:
                performer.draw(surface, camera)

    def _draw_leaper(self, surface: pygame.Surface, camera: Camera, thief: Rooted) -> None:
        u = min(1.0, (self.stage_time - RIDE) / LEAP)
        image = thief.animator.image(flip_x=thief.facing < 0)
        rotated = pygame.transform.rotate(image, -thief.facing * 360 * u)
        x, y = camera.to_screen(thief.body.centerx, thief.body.centery)
        surface.blit(rotated, rotated.get_rect(center=(x, y)))
        blit_glow(surface, (x, y), 18, WATER_LIGHT, 0.4)

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        self.flood.draw(surface, camera)

    # --- the manuscript ------------------------------------------------------------------------------------------
    @classmethod
    def _figure(cls, rect: pygame.Rect) -> tuple[float, float, float]:
        scale = min(rect.height / 400, rect.width / 620) * 0.82
        return rect.left + rect.width * 0.24, rect.bottom - 12, scale

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float, solved: float) -> None:
        """The noria and its ox, and a thief standing in the stolen water - until a fountain lifts him out of it."""
        fx, floor, scale = cls._figure(rect)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        ox, oy = rect.topleft
        lx, lf = fx - ox, floor - oy
        wheel = _scaled(lambda: art.wheel_frame(0), scale * 0.95, "wheel")
        hub = (lx, lf + art.HUB[1] * scale * 0.95)
        tower = _scaled(art.tower, scale * 0.95, "tower")
        layer.blit(tower, (lx + (art.TOWER_LEFT - art.TOWER_ORIGIN[0]) * scale * 0.95, lf - art.TOWER_ORIGIN[1] * scale * 0.95))
        beast = _scaled(lambda: art.ox("walk", 2), scale * 0.95, "ox")
        foot = (lx + (art.OX_PATH[0] + 20) * scale * 0.95, lf + (art.OX_PATH[1] + art.OX_RY) * scale * 0.95)
        layer.blit(beast, (foot[0] - art.OX_FOOT[0] * scale * 0.95, foot[1] - art.OX_FOOT[1] * scale * 0.95))
        layer.blit(wheel, wheel.get_rect(center=(round(hub[0]), round(hub[1]))))
        # The stolen water, and a thief standing in it.
        water_y = lf - 6
        pygame.draw.rect(layer, (*WATER, 150), (0, water_y, rect.width, 8))
        size = round(130 * scale * 2.0)
        thief_x = rect.width * 0.86
        lift = min(1.0, max(0.0, (solved - 0.2) / 0.5)) * size * 0.55
        pose = "flail" if solved > 0.25 else "idle"
        figure = portrait("yusuf", pose, int(t * 8), size)
        if solved > 0.2:
            fountain_art.draw_column(layer, (thief_x, lf), lift + size * 0.08, t * 3, width=max(8, round(26 * scale * 2.0)))
        layer.blit(figure, figure.get_rect(midbottom=(round(thief_x), round(lf + 2 - lift))))
        if solved < 0.35:
            # The coils of water climbing him.
            for strand in range(2):
                points = []
                for k in range(12):
                    h = k / 11 * size * 0.5
                    a = h * 0.12 + t * 4 + strand * math.pi
                    points.append((thief_x + math.sin(a) * size * 0.16, lf - h))
                pygame.draw.lines(layer, (*WATER_LIGHT, 255), False, points, 2)
        layer.fill((252, 238, 206, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(layer, rect.topleft)
        pygame.draw.line(surface, ink.INK, (rect.left + 6, floor), (rect.right - 6, floor), 2)

    @classmethod
    def miniature_lock(cls, rect: pygame.Rect) -> tuple[float, float]:
        fx, floor, scale = cls._figure(rect)
        return rect.left + rect.width * 0.86, floor - 6


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], u: float) -> tuple[int, int, int]:
    u = max(0.0, min(1.0, u))
    return tuple(round(x + (y - x) * u) for x, y in zip(a, b))


_band_cache: dict[int, pygame.Surface] = {}


def _reflection_band(frame: int) -> pygame.Surface:
    """The caustic net, fading upward from the water line (cached per frame)."""
    band = _band_cache.get(frame)
    if band is None:
        tile = art.caustic(frame)
        height = 90
        band = pygame.Surface((tile.get_width(), height))
        band.blit(tile, (0, 0))
        fade = pygame.Surface((tile.get_width(), height))
        for y in range(height):
            level = round(70 * (y / height) ** 1.6)
            fade.fill((level, level, level), (0, y, tile.get_width(), 1))
        band.blit(fade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        _band_cache[frame] = band
    return band


_scaled_cache: dict[tuple[str, float], pygame.Surface] = {}


def _scaled(sprite, scale: float, key: str) -> pygame.Surface:  # noqa: ANN001
    cache_key = (key, round(scale, 3))
    image = _scaled_cache.get(cache_key)
    if image is None:
        full = sprite()
        image = pygame.transform.smoothscale(full, (max(1, round(full.get_width() * scale)), max(1, round(full.get_height() * scale))))
        _scaled_cache[cache_key] = image
    return image
