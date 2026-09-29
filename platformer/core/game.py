import math

import pygame

from audio.audio_manager import AudioManager
from core import settings
from core.assets import AssetManager
from core.context import GameContext
from core.input import InputState
from rendering.sprite_library import SpriteLibrary
from scenes.menu_scene import MenuScene
from scenes.scene_manager import SceneManager
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader


class Game:
    """Owns the window, the clock and the main loop.

    Everything game-specific is delegated to the scene stack, so this class
    stays small no matter how big the game gets.
    """

    def __init__(self) -> None:
        pygame.display.set_caption(settings.WINDOW_TITLE)
        self._screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        self._clock = pygame.time.Clock()

        assets = AssetManager(settings.ASSETS_DIR)
        self._scenes = SceneManager()
        self._input = InputState()
        self._debug_overlay = DebugOverlay()
        self._context = GameContext(
            assets=assets,
            audio=AudioManager(assets),
            input=self._input,
            sprites=SpriteLibrary(assets),
            levels=LevelLoader(settings.MAPS_DIR),
            debug=self._debug_overlay,
            scenes=self._scenes,
        )
        self._scenes.push(MenuScene(self._context))

    def run(self) -> None:
        # Reset the clock so time spent loading isn't counted as the first frame.
        self._clock.tick()

        while self._scenes.running:
            frame_time = self._clock.tick(settings.FPS) / 1000.0
            frame_time = min(frame_time, settings.MAX_FRAME_TIME)

            self._handle_events()
            self._update(frame_time)
            self._draw()

    def _handle_events(self) -> None:
        events = pygame.event.get()
        self._input.begin_frame(events)
        for event in events:
            if event.type == pygame.QUIT:
                self._scenes.quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                self._debug_overlay.toggle()
            else:
                self._scenes.handle_event(event)

    def _update(self, frame_time: float) -> None:
        # Split the frame into equal sub-steps no longer than MAX_UPDATE_STEP.
        # Normally that's 2 steps per frame; on a slow frame it's more.
        step_count = max(1, math.ceil(frame_time / settings.MAX_UPDATE_STEP))
        step = frame_time / step_count
        for _ in range(step_count):
            self._scenes.update(step)
            # Key presses are seen by the first sub-step only.
            self._input.end_step()

        self._debug_overlay.update(frame_time, self._clock.get_fps())

    def _draw(self) -> None:
        self._scenes.draw(self._screen)
        top = self._scenes.top
        self._debug_overlay.draw(self._screen, top.debug_lines() if top else [])
        pygame.display.flip()
