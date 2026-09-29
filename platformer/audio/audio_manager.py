"""Sound effects and music behind one small interface.

Every method is safe to call when audio is unavailable (no sound card, mixer
failed to initialise, file missing): it simply does nothing. Gameplay code
never needs to check.
"""

import logging

import pygame

from audio.synth import synthesize
from core import settings
from core.assets import AssetManager
from core.events import EventType, GameEvent

logger = logging.getLogger(__name__)

EVENT_SOUNDS: dict[EventType, str] = {
    EventType.PLAYER_JUMPED: "jump",
    EventType.COIN_COLLECTED: "coin",
    EventType.ENEMY_STOMPED: "stomp",
    EventType.ENEMY_KNOCKED_OUT: "kick",
    EventType.BLOCK_BUMPED: "bump",
    EventType.BLOCK_BROKEN: "break",
    EventType.ITEM_SPAWNED: "item_appear",
    EventType.PLAYER_POWERED_UP: "powerup",
    EventType.EXTRA_LIFE: "extra_life",
    EventType.PLAYER_HURT: "hurt",
    EventType.PLAYER_DIED: "death",
    EventType.CHECKPOINT_REACHED: "checkpoint",
    EventType.LEVEL_COMPLETED: "level_complete",
    EventType.DOOR_ENTERED: "door",
}


class AudioManager:
    def __init__(self, assets: AssetManager) -> None:
        self._assets = assets
        self._enabled = pygame.mixer.get_init() is not None
        self._current_music: str | None = None
        if not self._enabled:
            logger.warning("Audio unavailable; continuing without sound")

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        sound = self._assets.get_sound(name, lambda: synthesize(name))
        if sound is not None:
            sound.set_volume(settings.SFX_VOLUME)
            sound.play()

    def play_for_event(self, event: GameEvent) -> None:
        name = EVENT_SOUNDS.get(event.type)
        if name is not None:
            self.play(name)

    def play_music(self, name: str | None) -> None:
        """Loop ``assets/music/<name>.(ogg|mp3|wav)``; silence if it doesn't exist."""
        if not self._enabled or name == self._current_music:
            return
        self._current_music = name
        pygame.mixer.music.stop()
        if name is None:
            return
        path = self._assets.find_music(name)
        if path is None:
            logger.info("No music file for %r in assets/music; playing silence", name)
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
            pygame.mixer.music.play(loops=-1)
        except pygame.error as error:
            logger.warning("Could not play music %s: %s", path, error)

    def pause_music(self) -> None:
        if self._enabled:
            pygame.mixer.music.pause()

    def resume_music(self) -> None:
        if self._enabled:
            pygame.mixer.music.unpause()

    def stop_music(self) -> None:
        self.play_music(None)
