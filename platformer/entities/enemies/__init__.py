"""Enemy registry: maps the ``kind`` property used in Tiled to a factory.

Adding an enemy type = write a subclass of Enemy + add one entry here.
"""

from collections.abc import Callable

from core import settings
from entities.enemies.creatures import Bat, Ghul, Hedgehog
from entities.enemies.enemy import Enemy
from entities.enemies.flyer import Flyer
from entities.enemies.hopper import Hopper
from entities.enemies.walker import Walker
from rendering import sprite_specs
from rendering.sprite_library import SpriteLibrary
from world.level_data import ObjectSpec

EnemyFactory = Callable[[ObjectSpec, SpriteLibrary], Enemy]


def _facing(spec: ObjectSpec) -> int:
    return 1 if spec.get_str("facing", "left").lower() == "right" else -1


def _create_walker(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    return Walker(
        spec.midbottom,
        sprites.animations(sprite_specs.WALKER),
        _facing(spec),
        edge_aware=spec.get_bool("edge_aware"),
    )


def _create_hopper(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    return Hopper(spec.midbottom, sprites.animations(sprite_specs.HOPPER), _facing(spec))


def _create_flyer(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    patrol = spec.get_float("patrol_tiles", settings.ENEMY.flyer_patrol_tiles)
    return Flyer(
        spec.midbottom,
        sprites.animations(sprite_specs.FLYER),
        patrol * settings.TILE_SIZE,
        _facing(spec),
        vertical=spec.get_str("axis", "horizontal").lower() == "vertical",
    )


def _create_hedgehog(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    return Hedgehog(spec.midbottom, sprites.animations(sprite_specs.HEDGEHOG), _facing(spec),
                    edge_aware=spec.get_bool("edge_aware", True))


def _create_bat(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    # Bats hang from the ceiling: anchor them at the top of their cell.
    midbottom = (spec.rect.centerx, spec.rect.top + settings.ENEMY.bat_hitbox[1])
    return Bat(midbottom, sprites.animations(sprite_specs.BAT), _facing(spec))


def _create_ghul(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    return Ghul(spec.midbottom, sprites.animations(sprite_specs.GHUL), _facing(spec))


# Mechanical names and themed aliases both work in Tiled.
ENEMY_FACTORIES: dict[str, EnemyFactory] = {
    "walker": _create_walker,
    "scorpion": _create_walker,
    "hopper": _create_hopper,
    "jar": _create_hopper,
    "flyer": _create_flyer,
    "jinn": _create_flyer,
    "hedgehog": _create_hedgehog,
    "spiky": _create_hedgehog,
    "bat": _create_bat,
    "ghul": _create_ghul,
    "ghost": _create_ghul,
}


def create_enemy(spec: ObjectSpec, sprites: SpriteLibrary) -> Enemy:
    kind = spec.get_str("kind", "walker").lower()
    factory = ENEMY_FACTORIES.get(kind)
    if factory is None:
        known = ", ".join(sorted(ENEMY_FACTORIES))
        raise ValueError(f"Unknown enemy kind {kind!r} (known: {known})")
    return factory(spec, sprites)
