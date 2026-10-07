"""Level 4's finale: the Sky-Noria, the River-Thieves and the Rose Fountain.

Run with: python -m unittest tests.test_river_thieves -v
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
from entities.player_controller import PlayerIntent
from jazari.catalog import entry_for
from jazari.levels.l04_fountain import Jet, RoseFountain
from jazari.levels.l04_noria import RiverThieves
from objects.hazards import Spikes
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader

T = 32


class RiverThievesTests(unittest.TestCase):
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
        level = self.levels.load("level4.tmx")
        self.session = GameSession(level_file=level.file_name, level_name=level.name)
        self.game = GameScene(self.context, self.session, level)
        self.context.scenes.reset(self.game)

    # --- helpers -------------------------------------------------------------------------------------
    @property
    def world(self):
        return self.game.world

    @property
    def guardian(self) -> RiverThieves:
        return self.world.wonder.guardian

    def advance(self, seconds, intent=None):
        for _ in range(round(seconds * 120)):
            self.world.player._invulnerable_timer = 1.0
            if intent is not None:
                self.world.player.intent = intent
                self.world.update(1 / 120, self.game._camera.view_rect)
                self.game._process_events()
            else:
                self.context.scenes.update(1 / 120)
            self.context.input.end_step()

    def until(self, condition, limit=20.0):
        waited = 0.0
        while not condition() and waited < limit:
            self.advance(0.05)
            waited += 0.05
        self.assertTrue(condition(), "timed out")

    def enter_stage(self):
        g = self.guardian
        self.world.player.arrive_at((g.left + 6 * T, g.floor))
        self.advance(0.2)

    def current(self):
        g = self.guardian
        return g.cast[g.act]

    def fighting(self):
        g = self.guardian
        return g.stage == "act" and self.current().state == "fight"

    def grant_power(self) -> RoseFountain:
        power = RoseFountain(self.world.wonder)
        self.world.wonder.power = power
        return power

    def strike(self, thief, times=1):
        for _ in range(times):
            thief.grace = 0.0
            thief.hit(self.world, 1)

    # --- tests --------------------------------------------------------------------------------------------
    def test_registered_with_its_power_and_the_exit_bolted(self):
        entry = entry_for("level4.tmx")
        self.assertIs(entry.guardian, RiverThieves)
        self.assertIs(entry.power, RoseFountain)
        self.assertEqual(self.world.goals, [])
        g = self.guardian
        self.assertFalse(any(isinstance(p, Spikes) and g.arena.colliderect(p.rect) for p in self.world.props),
                         "the old spikes over the last run are washed off the stage")

    def test_the_noria_wakes_floods_the_stage_and_roots_its_thief(self):
        self.enter_stage()
        g = self.guardian
        self.assertTrue(g.awake)
        self.until(self.fighting)
        self.assertEqual(self.current().kind, "yusuf")
        self.advance(0.6)
        self.assertGreater(g.flood.coverage(), 0.9)
        self.assertTrue(self.current().warded, "standing in the stolen river, the noria lends him its strength")
        self.assertIsNotNone(self.world.wonder.camera_focus)
        self.assertNotEqual(self.world.wonder.ambient(None), None, "the river in the sky drowns the dawn")
        self.game.draw(self.screen)

    def test_a_rooted_thief_shrugs_off_blows(self):
        self.enter_stage()
        self.until(self.fighting)
        self.advance(0.6)
        yusuf = self.current()
        hp = yusuf.hp
        self.strike(yusuf)
        self.assertEqual(yusuf.hp, hp, "the water drinks the blow")

    def test_when_the_ox_drinks_the_flood_ebbs_and_the_thief_is_only_a_man(self):
        self.enter_stage()
        self.until(self.fighting)
        g = self.guardian
        self.until(lambda: g.ebb == "dry", 12.0)
        self.assertEqual(g.machine.ox_state, "drink")
        self.until(lambda: g.flood.coverage() < 0.05, 2.0)
        yusuf = self.current()
        self.advance(0.2)
        self.assertFalse(yusuf.warded)
        hp = yusuf.hp
        self.strike(yusuf)
        self.assertEqual(yusuf.hp, hp - 1)
        # The ox bellows and the river comes back as a wave from the foot of the wheel.
        self.until(lambda: g.ebb == "" and g.flood.waves, 5.0)
        self.until(lambda: yusuf.state == "fight" and yusuf.warded, 4.0)
        self.game.draw(self.screen)

    def test_the_rose_fountain_lifts_a_thief_out_of_the_water(self):
        power = self.grant_power()
        self.enter_stage()
        self.until(self.fighting)
        self.advance(0.6)
        yusuf = self.current()
        yusuf.jet_timer = yusuf.cup_timer = yusuf.hop_timer = 99
        player = self.world.player
        player.arrive_at((yusuf.body.centerx - 4 * T, self.guardian.floor))
        player.facing = 1
        self.advance(0.05)
        self.assertTrue(yusuf.warded)
        self.assertTrue(power.use(self.world))
        self.until(lambda: yusuf.lifted, 1.0)
        self.advance(0.4)
        self.assertFalse(yusuf.warded)
        self.assertGreater(self.guardian.floor - yusuf.body.bottom, Jet.HOLD_AT * 0.7, "held up in the column")
        hp = yusuf.hp
        self.strike(yusuf, 2)
        self.assertEqual(yusuf.hp, hp - 2, "the fountain keeps holding him: strike again")
        self.assertTrue(yusuf.lifted)
        self.game.draw(self.screen)
        self.until(lambda: not yusuf.lifted, 3.0)
        self.assertEqual(yusuf.state, "stunned", "dropped dazed into the water")
        self.until(lambda: yusuf.warded, 4.0)

    def test_the_fountain_carries_the_prince_higher_than_a_jump(self):
        power = self.grant_power()
        g = self.guardian
        player = self.world.player
        player.arrive_at((g.left + 2 * T, g.floor))
        self.advance(0.1)
        self.assertTrue(power.use(self.world))
        best = 0.0
        for _ in range(12):
            self.advance(0.1, PlayerIntent())
            best = max(best, g.floor - player.body.bottom)
        self.assertGreater(best, 140, "a normal jump peaks near 123 px")

    def test_a_vaulting_fisher_leaves_the_river(self):
        self.enter_stage()
        self.until(self.fighting)
        self.strike_down(self.current())
        self.until(lambda: self.guardian.act == 1 and self.fighting(), 10.0)
        nur = self.current()
        self.assertEqual(nur.kind, "nur")
        self.advance(0.6)
        self.assertTrue(nur.warded)
        self.world.player.arrive_at((nur.body.centerx - 1.5 * T, self.guardian.floor))
        nur.net_timer = nur.fish_timer = 99
        nur.vault_timer = 0
        self.until(lambda: nur.plan == "vault", 3.0)
        self.advance(0.3)
        self.assertFalse(nur.warded, "in the air, out of the water, she is only herself")

    def strike_down(self, thief):
        while thief.state != "defeated":
            thief.roots = 0.0
            self.strike(thief)

    def test_the_whole_band_beaten_brings_the_river_home(self):
        self.enter_stage()
        g = self.guardian
        for act in range(3):
            self.until(lambda: g.act == act and self.fighting())
            thief = self.current()
            self.strike_down(thief)
            self.until(lambda: thief.gone)
            self.assertEqual(self.world.wonder.progress, act + 1)
        self.until(lambda: g.resolved, 8.0)
        self.advance(0.3)
        self.assertEqual(len(self.world.goals), 1)
        self.assertTrue(g.machine.freed)
        self.assertIn("level4.tmx", self.session.wonders_resolved)
        self.until(lambda: g.machine.river < 0.2, 6.0)
        self.game.draw(self.screen)

    def test_progress_survives_a_retry(self):
        self.enter_stage()
        self.until(self.fighting)
        self.strike_down(self.current())
        self.until(lambda: self.guardian.act == 1)
        self.game.restart_from_checkpoint()
        self.assertEqual(self.guardian.act, 1)
        self.assertTrue(self.guardian.cast[0].gone)
        self.assertEqual(self.world.goals, [])


if __name__ == "__main__":
    unittest.main()
