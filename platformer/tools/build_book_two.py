"""Write the Book II maps (level11.tmx onward) and nothing else.

    python -m tools.build_book_two            # all Book II levels
    python -m tools.build_book_two level12    # just one

Levels 1-10 and the shared tileset are never rewritten by this script.
"""

import os
import sys

import pygame

from core import settings
from tools.level_format import build_level, write_xml
from tools.levels.book_two import LEVELS


def main() -> int:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    wanted = {name.removesuffix(".tmx") for name in sys.argv[1:]}
    for level in LEVELS:
        if wanted and level.file_name.removesuffix(".tmx") not in wanted:
            continue
        number = int(level.file_name.removeprefix("level").removesuffix(".tmx"))
        if number <= 10:
            raise SystemExit(f"Refusing to overwrite {level.file_name}: Book II starts at level11")
        write_xml(build_level(level), settings.MAPS_DIR / level.file_name)
        print(f"Wrote {settings.MAPS_DIR / level.file_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
