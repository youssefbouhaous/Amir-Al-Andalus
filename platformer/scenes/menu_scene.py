from typing import TYPE_CHECKING

import pygame

from core import settings
from core.input import Action
from core.session import GameSession
from rendering.background import ParallaxBackground
from scenes.scene import Scene
from ui.button import Menu
from ui.text import draw_text

if TYPE_CHECKING:
    from core.context import GameContext

TITLE_Y = 100
TAGLINE_Y = 158
MENU_CENTER_Y = 300
MESSAGE_Y_FROM_BOTTOM = 40
CONTROLS_LINE_HEIGHT = 30
CONTROLS_TOP = 200

CONTROLS_TEXT = (
    "A / D  or  Left / Right  -  move",
    "Space  -  jump (hold for higher jumps)",
    "S / Down  -  enter the tiled wells",
    "Escape  -  pause",
    "F1  -  debug view      F5  -  reload level file",
    "",
    "Press Enter to go back",
)


class MenuScene(Scene):
    def __init__(self, context: "GameContext", message: str | None = None) -> None:
        super().__init__(context)
        self._message = message
        self._showing_controls = False
        width, height = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self._background = ParallaxBackground((width, height), settings.MENU_SKY_THEME)
        self._title_font = context.assets.get_font(settings.TITLE_FONT_SIZE)
        self._menu_font = context.assets.get_font(settings.MENU_FONT_SIZE)
        self._small_font = context.assets.get_font(settings.SMALL_FONT_SIZE)
        self._menu = Menu(
            [
                ("Start Game", self._start_game),
                ("Controls", self._show_controls),
                ("Quit", context.scenes.quit),
            ],
            (width // 2, MENU_CENTER_Y),
            context.audio,
        )

    def on_enter(self) -> None:
        self.context.audio.play_music(settings.MENU_MUSIC)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self._showing_controls:
            self._menu.handle_event(event)

    def update(self, dt: float) -> None:
        if self._showing_controls:
            input_state = self.context.input
            if input_state.was_pressed(Action.CONFIRM) or input_state.was_pressed(Action.PAUSE):
                self._showing_controls = False
            return
        self._menu.update(self.context.input)

    def _start_game(self) -> None:
        # Imported here to avoid a circular import (intro -> game -> menu).
        from scenes.level_intro_scene import LevelIntroScene

        session = GameSession(level_file=settings.FIRST_LEVEL)
        self.context.scenes.replace(LevelIntroScene(self.context, session))

    def _show_controls(self) -> None:
        self._showing_controls = True

    def draw(self, surface: pygame.Surface) -> None:
        self._background.draw(surface)
        center_x = surface.get_width() // 2
        draw_text(
            surface, self._title_font, settings.WINDOW_TITLE.upper(), settings.TITLE_COLOR,
            center=(center_x, TITLE_Y),
        )
        draw_text(
            surface, self._small_font, settings.GAME_TAGLINE,
            center=(center_x, TAGLINE_Y),
        )
        if self._showing_controls:
            for index, line in enumerate(CONTROLS_TEXT):
                draw_text(
                    surface, self._small_font, line,
                    center=(center_x, CONTROLS_TOP + index * CONTROLS_LINE_HEIGHT),
                )
            return

        self._menu.draw(surface, self._menu_font)
        if self._message:
            draw_text(
                surface, self._small_font, self._message, settings.ERROR_TEXT_COLOR,
                center=(center_x, surface.get_height() - MESSAGE_Y_FROM_BOTTOM),
            )
