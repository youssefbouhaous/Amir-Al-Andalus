"""Keyboard and gamepad input mapped to abstract actions.

Gameplay code asks "is JUMP held?" instead of "is K_SPACE held?", so key
bindings live in one place. Gamepads are polled every frame (buttons, D-pad
and left stick) and merged with the keyboard, so both work at the same time
and a pad can be plugged in while the game runs.
"""

from collections.abc import Iterable, Mapping
from enum import Enum, auto
from typing import Final

import pygame


class Action(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    JUMP = auto()
    ATTACK = auto()
    PAUSE = auto()
    CONFIRM = auto()
    BACK = auto()
    RELOAD_LEVEL = auto()


DEFAULT_BINDINGS: Final[Mapping[Action, tuple[int, ...]]] = {
    Action.LEFT: (pygame.K_a, pygame.K_LEFT),
    Action.RIGHT: (pygame.K_d, pygame.K_RIGHT),
    Action.UP: (pygame.K_w, pygame.K_UP),
    Action.DOWN: (pygame.K_s, pygame.K_DOWN),
    Action.JUMP: (pygame.K_SPACE, pygame.K_z, pygame.K_k),
    Action.ATTACK: (pygame.K_x, pygame.K_j, pygame.K_LSHIFT, pygame.K_RSHIFT),
    Action.PAUSE: (pygame.K_ESCAPE, pygame.K_p),
    Action.CONFIRM: (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z),
    Action.BACK: (pygame.K_ESCAPE, pygame.K_BACKSPACE),
    Action.RELOAD_LEVEL: (pygame.K_F5,),
}

# Common (Xbox-style) button layout as reported by SDL on Linux/Windows.
PAD_BUTTONS: Final[Mapping[int, tuple[Action, ...]]] = {
    0: (Action.JUMP, Action.CONFIRM),  # A
    1: (Action.ATTACK, Action.BACK),   # B
    2: (Action.ATTACK,),               # X
    3: (Action.ATTACK,),               # Y
    6: (Action.BACK,),                 # Back / Select
    7: (Action.PAUSE,),                # Start
}
STICK_DEADZONE: Final = 0.45


class InputState:
    """Tracks held actions plus edges (pressed/released this frame).

    Edges are visible only to the first update sub-step of a frame; the game
    loop calls ``end_step`` after each sub-step so a single key press is never
    handled twice.
    """

    def __init__(self, bindings: Mapping[Action, tuple[int, ...]] = DEFAULT_BINDINGS) -> None:
        self._bindings = bindings
        self._key_to_actions: dict[int, list[Action]] = {}
        for action, keys in bindings.items():
            for key in keys:
                self._key_to_actions.setdefault(key, []).append(action)
        self._held: set[Action] = set()
        self._pressed: set[Action] = set()
        self._released: set[Action] = set()
        self._pad_held: set[Action] = set()
        self._pads: dict[int, pygame.joystick.JoystickType] = {}
        self.any_pressed = False
        if pygame.joystick.get_init():
            for index in range(pygame.joystick.get_count()):
                self._add_pad(index)

    @property
    def pad_connected(self) -> bool:
        return bool(self._pads)

    def _add_pad(self, device_index: int) -> None:
        try:
            pad = pygame.joystick.Joystick(device_index)
            pad.init()
            self._pads[pad.get_instance_id()] = pad
        except pygame.error:
            pass

    def begin_frame(self, events: Iterable[pygame.event.Event]) -> None:
        self._pressed.clear()
        self._released.clear()
        self.any_pressed = False
        for event in events:
            if event.type == pygame.KEYDOWN:
                self._pressed.update(self._key_to_actions.get(event.key, ()))
                self.any_pressed = True
            elif event.type == pygame.KEYUP:
                self._released.update(self._key_to_actions.get(event.key, ()))
            elif event.type == pygame.JOYDEVICEADDED:
                self._add_pad(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._pads.pop(event.instance_id, None)
            elif event.type == pygame.JOYBUTTONDOWN:
                self.any_pressed = True

        keys = pygame.key.get_pressed()
        held = {
            action
            for action, bound_keys in self._bindings.items()
            if any(keys[key] for key in bound_keys)
        }
        # A press and release within one frame still counts as a press.
        held |= self._pressed - self._released

        pad_held = self._poll_pads()
        self._pressed |= pad_held - self._pad_held
        self._released |= self._pad_held - pad_held
        self._pad_held = pad_held
        self._held = held | pad_held

    def _poll_pads(self) -> set[Action]:
        held: set[Action] = set()
        for pad in self._pads.values():
            try:
                for button, actions in PAD_BUTTONS.items():
                    if button < pad.get_numbuttons() and pad.get_button(button):
                        held.update(actions)
                x = y = 0.0
                if pad.get_numhats() > 0:
                    hat_x, hat_y = pad.get_hat(0)
                    x, y = float(hat_x), float(-hat_y)
                if pad.get_numaxes() >= 2:
                    stick_x, stick_y = pad.get_axis(0), pad.get_axis(1)
                    if abs(stick_x) > STICK_DEADZONE:
                        x = stick_x
                    if abs(stick_y) > STICK_DEADZONE:
                        y = stick_y
            except pygame.error:
                continue
            if x < -0.5:
                held.add(Action.LEFT)
            elif x > 0.5:
                held.add(Action.RIGHT)
            if y < -0.5:
                held.add(Action.UP)
            elif y > 0.5:
                held.add(Action.DOWN)
        return held

    def end_step(self) -> None:
        self._pressed.clear()
        self._released.clear()
        self.any_pressed = False

    def is_held(self, action: Action) -> bool:
        return action in self._held

    def was_pressed(self, action: Action) -> bool:
        return action in self._pressed

    def was_released(self, action: Action) -> bool:
        return action in self._released

    def axis(self, negative: Action, positive: Action) -> int:
        return int(self.is_held(positive)) - int(self.is_held(negative))
