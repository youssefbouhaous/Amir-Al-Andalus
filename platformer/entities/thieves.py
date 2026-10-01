"""The Gilded Thieves: al-Muqallid's cutpurses on the rooftops of the Amber Market.

They are people like Amir, each with a thief's trick turned into a weapon,
and each gilded by the setting sun that their Elephant Clock holds in its
trunk: while a beam of that stolen sunlight rests on a thief, he is gold from
turban to boots and blows ring off him. Out of the light - in the prince's
shadow, behind the ink of the Night Qalam, or when he moves faster than the
elephant can turn its beam - he is flesh again.

* ``MirrorThief`` (Tariq) catches the sun in a brass mirror and throws it
  back as a burning lance; he vanishes in a glint when cornered. His mirror
  is dark whenever his own beam is cut.
* ``FireEater`` (Samira) breathes fire, whirls fire poi, and kicks embers
  that burn on the tiles.
* ``SnakeCharmer`` (Hakim) plays his gourd flute to raise brass cobras from
  his baskets, and escapes through one basket to pop out of another.
"""

import math
import random
from functools import lru_cache
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import Color
from entities.performer import Performer, strike_player
from jazari.base import ground_below, shove
from rendering import emitters
from rendering.art import thieves as art
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from rendering.sprite_library import SpriteLibrary

if TYPE_CHECKING:
    from world.world import World

T = 32
GOLD: Color = (255, 206, 96)
GOLD_LIGHT: Color = (255, 244, 190)
SUNLIGHT: Color = (255, 196, 110)
FIRE: Color = (255, 150, 50)
FIRE_HOT: Color = (255, 236, 150)
EMBER: Color = (255, 110, 40)
INK: Color = (22, 18, 44)
INK_EDGE: Color = (120, 96, 220)
BLINDED = 1.8     # seconds a thief rubs the night-ink from his eyes
INKED = 6.0       # seconds the ink keeps the sun off his skin


# --- tinted sprites ---------------------------------------------------------------------------------
_gold_cache: dict[int, pygame.Surface] = {}
_ink_cache: dict[int, pygame.Surface] = {}


def _gilded(image: pygame.Surface) -> pygame.Surface:
    """The same frame cast in gold (cached per frame surface)."""
    key = id(image)
    gold = _gold_cache.get(key)
    if gold is None:
        gold = image.copy()
        grey = pygame.transform.grayscale(gold)
        grey.fill((255, 214, 120), special_flags=pygame.BLEND_RGB_MULT)
        grey.fill((70, 44, 0), special_flags=pygame.BLEND_RGB_ADD)
        gold = grey
        _gold_cache[key] = gold
    return gold


def _inked(image: pygame.Surface, seed: int) -> pygame.Surface:
    """Splotches of night-ink over the frame, following its silhouette."""
    key = id(image) * 7 + seed
    inked = _ink_cache.get(key)
    if inked is None:
        w, h = image.get_size()
        blots = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(seed)
        for _ in range(5):
            x, y = rng.uniform(w * 0.32, w * 0.68), rng.uniform(h * 0.3, h * 0.92)
            r = rng.uniform(1.8, 3.6)
            pygame.draw.circle(blots, (*INK, 255), (round(x), round(y)), round(r))
            pygame.draw.line(blots, (*INK, 255), (round(x), round(y)), (round(x + rng.uniform(-1, 1)), round(y + r + rng.uniform(2, 6))), 2)
        mask = image.copy()
        mask.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        blots.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        inked = image.copy()
        inked.blit(blots, (0, 0))
        _ink_cache[key] = inked
    return inked


@lru_cache(maxsize=None)
def _halo() -> pygame.Surface:
    """A gold nimbus, as behind the heads of kings in the painted books."""
    size = 34
    halo = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*GOLD, 70), (size // 2, size // 2), 15)
    pygame.draw.circle(halo, (*GOLD_LIGHT, 200), (size // 2, size // 2), 15, 2)
    for k in range(16):
        a = k * math.tau / 16
        pygame.draw.line(halo, (*GOLD, 150), (size / 2 + math.cos(a) * 9, size / 2 + math.sin(a) * 9),
                         (size / 2 + math.cos(a) * 14, size / 2 + math.sin(a) * 14), 1)
    return halo


class _Loot:
    """A stolen coin flung from a beaten thief; it lands as a real coin."""

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.spin = random.uniform(0, math.tau)
        self.alive = True


# --- the gilded ward ------------------------------------------------------------------------------------
class Gilded(Performer):
    """A thief made gold by the stolen sun's beam."""

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.lit = False           # the guardian sets this every frame from the beam
        self.gild = 0.0            # 0..1, how gold he looks
        self.blot = 0.0            # seconds of night-ink left on his skin
        self.blot_seed = random.randrange(1000)
        self.loot: list[_Loot] = []
        self.jump_timer = 0.0

    @property
    def warded(self) -> bool:
        return self.lit and self.blot <= 0

    @property
    def chest(self) -> tuple[float, float]:
        return self.body.centerx, self.body.top + 10

    def begin_ward(self) -> None:
        self.gild = 0.0
        self.blot = 0.0

    def ward_blow(self, world: "World", direction: int, source: str) -> None:
        # The blade rings off gold: sparks, a bright note, and the prince's arm jarred back.
        x = self.body.centerx - direction * 8
        emitters.sparkle_burst(world.particles, x, self.body.top + 12, GOLD, 10, 160)
        for _ in range(6):
            rng = world.particles.rng
            world.particles.spawn(x, self.body.top + 12, -direction * rng.uniform(80, 200), rng.uniform(-160, -20),
                                  life=0.35, kind=Kind.SPARK, size=6, color=GOLD_LIGHT, color_end=GOLD, gravity=500)
        if source in ("blow", "dash"):
            shove(world, -direction * 150, -120, lock=0.12)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "clang")

    def drop_ward(self) -> None:
        self.lit = False
        self.gild = 0.0

    def inked(self, world: "World", seconds: float = INKED) -> None:
        """Night-ink across him: the sun can't reach his skin, and he's blinded for a moment."""
        if not self.targetable:
            return
        fresh = self.blot <= 0
        self.blot = max(self.blot, seconds)
        self.blot_seed = random.randrange(1000) if fresh else self.blot_seed
        self.stun(world, BLINDED)
        rng = world.particles.rng
        for _ in range(16):
            world.particles.spawn(self.body.centerx, self.body.top + 10, rng.uniform(-160, 160), rng.uniform(-200, 40),
                                  life=rng.uniform(0.4, 0.8), kind=Kind.DOT, size=rng.uniform(1.6, 3.0), color=INK,
                                  color_end=INK_EDGE, gravity=700)
        for _ in range(6):
            world.particles.spawn(self.body.centerx + rng.uniform(-10, 10), self.body.top + rng.uniform(0, 24), 0, -30,
                                  life=0.7, kind=Kind.TWINKLE, size=3, color=(255, 255, 255), color_end=INK_EDGE)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "ink_splat")

    def update_ward(self, dt: float, world: "World") -> None:
        self.blot = max(0.0, self.blot - dt)
        target = 1.0 if self.warded else 0.0
        before = self.gild
        self.gild += (target - self.gild) * min(1.0, dt * 9)
        if before < 0.5 <= self.gild:
            emitters.sparkle_burst(world.particles, *self.center, GOLD_LIGHT, 8, 90)

    def update(self, dt: float, world: "World") -> None:
        self._update_loot(dt, world)
        super().update(dt, world)

    def shed(self, world: "World") -> None:
        # His purse bursts: the market's gold comes back as coins.
        rng = world.particles.rng
        for k in range(5):
            self.loot.append(_Loot(self.body.centerx, self.body.top + 8, rng.uniform(-150, 150), rng.uniform(-420, -260)))
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "coins")

    def _update_loot(self, dt: float, world: "World") -> None:
        if not self.loot:
            return
        from entities.items import Coin
        from rendering import sprite_specs

        for coin in self.loot:
            coin.vy += 1100 * dt
            coin.x += coin.vx * dt
            coin.y += coin.vy * dt
            coin.spin += dt * 14
            floor = ground_below(world, coin.x, coin.y - 12)
            if coin.vy > 0 and coin.y >= floor - 8:
                coin.alive = False
                world.items.append(Coin((coin.x, floor - 2), world.sprites.animations(sprite_specs.COIN)))
                emitters.sparkle_burst(world.particles, coin.x, floor - 8, GOLD, 5, 70)
        self.loot = [coin for coin in self.loot if coin.alive]

    # --- movement across the rooftop terrace ----------------------------------------------------------
    def walk_to(self, target_x: float, speed: float) -> bool:
        arrived = super().walk_to(target_x, speed)
        # Hop up onto (or across) a terrace in the way.
        if not arrived and self.body.on_ground and self.body.hit_wall and not self.floats:
            self.body.velocity.y = -640
        return arrived

    # --- looks ----------------------------------------------------------------------------------------
    def sprite(self) -> pygame.Surface:
        image = super().sprite()
        if self.blot > 0 and self.state != "defeated":
            image = _inked(image, self.blot_seed)
        if self.gild > 0.02:
            gold = _gilded(image)
            if self.gild >= 0.98:
                return gold
            blend = image.copy()
            gold = gold.copy()
            gold.set_alpha(round(255 * self.gild))
            blend.blit(gold, (0, 0))
            return blend
        return image

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.gild > 0.1 and self.active and self.state != "vanished":
            x, y = camera.to_screen(self.body.centerx - self.facing * 2, self.body.top - 4)
            halo = _halo()
            if self.gild < 1:
                halo = halo.copy()
                halo.set_alpha(round(255 * self.gild))
            surface.blit(halo, halo.get_rect(center=(x, y)))
        for coin in self.loot:
            x, y = camera.to_screen(coin.x, coin.y)
            w = max(1, round(5 * abs(math.cos(coin.spin))))
            pygame.draw.ellipse(surface, (140, 90, 20), (x - w - 1, y - 6, w * 2 + 2, 12))
            pygame.draw.ellipse(surface, GOLD, (x - w, y - 5, w * 2, 10))

    def draw_ward(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.gild > 0.6:
            # A glint of light sliding down the gold.
            x, y = camera.to_screen(self.body.centerx, self.body.top)
            u = (self.time * 0.8) % 1.6
            if u < 1:
                blit_glow(surface, (x + (u - 0.5) * 10, y + 4 + u * 26), 8, GOLD_LIGHT, 0.7)
        if self.blot > 0 and self.state != "defeated":
            x, y = camera.to_screen(self.body.centerx, self.body.top)
            for k in range(4):
                a = self.time * 3 + k * 1.7
                sx, sy = x + math.cos(a) * 7, y + 10 + math.sin(a * 1.3) * 10
                if int(self.time * 6 + k) % 3 == 0:
                    surface.fill((255, 255, 255), (round(sx), round(sy), 1, 1))

    def ward_lights(self) -> list[Light]:
        if self.gild > 0.2:
            return [Light(*self.center, 52, SUNLIGHT, 0.6 * self.gild, bloom=0.2 * self.gild)]
        return []

    def dissolve(self, world: "World") -> None:
        emitters.sparkle_burst(world.particles, *self.center, GOLD, 12, 130)
        emitters.smoke_poof(world.particles, *self.center, (120, 110, 130), 10)


# --- Tariq, the mirror-thief ---------------------------------------------------------------------------------
class MirrorThief(Gilded):
    kind = "tariq"
    title = "Tariq the Mirror-Thief"
    sheet = art.TARIQ_SHEET
    max_hp = 3
    element = SUNLIGHT

    RAISE = 0.28
    AIM = 0.6
    LOCK = 0.22
    FIRE = 0.36

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.plan = "stalk"
        self.plan_time = 0.0
        self.lance_timer = 2.2
        self.glint_timer = 0.0
        self.aim = (x, floor)
        self.lance: tuple[tuple[float, float], tuple[float, float]] | None = None
        self.mirror_angle = 0.0
        self.fizzle = 0.0

    def mirror_point(self) -> tuple[float, float]:
        animation = self.animator.current if self.animator.current in art.TARIQ_ANIMS else "idle"
        _, front = art.hands("tariq", animation, self.animator.frame_index)
        return self.body.centerx + front[0] * self.facing, self.body.bottom + front[1]

    def _set_plan(self, plan: str) -> None:
        self.plan = plan
        self.plan_time = 0.0

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.plan_time += dt
        self.glint_timer = max(0.0, self.glint_timer - dt)
        self.fizzle = max(0.0, self.fizzle - dt)
        if self.plan == "stalk":
            self.face_player(world)
            distance = self.body.centerx - player.body.centerx
            keep = 6 * T if self.exposed else 4.5 * T
            ideal = player.body.centerx + math.copysign(keep, distance if distance else 1)
            left, right = self.bounds
            if not left + 40 < ideal < right - 40:
                ideal = player.body.centerx - math.copysign(keep, distance if distance else 1)
            arrived = self.walk_to(ideal, 120 if self.exposed else 80)
            self.animator.play("idle" if arrived else "walk")
            self.lance_timer -= dt
            if abs(distance) < 64 and self.glint_timer <= 0 and abs(player.body.bottom - self.body.bottom) < 48:
                self._glint_step(world)
            elif self.lance_timer <= 0:
                self._set_plan("raise")
                self.body.velocity.x = 0
                self.animator.play("raise", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "beam_charge")
        elif self.plan == "raise":
            self.body.velocity.x = 0
            if self.plan_time >= self.RAISE:
                if not self.lit:
                    # No sun on his mirror: nothing to throw.
                    self.fizzle = 0.6
                    self.lance_timer = 1.4
                    self._set_plan("stalk")
                    world.events.emit(EventType.MACHINE_CLUNK, self.center, "fizzle")
                else:
                    self._set_plan("aim")
                    self.animator.play("aim")
        elif self.plan == "aim":
            self.body.velocity.x = 0
            self.face_player(world)
            if self.plan_time < self.AIM:
                self.aim = (player.body.centerx, player.body.centery)
            if self.plan_time >= self.AIM + self.LOCK:
                if not self.lit:
                    self.fizzle = 0.6
                    self.lance_timer = 1.4
                    self._set_plan("stalk")
                    world.events.emit(EventType.MACHINE_CLUNK, self.center, "fizzle")
                else:
                    self._fire(world)
        elif self.plan == "fire":
            self.body.velocity.x = 0
            if self.lance is not None and self.plan_time < self.FIRE:
                start, end = self.lance
                if _segment_hits(start, end, player.rect.inflate(-4, -4)):
                    strike_player(world, self.facing, 320)
            else:
                self.lance = None
                self.lance_timer = 2.8
                self._set_plan("stalk")
                self.animator.play("idle")
        self._physics(dt, world, friction=self.plan != "stalk")

    def _fire(self, world: "World") -> None:
        self._set_plan("fire")
        self.animator.play("fire", restart=True)
        start = self.mirror_point()
        dx, dy = self.aim[0] - start[0], self.aim[1] - start[1]
        length = max(1.0, math.hypot(dx, dy))
        ux, uy = dx / length, dy / length
        self.mirror_angle = math.atan2(uy, ux)
        end = _raycast(world, start, (ux, uy), 640)
        self.lance = (start, end)
        world.events.emit(EventType.MACHINE_CLUNK, start, "lance")
        emitters.sparkle_burst(world.particles, *start, GOLD_LIGHT, 10, 160)
        for k in range(10):
            f = k / 10
            world.particles.spawn(start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f, 0, -20,
                                  life=0.4, kind=Kind.TWINKLE, size=3, color=GOLD_LIGHT, color_end=FIRE)

    def cut_lance(self, point: tuple[float, float]) -> None:
        """Something (the ink) stands in the lance's way."""
        if self.lance is not None:
            self.lance = (self.lance[0], point)

    def _glint_step(self, world: "World") -> None:
        """A flash off the mirror - the prince reels - and Tariq is somewhere else."""
        player = world.player
        self.glint_timer = 4.5
        flash = self.mirror_point()
        emitters.sparkle_burst(world.particles, *flash, GOLD_LIGHT, 16, 220)
        world.particles.spawn(*flash, life=0.3, kind=Kind.GLOW, size=70, size_end=10, color=GOLD_LIGHT, alpha=1.0)
        direction = 1 if player.body.centerx > self.body.centerx else -1
        shove(world, direction * 260, -200, lock=0.3)
        left, right = self.bounds
        target = self.body.centerx - direction * 5 * T
        if not left + 30 < target < right - 30:
            target = self.body.centerx + direction * 5 * T
        target = max(left + 30, min(right - 30, target))
        self.body.place_midbottom((target, ground_below(world, target, self.body.top - 40)))
        self.body.velocity.update(0, 0)
        emitters.sparkle_burst(world.particles, *self.center, GOLD_LIGHT, 12, 150)
        world.events.emit(EventType.MACHINE_CLUNK, flash, "glint")

    def on_interrupted(self, world: "World") -> None:
        self.lance = None
        self.lance_timer = max(self.lance_timer, 1.6)
        self.plan = "stalk"

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        mx, my = camera.to_screen(*self.mirror_point())
        lit = self.lit and self.blot <= 0
        angle = self.mirror_angle if self.plan in ("aim", "fire") else (-math.pi / 2 if self.plan == "raise" else 0.0)
        if self.facing < 0 and self.plan not in ("aim", "fire"):
            angle = math.pi - angle
        # The mirror: a disc of polished brass edge-on to its aim.
        nx, ny = math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2)
        a = (mx + nx * 7, my + ny * 7)
        b = (mx - nx * 7, my - ny * 7)
        pygame.draw.line(surface, (90, 56, 26), a, b, 5)
        pygame.draw.line(surface, (255, 236, 170) if lit else (150, 140, 150), a, b, 3)
        if lit:
            blit_glow(surface, (mx, my), 12 if self.plan != "aim" else 20, GOLD_LIGHT, 0.7 if self.plan != "aim" else 1.0)
        if self.fizzle > 0:
            for k in range(3):
                pygame.draw.circle(surface, (160, 150, 170), (round(mx + k * 3 - 3), round(my - 8 - self.fizzle * 20 - k * 4)), 2, 1)
        if self.plan == "aim":
            # The aiming line: thin and flickering while he tracks, steady and red-gold once locked.
            locked = self.plan_time >= self.AIM
            tx, ty = camera.to_screen(*self.aim)
            color = (255, 120, 60) if locked else (255, 220, 150)
            dx, dy = tx - mx, ty - my
            length = max(1.0, math.hypot(dx, dy))
            ux, uy = dx / length, dy / length
            for k in range(0, 640, 12):
                if locked or (k // 12 + int(self.time * 20)) % 2 == 0:
                    px, py = mx + ux * k, my + uy * k
                    surface.fill(color, (round(px), round(py), 2, 2))
        if self.lance is not None:
            start = camera.to_screen(*self.lance[0])
            end = camera.to_screen(*self.lance[1])
            fade = 1.0 - min(1.0, self.plan_time / self.FIRE)
            pygame.draw.line(surface, (255, 120, 40), start, end, round(12 * fade) + 3)
            pygame.draw.line(surface, (255, 220, 120), start, end, round(6 * fade) + 2)
            pygame.draw.line(surface, (255, 255, 240), start, end, 2)
            for k in range(8):
                f = k / 7
                blit_glow(surface, (start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f), 16, FIRE, 0.6 * fade)
            blit_glow(surface, end, 26, FIRE_HOT, 0.9 * fade)

    def lights(self) -> list[Light]:
        lights = super().lights()
        if self.lance is not None:
            (sx, sy), (ex, ey) = self.lance
            for k in range(4):
                f = (k + 0.5) / 4
                lights.append(Light(sx + (ex - sx) * f, sy + (ey - sy) * f, 70, FIRE, 0.8, bloom=0.3))
        return lights


# --- Samira, the fire-eater ------------------------------------------------------------------------------------
class _Patch:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.life = 3.0


class _Ember:
    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.alive = True


class FireEater(Gilded):
    kind = "samira"
    title = "Samira the Fire-Eater"
    sheet = art.SAMIRA_SHEET
    max_hp = 4
    element = FIRE

    INHALE = 0.55
    BREATH = 0.8
    CONE = 130.0

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.plan = "dance"
        self.plan_time = 0.0
        self.breath_timer = 2.0
        self.whirl_timer = 5.0
        self.kick_timer = 3.5
        self.whirl_dir = 1
        self.patches: list[_Patch] = []
        self.embers: list[_Ember] = []
        self.cone_cut = 1.0   # 0..1: how much of the flame the ink lets through

    def _set_plan(self, plan: str) -> None:
        self.plan = plan
        self.plan_time = 0.0

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.plan_time += dt
        distance = self.body.centerx - player.body.centerx
        if self.plan == "dance":
            self.face_player(world)
            keep = 5 * T if self.exposed else 3 * T
            ideal = player.body.centerx + math.copysign(keep, distance if distance else 1)
            left, right = self.bounds
            if not left + 40 < ideal < right - 40:
                ideal = player.body.centerx - math.copysign(keep, distance if distance else 1)
            arrived = self.walk_to(ideal, 130 if self.exposed else 100)
            self.animator.play("idle" if arrived else "walk")
            self.breath_timer -= dt
            self.whirl_timer -= dt
            self.kick_timer -= dt
            same_level = abs(player.body.bottom - self.body.bottom) < 40
            if self.breath_timer <= 0 and abs(distance) < 4.5 * T and same_level:
                self._set_plan("inhale")
                self.body.velocity.x = 0
                self.animator.play("inhale", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "inhale")
            elif self.whirl_timer <= 0 and same_level:
                self._set_plan("whirl")
                self.whirl_dir = -1 if distance > 0 else 1
                self.animator.play("whirl")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "poi")
            elif self.kick_timer <= 0:
                self._kick(world)
        elif self.plan == "inhale":
            self.body.velocity.x = 0
            if world.particles.rng.random() < dt * 30:
                mx, my = self.mouth()
                rng = world.particles.rng
                a = rng.uniform(0, math.tau)
                world.particles.spawn(mx + math.cos(a) * 24, my + math.sin(a) * 24, -math.cos(a) * 80, -math.sin(a) * 80,
                                      life=0.3, kind=Kind.DOT, size=1.8, color=FIRE_HOT, color_end=FIRE)
            if self.plan_time >= self.INHALE:
                self._set_plan("breathe")
                self.animator.play("breathe")
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "fire_breath")
        elif self.plan == "breathe":
            self.body.velocity.x = 0
            self._breathe(dt, world)
            if self.plan_time >= self.BREATH:
                self._set_plan("dance")
                self.breath_timer = 3.4
                self.animator.play("idle")
        elif self.plan == "whirl":
            self.body.velocity.x = self.whirl_dir * 250
            if self.body.hit_wall or not self.bounds[0] + 20 < self.body.centerx < self.bounds[1] - 20:
                self.whirl_dir = -self.whirl_dir
            reach = pygame.Rect(0, 0, 92, 72)
            reach.center = (round(self.body.centerx), round(self.body.centery - 4))
            if reach.colliderect(player.rect):
                strike_player(world, self.whirl_dir, 300)
            rng = world.particles.rng
            for k in range(2):
                a = self.time * 16 + k * math.pi
                world.particles.spawn(self.body.centerx + math.cos(a) * 40, self.body.centery - 4 + math.sin(a) * 18,
                                      rng.uniform(-30, 30), rng.uniform(-60, -20), life=0.4, kind=Kind.DOT, size=2.2,
                                      color=FIRE_HOT, color_end=EMBER, gravity=-60)
            if self.plan_time > 1.25:
                self._set_plan("dance")
                self.whirl_timer = 6.0
                self.animator.play("idle")
        self._physics(dt, world, friction=self.plan not in ("dance", "whirl"))

    def mouth(self) -> tuple[float, float]:
        hx, hy = art.head("samira", self.animator.current if self.animator.current in art.SAMIRA_ANIMS else "idle",
                          self.animator.frame_index)
        return self.body.centerx + (hx + 5) * self.facing, self.body.bottom + hy + 3

    def cone(self) -> list[tuple[float, float]]:
        mx, my = self.mouth()
        length = self.CONE * self.cone_cut
        half = math.radians(17)
        a = 0.08
        return [(mx, my), (mx + self.facing * math.cos(a - half) * length, my + math.sin(a - half) * length),
                (mx + self.facing * math.cos(a + half) * length, my + math.sin(a + half) * length)]

    def _breathe(self, dt: float, world: "World") -> None:
        mx, my = self.mouth()
        rng = world.particles.rng
        length = self.CONE * self.cone_cut
        for _ in range(4):
            spread = rng.uniform(-0.3, 0.3)
            speed = rng.uniform(260, 380) * self.cone_cut
            world.particles.spawn(mx, my, self.facing * math.cos(spread) * speed, math.sin(spread) * speed + 20,
                                  life=rng.uniform(0.25, 0.4) * max(0.3, self.cone_cut), kind=Kind.SMOKE,
                                  size=rng.uniform(3, 5), size_end=rng.uniform(10, 15), color=FIRE_HOT, color_end=EMBER, alpha=0.9)
        player = world.player
        points = self.cone()
        if length > 12 and _triangle_hits(points, player.rect.inflate(-6, -6)):
            strike_player(world, self.facing, 280)

    def _kick(self, world: "World") -> None:
        self.kick_timer = 4.5
        self.animator.play("kick", restart=True)
        rng = world.particles.rng
        for k in range(3):
            self.embers.append(_Ember(self.body.centerx + self.facing * 10, self.body.bottom - 10,
                                      self.facing * (120 + 70 * k) + rng.uniform(-20, 20), -rng.uniform(280, 360)))
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "embers")

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.cone_cut = min(1.0, self.cone_cut + dt * 4)
        player = world.player
        for ember in self.embers:
            ember.vy += 900 * dt
            ember.x += ember.vx * dt
            ember.y += ember.vy * dt
            floor = ground_below(world, ember.x, ember.y - 20)
            if ember.vy > 0 and ember.y >= floor:
                ember.alive = False
                self.patches.append(_Patch(ember.x, floor))
                emitters.embers(world.particles, ember.x, floor - 4, 6, 8)
            elif pygame.Rect(round(ember.x) - 5, round(ember.y) - 5, 10, 10).colliderect(player.rect):
                ember.alive = False
                strike_player(world, 1 if ember.vx > 0 else -1, 200)
        self.embers = [e for e in self.embers if e.alive]
        for patch in self.patches:
            patch.life -= dt
            if world.particles.rng.random() < dt * 8:
                emitters.embers(world.particles, patch.x + world.particles.rng.uniform(-14, 14), patch.y - 2, 1, 4)
            if patch.life > 0.3 and player.body.on_ground and abs(player.body.centerx - patch.x) < 20 \
                    and abs(player.body.bottom - patch.y) < 6:
                strike_player(world, 1 if player.body.centerx > patch.x else -1, 220)
        self.patches = [p for p in self.patches if p.life > 0]

    def silence(self, world: "World", effect) -> None:  # noqa: ANN001
        for ember in self.embers:
            ember.alive = False
            emitters.smoke_poof(world.particles, ember.x, ember.y, (90, 80, 100), 4)
        self.embers = []

    def on_interrupted(self, world: "World") -> None:
        self.plan = "dance"
        self.breath_timer = max(self.breath_timer, 1.8)
        self.body.velocity.x = 0

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        super().draw_back(surface, camera)
        for patch in self.patches:
            x, y = camera.to_screen(patch.x, patch.y)
            fade = min(1.0, patch.life / 0.6)
            for k in range(4):
                h = (8 + 6 * math.sin(self.time * 12 + k * 1.9 + patch.x)) * fade
                fx = x - 12 + k * 8
                pygame.draw.polygon(surface, EMBER, [(fx - 4, y), (fx, y - h), (fx + 4, y)])
                pygame.draw.polygon(surface, FIRE_HOT, [(fx - 2, y), (fx, y - h * 0.55), (fx + 2, y)])
            blit_glow(surface, (x, y - 6), 20, FIRE, 0.6 * fade)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        anim = self.animator.current if self.animator.current in art.SAMIRA_ANIMS else "idle"
        back, front = art.hands("samira", anim, self.animator.frame_index)
        f = self.facing
        hands = [camera.to_screen(self.body.centerx + back[0] * f, self.body.bottom + back[1]),
                 camera.to_screen(self.body.centerx + front[0] * f, self.body.bottom + front[1])]
        if self.plan == "whirl":
            cx, cy = camera.to_screen(self.body.centerx, self.body.centery - 4)
            for k in range(2):
                a = self.time * 16 + k * math.pi
                bx, by = cx + math.cos(a) * 40, cy + math.sin(a) * 18
                pygame.draw.line(surface, (90, 60, 40), (cx, cy), (bx, by), 1)
                blit_glow(surface, (bx, by), 18, FIRE, 0.9)
                pygame.draw.circle(surface, FIRE_HOT, (round(bx), round(by)), 5)
                for j in range(1, 5):
                    ta = a - j * 0.25
                    pygame.draw.circle(surface, EMBER, (round(cx + math.cos(ta) * 40), round(cy + math.sin(ta) * 18)), max(1, 5 - j))
        elif self.state in ("fight", "enter"):
            # Fire poi swinging on their chains at her sides.
            for k, (hx, hy) in enumerate(hands):
                a = self.time * 7 + k * math.pi
                bx, by = hx + math.cos(a) * 9, hy + 12 + math.sin(a) * 5
                pygame.draw.line(surface, (90, 60, 40), (hx, hy), (bx, by), 1)
                blit_glow(surface, (bx, by), 10, FIRE, 0.7)
                pygame.draw.circle(surface, FIRE_HOT, (round(bx), round(by)), 3)
        if self.plan == "inhale":
            mx, my = camera.to_screen(*self.mouth())
            u = min(1.0, self.plan_time / self.INHALE)
            blit_glow(surface, (mx, my), round(8 + 14 * u), FIRE_HOT, 0.4 + 0.6 * u)
        if self.plan == "breathe":
            points = [camera.to_screen(x, y) for x, y in self.cone()]
            flicker = 0.85 + 0.15 * math.sin(self.time * 40)
            mx, my = points[0]
            for k, color in enumerate(((200, 60, 30), FIRE, FIRE_HOT)):
                shrink = 1.0 - k * 0.28
                tri = [(mx, my)] + [(mx + (x - mx) * shrink * flicker, my + (y - my) * shrink * flicker) for x, y in points[1:]]
                pygame.draw.polygon(surface, color, tri)
            for k in range(5):
                f = (k + 1) / 5
                x = mx + ((points[1][0] + points[2][0]) / 2 - mx) * f
                y = my + ((points[1][1] + points[2][1]) / 2 - my) * f
                blit_glow(surface, (x, y), round(12 + 16 * f), FIRE, 0.7)
        for ember in self.embers:
            x, y = camera.to_screen(ember.x, ember.y)
            blit_glow(surface, (x, y), 10, FIRE, 0.8)
            pygame.draw.circle(surface, FIRE_HOT, (x, y), 3)

    def lights(self) -> list[Light]:
        lights = super().lights()
        if self.active:
            lights.append(Light(*self.center, 60, FIRE, 0.5, flicker=0.6))
        if self.plan == "breathe":
            points = self.cone()
            cx = sum(p[0] for p in points) / 3
            cy = sum(p[1] for p in points) / 3
            lights.append(Light(cx, cy, 140, FIRE, 1.0, flicker=1.0, bloom=0.4))
        for patch in self.patches:
            lights.append(Light(patch.x, patch.y - 8, 50, FIRE, 0.7, flicker=1.0))
        return lights


# --- Hakim, the snake-charmer --------------------------------------------------------------------------------------
class Cobra:
    """A brass cobra in a wicker basket, dancing while Hakim plays."""

    WINDUP = 0.45
    STRIKE = 0.18
    REACH = 72.0

    def __init__(self, x: float, floor: float) -> None:
        self.x = x
        self.floor = floor
        self.state = "hidden"
        self.timer = 0.0
        self.rise = 0.0
        self.time = random.random() * 5
        self.facing = 1
        self.lunge = 0.0
        self.knocked = 0.0
        self.lid = 0.0       # rattle of the lid (Hakim about to pop out of this basket)

    @property
    def head(self) -> tuple[float, float]:
        sway = math.sin(self.time * 3) * 5 * (self.state == "sway")
        return (self.x + self.facing * (6 + self.lunge * self.REACH) + sway,
                self.floor - 14 - 34 * self.rise + self.lunge * 18)

    def head_rect(self) -> pygame.Rect:
        x, y = self.head
        return pygame.Rect(round(x) - 9, round(y) - 8, 18, 16)

    def update(self, dt: float, world: "World", charmed: bool) -> None:
        self.time += dt
        self.timer += dt
        self.lid = max(0.0, self.lid - dt)
        self.knocked = max(0.0, self.knocked - dt)
        player = world.player
        distance = player.body.centerx - self.x
        near = abs(distance) < 150 and abs(player.body.bottom - self.floor) < 70
        if not charmed or self.knocked > 0:
            self.rise = max(0.0, self.rise - dt * 3)
            self.lunge = max(0.0, self.lunge - dt * 6)
            if self.state != "hidden" and self.rise <= 0:
                self.state = "hidden"
            return
        if self.state == "hidden":
            if near:
                self.state = "rise"
                self.timer = 0.0
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "cobra_hiss")
        elif self.state == "rise":
            self.rise = min(1.0, self.rise + dt / 0.4)
            if self.rise >= 1:
                self.state = "sway"
                self.timer = 0.0
        elif self.state == "sway":
            self.facing = 1 if distance > 0 else -1
            if abs(distance) < self.REACH + 20 and self.timer > 0.6 and abs(player.body.bottom - self.floor) < 60:
                self.state = "windup"
                self.timer = 0.0
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor), "cobra_hiss")
            elif not near and self.timer > 2.0:
                self.state = "sink"
        elif self.state == "windup":
            self.lunge = -0.15 * min(1.0, self.timer / self.WINDUP)
            if self.timer >= self.WINDUP:
                self.state = "strike"
                self.timer = 0.0
                world.events.emit(EventType.MACHINE_CLUNK, self.head, "cobra_strike")
        elif self.state == "strike":
            self.lunge = min(1.0, self.timer / self.STRIKE)
            if self.head_rect().inflate(6, 6).colliderect(player.rect):
                strike_player(world, self.facing, 260)
            if self.timer >= self.STRIKE + 0.12:
                self.state = "recoil"
                self.timer = 0.0
        elif self.state == "recoil":
            self.lunge = max(0.0, self.lunge - dt * 3)
            if self.timer > 0.7:
                self.state = "sway"
                self.timer = 0.0
        elif self.state == "sink":
            self.rise = max(0.0, self.rise - dt * 2)
            if self.rise <= 0:
                self.state = "hidden"
        # A slash on the cobra's head knocks it back into the basket.
        attack = player.attack_rect
        if attack is not None and self.rise > 0.5 and attack.colliderect(self.head_rect().inflate(10, 10)):
            self.knocked = 2.5
            self.state = "hidden"
            emitters.sparkle_burst(world.particles, *self.head, GOLD, 8, 120)
            world.events.emit(EventType.MACHINE_CLUNK, self.head, "clang")

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.x, self.floor)
        # The cobra rises out of the basket's mouth (drawn before the basket's front).
        if self.rise > 0.02:
            hx, hy = camera.to_screen(*self.head)
            base = (x, y - 18)
            ctrl = (x - self.facing * 10, (base[1] + hy) / 2)
            points = []
            for k in range(9):
                u = k / 8
                px = (1 - u) ** 2 * base[0] + 2 * (1 - u) * u * ctrl[0] + u * u * hx
                py = (1 - u) ** 2 * base[1] + 2 * (1 - u) * u * ctrl[1] + u * u * hy
                points.append((px, py))
            pygame.draw.lines(surface, (70, 44, 20), False, points, 8)
            pygame.draw.lines(surface, (196, 146, 60), False, points, 6)
            for k in range(1, 8, 2):
                pygame.draw.circle(surface, (46, 180, 170), (round(points[k][0]), round(points[k][1])), 1)
            flare = 1.0 + 0.5 * (self.state in ("windup", "strike"))
            hood = [(hx - self.facing * 2, hy - 9 * flare), (hx + self.facing * 7, hy - 3), (hx + self.facing * 7, hy + 3),
                    (hx - self.facing * 2, hy + 8 * flare), (hx - self.facing * 6, hy)]
            pygame.draw.polygon(surface, (70, 44, 20), [(px + 1, py + 1) for px, py in hood])
            pygame.draw.polygon(surface, (214, 164, 70), hood)
            pygame.draw.circle(surface, (224, 44, 70), (round(hx + self.facing * 3), round(hy - 2)), 2)
            if self.state in ("windup", "strike"):
                pygame.draw.line(surface, (200, 40, 60), (hx + self.facing * 7, hy + 1), (hx + self.facing * 13, hy + 3), 1)
        # The basket: woven wicker with a lid that rattles when Hakim is about to pop out.
        rattle = math.sin(self.time * 60) * 2 * min(1.0, self.lid * 3)
        pygame.draw.polygon(surface, (70, 44, 20), [(x - 15, y), (x + 15, y), (x + 12, y - 22), (x - 12, y - 22)])
        pygame.draw.polygon(surface, (196, 150, 84), [(x - 13, y - 1), (x + 13, y - 1), (x + 10, y - 21), (x - 10, y - 21)])
        for k in range(4):
            yy = y - 4 - k * 5
            pygame.draw.line(surface, (150, 104, 50), (x - 12 + k, yy), (x + 12 - k, yy), 1)
        if self.rise < 0.1:
            lid = pygame.Rect(0, 0, 26, 7)
            lid.midbottom = (round(x + rattle), round(y - 20 - abs(rattle)))
            pygame.draw.ellipse(surface, (70, 44, 20), lid.inflate(2, 2))
            pygame.draw.ellipse(surface, (214, 170, 96), lid)
            if self.lid > 0:
                blit_glow(surface, (x, y - 24), 16, GOLD, 0.5)


class SnakeCharmer(Gilded):
    kind = "hakim"
    title = "Hakim the Snake-Charmer"
    sheet = art.HAKIM_SHEET
    max_hp = 5
    element = (120, 220, 160)

    DIVE = 0.3
    TRANSIT = 0.75
    POP = 0.3

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.cobras: list[Cobra] = []
        self.basket = 0
        self.plan = "play"
        self.plan_time = 0.0
        self.trick_timer = 5.0
        self.call_timer = 7.0
        self.called = False
        self.destination = 0
        self.note_timer = 0.0

    def set_baskets(self, spots: list[tuple[float, float]]) -> None:
        self.cobras = [Cobra(x, y) for x, y in spots]

    @property
    def charming(self) -> bool:
        return self.state == "fight" and self.plan == "play" and self.blot <= 0

    def _set_plan(self, plan: str) -> None:
        self.plan = plan
        self.plan_time = 0.0

    def think(self, dt: float, world: "World") -> None:
        self.plan_time += dt
        self.called = False
        player = world.player
        if self.plan == "play":
            self.face_player(world)
            home = self.cobras[self.basket] if self.cobras else None
            if home is not None:
                # He stands beside his basket, on the side away from the prince.
                side = -1 if player.body.centerx > home.x else 1
                arrived = self.walk_to(home.x + side * 26, 60)
                self.animator.play("idle" if arrived else "walk")
            self.trick_timer -= dt
            self.call_timer -= dt
            self.note_timer -= dt
            if self.note_timer <= 0:
                self.note_timer = 0.35
                from rendering.art import nightingale

                hx, hy = art.head("hakim", "idle", self.animator.frame_index)
                world.particles.spawn(self.body.centerx + (hx + 8) * self.facing, self.body.bottom + hy + 4,
                                      self.facing * 20, -40, life=1.0, kind=Kind.IMAGE, spin=30,
                                      image=nightingale.note_image(3, (120, 230, 170)))
            near = abs(player.body.centerx - self.body.centerx) < 3 * T
            if self.trick_timer <= 0 or (near and self.trick_timer < 3.0 and len(self.cobras) > 1):
                self._begin_trick(world)
            elif self.call_timer <= 0:
                self._set_plan("summon")
                self.animator.play("summon", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "summon")
        elif self.plan == "summon":
            self.body.velocity.x = 0
            if self.plan_time > 0.5 and not self.called and self.call_timer <= 0:
                self.called = True
                self.call_timer = 8.0
            if self.plan_time > 0.9:
                self._set_plan("play")
                self.animator.play("idle")
        elif self.plan == "dive":
            self.body.velocity.x = 0
            if self.plan_time >= self.DIVE:
                self._set_plan("transit")
                self.state = "vanished"
        self._physics(dt, world, friction=self.plan != "play")

    def _begin_trick(self, world: "World") -> None:
        if len(self.cobras) < 2:
            self.trick_timer = 5.0
            return
        player = world.player
        options = [k for k in range(len(self.cobras)) if k != self.basket]
        # Pop out of the basket furthest from the prince.
        self.destination = max(options, key=lambda k: abs(self.cobras[k].x - player.body.centerx))
        home = self.cobras[self.basket]
        self.body.place_midbottom((home.x, home.floor))
        self._set_plan("dive")
        self.animator.play("dive", restart=True)
        self.trick_timer = 6.0
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "basket")

    def update(self, dt: float, world: "World") -> None:
        if self.state == "vanished" and self.plan == "transit":
            self._update_loot(dt, world)
            self.time += dt
            self.plan_time += dt
            destination = self.cobras[self.destination]
            destination.lid = 0.6
            if self.plan_time >= self.TRANSIT:
                self.basket = self.destination
                self.body.place_midbottom((destination.x, destination.floor))
                self.body.velocity.update(0, -300)
                self.state = "fight"
                self._set_plan("pop")
                self.animator.play("pop", restart=True)
                emitters.sparkle_burst(world.particles, destination.x, destination.floor - 24, GOLD, 10, 140)
                world.events.emit(EventType.MACHINE_CLUNK, (destination.x, destination.floor), "basket_pop")
            for cobra in self.cobras:
                cobra.update(dt, world, False)
            return
        if self.plan == "pop" and self.state == "fight":
            self.plan_time += dt
            if self.plan_time > self.POP + 0.35:
                self._set_plan("play")
                self.animator.play("idle")
        super().update(dt, world)
        charmed = self.charming and self.engaged
        for cobra in self.cobras:
            cobra.update(dt, world, charmed)

    def stun(self, world: "World", seconds: float) -> None:
        if self.state == "vanished":
            destination = self.cobras[self.destination]
            self.body.place_midbottom((destination.x, destination.floor))
            self.state = "fight"
            self.basket = self.destination
        super().stun(world, seconds)

    def on_interrupted(self, world: "World") -> None:
        if self.plan != "transit":
            self.plan = "play"

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        super().draw_back(surface, camera)
        for cobra in self.cobras:
            cobra.draw(surface, camera)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state in ("fight", "enter") and self.animator.current in ("idle", "walk"):
            # The gourd flute (pungi) at his lips.
            hx, hy = art.head("hakim", self.animator.current, self.animator.frame_index)
            mouth = camera.to_screen(self.body.centerx + (hx + 5) * self.facing, self.body.bottom + hy + 4)
            gourd = (mouth[0] + self.facing * 6, mouth[1] + 4)
            end = (mouth[0] + self.facing * 14, mouth[1] + 9)
            pygame.draw.line(surface, (70, 44, 20), mouth, end, 4)
            pygame.draw.line(surface, (196, 150, 84), mouth, end, 2)
            pygame.draw.circle(surface, (70, 44, 20), gourd, 5)
            pygame.draw.circle(surface, (214, 170, 96), gourd, 4)
            pygame.draw.circle(surface, (46, 180, 170), (gourd[0] - 1, gourd[1] - 1), 1)


# --- geometry helpers ----------------------------------------------------------------------------------------
def _raycast(world: "World", start: tuple[float, float], direction: tuple[float, float], length: float) -> tuple[float, float]:
    """The first solid tile along a ray (or its full length)."""
    x, y = start
    dx, dy = direction
    collision = world.collision
    step = 6.0
    travelled = 0.0
    while travelled < length:
        x += dx * step
        y += dy * step
        travelled += step
        tx, ty = collision.tile_at(x, y)
        if collision.get(tx, ty).name == "SOLID":
            return x, y
    return x, y


def _segment_hits(a: tuple[float, float], b: tuple[float, float], rect: pygame.Rect) -> bool:
    return bool(rect.clipline(a, b))


def _triangle_hits(points: list[tuple[float, float]], rect: pygame.Rect) -> bool:
    (ax, ay), (bx, by), (cx, cy) = points
    for px, py in ((rect.left, rect.top), (rect.right, rect.top), (rect.left, rect.bottom), (rect.right, rect.bottom), rect.center):
        d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
        d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
        d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
        negative = d1 < 0 or d2 < 0 or d3 < 0
        positive = d1 > 0 or d2 > 0 or d3 > 0
        if not (negative and positive):
            return True
    return any(rect.clipline(points[i], points[(i + 1) % 3]) for i in range(3))
