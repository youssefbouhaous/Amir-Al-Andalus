"""Level 1's finale: the Moon-Clock Fountain, the Moon Troupe and the Brass Nightingale.

Run with: python -m unittest tests.test_moon_troupe -v
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
from entities.troupe import SHIELD_HITS
from jazari.levels.l01_nightingale import BrassNightingale, Song
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader

T = 32


class MoonTroupeTests(unittest.TestCase):
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
        level = self.levels.load("level1.tmx")
        self.session = GameSession(level_file=level.file_name, level_name=level.name)
        self.game = GameScene(self.context, self.session, level)
        self.context.scenes.reset(self.game)

    # --- helpers -------------------------------------------------------------------------------------
    @property
    def world(self):
        return self.game.world

    @property
    def troupe(self):
        return self.world.wonder.guardian

    def advance(self, seconds, safe=True):
        for _ in range(round(seconds * 120)):
            if safe:
                self.world.player._invulnerable_timer = 1.0
            self.context.scenes.update(1 / 120)
            self.context.input.end_step()

    def enter_stage(self):
        troupe = self.troupe
        self.world.player.arrive_at((troupe.left + 6 * T, troupe.floor))
        self.advance(0.2)

    def until(self, condition, limit=20.0):
        waited = 0.0
        while not condition() and waited < limit:
            self.advance(0.05)
            waited += 0.05
        self.assertTrue(condition(), "timed out")

    def current(self):
        troupe = self.troupe
        return troupe.cast[troupe.act]

    # --- tests ------------------------------------------------------------------------------------------
    def test_exit_is_bolted_until_the_troupe_is_beaten(self):
        self.assertEqual(self.world.goals, [])
        self.assertEqual(self.troupe.stage, "sleep")
        self.enter_stage()
        self.assertTrue(self.troupe.awake)
        self.assertGreater(self.troupe.dusk_target, 0.5)
        self.until(lambda: self.troupe.stage == "act")
        self.assertEqual(self.current().kind, "juggler")
        self.assertIsNotNone(self.world.wonder.camera_focus)
        self.game.draw(self.screen)

    def test_song_bursts_bubble_snaps_string_and_stuns(self):
        self.world.wonder.power = BrassNightingale(self.world.wonder)
        self.enter_stage()
        self.until(lambda: self.troupe.stage == "act" and self.current().state == "fight")
        rashid = self.current()
        self.until(lambda: self.troupe.tethers and self.troupe.tethers[0].attached)
        self.assertEqual(rashid.shield, SHIELD_HITS)
        song = Song(rashid.body.centerx - 40, rashid.body.centery)
        song.radius = 400
        self.troupe.on_power("song", song, self.world)
        self.assertEqual(rashid.shield, 0)
        self.assertEqual(rashid.state, "stunned")
        self.assertFalse(self.troupe.tethers[0].attached)
        self.assertEqual(self.troupe.peck_target((rashid.body.centerx, rashid.body.top)), rashid)

    def test_nightingale_sings_on_power_key_and_pecks(self):
        power = BrassNightingale(self.world.wonder)
        self.world.wonder.power = power
        self.enter_stage()
        self.until(lambda: self.troupe.stage == "act" and self.current().state == "fight")
        rashid = self.current()
        self.world.player.arrive_at((rashid.body.centerx - 90, self.troupe.floor))
        self.advance(0.05)
        self.assertTrue(power.use(self.world))
        self.until(lambda: rashid.state == "stunned", 2.0)
        hp = rashid.hp
        self.until(lambda: rashid.hp < hp, 3.0)
        self.game.draw(self.screen)

    def test_string_cut_by_blade_stops_the_bubble_healing(self):
        self.enter_stage()
        self.until(lambda: self.troupe.stage == "act" and self.current().state == "fight")
        self.until(lambda: self.troupe.tethers and self.troupe.tethers[0].attached)
        tether = self.troupe.tethers[0]
        clock = self.troupe.clock
        tether.snap(self.world, clock.moon, clock.radius, 0.5, 4.0)
        rashid = self.current()
        rashid.pop(self.world)
        self.advance(3.5)
        self.assertEqual(rashid.shield, 0, "the bubble must not heal while its string is cut")

    def test_whole_troupe_beaten_opens_exit_and_returns_the_water(self):
        self.enter_stage()
        for act in range(3):
            self.until(lambda: self.troupe.act == act and self.troupe.stage == "act" and self.current().targetable)
            performer = self.current()
            for _ in range(performer.max_hp + SHIELD_HITS):
                performer.grace = 0.0
                performer.hit(self.world, 1)
                if performer.state == "defeated":
                    break
            self.assertEqual(performer.state, "defeated")
            self.until(lambda: performer.gone)
            self.assertEqual(self.world.wonder.progress, act + 1)
        self.until(lambda: self.troupe.resolved, 6.0)
        self.advance(0.2)
        self.assertEqual(len(self.world.goals), 1)
        self.assertTrue(self.troupe.clock.fallen)
        self.assertIn("level1.tmx", self.session.wonders_resolved)
        self.game.draw(self.screen)

    def test_progress_survives_a_retry(self):
        self.enter_stage()
        self.until(lambda: self.troupe.stage == "act" and self.current().targetable)
        rashid = self.current()
        while rashid.state != "defeated":
            rashid.grace = 0.0
            rashid.hit(self.world, 1)
        self.until(lambda: self.troupe.act == 1)
        self.game.restart_from_checkpoint()
        self.assertEqual(self.troupe.act, 1)
        self.assertTrue(self.troupe.cast[0].gone)
        self.assertEqual(self.world.goals, [])


if __name__ == "__main__":
    unittest.main()
