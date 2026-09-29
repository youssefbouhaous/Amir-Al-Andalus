"""Gameplay scene: glues the World to input, camera, HUD, audio and session.

The World simulates; this scene decides what the results *mean* for the
game as a whole: turning events into score, sounds and screen shake, deaths
into lives and respawns, doors into warps, the goal into the level tally.
It also owns the presentation layers that sit around the world: parallax
sky, weather, night lighting and the transitions that hide every cut.
"""

import logging
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.events import EventType, GameEvent
from core.input import Action
from core.session import GameSession
from entities.effects import ScorePopup
from entities.player import PlayerState
from entities.player_controller import PlayerController
from objects.triggers import Door
from rendering.background import ParallaxBackground
from rendering.camera import Camera
from rendering.lighting import LightLayer
from rendering.shake import ScreenShake
from rendering.transitions import IrisWipe, StarWipe, Transition
from rendering.weather import Weather
from scenes.scene import Scene
from ui.hud import Hud
from ui.text import TextStyle, render_styled
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
POPUP_STYLE = TextStyle(gradient=((255, 250, 220), (255, 196, 80)), outline=(60, 30, 20), outline_width=2, shadow=None)
BIG_POPUP_STYLE = TextStyle(gradient=((255, 255, 255), (150, 210, 255)), outline=(20, 30, 70), outline_width=2, shadow=None)
DEBUG_OUTLINE_WIDTH = 1

# Screen shake (trauma) and hit-stop (seconds) for impactful events.
SHAKE: dict[EventType, float] = {
    EventType.ENEMY_STOMPED: 0.18,
    EventType.BLOCK_BROKEN: 0.22,
    EventType.PLAYER_HURT: 0.45,
    EventType.PLAYER_DIED: 0.5,
    EventType.ENEMY_KNOCKED_OUT: 0.15,
    EventType.SPRING_BOUNCED: 0.12,
    EventType.PLATFORM_CRUMBLED: 0.12,
    EventType.BOSS_SLAM: 0.6,
    EventType.BOSS_HIT: 0.5,
    EventType.BOSS_DEFEATED: 1.0,
    EventType.BOSS_ROAR: 0.35,
}
HITSTOP: dict[EventType, float] = {
    EventType.ENEMY_STOMPED: settings.JUICE.hitstop_stomp,
    EventType.PLAYER_HURT: settings.JUICE.hitstop_hurt,
    EventType.BOSS_HIT: settings.JUICE.hitstop_boss,
    EventType.BOSS_DEFEATED: 0.4,
}
# Events that interrupt the music with a short jingle.
DEATH_MUSIC_FADE_MS = 400


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
        self._screen_size = (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        self._controller = PlayerController(context.input)
        self._hud = Hud(context.assets, context.save.data.options.show_timer)
        self._popup_font = context.assets.get_font(settings.POPUP_FONT_SIZE, "ui")
        self._wipe: Transition = StarWipe(self._screen_size)
        self._iris = IrisWipe(self._screen_size, duration=0.7)
        self._transition: Transition = self._wipe
        self._shake = ScreenShake()
        self._shake.enabled = context.save.data.options.screen_shake
        self._lighting = LightLayer(self._screen_size)
        self._hitstop = 0.0
        self._level_finished = False
        self._set_level_visuals(level)
        self._world = self._build_world(spawn_door)
        self._camera = Camera(self._screen_size, self._world.bounds)
        self._snap_camera()
        self._transition.fade_in()

    def _set_level_visuals(self, level: LevelData) -> None:
        self._background = ParallaxBackground(self._screen_size, level.theme, level.pixel_rect.height)
        theme = self._background.theme
        self._weather = Weather(theme.weather, self._screen_size, seed=len(level.file_name)) if theme.weather else None
        self._ambient = theme.light
        self._hud.set_level(level)

    # --- Scene lifecycle ------------------------------------------------------
    def on_enter(self) -> None:
        self.context.audio.play_music(self._level.music or self._background.theme.music)

    def on_resume(self) -> None:
        self.context.audio.resume_music()
        self._shake.enabled = self.context.save.data.options.screen_shake
        self._hud.show_timer = self.context.save.data.options.show_timer

    def restart_from_checkpoint(self) -> None:
        self._world = self._build_world()
        self._snap_camera()
        self._transition = self._wipe
        self._transition.fade_in()

    # --- Update -----------------------------------------------------------------
    def update(self, dt: float) -> None:
        input_state = self.context.input
        if input_state.was_pressed(Action.PAUSE) and not self._transition.active:
            self._open_pause_menu()
            return
        if input_state.was_pressed(Action.RELOAD_LEVEL):
            self._reload_level_file()
            return

        self._transition.update(dt)
        self._background.update(dt)
        if self._weather is not None:
            self._weather.wind = self._world.wind_at(self._world.player.body.centerx, self._world.player.body.centery)
            self._weather.update(dt)
        self._shake.update(dt)
        self._hud.update(dt, self._session)
        if self._transition.is_fading_out:
            return  # Freeze the world while the screen is covered.

        if self._hitstop > 0:
            self._hitstop = max(0.0, self._hitstop - dt)
            return

        player = self._world.player
        player.intent = self._controller.read()
        self._world.update(dt, self._camera.view_rect)
        if player.is_controllable:
            self._session.level_time += dt
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
            self._shake.add(SHAKE.get(event.type, 0.0))
            self._hitstop = max(self._hitstop, HITSTOP.get(event.type, 0.0))
            self._react(event)
            if points and event.type not in EVENTS_WITHOUT_POPUP:
                style = BIG_POPUP_STYLE if points >= 1000 else POPUP_STYLE
                text = render_styled(self._popup_font, str(points), style)
                self._world.spawn_effect(ScorePopup(event.position, text))
            if event.type == EventType.ENEMY_STOMPED and isinstance(event.value, int) and event.value > 7:
                text = render_styled(self._popup_font, "1UP", BIG_POPUP_STYLE)
                self._world.spawn_effect(ScorePopup(event.position, text))

    def _react(self, event: GameEvent) -> None:
        match event.type:
            case EventType.PAGE_COLLECTED:
                self._hud.flash_pages()
            case EventType.PLAYER_DIED:
                self.context.audio.fade_music(DEATH_MUSIC_FADE_MS)
            case EventType.LEVEL_COMPLETED:
                self.context.audio.fade_music(DEATH_MUSIC_FADE_MS)
            case EventType.CHECKPOINT_REACHED:
                self._hud.toast("Lantern lit")

    def _check_outcomes(self) -> None:
        player = self._world.player
        if player.death_finished:
            self._iris.focus = self._camera.to_screen(player.body.centerx, min(player.body.centery, self._camera.view_rect.bottom))
            self._transition = self._iris
            self._transition.fade_out_then(self._after_death)
        elif player.victory_finished and not self._level_finished:
            self._level_finished = True
            self._transition = self._wipe
            self._transition.fade_out_then(self._finish_level)
        elif self._world.pending_door is not None:
            door = self._world.pending_door
            self._world.pending_door = None
            self._transition = self._wipe
            self._transition.fade_out_then(lambda: self._use_door(door))

    def _update_camera(self, dt: float) -> None:
        player = self._world.player
        self._camera.shake = self._shake.offset
        if player.state == PlayerState.DEAD:
            return  # Keep the camera still while the player falls off screen.
        center = (player.body.centerx, player.body.centery)
        boss = self._world.boss
        if boss is not None and boss.camera_focus is not None:
            self._camera.set_bounds(boss.arena)
            self._camera.pan_to(boss.camera_focus, dt)
            return
        self._camera.set_bounds(self._world.camera_bounds_for(center))
        running = abs(player.body.velocity.x) > 60
        self._camera.follow(center, dt, player.facing if running else 0)

    # --- Outcomes ---------------------------------------------------------------
    def _after_death(self) -> None:
        self._session.lose_life()
        save = self.context.save
        save.data.total_deaths += 1
        save.save()
        if self._session.is_game_over:
            from scenes.end_scenes import GameOverScene

            self.context.scenes.replace(GameOverScene(self.context, self._session))
            return
        self._world = self._build_world()
        self._snap_camera()
        self.context.audio.play_music(self._level.music or self._background.theme.music, restart=True)

    def _finish_level(self) -> None:
        from scenes.tally_scene import TallyScene

        self.context.scenes.replace(TallyScene(self.context, self._session, self._level))

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
            self._set_level_visuals(level)
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
        self._set_level_visuals(self._level)
        self.restart_from_checkpoint()

    # --- Helpers --------------------------------------------------------------
    def _build_world(self, spawn_door: str | None = None) -> World:
        record = self.context.save.data.levels.get(self._level.file_name)
        found = set(record.pages) if record is not None else set()
        self._hud.known_pages = found
        return build_world(
            self._level,
            self.context.sprites,
            self.context.assets,
            power=self._session.power,
            checkpoint_id=self._session.checkpoint_id,
            spawn_door=spawn_door,
            found_pages=found | self._session.pages_found,
        )

    def _snap_camera(self) -> None:
        player = self._world.player
        center = (player.body.centerx, player.body.centery)
        self._camera.set_bounds(self._world.camera_bounds_for(center))
        self._camera.snap_to(center)

    @property
    def world(self) -> World:
        return self._world

    @property
    def session(self) -> GameSession:
        return self._session

    # --- Draw -------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._background.draw(surface, self._camera)
        offset = self._camera.offset
        if self._weather is not None:
            self._weather.draw(surface, offset, front=False)
        self._world.draw(surface, self._camera)
        if self._weather is not None:
            self._weather.draw(surface, offset, front=True)
        if self._ambient is not None:
            self._lighting.begin(self._ambient)
            for light in self._world.lights():
                self._lighting.add(light, offset, self._world.time)
            self._lighting.apply(surface)
        self._world.draw_overlays(surface, self._camera)
        if self.context.debug.enabled:
            self._draw_debug_shapes(surface)
        self._hud.draw(surface, self._session, self._world)
        self._transition.draw(surface)

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
        for prop in world.props:
            if prop.touchable:
                outline(prop.touch_rect(), settings.DEBUG_TRIGGER_COLOR)
        triggers = [c.rect for c in world.checkpoints] + [g.rect for g in world.goals]
        triggers += [d.rect for d in world.doors.values()]
        for rect in triggers:
            outline(rect, settings.DEBUG_TRIGGER_COLOR)
        if world.boss is not None:
            for rect in world.boss.debug_rects():
                outline(rect, settings.DEBUG_ENTITY_COLOR)
        outline(world.player.rect, settings.DEBUG_PLAYER_COLOR)
        outline(camera.dead_zone(), settings.DEBUG_DEAD_ZONE_COLOR)

    def debug_lines(self) -> list[str]:
        player = self._world.player
        body = player.body
        camera = self._camera.position
        return [
            f"Player pos: ({body.x:7.1f}, {body.y:7.1f})  tile ({int(body.centerx // 32)}, {int(body.bottom // 32)})",
            f"Velocity:   ({body.velocity.x:7.1f}, {body.velocity.y:7.1f})",
            f"State: {player.state.name}   power: {player.power.name}",
            f"Grounded: {body.on_ground}   ceiling: {body.hit_ceiling}   wall: {body.hit_wall}",
            f"On platform: {body.ground_platform is not None}",
            f"Camera: ({camera.x:7.1f}, {camera.y:7.1f})",
            f"Enemies: {len(self._world.enemies)}  items: {len(self._world.items)}"
            f"  effects: {len(self._world.effects)}  particles: {len(self._world.particles)}",
            f"Level: {self._level.file_name}  checkpoint: {self._session.checkpoint_id}",
        ]
