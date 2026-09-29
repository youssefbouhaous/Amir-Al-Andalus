"""Level authoring format and Tiled (.tmx) writer.

Levels are written in Python as ASCII *segments* placed side by side. Every
character is a tile or an object; digits and other free characters are
per-segment *marks* that place a richer object (a swinging lamp, a wheel, a
sign) exactly where the character sits. That keeps the geometry readable in a
code review while still producing ordinary Tiled maps, which can then be
edited visually.

Common legend (a level can override or extend it):

    .  empty                    #  surface terrain (theme)   %  fill terrain
    =  one-way ledge            -  second one-way style      |  solid pillar
    B  brick   ?  zellige coin   P  pomegranate   L  oil lamp (1-UP)
    N  najma (star power)       M  multi-coin    X  crumbling slab
    U  sun block   O  moon block   T  sun/moon toggle block
    C  dinar coin               ^  spikes        ~  deep water
    @  player spawn   K  checkpoint   G  exit gate   S  the sword
    w  scorpion   e  ledge-wise scorpion   j  clay jar   i  jinn wisp
    h  hedgehog   b  bat   g  ghul          o  darbuka drum
    ,  "air" that decoration never uses (keeps paths clear)
"""

import random
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from core import settings

T = settings.TILE_SIZE
TILESET_FILE = "tileset.tsx"
TILESET_IMAGE = "tileset.png"
TILESET_COLUMNS = 8
TILED_VERSION = "1.10.2"
TMX_VERSION = "1.10"

ONE_WAY = {"collision": "one_way"}

# Order = tile id in the tileset. Append new tiles at the end so existing
# maps keep their ids.
TILESET: tuple[tuple[str, dict[str, str]], ...] = (
    ("ground", {}),
    ("dirt", {}),
    ("stone", {}),
    ("brick", {"spawn": "brick"}),
    ("question", {"spawn": "question", "contents": "coin"}),
    ("question_powerup", {"spawn": "question", "contents": "powerup"}),
    ("question_life", {"spawn": "question", "contents": "extra_life"}),
    ("coin", {"spawn": "coin"}),
    ("used_block", {}),
    ("platform", ONE_WAY),
    ("pipe_top_left", {}),
    ("pipe_top_right", {}),
    ("pipe_left", {}),
    ("pipe_right", {}),
    ("cloud_left", {}),
    ("cloud_right", {}),
    ("bush", {}),
    ("grass", {}),
    ("flower", {}),
    ("fence", {}),
    ("question_star", {"spawn": "question", "contents": "star"}),
    ("sun_block", {"spawn": "switch_block", "color": "sun"}),
    ("moon_block", {"spawn": "switch_block", "color": "moon"}),
    # --- themed terrain and blocks ---
    ("marble", {}),
    ("ashlar", {}),
    ("roof", {}),
    ("plaster", {}),
    ("wood", {}),
    ("mudejar", {}),
    ("rock", {}),
    ("ice", {}),
    ("red_wall", {}),
    ("palace", {}),
    ("court", {}),
    ("awning", ONE_WAY),
    ("shelf", ONE_WAY),
    ("ledge", ONE_WAY),
    ("bridge", ONE_WAY),
    ("crumble", {"spawn": "crumble"}),
    ("question_multi", {"spawn": "question", "contents": "multicoin"}),
    ("switch_toggle", {"spawn": "switch_toggle"}),
    ("tuft", {}),
    ("rock_small", {}),
    ("books", {}),
    ("vase", {}),
)
TILE_IDS = {name: index for index, (name, _) in enumerate(TILESET)}
# Tiles whose art lives under another painter name.
TILE_ART = {"question_multi": "question", "switch_toggle": "question_star"}

LAYERS = ("background", "terrain", "blocks", "collectibles", "decorations", "foreground")
BLOCK_TILES = frozenset({
    "brick", "question", "question_powerup", "question_life", "question_star", "question_multi",
    "sun_block", "moon_block", "crumble", "switch_toggle",
})


@dataclass(frozen=True)
class Obj:
    """An object placed relative to a mark (or to its segment's origin)."""

    kind: str
    dx: float = 0
    dy: float = 0
    w: float = 1
    h: float = 1
    name: str = ""
    props: dict[str, object] = field(default_factory=dict)
    # Polyline points in tiles, relative to the object's position.
    points: tuple[tuple[float, float], ...] = ()


def O(kind: str, dx: float = 0, dy: float = 0, w: float = 1, h: float = 1, name: str = "",
      points: Iterable[tuple[float, float]] = (), **props: object) -> Obj:  # noqa: N802
    return Obj(kind, dx, dy, w, h, name, dict(props), tuple(points))


@dataclass
class Segment:
    rows: list[str]
    marks: dict[str, Obj | list[Obj]] = field(default_factory=dict)
    # Objects in tile coordinates relative to the segment's top-left.
    objects: list[tuple[float, float, Obj]] = field(default_factory=list)
    # Rectangles (x, y, w, h in tiles) painted with a backdrop style.
    backdrops: list[tuple[int, int, int, int, str]] = field(default_factory=list)
    # A closed bonus room: gets its own camera zone.
    room: bool = False

    @property
    def width(self) -> int:
        return max(len(row) for row in self.rows)

    def padded(self, height: int) -> "Segment":
        missing = height - len(self.rows)
        if missing <= 0:
            return self
        rows = ["." * self.width] * missing + list(self.rows)
        objects = [(x, y + missing, obj) for x, y, obj in self.objects]
        backdrops = [(x, y + missing, w, h, style) for x, y, w, h, style in self.backdrops]
        return Segment(rows, self.marks, objects, backdrops, self.room)


@dataclass
class Terrain:
    surface: str = "ground"
    fill: str = "dirt"
    ledge: str = "platform"
    ledge2: str = "awning"
    pillar: str = "stone"


@dataclass
class LevelDef:
    file_name: str
    name: str
    subtitle: str
    theme: str
    music: str
    next_level: str
    segments: list[Segment]
    terrain: Terrain = field(default_factory=Terrain)
    properties: dict[str, object] = field(default_factory=dict)
    # Extra single-character legend entries: char -> tile name or Obj.
    legend: dict[str, str | Obj] = field(default_factory=dict)
    decorate: bool = True
    seed: int = 1
    height: int = 18


# Big area objects that decoration may overlap.
UNRESERVED_KINDS = frozenset({"camera_zone", "wind", "water", "boss_arena"})

ENEMY_CHARS = {
    "w": {"kind": "scorpion"},
    "e": {"kind": "scorpion", "edge_aware": True},
    "j": {"kind": "jar"},
    "i": {"kind": "jinn"},
    "h": {"kind": "hedgehog"},
    "b": {"kind": "bat"},
    "g": {"kind": "ghul"},
}
BLOCK_CHARS = {
    "B": "brick", "?": "question", "P": "question_powerup", "L": "question_life", "N": "question_star",
    "M": "question_multi", "U": "sun_block", "O": "moon_block", "X": "crumble", "T": "switch_toggle",
}
OBJECT_CHARS: dict[str, Obj] = {
    "@": O("player_spawn"),
    "K": O("checkpoint"),
    "G": Obj("goal", props={"style": "gate"}),
    "S": Obj("goal", props={"style": "sword"}),
    "o": O("drum"),
}


# --- Building ---------------------------------------------------------------------
class _Map:
    def __init__(self, level: LevelDef) -> None:
        self.level = level
        self.segments = [segment.padded(level.height) for segment in level.segments]
        heights = {len(segment.rows) for segment in self.segments}
        if heights != {level.height}:
            raise ValueError(f"{level.file_name}: segment heights {sorted(heights)} != {level.height}")
        self.height = level.height
        self.width = sum(segment.width for segment in self.segments)
        self.grid = [["."] * self.width for _ in range(self.height)]
        self.layers = {name: [0] * (self.width * self.height) for name in LAYERS}
        self.objects: list[tuple[str, str, tuple[float, float, float, float], dict[str, object], tuple]] = []
        self.backdrops: list[tuple[int, int, int, int, str]] = []
        self.reserved: set[tuple[int, int]] = set()

    def build(self) -> None:
        x0 = 0
        main_end: int | None = None
        for segment in self.segments:
            if segment.room:
                if main_end is None:
                    main_end = x0
                self.add_obj(O("camera_zone", w=segment.width, h=self.height), x0, 0)
            for y, row in enumerate(segment.rows):
                for x, char in enumerate(row.ljust(segment.width, ".")):
                    self.grid[y][x0 + x] = char
            for y, row in enumerate(segment.rows):
                for x, char in enumerate(row):
                    if char in segment.marks:
                        marks = segment.marks[char]
                        for obj in marks if isinstance(marks, list) else [marks]:
                            self.add_obj(obj, x0 + x, y)
                        self.grid[y][x0 + x] = "."
            for ox, oy, obj in segment.objects:
                self.add_obj(obj, x0 + ox, oy)
            for bx, by, bw, bh, style in segment.backdrops:
                self.backdrops.append((x0 + bx, by, bw, bh, style))
            x0 += segment.width
        if main_end is not None:
            self.add_obj(O("camera_zone", w=main_end, h=self.height), 0, 0)
        self._paint()
        self._water()
        if self.level.decorate:
            self._decorate()

    def add_obj(self, obj: Obj, tx: float, ty: float) -> None:
        x, y = (tx + obj.dx) * T, (ty + obj.dy) * T
        points = tuple(((tx + obj.dx + px) * T, (ty + obj.dy + py) * T) for px, py in obj.points)
        self.objects.append((obj.kind, obj.name, (x, y, obj.w * T, obj.h * T), dict(obj.props), points))
        if obj.kind in UNRESERVED_KINDS:
            return
        for cx in range(int(tx + obj.dx), int(tx + obj.dx + max(1, obj.w))):
            for cy in range(int(ty + obj.dy), int(ty + obj.dy + max(1, obj.h))):
                self.reserved.add((cx, cy))

    def set_tile(self, layer: str, x: int, y: int, name: str) -> None:
        self.layers[layer][y * self.width + x] = TILE_IDS[name] + 1

    def char(self, x: int, y: int) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return "#" if 0 <= y else "."

    def _paint(self) -> None:
        terrain = self.level.terrain
        legend = self.level.legend
        for y in range(self.height):
            for x in range(self.width):
                char = self.grid[y][x]
                if char in (".", ",", "~"):
                    continue
                custom = legend.get(char)
                if isinstance(custom, str):
                    layer = "terrain"
                    if custom in BLOCK_TILES:
                        layer = "blocks"
                    elif custom in ("tuft", "rock_small", "books", "vase", "bush", "grass", "flower", "fence"):
                        layer = "decorations"
                    self.set_tile(layer, x, y, custom)
                elif isinstance(custom, Obj):
                    self.add_obj(custom, x, y)
                elif char == "#":
                    above = self.char(x, y - 1)
                    self.set_tile("terrain", x, y, terrain.fill if above in ("#", "%") else terrain.surface)
                elif char == "%":
                    self.set_tile("terrain", x, y, terrain.fill)
                elif char == "|":
                    self.set_tile("terrain", x, y, terrain.pillar)
                elif char == "=":
                    self.set_tile("terrain", x, y, terrain.ledge)
                elif char == "-":
                    self.set_tile("terrain", x, y, terrain.ledge2)
                elif char in BLOCK_CHARS:
                    self.set_tile("blocks", x, y, BLOCK_CHARS[char])
                elif char == "C":
                    self.set_tile("collectibles", x, y, "coin")
                elif char == "^":
                    self.add_obj(O("spikes"), x, y)
                elif char in ENEMY_CHARS:
                    self.add_obj(Obj("enemy", props=dict(ENEMY_CHARS[char])), x, y)
                elif char in OBJECT_CHARS:
                    self.add_obj(OBJECT_CHARS[char], x, y)
                else:
                    raise ValueError(f"{self.level.file_name}: unknown character {char!r} at ({x}, {y})")

    def _water(self) -> None:
        """Merge runs of '~' into water objects (one per horizontal run)."""
        for y in range(self.height):
            x = 0
            while x < self.width:
                if self.grid[y][x] == "~" and (y == 0 or self.grid[y - 1][x] != "~"):
                    start = x
                    while x < self.width and self.grid[y][x] == "~" and (y == 0 or self.grid[y - 1][x] != "~"):
                        x += 1
                    depth = 1
                    while y + depth < self.height and self.grid[y + depth][start] == "~":
                        depth += 1
                    # Water extends to the map bottom so falling in is final.
                    self.add_obj(O("water", w=x - start, h=self.height - y), start, y)
                    continue
                x += 1

    def _surface_cells(self) -> list[tuple[int, int]]:
        """Empty cells directly above terrain surfaces, free for decoration."""
        cells = []
        for y in range(1, self.height):
            for x in range(self.width):
                if self.grid[y][x] == "#" and self.grid[y - 1][x] == "." and (x, y - 1) not in self.reserved:
                    cells.append((x, y - 1))
        return cells

    def _decorate(self) -> None:
        rng = random.Random(self.level.seed)
        decor = THEME_DECOR.get(self.level.theme, ())
        if not decor:
            return
        taken: set[int] = set()
        for x, y in self._surface_cells():
            clear_above = all(self.char(x, y - k) == "." for k in range(0, 3))
            neighbours_flat = self.char(x - 1, y + 1) == "#" and self.char(x + 1, y + 1) == "#"
            roll = rng.random()
            for kind, chance, needs_room, spacing, props in decor:
                if roll < chance and (clear_above or not needs_room) and neighbours_flat:
                    if any(abs(x - t) < spacing for t in taken):
                        break
                    if kind == "tile":
                        self.set_tile("decorations", x, y, str(props["tile"]))
                    else:
                        props = dict(props)
                        self.add_obj(O("decor", **props), x, y)
                    taken.add(x)
                    break
                roll -= chance


# Automatic set dressing per theme: (kind, chance, needs headroom, spacing, props).
THEME_DECOR: dict[str, tuple[tuple[str, float, bool, int, dict[str, object]], ...]] = {
    "garden": (
        ("decor", 0.05, True, 9, {"style": "orange_tree", "size": 1}),
        ("decor", 0.04, True, 9, {"style": "cypress", "height": 120}),
        ("tile", 0.12, False, 2, {"tile": "tuft"}),
        ("tile", 0.05, False, 3, {"tile": "flower"}),
        ("tile", 0.04, False, 3, {"tile": "grass"}),
    ),
    "palace": (
        ("decor", 0.05, True, 8, {"style": "palm", "height": 130}),
        ("decor", 0.04, True, 8, {"style": "urn"}),
        ("tile", 0.06, False, 3, {"tile": "vase"}),
        ("tile", 0.06, False, 3, {"tile": "flower"}),
    ),
    "clockwork": (
        ("decor", 0.04, True, 10, {"style": "cypress", "height": 110}),
        ("tile", 0.08, False, 3, {"tile": "rock_small"}),
        ("tile", 0.05, False, 3, {"tile": "books"}),
    ),
    "rooftops": (
        ("tile", 0.1, False, 3, {"tile": "flower"}),
        ("tile", 0.05, False, 3, {"tile": "vase"}),
        ("decor", 0.03, True, 12, {"style": "palm", "height": 110}),
    ),
    "mountain": (
        ("decor", 0.035, True, 10, {"style": "cypress", "height": 100}),
        ("tile", 0.1, False, 2, {"tile": "rock_small"}),
    ),
    "fortress": (
        ("tile", 0.08, False, 3, {"tile": "rock_small"}),
        ("decor", 0.03, True, 12, {"style": "cypress", "height": 110}),
    ),
    "court": (
        ("tile", 0.06, False, 3, {"tile": "vase"}),
    ),
}


# --- Writers ----------------------------------------------------------------------
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


def write_xml(root: ElementTree.Element, path: Path) -> None:
    ElementTree.indent(root, space=" ")
    ElementTree.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def write_tileset_image(path: Path) -> None:
    import pygame

    from rendering.art.tiles import make_tile

    rows = -(-len(TILESET) // TILESET_COLUMNS)
    sheet = pygame.Surface((TILESET_COLUMNS * T, rows * T), pygame.SRCALPHA)
    for index, (name, _) in enumerate(TILESET):
        x, y = (index % TILESET_COLUMNS) * T, (index // TILESET_COLUMNS) * T
        sheet.blit(make_tile(TILE_ART.get(name, name)), (x, y))
    pygame.image.save(sheet, path)


def write_tileset_tsx(path: Path, image_path: str) -> None:
    rows = -(-len(TILESET) // TILESET_COLUMNS)
    root = ElementTree.Element(
        "tileset", version=TMX_VERSION, tiledversion=TILED_VERSION, name="tileset",
        tilewidth=str(T), tileheight=str(T), tilecount=str(rows * TILESET_COLUMNS), columns=str(TILESET_COLUMNS),
    )
    ElementTree.SubElement(root, "image", source=image_path, width=str(TILESET_COLUMNS * T), height=str(rows * T))
    for index, (name, properties) in enumerate(TILESET):
        element = ElementTree.SubElement(root, "tile", id=str(index))
        _add_properties(element, {"name": name, **properties})
    write_xml(root, path)


def build_level(level: LevelDef) -> ElementTree.Element:
    level_map = _Map(level)
    level_map.build()
    objects = level_map.objects
    for x, y, w, h, style in level_map.backdrops:
        objects.insert(0, ("backdrop", "", (x * T, y * T, w * T, h * T), {"style": style}, ()))
    if not any(kind == "player_spawn" for kind, *_ in objects):
        raise ValueError(f"{level.file_name}: no player spawn '@'")

    width, height = level_map.width, level_map.height
    root = ElementTree.Element(
        "map", version=TMX_VERSION, tiledversion=TILED_VERSION, orientation="orthogonal",
        renderorder="right-down", width=str(width), height=str(height),
        tilewidth=str(T), tileheight=str(T), infinite="0",
        nextlayerid=str(len(LAYERS) + 2), nextobjectid=str(len(objects) + 1),
    )
    properties: dict[str, object] = {
        "name": level.name, "subtitle": level.subtitle, "theme": level.theme, "music": level.music,
    }
    if level.next_level:
        properties["next_level"] = level.next_level
    properties.update(level.properties)
    _add_properties(root, properties)
    ElementTree.SubElement(root, "tileset", firstgid="1", source=TILESET_FILE)

    for layer_id, name in enumerate(LAYERS, start=1):
        cells = level_map.layers[name]
        if name == "foreground" and not any(cells):
            continue
        layer = ElementTree.SubElement(root, "layer", id=str(layer_id), name=name, width=str(width), height=str(height))
        data = ElementTree.SubElement(layer, "data", encoding="csv")
        lines = [",".join(str(gid) for gid in cells[y * width:(y + 1) * width]) for y in range(height)]
        data.text = "\n" + ",\n".join(lines) + "\n"

    group = ElementTree.SubElement(root, "objectgroup", id=str(len(LAYERS) + 1), name="entities")
    for object_id, (kind, name, (x, y, w, h), props, points) in enumerate(objects, start=1):
        attributes = {"id": str(object_id), "name": name, "type": kind, "x": _num(x), "y": _num(y)}
        if points:
            element = ElementTree.SubElement(group, "object", attributes)
            _add_properties(element, props)
            relative = " ".join(f"{_num(px - x)},{_num(py - y)}" for px, py in points)
            ElementTree.SubElement(element, "polyline", points=relative)
        else:
            attributes.update(width=_num(w), height=_num(h))
            element = ElementTree.SubElement(group, "object", attributes)
            _add_properties(element, props)
    return root


def _num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"
