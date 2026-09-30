"""Sprite sheet layouts for every animated thing in the game.

To replace a placeholder, create the PNG named in ``image_path`` inside
``assets/images/`` with frames laid out in rows as described here (run
``python -m tools.build_assets --export-sprites`` to get template PNGs).
"""

from rendering.art import enemies, items, prince
from rendering.sprite_library import AnimationSpec, SheetSpec

PLAYER_ANIMATIONS = {
    "idle": AnimationSpec(row=0, frame_count=12, frame_duration=0.1),
    "run": AnimationSpec(row=1, frame_count=10, frame_duration=0.062),
    "skid": AnimationSpec(row=2, frame_count=1, frame_duration=1.0),
    "jump": AnimationSpec(row=3, frame_count=2, frame_duration=0.08, loop=False),
    "apex": AnimationSpec(row=4, frame_count=1, frame_duration=1.0),
    "fall": AnimationSpec(row=5, frame_count=2, frame_duration=0.1),
    "wall_slide": AnimationSpec(row=6, frame_count=2, frame_duration=0.09),
    "throw": AnimationSpec(row=7, frame_count=3, frame_duration=0.06, loop=False),
    "hurt": AnimationSpec(row=8, frame_count=1, frame_duration=1.0),
    "death": AnimationSpec(row=9, frame_count=4, frame_duration=0.1),
    "victory": AnimationSpec(row=10, frame_count=6, frame_duration=0.09, loop=False),
    "door": AnimationSpec(row=11, frame_count=1, frame_duration=1.0),
    "sit": AnimationSpec(row=12, frame_count=2, frame_duration=0.6),
    "dash": AnimationSpec(row=13, frame_count=2, frame_duration=0.05),
    "slide": AnimationSpec(row=14, frame_count=2, frame_duration=0.12),
    "pound": AnimationSpec(row=15, frame_count=3, frame_duration=0.06),
    "glide": AnimationSpec(row=16, frame_count=4, frame_duration=0.12),
    "hang": AnimationSpec(row=17, frame_count=5, frame_duration=1.0),
}
_PLAYER_FRAME_COUNTS = {name: spec.frame_count for name, spec in PLAYER_ANIMATIONS.items()}

PLAYER = SheetSpec(
    "prince.png", 48, 48, PLAYER_ANIMATIONS,
    prince.prince_painter(prince.PRINCE_PALETTE, _PLAYER_FRAME_COUNTS),
)
PLAYER_POWERED = SheetSpec(
    "prince_powered.png", 48, 48, PLAYER_ANIMATIONS,
    prince.prince_painter(prince.PRINCE_POWERED_PALETTE, _PLAYER_FRAME_COUNTS),
)
PLAYER_STAR = SheetSpec(
    "prince_star.png", 48, 48, PLAYER_ANIMATIONS,
    prince.prince_painter(prince.PRINCE_STAR_PALETTE, _PLAYER_FRAME_COUNTS),
)

WALKER = SheetSpec(
    "scorpion.png", 32, 32,
    {
        "walk": AnimationSpec(row=0, frame_count=4, frame_duration=0.13),
        "squashed": AnimationSpec(row=1, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_scorpion,
)

HOPPER = SheetSpec(
    "clay_jar.png", 32, 32,
    {
        "walk": AnimationSpec(row=0, frame_count=2, frame_duration=0.3),
        "crouch": AnimationSpec(row=1, frame_count=1, frame_duration=1.0),
        "jump": AnimationSpec(row=2, frame_count=1, frame_duration=1.0),
        "squashed": AnimationSpec(row=3, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_clay_jar,
)

FLYER = SheetSpec(
    "jinn.png", 32, 32,
    {
        "walk": AnimationSpec(row=0, frame_count=4, frame_duration=0.1),
        "squashed": AnimationSpec(row=1, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_jinn,
)

HEDGEHOG = SheetSpec(
    "hedgehog.png", 32, 32,
    {
        "walk": AnimationSpec(row=0, frame_count=4, frame_duration=0.14),
        "curled": AnimationSpec(row=1, frame_count=1, frame_duration=1.0),
        "squashed": AnimationSpec(row=2, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_hedgehog,
)

BAT = SheetSpec(
    "bat.png", 32, 32,
    {
        "hang": AnimationSpec(row=0, frame_count=2, frame_duration=0.5),
        "walk": AnimationSpec(row=1, frame_count=4, frame_duration=0.07),
        "squashed": AnimationSpec(row=2, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_bat,
)

GHUL = SheetSpec(
    "ghul.png", 32, 40,
    {
        "walk": AnimationSpec(row=0, frame_count=4, frame_duration=0.15),
        "shy": AnimationSpec(row=1, frame_count=2, frame_duration=0.3),
        "squashed": AnimationSpec(row=2, frame_count=1, frame_duration=1.0),
    },
    enemies.paint_ghul,
)

COIN = SheetSpec(
    "dinar.png", 16, 16,
    {"spin": AnimationSpec(row=0, frame_count=8, frame_duration=0.08)},
    items.paint_dinar,
)

POWERUP = SheetSpec(
    "pomegranate.png", 24, 24,
    {"pulse": AnimationSpec(row=0, frame_count=4, frame_duration=0.14)},
    items.paint_pomegranate,
)

EXTRA_LIFE = SheetSpec(
    "oil_lamp.png", 24, 24,
    {"pulse": AnimationSpec(row=0, frame_count=4, frame_duration=0.1)},
    items.paint_oil_lamp,
)

STAR_POWER = SheetSpec(
    "najma.png", 24, 24,
    {"pulse": AnimationSpec(row=0, frame_count=4, frame_duration=0.08)},
    items.paint_star_power,
)

PAGE = SheetSpec(
    "page.png", 24, 24,
    {"float": AnimationSpec(row=0, frame_count=4, frame_duration=0.18)},
    items.paint_page,
)

STAR_PROJECTILE = SheetSpec(
    "star_projectile.png", 16, 16,
    {"spin": AnimationSpec(row=0, frame_count=4, frame_duration=0.04)},
    items.paint_star_projectile,
)

FIREBALL = SheetSpec(
    "fireball.png", 16, 16,
    {"burn": AnimationSpec(row=0, frame_count=3, frame_duration=0.07)},
    items.paint_fireball,
)

ALL_SHEETS = (
    PLAYER, PLAYER_POWERED, PLAYER_STAR, WALKER, HOPPER, FLYER, HEDGEHOG, BAT, GHUL,
    COIN, POWERUP, EXTRA_LIFE, STAR_POWER, PAGE, STAR_PROJECTILE, FIREBALL,
)
