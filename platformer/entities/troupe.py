"""The Moon Troupe: masked performers who serve the thief of al-Jazari's book.

They are people like Amir - the same rig, the same physics - each with a
performer's trick turned into a weapon, and each wrapped in a bubble of
enchanted water that the Moon-Clock keeps refilling along a glowing tether.

* ``Juggler`` (Rashid) lobs oranges that burst into sticky juice. Slash an
  orange in mid-air and it flies straight back at him.
* ``Dancer`` (Zahra) dissolves into a whirl of orange blossom, reappears
  behind the prince in a spinning kick, and throws fans of petal blades.
* ``Weaver`` (Layla) floats on a pillar of water, lashes a water whip and
  calls the moon's tide.

Hitting a performer first pops the bubble (three blows); only then does a
blow land. Unless the tether is cut, the bubble grows back in a few seconds.
"""

import math
from functools import lru_cache
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import Color
from entities.performer import Performer, strike_player
from entities.scarf import Scarf
from rendering import emitters
from rendering.art import troupe as art
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from rendering.sprite_library import SpriteLibrary

if TYPE_CHECKING:
    from world.world import World

SHIELD_HITS = 3
SHIELD_REGEN = 2.6
BUBBLE: Color = (120, 230, 240)
BUBBLE_LIGHT: Color = (225, 255, 255)
ORANGE: Color = (250, 150, 40)
ORANGE_DARK: Color = (200, 96, 24)
LEAF: Color = (70, 150, 60)
PETAL: Color = (255, 246, 236)
PETAL_PINK: Color = (255, 190, 200)
WATER: Color = (80, 200, 240)
STEP_WARNING = 0.72     # how long the petals gather before Zahra reappears
PARRY_REACH = 30        # how generous batting an orange back is

__all__ = ["Dancer", "Juggler", "Performer", "Weaver", "strike_player"]


@lru_cache(maxsize=None)
def _mask_image() -> pygame.Surface:
    """The golden half-mask that flies off a beaten performer."""
    mask = pygame.Surface((14, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (120, 70, 20), (0, 0, 14, 8))
    pygame.draw.ellipse(mask, (240, 196, 80), (1, 1, 12, 6))
    pygame.draw.ellipse(mask, (40, 20, 20), (3, 3, 3, 2))
    pygame.draw.ellipse(mask, (40, 20, 20), (8, 3, 3, 2))
    pygame.draw.line(mask, (255, 240, 180), (2, 2), (11, 2))
    return mask


# --- the moon's ward: a bubble of moon-water ------------------------------------------------------
class Bubbled(Performer):
    """A Moon Troupe performer, wrapped in a bubble that the moon's tether heals.

    The bubble takes three blows (or one song) to burst; while the tether holds,
    it grows back a few seconds later.
    """

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.shield = SHIELD_HITS
        self.shield_grow = 1.0         # 0..1 while a new bubble grows
        self.regen = 0.0
        self.tethered = True
        self.ripple = 0.0

    @property
    def warded(self) -> bool:
        return self.shield > 0

    @property
    def shielded(self) -> bool:
        return self.shield > 0 and self.shield_grow >= 1.0

    @property
    def bubble_radius(self) -> float:
        return 26.0 * self.shield_grow if (self.shield > 0 or self.shield_grow > 0) else 0.0

    @property
    def tether_point(self) -> tuple[float, float]:
        """Where the moon's tether meets the bubble (its crown)."""
        cx, cy = self.center
        return cx, cy - max(self.bubble_radius, 16.0) + 2

    def begin_ward(self) -> None:
        self.shield = SHIELD_HITS
        self.shield_grow = 0.0

    def ward_blow(self, world: "World", direction: int, source: str) -> None:
        self.shield -= 1
        self.ripple = 1.0
        emitters.sparkle_burst(world.particles, *self.center, BUBBLE_LIGHT, 6, 90)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "bubble_hit")
        if self.shield <= 0:
            self.pop(world)

    def break_ward(self, world: "World") -> None:
        if self.shield > 0:
            self.pop(world)

    def drop_ward(self) -> None:
        self.shield = 0
        self.shield_grow = 0.0

    def pop(self, world: "World") -> None:
        self.shield = 0
        self.shield_grow = 0.0
        self.regen = SHIELD_REGEN
        cx, cy = self.center
        rng = world.particles.rng
        for k in range(18):
            a = k * math.tau / 18
            world.particles.spawn(cx + math.cos(a) * 24, cy + math.sin(a) * 24, math.cos(a) * rng.uniform(80, 200),
                                  math.sin(a) * rng.uniform(80, 200) - 60, life=rng.uniform(0.4, 0.8), kind=Kind.DOT,
                                  size=rng.uniform(1.5, 3), color=BUBBLE_LIGHT, color_end=WATER, gravity=500)
        world.particles.spawn(cx, cy, life=0.35, kind=Kind.RING, size=18, size_end=48, color=BUBBLE_LIGHT)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "bubble_pop")

    def update_ward(self, dt: float, world: "World") -> None:
        self.ripple = max(0.0, self.ripple - dt * 2.5)
        if self.state == "enter":
            self.shield_grow = min(1.0, self.shield_grow + dt / 0.7)
            return
        # The bubble grows back along the moon's tether.
        if self.shield <= 0 and self.tethered:
            self.regen -= dt
            if self.regen <= 0:
                self.shield_grow = min(1.0, self.shield_grow + dt / 0.6)
                if self.shield_grow >= 1.0:
                    self.shield = SHIELD_HITS
                    world.events.emit(EventType.MACHINE_CLUNK, self.center, "bubble_grow")

    def shed(self, world: "World") -> None:
        # The golden mask flies off and spins away.
        world.particles.spawn(self.body.centerx, self.body.top + 4, -self.facing * 90, -420, life=1.6, kind=Kind.IMAGE,
                              image=_mask_image(), spin=540, gravity=1100, front=True)
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.top + 4, (255, 220, 120), 10, 140)

    def ward_lights(self) -> list[Light]:
        if self.shield_grow > 0.2:
            return [Light(*self.center, 46, BUBBLE, 0.55 * self.shield_grow, bloom=0.15)]
        return []

    def draw_ward(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.shield_grow <= 0:
            return
        cx, cy = camera.to_screen(*self.center)
        grow = self.shield_grow
        wobble = math.sin(self.time * 5) * 1.5 + self.ripple * 4 * math.sin(self.time * 40)
        radius = round((26 + wobble) * grow)
        if radius < 3:
            return
        size = radius * 2 + 8
        bubble = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        pygame.draw.circle(bubble, (*BUBBLE, 58), (c, c), radius)
        pygame.draw.circle(bubble, (*BUBBLE, 110), (c, c), radius, 4)
        pygame.draw.circle(bubble, (*BUBBLE_LIGHT, 235), (c, c), radius, 2)
        # A rainbow sheen sliding round the film, and a window highlight.
        for k, color in enumerate(((255, 160, 200), (255, 240, 150), (150, 255, 220))):
            a = self.time * 1.3 + k * 0.5
            rect = pygame.Rect(c - radius + 3, c - radius + 3, radius * 2 - 6, radius * 2 - 6)
            pygame.draw.arc(bubble, (*color, 120), rect, a, a + 0.9, 2)
        pygame.draw.arc(bubble, (255, 255, 255, 210), (c - radius + 6, c - radius + 6, radius * 2 - 12, radius * 2 - 12), 1.9, 2.7, 3)
        pygame.draw.circle(bubble, (255, 255, 255, 220), (c - radius // 2, c - radius // 2), 2)
        # Cracks for every blow the bubble has taken.
        for k in range(SHIELD_HITS - self.shield if self.shield > 0 else 0):
            a = 0.8 + k * 2.1
            start = (c + math.cos(a) * radius, c + math.sin(a) * radius)
            mid = (c + math.cos(a + 0.2) * radius * 0.55, c + math.sin(a + 0.2) * radius * 0.55)
            end = (c + math.cos(a - 0.1) * radius * 0.25, c + math.sin(a - 0.1) * radius * 0.25)
            pygame.draw.lines(bubble, (255, 255, 255, 200), False, [start, mid, end], 1)
        surface.blit(bubble, (cx - c, cy - c))


# --- Rashid, the orange juggler ----------------------------------------------------------------------
class _Orange:
    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.spin = 0.0
        self.reflected = False
        self.alive = True


class Juggler(Bubbled):
    kind = "juggler"
    title = "Rashid the Juggler"
    sheet = art.JUGGLER_SHEET
    max_hp = 3
    element = ORANGE

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.oranges: list[_Orange] = []
        self.puddles: list[list[float]] = []
        self.throws = 0
        self.juggling = 3

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.face_player(world)
        distance = self.body.centerx - player.body.centerx
        if self.animator.current in ("throw", "rain") and not self.animator.finished:
            self.body.velocity.x = 0
        else:
            keep = 7 * 32 if self.exposed else 5 * 32
            ideal = player.body.centerx + math.copysign(keep, distance if distance else 1)
            left, right = self.bounds
            if not left + 40 < ideal < right - 40:
                # Backed against the edge of the stage: slip past to the other side.
                ideal = player.body.centerx - math.copysign(keep, distance if distance else 1)
            arrived = self.walk_to(ideal, 150 if self.exposed else 70)
            self.animator.play("idle" if arrived else "walk")
            if self.timer > 2.0 and self.juggling > 0:
                self.timer = 0.0
                self.throws += 1
                if self.throws % 3 == 0:
                    self._rain(world)
                else:
                    self._throw(world, player.body.centerx + player.body.velocity.x * 0.45)
        self._physics(dt, world)

    def _launch(self, world: "World", target_x: float, flight: float, height: float = 0.0) -> None:
        start_x = self.body.centerx + self.facing * 10
        start_y = self.body.top + 4
        gravity = 900.0
        vx = (target_x - start_x) / flight
        vy = (self.floor - start_y - 0.5 * gravity * flight * flight) / flight - height
        self.oranges.append(_Orange(start_x, start_y, vx, vy))
        world.events.emit(EventType.MACHINE_CLUNK, (start_x, start_y), "toss")

    def _throw(self, world: "World", target_x: float) -> None:
        self.animator.play("throw", restart=True)
        self._launch(world, target_x, 1.0)

    def _rain(self, world: "World") -> None:
        self.animator.play("rain", restart=True)
        x = world.player.body.centerx
        for k, dx in enumerate((-64, 0, 64)):
            self._launch(world, x + dx, 1.15 + k * 0.12, 160)

    def silence(self, world: "World", song) -> None:  # noqa: ANN001
        for orange in self.oranges:
            if orange.alive and (song is None or song.reaches(orange.x, orange.y)) and not orange.reflected:
                orange.alive = False
                emitters.sparkle_burst(world.particles, orange.x, orange.y, (255, 200, 90), 6, 90)
                for _ in range(5):
                    rng = world.particles.rng
                    world.particles.spawn(orange.x, orange.y, rng.uniform(-80, 80), rng.uniform(-120, 0), life=0.5,
                                          kind=Kind.DOT, size=2, color=(255, 190, 70), color_end=ORANGE_DARK, gravity=700)

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self._update_oranges(dt, world)

    def _update_oranges(self, dt: float, world: "World") -> None:
        player = world.player
        for orange in self.oranges:
            orange.spin += dt * 12
            if orange.reflected:
                orange.x += orange.vx * dt
                orange.y += orange.vy * dt
                if pygame.Rect(round(orange.x) - 8, round(orange.y) - 8, 16, 16).colliderect(self.rect.inflate(10, 10)) \
                        and self.targetable:
                    orange.alive = False
                    self._splash(world, orange.x, orange.y)
                    self.break_ward(world)
                    self.grace = 0.0
                    self.hit(world, 1 if orange.vx > 0 else -1, "orange")
                    if self.active:
                        self.stun(world, 1.4)
                continue
            orange.vy += 900 * dt
            orange.x += orange.vx * dt
            orange.y += orange.vy * dt
            rect = pygame.Rect(round(orange.x) - 7, round(orange.y) - 7, 14, 14)
            attack = player.attack_rect
            if attack is not None and attack.colliderect(rect.inflate(PARRY_REACH, PARRY_REACH)):
                # Parried! It flies straight back at the juggler.
                orange.reflected = True
                dx, dy = self.body.centerx - orange.x, self.body.centery - orange.y
                distance = max(1.0, math.hypot(dx, dy))
                orange.vx, orange.vy = dx / distance * 620, dy / distance * 620
                emitters.sparkle_burst(world.particles, orange.x, orange.y, (255, 220, 140), 8, 120)
                world.events.emit(EventType.MACHINE_CLUNK, (orange.x, orange.y), "parry")
                continue
            if rect.colliderect(player.rect):
                orange.alive = False
                self._splash(world, orange.x, orange.y)
                strike_player(world, 1 if orange.vx > 0 else -1, 220)
                continue
            if orange.y >= self.floor - 6:
                orange.alive = False
                self._splash(world, orange.x, self.floor)
                self.puddles.append([orange.x, 4.0])
        left, right = self.bounds
        self.oranges = [o for o in self.oranges if o.alive and -200 < o.y < world.collision.pixel_height
                        and left - 300 < o.x < right + 300]
        for puddle in self.puddles:
            puddle[1] -= dt
            if player.body.on_ground and abs(player.body.centerx - puddle[0]) < 26 and abs(player.body.bottom - self.floor) < 6:
                # Sticky juice: the prince's feet drag.
                player.body.velocity.x *= 0.86
        self.puddles = [p for p in self.puddles if p[1] > 0]

    def _splash(self, world: "World", x: float, y: float) -> None:
        rng = world.particles.rng
        for _ in range(12):
            world.particles.spawn(x, y, rng.uniform(-160, 160), rng.uniform(-260, -60), life=rng.uniform(0.4, 0.7),
                                  kind=Kind.DOT, size=rng.uniform(1.6, 3.2), color=(255, 190, 70), color_end=ORANGE_DARK,
                                  gravity=900)
        world.events.emit(EventType.MACHINE_CLUNK, (x, y), "splat")

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        # Three oranges cascading between his hands while he juggles.
        if self.state in ("fight", "enter") and self.animator.current in ("idle", "walk"):
            back, front = art.hands("juggler", self.animator.current, self.animator.frame_index)
            f = self.facing
            bx, by = camera.to_screen(self.body.centerx + back[0] * f, self.body.bottom + back[1])
            fx, fy = camera.to_screen(self.body.centerx + front[0] * f, self.body.bottom + front[1])
            for k in range(3):
                u = (self.time * 1.7 + k / 3) % 1.0
                a, b = ((bx, by), (fx, fy)) if u < 0.5 else ((fx, fy), (bx, by))
                v = (u % 0.5) * 2
                x = a[0] + (b[0] - a[0]) * v
                y = a[1] + (b[1] - a[1]) * v - math.sin(v * math.pi) * 26
                self._orange(surface, (x, y), self.time * 8 + k)

    @staticmethod
    def _orange(surface: pygame.Surface, center: tuple[float, float], spin: float) -> None:
        x, y = round(center[0]), round(center[1])
        pygame.draw.circle(surface, (60, 30, 20), (x, y), 6)
        pygame.draw.circle(surface, ORANGE, (x, y), 5)
        pygame.draw.circle(surface, (255, 210, 120), (x - 2, y - 2), 2)
        a = spin
        pygame.draw.line(surface, LEAF, (x, y - 5), (x + math.cos(a) * 3, y - 5 + math.sin(a) * 2 - 2), 2)

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        for puddle in self.puddles:
            x, y = camera.to_screen(puddle[0], self.floor)
            fade = min(1.0, puddle[1] / 1.2)
            juice = pygame.Surface((56, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(juice, (255, 170, 50, round(200 * fade)), (0, 2, 56, 9))
            pygame.draw.ellipse(juice, (255, 220, 140, round(160 * fade)), (10, 3, 22, 4))
            surface.blit(juice, (x - 28, y - 7))

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        super().draw(surface, camera)
        for orange in self.oranges:
            x, y = camera.to_screen(orange.x, orange.y)
            if orange.reflected:
                blit_glow(surface, (x, y), 16, (255, 200, 90), 0.8)
            self._orange(surface, (x, y), orange.spin)

    def dissolve(self, world: "World") -> None:
        rng = world.particles.rng
        for _ in range(6):
            self.oranges.append(_Orange(self.body.centerx, self.body.top, rng.uniform(-160, 160), rng.uniform(-420, -200)))
        emitters.sparkle_burst(world.particles, *self.center, (255, 200, 90), 14, 150)


# --- Zahra, the blossom dancer -------------------------------------------------------------------------
class _Blade:
    def __init__(self, x: float, y: float, angle: float) -> None:
        self.x, self.y = x, y
        self.angle = angle
        self.age = 0.0
        self.alive = True


class Dancer(Bubbled):
    kind = "dancer"
    title = "Zahra the Blossom Dancer"
    sheet = art.DANCER_SHEET
    max_hp = 4
    element = (255, 170, 190)

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.veil = Scarf((x, floor - 40), (240, 110, 130), (250, 214, 110))
        self.blades: list[_Blade] = []
        self.plan = "dance"
        self.step_target = (x, floor)
        self.step_timer = 3.5
        self.fan_timer = 1.6
        self.fleeing = False

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        if self.plan == "dance":
            self.face_player(world)
            distance = self.body.centerx - player.body.centerx
            ideal = player.body.centerx + math.copysign(4 * 32, distance if distance else 1)
            arrived = self.walk_to(ideal, 120)
            if self.animator.current not in ("throw",) or self.animator.finished:
                self.animator.play("idle" if arrived else "walk")
            self.step_timer -= dt
            self.fan_timer -= dt
            if self.exposed and self.step_timer > 1.3 and abs(distance) < 3 * 32:
                self.step_timer = 1.3
            if self.step_timer <= 0:
                self._begin_step(world, flee=self.exposed)
            elif self.fan_timer <= 0 and abs(distance) > 2 * 32:
                self.fan_timer = 2.6
                self._fan(world)
            self._physics(dt, world)
        elif self.plan == "vanish":
            self.body.velocity.x = 0
            if self.timer > 0.3:
                self.plan = "gather"
                self.state = "vanished"
                self.timer = 0.0
        elif self.plan == "kick":
            self._physics(dt, world, friction=True)
            if 0.07 < self.timer < 0.25:
                reach = pygame.Rect(0, 0, 76, 40)
                reach.midbottom = self.body.midbottom
                if reach.colliderect(player.rect):
                    strike_player(world, self.facing, 380)
            if self.timer > 0.32:
                self.plan = "recover"
                self.timer = 0.0
                self.animator.play("idle")
        elif self.plan == "recover":
            self._physics(dt, world, friction=True)
            if self.timer > 1.0:
                self.plan = "dance"
                self.step_timer = 4.2
        emitters_rng = world.particles.rng
        if self.state == "fight" and self.plan == "dance" and emitters_rng.random() < dt * 3:
            world.particles.spawn(self.body.centerx + emitters_rng.uniform(-10, 10), self.body.bottom - 4,
                                  emitters_rng.uniform(-20, 20), -emitters_rng.uniform(10, 30), life=1.2, kind=Kind.PETAL,
                                  size=1.6, color=PETAL, wobble=30, front=False)

    def _begin_step(self, world: "World", flee: bool = False) -> None:
        player = world.player
        self.plan = "vanish"
        self.timer = 0.0
        self.fleeing = flee
        self.animator.play("vanish", restart=True)
        if flee:
            # Away from the prince, to whichever side of the stage has more room.
            left, right = self.bounds
            room_left = player.body.centerx - left
            room_right = right - player.body.centerx
            target_x = player.body.centerx + (-1 if room_left > room_right else 1) * 7 * 32
        else:
            target_x = player.body.centerx - player.facing * 56
        left, right = self.bounds
        target_x = max(left + 20, min(right - 20, target_x))
        self.step_target = (target_x, self.floor)
        self._petal_burst(world, *self.center, outward=True)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "petal_whoosh")

    def update(self, dt: float, world: "World") -> None:
        if self.state == "vanished":
            self.time += dt
            self.timer += dt
            self.grace = 0.5
            tx, ty = self.step_target
            rng = world.particles.rng
            # Petals spiral in to where she will appear: the telegraph.
            for _ in range(3):
                a = rng.uniform(0, math.tau)
                r = 60 * (1 - min(1.0, self.timer / STEP_WARNING)) + 8
                world.particles.spawn(tx + math.cos(a) * r, ty - 20 + math.sin(a) * r * 0.6,
                                      -math.cos(a) * 80, -math.sin(a) * 50, life=0.35, kind=Kind.PETAL, size=2.0,
                                      color=PETAL_PINK if rng.random() < 0.5 else PETAL, front=True)
            if self.timer > STEP_WARNING:
                self.body.place_midbottom((tx, ty))
                self.body.velocity.update(0, 0)
                self.state = "fight"
                self.timer = 0.0
                self.face_player(world)
                if self.fleeing:
                    self.plan = "recover"
                    self.animator.play("appear", restart=True)
                else:
                    self.plan = "kick"
                    self.animator.play("kick", restart=True)
                self.veil.reset(self._veil_point(), self.facing)
                self._petal_burst(world, *self.center, outward=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "spin_kick")
            self._update_blades(dt, world)
            return
        super().update(dt, world)
        self.veil.update(dt, self._veil_point(), self.facing, -self.body.velocity.x * 0.8)
        self._update_blades(dt, world)

    def _veil_point(self) -> tuple[float, float]:
        anim = self.animator.current
        try:
            dx, dy = art.veil(anim, self.animator.frame_index)
        except KeyError:
            dx, dy = -6.0, -34.0
        return self.body.centerx + dx * self.facing, self.body.bottom + dy

    def _fan(self, world: "World") -> None:
        self.animator.play("throw", restart=True)
        player = world.player
        x, y = self.body.centerx + self.facing * 12, self.body.top + 10
        base = math.atan2(player.body.centery - y, player.body.centerx - x)
        for spread in (-0.22, 0.0, 0.22):
            self.blades.append(_Blade(x, y, base + spread))
        world.events.emit(EventType.MACHINE_CLUNK, (x, y), "petal_whoosh")

    def _update_blades(self, dt: float, world: "World") -> None:
        player = world.player
        for blade in self.blades:
            blade.age += dt
            wobble = math.sin(blade.age * 12) * 0.6
            blade.x += math.cos(blade.angle + wobble * 0.1) * 300 * dt
            blade.y += math.sin(blade.angle + wobble * 0.1) * 300 * dt
            if pygame.Rect(round(blade.x) - 6, round(blade.y) - 6, 12, 12).colliderect(player.rect):
                blade.alive = False
                strike_player(world, 1 if math.cos(blade.angle) > 0 else -1, 200)
            tx, ty = world.collision.tile_at(blade.x, blade.y)
            if blade.age > 2.0 or world.collision.get(tx, ty).name == "SOLID":
                blade.alive = False
                emitters.sparkle_burst(world.particles, blade.x, blade.y, PETAL_PINK, 4, 60)
        self.blades = [b for b in self.blades if b.alive]

    def on_interrupted(self, world: "World") -> None:
        self.plan = "dance"
        self.step_timer = 4.0

    def silence(self, world: "World", song) -> None:  # noqa: ANN001
        for blade in self.blades:
            if blade.alive and (song is None or song.reaches(blade.x, blade.y)):
                blade.alive = False
                self._petal_burst(world, blade.x, blade.y, outward=True)

    def stun(self, world: "World", seconds: float) -> None:
        if self.state == "vanished":
            # The song catches her mid-step: she tumbles out of the petals.
            self.body.place_midbottom(self.step_target)
            self.state = "fight"
        super().stun(world, seconds)

    def _petal_burst(self, world: "World", x: float, y: float, outward: bool) -> None:
        rng = world.particles.rng
        for k in range(22):
            a = k * math.tau / 22
            speed = rng.uniform(60, 180)
            world.particles.spawn(x, y, math.cos(a) * speed, math.sin(a) * speed * 0.7 - 40, life=rng.uniform(0.7, 1.3),
                                  kind=Kind.PETAL, size=rng.uniform(1.6, 2.6), color=PETAL_PINK if k % 3 else PETAL,
                                  gravity=60, drag=1.5, wobble=40, front=True)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state not in ("offstage", "vanished") and not self.gone:
            self.veil.draw(surface, camera)
        super().draw(surface, camera)
        if self.state == "vanished":
            self._draw_gathering(surface, camera)
        for blade in self.blades:
            x, y = camera.to_screen(blade.x, blade.y)
            back = (x - math.cos(blade.angle) * 14, y - math.sin(blade.angle) * 14)
            pygame.draw.line(surface, (255, 150, 170), back, (x, y), 2)
            blit_glow(surface, (x, y), 12, PETAL_PINK, 0.7)
            a = blade.age * 18
            for k in range(3):
                ang = a + k * math.tau / 3
                tip = (x + math.cos(ang) * 8, y + math.sin(ang) * 8)
                mid = (x + math.cos(ang) * 4, y + math.sin(ang) * 4)
                side = (math.cos(ang + 1.57) * 3, math.sin(ang + 1.57) * 3)
                pygame.draw.polygon(surface, PETAL_PINK if k else PETAL, [(x, y), (mid[0] + side[0], mid[1] + side[1]), tip,
                                                                           (mid[0] - side[0], mid[1] - side[1])])
            pygame.draw.circle(surface, (255, 236, 120), (x, y), 2)

    def _draw_gathering(self, surface: pygame.Surface, camera: Camera) -> None:
        """The warning: a whirlwind of blossom gathers where she will step out, and her ghost fills it."""
        tx, ty = camera.to_screen(*self.step_target)
        u = min(1.0, self.timer / STEP_WARNING)
        blit_glow(surface, (tx, ty - 22), round(26 + 18 * u), PETAL_PINK, 0.45 + 0.5 * u)
        ring = pygame.Surface((96, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (255, 170, 190, round(120 + 135 * u)), (4, 4, 88, 20), 3)
        pygame.draw.ellipse(ring, (255, 255, 255, round(90 * u)), (18, 9, 60, 10), 1)
        surface.blit(ring, (tx - 48, ty - 14))
        for k in range(14):
            a = self.time * 7 + k * math.tau / 14
            radius = (46 - 34 * u) * (0.7 + 0.3 * math.sin(k * 1.7))
            height = 6 + (k % 5) * 9
            x = tx + math.cos(a) * radius
            y = ty - height + math.sin(a) * radius * 0.25
            w = 4 + 2 * abs(math.cos(a * 2))
            pygame.draw.ellipse(surface, PETAL_PINK if k % 3 else PETAL, (x - w / 2, y - 2, w, 4))
        if u > 0.35:
            ghost = self.animations["kick"].image(0.0, flip_x=self.facing < 0).copy()
            ghost.fill((255, 170, 200, 0), special_flags=pygame.BLEND_RGBA_MAX)
            ghost.set_alpha(round(200 * (u - 0.35) / 0.65))
            surface.blit(ghost, ghost.get_rect(midbottom=(tx, ty + 2)))

    def lights(self) -> list[Light]:
        lights = super().lights()
        if self.state == "vanished":
            u = min(1.0, self.timer / STEP_WARNING)
            lights.append(Light(self.step_target[0], self.step_target[1] - 20, 80, PETAL_PINK, 0.6 + 0.4 * u, bloom=0.3 * u))
        for blade in self.blades[:4]:
            lights.append(Light(blade.x, blade.y, 26, PETAL_PINK, 0.6))
        return lights

    def dissolve(self, world: "World") -> None:
        self._petal_burst(world, *self.center, outward=True)
        self._petal_burst(world, self.body.centerx, self.body.top, outward=True)


# --- Layla, the water-weaver --------------------------------------------------------------------------
class Weaver(Bubbled):
    kind = "weaver"
    title = "Layla the Water-Weaver"
    sheet = art.WEAVER_SHEET
    max_hp = 5
    floats = True
    element = WATER

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        super().__init__(x, floor, sprites, bounds)
        self.whip_timer = 2.4
        self.whip = 0.0          # >0 while lashing: progress 0..1
        self.whip_charge = 0.0
        self.call_timer = 7.0
        self.called_tide = False

    def think(self, dt: float, world: "World") -> None:
        player = world.player
        self.called_tide = False
        if self.whip_charge > 0:
            self.whip_charge -= dt
            self.body.velocity.x = 0
            if self.whip_charge <= 0:
                self.whip = 0.001
                self.animator.play("whip", restart=True)
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "whip")
        elif self.whip > 0:
            self.whip += dt / 0.32
            for x, y in self.whip_points(world):
                if player.rect.collidepoint(x, y):
                    strike_player(world, self.facing, 340)
                    break
            if self.whip >= 1.0:
                self.whip = 0.0
                self.whip_timer = 3.0
                self.animator.play("idle")
        else:
            self.face_player(world)
            distance = self.body.centerx - player.body.centerx
            ideal = player.body.centerx + math.copysign(3.5 * 32, distance if distance else 1)
            self.walk_to(ideal, 60)
            if self.animator.current == "cast" and not self.animator.finished:
                self.body.velocity.x = 0
            else:
                self.animator.play("idle")
            self.whip_timer -= dt
            self.call_timer -= dt
            if self.whip_timer <= 0 and abs(distance) < 6 * 32:
                self.whip_charge = 0.5
                world.events.emit(EventType.MACHINE_CLUNK, self.center, "whip_charge")
            elif self.call_timer <= 0:
                self.call_timer = 9.0
                self.called_tide = True
                self.animator.play("cast", restart=True)
        self._physics(dt, world)

    def hover_height(self) -> float:
        # Without her bubble she rises on her pillar, out of a standing blade's reach.
        return 78.0 if self.exposed or (self.state == "hurt" and self.shield <= 0) else 22.0

    def whip_points(self, world: "World | None" = None) -> list[tuple[float, float]]:
        """The water whip as a chain of points from her hand, sweeping down."""
        hand_x = self.body.centerx + self.facing * 10
        hand_y = self.body.top + 8
        progress = min(1.0, self.whip)
        points = []
        for k in range(12):
            u = k / 11
            angle = (-1.1 + progress * 1.7) - u * 0.4 * (1 - progress)
            reach = u * 150 * min(1.0, progress * 2.5)
            x = hand_x + self.facing * math.cos(angle) * reach
            y = hand_y + math.sin(angle) * reach + math.sin(u * 6 + self.time * 20) * 3
            points.append((x, y))
        return points

    def on_interrupted(self, world: "World") -> None:
        if self.whip > 0:
            for x, y in self.whip_points()[::3]:
                emitters.droplet(world.particles, x, y, world.particles.rng.uniform(-60, 60), -80)
        self.whip = 0.0
        self.whip_charge = 0.0

    def silence(self, world: "World", song) -> None:  # noqa: ANN001
        if self.whip > 0 or self.whip_charge > 0:
            self.on_interrupted(world)

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        if not self.active and self.state != "defeated":
            return
        if self.state == "defeated":
            return
        # The pillar of water she stands on.
        x, top = camera.to_screen(self.body.centerx, self.body.bottom)
        floor = camera.to_screen(0, self.floor)[1]
        if floor - top > 2:
            column = pygame.Surface((24, floor - top + 6), pygame.SRCALPHA)
            for row in range(column.get_height()):
                wobble = math.sin(self.time * 8 + row * 0.4) * 2
                alpha = 150 - row * 2
                pygame.draw.line(column, (*WATER, max(40, alpha)), (6 + wobble, row), (18 + wobble, row))
            surface.blit(column, (x - 12, top - 2))
            pygame.draw.ellipse(surface, BUBBLE_LIGHT, (x - 14, floor - 4, 28, 7), 1)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state not in ("offstage", "vanished") and not self.gone:
            x, y = camera.to_screen(*self.center)
            blit_glow(surface, (x, y - 4), 30, (70, 170, 230), 0.45 + 0.1 * math.sin(self.time * 3))
        super().draw(surface, camera)

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.whip_charge > 0:
            hx, hy = camera.to_screen(self.body.centerx + self.facing * 10, self.body.top + 8)
            u = 1 - self.whip_charge / 0.5
            for k in range(3):
                r = 18 * (1 - u) + k * 4
                pygame.draw.circle(surface, BUBBLE_LIGHT, (hx, hy), max(2, round(r)), 1)
            blit_glow(surface, (hx, hy), 16, WATER, 0.8 * u)
        if self.whip > 0:
            points = [camera.to_screen(x, y) for x, y in self.whip_points()]
            pygame.draw.lines(surface, (30, 90, 140), False, points, 7)
            pygame.draw.lines(surface, WATER, False, points, 5)
            pygame.draw.lines(surface, BUBBLE_LIGHT, False, points, 2)
            blit_glow(surface, points[-1], 18, WATER, 0.8)

    def lights(self) -> list[Light]:
        if not self.active:
            return []
        lights = [Light(*self.center, 110, WATER, 0.7)]
        if self.shield_grow > 0.2:
            lights.append(Light(*self.center, 46, BUBBLE, 0.55 * self.shield_grow, bloom=0.15))
        return lights

    def dissolve(self, world: "World") -> None:
        emitters.splash(world.particles, self.body.centerx, self.floor, 2.0)
        emitters.sparkle_burst(world.particles, *self.center, BUBBLE_LIGHT, 16, 160)
