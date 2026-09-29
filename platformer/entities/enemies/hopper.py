from collections.abc import Mapping
from typing import TYPE_CHECKING

from core.settings import ENEMY
from entities.enemies.enemy import Enemy
from physics.collision import apply_gravity, move_body
from rendering import emitters
from rendering.animation import Animation

if TYPE_CHECKING:
    from world.world import World

# The jar crouches for this long before each hop (anticipation).
CROUCH_TIME = 0.22


class Hopper(Enemy):
    """Rests on the ground, crouches, then jumps forward. Turns at walls."""

    poof_color = (214, 140, 100)

    def __init__(
        self, midbottom: tuple[float, float], animations: Mapping[str, Animation], facing: int = -1
    ) -> None:
        super().__init__(midbottom, ENEMY.hopper_hitbox, animations, facing)
        self._rest_timer = 0.0
        self._was_on_ground = True

    def behave(self, dt: float, world: "World") -> None:
        body = self.body
        if body.on_ground:
            body.velocity.x = 0.0
            self._rest_timer += dt
            if self._rest_timer >= ENEMY.hopper_rest_time:
                self._rest_timer = 0.0
                body.velocity.y = -ENEMY.hopper_jump_velocity
                body.velocity.x = self.facing * ENEMY.hopper_speed
        else:
            body.velocity.x = self.facing * ENEMY.hopper_speed

        apply_gravity(body, ENEMY.gravity, ENEMY.terminal_velocity, dt)
        move_body(body, dt, world.collision, world.platforms)
        if body.hit_wall:
            self.facing = -body.hit_wall
        if body.on_ground and not self._was_on_ground:
            emitters.landing_dust(world.particles, body.centerx, body.bottom, 0.3, world.dust_color)
        self._was_on_ground = body.on_ground
        if not body.on_ground:
            self.animator.play("jump")
        elif self._rest_timer > ENEMY.hopper_rest_time - CROUCH_TIME:
            self.animator.play("crouch")
        else:
            self.animator.play("walk")
