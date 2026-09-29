"""Generate campaign maps and tileset from tools/levels/campaign.py.

python -m tools.build_assets --force
Without --force, asks before overwriting maps edited in Tiled.
"""

import argparse
from pathlib import Path

import pygame

from core import settings
from rendering.sprite_library import build_placeholder_sheet
from rendering.sprite_specs import ALL_SHEETS
from tools.level_format import (
    TILESET_FILE, TILESET_IMAGE, build_level, write_tileset_image, write_tileset_tsx, write_xml,
)
from tools.levels.campaign import LEVELS


def export_sprite_templates(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for spec in ALL_SHEETS:
        pygame.image.save(build_placeholder_sheet(spec), directory / spec.image_path)
    print(f"Sprite templates written to {directory}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="overwrite existing .tmx files without asking")
    parser.add_argument("--export-sprites", action="store_true", help="also export sprite sheet templates")
    args = parser.parse_args()
    maps = settings.MAPS_DIR
    images = settings.ASSETS_DIR / "images"
    existing = [level.file_name for level in LEVELS if (maps / level.file_name).exists()]
    if existing and not args.force:
        answer = input(f"Overwrite {', '.join(existing)}? Edits made in Tiled will be lost [y/N] ")
        if answer.strip().lower() != "y":
            print("Aborted.")
            return 1
    maps.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)
    write_tileset_image(images / TILESET_IMAGE)
    write_tileset_tsx(maps / TILESET_FILE, f"../images/{TILESET_IMAGE}")
    for level in LEVELS:
        write_xml(build_level(level), maps / level.file_name)
        print(f"Wrote {maps / level.file_name}")
    if args.export_sprites:
        export_sprite_templates(images / "templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
