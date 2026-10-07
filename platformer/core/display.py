"""The window: the game draws a fixed 960x540 frame; this shows it sharp at any window size.

pygame's SCALED mode stretches that frame to the window in one step with
nearest-neighbour sampling. At a fractional scale - a maximised window on a
1080p screen is about 1.87x - some rows and columns of pixels get doubled and
others don't, so lines wobble, text breaks up and the picture shimmers as the
camera scrolls.

On a GPU renderer the frame is shown the "sharp bilinear" way emulators use
instead, through pygame's own renderer:

1. it is enlarged by the next whole number (2x for a maximised 1080p window)
   with nearest neighbour into a texture, so every pixel stays an even square;
2. that texture is fitted to the window with smooth filtering, letterboxed at
   16:9. It is already at least the window's size, so the smoothing only
   softens the seams between the squares instead of blurring the picture.

At an exact multiple (the 960x540 window, 1920x1080 fullscreen) it is
pixel-perfect. The window itself is still pygame's SCALED window - same size,
minimum size, vsync and F11 toggle as before - and on a software renderer
pygame shows the frame itself, as it always did.
"""

import math
import os

import pygame

from core import settings

FRAME = (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
MAX_FACTOR = 4          # 3840x2160 covers a 4K screen; anything bigger is smoothed the rest of the way

_MOUSE_EVENTS = (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
_RENDERER_SOFTWARE = 0x1
_RENDERER_TARGETTEXTURE = 0x8
_BLEND_NONE = 0
# pygame tags every event with the Window wrapper made for its window, without holding a reference
# to it: a wrapper that is freed while the window lives leaves a dangling pointer behind (a crash
# at exit). The wrappers are kept here for the life of the program.
_window_wrappers = []


class Display:
    def __init__(self, fullscreen: bool) -> None:
        flags = pygame.SCALED | pygame.RESIZABLE
        if fullscreen:
            flags |= pygame.FULLSCREEN
        try:
            self.frame = pygame.display.set_mode(FRAME, flags, vsync=1)
        except pygame.error:
            self.frame = pygame.display.set_mode(FRAME, flags)
        self._sharp = SharpPresenter.create(self.frame)

    @property
    def sharp(self) -> bool:
        return self._sharp is not None

    def present(self) -> None:
        if self._sharp is not None:
            try:
                self._sharp.present(self.frame)
                return
            except pygame.error:
                self.close()  # The GPU path failed: pygame shows the frames from now on.
        pygame.display.flip()

    def to_frame(self, event: pygame.event.Event) -> pygame.event.Event:
        """With the picture placed by hand, mouse positions arrive in window pixels."""
        if self._sharp is None or event.type not in _MOUSE_EVENTS:
            return event
        view = self._sharp.view
        data = dict(event.dict)
        data["pos"] = frame_point(view, event.pos)
        if "rel" in data:
            data["rel"] = (round(event.rel[0] * FRAME[0] / view.width),
                           round(event.rel[1] * FRAME[1] / view.height))
        return pygame.event.Event(event.type, data)

    @staticmethod
    def toggle_fullscreen() -> None:
        pygame.display.toggle_fullscreen()

    def close(self) -> None:
        """Free the GPU textures while their renderer still exists (before pygame.quit)."""
        if self._sharp is not None:
            self._sharp.release()
            self._sharp = None


class SharpPresenter:
    """Shows the frame through pygame's renderer in two GPU passes (see the module docstring)."""

    @classmethod
    def create(cls, frame: pygame.Surface) -> "SharpPresenter | None":
        try:
            info = pygame.display._get_renderer_info()
            if info is None or info[1] & _RENDERER_SOFTWARE or not info[1] & _RENDERER_TARGETTEXTURE:
                return None
            from pygame._sdl2.video import Renderer, Texture, Window

            window = Window.from_display_module()
            _window_wrappers.append(window)
            return cls(Renderer.from_window(window), Texture, frame)
        except (ImportError, AttributeError, pygame.error):
            return None

    def __init__(self, renderer, texture_type, frame: pygame.Surface) -> None:
        self._renderer = renderer
        self._texture_type = texture_type
        self._small = _with_filter("nearest", lambda: texture_type.from_surface(renderer, frame))
        self._small.blend_mode = _BLEND_NONE
        self._big = None
        self._factor = 0
        self.view = pygame.Rect((0, 0), FRAME)    # where the frame sits in the window, in pixels

    def present(self, frame: pygame.Surface) -> None:
        renderer = self._renderer
        if renderer.logical_size != (0, 0):
            renderer.logical_size = (0, 0)        # we place the picture; pygame sets this again on F11
        renderer.set_viewport(None)
        output = renderer.get_viewport().size
        if min(output) < 1:
            return                                # minimised
        self.view = fit_view(output)
        factor = enlargement(self.view)
        if factor != self._factor:
            size = (FRAME[0] * factor, FRAME[1] * factor)
            self._big = _with_filter("linear", lambda: self._texture_type(renderer, size, target=True))
            self._big.blend_mode = _BLEND_NONE
            self._factor = factor

        self._small.update(frame)
        renderer.target = self._big
        self._small.draw(None, self._big.get_rect())
        renderer.target = None
        renderer.draw_color = (0, 0, 0, 255)
        renderer.clear()
        self._big.draw(None, self.view)
        renderer.present()

    def release(self) -> None:
        self._small = self._big = None
        self._factor = 0
        try:
            self._renderer.logical_size = FRAME   # pygame letterboxes its own frames again
        except pygame.error:
            pass


def fit_view(output: tuple[int, int]) -> pygame.Rect:
    """The largest 16:9 rectangle centred in the window (letterboxed)."""
    width, height = output
    scale = min(width / FRAME[0], height / FRAME[1])
    view = pygame.Rect(0, 0, max(1, round(FRAME[0] * scale)), max(1, round(FRAME[1] * scale)))
    view.center = (width // 2, height // 2)
    return view


def enlargement(view: pygame.Rect) -> int:
    """The whole-number pre-scale: the smallest one that reaches the window size."""
    scale = max(view.width / FRAME[0], view.height / FRAME[1])
    return max(1, min(MAX_FACTOR, math.ceil(scale - 1e-6)))


def frame_point(view: pygame.Rect, pos: tuple[int, int]) -> tuple[int, int]:
    """A window pixel to the frame pixel shown there (outside the picture it runs past the edges)."""
    return ((pos[0] - view.x) * FRAME[0] // view.width, (pos[1] - view.y) * FRAME[1] // view.height)


def _with_filter(quality: str, make):
    """SDL fixes a texture's filtering when it is made, from this hint; the environment variable
    of the same name wins over pygame's own setting."""
    key = "SDL_RENDER_SCALE_QUALITY"
    saved = os.environ.get(key)
    os.environ[key] = quality
    try:
        return make()
    finally:
        if saved is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = saved
