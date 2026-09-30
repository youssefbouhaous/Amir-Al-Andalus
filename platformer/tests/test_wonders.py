"""Real-physics regression checks for opt-in moves and telegraphed enemies."""

import hashlib
import os
import unittest
from dataclasses import replace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from core.campaign import next_level
from entities.enemies.enemy import EnemyState
from entities.enemies.wonders import MirrorDuelist, SandBurrower, LanternThief, ClockworkGuardian
from entities.player import PlayerState, PowerLevel
from entities.player_controller import PlayerIntent
from objects.grapple_hook import GrappleHook
from objects.hazards import Spikes
from objects.mechanisms import DashLantern
from rendering import sprite_specs, wonders_specs
from rendering.acrobatics_specs import PLAYER_SHEETS
from rendering.sprite_library import SpriteLibrary, build_placeholder_sheet
from world.collision_map import CollisionMap, TileCollision
from world.level_data import ObjectSpec
from world.level_loader import LevelLoader
from world.world_builder import build_world


class WondersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 540))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.loader = LevelLoader(settings.MAPS_DIR)
        cls.level = cls.loader.load("challenge_courtyard.tmx")

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        collision = CollisionMap(80, 24, 32)
        for tx in range(80):
            collision.set(tx, 20, TileCollision.SOLID)
        level = replace(self.level, collision=collision, back_layers=[], front_layers=[], objects=[
            ObjectSpec(1, "player_spawn", "", pygame.Rect(180, 612, 24, 28))])
        self.world = build_world(level, self.sprites, self.assets)
        self.player = self.world.player
        self.step()

    def step(self, dt=1 / 120, **intent):
        self.player.intent = PlayerIntent(**intent)
        self.world.update(dt, self.world.bounds)

    def advance(self, seconds, **intent):
        for _ in range(round(seconds * 120)):
            self.step(**intent)

    def air(self):
        self.player.arrive_at((192, 450))
        self.player.state = PlayerState.FALLING

    def hook(self, position=(230, 290)):
        hook = GrappleHook(position)
        self.world.grapple_hooks.append(hook)
        self.world.props.append(hook)
        return hook

    def ledge(self, side=1):
        for y in range(16, 20):
            self.world.collision.set(10, y, TileCollision.SOLID)
        self.player.arrive_at((310 if side == 1 else 362, 542))
        self.player.body.velocity.y = 90
        self.player.state = PlayerState.FALLING
        self.step(move_axis=side)

    def test_original_procedural_frames_are_pixel_identical(self):
        expected = (
            "de1058ccaf4b91c9081dcb9b44ed4c6f463d8aa3a0cedbc5589481282462242d",
            "bffdae5e9c34fc64fdb326b555f0c9c9359c8d3cac6eb5a3598167530d01a24f",
            "eea823d92fbde4fb7b07e801a87c851863df1f32c817eea46752e387683738bc",
        )
        for spec, digest in zip((sprite_specs.PLAYER, sprite_specs.PLAYER_POWERED, sprite_specs.PLAYER_STAR), expected):
            self.assertEqual(hashlib.sha256(pygame.image.tobytes(build_placeholder_sheet(spec), "RGBA")).hexdigest(), digest)

    def test_old_levels_do_not_enable_moves_or_load_supplemental_sheets(self):
        sprites = SpriteLibrary(self.assets)
        for index in range(1, 16):
            level = self.loader.load(f"level{index}.tmx")
            # No set dressing needed to check per-map setup.
            level = replace(level, objects=level.objects_of("player_spawn"))
            player = build_world(level, sprites, self.assets).player
            self.assertFalse(player.acrobatics_enabled)
            self.assertFalse(player._animator.has("vault"))
        self.assertNotIn(PLAYER_SHEETS[0].image_path, sprites._cache)
        self.assertIsNone(next_level("level15.tmx"))

    def test_optional_map_has_three_pages_four_enemies_and_safe_checkpoints(self):
        world = build_world(self.level, self.sprites, self.assets)
        self.assertEqual(len(world.enemies), 4)
        self.assertEqual(len(self.level.objects_of("page")), 3)
        self.assertEqual(len(world.grapple_hooks), 7)
        for checkpoint in world.checkpoints:
            self.assertTrue(all(abs(e.body.centerx - checkpoint.rect.centerx) > 96 for e in world.enemies))
        for tx in range(150):
            self.assertEqual(world.collision.get(tx, 20), TileCollision.SOLID)

    def test_grapple_is_opt_in_and_needs_fresh_press(self):
        self.air()
        hook = self.hook()
        self.step(up_held=True)
        self.assertFalse(hook.held)
        self.player.acrobatics_enabled = False
        self.step(up_pressed=True)
        self.assertFalse(hook.held)
        self.player.acrobatics_enabled = True
        self.step(up_pressed=True)
        self.assertTrue(hook.held)
        self.assertEqual(self.player.state, PlayerState.SWING)
        self.assertEqual(self.player._animator.current, "scarf_cast")

    def test_grapple_attaches_without_teleport_and_refills_dash(self):
        self.air()
        hook = self.hook()
        original = pygame.Vector2(self.player.body.midbottom)
        self.player.dash_charges = 0
        self.step(up_pressed=True)
        self.assertLess(pygame.Vector2(self.player.body.midbottom).distance_to(original), .01)
        self.assertEqual(self.player.dash_charges, 1)
        self.advance(.2, move_axis=1)
        self.assertEqual(self.player._animator.current, "scarf_swing")
        self.assertTrue(hook.held)

    def test_hooks_behind_walls_below_player_or_out_of_range_are_rejected(self):
        for position in ((230, 100), (230, 500), (230, 290)):
            with self.subTest(position=position):
                self.air()
                self.world.grapple_hooks = []
                hook = self.hook(position)
                if position == (230, 290):
                    self.world.collision.set(6, 10, TileCollision.SOLID)
                    self.world.collision.set(7, 10, TileCollision.SOLID)
                self.step(up_pressed=True)
                self.assertFalse(hook.held)

    def test_up_dash_does_not_attach_to_hook(self):
        self.air()
        hook = self.hook()
        self.step(up_pressed=True, up_held=True, dash_pressed=True)
        self.assertFalse(hook.held)
        self.assertEqual(self.player.state, PlayerState.DASH)
        self.assertLess(self.player.body.velocity.y, -500)

    def test_swing_jump_and_dash_release_cleanly(self):
        for dash in (False, True):
            with self.subTest(dash=dash):
                self.air()
                self.world.grapple_hooks = []
                hook = self.hook()
                self.step(up_pressed=True)
                self.advance(.2, move_axis=1)
                self.step(move_axis=1, dash_pressed=dash, jump_pressed=not dash, jump_held=not dash)
                self.assertFalse(hook.held)
                self.assertIsNone(self.player._ring)
                self.assertEqual(self.player.state, PlayerState.DASH if dash else PlayerState.JUMPING)
                self.assertEqual(self.player._animator.current, "dash" if dash else "spin_jump")
                self.assertEqual(self.player.dash_charges, 0 if dash else 1)

    def test_respawn_releases_hook_and_clears_acrobatic_state(self):
        self.air()
        hook = self.hook()
        self.step(up_pressed=True)
        self.player.die(self.world)
        self.assertFalse(hook.held)
        self.player.arrive_at((192, 640))
        self.assertIsNone(self.player._ledge)
        self.assertEqual(self.player._spin_timer, 0)
        self.assertEqual(self.player._grapple_cast, 0)
        self.assertTrue(self.player.acrobatics_enabled)

    def test_ledge_catch_and_vault_on_both_sides(self):
        for side in (-1, 1):
            with self.subTest(side=side):
                self.ledge(side)
                self.assertEqual(self.player.state, PlayerState.LEDGE_HANG)
                for _ in range(70):
                    self.step(move_axis=side)
                    if self.player.body.on_ground:
                        break
                self.assertTrue(self.player.body.on_ground)
                self.assertAlmostEqual(self.player.body.bottom, 512)
                self.assertGreaterEqual(self.player.body.left, 320)
                self.assertLessEqual(self.player.body.right, 352)

    def test_down_drops_ledge_and_prevents_immediate_recatch(self):
        self.ledge()
        self.step(down_held=True, down_pressed=True, move_axis=1)
        self.assertEqual(self.player.state, PlayerState.FALLING)
        self.advance(.1, move_axis=1)
        self.assertNotIn(self.player.state, (PlayerState.LEDGE_HANG, PlayerState.VAULT))

    def test_jump_vaults_without_holding_direction(self):
        self.ledge()
        self.step(jump_pressed=True, jump_held=True)
        self.assertEqual(self.player.state, PlayerState.VAULT)
        self.advance(.3)
        self.assertTrue(self.player.body.on_ground)
        self.assertEqual(self.player._jump_buffer_timer, 0)

    def test_low_ceiling_and_hazardous_ledge_do_not_grab(self):
        self.world.collision.set(10, 15, TileCollision.SOLID)
        self.ledge()
        self.assertNotEqual(self.player.state, PlayerState.LEDGE_HANG)
        self.world.collision.set(10, 15, TileCollision.EMPTY)
        self.world.props.append(Spikes(pygame.Rect(320, 480, 32, 32)))
        self.ledge()
        self.assertNotEqual(self.player.state, PlayerState.LEDGE_HANG)

    def test_new_obstacle_during_vault_aborts_without_embedding_player(self):
        self.ledge()
        self.step(jump_pressed=True)
        self.world.collision.set(10, 15, TileCollision.SOLID)
        self.advance(.3)
        self.assertNotEqual(self.player.state, PlayerState.VAULT)
        self.assertFalse(any(k == TileCollision.SOLID for _, _, k in self.world.collision.cells_overlapping(
            self.player.body.left, self.player.body.top, self.player.body.right, self.player.body.bottom)))

    def test_slide_jump_adds_spin_without_changing_launch_velocity(self):
        self.player.body.velocity.x = 230
        self.step(move_axis=1, down_pressed=True, down_held=True)
        self.assertEqual(self.player._animator.current, "sand_slide")
        self.step(move_axis=1, jump_pressed=True, jump_held=True)
        self.assertEqual(self.player._animator.current, "spin_jump")
        self.assertAlmostEqual(self.player.body.velocity.y, -self.player.physics.jump_velocity * .86)

    def test_landing_pose_does_not_lock_jump_or_attack(self):
        self.player.arrive_at((192, 610))
        self.player.state = PlayerState.FALLING
        self.player._was_on_ground = False
        self.player.body.velocity.y = 550
        self.advance(.05)
        self.assertEqual(self.player._animator.current, "land_hard")
        self.step(jump_pressed=True, jump_held=True, attack_pressed=True)
        self.assertLess(self.player.body.velocity.y, -600)
        self.assertEqual(self.player._animator.current, "throw")

    def enemy(self, cls, spec):
        enemy = cls((500, 640), self.sprites.animations(spec), facing=-1)
        self.world.enemies.append(enemy)
        return enemy

    def test_mirror_has_a_locked_lunge_and_generous_recovery(self):
        enemy = self.enemy(MirrorDuelist, wonders_specs.MIRROR_DUELIST)
        self.player.arrive_at((380, 640))
        enemy.behave(.01, self.world)
        self.assertEqual(enemy.phase, "windup")
        self.player.arrive_at((620, 640))
        enemy.behave(.6, self.world)
        self.assertEqual(enemy.facing, -1)
        self.assertEqual(enemy.phase, "lunge")
        for _ in range(35): enemy.behave(1 / 120, self.world)
        self.assertEqual(enemy.phase, "recover")
        self.assertTrue(enemy.on_slashed(self.world, 1))

    def test_mirror_blocks_front_but_not_back_attacks(self):
        enemy = self.enemy(MirrorDuelist, wonders_specs.MIRROR_DUELIST)
        self.assertFalse(enemy.on_slashed(self.world, 1))
        self.assertTrue(enemy.on_starred(self.world, 1))
        self.assertEqual(enemy.state, EnemyState.ACTIVE)
        self.assertTrue(enemy.on_slashed(self.world, -1))
        self.assertEqual(enemy.state, EnemyState.KNOCKED_OUT)

    def test_burrower_is_harmless_until_warning_and_emergence_finish(self):
        enemy = self.enemy(SandBurrower, wonders_specs.SAND_BURROWER)
        self.player.arrive_at((440, 640))
        self.assertFalse(enemy.is_dangerous)
        self.assertFalse(enemy.on_slashed(self.world, 1))
        for _ in range(170): enemy.behave(1 / 120, self.world)
        self.assertEqual(enemy.phase, "warn")
        self.assertFalse(enemy.is_dangerous)
        for _ in range(90): enemy.behave(1 / 120, self.world)
        self.assertEqual(enemy.phase, "emerge")
        self.assertFalse(enemy.is_dangerous)
        for _ in range(40): enemy.behave(1 / 120, self.world)
        self.assertTrue(enemy.is_dangerous)
        self.assertTrue(enemy.on_stomped(self.world))

    def test_guardian_blocks_all_attacks_then_opens_for_counter(self):
        enemy = self.enemy(ClockworkGuardian, wonders_specs.CLOCKWORK_GUARDIAN)
        self.assertFalse(enemy.on_slashed(self.world, 1))
        self.assertFalse(enemy.on_stomped(self.world))
        self.assertTrue(enemy.on_starred(self.world, 1))
        self.assertEqual(enemy.state, EnemyState.ACTIVE)
        for _ in range(240): enemy.behave(1 / 120, self.world)
        self.assertEqual(enemy.phase, "open")
        self.assertTrue(enemy.on_slashed(self.world, 1))
        self.assertEqual(enemy.state, EnemyState.KNOCKED_OUT)

    def borrowing_thief(self):
        enemy = self.enemy(LanternThief, wonders_specs.LANTERN_THIEF)
        lamp = DashLantern((490, 590))
        self.world.props.append(lamp)
        self.player.arrive_at((400, 640))
        enemy.behave(1.1, self.world)
        self.assertIs(enemy.lantern, lamp)
        self.assertFalse(lamp.lit)
        return enemy, lamp

    def test_thief_borrowing_expires_and_never_permanently_removes_lamp(self):
        enemy, lamp = self.borrowing_thief()
        for _ in range(500):
            lamp.update(1 / 120, self.world)
            enemy.behave(1 / 120, self.world)
        self.assertTrue(lamp.lit)
        self.assertIsNone(enemy.lantern)

    def test_all_thief_defeat_paths_return_light_and_refill_dash(self):
        for attack in ("on_slashed", "on_starred", "on_stomped", "knock_out"):
            with self.subTest(attack=attack):
                self.world.props = []
                enemy, lamp = self.borrowing_thief()
                self.player.dash_charges = 0
                if attack == "on_stomped":
                    enemy.on_stomped(self.world)
                else:
                    getattr(enemy, attack)(self.world, 1)
                self.assertTrue(lamp.lit)
                self.assertIsNone(enemy.lantern)
                self.assertEqual(self.player.dash_charges, 1)

    def test_lamp_recovers_if_borrower_disappears(self):
        enemy, lamp = self.borrowing_thief()
        enemy.alive = False
        lamp.update(1 / 120, self.world)
        self.assertTrue(lamp.lit)

    def test_supplemental_frames_are_cached_and_power_variants_complete(self):
        for power in PowerLevel:
            self.player._set_power(power)
            self.assertTrue(self.player._animator.has("spin_jump"))
            self.assertTrue(self.player._animator.has("run"))
        for spec in (*PLAYER_SHEETS, *wonders_specs.ENEMY_SHEETS):
            animations = self.sprites.animations(spec)
            self.assertIs(animations, self.sprites.animations(spec))
            for animation in animations.values():
                pixels = {pygame.image.tobytes(frame, "RGBA") for frame in animation.frames}
                self.assertGreater(len(pixels), 1)


if __name__ == "__main__":
    unittest.main()
