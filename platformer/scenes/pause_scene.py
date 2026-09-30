from typing import TYPE_CHECKING

import pygame

from core import settings
from core.input import Action
from scenes.scene import Scene
from ui.button import Menu
from ui.text import draw_text

if TYPE_CHECKING:
    from core.context import GameContext
    from scenes.game_scene import GameScene

TITLE_Y = 150
MENU_CENTER_Y = 310


class PauseScene(Scene):
    """Overlay drawn on top of the frozen game scene.

    The game scene simply stops receiving update() calls while this is on
    top of the stack; no "if paused" checks are needed anywhere.
    """

    is_overlay = True

    def __init__(self, context: "GameContext", game_scene: "GameScene") -> None:
        super().__init__(context)
        self._game_scene = game_scene
        self._overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(settings.OVERLAY_COLOR)
        self._title_font = context.assets.get_font(settings.TITLE_FONT_SIZE)
        self._menu_font = context.assets.get_font(settings.MENU_FONT_SIZE)
        self._menu = Menu(
            [
                ("Resume", self._resume),
                ("Restart from checkpoint", self._restart),
                ("Level Select" if game_scene.session.replay else "Main Menu", self._main_menu),
            ],
            (settings.SCREEN_WIDTH // 2, MENU_CENTER_Y),
            context.audio,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        self._menu.handle_event(event)

    def update(self, dt: float) -> None:
        if self.context.input.was_pressed(Action.PAUSE):
            self._resume()
            return
        self._menu.update(self.context.input)

    def _resume(self) -> None:
        self.context.scenes.pop()

    def _restart(self) -> None:
        self._game_scene.restart_from_checkpoint()
        self.context.scenes.pop()

    def _main_menu(self) -> None:
        if self._game_scene.session.replay:
            from scenes.level_select_scene import LevelSelectScene

            self.context.scenes.reset(LevelSelectScene(self.context, self._game_scene.session.level_file))
            return
        from scenes.menu_scene import MenuScene

        self.context.scenes.reset(MenuScene(self.context))

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))
        draw_text(
            surface, self._title_font, "Paused", settings.TITLE_COLOR,
            center=(surface.get_width() // 2, TITLE_Y),
        )
        self._menu.draw(surface, self._menu_font)
