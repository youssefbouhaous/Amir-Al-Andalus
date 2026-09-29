from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

from rendering.camera import Camera

if TYPE_CHECKING:
    from world.world import World


class Entity(ABC):
    """Anything dynamic in the world that updates, draws and can be removed.

    Kept deliberately thin: shared *behaviour* (physics, animation) is added by
    composition (Body, Animator), not by growing this base class.
    """

    def __init__(self) -> None:
        self.alive = True

    @property
    @abstractmethod
    def rect(self) -> pygame.Rect: ...

    @abstractmethod
    def update(self, dt: float, world: "World") -> None: ...

    @abstractmethod
    def draw(self, surface: pygame.Surface, camera: Camera) -> None: ...
