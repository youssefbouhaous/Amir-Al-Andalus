"""Turns static LevelData into a live World.

This is the one place that knows which Tiled object types map to which game
classes. Unknown types are logged and skipped rather than crashing, so a typo
in Tiled doesn't make the level unplayable.
"""

import logging
from collections.abc import Callable, Collection

import pygame

from core import settings
from core.assets import AssetManager
from entities.enemies import create_enemy
from entities.items import Coin, Page
from entities.player import Player, PowerLevel
from objects.block import Block, BrickBlock, CrumbleBlock, QuestionBlock, SwitchBlock, SwitchToggleBlock
from objects.decor import create_decor
from objects.hazards import FireLion, Spikes, Water, WindZone
from objects.interactive import Drum, Fountain, Sign
from objects.platforms import Carpet, LilyPad, MovingPlatform, PendulumPlatform, Wheel
from objects.switches import SwitchController
from objects.triggers import Checkpoint, Door, Goal
from rendering import sprite_specs
from rendering.art import objects as object_art
from rendering.art.tiles import make_tile, switch_outline
from rendering.sprite_library import SpriteLibrary
from ui.bubble import make_bubble
from world.collision_map import TileCollision
from world.level_data import LevelData, ObjectSpec
from world.world import World

logger = logging.getLogger(__name__)

T = settings.TILE_SIZE
CHECKPOINT_SIZE = (T, T * 2)
# Object types that are handled elsewhere (or are just markers).
IGNORED_KINDS = frozenset({"player_spawn", "backdrop", "boss_arena", "note"})


def build_world(
    level: LevelData,
    sprites: SpriteLibrary,
    assets: AssetManager,
    power: int = 0,
    checkpoint_id: int | None = None,
    spawn_door: str | None = None,
    found_pages: Collection[int] = (),
) -> World:
    player_animations = {
        PowerLevel.NONE: sprites.animations(sprite_specs.PLAYER),
        PowerLevel.POMEGRANATE: sprites.animations(sprite_specs.PLAYER_POWERED),
        PowerLevel.STAR: sprites.animations(sprite_specs.PLAYER_STAR),
    }
    player = Player(
        level.objects_of("player_spawn")[0].midbottom,
        player_animations,
        power=PowerLevel(max(0, min(2, int(power)))),
    )
    world = World(level, player, sprites, level.collision.copy())
    locked = str(level.properties.get("locked_moves") or "")
    player.locked_moves = frozenset(move.strip() for move in locked.split(",") if move.strip())
    world.switch = SwitchController(
        level.get_float("switch_period", 0.0),
        str(level.properties.get("switch_start", "sun")),
    )
    builder = _Builder(world, level, sprites, assets, checkpoint_id, found_pages)
    for spec in level.objects:
        builder.add(spec)
    world.switch.start(world)

    spawn = _resolve_spawn(world, level, checkpoint_id, spawn_door)
    if spawn_door and spawn_door in world.doors:
        player.emerge_from(world.doors[spawn_door])
    else:
        player.arrive_at(spawn)
    world.protect_arrival()
    for prop in world.props:
        settle = getattr(prop, "settle_below", None)
        if settle is not None:
            settle(player.body.bottom)
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
                return _safe_checkpoint_spawn(world, checkpoint.respawn_point, level)
    return level.objects_of("player_spawn")[0].midbottom


def _safe_checkpoint_spawn(world: World, point: tuple[float, float], level: LevelData) -> tuple[float, float]:
    """Recover old/custom checkpoints embedded in terrain or a lethal pool."""
    x, y = point
    offsets = sorted(((dx, dy) for dx in range(-6, 7) for dy in range(-3, 4)),
                     key=lambda pair: abs(pair[0]) + abs(pair[1]) * 2)
    for dx, dy in offsets:
        candidate = (x + dx * T, y + dy * T)
        rect = world.player.rect.copy()
        rect.midbottom = (round(candidate[0]), round(candidate[1]))
        if not world.bounds.contains(rect):
            continue
        if any(kind == TileCollision.SOLID for _, _, kind in world.collision.cells_overlapping(
            rect.left, rect.top, rect.right, rect.bottom
        )):
            continue
        if not all(world.collision.is_standable(px, rect.bottom + 1)
                   for px in (rect.left, rect.right - 1)):
            continue
        if any(isinstance(prop, (Water, Spikes)) and prop.touch_rect().colliderect(rect.inflate(8, 8))
               for prop in world.props):
            continue
        return candidate
    logger.warning("Unsafe checkpoint in %s; returning to level entrance", level.file_name)
    return level.objects_of("player_spawn")[0].midbottom


class _Builder:
    def __init__(
        self,
        world: World,
        level: LevelData,
        sprites: SpriteLibrary,
        assets: AssetManager,
        checkpoint_id: int | None,
        found_pages: Collection[int],
    ) -> None:
        self._world = world
        self._level = level
        self._sprites = sprites
        self._assets = assets
        self._checkpoint_id = checkpoint_id
        self._found_pages = set(found_pages)
        self._handlers: dict[str, Callable[[ObjectSpec], None]] = {
            "enemy": self._add_enemy,
            "coin": self._add_coin,
            "page": self._add_page,
            "brick": self._add_brick,
            "question": self._add_question,
            "switch_block": self._add_switch_block,
            "switch_toggle": self._add_switch_toggle,
            "crumble": self._add_crumble,
            "moving_platform": self._add_platform,
            "pendulum": self._add_pendulum,
            "wheel": self._add_wheel,
            "lily_pad": self._add_lily_pad,
            "carpet": self._add_carpet,
            "checkpoint": self._add_checkpoint,
            "goal": self._add_goal,
            "door": self._add_door,
            "camera_zone": self._add_camera_zone,
            "drum": self._add_drum,
            "spikes": self._add_spikes,
            "water": self._add_water,
            "fountain": self._add_fountain,
            "wind": self._add_wind,
            "fire_lion": self._add_fire_lion,
            "sign": self._add_sign,
            "decor": self._add_decor,
            "boss": self._add_boss,
            # Book II
            "cracked": self._add_cracked,
            "ring": self._add_ring,
            "dash_lantern": self._add_dash_lantern,
            "updraft": self._add_updraft,
            "pound_plate": self._add_pound_plate,
            "gate": self._add_gate,
            "flood": self._add_flood,
            "blade_trap": self._add_blade_trap,
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
            image = make_tile(name).convert_alpha()
            self._level.named_tiles[name] = image
        return image

    def _cell(self, spec: ObjectSpec) -> tuple[int, int]:
        return self._world.collision.tile_at(spec.rect.x + 1, spec.rect.y + 1)

    # --- Enemies and collectibles --------------------------------------------------
    def _add_enemy(self, spec: ObjectSpec) -> None:
        self._world.enemies.append(create_enemy(spec, self._sprites))

    def _add_coin(self, spec: ObjectSpec) -> None:
        center = spec.rect.center
        midbottom = (center[0], center[1] + settings.ITEMS.coin_hitbox_size / 2)
        self._world.items.append(Coin(midbottom, self._sprites.animations(sprite_specs.COIN)))

    def _add_page(self, spec: ObjectSpec) -> None:
        index = spec.get_int("index", 0)
        self._world.items.append(
            Page(spec.rect.center, index, self._sprites.animations(sprite_specs.PAGE),
                 already_found=index in self._found_pages)
        )

    # --- Blocks ------------------------------------------------------------------------
    def _register_block(self, block: Block) -> None:
        self._world.blocks[block.cell] = block
        self._world.collision.set(*block.cell, TileCollision.SOLID)

    def _add_brick(self, spec: ObjectSpec) -> None:
        self._register_block(BrickBlock(self._cell(spec), T, self._tile("brick")))

    def _add_question(self, spec: ObjectSpec) -> None:
        contents = spec.get_str("contents", "coin").lower()
        # Hidden blocks look like plain wall until bumped.
        image_name = spec.get_str("look", "question")
        block = QuestionBlock(self._cell(spec), T, self._tile(image_name), self._tile("used_block"), contents)
        self._register_block(block)

    def _add_switch_block(self, spec: ObjectSpec) -> None:
        color = spec.get_str("color", "sun").lower()
        if color not in {"sun", "moon"}:
            raise ValueError(f"unknown switch block color {color!r}")
        ghost = switch_outline(color == "sun").convert_alpha()
        block = SwitchBlock(self._cell(spec), T, self._tile(f"{color}_block"), ghost, color)
        self._register_block(block)
        assert self._world.switch is not None
        self._world.switch.attach(block)

    def _add_switch_toggle(self, spec: ObjectSpec) -> None:
        self._register_block(SwitchToggleBlock(self._cell(spec), T, self._tile("question_star")))

    def _add_crumble(self, spec: ObjectSpec) -> None:
        self._register_block(CrumbleBlock(self._cell(spec), T, self._tile("crumble")))

    # --- Platforms -----------------------------------------------------------------------
    def _add_platform(self, spec: ObjectSpec) -> None:
        horizontal = spec.get_str("axis", "horizontal").lower() != "vertical"
        distance = spec.get_float("distance", settings.PLATFORM_DEFAULT_DISTANCE_TILES)
        rect = pygame.Rect(spec.rect.x, spec.rect.y, spec.rect.width, 16)
        image = object_art.platform_strip(spec.get_str("style", "beam"), rect.width).convert_alpha()
        self._world.platforms.append(
            MovingPlatform(
                rect, horizontal, distance * T, spec.get_float("speed", settings.PLATFORM_DEFAULT_SPEED),
                image, reverse=spec.get_bool("reverse"),
            )
        )

    def _add_pendulum(self, spec: ObjectSpec) -> None:
        self._world.platforms.append(
            PendulumPlatform(
                (spec.rect.centerx, spec.rect.top), spec.rect.height,
                spec.get_float("amplitude", 45.0), spec.get_float("period", 3.2),
                width=spec.get_int("platform_width", spec.get_int("width", 64)), phase=spec.get_float("phase", 0.0),
            )
        )

    def _add_wheel(self, spec: ObjectSpec) -> None:
        wheel = Wheel(
            spec.rect.center, spec.rect.width / 2, spec.get_int("seats", 4),
            spec.get_float("speed", 30.0), spec.get_str("style", "noria"), spec.get_int("seat_width", 56),
        )
        self._world.props.append(wheel)
        self._world.platforms.extend(wheel.seats)

    def _add_lily_pad(self, spec: ObjectSpec) -> None:
        self._world.platforms.append(
            LilyPad((spec.rect.centerx, spec.rect.top), max(40, spec.rect.width), spec.get_bool("flower"),
                    spec.rect.x * 0.013)
        )

    def _add_carpet(self, spec: ObjectSpec) -> None:
        points = list(spec.points) or [spec.rect.midtop, (spec.rect.right, spec.rect.top)]
        self._world.platforms.append(
            Carpet(points, spec.get_int("carpet_width", spec.get_int("width", 96)), spec.get_float("speed", 150.0))
        )

    # --- Triggers ------------------------------------------------------------------------
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

    # --- Props -----------------------------------------------------------------------------
    def _add_drum(self, spec: ObjectSpec) -> None:
        self._world.props.append(Drum(spec.midbottom))

    def _add_spikes(self, spec: ObjectSpec) -> None:
        self._world.props.append(Spikes(spec.rect, spec.get_str("direction", "up")))

    def _add_water(self, spec: ObjectSpec) -> None:
        color = (60, 130, 190) if spec.get_str("style", "pool") == "pool" else (40, 90, 120)
        self._world.props.append(Water(spec.rect, color, reflective=spec.get_bool("reflective", True)))

    def _add_fountain(self, spec: ObjectSpec) -> None:
        self._world.props.append(
            Fountain(
                spec.midbottom,
                spec.rect.height / T,
                spec.get_float("on", 2.0),
                spec.get_float("off", 1.5),
                spec.get_float("phase", 0.0),
            )
        )

    def _add_wind(self, spec: ObjectSpec) -> None:
        zone = WindZone(
            spec.rect,
            spec.get_float("strength", 120.0),
            spec.get_float("on", 2.0),
            spec.get_float("off", 1.5),
            spec.get_float("phase", 0.0),
        )
        self._world.props.append(zone)
        self._world.wind_zones.append(zone)

    def _add_fire_lion(self, spec: ObjectSpec) -> None:
        lion = FireLion(
            self._cell(spec),
            1 if spec.get_str("facing", "right").lower() == "right" else -1,
            spec.get_float("interval", 2.4),
            spec.get_float("phase", 0.0),
            spec.get_bool("arc"),
        )
        lion.register(self._world)
        self._world.props.append(lion)

    def _add_sign(self, spec: ObjectSpec) -> None:
        text = spec.get_str("text", "...").replace("\\n", "\n")
        font = self._assets.get_font(settings.SIGN_FONT_SIZE, "body")
        self._world.props.append(Sign(spec.midbottom, make_bubble(font, text)))

    def _add_decor(self, spec: ObjectSpec) -> None:
        prop = create_decor(spec)
        if prop is None:
            raise ValueError(f"unknown decor style {spec.get_str('style')!r}")
        self._world.props.append(prop)

    def _add_boss(self, spec: ObjectSpec) -> None:
        from entities.boss import Ifrit

        arena = next(iter(self._level.objects_of("boss_arena")), None)
        arena_rect = pygame.Rect(arena.rect) if arena is not None else self._level.pixel_rect
        self._world.boss = Ifrit(spec.midbottom, arena_rect, self._sprites)

    # --- Book II mechanisms ------------------------------------------------------------
    def _add_cracked(self, spec: ObjectSpec) -> None:
        from objects.block import CrackedBlock

        cell = self._cell(spec)
        for dx in range(max(1, spec.rect.width // T)):
            for dy in range(max(1, spec.rect.height // T)):
                self._register_block(CrackedBlock((cell[0] + dx, cell[1] + dy), T, self._tile("cracked")))

    def _add_ring(self, spec: ObjectSpec) -> None:
        from objects.rings import Ring

        ring = Ring((spec.rect.centerx, spec.rect.top), spec.rect.height, spec.rect.x * 0.01)
        self._world.props.append(ring)
        self._world.rings.append(ring)

    def _add_dash_lantern(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import DashLantern

        self._world.props.append(DashLantern(spec.rect.center))

    def _add_updraft(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import Updraft

        draft = Updraft(spec.rect, spec.get_float("strength", 260.0))
        self._world.props.append(draft)
        self._world.updrafts.append(draft)

    def _add_pound_plate(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import PoundPlate

        plate = PoundPlate(spec.midbottom, spec.get_str("group", "a"), spec.get_float("timer", 0.0))
        self._world.props.append(plate)
        self._world.plates.append(plate)

    def _add_gate(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import Gate

        gate = Gate(pygame.Rect(spec.rect), spec.get_str("group", "a"), spec.get_bool("open"))
        gate.register(self._world)
        self._world.props.append(gate)
        self._world.gates.append(gate)

    def _add_flood(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import RisingFlood

        top_limit = spec.get_float("top_limit_tiles", 0.0) * T
        self._world.props.append(
            RisingFlood(pygame.Rect(spec.rect), spec.get_float("speed", 40.0), top_limit,
                        spec.get_float("delay", 2.5), spec.get_float("lag_tiles", 7.0) * T)
        )

    def _add_blade_trap(self, spec: ObjectSpec) -> None:
        from objects.mechanisms import BladeTrap

        for dx in range(max(1, spec.rect.width // T)):
            rect = pygame.Rect(spec.rect.x + dx * T, spec.rect.y, T, spec.rect.height)
            self._world.props.append(BladeTrap(rect, spec.get_float("speed", 9.0)))
