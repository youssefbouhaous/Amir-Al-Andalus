import math

import pygame

from audio.audio_manager import AudioManager
from core import settings
from core.assets import AssetManager
from core.context import GameContext
from core.display import Display
from core.input import InputState
from core.save import SaveManager
from rendering.sprite_library import SpriteLibrary
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
        self._save = SaveManager()
        options = self._save.data.options
        # The game draws a fixed 960x540 frame; the display keeps it sharp at any window size.
        self._display = Display(options.fullscreen)
        self._screen = self._display.frame
        self._clock = pygame.time.Clock()

        assets = AssetManager(settings.ASSETS_DIR)
        self._scenes = SceneManager()
        self._input = InputState()
        self._debug_overlay = DebugOverlay()
        self._audio = AudioManager(assets)
        self._audio.set_volumes(options.music_volume, options.sfx_volume)
        self._context = GameContext(
            assets=assets,
            audio=self._audio,
            input=self._input,
            sprites=SpriteLibrary(assets),
            levels=LevelLoader(settings.MAPS_DIR),
            debug=self._debug_overlay,
            scenes=self._scenes,
            save=self._save,
        )
        from scenes.title_scene import TitleScene

        self._scenes.push(TitleScene(self._context))

    def run(self) -> None:
        # Reset the clock so time spent loading isn't counted as the first frame.
        self._clock.tick()

        try:
            while self._scenes.running:
                frame_time = self._clock.tick(settings.FPS) / 1000.0
                frame_time = min(frame_time, settings.MAX_FRAME_TIME)

                self._handle_events()
                self._update(frame_time)
                self._draw()
            self._save.save()
        finally:
            self._display.close()

    def _handle_events(self) -> None:
        events = pygame.event.get()
        self._input.begin_frame(events)
        for event in events:
            if event.type == pygame.QUIT:
                self._scenes.quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                self._debug_overlay.toggle()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            else:
                self._scenes.handle_event(self._display.to_frame(event))

    def toggle_fullscreen(self) -> None:
        options = self._save.data.options
        options.fullscreen = not options.fullscreen
        self._display.toggle_fullscreen()
        self._save.save()

    def _update(self, frame_time: float) -> None:
        # Split the frame into equal sub-steps no longer than MAX_UPDATE_STEP.
        # Normally that's 2 steps per frame; on a slow frame it's more.
        step_count = max(1, math.ceil(frame_time / settings.MAX_UPDATE_STEP))
        step = frame_time / step_count
        for _ in range(step_count):
            self._scenes.update(step)
            # Key presses are seen by the first sub-step only.
            self._input.end_step()

        self._audio.update()
        self._debug_overlay.update(frame_time, self._clock.get_fps())

    def _draw(self) -> None:
        self._scenes.draw(self._screen)
        top = self._scenes.top
        self._debug_overlay.draw(self._screen, top.debug_lines() if top else [])
        self._display.present()
