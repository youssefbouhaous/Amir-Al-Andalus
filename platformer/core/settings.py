"""Global, read-only configuration.

Every tunable number lives here so gameplay code never contains magic numbers.
Values are constants (typed ``Final``) or frozen dataclasses, so there is no
global mutable state. Tweak physics feel by editing the dataclass defaults.
(Player-adjustable options such as volume live in the save file instead, see
``core/save.py``.)
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

Color = tuple[int, int, int]


def _user_dir(kind: str) -> Path:
    """Per-user folder for saves ("data") or regenerable files ("cache")."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home())
        return base / "AmirAlAndalus" / kind
    if sys.platform == "darwin":
        sub = "Application Support" if kind == "data" else "Caches"
        return Path.home() / "Library" / sub / "AmirAlAndalus"
    env = "XDG_DATA_HOME" if kind == "data" else "XDG_CACHE_HOME"
    default = Path.home() / (".local/share" if kind == "data" else ".cache")
    return Path(os.environ.get(env) or default) / "amir-al-andalus"


# --- Paths ------------------------------------------------------------------
PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent
ASSETS_DIR: Final = PROJECT_ROOT / "assets"
MAPS_DIR: Final = ASSETS_DIR / "maps"
FONTS_DIR: Final = ASSETS_DIR / "fonts"
SAVE_DIR: Final = _user_dir("data")
SAVE_FILE: Final = "save.json"
CACHE_DIR: Final = _user_dir("cache")

# --- Window -----------------------------------------------------------------
WINDOW_TITLE: Final = "Amir Al-Andalus"
WINDOW_TITLE_ARABIC: Final = "أمير الأندلس"
GAME_TAGLINE: Final = "Seek the Sword of Light"
SCREEN_WIDTH: Final = 960
SCREEN_HEIGHT: Final = 540
FPS: Final = 60

# --- Timing -----------------------------------------------------------------
# A frame that took longer than this (window drag, breakpoint, disk stall) is
# treated as if it took exactly this long. Without the cap, one huge dt would
# launch objects through walls after the game resumes.
MAX_FRAME_TIME: Final = 0.1

# Large frames are split into equal sub-steps no longer than this, so physics
# behaves the same at 30 FPS as at 60 FPS and nothing moves more than a few
# pixels per step (which is what keeps collisions from being skipped).
MAX_UPDATE_STEP: Final = 1 / 120

# --- World ------------------------------------------------------------------
TILE_SIZE: Final = 32
FIRST_LEVEL: Final = "level1.tmx"
# How far below the bottom of the map the player may fall before dying.
FALL_DEATH_MARGIN: Final = 64
# Enemies start moving once they come within this distance of the screen.
ENEMY_ACTIVATION_MARGIN: Final = 96
# Terrain is pre-rendered into square chunks of this many tiles.
TERRAIN_CHUNK_TILES: Final = 16

# --- Session / scoring --------------------------------------------------------
STARTING_LIVES: Final = 5
COINS_PER_EXTRA_LIFE: Final = 100
PAGES_PER_LEVEL: Final = 3
SCORE_COIN: Final = 200
SCORE_STOMP: Final = 100
SCORE_ENEMY_KNOCKED: Final = 200
SCORE_ENEMY_STARRED: Final = 200
SCORE_BRICK: Final = 50
SCORE_POWERUP: Final = 1000
SCORE_EXTRA_LIFE: Final = 1000
SCORE_PAGE: Final = 2000
SCORE_LEVEL_COMPLETE: Final = 2000
SCORE_BOSS_HIT: Final = 1000
SCORE_BOSS_DEFEATED: Final = 10000
# Finishing a level under par time earns this many points per second saved.
TIME_BONUS_PER_SECOND: Final = 20


@dataclass(frozen=True)
class PlayerPhysics:
    """Everything that defines how the player *feels*. Units: pixels, seconds."""

    hitbox_width: float = 20.0
    hitbox_height: float = 28.0

    max_run_speed: float = 230.0
    ground_acceleration: float = 1500.0
    air_acceleration: float = 1000.0
    # Used instead of ground_acceleration when pushing against current motion,
    # so turning around feels snappy instead of floaty.
    turn_acceleration: float = 2800.0
    ground_friction: float = 1800.0
    air_friction: float = 250.0

    gravity: float = 2100.0
    # Falling faster than rising makes jumps feel less floaty.
    fall_gravity_multiplier: float = 1.5
    terminal_velocity: float = 900.0

    # Peak height = jump_velocity^2 / (2 * gravity) ~= 123 px ~= 3.8 tiles.
    jump_velocity: float = 720.0
    # Upward speed is multiplied by this when jump is released early.
    jump_cut_multiplier: float = 0.4
    # Grace period to still jump after walking off a ledge.
    coyote_time: float = 0.1
    # A jump pressed this long before landing still triggers on landing.
    jump_buffer_time: float = 0.12

    # Wall slide / wall jump. Sliding caps the fall speed; the jump pushes
    # away from the wall and briefly ignores input toward it, so holding the
    # direction of the wall climbs a shaft in a zigzag instead of re-sticking.
    wall_slide_speed: float = 130.0
    wall_jump_velocity_x: float = 250.0
    wall_jump_velocity_y: float = 650.0
    wall_jump_lock_time: float = 0.16
    wall_coyote_time: float = 0.09

    stomp_bounce_velocity: float = 420.0
    stomp_bounce_held_velocity: float = 650.0
    spring_velocity: float = 900.0
    spring_held_velocity: float = 1180.0

    # Star power: thrown eight-pointed stars.
    throw_cooldown: float = 0.25
    max_projectiles: int = 2
    throw_pose_time: float = 0.18

    hurt_invulnerability_time: float = 1.6
    invulnerability_blink_rate: float = 16.0
    star_invincibility_time: float = 0.0

    death_freeze_time: float = 0.5
    death_bounce_velocity: float = 560.0
    death_duration: float = 2.2

    door_enter_duration: float = 0.6
    door_sink_speed: float = 48.0
    door_exit_duration: float = 0.5
    victory_duration: float = 2.2

    # Below this horizontal speed the player counts as standing still.
    idle_speed_threshold: float = 12.0
    # Run animation playback speed scales with velocity, never below this.
    min_run_animation_speed: float = 0.5
    # Landing faster than this squashes the sprite and puffs dust.
    hard_landing_speed: float = 380.0


PLAYER_PHYSICS: Final = PlayerPhysics()


@dataclass(frozen=True)
class EnemySettings:
    gravity: float = 2100.0
    terminal_velocity: float = 900.0

    walker_speed: float = 55.0
    walker_hitbox: tuple[float, float] = (26.0, 20.0)

    hopper_speed: float = 70.0
    hopper_jump_velocity: float = 520.0
    hopper_rest_time: float = 0.9
    hopper_hitbox: tuple[float, float] = (24.0, 22.0)

    flyer_speed: float = 70.0
    flyer_patrol_tiles: float = 3.0
    flyer_bob_amplitude: float = 18.0
    flyer_bob_frequency: float = 2.0
    flyer_hitbox: tuple[float, float] = (24.0, 18.0)

    hedgehog_speed: float = 45.0
    hedgehog_hitbox: tuple[float, float] = (26.0, 20.0)

    bat_hitbox: tuple[float, float] = (22.0, 16.0)
    bat_trigger_distance: float = 170.0
    bat_dive_speed: float = 260.0
    bat_flee_speed: float = 150.0

    ghul_speed: float = 55.0
    ghul_hitbox: tuple[float, float] = (22.0, 30.0)

    squash_duration: float = 0.5
    knockout_velocity: float = 380.0
    knockout_horizontal_speed: float = 60.0
    # Tolerance (px) when deciding whether the player landed on an enemy.
    stomp_tolerance: float = 10.0


ENEMY: Final = EnemySettings()


@dataclass(frozen=True)
class ItemSettings:
    rise_duration: float = 0.5
    powerup_speed: float = 80.0
    gravity: float = 1800.0
    terminal_velocity: float = 700.0
    hitbox_size: float = 22.0
    coin_hitbox_size: float = 16.0
    coin_pop_velocity: float = 460.0
    coin_pop_gravity: float = 1400.0
    coin_pop_duration: float = 0.55


ITEMS: Final = ItemSettings()


@dataclass(frozen=True)
class ProjectileSettings:
    star_speed: float = 430.0
    star_gravity: float = 1700.0
    star_bounce_velocity: float = 360.0
    star_lifetime: float = 2.6
    star_size: float = 14.0
    fireball_speed: float = 190.0
    fireball_size: float = 14.0
    fireball_lifetime: float = 6.0


PROJECTILES: Final = ProjectileSettings()


@dataclass(frozen=True)
class BlockSettings:
    bump_duration: float = 0.18
    bump_height: float = 8.0
    debris_speed: float = 180.0
    debris_jump_velocity: float = 420.0
    debris_gravity: float = 1600.0
    debris_lifetime: float = 1.2
    debris_size: int = 10


BLOCKS: Final = BlockSettings()


@dataclass(frozen=True)
class CameraSettings:
    # The player can move this far from the screen centre before the camera
    # starts following (the "dead zone").
    dead_zone_width: float = 64.0
    dead_zone_height: float = 96.0
    # Aim a little above the player so they see more of what's above.
    vertical_offset: float = 40.0
    # Higher = snappier. Used as 1 - exp(-smoothing * dt), which is
    # frame-rate independent unlike a fixed per-frame lerp factor.
    smoothing: float = 9.0
    # The camera leads the player in the direction they run.
    look_ahead: float = 70.0
    look_ahead_smoothing: float = 2.5


CAMERA: Final = CameraSettings()


@dataclass(frozen=True)
class JuiceSettings:
    """Screen shake and hit-stop: feedback that makes impacts feel heavy."""

    shake_max_offset: float = 14.0
    shake_decay: float = 1.8  # trauma lost per second
    shake_frequency: float = 22.0
    hitstop_stomp: float = 0.045
    hitstop_hurt: float = 0.12
    hitstop_boss: float = 0.16


JUICE: Final = JuiceSettings()

# --- Moving platforms ---------------------------------------------------------
PLATFORM_DEFAULT_SPEED: Final = 80.0
PLATFORM_DEFAULT_DISTANCE_TILES: Final = 4.0

# --- Scene timings ------------------------------------------------------------
LEVEL_INTRO_DURATION: Final = 2.6
LEVEL_COMPLETE_SCREEN_DURATION: Final = 2.8
FADE_DURATION: Final = 0.35
TRANSITION_DURATION: Final = 0.55
SCORE_POPUP_DURATION: Final = 0.9
SCORE_POPUP_RISE_SPEED: Final = 46.0

# --- Audio --------------------------------------------------------------------
DEFAULT_SFX_VOLUME: Final = 0.7
DEFAULT_MUSIC_VOLUME: Final = 0.6
SFX_VOLUME: Final = 0.5
MUSIC_VOLUME: Final = 0.4
SYNTH_AMPLITUDE: Final = 0.22
MENU_MUSIC: Final = "title"
# The menu has no level camera, so it uses a fixed Andalusian sunset scene.
MENU_SKY_THEME: Final = "rooftops"
MAP_MUSIC: Final = "map"
AUDIO_SAMPLE_RATE: Final = 44100

# --- Particles ------------------------------------------------------------------
MAX_PARTICLES: Final = 900

# --- Colors -------------------------------------------------------------------
TEXT_COLOR: Final[Color] = (255, 255, 255)
TEXT_SHADOW_COLOR: Final[Color] = (20, 20, 30)
TITLE_COLOR: Final[Color] = (255, 214, 90)
GOLD: Final[Color] = (240, 190, 70)
GOLD_LIGHT: Final[Color] = (255, 232, 150)
PARCHMENT: Final[Color] = (238, 222, 184)
INK: Final[Color] = (58, 36, 28)
MENU_BACKGROUND_COLOR: Final[Color] = (24, 18, 36)
OVERLAY_COLOR: Final = (8, 6, 16, 150)
FADE_COLOR: Final[Color] = (14, 10, 24)
BUTTON_COLOR: Final[Color] = (52, 38, 66)
BUTTON_HOVER_COLOR: Final[Color] = (118, 62, 58)
BUTTON_BORDER_COLOR: Final[Color] = (240, 196, 96)
ERROR_TEXT_COLOR: Final[Color] = (255, 120, 120)

# --- Fonts --------------------------------------------------------------------
# Roles -> font files in assets/fonts (all SIL Open Font License). A missing
# file falls back to pygame's default font, so the game still runs.
FONT_FILES: Final[dict[str, str]] = {
    "display": "ArefRuqaa-Bold.ttf",
    "arabic": "Amiri-Bold.ttf",
    "ui": "Marcellus-Regular.ttf",
    "body": "Alegreya-Variable.ttf",
}
HUD_FONT_SIZE: Final = 24
POPUP_FONT_SIZE: Final = 20
MENU_FONT_SIZE: Final = 30
TITLE_FONT_SIZE: Final = 76
SUBTITLE_FONT_SIZE: Final = 30
SMALL_FONT_SIZE: Final = 20

# --- UI layout ----------------------------------------------------------------
HUD_MARGIN: Final = 14
HUD_ICON_GAP: Final = 6
BUTTON_WIDTH: Final = 320
BUTTON_HEIGHT: Final = 46
BUTTON_SPACING: Final = 12
BUTTON_BORDER_WIDTH: Final = 2
BUTTON_CORNER_RADIUS: Final = 8

# --- Debug overlay ------------------------------------------------------------
DEBUG_FONT_SIZE: Final = 22
DEBUG_TEXT_COLOR: Final[Color] = (255, 255, 255)
DEBUG_PANEL_COLOR: Final = (0, 0, 0, 150)  # RGBA, semi-transparent
DEBUG_PANEL_PADDING: Final = 8
DEBUG_PANEL_MARGIN: Final = 8
DEBUG_TILE_COLOR: Final[Color] = (255, 80, 80)
DEBUG_ONE_WAY_COLOR: Final[Color] = (255, 200, 60)
DEBUG_PLAYER_COLOR: Final[Color] = (60, 255, 120)
DEBUG_ENTITY_COLOR: Final[Color] = (80, 200, 255)
DEBUG_TRIGGER_COLOR: Final[Color] = (220, 120, 255)
DEBUG_DEAD_ZONE_COLOR: Final[Color] = (255, 255, 255)
