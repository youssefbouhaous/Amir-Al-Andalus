"""Ivory marquetry, oxblood leather and black iron: the Folded Fulcrum's look.

The Fulcrum is a lattice of pinned ivory ribs with taut red cords; it unfolds
into a lifting step or a brace for a clock's jaw. (Level 3's clock and its
keeper are drawn in ``rendering/art/castleclock.py``.)
"""

import math
from functools import lru_cache

import pygame

from jazari.art import gear
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


@lru_cache(maxsize=32)
def manuscript_prince(pose, frame=0):
    image = prince.draw_pose(prince.pose_for(pose, frame % 8, 8), prince.PRINCE_PALETTE)
    return pygame.transform.smoothscale(image, (72, 72))


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
