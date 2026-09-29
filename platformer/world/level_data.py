"""Static description of a level, as read from a Tiled map.

LevelData is loaded once and cached. Every time the player (re)spawns, a fresh
World is built from it, so enemies, coins and blocks reset without re-reading
the file.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

import pygame

from world.collision_map import CollisionMap
from world.tile_layer import TileLayer


@dataclass(frozen=True, eq=False)
class ObjectSpec:
    """One object placed in Tiled (or a tile converted into an object)."""

    object_id: int
    kind: str
    name: str
    rect: pygame.Rect
    properties: Mapping[str, object] = field(default_factory=dict)
    # Absolute world points of a polyline/polygon object (e.g. a carpet path).
    points: tuple[tuple[float, float], ...] = ()

    @property
    def midbottom(self) -> tuple[int, int]:
        return self.rect.centerx, self.rect.bottom

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(float(self.properties.get(key, default)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    def get_str(self, key: str, default: str = "") -> str:
        value = self.properties.get(key, default)
        return str(value) if value is not None else default

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.properties.get(key, default))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.properties.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes")
        return bool(value)


@dataclass(eq=False)
class LevelData:
    file_name: str
    name: str
    subtitle: str
    next_level: str | None
    music: str | None
    theme: str
    collision: CollisionMap
    back_layers: list[TileLayer]
    front_layers: list[TileLayer]
    objects: list[ObjectSpec]
    # Tile images looked up by their "name" property (e.g. "used_block").
    named_tiles: dict[str, pygame.Surface]
    # Every map property, for features that read their own settings.
    properties: Mapping[str, object] = field(default_factory=dict)

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.properties.get(key, default))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    @property
    def pixel_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.collision.pixel_width, self.collision.pixel_height)

    def objects_of(self, kind: str) -> list[ObjectSpec]:
        return [spec for spec in self.objects if spec.kind == kind]
