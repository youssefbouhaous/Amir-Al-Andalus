"""Pre-rendered terrain: backdrops, tiles and auto-tiling baked into chunks.

Drawing thousands of tiles every frame is wasteful when they never change,
so the level's static layers are composited once into square chunk surfaces
(``TERRAIN_CHUNK_TILES`` tiles on a side). Each frame then only blits the few
chunks that overlap the camera.

Baking is also where the terrain gets its hand-drawn look (see
``rendering/art/tiles.py``): exposed edges get caps, rims and icicles, and
buried tiles darken with their distance from open air.
"""

from collections import deque

import pygame

from core import settings
from rendering.art.backdrops import paint_backdrop
from rendering.art.kit import hash01
from rendering.art.tiles import SOLID_TERRAIN, TERRAIN_STYLES
from rendering.camera import Camera
from world.level_data import LevelData
from world.tile_layer import TileLayer

T = settings.TILE_SIZE
AUTOTILE_LAYERS = frozenset({"terrain"})
_shade_cache: dict[int, pygame.Surface] = {}


def _shade(alpha: int) -> pygame.Surface:
    surface = _shade_cache.get(alpha)
    if surface is None:
        surface = pygame.Surface((T, T))
        surface.fill((0, 0, 0))
        surface.set_alpha(alpha)
        _shade_cache[alpha] = surface
    return surface


class _Autotile:
    """Exposure and depth information for one terrain layer."""

    def __init__(self, layer: TileLayer) -> None:
        self.layer = layer
        width, height = layer.width, layer.height
        self._solid = [name in SOLID_TERRAIN for name in layer.names]
        self.depth = [0] * (width * height)
        queue: deque[tuple[int, int]] = deque()
        unseen = -1
        for ty in range(height):
            for tx in range(width):
                index = ty * width + tx
                if not self._solid[index]:
                    continue
                if self.exposed(tx, ty, 0, -1) or self.exposed(tx, ty, -1, 0) or \
                        self.exposed(tx, ty, 1, 0) or self.exposed(tx, ty, 0, 1):
                    queue.append((tx, ty))
                else:
                    self.depth[index] = unseen
        while queue:
            tx, ty = queue.popleft()
            d = self.depth[ty * width + tx]
            for nx, ny in ((tx + 1, ty), (tx - 1, ty), (tx, ty + 1), (tx, ty - 1)):
                if 0 <= nx < width and 0 <= ny < height:
                    n = ny * width + nx
                    if self.depth[n] == unseen:
                        self.depth[n] = d + 1
                        queue.append((nx, ny))

    def solid(self, tx: int, ty: int) -> bool:
        layer = self.layer
        if tx < 0 or tx >= layer.width:
            tx = min(max(tx, 0), layer.width - 1)
        if ty >= layer.height:
            ty = layer.height - 1
        if ty < 0:
            return False
        return self._solid[ty * layer.width + tx]

    def exposed(self, tx: int, ty: int, dx: int, dy: int) -> bool:
        return not self.solid(tx + dx, ty + dy)


class TerrainRenderer:
    def __init__(self, level: LevelData) -> None:
        self._level = level
        self._chunk = settings.TERRAIN_CHUNK_TILES * T
        self._width_px = level.collision.pixel_width
        self._height_px = level.collision.pixel_height
        self._back: dict[tuple[int, int], pygame.Surface | None] = {}
        self._front: dict[tuple[int, int], pygame.Surface | None] = {}
        self._autotile = {
            id(layer): _Autotile(layer) for layer in level.back_layers if layer.name in AUTOTILE_LAYERS
        }
        self._backdrops: list[tuple[pygame.Rect, pygame.Surface]] = []
        for index, spec in enumerate(level.objects_of("backdrop")):
            rect = pygame.Rect(spec.rect)
            style = spec.get_str("style", "cave")
            self._backdrops.append((rect, paint_backdrop(style, rect.size, seed=index * 31 + rect.x)))
        self.front_alpha = 255

    # --- baking ------------------------------------------------------------------
    def _chunk_rect(self, key: tuple[int, int]) -> pygame.Rect:
        cx, cy = key
        rect = pygame.Rect(cx * self._chunk, cy * self._chunk, self._chunk, self._chunk)
        return rect.clip(pygame.Rect(0, 0, self._width_px, self._height_px))

    def _bake(self, key: tuple[int, int], layers: list[TileLayer], with_backdrops: bool) -> pygame.Surface | None:
        rect = self._chunk_rect(key)
        if rect.width <= 0 or rect.height <= 0:
            return None
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        drew = False
        if with_backdrops:
            for zone, image in self._backdrops:
                overlap = zone.clip(rect)
                if overlap.width > 0 and overlap.height > 0:
                    area = overlap.move(-zone.x, -zone.y)
                    surface.blit(image, (overlap.x - rect.x, overlap.y - rect.y), area)
                    drew = True
        min_tx = rect.left // T - 1
        max_tx = (rect.right - 1) // T + 1
        min_ty = rect.top // T - 1
        max_ty = (rect.bottom - 1) // T + 1
        for layer in layers:
            autotile = self._autotile.get(id(layer))
            if autotile is None:
                drew |= self._blit_plain(surface, rect, layer, min_tx, max_tx, min_ty, max_ty)
            else:
                drew |= self._blit_autotiled(surface, rect, autotile, min_tx, max_tx, min_ty, max_ty)
        return surface if drew else None

    @staticmethod
    def _blit_plain(surface, rect, layer, min_tx, max_tx, min_ty, max_ty) -> bool:
        drew = False
        for ty in range(max(0, min_ty), min(layer.height, max_ty + 1)):
            for tx in range(max(0, min_tx), min(layer.width, max_tx + 1)):
                image = layer.tiles[ty * layer.width + tx]
                if image is not None:
                    surface.blit(image, (tx * T - rect.x, ty * T - rect.y))
                    drew = True
        return drew

    def _blit_autotiled(self, surface, rect, auto: _Autotile, min_tx, max_tx, min_ty, max_ty) -> bool:
        layer = auto.layer
        drew = False
        caps = []
        bottoms = []
        for ty in range(max(0, min_ty), min(layer.height, max_ty + 1)):
            for tx in range(max(0, min_tx), min(layer.width, max_tx + 1)):
                index = ty * layer.width + tx
                image = layer.tiles[index]
                if image is None:
                    continue
                drew = True
                x, y = tx * T - rect.x, ty * T - rect.y
                surface.blit(image, (x, y))
                style = TERRAIN_STYLES.get(layer.names[index] or "")
                if style is None:
                    continue
                depth = auto.depth[index]
                if style.depth_shade > 0 and depth > 0:
                    alpha = round(255 * min(0.62, style.depth_shade * min(depth, style.max_depth)))
                    surface.blit(_shade(alpha), (x, y))
                left = auto.exposed(tx, ty, -1, 0)
                right = auto.exposed(tx, ty, 1, 0)
                top = auto.exposed(tx, ty, 0, -1)
                bottom = auto.exposed(tx, ty, 0, 1)
                rim, width = style.rim, style.rim_width
                if left:
                    surface.fill(rim, (x, y, width, T))
                if right:
                    surface.fill(rim, (x + T - width, y, width, T))
                if bottom:
                    surface.fill(rim, (x, y + T - width, T, width))
                    if style.bottom is not None:
                        bottoms.append((style.bottom, x, y + T, hash01(tx, ty, 7)))
                if top:
                    if style.cap is not None:
                        caps.append((style.cap, x, y, left, right, hash01(tx, ty)))
                    else:
                        surface.fill(rim, (x, y, T, width))
        for bottom_fn, x, y, r in bottoms:
            bottom_fn(surface, x, y, r)
        for cap, x, y, left, right, r in caps:
            cap(surface, x, y, left, right, r)
        return drew

    def bake_all(self) -> None:
        cols = -(-self._width_px // self._chunk)
        rows = -(-self._height_px // self._chunk)
        for cy in range(rows):
            for cx in range(cols):
                self._get((cx, cy), front=False)
                self._get((cx, cy), front=True)

    def _get(self, key: tuple[int, int], front: bool) -> pygame.Surface | None:
        cache = self._front if front else self._back
        if key not in cache:
            layers = self._level.front_layers if front else self._level.back_layers
            cache[key] = self._bake(key, layers, with_backdrops=not front) if layers or not front else None
        return cache[key]

    # --- drawing --------------------------------------------------------------------
    def _draw(self, surface: pygame.Surface, camera: Camera, front: bool) -> None:
        view = camera.view_rect
        offset_x, offset_y = camera.offset
        size = self._chunk
        for cy in range(max(0, view.top // size), (view.bottom - 1) // size + 1):
            for cx in range(max(0, view.left // size), (view.right - 1) // size + 1):
                chunk = self._get((cx, cy), front)
                if chunk is None:
                    continue
                if front and self.front_alpha < 255:
                    chunk.set_alpha(self.front_alpha)
                    surface.blit(chunk, (cx * size - offset_x, cy * size - offset_y))
                    chunk.set_alpha(None)
                else:
                    surface.blit(chunk, (cx * size - offset_x, cy * size - offset_y))

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        self._draw(surface, camera, front=False)

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        if self._level.front_layers:
            self._draw(surface, camera, front=True)

    def has_front_tile(self, x: float, y: float) -> bool:
        tx, ty = int(x // T), int(y // T)
        return any(layer.image_at(tx, ty) is not None for layer in self._level.front_layers)
