"""The catalogue: which enchanted machine guards each level's finish, and which
of al-Jazari's devices its three manuscript pages teach.

The story: the Book of Knowledge of Ingenious Mechanical Devices, which the
great engineer Ibn al-Razzaz al-Jazari completed in 1206, was stolen from a
library in Qurtuba by a man who called himself al-Muqallid, the Imitator. He
could copy the machines but not understand them, so he bent them with magic
and gave them to his players, who use them to steal what the country needs
(in the orchard, its water). He tore the book apart and scattered the pages.
Every level hides three of them; read together, they teach one device, and
the device is the key to that level's machine and its players.

Encounters are placed at runtime (levels 1-10 are never edited): each entry
gives the column the machine stands on and the floor row beneath it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jazari.base import Guardian, Power

if TYPE_CHECKING:
    from core.assets import AssetManager
    from world.level_data import LevelData
    from world.world import World


@dataclass(frozen=True)
class Entry:
    level_file: str
    chapter: str
    guardian: type[Guardian]
    power: type[Power]
    anchor_col: int
    floor_row: int
    art_caption: str
    text: str
    demo_caption: str
    lock: str = "goal"  # "goal" bolts the exit arch; "arena_gate" keeps the boss arena shut


def _entries() -> list[Entry]:
    from jazari.levels import l01_moonclock as l01
    from jazari.levels import l01_nightingale as nightingale
    from jazari.levels import l02_elephant as l02
    from jazari.levels import l02_qalam as qalam
    from jazari.levels.l03_archivist import SilentArchivist
    from jazari.levels.l03_fulcrum import FoldedFulcrum
    from jazari.levels.l04_fountain import RoseFountain
    from jazari.levels.l04_noria import RiverThieves

    return [
        Entry(
            "level1.tmx", "Chapter of birds that sing by water: the brass nightingale",
            l01.MoonTroupe, nightingale.BrassNightingale, 184, 22,
            "Water held by a spell trembles at a true note.",
            "I set a nightingale of brass upon a pipe of falling water, so that the water "
            "pressed the air through its throat, and it sang. Its note is true. Water that a "
            "spell holds in a false shape - a moon, a bubble, a string - trembles at it and "
            "bursts, and those who hide inside it cover their ears. Let the bird ride upon "
            "your shoulder; when it sings, strike.",
            "The nightingale sings: the bubble bursts, the string breaks, the player covers his ears.",
        ),
        Entry(
            "level2.tmx", "Chapter of clocks with a scribe: the pen of night",
            l02.GildedThieves, qalam.NightQalam, 214, 22,
            "Where night is written, the stolen sun cannot pass.",
            "Upon my elephant clock sits a scribe who writes the hours. I cut him a second "
            "reed and filled it with the ink of the night, which carries its own stars. Where "
            "it writes, sunlight cannot pass; what it touches forgets the light, and gold falls "
            "away from it. A line of it will even bear a man's weight, until it dries. If the "
            "sun is ever stolen, write between the sun and the thief.",
            "The pen writes across the beam: the gold leaves the thief, and he can be struck.",
        ),
        Entry(
            "level3.tmx", "Chapter of the castle clock and the folded lever",
            SilentArchivist, FoldedFulcrum, 249, 22,
            "A folded lever in the jaw stops the clock; even borrowed hours stand still.",
            "Amir's notes, after al-Jazari: the builder made servants, not jailers. "
            "Al-Muqallid has chained this keeper inside a clock that borrows hours: each "
            "hour a door opens and you step out of it as you were an hour before. When "
            "white light rises from a jaw, pound its treadle to turn one tooth; six free "
            "a drive. Set the Fulcrum in the jaw with V and the clock stops: borrowed "
            "hours stand as glass, and one pound turns all six. On firm ground its ribs "
            "lift a step.",
            "Brace the jaw and time stands still: one pound frees the whole drive.",
        ),
        Entry(
            "level4.tmx", "Chapter of fountains that hold a ball upon the water",
            RiverThieves, RoseFountain, 257, 22,
            "Whoever stands in stolen water borrows the noria's strength.",
            "I made a fountain whose water rises and holds a ball dancing upon its crest, and will not "
            "let it fall until the water fails. The thief has set a noria over the river and taught it "
            "to pour the water into the sky; whoever stands in the water it leaves borrows its patient "
            "strength, and no blow will reach him. Throw this rose of brass beneath such a one, and the "
            "fountain will lift him out of the stolen water: in the air he is only himself. The rose "
            "will lift you too, where the stairs give out.",
            "The rose blooms under the thief: the fountain lifts him, and the river lets him go.",
        ),
    ]


CATALOG: dict[str, Entry] = {}


def entry_for(level_file: str) -> Entry | None:
    if not CATALOG:
        CATALOG.update({entry.level_file: entry for entry in _entries()})
    return CATALOG.get(level_file)


def install(world: "World", level: "LevelData", assets: "AssetManager", known_pages: set[int],
            resolved: bool = False, progress: int = 0) -> None:
    """Give ``world`` its level's machine and (if earned) its power."""
    entry = entry_for(level.file_name)
    if entry is None:
        return
    from jazari.director import WonderDirector

    world.wonder = WonderDirector(world, entry, known_pages, assets, resolved, progress)
