"""Boss attacks must not depend on whether the player can take damage."""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from core.events import EventType
from entities.boss import HOVER_HEIGHT, MAX_HEALTH, Mode, STUNNED_HEAD_HEIGHT
from entities.player import PlayerState, PowerLevel
from entities.player_controller import PlayerIntent
from rendering.sprite_library import SpriteLibrary
from world.level_loader import LevelLoader
from world.world_builder import build_world


class BossCombatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.level = LevelLoader(settings.MAPS_DIR).load("level15.tmx")

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.world = build_world(self.level, self.sprites, self.assets)
        self.player = self.world.player
        self.boss = self.world.boss
        self.boss.head_y = self.boss.target_head_y = self.boss.floor - STUNNED_HEAD_HEIGHT
        self.boss._set(Mode.STUNNED, 3.6)
        self.player.arrive_at((self.boss.x - 46, self.boss.head_y + 14))
        self.player._invulnerable_timer = 0.0

    def step(self, dt=1 / 120, **intent):
        self.player.intent = PlayerIntent(**intent)
        self.world.update(dt, self.world.bounds)

    def resting_fist(self, offset=60):
        fist = self.boss.fists[0]
        fist.x, fist.y = self.boss.x - 120, self.boss.floor
        fist.resting = True
        self.boss._active_fist = fist
        self.boss.head_y = self.boss.target_head_y = self.boss.floor - HOVER_HEIGHT
        self.boss._set(Mode.SLAM_REST, 2.4)
        self.player.arrive_at((fist.x + offset, self.boss.floor))
        self.step()
        return fist

    def jump_and_pound(self, dt=1 / 120):
        for tick in range(round(0.9 / dt)):
            self.step(
                dt=dt,
                jump_pressed=tick == 0,
                jump_held=tick < round(0.2 / dt),
                down_pressed=tick == round(0.2 / dt),
            )

    def slash(self):
        self.step(move_axis=1, attack_pressed=True)
        # The same swing must not remove more than one health point.
        for _ in range(12):
            self.step()

    def assert_one_hit(self):
        self.assertEqual(self.boss.health, MAX_HEALTH - 1)
        self.assertEqual(self.boss.mode, Mode.HURT)
        events = [event.type for event in self.world.events.drain()]
        self.assertEqual(events.count(EventType.BOSS_HIT), 1)
        self.assertNotEqual(self.player.state, PlayerState.DEAD)

    def test_sword_hits_while_flashing_after_damage(self):
        self.player.power_up(self.world, PowerLevel.POMEGRANATE)
        self.player.take_damage(self.world)
        self.assertFalse(self.player.can_be_hurt)
        self.assertEqual(self.player.power, PowerLevel.NONE)
        self.slash()
        self.assert_one_hit()

    def test_sword_hits_with_spawn_protection(self):
        self.player.protect_on_spawn()
        self.slash()
        self.assert_one_hit()

    def test_sword_hits_without_protection(self):
        self.assertTrue(self.player.can_be_hurt)
        self.slash()
        self.assert_one_hit()

    def test_stomp_hits_while_protected(self):
        self.player.arrive_at((self.boss.x, self.boss.head_rect.top - 2))
        self.player.body.velocity.y = 240
        self.player.protect_on_spawn()
        for _ in range(6):
            self.step()
        self.assert_one_hit()

    def test_dash_still_hits_while_protected(self):
        self.player.protect_on_spawn()
        self.step(move_axis=1, dash_pressed=True)
        for _ in range(6):
            self.step()
        self.assert_one_hit()

    def test_protection_still_prevents_boss_contact_damage(self):
        self.boss._set(Mode.IDLE, 10.0)
        self.player.arrive_at((self.boss.x, self.boss.head_y + 14))
        self.player.protect_on_spawn()
        self.step(attack_pressed=True)
        self.assertEqual(self.boss.health, MAX_HEALTH)
        self.assertNotEqual(self.player.state, PlayerState.DEAD)

    def test_unstunned_boss_still_hurts_unprotected_player(self):
        self.boss._set(Mode.IDLE, 10.0)
        self.player.arrive_at((self.boss.x, self.boss.head_y + 14))
        self.step(attack_pressed=True)
        self.assertEqual(self.boss.health, MAX_HEALTH)
        self.assertEqual(self.player.state, PlayerState.DEAD)

    def test_non_controllable_player_cannot_stomp_boss(self):
        for state in (PlayerState.DEAD, PlayerState.ENTERING_DOOR,
                      PlayerState.EXITING_DOOR, PlayerState.VICTORY):
            with self.subTest(state=state):
                self.player.arrive_at((self.boss.x, self.boss.head_rect.top + 4))
                self.player.previous_bottom = self.boss.head_rect.top - 2
                self.player.body.velocity.y = 240
                self.player.state = state
                self.boss._contact_damage(self.world)
                self.assertEqual(self.boss.health, MAX_HEALTH)

    def test_nearby_ground_pound_stuns_resting_fist(self):
        # Both sides of the fist are inside the existing ground-pound impact.
        for offset in (-85, -60, 60, 85):
            with self.subTest(offset=offset):
                self.setUp()
                self.resting_fist(offset)
                self.jump_and_pound()
                self.assertEqual(self.boss.mode, Mode.STUNNED)
                self.assertEqual(self.boss.health, MAX_HEALTH)
                self.assertNotEqual(self.player.state, PlayerState.DEAD)

    def test_distant_ground_pound_does_not_stun(self):
        self.resting_fist(offset=140)
        self.jump_and_pound()
        self.assertEqual(self.boss.mode, Mode.SLAM_REST)

    def test_ground_pound_does_not_stun_a_raised_fist(self):
        fist = self.resting_fist()
        fist.resting = False
        fist.slamming = True
        fist.y = self.boss.floor - 190
        self.boss._set(Mode.SLAM_AIM, 3.0)
        self.jump_and_pound()
        self.assertEqual(self.boss.mode, Mode.SLAM_AIM)

    def test_plain_landing_and_slash_do_not_stun_resting_fist(self):
        self.resting_fist(offset=0)
        for tick in range(120):
            self.step(jump_pressed=tick == 0, jump_held=tick < 24,
                      attack_pressed=tick % 40 == 0)
        self.assertEqual(self.boss.mode, Mode.SLAM_REST)
        self.assertEqual(self.boss.health, MAX_HEALTH)

    def test_slam_pound_and_grounded_attack_sequence(self):
        for health in (6, 4, 2):
            for attack in ("sword", "dash"):
                for dt in (1 / 60, 1 / 120):
                    with self.subTest(health=health, attack=attack, dt=dt):
                        self.setUp()
                        self.boss.health = health
                        fist = self.resting_fist()
                        fist.resting = False
                        fist.slamming = True
                        fist.y = self.boss.floor - 190
                        self.boss._set(Mode.SLAM_DROP, 1.0)
                        # Real jump avoids the slam's wave; pound just beside
                        # the fist, then attack after landing from the bounce.
                        stunned = False
                        attacked = False
                        for tick in range(round(4.0 / dt)):
                            stunned |= self.boss.mode == Mode.STUNNED
                            ready = (stunned and self.player.body.on_ground
                                     and self.boss.head_rect.bottom > self.player.rect.top)
                            press = ready and not attacked
                            attacked |= press
                            self.step(
                                dt=dt,
                                move_axis=1 if attack == "dash" and attacked else 0,
                                jump_pressed=tick == 0,
                                jump_held=tick < round(0.2 / dt),
                                down_pressed=tick == round(0.2 / dt),
                                attack_pressed=press and attack == "sword",
                                dash_pressed=press and attack == "dash",
                            )
                            if self.boss.health < health or self.player.state == PlayerState.DEAD:
                                break
                        self.assertTrue(stunned, "Ground pound never stunned the resting fist")
                        self.assertTrue(attacked, "Stunned head never entered grounded attack range")
                        self.assertNotEqual(self.player.state, PlayerState.DEAD)
                        self.assertEqual(self.boss.health, health - 1)


if __name__ == "__main__":
    unittest.main()
