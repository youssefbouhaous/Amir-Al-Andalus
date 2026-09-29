"""Background art: horizontally tileable parallax strips and sky objects.

Each strip is a silhouette of one depth band: distant mountains, a city
skyline with a recognisable landmark of the level's city, or a line of
trees. Strips are drawn with a 2x supersampled canvas for smooth edges and
must tile seamlessly, so every shape stays well inside the strip or wraps.

Landmarks (simplified but faithful in outline):
* Qurtuba: the Great Mosque's long roofline and minaret, the Roman bridge.
* Madinat al-Zahra: the palace-city's terraces climbing the Sierra Morena.
* Tulaytula: the city crowning its hill, ringed by the Tagus gorge.
* Ishbiliya: the Almohad minaret (today's Giralda) with its golden yamur,
  and the twelve-sided Torre del Oro by the river.
* Gharnata: the Alhambra's walls and towers under the Sierra Nevada.
"""

import math
import random

import pygame

from core.settings import Color
from rendering.art.kit import Canvas, mix, shade

STRIP_WIDTH = 1920
LIGHT: Color = (255, 214, 130)


def _canvas(width: int, height: int, color: Color) -> Canvas:
    return Canvas(width, height, scale=2, fringe=color)


# --- Mountains / hills ------------------------------------------------------------
def mountains(height: int, color: Color, snow: Color | None, seed: int, peaks: int = 7,
              jagged: float = 1.0, min_height: float = 0.35) -> pygame.Surface:
    """A tileable range: peak heights are periodic so both ends match."""
    c = _canvas(STRIP_WIDTH, height, color)
    rng = random.Random(seed)
    heights = [rng.uniform(min_height, 1.0) for _ in range(peaks)]
    ridge: list[tuple[float, float]] = []
    samples = 160
    for k in range(samples + 1):
        x = STRIP_WIDTH * k / samples
        t = k / samples * peaks
        i0 = int(t) % peaks
        i1 = (i0 + 1) % peaks
        frac = t - int(t)
        profile = heights[i0] * (1 - frac) + heights[i1] * frac
        peakness = 1.0 - abs(frac - 0.5) * 2
        y = height - height * (0.25 + 0.75 * profile * (0.55 + 0.45 * peakness))
        y += (math.sin(k * 1.7 + seed) * 4 + math.sin(k * 5.3) * 2) * jagged
        ridge.append((x, max(4.0, y)))
    closed = [(0.0, float(height))] + ridge + [(float(STRIP_WIDTH), float(height))]
    if snow is None:
        c.polygon(color, closed)
        return c.finish()
    # Snow caps: draw the range in snow, then the rock again lowered by an
    # amount that is zero below the snow line and grows toward the peaks.
    snowline = height * 0.45
    c.polygon(snow, closed)
    rock = [(0.0, float(height))]
    for index, (x, y) in enumerate(ridge):
        drop = max(0.0, snowline - y) * 0.75 + (math.sin(index * 2.9) * 3 if y < snowline else 0)
        rock.append((x, y + drop))
    rock.append((float(STRIP_WIDTH), float(height)))
    c.polygon(color, rock)
    return c.finish()


def hills(height: int, color: Color, seed: int, bumps: int = 5) -> pygame.Surface:
    c = _canvas(STRIP_WIDTH, height, color)
    rng = random.Random(seed)
    amplitudes = [rng.uniform(0.3, 0.9) for _ in range(bumps)]
    points = [(0.0, float(height))]
    for k in range(121):
        x = STRIP_WIDTH * k / 120
        y = height * 0.55
        for index, amp in enumerate(amplitudes):
            y -= math.sin((k / 120) * math.tau * (index + 1) + index * 1.3) * height * 0.12 * amp
        points.append((x, y))
    points.append((float(STRIP_WIDTH), float(height)))
    c.polygon(color, points)
    return c.finish()


# --- Building blocks for skylines ----------------------------------------------------------
def _crenellated_wall(c: Canvas, color: Color, x0: float, x1: float, base: float, top: float, merlon: float = 7) -> None:
    c.rect(color, (x0, top, x1 - x0, base - top))
    x = x0
    while x < x1 - merlon * 0.5:
        c.rect(color, (x, top - merlon, merlon * 0.65, merlon + 1))
        x += merlon * 1.3


def _tower(c: Canvas, color: Color, x: float, base: float, width: float, height: float, merlon: float = 6) -> None:
    _crenellated_wall(c, color, x, x + width, base, base - height, merlon)


def _dome(c: Canvas, color: Color, cx: float, base: float, radius: float) -> None:
    c.ellipse(color, (cx - radius, base - radius * 1.4, radius * 2, radius * 2))
    c.rect(color, (cx - radius, base - radius * 0.4, radius * 2, radius * 0.4 + 1))
    c.line(color, (cx, base - radius * 1.4), (cx, base - radius * 1.9), 2)


def _cypress(c: Canvas, color: Color, x: float, base: float, height: float) -> None:
    width = height * 0.16
    c.ellipse(color, (x - width / 2, base - height, width, height))
    c.rect(color, (x - width * 0.2, base - height * 0.15, width * 0.4, height * 0.15))


def _palm(c: Canvas, color: Color, x: float, base: float, height: float) -> None:
    top = (x + height * 0.1, base - height)
    c.lines(color, [(x, base), (x + height * 0.06, base - height * 0.5), top], max(2.0, height * 0.035))
    for angle, length in ((-160, 0.42), (-130, 0.5), (-100, 0.3), (-60, 0.5), (-25, 0.44), (-80, 0.35)):
        a = math.radians(angle)
        tip = (top[0] + math.cos(a) * height * length, top[1] - math.sin(a) * height * length * 0.4 + height * length * 0.35)
        mid = ((top[0] + tip[0]) / 2, (top[1] + tip[1]) / 2 - height * 0.06)
        c.tapered(color, [top, mid, tip], max(1.5, height * 0.03), 0.5)


def _orange_tree(c: Canvas, color: Color, x: float, base: float, height: float) -> None:
    c.rect(color, (x - height * 0.05, base - height * 0.45, height * 0.1, height * 0.45))
    c.circle(color, (x, base - height * 0.62), height * 0.34)
    c.circle(color, (x - height * 0.22, base - height * 0.5), height * 0.22)
    c.circle(color, (x + height * 0.22, base - height * 0.52), height * 0.24)


def _pine(c: Canvas, color: Color, x: float, base: float, height: float, snow: Color | None = None) -> None:
    c.rect(color, (x - height * 0.04, base - height * 0.2, height * 0.08, height * 0.2))
    for k in range(4):
        w = height * (0.42 - k * 0.08)
        y = base - height * (0.18 + k * 0.2)
        c.polygon(color, [(x - w, y), (x, y - height * 0.32), (x + w, y)])
        if snow is not None:
            c.polygon(snow, [(x - w * 0.4, y - height * 0.2), (x, y - height * 0.32), (x + w * 0.4, y - height * 0.2)])


def _houses_row(c: Canvas, color: Color, rng: random.Random, x0: float, x1: float, base: float,
                min_h: float, max_h: float, windows: Color | None = None) -> None:
    x = x0
    while x < x1:
        w = rng.uniform(26, 60)
        h = rng.uniform(min_h, max_h)
        c.rect(color, (x, base - h, w + 1, h))
        if rng.random() < 0.3:
            c.polygon(color, [(x - 2, base - h), (x + w / 2, base - h - 10), (x + w + 2, base - h)])
        if windows is not None:
            for wy in range(int(base - h + 8), int(base - 6), 14):
                for wx in range(int(x + 5), int(x + w - 6), 12):
                    if rng.random() < 0.28:
                        c.rect(windows, (wx, wy, 3.5, 5))
        x += w


# --- City skylines ------------------------------------------------------------------------
def skyline(style: str, height: int, color: Color, seed: int, windows: Color | None = None) -> pygame.Surface:
    c = _canvas(STRIP_WIDTH, height, color)
    rng = random.Random(seed)
    base = float(height)
    painter = _SKYLINES.get(style, _skyline_generic)
    painter(c, rng, base, height, color, windows)
    return c.finish()


def _skyline_generic(c, rng, base, height, color, windows):
    _crenellated_wall(c, color, 0, STRIP_WIDTH, base, base - 26, 8)
    for x in range(60, STRIP_WIDTH - 60, 320):
        _tower(c, color, x, base, 40, rng.uniform(90, 140))
        _cypress(c, color, x + 90, base, rng.uniform(70, 100))
        _dome(c, color, x + 180, base - 40, 26)
        c.rect(color, (x + 150, base - 44, 62, 44))
        _palm(c, color, x + 260, base, rng.uniform(80, 110))


def _skyline_cordoba(c, rng, base, height, color, windows):
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        _houses_row(c, color, rng, ox, ox + period, base, 20, 44, windows)
        # The Great Mosque: a long low hall with a row of gabled roofs...
        mx = ox + 200
        c.rect(color, (mx, base - 52, 420, 52))
        for gx in range(int(mx), int(mx + 420), 21):
            c.polygon(color, [(gx, base - 52), (gx + 10.5, base - 62), (gx + 21, base - 52)])
        _crenellated_wall(c, color, mx - 10, mx + 430, base - 30, base - 56, 6)
        # ...and its minaret: a square tower with a small lantern on top.
        tx = mx + 60
        c.rect(color, (tx, base - 170, 34, 170))
        c.rect(color, (tx - 4, base - 176, 42, 8))
        c.rect(color, (tx + 7, base - 204, 20, 30))
        _dome(c, color, tx + 17, base - 204, 9)
        # The Roman bridge over the Guadalquivir with its arches.
        bx = ox + 700
        c.rect(color, (bx, base - 34, 220, 12))
        for ax in range(int(bx), int(bx + 220), 27):
            c.rect(color, (ax, base - 24, 9, 24))
        _tower(c, color, bx + 220, base, 36, 70)
        for x in (ox + 90, ox + 160, ox + 660, ox + 900):
            _palm(c, color, x, base, rng.uniform(70, 110))
        _cypress(c, color, ox + 640, base, 90)


def _skyline_zahra(c, rng, base, height, color, windows):
    # Terraces of the palace-city stepping up the hillside.
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        levels = ((0, 60, 960), (140, 110, 660), (300, 160, 360))
        for dx, h, w in levels:
            c.rect(color, (ox + dx, base - h, w, h))
            for ax in range(int(ox + dx + 20), int(ox + dx + w - 20), 44):
                c.ellipse(shade(color, 0.12), (ax, base - h + 12, 24, 30))
                c.rect(shade(color, 0.12), (ax, base - h + 27, 24, h - 27))
        _palm(c, color, ox + 80, base - 60, 90)
        _palm(c, color, ox + 860, base - 60, 100)
        _cypress(c, color, ox + 520, base - 160, 80)
        _cypress(c, color, ox + 560, base - 160, 60)


def _skyline_toledo(c, rng, base, height, color, windows):
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        # The hill with its houses cascading down.
        c.polygon(color, [(ox, base), (ox + 120, base - 90), (ox + 480, base - 150), (ox + 840, base - 80), (ox + period, base)])
        _houses_row(c, color, rng, ox + 150, ox + 800, base - 110, 16, 40, windows)
        # The alcazar: a square fortress with four corner towers.
        ax = ox + 400
        c.rect(color, (ax, base - 250, 150, 110))
        for tx in (ax - 6, ax + 136):
            c.rect(color, (tx, base - 280, 20, 140))
            c.polygon(color, [(tx - 2, base - 280), (tx + 10, base - 312), (tx + 22, base - 280)])
        # A tall minaret-turned-tower.
        c.rect(color, (ox + 250, base - 250, 22, 120))
        c.polygon(color, [(ox + 248, base - 250), (ox + 261, base - 290), (ox + 274, base - 250)])


def _skyline_seville(c, rng, base, height, color, windows):
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        _houses_row(c, color, rng, ox, ox + period, base, 22, 56, windows)
        # The great Almohad minaret, crowned by the yamur: golden spheres.
        gx = ox + 330
        c.rect(color, (gx, base - 230, 44, 230))
        c.rect(color, (gx + 8, base - 262, 28, 34))
        c.rect(color, (gx - 3, base - 234, 50, 6))
        c.line(color, (gx + 22, base - 262), (gx + 22, base - 300), 2)
        for k2, r in enumerate((6, 5, 4.5, 3.5)):
            c.circle((242, 194, 80), (gx + 22, base - 268 - k2 * 9), r)
        # The twelve-sided Torre del Oro on the riverbank.
        tx = ox + 760
        c.rect(color, (tx, base - 80, 50, 80))
        c.rect(color, (tx + 10, base - 110, 30, 32))
        c.rect(color, (tx + 17, base - 128, 16, 20))
        _dome(c, color, tx + 25, base - 128, 8)
        for x in (ox + 120, ox + 540, ox + 600, ox + 900):
            _palm(c, color, x, base, rng.uniform(80, 120))


def _skyline_granada(c, rng, base, height, color, windows):
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        # Sabika hill.
        c.polygon(color, [(ox, base), (ox + 90, base - 70), (ox + 700, base - 90), (ox + 900, base - 40), (ox + period, base)])
        # The Alhambra's long walls and towers along the ridge.
        _crenellated_wall(c, color, ox + 110, ox + 760, base - 70, base - 110, 8)
        for tx, tw, th in ((ox + 120, 50, 90), (ox + 330, 70, 120), (ox + 470, 40, 70), (ox + 690, 56, 84)):
            _tower(c, color, tx, base - 90, tw, th)
        _cypress(c, color, ox + 800, base - 40, 90)
        _cypress(c, color, ox + 825, base - 40, 70)
        if windows is not None:
            for tx in (ox + 150, ox + 360, ox + 380, ox + 710):
                c.rect(windows, (tx, base - 150, 4, 7))
        _houses_row(c, color, rng, ox + 900, ox + period, base, 12, 30, windows)


def _skyline_alhambra_close(c, rng, base, height, color, windows):
    # Palace roofs seen from within: tiled roofs, the Comares tower, cypresses.
    period = STRIP_WIDTH / 2
    for k in range(2):
        ox = k * period
        c.rect(color, (ox, base - 60, period, 60))
        for rx in range(int(ox), int(ox + period), 160):
            c.polygon(color, [(rx, base - 60), (rx + 80, base - 96), (rx + 160, base - 60)])
        _tower(c, color, ox + 400, base, 110, 200, 8)
        for x in (ox + 120, ox + 150, ox + 700, ox + 730, ox + 760):
            _cypress(c, color, x, base - 50, rng.uniform(90, 130))


_SKYLINES = {
    "cordoba": _skyline_cordoba,
    "zahra": _skyline_zahra,
    "toledo": _skyline_toledo,
    "seville": _skyline_seville,
    "granada": _skyline_granada,
    "alhambra": _skyline_alhambra_close,
    "generic": _skyline_generic,
}


# --- Tree lines ---------------------------------------------------------------------------
def tree_line(style: str, height: int, color: Color, seed: int, snow: Color | None = None) -> pygame.Surface:
    c = _canvas(STRIP_WIDTH, height, color)
    rng = random.Random(seed)
    base = float(height)
    x = 30.0
    while x < STRIP_WIDTH - 60:
        size = rng.uniform(0.6, 1.0) * height
        kind = style if style != "mixed" else rng.choice(("cypress", "orange", "palm"))
        if kind == "cypress":
            _cypress(c, color, x, base, size)
            if rng.random() < 0.5:
                _cypress(c, color, x + size * 0.14, base, size * 0.8)
        elif kind == "palm":
            _palm(c, color, x, base, size)
        elif kind == "pine":
            _pine(c, color, x, base, size, snow)
        else:
            _orange_tree(c, color, x, base, size * 0.8)
        x += rng.uniform(70, 220)
    c.rect(color, (0, base - 6, STRIP_WIDTH, 6))
    return c.finish()


# --- Sky objects ------------------------------------------------------------------------------
def cloud(width: int, height: int, color: Color, shade_color: Color, seed: int) -> pygame.Surface:
    c = _canvas(width, height, color)
    rng = random.Random(seed)
    puffs = []
    for _ in range(max(4, width // 26)):
        r = rng.uniform(height * 0.22, height * 0.42)
        x = rng.uniform(r, width - r)
        y = height - r - rng.uniform(0, height * 0.35)
        puffs.append((x, y, r))
    for x, y, r in puffs:
        c.circle(shade_color, (x, y + r * 0.18), r)
    for x, y, r in puffs:
        c.circle(color, (x, y), r * 0.92)
    return c.finish()


def moon(radius: int, color: Color) -> pygame.Surface:
    size = radius * 2 + 2
    c = _canvas(size, size, color)
    center = (size / 2, size / 2)
    c.circle(color, center, radius)
    rng = random.Random(3)
    for _ in range(6):
        a, d = rng.uniform(0, math.tau), rng.uniform(0, radius * 0.6)
        c.circle(shade(color, -0.1), (center[0] + math.cos(a) * d, center[1] + math.sin(a) * d), rng.uniform(radius * 0.1, radius * 0.22))
    return c.finish()


def sun(radius: int, color: Color) -> pygame.Surface:
    size = radius * 2 + 2
    c = _canvas(size, size, color)
    center = (size / 2, size / 2)
    c.circle(color, center, radius)
    c.circle(mix(color, (255, 255, 255), 0.5), center, radius * 0.7)
    return c.finish()


def bird_frames(color: Color, size: int = 10) -> list[pygame.Surface]:
    """A tiny flapping bird silhouette (swallow/dove), 4 frames."""
    frames = []
    for k in range(4):
        c = Canvas(size * 2, size, scale=4, fringe=color)
        flap = math.sin(k / 4 * math.tau)
        mid = (size, size * 0.55)
        wing_y = size * 0.55 - flap * size * 0.4
        c.lines(color, [(size * 0.1, wing_y), (size * 0.55, size * 0.45), mid], 1.3)
        c.lines(color, [mid, (size * 1.45, size * 0.45), (size * 1.9, wing_y)], 1.3)
        c.circle(color, mid, 1.2)
        frames.append(c.finish())
    return frames
