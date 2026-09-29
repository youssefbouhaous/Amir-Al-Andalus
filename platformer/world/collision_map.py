"""Grid of collision cells: the spatial partition for all terrain collisions.

Instead of testing a body against every tile in the level, we convert the
body's bounds to tile indices (min_tx..max_tx, min_ty..max_ty) and look only
at those few cells. Cost depends on the body's size, not the level's size, so
a 10,000-tile level is as cheap as a 100-tile one.
"""

import math
from collections.abc import Iterator
from enum import IntEnum

# Treat a right/bottom edge that exactly touches a tile boundary as *not*
# overlapping the next tile; otherwise a body resting on the ground would
# register as intersecting it.
EDGE_EPSILON = 1e-6


class TileCollision(IntEnum):
    EMPTY = 0
    SOLID = 1
    ONE_WAY = 2  # Solid only from above: you can jump up through it.


class CollisionMap:
    def __init__(
        self, width: int, height: int, tile_size: int, cells: bytearray | None = None
    ) -> None:
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self._cells = cells if cells is not None else bytearray(width * height)
        if len(self._cells) != width * height:
            raise ValueError("Cell buffer size does not match map dimensions")

    @property
    def pixel_width(self) -> int:
        return self.width * self.tile_size

    @property
    def pixel_height(self) -> int:
        return self.height * self.tile_size

    def copy(self) -> "CollisionMap":
        return CollisionMap(self.width, self.height, self.tile_size, bytearray(self._cells))

    def get(self, tx: int, ty: int) -> TileCollision:
        # The left and right map edges are walls at every height, so nothing
        # can leave the level sideways. Above and below the map is open air
        # (falling off the bottom is how pits kill you).
        if tx < 0 or tx >= self.width:
            return TileCollision.SOLID
        if ty < 0 or ty >= self.height:
            return TileCollision.EMPTY
        return TileCollision(self._cells[ty * self.width + tx])

    def set(self, tx: int, ty: int, kind: TileCollision) -> None:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            self._cells[ty * self.width + tx] = kind

    def tile_at(self, x: float, y: float) -> tuple[int, int]:
        return math.floor(x / self.tile_size), math.floor(y / self.tile_size)

    def tile_range(
        self, left: float, top: float, right: float, bottom: float
    ) -> tuple[int, int, int, int]:
        """Inclusive tile index bounds covered by a float rectangle."""
        size = self.tile_size
        return (
            math.floor(left / size),
            math.floor((right - EDGE_EPSILON) / size),
            math.floor(top / size),
            math.floor((bottom - EDGE_EPSILON) / size),
        )

    def cells_overlapping(
        self, left: float, top: float, right: float, bottom: float
    ) -> Iterator[tuple[int, int, TileCollision]]:
        """Yield every non-empty cell touched by the rectangle."""
        min_tx, max_tx, min_ty, max_ty = self.tile_range(left, top, right, bottom)
        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                kind = self.get(tx, ty)
                if kind != TileCollision.EMPTY:
                    yield tx, ty, kind

    def solid_beside(self, left: float, top: float, right: float, bottom: float, side: int) -> bool:
        """Is there a solid tile (inside the map) directly beside this box?

        Used for wall slides. Only the middle of the box is checked, so the
        corner of a ledge doesn't count as a wall.
        """
        size = self.tile_size
        x = right + 1.0 if side > 0 else left - 1.0
        tx = math.floor(x / size)
        if tx < 0 or tx >= self.width:
            return False
        for ty in range(math.floor((top + 4) / size), math.floor((bottom - 4 - EDGE_EPSILON) / size) + 1):
            if self.get(tx, ty) == TileCollision.SOLID:
                return True
        return False

    def is_standable(self, x: float, y: float) -> bool:
        """True if a point is inside a cell something could stand on."""
        tx, ty = self.tile_at(x, y)
        return self.get(tx, ty) != TileCollision.EMPTY
