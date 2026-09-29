"""Rules for what happens when things touch.

These live here, not in Player or Enemy, because they involve two parties.
Each rule asks the entities involved to react (enemy.on_stomped,
player.take_damage...), so the *what* stays inside each class.
"""

from typing import TYPE_CHECKING

from core.events import EventType
from core.settings import ENEMY

if TYPE_CHECKING:
    from world.world import World


def resolve(world: "World") -> None:
    if world.player.is_controllable:
        _player_vs_enemies(world)
        _player_vs_items(world)
        _player_vs_checkpoints(world)
        _player_vs_goals(world)
        _player_vs_doors(world)
    _enemies_vs_enemies(world)


def _player_vs_enemies(world: "World") -> None:
    player = world.player
    for enemy in world.enemies:
        if not enemy.is_dangerous or not player.rect.colliderect(enemy.rect):
            continue

        # A stomp means the player was falling and their feet were above the
        # enemy's head *before* this step. Checking the previous position is
        # what separates "landed on it" from "walked into its side".
        falling = player.body.velocity.y > 0
        was_above = player.previous_bottom <= enemy.body.top + ENEMY.stomp_tolerance
        if falling and was_above and enemy.on_stomped(world):
            player.body.y = enemy.body.top - player.body.height
            player.stomp_combo += 1
            world.events.emit(
                EventType.ENEMY_STOMPED,
                (enemy.body.centerx, enemy.body.top),
                player.stomp_combo,
            )
            player.bounce()
            continue

        player.take_damage(world)
        if not player.is_controllable:
            return


def _player_vs_items(world: "World") -> None:
    player_rect = world.player.rect
    for item in world.items:
        if item.alive and item.collectible and player_rect.colliderect(item.rect):
            item.collect(world.player, world)


def _player_vs_checkpoints(world: "World") -> None:
    player_rect = world.player.rect
    for checkpoint in world.checkpoints:
        if not checkpoint.active and player_rect.colliderect(checkpoint.rect):
            checkpoint.activate(world)


def _player_vs_goals(world: "World") -> None:
    player = world.player
    for goal in world.goals:
        if not goal.reached and player.rect.colliderect(goal.rect):
            goal.reached = True
            player.celebrate()
            world.events.emit(EventType.LEVEL_COMPLETED, goal.rect.midbottom)
            return


def _player_vs_doors(world: "World") -> None:
    player = world.player
    for door in world.doors.values():
        if door.can_enter(player) and door.wants_enter(player.intent):
            player.enter_door(door)
            world.events.emit(EventType.DOOR_ENTERED, door.rect.midbottom)
            return


def _enemies_vs_enemies(world: "World") -> None:
    walkers = [
        enemy
        for enemy in world.enemies
        if enemy.activated and enemy.is_dangerous and enemy.turns_on_enemy_contact
    ]
    for index, first in enumerate(walkers):
        for second in walkers[index + 1:]:
            if first.rect.colliderect(second.rect):
                # Face away from each other (idempotent, so no flip-flopping).
                left, right = sorted((first, second), key=lambda e: e.body.centerx)
                left.facing, right.facing = -1, 1
