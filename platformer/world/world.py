"""The live, mutable state of one level attempt.

World owns the entity collections and the update order. It does not know
about score, audio, input devices or scenes: it just simulates and emits
events. Built fresh by ``world_builder.build_world`` on every (re)spawn.
"""

import pygame

from core import settings
from core.events import EventQueue, EventType
from entities.effects import DebrisEffect, Effect
from entities.enemies.enemy import Enemy
from entities.items import Coin, Item
from entities.player import Player
from entities.projectiles import Projectile
from objects.block import Block
from objects.moving_platform import MovingPlatform
from objects.prop import Prop
from objects.switches import SwitchController
from objects.triggers import Checkpoint, Door, Goal
from rendering.camera import Camera
from rendering.placeholder_art import make_debris
from rendering.particles import ParticleSystem
from rendering.sprite_library import SpriteLibrary
from rendering.terrain import TerrainRenderer
from rendering.themes import get_theme
from world.collision_map import CollisionMap, TileCollision
from world import interactions
from world.level_data import LevelData

# Debris pieces fly out as (x direction, relative upward speed).
DEBRIS_PATTERN = ((-1, 1.0), (1, 1.0), (-1, 0.6), (1, 0.6))


class World:
    def __init__(
        self,
        level: LevelData,
        player: Player,
        sprites: SpriteLibrary,
        collision: CollisionMap,
    ) -> None:
        self.level = level
        self.player = player
        self.sprites = sprites
        self.collision = collision
        self.events = EventQueue()
        self.particles = ParticleSystem()
        self.dust_color = get_theme(level.theme).dust
        self.terrain = TerrainRenderer(level)
        self.time = 0.0
        self.view = level.pixel_rect
        self.switch: SwitchController | None = None

        self.enemies: list[Enemy] = []
        self.items: list[Item] = []
        self.projectiles: list[Projectile] = []
        self.effects: list[Effect] = []
        self.props: list[Prop] = []
        self.blocks: dict[tuple[int, int], Block] = {}
        self.platforms: list[MovingPlatform] = []
        self.checkpoints: list[Checkpoint] = []
        self.goals: list[Goal] = []
        self.doors: dict[str, Door] = {}
        self.camera_zones: list[pygame.Rect] = []

        # Set when the player finishes entering a door; the scene handles it.
        self.pending_door: Door | None = None
        self._debris_image = make_debris(settings.BLOCKS.debris_size).convert_alpha()

    @property
    def bounds(self) -> pygame.Rect:
        return self.level.pixel_rect

    # --- Spawning / queries ---------------------------------------------------
    def spawn_item(self, item: Item) -> None:
        self.items.append(item)

    def spawn_effect(self, effect: Effect) -> None:
        self.effects.append(effect)

    def spawn_projectile(self, projectile: Projectile) -> None:
        self.projectiles.append(projectile)

    def count_player_projectiles(self) -> int:
        return sum(projectile.friendly and projectile.alive for projectile in self.projectiles)

    def on_screen(self, rect: pygame.Rect, margin: int = 0) -> bool:
        return rect.colliderect(self.view.inflate(margin * 2, margin * 2))

    def wind_at(self, x: float, y: float) -> float:
        point = pygame.Vector2(x, y)
        return sum(
            getattr(prop, "current", 0.0)
            for prop in self.props
            if prop.__class__.__name__ == "WindZone" and prop.rect.collidepoint(point)
        )

    def anything_overlaps(self, rect: pygame.Rect) -> bool:
        if self.player.rect.colliderect(rect):
            return True
        return any(enemy.alive and enemy.rect.colliderect(rect) for enemy in self.enemies)

    def cells_under_player(self) -> list[tuple[int, int]]:
        body = self.player.body
        return list(self.collision.cells_overlapping(body.left, body.bottom, body.right, body.bottom + 1))

    def camera_bounds_for(self, point: tuple[float, float]) -> pygame.Rect:
        """Camera zones let a bonus room have its own scroll limits."""
        for zone in self.camera_zones:
            if zone.collidepoint(point):
                return zone
        return self.bounds

    # --- Update ---------------------------------------------------------------
    def update(self, dt: float, view: pygame.Rect) -> None:
        self.time += dt
        self.view = pygame.Rect(view)
        if self.switch is not None:
            self.switch.update(dt, self)
        # Platforms move first so anything standing on them sees this step's
        # delta when it moves.
        for platform in self.platforms:
            platform.update(dt)
        for block in self.blocks.values():
            block.update(dt, self)
        for prop in self.props:
            if prop.alive:
                prop.update(dt, self)

        self.player.update(dt, self)

        activation_area = view.inflate(
            settings.ENEMY_ACTIVATION_MARGIN * 2, settings.ENEMY_ACTIVATION_MARGIN * 2
        )
        for enemy in self.enemies:
            if not enemy.activated and enemy.rect.colliderect(activation_area):
                enemy.activated = True
            if enemy.activated:
                enemy.update(dt, self)
        for projectile in self.projectiles:
            if projectile.alive:
                projectile.update(dt, self)
        for item in self.items:
            item.update(dt, self)
        for effect in self.effects:
            effect.update(dt, self)
        self.particles.update(dt)

        interactions.resolve(self)
        self._projectile_collisions()
        self._touch_props()
        self._check_fall_death()
        if self.player.door_entered and self.pending_door is None:
            self.pending_door = self.player.door
        self._remove_dead()

    def _check_fall_death(self) -> None:
        if self.player.body.top > self.collision.pixel_height + settings.FALL_DEATH_MARGIN:
            self.player.die(self, fell=True)

    def _remove_dead(self) -> None:
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.items = [item for item in self.items if item.alive]
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self.props = [prop for prop in self.props if prop.alive]
        self.effects = [effect for effect in self.effects if effect.alive]

    def _projectile_collisions(self) -> None:
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            if projectile.friendly:
                for enemy in self.enemies:
                    if enemy.is_dangerous and projectile.rect.colliderect(enemy.rect):
                        direction = 1 if projectile.body.velocity.x >= 0 else -1
                        if enemy.on_starred(self, direction):
                            projectile.expire(self)
                            break
            elif self.player.is_controllable and projectile.rect.colliderect(self.player.rect):
                projectile.expire(self)
                self.player.take_damage(self)

    def _touch_props(self) -> None:
        if not self.player.is_controllable:
            return
        for prop in self.props:
            if prop.alive and prop.touchable and self.player.rect.colliderect(prop.touch_rect()):
                prop.on_touch(self.player, self)

    # --- Blocks -----------------------------------------------------------------
    def bump_blocks(self, cells: list[tuple[int, int]], player: Player) -> None:
        """The player's head hit these cells; the block nearest their centre reacts."""
        candidates = [cell for cell in cells if cell in self.blocks]
        if not candidates:
            return
        size = self.collision.tile_size
        nearest = min(candidates, key=lambda cell: abs((cell[0] + 0.5) * size - player.body.centerx))
        self.blocks[nearest].hit_from_below(player, self)

    def bump_from_below(self, block_rect: pygame.Rect) -> None:
        """Knock out enemies and collect coins sitting on top of a bumped block."""
        above = pygame.Rect(block_rect.x, block_rect.y - block_rect.height // 2, block_rect.width, block_rect.height // 2)
        for enemy in self.enemies:
            if enemy.is_dangerous and enemy.rect.colliderect(above):
                direction = 1 if enemy.body.centerx >= block_rect.centerx else -1
                enemy.knock_out(self, direction)
        for item in self.items:
            if isinstance(item, Coin) and item.alive and item.rect.colliderect(above):
                item.collect(self.player, self)

    def break_block(self, block: Block) -> None:
        self.blocks.pop(block.cell, None)
        self.collision.set(*block.cell, TileCollision.EMPTY)
        blocks = settings.BLOCKS
        for direction, lift in DEBRIS_PATTERN:
            velocity = (direction * blocks.debris_speed, -blocks.debris_jump_velocity * lift)
            self.spawn_effect(DebrisEffect(block.rect.center, velocity, self._debris_image))
        self.events.emit(EventType.BLOCK_BROKEN, block.rect.midtop)
        self.bump_from_below(block.rect)

    # --- Doors ------------------------------------------------------------------
    def warp_player_to(self, door_name: str) -> bool:
        door = self.doors.get(door_name)
        if door is None:
            return False
        self.player.arrive_at(door.arrival_point)
        self.pending_door = None
        return True

    # --- Draw -------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        self.terrain.draw_back(surface, camera)
        self.particles.draw(surface, camera.offset, front=False)
        for prop in self.props:
            if prop.layer == "back" and prop.rect.colliderect(view):
                prop.draw(surface, camera)
        for checkpoint in self.checkpoints:
            checkpoint.draw(surface, camera)
        for goal in self.goals:
            goal.draw(surface, camera)
        # Items before blocks, so power-ups appear to rise out of the block.
        for item in self.items:
            item.draw(surface, camera)
        for block in self.blocks.values():
            if block.rect.colliderect(view):
                block.draw(surface, camera)
        for platform in self.platforms:
            platform.draw(surface, camera)
        for prop in self.props:
            if prop.layer == "mid" and prop.rect.colliderect(view):
                prop.draw(surface, camera)
        for enemy in self.enemies:
            enemy.draw(surface, camera)
        for projectile in self.projectiles:
            if projectile.rect.colliderect(view):
                projectile.draw(surface, camera)
        self.player.draw(surface, camera)
        for effect in self.effects:
            effect.draw(surface, camera)
        for prop in self.props:
            if prop.layer == "front" and prop.rect.colliderect(view):
                prop.draw(surface, camera)
        self.particles.draw(surface, camera.offset, front=True)
        self.terrain.draw_front(surface, camera)
