"""Exercise input timing with the real player, collision code and lanterns."""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from core.events import EventType
from entities.player import PlayerState
from entities.player_controller import PlayerIntent
from objects.mechanisms import DashLantern
from rendering.sprite_library import SpriteLibrary
from world.collision_map import CollisionMap, TileCollision
from world.level_loader import LevelLoader
from world.world_builder import build_world


class PlayerControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((960, 540))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.level = LevelLoader(settings.MAPS_DIR).load("level11.tmx")

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.world = build_world(self.level, self.sprites, self.assets)
        # A controlled arena avoids enemies and puzzle geometry affecting
        # measurements. The bazaar's move locks and real player stay intact.
        self.world.collision = CollisionMap(80, 32, 32)
        for x in range(80):
            self.world.collision.set(x, 20, TileCollision.SOLID)
        self.world.enemies = []
        self.world.items = []
        self.world.props = []
        self.world.platforms = []
        self.world.rings = []
        self.world.wind_zones = []
        self.world.blocks = {}
        self.world.checkpoints = []
        self.world.goals = []
        self.world.switch = None
        self.player = self.world.player
        self.player.arrive_at((192, 640))
        self.step()
        self.world.events.drain()

    def step(self, dt=1 / 120, **intent):
        self.player.intent = PlayerIntent(**intent)
        self.world.update(dt, self.world.bounds)

    def advance(self, seconds, **intent):
        for _ in range(round(seconds * 120)):
            self.step(**intent)

    def airborne(self, bottom=400):
        self.player.arrive_at((192, bottom))
        self.player.state = PlayerState.FALLING

    def test_jump_pressed_during_dash_is_used_after_landing(self):
        self.airborne(620)
        self.step(dash_pressed=True, down_held=True)
        self.step(jump_pressed=True)  # early, released before the dash ends
        self.advance(0.09)
        self.assertLess(self.player.body.velocity.y, -150)
        self.assertLess(self.player.body.bottom, 620)
        self.assertIn(EventType.PLAYER_JUMPED, [e.type for e in self.world.events.drain()])

    def test_jump_can_be_pressed_early_before_landing(self):
        self.airborne(581)
        self.player.body.velocity.y = 80
        self.step(jump_pressed=True)
        self.advance(0.19)
        self.assertLess(self.player.body.velocity.y, -150)
        self.assertLess(self.player.body.bottom, 635)

    def test_a_late_ledge_jump_works_at_different_frame_rates(self):
        for dt in (1 / 60, 1 / 120, 1 / 144):
            with self.subTest(dt=dt):
                self.player.arrive_at((192, 640))
                self.step(dt=dt)
                # Remove the supporting tile, as if walking off its edge.
                self.world.collision.set(6, 20, TileCollision.EMPTY)
                self.world.collision.set(5, 20, TileCollision.EMPTY)
                elapsed = 0.0
                while elapsed < 0.12:
                    self.step(dt=dt)
                    elapsed += dt
                self.assertFalse(self.player.body.on_ground)
                self.step(dt=dt, jump_pressed=True, jump_held=True)
                self.assertLess(self.player.body.velocity.y, -600)
                self.world.collision.set(5, 20, TileCollision.SOLID)
                self.world.collision.set(6, 20, TileCollision.SOLID)

    def test_jump_and_dash_together_preserve_both_actions(self):
        self.step(move_axis=1, jump_pressed=True, jump_held=True, dash_pressed=True)
        self.assertEqual(self.player.state, PlayerState.JUMPING)
        self.advance(0.09, move_axis=1, jump_held=True)
        self.assertEqual(self.player.state, PlayerState.DASH)
        self.assertLess(self.player.body.bottom, 610)
        events = [e.type for e in self.world.events.drain()]
        self.assertEqual(events.count(EventType.PLAYER_JUMPED), 1)
        self.assertEqual(events.count(EventType.PLAYER_DASHED), 1)

    def test_dash_pressed_before_recharge_keeps_its_aim(self):
        self.airborne()
        self.player.dash_charges = 0
        self.step(dash_pressed=True, up_held=True, move_axis=1)
        self.advance(0.10, move_axis=-1)
        lantern = DashLantern(self.player.rect.center)
        self.world.props = [lantern]
        self.step(move_axis=-1)  # world contact restores the spent charge
        self.assertFalse(lantern.lit)
        self.step(move_axis=-1)
        self.assertEqual(self.player.state, PlayerState.DASH)
        self.assertGreater(self.player.body.velocity.x, 0)
        self.assertLess(self.player.body.velocity.y, 0)
        self.assertEqual(self.player.dash_charges, 0)

    def test_next_dash_press_is_not_lost_during_current_dash(self):
        self.airborne()
        self.step(dash_pressed=True, move_axis=1)
        self.advance(0.05)
        self.step(dash_pressed=True, up_held=True)
        self.player.refill_dash()
        self.advance(0.12)
        self.assertEqual(self.player.state, PlayerState.DASH)
        self.assertLess(self.player.body.velocity.y, -500)
        self.assertAlmostEqual(self.player.body.velocity.x, 0)
        self.assertEqual(self.player.dash_charges, 0)
        events = [e.type for e in self.world.events.drain()]
        self.assertEqual(events.count(EventType.PLAYER_DASHED), 2)

    def test_expired_press_does_not_dash_after_late_recharge(self):
        self.airborne(250)
        self.player.dash_charges = 0
        self.step(dash_pressed=True)
        self.advance(0.24)
        self.player.refill_dash()
        self.step()
        self.assertNotEqual(self.player.state, PlayerState.DASH)
        self.assertEqual(self.player.dash_charges, 1)

    def test_buffer_cannot_supply_an_extra_air_dash(self):
        self.airborne(250)
        self.step(dash_pressed=True, move_axis=1)
        self.advance(0.05)
        self.step(dash_pressed=True, up_held=True)
        self.advance(0.25)
        events = [e.type for e in self.world.events.drain()]
        self.assertEqual(events.count(EventType.PLAYER_DASHED), 1)
        self.assertEqual(self.player.dash_charges, 0)

    def test_locked_dash_does_not_queue(self):
        self.player.locked_moves = frozenset({"dash"})
        self.step(dash_pressed=True)
        self.player.locked_moves = frozenset()
        self.advance(0.10)
        self.assertNotEqual(self.player.state, PlayerState.DASH)
        self.assertEqual(self.player._dash_buffer_timer, 0)

    def test_holding_jump_does_not_auto_repeat_on_landing(self):
        self.step(jump_pressed=True, jump_held=True)
        self.advance(1.0, jump_held=True)
        self.assertTrue(self.player.body.on_ground)
        events = [e.type for e in self.world.events.drain()]
        self.assertEqual(events.count(EventType.PLAYER_JUMPED), 1)

    def test_bazaar_opening_gap_still_accepts_jump_dash_chains(self):
        # Keep the actual map, props, enemies and move locks for this replay.
        for delay, upward in ((0.30, False), (0.25, True), (0.30, True)):
            with self.subTest(dash_delay=delay, upward=upward):
                self.world = build_world(self.level, self.sprites, self.assets)
                self.player = self.world.player
                self.player.arrive_at((504, 576))
                self.step()
                self.player.body.velocity.x = self.player.physics.max_run_speed
                landed = False
                for tick in range(180):
                    self.step(
                        move_axis=1,
                        jump_pressed=tick == 0,
                        jump_held=True,
                        dash_pressed=tick == round(delay * 120),
                        up_held=upward,
                    )
                    if (self.player.body.on_ground and self.player.body.centerx > 746
                            and self.player.body.bottom <= 576):
                        landed = True
                        break
                    if self.player.state == PlayerState.DEAD:
                        break
                self.assertTrue(landed)

    def test_wall_jump_remembers_wall_side_during_grace_period(self):
        self.airborne(480)
        self.world.collision.set(6, 14, TileCollision.SOLID)
        self.player.body.x = 192 - self.player.body.width
        self.step(move_axis=1)
        self.assertEqual(self.player._wall_side, 1)
        self.player.body.x -= 15
        self.advance(0.10)
        self.assertEqual(self.player._wall_side, 0)
        self.step(jump_pressed=True, jump_held=True)
        self.assertLess(self.player.body.velocity.x, -200)
        self.assertLess(self.player.body.velocity.y, -500)

    def test_slide_jump_press_waits_until_ceiling_is_clear(self):
        # Slide toward a low roof's edge, pressing jump under the last tile.
        # A 16px passage fits the 14px slide, but not the 28px standing body.
        self.world.collision = CollisionMap(160, 64, 16)
        for x in range(160):
            self.world.collision.set(x, 40, TileCollision.SOLID)
        self.player.arrive_at((216, 640))
        self.step()
        self.player.body.velocity.x = 230
        self.step(move_axis=1, down_pressed=True, down_held=True)
        self.world.collision.set(13, 38, TileCollision.SOLID)
        self.step(move_axis=1, jump_pressed=True)
        self.assertEqual(self.player.state, PlayerState.SLIDE)
        self.advance(0.11, move_axis=1)
        self.assertEqual(self.player.body.height, self.player.physics.hitbox_height)
        self.assertLess(self.player.body.velocity.y, -100)

    def test_air_turn_is_quicker_without_increasing_maximum_run_speed(self):
        self.airborne()
        self.player.body.velocity.x = 230
        self.advance(0.15, move_axis=-1)
        self.assertLess(self.player.body.velocity.x, 0)
        self.advance(0.30, move_axis=-1)
        self.assertGreaterEqual(self.player.body.velocity.x, -self.player.physics.max_run_speed)

    def test_quick_tap_is_usable_but_hold_still_jumps_higher(self):
        peaks = []
        for held in (False, True):
            self.player.arrive_at((192, 640))
            self.step()
            self.step(jump_pressed=True, jump_held=held)
            peak = self.player.body.bottom
            for _ in range(75):
                self.step(jump_held=held)
                peak = min(peak, self.player.body.bottom)
            peaks.append(640 - peak)
        self.assertGreater(peaks[0], 40)
        self.assertGreater(peaks[1], peaks[0] + 40)
        self.assertLess(peaks[1], 125)

    def test_respawn_discards_queued_inputs(self):
        self.airborne()
        self.player.dash_charges = 0
        self.step(dash_pressed=True, jump_pressed=True)
        self.player.arrive_at((192, 640))
        self.advance(0.10)
        self.assertNotEqual(self.player.state, PlayerState.DASH)
        self.assertTrue(self.player.body.on_ground)


if __name__ == "__main__":
    unittest.main()
