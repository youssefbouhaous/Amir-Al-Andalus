"""Progress that survives deaths and level changes: score, coins, lives.

This is pure game logic with no rendering, so the HUD only *reads* it.
"""

from dataclasses import dataclass

from core import settings
from core.events import EventType, GameEvent

SCORE_TABLE: dict[EventType, int] = {
    EventType.COIN_COLLECTED: settings.SCORE_COIN,
    EventType.ENEMY_STOMPED: settings.SCORE_STOMP,
    EventType.ENEMY_KNOCKED_OUT: settings.SCORE_ENEMY_KNOCKED,
    EventType.BLOCK_BROKEN: settings.SCORE_BRICK,
    EventType.PLAYER_POWERED_UP: settings.SCORE_POWERUP,
    EventType.EXTRA_LIFE: settings.SCORE_EXTRA_LIFE,
    EventType.LEVEL_COMPLETED: settings.SCORE_LEVEL_COMPLETE,
}


@dataclass
class GameSession:
    level_file: str
    level_name: str = ""
    score: int = 0
    coins: int = 0
    lives: int = settings.STARTING_LIVES
    player_powered: bool = False
    # Tiled object id of the last checkpoint touched in the current level.
    checkpoint_id: int | None = None

    def apply_event(self, event: GameEvent) -> int:
        """Update progress for one event. Returns the points awarded."""
        points = SCORE_TABLE.get(event.type, 0)
        self.score += points

        match event.type:
            case EventType.COIN_COLLECTED:
                self._add_coin()
            case EventType.EXTRA_LIFE:
                self.lives += 1
            case EventType.PLAYER_POWERED_UP:
                self.player_powered = True
            case EventType.PLAYER_HURT:
                self.player_powered = False
            case EventType.CHECKPOINT_REACHED if isinstance(event.value, int):
                self.checkpoint_id = event.value
        return points

    def lose_life(self) -> None:
        self.lives -= 1
        self.player_powered = False

    @property
    def is_game_over(self) -> bool:
        return self.lives <= 0

    def enter_level(self, level_file: str) -> None:
        if level_file != self.level_file:
            self.checkpoint_id = None
        self.level_file = level_file

    def _add_coin(self) -> None:
        self.coins += 1
        if self.coins >= settings.COINS_PER_EXTRA_LIFE:
            self.coins -= settings.COINS_PER_EXTRA_LIFE
            self.lives += 1
