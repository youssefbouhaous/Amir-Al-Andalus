"""The opening film: first-person story and deterministic actor choreography.

This is a little stage, not a playable map. Sampling any time (including after
skipping a shot) produces the same positions, props and camera. No gameplay
physics, save progress, water hazards or chapter timers run in the film.
"""

from dataclasses import dataclass

PROLOGUE_KEY = "prologue:the-lantern-promise:v1"
FLOOR = 408.0
WORLD_WIDTH = 2240
FOUNTAIN_X = 888
LANTERN_X = 1576


@dataclass(frozen=True)
class Shot:
    start: float
    end: float
    text: str


SHOTS = (
    Shot(0, 8, "My name is Amir. In the palace, they call me prince. But I knew my city by its rooftops, orange trees, and running water."),
    Shot(8, 16, "Every morning I raced the garden channels. That water filled our cups, cooled our homes, and kept the orchards alive."),
    Shot(16, 25, "Then, one morning, the fountain fell silent. I caught its last drop. Beyond the palace walls, people were already waiting with empty jars."),
    Shot(25, 34, "My gardener brought an old map. 'The Sword of Light guards our springs,' he said. 'Find it in the mountain shrine. Bring its light home.'"),
    Shot(34, 43, "To find it, I would cross the market roofs, search the moonlit library, and follow the aqueduct to the brass observatory. There lay the path uphill."),
    Shot(43, 51, "One warning remained: 'The blade is a key. Remember what it keeps closed.' The rest of the page had been torn away."),
    Shot(51, 60, "I could stay behind the palace walls and wait. Or I could find the Sword, restore the springs, and bring water home. I chose the road."),
    Shot(60, 70, "I lit a lantern for my return. 'Keep it burning,' I told the gardener. 'I'll bring the water back.' And I stepped beyond the orchard gate."),
)
DURATION = SHOTS[-1].end


def fraction(time: float, start: float, end: float) -> float:
    return max(0.0, min(1.0, (time - start) / (end - start)))


def ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def between(time: float, start: float, end: float, a: float, b: float) -> float:
    return a + (b - a) * ease(fraction(time, start, end))


@dataclass(frozen=True)
class Motion:
    start: float
    end: float
    x0: float
    x1: float
    pose: str
    facing: int = 1
    jump_height: float = 0


# Feet are world coordinates. Jumps have authored parabolic arcs; all clips
# meet at the same position so advancing the camera never slides an idle sprite.
AMIR_TRACK = (
    Motion(0, 1.5, 154, 154, "look"),
    Motion(1.5, 7.2, 154, 432, "run"),
    Motion(7.2, 9.0, 432, 602, "jump", jump_height=105),
    Motion(9.0, 9.28, 602, 602, "land"),
    Motion(9.28, 13.8, 602, 791, "run"),
    Motion(13.8, 14.2, 791, 806, "skid"),
    Motion(14.2, 17.2, 806, 806, "look"),
    Motion(17.2, 23.8, 806, 806, "kneel"),
    Motion(23.8, 27.0, 806, 806, "look"),
    Motion(27.0, 30.5, 806, 806, "receive"),
    Motion(30.5, 50.0, 806, 806, "read"),
    Motion(50.0, 51.5, 806, 806, "fold"),
    Motion(51.5, 58.2, 806, 1522, "run"),
    Motion(58.2, 58.6, 1522, 1533, "skid"),
    Motion(58.6, 62.0, 1533, 1533, "light"),
    Motion(62.0, 64.5, 1533, 1533, "wave", facing=-1),
    Motion(64.5, 70.0, 1533, 2130, "run"),
)
GARDENER_TRACK = (
    Motion(0, 24, 1008, 1008, "tend", facing=-1),
    Motion(24, 27, 1008, 866, "walk", facing=-1),
    Motion(27, 30.5, 866, 866, "offer", facing=-1),
    Motion(30.5, 50.5, 866, 866, "look", facing=-1),
    Motion(50.5, 60, 866, 1380, "walk"),
    Motion(60, 70, 1380, 1380, "wave"),
)


@dataclass(frozen=True)
class ActorFrame:
    x: float
    y: float
    pose: str
    facing: int
    elapsed: float
    airborne: bool = False


def actor_at(track: tuple[Motion, ...], time: float) -> ActorFrame:
    clip = next((clip for clip in track if time < clip.end), track[-1])
    t = fraction(time, clip.start, clip.end)
    x = clip.x0 + (clip.x1 - clip.x0) * t
    y = FLOOR - 4 * clip.jump_height * t * (1 - t)
    pose = clip.pose
    if clip.jump_height:
        pose = "jump" if t < .38 else "apex" if t < .62 else "fall"
    return ActorFrame(x, y, pose, clip.facing, max(0, time - clip.start), bool(clip.jump_height and 0 < t < 1))


@dataclass(frozen=True)
class PrologueFrame:
    time: float
    shot: int
    amir: ActorFrame
    gardener: ActorFrame
    camera_x: float
    water: float
    map_open: float
    route: float
    warning: float
    page_handoff: float
    lantern: float
    fade: float


def sample(time: float) -> PrologueFrame:
    time = max(0.0, min(DURATION, time))
    amir = actor_at(AMIR_TRACK, time)
    gardener = actor_at(GARDENER_TRACK, time)
    # The camera leads a travelling actor, then settles on the two-person scene.
    if time < 15:
        camera_x = between(time, 2, 15, 0, 410)
    elif time < 51.5:
        camera_x = 410
    else:
        camera_x = max(410, min(WORLD_WIDTH - 960, amir.x - 405))
    return PrologueFrame(
        time=time,
        shot=next((i for i, shot in enumerate(SHOTS) if time < shot.end), len(SHOTS) - 1),
        amir=amir, gardener=gardener, camera_x=camera_x,
        water=1 - ease(fraction(time, 16.3, 20.0)),
        map_open=ease(fraction(time, 32.5, 34.0)) * (1 - ease(fraction(time, 49.4, 50.6))),
        route=fraction(time, 34, 41.5), warning=ease(fraction(time, 43, 44)),
        page_handoff=ease(fraction(time, 28, 30)),
        lantern=ease(fraction(time, 60.1, 60.7)),
        fade=max(1 - fraction(time, 0, 1.0), fraction(time, 68.8, 70)),
    )


# Time, existing sound, volume. Skipping seeks without playing missed effects.
SOUND_CUES = ((7.2, "jump", .55), (9.0, "land", .6), (19.3, "splash", .35),
              (28.5, "page", .65), (50.3, "page", .35), (60.25, "checkpoint", .7))
