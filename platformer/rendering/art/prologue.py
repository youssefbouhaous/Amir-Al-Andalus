"""Film-only acting poses and props, extending (not replacing) the prince rig."""

import math
from dataclasses import dataclass, replace

import pygame

from rendering.animation import Animation
from rendering.art import prince
from rendering.art.kit import Canvas

EXTRA_POSES = ("look", "kneel", "receive", "read", "fold", "light", "wave", "offer", "tend", "walk", "land")
GARDENER = replace(prince.PRINCE_PALETTE, robe=(150, 97, 62), robe_shade=(92, 61, 48),
                   sash=(74, 112, 98), turban=(226, 214, 181), turban_shade=(166, 150, 121),
                   plume=(226, 214, 181), scarf=(99, 119, 97), slipper=(82, 59, 45))
VILLAGER = replace(GARDENER, robe=(133, 90, 141), robe_shade=(86, 61, 108), sash=(198, 143, 62))


def acting_pose(name: str, frame: int, count: int = 8) -> prince.Pose:
    t = frame / max(1, count - 1)
    wave = math.sin(math.tau * frame / count)
    if name == "walk":
        p = prince.pose_for("run", frame, count)
        return replace(p, lean=3, front_thigh=p.front_thigh * .6, back_thigh=p.back_thigh * .6,
                       front_knee=p.front_knee * .55, back_knee=p.back_knee * .55,
                       front_upper=p.front_upper * .45, back_upper=p.back_upper * .45,
                       plume=4, hem=3)
    if name == "kneel":
        p = prince.pose_for("sit", frame, count)
        return replace(p, lean=24, head_tilt=10, front_upper=65 + wave * 2,
                       front_elbow=8, back_upper=15, back_elbow=55, eyes="wide", mouth="none")
    if name in ("read", "fold"):
        return prince.Pose(lean=4, head_tilt=14, front_upper=66, front_elbow=67,
                           back_upper=51, back_elbow=76, head_dy=.35 * wave,
                           plume=6, eyes="open", mouth="none", hem=wave)
    if name in ("receive", "offer"):
        return prince.Pose(lean=5 * t, head_tilt=5, front_upper=35 + 46 * t,
                           front_elbow=55 * (1 - t), back_upper=15, back_elbow=38,
                           mouth="smile" if name == "offer" else "none", plume=8)
    if name == "light":
        return prince.Pose(lean=3, head_tilt=-8, front_upper=110, front_elbow=-8,
                           back_upper=-12, back_elbow=22, plume=10, hand_glow=False)
    if name == "wave":
        return prince.Pose(lean=-3, head_tilt=-4, front_upper=150 + 10 * wave,
                           front_elbow=12 - 8 * wave, back_upper=8, back_elbow=18,
                           mouth="smile", eyes="happy", plume=8 + 4 * wave)
    if name == "tend":
        return prince.Pose(hip_y=37, lean=12 + 3 * wave, head_tilt=10, front_upper=45,
                           front_elbow=50, back_upper=10, back_elbow=30,
                           front_thigh=20, front_knee=22, back_knee=20, plume=6)
    if name == "land":
        bend = 1 - t
        return prince.Pose(hip_y=35.8 + 4 * bend, lean=22 * bend, head_tilt=-10 * bend,
                           front_thigh=50 * bend, front_knee=85 * bend,
                           back_thigh=26 * bend, back_knee=65 * bend,
                           front_upper=35 * bend, front_elbow=35, back_upper=-35 * bend)
    p = prince.pose_for("idle", frame, count)
    return replace(p, head_tilt=-8, lean=-3, mouth="none")


@dataclass
class ActorArt:
    animations: dict[str, Animation]
    anchors: dict[str, tuple[tuple[float, float], ...]]
    hands: dict[str, tuple[tuple[float, float], ...]]


def actor_art(original, palette=prince.PRINCE_PALETTE, elder=False) -> ActorArt:
    animations, anchors, hands = {}, {}, {}
    names = {"idle", "run", "skid", "jump", "apex", "fall"} | set(EXTRA_POSES)
    for name in names:
        extra = name in EXTRA_POSES
        count = 8 if extra else len(original[name].frames)
        frames, head_points, hand_points = [], [], []
        for index in range(count):
            pose = acting_pose(name, index, count) if extra else prince.pose_for(name, index, count)
            # Custom player PNGs remain in use for the established actions.
            image = (original[name].frames[index] if not extra and palette is prince.PRINCE_PALETTE
                     else prince.draw_pose(pose, palette))
            skeleton = prince.skeleton(pose)
            if elder:
                c = Canvas(48, 48, fringe=prince.OUTLINE)
                c.blit(image, (0, 0))
                hx, hy = skeleton.head
                c.polygon((218, 214, 197), [(hx - 3, hy + 2), (hx + 4, hy + 3), (hx + 1, hy + 9)],
                          (107, 98, 83), .5)
                image = c.finish()
            frames.append(image)
            hx, hy = skeleton.head
            head_points.append((hx - 5.8 - 24, hy - 4.4 - 48))
            hand_points.append((skeleton.front_hand[0] - 24, skeleton.front_hand[1] - 48))
        loop = name not in ("receive", "offer", "land")
        duration = .035 if name == "land" else .12
        if not extra:
            duration, loop = original[name].frame_duration, original[name].loop
        animations[name] = Animation(tuple(frames), duration, loop)
        anchors[name] = tuple(head_points)
        hands[name] = tuple(hand_points)
    return ActorArt(animations, anchors, hands)


def jug():
    c = Canvas(28, 32, fringe=(68, 41, 34))
    c.ring((156, 90, 52), (22, 14), 5, 2)
    c.ellipse((180, 112, 65), (4, 9, 19, 21), (74, 45, 33), .8)
    c.rect((180, 112, 65), (9, 4, 10, 10), 1, (74, 45, 33), .7)
    c.ellipse((70, 47, 43), (8, 3, 12, 5), (218, 159, 102), .7)
    c.line((223, 169, 113), (7, 20), (20, 20), 1.4)
    c.line((223, 169, 113), (8, 24), (20, 24), .8)
    return c.finish()


ROUTE_POINTS = ((48, 139), (151, 86), (267, 124), (377, 73), (489, 45))
ROUTE_LABELS = ("MARKET", "LIBRARY", "AQUEDUCT", "OBSERVATORY", "SUMMIT")


def route_map(font):
    c = Canvas(560, 202, fringe=(60, 37, 30))
    edge = [(14, 8), (176, 12), (281, 5), (398, 9), (535, 5), (549, 31),
            (540, 66), (552, 98), (534, 116), (545, 160), (528, 196), (388, 193),
            (268, 198), (139, 191), (10, 198), (6, 155), (12, 119), (4, 66)]
    c.polygon((224, 196, 143), edge, (97, 64, 41), 2)
    c.polygon((239, 216, 168), [(19, 20), (525, 17), (525, 181), (18, 182)])
    for x in (174, 350):
        c.line((206, 176, 124), (x, 16), (x + 9, 186), 1.2)
    # Tiny drawn landmarks, rather than detached UI buttons.
    ink = (102, 87, 63)
    for x, y in ROUTE_POINTS[:2]:
        for i in range(3):
            c.rect(ink, (x - 16 + i * 10, y - 18 - i * 4, 8, 18 + i * 4))
    for i in range(4):
        x, y = 248 + i * 11, 119
        c.lines(ink, [(x, y), (x, y - 17), (x + 5, y - 22), (x + 10, y - 17), (x + 10, y)], 1.2)
    c.ring(ink, (377, 59), 15, 1.5)
    c.line(ink, (360, 59), (394, 59), 1)
    c.line(ink, (377, 42), (377, 77), 1)
    c.lines(ink, [(457, 49), (478, 17), (493, 39), (502, 28), (523, 55)], 1.5)
    c.line((170, 109, 44), (489, 16), (489, 44), 2)
    c.line((170, 109, 44), (482, 23), (496, 23), 2)
    image = c.finish()
    for (x, y), label in zip(ROUTE_POINTS, ROUTE_LABELS):
        text = font.render(label, True, ink)
        position = (389, 113) if label == "OBSERVATORY" else (x, y + 8)
        image.blit(text, text.get_rect(midtop=position))
    return image
