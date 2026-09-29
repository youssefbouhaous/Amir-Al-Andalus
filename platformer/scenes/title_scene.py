"""Title screen and entry point for a new or saved journey."""

from typing import TYPE_CHECKING

import pygame

from core import settings
from core.input import Action
from core.session import GameSession
from rendering.background import ParallaxBackground
from scenes.scene import Scene
from ui.button import Menu
from ui.text import GOLD_TITLE, draw_text, render_arabic, wrap_text
from world.level_loader import LevelLoadError

if TYPE_CHECKING:
    from core.context import GameContext


CONTROLS = (
    "A / D or Left / Right - move",
    "Space / Z / K - jump (hold for higher jumps)",
    "X / J / Shift - throw stars with the star robe",
    "S / Down - enter wells",
    "Escape / P - pause     F11 - fullscreen",
    "F1 - debug view     F5 - reload the level",
    "Gamepad: left stick / D-pad, A to jump, B / X to attack",
    "Enter / Escape - back",
)


class TitleScene(Scene):
    def __init__(self, context: "GameContext", message: str | None = None) -> None:
        super().__init__(context)
        self._message = message
        self._showing_controls = False
        self._confirming_new = False
        self._elapsed = 0.0
        size = (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        self._background = ParallaxBackground(size, settings.MENU_SKY_THEME)
        self._title_font = context.assets.get_font(54, "display")
        self._menu_font = context.assets.get_font(settings.MENU_FONT_SIZE)
        self._small_font = context.assets.get_font(settings.SMALL_FONT_SIZE)
        self._arabic_title = render_arabic(
            context.assets.get_font(42, "arabic"), settings.WINDOW_TITLE_ARABIC, GOLD_TITLE
        )
        self._make_menu()

    def _make_menu(self) -> None:
        entries = []
        data = self.context.save.data
        if data.has_progress and not data.game_completed:
            entries.append(("Continue", self._continue_game))
        label = "New Journey" if data.has_progress else "Start Game"
        entries.extend([
            (label, self._new_game),
            ("Controls", self._show_controls),
            ("Quit", self.context.scenes.quit),
        ])
        self._menu = Menu(entries, (settings.SCREEN_WIDTH // 2, 320), self.context.audio)

    def on_enter(self) -> None:
        self.context.audio.play_music(settings.MENU_MUSIC)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self._showing_controls:
            self._menu.handle_event(event)

    def update(self, dt: float) -> None:
        self._elapsed += dt
        self._background.update(dt)
        inputs = self.context.input
        if self._showing_controls:
            if inputs.was_pressed(Action.CONFIRM) or inputs.was_pressed(Action.BACK) or inputs.was_pressed(Action.PAUSE):
                self._showing_controls = False
            return
        if self._confirming_new and (inputs.was_pressed(Action.BACK) or inputs.was_pressed(Action.PAUSE)):
            self._cancel_new()
            return
        self._menu.update(inputs)

    def _show_controls(self) -> None:
        self._showing_controls = True

    def _new_game(self) -> None:
        if not self.context.save.data.has_progress:
            self._start_new()
            return
        self._confirming_new = True
        self._menu = Menu(
            [("Keep my journey", self._cancel_new), ("Start a new journey", self._start_new)],
            (settings.SCREEN_WIDTH // 2, 335), self.context.audio,
        )

    def _cancel_new(self) -> None:
        self._confirming_new = False
        self._make_menu()

    def _start_new(self) -> None:
        self.context.save.reset_progress()
        self._start_level(settings.FIRST_LEVEL)

    def _continue_game(self) -> None:
        # Follow the maps' own next_level links so the menu also works when
        # new levels are added. A save resumes at the first unfinished level.
        file_name = settings.FIRST_LEVEL
        visited: set[str] = set()
        try:
            while self.context.save.data.is_completed(file_name):
                if file_name in visited:
                    raise LevelLoadError("The campaign contains a circular next_level link")
                visited.add(file_name)
                level = self.context.levels.load(file_name)
                if not level.next_level:
                    file_name = settings.FIRST_LEVEL
                    break
                file_name = level.next_level
        except LevelLoadError as error:
            self._message = str(error)
            return
        self._start_level(file_name)

    def _start_level(self, file_name: str) -> None:
        from scenes.level_intro_scene import LevelIntroScene

        self.context.save.data.seen_intro = True
        self.context.save.save()
        self.context.scenes.replace(LevelIntroScene(self.context, GameSession(file_name)))

    def draw(self, surface: pygame.Surface) -> None:
        self._background.draw(surface, scroll=self._elapsed * 12)
        center_x = surface.get_width() // 2
        surface.blit(self._arabic_title, self._arabic_title.get_rect(center=(center_x, 65)))
        draw_text(surface, self._title_font, settings.WINDOW_TITLE, style=GOLD_TITLE, center=(center_x, 123))
        draw_text(surface, self._small_font, settings.GAME_TAGLINE, center=(center_x, 174))
        if self._showing_controls:
            for index, line in enumerate(CONTROLS):
                draw_text(surface, self._small_font, line, center=(center_x, 235 + index * 32))
            return
        if self._confirming_new:
            draw_text(surface, self._small_font, "Replace your saved progress?", center=(center_x, 252))
        self._menu.draw(surface, self._menu_font)
        if self._message:
            for index, line in enumerate(wrap_text(self._small_font, self._message, surface.get_width() - 64)[:2]):
                draw_text(surface, self._small_font, line, settings.ERROR_TEXT_COLOR,
                          center=(center_x, 470 + index * 26))
        else:
            draw_text(surface, self._small_font, "Up / Down to choose  -  Enter to play",
                      center=(center_x, 486))
