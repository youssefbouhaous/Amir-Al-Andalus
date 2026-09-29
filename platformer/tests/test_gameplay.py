"""Regression tests for authored level safety, enemy ecology and combat."""

import os
import unittest
from dataclasses import replace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core import settings
from core.assets import AssetManager
from entities.player import PlayerState
from entities.player_controller import PlayerIntent
from rendering.sprite_library import SpriteLibrary
from world.level_data import ObjectSpec
from world.level_loader import LevelLoader
from world.world_builder import build_world


class GameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.font.init()
        cls.assets = AssetManager(settings.ASSETS_DIR)
        cls.sprites = SpriteLibrary(cls.assets)
        cls.loader = LevelLoader(settings.MAPS_DIR)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def world(self, number):
        return build_world(
            self.loader.load(f"level{number}.tmx"), self.sprites, self.assets
        )

    def test_day_levels_do_not_spawn_night_enemies(self):
        night_kinds = {"bat", "jinn", "ghul"}
        for number in range(1, 11):
            level = self.loader.load(f"level{number}.tmx")
            kinds = {
                spec.get_str("kind")
                for spec in level.objects_of("enemy")
            }
            if level.theme not in {"fortress", "mountain", "court"}:
                self.assertTrue(kinds.isdisjoint(night_kinds), (number, kinds))
            else:
                self.assertTrue(kinds & night_kinds, (number, kinds))

    def test_levels_are_long_and_not_copies(self):
        levels = [self.loader.load(f"level{n}.tmx") for n in range(1, 11)]
        self.assertEqual(len({level.collision.width for level in levels}), 10)
        self.assertGreaterEqual(len({level.theme for level in levels}), 7)
        self.assertTrue(all(level.collision.width >= 200 for level in levels))
        self.assertTrue(all(len(level.objects_of("checkpoint")) >= 3 for level in levels))

    def test_melee_attack_works_without_power_up(self):
        world = self.world(1)
        enemy = world.enemies[0]
        world.enemies = [enemy]
        player = world.player
        player.arrive_at((enemy.body.centerx - 30, enemy.body.bottom))
        enemy.body.place_midbottom((player.body.centerx + 28, player.body.bottom))
        enemy.activated = True
        player.facing = 1
        player.intent = PlayerIntent(attack_pressed=True)
        world.update(1 / 120, world.bounds)
        self.assertNotEqual(player.state, PlayerState.DEAD)
        self.assertFalse(enemy.is_dangerous)
        self.assertTrue(any(event.type.name == "PLAYER_ATTACKED" for event in world.events.drain()))

    def test_checkpoint_respawn_clears_overlapping_enemy_and_protects_player(self):
        original = self.loader.load("level1.tmx")
        checkpoint = original.objects_of("checkpoint")[0]
        enemy = ObjectSpec(
            9999,
            "enemy",
            "test-overlap",
            pygame.Rect(checkpoint.rect.centerx - 16, checkpoint.rect.bottom - 32, 32, 32),
            {"kind": "scorpion"},
        )
        level = replace(original, objects=[*original.objects, enemy])
        world = build_world(
            level, self.sprites, self.assets, checkpoint_id=checkpoint.object_id
        )
        self.assertFalse(world.player.can_be_hurt)
        self.assertTrue(all(not world.player.rect.colliderect(other.rect) for other in world.enemies))
        for _ in range(120):
            world.player.intent = PlayerIntent()
            world.update(1 / 120, world.bounds)
        self.assertNotEqual(world.player.state, PlayerState.DEAD)

    def test_each_main_route_can_be_crossed_with_normal_jump_holds(self):
        """A missed optional challenge must not make the campaign unwinnable."""
        for number in range(1, 11):
            with self.subTest(level=number):
                world = self.world(number)
                world.enemies = []
                world.view = world.bounds
                hold = 0
                for _frame in range(60 * 70):
                    grounded = world.player.body.on_ground
                    if grounded and hold <= 0:
                        hold = 18  # a normal held jump, not a physics cheat
                    world.player.intent = PlayerIntent(
                        move_axis=1,
                        jump_pressed=grounded and hold == 18,
                        jump_held=hold > 0,
                    )
                    world.update(1 / 60, world.bounds)
                    hold = max(0, hold - 1)
                    if world.player.state in (PlayerState.DEAD, PlayerState.VICTORY):
                        break
                self.assertEqual(world.player.state, PlayerState.VICTORY)


if __name__ == "__main__":
    unittest.main()
