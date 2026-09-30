"""Hand-authored silhouettes on cached supersampled canvases.

Mirror glass, rippling sand, silk moth wings and iris-like bronze armor each
have their own animation language. No runtime sprite generation is needed.
"""

import math

from rendering.art.kit import Canvas, limb, mix

INK = (39, 28, 46)
GOLD = (224, 174, 80)
LIGHT = (251, 231, 166)
GLASS = (136, 222, 228)


def _joint(c, start, angle, length, color, radius=2):
    end = limb(start, angle, length)
    c.capsule(color, start, end, radius, INK, .7)
    return end


def paint_duelist(surface, animation, frame):
    c = Canvas(56, 56, fringe=INK)
    w = frame * math.tau / 6
    lunge = animation == "lunge"
    recover = animation == "recover"
    windup = animation == "windup"
    hip = (25, 42 + (2 if lunge else math.sin(w) * .6))
    shoulder = (hip[0] + (10 if lunge else -3 if windup else 0), hip[1] - 12)
    # Split turquoise cape: a different trailing contour on each frame.
    c.polygon((42, 108, 127), [(shoulder[0] - 3, shoulder[1]), (18, 33),
                              (6 + math.sin(w) * 3, 47), (17, 44), (12, 52), (29, 47)], INK)
    for side, angle in ((-1, -55 if lunge else -20), (1, 55 if lunge else 18)):
        knee = _joint(c, (hip[0] + side * 3, hip[1]), angle, 6, (122, 139, 161))
        foot = _joint(c, knee, -15 if side < 0 else 10, 6, (77, 91, 123))
        c.ellipse(GOLD, (foot[0] - 3, min(53, foot[1]) - 1, 7, 2), INK, .5)
    c.polygon((177, 206, 216), [(shoulder[0] - 5, shoulder[1]), (shoulder[0] + 5, shoulder[1]),
                              (hip[0] + 5, hip[1]), (hip[0] - 5, hip[1])], INK)
    c.line(LIGHT, shoulder, hip, 1)
    head = (shoulder[0] + 1, shoulder[1] - 7)
    c.polygon(GLASS, [(head[0] - 5, head[1] - 5), (head[0] + 5, head[1] - 5),
                     (head[0] + 6, head[1] + 2), (head[0], head[1] + 6), (head[0] - 5, head[1] + 1)], INK)
    c.line((240, 255, 255), (head[0] - 3, head[1] + 1), (head[0] + 3, head[1] - 3), 1.2)
    c.line(INK, (head[0] + 1, head[1] + 1), (head[0] + 5, head[1] + 1), 1.3)
    arm = _joint(c, shoulder, 92 if lunge else 35 if recover else 65, 9, (139, 180, 196))
    tip = (min(54, arm[0] + (12 if lunge else 5)), arm[1] + (9 if recover else -16))
    c.line(INK, arm, tip, 4)
    c.line(GLASS, arm, tip, 2)
    c.line(GOLD, (arm[0] - 3, arm[1] - 2), (arm[0] + 4, arm[1] + 1), 2)
    if windup:
        c.star(LIGHT, tip, 3 + frame % 3, points=4, inner=.2, rotation=frame * 12)
    if recover:
        c.ellipse(GLASS, (13, 9, 14, 3))
    surface.blit(c.finish(), (0, 0))


def paint_burrower(surface, animation, frame):
    c = Canvas(56, 56, fringe=INK)
    w = frame * math.tau / 6
    hidden = animation in ("walk", "warn")
    if animation == "emerge":
        rise = frame / 5
    elif animation == "retreat":
        rise = 1 - frame / 5
    else:
        rise = 1.0
    if not hidden:
        y = 52 - 25 * rise
        for i in range(4):
            x = 15 + i * 6
            cy = y + (3 - i) * 3 + math.sin(w + i * .7) * 1.3
            c.ellipse((170 + i * 12, 106 + i * 12, 69), (x - 5, cy, 13, 12), INK, .7)
            c.line(LIGHT, (x - 2, cy + 2), (x + 5, cy + 2), .8)
            c.polygon((66, 149, 148), [(x - 1, cy), (x + 2, cy - 5), (x + 5, cy)], INK, .5)
        c.ellipse((241, 188, 110), (31, y - 4, 14, 13), INK)
        c.circle(INK, (41, y + 1), 2)
        c.circle((255, 254, 222), (41.5, y), .7)
        c.line(INK, (39, y + 6), (46, y + 5), .8)
    c.ellipse((177, 122, 73), (8, 50, 40, 5))
    for i in range(3):
        width = 10 + i * 10 + (frame % 3) * 2
        c.ellipse((225, 179, 112), (28 - width / 2, 50 - i * 1.8, width, 3))
    if animation == "warn":
        c.star(LIGHT, (28, 38 - math.sin(w) * 2), 5, points=4, inner=.3)
        for i in range(5):
            c.circle(GOLD, (12 + i * 8, 45 - math.sin(w + i) * 3), .8)
    surface.blit(c.finish(), (0, 0))


def paint_thief(surface, animation, frame):
    c = Canvas(56, 56, fringe=INK)
    w = frame * math.tau / 8
    wing = 6 + 12 * (math.sin(w) + 1) / 2
    y = 34 + math.sin(w * 2)
    for side in (-1, 1):
        points = [(28 + side * 3, y), (28 + side * wing, y - 18),
                  (28 + side * (wing + 6), y - 8), (28 + side * 14, y + 7), (28, y + 5)]
        c.polygon((124, 80, 174), points, INK)
        c.line((222, 166, 208), points[0], points[1], 1)
        c.circle(GOLD, (28 + side * (wing - 1), y - 7), 3)
        c.circle((52, 47, 95), (28 + side * (wing - 1), y - 7), 1.4)
    c.ellipse((60, 50, 94), (22, y - 6, 12, 18), INK)
    c.polygon((213, 163, 217), [(21, y - 5), (25, y - 14), (34, y - 13), (36, y - 4), (28, y)], INK)
    c.line(INK, (23, y - 5), (35, y - 5), 3)
    for x in (27, 33):
        c.circle(LIGHT, (x, y - 5), 1)
        c.line(GOLD, (x, y - 11), (x + (3 if x > 28 else -4), y - 19), .8)
    for side in (-1, 1):
        c.line(GOLD, (28 + side * 4, y + 5), (28 + side * 7, y + 11), 1.5)
    if animation == "carry":
        c.circle((65, 124, 207), (28, y + 12), 6, INK)
        c.star((182, 242, 255), (28, y + 12), 5, points=4, inner=.5, rotation=frame * 12)
        c.ring(GOLD, (28, y + 12), 6, .8)
    surface.blit(c.finish(), (0, 0))


def paint_guardian(surface, animation, frame):
    c = Canvas(56, 56, fringe=INK)
    w = frame * math.tau / 6
    openness = 1.0 if animation == "open" else (frame / 5 if animation == "unfold" else 1 - frame / 5 if animation == "close" else 0)
    cy = 29 + (math.sin(w) if animation == "walk" else 0)
    for side in (-1, 1):
        knee = _joint(c, (28 + side * 8, cy + 11), side * (12 + (math.sin(w) * 15 if animation == "walk" else 0)), 7, GOLD, 3)
        ankle = _joint(c, knee, -side * 10, 7, (153, 106, 64), 2.5)
        c.ellipse(GOLD, (ankle[0] - 5, 52, 10, 3), INK, .6)
    c.star((123, 94, 64), (28, cy), 17, points=12, inner=.87, rotation=frame * 5, outline=INK)
    c.circle((46, 73, 77), (28, cy), 12, GOLD, 1)
    c.star((110, 248, 207), (28, cy), 7 + .8 * math.sin(w), points=8, inner=.5, rotation=frame * 12)
    for i in range(6):
        a = i * math.tau / 6 + .3
        center = (28 + math.cos(a) * (6 + openness * 11), cy + math.sin(a) * (6 + openness * 11))
        corners = [(center[0] + math.cos(a + j * math.pi / 2) * r,
                    center[1] + math.sin(a + j * math.pi / 2) * r) for j, r in enumerate((8, 5, 5, 5))]
        c.polygon(mix((156, 108, 59), GOLD, i / 6), corners, INK, .7)
        c.circle(LIGHT, center, 1)
    c.rect((182, 139, 79), (20, cy - 19, 16, 8), 2, INK, .7)
    c.line((114, 246, 215) if openness else LIGHT, (23, cy - 15), (33, cy - 15), 2)
    surface.blit(c.finish(), (0, 0))
