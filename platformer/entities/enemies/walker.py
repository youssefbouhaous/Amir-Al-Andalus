from collections.abc import Mapping
from typing import TYPE_CHECKING

from core.settings import ENEMY
from entities.enemies.enemy import Enemy
from physics.collision import apply_gravity, move_body
from rendering.animation import Animation

if TYPE_CHECKING:
    from world.world import World

# How far past its front edge a walker looks for ground.
EDGE_PROBE_DISTANCE = 1.0


class Walker(Enemy):
    """Walks in one direction, turns at walls.

    With ``edge_aware`` it also turns at ledges, so it patrols its platform
    instead of walking off.
    """

    poof_color = (220, 180, 120)

    def __init__(
        self,
        midbottom: tuple[float, float],
        animations: Mapping[str, Animation],
        facing: int = -1,
        edge_aware: bool = False,
        speed: float = ENEMY.walker_speed,
        hitbox: tuple[float, float] = ENEMY.walker_hitbox,
    ) -> None:
        super().__init__(midbottom, hitbox, animations, facing)
        self.edge_aware = edge_aware
        self._speed = speed

    def behave(self, dt: float, world: "World") -> None:
        body = self.body
        body.velocity.x = self.facing * self._speed
        apply_gravity(body, ENEMY.gravity, ENEMY.terminal_velocity, dt)
        move_body(body, dt, world.collision, world.platforms)

        if body.hit_wall:
            self.facing = -body.hit_wall
        elif self.edge_aware and body.on_ground and not self._ground_ahead(world):
            self.turn_around()

    def _ground_ahead(self, world: "World") -> bool:
        if self.body.ground_platform is not None:
            return True
        probe_x = (
            self.body.right + EDGE_PROBE_DISTANCE
            if self.facing > 0
            else self.body.left - EDGE_PROBE_DISTANCE
        )
        return world.collision.is_standable(probe_x, self.body.bottom + EDGE_PROBE_DISTANCE)
