import pygame


class TileLayer:
    """A purely visual grid of tiles: one image and one tile name per cell.

    The names let the terrain renderer auto-tile (caps, rims, depth shading)
    without caring which tileset image a tile came from.
    """

    def __init__(
        self,
        name: str,
        width: int,
        height: int,
        tile_size: int,
        tiles: list[pygame.Surface | None],
        names: list[str | None] | None = None,
    ) -> None:
        if len(tiles) != width * height:
            raise ValueError(f"Layer {name!r}: tile count does not match size")
        self.name = name
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = tiles
        self.names = names if names is not None else [None] * (width * height)

    def image_at(self, tx: int, ty: int) -> pygame.Surface | None:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.tiles[ty * self.width + tx]
        return None

    def name_at(self, tx: int, ty: int) -> str | None:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.names[ty * self.width + tx]
        return None
