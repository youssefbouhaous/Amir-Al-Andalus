"""Sounds for level 3's Castle of Borrowed Hours: bells, echoes, glass and midnight.

Merged into ``audio.synth.SOUND_RECIPES`` like the other finales' sounds.
"""

import math

import numpy as np

from audio.music import SR, _band_noise, bell, midi_hz

_rng = np.random.default_rng(1206)
D5, FS5, A5, D6 = 74, 78, 81, 86


def _t(duration: float) -> np.ndarray:
    return np.arange(int(duration * SR)) / SR


def _env(t: np.ndarray, attack: float, decay: float) -> np.ndarray:
    return np.clip(t / max(attack, 1e-4), 0, 1) * np.exp(-t * decay)


def _sweep(f0: float, f1: float, duration: float, curve: float = 1.0) -> np.ndarray:
    t = _t(duration)
    freq = f0 * (f1 / f0) ** ((t / duration) ** curve)
    return np.sin(np.cumsum(freq) / SR * math.tau)


def _noise(duration: float, low: float, high: float) -> np.ndarray:
    return _band_noise(int(duration * SR), low, high, _rng)


def _mix(*parts: tuple[np.ndarray, float]) -> np.ndarray:
    length = max(int(offset * SR) + len(part) for part, offset in parts)
    out = np.zeros(length)
    for part, offset in parts:
        start = int(offset * SR)
        out[start:start + len(part)] += part[: max(0, length - start)]
    return out


def _hour_bell() -> np.ndarray:
    return _mix((bell(midi_hz(A5 - 12), 1.6) * 0.22, 0.0), (bell(midi_hz(D6), 1.0) * 0.08, 0.02))


def _echo_appear() -> np.ndarray:
    t = _t(0.9)
    rise = _sweep(300, 1400, 0.9, 0.6) * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) * 0.12
    air = _noise(0.9, 2000, 9000) * (t / 0.9) ** 2 * np.clip((0.9 - t) / 0.1, 0, 1) * 0.12
    return rise + air


def _echo_shatter() -> np.ndarray:
    crack = _noise(0.08, 2000, 12000) * _env(_t(0.08), 0.0005, 50) * 0.45
    tinkles = [(bell(midi_hz(n), 0.4) * 0.07, 0.02 + k * 0.03) for k, n in enumerate((D6 + 12, A5 + 12, FS5 + 24, D6 + 24, A5 + 24, FS5 + 12))]
    return _mix((crack, 0.0), *tinkles)


def _echo_pass() -> np.ndarray:
    t = _t(0.4)
    return _noise(0.4, 400, 3000) * np.sin(np.pi * np.clip(t / 0.4, 0, 1)) * 0.18 + _sweep(500, 260, 0.4) * _env(t, 0.02, 5) * 0.06


def _borrow() -> np.ndarray:
    """An hour slipping away: a tone that bends down, and the lamp's soft chime."""
    t = _t(0.7)
    bend = _sweep(880, 330, 0.7, 0.5) * _env(t, 0.01, 3) * 0.16
    return _mix((bend, 0.0), (bell(midi_hz(FS5 + 12), 0.6) * 0.1, 0.25))


def _midnight() -> np.ndarray:
    tolls = [(bell(midi_hz(D5 - 12 + (k % 2) * 7), 0.9) * 0.2, k * 0.12) for k in range(12)]
    gong = bell(midi_hz(D5 - 24), 3.0) * 0.4
    return _mix(*tolls, (gong, 1.4))


def _chain_break() -> np.ndarray:
    snap = _noise(0.1, 1500, 9000) * _env(_t(0.1), 0.0005, 40) * 0.5
    glyphs = [(bell(midi_hz(n), 0.6) * 0.08, 0.05 + k * 0.05) for k, n in enumerate((D6, FS5 + 12, A5 + 12, D6 + 12, A5 + 12))]
    return _mix((snap, 0.0), *glyphs)


def _cymbal() -> np.ndarray:
    t = _t(1.6)
    return _noise(1.6, 3000, 12000) * _env(t, 0.002, 2.4) * 0.35 + _noise(1.6, 600, 3000) * _env(t, 0.002, 4) * 0.15


def _library_wakes() -> np.ndarray:
    chord = _mix(*[(bell(midi_hz(n), 2.4) * 0.12, k * 0.1) for k, n in enumerate((D5 - 12, A5 - 12, D5, FS5, A5, D6, FS5 + 12))])
    t = _t(2.6)
    pad = (_sweep(147, 147, 2.6) * 0.3 + _sweep(220, 220, 2.6) * 0.2) * np.sin(np.pi * np.clip(t / 2.6, 0, 1)) * 0.2
    return _mix((chord, 0.0), (pad, 0.0))


def _time_stop() -> np.ndarray:
    t = _t(0.9)
    down = _sweep(1200, 140, 0.35, 0.6) * _env(_t(0.35), 0.002, 6) * 0.22
    ring = _sweep(2093, 2093, 0.9) * _env(t, 0.05, 2.5) * 0.06 + _sweep(3136, 3136, 0.9) * _env(t, 0.05, 3) * 0.04
    return _mix((down, 0.0), (ring, 0.15))


RECIPES = {
    "wonder_hour_bell": _hour_bell,
    "wonder_echo_appear": _echo_appear,
    "wonder_echo_shatter": _echo_shatter,
    "wonder_echo_pass": _echo_pass,
    "wonder_borrow": _borrow,
    "wonder_midnight": _midnight,
    "wonder_chain_break": _chain_break,
    "wonder_cymbal": _cymbal,
    "wonder_library_wakes": _library_wakes,
    "wonder_time_stop": _time_stop,
}
