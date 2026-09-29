"""Reads Tiled .tmx maps into LevelData.

Conventions (see README "Designing levels in Tiled"):

* Tile layers named ``terrain`` or ``collision`` create collision. A tile's
  ``collision`` property may be ``solid`` (default), ``one_way`` or ``none``.
  The ``collision`` layer itself is never drawn.
* A tile layer named ``foreground`` is drawn in front of entities; every other
  tile layer (``background``, ``terrain``, ``decorations``...) is drawn behind.
* Any tile whose tileset entry has a ``spawn`` property (brick, question,
  coin) is turned into a game object instead of a static tile, so blocks and
  coins can be *painted* like tiles.
* Every object in every object layer becomes an ObjectSpec. Its kind is the
  object's Class/Type in Tiled (falling back to its Name).
"""

import logging
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pygame
import pytmx
from pytmx.util_pygame import load_pygame

from core import settings
from rendering.art.tiles import make_tile
from world.collision_map import CollisionMap, TileCollision
from world.level_data import LevelData, ObjectSpec
from world.tile_layer import TileLayer

logger = logging.getLogger(__name__)

COLLIDING_LAYERS = frozenset({"terrain", "collision"})
HIDDEN_LAYERS = frozenset({"collision"})
FOREGROUND_LAYERS = frozenset({"foreground"})

DEFAULT_THEME = "garden"

COLLISION_KINDS = {
    "solid": TileCollision.SOLID,
    "one_way": TileCollision.ONE_WAY,
    "none": TileCollision.EMPTY,
}


class LevelLoadError(Exception):
    """A level file is missing or doesn't follow the expected conventions."""


class LevelLoader:
    def __init__(self, maps_dir: Path) -> None:
        self._maps_dir = maps_dir
        self._cache: dict[str, LevelData] = {}

    def load(self, file_name: str) -> LevelData:
        level = self._cache.get(file_name)
        if level is None:
            level = _TmxReader(self._maps_dir / file_name).read()
            self._cache[file_name] = level
        return level

    def invalidate(self, file_name: str) -> None:
        self._cache.pop(file_name, None)


class _TmxReader:
    """Single-use helper holding the state of one TMX parse."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._tmx = self._open(path)
        self._image_cache: dict[int, pygame.Surface] = {}
        self._objects: list[ObjectSpec] = []

    @staticmethod
    def _open(path: Path) -> pytmx.TiledMap:
        if not path.is_file():
            raise LevelLoadError(f"Level file not found: {path}")
        try:
            try:
                return load_pygame(str(path))
            except (FileNotFoundError, pygame.error) as error:
                # Tileset image missing: parse without images and use
                # placeholder art looked up by each tile's "name" property.
                logger.warning("Tileset image unavailable (%s); using placeholders", error)
                return pytmx.TiledMap(str(path))
        except (ElementTree.ParseError, KeyError, ValueError, TypeError, OSError) as error:
            raise LevelLoadError(f"Could not parse {path.name}: {error}") from error

    def read(self) -> LevelData:
        tmx = self._tmx
        if tmx.tilewidth != settings.TILE_SIZE or tmx.tileheight != settings.TILE_SIZE:
            raise LevelLoadError(
                f"{self._path.name}: tiles must be {settings.TILE_SIZE}x{settings.TILE_SIZE}"
            )
        if getattr(tmx, "orientation", "orthogonal") != "orthogonal":
            raise LevelLoadError(f"{self._path.name}: only orthogonal maps are supported")

        collision = CollisionMap(tmx.width, tmx.height, settings.TILE_SIZE)
        back_layers: list[TileLayer] = []
        front_layers: list[TileLayer] = []

        for layer in tmx.layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                tile_layer = self._read_tile_layer(layer, collision)
                if tile_layer is not None:
                    target = front_layers if tile_layer.name in FOREGROUND_LAYERS else back_layers
                    target.append(tile_layer)
            elif isinstance(layer, pytmx.TiledObjectGroup):
                self._read_object_layer(layer)

        if not any(spec.kind == "player_spawn" for spec in self._objects):
            raise LevelLoadError(f"{self._path.name}: no object of type 'player_spawn'")

        properties = tmx.properties
        return LevelData(
            file_name=self._path.name,
            name=str(properties.get("name", self._path.stem)),
            subtitle=str(properties.get("subtitle", "")),
            next_level=properties.get("next_level") or None,
            music=properties.get("music") or None,
            theme=str(properties.get("theme") or properties.get("sky") or DEFAULT_THEME),
            collision=collision,
            back_layers=back_layers,
            front_layers=front_layers,
            objects=self._objects,
            named_tiles=self._read_named_tiles(),
            properties=dict(properties),
        )

    def _read_tile_layer(
        self, layer: pytmx.TiledTileLayer, collision: CollisionMap
    ) -> TileLayer | None:
        name = layer.name.strip().lower()
        colliding = name in COLLIDING_LAYERS
        visible = bool(layer.visible) and name not in HIDDEN_LAYERS
        width, size = self._tmx.width, settings.TILE_SIZE
        tiles: list[pygame.Surface | None] = [None] * (width * self._tmx.height)
        names: list[str | None] = [None] * (width * self._tmx.height)

        for x, y, gid in layer.iter_data():
            if not gid:
                continue
            properties = self._tmx.get_tile_properties_by_gid(gid) or {}
            spawn = properties.get("spawn")
            if spawn:
                rect = pygame.Rect(x * size, y * size, size, size)
                self._objects.append(ObjectSpec(-1, str(spawn), "", rect, dict(properties)))
                continue
            if colliding:
                collision.set(x, y, self._collision_kind(properties))
            if visible:
                tiles[y * width + x] = self._tile_image(gid)
                names[y * width + x] = str(properties.get("name", "")) or None

        if not visible:
            return None
        return TileLayer(name, width, self._tmx.height, size, tiles, names)

    def _read_object_layer(self, group: pytmx.TiledObjectGroup) -> None:
        for obj in group:
            kind = obj.type or getattr(obj, "class", None) or obj.name or ""
            points = tuple((float(p[0]), float(p[1])) for p in (getattr(obj, "points", None) or ()))
            if points:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                rect = pygame.Rect(round(min(xs)), round(min(ys)),
                                   max(1, round(max(xs) - min(xs))), max(1, round(max(ys) - min(ys))))
            else:
                rect = pygame.Rect(
                    round(obj.x), round(obj.y), max(1, round(obj.width)), max(1, round(obj.height))
                )
            self._objects.append(
                ObjectSpec(
                    object_id=int(obj.id),
                    kind=str(kind).strip().lower(),
                    name=obj.name or "",
                    rect=rect,
                    properties=dict(obj.properties),
                    points=points,
                )
            )

    def _read_named_tiles(self) -> dict[str, pygame.Surface]:
        named: dict[str, pygame.Surface] = {}
        for gid, properties in self._tmx.tile_properties.items():
            name = properties.get("name")
            if name and name not in named:
                named[str(name)] = self._tile_image(gid)
        return named

    def _tile_image(self, gid: int) -> pygame.Surface:
        image = self._image_cache.get(gid)
        if image is None:
            image = self._tmx.get_tile_image_by_gid(gid)
            if not isinstance(image, pygame.Surface):
                properties = self._tmx.get_tile_properties_by_gid(gid) or {}
                image = make_tile(str(properties.get("name", ""))).convert_alpha()
            self._image_cache[gid] = image
        return image

    def _collision_kind(self, properties: dict) -> TileCollision:
        value = str(properties.get("collision", "solid")).lower()
        kind = COLLISION_KINDS.get(value)
        if kind is None:
            logger.warning("%s: unknown collision %r, using solid", self._path.name, value)
            kind = TileCollision.SOLID
        return kind
