"""Exercise scene transitions with the real maps and temporary save files.

Run with: uv run --active python -m unittest discover -s tests -v
"""

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from audio.audio_manager import AudioManager
from core import settings
from core.assets import AssetManager
from core.context import GameContext
from core.input import InputState
from core.save import SaveManager
from core.session import GameSession
from entities.player import PlayerState
from rendering.sprite_library import SpriteLibrary
from scenes.end_scenes import GameOverScene, VictoryScene
from scenes.game_scene import GameScene
from scenes.level_intro_scene import LevelIntroScene
from scenes.menu_scene import MenuScene
from scenes.pause_scene import PauseScene
from scenes.scene_manager import SceneManager
from scenes.tally_scene import TallyScene
from scenes.title_scene import TitleScene
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader


class SceneFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        # Exercise the supported no-sound mode; startup with real audio is
        # checked separately so tests don't launch background music workers.
        pygame.mixer.quit()
        cls.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.levels = LevelLoader(settings.MAPS_DIR)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="platformer-tests-")
        self.addCleanup(directory.cleanup)
        self.save = SaveManager(Path(directory.name))
        self.context = GameContext(
            assets=self.assets, audio=AudioManager(self.assets), input=InputState(),
            sprites=self.sprites, levels=self.levels, debug=DebugOverlay(),
            scenes=SceneManager(), save=self.save,
        )

    def advance(self, seconds):
        for _ in range(round(seconds * 120)):
            self.context.scenes.update(1 / 120)
            self.context.input.end_step()

    def press(self, key):
        self.context.input.begin_frame([pygame.event.Event(pygame.KEYDOWN, key=key)])
        self.context.scenes.update(1 / 120)
        self.context.input.begin_frame([pygame.event.Event(pygame.KEYUP, key=key)])

    def test_title_starts_real_game_with_keyboard(self):
        self.context.scenes.push(TitleScene(self.context))
        self.context.scenes.draw(self.screen)
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, LevelIntroScene)
        self.advance(settings.LEVEL_INTRO_DURATION + 0.1)
        self.assertIsInstance(self.context.scenes.top, GameScene)
        self.context.scenes.draw(self.screen)
        self.assertTrue(self.save.data.seen_intro)

    def test_each_goal_reaches_tally_and_next_level_or_victory(self):
        session = GameSession(settings.FIRST_LEVEL)
        for number in range(1, 7):
            with self.subTest(level=number):
                level = self.levels.load(f"level{number}.tmx")
                session.enter_level(level.file_name)
                game = GameScene(self.context, session, level)
                self.context.scenes.reset(game)
                self.advance(0.7)
                self.context.scenes.draw(self.screen)
                goal = game.world.goals[0]
                game.world.player.arrive_at(goal.rect.midbottom)
                self.advance(0.1)
                self.assertEqual(game.world.player.state, PlayerState.VICTORY)
                self.advance(settings.PLAYER_PHYSICS.victory_duration + settings.TRANSITION_DURATION + 0.2)
                self.assertIsInstance(self.context.scenes.top, TallyScene)
                self.context.scenes.draw(self.screen)
                self.assertTrue(self.save.data.is_completed(level.file_name))
                self.advance(0.5)
                self.press(pygame.K_RETURN)
                expected = LevelIntroScene if level.next_level else VictoryScene
                self.assertIsInstance(self.context.scenes.top, expected)
        self.assertTrue(self.save.data.game_completed)
        self.assertTrue(SaveManager(self.save.path.parent).data.game_completed)

    def test_tally_bonus_is_applied_once_and_records_survive_restart(self):
        level = replace(self.levels.load("level1.tmx"), properties={"par_time": 100})
        session = GameSession(level.file_name, score=1000, level_time=60, pages_found={0, 2})
        tally = TallyScene(self.context, session, level)
        self.context.scenes.push(tally)
        tally.on_enter()
        self.assertEqual(session.score, 1000 + 40 * settings.TIME_BONUS_PER_SECOND)
        stored = SaveManager(self.save.path.parent).data.record(level.file_name)
        self.assertEqual(stored.best_time, 60)
        self.assertEqual(stored.pages, [0, 2])
        self.assertEqual(stored.best_score, session.score)
        # A later, slower run adds pages without losing the previous best.
        self.context.scenes.replace(TallyScene(
            self.context, GameSession(level.file_name, level_time=110, pages_found={1}), level
        ))
        stored = SaveManager(self.save.path.parent).data.record(level.file_name)
        self.assertEqual(stored.best_time, 60)
        self.assertEqual(stored.pages, [0, 1, 2])
        self.assertEqual(stored.best_score, session.score)

    def test_continue_resumes_first_unfinished_level(self):
        for number in (1, 2):
            self.save.data.record(f"level{number}.tmx").completed = True
        self.save.save()
        self.context.save = SaveManager(self.save.path.parent)
        self.context.scenes.push(TitleScene(self.context))
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, LevelIntroScene)
        self.advance(settings.LEVEL_INTRO_DURATION + 0.1)
        self.assertEqual(self.context.scenes.top.session.level_file, "level3.tmx")

    def test_new_journey_requires_confirmation_and_keeps_options(self):
        self.save.data.record("level1.tmx").completed = True
        self.save.data.options.music_volume = 0.2
        title = TitleScene(self.context)
        self.context.scenes.push(title)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.context.scenes.draw(self.screen)
        self.assertTrue(title._confirming_new)
        self.press(pygame.K_ESCAPE)
        self.assertTrue(self.save.data.is_completed("level1.tmx"))
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, LevelIntroScene)
        self.assertFalse(self.save.data.is_completed("level1.tmx"))
        self.assertEqual(self.save.data.options.music_volume, 0.2)

    def test_pause_and_game_over_return_to_working_title(self):
        self.assertIs(MenuScene, TitleScene)
        game = GameScene(self.context, GameSession(settings.FIRST_LEVEL), self.levels.load(settings.FIRST_LEVEL))
        self.context.scenes.push(game)
        self.advance(0.7)
        self.press(pygame.K_ESCAPE)
        self.assertIsInstance(self.context.scenes.top, PauseScene)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, TitleScene)
        self.context.scenes.reset(GameOverScene(self.context, game.session))
        self.advance(0.5)
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, TitleScene)

    def test_missing_level_returns_to_title_with_message(self):
        self.context.scenes.push(LevelIntroScene(self.context, GameSession("missing.tmx")))
        self.advance(1 / 120)
        self.assertIsInstance(self.context.scenes.top, TitleScene)
        self.assertIn("missing.tmx", self.context.scenes.top._message)
        self.context.scenes.draw(self.screen)


if __name__ == "__main__":
    unittest.main()
