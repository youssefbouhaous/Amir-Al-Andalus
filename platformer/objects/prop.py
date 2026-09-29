"""Base class for level objects that aren't blocks, platforms or enemies.

Props update every step, draw on one of three layers, may emit lights, and
may react while the player overlaps them (``on_touch``). The world keeps
them in one list, so adding a new kind of object never touches World.
"""

from typing import TYPE_CHECKING, ClassVar

import pygame

from rendering.camera import Camera
from rendering.lighting import Light

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World


class Prop:
    # "back": behind entities; "mid": with entities; "front": in front of the player.
    layer: ClassVar[str] = "back"
    # Only props with this set get on_touch calls.
    touchable: ClassVar[bool] = False

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        self.alive = True

    def update(self, dt: float, world: "World") -> None:
        pass

    def on_touch(self, player: "Player", world: "World") -> None:
        pass

    def touch_rect(self) -> pygame.Rect:
        return self.rect

    def lights(self) -> list[Light]:
        return []

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        pass
