"""The physical part of anything that moves and collides.

Player, enemies and items all *have* a Body (composition) rather than
inheriting collision behaviour, so they share one collision implementation.

Positions are floats. pygame.Rect stores ints, and truncating every frame
causes the classic "slowly sinking into the floor" and jitter bugs, so Rects
are only created for rendering and coarse overlap tests.
"""

from dataclasses import dataclass, field
from typing import Protocol

import pygame


class PlatformSurface(Protocol):
    """Anything a body can stand on and be carried by (moving platforms)."""

    @property
    def left(self) -> float: ...

    @property
    def right(self) -> float: ...

    @property
    def top(self) -> float: ...

    @property
    def previous_top(self) -> float: ...

    @property
    def delta(self) -> pygame.Vector2: ...


@dataclass
class Body:
    x: float
    y: float
    width: float
    height: float
    velocity: pygame.Vector2 = field(default_factory=pygame.Vector2)
    # Extra displacement speed applied by the world for one step (wind).
    external: pygame.Vector2 = field(default_factory=pygame.Vector2)

    # Contact state, rewritten by every call to move_body().
    on_ground: bool = False
    hit_ceiling: bool = False
    hit_wall: int = 0  # -1 = wall on the left, 1 = on the right, 0 = none
    ground_platform: PlatformSurface | None = None

    @classmethod
    def from_midbottom(
        cls, midbottom: tuple[float, float], width: float, height: float
    ) -> "Body":
        return cls(midbottom[0] - width / 2, midbottom[1] - height, width, height)

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def centerx(self) -> float:
        return self.x + self.width / 2

    @property
    def centery(self) -> float:
        return self.y + self.height / 2

    @property
    def midbottom(self) -> tuple[float, float]:
        return self.centerx, self.bottom

    def place_midbottom(self, midbottom: tuple[float, float]) -> None:
        self.x = midbottom[0] - self.width / 2
        self.y = midbottom[1] - self.height

    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), round(self.width), round(self.height))

    def clear_contacts(self) -> None:
        self.on_ground = False
        self.hit_ceiling = False
        self.hit_wall = 0
        self.ground_platform = None
