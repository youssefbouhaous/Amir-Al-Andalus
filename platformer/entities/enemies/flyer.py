import math
from collections.abc import Mapping
from typing import TYPE_CHECKING

from core.settings import ENEMY
from entities.enemies.enemy import Enemy, EnemyState
from physics.collision import move_body
from rendering.animation import Animation
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from world.world import World


class Flyer(Enemy):
    """A jinn wisp: patrols around its spawn point while bobbing up and down.

    Ignores gravity until stomped, then drops out of the sky. Leaves a faint
    trail of violet smoke.
    """

    turns_on_enemy_contact = False
    poof_color = (190, 150, 240)

    def __init__(
        self,
        midbottom: tuple[float, float],
        animations: Mapping[str, Animation],
        patrol_distance: float,
        facing: int = -1,
        vertical: bool = False,
    ) -> None:
        super().__init__(midbottom, ENEMY.flyer_hitbox, animations, facing)
        self._vertical = vertical
        self._origin = (self.body.x, self.body.y)
        self._patrol = patrol_distance
        self._time = 0.0
        self._smoke_timer = 0.0

    def behave(self, dt: float, world: "World") -> None:
        self._time += dt
        body = self.body
        angular = math.tau * ENEMY.flyer_bob_frequency
        if self._vertical:
            # Rise and fall along a column instead of patrolling sideways.
            body.velocity.x = math.cos(angular * self._time) * 12
            speed = ENEMY.flyer_speed * self.facing
            body.velocity.y = speed
            move_body(body, dt, world.collision)
            if body.hit_ceiling or body.y <= self._origin[1] - self._patrol:
                self.facing = 1
            elif body.on_ground or body.y >= self._origin[1] + self._patrol:
                self.facing = -1
        else:
            body.velocity.x = self.facing * ENEMY.flyer_speed
            # Velocity is the derivative of a sine bob, so position follows a sine
            # wave while still going through collision.
            body.velocity.y = ENEMY.flyer_bob_amplitude * angular * math.cos(angular * self._time)
            move_body(body, dt, world.collision)
            if body.hit_wall:
                self.facing = -body.hit_wall
            elif self.facing > 0 and body.x >= self._origin[0] + self._patrol:
                self.facing = -1
            elif self.facing < 0 and body.x <= self._origin[0] - self._patrol:
                self.facing = 1

        self._smoke_timer -= dt
        if self._smoke_timer <= 0:
            self._smoke_timer = 0.07
            rng = world.particles.rng
            world.particles.spawn(
                body.centerx - self.facing * 6, body.bottom, rng.uniform(-10, 10), rng.uniform(10, 30),
                life=0.6, kind=Kind.SMOKE, size=3, size_end=7, color=(170, 120, 230), alpha=0.5, front=False,
            )

    def on_stomped(self, world: "World") -> bool:
        self._set_state(EnemyState.KNOCKED_OUT)
        self.body.velocity.update(0, 0)
        return True

    def lights(self) -> list[Light]:
        if self.state != EnemyState.ACTIVE:
            return []
        return [Light(self.body.centerx, self.body.centery, 70, (190, 140, 255), 0.7, flicker=0.3)]
