"""Procedural sound effects.

Every sound is built from a few numpy primitives (pitch sweeps, plucked
strings, band-limited noise, bells, drum hits) shaped with envelopes, and
tuned to the same Hijaz scale as the music so pickups sound "in key".
Drop a ``.wav``/``.ogg`` with the same name into ``assets/sounds`` to replace
any of them.
"""

import logging
import math
from collections.abc import Callable

import numpy as np
import pygame

from audio import music
from audio.music import SR, bell, doum, midi_hz, pluck, tek

logger = logging.getLogger(__name__)

_rng = np.random.default_rng(1234)

# Hijaz on D (the game's home key).
D5, EB5, FS5, G5, A5, BB5, C6, D6 = 74, 75, 78, 79, 81, 82, 84, 86


def _t(duration: float) -> np.ndarray:
    return np.arange(int(duration * SR)) / SR


def _env(t: np.ndarray, attack: float, decay: float) -> np.ndarray:
    return np.clip(t / max(attack, 1e-4), 0, 1) * np.exp(-t * decay)


def _sweep(f0: float, f1: float, duration: float, shape: str = "sine", curve: float = 1.0) -> np.ndarray:
    t = _t(duration)
    progress = (t / duration) ** curve
    freq = f0 * (f1 / f0) ** progress
    phase = np.cumsum(freq) / SR * math.tau
    if shape == "square":
        return np.tanh(np.sin(phase) * 4) * 0.6
    if shape == "tri":
        return 2 / math.pi * np.arcsin(np.sin(phase))
    return np.sin(phase)


def _noise(duration: float, low: float, high: float) -> np.ndarray:
    return music._band_noise(int(duration * SR), low, high, _rng)


def _mix(*parts: tuple[np.ndarray, float]) -> np.ndarray:
    # Delayed notes still need room for their entire tail.
    length = max(int(offset * SR) + len(part) for part, offset in parts)
    out = np.zeros(length)
    for part, offset in parts:
        start = int(offset * SR)
        end = min(length, start + len(part))
        if start < length:
            out[start:end] += part[: end - start]
    return out


def _seq(notes: list[tuple[float, float]], voice: Callable[[float, float], np.ndarray], gap: float | None = None) -> np.ndarray:
    parts = []
    time = 0.0
    for pitch, duration in notes:
        parts.append((voice(midi_hz(pitch), duration), time))
        time += gap if gap is not None else duration * 0.8
    return _mix(*parts)


def _qanun(freq: float, duration: float) -> np.ndarray:
    return pluck(freq, duration + 0.4, 0.95, _rng, 0.995)


def _oud(freq: float, duration: float) -> np.ndarray:
    return pluck(freq, duration + 0.3, 0.6, _rng)


def _chime(freq: float, duration: float) -> np.ndarray:
    return bell(freq, duration + 1.0) * 0.6


# --- Recipes -----------------------------------------------------------------------
def _jump() -> np.ndarray:
    t = _t(0.16)
    return _sweep(260, 640, 0.16, "tri", 0.6) * _env(t, 0.005, 14) * 0.5 + _noise(0.16, 800, 3000) * _env(t, 0.002, 30) * 0.12


def _wall_jump() -> np.ndarray:
    t = _t(0.18)
    return _sweep(340, 820, 0.18, "tri", 0.5) * _env(t, 0.003, 12) * 0.45 + _noise(0.18, 400, 2000) * _env(t, 0.001, 25) * 0.25


def _land() -> np.ndarray:
    t = _t(0.14)
    return _noise(0.14, 60, 900) * _env(t, 0.001, 28) * 0.5 + _sweep(140, 60, 0.14) * _env(t, 0.001, 22) * 0.4


def _coin() -> np.ndarray:
    return _seq([(A5 + 12, 0.07), (D6 + 12, 0.25)], _qanun, gap=0.06) * 0.6


def _page() -> np.ndarray:
    arpeggio = _seq([(D5, 0.1), (FS5, 0.1), (A5, 0.1), (D6, 0.1), (FS5 + 12, 0.4)], _chime, gap=0.07)
    shimmer = _noise(1.2, 5000, 12000) * _env(_t(1.2), 0.2, 3) * 0.08
    return _mix((arpeggio * 0.7, 0.0), (shimmer, 0.0))


def _stomp(level: int = 1) -> Callable[[], np.ndarray]:
    def make() -> np.ndarray:
        t = _t(0.18)
        pitch = 1.0 + 0.12 * (level - 1)
        thump = _sweep(220 * pitch, 90, 0.18) * _env(t, 0.001, 18) * 0.7
        pop = _sweep(600 * pitch, 1200 * pitch, 0.06, "tri") * _env(_t(0.06), 0.001, 40) * 0.3
        return _mix((thump, 0.0), (pop, 0.0))
    return make


def _kick() -> np.ndarray:
    t = _t(0.3)
    return _sweep(900, 180, 0.3, "tri", 0.7) * _env(t, 0.002, 9) * 0.45 + _noise(0.3, 1000, 5000) * _env(t, 0.001, 40) * 0.2


def _bump() -> np.ndarray:
    t = _t(0.12)
    return _sweep(170, 80, 0.12) * _env(t, 0.001, 25) * 0.7 + _noise(0.12, 100, 1200) * _env(t, 0.001, 40) * 0.3


def _break() -> np.ndarray:
    t = _t(0.45)
    crash = _noise(0.45, 150, 5000) * _env(t, 0.001, 9) * 0.6
    knocks = _mix(*[(tek(_rng) * 0.4, k * 0.05) for k in range(4)])
    return _mix((crash, 0.0), (knocks, 0.02))


def _crumble() -> np.ndarray:
    t = _t(0.5)
    rumble = _noise(0.5, 80, 1500) * _env(t, 0.03, 7) * 0.5
    return _mix((rumble, 0.0), (tek(_rng, True) * 0.3, 0.05), (tek(_rng, True) * 0.25, 0.14))


def _item_appear() -> np.ndarray:
    return _seq([(D5, 0.06), (EB5, 0.06), (FS5, 0.06), (G5, 0.06), (A5, 0.2)], _qanun, gap=0.055) * 0.5


def _powerup() -> np.ndarray:
    notes = [(D5, 0.07), (FS5, 0.07), (A5, 0.07), (D6, 0.07), (FS5 + 12, 0.07), (A5 + 12, 0.3)]
    sparkle = _noise(0.8, 6000, 13000) * _env(_t(0.8), 0.05, 5) * 0.12
    return _mix((_seq(notes, _qanun, gap=0.06) * 0.55, 0.0), (sparkle, 0.1))


def _star_power() -> np.ndarray:
    notes = [(A5, 0.06), (C6, 0.06), (D6, 0.06), (FS5 + 12, 0.06), (A5 + 12, 0.06), (D6 + 12, 0.5)]
    return _mix((_seq(notes, _chime, gap=0.05) * 0.5, 0.0), (_seq(notes, _qanun, gap=0.05) * 0.3, 0.0))


def _extra_life() -> np.ndarray:
    notes = [(A5, 0.08), (BB5, 0.08), (A5, 0.08), (FS5, 0.08), (G5, 0.08), (D6, 0.35)]
    return _seq(notes, _qanun, gap=0.09) * 0.6


def _hurt() -> np.ndarray:
    t = _t(0.4)
    wobble = 1 + 0.08 * np.sin(math.tau * 30 * t)
    phase = np.cumsum(700 * np.exp(-t * 4) * wobble + 150) / SR * math.tau
    return np.tanh(np.sin(phase) * 3) * _env(t, 0.002, 6) * 0.35


def _death() -> np.ndarray:
    notes = [(A5, 0.14), (G5, 0.14), (FS5, 0.14), (EB5, 0.18), (D5, 0.6)]
    return _seq(notes, _oud, gap=0.15) * 0.7


def _checkpoint() -> np.ndarray:
    whoosh = _noise(0.5, 300, 3000) * _env(_t(0.5), 0.15, 8) * 0.15
    return _mix((whoosh, 0.0), (_seq([(FS5, 0.1), (A5, 0.1), (D6, 0.5)], _chime, gap=0.09) * 0.6, 0.08))


def _door() -> np.ndarray:
    t = _t(0.5)
    return _sweep(520, 110, 0.5, "tri", 0.8) * _env(t, 0.01, 4) * 0.35 + _noise(0.5, 200, 1800) * _env(t, 0.05, 6) * 0.15


def _spring() -> np.ndarray:
    t = _t(0.45)
    boing = _sweep(90, 300, 0.45, "sine", 0.4) * (1 + 0.3 * np.sin(math.tau * 18 * t)) * _env(t, 0.002, 6) * 0.5
    return _mix((doum(_rng, 1.1) * 0.8, 0.0), (boing, 0.0))


def _switch() -> np.ndarray:
    return _mix(
        (bell(midi_hz(50), 1.4) * 0.5, 0.0),
        (bell(midi_hz(62), 1.2) * 0.25, 0.0),
        (tek(_rng) * 0.4, 0.0),
    )


def _tick() -> np.ndarray:
    return _mix((tek(_rng, True) * 0.5, 0.0), (bell(midi_hz(93), 0.2) * 0.15, 0.0))


def _splash() -> np.ndarray:
    t = _t(0.6)
    plop = _sweep(500, 180, 0.6) * _env(t, 0.001, 22) * 0.25
    return _noise(0.6, 300, 7000) * _env(t, 0.005, 6) * 0.45 + plop


def _fire() -> np.ndarray:
    t = _t(0.35)
    return _noise(0.35, 100, 2500) * _env(t, 0.02, 7) * 0.4 + _sweep(160, 90, 0.35) * _env(t, 0.01, 8) * 0.2


def _screech() -> np.ndarray:
    t = _t(0.3)
    freq = 2200 + 500 * np.sin(math.tau * 14 * t)
    phase = np.cumsum(freq) / SR * math.tau
    return np.sin(phase) * _env(t, 0.01, 10) * 0.15 + _noise(0.3, 3000, 8000) * _env(t, 0.01, 12) * 0.1


def _flutter() -> np.ndarray:
    t = _t(0.5)
    flaps = (0.5 + 0.5 * np.sign(np.sin(math.tau * 22 * t)))
    return _noise(0.5, 300, 2500) * flaps * _env(t, 0.005, 5) * 0.3


def _wind() -> np.ndarray:
    t = _t(1.2)
    swell = np.sin(np.pi * np.clip(t / 1.2, 0, 1)) ** 2
    return _noise(1.2, 200, 1400) * swell * 0.3


def _carpet() -> np.ndarray:
    notes = [(D5 + 12, 0.1), (A5, 0.1), (FS5, 0.1), (D5, 0.4)]
    return _mix((_seq(notes, _chime, gap=0.07) * 0.4, 0.0), (_noise(0.8, 4000, 10000) * _env(_t(0.8), 0.1, 4) * 0.1, 0.0))


def _throw() -> np.ndarray:
    t = _t(0.2)
    return _noise(0.2, 1500, 7000) * _env(t, 0.01, 18) * 0.25 + _sweep(900, 1800, 0.2, "tri") * _env(t, 0.002, 20) * 0.15


def _clink() -> np.ndarray:
    return bell(midi_hz(96), 0.3) * 0.25


def _roar() -> np.ndarray:
    t = _t(1.3)
    growl = np.tanh(_sweep(90, 55, 1.3, "square") * (1 + 0.5 * np.sin(math.tau * 27 * t)) * 2) * _env(t, 0.08, 2.2) * 0.45
    return growl + _noise(1.3, 80, 1200) * _env(t, 0.05, 2.5) * 0.35


def _boss_hit() -> np.ndarray:
    t = _t(0.5)
    return _mix((doum(_rng, 0.7) * 0.9, 0.0), (bell(midi_hz(64), 0.6) * 0.3, 0.0), (_noise(0.5, 500, 6000) * _env(t, 0.001, 12) * 0.3, 0.0))


def _slam() -> np.ndarray:
    t = _t(0.8)
    return _sweep(80, 35, 0.8) * _env(t, 0.001, 5) * 0.9 + _noise(0.8, 40, 900) * _env(t, 0.001, 6) * 0.5


def _boss_defeated() -> np.ndarray:
    t = _t(2.5)
    rumble = _noise(2.5, 40, 1500) * _env(t, 0.05, 1.6) * 0.5
    return _mix((rumble, 0.0), (_roar() * 0.6, 0.0), (bell(midi_hz(62), 2.0) * 0.4, 0.6))


def _sword() -> np.ndarray:
    chord = _mix(*[(bell(midi_hz(p), 3.0) * 0.25, i * 0.05) for i, p in enumerate((62, 69, 74, 78, 81, 86))])
    return chord


def _menu_move() -> np.ndarray:
    return _qanun(midi_hz(A5), 0.05) * 0.35


def _menu_select() -> np.ndarray:
    return _seq([(FS5, 0.05), (A5, 0.15)], _qanun, gap=0.05) * 0.45


def _menu_back() -> np.ndarray:
    return _seq([(A5, 0.05), (FS5, 0.15)], _qanun, gap=0.05) * 0.4


def _pause() -> np.ndarray:
    return _seq([(A5, 0.05), (A5 - 12, 0.12)], _oud, gap=0.06) * 0.5


def _page_turn() -> np.ndarray:
    t = _t(0.35)
    return _noise(0.35, 1500, 9000) * np.abs(np.sin(math.tau * 5 * t)) * _env(t, 0.02, 7) * 0.25


def _level_complete() -> np.ndarray:
    track = music.render_jingle("fanfare")
    return track[:, 0] / 32767.0 if track is not None else np.zeros(1)


def _dash() -> np.ndarray:
    t = _t(0.28)
    whoosh = _noise(0.28, 900, 9000) * np.sin(np.pi * np.clip(t / 0.28, 0, 1)) ** 0.6 * 0.4
    zing = _sweep(500, 1600, 0.18, "tri", 0.5) * _env(_t(0.18), 0.002, 14) * 0.18
    return _mix((whoosh, 0.0), (zing, 0.0))


def _slide() -> np.ndarray:
    t = _t(0.45)
    return _noise(0.45, 300, 3500) * _env(t, 0.01, 5) * (0.7 + 0.3 * np.sin(math.tau * 30 * t)) * 0.3


def _pound() -> np.ndarray:
    t = _t(0.7)
    boom = _sweep(120, 38, 0.7) * _env(t, 0.001, 5) * 0.9
    crunch = _noise(0.7, 60, 2500) * _env(t, 0.001, 9) * 0.5
    return _mix((boom, 0.0), (crunch, 0.0), (doum(_rng, 0.6) * 0.6, 0.0))


def _pound_start() -> np.ndarray:
    return _sweep(300, 900, 0.14, "tri", 0.7) * _env(_t(0.14), 0.002, 10) * 0.3


def _glide() -> np.ndarray:
    t = _t(0.6)
    flap = _noise(0.6, 250, 2200) * (0.6 + 0.4 * np.abs(np.sin(math.tau * 6 * t))) * _env(t, 0.03, 4) * 0.3
    return flap


def _ring_grab() -> np.ndarray:
    return _mix((bell(midi_hz(A5 + 12), 0.5) * 0.25, 0.0), (tek(_rng, True) * 0.3, 0.0))


def _ring_release() -> np.ndarray:
    t = _t(0.25)
    return _sweep(400, 1000, 0.25, "tri", 0.6) * _env(t, 0.003, 9) * 0.25 + _noise(0.25, 800, 5000) * _env(t, 0.01, 14) * 0.12


def _refill() -> np.ndarray:
    return _seq([(A5, 0.06), (D6, 0.06), (FS5 + 12, 0.25)], _chime, gap=0.045) * 0.45


def _plate() -> np.ndarray:
    t = _t(0.5)
    return _mix((bell(midi_hz(45), 0.6) * 0.5, 0.0), (_noise(0.5, 200, 3000) * _env(t, 0.001, 20) * 0.3, 0.0))


def _gate() -> np.ndarray:
    t = _t(1.1)
    rattle = _noise(1.1, 300, 4000) * (0.5 + 0.5 * np.sign(np.sin(math.tau * 18 * t))) * _env(t, 0.02, 2.5) * 0.25
    return _mix((rattle, 0.0), (bell(midi_hz(40), 1.0) * 0.3, 0.0))


def _flood() -> np.ndarray:
    t = _t(2.0)
    return _noise(2.0, 60, 900) * np.sin(np.pi * np.clip(t / 2.0, 0, 1)) * 0.5



# --- Level 1 finale: the Moon Troupe and the Brass Nightingale ------------------------------------------
def _warble(f0: float, f1: float, duration: float, vibrato: float = 38.0, depth: float = 0.05) -> np.ndarray:
    """A bird's chirp: a quick sweep with a fast trill on top."""
    t = _t(duration)
    progress = t / duration
    freq = (f0 + (f1 - f0) * np.sin(progress * math.pi * 0.5)) * (1 + depth * np.sin(math.tau * vibrato * t))
    phase = np.cumsum(freq) / SR * math.tau
    return np.sin(phase) * np.sin(np.pi * np.clip(progress, 0, 1)) ** 0.6


def _power_nightingale() -> np.ndarray:
    parts = []
    time = 0.0
    for f0, f1, d in ((2300, 3300, 0.07), (3300, 2600, 0.06), (2500, 3800, 0.08), (3000, 3000, 0.16),
                      (3600, 2400, 0.07), (2600, 3500, 0.07), (3200, 4200, 0.2)):
        parts.append((_warble(f0, f1, d) * 0.22, time))
        time += d * 0.9
    arpeggio = _seq([(D5, 0.12), (FS5, 0.12), (A5, 0.12), (D6, 0.5)], _chime, gap=0.08) * 0.35
    shimmer = _noise(1.2, 6000, 12000) * _env(_t(1.2), 0.05, 3.5) * 0.06
    return _mix(*parts, (arpeggio, 0.05), (shimmer, 0.0))


def _wonder_peck() -> np.ndarray:
    return _mix((tek(_rng, True) * 0.5, 0.0), (bell(midi_hz(A5 + 12), 0.25) * 0.15, 0.0), (tek(_rng, True) * 0.35, 0.09))


def _wonder_rustle() -> np.ndarray:
    t = _t(0.7)
    return _noise(0.7, 2000, 9000) * _env(t, 0.03, 4) * (0.6 + 0.4 * np.abs(np.sin(math.tau * 11 * t))) * 0.3


def _wonder_fruit() -> np.ndarray:
    t = _t(0.25)
    plop = _sweep(420, 160, 0.25) * _env(t, 0.002, 18) * 0.35
    return _mix((plop, 0.0), (bell(midi_hz(D6 + 12), 0.4) * 0.12, 0.03))


def _wonder_bubble_hit() -> np.ndarray:
    t = _t(0.3)
    glass = bell(midi_hz(D6 + 12), 0.3) * 0.22 + bell(midi_hz(A5 + 12), 0.3) * 0.12
    blip = _sweep(700, 1100, 0.08) * _env(_t(0.08), 0.002, 30) * 0.2
    return _mix((glass * _env(t, 0.001, 9), 0.0), (blip, 0.0))


def _wonder_bubble_pop() -> np.ndarray:
    t = _t(0.5)
    pop = _sweep(900, 180, 0.09) * _env(_t(0.09), 0.001, 25) * 0.5
    burst = _noise(0.12, 1500, 9000) * _env(_t(0.12), 0.001, 35) * 0.35
    tinkles = []
    for k in range(7):
        note = (D6, FS5 + 12, A5 + 12, D6 + 12, BB5 + 12, G5 + 12, EB5 + 12)[k]
        tinkles.append((bell(midi_hz(note), 0.35) * 0.08, 0.03 + k * 0.035))
    spray = _noise(0.5, 3000, 10000) * _env(t, 0.01, 8) * 0.12
    return _mix((pop, 0.0), (burst, 0.0), (spray, 0.0), *tinkles)


def _wonder_bubble_grow() -> np.ndarray:
    t = _t(0.55)
    rise = _sweep(260, 820, 0.55, "sine", 0.7) * (1 + 0.3 * np.sin(math.tau * 18 * t)) * _env(t, 0.1, 3) * 0.2
    return rise


def _wonder_toss() -> np.ndarray:
    t = _t(0.22)
    return _noise(0.22, 700, 4000) * np.sin(np.pi * t / 0.22) * 0.25


def _wonder_splat() -> np.ndarray:
    t = _t(0.35)
    squelch = _noise(0.35, 150, 1800) * _env(t, 0.002, 14) * 0.5
    drop = _sweep(300, 90, 0.2) * _env(_t(0.2), 0.001, 16) * 0.35
    return _mix((squelch, 0.0), (drop, 0.0))


def _wonder_parry() -> np.ndarray:
    ring = bell(midi_hz(D6 + 12), 0.5) * 0.3 + bell(midi_hz(A5 + 12), 0.5) * 0.2
    whoosh = _noise(0.25, 1000, 6000) * np.sin(np.pi * _t(0.25) / 0.25) * 0.2
    return _mix((ring, 0.0), (whoosh, 0.02))


def _wonder_petal_whoosh() -> np.ndarray:
    t = _t(0.6)
    air = _noise(0.6, 2500, 11000) * np.sin(np.pi * t / 0.6) ** 1.5 * 0.28
    return _mix((air, 0.0), (bell(midi_hz(FS5 + 12), 0.5) * 0.08, 0.15))


def _wonder_spin_kick() -> np.ndarray:
    t = _t(0.3)
    swish = _noise(0.3, 800, 7000) * np.sin(np.pi * t / 0.3) * 0.35
    return _mix((swish, 0.0), (doum(_rng, 1.4) * 0.3, 0.12))


def _wonder_whip_charge() -> np.ndarray:
    t = _t(0.5)
    gurgle = _sweep(180, 620, 0.5, "sine", 0.8) * (0.6 + 0.4 * np.sin(math.tau * 26 * t)) * _env(t, 0.2, 1.5) * 0.25
    return gurgle + _noise(0.5, 300, 2000) * _env(t, 0.3, 2) * 0.12


def _wonder_whip() -> np.ndarray:
    t = _t(0.45)
    crack = _noise(0.05, 1500, 9000) * _env(_t(0.05), 0.0005, 60) * 0.7
    lash = _noise(0.45, 300, 5000) * _env(t, 0.005, 9) * 0.35
    return _mix((lash, 0.0), (crack, 0.12))


def _wonder_tide_swell() -> np.ndarray:
    t = _t(1.1)
    rise = (t / 1.1) ** 1.5
    hum = (_sweep(62, 124, 1.1) * 0.5 + _sweep(124, 248, 1.1) * 0.25 + _sweep(186, 372, 1.1) * 0.12) * rise * 0.45
    shimmer = _noise(1.1, 4000, 10000) * rise * 0.07
    return hum + shimmer


def _wonder_geyser() -> np.ndarray:
    t = _t(0.9)
    rush = _noise(0.9, 200, 5000) * _env(t, 0.03, 3.5) * 0.5
    thump = _sweep(120, 50, 0.3) * _env(_t(0.3), 0.002, 10) * 0.5
    return _mix((rush, 0.0), (thump, 0.0))


def _wonder_tether_snap() -> np.ndarray:
    twang = pluck(midi_hz(D6), 0.6, 0.95, _rng, 0.994) * 0.4
    t = _t(0.6)
    bend = twang[: len(t)] * (1 + 0 * t)
    return _mix((bend, 0.0), (bell(midi_hz(A5 + 12), 0.4) * 0.12, 0.0), (_noise(0.2, 3000, 9000) * _env(_t(0.2), 0.001, 25) * 0.2, 0.0))


def _wonder_tide_cancel() -> np.ndarray:
    fall = _seq([(D6 + 12, 0.1), (A5 + 12, 0.1), (FS5 + 12, 0.1), (D6, 0.3)], _chime, gap=0.06) * 0.3
    rain = _noise(1.0, 3000, 9000) * _env(_t(1.0), 0.05, 3) * (0.5 + 0.5 * np.sign(np.sin(math.tau * 23 * _t(1.0)))) * 0.1
    return _mix((fall, 0.0), (rain, 0.05))


def _wonder_pour() -> np.ndarray:
    t = _t(0.7)
    gloop = _sweep(950, 280, 0.7, "sine", 0.6) * (1 + 0.25 * np.sin(math.tau * 14 * t)) * _env(t, 0.02, 2.5) * 0.25
    return gloop


def _wonder_land() -> np.ndarray:
    return _mix((_splash() * 0.9, 0.0), (bell(midi_hz(D6), 0.8) * 0.18, 0.02))


def _wonder_bow() -> np.ndarray:
    return _seq([(A5, 0.08), (C6, 0.08), (D6, 0.3)], _qanun, gap=0.07) * 0.35


def _wonder_moon_wake() -> np.ndarray:
    chord = _mix(*[(bell(midi_hz(note), 2.0) * 0.16, k * 0.14) for k, note in enumerate((D5 - 12, A5 - 12, D5, FS5, A5, D6))])
    t = _t(2.0)
    swell = (_sweep(55, 110, 2.0) * 0.4 + _noise(2.0, 3000, 9000) * 0.05) * np.sin(np.pi * t / 2.0)
    return _mix((chord, 0.0), (swell * 0.5, 0.0))


def _wonder_moon_crack() -> np.ndarray:
    parts = []
    for k in range(9):
        click = _noise(0.03, 3000, 12000) * _env(_t(0.03), 0.0005, 80) * 0.4
        parts.append((click, k * 0.1 + (k % 3) * 0.02))
    t = _t(1.0)
    tension = _sweep(300, 900, 1.0, "tri", 1.4) * _env(t, 0.6, 0.5) * 0.12
    return _mix((tension, 0.0), *parts)


def _wonder_moon_fall() -> np.ndarray:
    t = _t(0.7)
    return _sweep(1400, 180, 0.7, "sine", 0.6) * _env(t, 0.05, 1.5) * 0.25 + _noise(0.7, 400, 4000) * (t / 0.7) * 0.25


def _wonder_resolved() -> np.ndarray:
    t = _t(1.4)
    splash = _noise(1.4, 150, 8000) * _env(t, 0.004, 3.2) * 0.55
    boom = _sweep(110, 40, 0.8) * _env(_t(0.8), 0.002, 5) * 0.6
    fanfare = _seq([(D5, 0.12), (FS5, 0.12), (A5, 0.12), (D6, 0.14), (FS5 + 12, 0.7)], _qanun, gap=0.11) * 0.45
    bells = _seq([(D6, 0.2), (A5 + 12, 0.2), (D6 + 12, 0.8)], _chime, gap=0.18) * 0.25
    return _mix((splash, 0.0), (boom, 0.0), (fanfare, 0.35), (bells, 0.5))


def _wonder_shove() -> np.ndarray:
    t = _t(0.4)
    return _noise(0.4, 300, 6000) * np.sin(np.pi * t / 0.4) * 0.3


SOUND_RECIPES: dict[str, Callable[[], np.ndarray]] = {
    "jump": _jump,
    "wall_jump": _wall_jump,
    "land": _land,
    "coin": _coin,
    "page": _page,
    "stomp": _stomp(1),
    **{f"stomp{n}": _stomp(n) for n in range(1, 9)},
    "kick": _kick,
    "bump": _bump,
    "break": _break,
    "crumble": _crumble,
    "item_appear": _item_appear,
    "powerup": _powerup,
    "star_power": _star_power,
    "extra_life": _extra_life,
    "hurt": _hurt,
    "death": _death,
    "checkpoint": _checkpoint,
    "level_complete": _level_complete,
    "door": _door,
    "spring": _spring,
    "switch": _switch,
    "tick": _tick,
    "splash": _splash,
    "fire": _fire,
    "screech": _screech,
    "flutter": _flutter,
    "wind": _wind,
    "carpet": _carpet,
    "throw": _throw,
    "clink": _clink,
    "roar": _roar,
    "boss_hit": _boss_hit,
    "slam": _slam,
    "boss_defeated": _boss_defeated,
    "sword": _sword,
    "menu_move": _menu_move,
    "menu_select": _menu_select,
    "menu_back": _menu_back,
    "pause": _pause,
    "page_turn": _page_turn,
    "dash": _dash,
    "slide": _slide,
    "pound": _pound,
    "pound_start": _pound_start,
    "glide": _glide,
    "ring_grab": _ring_grab,
    "ring_release": _ring_release,
    "refill": _refill,
    "plate": _plate,
    "gate": _gate,
    "flood": _flood,
    "power_nightingale": _power_nightingale,
    "wonder_peck": _wonder_peck,
    "wonder_rustle": _wonder_rustle,
    "wonder_fruit": _wonder_fruit,
    "wonder_bubble_hit": _wonder_bubble_hit,
    "wonder_bubble_pop": _wonder_bubble_pop,
    "wonder_bubble_grow": _wonder_bubble_grow,
    "wonder_toss": _wonder_toss,
    "wonder_splat": _wonder_splat,
    "wonder_parry": _wonder_parry,
    "wonder_petal_whoosh": _wonder_petal_whoosh,
    "wonder_spin_kick": _wonder_spin_kick,
    "wonder_whip_charge": _wonder_whip_charge,
    "wonder_whip": _wonder_whip,
    "wonder_tide_swell": _wonder_tide_swell,
    "wonder_geyser": _wonder_geyser,
    "wonder_tether_snap": _wonder_tether_snap,
    "wonder_tide_cancel": _wonder_tide_cancel,
    "wonder_pour": _wonder_pour,
    "wonder_land": _wonder_land,
    "wonder_bow": _wonder_bow,
    "wonder_moon_wake": _wonder_moon_wake,
    "wonder_moon_crack": _wonder_moon_crack,
    "wonder_moon_fall": _wonder_moon_fall,
    "wonder_resolved": _wonder_resolved,
    "wonder_shove": _wonder_shove,
}


def to_sound(samples: np.ndarray) -> pygame.mixer.Sound | None:
    """Mono or stereo float/int16 samples -> a Sound matching the mixer format."""
    init = pygame.mixer.get_init()
    if init is None:
        return None
    _rate, sample_format, channels = init
    if sample_format != -16:
        logger.info("Mixer format %s unsupported by synth; sound disabled", sample_format)
        return None
    if samples.dtype != np.int16:
        samples = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    if samples.ndim == 1:
        samples = np.repeat(samples[:, None], channels, axis=1)
    elif samples.shape[1] != channels:
        samples = samples[:, :1] if channels == 1 else np.repeat(samples[:, :1], channels, axis=1)
    if channels == 1:
        samples = samples[:, 0]
    return pygame.sndarray.make_sound(np.ascontiguousarray(samples))


def synthesize(name: str) -> pygame.mixer.Sound | None:
    recipe = SOUND_RECIPES.get(name)
    if recipe is None:
        return None
    samples = recipe()
    fade = min(len(samples), int(0.01 * SR))
    if fade:
        samples = samples.copy()
        samples[-fade:] *= np.linspace(1, 0, fade)
    return to_sound(samples)
