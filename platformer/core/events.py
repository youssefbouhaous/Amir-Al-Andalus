"""Gameplay events.

Entities announce *what happened* ("a coin was collected") instead of
directly changing the score, playing sounds or spawning popups. The game scene
drains the queue once per update and routes each event to the systems that
care (session/score, audio, visual effects). This keeps entities ignorant of
scoring and audio, and makes adding a new reaction a one-line change.
"""

from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    PLAYER_JUMPED = auto()
    PLAYER_WALL_JUMPED = auto()
    PLAYER_LANDED = auto()      # value: impact speed (px/s)
    PLAYER_HURT = auto()
    PLAYER_DIED = auto()
    PLAYER_POWERED_UP = auto()  # value: new power level
    STAR_THROWN = auto()
    PLAYER_ATTACKED = auto()
    EXTRA_LIFE = auto()
    COIN_COLLECTED = auto()
    PAGE_COLLECTED = auto()     # value: page index
    ENEMY_STOMPED = auto()      # value: stomp combo count
    ENEMY_KNOCKED_OUT = auto()
    ENEMY_STARRED = auto()      # hit by a thrown star
    PROJECTILE_BLOCKED = auto()
    BLOCK_BUMPED = auto()
    BLOCK_BROKEN = auto()
    ITEM_SPAWNED = auto()
    CHECKPOINT_REACHED = auto()
    LEVEL_COMPLETED = auto()
    DOOR_ENTERED = auto()
    SPRING_BOUNCED = auto()
    PLATFORM_CRUMBLED = auto()
    SWITCH_TOGGLED = auto()     # value: "sun" or "moon" (the set now solid)
    SWITCH_WARNING = auto()
    SPLASH = auto()
    TORCH_LIT = auto()
    FIRE_SHOT = auto()
    BAT_SCREECH = auto()
    WIND_GUST = auto()
    CARPET_LAUNCHED = auto()
    BOSS_ROAR = auto()
    BOSS_HIT = auto()
    BOSS_SLAM = auto()
    BOSS_DEFEATED = auto()
    SWORD_APPEARED = auto()


@dataclass(frozen=True)
class GameEvent:
    type: EventType
    # World position where it happened (used for score popups).
    position: tuple[float, float]
    # Optional payload, e.g. the checkpoint id.
    value: int | str | None = None


class EventQueue:
    def __init__(self) -> None:
        self._events: list[GameEvent] = []

    def emit(
        self,
        event_type: EventType,
        position: tuple[float, float],
        value: int | str | None = None,
    ) -> None:
        self._events.append(GameEvent(event_type, position, value))

    def drain(self) -> list[GameEvent]:
        events, self._events = self._events, []
        return events
