"""Level 3's mechanism, real input route, page teaching and retry integration."""

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
from jazari.catalog import entry_for
from jazari.levels.l03_archivist import CYCLE, SERVICE_START, SilentArchivist
from jazari.levels.l03_fulcrum import FoldedFulcrum, LIFT_LIFE, footing
from jazari.manuscript import GrantCeremony, ManuscriptOverlay
from rendering.sprite_library import SpriteLibrary
from scenes.game_scene import GameScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from ui.text import wrap_text
from world.collision_map import TileCollision
from world.level_loader import LevelLoader
from world.world_builder import build_world


class ArchivistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.mixer.quit()
        cls.screen = pygame.display.set_mode((960, 540))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.levels = LevelLoader(settings.MAPS_DIR)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="archivist-tests-")
        self.addCleanup(directory.cleanup)
        self.context = GameContext(assets=self.assets, sprites=self.sprites, levels=self.levels,
            audio=Mock(), input=InputState(), scenes=SceneManager(), save=SaveManager(Path(directory.name)),
            debug=DebugOverlay())
        self.make_game()

    def make_game(self, pages=()):
        self.session = GameSession("level3.tmx", pages_found=set(pages))
        self.game = GameScene(self.context, self.session, self.levels.load("level3.tmx"))
        self.context.scenes.reset(self.game)
        self.world = self.game.world
        self.guardian = self.world.wonder.guardian

    def step(self, seconds, intent=None, hz=120):
        events = []
        for _ in range(round(seconds * hz)):
            self.world.player.intent = intent or PlayerIntent()
            self.world.update(1 / hz, self.game._camera.view_rect)
            events.extend(self.world.events.drain())
        return events

    def enter(self):
        self.world.player.arrive_at((self.guardian.x - 200, self.guardian.floor))
        self.step(2.1)
        self.assertEqual(self.guardian.stage, "work")

    def pound_event(self):
        self.world.events.emit(EventType.PLAYER_POUNDED, self.guardian.treadle.midbottom)
        self.guardian.update(.001, self.world)
        self.world.events.drain()

    def physical_pound(self):
        self.step(1 / 120, PlayerIntent(jump_pressed=True, jump_held=True))
        self.step(.055, PlayerIntent(jump_held=True))
        self.step(1 / 120, PlayerIntent(down_pressed=True, down_held=True))
        return self.step(.35)

    def test_only_level_three_registered_and_terrain_untouched(self):
        self.assertIs(entry_for("level3.tmx").guardian, SilentArchivist)
        self.assertEqual(entry_for("level1.tmx").power.key, "nightingale")
        self.assertIsNone(entry_for("level4.tmx"))
        plain = build_world(self.world.level, self.sprites, self.assets)
        self.assertEqual(self.world.collision._cells, plain.collision._cells)
        self.assertFalse(self.guardian.lethal)
        self.assertEqual(self.world.goals, [])
        for index in range(3):
            x = self.guardian.x + (-96, 0, 96)[index]
            self.assertEqual(self.world.collision.get(int(x // 32), 22), TileCollision.SOLID)

    def test_three_pages_grant_after_demo_and_ceremony_not_before(self):
        director = self.world.wonder
        for index in (2, 0, 1):
            director.on_page_collected(index)
        self.assertIsNone(director.power)
        kinds = [director.overlay, *director._queue]
        self.assertEqual([p.index for p in kinds if isinstance(p, ManuscriptOverlay)], [2, 0, 1])
        self.assertIsInstance(kinds[-1], GrantCeremony)
        for _ in range(4):
            director.overlay.time = 6
            self.context.input._pressed = set()
            # Use the same abstract POWER action as keyboard V / E and stick click.
            from core.input import Action
            self.context.input._pressed.add(Action.POWER)
            director.update_overlay(.01, self.context.input)
            self.context.input.end_step()
            director.update_overlay(.4, self.context.input)
        self.assertIsInstance(director.power, FoldedFulcrum)
        self.assertFalse(director.overlay_active)
        director.on_page_collected(2)
        self.assertFalse(director.overlay_active)

    def test_prior_saved_pages_restore_the_power_without_an_overlay(self):
        self.context.save.data.record("level3.tmx").pages = [0, 1, 2]
        self.make_game()
        self.assertIsInstance(self.world.wonder.power, FoldedFulcrum)
        self.assertFalse(self.world.wonder.overlay_active)

    def test_body_attacks_do_not_release_drives(self):
        self.enter()
        self.step(.7, PlayerIntent(attack_pressed=True))
        self.assertEqual(self.world.wonder.progress, 0)
        self.assertFalse(self.guardian.resolved)

    def test_closed_wrong_and_distant_treadles_do_not_advance(self):
        self.enter()
        self.pound_event()
        self.assertEqual(self.guardian.teeth, 0)
        self.guardian.cycle = SERVICE_START
        self.world.events.emit(EventType.PLAYER_POUNDED, (self.guardian.x + 96, self.guardian.floor))
        self.guardian.update(.01, self.world)
        self.assertEqual(self.guardian.teeth, 0)
        self.world.events.drain()

    def test_manual_stroke_turns_one_tooth_and_cannot_repeat_in_same_window(self):
        self.enter()
        self.guardian.cycle = SERVICE_START
        self.pound_event()
        self.assertEqual(self.guardian.teeth, 1)
        self.pound_event()
        self.assertEqual(self.guardian.teeth, 1)

    def test_real_jump_and_pound_works_in_the_unpowered_window(self):
        self.enter()
        g = self.guardian
        self.world.player.arrive_at((g.treadle.centerx, g.floor))
        self.step(.2)
        g.cycle = SERVICE_START
        events = self.physical_pound()
        self.assertTrue(any(e.type == EventType.PLAYER_POUNDED for e in events))
        self.assertEqual(g.teeth, 1)

    def test_power_holds_drive_then_real_pound_rewinds_all_six(self):
        self.make_game((0, 1, 2))
        self.enter()
        g = self.guardian
        self.world.player.arrive_at((g.treadle.centerx, g.floor))
        self.step(.2)
        power = self.world.wonder.power
        self.assertTrue(power.use(self.world))
        self.step(.4)
        self.assertGreater(g.braced, 2.5)
        self.assertEqual(g.contact_rects(), [])
        self.physical_pound()
        self.assertEqual(g.stage, "rewind")
        self.step(2)
        self.assertEqual(g.released, 1)
        self.assertEqual(self.world.wonder.progress, 6)

    def test_three_drives_are_solvable_without_power_and_unlock_nonlethally(self):
        self.enter()
        g = self.guardian
        for phase in range(3):
            for tooth in range(6):
                g.cycle = tooth * CYCLE + SERVICE_START
                self.pound_event()
            if phase < 2:
                self.step(1.3)
        self.assertEqual(g.stage, "ending")
        self.step(3.1)
        self.assertTrue(g.resolved)
        self.assertEqual(len(self.world.goals), 1)
        self.assertEqual(g.released, 3)
        self.assertEqual(g.stage, "done")

    def test_partial_ratchet_progress_and_power_survive_checkpoint_retry(self):
        self.make_game((0, 1, 2))
        self.enter()
        self.guardian.cycle = SERVICE_START
        self.pound_event()
        self.game.restart_from_checkpoint()
        director = self.game.world.wonder
        self.assertEqual(director.progress, 1)
        self.assertEqual(director.guardian.teeth, 1)
        self.assertIsInstance(director.power, FoldedFulcrum)

    def test_resolved_retry_does_not_lock_the_exit_again(self):
        self.enter()
        self.guardian.resolve(self.world, "test")
        self.game._process_events()
        self.game.restart_from_checkpoint()
        self.assertTrue(self.game.world.wonder.guardian.resolved)
        self.assertEqual(len(self.game.world.goals), 1)

    def test_shoves_cost_rhythm_not_health(self):
        self.enter()
        g = self.guardian
        g.cycle = 1.5
        rect = g.contact_rects()[0]
        player = self.world.player
        player.arrive_at((rect.centerx, rect.bottom))
        player._invulnerable_timer = 0
        power = player.power
        g.update(.001, self.world)
        self.assertLess(player.body.velocity.y, 0)
        self.assertEqual(player.power, power)
        self.assertTrue(player.is_controllable)
        self.assertTrue(any(e.type == EventType.PLAYER_SHOVED for e in self.world.events.drain()))

    def test_attack_rectangles_match_visible_fingertips(self):
        self.enter()
        g = self.guardian
        for phase in range(3):
            g.released = phase
            g.cycle = 1.7
            tips = [(round(g.x + x), round(g.floor + y)) for x, y in g.hand_tips()]
            for rect in g.contact_rects():
                self.assertTrue(any(rect.collidepoint(tip) for tip in tips))
            g.cycle = SERVICE_START
            self.assertFalse(g.contact_rects())

    def test_cast_cannot_reach_through_masonry(self):
        self.make_game((0, 1, 2))
        self.enter()
        player = self.world.player
        player.arrive_at((self.guardian.x - 180, self.guardian.floor))
        self.assertTrue(self.guardian.can_brace(player))
        self.world.collision.set(245, 21, TileCollision.SOLID)
        self.assertFalse(self.guardian.can_brace(player))

    def test_lifting_step_carries_player_and_cannot_be_stacked(self):
        self.make_game((0, 1, 2))
        player = self.world.player
        player.arrive_at((6544, 704))
        self.step(.2)
        power = self.world.wonder.power
        self.assertTrue(power.use(self.world))
        floor = player.body.bottom
        self.step(1)
        self.assertAlmostEqual(player.body.bottom, floor - 104, delta=2)
        power.cooldown_left = 0
        self.assertFalse(power.use(self.world))
        self.assertIsNotNone(power.step)
        self.step(LIFT_LIFE)
        self.assertIsNone(power.step)
        self.assertAlmostEqual(player.body.bottom, floor, delta=2)

    def test_lift_rejects_pits_edges_and_low_ceilings(self):
        x = 6544
        self.assertIsNotNone(footing(self.world, x, 704))
        self.assertIsNone(footing(self.world, -3, 704))
        tx = int(x // 32)
        for col in range(tx - 1, tx + 2):
            self.world.collision.set(col, 20, TileCollision.SOLID)
        self.assertIsNone(footing(self.world, x, 704))
        for col in range(tx - 1, tx + 2):
            for row in range(20, 26):
                self.world.collision.set(col, row, TileCollision.EMPTY)
        self.assertIsNone(footing(self.world, x, 704))

    def test_lift_can_defeat_an_ordinary_enemy_away_from_the_guardian(self):
        self.make_game((0, 1, 2))
        player = self.world.player
        player.arrive_at((6544, 704))
        self.step(.2)
        enemy = next(e for e in self.world.enemies if not e.star_immune)
        enemy.body.place_midbottom((6560, 704))
        self.assertTrue(self.world.wonder.power.use(self.world))
        self.step(.12)
        self.assertFalse(enemy.is_dangerous)

    def test_hand_paths_are_continuous_across_cycle_boundaries(self):
        self.enter()
        for phase in range(3):
            self.guardian.released = phase
            previous = None
            for frame in range(505):
                self.guardian.cycle = frame / 120
                tips = self.guardian.hand_tips()
                if previous is not None:
                    for a, b in zip(previous, tips):
                        self.assertLess(pygame.Vector2(a).distance_to(b), 7)
                previous = tips
    def test_pages_ceremony_and_all_mechanical_states_render(self):
        entry = self.world.wonder.entry
        for index in range(3):
            overlay = ManuscriptOverlay(entry, index, self.assets, 3)
            overlay.time = 2.9
            overlay.draw(self.screen)
        lines = wrap_text(overlay._body_font, entry.text, 492)
        self.assertLessEqual(len(lines) * (overlay._body_font.get_linesize() + 2), 240)
        self.assertLess(overlay._caption_font.size(entry.demo_caption)[0], 540)
        ceremony = GrantCeremony(entry, self.assets)
        for time in (0, .5, 1.3, 1.55, 2.1, 2.8, 3.5, 4.5):
            ceremony.time = time
            ceremony.draw(self.screen)
        self.enter()
        g = self.guardian
        self.game._camera.snap_to((g.x - 85, g.floor - 210))
        for phase in range(3):
            g.released = phase
            for beat in (0, .8, 1.4, 2, 3.4):
                g.cycle = beat
                self.game.draw(self.screen)
        for stage in ("rewind", "turn", "ending", "done"):
            g.stage = stage
            self.game.draw(self.screen)

    def complete_with_inputs(self, powered, hz):
        """No teleports, injected pound events, invulnerability or forced phases.

        Manual: retreat beyond the comb, dash back, jump and time the pound.
        Powered: approach, V, jump and pound. Both start at the arena entrance.
        """
        self.make_game((0, 1, 2) if powered else ())
        world, g = self.world, self.guardian
        player = world.player
        player.arrive_at((g.x - 230, g.floor))
        last_jump = -10
        last_lap = last_dash = None
        shoves = 0
        for frame in range(hz * 100):
            t = frame / hz
            move = 0
            jump = down = use = dash = False
            if g.stage == "work":
                lap = (g.released, int(g.cycle / CYCLE))
                target = g.treadle.centerx
                if not powered and g.beat < 2.1:
                    target = g.x + 224
                dx = target - player.body.centerx
                stopping = max(3, abs(player.body.velocity.x) * .035)
                move = (1 if dx > 0 else -1) if abs(dx) > stopping else 0
                if not powered and 2.1 <= g.beat < 2.3 and abs(dx) > 170 and last_dash != lap:
                    dash = True
                    last_dash = lap
                if powered and abs(dx) < 20 and world.wonder.power.ready and g.braced <= 0:
                    use = True
                window = (g.braced > .5 if powered else 3.08 <= g.beat < 3.46 and last_lap != lap)
                if window and player.body.on_ground and abs(dx) < 13:
                    jump = True
                    last_jump = t
                    last_lap = lap
            if .09 < t - last_jump < .09 + 1.2 / hz:
                down = True
            player.intent = PlayerIntent(move_axis=move, jump_pressed=jump, jump_held=t-last_jump < .11,
                down_pressed=down, down_held=down, power_pressed=use, dash_pressed=dash)
            world.update(1 / hz, world.bounds)
            events = world.events.drain()
            shoves += sum(event.type == EventType.PLAYER_SHOVED for event in events)
            self.assertFalse(any(e.type in (EventType.PLAYER_HURT, EventType.PLAYER_DIED) for e in events))
            if g.resolved:
                self.assertEqual(len(world.goals), 1)
                return t, shoves
        self.fail(f"Input route stuck: powered={powered}, hz={hz}, progress={world.wonder.progress}")

    def test_skilled_input_routes_and_four_to_six_times_balance_at_two_frame_rates(self):
        for hz in (30, 120):
            with self.subTest(hz=hz):
                manual, manual_shoves = self.complete_with_inputs(False, hz)
                powered, powered_shoves = self.complete_with_inputs(True, hz)
                self.assertGreaterEqual(manual / powered, 4)
                self.assertLessEqual(manual / powered, 6)
                self.assertEqual((manual_shoves, powered_shoves), (0, 0))


if __name__ == "__main__":
    unittest.main()
