"""Level 3's borrowed hours: echoes of the prince, the twelve lamps, midnight and stopped time.

Run with: python -m unittest tests.test_borrowed_hours -v
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from core.context import GameContext
from core.events import EventType
from core.input import InputState
from core.save import SaveManager
from core.session import GameSession
from entities.player_controller import PlayerIntent
from jazari.levels.l03_archivist import CYCLE, LAMPS, SERVICE_START, Echo, Sample
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader


class BorrowedHoursTests(unittest.TestCase):
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
        directory = tempfile.TemporaryDirectory(prefix="borrowed-hours-tests-")
        self.addCleanup(directory.cleanup)
        self.context = GameContext(assets=self.assets, sprites=self.sprites, levels=self.levels, audio=Mock(),
                                   input=InputState(), scenes=SceneManager(),
                                   save=SaveManager(Path(directory.name)), debug=DebugOverlay())
        self.make_game()

    def make_game(self, pages=()):
        self.session = GameSession("level3.tmx", pages_found=set(pages))
        self.game = GameScene(self.context, self.session, self.levels.load("level3.tmx"))
        self.context.scenes.reset(self.game)
        self.world = self.game.world
        self.guardian = self.world.wonder.guardian

    def step(self, seconds, intent=None, hz=60):
        for _ in range(round(seconds * hz)):
            self.world.player.intent = intent or PlayerIntent()
            self.world.player._invulnerable_timer = 0
            self.world.update(1 / hz, self.game._camera.view_rect)
            self.world.events.drain()

    def enter(self, x_offset=-200):
        self.world.player.arrive_at((self.guardian.x + x_offset, self.guardian.floor))
        self.step(2.1)
        self.assertEqual(self.guardian.stage, "work")

    def remember(self, x, facing=1, attacking=False):
        """Make the clock remember the prince at ``x`` exactly one hour ago."""
        g = self.guardian
        image = self.world.player._animator.image()
        sample = Sample(g.cycle - CYCLE, x, g.floor, facing, image, attacking, None)
        g.recorder.clear()
        g.recorder.record(sample)
        return sample

    def plant_echo(self, x, facing=1, attacking=False):
        """An echo standing at ``x`` (as if the prince had stood there an hour ago)."""
        g = self.guardian
        echo = Echo(CYCLE, 0)
        echo.sample = self.remember(x, facing, attacking)
        echo.replayed = g.cycle - CYCLE
        g.echoes.append(echo)
        return echo

    # --- tests ------------------------------------------------------------------------------------------
    def test_an_echo_steps_out_each_hour_and_retraces_the_prince(self):
        self.enter(-230)
        g = self.guardian
        walk = PlayerIntent(move_axis=1)
        self.step(0.6, walk)
        self.step(CYCLE - 0.6 + 0.4)
        echoes = [e for e in g.echoes if e.visible]
        self.assertEqual(len(echoes), 1)
        echo = echoes[0]
        recorded = g.recorder.at(g.cycle - CYCLE)
        self.assertAlmostEqual(echo.sample.x, recorded.x, delta=1)
        self.assertLess(echo.sample.x, self.world.player.body.centerx, "it walks where he walked an hour ago")
        self.game.draw(self.screen)

    def test_an_echo_can_cover_a_missed_window_but_each_jaw_takes_one_stroke(self):
        self.enter()
        g = self.guardian
        g.cycle = SERVICE_START + 0.05
        lap = int(g.cycle / CYCLE)
        g._work_treadle(self.world, lap, 12345)
        self.assertEqual(g.teeth, 1, "a borrowed hour's stroke turns a tooth")
        g._work_treadle(self.world, lap, "prince")
        self.assertEqual(g.teeth, 1, "the jaw takes one stroke per opening")

    def test_echoes_shatter_only_face_to_face_and_give_their_hour_back(self):
        self.enter()
        g = self.guardian
        player = self.world.player
        player.arrive_at((g.x - 220, g.floor))
        g.debt = 4.0
        behind = self.plant_echo(g.x - 200, facing=1)        # faces away from the prince
        player.facing = 1
        player._attack_timer = 0.15
        player._attack_facing = 1
        g._update_echoes(0.0, self.world, True, int(g.cycle / CYCLE))
        self.assertTrue(behind.alive, "from behind, the blade passes through")
        self.remember(behind.sample.x, facing=-1)                # now it turns to face him
        g._update_echoes(0.0, self.world, True, int(g.cycle / CYCLE))
        self.assertFalse(behind.alive, "face to face, the borrowed hour shatters")
        self.assertEqual(g.debt, 2.0)

    def test_a_ghost_passes_through_but_its_blade_borrows_an_hour(self):
        self.enter()
        g = self.guardian
        player = self.world.player
        player.arrive_at((g.x - 220, g.floor))
        ghost = self.plant_echo(player.body.centerx, facing=1)
        g._update_echoes(0.0, self.world, True, int(g.cycle / CYCLE))
        self.assertEqual(g.debt, 0.0)
        g.echoes.remove(ghost)
        self.plant_echo(player.body.centerx - 20, facing=1, attacking=True)
        g._update_echoes(0.0, self.world, True, int(g.cycle / CYCLE))
        self.assertEqual(g.debt, 2.0)
        self.assertTrue(any(e.type == EventType.PLAYER_SHOVED for e in self.world.events.drain()))
        self.assertTrue(player.is_controllable, "the clock borrows time, never a life")

    def test_twelve_lamps_strike_midnight_and_the_drive_rewinds(self):
        self.enter()
        g = self.guardian
        g.cycle = SERVICE_START + 0.05
        g._work_treadle(self.world, int(g.cycle / CYCLE), "prince")
        self.assertEqual(g.teeth, 1)
        g.debt = LAMPS - 2
        g._borrow(self.world, (g.x, g.floor - 100))
        self.step(1 / 60)
        self.assertEqual(g.stage, "midnight")
        self.assertEqual(g.teeth, 0)
        self.assertEqual(self.world.wonder.progress, 0)
        self.step(2.0)
        self.assertEqual(g.stage, "work")
        self.game.draw(self.screen)

    def test_stopped_time_freezes_echoes_into_glass_that_any_blow_shatters(self):
        self.make_game((0, 1, 2))
        self.enter()
        g = self.guardian
        player = self.world.player
        echo = self.plant_echo(g.x - 160, facing=1)       # facing away: unbreakable while time runs
        player.arrive_at((g.treadle.centerx, g.floor))
        self.step(0.1)
        self.assertTrue(self.world.wonder.power.use(self.world))
        self.step(0.5)
        self.assertGreater(g.braced, 0)
        before = g.cycle
        self.step(0.5)
        self.assertEqual(g.cycle, before, "the clock is stopped")
        self.assertGreater(g.dusk, 0.5, "and the world has gone silver")
        self.game.draw(self.screen)
        player.arrive_at((echo.sample.x - 20, g.floor))
        player.facing = 1
        player._attack_timer = 0.15
        player._attack_facing = 1
        g._update_echoes(0.0, self.world, False, int(g.cycle / CYCLE))
        self.assertFalse(echo.alive)


if __name__ == "__main__":
    unittest.main()
