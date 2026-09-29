"""Sound effects and music behind one small interface.

Every method is safe to call when audio is unavailable (no sound card, mixer
failed to initialise, file missing): it simply does nothing. Gameplay code
never needs to check.

Music comes from ``assets/music/<name>.(ogg|mp3|wav)`` when such a file
exists; otherwise the track is composed procedurally (``audio/music.py``).
Composing takes a second or two, so it runs on a background thread and the
result is cached on disk; a track requested before it's ready starts (with a
fade-in) as soon as it is.
"""

import logging
import threading
import wave
from pathlib import Path

import numpy as np
import pygame

from audio import music
from audio.synth import synthesize, to_sound
from core import settings
from core.assets import AssetManager
from core.events import EventType, GameEvent

logger = logging.getLogger(__name__)

MUSIC_CACHE_VERSION = 3
MUSIC_FADE_IN_MS = 600
# The same effect retriggered faster than this is skipped (coin bursts).
RETRIGGER_SECONDS = 0.035
# Tracks composed in the background at startup, most urgent first.
PREWARM = ("title", "story", "map", "level1", "level2", "level3", "level4", "level5", "level6", "boss", "ending")

EVENT_SOUNDS: dict[EventType, str] = {
    EventType.PLAYER_JUMPED: "jump",
    EventType.PLAYER_WALL_JUMPED: "wall_jump",
    EventType.COIN_COLLECTED: "coin",
    EventType.PAGE_COLLECTED: "page",
    EventType.ENEMY_KNOCKED_OUT: "kick",
    EventType.ENEMY_STARRED: "kick",
    EventType.BLOCK_BUMPED: "bump",
    EventType.BLOCK_BROKEN: "break",
    EventType.ITEM_SPAWNED: "item_appear",
    EventType.EXTRA_LIFE: "extra_life",
    EventType.PLAYER_HURT: "hurt",
    EventType.PLAYER_DIED: "death",
    EventType.CHECKPOINT_REACHED: "checkpoint",
    EventType.LEVEL_COMPLETED: "level_complete",
    EventType.DOOR_ENTERED: "door",
    EventType.SPRING_BOUNCED: "spring",
    EventType.PLATFORM_CRUMBLED: "crumble",
    EventType.SWITCH_TOGGLED: "switch",
    EventType.SWITCH_WARNING: "tick",
    EventType.SPLASH: "splash",
    EventType.FIRE_SHOT: "fire",
    EventType.WIND_GUST: "wind",
    EventType.CARPET_LAUNCHED: "carpet",
    EventType.STAR_THROWN: "throw",
    EventType.PROJECTILE_BLOCKED: "clink",
    EventType.BOSS_ROAR: "roar",
    EventType.BOSS_HIT: "boss_hit",
    EventType.BOSS_SLAM: "slam",
    EventType.BOSS_DEFEATED: "boss_defeated",
    EventType.SWORD_APPEARED: "sword",
}


def _cache_path(name: str) -> Path:
    return settings.CACHE_DIR / "music" / f"{name}-v{MUSIC_CACHE_VERSION}.wav"


def _write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with wave.open(str(temporary), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(music.SR)
        file.writeframes(np.ascontiguousarray(samples).tobytes())
    temporary.replace(path)


def _read_wav(path: Path) -> np.ndarray | None:
    try:
        with wave.open(str(path), "rb") as file:
            if file.getnchannels() != 2 or file.getsampwidth() != 2 or file.getframerate() != music.SR:
                return None
            data = np.frombuffer(file.readframes(file.getnframes()), dtype=np.int16)
        return data.reshape(-1, 2)
    except (OSError, wave.Error, ValueError):
        return None


class _MusicLibrary:
    """Composes tracks on a worker thread; the main thread only reads results."""

    def __init__(self) -> None:
        self._ready: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()
        self._wanted: list[str] = list(PREWARM)
        self._event = threading.Event()
        self._event.set()
        self._thread = threading.Thread(target=self._work, name="music-composer", daemon=True)
        self._thread.start()

    def request(self, name: str) -> np.ndarray | None:
        with self._lock:
            samples = self._ready.get(name)
            if samples is None and name not in self._wanted:
                self._wanted.insert(0, name)
            elif samples is None:
                # Move it to the front of the queue.
                self._wanted.remove(name)
                self._wanted.insert(0, name)
        self._event.set()
        return samples

    def _work(self) -> None:
        while True:
            self._event.wait()
            with self._lock:
                if not self._wanted:
                    self._event.clear()
                    continue
                name = self._wanted.pop(0)
                if name in self._ready:
                    continue
            samples = _read_wav(_cache_path(name))
            if samples is None:
                try:
                    samples = music.render_track(name)
                except Exception:  # never let a composing bug kill audio
                    logger.exception("Could not compose track %r", name)
                    samples = None
                if samples is not None:
                    try:
                        _write_wav(_cache_path(name), samples)
                    except OSError as error:
                        logger.info("Could not cache track %r: %s", name, error)
            if samples is not None:
                with self._lock:
                    self._ready[name] = samples


class AudioManager:
    def __init__(self, assets: AssetManager) -> None:
        self._assets = assets
        self._enabled = pygame.mixer.get_init() is not None
        self._current_music: str | None = None
        self._pending_music: str | None = None
        self._music_sounds: dict[str, pygame.mixer.Sound] = {}
        self._streaming = False
        self._music_volume = settings.DEFAULT_MUSIC_VOLUME
        self._sfx_volume = settings.DEFAULT_SFX_VOLUME
        self._last_played: dict[str, int] = {}
        self._music_channel: pygame.mixer.Channel | None = None
        self._jingle_channel: pygame.mixer.Channel | None = None
        self._library: _MusicLibrary | None = None
        if not self._enabled:
            logger.warning("Audio unavailable; continuing without sound")
            return
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(2)
        self._music_channel = pygame.mixer.Channel(0)
        self._jingle_channel = pygame.mixer.Channel(1)
        self._library = _MusicLibrary()

    # --- volume ----------------------------------------------------------------
    def set_volumes(self, music_volume: float, sfx_volume: float) -> None:
        self._music_volume = music_volume
        self._sfx_volume = sfx_volume
        if not self._enabled:
            return
        if self._music_channel is not None:
            self._music_channel.set_volume(self._music_level())
        pygame.mixer.music.set_volume(self._music_level())

    def _music_level(self) -> float:
        return self._music_volume * settings.MUSIC_VOLUME * 1.6

    # --- effects ----------------------------------------------------------------
    def play(self, name: str, volume: float = 1.0) -> None:
        if not self._enabled or self._sfx_volume <= 0:
            return
        now = pygame.time.get_ticks()
        if now - self._last_played.get(name, -10_000) < RETRIGGER_SECONDS * 1000:
            return
        self._last_played[name] = now
        sound = self._assets.get_sound(name, lambda: synthesize(name))
        if sound is not None:
            sound.set_volume(min(1.0, self._sfx_volume * settings.SFX_VOLUME * 1.4 * volume))
            sound.play()

    def play_for_event(self, event: GameEvent) -> None:
        match event.type:
            case EventType.ENEMY_STOMPED:
                combo = event.value if isinstance(event.value, int) else 1
                self.play(f"stomp{min(8, max(1, combo))}")
                return
            case EventType.PLAYER_LANDED:
                if isinstance(event.value, int) and event.value > settings.PLAYER_PHYSICS.hard_landing_speed:
                    self.play("land", 0.8)
                return
            case EventType.PLAYER_POWERED_UP:
                self.play("star_power" if event.value == 2 else "powerup")
                return
            case EventType.BAT_SCREECH:
                self.play("flutter" if event.value == "pigeons" else "screech")
                return
            case EventType.SWITCH_WARNING:
                self.play("tick", 0.7)
                return
        name = EVENT_SOUNDS.get(event.type)
        if name is not None:
            self.play(name)

    def play_jingle(self, name: str) -> None:
        """A short musical stinger over (ducked) music."""
        if not self._enabled or self._jingle_channel is None:
            return
        key = f"jingle:{name}"
        sound = self._music_sounds.get(key)
        if sound is None:
            samples = music.render_jingle(name)
            if samples is None:
                return
            sound = to_sound(samples)
            if sound is None:
                return
            self._music_sounds[key] = sound
        self._jingle_channel.set_volume(min(1.0, self._music_level() * 1.2 + 0.1))
        self._jingle_channel.play(sound)

    # --- music --------------------------------------------------------------------
    def play_music(self, name: str | None, restart: bool = False) -> None:
        """Loop a track; ``None`` stops the music."""
        if not self._enabled:
            return
        if name == self._current_music and not restart and name is not None:
            if self._pending_music is None and not self._is_music_playing():
                restart = True
            else:
                return
        self._stop_current()
        self._current_music = name
        self._pending_music = None
        if name is None:
            return
        path = self._assets.find_music(name)
        if path is not None:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._music_level())
                pygame.mixer.music.play(loops=-1, fade_ms=MUSIC_FADE_IN_MS)
                self._streaming = True
                return
            except pygame.error as error:
                logger.warning("Could not play music %s: %s", path, error)
        if not self._start_generated(name):
            self._pending_music = name

    def _start_generated(self, name: str) -> bool:
        sound = self._music_sounds.get(name)
        if sound is None and self._library is not None:
            samples = self._library.request(name)
            if samples is None:
                return False
            sound = to_sound(samples)
            if sound is None:
                return True  # mixer can't play it; don't keep waiting
            self._music_sounds[name] = sound
        if sound is None or self._music_channel is None:
            return True
        self._music_channel.set_volume(self._music_level())
        self._music_channel.play(sound, loops=-1, fade_ms=MUSIC_FADE_IN_MS)
        return True

    def _is_music_playing(self) -> bool:
        if self._streaming:
            return pygame.mixer.music.get_busy()
        return self._music_channel is not None and self._music_channel.get_busy()

    def _stop_current(self) -> None:
        if self._streaming:
            pygame.mixer.music.stop()
            self._streaming = False
        if self._music_channel is not None:
            self._music_channel.stop()

    def update(self) -> None:
        """Start a track that finished composing after it was requested."""
        if self._pending_music is not None and self._start_generated(self._pending_music):
            self._pending_music = None

    def fade_music(self, milliseconds: int) -> None:
        if not self._enabled:
            return
        self._pending_music = None
        if self._streaming:
            pygame.mixer.music.fadeout(milliseconds)
        elif self._music_channel is not None:
            self._music_channel.fadeout(milliseconds)

    def pause_music(self) -> None:
        if not self._enabled:
            return
        if self._streaming:
            pygame.mixer.music.pause()
        elif self._music_channel is not None:
            self._music_channel.pause()

    def resume_music(self) -> None:
        if not self._enabled:
            return
        if self._streaming:
            pygame.mixer.music.unpause()
        elif self._music_channel is not None:
            self._music_channel.unpause()

    def stop_music(self) -> None:
        self.play_music(None)
