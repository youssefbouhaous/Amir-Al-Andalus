"""Story content keyed to shipped maps, independent of terrain and mechanics.

The Sword is found at the summit (6), awakened at the second shrine (10),
and used to restore dawn after the Ifrit (15). Daylight in chapters 7 and 9
is intentional: the endless night does not begin until the second shrine.
Manuscripts add context, never keys required to finish a level.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryBeat:
    speaker: str
    text: str
    motif: str = "lantern"
    pose: str = "idle"

    @property
    def duration(self) -> float:
        # Full text appears immediately; leave enough time for unhurried reading.
        return max(5.0, len(self.text.split()) / 2.6 + 1.0)


@dataclass(frozen=True)
class StorySequence:
    key: str
    title: str
    theme: str
    music: str
    beats: tuple[StoryBeat, ...]


def _chapter(number, title, theme, music, *beats):
    return StorySequence(f"arrival:level{number}", title, theme, music, beats)


ARRIVALS = {
    "level1.tmx": _chapter(1, "A promise in the orchard", "garden", "dawn",
        StoryBeat("THE GARDENER", "The fountains are failing, Amir. Beyond these orange trees lies a road to the Sword of Light.", "tree"),
        StoryBeat("AMIR", "Then I will bring its light home. Keep a lantern burning for me.", "lantern", "victory")),
    "level2.tmx": _chapter(2, "The rooftops remember", "rooftops", "sunset",
        StoryBeat("THE STORYTELLER", "Above the amber market, a torn manuscript catches on an awning. Its ink describes a library that opens after sundown.", "page"),
        StoryBeat("AMIR", "A road written in the air. I will follow it, roof by roof.", "carpet", "jump")),
    "level3.tmx": _chapter(3, "The keeper of two lights", "fortress", "night",
        StoryBeat("THE KEEPER'S MARGIN", "Sun and moon share a stair. Look the restless spirits in the face; even the dead remember courtesy.", "book"),
        StoryBeat("AMIR", "Here: 'The Sword is both a key and a seal.' Why did no one tell the rest of this story?", "page", "sit")),
    "level4.tmx": _chapter(4, "Water carries the answer", "palace", "dawn",
        StoryBeat("THE STORYTELLER", "At daybreak the aqueduct begins to sing. Its fountains carry water toward the city, and a path toward the observatory.", "fountain"),
        StoryBeat("AMIR", "Not every current is an enemy. This one is showing me where to go.", "wheel", "jump")),
    "level5.tmx": _chapter(5, "A sky made of brass", "clockwork", "clockwork",
        StoryBeat("THE ASTRONOMER'S NOTE", "Our clocks follow the water; our stones follow the sun. Wait for the rhythm, and the heavens will lend you a step.", "clock"),
        StoryBeat("AMIR", "The chart points to the summit. The Sword has been waiting above the clouds.", "stars", "idle")),
    "level6.tmx": _chapter(6, "The first shrine", "mountain", "mountain",
        StoryBeat("THE STORYTELLER", "At the starlit summit, carpets cross the wind and lanterns mark the last sheltered ledges. Beyond them waits the mountain shrine.", "carpet"),
        StoryBeat("AMIR", "Stone and sky: two locks on one promise. Let me reach the first.", "sword", "idle")),
    "level7.tmx": _chapter(7, "The silent blade", "clockwork", "clockwork",
        StoryBeat("THE STORYTELLER", "The Sword came free, but its light stayed cold. The keeper's pages lead Amir to a gallery that measures the constellations.", "sword"),
        StoryBeat("AMIR", "Four trials to wake one blade. I will learn the machines before I trust the shortest road.", "clock", "sit")),
    "level8.tmx": _chapter(8, "The caravan without footprints", "mountain", "mountain",
        StoryBeat("THE CARAVAN'S SONG", "A carpet remembers its passenger. A lantern remembers its keeper. Let the wind carry neither promise away.", "carpet"),
        StoryBeat("AMIR", "The night spirits gather around the silent Sword. They know something I have not yet read.", "lantern", "idle")),
    "level9.tmx": _chapter(9, "What the water reflects", "palace", "dawn",
        StoryBeat("THE STORYTELLER", "Morning returns to the mirror aqueduct. In its turning wheels, Amir sees the same pattern as the brass star chart.", "wheel"),
        StoryBeat("AMIR", "The two stairways are one question asked twice. Sun first, then moon. The water has kept the answer.", "stars", "sit")),
    "level10.tmx": _chapter(10, "The second shrine", "court", "night",
        StoryBeat("THE KEEPER'S MARGIN", "When the final constellation aligns, return the blade to the star shrine. Its light will wake. So may what sleeps beneath it.", "book"),
        StoryBeat("AMIR", "The orchard still waits for water. I cannot turn back now... but this time I will read to the end.", "sword", "idle")),
    "level11.tmx": _chapter(11, "The night that would not end", "rooftops", "level4",
        StoryBeat("THE STORYTELLER", "The awakened Sword broke the ancient seal. An Ifrit rose from the shrine and stole the coming dawn. The bazaar's lamps burn blue.", "ifrit"),
        StoryBeat("AMIR", "I opened his prison. I will put this right. A little borrowed light is enough to begin.", "lantern", "dash")),
    "level12.tmx": _chapter(12, "Moons made by hand", "fortress", "level6",
        StoryBeat("THE STORYTELLER", "With the moon swallowed, the gardeners hang golden rings above the Generalife. Warm fountains still breathe beneath the dark.", "ring"),
        StoryBeat("AMIR", "If the sky will not hold me, my shawl will. They have left a way through.", "fountain", "glide")),
    "level13.tmx": _chapter(13, "The city beneath the city", "court", "boss",
        StoryBeat("THE IFRIT", "You came to save their fountains, little prince? Then take all the water you wished for.", "flood"),
        StoryBeat("AMIR", "He has opened the sluices. Up to the roof, before the cistern takes the stairs!", "gate", "jump")),
    "level14.tmx": _chapter(14, "Seven answers in bronze", "mountain", "level5",
        StoryBeat("THE KEEPER'S MARGIN", "The seven gates were built for the lamp-bearer. Wake each bronze plate with a falling blow; leave no promise behind.", "gate"),
        StoryBeat("AMIR", "His prison is a lamp, not a throne. At the Alhambra, I will take back what he stole.", "lantern", "pound")),
    "level15.tmx": _chapter(15, "The borrowed crown", "court", "level6",
        StoryBeat("THE STORYTELLER", "Beyond the lions' gate, the Ifrit wears the stolen dawn in his jewel. The lamp below him waits, empty.", "ifrit"),
        StoryBeat("THE KEEPER'S LAST LINE", "Do not chase the fire. Pound the fist when it rests. When the jewel bows, strike.", "jewel"),
        StoryBeat("AMIR", "You borrowed a whole morning. It is time to give it back.", "sword", "throw")),
    "challenge_courtyard.tmx": StorySequence("arrival:courtyard", "A tale between journeys", "court", "palace", (
        StoryBeat("THE STORYTELLER", "Some tales are told for the joy of the telling. In the Courtyard of Wonders, a scarf becomes a bridge and bronze flowers learn to walk.", "ring"),
        StoryBeat("AMIR", "No kingdom to save this time. Just one more impossible-looking leap.", "lantern", "victory"))),
}

DEPARTURES = {
    "level6.tmx": StorySequence("departure:summit", "A light still sleeping", "mountain", "mountain", (
        StoryBeat("THE STORYTELLER", "Amir lifts the Sword from the mountain shrine. Its edge reflects every star, yet gives no light of its own.", "sword", "victory"),
        StoryBeat("AMIR", "The second lock is in the sky. The gallery will show me how to turn it.", "stars"))),
    "level10.tmx": StorySequence("departure:seal", "The missing warning", "court", "night", (
        StoryBeat("THE STORYTELLER", "The blade meets the final constellation. Light pours through the shrine... and something on the other side pulls back.", "sword", "hurt"),
        StoryBeat("THE IFRIT", "A thousand nights in a lamp. For opening the door, prince, I shall let you keep this one forever.", "ifrit"),
        StoryBeat("AMIR", "The dawn is gone. No. This cannot be how our story ends.", "jewel", "idle"))),
    "level15.tmx": StorySequence("departure:dawn", "The lantern kept burning", "garden", "ending", (
        StoryBeat("THE STORYTELLER", "The jewel breaks its hold on the morning. Fire curls into the waiting lamp, and the first sunbeam crosses the Court of the Lions.", "sealed_lamp", "victory"),
        StoryBeat("THE GARDENER", "You brought the dawn home, Amir. The fountains have been singing since you crossed the gate.", "tree"),
        StoryBeat("AMIR", "Keep the Sword's whole story this time. A light is worth little if we forget who it is for.", "fountain", "sit"))),
}

# Small discoveries fit the existing one-line HUD toast; no new journal UI.
MANUSCRIPTS = {
    "level1.tmx": ("A promise begins with one lamp.", "Water remembers the road home.", "The orchard waits for the morning."),
    "level2.tmx": ("The awnings carry more than shade.", "Every roof shelters someone's story.", "Seek the keeper after sundown."),
    "level3.tmx": ("Sun and moon share one stair.", "Even a ghost remembers courtesy.", "The Sword is both key and seal."),
    "level4.tmx": ("A fountain lifts what a flood takes.", "The noria lends its patient strength.", "Follow the water to the brass sky."),
    "level5.tmx": ("Three ticks before the stones turn.", "The safest step is not always still.", "The summit holds the first lock."),
    "level6.tmx": ("A lantern marks a sheltered promise.", "Trust the carpet; respect the wind.", "The second lock is written in stars."),
    "level7.tmx": ("Brass remembers the shape of heaven.", "Two roads; one patient machine.", "Light must be woken, not commanded."),
    "level8.tmx": ("A carpet remembers its passenger.", "The wind cannot carry a promise away.", "The spirits follow the silent blade."),
    "level9.tmx": ("Read the water as you read the sky.", "Sun first. Then moon.", "A reflection can hide a warning."),
    "level10.tmx": ("The shrine has waited for its key.", "What wakes above may wake below.", "Never leave the last line unread."),
    "level11.tmx": ("Blue lamps lend a little lost dawn.", "Borrowed light is enough to begin.", "A falling blow wakes the bronze."),
    "level12.tmx": ("The gardeners hung their own moons.", "Warm water still breathes in the dark.", "A shawl can remember the wind."),
    "level13.tmx": ("The old cistern is the city's heart.", "A keeper closes what they open.", "Even the flood must end somewhere."),
    "level14.tmx": ("Seven gates await the lamp-bearer.", "Do not mistake haste for courage.", "A prison need not be a throne."),
    "level15.tmx": ("The jewel holds a borrowed morning.", "Wait for the fist. Then wake the stone.", "Bring home the light, not the crown."),
    "challenge_courtyard.tmx": ("A scarf can become a bridge.", "Even sand knows how to dance.", "Bronze flowers open to the patient."),
}


def manuscript_line(level_file: str, index: object) -> str | None:
    pages = MANUSCRIPTS.get(level_file, ())
    return pages[index] if isinstance(index, int) and 0 <= index < len(pages) else None


def should_play(sequence: StorySequence | None, session, save) -> bool:
    return sequence is not None and not session.replay and sequence.key not in save.story_seen
