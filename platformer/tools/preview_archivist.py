"""Rehearse level 3's finale without touching the real save or other levels.

    uv run --active python -m tools.preview_archivist
    uv run --active python -m tools.preview_archivist --without-power

The regular title, level-select and campaign entry paths are unchanged.
"""

import argparse
import os
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--without-power", action="store_true", help="Rehearse the skilled manual route")
    args = parser.parse_args()
    # Set the data path before importing settings: preview never reads or writes
    # the real save. Music uses the game's normal reusable cache.
    with tempfile.TemporaryDirectory(prefix="amir-library-rehearsal-") as directory:
        os.environ["XDG_DATA_HOME"] = directory
        import pygame
        from core.game import Game
        from core.session import GameSession
        from scenes.game_scene import GameScene

        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        try:
            game = Game()
            context = game._context
            for number in (1, 2):
                context.save.data.record(f"level{number}.tmx").completed = True
            session = GameSession("level3.tmx", replay=True)
            if not args.without_power:
                session.pages_found = {0, 1, 2}
            scene = GameScene(context, session, context.levels.load(session.level_file))
            context.scenes.reset(scene)
            guardian = scene.world.wonder.guardian
            scene.world.player.arrive_at((guardian.x - 170, guardian.floor))
            scene._camera.snap_to((guardian.x - 85, guardian.floor - 210))
            game.run()
        finally:
            pygame.quit()


if __name__ == "__main__":
    main()
