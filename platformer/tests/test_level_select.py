"""Unlocking, replay records and keyboard/mouse navigation on real maps."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from core.context import GameContext
from core.input import Action, InputState
from core.save import SaveManager
from core.session import GameSession
from rendering.sprite_library import SpriteLibrary
from scenes.level_intro_scene import LevelIntroScene
from scenes.end_scenes import GameOverScene
from scenes.game_scene import GameScene
from scenes.pause_scene import PauseScene
from scenes.level_select_scene import LevelSelectScene, format_time
from scenes.scene_manager import SceneManager
from scenes.tally_scene import TallyScene
from scenes.title_scene import TitleScene
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoadError, LevelLoader


class LevelSelectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        cls.screen = pygame.display.set_mode((960, 540))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.levels = LevelLoader(settings.MAPS_DIR)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="level-select-tests-")
        self.addCleanup(directory.cleanup)
        self.save = SaveManager(Path(directory.name))
        self.context = GameContext(
            assets=self.assets, audio=Mock(), input=InputState(), sprites=self.sprites,
            levels=self.levels, debug=DebugOverlay(), scenes=SceneManager(), save=self.save,
        )

    def open_select(self, selected=None):
        scene = LevelSelectScene(self.context, selected)
        self.context.scenes.reset(scene)
        return scene

    def press(self, key):
        self.context.input.begin_frame([pygame.event.Event(pygame.KEYDOWN, key=key)])
        self.context.scenes.update(1 / 120)
        self.context.input.begin_frame([pygame.event.Event(pygame.KEYUP, key=key)])

    def test_title_opens_selection_with_keyboard(self):
        self.context.scenes.push(TitleScene(self.context))
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertIsInstance(self.context.scenes.top, LevelSelectScene)

    def test_new_save_only_unlocks_first_level_and_browsing_does_not_save(self):
        scene = self.open_select()
        self.assertEqual(len(scene.entries), 15)
        self.assertEqual([e.unlocked for e in scene.entries], [True] + [False] * 14)
        self.context.scenes.draw(self.screen)
        self.assertEqual(self.save.data.levels, {})
        self.assertFalse(self.save.path.exists())

    def test_completion_unlocks_next_level_across_book_boundary(self):
        for number in range(1, 11):
            self.save.data.record(f"level{number}.tmx").completed = True
        scene = self.open_select()
        self.assertEqual(scene.entries[scene.selected].level.file_name, "level11.tmx")
        self.assertTrue(scene.entries[10].unlocked)
        self.assertFalse(scene.entries[11].unlocked)

    def test_locked_level_cannot_start_by_keyboard_or_mouse(self):
        scene = self.open_select()
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.context.scenes.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=scene._play.center
        ))
        self.assertIs(self.context.scenes.top, scene)
        self.assertFalse(self.save.path.exists())

    def test_page_navigation_and_gamepad_actions(self):
        scene = self.open_select()
        self.press(pygame.K_RIGHT)
        self.assertEqual(scene.selected, 6)
        self.press(pygame.K_RIGHT)
        self.assertEqual(scene.selected, 12)
        for _ in range(8):
            self.press(pygame.K_DOWN)
        self.assertEqual(scene.selected, 14)
        self.context.scenes.draw(self.screen)
        # Gamepad buttons/D-pad feed these same abstract actions.
        self.context.input._pressed = {Action.LEFT}
        scene.update(1 / 120)
        self.context.input.end_step()
        self.assertEqual(scene.page, 1)
        self.press(pygame.K_ESCAPE)
        self.assertIsInstance(self.context.scenes.top, TitleScene)

    def test_mouse_selects_then_starts_a_fresh_run_without_resetting_save(self):
        self.save.data.record("level1.tmx").completed = True
        self.save.data.record("level1.tmx").pages = [0, 2]
        self.save.data.game_completed = True
        self.save.data.options.music_volume = 0.2
        scene = self.open_select()
        first = next(scene._rows())[1]
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=first.center))
        scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=scene._play.center))
        intro = self.context.scenes.top
        self.assertIsInstance(intro, LevelIntroScene)
        self.assertEqual(intro._session.level_file, "level1.tmx")
        self.assertTrue(intro._session.replay)
        self.assertEqual(intro._session.score, 0)
        self.assertEqual(intro._session.lives, settings.STARTING_LIVES)
        stored = SaveManager(self.save.path.parent).data
        self.assertTrue(stored.game_completed)
        self.assertEqual(stored.record("level1.tmx").pages, [0, 2])
        self.assertEqual(stored.options.music_volume, 0.2)

    def test_replay_records_merge_and_tally_returns_to_same_level(self):
        record = self.save.data.record("level1.tmx")
        record.completed = True
        record.best_score = 90000  # historical journey score is preserved
        record.best_time = 30.0
        record.pages = [0]
        record.best_replay_score = 100
        level = self.levels.load("level1.tmx")
        tally = TallyScene(self.context, GameSession(
            "level1.tmx", score=200, level_time=40.0, pages_found={1}, replay=True
        ), level)
        self.context.scenes.push(tally)
        total = 200 + tally.time_bonus
        tally.on_enter()
        stored = SaveManager(self.save.path.parent).data.record("level1.tmx")
        self.assertEqual(stored.best_replay_score, total)
        self.assertEqual(stored.best_score, 90000)
        self.assertEqual(stored.best_time, 30.0)
        self.assertEqual(stored.pages, [0, 1])
        tally.on_continue()
        scene = self.context.scenes.top
        self.assertIsInstance(scene, LevelSelectScene)
        self.assertEqual(scene.selected, 0)
        self.assertIn(f"Beat your replay score: {total:,}", scene.entries[0].goals())

    def test_slower_lower_replay_preserves_bests_and_adds_pages(self):
        record = self.save.data.record("level1.tmx")
        record.best_replay_score = 90000
        record.best_time = 20
        record.pages = [0, 1]
        tally = TallyScene(self.context, GameSession(
            "level1.tmx", score=10, level_time=999, pages_found={2}, replay=True
        ), self.levels.load("level1.tmx"))
        tally.on_enter()
        self.assertEqual(record.best_replay_score, 90000)
        self.assertEqual(record.best_time, 20)
        self.assertEqual(record.pages, [0, 1, 2])

    def test_replay_score_does_not_replace_journey_score(self):
        record = self.save.data.record("level1.tmx")
        record.best_score = 50
        tally = TallyScene(self.context, GameSession(
            "level1.tmx", score=1000, level_time=999, replay=True
        ), self.levels.load("level1.tmx"))
        tally.on_enter()
        self.assertEqual(record.best_score, 50)
        self.assertEqual(record.best_replay_score, 1000)

    def test_replay_completes_final_level_without_relocking_campaign(self):
        for number in range(1, 16):
            self.save.data.record(f"level{number}.tmx").completed = True
        self.save.data.game_completed = True
        scene = self.open_select("level15.tmx")
        self.assertTrue(all(entry.unlocked for entry in scene.entries))
        scene._start_selected()
        intro = self.context.scenes.top
        tally = TallyScene(self.context, intro._session, self.levels.load("level15.tmx"))
        self.context.scenes.replace(tally)
        tally.on_continue()
        self.assertIsInstance(self.context.scenes.top, LevelSelectScene)
        self.assertEqual(self.context.scenes.top.selected, 14)
        self.assertTrue(SaveManager(self.save.path.parent).data.game_completed)

    def test_replay_game_over_and_pause_return_to_selection(self):
        self.save.data.record("level1.tmx").completed = True
        session = GameSession("level1.tmx", replay=True)
        over = GameOverScene(self.context, session)
        self.context.scenes.push(over)
        over.on_continue()
        self.assertIsInstance(self.context.scenes.top, LevelSelectScene)
        game = GameScene(self.context, session, self.levels.load("level1.tmx"))
        self.context.scenes.reset(game)
        pause = PauseScene(self.context, game)
        self.context.scenes.push(pause)
        pause._main_menu()
        self.assertIsInstance(self.context.scenes.top, LevelSelectScene)
        self.assertTrue(self.save.data.is_completed("level1.tmx"))

    def test_missing_map_or_cycle_remains_navigable(self):
        with patch.object(self.context.levels, "load", side_effect=LevelLoadError("Missing map")):
            scene = self.open_select()
            self.context.scenes.draw(self.screen)
            self.press(pygame.K_RETURN)
            self.assertIs(self.context.scenes.top, scene)
            self.press(pygame.K_ESCAPE)
            self.assertIsInstance(self.context.scenes.top, TitleScene)
        with patch("scenes.level_select_scene.next_level", return_value="level1.tmx"):
            scene = self.open_select()
            self.assertEqual(len(scene.entries), 1)
            self.assertIn("circular", scene._error)

    def test_old_save_records_do_not_require_replay_score(self):
        from core.save import _from_dict

        old = _from_dict({"levels": {"level1.tmx": {"completed": True, "best_score": 500}}})
        self.assertIsNone(old.record("level1.tmx").best_replay_score)
        self.assertEqual(old.record("level1.tmx").best_score, 500)

    def test_time_format_handles_rounding_and_missing_records(self):
        self.assertEqual(format_time(None), "--:--")
        self.assertEqual(format_time(59.99), "1:00.0")
        self.assertEqual(format_time(83.2), "1:23.2")


if __name__ == "__main__":
    unittest.main()
