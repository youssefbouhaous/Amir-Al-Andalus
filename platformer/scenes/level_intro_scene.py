import logging
from typing import TYPE_CHECKING

from core import settings
from core.session import GameSession
from scenes.message_scene import MessageScene
from world.level_loader import LevelLoadError

if TYPE_CHECKING:
    from core.context import GameContext

logger = logging.getLogger(__name__)


class LevelIntroScene(MessageScene):
    """The "level name / lives" card shown before each level.

    Loading happens here, so a broken level file sends the player back to the
    menu with an error message instead of crashing the game.
    """

    def __init__(self, context: "GameContext", session: GameSession) -> None:
        self._session = session
        self._error: str | None = None
        self._subtitle = ""
        try:
            self._level = context.levels.load(session.level_file)
            session.level_name = self._level.name
            self._subtitle = self._level.subtitle
            title = self._level.name
        except LevelLoadError as error:
            logger.error("%s", error)
            self._error = str(error)
            title = "Error"
        lines = [self._subtitle] if self._subtitle else []
        lines.append(f"Lives  x {session.lives}")
        super().__init__(
            context,
            title,
            lines,
            auto_continue_after=settings.LEVEL_INTRO_DURATION,
        )

    def update(self, dt: float) -> None:
        if self._error is not None:
            from scenes.menu_scene import MenuScene

            self.context.scenes.reset(MenuScene(self.context, self._error))
            return
        super().update(dt)

    def on_continue(self) -> None:
        from scenes.game_scene import GameScene

        self.context.scenes.replace(GameScene(self.context, self._session, self._level))
