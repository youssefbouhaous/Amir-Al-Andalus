"""The River-Thieves: al-Muqallid's people at the Singing Aqueduct.

His Sky-Noria pours the river into the sky and floods the stage with what is
left; the thieves sell the city its own water by the cup. While a thief stands
in that stolen water the noria lends him its patient strength - the water
climbs him in shining coils and drinks every blow. Out of it he is only a man:
when the flood ebbs (the brass ox stops to drink), when he leaps, or when a
fountain lifts him off his feet.

* ``WaterSeller`` (Yusuf) squeezes his goatskin into a jet that hurls the
  prince back, throws his brass cups like boomerangs, and belly-flops.
* ``NetFisher`` (Nur) casts a weighted net, fishes carp out of the sky river
  to drop on the prince, and pole-vaults over him on her spear.
* ``RainCaller`` (Hamida) calls spears of rain down from the river, floats
  under her parasol scattering drops, and spins it to push the prince away.
"""

import math
import random
from typing import TYPE_CHECKING, Protocol

import pygame

from core.events import EventType
from core.settings import Color
from entities.performer import Performer, strike_player
from jazari.base import ground_below, shove
from rendering import emitters
from rendering.art import noria
from rendering.art import river_thieves as art
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from rendering.sprite_library import SpriteLibrary

if TYPE_CHECKING:
    from world.world import World

T = 32
WATER: Color = (96, 200, 236)
WATER_LIGHT: Color = (214, 246, 255)
WATER_DEEP: Color = (40, 120, 178)
CUP: Color = (232, 186, 84)
CUP_LIGHT: Color = (255, 236, 170)
LEATHER: Color = (128, 80, 44)
LEATHER_DARK: Color = (88, 54, 30)
OUTLINE: Color = (40, 26, 22)
ROOT_GROW = 1.6      # how fast the water climbs a thief standing in the flood (per second)
ROOT_FADE = 4.0      # ...and leaves him once he is out of it
WARD_AT = 0.55       # roots above this drink blows
DIZZY = 1.1          # seconds a thief sits stunned after a fountain lets him fall


class Fountain(Protocol):
    """What a thief needs to know about one of the prince's fountains (``jazari.levels.l04_fountain.Jet``)."""

    x: float

    @property
    def holding(self) -> bool: ...

    @property
    def crest(self) -> float: ...

    def column(self) -> pygame.Rect: ...


# --- the water's coils on a thief ------------------------------------------------------------------
_wet_cache: dict[int, pygame.Surface] = {}


def _watered(image: pygame.Surface) -> pygame.Surface:
    """The frame with stolen river running over it (cached per frame surface)."""
    key = id(image)
    wet = _wet_cache.get(key)
    if wet is None:
        wet = image.copy()
        wet.fill((196, 232, 255), special_flags=pygame.BLEND_RGB_MULT)
        wet.fill((10, 34, 52), special_flags=pygame.BLEND_RGB_ADD)
        _wet_cache[key] = wet
    return wet


class Rooted(Performer):
    """A thief standing in the stolen river, made unshakable by the noria's strength."""

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.flooded = False          # set every frame by the guardian
        self.roots = 0.0              # 0..1: how far the water has climbed him
        self.jet: Fountain | None = None
        self.jets: list[Fountain] = []                    # the prince's fountains (beams and missiles stop at them)
        self.river_y = lambda x: self.floor - 330.0       # the sky river's underside above x (set by the guardian)
        self.plan = ""
        self.plan_time = 0.0

    # --- the ward ------------------------------------------------------------------------------------
    @property
    def warded(self) -> bool:
        return self.roots > WARD_AT and self.jet is None

    @property
    def lifted(self) -> bool:
        return self.jet is not None

    def begin_ward(self) -> None:
        self.roots = 0.0

    def ward_blow(self, world: "World", direction: int, source: str) -> None:
        # The water swallows the blow: a gout of spray, a deep thud, the prince's arm thrown back.
        x = self.body.centerx - direction * 8
        emitters.splash(world.particles, x, self.body.centery, 0.8)
        rng = world.particles.rng
        for _ in range(6):
            world.particles.spawn(x, self.body.centery, -direction * rng.uniform(60, 180), rng.uniform(-200, -60),
                                  life=0.5, kind=Kind.DOT, size=2.4, color=WATER_LIGHT, color_end=WATER, gravity=900)
        if source in ("blow", "dash"):
            shove(world, -direction * 150, -110, lock=0.12)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "water_thud")

    def break_ward(self, world: "World") -> None:
        if self.roots > 0.2:
            emitters.splash(world.particles, self.body.centerx, self.body.bottom, 1.0)
        self.roots = 0.0

    def drop_ward(self) -> None:
        self.roots = 0.0
        self.jet = None

    def update_ward(self, dt: float, world: "World") -> None:
        standing = self.flooded and self.body.on_ground and self.jet is None and self.state in ("fight", "enter")
        before = self.roots
        if standing:
            self.roots = min(1.0, self.roots + dt * ROOT_GROW)
        else:
            self.roots = max(0.0, self.roots - dt * ROOT_FADE)
        if before <= WARD_AT < self.roots:
            # The river closes over him again.
            emitters.sparkle_burst(world.particles, self.body.centerx, self.body.bottom - 10, WATER_LIGHT, 8, 70)
            world.events.emit(EventType.MACHINE_CLUNK, self.center, "rooted")
        elif before > WARD_AT >= self.roots and self.state != "defeated":
            emitters.splash(world.particles, self.body.centerx, self.body.bottom, 0.6)

    # --- lifted by a fountain -------------------------------------------------------------------------
    def lift(self, world: "World", jet: Fountain) -> bool:
        """A fountain under his feet: up he goes, out of the stolen water, kicking."""
        if not self.targetable or self.jet is not None:
            return False
        self.jet = jet
        self.roots = 0.0
        self.state = "stunned"
        self.stun_time = 99.0
        self.timer = 0.0
        self.plan = ""
        self.animator.play("flail", restart=True)
        self.on_interrupted(world)
        self.uprooted(world)
        emitters.splash(world.particles, self.body.centerx, self.body.bottom, 1.3)
        emitters.sparkle_burst(world.particles, *self.center, WATER_LIGHT, 10, 120)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "uproot")
        return True

    def uprooted(self, world: "World") -> None:
        """Whatever a fountain does to his tricks (subclasses)."""

    def hit(self, world: "World", direction: int, source: str = "blow") -> bool:
        held = self.jet is not None
        connected = super().hit(world, direction, source)
        if held and self.state == "stunned":
            self.stun_time = 99.0     # the fountain still holds him: strike again
            self.body.velocity.y -= 120
        return connected

    def update(self, dt: float, world: "World") -> None:
        jet = self.jet
        if jet is not None and self.state == "stunned" and not jet.holding:
            # The fountain sinks: he drops back into the wet, dazed.
            self.jet = None
            self.stun_time = DIZZY
            self.animator.play("stunned", restart=True)
        super().update(dt, world)
        self.update_missiles(dt, world)

    def update_missiles(self, dt: float, world: "World") -> None:
        """Advance whatever he has thrown (subclasses)."""

    def _physics(self, dt: float, world: "World", friction: bool = False) -> None:
        jet = self.jet
        if jet is not None and jet.holding and self.state != "defeated":
            body = self.body
            target = jet.crest - 2 + math.sin(self.time * 9) * 3
            body.velocity.y = (target - body.bottom) * 7
            body.velocity.x = (jet.x - body.centerx) * 5
            body.x += body.velocity.x * dt
            body.y += body.velocity.y * dt
            left, right = self.bounds
            body.x = max(left, min(right - body.width, body.x))
            if world.particles.rng.random() < dt * 20:
                emitters.droplet(world.particles, body.centerx + world.particles.rng.uniform(-8, 8), body.bottom,
                                 world.particles.rng.uniform(-80, 80), -world.particles.rng.uniform(40, 160))
            return
        super()._physics(dt, world, friction)

    # --- shared tricks ---------------------------------------------------------------------------------
    def _set_plan(self, plan: str) -> None:
        self.plan = plan
        self.plan_time = 0.0

    def keep_away(self, world: "World", near: float, far: float, speed: float, wary_speed: float) -> bool:
        """Hold a distance from the prince (further when the river has left him); True once in place."""
        player = world.player
        self.face_player(world)
        distance = self.body.centerx - player.body.centerx
        keep = far if self.exposed else near
        side = math.copysign(1, distance) if distance else 1
        ideal = player.body.centerx + side * keep
        left, right = self.bounds
        if not left + 40 < ideal < right - 40:
            ideal = player.body.centerx - side * keep
        ideal = max(left + 30, min(right - 30, ideal))
        arrived = self.walk_to(ideal, wary_speed if self.exposed else speed)
        if not arrived and self.body.on_ground and self.body.hit_wall:
            self.body.velocity.y = -600
        self.animator.play("idle" if arrived else "walk")
        return arrived

    def same_level(self, world: "World", tolerance: float = 44) -> bool:
        return abs(world.player.body.bottom - self.body.bottom) < tolerance

    def blocked_at(self, a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
        """Where a fountain column stands in the way of a->b (it stops water and missiles)."""
        best = None
        best_d = math.inf
        for jet in self.jets:
            if not jet.holding:
                continue
            clip = jet.column().clipline(a, b)
            if clip:
                d = math.hypot(clip[0][0] - a[0], clip[0][1] - a[1])
                if d < best_d:
                    best, best_d = clip[0], d
        return best

    def hand(self, front: bool = True) -> tuple[float, float]:
        animation = self.animator.current
        back, fore = art.hands(self.kind, animation, self.animator.frame_index)
        x, y = fore if front else back
        return self.body.centerx + x * self.facing, self.body.bottom + y

    def head_point(self) -> tuple[float, float]:
        hx, hy = art.head(self.kind, self.animator.current, self.animator.frame_index)
        return self.body.centerx + hx * self.facing, self.body.bottom + hy

    # --- looks ---------------------------------------------------------------------------------------
    def sprite(self) -> pygame.Surface:
        image = super().sprite()
        if self.roots > 0.05 and self.state != "defeated":
            wet = _watered(image)
            if self.roots >= 0.98:
                return wet
            blend = image.copy()
            wet = wet.copy()
            wet.set_alpha(round(255 * self.roots))
            blend.blit(wet, (0, 0))
            return blend
        return image

    def draw_ward(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.roots <= 0.05 or not self.active or self.state == "vanished":
            return
        # Two coils of river spiralling up from his feet, as high as the noria's strength has climbed.
        x, bottom = camera.to_screen(self.body.centerx, self.body.bottom)
        height = 8 + 30 * self.roots
        for strand in range(2):
            points = []
            front = []
            for k in range(14):
                h = k / 13 * height
                a = h * 0.32 - self.time * 5 + strand * math.pi
                r = 9 - h * 0.07
                px, py = x + math.sin(a) * r, bottom - h
                points.append((px, py))
                front.append(math.cos(a) > 0)
            for k in range(13):
                color = WATER_LIGHT if front[k] else WATER_DEEP
                pygame.draw.line(surface, color, points[k], points[k + 1], 3 if front[k] else 2)
            tip = points[-1]
            pygame.draw.circle(surface, WATER_LIGHT, (round(tip[0]), round(tip[1])), 2)
        if int(self.time * 7) % 3 == 0:
            a = self.time * 4
            surface.fill((255, 255, 255), (round(x + math.cos(a) * 10), round(bottom - height * 0.6 + math.sin(a * 1.3) * 6), 2, 2))

    def ward_lights(self) -> list[Light]:
        # A warm light on the thief himself, so he reads against the drowned dawn.
        lights = [Light(self.body.centerx, self.body.centery - 4, 62, (255, 246, 230), 0.7)]
        if self.roots > 0.2:
            lights.append(Light(self.body.centerx, self.body.bottom - 14, 54, WATER, 0.55 * self.roots, bloom=0.15))
        return lights

    def dissolve(self, world: "World") -> None:
        emitters.splash(world.particles, *self.center, 1.4)
        emitters.sparkle_burst(world.particles, *self.center, WATER_LIGHT, 12, 140)

    def shed(self, world: "World") -> None:
        # The stolen water he carried falls as coins: the city's money back.
        from entities.items import Coin
        from rendering import sprite_specs

        rng = world.particles.rng
        for k in range(4):
            x = self.body.centerx + (k - 1.5) * 18 + rng.uniform(-4, 4)
            floor = ground_below(world, x, self.body.top - 20)
            world.items.append(Coin((x, floor - 2), world.sprites.animations(sprite_specs.COIN)))
            emitters.sparkle_burst(world.particles, x, floor - 10, CUP, 5, 70)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "coins")


# --- Yusuf, the water-seller ------------------------------------------------------------------------
class Cup:
    """A brass drinking cup thrown like a boomerang: out, round, and home to his hand."""

    def __init__(self, x: float, y: float, direction: int) -> None:
        self.x, self.y = x, y
        self.vx = direction * 430.0
        self.vy = -70.0
        self.age = 0.0
        self.returning = False
        self.knocked = False
        self.alive = True
        self.spin = 0.0
        self.bob = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 7, round(self.y) - 6, 14, 12)

    def update(self, dt: float, world: "World", home: tuple[float, float], jets: list[Fountain]) -> None:
        self.age += dt
        self.spin += dt * 18
        player = world.player
        if self.knocked:
            self.vy += 1200 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            floor = ground_below(world, self.x, self.y - 12)
            if self.y >= floor - 4:
                self.alive = False
                emitters.splash(world.particles, self.x, floor, 0.4)
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, floor), "cup_ting")
            return
        for jet in jets:
            if jet.holding and jet.column().colliderect(self.rect()):
                # Caught in a fountain: it bobs on the crest, then tumbles out.
                self.bob += dt
                self.x += (jet.x - self.x) * min(1.0, dt * 6)
                self.y += (jet.crest - 10 - self.y) * min(1.0, dt * 6)
                if self.bob > 0.8:
                    self.knocked = True
                    self.vx, self.vy = random.choice((-90, 90)), -260
                return
        if not self.returning:
            self.vx *= max(0.0, 1.0 - dt * 1.9)
            self.vy += 140 * dt
            if self.age > 0.55 or abs(self.vx) < 90:
                self.returning = True
        else:
            dx, dy = home[0] - self.x, home[1] - self.y
            d = max(1.0, math.hypot(dx, dy))
            speed = 420.0
            self.vx += (dx / d * speed - self.vx) * min(1.0, dt * 5)
            self.vy += (dy / d * speed - self.vy) * min(1.0, dt * 5)
            if d < 16 or self.age > 3.0:
                self.alive = False      # back in his hand
                return
        self.x += self.vx * dt
        self.y += self.vy * dt
        rect = self.rect()
        if rect.colliderect(player.rect):
            strike_player(world, 1 if self.vx > 0 else -1, 220)
            self.returning = True
        attack = player.attack_rect
        if attack is not None and attack.colliderect(rect.inflate(8, 8)):
            self.knocked = True
            self.vx, self.vy = player.attack_facing * 160, -320
            emitters.sparkle_burst(world.particles, self.x, self.y, CUP_LIGHT, 8, 120)
            world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.y), "cup_ting")

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.x, self.y)
        w = max(2, round(7 * abs(math.cos(self.spin))))
        pygame.draw.ellipse(surface, OUTLINE, (x - w - 1, y - 6, w * 2 + 2, 12))
        pygame.draw.ellipse(surface, CUP, (x - w, y - 5, w * 2, 10))
        pygame.draw.line(surface, CUP_LIGHT, (x - w + 1, y - 3), (x + w - 1, y - 3), 1)
        if not self.knocked:
            blit_glow(surface, (x, y), 10, CUP_LIGHT, 0.4)
            for k in range(3):
                a = self.spin - k * 0.5
                surface.fill(WATER_LIGHT, (round(x - math.cos(a) * (8 + k * 3) * (1 if self.vx > 0 else -1)), round(y + k), 2, 2))


class WaterSeller(Rooted):
    kind = "yusuf"
    title = "Yusuf the Water-Seller"
    sheet = art.YUSUF_SHEET
    max_hp = 3
    element = WATER

    SQUEEZE = 0.55
    JET = 0.6
    JET_LENGTH = 5.5 * T

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.plan = "stroll"
        self.jet_timer = 2.4
        self.cup_timer = 4.5
        self.hop_timer = 3.0
        self.bag = 1.0            # how full the goatskin is
        self.swell = 0.0          # how hard he is squeezing it
        self.beam: tuple[tuple[float, float], tuple[float, float]] | None = None
        self.cups: list[Cup] = []
        self.landing_ring = 0.0

    def spout(self) -> tuple[float, float]:
        return self.body.centerx + self.facing * 14, self.body.bottom - 17

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.plan_time += dt
        self.swell += ((1.0 if self.plan == "squeeze" else 0.3 if self.plan == "jet" else 0.0) - self.swell) * min(1.0, dt * 8)
        if self.plan == "stroll":
            self.keep_away(world, 4.5 * T, 6.5 * T, 90, 120)
            self.jet_timer -= dt
            self.cup_timer -= dt
            self.hop_timer -= dt
            near = abs(player.body.centerx - self.body.centerx) < 1.7 * T
            if self.bag < 0.35 and self.flooded:
                self._set_plan("refill")
                self.animator.play("refill", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "refill")
            elif near and self.hop_timer <= 0 and self.body.on_ground:
                self._set_plan("hop")
                direction = 1 if player.body.centerx > self.body.centerx else -1
                self.body.velocity.update(direction * 150, -560)
                self.animator.play("hop")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "hop")
            elif self.jet_timer <= 0 and self.bag >= 0.5 and self.same_level(world):
                self._set_plan("squeeze")
                self.body.velocity.x = 0
                self.animator.play("squeeze", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "qirba_squeeze")
            elif self.cup_timer <= 0 and len(self.cups) < 2:
                self._set_plan("fling")
                self.body.velocity.x = 0
                self.animator.play("fling", restart=True)
        elif self.plan == "squeeze":
            self.body.velocity.x = 0
            self.face_player(world)
            if self.plan_time >= self.SQUEEZE:
                self._set_plan("jet")
                self.animator.play("jet")
                world.events.emit(EventType.MACHINE_CLUNK, self.spout(), "qirba_jet")
        elif self.plan == "jet":
            self.body.velocity.x = 0
            self._spray(dt, world)
            if self.plan_time >= self.JET:
                self.beam = None
                self.bag = max(0.0, self.bag - 0.5)
                self.jet_timer = 3.4
                self._set_plan("stroll")
        elif self.plan == "fling":
            self.body.velocity.x = 0
            if self.plan_time >= 0.12 and self.cup_timer <= 0:
                hx, hy = self.hand()
                self.cups.append(Cup(hx, hy, self.facing))
                self.cup_timer = 4.6
                world.events.emit(EventType.MACHINE_CLUNK, (hx, hy), "cup_throw")
            if self.plan_time >= 0.3:
                self._set_plan("stroll")
        elif self.plan == "hop":
            if self.body.velocity.y > 0 and self.animator.current != "flop":
                self.animator.play("flop")
            if self.plan_time > 0.15 and self.body.on_ground:
                self._belly_flop(world)
        elif self.plan == "refill":
            self.body.velocity.x = 0
            if self.plan_time >= 1.2:
                self.bag = 1.0
                self._set_plan("stroll")
        self._physics(dt, world, friction=self.plan not in ("stroll", "hop"))

    def _spray(self, dt: float, world: "World") -> None:
        """The goatskin's jet: a rope of water that hurls the prince away."""
        start = self.spout()
        end = (start[0] + self.facing * self.JET_LENGTH, start[1])
        x = start[0]
        step = 8 * self.facing
        collision = world.collision
        while abs(x - start[0]) < self.JET_LENGTH:
            tx, ty = collision.tile_at(x, start[1])
            if collision.get(tx, ty).name == "SOLID":
                end = (x, start[1])
                break
            x += step
        cut = self.blocked_at(start, end)
        if cut is not None:
            end = cut
            if world.particles.rng.random() < dt * 30:
                emitters.droplet(world.particles, end[0], end[1], world.particles.rng.uniform(-60, 60), -world.particles.rng.uniform(80, 200))
        self.beam = (start, end)
        if world.player.rect.inflate(-2, -4).clipline(start, end):
            strike_player(world, self.facing, 320)
        rng = world.particles.rng
        if rng.random() < dt * 40:
            world.particles.spawn(end[0], end[1], -self.facing * rng.uniform(20, 120), rng.uniform(-160, -40), life=0.4,
                                  kind=Kind.DOT, size=2.2, color=WATER_LIGHT, color_end=WATER, gravity=900)

    def _belly_flop(self, world: "World") -> None:
        self._set_plan("stroll")
        self.hop_timer = 4.2
        self.body.velocity.x = 0
        self.animator.play("land", restart=True)
        self.landing_ring = 0.45
        emitters.splash(world.particles, self.body.centerx, self.body.bottom, 1.6)
        world.events.emit(EventType.MACHINE_CLUNK, self.body.midbottom, "belly_flop")
        player = world.player
        if player.body.on_ground and abs(player.body.centerx - self.body.centerx) < 1.9 * T \
                and abs(player.body.bottom - self.body.bottom) < 20:
            strike_player(world, 1 if player.body.centerx > self.body.centerx else -1, 260)

    def uprooted(self, world: "World") -> None:
        # The fountain pulls the water out of his goatskin, too.
        if self.bag > 0:
            self.bag = 0.0
            hx, hy = self.spout()
            for _ in range(10):
                rng = world.particles.rng
                world.particles.spawn(hx, hy, rng.uniform(-40, 40), -rng.uniform(160, 320), life=0.7, kind=Kind.DOT,
                                      size=2.6, color=WATER_LIGHT, color_end=WATER, gravity=600)

    def on_interrupted(self, world: "World") -> None:
        self.beam = None
        if self.plan in ("squeeze", "jet"):
            self.jet_timer = max(self.jet_timer, 1.6)
        self.plan = "stroll"

    def silence(self, world: "World", effect) -> None:  # noqa: ANN001
        for cup in self.cups:
            cup.knocked = True
        self.beam = None

    def quench(self, world: "World", jet: Fountain) -> bool:
        return False      # cups and the jet already stop at fountains on their own

    def update_missiles(self, dt: float, world: "World") -> None:
        self.landing_ring = max(0.0, self.landing_ring - dt)
        home = self.hand()
        for cup in self.cups:
            cup.update(dt, world, home, self.jets)
        self.cups = [cup for cup in self.cups if cup.alive]

    # --- looks -------------------------------------------------------------------------------------
    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        if not self.active or self.state == "vanished":
            return
        # The goatskin slung on his back: it swells as he squeezes and sags when it is empty.
        sx, sy = camera.to_screen(self.body.centerx - self.facing * 8, self.body.bottom - 22)
        full = 0.55 + 0.45 * self.bag
        w = round(16 * full + 6 * self.swell)
        h = round(14 * full + 4 * self.swell)
        bag = pygame.Rect(0, 0, w, h)
        bag.center = (sx, sy)
        pygame.draw.ellipse(surface, OUTLINE, bag.inflate(3, 3))
        pygame.draw.ellipse(surface, LEATHER, bag)
        pygame.draw.ellipse(surface, (160, 106, 62), bag.inflate(-w // 2, -h // 2).move(-w // 6, -h // 6))
        for k in (-1, 1):
            leg = (sx - self.facing * w // 2, sy + k * h // 4)
            pygame.draw.line(surface, LEATHER_DARK, leg, (leg[0] - self.facing * 4, leg[1] + 3), 3)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state in ("fight", "enter", "hurt"):
            # The spout of the goatskin, under his front arm.
            px, py = camera.to_screen(*self.spout())
            pygame.draw.line(surface, OUTLINE, (px - self.facing * 8, py), (px, py), 5)
            pygame.draw.line(surface, LEATHER, (px - self.facing * 8, py), (px, py), 3)
            pygame.draw.circle(surface, CUP, (round(px), round(py)), 2)
        if self.beam is not None:
            start = camera.to_screen(*self.beam[0])
            end = camera.to_screen(*self.beam[1])
            fade = 1.0 - min(1.0, self.plan_time / self.JET) * 0.4
            wobble = math.sin(self.time * 40) * 1.5
            pygame.draw.line(surface, WATER_DEEP, start, (end[0], end[1] + wobble), round(9 * fade))
            pygame.draw.line(surface, WATER, start, (end[0], end[1] + wobble), round(6 * fade))
            pygame.draw.line(surface, WATER_LIGHT, (start[0], start[1] - 1), (end[0], end[1] - 1 + wobble), 2)
            for k in range(6):
                f = ((self.time * 3 + k / 6) % 1.0)
                x = start[0] + (end[0] - start[0]) * f
                surface.fill((255, 255, 255), (round(x), round(start[1] - 2 + math.sin(k + self.time * 30)), 3, 2))
            blit_glow(surface, end, 14, WATER_LIGHT, 0.6)
        for cup in self.cups:
            cup.draw(surface, camera)
        if self.landing_ring > 0:
            x, y = camera.to_screen(*self.body.midbottom)
            u = 1 - self.landing_ring / 0.45
            r = round(10 + 52 * u)
            pygame.draw.ellipse(surface, WATER_LIGHT, (x - r, y - r // 4, r * 2, r // 2), 2)

    def lights(self) -> list[Light]:
        lights = super().lights()
        if self.beam is not None:
            (sx, sy), (ex, ey) = self.beam
            lights += [Light(sx + (ex - sx) * f, sy, 50, WATER, 0.6) for f in (0.3, 0.7, 1.0)]
        return lights


# --- Nur, the net-fisher ------------------------------------------------------------------------------
class Net:
    """A weighted casting net, opening as it flies."""

    FLIGHT = 0.7

    def __init__(self, start: tuple[float, float], target: tuple[float, float]) -> None:
        self.start = start
        self.target = target
        self.age = 0.0
        self.alive = True
        self.spin = random.uniform(0, math.tau)
        self.landed = 0.0
        self.caught = False

    @property
    def u(self) -> float:
        return min(1.0, self.age / self.FLIGHT)

    def position(self) -> tuple[float, float]:
        u = self.u
        (x0, y0), (x1, y1) = self.start, self.target
        return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u - math.sin(u * math.pi) * 90

    def width(self) -> float:
        return 12 + 46 * min(1.0, self.u * 1.4)

    def rect(self) -> pygame.Rect:
        x, y = self.position()
        w = self.width()
        return pygame.Rect(round(x - w / 2), round(y - 7), round(w), 14)

    def update(self, dt: float, world: "World", jets: list[Fountain]) -> None:
        self.age += dt
        self.spin += dt * 9
        if self.u >= 1.0:
            self.landed += dt
            if self.landed > 0.6:
                self.alive = False
            return
        rect = self.rect()
        for jet in jets:
            if jet.holding and jet.column().colliderect(rect):
                # The fountain tosses it away, harmless.
                self.alive = False
                x, y = self.position()
                emitters.splash(world.particles, x, y, 0.6)
                world.events.emit(EventType.MACHINE_CLUNK, (x, y), "net_toss")
                return
        if not self.caught and rect.colliderect(world.player.rect):
            self.caught = True
            strike_player(world, 1 if self.target[0] > self.start[0] else -1, 200)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(*self.position())
        w = self.width()
        fade = 1.0 if self.landed <= 0 else max(0.0, 1 - self.landed / 0.6)
        squash = 0.28 if self.u < 1 else 0.12
        rx, ry = w / 2, w / 2 * squash
        color = (92, 70, 46) if fade > 0.5 else (130, 112, 86)
        for k in range(8):
            a = self.spin + k * math.tau / 8
            pygame.draw.line(surface, color, (x, y - ry * 0.4), (x + math.cos(a) * rx, y + math.sin(a) * ry), 1)
        for ring in (0.5, 1.0):
            rect = pygame.Rect(0, 0, max(2, round(rx * 2 * ring)), max(2, round(ry * 2 * ring)))
            rect.center = (round(x), round(y))
            pygame.draw.ellipse(surface, color, rect, 1)
        for k in range(10):
            a = self.spin + k * math.tau / 10
            pygame.draw.circle(surface, (70, 64, 70), (round(x + math.cos(a) * rx), round(y + math.sin(a) * ry)), 2)


class Fish:
    """A carp hooked out of the sky river: it falls on the prince, flops twice, and leaps home."""

    def __init__(self, x: float, top: float, floor: float, toward: int) -> None:
        self.x, self.y = x, top
        self.floor = floor
        self.vy = 60.0
        self.vx = 0.0
        self.state = "fall"
        self.time = 0.0
        self.alive = True
        self.toward = toward
        self.flops = 0
        self.kind = random.randrange(3)
        self.spin = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 13, round(self.y) - 8, 26, 14)

    def update(self, dt: float, world: "World", jets: list[Fountain]) -> None:
        self.time += dt
        player = world.player
        for jet in jets:
            if jet.holding and self.state != "home" and jet.column().colliderect(self.rect()):
                # A fountain throws the carp back up to its river.
                self.state = "home"
                self.vy = -900
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.y), "fish_home")
        if self.state == "fall":
            self.vy += 1500 * dt
            self.y += self.vy * dt
            self.spin += dt * 6
            if self.y >= self.floor - 7:
                self.y = self.floor - 7
                self._splash(world)
                self.state = "flop"
                self._hop()
        elif self.state == "flop":
            self.vy += 1500 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.spin += dt * 12 * self.toward
            if self.y >= self.floor - 7:
                self.y = self.floor - 7
                if self.flops >= 2:
                    self.state = "home"
                    self.vy = -950
                    emitters.splash(world.particles, self.x, self.floor, 0.7)
                else:
                    self._hop()
                    emitters.splash(world.particles, self.x, self.floor, 0.5)
                    world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "fish_flop")
        else:
            self.y += self.vy * dt
            self.spin += dt * 10
            if self.y < self.floor - 600:
                self.alive = False
            return
        if self.rect().colliderect(player.rect):
            strike_player(world, 1 if player.body.centerx > self.x else -1, 230)

    def _hop(self) -> None:
        self.flops += 1
        self.vy = -420
        self.vx = self.toward * 150

    def _splash(self, world: "World") -> None:
        emitters.splash(world.particles, self.x, self.floor, 1.2)
        world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "fish_splash")
        player = world.player
        if abs(player.body.centerx - self.x) < 26 and abs(player.body.bottom - self.floor) < 40:
            strike_player(world, 1 if player.body.centerx > self.x else -1, 240)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state == "fall":
            # Its shadow on the water, growing as it falls.
            fx, fy = camera.to_screen(self.x, self.floor)
            u = max(0.0, min(1.0, 1 - (self.floor - self.y) / 380))
            r = round(8 + 16 * u)
            pygame.draw.ellipse(surface, WATER_DEEP, (fx - r, fy - 3, r * 2, 6), 2)
            pygame.draw.ellipse(surface, WATER_LIGHT, (fx - r // 2, fy - 2, r, 4), 1)
        x, y = camera.to_screen(self.x, self.y)
        image = pygame.transform.scale2x(noria.fish_image(self.kind, int(self.time * 14) % 4))
        if self.toward < 0:
            image = pygame.transform.flip(image, True, False)
        angle = -90 if self.state == "fall" else (90 if self.state == "home" else math.degrees(math.sin(self.spin)) * 0.4)
        rotated = pygame.transform.rotate(image, angle * (1 if self.toward > 0 else -1))
        surface.blit(rotated, rotated.get_rect(center=(x, y)))
        blit_glow(surface, (x, y), 18, (255, 220, 140), 0.35)


class NetFisher(Rooted):
    kind = "nur"
    title = "Nur the Net-Fisher"
    sheet = art.NUR_SHEET
    max_hp = 4
    element = (120, 222, 210)

    TWIRL = 0.5
    ANGLE = 1.0
    PLANT = 0.2
    VAULT = 0.8

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.plan = "wade"
        self.net_timer = 2.6
        self.fish_timer = 5.5
        self.vault_timer = 3.5
        self.nets: list[Net] = []
        self.fish: list[Fish] = []
        self.vault_from = (x, floor)
        self.vault_to = (x, floor)
        self.struck = False

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.plan_time += dt
        if self.plan == "wade":
            self.keep_away(world, 5 * T, 7 * T, 110, 140)
            self.net_timer -= dt
            self.fish_timer -= dt
            self.vault_timer -= dt
            near = abs(player.body.centerx - self.body.centerx) < 2.3 * T
            if near and self.vault_timer <= 0 and self.body.on_ground:
                self._set_plan("plant")
                self.body.velocity.x = 0
                self.animator.play("plant", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "spear_plant")
            elif self.net_timer <= 0 and self.same_level(world, 60):
                self._set_plan("twirl")
                self.body.velocity.x = 0
                self.animator.play("twirl")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "net_twirl")
            elif self.fish_timer <= 0:
                self._set_plan("angle")
                self.body.velocity.x = 0
                self.animator.play("angle")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "line_cast")
        elif self.plan == "twirl":
            self.body.velocity.x = 0
            self.face_player(world)
            if self.plan_time >= self.TWIRL:
                hx, hy = self.hand()
                target = (player.body.centerx + player.body.velocity.x * 0.3, player.body.bottom - 8)
                self.nets.append(Net((hx, hy - 6), target))
                self.net_timer = 3.6
                self._set_plan("cast")
                self.animator.play("cast", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, (hx, hy), "net_cast")
        elif self.plan == "cast":
            self.body.velocity.x = 0
            if self.plan_time >= 0.3:
                self._set_plan("wade")
        elif self.plan == "angle":
            self.body.velocity.x = 0
            if self.plan_time >= self.ANGLE:
                x = max(self.bounds[0] + 20, min(self.bounds[1] - 20, player.body.centerx))
                toward = 1 if player.body.centerx > self.body.centerx else -1
                self.fish.append(Fish(x, self.river_y(x), ground_below(world, x, self.floor - 3 * T), toward))
                self.fish_timer = 7.0
                self._set_plan("reel")
                self.animator.play("reel", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "line_yank")
        elif self.plan == "reel":
            self.body.velocity.x = 0
            if self.plan_time >= 0.3:
                self._set_plan("wade")
        elif self.plan == "plant":
            self.body.velocity.x = 0
            if self.plan_time >= self.PLANT:
                side = 1 if player.body.centerx > self.body.centerx else -1
                left, right = self.bounds
                land = player.body.centerx + side * 2.6 * T
                if not left + 30 < land < right - 30:
                    land = player.body.centerx - side * 2.6 * T
                land = max(left + 30, min(right - 30, land))
                self.vault_from = self.body.midbottom
                self.vault_to = (land, ground_below(world, land, self.floor - 3 * T))
                self.facing = 1 if land > self.body.centerx else -1
                self.struck = False
                self._set_plan("vault")
                self.animator.play("vault")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "vault")
        elif self.plan == "vault":
            self._vault(world)
            return
        elif self.plan == "strike":
            if self.plan_time > 0.35:
                self._set_plan("wade")
        self._physics(dt, world, friction=self.plan != "wade")

    def _vault(self, world: "World") -> None:
        """Over the prince on her spear, stabbing down at the top of the arc."""
        u = min(1.0, self.plan_time / self.VAULT)
        (x0, y0), (x1, y1) = self.vault_from, self.vault_to
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u - math.sin(u * math.pi) * 112
        self.body.place_midbottom((x, y))
        self.body.velocity.update(0, 0)
        self.body.on_ground = u >= 1.0
        player = world.player
        if 0.4 < u < 0.75 and not self.struck:
            if self.animator.current != "strike":
                self.animator.play("strike", restart=True)
            tip = (self.body.centerx, self.body.bottom + 22)
            if player.rect.inflate(8, 0).collidepoint(tip) or player.rect.clipline(self.body.midbottom, tip):
                self.struck = True
                strike_player(world, self.facing, 240)
        if u >= 1.0:
            self.vault_timer = 6.5
            self.body.on_ground = True
            self._set_plan("strike")
            self.animator.play("land", restart=True)
            emitters.splash(world.particles, self.body.centerx, self.body.bottom, 0.9)
            world.events.emit(EventType.MACHINE_CLUNK, self.body.midbottom, "land")

    def on_interrupted(self, world: "World") -> None:
        if self.plan == "vault":
            # Knocked off her spear in the air: she drops where she is.
            self.vault_timer = 5.0
        self.plan = "wade"

    def silence(self, world: "World", effect) -> None:  # noqa: ANN001
        self.nets = []
        for fish in self.fish:
            fish.state = "home"
            fish.vy = -900

    def update_missiles(self, dt: float, world: "World") -> None:
        for net in self.nets:
            net.update(dt, world, self.jets)
        self.nets = [net for net in self.nets if net.alive]
        for fish in self.fish:
            fish.update(dt, world, self.jets)
        self.fish = [fish for fish in self.fish if fish.alive]

    # --- looks -------------------------------------------------------------------------------------
    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        for net in self.nets:
            if net.landed > 0:
                net.draw(surface, camera)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        f = self.facing
        anim = self.animator.current
        if self.state in ("fight", "enter", "hurt", "stunned") and self.plan not in ("vault", "twirl", "angle", "reel"):
            # A fishing spear in her back hand, the rolled net at her hip.
            bx, by = camera.to_screen(*self.hand(front=False))
            top, bottom = (bx + f * 3, by - 26), (bx - f * 2, by + 18)
            pygame.draw.line(surface, OUTLINE, bottom, top, 4)
            pygame.draw.line(surface, (176, 130, 84), bottom, top, 2)
            for k in (-4, 0, 4):
                pygame.draw.line(surface, (200, 206, 214), (top[0] + k * 0.6, top[1]), (top[0] + k, top[1] - 7), 1)
            nx, ny = camera.to_screen(*self.hand())
            pygame.draw.ellipse(surface, OUTLINE, (nx - 6, ny - 3, 12, 8))
            pygame.draw.ellipse(surface, (214, 200, 150), (nx - 5, ny - 2, 10, 6))
        if self.plan == "twirl":
            hx, hy = camera.to_screen(*self.hand())
            r = 18
            for k in range(8):
                a = self.time * 16 + k * math.tau / 8
                pygame.draw.line(surface, (92, 70, 46), (hx, hy), (hx + math.cos(a) * r, hy - 4 + math.sin(a) * 5), 1)
                pygame.draw.circle(surface, (70, 64, 70), (round(hx + math.cos(a) * r), round(hy - 4 + math.sin(a) * 5)), 2)
        if self.plan in ("angle", "reel"):
            # The rod up into the sky, and a glinting line to the river.
            hx, hy = camera.to_screen(*self.hand())
            tip = (hx + f * 10, hy - 30)
            pygame.draw.line(surface, OUTLINE, (hx, hy), tip, 4)
            pygame.draw.line(surface, (176, 130, 84), (hx, hy), tip, 2)
            river = camera.to_screen(self.body.centerx, self.river_y(self.body.centerx))
            slack = 6 * math.sin(self.time * 3) if self.plan == "angle" else 0
            pygame.draw.line(surface, (236, 240, 250), tip, (river[0] + slack, river[1]), 1)
            if int(self.time * 10) % 2 == 0:
                blit_glow(surface, (river[0] + slack, river[1]), 10, WATER_LIGHT, 0.7)
        if self.plan in ("vault", "plant"):
            hx, hy = camera.to_screen(*self.hand())
            ground = camera.to_screen(self.vault_from[0] if self.plan == "vault" else self.body.centerx + f * 18,
                                      self.vault_from[1] if self.plan == "vault" else self.body.bottom)
            if self.plan == "plant" or self.plan_time / self.VAULT < 0.5:
                pygame.draw.line(surface, OUTLINE, (hx, hy), ground, 4)
                pygame.draw.line(surface, (176, 130, 84), (hx, hy), ground, 2)
            elif anim == "strike":
                tip = (hx, hy + 26)
                pygame.draw.line(surface, OUTLINE, (hx, hy - 10), tip, 4)
                pygame.draw.line(surface, (200, 206, 214), (hx, hy - 10), tip, 2)
        for net in self.nets:
            if net.landed <= 0:
                net.draw(surface, camera)
        for fish in self.fish:
            fish.draw(surface, camera)


# --- Hamida, the rain-caller --------------------------------------------------------------------------
class RainSpear:
    """A spear of rain called down from the river: a ring on the water first, then the strike."""

    FALL = 0.22

    def __init__(self, x: float, top: float, floor: float, delay: float) -> None:
        self.x, self.top, self.floor = x, top, floor
        self.delay = delay
        self.age = 0.0
        self.alive = True
        self.struck = False

    def update(self, dt: float, world: "World", jets: list[Fountain]) -> None:
        self.age += dt
        if self.age < self.delay:
            return
        u = (self.age - self.delay) / self.FALL
        y = self.top + (self.floor - self.top) * min(1.0, u)
        for jet in jets:
            if jet.holding and jet.column().collidepoint(self.x, y):
                # It shatters on the fountain's crest.
                self.alive = False
                emitters.splash(world.particles, self.x, jet.crest, 0.6)
                return
        if not self.struck and u >= 0.6:
            player = world.player
            if abs(player.body.centerx - self.x) < 16 and player.body.top < self.floor and player.body.bottom > y - 40:
                self.struck = True
                strike_player(world, 1 if player.body.centerx > self.x else -1, 220)
        if u >= 1.0 and not self.struck:
            self.struck = True
            emitters.splash(world.particles, self.x, self.floor, 0.9)
            world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "rain_spear")
        if u >= 1.3:
            self.alive = False

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        fx, fy = camera.to_screen(self.x, self.floor)
        if self.age < self.delay:
            u = self.age / self.delay
            r = round(18 - 10 * u)
            pygame.draw.ellipse(surface, WATER_LIGHT, (fx - r, fy - r // 4 - 1, r * 2, max(2, r // 2)), 2)
            pygame.draw.ellipse(surface, WATER, (fx - r * 2, fy - r // 2 - 1, r * 4, max(2, r)), 1)
            return
        u = min(1.0, (self.age - self.delay) / self.FALL)
        y = self.top + (self.floor - self.top) * u
        sx, sy = camera.to_screen(self.x, y)
        tail = camera.to_screen(self.x, max(self.top, y - 90))
        pygame.draw.line(surface, WATER, tail, (sx, sy), 4)
        pygame.draw.line(surface, WATER_LIGHT, tail, (sx, sy), 2)
        blit_glow(surface, (sx, sy), 12, WATER_LIGHT, 0.8)


class RainBead:
    def __init__(self, x: float, y: float, vx: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, 40.0
        self.alive = True

    def update(self, dt: float, world: "World") -> None:
        self.vy += 900 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        floor = ground_below(world, self.x, self.y - 10)
        if self.y >= floor - 3:
            self.alive = False
            emitters.splash(world.particles, self.x, floor, 0.5)
        elif pygame.Rect(round(self.x) - 4, round(self.y) - 5, 8, 10).colliderect(world.player.rect):
            self.alive = False
            strike_player(world, 1 if self.vx > 0 else -1, 180)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.x, self.y)
        pygame.draw.polygon(surface, WATER_DEEP, [(x, y - 6), (x + 4, y + 1), (x, y + 4), (x - 4, y + 1)])
        pygame.draw.polygon(surface, WATER_LIGHT, [(x, y - 4), (x + 2, y + 1), (x, y + 2), (x - 2, y + 1)])


class RainCaller(Rooted):
    kind = "hamida"
    title = "Hamida the Rain-Caller"
    sheet = art.HAMIDA_SHEET
    max_hp = 5
    element = (156, 176, 255)

    RAISE = 0.9
    SPIN = 1.0

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.plan = "drift"
        self.rain_timer = 2.6
        self.glide_timer = 6.0
        self.spin_timer = 2.0
        self.spears: list[RainSpear] = []
        self.beads: list[RainBead] = []
        self.bead_timer = 0.0
        self.open = 0.0          # 0 furled .. 1 the parasol wide open

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.plan_time += dt
        target_open = 1.0 if self.plan in ("raise", "glide", "spin") else 0.0
        self.open += (target_open - self.open) * min(1.0, dt * 10)
        if self.plan == "drift":
            self.keep_away(world, 5.5 * T, 7.5 * T, 70, 110)
            self.rain_timer -= dt
            self.glide_timer -= dt
            self.spin_timer -= dt
            near = abs(player.body.centerx - self.body.centerx) < 1.8 * T
            if near and self.spin_timer <= 0 and self.warded:
                # Only while the river holds her: caught out of it, she hobbles away instead.
                self._set_plan("spin")
                self.body.velocity.x = 0
                self.animator.play("spin")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "parasol_spin")
            elif self.glide_timer <= 0 and self.body.on_ground:
                self._set_plan("glide")
                self.body.velocity.update(0, -780)
                self.animator.play("glide")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "parasol_open")
            elif self.rain_timer <= 0:
                self._call_rain(world)
        elif self.plan == "raise":
            self.body.velocity.x = 0
            if self.plan_time >= self.RAISE + 0.3:
                self._set_plan("drift")
        elif self.plan == "glide":
            self._glide(dt, world)
            return
        elif self.plan == "spin":
            self.body.velocity.x = 0
            self.face_player(world)
            if abs(player.body.centerx - self.body.centerx) < 40 and self.same_level(world, 40):
                direction = 1 if player.body.centerx > self.body.centerx else -1
                if shove(world, direction * 320, -220):
                    world.events.emit(EventType.MACHINE_CLUNK, self.center, "parasol_push")
            if world.particles.rng.random() < dt * 30:
                hx, hy = self.hand()
                a = world.particles.rng.uniform(0, math.tau)
                emitters.droplet(world.particles, hx + math.cos(a) * 20, hy - 6, math.cos(a) * 160, -40)
            if self.plan_time >= self.SPIN:
                self.spin_timer = 3.5
                self._set_plan("drift")
        self._physics(dt, world, friction=self.plan != "drift")

    def _call_rain(self, world: "World") -> None:
        """Rings on the water where the river will strike: one under the prince, the rest around."""
        self._set_plan("raise")
        self.body.velocity.x = 0
        self.animator.play("raise")
        player = world.player
        left, right = self.bounds
        xs = [player.body.centerx]
        rng = world.particles.rng
        offsets = [2.4 * T, -2.4 * T, 4.8 * T, -4.8 * T]
        rng.shuffle(offsets)
        for offset in offsets[:3]:
            xs.append(player.body.centerx + offset + rng.uniform(-10, 10))
        for k, x in enumerate(xs):
            if left + 10 < x < right - 10:
                floor = ground_below(world, x, self.floor - 3 * T)
                self.spears.append(RainSpear(x, self.river_y(x), floor, self.RAISE + k * 0.08))
        self.rain_timer = 3.4
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "rain_call")

    def _glide(self, dt: float, world: "World") -> None:
        """Up on a gust from the river, then down under the parasol, scattering drops."""
        body = self.body
        player = world.player
        if body.velocity.y > 0:
            body.velocity.y = min(body.velocity.y, 70.0)
            toward = 1 if player.body.centerx > body.centerx else -1
            body.velocity.x += (toward * 80 - body.velocity.x) * min(1.0, dt * 2)
            self.bead_timer -= dt
            if self.bead_timer <= 0:
                self.bead_timer = 0.55
                hx, hy = self.hand()
                self.beads.append(RainBead(body.centerx + world.particles.rng.uniform(-14, 14), hy - 14, body.velocity.x * 0.5))
        self._physics(dt, world)
        if self.plan_time > 0.3 and body.on_ground:
            self.glide_timer = 8.5
            self._set_plan("drift")
            self.animator.play("land", restart=True)
            emitters.splash(world.particles, body.centerx, body.bottom, 0.8)
            world.events.emit(EventType.MACHINE_CLUNK, body.midbottom, "land")

    def on_interrupted(self, world: "World") -> None:
        if self.plan == "glide":
            self.glide_timer = 6.0
        self.plan = "drift"

    def silence(self, world: "World", effect) -> None:  # noqa: ANN001
        self.spears = []
        self.beads = []

    def update_missiles(self, dt: float, world: "World") -> None:
        if self.plan not in ("raise", "glide", "spin"):
            self.open = max(0.0, self.open - dt * 6)
        for spear in self.spears:
            spear.update(dt, world, self.jets)
        self.spears = [spear for spear in self.spears if spear.alive]
        for bead in self.beads:
            bead.update(dt, world)
        self.beads = [bead for bead in self.beads if bead.alive]

    # --- looks -------------------------------------------------------------------------------------
    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        for spear in self.spears:
            if spear.age < spear.delay:
                spear.draw(surface, camera)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        hx, hy = camera.to_screen(*self.hand())
        f = self.facing
        if self.active and self.state != "defeated":
            if self.open < 0.2:
                # The furled parasol, used as a cane.
                tip = (hx + f * 4, camera.to_screen(0, self.body.bottom)[1])
                top = (hx - f * 2, hy - 14)
                pygame.draw.line(surface, OUTLINE, tip, top, 5)
                pygame.draw.line(surface, (60, 170, 176), tip, top, 3)
                pygame.draw.circle(surface, CUP, (round(top[0]), round(top[1]) - 2), 3)
            else:
                self._draw_parasol(surface, (hx, hy))
            # Her string of bells, chiming in the other hand.
            bx, by = camera.to_screen(*self.hand(front=False))
            for k in range(3):
                swing = math.sin(self.time * (9 if self.plan == "raise" else 2) + k) * 2
                pygame.draw.circle(surface, OUTLINE, (round(bx + swing), round(by + 3 + k * 4)), 3)
                pygame.draw.circle(surface, CUP, (round(bx + swing), round(by + 3 + k * 4)), 2)
        for spear in self.spears:
            if spear.age >= spear.delay:
                spear.draw(surface, camera)
        for bead in self.beads:
            bead.draw(surface, camera)

    def _draw_parasol(self, surface: pygame.Surface, hand: tuple[float, float]) -> None:
        """A shamsiyya of turquoise and white, its ribs turning when she spins it."""
        hx, hy = hand
        r = 8 + 16 * self.open
        spin = self.time * (14 if self.plan == "spin" else 2)
        if self.plan == "spin":
            cx, cy = hx + self.facing * 10, hy - 4
            rect = pygame.Rect(0, 0, round(r * 0.7), round(r * 2))
            rect.center = (round(cx), round(cy))
            pygame.draw.ellipse(surface, OUTLINE, rect.inflate(4, 4))
            pygame.draw.ellipse(surface, (60, 186, 190), rect)
            for k in range(6):
                a = spin + k * math.tau / 6
                y = cy + math.sin(a) * r
                if math.cos(a) > 0:
                    pygame.draw.line(surface, (240, 244, 250), (cx, cy), (cx, y), 2)
            return
        cx, cy = hx, hy - 30
        pygame.draw.line(surface, OUTLINE, (hx, hy), (cx, cy - r * 0.2), 3)
        canopy = []
        for k in range(13):
            a = math.pi + k / 12 * math.pi
            canopy.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.6))
        pygame.draw.polygon(surface, OUTLINE, [(x, y - 1) for x, y in canopy] + [(cx + r, cy + 2), (cx - r, cy + 2)])
        pygame.draw.polygon(surface, (60, 186, 190), canopy + [(cx + r, cy), (cx - r, cy)])
        for k in range(6):
            a = math.pi + (k + 0.5) / 6 * math.pi + math.sin(spin) * 0.05
            if k % 2 == 0:
                pts = [(cx, cy - r * 0.6 + 2), (cx + math.cos(a - 0.26) * r, cy + math.sin(a - 0.26) * r * 0.6),
                       (cx + math.cos(a + 0.26) * r, cy + math.sin(a + 0.26) * r * 0.6)]
                pygame.draw.polygon(surface, (238, 242, 250), pts)
        for k in range(7):
            x = cx - r + k * r / 3
            pygame.draw.circle(surface, CUP, (round(x), round(cy + 2)), 2)
        pygame.draw.circle(surface, CUP, (round(cx), round(cy - r * 0.6 - 2)), 3)

    def lights(self) -> list[Light]:
        lights = super().lights()
        for spear in self.spears:
            if spear.age >= spear.delay:
                lights.append(Light(spear.x, spear.floor - 30, 60, WATER, 0.7))
        return lights
