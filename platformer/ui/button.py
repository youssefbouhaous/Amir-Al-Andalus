from collections.abc import Callable, Sequence

import pygame

from audio.audio_manager import AudioManager
from core import settings
from core.input import Action, InputState
from ui.text import draw_text


class Button:
    def __init__(self, label: str, rect: pygame.Rect, action: Callable[[], None]) -> None:
        self.label = label
        self.rect = rect
        self.action = action

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: bool) -> None:
        color = settings.BUTTON_HOVER_COLOR if selected else settings.BUTTON_COLOR
        radius = settings.BUTTON_CORNER_RADIUS
        pygame.draw.rect(surface, color, self.rect, border_radius=radius)
        if selected:
            pygame.draw.rect(
                surface,
                settings.BUTTON_BORDER_COLOR,
                self.rect,
                settings.BUTTON_BORDER_WIDTH,
                border_radius=radius,
            )
        draw_text(surface, font, self.label, center=self.rect.center)


class Menu:
    """Vertical list of buttons, usable with keyboard (Up/Down/Enter) or mouse."""

    def __init__(
        self,
        entries: Sequence[tuple[str, Callable[[], None]]],
        center: tuple[int, int],
        audio: AudioManager,
    ) -> None:
        self._audio = audio
        self._selected = 0
        step = settings.BUTTON_HEIGHT + settings.BUTTON_SPACING
        total_height = step * len(entries) - settings.BUTTON_SPACING
        top = center[1] - total_height // 2
        self._buttons = []
        for index, (label, action) in enumerate(entries):
            rect = pygame.Rect(0, 0, settings.BUTTON_WIDTH, settings.BUTTON_HEIGHT)
            rect.midtop = (center[0], top + index * step)
            self._buttons.append(Button(label, rect, action))

    def update(self, input_state: InputState) -> None:
        if input_state.was_pressed(Action.UP):
            self._move(-1)
        elif input_state.was_pressed(Action.DOWN):
            self._move(1)
        elif input_state.was_pressed(Action.CONFIRM):
            self._activate(self._selected)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            for index, button in enumerate(self._buttons):
                if button.rect.collidepoint(event.pos) and index != self._selected:
                    self._selected = index
                    self._audio.play("menu_move")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, button in enumerate(self._buttons):
                if button.rect.collidepoint(event.pos):
                    self._activate(index)
                    return

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for index, button in enumerate(self._buttons):
            button.draw(surface, font, index == self._selected)

    def _move(self, step: int) -> None:
        self._selected = (self._selected + step) % len(self._buttons)
        self._audio.play("menu_move")

    def _activate(self, index: int) -> None:
        self._selected = index
        self._audio.play("menu_select")
        self._buttons[index].action()
