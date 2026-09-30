"""Four readable encounters: each has a tell, a commitment, and a counter."""

import math

import pygame

from core.events import EventType
from core.settings import ENEMY
from entities.enemies.enemy import Enemy, EnemyState
from objects.mechanisms import DashLantern
from physics.collision import apply_gravity, move_body
from rendering import emitters
from rendering.lighting import Light


class GroundPerformer(Enemy):
    turns_on_enemy_contact = False

    def __init__(self, midbottom, animations, facing=-1, hitbox=(26, 36)):
        super().__init__(midbottom, hitbox, animations, facing)
        self.home_x = midbottom[0]
        self.phase = "walk"
        self.phase_time = 0.0
        self._block_timer = 0.0

    def change_phase(self, phase):
        self.phase = phase
        self.phase_time = 0.0
        self.animator.play(phase, restart=True)

    def ground_step(self, dt, world, speed):
        self._block_timer = max(0.0, self._block_timer - dt)
        body = self.body
        probe = body.right + 5 if self.facing > 0 else body.left - 5
        if body.on_ground and not world.collision.is_standable(probe, body.bottom + 2):
            speed = 0
        body.velocity.x = self.facing * speed
        apply_gravity(body, ENEMY.gravity, ENEMY.terminal_velocity, dt)
        move_body(body, dt, world.collision, world.platforms)

    def block(self, world):
        if self._block_timer <= 0:
            emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery,
                                  (170, 230, 255), 5, 90)
            world.events.emit(EventType.PROJECTILE_BLOCKED, self.body.midbottom)
            self._block_timer = .2


class MirrorDuelist(GroundPerformer):
    """Faces you while guarding; locks its aim before a lunge. Flank or wait."""
    poof_color = (143, 218, 222)

    def exposed(self, direction):
        return self.phase == "recover" or direction == self.facing

    def behave(self, dt, world):
        self.phase_time += dt
        dx = world.player.body.centerx - self.body.centerx
        speed = 0
        if self.phase == "walk":
            self.facing = 1 if dx > 0 else -1
            if abs(dx) < 155 and abs(world.player.body.bottom - self.body.bottom) < 80:
                self.change_phase("windup")
            elif abs(self.body.centerx - self.home_x) > 8:
                self.facing = 1 if self.home_x > self.body.centerx else -1
                speed = 45
        elif self.phase == "windup" and self.phase_time >= .6:
            self.change_phase("lunge")
        elif self.phase == "lunge":
            speed = 240
            if self.phase_time >= .28 or self.body.hit_wall:
                self.change_phase("recover")
                speed = 0
        elif self.phase == "recover" and self.phase_time >= 1.05:
            self.change_phase("walk")
        self.ground_step(dt, world, speed)

    def on_slashed(self, world, direction):
        if self.exposed(direction):
            return super().on_slashed(world, direction)
        self.block(world)
        return False

    def on_starred(self, world, direction):
        if self.exposed(direction):
            return super().on_starred(world, direction)
        self.block(world)
        return True

    def on_stomped(self, world):
        if self.phase == "recover":
            return super().on_stomped(world)
        self.block(world)
        return False


class SandBurrower(GroundPerformer):
    """Never damages while hidden: sand ripples precede the exposed sandfish."""
    poof_color = (227, 176, 100)

    def __init__(self, midbottom, animations, facing=-1):
        super().__init__(midbottom, animations, facing, (28, 26))

    @property
    def is_dangerous(self):
        return super().is_dangerous and self.phase == "exposed"

    def behave(self, dt, world):
        self.phase_time += dt
        speed = 0
        if self.phase == "walk":
            dx = world.player.body.centerx - self.body.centerx
            self.facing = 1 if dx > 0 else -1
            target = max(self.home_x - 85, min(self.home_x + 85, world.player.body.centerx))
            speed = 65 if abs(target - self.body.centerx) > 15 else 0
            if self.phase_time >= 1.4 and abs(dx) < 220:
                self.change_phase("warn")
        elif self.phase == "warn" and self.phase_time >= .75:
            self.change_phase("emerge")
        elif self.phase == "emerge" and self.phase_time >= .3:
            self.change_phase("exposed")
        elif self.phase == "exposed" and self.phase_time >= 1.25:
            self.change_phase("retreat")
        elif self.phase == "retreat" and self.phase_time >= .3:
            self.change_phase("walk")
        self.ground_step(dt, world, speed)

    def on_stomped(self, world):
        return super().on_stomped(world) if self.is_dangerous else False

    def on_starred(self, world, direction):
        return super().on_starred(world, direction) if self.is_dangerous else False


class ClockworkGuardian(GroundPerformer):
    """Bronze petals unfold, exposing the turquoise heart for a full second."""
    poof_color = (213, 168, 92)

    def __init__(self, midbottom, animations, facing=-1):
        super().__init__(midbottom, animations, facing, (32, 40))

    def behave(self, dt, world):
        self.phase_time += dt
        durations = {"walk": 1.5, "unfold": .45, "open": 1.25, "close": .4}
        sequence = {"walk": "unfold", "unfold": "open", "open": "close", "close": "walk"}
        if self.phase_time >= durations[self.phase]:
            self.change_phase(sequence[self.phase])
        if self.phase == "walk" and abs(self.body.centerx - self.home_x) > 52:
            self.facing = 1 if self.home_x > self.body.centerx else -1
        self.ground_step(dt, world, 28 if self.phase == "walk" else 0)
        if self.body.hit_wall:
            self.facing = -self.body.hit_wall

    def on_slashed(self, world, direction):
        if self.phase == "open":
            return super().on_slashed(world, direction)
        self.block(world)
        return False

    def on_starred(self, world, direction):
        if self.phase == "open":
            return super().on_starred(world, direction)
        self.block(world)
        return True

    def on_stomped(self, world):
        if self.phase == "open":
            return super().on_stomped(world)
        self.block(world)
        return False

    def lights(self):
        return [Light(self.body.centerx, self.body.centery, 55, (98, 237, 208), .65)] if self.phase == "open" else []


class LanternThief(Enemy):
    """A daylight jewel moth that borrows a lamp, never permanently removes it."""
    turns_on_enemy_contact = False
    poof_color = (169, 139, 222)

    def __init__(self, midbottom, animations, facing=-1):
        super().__init__(midbottom, (24, 26), animations, facing)
        self.home = pygame.Vector2(midbottom)
        self._time = 0.0
        self._rest = 1.0
        self.lantern = None

    def behave(self, dt, world):
        self._time += dt
        self._rest = max(0.0, self._rest - dt)
        previous = self.body.centerx
        self.body.place_midbottom((self.home.x + math.sin(self._time * 1.6) * 55,
                                   self.home.y + math.sin(self._time * 3.2) * 12))
        self.facing = 1 if self.body.centerx > previous else -1
        if self.lantern is not None and self.lantern.borrower is not self:
            self.lantern = None
            self._rest = 4.0
        if self.lantern is None and self._rest <= 0 and abs(world.player.body.centerx - self.home.x) < 240:
            lamps = [p for p in world.props if isinstance(p, DashLantern) and p.lit
                     and pygame.Vector2(p.rect.center).distance_to(self.home) < 150]
            if lamps:
                lamp = min(lamps, key=lambda p: pygame.Vector2(p.rect.center).distance_to(self.home))
                if lamp.borrow(self):
                    self.lantern = lamp
                    emitters.sparkle_burst(world.particles, *lamp.rect.center, (175, 210, 255), 8, 100)
        self.animator.play("carry" if self.lantern else "walk")

    def _return_lantern(self, world):
        if self.lantern is None:
            return
        self.lantern.return_light(self)
        emitters.sparkle_burst(world.particles, *self.lantern.rect.center, (160, 240, 255), 12, 130)
        self.lantern = None
        if world.player.refill_dash():
            world.events.emit(EventType.DASH_REFILLED, world.player.body.midbottom)

    def knock_out(self, world, direction):
        self._return_lantern(world)
        super().knock_out(world, direction)

    def on_starred(self, world, direction):
        result = super().on_starred(world, direction)
        if result:
            self._return_lantern(world)
        return result

    def on_stomped(self, world):
        result = super().on_stomped(world)
        if result:
            self._return_lantern(world)
        return result

    def draw(self, surface, camera):
        if self.lantern and self.state == EnemyState.ACTIVE:
            a = camera.to_screen(*self.lantern.rect.center)
            b = camera.to_screen(self.body.centerx, self.body.bottom - 6)
            # A dashed thread visibly connects the stolen light to its lamp.
            for i in range(0, 12, 2):
                start = pygame.Vector2(a).lerp(b, i / 12)
                end = pygame.Vector2(a).lerp(b, (i + 1) / 12)
                pygame.draw.line(surface, (150, 187, 238), start, end, 1)
        super().draw(surface, camera)
