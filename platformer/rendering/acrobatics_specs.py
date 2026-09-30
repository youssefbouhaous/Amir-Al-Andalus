"""Separate, cached sheets: existing PNG replacements remain compatible."""

from rendering.art import acrobatics, prince
from rendering.sprite_library import AnimationSpec, SheetSpec

_LAYOUT = (("ledge_hang", 6, .12, True), ("vault", 8, .03, False),
           ("scarf_cast", 5, .03, False), ("scarf_swing", 5, 1., False),
           ("sand_slide", 6, .07, True), ("spin_jump", 12, .03, False),
           ("land_soft", 4, .035, False), ("land_hard", 6, .035, False),
           ("wall_kick", 4, .04, False))
ANIMATIONS = {name: AnimationSpec(row, frames, duration, loop)
              for row, (name, frames, duration, loop) in enumerate(_LAYOUT)}
_COUNTS = {name: spec.frame_count for name, spec in ANIMATIONS.items()}
PLAYER_SHEETS = tuple(
    SheetSpec(f"prince_wonders_{index}.png", 48, 48, ANIMATIONS, acrobatics.painter(palette, _COUNTS))
    for index, palette in enumerate((prince.PRINCE_PALETTE, prince.PRINCE_POWERED_PALETTE,
                                     prince.PRINCE_STAR_PALETTE))
)
