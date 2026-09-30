"""Optional enemies, built once per asset library and reused on respawn."""

from rendering.art import wonders
from rendering.sprite_library import AnimationSpec, SheetSpec


def _sheet(name, painter, states, frames=6):
    animations = {state: AnimationSpec(row, frames, duration, loop)
                  for row, (state, duration, loop) in enumerate(states)}
    return SheetSpec(name + ".png", 56, 56, animations, painter)


MIRROR_DUELIST = _sheet("mirror_duelist", wonders.paint_duelist,
                       (("walk", .12, True), ("windup", .1, False),
                        ("lunge", .047, False), ("recover", .175, False)))
SAND_BURROWER = _sheet("sand_burrower", wonders.paint_burrower,
                       (("walk", .12, True), ("warn", .125, False), ("emerge", .05, False),
                        ("exposed", .1, True), ("retreat", .05, False)))
LANTERN_THIEF = _sheet("lantern_thief", wonders.paint_thief,
                      (("walk", .065, True), ("carry", .065, True)), frames=8)
CLOCKWORK_GUARDIAN = _sheet("clockwork_guardian", wonders.paint_guardian,
                           (("walk", .12, True), ("unfold", .075, False),
                            ("open", .10, True), ("close", .067, False)))
ENEMY_SHEETS = (MIRROR_DUELIST, SAND_BURROWER, LANTERN_THIEF, CLOCKWORK_GUARDIAN)
