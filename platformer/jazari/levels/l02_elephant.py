"""Level 2's finale: the Elephant Clock and the Gilded Thieves.

On the last rooftop of the Amber Market, the thief's great brass elephant
stands in the street below and holds the setting sun in its trunk: while it
does, sundown never comes (and the keeper's library, which opens only after
sundown, stays shut). The sky drains to a cold twilight; the only warm light
left is the stolen sun.

Three thieves leap down from the castle on its back, one after another. A
beam of the stolen sunlight follows each one and gilds him: while it rests
on him he is gold, and blows ring off. The beam turns after its thief with a
lag, and anything in its way casts him into shadow - the prince's own body,
a wall, or a stroke of the Night Qalam's ink.

Every hour of the fight the elephant keeps time as al-Jazari's clock did: the
phoenix turns, a falcon drops its golden ball into a serpent's mouth, and the
serpent flings it onto the roof as a bouncing ball of sun.

When the last thief falls, the elephant lifts its trunk and lets the sun go.
It sets at last; the colours flood back, then the blue of evening.
"""

import math
import random
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from entities.performer import strike_player
from entities.thieves import FireEater, Gilded, MirrorThief, SnakeCharmer
from jazari import art as ink
from jazari.base import Guardian
from rendering import emitters
from rendering.art import elephant as art
from rendering.art.thieves import portrait
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from jazari.director import WonderDirector
    from jazari.levels.l02_qalam import InkRoad
    from world.world import World

T = 32
SUNLIGHT = (255, 196, 110)
SUN_GOLD = (255, 214, 120)
STOLEN = (150, 136, 176)     # the sky with its sun taken away
WARM = (255, 214, 170)       # the sunset flooding back
EVENING = (112, 118, 184)    # the blue hour after sundown
CURTAIN = 3.0
LEAP = 0.95
INTERLUDE = 1.6
HOUR = 9.0                   # seconds between the elephant's rituals
BEAM_TURN = 330.0            # how fast a beam swings after its thief (px/s)
PHOENIX_TIME, DROP_TIME, SWING_TIME, REST_TIME = 0.8, 0.45, 0.45, 0.7


# --- the machine -------------------------------------------------------------------------------------
class ElephantClock:
    def __init__(self, x: float, floor: float) -> None:
        self.x = x
        self.floor = floor
        self.time = 0.0
        self.sway = 0.0
        self.lift = 0.0
        self.lift_target = 0.0
        self.strength = 0.45
        self.strength_target = 0.45
        self.setting = 0.0
        self.released = False
        self.free_sun: list[float] = [0.0, 0.0, 0.0, 0.0]   # x, y, vx, vy once it is let go
        self.kneel = 0.0
        self.kneel_target = 0.0
        self.ritual = ""
        self.ritual_time = 0.0
        self.ball_visible = False
        self.serpent_angle = 0.0
        self.falcon_lean = 0
        self.mahout = 0
        self.gaze = (x - 400, floor)
        self.awake = False

    # --- where things are (world coordinates) --------------------------------------------------------
    def at(self, point: tuple[float, float]) -> tuple[float, float]:
        return self.x + point[0], self.floor + point[1] + self.kneel * 20

    @property
    def root(self) -> tuple[float, float]:
        return self.at(art.TRUNK_ROOT)

    @property
    def sun(self) -> tuple[float, float]:
        if self.released:
            return self.free_sun[0], self.free_sun[1]
        rx, ry = self.root
        hx, hy = art.sun_hold(self.sway, self.lift)
        return rx + hx, ry + hy

    @property
    def serpent_mouth(self) -> tuple[float, float]:
        px, py = self.at(art.SERPENT_PIVOT)
        mx, my = art.serpent_mouth(self.serpent_angle)
        return px + mx, py + my

    @property
    def falcon_beak(self) -> tuple[float, float]:
        fx, fy = self.at(art.FALCONS[0])
        return fx - 16, fy - 10

    def start_ritual(self) -> bool:
        if self.ritual or self.released:
            return False
        self.ritual = "phoenix"
        self.ritual_time = 0.0
        return True

    def release(self) -> None:
        sx, sy = self.sun
        self.released = True
        self.free_sun = [sx, sy, -40.0, -150.0]

    def update(self, dt: float) -> str | None:
        """Advance; returns "fling" on the frame the serpent lets go of its ball."""
        self.time += dt
        self.sway = math.sin(self.time * 0.9) * 0.6
        self.lift += (self.lift_target - self.lift) * min(1.0, dt * 2.2)
        self.strength += (self.strength_target - self.strength) * min(1.0, dt * 1.5)
        self.kneel += (self.kneel_target - self.kneel) * min(1.0, dt * 1.2)
        if self.released:
            sun = self.free_sun
            sun[2] *= 1 - dt * 0.3
            sun[0] += sun[2] * dt
            sun[1] += sun[3] * dt
            self.setting = min(1.0, self.setting + dt * 0.35)
            self.strength_target = max(0.0, 1.0 - self.setting * 1.3)
        event = None
        if self.ritual:
            self.ritual_time += dt
            stage = self.ritual
            if stage == "phoenix" and self.ritual_time > PHOENIX_TIME:
                self.ritual, self.ritual_time = "drop", 0.0
                self.ball_visible = True
            elif stage == "drop":
                self.falcon_lean = min(3, int(self.ritual_time / DROP_TIME * 4))
                if self.ritual_time > DROP_TIME:
                    self.ritual, self.ritual_time = "swing", 0.0
            elif stage == "swing":
                self.serpent_angle = -55 * math.sin(min(1.0, self.ritual_time / SWING_TIME) * math.pi / 2)
                if self.ritual_time > SWING_TIME:
                    self.ritual, self.ritual_time = "rest", 0.0
                    self.ball_visible = False
                    event = "fling"
            elif stage == "rest":
                self.falcon_lean = max(0, 3 - int(self.ritual_time / REST_TIME * 4))
                self.serpent_angle *= max(0.0, 1 - dt * 5)
                self.mahout = 1 + int(self.ritual_time * 8) % 2
                if self.ritual_time > REST_TIME:
                    self.ritual = ""
                    self.mahout = 0
                    self.serpent_angle = 0.0
        return event

    def ball_position(self) -> tuple[float, float]:
        """The golden ball in the machine (from the falcon's beak to the serpent's mouth)."""
        if self.ritual == "drop":
            u = min(1.0, self.ritual_time / DROP_TIME)
            (bx, by), (mx, my) = self.falcon_beak, self.serpent_mouth
            return bx + (mx - bx) * u, by + (my - by) * u * u
        return self.serpent_mouth

    # --- drawing (behind the rooftop: this is scenery) ------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        fx, fy = camera.to_screen(self.x, self.floor + self.kneel * 20)
        glow = self.strength
        # The castle's windows glow with the stolen light (painted behind the lattice).
        for wx, wy in art.WINDOWS:
            flicker = 0.85 + 0.15 * math.sin(self.time * 7 + wx)
            blit_glow(surface, (fx + wx, fy + wy), 34, SUNLIGHT, min(1.0, (0.35 + 0.6 * glow) * flicker))
            pygame.draw.ellipse(surface, (255, 214, 140) if glow > 0.3 else (190, 150, 110), (fx + wx - 12, fy + wy - 22, 24, 50))
        scribe = art.scribe(int(self.time * 5) % 4)
        surface.blit(scribe, scribe.get_rect(midbottom=(fx + art.WINDOWS[1][0], fy + art.WINDOWS[1][1] + 26)))
        base = art.base()
        surface.blit(base, (fx - art.BASE_ORIGIN[0], fy - art.BASE_ORIGIN[1]))
        ear = art.ear(int(self.time * 4) % 8)
        surface.blit(ear, (fx + art.EAR_ROOT[0] - art.EAR_ORIGIN[0], fy + art.EAR_ROOT[1] - art.EAR_ORIGIN[1]))
        mahout = art.mahout(3 if self.kneel > 0.5 else self.mahout)
        surface.blit(mahout, mahout.get_rect(midbottom=(fx + art.MAHOUT[0], fy + art.MAHOUT[1])))
        # The serpent swings on its pivot.
        serpent = art.serpent(1 if self.ritual in ("drop", "swing") else 0)
        rotated = pygame.transform.rotate(serpent, self.serpent_angle)
        pvx, pvy = art.SERPENT_ORIGIN
        cx, cy = serpent.get_width() / 2, serpent.get_height() / 2
        a = math.radians(-self.serpent_angle)
        vx, vy = pvx - cx, pvy - cy
        rvx, rvy = vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
        px, py = fx + art.SERPENT_PIVOT[0], fy + art.SERPENT_PIVOT[1]
        surface.blit(rotated, rotated.get_rect(center=(round(px - rvx), round(py - rvy))))
        for k, (x, y) in enumerate(art.FALCONS):
            falcon = art.falcon(self.falcon_lean if k == 0 else 0, not (k == 0 and self.ritual in ("drop", "swing", "rest")))
            if k == 1:
                falcon = pygame.transform.flip(falcon, True, False)
            surface.blit(falcon, falcon.get_rect(midbottom=(fx + x, fy + y + 6)))
        spin = 3.0 if self.ritual == "phoenix" else 0.6
        phoenix = art.phoenix(int(self.time * 8 * spin) % 8)
        surface.blit(phoenix, phoenix.get_rect(center=(fx + art.PHOENIX[0], fy + art.PHOENIX[1])))
        if self.ritual == "phoenix":
            blit_glow(surface, (fx + art.PHOENIX[0], fy + art.PHOENIX[1]), 30, SUN_GOLD, 0.6)
        if self.ball_visible:
            bx, by = camera.to_screen(*self.ball_position())
            blit_glow(surface, (bx, by), 14, SUNLIGHT, 0.8)
            pygame.draw.circle(surface, (120, 70, 20), (bx, by), 6)
            pygame.draw.circle(surface, SUN_GOLD, (bx, by), 5)
        # The trunk, holding the sun (or letting it go, or bowed).
        lift_step = max(-4, min(4, round(self.lift * 4)))
        trunk = art.trunk(max(-4, min(4, round(self.sway * 4))), lift_step)
        rx, ry = camera.to_screen(*self.root)
        surface.blit(trunk, (rx - art.TRUNK_ORIGIN[0], ry - art.TRUNK_ORIGIN[1]))
        # The eye: amber, glowing, following the prince.
        ex, ey = fx + art.EYE[0], fy + art.EYE[1]
        gx, gy = camera.to_screen(*self.gaze)
        dx, dy = gx - ex, gy - ey
        d = max(1.0, math.hypot(dx, dy))
        blit_glow(surface, (ex, ey), 14, (255, 170, 60), 0.5 + 0.5 * glow)
        pygame.draw.circle(surface, (255, 204, 96) if self.awake else (170, 120, 60), (ex, ey), 5)
        pygame.draw.circle(surface, (50, 26, 10), (round(ex + dx / d * 2), round(ey + dy / d * 1.5)), 2)
        if self.strength > 0.02:
            sx, sy = camera.to_screen(*self.sun)
            art.draw_sun(surface, (sx, sy), art.SUN_RADIUS * (1 - 0.35 * self.setting), self.time, self.strength, self.setting)

    def lights(self) -> list[Light]:
        sx, sy = self.sun
        lights = [Light(sx, sy, 440, SUNLIGHT, min(1.0, 0.4 + 0.6 * self.strength), bloom=0.45 * self.strength)]
        for wx, wy in art.WINDOWS:
            x, y = self.at((wx, wy))
            lights.append(Light(x, y, 60, SUNLIGHT, 0.5 * self.strength, flicker=0.3))
        ex, ey = self.at(art.EYE)
        lights.append(Light(ex, ey, 40, (255, 170, 60), 0.6))
        return lights


# --- the sunbeams that gild the thieves ------------------------------------------------------------------------
class Beam:
    def __init__(self, thief: Gilded, sun: tuple[float, float]) -> None:
        self.thief = thief
        self.aim = sun
        self.end = sun
        self.blocker = ""
        self.time = random.uniform(0, 10)

    def update(self, dt: float, world: "World", sun: tuple[float, float], roads: list["InkRoad"]) -> None:
        self.time += dt
        thief = self.thief
        target = thief.chest
        dx, dy = target[0] - self.aim[0], target[1] - self.aim[1]
        distance = math.hypot(dx, dy)
        step = BEAM_TURN * dt
        if distance <= step:
            self.aim = target
        else:
            self.aim = (self.aim[0] + dx / distance * step, self.aim[1] + dy / distance * step)
        on_target = math.hypot(target[0] - self.aim[0], target[1] - self.aim[1]) < 22
        self.end, self.blocker = self._trace(world, sun, self.aim, roads)
        thief.lit = on_target and not self.blocker and thief.state not in ("vanished", "defeated", "offstage")

    @staticmethod
    def _trace(world: "World", sun: tuple[float, float], aim: tuple[float, float],
               roads: list["InkRoad"]) -> tuple[tuple[float, float], str]:
        """Follow the light from the sun to ``aim``; return where it stops and what stopped it."""
        best = (aim, "")
        best_d = math.hypot(aim[0] - sun[0], aim[1] - sun[1])
        rect = world.player.rect.inflate(-2, -2)
        clip = rect.clipline(sun, aim)
        if clip and world.player.is_controllable:
            point = clip[0]
            d = math.hypot(point[0] - sun[0], point[1] - sun[1])
            if d < best_d:
                best, best_d = (point, "prince"), d
        for road in roads:
            if road.wet:
                point = road.blocks(sun, aim)
                if point is not None:
                    d = math.hypot(point[0] - sun[0], point[1] - sun[1])
                    if d < best_d:
                        best, best_d = (point, "ink"), d
        # Walls and roofs cast shadows too (checked coarsely, only near the end of the beam).
        collision = world.collision
        length = best_d
        if length > 1:
            ux, uy = (aim[0] - sun[0]) / max(1.0, math.hypot(aim[0] - sun[0], aim[1] - sun[1])), \
                     (aim[1] - sun[1]) / max(1.0, math.hypot(aim[0] - sun[0], aim[1] - sun[1]))
            d = max(0.0, length - 260)
            while d < length - 6:
                x, y = sun[0] + ux * d, sun[1] + uy * d
                tx, ty = collision.tile_at(x, y)
                if collision.get(tx, ty).name == "SOLID":
                    return (x, y), "wall"
                d += 8
        return best

    def draw(self, surface: pygame.Surface, camera: Camera, sun: tuple[float, float], strength: float) -> None:
        if self.thief.gone or self.thief.state in ("offstage", "defeated"):
            return
        start = camera.to_screen(*sun)
        end = camera.to_screen(*self.end)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        if length < 4:
            return
        steps = max(4, int(length / 26))
        for k in range(1, steps + 1):
            f = k / steps
            x = start[0] + (end[0] - start[0]) * f
            y = start[1] + (end[1] - start[1]) * f
            blit_glow(surface, (x, y), round(10 + 12 * f), SUNLIGHT, 0.22 * strength)
        pygame.draw.line(surface, (255, 226, 150), start, end, 2)
        # Motes of light drifting down the shaft.
        for k in range(5):
            f = (self.time * 0.35 + k / 5) % 1.0
            x = start[0] + (end[0] - start[0]) * f + math.sin(self.time * 3 + k) * 3
            y = start[1] + (end[1] - start[1]) * f
            surface.fill((255, 250, 220), (round(x), round(y), 2, 2))
        if self.blocker == "prince":
            blit_glow(surface, end, 22, SUN_GOLD, 0.9)
        elif self.blocker == "ink":
            blit_glow(surface, end, 16, (170, 150, 255), 0.8)
            for k in range(3):
                a = self.time * 9 + k * 2.1
                surface.fill((255, 240, 200), (round(end[0] + math.cos(a) * 6), round(end[1] + math.sin(a) * 3 - 2), 2, 2))
        elif self.blocker == "":
            blit_glow(surface, end, 20, SUN_GOLD, 0.6 * strength)

    def lights(self, sun: tuple[float, float]) -> list[Light]:
        if self.thief.gone or self.thief.state in ("offstage", "defeated"):
            return []
        (sx, sy), (ex, ey) = sun, self.end
        return [Light(sx + (ex - sx) * f, sy + (ey - sy) * f, 46, SUNLIGHT, 0.35) for f in (0.35, 0.65, 0.95)]


class SunBall:
    """A golden ball flung by the serpent: it bounces across the roof, blazing."""

    RADIUS = 11

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        from physics.body import Body

        self.body = Body.from_midbottom((x, y + self.RADIUS), self.RADIUS * 2, self.RADIUS * 2)
        self.body.velocity.update(vx, vy)
        self.age = 0.0
        self.alive = True
        self.bounces = 0
        self.spin = 0.0

    @property
    def center(self) -> tuple[float, float]:
        return self.body.centerx, self.body.centery

    def update(self, dt: float, world: "World", bounds: tuple[float, float]) -> None:
        from physics.collision import apply_gravity, move_body

        self.age += dt
        body = self.body
        vx = body.velocity.x
        apply_gravity(body, 1100.0, 900.0, dt)
        falling = body.velocity.y
        move_body(body, dt, world.collision)
        self.spin += vx * dt * 0.1
        if body.on_ground and falling > 60:
            self.bounces += 1
            body.velocity.y = -max(260.0, falling * 0.72)
            emitters.embers(world.particles, body.centerx, body.bottom - 2, 5, 10)
            world.events.emit(EventType.MACHINE_CLUNK, (body.centerx, body.bottom), "sunball_bounce")
        if body.hit_wall:
            body.velocity.x = -vx
        else:
            body.velocity.x = vx
        if world.particles.rng.random() < 0.6:
            emitters.embers(world.particles, body.centerx, body.centery, 1, 6)
        left, right = bounds
        if self.age > 7.0 or not left - 60 < body.centerx < right + 60 or body.top > world.collision.pixel_height:
            self.burst(world)
            return
        if body.rect().inflate(-6, -6).colliderect(world.player.rect):
            strike_player(world, 1 if body.velocity.x > 0 else -1, 260)
            self.burst(world)

    def burst(self, world: "World") -> None:
        if not self.alive:
            return
        self.alive = False
        emitters.sparkle_burst(world.particles, *self.center, SUN_GOLD, 12, 160)
        emitters.embers(world.particles, *self.center, 8, 12)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(*self.center)
        blit_glow(surface, (x, y), 30, SUNLIGHT, 0.9)
        pygame.draw.circle(surface, (160, 70, 20), (x, y), self.RADIUS + 1)
        pygame.draw.circle(surface, (255, 170, 60), (x, y), self.RADIUS)
        pygame.draw.circle(surface, (255, 236, 160), (x - 3, y - 3), self.RADIUS // 2)
        for k in range(6):
            a = self.spin + k * math.tau / 6
            pygame.draw.line(surface, (255, 120, 40), (x + math.cos(a) * 5, y + math.sin(a) * 5),
                             (x + math.cos(a) * (self.RADIUS + 5), y + math.sin(a) * (self.RADIUS + 5)), 2)


# --- the encounter --------------------------------------------------------------------------------------------------
class GildedThieves(Guardian):
    name = "The Gilded Thieves"
    device = "The Elephant Clock"
    lethal = True
    reach = 16
    intro = "The Gilded Thieves! Their elephant holds the setting sun - sundown will never come!"
    farewell = "The elephant lets the sun go. Evening falls over the Amber Market."
    music = "gilded"

    def __init__(self, director: "WonderDirector", x: float, floor: float) -> None:
        super().__init__(director, x, floor)
        world = director.world
        self.left = x - 17 * T
        goals = list(world.goals) + list(getattr(director, "_held_goals", []))
        self.right = min((goal.rect.left - 8 for goal in goals if goal.rect.left > x), default=x + 11 * T)
        self.arena = pygame.Rect(round(self.left), round(floor - 12 * T), round(self.right - self.left), 12 * T)
        self.focus = (self.left + 464.0, floor - 142.0)
        bounds = (self.left + 12.0, self.right - 10.0)
        sprites = world.sprites
        self.cast: list[Gilded] = [MirrorThief(x, floor, sprites, bounds), FireEater(x, floor, sprites, bounds),
                                   SnakeCharmer(x, floor, sprites, bounds)]
        self.spots = self._spots(world)
        charmer = self.cast[2]
        assert isinstance(charmer, SnakeCharmer)
        charmer.set_baskets(self._baskets(world))
        self.act = max(0, min(3, getattr(director, "progress", 0)))
        for thief in self.cast[:self.act]:
            thief.gone = True
        self.clock = ElephantClock(x, floor)
        self.stage = "sleep"
        self.stage_time = 0.0
        self.beams: list[Beam] = []
        self.balls: list[SunBall] = []
        self.hour_timer = HOUR
        self.dusk = 0.0
        self.dusk_target = 0.0
        self.sky = STOLEN
        self.leaper: Gilded | None = None
        self.leap_from = (0.0, 0.0)
        self.leap_to = (0.0, 0.0)
        self.motes: list[list[float]] = []

    def _ground(self, world: "World", x: float) -> float:
        from jazari.base import ground_below

        return ground_below(world, x, self.floor - 4 * T)

    def _spots(self, world: "World") -> list[tuple[float, float]]:
        xs = (self.left + 3.5 * T, self.x - 5 * T, self.x + 2 * T, self.right - 3 * T)
        return [(x, self._ground(world, x)) for x in xs]

    def _baskets(self, world: "World") -> list[tuple[float, float]]:
        xs = (self.left + 3 * T, self.x - 2 * T, self.right - 2.5 * T)
        return [(x, self._ground(world, x)) for x in xs]

    # --- what the director and powers ask ------------------------------------------------------------------
    @property
    def fighting(self) -> bool:
        return self.stage in ("curtain", "leap", "act", "interlude", "finale")

    @property
    def camera_focus(self) -> tuple[float, float] | None:
        player = self.director.world.player
        if not self.fighting or not (self.left - 48 <= player.body.centerx <= self.right + 96):
            return None
        return self.focus

    @property
    def night(self) -> tuple[int, int, int]:
        return self.sky

    def roads(self) -> list["InkRoad"]:
        power = self.director.power
        return list(getattr(power, "roads", []))

    def lock_rect(self) -> pygame.Rect:
        sx, sy = self.clock.sun
        return pygame.Rect(round(sx) - 30, round(sy) - 30, 60, 60)

    def on_power(self, kind: str, thing: object, world: "World") -> bool:
        if kind != "ink":
            return False
        road = thing
        reacted = False
        for thief in self.cast:
            if not thief.targetable or id(thief) in road.touched:
                continue
            reach = thief.rect.inflate(6, 10)
            if road.overlaps(reach):
                road.touched.add(id(thief))
                if road.flying:
                    road.stop(world, abs(thief.body.centerx - road.x0))
                thief.inked(world)
                reacted = True
        # Night swallows the sun's missiles and cuts its fire short.
        for ball in self.balls:
            if ball.alive and road.overlaps(ball.body.rect().inflate(6, 6)):
                ball.alive = False
                for _ in range(10):
                    rng = world.particles.rng
                    world.particles.spawn(ball.body.centerx, ball.body.centery, rng.uniform(-40, 40), rng.uniform(-90, -30),
                                          life=0.8, kind=Kind.SMOKE, size=4, size_end=12, color=(150, 140, 170), alpha=0.7)
                world.events.emit(EventType.MACHINE_CLUNK, ball.center, "ink_hiss")
                reacted = True
        for thief in self.cast:
            if isinstance(thief, MirrorThief) and thief.lance is not None:
                point = road.blocks(*thief.lance)
                if point is not None:
                    thief.cut_lance(point)
            if isinstance(thief, FireEater) and thief.plan == "breathe":
                mx, my = thief.mouth()
                left, right = road.span()
                if abs(road.y - my) < 30 and left - 10 <= mx + thief.facing * 40 <= right + 10:
                    thief.cone_cut = min(thief.cone_cut, 0.25)
        return reacted

    # --- update ------------------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.stage_time += dt
        clock = self.clock
        player = world.player
        if self.resolved and self.stage not in ("done", "finale"):
            self._settle()
        engaged = self.left - 16 <= player.body.centerx <= self.right + 40 and player.is_controllable
        clock.gaze = (player.body.centerx, player.body.centery)
        stage = self.stage
        if stage == "sleep":
            if player.is_controllable and self.left + 6 * T < player.body.centerx < self.right + 64:
                self._wake(world)
        elif stage == "curtain":
            if self.stage_time > CURTAIN:
                self._leap_next(world)
        elif stage == "leap":
            self._update_leap(world)
        elif stage == "act":
            thief = self.cast[self.act]
            fighting = thief.state not in ("defeated", "enter") and not thief.gone
            if self.act >= 1 and engaged and fighting:
                self.hour_timer -= dt
                if self.hour_timer <= 0 and clock.start_ritual():
                    self.hour_timer = HOUR
                    world.events.emit(EventType.MACHINE_CLUNK, clock.at(art.PHOENIX), "phoenix")
            if isinstance(thief, SnakeCharmer) and thief.called and fighting:
                if clock.start_ritual():
                    world.events.emit(EventType.MACHINE_CLUNK, clock.at(art.PHOENIX), "phoenix")
            if thief.gone:
                self.act += 1
                self.director.progress = self.act
                self.beams = [b for b in self.beams if b.thief is not thief]
                if self.act >= 3:
                    self._set_stage("finale")
                    for ball in self.balls:
                        ball.burst(world)
                    clock.lift_target = 1.0
                    clock.strength_target = 1.0
                    world.events.emit(EventType.MACHINE_CLUNK, clock.sun, "elephant")
                else:
                    self._set_stage("interlude")
        elif stage == "interlude":
            if self.stage_time > INTERLUDE:
                self._leap_next(world)
        elif stage == "finale":
            self._update_finale(dt, world)
        if clock.update(dt) == "fling":
            self._fling(world)
        roads = self.roads()
        for beam in self.beams:
            beam.update(dt, world, clock.sun, roads)
        for thief in self.cast:
            if thief.state != "offstage" or thief.gone:
                thief.engaged = engaged
                thief.update(dt, world)
        for ball in self.balls:
            if ball.alive:
                ball.update(dt, world, (self.left, self.right))
        self.balls = [ball for ball in self.balls if ball.alive]
        self._update_motes(dt, world)
        self.dusk += (self.dusk_target - self.dusk) * min(1.0, dt * 1.1)

    def _set_stage(self, stage: str) -> None:
        self.stage = stage
        self.stage_time = 0.0

    def _wake(self, world: "World") -> None:
        self.awake = True
        self.clock.awake = True
        self.clock.strength_target = 1.0
        self.clock.lift_target = 0.15
        self.dusk_target = 1.0
        self.sky = STOLEN
        self._set_stage("curtain" if self.act < 3 else "finale")
        world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), self.intro)
        world.events.emit(EventType.MACHINE_CLUNK, self.clock.sun, "elephant")

    def _settle(self) -> None:
        """Beaten already: the elephant kneels, its castle lamps lit, and the sun has set."""
        self._set_stage("done")
        clock = self.clock
        clock.released = True
        clock.free_sun = [clock.x - 400, clock.floor - 900, 0.0, 0.0]
        clock.strength = clock.strength_target = 0.0
        clock.setting = 1.0
        clock.kneel = clock.kneel_target = 1.0
        clock.lift = clock.lift_target = -1.0
        clock.awake = False
        for thief in self.cast:
            thief.gone = True
        self.beams = []
        self.dusk_target = 0.0

    # --- a thief leaps down from the castle ------------------------------------------------------------------
    def _leap_next(self, world: "World") -> None:
        thief = self.cast[self.act]
        player = world.player
        spots = sorted(self.spots, key=lambda s: -abs(s[0] - player.body.centerx))
        self.leap_to = spots[0] if random.random() < 0.7 else spots[1]
        self.leap_from = self.clock.at((art.HOWDAH_X - 40, -280))
        self.leaper = thief
        thief.state = "enter"
        thief.body.place_midbottom(self.leap_from)
        thief.animator.play("leap")
        self._set_stage("leap")
        world.events.emit(EventType.MACHINE_CLUNK, self.leap_from, "leap")

    def _update_leap(self, world: "World") -> None:
        thief = self.leaper
        if thief is None:
            return
        u = min(1.0, self.stage_time / LEAP)
        (x0, y0), (x1, y1) = self.leap_from, self.leap_to
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u - math.sin(u * math.pi) * 110
        thief.body.place_midbottom((x, y))
        thief.facing = 1 if x1 > x0 else -1
        if u >= 1.0:
            thief.body.velocity.update(0, 0)
            thief.enter(world)
            thief.animator.play("land", restart=True)
            thief.facing = 1 if world.player.body.centerx > x1 else -1
            emitters.landing_dust(world.particles, x1, y1, 1.4)
            self.beams.append(Beam(thief, self.clock.sun))
            if isinstance(thief, SnakeCharmer):
                thief.basket = min(range(len(thief.cobras)), key=lambda k: abs(thief.cobras[k].x - x1))
            self.leaper = None
            self.hour_timer = HOUR * 0.7
            self._set_stage("act")
            world.events.emit(EventType.MACHINE_CLUNK, (x1, y1), "land")
            world.events.emit(EventType.GUARDIAN_AWAKE, (x1, y1), thief.title + "!")

    # --- the elephant's hour --------------------------------------------------------------------------------------
    def _fling(self, world: "World") -> None:
        mx, my = self.clock.serpent_mouth
        player = world.player
        target = player.body.centerx + random.uniform(-40, 40)
        flight = 1.0
        vx = (target - mx) / flight
        vy = (player.body.bottom - 20 - my - 0.5 * 1100 * flight * flight) / flight
        self.balls.append(SunBall(mx, my, vx * 0.85, vy))
        world.events.emit(EventType.MACHINE_CLUNK, (mx, my), "serpent_fling")

    # --- the finale -------------------------------------------------------------------------------------------------
    def _update_finale(self, dt: float, world: "World") -> None:
        clock = self.clock
        t = self.stage_time
        if t > 1.2 and not clock.released:
            clock.release()
            world.events.emit(EventType.MACHINE_CLUNK, clock.sun, "sun_release")
            sx, sy = clock.sun
            emitters.sparkle_burst(world.particles, sx, sy, SUN_GOLD, 24, 220)
            world.particles.spawn(sx, sy, life=0.8, kind=Kind.RING, size=20, size_end=180, color=SUN_GOLD)
        if clock.released:
            since = t - 1.2
            # The colours flood back, then deepen into evening.
            if since < 0.8:
                self.sky = _mix(STOLEN, WARM, since / 0.8)
            else:
                self.sky = _mix(WARM, EVENING, min(1.0, (since - 0.8) / 3.0))
            if since > 0.9 and not self.resolved:
                clock.lift_target = -1.0
                clock.kneel_target = 1.0
                clock.awake = False
                self.resolve(world, "sunset")
                emitters.petal_shower(world.particles, clock.x, clock.floor - 140, 30)
            if since > 4.0:
                self._set_stage("done")

    def _update_motes(self, dt: float, world: "World") -> None:
        """While it holds the sun, golden motes of the city's light drift into it."""
        clock = self.clock
        if self.fighting and not clock.released and world.particles.rng.random() < dt * 12:
            rng = world.particles.rng
            a = rng.uniform(0, math.tau)
            r = rng.uniform(160, 320)
            sx, sy = clock.sun
            self.motes.append([sx + math.cos(a) * r, sy + math.sin(a) * r * 0.6 + 60, 0.0])
        sx, sy = clock.sun
        for mote in self.motes:
            mote[2] += dt
            dx, dy = sx - mote[0], sy - mote[1]
            d = max(1.0, math.hypot(dx, dy))
            speed = 60 + 220 * min(1.0, mote[2])
            mote[0] += dx / d * speed * dt - dy / d * 40 * dt
            mote[1] += dy / d * speed * dt + dx / d * 40 * dt
            if d < 24:
                mote[2] = 99
        self.motes = [m for m in self.motes if m[2] < 5]

    # --- drawing -------------------------------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        clock = self.clock
        lights = clock.lights()
        for thief in self.cast:
            lights += thief.lights()
        for beam in self.beams:
            lights += beam.lights(clock.sun)
        for ball in self.balls:
            lights.append(Light(*ball.center, 90, SUNLIGHT, 0.9, flicker=0.5, bloom=0.3))
        if self.stage in ("finale", "done") and clock.released:
            # The market's lamps come on for the evening.
            for k in range(6):
                x = self.left + 60 + k * (self.right - self.left - 120) / 5
                lights.append(Light(x, self.floor - 70, 70, (255, 200, 120), 0.5 * min(1.0, self.stage_time / 3), flicker=0.4))
        return lights

    def draw_scenery(self, surface: pygame.Surface, camera: Camera) -> None:
        self.clock.draw(surface, camera)
        for mote in self.motes:
            x, y = camera.to_screen(mote[0], mote[1])
            surface.fill((255, 226, 150), (x, y, 2, 2))

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        clock = self.clock
        for beam in self.beams:
            beam.draw(surface, camera, clock.sun, clock.strength)
        for thief in self.cast:
            thief.draw_back(surface, camera)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for thief in self.cast:
            if thief is self.leaper:
                self._draw_leaper(surface, camera, thief)
            else:
                thief.draw(surface, camera)
        for ball in self.balls:
            ball.draw(surface, camera)

    def _draw_leaper(self, surface: pygame.Surface, camera: Camera, thief: Gilded) -> None:
        u = min(1.0, self.stage_time / LEAP)
        image = thief.animator.image(flip_x=thief.facing < 0)
        spin = -thief.facing * 360 * u
        rotated = pygame.transform.rotate(image, spin)
        x, y = camera.to_screen(thief.body.centerx, thief.body.centery)
        surface.blit(rotated, rotated.get_rect(center=(x, y)))
        blit_glow(surface, (x, y), 20, SUN_GOLD, 0.5)

    # --- the manuscript ---------------------------------------------------------------------------------------------
    @classmethod
    def _figure(cls, rect: pygame.Rect) -> tuple[float, float, float]:
        scale = min(rect.height / 420, rect.width / 640)
        return rect.left + rect.width * 0.46, rect.bottom - 10, scale

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float, solved: float) -> None:
        """The elephant holding the sun, and a thief gilded by its beam - until night is written across it."""
        fx, floor, scale = cls._figure(rect)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        ox, oy = rect.topleft
        lx, lf = fx - ox, floor - oy
        base = _scaled(art.base, scale)
        layer.blit(base, (lx - art.BASE_ORIGIN[0] * scale, lf - art.BASE_ORIGIN[1] * scale))
        ear = _scaled(lambda: art.ear(0), scale, "ear")
        layer.blit(ear, (lx + (art.EAR_ROOT[0] - art.EAR_ORIGIN[0]) * scale, lf + (art.EAR_ROOT[1] - art.EAR_ORIGIN[1]) * scale))
        trunk = _scaled(lambda: art.trunk(0, 0), scale, "trunk")
        rx, ry = lx + art.TRUNK_ROOT[0] * scale, lf + art.TRUNK_ROOT[1] * scale
        layer.blit(trunk, (rx - art.TRUNK_ORIGIN[0] * scale, ry - art.TRUNK_ORIGIN[1] * scale))
        hx, hy = art.sun_hold(0, 0)
        sun = (rx + hx * scale, ry + hy * scale)
        art.draw_sun(layer, sun, art.SUN_RADIUS * scale * 1.3, t)
        # The thief, larger than life so the page can show the gold on him.
        size = round(150 * scale * 1.6)
        thief_x = rect.width * 0.86
        figure = portrait("tariq", "stunned" if solved > 0.5 else "idle", int(t * 8), size)
        if solved < 0.5:
            gold = pygame.transform.grayscale(figure)
            gold.fill((255, 214, 120), special_flags=pygame.BLEND_RGB_MULT)
            gold.fill((70, 44, 0), special_flags=pygame.BLEND_RGB_ADD)
            figure = gold
        chest = (thief_x, lf - size * 0.55)
        beam_end = chest
        cut = None
        if solved > 0.25:
            # A stroke of night written across the beam.
            f = 0.55
            cut = (sun[0] + (chest[0] - sun[0]) * f, sun[1] + (chest[1] - sun[1]) * f)
            beam_end = cut
        pygame.draw.line(layer, (255, 226, 150, 255), sun, beam_end, 3)
        for k in range(6):
            f = (k + 1) / 6
            blit_glow(layer, (sun[0] + (beam_end[0] - sun[0]) * f, sun[1] + (beam_end[1] - sun[1]) * f), 9, SUNLIGHT, 0.5)
        layer.blit(figure, figure.get_rect(midbottom=(round(thief_x), round(lf + 2))))
        if cut is not None:
            length = min(1.0, (solved - 0.25) / 0.3) * rect.width * 0.22
            from rendering.art import qalam

            qalam.draw_stroke(layer, (cut[0] - rect.width * 0.11, cut[1]), length, 1, t, 0.0, 99.0, 0.4, qalam.make_stars(8, 8))
        layer.fill((252, 238, 206, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(layer, rect.topleft)
        pygame.draw.line(surface, ink.INK, (rect.left + 6, floor), (rect.right - 6, floor), 2)

    @classmethod
    def miniature_lock(cls, rect: pygame.Rect) -> tuple[float, float]:
        fx, floor, scale = cls._figure(rect)
        rx, ry = fx + art.TRUNK_ROOT[0] * scale, floor + art.TRUNK_ROOT[1] * scale
        hx, hy = art.sun_hold(0, 0)
        sun = (rx + hx * scale, ry + hy * scale)
        size = round(150 * scale * 1.6)
        chest = (rect.left + rect.width * 0.86, floor - size * 0.55)
        return sun[0] + (chest[0] - sun[0]) * 0.55, sun[1] + (chest[1] - sun[1]) * 0.55


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], u: float) -> tuple[int, int, int]:
    u = max(0.0, min(1.0, u))
    return tuple(round(x + (y - x) * u) for x, y in zip(a, b))


_scaled_cache: dict[tuple[str, float], pygame.Surface] = {}


def _scaled(sprite, scale: float, key: str = "") -> pygame.Surface:  # noqa: ANN001
    name = key or sprite.__name__
    cache_key = (name, round(scale, 3))
    image = _scaled_cache.get(cache_key)
    if image is None:
        full = sprite()
        image = pygame.transform.smoothscale(full, (max(1, round(full.get_width() * scale)), max(1, round(full.get_height() * scale))))
        _scaled_cache[cache_key] = image
    return image
