import pygame

from core import settings


class DebugOverlay:
    """Screen-space panel with engine and scene diagnostics, toggled with F1.

    It is drawn after everything else, directly in screen coordinates, so it
    never scrolls with the world. Scenes contribute their own lines.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._font = pygame.font.Font(None, settings.DEBUG_FONT_SIZE)
        self._engine_lines: list[str] = []

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def update(self, frame_time: float, fps: float) -> None:
        if not self.enabled:
            return
        self._engine_lines = [
            f"FPS: {fps:5.1f}",
            f"Frame time: {frame_time * 1000:5.2f} ms",
        ]

    def draw(self, surface: pygame.Surface, scene_lines: list[str]) -> None:
        lines = self._engine_lines + scene_lines
        if not self.enabled or not lines:
            return

        rendered = [
            self._font.render(line, True, settings.DEBUG_TEXT_COLOR) for line in lines
        ]
        padding = settings.DEBUG_PANEL_PADDING
        line_height = self._font.get_linesize()
        panel_width = max(text.get_width() for text in rendered) + 2 * padding
        panel_height = line_height * len(rendered) + 2 * padding

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill(settings.DEBUG_PANEL_COLOR)
        for index, text in enumerate(rendered):
            panel.blit(text, (padding, padding + index * line_height))

        margin = settings.DEBUG_PANEL_MARGIN
        # Below the HUD row so both stay readable.
        surface.blit(panel, (margin, margin + settings.HUD_FONT_SIZE + margin))
