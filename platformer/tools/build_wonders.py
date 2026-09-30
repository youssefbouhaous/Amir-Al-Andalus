"""Build only the optional Courtyard of Wonders, never the campaign maps.

Run: python -m tools.build_wonders [--force]
The lower route has a continuous safety floor. Three manuscript detours teach
ledge -> scarf -> dash, slide -> spin-jump, and pound -> grapple -> timed gate.
"""

import argparse

from core import settings
from tools.level_format import LevelDef, O, Obj, Segment, Terrain, build_level, write_xml
from tools.levels.book_two import Grid

FILE_NAME = "challenge_courtyard.tmx"


def courtyard() -> LevelDef:
    g = Grid(150, 24).fill(0, 20, 150, 4, "#")
    g.put(3, 19, "@").put(146, 19, "G")
    # First lesson: a low stair, then a ledge just above normal jump height.
    g.fill(12, 18, 3, 2, "#").fill(20, 16, 5, 4, "#")
    g.fill(43, 14, 6, 1, "=")
    # Sand alley: run-up, two blade bands, then a slide-jump manuscript.
    g.fill(55, 18, 7, 1, "|")
    g.fill(63, 17, 5, 1, "=")
    # Final combination: a plate on a low balcony opens the upper archive.
    g.fill(125, 17, 6, 1, "=").fill(134, 14, 7, 1, "=")
    g.fill(141, 17, 3, 1, "=")
    for x in (7, 50, 69, 84, 111, 123):
        g.put(x, 19, "K")
    for x in (9, 52, 82, 110, 121):
        g.put(x, 17, "P")
    for x, y in ((14, 16), (22, 14), (28, 15), (32, 14), (37, 13),
                 (42, 12), (47, 12), (64, 15), (65, 15), (66, 15),
                 (96, 17), (100, 16), (104, 17), (128, 15), (138, 12)):
        g.put(x, y, "C")
    objects = [
        (5, 19, O("sign", text="COURTYARD OF WONDERS\nAn optional movement playground.\nThe original chapters are unchanged.")),
        (17, 19, O("sign", text="Catch a ledge: fall toward its edge.\nKeep pushing, or Jump / Up to vault.\nDown lets go. Try the high route!")),
        (23, 15, O("sign", text="Golden rosettes are SCARF HOOKS.\nIn the air, TAP Up / W to grapple.\nLeft / Right pumps. Jump or Dash releases.")),
        (31, 19, O("sign", text="Missed a hook? The floor is safe.\nUp + Dash also reaches the rosettes.\nReleasing a hook restores your scarf tail.")),
        (52, 19, O("sign", text="Run, then Down: SAND SLIDE.\nJump out for a spinning launch!\nThe page waits just beyond the blades.")),
        (56, 19, O("blade_trap")), (59, 19, O("blade_trap")),
        (70, 19, O("sign", text="MIRROR DUELIST\nBait the glint, jump over his lunge.\nSlash his back or his recovery!")),
        (76, 19, Obj("enemy", props={"kind": "mirror_duelist"})),
        (85, 19, O("sign", text="SANDFISH: watch the ripples!\nHidden sand cannot hurt you.\nMove aside, then strike when it emerges.")),
        (90, 19, Obj("enemy", props={"kind": "sand_burrower"})),
        (96, 19, O("sign", text="The jewel moth borrows blue light.\nDefeat it to refill your dash at once.\nOr wait: the lamp returns in 4 seconds.")),
        (103, 17, Obj("enemy", props={"kind": "lantern_thief"})),
        (101, 17, O("dash_lantern")),
        (112, 19, O("sign", text="CLOCKWORK GUARDIAN\nBronze closed: shielded.\nTurquoise heart open: slash or stomp!")),
        (117, 19, Obj("enemy", props={"kind": "clockwork_guardian"})),
        (124, 19, O("sign", text="THE ARCHIVE COMBINATION\nPound the balcony plate. Catch a hook.\nDash through the gate before it closes!")),
        (129, 16, O("pound_plate", group="archive", timer=9.0)),
        (135, 10, O("gate", h=4, group="archive")),
        (144, 19, O("sign", text="Three pages, three movement chains.\nMissed one? Replay from Level Select.\nYour journey progress stays safe.")),
        (45, 12, O("page", index=0)), (66, 16, O("page", index=1)),
        (138, 13, O("page", index=2)),
    ]
    for x, y in ((27, 11), (33, 11), (39, 10), (45, 10), (99, 13),
                 (127, 12), (132, 10)):
        objects.append((x, y, O("grapple_hook")))
    for x in (9, 49, 81, 109, 143):
        objects.append((x, 19, O("decor", style="orange_tree", size=1)))
    for x in (18, 42, 69, 95, 124, 140):
        objects.append((x, 12, O("decor", style="banner", color="blue" if x % 2 else "red")))
    for x in (2, 51, 96):
        objects.append((x, 9, O("decor", w=9, h=2, style="garland", count=7)))
    return LevelDef(
        FILE_NAME, "Courtyard of Wonders", "Scarf flights, sand pirouettes & living clockwork",
        "court", "palace", "", [Segment(g.rows(), objects=objects)],
        terrain=Terrain(surface="court", fill="plaster", ledge="ledge", pillar="wood"),
        properties={"acrobatics": True, "optional_challenge": True, "par_time": 150.0},
        height=24, seed=407,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite only the optional courtyard map")
    args = parser.parse_args()
    target = settings.MAPS_DIR / FILE_NAME
    if target.exists() and not args.force:
        parser.error(f"{target.name} already exists; use --force to rebuild it")
    write_xml(build_level(courtyard()), target)
    print(f"Built {target.name}; campaign maps untouched.")


if __name__ == "__main__":
    main()
