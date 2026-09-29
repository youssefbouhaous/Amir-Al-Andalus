"""Visual themes: sky, parallax layers, weather and lighting per level.

The journey runs from dawn in Qurtuba to midnight in the Alhambra, so each
theme is also a time of day. A level picks its theme with the map property
``theme`` (older maps used ``sky`` = dawn / sunset / night, still accepted).
"""

from dataclasses import dataclass, field

from core.settings import Color


@dataclass(frozen=True)
class Layer:
    kind: str            # "mountains" | "hills" | "skyline" | "trees"
    color: Color
    parallax: float      # 0 = fixed to the screen, 1 = moves with the world
    height: int
    # Distance of the layer's base below the horizon line, in pixels.
    drop: int = 0
    style: str = ""
    snow: Color | None = None
    seed: int = 1
    windows: Color | None = None


@dataclass(frozen=True)
class Theme:
    name: str
    sky: tuple[tuple[float, Color], ...]
    layers: tuple[Layer, ...]
    celestial: str | None = None       # "sun" | "moon"
    celestial_pos: tuple[float, float] = (0.8, 0.2)
    celestial_color: Color = (255, 240, 200)
    celestial_radius: int = 34
    celestial_glow: Color = (255, 200, 120)
    stars: int = 0
    clouds: int = 0
    cloud_color: Color = (255, 250, 242)
    cloud_shade: Color = (226, 214, 214)
    birds: bool = False
    bird_color: Color = (40, 30, 40)
    weather: tuple[str, ...] = ()       # "petals", "motes", "snow", "fireflies", "embers", "leaves"
    # Ambient light for the lighting pass; None disables lighting.
    light: Color | None = None
    dust: Color = (226, 206, 170)
    horizon: float = 0.72               # horizon line as a fraction of screen height
    music: str = "level1"
    shooting_stars: bool = False
    extra: dict = field(default_factory=dict)


THEMES: dict[str, Theme] = {
    "garden": Theme(
        name="garden",
        sky=((0.0, (96, 132, 204)), (0.55, (236, 184, 176)), (0.8, (252, 214, 170)), (1.0, (252, 226, 186))),
        celestial="sun", celestial_pos=(0.2, 0.6), celestial_color=(255, 236, 190), celestial_radius=36,
        celestial_glow=(255, 190, 130),
        clouds=7, cloud_color=(255, 240, 236), cloud_shade=(232, 196, 204),
        layers=(
            Layer("mountains", (158, 140, 186), 0.06, 150, drop=-40, seed=3),
            Layer("hills", (170, 142, 168), 0.12, 120, drop=-10, seed=4),
            Layer("skyline", (176, 124, 132), 0.22, 230, drop=10, style="cordoba", seed=5),
            Layer("trees", (128, 98, 110), 0.4, 150, drop=40, style="mixed", seed=6),
        ),
        birds=True, bird_color=(90, 60, 80), weather=("petals",), dust=(226, 206, 170), music="level1",
    ),
    "palace": Theme(
        name="palace",
        sky=((0.0, (74, 136, 226)), (0.6, (156, 200, 244)), (1.0, (224, 238, 250))),
        celestial="sun", celestial_pos=(0.82, 0.16), celestial_color=(255, 252, 230), celestial_radius=30,
        celestial_glow=(255, 240, 180),
        clouds=9, cloud_color=(255, 255, 255), cloud_shade=(206, 222, 240),
        layers=(
            Layer("mountains", (118, 150, 176), 0.06, 170, drop=-50, seed=11),
            Layer("skyline", (196, 184, 160), 0.18, 230, drop=0, style="zahra", seed=12),
            Layer("trees", (96, 132, 104), 0.4, 160, drop=40, style="palm", seed=13),
        ),
        birds=True, bird_color=(60, 60, 80), weather=("motes",), dust=(236, 226, 206), music="level2",
    ),
    "clockwork": Theme(
        name="clockwork",
        sky=((0.0, (104, 160, 226)), (0.7, (214, 214, 206)), (1.0, (238, 222, 190))),
        celestial="sun", celestial_pos=(0.5, 0.1), celestial_color=(255, 250, 230), celestial_radius=28,
        clouds=5,
        layers=(
            Layer("hills", (150, 160, 150), 0.08, 130, drop=-20, seed=21),
            Layer("skyline", (178, 150, 130), 0.2, 330, drop=20, style="toledo", seed=22),
            Layer("trees", (110, 110, 96), 0.42, 130, drop=50, style="cypress", seed=23),
        ),
        weather=("motes",), dust=(214, 190, 160), music="level3",
    ),
    "rooftops": Theme(
        name="rooftops",
        sky=((0.0, (64, 44, 108)), (0.45, (178, 88, 112)), (0.75, (246, 146, 90)), (1.0, (255, 200, 120))),
        celestial="sun", celestial_pos=(0.68, 0.7), celestial_color=(255, 176, 96), celestial_radius=52,
        celestial_glow=(255, 130, 60),
        clouds=6, cloud_color=(255, 170, 140), cloud_shade=(160, 80, 110),
        layers=(
            Layer("hills", (132, 70, 96), 0.08, 120, drop=-20, seed=31),
            Layer("skyline", (98, 50, 74), 0.22, 320, drop=20, style="seville", seed=32, windows=(255, 200, 120)),
            Layer("trees", (60, 32, 52), 0.42, 150, drop=50, style="palm", seed=33),
        ),
        birds=True, bird_color=(50, 24, 40), weather=("motes",), dust=(236, 196, 160),
        light=(255, 236, 222), music="level4",
    ),
    "mountain": Theme(
        name="mountain",
        sky=((0.0, (18, 22, 58)), (0.55, (66, 62, 126)), (0.85, (196, 128, 150)), (1.0, (236, 170, 150))),
        celestial="moon", celestial_pos=(0.24, 0.26), celestial_color=(236, 240, 255), celestial_radius=28,
        celestial_glow=(160, 180, 255), stars=110,
        layers=(
            Layer("mountains", (70, 76, 124), 0.05, 260, drop=-60, snow=(222, 230, 250), seed=41),
            Layer("mountains", (52, 56, 96), 0.12, 200, drop=0, snow=(190, 200, 236), seed=42),
            Layer("trees", (30, 34, 62), 0.4, 150, drop=50, style="pine", snow=(170, 180, 220), seed=43),
        ),
        weather=("snow",), light=(176, 180, 228), dust=(240, 244, 255), music="level5",
        shooting_stars=True,
    ),
    "fortress": Theme(
        name="fortress",
        sky=((0.0, (8, 12, 38)), (0.7, (34, 38, 88)), (1.0, (58, 56, 108))),
        celestial="moon", celestial_pos=(0.8, 0.2), celestial_color=(244, 244, 255), celestial_radius=34,
        celestial_glow=(150, 170, 255), stars=160,
        layers=(
            Layer("mountains", (36, 40, 78), 0.05, 240, drop=-60, snow=(120, 130, 180), seed=51),
            Layer("skyline", (26, 24, 52), 0.18, 260, drop=10, style="granada", seed=52, windows=(255, 196, 110)),
            Layer("trees", (16, 16, 34), 0.4, 170, drop=50, style="cypress", seed=53),
        ),
        weather=("fireflies",), light=(92, 98, 158), dust=(170, 150, 150), music="level6",
        shooting_stars=True,
    ),
    "court": Theme(
        name="court",
        sky=((0.0, (8, 6, 26)), (0.7, (46, 18, 54)), (1.0, (86, 30, 60))),
        celestial="moon", celestial_pos=(0.5, 0.2), celestial_color=(255, 226, 222), celestial_radius=44,
        celestial_glow=(255, 110, 110), stars=180,
        layers=(
            Layer("skyline", (24, 16, 40), 0.15, 300, drop=20, style="alhambra", seed=61),
        ),
        weather=("embers", "fireflies"), light=(110, 90, 140), dust=(200, 180, 190), music="boss",
    ),
}

LEGACY_THEMES = {"dawn": "garden", "sunset": "rooftops", "night": "fortress"}
DEFAULT_THEME = "garden"


def get_theme(name: str) -> Theme:
    name = LEGACY_THEMES.get(name, name)
    return THEMES.get(name, THEMES[DEFAULT_THEME])
