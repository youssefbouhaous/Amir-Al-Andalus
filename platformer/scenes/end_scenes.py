"""Screens shown between/after levels."""

from typing import TYPE_CHECKING

from core import settings
from core.session import GameSession
from scenes.message_scene import MessageScene
from world.level_data import LevelData

if TYPE_CHECKING:
    from core.context import GameContext


class LevelCompleteScene(MessageScene):
    def __init__(self, context: "GameContext", session: GameSession, level: LevelData) -> None:
        super().__init__(
            context,
            "Level Complete!",
            [level.name, f"Score  {session.score}"],
            auto_continue_after=settings.LEVEL_COMPLETE_SCREEN_DURATION,
        )
        self._session = session
        self._level = level

    def on_continue(self) -> None:
        from scenes.level_intro_scene import LevelIntroScene

        next_level = self._level.next_level
        if next_level:
            self._session.enter_level(next_level)
            self.context.scenes.replace(LevelIntroScene(self.context, self._session))
        else:
            self.context.scenes.replace(VictoryScene(self.context, self._session))


class GameOverScene(MessageScene):
    def __init__(self, context: "GameContext", session: GameSession) -> None:
        super().__init__(
            context,
            "Game Over",
            ["The journey ends here... for now.", f"Final score  {session.score}", "Press Enter"],
            title_color=settings.ERROR_TEXT_COLOR,
        )

    def on_enter(self) -> None:
        self.context.audio.stop_music()

    def on_continue(self) -> None:
        from scenes.menu_scene import MenuScene

        self.context.scenes.reset(MenuScene(self.context))


class VictoryScene(MessageScene):
    def __init__(self, context: "GameContext", session: GameSession) -> None:
        super().__init__(
            context,
            "The Sword is Yours!",
            [
                "The prince raises the Sword of Light over al-Andalus.",
                f"Final score  {session.score}",
                "Press Enter",
            ],
        )

    def on_enter(self) -> None:
        self.context.audio.stop_music()

    def on_continue(self) -> None:
        from scenes.menu_scene import MenuScene

        self.context.scenes.reset(MenuScene(self.context))
