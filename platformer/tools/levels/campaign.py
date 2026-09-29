"""Six authored routes with distinct terrain, mechanics and enemy habitats.

Coordinates are tiles. Profiles give (start, surface height) for each terrace.
Pools cut terrain away. Recovery ledges sit below optional high challenges.
"""

from tools.level_format import LevelDef, O, Obj, Segment, Terrain

HEIGHT = 26


class Route:
    def __init__(self, width: int, profile: list[tuple[int, int]]) -> None:
        self.width = width
        self.grid = [["."] * width for _ in range(HEIGHT)]
        self.floor = [0] * width
        self.objects: list[tuple[float, float, Obj]] = []
        self.backdrops: list[tuple[int, int, int, int, str]] = []
        for (start, y), (end, _) in zip(profile, profile[1:] + [(width, 0)]):
            for x in range(start, end):
                self.floor[x] = y
                for row in range(y, HEIGHT):
                    self.grid[row][x] = "#"

    def strip(self, x: int, y: int, width: int, char: str = "=") -> None:
        for col in range(x, x + width):
            self.grid[y][col] = char

    def pool(self, start: int, end: int, surface: int = 23) -> None:
        for x in range(start, end):
            for y in range(HEIGHT):
                self.grid[y][x] = "~" if y >= surface else "."

    def obj(self, x: float, y: float, obj: Obj) -> None:
        self.objects.append((x, y, obj))

    def ground_obj(self, x: int, obj: Obj) -> None:
        self.obj(x, self.floor[x] - obj.h, obj)

    def sign(self, x: int, text: str) -> None:
        self.ground_obj(x, O("sign", text=text))

    def checkpoint(self, x: int) -> None:
        self.ground_obj(x, O("checkpoint", h=2))

    def enemy(self, x: int, kind: str = "scorpion", y: int | None = None) -> None:
        self.obj(x, self.floor[x] - 1 if y is None else y,
                 Obj("enemy", props={"kind": kind, "edge_aware": True, "patrol_tiles": 2}))

    def page(self, x: int, y: int, index: int) -> None:
        self.obj(x, y, O("page", index=index))

    def coins(self, x: int, y: int, count: int, step: int = 2) -> None:
        for n in range(count):
            self.obj(x + n * step, y, O("coin"))

    def backdrop(self, x: int, y: int, w: int, h: int, style: str) -> None:
        self.backdrops.append((x, y, w, h, style))

    def finish(self, number: int, name: str, subtitle: str, theme: str,
               terrain: Terrain, music: str, **properties: object) -> LevelDef:
        self.ground_obj(3, O("player_spawn"))
        self.ground_obj(self.width - 5, O("goal", style="sword" if number == 6 else "gate"))
        return LevelDef(
            f"level{number}.tmx", name, subtitle, theme, music,
            f"level{number + 1}.tmx" if number < 6 else "",
            [Segment(["".join(row) for row in self.grid], objects=self.objects, backdrops=self.backdrops)],
            terrain, {"par_time": 100 + number * 35, "difficulty": number, **properties},
            seed=number * 37, height=HEIGHT,
        )


def orchard() -> LevelDef:
    r = Route(200, [(0, 22), (26, 21), (34, 20), (44, 22), (72, 21),
                    (82, 20), (94, 22), (130, 21), (140, 19), (150, 21), (170, 22)])
    r.sign(7, "X / J / Shift: slash!\nYou can attack without a power-up.\nHold jump to leap farther.")
    r.strip(12, 18, 1, "P")
    r.coins(15, 20, 4)
    r.enemy(22)
    r.page(37, 17, 0)
    r.coins(28, 19, 4)
    r.enemy(40, "jar")
    r.checkpoint(48)
    r.sign(50, "The lily pads dip, but stay safe.\nJump from pad to pad across the pond.")
    r.pool(56, 68)
    for x in (56, 60, 64):
        r.obj(x, 22.25, O("lily_pad", w=2, flower=x == 60))
        r.coins(x, 19, 1)
    r.enemy(79)
    r.strip(84, 17, 5)
    r.coins(84, 16, 3)
    r.enemy(92, "jar")
    r.checkpoint(103)
    r.sign(107, "Land on the drum and hold jump\nto reach the orchard balcony.")
    r.ground_obj(114, O("drum"))
    r.strip(116, 17, 7)
    r.page(120, 16, 1)
    r.coins(116, 16, 2)
    r.enemy(133)
    r.page(144, 16, 2)
    r.strip(136, 17, 1, "P")
    r.pool(155, 165)
    for x in (155, 159, 163):
        r.obj(x, 21, O("lily_pad", w=2))
    r.checkpoint(173)
    r.enemy(183, "jar")
    r.coins(187, 20, 4)
    return r.finish(1, "The Orange Orchard", "First steps, spring drums and lily ponds", "garden",
                    Terrain(), "dawn")


def rooftops() -> LevelDef:
    r = Route(230, [(0, 22), (18, 20), (29, 18), (41, 20), (50, 22), (68, 20),
                    (80, 18), (94, 16), (106, 18), (116, 20), (128, 22), (149, 20),
                    (162, 18), (176, 20), (186, 22), (207, 20), (218, 22)])
    r.sign(7, "Follow the awnings above the market.\nTap jump for a short hop;\nhold jump for the higher roofs.")
    r.strip(12, 18, 1, "P")
    r.enemy(23)
    r.strip(31, 15, 6, "-")
    r.page(34, 14, 0)
    r.coins(29, 17, 5)
    r.backdrop(17, 15, 29, 9, "houses")
    r.checkpoint(54)
    for a, b, y in ((60, 65, 22), (72, 77, 21), (132, 138, 22), (190, 196, 22)):
        r.pool(a, b, 25)
        r.strip(a, y, b - a, "-")
        r.coins(a + 1, y - 2, 2)
    r.enemy(86, "jar")
    r.page(99, 13, 1)
    r.backdrop(79, 10, 38, 14, "houses")
    r.sign(112, "Hanging seats are a high shortcut.\nThe awnings below catch you.")
    r.obj(119, 12, O("pendulum", w=2, h=6, platform_width=80, amplitude=24, period=3.6))
    r.strip(120, 20, 6, "-")
    r.checkpoint(142)
    r.enemy(156, "hedgehog")
    r.sign(148, "Spines hurt! Slash hedgehogs\nfrom the side instead of stomping.")
    r.strip(165, 15, 6, "-")
    r.page(168, 14, 2)
    r.obj(174, 17, O("moving_platform", w=3, distance=5, speed=65, style="beam"))
    r.enemy(179, "jar")
    r.checkpoint(201)
    r.coins(210, 18, 4)
    r.backdrop(149, 12, 36, 12, "houses")
    return r.finish(2, "Above the Amber Market", "Roof terraces, hanging seats and hidden awnings", "rooftops",
                    Terrain("roof", "plaster", "awning", "awning", "ashlar"), "sunset")


def fortress() -> LevelDef:
    r = Route(260, [(0, 22), (23, 20), (37, 18), (49, 20), (62, 22), (90, 20),
                    (105, 18), (119, 20), (130, 22), (163, 20), (177, 18),
                    (190, 20), (202, 22), (228, 20), (244, 22)])
    r.sign(7, "After sundown, bats wake in the vaults.\nSlash in the air or stomp them.")
    r.strip(14, 18, 1, "P")
    r.enemy(28, "bat", 15)
    r.page(42, 15, 0)
    r.backdrop(21, 9, 36, 14, "fortress")
    r.checkpoint(65)
    r.sign(69, "Bump the star-marked switch below.\nSun and moon stones trade places.\nThe floor is safe if you miss.")
    r.strip(74, 18, 1, "T")
    r.strip(80, 20, 3, "O")
    r.strip(84, 18, 3, "O")
    r.strip(88, 16, 3, "U")
    r.strip(92, 14, 6)
    r.strip(88, 17, 1, "T")
    r.page(96, 13, 1)
    r.enemy(110, "jinn", 14)
    r.backdrop(72, 9, 45, 14, "library")
    r.enemy(122, "jar")
    r.checkpoint(137)
    r.sign(143, "Ghul spirits cannot be cut.\nFace them to freeze them,\nthen jump past before turning away.")
    r.enemy(154, "ghul", 18)
    r.strip(149, 19, 5)
    r.strip(158, 17, 4)
    r.enemy(172, "bat", 14)
    r.strip(180, 15, 5)
    r.page(182, 14, 2)
    r.backdrop(148, 9, 47, 14, "arcade")
    r.enemy(196, "hedgehog")
    r.checkpoint(209)
    r.strip(217, 15, 2, "^")
    r.strip(232, 16, 1, "N")
    r.enemy(237, "jinn", 17)
    r.coins(246, 20, 4)
    return r.finish(3, "The Moonlit Library", "Two-colour stairs and watchful spirits", "fortress",
                    Terrain("ashlar", "mudejar", "shelf", "ledge", "ashlar"), "night")


def aqueduct() -> LevelDef:
    r = Route(285, [(0, 22), (25, 20), (38, 22), (80, 20), (95, 22),
                    (122, 20), (142, 22), (174, 20), (189, 22), (229, 20), (249, 22)])
    r.sign(7, "The aqueduct glitters in daylight.\nWatch each fountain's rhythm;\nits water lifts you, it does not hurt.")
    r.enemy(28, "jar")
    r.strip(16, 18, 1, "P")
    r.pool(44, 71)
    for x in (44, 48, 52, 56, 60, 65):
        r.obj(x, 22.25, O("lily_pad", w=2.5, flower=x == 56))
        r.coins(x, 20, 1)
    r.strip(69, 22, 2)
    r.checkpoint(75)
    r.obj(86, 14, O("fountain", h=6, on=2.6, off=1.2))
    r.strip(87, 14, 7)
    r.page(91, 13, 0)
    r.backdrop(80, 8, 15, 14, "cistern")
    r.sign(98, "Ride the noria seats for the high route.\nStepping stones below let you try again.")
    r.pool(104, 120)
    for x in (104, 108, 112, 116):
        r.strip(x, 22, 2)
    r.obj(105, 15, O("wheel", w=8, h=8, seats=6, speed=22, seat_width=72))
    r.strip(115, 17, 5)
    r.enemy(129, "hedgehog")
    r.checkpoint(146)
    r.obj(155, 16, O("fountain", h=6, on=2.2, off=1.4))
    r.strip(157, 16, 7)
    r.page(162, 15, 1)
    r.obj(166, 18, O("moving_platform", w=3, axis="vertical", distance=3, reverse=True, speed=55))
    r.enemy(180, "jar")
    r.backdrop(148, 10, 39, 13, "palace_wall")
    r.checkpoint(193)
    r.pool(203, 224)
    # A generous lower crossing is always available; the wheel above is the
    # faster, more demanding route.
    for x in (203, 206, 209, 212, 215, 218, 221):
        r.obj(x, 22.25, O("lily_pad", w=3))
    r.page(216, 17, 2)
    r.enemy(237)
    r.checkpoint(254)
    r.strip(261, 15, 2, "^")
    r.enemy(271, "jar")
    r.coins(275, 20, 3)
    return r.finish(4, "The Singing Aqueduct", "Fountain lifts, water wheels and stepping islands", "palace",
                    Terrain("marble", "palace", "ledge", "bridge", "marble"), "dawn")


def clockwork() -> LevelDef:
    r = Route(310, [(0, 22), (22, 20), (40, 22), (75, 20), (89, 18), (103, 20),
                    (114, 22), (151, 20), (165, 18), (179, 20), (190, 22),
                    (229, 20), (246, 18), (260, 20), (274, 22)])
    r.sign(7, "The workshop runs in sunlight.\nStones switch with the water clock.\nListen for three warning ticks.")
    r.strip(13, 18, 1, "P")
    r.enemy(29, "hedgehog")
    r.backdrop(20, 8, 36, 16, "clockwork")
    r.strip(43, 20, 3, "U")
    r.strip(47, 18, 3, "O")
    r.strip(51, 16, 3, "U")
    r.strip(55, 15, 6)
    r.page(58, 14, 0)
    r.checkpoint(66)
    r.sign(69, "Crumbling slabs fall after you step on them.\nKeep moving! The lower floor is safe.")
    r.strip(77, 17, 4, "X")
    r.strip(83, 15, 4, "X")
    r.strip(89, 13, 4, "X")
    r.strip(96, 13, 5)
    r.page(99, 12, 1)
    r.enemy(109, "jar")
    r.checkpoint(121)
    r.sign(126, "Cross the broken service catwalk\nor take the pendulums above it.")
    r.pool(133, 149, 25)
    for x in (133, 137, 141, 145):
        r.strip(x, 22, 2, "X")
    r.obj(134, 12, O("pendulum", w=2, h=7, amplitude=20, period=3.5, platform_width=80))
    r.obj(143, 12, O("pendulum", w=2, h=7, amplitude=20, period=3.5, phase=1.4, platform_width=80))
    r.enemy(158, "hedgehog")
    r.backdrop(130, 8, 52, 16, "clockwork")
    r.enemy(171, "jar")
    r.checkpoint(195)
    r.obj(203, 15, O("wheel", w=8, h=8, seats=5, style="gear", speed=-27, seat_width=64))
    r.strip(213, 17, 4)
    r.strip(218, 15, 5)
    r.page(221, 14, 2)
    r.ground_obj(207, O("drum"))
    r.sign(199, "The drum reaches the turning gear.\nRide a seat to the manuscript balcony.")
    r.enemy(235)
    r.strip(243, 16, 1, "N")
    r.strip(250, 9, 2, "^")
    r.enemy(266, "hedgehog")
    r.checkpoint(279)
    r.strip(288, 9, 2, "^")
    r.coins(294, 20, 5)
    return r.finish(5, "The Brass Observatory", "Timed stones, collapsing catwalks and swinging gears", "clockwork",
                    Terrain("wood", "mudejar", "bridge", "shelf", "ashlar"), "clockwork", switch_period=3.4)


def summit() -> LevelDef:
    r = Route(340, [(0, 22), (18, 20), (30, 18), (42, 16), (55, 18), (66, 20),
                    (77, 22), (109, 20), (124, 18), (138, 16), (151, 18),
                    (165, 20), (179, 22), (215, 20), (229, 18), (243, 16),
                    (257, 18), (272, 20), (287, 22), (301, 20), (313, 18), (326, 16)])
    r.sign(7, "The final ascent begins under the moon.\nUse everything you have learned.\nLanterns mark sheltered resting places.")
    r.strip(13, 18, 1, "N")
    r.enemy(25, "bat", 14)
    r.enemy(39, "jinn", 14)
    r.strip(44, 13, 5)
    r.page(47, 12, 0)
    r.obj(31, 8, O("wind", w=25, h=12, strength=75, on=2, off=2))
    r.enemy(60, "hedgehog")
    r.checkpoint(80)
    r.sign(84, "The carpet waits for you. Stay aboard!\nIf you fall, the lower ledges\nlet you climb back out of the ravine.")
    r.pool(91, 107, 25)
    for x, y in ((91, 23), (95, 22), (99, 23), (103, 22)):
        r.strip(x, y, 2)
    r.obj(89, 21, O("carpet", carpet_width=96, speed=120, points=((0, 0), (7, -4), (14, -3), (21, -1))))
    r.enemy(117, "jar")
    r.enemy(132, "bat", 12)
    r.backdrop(123, 6, 31, 14, "cave")
    r.strip(140, 13, 6, "X")
    r.page(143, 12, 1)
    r.enemy(159, "ghul", 14)
    r.checkpoint(184)
    r.sign(188, "Face the spirits to hold them still.\nSave your slash for bats and jinn.")
    r.obj(195, 14, O("pendulum", w=2, h=6, amplitude=25, platform_width=80))
    r.pool(195, 211, 25)
    for x in (195, 199, 203, 207):
        r.strip(x, 22, 2)
    r.obj(218, 9, O("wind", w=31, h=12, strength=-90, on=2.2, off=1.8))
    r.enemy(224, "jinn", 16)
    r.enemy(236, "bat", 12)
    r.strip(246, 13, 5)
    r.page(249, 12, 2)
    r.strip(263, 17, 2, "^")
    r.checkpoint(281)
    r.strip(293, 18, 1, "P")
    r.enemy(304, "hedgehog")
    r.enemy(318, "jinn", 14)
    r.coins(328, 14, 4)
    r.backdrop(325, 6, 15, 12, "court_arcade")
    return r.finish(6, "The Starlit Summit", "Wind, flying carpets and the final climb", "mountain",
                    Terrain("rock", "ashlar", "ledge", "bridge", "rock"), "mountain")


LEVELS = (orchard(), rooftops(), fortress(), aqueduct(), clockwork(), summit())
