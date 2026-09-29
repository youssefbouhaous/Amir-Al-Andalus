from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from core.context import GameContext


class Scene(ABC):
    """One screen of the game: menu, gameplay, pause, game over...

    The main loop only talks to this interface, so adding a new screen never
    requires touching the loop itself.
    """

    # Overlay scenes (pause) are drawn on top of the scene below them.
    is_overlay = False

    def __init__(self, context: "GameContext") -> None:
        self.context = context

    def on_enter(self) -> None:
        """Called when the scene becomes active for the first time."""

    def on_resume(self) -> None:
        """Called when a scene pushed on top of this one is popped."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """React to raw events (mouse). Keyboard goes through InputState."""

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds."""

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Render the current state. Must not change game state."""

    def debug_lines(self) -> list[str]:
        return []
