"""Level 2's finale: the Elephant Clock, the Gilded Thieves and the Night Qalam.

Run with: python -m unittest tests.test_gilded_thieves -v
"""

import os
import tempfile
import unittest
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
from jazari.levels.l02_qalam import InkRoad, NightQalam
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader

T = 32


class GildedThievesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
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
        self.context = GameContext(
            assets=self.assets, audio=AudioManager(self.assets), input=InputState(),
            sprites=self.sprites, levels=self.levels, debug=DebugOverlay(),
            scenes=SceneManager(), save=SaveManager(Path(directory.name)),
        )
        level = self.levels.load("level2.tmx")
        self.session = GameSession(level_file=level.file_name, level_name=level.name)
        self.game = GameScene(self.context, self.session, level)
        self.context.scenes.reset(self.game)

    # --- helpers -------------------------------------------------------------------------------------
    @property
    def world(self):
        return self.game.world

    @property
    def thieves(self):
        return self.world.wonder.guardian

    def advance(self, seconds, safe=True):
        for _ in range(round(seconds * 120)):
            if safe:
                self.world.player._invulnerable_timer = 1.0
            self.context.scenes.update(1 / 120)
            self.context.input.end_step()

    def until(self, condition, limit=20.0):
        waited = 0.0
        while not condition() and waited < limit:
            self.advance(0.05)
            waited += 0.05
        self.assertTrue(condition(), "timed out")

    def enter_stage(self):
        g = self.thieves
        self.world.player.arrive_at((g.left + 7 * T, g.floor))
        self.advance(0.2)

    def current(self):
        g = self.thieves
        return g.cast[g.act]

    def fighting(self):
        g = self.thieves
        return g.stage == "act" and self.current().state == "fight"

    # --- tests ------------------------------------------------------------------------------------------
    def test_exit_is_bolted_and_the_sun_is_stolen(self):
        self.assertEqual(self.world.goals, [])
        self.enter_stage()
        self.assertTrue(self.thieves.awake)
        self.until(self.fighting)
        self.assertEqual(self.current().kind, "tariq")
        self.advance(0.6)
        self.assertTrue(self.current().lit, "the stolen sun's beam should find its thief")
        self.assertTrue(self.current().warded)
        self.assertIsNotNone(self.world.wonder.camera_focus)
        self.assertNotEqual(self.world.wonder.ambient(None), None)
        self.game.draw(self.screen)

    def test_gilded_thief_shrugs_off_blows(self):
        self.enter_stage()
        self.until(self.fighting)
        self.advance(0.6)
        tariq = self.current()
        hp = tariq.hp
        tariq.grace = 0.0
        self.assertTrue(tariq.hit(self.world, 1))
        self.assertEqual(tariq.hp, hp, "gold doesn't bleed")

    def test_the_princes_shadow_ungilds_a_thief(self):
        self.enter_stage()
        self.until(self.fighting)
        self.advance(0.6)
        tariq = self.current()
        beam = self.thieves.beams[0]
        sun = self.thieves.clock.sun
        # Stand the prince in the light, halfway down the beam.
        x = sun[0] + (tariq.chest[0] - sun[0]) * 0.8
        y = sun[1] + (tariq.chest[1] - sun[1]) * 0.8
        self.world.player.body.place_midbottom((x, y + 14))
        self.world.player.body.velocity.update(0, 0)
        beam.update(0.0, self.world, sun, [])
        self.assertEqual(beam.blocker, "prince")
        self.assertFalse(tariq.lit)

    def test_ink_blots_a_thief_and_makes_a_road(self):
        power = NightQalam(self.world.wonder)
        self.world.wonder.power = power
        self.enter_stage()
        self.until(self.fighting)
        self.advance(0.6)
        tariq = self.current()
        g = self.thieves
        tariq.body.place_midbottom((g.right - 2 * T, g.floor))
        player = self.world.player
        player.arrive_at((g.right - 6 * T, g.floor))
        player.facing = 1
        self.advance(0.02)
        self.assertTrue(power.use(self.world))
        self.until(lambda: tariq.blot > 0, 2.0)
        self.assertFalse(tariq.warded)
        self.assertEqual(tariq.state, "stunned")
        road = power.roads[0]
        self.assertIsInstance(road, InkRoad)
        self.assertIn(road, self.world.platforms)
        hp = tariq.hp
        tariq.grace = 0.0
        tariq.hit(self.world, 1)
        self.assertEqual(tariq.hp, hp - 1)
        self.until(lambda: not power.roads, 6.0)
        self.assertNotIn(road, self.world.platforms)
        self.game.draw(self.screen)

    def test_whole_gang_beaten_lets_the_sun_set(self):
        self.enter_stage()
        for act in range(3):
            self.until(lambda: self.thieves.act == act and self.fighting())
            thief = self.current()
            thief.blot = 99.0
            for _ in range(thief.max_hp + 2):
                thief.grace = 0.0
                thief.hit(self.world, 1)
                if thief.state == "defeated":
                    break
            self.assertEqual(thief.state, "defeated")
            self.until(lambda: thief.gone)
            self.assertEqual(self.world.wonder.progress, act + 1)
        self.until(lambda: self.thieves.resolved, 8.0)
        self.advance(0.3)
        self.assertEqual(len(self.world.goals), 1)
        self.assertTrue(self.thieves.clock.released)
        self.assertIn("level2.tmx", self.session.wonders_resolved)
        self.game.draw(self.screen)

    def test_progress_survives_a_retry(self):
        self.enter_stage()
        self.until(self.fighting)
        tariq = self.current()
        tariq.blot = 99.0
        while tariq.state != "defeated":
            tariq.grace = 0.0
            tariq.hit(self.world, 1)
        self.until(lambda: self.thieves.act == 1)
        self.game.restart_from_checkpoint()
        self.assertEqual(self.thieves.act, 1)
        self.assertTrue(self.thieves.cast[0].gone)
        self.assertEqual(self.world.goals, [])


if __name__ == "__main__":
    unittest.main()
