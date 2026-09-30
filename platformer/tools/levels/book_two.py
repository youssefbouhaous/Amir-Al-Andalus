"""Book II - "The Ifrit's Night" (levels 11+).

When the prince lifted the Sword of Light, the Ifrit sealed inside its
shrine broke free and stole the dawn. Book II follows the prince through
a night that will not end, and each chapter is built around one of his new
moves before the last ones braid them all together:

    11  The Djinn's Bazaar      dash + slide     (lantern roads, blade alleys)
    12  The Swinging Moons      rings + glide    (updrafts, moon orchards)
    13  The Drowned Cistern     rising flood     (a vertical escape)
    14  The Hall of Seven Gates pound + plates   (timed portcullis races)
    15  The Ifrit's Crown       everything       (the storm above Granada)

Levels 1-10 are built by other modules and are never touched here.
Build with ``python -m tools.build_book_two`` and verify with
``python -m tools.check_levels --all-book-two``.
"""

from tools.level_format import LevelDef, O, Segment, Terrain

# Characters shared by every Book II level.
BOOK_TWO_LEGEND = {
    "Z": O("cracked"),
    "*": O("dash_lantern"),
    "/": O("blade_trap"),
    "Q": O("ring", h=3),
    "q": O("ring", h=2),
    # Extra terrain materials: brick, cut stone, palace, fortress, rock, ice, wood.
    "m": "mudejar",
    "a": "ashlar",
    "p": "palace",
    "r": "red_wall",
    "k": "rock",
    "n": "ice",
    "d": "wood",
    "[": "pipe_top_left",
    "]": "pipe_top_right",
    "{": "pipe_left",
    "}": "pipe_right",
}


class Grid:
    """A blank ASCII segment to draw on (for layouts easier to compute than type)."""

    def __init__(self, width: int, height: int) -> None:
        self.cells = [["."] * width for _ in range(height)]

    def put(self, x: int, y: int, char: str) -> "Grid":
        self.cells[y][x] = char
        return self

    def put_all(self, char: str, points: list[tuple[int, int]]) -> "Grid":
        for x, y in points:
            self.put(x, y, char)
        return self

    def fill(self, x: int, y: int, w: int, h: int, char: str) -> "Grid":
        for row in range(y, y + h):
            for col in range(x, x + w):
                self.cells[row][col] = char
        return self

    def rows(self) -> list[str]:
        return ["".join(row) for row in self.cells]


def S(rows: list[str], height: int = 22, **kwargs) -> Segment:  # noqa: N802
    """A Segment whose rows are bottom-aligned to ``height`` and whose
    ``objects``/``backdrops`` use absolute map rows."""
    width = max(len(row) for row in rows)
    padded = ["." * width] * (height - len(rows)) + list(rows)
    return Segment(padded, **kwargs)


def sign(text: str) -> O:
    return O("sign", text=text)


def gate(group: str, height: int) -> O:
    """A portcullis whose *bottom* sits on the mark's row."""
    return O("gate", dy=-(height - 1), h=height, group=group)


def plate(group: str, timer: float = 0.0) -> O:
    return O("pound_plate", group=group, timer=timer)


# ---------------------------------------------------------------------------------------
# 11 - The Djinn's Bazaar
# ---------------------------------------------------------------------------------------
def djinn_bazaar() -> LevelDef:
    street = S(
        [
            "...........................................",  # 10
            "..................CCC......................",  # 11
            "...............C.......C...................",  # 12
            ".............C...........C.................",  # 13
            "...........................................",  # 14
            "...........................................",  # 15
            "...........................................",  # 16
            "..@...1......................2.............",  # 17
            "################.......####################",  # 18
            "################.......####################",  # 19
            "################.......####################",  # 20
            "###########################################",  # 21
        ],
        marks={
            "1": sign("C, L or Ctrl: DASH!\nJump, then dash to cross wide gaps.\nLanding recharges your dash."),
            "2": sign("Hold UP as you dash to fly upward.\nDiagonals work too."),
        },
    )
    tower = S(
        [
            "...........CCCC.........",  # 10
            "........................",  # 11
            "..........mmmmmm........",  # 12
            "..........mmmmmm........",  # 13
            "..........mmmmmm........",  # 14
            "..........mmmmmm........",  # 15
            "..........mmmmmm....j...",  # 16
            "..........mmmmmm........",  # 17
            "########################",  # 18
            "########################",  # 19
            "########################",  # 20
            "########################",  # 21
        ],
        objects=[(9, 12, O("decor", style="lamp", chain=20)), (16, 12, O("decor", style="lamp", chain=28))],
    )
    alley = S(
        [
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 9
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 10
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 11
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 12
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 13
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 14
            ".....1......mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 15
            "............mmmmmmmmmmmmmmmmmmmmmmmm.......",  # 16
            "..............C./..C.w.C.../.C.C./..C......",  # 17
            "###########################################",  # 18
            "###########################################",  # 19
            "###########################################",  # 20
            "###########################################",  # 21
        ],
        marks={"1": sign("Blades at head height!\nRun, then press DOWN to SLIDE under.\nSlides knock enemies flat.")},
        objects=[(x, 9, O("decor", style="banner", color="red" if x % 2 else "blue")) for x in (14, 19, 24, 29, 33)]
        + [(x, 17, O("decor", style="torch", dy=0)) for x in (13, 21, 28, 35)]
        + [(1, 10, O("decor", w=10, h=2, style="garland", count=6))],
    )
    cracked = S(
        [
            "..........................................",  # 10
            "..............ZZZZ........................",  # 11
            "..............Z..Z........................",  # 12
            "..............Z3.Z........................",  # 13
            "..............ZZZZ.......ZZ...............",  # 14
            ".........................ZZ...............",  # 15
            ".........................ZZ...............",  # 16
            "..1.....................ZZZ.....w.........",  # 17
            "##########################################",  # 18
            "##########################################",  # 19
            "##########################################",  # 20
            "##########################################",  # 21
        ],
        marks={
            "1": sign("Cracked sandstone crumbles\nunder a dash, a slide or a pound.\nSomething glints inside that box..."),
            "3": O("page", index=0),
        },
    )
    lanterns = S(
        Grid(64, 14)
        .fill(0, 10, 7, 4, "#").fill(30, 10, 3, 4, "#").fill(60, 10, 4, 4, "#")
        # Lanterns sit on real dash-chain trajectories (flat dashes sink
        # about a tile, diagonal ones climb two), measured with the checker.
        .put_all("*", [(12, 7), (15, 5), (18, 3), (23, 5), (27, 6)])
        .put_all("*", [(37, 4), (41, 5), (44, 3), (49, 5), (53, 6), (56, 4)])
        .put_all("C", [(14, 6), (17, 4), (20, 3), (25, 5), (39, 4), (43, 4), (46, 3), (51, 5), (55, 5)])
        .put(3, 7, "1").put(1, 9, "K").put(31, 9, "K")
        .rows(),
        marks={"1": sign("The Lantern Road.\nTouching a blue lantern gives\nyour dash back in mid-air.")},
    )
    cellar = S(
        [
            "..............................%...............",  # 9
            "..............................%...............",  # 10
            "..............................%...............",  # 11
            "..............................%...............",  # 12
            "..1...........................%...............",  # 13
            "..............................................",  # 14
            "..............................................",  # 15
            "..........................2...................",  # 16
            "......................CC..y...!...............",  # 17
            "########ZZZZ##########==######################",  # 18
            "########......C...C...........################",  # 19
            "########.C..4..C......C.......################",  # 20
            "##############################################",  # 21
        ],
        marks={
            "1": sign("In the air, press DOWN to POUND.\nPounds break cracked floors\nand press bronze plates."),
            "2": sign("A pressed plate opens its portcullis."),
            "4": O("page", index=1),
            "y": plate("bazaar"),
            "!": gate("bazaar", 4),
        },
        objects=[(9, 19, O("decor", style="torch")), (19, 19, O("decor", style="torch")),
                 (35, 12, O("decor", w=9, h=2, style="garland", count=5))],
    )
    finale = S(
        [
            "...............................3.........",  # 6
            "............................*.aaa........",  # 7
            "..............................aaa........",  # 8
            ".........................*....aaa........",  # 9
            "..............................aaa........",  # 10
            "..............................aaa........",  # 11
            ".............mmmmmmmmmmmmm....aaa........",  # 12
            ".............mmmmmmmmmmmmm....aaa........",  # 13
            ".............mmmmmmmmmmmmm....aaa........",  # 14
            ".............mmmmmmmmmmmmm....aaa........",  # 15
            ".............mmmmmmmmmmmmm....aaa........",  # 16
            "...K...........C./.C./.C...........G.....",  # 17
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa##",  # 18
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa##",  # 19
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa##",  # 20
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa##",  # 21
        ],
        marks={"3": O("page", index=2)},
        objects=[(25, 10, O("decor", w=5, h=2, style="garland", count=3)),
                 (2, 12, O("decor", w=11, h=3, style="garland", count=6))]
        + [(x, 12, O("decor", style="banner", color="blue" if x % 2 else "red")) for x in (15, 19, 23)],
    )
    return LevelDef(
        file_name="level11.tmx",
        name="The Djinn's Bazaar",
        subtitle="Book II - the night that would not end",
        theme="rooftops",
        music="level4",
        next_level="level12.tmx",
        segments=[street, tower, alley, cracked, lanterns, cellar, finale],
        terrain=Terrain(surface="roof", fill="mudejar", ledge="awning", ledge2="awning", pillar="ashlar"),
        legend=BOOK_TWO_LEGEND,
        properties={"par_time": 240, "difficulty": 11, "book": 2, "locked_moves": "glide,swing"},
        seed=111,
        height=22,
    )


# ---------------------------------------------------------------------------------------
# 12 - The Swinging Moons (Generalife gardens by night)
# ---------------------------------------------------------------------------------------
def swinging_moons() -> LevelDef:
    H = 24
    pools = S(
        [
            "..............................................",  # 10
            "..............................................",  # 11
            "..........CCC.................................",  # 12
            "...........................C..C..C..C.........",  # 13
            ".......................................C......",  # 14
            "..@..1..............................2.........",  # 15
            "pppppppppp...................................",  # 16
            "pppppppppp...................................",  # 17
            "pppppppppp...................................",  # 18
            "pppppppppp.............................######",  # 19
            "pppppppppp.............................######",  # 20
            "pppppppppp~~~~~~~~~~~~~~~~~~~~~~~~~~~~~######",  # 21
            "pppppppppp~~~~~~~~~~~~~~~~~~~~~~~~~~~~~######",  # 22
            "pppppppppp~~~~~~~~~~~~~~~~~~~~~~~~~~~~~######",  # 23
        ],
        H,
        marks={
            "1": sign("The moon is gone - but the shawl remains.\nIn mid-air press JUMP again and HOLD it\nto GLIDE."),
            "2": sign("Warm air rises from the fountains.\nGlide into it and ride it up."),
        },
        objects=[(x, 20, O("lily_pad", w=2, flower=x % 2 == 0)) for x in (16, 23, 30)]
        + [(20, 20, O("decor", style="koi", span=80)), (27, 20, O("decor", style="koi", span=60)),
           (1, 15, O("decor", style="cypress", decor_height=130)), (8, 15, O("decor", style="torch")),
           (42, 18, O("decor", style="lion_statue", facing="left")), (44, 18, O("decor", style="torch"))],
    )
    updrafts = S(
        [
            "..............................................",  # 3
            "...............................3..............",  # 4
            "..............................ppp.............",  # 5
            "..............................................",  # 6
            "......................CCC.....................",  # 7
            "......................ppppp...................",  # 8
            "......................ppppp...................",  # 9
            "..............................................",  # 10
            "..........CCC.................................",  # 11
            "..........pppppp..............................",  # 12
            "..........pppppp..............................",  # 13
            "..............................................",  # 14
            ".......................................K......",  # 15
            "..............................................",  # 16
            "..............................................",  # 17
            "..............................................",  # 18
            "######..u.............u.............##########",  # 19
            "######~~~~~~####~~~~~~~~~~~~~~~~~~~~##########",  # 20
            "######~~~~~~####~~~~~~~~~~~~~~~~~~~~##########",  # 21
            "######~~~~~~####~~~~~~~~~~~~~~~~~~~~##########",  # 22
            "######~~~~~~####~~~~~~~~~~~~~~~~~~~~##########",  # 23
        ],
        H,
        marks={
            "u": O("updraft", w=3, h=16, dy=-15, dx=-1, strength=260),
            "3": O("page", index=0),
        },
        objects=[(7, 19, O("decor", style="fountain")), (21, 19, O("decor", style="fountain")),
                 (28, 16, O("decor", style="butterflies", count=3)),
                 (12, 12, O("decor", style="torch")), (24, 8, O("decor", style="torch")),
                 (38, 18, O("decor", style="cypress", decor_height=140)),
                 (43, 18, O("decor", style="cypress", decor_height=120))],
    )
    rings = S(
        [
            "......................................................",  # 8
            "....1.................................................",  # 9
            "......................................................",  # 10
            "..........C.....C......C......C......C.......C........",  # 11
            "........Q.....Q......Q......Q......Q.......Q..........",  # 12
            "......................................................",  # 13
            "......................................................",  # 14
            "......................................................",  # 15
            "......................................................",  # 16
            "......................................................",  # 17
            "......................................................",  # 18
            "######.........................................#######",  # 19
            "######.........................................#######",  # 20
            "######.........................................#######",  # 21
            "######.........................................#######",  # 22
            "######.........................................#######",  # 23
        ],
        H,
        marks={"1": sign("Touch a golden ring in the air to GRAB it.\nLEFT/RIGHT pump the swing,\nJUMP lets go with a kick.")},
        objects=[(1, 18, O("decor", style="torch")), (50, 18, O("decor", style="torch")),
                 (2, 18, O("decor", style="urn")), (52, 18, O("decor", style="urn"))],
    )
    orchard = S(
        [
            "..............................................................",  # 1
            "..............................................................",  # 2
            "..............................................................",  # 3
            "...................................4........Q.................",  # 4
            "................................................*.............",  # 5
            "..............................Q...............................",  # 6
            "..............................................................",  # 7
            "..................*...........................................",  # 8
            "..............................................................",  # 9
            "..............................................................",  # 10
            "........Q.....................................................",  # 11
            "..............................................................",  # 12
            "...........................................................CC.",  # 13
            "..........................................................pppp",  # 14
            "..............................................................",  # 15
            "..............................................................",  # 16
            "..................................u...........................",  # 17
            "...K..........................................................",  # 18
            "pppppp........................pppppp..........................",  # 19
            "pppppp........................pppppp..........................",  # 20
            "pppppp........................pppppp..........................",  # 21
            "pppppp........................pppppp..........................",  # 22
            "pppppp........................pppppp..........................",  # 23
        ],
        H,
        marks={
            "u": O("updraft", w=4, h=14, dy=-13, dx=-1, strength=240),
            "4": O("page", index=1),
        },
        objects=[(2, 18, O("decor", style="torch")), (31, 18, O("decor", style="lion_fountain")),
                 (60, 13, O("decor", style="torch"))],
    )
    finale = S(
        [
            "...........................................",  # 9
            ".............5.............................",  # 10
            ".............ZZZ...........................",  # 11
            ".............Z.Z...........................",  # 12
            "..............................C.C.C........",  # 13
            "pppppp........................ppppp........",  # 14
            "pppppp.....................................",  # 15
            "pppppp.....................................",  # 16
            "pppppp...........u.........................",  # 17
            "pppppp.....................................",  # 18
            "pppppppppppp.........pppppppppppppppp..G...",  # 19
            "pppppppppppp.........######################",  # 20
            "pppppppppppp~~~~~~~~~######################",  # 21
            "pppppppppppp~~~~~~~~~######################",  # 22
            "pppppppppppp~~~~~~~~~######################",  # 23
        ],
        H,
        marks={
            "u": O("updraft", w=3, h=11, dy=-10, dx=-1, strength=250),
            "5": O("page", index=2),
        },
        objects=[(3, 13, O("decor", style="torch")), (24, 18, O("decor", style="cypress", decor_height=120)),
                 (28, 18, O("decor", style="cypress", decor_height=150)), (34, 18, O("decor", style="torch")),
                 (15, 19, O("decor", style="koi", span=70))],
    )
    return LevelDef(
        file_name="level12.tmx",
        name="The Swinging Moons",
        subtitle="Night in the gardens of the Generalife",
        theme="fortress",
        music="level6",
        next_level="level13.tmx",
        segments=[pools, updrafts, rings, orchard, finale],
        terrain=Terrain(surface="court", fill="palace", ledge="ledge", ledge2="bridge", pillar="marble"),
        legend=BOOK_TWO_LEGEND,
        properties={"par_time": 260, "difficulty": 12, "book": 2},
        seed=121,
        height=H,
    )


# ---------------------------------------------------------------------------------------
# 13 - The Drowned Cistern (a vertical escape from rising water)
# ---------------------------------------------------------------------------------------
def drowned_cistern() -> LevelDef:
    W, H = 30, 96
    g = Grid(W, H)
    g.fill(0, 0, 2, H, "a").fill(W - 2, 0, 2, H, "a")          # outer walls
    g.fill(2, 93, W - 4, 3, "#")                                   # cistern floor
    # Band 0: ledges out of the start chamber.
    g.fill(8, 90, 5, 1, "=").fill(16, 87, 5, 1, "=").fill(9, 84, 4, 1, "=").put_all("C", [(10, 89), (18, 86), (11, 83)])
    # Band 1: a wall-jump shaft (cols 10-13) with a page nook in its left wall.
    g.fill(2, 64, 8, 18, "a").fill(14, 64, 14, 18, "a")
    g.fill(7, 70, 3, 2, ".")
    g.put_all("C", [(11, 76), (12, 73), (11, 70), (12, 67)])
    # Band 2: the lantern tower - chain up-dashes from lantern to lantern.
    # A vertical up-dash lifts ~3.3 tiles, so the lanterns stack 3 rows apart.
    g.put_all("*", [(19, 59), (19, 56), (19, 53), (19, 50), (19, 47), (19, 44), (19, 41)])
    g.put_all("C", [(21, 57), (17, 54), (21, 51), (17, 48), (21, 45)])
    g.fill(14, 40, 9, 1, "=")
    g.fill(2, 49, 4, 1, "a")                                       # alcove floor for page 1
    # Band 3: an updraft vent rising from a stone block.
    g.fill(3, 39, 5, 2, "a")
    g.fill(8, 27, 7, 1, "=")
    g.put_all("C", [(5, 34), (5, 31), (5, 28)])
    # Band 4: rings to the east balcony, a pound plate and its portcullis,
    # then crumbling stairs up to a cracked ceiling.
    g.fill(22, 21, 6, 1, "a")                                      # east balcony
    g.fill(2, 7, W - 4, 2, "a")                                    # the roof
    g.fill(6, 7, 3, 2, "Z")                                        # cracked roof panel
    g.put_all("X", [(17, 18), (18, 18), (12, 15), (13, 15), (7, 12), (8, 12)])
    g.put_all("C", [(17, 17), (12, 14), (7, 11)])
    # The roof: open sky above the city.
    g.fill(2, 0, W - 4, 7, ".")
    g.put(22, 6, "G").put(8, 6, "K")
    g.put(5, 92, "@").put(8, 92, "1").put(21, 63, "K").put(18, 39, "K").put(24, 20, "K")
    g.put(4, 48, "2").put(26, 20, "3")
    g.put(3, 5, "4")
    g.put(22, 48, "b").put(10, 33, "b").put(16, 22, "i")
    return LevelDef(
        file_name="level13.tmx",
        name="The Drowned Cistern",
        subtitle="The Ifrit has opened the sluices - climb!",
        theme="court",
        music="boss",
        next_level="level14.tmx",
        segments=[Segment(
            g.rows(),
            marks={
                "1": sign("The water is rising!\nWall-jump, dash and glide your way\nup to the roof. Don't look down."),
                "2": O("page", index=1),
                "3": [O("pound_plate", group="cistern"), sign("Pound the plate to lift the portcullis.")],
                "4": O("page", index=2),
            },
            objects=[
                (8, 70, O("page", index=0)),
                (2, 94, O("flood", w=W - 4, h=2, speed=34, delay=3.0, top_limit_tiles=8, lag_tiles=8)),
                (4, 26, O("updraft", w=3, h=13, strength=270)),
                (17, 21, O("ring", h=3)),
                (9, 9, O("gate", w=1, h=3, group="cistern")),
            ]
            + [(x, y, O("decor", style="torch")) for x, y in
               ((3, 92), (26, 92), (15, 86), (3, 80), (26, 80), (11, 66), (24, 62), (3, 58), (26, 52),
                (3, 44), (26, 38), (10, 26), (26, 16), (4, 15), (14, 9))],
            backdrops=[(0, 7, W, H - 7, "cistern")],
        )],
        terrain=Terrain(surface="ashlar", fill="stone", ledge="ledge", ledge2="bridge", pillar="ashlar"),
        legend=BOOK_TWO_LEGEND,
        properties={"par_time": 150, "difficulty": 13, "book": 2},
        decorate=False,
        seed=131,
        height=H,
    )


# ---------------------------------------------------------------------------------------
# 14 - The Seven Gates of the Sierra (pound, plates and portcullis races)
# ---------------------------------------------------------------------------------------
def seven_gates() -> LevelDef:
    W, H, FLOOR = 262, 24, 20
    g = Grid(W, H)
    g.fill(0, FLOOR, W, H - FLOOR, "#")
    objects: list[tuple[float, float, O]] = []
    marks: dict[str, O | list[O]] = {}

    def gate_wall(x: int, group: str, height: int = 4) -> None:
        g.fill(x, 0, 1, FLOOR - height, "k")
        objects.append((x, FLOOR - height, O("gate", h=height, group=group)))

    def plate_at(x: int, y: int, group: str, timer: float = 0.0) -> None:
        objects.append((x, y, plate(group, timer)))

    def note(x: int, text: str, y: int = FLOOR - 1) -> None:
        objects.append((x, y, sign(text)))

    # A - the first gate: find the plate, pound it.
    g.put(3, FLOOR - 1, "@")
    note(6, "Seven gates bar the pass.\nEach opens to a bronze plate:\njump, then DOWN to POUND it.")
    g.put(14, FLOOR - 1, "h")
    note(11, "Hedgehogs can't be stomped -\nbut a pound's shockwave\nflattens anything nearby.")
    plate_at(21, FLOOR - 1, "g1")
    gate_wall(26, "g1")
    g.put_all("C", [(17, 16), (19, 15), (21, 16)])

    # B - the second plate waits on a high ledge: pound onto the drum.
    g.put(32, FLOOR - 1, "K")
    note(35, "Pound onto a drum\nfor a mighty launch!")
    objects.append((39, FLOOR - 1, O("drum")))
    g.fill(40, 9, 6, 1, "k")
    plate_at(43, 8, "g2")
    objects.append((45, 6, O("page", index=0)))
    g.put_all("C", [(39, 14), (39, 11), (40, 8)])
    gate_wall(56, "g2")

    # C - a timed plate: race through the blade alley and over the gap.
    g.put(60, FLOOR - 1, "K")
    note(63, "This plate only holds for a while.\nPound it - then RUN!")
    plate_at(66, FLOOR - 1, "g3", 9.0)
    g.fill(69, 12, 13, 6, "k")                          # low roof over the alley
    for x in (71, 75, 79):
        objects.append((x, FLOOR - 1, O("blade_trap")))
    g.fill(85, FLOOR, 5, H - FLOOR, ".")                # the gap
    g.put_all("C", [(86, 16), (87, 15), (88, 16)])
    gate_wall(96, "g3")

    # D - the fourth plate is sealed under crumbling slabs.
    g.put(100, FLOOR - 1, "K")
    note(103, "Pound through the slabs:\na plunging pound doesn't stop\nuntil it hits something solid.")
    g.fill(108, FLOOR, 4, 2, ".")                       # the pit
    # Only half the pit is lidded, so the slabs can never seal you in.
    g.put_all("X", [(108, FLOOR), (109, FLOOR)])
    g.fill(108, FLOOR + 2, 4, 2, "#")
    plate_at(109, FLOOR + 1, "g4")
    objects.append((108, FLOOR + 1, O("page", index=1)))
    gate_wall(122, "g4")

    # E - a plate on a pillar reached by rings; then a timed lantern race.
    g.put(126, FLOOR - 1, "K")
    note(128, "Swing to the pillar-top plate.\nThen fly the lanterns before\nthe gate falls again!")
    objects.append((133, 11, O("ring", h=3)))
    objects.append((138, 9, O("ring", h=3)))
    g.fill(142, 10, 3, FLOOR - 10, "k")
    plate_at(143, 9, "g5", 11.0)
    g.fill(148, FLOOR, 18, H - FLOOR, ".")               # spike-bottomed chasm
    g.fill(148, H - 1, 18, 1, "^")
    g.put_all("*", [(151, 15), (155, 16), (159, 17), (163, 17)])
    gate_wall(172, "g5")

    # F - the hedgehog gauntlet guards the sixth plate.
    g.put(176, FLOOR - 1, "K")
    g.put_all("h", [(183, FLOOR - 1), (188, FLOOR - 1), (193, FLOOR - 1)])
    g.put(186, 14, "b")
    plate_at(197, FLOOR - 1, "g6")
    g.put_all("C", [(183, 15), (188, 15), (193, 15)])
    gate_wall(204, "g6")

    # G - the seventh gate: a timed plate and a wall only a pound-launch clears.
    g.put(208, FLOOR - 1, "K")
    note(211, "The Seventh Gate.\nPound the plate, pound the drum,\nand fly over the wall!")
    plate_at(215, FLOOR - 1, "g7", 10.0)
    objects.append((222, FLOOR - 1, O("drum")))
    g.fill(226, 6, 3, FLOOR - 6, "k")                  # the great wall
    objects.append((227, 4, O("page", index=2)))
    g.put_all("C", [(222, 12), (222, 9), (224, 6)])
    gate_wall(246, "g7")
    g.put(254, FLOOR - 1, "G")
    g.put_all("g", [(236, FLOOR - 2)])

    for x in (5, 30, 58, 98, 124, 174, 206, 250):
        objects.append((x, FLOOR - 1, O("decor", style="torch")))
    return LevelDef(
        file_name="level14.tmx",
        name="The Seven Gates of the Sierra",
        subtitle="Pound the plates, race the portcullis",
        theme="mountain",
        music="level5",
        next_level="level15.tmx",
        segments=[Segment(g.rows(), marks=marks, objects=objects)],
        terrain=Terrain(surface="rock", fill="rock", ledge="bridge", ledge2="ledge", pillar="rock"),
        legend=BOOK_TWO_LEGEND,
        properties={"par_time": 300, "difficulty": 14, "book": 2},
        seed=141,
        height=H,
    )


# ---------------------------------------------------------------------------------------
# 15 - The Ifrit's Crown (the Alhambra at midnight, and the final battle)
# ---------------------------------------------------------------------------------------
def ifrit_crown() -> LevelDef:
    W, H, FLOOR = 166, 24, 20
    g = Grid(W, H)
    g.fill(0, FLOOR, W, H - FLOOR, "#")
    objects: list[tuple[float, float, O]] = []

    def note(x: int, text: str, y: int = FLOOR - 1) -> None:
        objects.append((x, y, sign(text)))

    # A - the Court of the Myrtles: rings over the long pool, or the lily pads.
    g.put(3, FLOOR - 1, "@")
    note(5, "The Ifrit waits in the Court of the Lions.\nEverything you have learned,\nyou will need tonight.")
    g.fill(9, FLOOR, 24, H - FLOOR, "~")
    g.fill(8, 9, 26, 2, "p")                              # arcade roof over the pool
    for x in (12, 18, 24, 30):
        objects.append((x, 11, O("ring", h=3)))
    for x in (11, 16, 21, 26, 31):
        objects.append((x, FLOOR - 1, O("lily_pad", dy=1, w=2, flower=x % 2 == 0)))
    g.put_all("*", [(14, 6), (19, 5), (24, 5)])
    objects.append((28, 4, O("page", index=0)))
    g.put_all("C", [(15, 15), (21, 15), (27, 15)])

    # B - the Hall of the Abencerrajes: slide and dash through the vaulted hall.
    g.put(37, FLOOR - 1, "K")
    g.fill(40, 4, 30, 12, "p")                            # the hall's massive roof
    g.fill(40, 16, 30, 2, "a")                            # low ceiling (corridor is rows 18-19)
    for x in (44, 50, 57, 63):
        objects.append((x, FLOOR - 1, O("blade_trap")))
    g.fill(54, 18, 1, 2, "Z").fill(67, 18, 1, 2, "Z")
    g.put_all("C", [(46, 19), (52, 19), (60, 19), (65, 19)])
    g.put(48, 19, "w").put(61, 19, "w")
    objects.append((58, 3, O("page", index=1)))
    g.fill(56, 3, 5, 1, "p")

    # C - the Mirador: glide the fountain updrafts above a spiked garden,
    # then pound the plate that opens the way to the Court of the Lions.
    g.put(73, FLOOR - 1, "K")
    note(75, "Ride the warm air over the thorns.")
    g.fill(78, FLOOR, 22, 1, "^")
    g.fill(78, FLOOR + 1, 22, H - FLOOR - 1, "#")
    objects.append((80, 6, O("updraft", w=3, h=14, strength=260)))
    objects.append((90, 6, O("updraft", w=3, h=14, strength=260)))
    g.fill(84, 9, 3, 1, "=").fill(94, 8, 4, 1, "=")
    g.fill(100, 12, 6, 8, "p")
    objects.append((96, 5, O("page", index=2)))
    plate_x = 103
    objects.append((plate_x, 11, plate("court")))
    note(101, "Pound the plate:\nthe lions' gate will open.", y=11)
    g.fill(110, 0, 1, FLOOR - 4, "p")
    objects.append((110, FLOOR - 4, O("gate", h=4, group="court")))
    g.put(114, FLOOR - 1, "K")
    g.put_all("P", [(115, FLOOR - 4)]).put_all("N", [(117, FLOOR - 4)])

    # D - the Court of the Lions: the arena. Its gate stays open until the
    # fight begins, then slams shut.
    arena_left = 120
    g.fill(arena_left - 1, 0, 1, FLOOR - 4, "p")
    objects.append((arena_left - 1, FLOOR - 4, O("gate", h=4, group="arena", open=True)))
    g.fill(W - 2, 0, 2, FLOOR, "p")
    objects.append((arena_left, 0, O("boss_arena", w=W - 2 - arena_left, h=FLOOR)))
    objects.append(((arena_left + W - 2) / 2, FLOOR - 1, O("boss")))
    note(116, "Only a POUND on his resting fist\nwill bring the Ifrit's head down.\nThen strike his jewel!")
    for x in range(arena_left + 3, W - 3, 7):
        objects.append((x, FLOOR - 1, O("decor", style="column", decor_height=150)))
    objects.append(((arena_left + W) // 2 - 1, FLOOR - 1, O("decor", style="lion_fountain")))
    for x, y in ((2, 19), (36, 19), (72, 19), (113, 19), (arena_left + 1, 19), (W - 3, 19)):
        objects.append((x, y, O("decor", style="torch")))
    return LevelDef(
        file_name="level15.tmx",
        name="The Ifrit's Crown",
        subtitle="The Alhambra at midnight",
        theme="court",
        music="level6",
        next_level="",
        segments=[Segment(g.rows(), objects=objects, backdrops=[(40, 16, 30, 4, "court_arcade")])],
        terrain=Terrain(surface="court", fill="palace", ledge="ledge", ledge2="bridge", pillar="marble"),
        legend=BOOK_TWO_LEGEND,
        properties={"par_time": 360, "difficulty": 15, "book": 2},
        seed=151,
        height=H,
    )


LEVELS = [djinn_bazaar(), swinging_moons(), drowned_cistern(), seven_gates(), ifrit_crown()]
