"""Persistent progress and options, stored as JSON in the user's data folder.

The save file is small and human-readable. Loading never crashes the game: a
missing file means a fresh save, and a corrupt one is renamed aside (so it can
be inspected) before starting fresh. Writes go to a temporary file that is
then renamed over the old one, so a crash mid-write can't destroy progress.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core import settings

logger = logging.getLogger(__name__)

SAVE_VERSION = 1


@dataclass
class LevelRecord:
    completed: bool = False
    best_score: int = 0
    best_time: float | None = None
    pages: list[int] = field(default_factory=list)
    # Standalone runs start at zero; journey scores can span several maps.
    best_replay_score: int | None = None

    def merge_pages(self, pages: set[int]) -> None:
        self.pages = sorted(set(self.pages) | pages)


@dataclass
class Options:
    music_volume: float = settings.DEFAULT_MUSIC_VOLUME
    sfx_volume: float = settings.DEFAULT_SFX_VOLUME
    fullscreen: bool = False
    screen_shake: bool = True
    show_timer: bool = True


@dataclass
class SaveData:
    levels: dict[str, LevelRecord] = field(default_factory=dict)
    options: Options = field(default_factory=Options)
    seen_intro: bool = False
    game_completed: bool = False
    total_deaths: int = 0

    def record(self, level_file: str) -> LevelRecord:
        record = self.levels.get(level_file)
        if record is None:
            record = LevelRecord()
            self.levels[level_file] = record
        return record

    def is_completed(self, level_file: str) -> bool:
        record = self.levels.get(level_file)
        return record is not None and record.completed

    @property
    def total_pages(self) -> int:
        return sum(len(record.pages) for record in self.levels.values())

    @property
    def has_progress(self) -> bool:
        return self.seen_intro or any(record.completed for record in self.levels.values())


def _clamp01(value: object, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _from_dict(raw: dict) -> SaveData:
    """Build SaveData from JSON, tolerating missing or mistyped fields."""
    data = SaveData()
    for name, value in (raw.get("levels") or {}).items():
        if not isinstance(value, dict):
            continue
        best_time = value.get("best_time")
        data.levels[str(name)] = LevelRecord(
            completed=bool(value.get("completed", False)),
            best_score=int(value.get("best_score", 0) or 0),
            best_time=float(best_time) if isinstance(best_time, (int, float)) else None,
            pages=sorted({int(page) for page in value.get("pages", []) if isinstance(page, int)}),
            best_replay_score=(max(0, int(value["best_replay_score"]))
                               if isinstance(value.get("best_replay_score"), int) else None),
        )
    options = raw.get("options") or {}
    defaults = Options()
    data.options = Options(
        music_volume=_clamp01(options.get("music_volume"), defaults.music_volume),
        sfx_volume=_clamp01(options.get("sfx_volume"), defaults.sfx_volume),
        fullscreen=bool(options.get("fullscreen", defaults.fullscreen)),
        screen_shake=bool(options.get("screen_shake", defaults.screen_shake)),
        show_timer=bool(options.get("show_timer", defaults.show_timer)),
    )
    data.seen_intro = bool(raw.get("seen_intro", False))
    data.game_completed = bool(raw.get("game_completed", False))
    data.total_deaths = int(raw.get("total_deaths", 0) or 0)
    return data


class SaveManager:
    def __init__(self, directory: Path = settings.SAVE_DIR, file_name: str = settings.SAVE_FILE) -> None:
        self._path = directory / file_name
        self.data = self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> SaveData:
        if not self._path.is_file():
            return SaveData()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("save root is not an object")
            return _from_dict(raw)
        except (OSError, ValueError, TypeError) as error:
            backup = self._path.with_suffix(".corrupt.json")
            logger.warning("Save file unreadable (%s); moving it to %s", error, backup)
            try:
                os.replace(self._path, backup)
            except OSError:
                pass
            return SaveData()

    def save(self) -> None:
        payload = {"version": SAVE_VERSION, **asdict(self.data)}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError as error:
            logger.warning("Could not write save file %s: %s", self._path, error)

    def reset_progress(self) -> None:
        """Start a new journey but keep the player's options."""
        options = self.data.options
        self.data = SaveData(options=options)
        self.save()
