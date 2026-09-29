"""Shared base for full-screen message screens (level intro, level complete,
game over, victory): a title, a few lines, then continue."""

from abc import abstractmethod
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.input import Action
from scenes.scene import Scene
from ui.text import draw_text

if TYPE_CHECKING:
    from core.context import GameContext

# Ignore Confirm briefly so a held/mashed key doesn't skip the screen instantly.
INPUT_GRACE_PERIOD = 0.4
LINE_SPACING = 44
TITLE_OFFSET = 70


class MessageScene(Scene):
    def __init__(
        self,
        context: "GameContext",
        title: str,
        lines: list[str],
        auto_continue_after: float | None = None,
        title_color: settings.Color = settings.TITLE_COLOR,
    ) -> None:
        super().__init__(context)
        self._title = title
        self._lines = lines
        self._auto_continue_after = auto_continue_after
        self._title_color = title_color
        self._elapsed = 0.0
        self._done = False
        self._title_font = context.assets.get_font(settings.TITLE_FONT_SIZE)
        self._line_font = context.assets.get_font(settings.SUBTITLE_FONT_SIZE)

    def update(self, dt: float) -> None:
        if self._done:
            return
        self._elapsed += dt
        confirmed = (
            self._elapsed >= INPUT_GRACE_PERIOD
            and self.context.input.was_pressed(Action.CONFIRM)
        )
        timed_out = (
            self._auto_continue_after is not None and self._elapsed >= self._auto_continue_after
        )
        if confirmed or timed_out:
            self._done = True
            self.on_continue()

    @abstractmethod
    def on_continue(self) -> None: ...

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.MENU_BACKGROUND_COLOR)
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        draw_text(
            surface, self._title_font, self._title, self._title_color,
            center=(center_x, center_y - TITLE_OFFSET),
        )
        for index, line in enumerate(self._lines):
            draw_text(
                surface, self._line_font, line,
                center=(center_x, center_y + index * LINE_SPACING),
            )
