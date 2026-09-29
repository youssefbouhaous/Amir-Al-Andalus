"""Campaign progression helpers.

The original six maps keep their own ``next_level`` properties. When an
optional continuation map exists after a map with no explicit link, the
numeric filename supplies the link (for example level6 -> level7). This lets
new chapters be added without rewriting old Tiled files.
"""

import re
from pathlib import Path

from core import settings

_LEVEL_FILE = re.compile(r"^level([0-9]+)\.tmx$")


def next_level(file_name: str, explicit: str | None = None,
               maps_dir: Path = settings.MAPS_DIR) -> str | None:
    """Return the next map, preserving explicit Tiled links when present."""
    if explicit:
        return explicit
    match = _LEVEL_FILE.fullmatch(file_name)
    if match is None:
        return None
    candidate = f"level{int(match.group(1)) + 1}.tmx"
    return candidate if (maps_dir / candidate).is_file() else None


def has_unfinished_extension(completed: object,
                             maps_dir: Path = settings.MAPS_DIR) -> bool:
    """Whether a continuation chapter exists and its first map is unfinished."""
    first = maps_dir / "level7.tmx"
    checker = getattr(completed, "is_completed", None)
    return first.is_file() and callable(checker) and not checker(first.name)
