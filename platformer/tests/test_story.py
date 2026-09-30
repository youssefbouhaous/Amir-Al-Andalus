"""Story content, real-map flow, save compatibility and frozen-world guarantees."""

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
from core.events import EventType, GameEvent
from core.input import Action, InputState
from core.save import SaveManager, _from_dict
from core.session import GameSession
from core.story import ARRIVALS, DEPARTURES, MANUSCRIPTS, manuscript_line, should_play
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.level_intro_scene import LevelIntroScene
from scenes.scene import Scene
from scenes.scene_manager import SceneManager
from scenes.story_scene import StoryScene, with_story
from scenes.tally_scene import TallyScene
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader


class Destination(Scene):
    def __init__(self, context):
        super().__init__(context)
        self.entered = 0

    def on_enter(self):
        self.entered += 1

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class StoryTests(unittest.TestCase):
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
        directory = tempfile.TemporaryDirectory(prefix="story-tests-")
        self.addCleanup(directory.cleanup)
        self.save = SaveManager(Path(directory.name))
        self.context = GameContext(assets=self.assets, sprites=self.sprites, levels=self.levels,
            audio=Mock(), input=InputState(), scenes=SceneManager(), save=self.save, debug=DebugOverlay())
        self.session = GameSession("level1.tmx")
        self.destination = Destination(self.context)

    def open_story(self, sequence=None, following=None):
        story = StoryScene(self.context, sequence or ARRIVALS["level1.tmx"], following or self.destination)
        self.context.scenes.reset(story)
        return story

    def action(self, action, dt=.01):
        self.context.input._pressed = {action}
        self.context.scenes.update(dt)
        self.context.input.end_step()

    def test_all_fifteen_maps_have_matching_themes_and_page_lore(self):
        for i in range(1, 16):
            file = f"level{i}.tmx"
            level = self.levels.load(file)
            self.assertEqual(ARRIVALS[file].theme, level.theme)
            self.assertEqual(ARRIVALS[file].music, level.music)
            self.assertEqual(len(MANUSCRIPTS[file]), len(level.objects_of("page")))
        self.assertEqual(set(DEPARTURES), {"level6.tmx", "level10.tmx", "level15.tmx"})
        keys = [s.key for s in (*ARRIVALS.values(), *DEPARTURES.values())]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_scene_and_beat_renders_and_text_fits(self):
        for sequence in (*ARRIVALS.values(), *DEPARTURES.values()):
            with self.subTest(sequence=sequence.key):
                story = self.open_story(sequence)
                self.assertLess(story._title_font.size(sequence.title)[0], 880)
                for index, beat in enumerate(sequence.beats):
                    story.index = index
                    story.elapsed = 1.0
                    story.draw(self.screen)
                    self.assertLessEqual(len(story._lines[index]), 3)
                    self.assertTrue(all(story._body_font.size(line)[0] <= 790 for line in story._lines[index]))
                    self.assertGreaterEqual(beat.duration, 5)
                    self.assertFalse(self.save.path.exists())  # drawing must not save/advance

    def test_confirm_advances_one_beat_and_skip_marks_whole_scene(self):
        story = self.open_story()
        self.action(Action.CONFIRM)
        self.assertEqual(story.index, 0)  # input grace
        story.update(.5)
        self.action(Action.CONFIRM)
        self.assertEqual(story.index, 1)
        self.assertFalse(self.save.data.story_seen)
        story.update(.5)
        self.action(Action.BACK)
        self.assertIs(self.context.scenes.top, self.destination)
        self.assertEqual(self.destination.entered, 1)
        self.assertIn(story.sequence.key, SaveManager(self.save.path.parent).data.story_seen)
        story.finish()
        self.assertEqual(self.destination.entered, 1)

    def test_scenes_auto_advance_without_input(self):
        story = self.open_story()
        story.update(story.sequence.beats[0].duration + .01)
        self.assertEqual(story.index, 1)
        story.update(story.sequence.beats[1].duration + .01)
        self.assertIs(self.context.scenes.top, self.destination)

    def test_gamepad_back_and_confirm_use_existing_actions(self):
        story = self.open_story()
        story.update(.5)
        self.action(Action.PAUSE)
        self.assertIs(self.context.scenes.top, self.destination)
        self.assertFalse(self.context.input.was_pressed(Action.PAUSE))

    def test_seen_scene_and_replay_return_destination_without_loading_stage(self):
        sequence = ARRIVALS["level1.tmx"]
        self.session.replay = True
        with patch("scenes.story_scene.StoryStage", side_effect=AssertionError("stage loaded on replay")):
            self.assertIs(with_story(self.context, self.session, sequence, self.destination), self.destination)
        self.session.replay = False
        self.save.data.story_seen.add(sequence.key)
        self.assertIs(with_story(self.context, self.session, sequence, self.destination), self.destination)
        self.assertIs(with_story(self.context, self.session, None, self.destination), self.destination)

    def test_legacy_and_malformed_story_save_fields_do_not_destroy_progress(self):
        for value in (None, "arrival:level1", {}, [None, 4, "arrival:level1"]):
            raw = {"levels": {"level4.tmx": {"completed": True, "best_score": 900}}, "story_seen": value}
            data = _from_dict(raw)
            self.assertTrue(data.is_completed("level4.tmx"))
            self.assertEqual(data.levels["level4.tmx"].best_score, 900)
            self.assertEqual(data.story_seen, {"arrival:level1"} if isinstance(value, list) else set())
        self.assertEqual(_from_dict({}).story_seen, set())

    def test_new_journey_resets_story_but_keeps_options(self):
        self.save.data.story_seen.add("arrival:level1")
        self.save.data.options.music_volume = .17
        self.save.save()
        self.save.reset_progress()
        restored = SaveManager(self.save.path.parent).data
        self.assertFalse(restored.story_seen)
        self.assertEqual(restored.options.music_volume, .17)

    def test_cistern_and_level_clock_do_not_run_during_story(self):
        session = GameSession("level13.tmx", score=500, lives=3, level_time=17)
        game = GameScene(self.context, session, self.levels.load(session.level_file))
        world = game.world
        original = (world.player.body.midbottom, world.time, session.score, session.lives,
                    session.level_time, tuple((type(p).__name__, tuple(p.rect)) for p in world.props))
        story = self.open_story(ARRIVALS[session.level_file], game)
        for _ in range(1200):
            story.update(1 / 120)
        after = (world.player.body.midbottom, world.time, session.score, session.lives,
                 session.level_time, tuple((type(p).__name__, tuple(p.rect)) for p in world.props))
        self.assertEqual(original, after)
        self.assertFalse(self.save.data.is_completed(session.level_file))

    def test_checkpoint_retry_does_not_reopen_story(self):
        session = GameSession("level1.tmx")
        intro = LevelIntroScene(self.context, session)
        self.context.scenes.reset(intro)
        intro.on_continue()
        story = self.context.scenes.top
        self.assertIsInstance(story, StoryScene)
        story.finish()
        game = self.context.scenes.top
        game.restart_from_checkpoint()
        self.assertIs(self.context.scenes.top, game)
        self.assertFalse(should_play(ARRIVALS[session.level_file], session, self.save.data))

    def test_departure_happens_after_score_is_saved_and_not_in_replay(self):
        for replay in (False, True):
            with self.subTest(replay=replay):
                session = GameSession("level10.tmx", replay=replay, score=100)
                tally = TallyScene(self.context, session, self.levels.load(session.level_file))
                self.context.scenes.reset(tally)
                self.assertTrue(SaveManager(self.save.path.parent).data.is_completed("level10.tmx"))
                tally.on_continue()
                self.assertEqual(isinstance(self.context.scenes.top, StoryScene), not replay)
                self.assertEqual(session.level_file, "level10.tmx" if replay else "level11.tmx")

    def test_lore_uses_existing_toast_and_does_not_change_score(self):
        session = GameSession("level1.tmx")
        game = GameScene(self.context, session, self.levels.load(session.level_file))
        with patch.object(game._hud, "toast") as toast:
            game._react(GameEvent(EventType.PAGE_COLLECTED, (0, 0), 1))
            toast.assert_called_once_with(MANUSCRIPTS["level1.tmx"][1])
            self.assertEqual(session.score, 0)
            session.replay = True
            game._react(GameEvent(EventType.PAGE_COLLECTED, (0, 0), 2))
            self.assertEqual(toast.call_count, 1)
        self.assertIsNone(manuscript_line("custom.tmx", 0))
        self.assertIsNone(manuscript_line("level1.tmx", -1))
        self.assertIsNone(manuscript_line("level1.tmx", "bad"))
        font = self.assets.get_font(settings.HUD_FONT_SIZE, "ui")
        for lines in MANUSCRIPTS.values():
            for line in lines:
                self.assertLess(font.size(line)[0], 880)


if __name__ == "__main__":
    unittest.main()
