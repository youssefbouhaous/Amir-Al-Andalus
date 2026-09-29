"""Turns static LevelData into a live World.

This is the one place that knows which Tiled object types map to which game
classes. Unknown types are logged and skipped rather than crashing, so a typo
in Tiled doesn't make the level unplayable.
"""

import logging
from collections.abc import Callable

import pygame

from core import settings
from core.assets import AssetManager
from entities.enemies import create_enemy
from entities.items import Coin
from entities.player import Player, PowerLevel
from objects.block import BrickBlock, QuestionBlock
from objects.interactive import Drum, Fountain
from objects.hazards import Spikes, Water, WindZone
from objects.moving_platform import MovingPlatform
from objects.block import SwitchBlock
from objects.switches import SwitchController
from objects.triggers import Checkpoint, Door, Goal
from rendering import placeholder_art, sprite_specs
from rendering.sprite_library import SpriteLibrary
from world.collision_map import TileCollision
from world.level_data import LevelData, ObjectSpec
from world.world import World

logger = logging.getLogger(__name__)

CHECKPOINT_SIZE = (settings.TILE_SIZE, settings.TILE_SIZE * 2)
# Object types that are handled elsewhere (or are just markers).
IGNORED_KINDS = frozenset({"player_spawn"})


def build_world(
    level: LevelData,
    sprites: SpriteLibrary,
    assets: AssetManager,
    player_powered: bool,
    checkpoint_id: int | None = None,
    spawn_door: str | None = None,
) -> World:
    player_animations = {
        PowerLevel.NONE: sprites.animations(sprite_specs.PLAYER),
        PowerLevel.POMEGRANATE: sprites.animations(sprite_specs.PLAYER_POWERED),
        PowerLevel.STAR: sprites.animations(sprite_specs.PLAYER_STAR),
    }
    player = Player(
        level.objects_of("player_spawn")[0].midbottom,
        player_animations,
        power=PowerLevel.POMEGRANATE if player_powered else PowerLevel.NONE,
    )
    world = World(level, player, sprites, level.collision.copy())
    world.switch = SwitchController(
        level.get_float("switch_period", 0.0),
        str(level.properties.get("switch_start", "sun")),
    )
    builder = _Builder(world, level, sprites, assets, checkpoint_id)
    for spec in level.objects:
        builder.add(spec)
    world.switch.start(world)

    spawn = _resolve_spawn(world, level, checkpoint_id, spawn_door)
    player.arrive_at(spawn)
    return world


def _resolve_spawn(
    world: World, level: LevelData, checkpoint_id: int | None, spawn_door: str | None
) -> tuple[float, float]:
    if spawn_door:
        door = world.doors.get(spawn_door)
        if door is not None:
            return door.arrival_point
        logger.warning("Spawn door %r not found in %s", spawn_door, level.file_name)
    if checkpoint_id is not None:
        for checkpoint in world.checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                return checkpoint.respawn_point
    return level.objects_of("player_spawn")[0].midbottom


class _Builder:
    def __init__(
        self,
        world: World,
        level: LevelData,
        sprites: SpriteLibrary,
        assets: AssetManager,
        checkpoint_id: int | None,
    ) -> None:
        self._world = world
        self._level = level
        self._sprites = sprites
        self._assets = assets
        self._checkpoint_id = checkpoint_id
        self._handlers: dict[str, Callable[[ObjectSpec], None]] = {
            "enemy": self._add_enemy,
            "coin": self._add_coin,
            "brick": self._add_brick,
            "question": self._add_question,
            "moving_platform": self._add_platform,
            "checkpoint": self._add_checkpoint,
            "goal": self._add_goal,
            "door": self._add_door,
            "camera_zone": self._add_camera_zone,
            "switch_block": self._add_switch_block,
            "drum": self._add_drum,
            "spikes": self._add_spikes,
            "water": self._add_water,
            "fountain": self._add_fountain,
            "wind": self._add_wind,
        }

    def add(self, spec: ObjectSpec) -> None:
        if spec.kind in IGNORED_KINDS:
            return
        handler = self._handlers.get(spec.kind)
        if handler is None:
            logger.warning("%s: ignoring unknown object type %r", self._level.file_name, spec.kind)
            return
        try:
            handler(spec)
        except ValueError as error:
            logger.warning("%s: skipping object %s: %s", self._level.file_name, spec.object_id, error)

    def _tile(self, name: str) -> pygame.Surface:
        image = self._level.named_tiles.get(name)
        if image is None:
            image = placeholder_art.make_tile(name).convert_alpha()
            self._level.named_tiles[name] = image
        return image

    def _cell(self, spec: ObjectSpec) -> tuple[int, int]:
        return self._world.collision.tile_at(spec.rect.x, spec.rect.y)

    def _add_enemy(self, spec: ObjectSpec) -> None:
        self._world.enemies.append(create_enemy(spec, self._sprites))

    def _add_coin(self, spec: ObjectSpec) -> None:
        center = spec.rect.center
        midbottom = (center[0], center[1] + settings.ITEMS.coin_hitbox_size / 2)
        self._world.items.append(Coin(midbottom, self._sprites.animations(sprite_specs.COIN)))

    def _add_brick(self, spec: ObjectSpec) -> None:
        cell = self._cell(spec)
        self._register_block(BrickBlock(cell, settings.TILE_SIZE, self._tile("brick")))

    def _add_question(self, spec: ObjectSpec) -> None:
        cell = self._cell(spec)
        block = QuestionBlock(
            cell,
            settings.TILE_SIZE,
            self._tile("question"),
            self._tile("used_block"),
            spec.get_str("contents", "coin").lower(),
        )
        self._register_block(block)

    def _register_block(self, block: BrickBlock | QuestionBlock) -> None:
        self._world.blocks[block.cell] = block
        self._world.collision.set(*block.cell, TileCollision.SOLID)

    def _add_switch_block(self, spec: ObjectSpec) -> None:
        color = spec.get_str("color", "sun").lower()
        if color not in {"sun", "moon"}:
            raise ValueError(f"unknown switch block color {color!r}")
        cell = self._cell(spec)
        image = self._tile(f"{color}_block")
        block = SwitchBlock(cell, settings.TILE_SIZE, image, self._tile("used_block"), color)
        self._register_block(block)
        assert self._world.switch is not None
        self._world.switch.attach(block)

    def _add_platform(self, spec: ObjectSpec) -> None:
        horizontal = spec.get_str("axis", "horizontal").lower() != "vertical"
        distance = spec.get_float("distance", settings.PLATFORM_DEFAULT_DISTANCE_TILES)
        self._world.platforms.append(
            MovingPlatform(
                spec.rect,
                horizontal,
                distance * settings.TILE_SIZE,
                spec.get_float("speed", settings.PLATFORM_DEFAULT_SPEED),
                self._tile("platform"),
                reverse=spec.get_bool("reverse"),
            )
        )

    def _add_checkpoint(self, spec: ObjectSpec) -> None:
        self._world.checkpoints.append(
            Checkpoint(
                spec.object_id,
                spec.midbottom,
                CHECKPOINT_SIZE,
                style=spec.get_str("style", "lantern"),
                active=spec.object_id == self._checkpoint_id,
            )
        )

    def _add_goal(self, spec: ObjectSpec) -> None:
        # style "gate" = arch to the next level, "sword" = the final prize.
        self._world.goals.append(Goal(spec.rect, spec.get_str("style", "gate").lower()))

    def _add_door(self, spec: ObjectSpec) -> None:
        if not spec.name:
            raise ValueError("doors need a name")
        self._world.doors[spec.name] = Door(
            spec.name,
            spec.rect,
            spec.get_str("target_door") or None,
            spec.get_str("target_level") or None,
            spec.get_str("enter", "down").lower(),
        )

    def _add_camera_zone(self, spec: ObjectSpec) -> None:
        self._world.camera_zones.append(pygame.Rect(spec.rect))

    def _add_drum(self, spec: ObjectSpec) -> None:
        self._world.props.append(Drum(spec.midbottom))

    def _add_spikes(self, spec: ObjectSpec) -> None:
        self._world.props.append(Spikes(spec.rect, spec.get_str("direction", "up")))

    def _add_water(self, spec: ObjectSpec) -> None:
        self._world.props.append(Water(spec.rect))

    def _add_fountain(self, spec: ObjectSpec) -> None:
        self._world.props.append(
            Fountain(
                spec.midbottom,
                spec.rect.height / settings.TILE_SIZE,
                spec.get_float("on", 2.0),
                spec.get_float("off", 1.5),
                spec.get_float("phase", 0.0),
            )
        )

    def _add_wind(self, spec: ObjectSpec) -> None:
        self._world.props.append(
            WindZone(
                spec.rect,
                spec.get_float("strength", 120.0),
                spec.get_float("on", 2.0),
                spec.get_float("off", 1.5),
                spec.get_float("phase", 0.0),
            )
        )
