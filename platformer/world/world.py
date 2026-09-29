"""The live, mutable state of one level attempt.

World owns the entity collections and the update order. It does not know
about score, audio, input devices or scenes: it just simulates and emits
events. Built fresh by ``world_builder.build_world`` on every (re)spawn.
"""

from typing import TYPE_CHECKING

import pygame

from core import settings
from core.events import EventQueue, EventType
from entities.effects import DebrisEffect, Effect
from entities.enemies.enemy import Enemy
from entities.items import Coin, Item
from entities.player import Player
from entities.projectiles import Projectile
from objects.block import Block
from objects.hazards import WindZone
from objects.platforms import Platform
from objects.prop import Prop
from objects.switches import SwitchController
from objects.triggers import Checkpoint, Door, Goal
from rendering.art.tiles import make_debris
from rendering.camera import Camera
from rendering.lighting import Light
from rendering.particles import ParticleSystem
from rendering.sprite_library import SpriteLibrary
from rendering.terrain import TerrainRenderer
from rendering.themes import get_theme
from world import interactions
from world.collision_map import CollisionMap, TileCollision
from world.level_data import LevelData

if TYPE_CHECKING:
    from entities.boss import Ifrit

# Debris pieces fly out as (x direction, relative upward speed).
DEBRIS_PATTERN = ((-1, 1.0), (1, 1.0), (-1, 0.6), (1, 0.6))
# Lights further than this outside the view are skipped.
LIGHT_MARGIN = 220


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
        self.theme = get_theme(level.theme)
        self.dust_color = self.theme.dust
        self.terrain = TerrainRenderer(level)
        self.time = 0.0
        self.view = level.pixel_rect
        self.switch: SwitchController | None = None
        self.boss: "Ifrit | None" = None

        self.enemies: list[Enemy] = []
        self.items: list[Item] = []
        self.projectiles: list[Projectile] = []
        self.effects: list[Effect] = []
        self.props: list[Prop] = []
        self.blocks: dict[tuple[int, int], Block] = {}
        self.platforms: list[Platform] = []
        self.checkpoints: list[Checkpoint] = []
        self.goals: list[Goal] = []
        self.doors: dict[str, Door] = {}
        self.camera_zones: list[pygame.Rect] = []
        self.wind_zones: list[WindZone] = []

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

    def spawn_enemy(self, enemy: Enemy) -> None:
        enemy.activated = True
        self.enemies.append(enemy)

    def count_player_projectiles(self) -> int:
        return sum(projectile.friendly and projectile.alive for projectile in self.projectiles)

    def on_screen(self, rect: pygame.Rect, margin: int = 0) -> bool:
        return rect.colliderect(self.view.inflate(margin * 2, margin * 2))

    def wind_at(self, x: float, y: float) -> float:
        return sum(zone.current for zone in self.wind_zones if zone.rect.collidepoint(x, y))

    def anything_overlaps(self, rect: pygame.Rect) -> bool:
        if self.player.rect.colliderect(rect):
            return True
        return any(enemy.alive and enemy.rect.colliderect(rect) for enemy in self.enemies)

    def cells_under_player(self) -> list[tuple[int, int]]:
        body = self.player.body
        if not body.on_ground:
            return []
        return [
            (tx, ty)
            for tx, ty, _kind in self.collision.cells_overlapping(body.left, body.bottom, body.right, body.bottom + 1)
        ]

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
            platform.update(dt, self)
        for block in self.blocks.values():
            block.update(dt, self)
        for prop in self.props:
            if prop.alive:
                prop.update(dt, self)
        for checkpoint in self.checkpoints:
            checkpoint.update(dt, self)
        for goal in self.goals:
            goal.update(dt, self)

        self.player.update(dt, self)

        activation_area = view.inflate(
            settings.ENEMY_ACTIVATION_MARGIN * 2, settings.ENEMY_ACTIVATION_MARGIN * 2
        )
        for enemy in self.enemies:
            if not enemy.activated and enemy.rect.colliderect(activation_area):
                enemy.activated = True
            if enemy.activated:
                enemy.update(dt, self)
        if self.boss is not None:
            self.boss.update(dt, self)
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
        player = self.player
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            if projectile.friendly:
                direction = 1 if projectile.body.velocity.x >= 0 else -1
                if self.boss is not None and self.boss.hit_by_star(projectile.rect, self, direction):
                    projectile.expire(self)
                    continue
                for enemy in self.enemies:
                    if enemy.is_dangerous and projectile.rect.colliderect(enemy.rect):
                        if enemy.on_starred(self, direction):
                            projectile.expire(self)
                            break
            elif player.can_be_hurt and projectile.rect.colliderect(player.rect.inflate(-4, -4)):
                projectile.expire(self)
                player.take_damage(self)

    def _touch_props(self) -> None:
        if not self.player.is_controllable:
            return
        player_rect = self.player.rect
        for prop in self.props:
            if prop.alive and prop.touchable and player_rect.colliderect(prop.touch_rect()):
                prop.on_touch(self.player, self)
                if not self.player.is_controllable:
                    return

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
            if enemy.is_dangerous and enemy.bumpable and enemy.rect.colliderect(above):
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
        self.player.emerge_from(door)
        self.pending_door = None
        return True

    # --- Lights -----------------------------------------------------------------
    def lights(self) -> list[Light]:
        """Every light source near the view, for the night lighting pass."""
        area = self.view.inflate(LIGHT_MARGIN * 2, LIGHT_MARGIN * 2)
        sources: list[Light] = []
        sources += self.player.lights()
        for group in (self.props, self.platforms, self.checkpoints, self.goals):
            for thing in group:
                sources += thing.lights()
        for group in (self.items, self.enemies, self.projectiles):
            for entity in group:
                if entity.rect.colliderect(area):
                    sources += entity.lights()
        if self.boss is not None:
            sources += self.boss.lights()
        return [light for light in sources if area.collidepoint(light.x, light.y)]

    # --- Draw -------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view = camera.view_rect
        self.terrain.draw_back(surface, camera)
        self.particles.draw(surface, camera.offset, front=False)
        for prop in self.props:
            if prop.layer == "back" and prop.rect.colliderect(view):
                prop.draw(surface, camera)
        for checkpoint in self.checkpoints:
            if checkpoint.rect.colliderect(view.inflate(64, 64)):
                checkpoint.draw(surface, camera)
        for goal in self.goals:
            goal.draw(surface, camera)
        if self.boss is not None:
            self.boss.draw_back(surface, camera)
        # Items before blocks, so power-ups appear to rise out of the block.
        for item in self.items:
            if item.rect.colliderect(view):
                item.draw(surface, camera)
        for block in self.blocks.values():
            if block.rect.colliderect(view):
                block.draw(surface, camera)
        for platform in self.platforms:
            if platform.rect.colliderect(view.inflate(160, 160)):
                platform.draw(surface, camera)
        for prop in self.props:
            if prop.layer == "mid" and prop.rect.colliderect(view):
                prop.draw(surface, camera)
        for enemy in self.enemies:
            if enemy.rect.colliderect(view.inflate(64, 64)):
                enemy.draw(surface, camera)
        if self.boss is not None:
            self.boss.draw(surface, camera)
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

    def draw_overlays(self, surface: pygame.Surface, camera: Camera) -> None:
        """Things drawn after lighting so they stay readable (sign bubbles)."""
        for prop in self.props:
            draw_overlay = getattr(prop, "draw_overlay", None)
            if draw_overlay is not None:
                draw_overlay(surface, camera)
