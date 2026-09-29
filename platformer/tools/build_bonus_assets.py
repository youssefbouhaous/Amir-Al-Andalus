"""Write only the additional campaign maps (level7.tmx through level10.tmx).

This script intentionally never rewrites levels 1-6 or the shared tileset:

    python -m tools.build_bonus_assets --force
"""

import argparse

from core import settings
from tools.level_format import build_level, write_xml
from tools.levels.extended_campaign import LEVELS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite only level7-level10")
    args = parser.parse_args()
    maps = settings.MAPS_DIR
    existing = [level.file_name for level in LEVELS if (maps / level.file_name).exists()]
    if existing and not args.force:
        answer = input(f"Overwrite {', '.join(existing)}? [y/N] ")
        if answer.strip().lower() != "y":
            return 1
    for level in LEVELS:
        write_xml(build_level(level), maps / level.file_name)
        print(f"Wrote {maps / level.file_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
