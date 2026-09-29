"""Generate the placeholder tileset and the starter levels as Tiled files.

Run from the project folder:

    python -m tools.build_assets                  # tileset + levels
    python -m tools.build_assets --export-sprites # also PNG sprite templates

This is a one-off *bootstrapping* tool. The levels below are sketched as
ASCII so they're readable in a code review, then written out as real .tmx
files. From then on, edit the .tmx files visually in Tiled; re-running this
tool overwrites them (it asks first unless --force is given).
"""

import argparse
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from core import settings
from rendering import placeholder_art
from rendering.sprite_library import build_placeholder_sheet
from rendering.sprite_specs import ALL_SHEETS

T = settings.TILE_SIZE
MAPS_DIR = settings.MAPS_DIR
IMAGES_DIR = settings.ASSETS_DIR / "images"
TILESET_FILE = "tileset.tsx"
TILESET_IMAGE = "tileset.png"
TILESET_COLUMNS = 8
TILED_VERSION = "1.10.2"
TMX_VERSION = "1.10"
PLATFORM_HEIGHT = 16


@dataclass(frozen=True)
class TileDef:
    name: str
    properties: dict[str, str] = field(default_factory=dict)


# Order = tile id in the tileset. Append new tiles at the end so existing
# maps keep their ids.
TILESET: tuple[TileDef, ...] = (
    TileDef("ground"),
    TileDef("dirt"),
    TileDef("stone"),
    TileDef("brick", {"spawn": "brick"}),
    TileDef("question", {"spawn": "question", "contents": "coin"}),
    TileDef("question_powerup", {"spawn": "question", "contents": "powerup"}),
    TileDef("question_life", {"spawn": "question", "contents": "extra_life"}),
    TileDef("coin", {"spawn": "coin"}),
    TileDef("used_block"),
    TileDef("platform", {"collision": "one_way"}),
    TileDef("pipe_top_left"),
    TileDef("pipe_top_right"),
    TileDef("pipe_left"),
    TileDef("pipe_right"),
    TileDef("cloud_left"),
    TileDef("cloud_right"),
    TileDef("bush"),
    TileDef("grass"),
    TileDef("flower"),
    TileDef("fence"),
    TileDef("question_star", {"spawn": "question", "contents": "star"}),
    TileDef("sun_block", {"spawn": "switch_block", "color": "sun"}),
    TileDef("moon_block", {"spawn": "switch_block", "color": "moon"}),
)
TILE_IDS = {tile.name: index for index, tile in enumerate(TILESET)}

LAYER_ORDER = ("background", "terrain", "blocks", "collectibles", "decorations")

# ASCII legend: character -> (tile layer, tile name)
TILE_CHARS: dict[str, tuple[str, str]] = {
    "G": ("terrain", "ground"),
    "D": ("terrain", "dirt"),
    "S": ("terrain", "stone"),
    "=": ("terrain", "platform"),
    "[": ("terrain", "pipe_top_left"),
    "]": ("terrain", "pipe_top_right"),
    "{": ("terrain", "pipe_left"),
    "}": ("terrain", "pipe_right"),
    "B": ("blocks", "brick"),
    "?": ("blocks", "question"),
    "P": ("blocks", "question_powerup"),
    "L": ("blocks", "question_life"),
    "N": ("blocks", "question_star"),
    "U": ("blocks", "sun_block"),
    "M": ("blocks", "moon_block"),
    "C": ("collectibles", "coin"),
    "(": ("background", "cloud_left"),
    ")": ("background", "cloud_right"),
    "b": ("decorations", "bush"),
    "t": ("decorations", "grass"),
    "f": ("decorations", "flower"),
    "n": ("decorations", "fence"),
}

# ASCII legend: character -> (object type, properties)
OBJECT_CHARS: dict[str, tuple[str, dict[str, object]]] = {
    "@": ("player_spawn", {}),
    "w": ("enemy", {"kind": "scorpion"}),
    "e": ("enemy", {"kind": "scorpion", "edge_aware": True}),
    "h": ("enemy", {"kind": "jar"}),
    "v": ("enemy", {"kind": "jinn"}),
    "q": ("enemy", {"kind": "hedgehog"}),
    "a": ("enemy", {"kind": "bat"}),
    "g": ("enemy", {"kind": "ghul"}),
    "o": ("drum", {}),
    "!": ("spikes", {}),
    "K": ("checkpoint", {}),
    "F": ("goal", {"style": "gate"}),
    "X": ("goal", {"style": "sword"}),
}


@dataclass(frozen=True)
class Platform:
    col: int
    row: int
    width_tiles: int
    axis: str
    distance: float
    speed: float


@dataclass(frozen=True)
class DoorDef:
    name: str
    col: int
    row: int
    width_tiles: int
    target_door: str = ""
    target_level: str = ""


@dataclass(frozen=True)
class Zone:
    col: int
    width_tiles: int


@dataclass(frozen=True)
class PropDef:
    kind: str
    col: int
    row: int
    width_tiles: int = 1
    height_tiles: int = 1
    properties: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LevelDef:
    file_name: str
    name: str
    subtitle: str
    next_level: str
    sky: str
    music: str
    rows: tuple[str, ...]
    platforms: tuple[Platform, ...] = ()
    doors: tuple[DoorDef, ...] = ()
    camera_zones: tuple[Zone, ...] = ()
    props: tuple[PropDef, ...] = ()
    switch_period: float = 0.0
    switch_start: str = "sun"


# --- Level sketches ---------------------------------------------------------------
# Legend: see TILE_CHARS / OBJECT_CHARS above. Rows are 17 tiles tall.

LEVEL_1_ROWS = (
    "........................................................................................................................",  # 0
    "........................................................................................................................",  # 1
    ".........................().....................................().....................................()...............",  # 2
    "........().........................................................................()...................................",  # 3
    "............................................()..........................................................................",  # 4
    "........................................................................................................................",  # 5
    "..................?.................................CCCC................................................................",  # 6
    "........................................................................................................................",  # 7
    ".........................................................................................................SSS............",  # 8
    "......................................................................CCCCC.............................SSSS............",  # 9
    "............?...B?BPB.............................BBB?BBBB.....S......=====....................L.......SSSSS............",  # 10
    "..................................[]..........................SS....................CCC...............SSSSSS............",  # 11
    "..........................[]......{}.........................SSS............................[].......SSSSSSS............",  # 12
    "...@..b.t.............w...{}..f...{}..w..w.............b....SSSS..K.nnn.....w...w.......t...{}...w..SSSSSSSS....F..f....",  # 13
    "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG..GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG...GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # 14
    "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD..DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",  # 15
    "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD..DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD...DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",  # 16
)
LEVEL_2_ROWS = (
    "..............................................................................................................SSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",  # 0
    "..............................................................................................................SSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",  # 1
    "......()..........................................()....................................()....................S............................S",  # 2
    "............................()........................................()......................................S............................S",  # 3
    "..............................................................................................................S............................S",  # 4
    "..............................................................................................................S............................S",  # 5
    "......................................CCCCC...................................................................S............................S",  # 6
    "......................................=====...................................................................S............................S",  # 7
    "..............................................................................................................S............................S",  # 8
    "......................CCCC....................................................................................S....CCCCCCCCCCCCCCCCCC......S",  # 9
    "................................=====...............................................B?BPB..........S..........S............................S",  # 10
    "..........................................................[]......................................SS..........S....CCCCCCCCCCCCCCCCCC......S",  # 11
    "............................................[]............{}.....................................SSS..........S.........................[].S",  # 12
    "..@.....b.....t.....................h....h..{}...K........{}......................w..w..........SSSS....F.....S.........................{}.S",  # 13
    "GGGGGGGGGGGGGGGGGGGG........GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG............GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",  # 14
    "DDDDDDDDDDDDDDDDDDDD........DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD............DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",  # 15
    "DDDDDDDDDDDDDDDDDDDD........DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD............DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",  # 16
)
LEVEL_3_ROWS = (
    "..................................................................................................................................",  # 0
    "..................................................................................................................................",  # 1
    "............()...............................().................................()............................()..................",  # 2
    "..............................()...............................................................().................................",  # 3
    "..................................................................................................................................",  # 4
    "..................................................................................................................................",  # 5
    "....................................................L.............................................................................",  # 6
    "..................................................................................................................................",  # 7
    "....................................v............................................................................SSS..............",  # 8
    ".......e....................v............CCCC...................................................................SSSS..............",  # 9
    ".....SSSSSS...................BBPBB........v................................................?B?B?..............SSSSS..............",  # 10
    "....................................................S...........[]............................................SSSSSS..............",  # 11
    "....................................................S...........{}...........................................SSSSSSS..............",  # 12
    "..@.......t.............b......................K....S..h....h...{}.....................K....w.w.w...........SSSSSSSS......X.......",  # 13
    "GGGGGGGGGGGGGGG........GGGGGGGGGGGGGGGGGG....GGGGGGGGGGGGGGGGGGGGGGGGGG..............GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # 14
    "DDDDDDDDDDDDDDD........DDDDDDDDDDDDDDDDDD....DDDDDDDDDDDDDDDDDDDDDDDDDD..............DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",  # 15
    "DDDDDDDDDDDDDDD........DDDDDDDDDDDDDDDDDD....DDDDDDDDDDDDDDDDDDDDDDDDDD..............DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",  # 16
)


def _campaign_rows(
    width: int,
    gaps: tuple[tuple[int, int], ...],
    checkpoints: tuple[int, ...],
    enemies: tuple[tuple[int, str], ...],
    coins: tuple[int, ...],
    blocks: tuple[tuple[int, str], ...],
    steps: tuple[tuple[int, int], ...] = (),
    switch_spans: tuple[tuple[int, int, int, str], ...] = (),
    final: bool = False,
) -> tuple[str, ...]:
    """Create a long readable course from a few authored encounter markers.

    The bottom three rows are the floor. Gaps are deliberately authored as
    intervals so every long level can mix safe running, jumps, and platform
    timing without maintaining thousands of hand-written CSV cells.
    """
    grid = [["."] * width for _ in range(17)]

    def in_gap(column: int) -> bool:
        return any(start <= column < end for start, end in gaps)

    def put(column: int, row: int, value: str) -> None:
        if 0 <= column < width and 0 <= row < 17 and grid[row][column] == ".":
            grid[row][column] = value

    for column in range(width):
        if not in_gap(column):
            grid[14][column] = "G"
            grid[15][column] = "D"
            grid[16][column] = "D"

    # The horizon gives long stretches of scenery a little visual rhythm.
    for column in range(10, width - 4, 29):
        put(column, 2, "(")
        put(column + 1, 2, ")")
    for column in range(23, width - 8, 47):
        put(column, 3, "(")
        put(column + 1, 3, ")")

    put(2, 13, "@")
    for column in checkpoints:
        if not in_gap(column):
            put(column, 13, "K")
    put(width - 4, 13, "X" if final else "F")

    for column in coins:
        if not in_gap(column):
            put(column, 11 - (column // 7 % 3), "C")
    for start, end in gaps:
        # Coin arcs show the intended jump line over every early pit.
        for column in range(max(3, start - 1), min(width - 3, end + 1)):
            if not in_gap(column):
                put(column, 10 + abs(column - (start + end - 1) // 2), "C")

    for column, value in blocks:
        if in_gap(column):
            continue
        put(column, 10, value)
        if value in {"?", "P", "N"} and not in_gap(column + 1):
            put(column + 1, 10, "B")

    for base, height in steps:
        for offset in range(height):
            put(base + offset, 13 - offset, "S")
            put(base + offset + 1, 13 - offset, "S")

    for start, end, row, value in switch_spans:
        for column in range(start, min(end, width)):
            # Never place a timed block inside a main-route pit: when active
            # it would become a ceiling directly above the rescue bridge.
            if not in_gap(column):
                put(column, row, value)

    for column, value in enemies:
        if not in_gap(column):
            put(column, 13, value)
    for column in range(12, width - 5, 31):
        if not in_gap(column):
            put(column, 13, "t")

    return tuple("".join(row) for row in grid)


LEVEL_1_ROWS = _campaign_rows(
    190,
    ((30, 32), (67, 69), (105, 108), (145, 147), (174, 178)),
    (58, 120, 160),
    ((18, "w"), (44, "w"), (82, "e"), (96, "w"), (128, "h"), (138, "w"), (163, "e"), (180, "w")),
    (14, 22, 42, 52, 74, 89, 101, 124, 134, 156, 169, 184),
    ((36, "?"), (48, "P"), (86, "?"), (116, "?"), (151, "L"), (171, "?")),
    ((74, 2), (121, 2), (157, 3)),
)

LEVEL_2_ROWS = _campaign_rows(
    230,
    ((24, 27), (52, 56), (83, 87), (118, 123), (153, 158), (190, 195), (217, 222)),
    (63, 132, 180),
    ((16, "w"), (39, "h"), (70, "e"), (101, "w"), (111, "h"), (144, "w"), (169, "e"),
     (183, "h"), (207, "w"), (224, "e")),
    (12, 20, 43, 61, 76, 98, 115, 137, 151, 174, 187, 211, 226),
    ((31, "?"), (45, "P"), (73, "?"), (106, "?"), (141, "N"), (175, "?"), (204, "L")),
    ((34, 2), (91, 3), (160, 3), (201, 2)),
)

LEVEL_3_ROWS = _campaign_rows(
    270,
    ((25, 29), (57, 62), (91, 96), (126, 131), (164, 169), (201, 206), (239, 244)),
    (70, 145, 218),
    ((15, "w"), (38, "q"), (65, "v"), (80, "w"), (104, "h"), (115, "v"), (139, "q"),
     (155, "a"), (180, "w"), (193, "v"), (218, "q"), (231, "a"), (257, "w")),
    (14, 31, 46, 67, 79, 102, 113, 136, 150, 177, 190, 216, 230, 254, 264),
    ((34, "P"), (68, "?"), (108, "N"), (143, "?"), (185, "?"), (224, "P"), (252, "L")),
    ((41, 3), (99, 3), (173, 3), (212, 3)),
    ((76, 84, 12, "U"), (86, 95, 12, "M"), (151, 161, 12, "U"), (174, 184, 12, "M")),
)

LEVEL_4_ROWS = _campaign_rows(
    300,
    ((22, 27), (50, 55), (79, 84), (110, 115), (143, 148), (177, 182), (213, 218), (253, 258), (282, 287)),
    (66, 135, 204, 265),
    ((14, "w"), (31, "q"), (45, "a"), (62, "v"), (73, "h"), (97, "w"), (108, "q"), (130, "a"),
     (147, "v"), (163, "h"), (191, "q"), (205, "a"), (229, "v"), (242, "q"), (270, "a"), (294, "w")),
    tuple(range(12, 296, 13)),
    ((29, "P"), (60, "?"), (94, "N"), (128, "?"), (162, "P"), (196, "?"), (238, "N"), (274, "L")),
    ((34, 3), (88, 3), (154, 3), (224, 3), (270, 2)),
    ((71, 80, 12, "U"), (83, 92, 12, "M"), (137, 147, 12, "U"), (190, 201, 12, "M"),
     (235, 245, 12, "U")),
)

LEVEL_5_ROWS = _campaign_rows(
    330,
    ((20, 25), (47, 52), (73, 78), (101, 106), (131, 136), (163, 168), (198, 203), (235, 240),
     (270, 275), (306, 311)),
    (61, 124, 190, 255),
    ((13, "w"), (28, "q"), (41, "a"), (57, "v"), (69, "g"), (88, "h"), (106, "q"), (119, "a"),
     (137, "v"), (153, "g"), (176, "q"), (188, "a"), (215, "v"), (229, "g"), (253, "q"), (267, "a"),
     (291, "v"), (303, "q"), (322, "a")),
    tuple(range(10, 327, 11)),
    ((26, "P"), (55, "?"), (84, "N"), (116, "?"), (149, "P"), (181, "?"), (218, "N"), (247, "?"), (279, "P"), (311, "L")),
    ((32, 3), (69, 3), (121, 3), (259, 3), (298, 2)),
    ((61, 71, 12, "U"), (74, 84, 12, "M"), (126, 137, 12, "U"), (153, 164, 12, "M"),
     (207, 219, 12, "U"), (242, 254, 12, "M"), (286, 298, 12, "U")),
)

LEVEL_6_ROWS = _campaign_rows(
    360,
    ((19, 24), (45, 50), (70, 75), (97, 102), (126, 131), (157, 162), (190, 195), (226, 231),
     (263, 268), (300, 305), (338, 343)),
    (58, 118, 181, 246, 310),
    ((12, "w"), (25, "q"), (39, "a"), (55, "v"), (68, "g"), (86, "h"), (103, "q"), (116, "a"),
     (139, "v"), (151, "g"), (173, "q"), (187, "a"), (209, "v"), (223, "g"), (246, "q"), (259, "a"),
     (281, "v"), (296, "g"), (317, "q"), (329, "a"), (351, "w")),
    tuple(range(10, 358, 10)),
    ((23, "P"), (52, "N"), (82, "?"), (113, "P"), (145, "N"), (178, "?"), (211, "P"), (244, "N"),
     (276, "?"), (309, "P"), (340, "L")),
    ((31, 3), (66, 3), (119, 3), (171, 3), (230, 3), (287, 3), (325, 2)),
    ((57, 68, 12, "U"), (71, 82, 12, "M"), (110, 122, 12, "U"), (146, 158, 12, "M"),
     (205, 218, 12, "U"), (242, 255, 12, "M"), (274, 287, 12, "U"), (315, 328, 12, "M")),
    final=True,
)


def _gap_bridges(rows: tuple[str, ...]) -> tuple[Platform, ...]:
    """Guarantee a reachable landing surface for every authored floor gap.

    Moving platforms are used for bonus routes, but the main path must never
    depend on catching one at exactly the right phase. These low bridges sit
    two tiles above the floor, comfortably within the player's normal jump arc.
    """
    terrain = rows[14]
    gaps: list[tuple[int, int]] = []
    start: int | None = None
    for column, tile in enumerate(terrain + "G"):
        if tile != "G" and start is None:
            start = column
        elif tile == "G" and start is not None:
            gaps.append((start, column))
            start = None
    bridges = []
    for start, end in gaps:
        # Extend onto solid ground on both sides. This gives the player a
        # generous landing window instead of requiring a pixel-perfect jump
        # at the exact edge of a pit (and keeps water crossings forgiving).
        bridge_start = max(0, start - 2)
        bridge_end = min(len(terrain), end + 2)
        bridges.append(
            Platform(bridge_start, 12, bridge_end - bridge_start, "horizontal", 0.0, 0.0)
        )
    return tuple(bridges)


LEVELS = (
    LevelDef(
        "level1.tmx", "Gardens of Qurtuba", "Learn the rhythm of running, jumping, and spring drums",
        "level2.tmx", "dawn", "level1", LEVEL_1_ROWS,
        platforms=_gap_bridges(LEVEL_1_ROWS) + (
            Platform(43, 11, 3, "vertical", 3, 60), Platform(92, 11, 3, "horizontal", 4, 70),
            Platform(152, 11, 3, "vertical", 3, 70),
        ),
        props=(PropDef("drum", 23, 13), PropDef("drum", 91, 13)),
    ),
    LevelDef(
        "level2.tmx", "Rooftops of Ishbiliya", "Choose your route and read the fountains",
        "level3.tmx", "sunset", "level2", LEVEL_2_ROWS,
        platforms=_gap_bridges(LEVEL_2_ROWS) + (
            Platform(39, 11, 3, "horizontal", 4, 75), Platform(96, 11, 3, "vertical", 4, 70),
            Platform(174, 11, 3, "horizontal", 5, 85),
        ),
        doors=(DoorDef("rooftop_shortcut", 99, 13, 1, target_door="hidden_terrace"), DoorDef("hidden_terrace", 178, 13, 1)),
        props=(PropDef("water", 118, 13, 5, 2), PropDef("fountain", 151, 13, 1, 5, {"on": 2.0, "off": 1.6, "phase": 0.4})),
    ),
    LevelDef(
        "level3.tmx", "The Red Fortress", "Master moving walls before the fortress closes",
        "level4.tmx", "night", "level3", LEVEL_3_ROWS,
        platforms=_gap_bridges(LEVEL_3_ROWS) + (
            Platform(42, 11, 3, "vertical", 4, 80), Platform(100, 11, 3, "horizontal", 5, 90),
            Platform(177, 11, 3, "vertical", 4, 95), Platform(226, 11, 3, "horizontal", 5, 100),
        ),
        props=(PropDef("spikes", 74, 13, 2), PropDef("spikes", 153, 13, 2), PropDef("wind", 184, 8, 5, 5, {"strength": -120.0, "on": 2.5, "off": 1.5})),
        switch_period=9.0,
    ),
    LevelDef(
        "level4.tmx", "Aqueducts of Granada", "Time fountains, drums, and the moonlit gaps",
        "level5.tmx", "mountain", "level4", LEVEL_4_ROWS,
        platforms=_gap_bridges(LEVEL_4_ROWS) + tuple(
            Platform(col, 11, 3, "horizontal" if col % 3 else "vertical", 5, 100)
            for col in (39, 96, 156, 224, 270)
        ),
        props=(
            PropDef("water", 110, 13, 5, 2), PropDef("fountain", 143, 13, 1, 6, {"on": 1.8, "off": 1.8}),
            PropDef("drum", 91, 13), PropDef("spikes", 190, 13, 3), PropDef("wind", 220, 8, 6, 5, {"strength": 150.0, "on": 2.0, "off": 1.0}),
        ),
        switch_period=7.5,
    ),
    LevelDef(
        "level5.tmx", "The Clockwork Alcazar", "Every opening is temporary",
        "level6.tmx", "clockwork", "level5", LEVEL_5_ROWS,
        platforms=_gap_bridges(LEVEL_5_ROWS) + tuple(
            Platform(col, 11, 3, "vertical" if col % 3 else "horizontal", 5, 110)
            for col in (38, 93, 151, 216, 282)
        ),
        props=(
            PropDef("spikes", 101, 13, 4), PropDef("spikes", 198, 13, 4), PropDef("fountain", 235, 13, 1, 6, {"on": 1.4, "off": 2.0}),
            PropDef("wind", 286, 7, 8, 6, {"strength": -180.0, "on": 1.5, "off": 1.2}),
        ),
        switch_period=5.5,
    ),
    LevelDef(
        "level6.tmx", "Summit of the Sword", "The final crossing demands everything you learned",
        "", "court", "level6", LEVEL_6_ROWS,
        platforms=_gap_bridges(LEVEL_6_ROWS) + tuple(
            Platform(col, 11, 3, "horizontal" if col % 3 else "vertical", 5, 120)
            for col in (36, 91, 149, 212, 276, 324)
        ),
        props=(
            PropDef("spikes", 126, 13, 5), PropDef("spikes", 226, 13, 5), PropDef("spikes", 300, 13, 5),
            PropDef("wind", 240, 7, 10, 6, {"strength": 190.0, "on": 1.2, "off": 1.0}),
        ),
        switch_period=4.5,
    ),
)


# --- Writers --------------------------------------------------------------------
def write_tileset_image(path: Path) -> None:
    rows = -(-len(TILESET) // TILESET_COLUMNS)
    sheet = pygame.Surface((TILESET_COLUMNS * T, rows * T), pygame.SRCALPHA)
    for index, tile in enumerate(TILESET):
        x, y = (index % TILESET_COLUMNS) * T, (index // TILESET_COLUMNS) * T
        sheet.blit(placeholder_art.make_tile(tile.name), (x, y))
    pygame.image.save(sheet, path)


def write_tileset_tsx(path: Path, image_path: str) -> None:
    rows = -(-len(TILESET) // TILESET_COLUMNS)
    root = ElementTree.Element(
        "tileset",
        version=TMX_VERSION, tiledversion=TILED_VERSION, name="tileset",
        tilewidth=str(T), tileheight=str(T),
        tilecount=str(rows * TILESET_COLUMNS), columns=str(TILESET_COLUMNS),
    )
    ElementTree.SubElement(
        root, "image", source=image_path,
        width=str(TILESET_COLUMNS * T), height=str(rows * T),
    )
    for index, tile in enumerate(TILESET):
        element = ElementTree.SubElement(root, "tile", id=str(index))
        _add_properties(element, {"name": tile.name, **tile.properties})
    _write_xml(root, path)


def _add_properties(element: ElementTree.Element, properties: dict[str, object]) -> None:
    if not properties:
        return
    container = ElementTree.SubElement(element, "properties")
    for key, value in properties.items():
        attributes = {"name": key}
        if isinstance(value, bool):
            attributes.update(type="bool", value="true" if value else "false")
        elif isinstance(value, int):
            attributes.update(type="int", value=str(value))
        elif isinstance(value, float):
            attributes.update(type="float", value=repr(value))
        else:
            attributes["value"] = str(value)
        ElementTree.SubElement(container, "property", attributes)


def _write_xml(root: ElementTree.Element, path: Path) -> None:
    ElementTree.indent(root, space=" ")
    tree = ElementTree.ElementTree(root)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def build_level(level: LevelDef) -> ElementTree.Element:
    height = len(level.rows)
    width = max(len(row) for row in level.rows)
    layers = {name: [0] * (width * height) for name in LAYER_ORDER}
    objects: list[tuple[str, str, tuple[int, int, int, int], dict[str, object]]] = []

    for y, row in enumerate(level.rows):
        for x, char in enumerate(row):
            if char == ".":
                continue
            if char in TILE_CHARS:
                layer, tile = TILE_CHARS[char]
                layers[layer][y * width + x] = TILE_IDS[tile] + 1  # gid = id + firstgid
            elif char in OBJECT_CHARS:
                kind, properties = OBJECT_CHARS[char]
                objects.append((kind, "", (x * T, y * T, T, T), properties))
            else:
                raise ValueError(f"{level.file_name}: unknown character {char!r} at ({x}, {y})")

    for platform in level.platforms:
        rect = (platform.col * T, platform.row * T, platform.width_tiles * T, PLATFORM_HEIGHT)
        properties = {"axis": platform.axis, "distance": float(platform.distance), "speed": float(platform.speed)}
        objects.append(("moving_platform", "", rect, properties))
    for door in level.doors:
        properties = {"target_door": door.target_door, "target_level": door.target_level}
        properties = {key: value for key, value in properties.items() if value}
        objects.append(("door", door.name, (door.col * T, door.row * T, door.width_tiles * T, T), properties))
    for zone in level.camera_zones:
        objects.append(("camera_zone", "", (zone.col * T, 0, zone.width_tiles * T, height * T), {}))
    for prop in level.props:
        properties = dict(prop.properties)
        objects.append(
            (
                prop.kind,
                "",
                (prop.col * T, prop.row * T, prop.width_tiles * T, prop.height_tiles * T),
                properties,
            )
        )

    if not any(kind == "player_spawn" for kind, *_ in objects):
        raise ValueError(f"{level.file_name}: no player spawn '@'")

    root = ElementTree.Element(
        "map",
        version=TMX_VERSION, tiledversion=TILED_VERSION, orientation="orthogonal",
        renderorder="right-down", width=str(width), height=str(height),
        tilewidth=str(T), tileheight=str(T), infinite="0",
        nextlayerid=str(len(LAYER_ORDER) + 2), nextobjectid=str(len(objects) + 1),
    )
    map_properties: dict[str, object] = {
        "name": level.name, "subtitle": level.subtitle, "sky": level.sky, "music": level.music,
    }
    if level.switch_period > 0:
        map_properties["switch_period"] = level.switch_period
        map_properties["switch_start"] = level.switch_start
    if level.next_level:
        map_properties["next_level"] = level.next_level
    _add_properties(root, map_properties)
    ElementTree.SubElement(root, "tileset", firstgid="1", source=TILESET_FILE)

    for layer_id, name in enumerate(LAYER_ORDER, start=1):
        layer = ElementTree.SubElement(
            root, "layer", id=str(layer_id), name=name, width=str(width), height=str(height)
        )
        data = ElementTree.SubElement(layer, "data", encoding="csv")
        cells = layers[name]
        lines = [",".join(str(gid) for gid in cells[y * width:(y + 1) * width]) for y in range(height)]
        data.text = "\n" + ",\n".join(lines) + "\n"

    group = ElementTree.SubElement(root, "objectgroup", id=str(len(LAYER_ORDER) + 1), name="entities")
    for object_id, (kind, name, (x, y, w, h), properties) in enumerate(objects, start=1):
        element = ElementTree.SubElement(
            group, "object", id=str(object_id), name=name, type=kind,
            x=str(x), y=str(y), width=str(w), height=str(h),
        )
        _add_properties(element, properties)
    return root


def export_sprite_templates(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for spec in ALL_SHEETS:
        pygame.image.save(build_placeholder_sheet(spec), directory / spec.image_path)
    print(f"Sprite templates written to {directory}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="overwrite existing .tmx files without asking")
    parser.add_argument("--export-sprites", action="store_true", help="also export sprite sheet templates")
    args = parser.parse_args()

    existing = [level.file_name for level in LEVELS if (MAPS_DIR / level.file_name).exists()]
    if existing and not args.force:
        answer = input(f"Overwrite {', '.join(existing)}? Edits made in Tiled will be lost [y/N] ")
        if answer.strip().lower() != "y":
            print("Aborted.")
            return 1

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    write_tileset_image(IMAGES_DIR / TILESET_IMAGE)
    # The .tsx lives next to the maps, so its image path is relative to maps/.
    write_tileset_tsx(MAPS_DIR / TILESET_FILE, f"../images/{TILESET_IMAGE}")
    for level in LEVELS:
        _write_xml(build_level(level), MAPS_DIR / level.file_name)
        print(f"Wrote {MAPS_DIR / level.file_name}")
    if args.export_sprites:
        export_sprite_templates(IMAGES_DIR / "templates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
