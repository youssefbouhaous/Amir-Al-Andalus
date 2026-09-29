"""Gameplay scene: glues the World to input, camera, HUD, audio and session.

The World simulates; this scene decides what the results *mean* for the
game as a whole: turning events into score and sounds, deaths into lives and
respawns, doors into warps, the goal into the next level.
"""

import logging
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.events import EventType
from core.input import Action
from core.session import GameSession
from entities.effects import ScorePopup
from entities.player import PlayerState
from entities.player_controller import PlayerController
from objects.triggers import Door
from rendering.background import ParallaxBackground
from rendering.camera import Camera
from rendering.fade import ScreenFade
from scenes.scene import Scene
from ui.hud import Hud
from ui.text import render_text
from world.collision_map import TileCollision
from world.level_data import LevelData
from world.level_loader import LevelLoadError
from world.world import World
from world.world_builder import build_world

if TYPE_CHECKING:
    from core.context import GameContext

logger = logging.getLogger(__name__)

# Coins are too frequent for popups to be useful; the HUD shows them instead.
EVENTS_WITHOUT_POPUP = frozenset({EventType.COIN_COLLECTED})
DEBUG_OUTLINE_WIDTH = 1


class GameScene(Scene):
    def __init__(
        self,
        context: "GameContext",
        session: GameSession,
        level: LevelData,
        spawn_door: str | None = None,
    ) -> None:
        super().__init__(context)
        self._session = session
        self._level = level
        screen_size = (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        self._controller = PlayerController(context.input)
        self._hud = Hud(context.assets)
        self._popup_font = context.assets.get_font(settings.POPUP_FONT_SIZE)
        self._fade = ScreenFade(screen_size)
        self._background = ParallaxBackground(
            screen_size, level.theme, level.pixel_rect.height
        )
        self._world = self._build_world(spawn_door)
        self._camera = Camera(screen_size, self._world.bounds)
        self._snap_camera()
        self._level_finished = False
        self._fade.fade_in()

    # --- Scene lifecycle ------------------------------------------------------
    def on_enter(self) -> None:
        self.context.audio.play_music(self._level.music)

    def on_resume(self) -> None:
        self.context.audio.resume_music()

    def restart_from_checkpoint(self) -> None:
        self._world = self._build_world()
        self._snap_camera()
        self._fade.fade_in()

    # --- Update -----------------------------------------------------------------
    def update(self, dt: float) -> None:
        input_state = self.context.input
        if input_state.was_pressed(Action.PAUSE) and not self._fade.active:
            self._open_pause_menu()
            return
        if input_state.was_pressed(Action.RELOAD_LEVEL):
            self._reload_level_file()
            return

        self._fade.update(dt)
        if self._fade.is_fading_out:
            return  # Freeze the world while the screen goes black.

        self._world.player.intent = self._controller.read()
        self._world.update(dt, self._camera.view_rect)
        self._process_events()
        self._check_outcomes()
        self._update_camera(dt)

    def _open_pause_menu(self) -> None:
        from scenes.pause_scene import PauseScene

        self.context.audio.pause_music()
        self.context.audio.play("pause")
        self.context.scenes.push(PauseScene(self.context, self))

    def _process_events(self) -> None:
        for event in self._world.events.drain():
            points = self._session.apply_event(event)
            self.context.audio.play_for_event(event)
            if points and event.type not in EVENTS_WITHOUT_POPUP:
                text = render_text(self._popup_font, str(points))
                self._world.spawn_effect(ScorePopup(event.position, text))

    def _check_outcomes(self) -> None:
        player = self._world.player
        if player.death_finished:
            self._fade.fade_out_then(self._after_death)
        elif player.victory_finished and not self._level_finished:
            self._level_finished = True
            self._finish_level()
        elif self._world.pending_door is not None:
            door = self._world.pending_door
            self._world.pending_door = None
            self._fade.fade_out_then(lambda: self._use_door(door))

    def _update_camera(self, dt: float) -> None:
        player = self._world.player
        if player.state == PlayerState.DEAD:
            return  # Keep the camera still while the player falls off screen.
        center = (player.body.centerx, player.body.centery)
        self._camera.set_bounds(self._world.camera_bounds_for(center))
        self._camera.follow(center, dt)

    # --- Outcomes ---------------------------------------------------------------
    def _after_death(self) -> None:
        self._session.lose_life()
        if self._session.is_game_over:
            from scenes.end_scenes import GameOverScene

            self.context.scenes.replace(GameOverScene(self.context, self._session))
            return
        self._world = self._build_world()
        self._snap_camera()

    def _finish_level(self) -> None:
        from scenes.end_scenes import LevelCompleteScene

        self.context.scenes.replace(LevelCompleteScene(self.context, self._session, self._level))

    def _use_door(self, door: Door) -> None:
        if door.target_level:
            try:
                level = self.context.levels.load(door.target_level)
            except LevelLoadError as error:
                logger.error("%s", error)
                self._world.player.arrive_at(door.arrival_point)
                return
            self._session.enter_level(door.target_level)
            self._session.level_name = level.name
            self._level = level
            self._background = ParallaxBackground(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                level.theme,
                level.pixel_rect.height,
            )
            self._world = self._build_world(door.target_door)
            self.context.audio.play_music(level.music)
        elif not door.target_door or not self._world.warp_player_to(door.target_door):
            logger.warning("Door %r has no valid target %r", door.name, door.target_door)
            self._world.player.arrive_at(door.arrival_point)
        self._snap_camera()

    def _reload_level_file(self) -> None:
        """F5: re-read the .tmx from disk. Handy while editing in Tiled."""
        levels = self.context.levels
        levels.invalidate(self._level.file_name)
        try:
            self._level = levels.load(self._level.file_name)
        except LevelLoadError as error:
            logger.error("Reload failed, keeping current level: %s", error)
            return
        logger.info("Reloaded %s", self._level.file_name)
        self._session.level_name = self._level.name
        self.restart_from_checkpoint()

    # --- Helpers --------------------------------------------------------------
    def _build_world(self, spawn_door: str | None = None) -> World:
        return build_world(
            self._level,
            self.context.sprites,
            self.context.assets,
            player_powered=self._session.player_powered,
            checkpoint_id=self._session.checkpoint_id,
            spawn_door=spawn_door,
        )

    def _snap_camera(self) -> None:
        player = self._world.player
        center = (player.body.centerx, player.body.centery)
        self._camera.set_bounds(self._world.camera_bounds_for(center))
        self._camera.snap_to(center)

    # --- Draw -------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._background.draw(surface, self._camera)
        self._world.draw(surface, self._camera)
        if self.context.debug.enabled:
            self._draw_debug_shapes(surface)
        self._hud.draw(surface, self._session, self._world.player.powered)
        self._fade.draw(surface)

    def _draw_debug_shapes(self, surface: pygame.Surface) -> None:
        camera = self._camera
        world = self._world
        collision = world.collision
        size = collision.tile_size
        view = camera.view_rect

        for tx, ty, kind in collision.cells_overlapping(view.left, view.top, view.right, view.bottom):
            if not (0 <= tx < collision.width):
                continue
            color = (
                settings.DEBUG_ONE_WAY_COLOR
                if kind == TileCollision.ONE_WAY
                else settings.DEBUG_TILE_COLOR
            )
            rect = camera.apply(pygame.Rect(tx * size, ty * size, size, size))
            pygame.draw.rect(surface, color, rect, DEBUG_OUTLINE_WIDTH)

        def outline(rect: pygame.Rect, color: settings.Color) -> None:
            pygame.draw.rect(surface, color, camera.apply(rect), DEBUG_OUTLINE_WIDTH)

        for enemy in world.enemies:
            outline(enemy.rect, settings.DEBUG_ENTITY_COLOR)
        for item in world.items:
            outline(item.rect, settings.DEBUG_ENTITY_COLOR)
        for platform in world.platforms:
            outline(platform.rect, settings.DEBUG_ONE_WAY_COLOR)
        triggers = [c.rect for c in world.checkpoints] + [g.rect for g in world.goals]
        triggers += [d.rect for d in world.doors.values()]
        for rect in triggers:
            outline(rect, settings.DEBUG_TRIGGER_COLOR)
        outline(world.player.rect, settings.DEBUG_PLAYER_COLOR)
        outline(camera.dead_zone(), settings.DEBUG_DEAD_ZONE_COLOR)

    def debug_lines(self) -> list[str]:
        player = self._world.player
        body = player.body
        camera = self._camera.position
        return [
            f"Player pos: ({body.x:7.1f}, {body.y:7.1f})",
            f"Velocity:   ({body.velocity.x:7.1f}, {body.velocity.y:7.1f})",
            f"State: {player.state.name}   powered: {player.powered}",
            f"Grounded: {body.on_ground}   ceiling: {body.hit_ceiling}   wall: {body.hit_wall}",
            f"On platform: {body.ground_platform is not None}",
            f"Camera: ({camera.x:7.1f}, {camera.y:7.1f})",
            f"Enemies: {len(self._world.enemies)}  items: {len(self._world.items)}"
            f"  effects: {len(self._world.effects)}",
            f"Level: {self._level.file_name}  checkpoint: {self._session.checkpoint_id}",
        ]
