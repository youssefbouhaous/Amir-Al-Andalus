"""Ivory marquetry, oxblood leather and black iron for the Moonlit Library.

The silhouette is an open book, not an orb: a castle-clock bookcase contains
a folding, long-armed librarian. Everything that moves has a pin, rod or cord.
Large engraved pieces are supersampled once; the mechanism is drawn live.
"""

import math
from functools import lru_cache

import pygame

from jazari.art import gear
from rendering.art.kit import Canvas
from rendering.art import prince

BONE = (241, 229, 200)
PAPER = (255, 248, 225)
SHADE = (151, 137, 118)
RED = (174, 43, 59)
RED_DARK = (85, 28, 40)
IRON = (42, 39, 48)
STEEL = (115, 112, 118)
EDGE = (23, 22, 29)
BRASS = (166, 127, 83)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def line(surface, color, a, b, width=2):
    pygame.draw.line(surface, EDGE, a, b, width + 2)
    pygame.draw.line(surface, color, a, b, width)


def pin(surface, p, radius=4):
    p = (round(p[0]), round(p[1]))
    pygame.draw.circle(surface, EDGE, p, radius + 1)
    pygame.draw.circle(surface, BONE, p, radius)
    pygame.draw.circle(surface, IRON, p, max(1, radius // 2))


@lru_cache(maxsize=1)
def cabinet():
    c = Canvas(520, 400)
    # Deep recess: the scribe unfolds out of a book rather than a monster door.
    c.polygon(IRON, [(115, 370), (115, 115), (161, 79), (260, 20),
                     (359, 79), (405, 115), (405, 370)], EDGE, 2)
    for side in (-1, 1):
        x = 260 + side * 163
        c.polygon(RED_DARK, [(x - 50, 376), (x - 50, 97), (x, 64), (x + 50, 97), (x + 50, 376)], EDGE, 2)
        c.rect(BONE, (x - 53, 112, 7, 258), 1, EDGE, 1)
        c.rect(BONE, (x + 46, 112, 7, 258), 1, EDGE, 1)
        for row in range(5):
            y = 140 + row * 43
            c.rect(EDGE, (x - 44, y - 30, 87, 32))
            for k in range(8):
                bx = x - 40 + k * 10
                height = 21 + ((row * 13 + k * 7) % 10)
                color = (BONE, RED, SHADE, BRASS)[(k + row) % 4]
                c.rect(color, (bx, y - height, 7, height), .5)
                c.line(EDGE, (bx + 2, y - height + 4), (bx + 6, y - height + 4), .6)
                c.line(EDGE, (bx + 2, y - 4), (bx + 6, y - 4), .6)
            c.rect(BRASS, (x - 46, y + 2, 91, 4), 0, EDGE, .8)
        # Trefoil crest and blind arcade, inlaid rather than luminous.
        for k in range(3):
            bx = x - 28 + k * 28
            c.circle(BONE, (bx, 94), 11, EDGE, 1)
            c.rect(BONE, (bx - 11, 95, 22, 16))
            c.polygon(RED, [(bx, 89), (bx + 5, 98), (bx, 107), (bx - 5, 98)])
    # The clock is a twelve-window castle façade with a working hand.
    c.circle(BRASS, (260, 94), 71, EDGE, 2)
    c.circle(BONE, (260, 94), 65, RED_DARK, 2)
    c.circle(IRON, (260, 94), 51, SHADE, 1)
    for k in range(12):
        a = k * math.tau / 12
        x, y = 260 + math.sin(a) * 58, 94 - math.cos(a) * 58
        c.polygon(RED, [(x - 3, y), (x, y - 5), (x + 3, y), (x, y + 5)])
    # Open-book cornice, carrying actual etched linkages.
    for side in (-1, 1):
        pts = [(260, 35), (260 + side * 55, 8), (260 + side * 104, 16),
               (260 + side * 94, 43), (260, 51)]
        c.polygon(BONE, pts, EDGE, 1.4)
        for row in range(3):
            c.line(SHADE, (260 + side * 9, 33 + row * 4),
                   (260 + side * 91, 21 + row * 5), .8)
    c.rect(RED_DARK, (49, 370, 422, 17), 2, EDGE, 2)
    c.rect(BONE, (42, 385, 436, 10), 1, EDGE, 1)
    for k in range(17):
        x = 55 + k * 24
        c.polygon(BRASS, [(x, 373), (x + 8, 380), (x, 384), (x - 8, 380)])
    return c.finish()


@lru_cache(maxsize=1)
def head():
    c = Canvas(106, 102)
    # Split manuscript covers form the brow; a nib-shaped nose remains metal.
    c.polygon(RED_DARK, [(8, 10), (50, 26), (98, 10), (84, 80), (53, 96), (21, 80)], EDGE, 1.8)
    c.polygon(BONE, [(14, 17), (49, 31), (49, 88), (26, 75)], EDGE, 1)
    c.polygon(PAPER, [(56, 31), (93, 17), (80, 75), (56, 88)], EDGE, 1)
    for side in (-1, 1):
        x = 53 + side * 22
        c.circle(BRASS, (x, 51), 15, EDGE, 1.2)
        c.circle(IRON, (x, 51), 11)
        c.circle(BONE, (x - side * 3, 51), 4)
        c.line(SHADE, (x - 10, 69), (x + 6, 76), 1)
        c.line(SHADE, (x - 8, 74), (x + 4, 80), .7)
    c.line(BRASS, (45, 51), (60, 51), 3)
    c.polygon(IRON, [(49, 52), (57, 52), (61, 68), (53, 81), (45, 68)], EDGE, 1)
    c.line(BONE, (53, 58), (53, 73), 1)
    return c.finish()


@lru_cache(maxsize=32)
def manuscript_prince(pose, frame=0):
    image = prince.draw_pose(prince.pose_for(pose, frame % 8, 8), prince.PRINCE_PALETTE)
    return pygame.transform.smoothscale(image, (72, 72))


def arm(surface, root, tip, side, closed=0.0):
    """Two pinned links and five hinged book-clamp fingers; tip is the hitbox."""
    a, b = pygame.Vector2(root), pygame.Vector2(tip)
    delta = b - a
    distance = max(1, delta.length())
    normal = pygame.Vector2(-delta.y, delta.x) / distance
    elbow = (a + b) * .5 + normal * side * math.sqrt(max(0, 119 ** 2 - (distance / 2) ** 2))
    for start, end in ((a, elbow), (elbow, b)):
        line(surface, STEEL, start, end, 12)
        d = end - start
        n = pygame.Vector2(-d.y, d.x).normalize() * 7 if d.length_squared() else pygame.Vector2(7, 0)
        pts = (start.lerp(end, .12) + n, start.lerp(end, .78) + n * .6,
               start.lerp(end, .9) - n * .6, start.lerp(end, .1) - n)
        pygame.draw.polygon(surface, EDGE, pts)
        pygame.draw.polygon(surface, BONE, pts, 3)
        line(surface, RED, start.lerp(end, .22), start.lerp(end, .73), 2)
    pin(surface, a, 7)
    pin(surface, elbow, 6)
    pin(surface, b, 5)
    x, y = b
    pygame.draw.rect(surface, EDGE, (x - 27, y - 12, 54, 25), border_radius=4)
    pygame.draw.rect(surface, RED_DARK, (x - 25, y - 10, 50, 21), border_radius=3)
    for k in range(5):
        px = x - 21 + k * 10
        extension = 10 + 9 * (1 - closed)
        line(surface, BONE, (px, y - 4), (px + side * 3, y + extension), 4)
        pin(surface, (px, y - 4), 2)


def cabinet_live(surface, origin, clock, released, teeth, open_amount, weight_drop=1.0):
    x, floor = origin
    surface.blit(cabinet(), (round(x - 260), round(floor - 395)))
    dial = (x, floor - 301)
    gear(surface, dial, 35, 12, clock * .8, BRASS)
    hand = (dial[0] + math.sin(clock) * 48, dial[1] - math.cos(clock) * 48)
    line(surface, RED, dial, hand, 3)
    pin(surface, dial, 5)
    # Three labelled hanging drives: one counterweight per chapter of the fight.
    for k, dx in enumerate((-190, 151, 204)):
        finished = k < released
        drop = (118 * weight_drop if k == released - 1 else 118) if finished else 0
        cy = floor - 245 + drop
        px = x + dx
        line(surface, SHADE, (px, floor - 329), (px, cy - 10), 2)
        gear(surface, (px, floor - 327), 12, 9, clock * (-1 if k % 2 else 1), SHADE)
        pygame.draw.rect(surface, EDGE, (px - 12, cy - 12, 24, 37), border_radius=3)
        pygame.draw.rect(surface, BONE if finished else BRASS, (px - 10, cy - 10, 20, 33), border_radius=2)
        for notch in range(k + 1):
            pygame.draw.line(surface, RED, (px - 6, cy + notch * 6), (px + 6, cy + notch * 6), 2)
    # Exposed crank and connecting rod, visibly held still by a brace.
    gear(surface, (x, floor - 79), 29, 10, clock * 2, BONE)
    crank = (x + math.sin(clock * 2) * 22, floor - 79 + math.cos(clock * 2) * 22)
    line(surface, RED, crank, (x + 62, floor - 54), 5)
    pin(surface, crank, 4)
    line(surface, STEEL, (x - 139, floor - 75), (x + 139, floor - 75), 5)
    for i, dx in enumerate((-96, 0, 96)):
        center = (x + dx, floor - 16)
        active = i == released
        opened = open_amount if active else float(i < released)
        cam = (x + dx, floor - 75)
        gear(surface, cam, 10, 7, clock * 2 + i, BRASS)
        # Followers connect the shared camshaft to each jaw and semaphore.
        for side in (-1, 1):
            line(surface, RED, cam, (center[0] + side * 29, floor - 63 + opened * 9), 2)
        # A real jaw opens above the treadle, not a coloured weak-point blob.
        for side in (-1, 1):
            pygame.draw.polygon(surface, EDGE, [(center[0] + side * 29, floor - 65),
                (center[0] + side * (5 + opened * 22), floor - 36),
                (center[0] + side * (5 + opened * 22), floor - 21),
                (center[0] + side * 34, floor - 49)])
            pygame.draw.line(surface, BONE, (center[0] + side * 29, floor - 63),
                             (center[0] + side * (8 + opened * 22), floor - 25), 4)
        pygame.draw.rect(surface, EDGE, (center[0] - 26, floor - 7, 52, 7), border_radius=2)
        pygame.draw.rect(surface, BONE if active else SHADE, (center[0] - 24, floor - 6, 48, 4))
        for n in range(6):
            color = PAPER if i < released or (active and n < teeth) else RED_DARK
            pygame.draw.rect(surface, color, (center[0] - 23 + n * 8, floor + 1, 6, 7))
        if active:
            # Tiny mechanical semaphore shares the same opening as the jaw.
            line(surface, IRON, (center[0] - 32, floor - 8), (center[0] - 32, floor - 81), 3)
            pygame.draw.polygon(surface, BONE if opened > .7 else RED, [
                (center[0] - 32, floor - 81), (center[0] - 7, floor - 81 - opened * 18),
                (center[0] - 13, floor - 67 - opened * 18), (center[0] - 32, floor - 70)])


def archivist(surface, origin, clock, tips, release=0.0):
    x, floor = origin
    # Telescoping spine and open folio chest; the final bow folds the figure away.
    sink = release * 82
    cy = floor - 171 + sink
    for k in range(8):
        pygame.draw.rect(surface, BONE if k % 2 else BRASS, (x - 12, cy + k * 9, 24, 7))
    for side in (-1, 1):
        pts = [(x + side * 6, cy - 29), (x + side * 53, cy - 14),
               (x + side * 38, cy + 53), (x + side * 6, cy + 39)]
        pygame.draw.polygon(surface, EDGE, pts)
        pygame.draw.polygon(surface, RED_DARK, pts, 4)
        for k in range(7):
            line(surface, SHADE, (x + side * 11, cy - 18 + k * 8),
                 (x + side * (43 - k), cy - 7 + k * 8), 1)
    for side, tip in zip((-1, 1), tips):
        arm(surface, (x + side * 43, cy - 7), (x + tip[0], floor + tip[1]), side, release)
    nod = math.sin(clock * .5) * 2 * (1 - release * .7)
    image = head()
    surface.blit(image, image.get_rect(midbottom=(round(x), round(cy - 19 + nod))))


def folds(surface, a, b, spread, count=6, scale=1.0):
    """An articulated diamond lattice with taut red cords, not a magic trail."""
    start, end = pygame.Vector2(a), pygame.Vector2(b)
    delta = end - start
    if delta.length_squared() < 1:
        return
    normal = pygame.Vector2(-delta.y, delta.x).normalize()
    last_top, last_bottom = start, start
    for k in range(count):
        u = (k + .5) / count
        center = start.lerp(end, u)
        width = math.sin(math.pi * u) * spread
        top, bottom = center + normal * width, center - normal * width
        for p, q in ((last_top, bottom), (last_bottom, top)):
            line(surface, BONE if k % 2 else SHADE, p, q, max(2, round(4 * scale)))
        line(surface, RED, last_top, top, max(1, round(scale * 2)))
        line(surface, RED, last_bottom, bottom, max(1, round(scale * 2)))
        pin(surface, top, max(2, round(3 * scale)))
        pin(surface, bottom, max(2, round(3 * scale)))
        last_top, last_bottom = top, bottom
    line(surface, BONE, last_top, end, max(2, round(4 * scale)))
    line(surface, BONE, last_bottom, end, max(2, round(4 * scale)))
    pin(surface, start, max(2, round(4 * scale)))
    pin(surface, end, max(2, round(4 * scale)))


def lift(surface, center, floor, height, time):
    x = center
    pygame.draw.ellipse(surface, EDGE, (x - 33, floor - 3, 66, 6))
    folds(surface, (x, floor - 4), (x, floor - height), 26, 4)
    pygame.draw.rect(surface, EDGE, (x - 34, floor - height - 2, 68, 9), border_radius=3)
    pygame.draw.rect(surface, BONE, (x - 32, floor - height, 64, 4), border_radius=2)
    for k in range(5):
        pygame.draw.line(surface, RED, (x - 24 + k * 12, floor - height),
                         (x - 20 + k * 12, floor - height + 3), 2)
    gear(surface, (x, floor - 8), 8, 8, time * 3, BRASS)


def emblem(surface, rect, time):
    x, y = rect.center
    length = min(rect.width, rect.height) * .39
    breathe = .78 + .22 * abs(math.sin(time * 1.8))
    folds(surface, (x - length, y + length * .55), (x + length, y - length * .55),
          length * .38 * breathe, 3, .6)


def ceremony(surface, center, t):
    """Engraved ribs lift from the page, hinge into a lattice, then fold to a cuff."""
    cx, cy = center
    open_ = smooth((t - .3) / .32)
    close = smooth((t - .72) / .28)
    span = (34 + 145 * open_) * (1 - close) + 13 * close
    y = cy - 100 * (1 - close) - 9 * close
    x = cx + 13 * close
    # Six physical ruler leaves arrive on straight ruled paths, in staggered clicks.
    if t < .37:
        for k in range(6):
            p = smooth((t - k * .032) / .18)
            start_x = cx + (-1 if k % 2 else 1) * (150 + k * 17) * (1 - p)
            start_y = cy - 145 + k * 15
            end_y = y + (k - 2.5) * 3
            yy = start_y + (end_y - start_y) * p
            line(surface, BONE, (start_x - 27, yy - 10), (start_x + 27, yy + 10), 6)
            pin(surface, (start_x, yy), 3)
    else:
        folds(surface, (x - span, y + span * .3), (x + span, y - span * .3),
              (12 + 29 * open_) * (1 - close) + 3, 6, 1.35 - close * .7)
    # A counterweight drops and pulls the last cord taut: the freeze is mechanical.
    if .4 < t < .78:
        fall = smooth((t - .4) / .17)
        wx, wy = x + span - 8, y + 9 + 64 * fall
        line(surface, RED, (wx, y - 14), (wx, wy), 2)
        pygame.draw.rect(surface, EDGE, (wx - 10, wy, 20, 27), border_radius=3)
        pygame.draw.rect(surface, BONE, (wx - 8, wy + 2, 16, 23), border_radius=2)
        for n in range(3):
            pygame.draw.line(surface, RED, (wx - 5, wy + 7 + n * 5), (wx + 5, wy + 7 + n * 5), 1)
