"""Turns raw input into player *intent*.

The Player never reads the keyboard. It receives a PlayerIntent each step,
so the same Player could be driven by a gamepad, a replay file or a test.
"""

from dataclasses import dataclass

from core.input import Action, InputState


@dataclass(frozen=True)
class PlayerIntent:
    move_axis: int = 0  # -1 left, 0 none, 1 right
    jump_pressed: bool = False
    jump_held: bool = False
    up_held: bool = False
    down_held: bool = False
    attack_pressed: bool = False
    dash_pressed: bool = False
    down_pressed: bool = False


class PlayerController:
    def __init__(self, input_state: InputState) -> None:
        self._input = input_state

    def read(self) -> PlayerIntent:
        state = self._input
        return PlayerIntent(
            move_axis=state.axis(Action.LEFT, Action.RIGHT),
            jump_pressed=state.was_pressed(Action.JUMP),
            jump_held=state.is_held(Action.JUMP),
            up_held=state.is_held(Action.UP),
            down_held=state.is_held(Action.DOWN),
            attack_pressed=state.was_pressed(Action.ATTACK),
            dash_pressed=state.was_pressed(Action.DASH),
            down_pressed=state.was_pressed(Action.DOWN),
        )
