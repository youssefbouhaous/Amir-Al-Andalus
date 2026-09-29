"""Progress that survives deaths and level changes: score, coins, lives.

This is pure game logic with no rendering, so the HUD only *reads* it.
Per-level statistics (time, pages, enemies) reset on ``enter_level`` and feed
the end-of-level tally.
"""

from dataclasses import dataclass, field

from core import settings
from core.events import EventType, GameEvent

SCORE_TABLE: dict[EventType, int] = {
    EventType.COIN_COLLECTED: settings.SCORE_COIN,
    EventType.ENEMY_KNOCKED_OUT: settings.SCORE_ENEMY_KNOCKED,
    EventType.ENEMY_STARRED: settings.SCORE_ENEMY_STARRED,
    EventType.BLOCK_BROKEN: settings.SCORE_BRICK,
    EventType.PLAYER_POWERED_UP: settings.SCORE_POWERUP,
    EventType.EXTRA_LIFE: settings.SCORE_EXTRA_LIFE,
    EventType.LEVEL_COMPLETED: settings.SCORE_LEVEL_COMPLETE,
    EventType.BOSS_HIT: settings.SCORE_BOSS_HIT,
    EventType.BOSS_DEFEATED: settings.SCORE_BOSS_DEFEATED,
}
ENEMY_EVENTS = frozenset({EventType.ENEMY_STOMPED, EventType.ENEMY_KNOCKED_OUT, EventType.ENEMY_STARRED})
# Chained stomps without touching the ground score more each time; the
# eighth and later earn an extra life instead.
STOMP_CHAIN = (100, 200, 400, 800, 1000, 2000, 4000)


@dataclass
class GameSession:
    level_file: str
    level_name: str = ""
    score: int = 0
    coins: int = 0
    lives: int = settings.STARTING_LIVES
    power: int = 0
    # Tiled object id of the last checkpoint touched in the current level.
    checkpoint_id: int | None = None
    # --- per-level stats ---
    level_time: float = 0.0
    level_deaths: int = 0
    level_coins: int = 0
    level_enemies: int = 0
    pages_found: set[int] = field(default_factory=set)
    total_deaths: int = 0

    @property
    def player_powered(self) -> bool:
        return self.power > 0

    def apply_event(self, event: GameEvent) -> int:
        """Update progress for one event. Returns the points awarded."""
        points = SCORE_TABLE.get(event.type, 0)

        match event.type:
            case EventType.COIN_COLLECTED:
                self._add_coin()
            case EventType.EXTRA_LIFE:
                self.lives += 1
            case EventType.PLAYER_POWERED_UP if isinstance(event.value, int):
                self.power = max(self.power, event.value) if event.value == 1 else event.value
            case EventType.PLAYER_HURT if isinstance(event.value, int):
                self.power = event.value
            case EventType.CHECKPOINT_REACHED if isinstance(event.value, int):
                self.checkpoint_id = event.value
            case EventType.PAGE_COLLECTED if isinstance(event.value, int):
                if event.value >= 0 and event.value not in self.pages_found:
                    self.pages_found.add(event.value)
                    points = settings.SCORE_PAGE
            case EventType.ENEMY_STOMPED:
                combo = event.value if isinstance(event.value, int) else 1
                if combo > len(STOMP_CHAIN):
                    self.lives += 1
                    points = 0
                else:
                    points = STOMP_CHAIN[combo - 1]
        if event.type in ENEMY_EVENTS:
            self.level_enemies += 1
        self.score += points
        return points

    def lose_life(self) -> None:
        self.lives -= 1
        self.power = 0
        self.level_deaths += 1
        self.total_deaths += 1

    @property
    def is_game_over(self) -> bool:
        return self.lives <= 0

    def enter_level(self, level_file: str) -> None:
        if level_file != self.level_file:
            self.checkpoint_id = None
            self.reset_level_stats()
        self.level_file = level_file

    def reset_level_stats(self) -> None:
        self.level_time = 0.0
        self.level_deaths = 0
        self.level_coins = 0
        self.level_enemies = 0
        self.pages_found = set()

    def continue_after_game_over(self) -> None:
        """Start the same level again with fresh lives but no score."""
        self.lives = settings.STARTING_LIVES
        self.score = 0
        self.coins = 0
        self.power = 0
        self.checkpoint_id = None
        self.reset_level_stats()

    def _add_coin(self) -> None:
        self.coins += 1
        self.level_coins += 1
        if self.coins >= settings.COINS_PER_EXTRA_LIFE:
            self.coins -= settings.COINS_PER_EXTRA_LIFE
            self.lives += 1
