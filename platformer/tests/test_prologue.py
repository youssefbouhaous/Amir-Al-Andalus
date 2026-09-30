"""Opening-film choreography, rendering, input and saved-journey integration."""

import os
import tempfile
import unittest
from copy import deepcopy
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
from core.prologue import (
    AMIR_TRACK, GARDENER_TRACK, DURATION, FLOOR, PROLOGUE_KEY, SHOTS, WORLD_WIDTH,
    actor_at, sample,
)
from core.save import SaveManager
from core.session import GameSession
from rendering import sprite_specs
from rendering.sprite_library import SpriteLibrary
from scenes.level_intro_scene import LevelIntroScene
from scenes.prologue_scene import PrologueScene
from scenes.scene import Scene
from scenes.scene_manager import SceneManager
from scenes.title_scene import TitleScene
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader


class ChoreographyTests(unittest.TestCase):
    def test_shots_and_tracks_cover_whole_film_without_gaps(self):
        for track in (SHOTS, AMIR_TRACK, GARDENER_TRACK):
            self.assertEqual(track[0].start, 0)
            self.assertEqual(track[-1].end, DURATION)
            for left, right in zip(track, track[1:]):
                self.assertEqual(left.end, right.start)
        for track in (AMIR_TRACK, GARDENER_TRACK):
            for left, right in zip(track, track[1:]):
                self.assertEqual(left.x1, right.x0)
                before = actor_at(track, right.start - 1e-6)
                after = actor_at(track, right.start)
                self.assertAlmostEqual(before.x, after.x, places=3)
                self.assertAlmostEqual(before.y, after.y, places=3)

    def test_prince_really_crosses_channel_in_an_arc_and_lands(self):
        launch, apex, land = [sample(t).amir for t in (7.2, 8.1, 9)]
        self.assertLess(launch.x, 448)
        self.assertGreater(apex.x, 448)
        self.assertLess(apex.x, 576)
        self.assertLess(apex.y, FLOOR - 100)
        self.assertTrue(apex.airborne)
        self.assertEqual(apex.pose, "apex")
        self.assertGreater(land.x, 576)
        self.assertEqual(land.y, FLOOR)
        self.assertEqual(land.pose, "land")

    def test_water_map_warning_and_lantern_follow_the_story(self):
        self.assertEqual(sample(10).water, 1)
        self.assertTrue(0 < sample(18).water < 1)
        self.assertEqual(sample(21).water, 0)
        self.assertEqual(sample(21).amir.pose, "kneel")
        self.assertEqual(sample(28).page_handoff, 0)
        self.assertEqual(sample(30).page_handoff, 1)
        self.assertEqual(sample(42).route, 1)
        self.assertEqual(sample(42).map_open, 1)
        self.assertEqual(sample(45).warning, 1)
        self.assertEqual(sample(52).map_open, 0)
        self.assertEqual(sample(59).lantern, 0)
        self.assertEqual(sample(61).lantern, 1)
        self.assertEqual(sample(63).amir.facing, -1)
        self.assertGreater(sample(69).amir.x, 1970)  # through the orchard gate

    def test_camera_keeps_actor_visible_and_never_leaves_stage(self):
        previous = sample(0)
        for step in range(int(DURATION * 60) + 1):
            frame = sample(step / 60)
            self.assertGreaterEqual(frame.camera_x, 0)
            self.assertLessEqual(frame.camera_x, WORLD_WIDTH - 960)
            self.assertTrue(40 < frame.amir.x - frame.camera_x < 920)
            self.assertLess(abs(previous.camera_x - frame.camera_x), 3)
            previous = frame

    def test_seeking_is_deterministic_and_clamped(self):
        expected = sample(61)
        for time in (0, 53, 10, 29, 80, -50):
            sample(time)
        self.assertEqual(sample(61), expected)
        self.assertEqual(sample(-50), sample(0))
        self.assertEqual(sample(1000), sample(DURATION))


class Destination(Scene):
    def __init__(self, context):
        super().__init__(context)
        self.entered = 0
        self.updates = 0

    def on_enter(self):
        self.entered += 1

    def update(self, dt):
        self.updates += 1

    def draw(self, surface):
        pass


class PrologueTests(unittest.TestCase):
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
        directory = tempfile.TemporaryDirectory(prefix="prologue-tests-")
        self.addCleanup(directory.cleanup)
        self.save = SaveManager(Path(directory.name))
        self.context = GameContext(assets=self.assets, sprites=self.sprites, levels=self.levels,
            audio=Mock(), input=InputState(), scenes=SceneManager(), save=self.save, debug=DebugOverlay())
        self.destination = Destination(self.context)

    def open_film(self, following=None):
        film = PrologueScene(self.context, following or self.destination)
        self.context.scenes.reset(film)
        return film

    def action(self, action, dt=.01):
        self.context.input._pressed = {action}
        self.context.scenes.update(dt)
        self.context.input.end_step()

    def test_full_film_completes_once_without_updating_destination(self):
        film = self.open_film()
        self.context.audio.play_music.assert_called_once_with("story")
        for _ in range(int(DURATION * 60) + 1):
            film.update(1 / 60)
        self.assertIs(self.context.scenes.top, self.destination)
        self.assertEqual(self.destination.updates, 0)
        self.assertEqual(self.destination.entered, 1)
        film.finish()
        self.assertEqual(self.destination.entered, 1)
        stored = SaveManager(self.save.path.parent).data.story_seen
        self.assertTrue({PROLOGUE_KEY, "arrival:level1"} <= stored)

    def test_input_grace_next_moment_and_escape_skip(self):
        film = self.open_film()
        self.action(Action.CONFIRM)
        self.assertLess(film.elapsed, .1)
        film.update(.5)
        self.action(Action.CONFIRM)
        self.assertEqual(film.elapsed, SHOTS[1].start)
        self.assertFalse(self.save.data.story_seen)
        self.action(Action.CONFIRM)
        self.assertLess(film.elapsed, SHOTS[1].start + .1)
        film.update(.5)
        self.action(Action.BACK)
        self.assertIs(self.context.scenes.top, self.destination)
        self.assertFalse(self.context.input.was_pressed(Action.BACK))

    def test_gamepad_pause_skip_and_confirm_last_moment(self):
        film = self.open_film()
        film.update(.5)
        self.action(Action.PAUSE)
        self.assertIs(self.context.scenes.top, self.destination)
        film = self.open_film()
        film.elapsed = SHOTS[-1].start
        film.update(.5)
        self.action(Action.CONFIRM)
        self.assertIs(self.context.scenes.top, self.destination)

    def test_seeking_does_not_play_missed_sound_effects(self):
        film = self.open_film()
        film.elapsed = 7.19
        film.update(.02)
        self.context.audio.play.assert_called_once_with("jump", .55)
        self.context.audio.play.reset_mock()
        film.next_shot()
        film.update(.01)
        self.context.audio.play.assert_not_called()
        film.update(40)
        self.context.audio.play.assert_not_called()

    def test_all_captions_fit_and_rendering_uses_cached_actor_art(self):
        film = self.open_film()
        for lines in film._captions:
            self.assertLessEqual(len(lines), 3)
            self.assertTrue(all(film._font.size(line)[0] <= 838 for line in lines))
        with patch("rendering.art.prince.draw_pose", side_effect=AssertionError("art rebuilt while drawing")):
            for time in (0, 4, 8.1, 18.5, 19.9, 29.4, 39, 46, 50, 56, 60.5, 63, 67, 69.9):
                film.elapsed = time
                film.draw(self.screen)
                self.assertEqual(film.elapsed, time)
        self.assertFalse(self.save.path.exists())
        self.assertFalse(self.save.data.story_seen)
        original = self.sprites.animations(sprite_specs.PLAYER)
        for pose in ("run", "skid", "jump", "apex", "fall"):
            self.assertIs(film._stage.actors["amir"].animations[pose].frames[0], original[pose].frames[0])

    def test_opening_does_not_change_session_stats_or_progress(self):
        session = GameSession("level1.tmx", score=800, lives=4, level_time=31, checkpoint_id=7)
        following = LevelIntroScene(self.context, session)
        before = deepcopy(session)
        film = self.open_film(following)
        film.update(DURATION)
        self.assertIs(self.context.scenes.top, following)
        self.assertEqual(session, before)
        self.assertFalse(self.save.data.levels)

    def test_legacy_continue_shows_film_then_resumes_without_losing_records(self):
        for i in range(1, 5):
            record = self.save.data.record(f"level{i}.tmx")
            record.completed = True
            record.best_score = i * 100
        self.save.data.story_seen.add("arrival:level1")
        self.save.data.options.music_volume = .23
        before = deepcopy(self.save.data)
        title = TitleScene(self.context)
        self.context.scenes.reset(title)
        title._continue_game()
        film = self.context.scenes.top
        self.assertIsInstance(film, PrologueScene)
        self.assertEqual(film.following._session.level_file, "level5.tmx")
        film.finish()
        self.assertIsInstance(self.context.scenes.top, LevelIntroScene)
        self.assertEqual(self.save.data.levels, before.levels)
        self.assertEqual(self.save.data.options, before.options)
        self.context.save = SaveManager(self.save.path.parent)
        title = TitleScene(self.context)
        self.context.scenes.reset(title)
        with patch("scenes.prologue_scene.PrologueStage", side_effect=AssertionError("film loaded twice")):
            title._continue_game()
        self.assertIsInstance(self.context.scenes.top, LevelIntroScene)
        self.assertEqual(self.context.scenes.top._session.level_file, "level5.tmx")

    def test_new_journey_replays_opening_and_keeps_options(self):
        self.save.data.story_seen.update((PROLOGUE_KEY, "arrival:level1"))
        self.save.data.record("level1.tmx").completed = True
        self.save.data.options.music_volume = .19
        title = TitleScene(self.context)
        self.context.scenes.reset(title)
        title._start_new()  # the confirmed New Journey callback
        self.assertIsInstance(self.context.scenes.top, PrologueScene)
        self.assertFalse(self.save.data.story_seen)
        self.assertFalse(self.save.data.levels)
        self.assertEqual(self.save.data.options.music_volume, .19)


if __name__ == "__main__":
    unittest.main()
