"""The Ifrit: the Book II boss, fought in the Court of the Lions.

A towering djinn of smoke and fire hovers over the arena. He can only be
hurt when stunned, and only a *ground pound* on one of his resting fists
stuns him. Then his head sinks to the floor and his crown jewel is open to a
dash, a slash, a pound, a stomp or a thrown star.

Attacks (faster and combined in later phases):
* Fire rain: arcing fireballs from his mouth.
* Fist slam: a fist hunts the prince, slams down and sends shockwaves
  rolling along the floor (jump them). The fist then rests: pound it!
* Fire breath (phase 2+): a jet sweeping the arena at head height.
  Slide under it.

Six hits over three phases. On defeat he is sucked back into a brass lamp,
the stolen dawn returns and the Sword of Light descends.
"""

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from entities.projectiles import Fireball
from rendering import emitters
from rendering.art.kit import Canvas
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from rendering.sprite_library import SpriteLibrary
from ui.text import HUD_STYLE, render_styled

if TYPE_CHECKING:
    from world.world import World

MAX_HEALTH = 6
HITS_PER_PHASE = 2
FIST_SIZE = (60, 44)
HEAD_RADIUS = 34
HOVER_HEIGHT = 250
# Bring the vulnerable head into standing slash / horizontal dash range.
# At 70px its bottom stayed above both hitboxes even after fully settling.
STUNNED_HEAD_HEIGHT = 50
WAVE_SPEED = 310.0
WAVE_HEIGHT = 22
BREATH_BAND = (16, 30)
SLAM_TELEGRAPH = 0.45  # seconds the fist hangs still before dropping  # hurt band above the floor, like the blade traps
SMOKE = (60, 30, 70)
FIRE = (255, 140, 50)
FIRE_HOT = (255, 230, 150)
SKIN = (170, 40, 60)
SKIN_DARK = (100, 20, 50)
GOLD = (236, 184, 64)


class Mode(Enum):
    DORMANT = auto()
    INTRO = auto()
    IDLE = auto()
    RAIN = auto()
    SLAM_AIM = auto()
    SLAM_DROP = auto()
    SLAM_REST = auto()
    BREATH_AIM = auto()
    BREATH = auto()
    STUNNED = auto()
    HURT = auto()
    DEFEAT = auto()
    GONE = auto()


class _Fist:
    def __init__(self, side: int, x: float, y: float) -> None:
        self.side = side
        self.x, self.y = x, y
        self.home = (x, y)
        self.slamming = False
        self.resting = False

    @property
    def rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, *FIST_SIZE)
        rect.midbottom = (round(self.x), round(self.y))
        return rect


class _Wave:
    def __init__(self, x: float, floor: float, direction: int) -> None:
        self.x = x
        self.floor = floor
        self.direction = direction
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - 10, round(self.floor) - WAVE_HEIGHT, 20, WAVE_HEIGHT)


def _gem_image() -> pygame.Surface:
    c = Canvas(22, 22, fringe=(40, 10, 20))
    c.star((230, 40, 80), (11, 11), 10, outline=(60, 10, 20), width=1)
    c.star((255, 160, 190), (11, 11), 5, rotation=math.pi / 8)
    return c.finish()


class Ifrit:
    def __init__(self, midbottom: tuple[float, float], arena: pygame.Rect, sprites: SpriteLibrary) -> None:
        self.arena = pygame.Rect(arena)
        self.sprites = sprites
        self.floor = float(arena.bottom)
        self.x = float(midbottom[0])
        self.head_y = self.floor - HOVER_HEIGHT - 200  # hidden above the arena until the intro
        self.target_head_y = self.head_y
        self.mode = Mode.DORMANT
        self.health = MAX_HEALTH
        self.timer = 0.0
        self.time = 0.0
        self.flash = 0.0
        self.dawn = 0.0
        self.camera_focus: tuple[float, float] | None = None
        self.fists = [_Fist(-1, self.x - 120, self.floor - 200), _Fist(1, self.x + 120, self.floor - 200)]
        self.waves: list[_Wave] = []
        self.breath_x = 0.0
        self.breath_dir = 1
        self._active_fist: _Fist | None = None
        self._rng = random.Random(7)
        self._volleys = 0
        self._gem = _gem_image()
        self._defeat_spin = 0.0
        self._pattern = 0

    # --- queries --------------------------------------------------------------------
    @property
    def phase(self) -> int:
        return min(3, 1 + (MAX_HEALTH - self.health) // HITS_PER_PHASE)

    @property
    def defeated(self) -> bool:
        return self.mode in (Mode.DEFEAT, Mode.GONE)

    @property
    def head_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, HEAD_RADIUS * 2, HEAD_RADIUS * 2)
        rect.center = (round(self.x), round(self.head_y))
        return rect

    @property
    def body_rect(self) -> pygame.Rect:
        # Only the chest is solid; the smoke below it is harmless.
        rect = pygame.Rect(0, 0, 110, 90)
        rect.midtop = (round(self.x), round(self.head_y + HEAD_RADIUS - 6))
        return rect

    def _vulnerable(self) -> bool:
        return self.mode == Mode.STUNNED

    # --- update -------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.flash = max(0.0, self.flash - dt * 3)
        self.timer -= dt
        player = world.player
        if self.mode == Mode.DORMANT:
            if self.arena.collidepoint(player.body.centerx, player.body.centery) and player.body.on_ground \
                    and player.body.centerx > self.arena.left + 5 * 32:
                self._start_intro(world)
            return
        if self.mode == Mode.GONE:
            self.dawn = min(1.0, self.dawn + dt * 0.35)
            return
        self._update_waves(dt, world)
        handler = {
            Mode.INTRO: self._intro, Mode.IDLE: self._idle, Mode.RAIN: self._rain,
            Mode.SLAM_AIM: self._slam_aim, Mode.SLAM_DROP: self._slam_drop, Mode.SLAM_REST: self._slam_rest,
            Mode.BREATH_AIM: self._breath_aim, Mode.BREATH: self._breath, Mode.STUNNED: self._stunned,
            Mode.HURT: self._hurt, Mode.DEFEAT: self._defeat,
        }[self.mode]
        handler(dt, world)
        # Float gently; the head eases toward its target height.
        self.head_y += (self.target_head_y - self.head_y) * min(1.0, dt * 3.0)
        for fist in self.fists:
            if not fist.slamming and not fist.resting:
                hx = self.x + fist.side * 130
                hy = self.head_y + 110 + math.sin(self.time * 2 + fist.side) * 10
                fist.x += (hx - fist.x) * min(1.0, dt * 4)
                fist.y += (hy - fist.y) * min(1.0, dt * 4)
        self._contact_damage(world)
        self._ambient_particles(world)

    def _set(self, mode: Mode, timer: float) -> None:
        self.mode = mode
        self.timer = timer

    def _start_intro(self, world: "World") -> None:
        self._set(Mode.INTRO, 3.2)
        # The arena's gates slam shut behind the prince.
        for gate in world.gates_in("arena"):
            gate.set_open(False, world)
        self.target_head_y = self.floor - HOVER_HEIGHT
        world.events.emit(EventType.BOSS_ROAR, (self.x, self.floor - 200), "intro")

    def _intro(self, dt: float, world: "World") -> None:
        self.camera_focus = (self.arena.centerx, self.arena.bottom - 170)
        if self.timer < 1.6 and self.timer + dt >= 1.6:
            world.events.emit(EventType.BOSS_ROAR, (self.x, self.head_y), "roar")
        if self.timer <= 0:
            self.camera_focus = None
            self._set(Mode.IDLE, 1.0)

    def _next_attack(self) -> Mode:
        phase = self.phase
        options = [Mode.RAIN, Mode.SLAM_AIM]
        if phase >= 2:
            options.append(Mode.BREATH_AIM)
        # Always come back to a slam soon: it's the only way to win.
        self._pattern += 1
        if self._pattern % 2 == 0:
            return Mode.SLAM_AIM
        return self._rng.choice(options)

    def _idle(self, dt: float, world: "World") -> None:
        player = world.player
        drift = player.body.centerx + math.sin(self.time * 0.7) * 160
        drift = max(self.arena.left + 180, min(self.arena.right - 180, drift))
        self.x += (drift - self.x) * min(1.0, dt * 0.8)
        self.target_head_y = self.floor - HOVER_HEIGHT + math.sin(self.time * 1.5) * 16
        if self.timer <= 0:
            mode = self._next_attack()
            if mode == Mode.RAIN:
                self._volleys = 2 + self.phase
                self._set(Mode.RAIN, 0.4)
            elif mode == Mode.SLAM_AIM:
                self._active_fist = min(self.fists, key=lambda f: abs(f.x - player.body.centerx))
                self._active_fist.slamming = True
                self._set(Mode.SLAM_AIM, 1.25 - 0.2 * (self.phase - 1) + SLAM_TELEGRAPH)
                world.events.emit(EventType.BOSS_ROAR, (self.x, self.head_y), "growl")
            else:
                self.breath_dir = 1 if player.body.centerx > self.x else -1
                self.target_head_y = self.floor - 150
                self._set(Mode.BREATH_AIM, 1.0)

    def _rain(self, dt: float, world: "World") -> None:
        if self.timer > 0:
            return
        player = world.player
        mouth = (self.x, self.head_y + 14)
        # A fan of fireballs around the prince with one shot left out, so
        # every volley has a readable gap to step into.
        shots = 3 + self.phase
        gap = self._rng.randrange(shots)
        for k in range(shots):
            if k == gap:
                continue
            target_x = player.body.centerx + (k - (shots - 1) / 2) * 90 + self._rng.uniform(-15, 15)
            flight = 1.1
            vx = (target_x - mouth[0]) / flight
            vy = (self.floor - 10 - mouth[1] - 0.5 * 700 * flight * flight) / flight
            world.spawn_projectile(Fireball(mouth, (vx, vy), self.sprites, gravity=700.0, lifetime=3.0, passes_walls=True))
        emitters.embers(world.particles, mouth[0], mouth[1], 10, 12)
        world.events.emit(EventType.FIRE_SHOT, mouth)
        self._volleys -= 1
        if self._volleys > 0:
            self._set(Mode.RAIN, 0.75 - 0.1 * self.phase)
        else:
            self._set(Mode.IDLE, 1.2)

    def _slam_aim(self, dt: float, world: "World") -> None:
        fist = self._active_fist
        assert fist is not None
        player = world.player
        if self.timer > SLAM_TELEGRAPH:
            tx = max(self.arena.left + 40, min(self.arena.right - 40, player.body.centerx))
            ty = self.floor - 190
            fist.x += (tx - fist.x) * min(1.0, dt * 6)
            fist.y += (ty - fist.y) * min(1.0, dt * 6)
        else:
            # Locked on: it stops following and trembles, then falls.
            fist.x += math.sin(self.time * 70) * 1.5
        if self.timer <= 0:
            self._set(Mode.SLAM_DROP, 1.0)

    def _slam_drop(self, dt: float, world: "World") -> None:
        fist = self._active_fist
        assert fist is not None
        fist.y = min(self.floor, fist.y + 1500 * dt)
        if fist.y >= self.floor:
            fist.slamming = False
            fist.resting = True
            for direction in (-1, 1):
                self.waves.append(_Wave(fist.x + direction * 34, self.floor, direction))
            other = self.fists[0] if fist is self.fists[1] else self.fists[1]
            # Phase 3: the idle fist thumps too - but never right on top of the prince.
            if self.phase >= 3 and abs(other.x - world.player.body.centerx) > 160:
                for direction in (-1, 1):
                    self.waves.append(_Wave(other.x + direction * 20, self.floor, direction))
            emitters.landing_dust(world.particles, fist.x, self.floor, 1.0, (200, 170, 180))
            emitters.shockwave(world.particles, fist.x, self.floor - 10, 120, (255, 200, 150))
            emitters.debris(world.particles, fist.x, self.floor, ((170, 150, 150), (120, 100, 110)), 12, 1.0)
            world.events.emit(EventType.BOSS_SLAM, (fist.x, self.floor))
            self._set(Mode.SLAM_REST, 2.4 - 0.3 * (self.phase - 1))

    def _slam_rest(self, dt: float, world: "World") -> None:
        fist = self._active_fist
        assert fist is not None
        player = world.player
        top = pygame.Rect(fist.rect.x - 4, fist.rect.y - 10, fist.rect.width + 8, 24)
        if player.is_pounding and player.rect.colliderect(top):
            self._stun(world)
            return
        if self.phase >= 3 and int(self.timer * 10) % 9 == 0 and self._rng.random() < 0.08:
            mouth = (self.x, self.head_y + 14)
            world.spawn_projectile(Fireball(mouth, (self._rng.uniform(-200, 200), -150), self.sprites,
                                            gravity=700.0, lifetime=3.0, passes_walls=True))
        if self.timer <= 0:
            fist.resting = False
            self._active_fist = None
            self._set(Mode.IDLE, 1.3 - 0.25 * (self.phase - 1))

    def _stun(self, world: "World") -> None:
        fist = self._active_fist
        if fist is not None:
            fist.resting = False
        self._active_fist = None
        player = world.player
        player.end_pound()
        player.body.velocity.y = -520
        self.target_head_y = self.floor - STUNNED_HEAD_HEIGHT
        self._set(Mode.STUNNED, 3.6)
        emitters.sparkle_burst(world.particles, player.body.centerx, player.body.bottom, (255, 230, 150), 16, 200)
        world.events.emit(EventType.BOSS_ROAR, (self.x, self.head_y), "stunned")

    def _breath_aim(self, dt: float, world: "World") -> None:
        # Glide to the far side, glowing, before sweeping the arena.
        side_x = self.arena.left + 120 if self.breath_dir > 0 else self.arena.right - 120
        self.x += (side_x - self.x) * min(1.0, dt * 3)
        if self.timer <= 0:
            self.breath_x = self.x
            self._set(Mode.BREATH, 99.0)
            world.events.emit(EventType.FIRE_SHOT, (self.x, self.floor - 23))

    def _breath(self, dt: float, world: "World") -> None:
        speed = 420 + 60 * self.phase
        self.breath_x += self.breath_dir * speed * dt
        rng = world.particles.rng
        for _ in range(4):
            world.particles.spawn(
                self.breath_x + rng.uniform(-30, 10) * self.breath_dir, self.floor - 23 + rng.uniform(-5, 5),
                self.breath_dir * rng.uniform(40, 160), rng.uniform(-30, 10), life=rng.uniform(0.3, 0.6),
                kind=Kind.GLOW, size=rng.uniform(8, 14), color=FIRE_HOT, color_end=FIRE, front=True,
            )
        player = world.player
        band = self._breath_rect()
        if band.colliderect(player.rect) and player.body.height >= player.physics.hitbox_height:
            player.take_damage(world)
        done = self.breath_x > self.arena.right - 20 if self.breath_dir > 0 else self.breath_x < self.arena.left + 20
        if done:
            self.target_head_y = self.floor - HOVER_HEIGHT
            self._set(Mode.IDLE, 1.0)

    def _breath_rect(self) -> pygame.Rect:
        start = self.x
        left, right = sorted((start, self.breath_x))
        low, high = BREATH_BAND
        return pygame.Rect(round(left), round(self.floor - high), round(right - left), high - low)

    def _stunned(self, dt: float, world: "World") -> None:
        # Dazed stars circle the jewel.
        if int(self.time * 20) % 3 == 0:
            angle = self.time * 5
            emitters.aura(world.particles, self.x + math.cos(angle) * 40, self.head_y - 40 + math.sin(angle) * 8,
                          (255, 240, 170), 3)
        if self.timer <= 0:
            self.target_head_y = self.floor - HOVER_HEIGHT
            world.events.emit(EventType.BOSS_ROAR, (self.x, self.head_y), "recover")
            self._set(Mode.IDLE, 1.0)

    def _hurt(self, dt: float, world: "World") -> None:
        if self.timer <= 0:
            self.target_head_y = self.floor - HOVER_HEIGHT
            self._set(Mode.IDLE, 1.4)

    def _register_hit(self, world: "World") -> None:
        self.health -= 1
        self.flash = 1.0
        world.events.emit(EventType.BOSS_HIT, (self.x, self.head_y - 30))
        emitters.sparkle_burst(world.particles, self.x, self.head_y, (255, 120, 150), 24, 260)
        emitters.shockwave(world.particles, self.x, self.head_y, 90, (255, 180, 200))
        player = world.player
        direction = 1 if player.body.centerx >= self.x else -1
        player.body.velocity.update(direction * 320, -480)
        # A moment of grace while he recoils, so the rebound never hurts.
        player._invulnerable_timer = max(player._invulnerable_timer, 1.2)
        if self.health <= 0:
            self._set(Mode.DEFEAT, 3.5)
            self.camera_focus = (self.x, self.floor - 150)
            world.events.emit(EventType.BOSS_DEFEATED, (self.x, self.head_y))
            self.waves.clear()
            for projectile in world.projectiles:
                if not projectile.friendly:
                    projectile.expire(world)
            return
        self.target_head_y = self.floor - HOVER_HEIGHT - 40
        self._set(Mode.HURT, 1.2)

    def _defeat(self, dt: float, world: "World") -> None:
        # Sucked, spinning, into a brass lamp that clatters onto the floor.
        self._defeat_spin += dt
        self.target_head_y = self.floor - 60
        rng = world.particles.rng
        for _ in range(3):
            world.particles.spawn(self.x + rng.uniform(-80, 80), self.head_y + rng.uniform(-80, 120),
                                  (self.x - (self.x + rng.uniform(-80, 80))) * 2, rng.uniform(40, 120),
                                  life=0.6, kind=Kind.SMOKE, size=rng.uniform(10, 22), color=SMOKE, alpha=0.7)
        if self.timer <= 0:
            self._set(Mode.GONE, 0.0)
            self.camera_focus = None
            emitters.sparkle_burst(world.particles, self.x, self.floor - 20, GOLD, 30, 220)
            emitters.shockwave(world.particles, self.x, self.floor - 20, 160, (255, 240, 200))
            from objects.triggers import Goal

            sword_rect = pygame.Rect(0, 0, 64, 32)
            sword_rect.midbottom = (round(self.arena.centerx), round(self.floor))
            world.goals.append(Goal(sword_rect, "sword"))
            world.events.emit(EventType.SWORD_APPEARED, sword_rect.midbottom)

    # --- hits from the prince ---------------------------------------------------------------
    def hit_by_pound(self, area: pygame.Rect, world: "World") -> None:
        """The existing ground-pound shockwave also strikes a resting fist."""
        fist = self._active_fist
        if (self.mode == Mode.SLAM_REST and fist is not None and fist.resting
                and world.player.is_controllable and area.colliderect(fist.rect)):
            self._stun(world)

    def hit_by_star(self, rect: pygame.Rect, world: "World", direction: int) -> bool:
        if self._vulnerable() and rect.colliderect(self.head_rect):
            self._register_hit(world)
            return True
        return False

    def hit_by_move(self, area: pygame.Rect, world: "World", direction: int) -> None:
        if self._vulnerable() and area.colliderect(self.head_rect):
            self._register_hit(world)

    def _contact_damage(self, world: "World") -> None:
        player = world.player
        if not player.is_controllable:
            return
        rect = player.rect
        if self._vulnerable():
            # A slash, a stomp or a pound on the dazed head.
            attack = player.attack_rect
            if attack is not None and attack.colliderect(self.head_rect):
                self._register_hit(world)
                return
            falling_on_head = player.body.velocity.y > 0 and player.previous_bottom <= self.head_rect.top + 12
            if falling_on_head and rect.colliderect(self.head_rect):
                self._register_hit(world)
            return
        # Protection blocks incoming damage, not the prince's own attacks.
        if not player.can_be_hurt:
            return
        if self.defeated or self.mode in (Mode.DORMANT, Mode.INTRO, Mode.HURT):
            return
        for fist in self.fists:
            danger = fist.slamming and self.mode == Mode.SLAM_DROP
            if danger and rect.colliderect(fist.rect.inflate(-10, -6)):
                player.take_damage(world)
                return
        if rect.colliderect(self.head_rect.inflate(-16, -16)) or rect.colliderect(self.body_rect.inflate(-40, -40)):
            player.take_damage(world)

    def _update_waves(self, dt: float, world: "World") -> None:
        player = world.player
        for wave in self.waves:
            wave.x += wave.direction * WAVE_SPEED * dt
            if not self.arena.inflate(-10, 0).collidepoint(wave.x, wave.floor - 5):
                wave.alive = False
            if player.can_be_hurt and wave.rect.colliderect(player.rect):
                player.take_damage(world)
            if int(self.time * 40) % 2 == 0:
                emitters.embers(world.particles, wave.x, wave.floor - 6, 1, 6)
        self.waves = [wave for wave in self.waves if wave.alive]

    def _ambient_particles(self, world: "World") -> None:
        if self.mode in (Mode.GONE, Mode.DORMANT):
            return
        rng = world.particles.rng
        # The smoke tail streaming down from his waist.
        base_y = self.head_y + HEAD_RADIUS + 120
        world.particles.spawn(self.x + rng.uniform(-30, 30), base_y + rng.uniform(-10, 30), rng.uniform(-30, 30),
                              rng.uniform(20, 60), life=rng.uniform(0.8, 1.4), kind=Kind.SMOKE,
                              size=rng.uniform(14, 26), size_end=4, color=SMOKE, alpha=0.6, front=False)
        if rng.random() < 0.5:
            world.particles.spawn(self.x + rng.uniform(-50, 50), self.head_y + rng.uniform(-40, 80),
                                  rng.uniform(-20, 20), -rng.uniform(30, 90), life=rng.uniform(0.5, 1.0),
                                  kind=Kind.GLOW, size=rng.uniform(4, 8), color=FIRE_HOT, color_end=FIRE, front=True)

    # --- lighting and drawing -------------------------------------------------------------------
    def lights(self) -> list[Light]:
        if self.mode in (Mode.GONE, Mode.DORMANT):
            return []
        lights = [Light(self.x, self.head_y + 40, 320, (255, 120, 70), 1.0, flicker=0.4, bloom=0.3)]
        for fist in self.fists:
            lights.append(Light(fist.x, fist.y - 20, 110, (255, 140, 80), 0.8, flicker=0.5))
        for wave in self.waves:
            lights.append(Light(wave.x, wave.floor - 10, 80, (255, 150, 60), 0.9))
        if self.mode == Mode.BREATH:
            lights.append(Light(self.breath_x, self.floor - 23, 160, (255, 170, 80), 1.0, bloom=0.4))
        return lights

    def debug_rects(self) -> list[pygame.Rect]:
        return [self.head_rect, self.body_rect] + [fist.rect for fist in self.fists] + [w.rect for w in self.waves]

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.mode in (Mode.DORMANT, Mode.GONE):
            return
        # The smoky torso and arms, behind the fists and the prince.
        x, y = camera.to_screen(self.x, self.head_y)
        pulse = math.sin(self.time * 3)
        blit_glow(surface, (x, y + 60), 170, (160, 50, 40), 0.55)
        torso = [(x - 70, y + 20), (x + 70, y + 20), (x + 52, y + 110), (x + 18, y + 170 + pulse * 6),
                 (x - 18, y + 170 - pulse * 6), (x - 52, y + 110)]
        pygame.draw.polygon(surface, SKIN_DARK, torso)
        chest = [(x - 58, y + 26), (x + 58, y + 26), (x + 42, y + 100), (x - 42, y + 100)]
        pygame.draw.polygon(surface, SKIN, chest)
        # Golden armbands and a sash.
        pygame.draw.line(surface, GOLD, (x - 44, y + 96), (x + 44, y + 96), 5)
        for fist in self.fists:
            fx, fy = camera.to_screen(fist.x, fist.y - FIST_SIZE[1] / 2)
            shoulder = (x + fist.side * 64, y + 34)
            elbow = ((shoulder[0] + fx) / 2 + fist.side * 30, (shoulder[1] + fy) / 2 + 10)
            pygame.draw.line(surface, SKIN_DARK, shoulder, elbow, 24)
            pygame.draw.line(surface, SKIN_DARK, elbow, (fx, fy), 20)
            pygame.draw.line(surface, SKIN, shoulder, elbow, 14)
            pygame.draw.line(surface, SKIN, elbow, (fx, fy), 11)
            pygame.draw.circle(surface, GOLD, (round(elbow[0]), round(elbow[1])), 9, 3)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for wave in self.waves:
            rect = camera.apply(wave.rect)
            flame = [(rect.left, rect.bottom), (rect.centerx - 6, rect.top + 6), (rect.centerx, rect.top - 6),
                     (rect.centerx + 6, rect.top + 4), (rect.right, rect.bottom)]
            pygame.draw.polygon(surface, FIRE, flame)
            pygame.draw.polygon(surface, FIRE_HOT, [(rect.left + 5, rect.bottom), (rect.centerx, rect.top + 4),
                                                    (rect.right - 5, rect.bottom)])
        if self.mode == Mode.BREATH:
            band = camera.apply(self._breath_rect())
            if band.width > 0:
                jet = pygame.Surface(band.size, pygame.SRCALPHA)
                jet.fill((255, 150, 60, 170))
                surface.blit(jet, band)
                pygame.draw.line(surface, FIRE_HOT, band.midleft, band.midright, 4)
        if self.mode == Mode.BREATH_AIM:
            # Telegraph: a flickering warning line at head height.
            y = camera.to_screen(0, self.floor - 23)[1]
            left = camera.to_screen(self.arena.left, 0)[0]
            right = camera.to_screen(self.arena.right, 0)[0]
            if int(self.time * 12) % 2 == 0:
                pygame.draw.line(surface, (255, 120, 60), (left, y), (right, y), 2)
        if self.mode in (Mode.DORMANT, Mode.GONE):
            if self.mode == Mode.GONE:
                self._draw_lamp(surface, camera)
            return
        for fist in self.fists:
            self._draw_fist(surface, camera, fist)
        self._draw_head(surface, camera)

    def _draw_fist(self, surface: pygame.Surface, camera: Camera, fist: _Fist) -> None:
        rect = camera.apply(fist.rect)
        if fist.slamming and self.mode == Mode.SLAM_AIM:
            # Shadow on the floor where it will land.
            sx = rect.centerx
            sy = camera.to_screen(0, self.floor)[1]
            width = 50 + 30 * math.sin(self.time * 10)
            pygame.draw.ellipse(surface, (20, 10, 20), (sx - width / 2, sy - 6, width, 10))
        pygame.draw.rect(surface, SKIN_DARK, rect.inflate(6, 6), border_radius=14)
        pygame.draw.rect(surface, SKIN, rect, border_radius=12)
        for k in range(4):
            kx = rect.left + 8 + k * 12
            pygame.draw.line(surface, SKIN_DARK, (kx, rect.top + 6), (kx, rect.top + 18), 3)
        pygame.draw.rect(surface, GOLD, (rect.left, rect.bottom - 12, rect.width, 6))
        if fist.resting:
            pulse = 0.5 + 0.5 * math.sin(self.time * 8)
            blit_glow(surface, (rect.centerx, rect.top), 30, (255, 220, 120), 0.3 + 0.4 * pulse)
            # "Pound me" arrow.
            ax, ay = rect.centerx, rect.top - 30 - 6 * pulse
            pygame.draw.polygon(surface, (255, 230, 150), ((ax - 8, ay), (ax + 8, ay), (ax, ay + 12)))

    def _draw_head(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.x, self.head_y)
        if self.mode == Mode.DEFEAT:
            scale = max(0.05, self.timer / 3.5)
            radius = max(4, round(HEAD_RADIUS * scale))
            pygame.draw.circle(surface, SKIN, (x, y), radius)
            blit_glow(surface, (x, y), radius * 3, (255, 180, 120), 0.8)
            return
        # Flaming hair behind the head.
        for k in range(7):
            angle = math.pi + k * math.pi / 6
            flick = math.sin(self.time * 9 + k) * 6
            tip = (x + math.cos(angle) * 55, y + math.sin(angle) * (60 + flick) - 10)
            base_a = (x + math.cos(angle - 0.25) * 28, y + math.sin(angle - 0.25) * 28)
            base_b = (x + math.cos(angle + 0.25) * 28, y + math.sin(angle + 0.25) * 28)
            pygame.draw.polygon(surface, FIRE, (base_a, tip, base_b))
            pygame.draw.polygon(surface, FIRE_HOT, (base_a, ((base_a[0] + tip[0]) / 2, (base_a[1] + tip[1]) / 2 + 4), base_b))
        color = SKIN if self.flash <= 0 else (255, 230, 230)
        pygame.draw.circle(surface, SKIN_DARK, (x, y), HEAD_RADIUS + 3)
        pygame.draw.circle(surface, color, (x, y), HEAD_RADIUS)
        # Horns.
        for side in (-1, 1):
            horn = [(x + side * 20, y - 24), (x + side * 44, y - 58), (x + side * 30, y - 20)]
            pygame.draw.polygon(surface, (240, 220, 190), horn)
            pygame.draw.polygon(surface, (90, 60, 50), horn, 2)
        # Turban band and the crown jewel.
        pygame.draw.rect(surface, GOLD, (x - HEAD_RADIUS + 4, y - 22, HEAD_RADIUS * 2 - 8, 10), border_radius=4)
        gem = self._gem
        if self._vulnerable():
            blit_glow(surface, (x, y - 17), 34, (255, 80, 130), 0.7 + 0.3 * math.sin(self.time * 10))
        surface.blit(gem, gem.get_rect(center=(x, y - 17)))
        # Eyes: burning slits, wide and dizzy when stunned.
        stunned = self.mode == Mode.STUNNED
        for side in (-1, 1):
            ex = x + side * 13
            if stunned:
                spin = self.time * 12 * side
                pygame.draw.circle(surface, FIRE_HOT, (ex, y + 2), 7, 2)
                pygame.draw.line(surface, FIRE_HOT, (ex, y + 2), (ex + math.cos(spin) * 6, y + 2 + math.sin(spin) * 6), 2)
            else:
                pygame.draw.polygon(surface, FIRE_HOT, ((ex - 9, y - 2 + side), (ex + 9, y - 2 - side), (ex + 5, y + 5)))
        # Mouth: a glowing grin, gaping when breathing fire.
        if self.mode in (Mode.BREATH, Mode.BREATH_AIM, Mode.RAIN, Mode.INTRO):
            pygame.draw.ellipse(surface, (60, 10, 20), (x - 14, y + 12, 28, 18))
            pygame.draw.ellipse(surface, FIRE, (x - 9, y + 16, 18, 10))
        else:
            pygame.draw.arc(surface, FIRE_HOT, (x - 16, y + 4, 32, 20), math.pi + 0.3, 2 * math.pi - 0.3, 3)
        # A curled beard of smoke.
        pygame.draw.polygon(surface, SKIN_DARK, ((x - 16, y + 26), (x + 16, y + 26), (x, y + 52)))

    def _draw_lamp(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.x, self.floor)
        pygame.draw.ellipse(surface, (160, 110, 40), (x - 22, y - 16, 44, 16))
        pygame.draw.ellipse(surface, GOLD, (x - 18, y - 16, 36, 12))
        pygame.draw.polygon(surface, GOLD, ((x + 16, y - 12), (x + 34, y - 20), (x + 30, y - 14)))
        pygame.draw.arc(surface, GOLD, (x - 32, y - 20, 16, 14), 1.2, 4.8, 3)
        wisp = (x + 34, y - 26 - math.sin(self.time * 3) * 4)
        blit_glow(surface, wisp, 12, (200, 120, 220), 0.6)

    def draw_health_bar(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if self.mode in (Mode.DORMANT, Mode.GONE):
            return
        width = 420
        rect = pygame.Rect(0, 0, width, 14)
        rect.midtop = (surface.get_width() // 2, 78)
        pygame.draw.rect(surface, (20, 10, 16), rect.inflate(6, 6), border_radius=6)
        pygame.draw.rect(surface, (70, 20, 30), rect, border_radius=4)
        fill = rect.copy()
        fill.width = round(width * max(0, self.health) / MAX_HEALTH)
        pygame.draw.rect(surface, (230, 60, 70) if self.flash <= 0 else (255, 230, 230), fill, border_radius=4)
        for k in range(1, MAX_HEALTH):
            tick = rect.left + round(width * k / MAX_HEALTH)
            pygame.draw.line(surface, (20, 10, 16), (tick, rect.top), (tick, rect.bottom), 2)
        label = render_styled(font, "THE IFRIT", HUD_STYLE)
        surface.blit(label, label.get_rect(midtop=(rect.centerx, rect.bottom + 4)))
