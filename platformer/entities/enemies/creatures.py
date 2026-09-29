"""The later enemies: hedgehog (can't be stomped), bat (dives), ghul (sneaks)."""

import math
from collections.abc import Mapping
from enum import Enum, auto
from typing import TYPE_CHECKING

from core.events import EventType
from core.settings import ENEMY
from entities.enemies.enemy import Enemy, EnemyState
from entities.enemies.walker import Walker
from physics.collision import move_body
from rendering import emitters
from rendering.animation import Animation
from rendering.lighting import Light

if TYPE_CHECKING:
    from world.world import World


class Hedgehog(Walker):
    """A spiky walker: stomping it hurts. Knock it out with a star or a bump."""

    stompable = False
    poof_color = (170, 130, 100)

    def __init__(self, midbottom: tuple[float, float], animations: Mapping[str, Animation],
                 facing: int = -1, edge_aware: bool = True) -> None:
        super().__init__(midbottom, animations, facing, edge_aware, speed=ENEMY.hedgehog_speed,
                         hitbox=ENEMY.hedgehog_hitbox)

    def knock_out(self, world: "World", direction: int) -> None:
        if self.animator.has("curled"):
            self.animator.play("curled")
        super().knock_out(world, direction)


class BatMode(Enum):
    HANGING = auto()
    DIVING = auto()
    FLEEING = auto()


class Bat(Enemy):
    """Sleeps upside down on a ceiling, dives at the prince, then flutters off."""

    turns_on_enemy_contact = False
    poof_color = (140, 110, 170)

    def __init__(self, midbottom: tuple[float, float], animations: Mapping[str, Animation], facing: int = -1) -> None:
        super().__init__(midbottom, ENEMY.bat_hitbox, animations, facing)
        self.mode = BatMode.HANGING
        self.animator.play("hang")
        self._home = (self.body.x, self.body.y)
        self._time = 0.0
        self._target = (0.0, 0.0)

    def behave(self, dt: float, world: "World") -> None:
        self._time += dt
        body = self.body
        player = world.player
        if self.mode == BatMode.HANGING:
            dx = player.body.centerx - body.centerx
            dy = player.body.centery - body.centery
            if abs(dx) < ENEMY.bat_trigger_distance and 0 < dy < ENEMY.bat_trigger_distance * 1.6 and player.is_controllable:
                self.mode = BatMode.DIVING
                self._time = 0.0
                self._target = (player.body.centerx, player.body.centery)
                self.facing = 1 if dx > 0 else -1
                self.animator.play("walk")
                world.events.emit(EventType.BAT_SCREECH, (body.centerx, body.centery))
            return
        if self.mode == BatMode.DIVING:
            tx, ty = self._target
            direction_x = tx - body.centerx
            direction_y = ty - body.centery
            distance = math.hypot(direction_x, direction_y)
            if distance < 12 or self._time > 1.6:
                self.mode = BatMode.FLEEING
                self._time = 0.0
            else:
                speed = ENEMY.bat_dive_speed
                body.velocity.update(direction_x / distance * speed, direction_y / distance * speed)
        if self.mode == BatMode.FLEEING:
            body.velocity.update(self.facing * ENEMY.bat_flee_speed, -ENEMY.bat_flee_speed * 0.55 + math.sin(self._time * 6) * 40)
        move_body(body, dt, world.collision)
        if body.hit_wall:
            self.facing = -body.hit_wall
        if self.mode == BatMode.FLEEING and (body.hit_ceiling or self._time > 3.0):
            # Perch again wherever it ended up.
            if body.hit_ceiling:
                self.mode = BatMode.HANGING
                self.animator.play("hang")
                body.velocity.update(0, 0)

    def on_stomped(self, world: "World") -> bool:
        self._set_state(EnemyState.KNOCKED_OUT)
        self.body.velocity.update(0, 0)
        emitters.stomp_impact(world.particles, self.body.centerx, self.body.top)
        return True


class Ghul(Enemy):
    """A shy desert spirit. It glides toward the prince (through walls) only
    while his back is turned, and covers its face when he looks at it.
    Nothing hurts it; stay out of its way."""

    stompable = False
    turns_on_enemy_contact = False
    star_immune = True
    bumpable = False
    poof_color = (200, 230, 220)

    def __init__(self, midbottom: tuple[float, float], animations: Mapping[str, Animation], facing: int = -1) -> None:
        super().__init__(midbottom, ENEMY.ghul_hitbox, animations, facing)
        self._time = 0.0
        self.watched = False

    def behave(self, dt: float, world: "World") -> None:
        self._time += dt
        body = self.body
        player = world.player
        dx = player.body.centerx - body.centerx
        dy = player.body.centery - body.centery
        # The player is looking at the ghul if he faces toward it.
        self.watched = (dx < 0 and player.facing > 0) or (dx > 0 and player.facing < 0)
        if abs(dx) > 520 or not player.is_controllable:
            self.watched = True
        if self.watched:
            body.velocity.update(0, 0)
            self.animator.play("shy")
        else:
            distance = max(1.0, math.hypot(dx, dy))
            speed = ENEMY.ghul_speed
            body.velocity.update(dx / distance * speed, dy / distance * speed)
            self.facing = 1 if dx > 0 else -1
            self.animator.play("walk")
        body.x += body.velocity.x * dt
        body.y += body.velocity.y * dt + math.sin(self._time * 2.2) * 6 * dt

    def lights(self) -> list[Light]:
        return [Light(self.body.centerx, self.body.centery - 6, 60, (120, 255, 190), 0.6, flicker=0.2)]
