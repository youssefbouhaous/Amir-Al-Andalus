"""Sounds for level 2's finale: the Elephant Clock, the Gilded Thieves and the Night Qalam.

Built from the same primitives as the rest of the game's sound (``audio.music``),
in the Hijaz on D used everywhere, and merged into ``audio.synth.SOUND_RECIPES``.
"""

import math

import numpy as np

from audio.music import SR, _band_noise, bell, doum, midi_hz, pluck, tek

_rng = np.random.default_rng(2026)
D5, EB5, FS5, G5, A5, BB5, C6, D6 = 74, 75, 78, 79, 81, 82, 84, 86


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


def _chimes(notes: list[int], gap: float, decay: float = 0.6, level: float = 0.2) -> np.ndarray:
    return _mix(*[(bell(midi_hz(note), decay) * level, k * gap) for k, note in enumerate(notes)])


# --- the Night Qalam ---------------------------------------------------------------------------------
def _power_qalam() -> np.ndarray:
    t = _t(0.35)
    brush = _noise(0.35, 1200, 7000) * np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 1.2 * 0.32
    stars = _chimes([A5 + 12, D6 + 12, FS5 + 24, A5 + 24], 0.045, 0.4, 0.09)
    return _mix((brush, 0.0), (stars, 0.08))


def _ink_flick() -> np.ndarray:
    return _power_qalam() * 0.6


def _ink_splat() -> np.ndarray:
    t = _t(0.3)
    wet = _noise(0.3, 200, 2400) * _env(t, 0.002, 16) * 0.45
    plop = _sweep(380, 120, 0.18) * _env(_t(0.18), 0.001, 20) * 0.3
    return _mix((wet, 0.0), (plop, 0.0), (bell(midi_hz(D6 + 12), 0.4) * 0.07, 0.04))


def _ink_dry() -> np.ndarray:
    parts = [(_noise(0.02, 2000, 9000) * _env(_t(0.02), 0.0005, 120) * 0.25, k * 0.06 + (k % 3) * 0.013) for k in range(8)]
    return _mix(*parts, (bell(midi_hz(A5 + 12), 0.9) * 0.05, 0.1))


def _ink_hiss() -> np.ndarray:
    t = _t(0.7)
    return _noise(0.7, 2500, 10000) * _env(t, 0.01, 4.5) * 0.35 + _noise(0.7, 200, 900) * _env(t, 0.005, 9) * 0.15


# --- gold, mirrors and the sun ----------------------------------------------------------------------------
def _clang() -> np.ndarray:
    click = _noise(0.03, 3000, 11000) * _env(_t(0.03), 0.0005, 90) * 0.3
    return _mix((bell(1568, 0.6) * 0.18, 0.0), (bell(2349, 0.5) * 0.12, 0.0), (bell(3136, 0.3) * 0.06, 0.0), (click, 0.0))


def _beam_charge() -> np.ndarray:
    t = _t(0.45)
    rise = _sweep(600, 1800, 0.45, 0.8) * (0.6 + 0.4 * np.sin(math.tau * 22 * t)) * (t / 0.45) * 0.16
    return rise + _noise(0.45, 4000, 10000) * (t / 0.45) ** 2 * 0.08


def _lance() -> np.ndarray:
    t = _t(0.45)
    sear = _noise(0.45, 900, 7000) * _env(t, 0.003, 5) * 0.45
    tone = (_sweep(1300, 280, 0.45, 0.7) + 0.4 * _sweep(2600, 560, 0.45, 0.7)) * _env(t, 0.002, 6) * 0.2
    crackle = (np.abs(_noise(0.45, 3000, 9000)) > 0.25) * _noise(0.45, 3000, 9000) * _env(t, 0.01, 8) * 0.3
    return sear + tone + crackle


def _fizzle() -> np.ndarray:
    t = _t(0.35)
    return _sweep(700, 250, 0.35) * _env(t, 0.005, 9) * 0.18 + _noise(0.35, 400, 3000) * _env(t, 0.01, 12) * 0.15


def _glint() -> np.ndarray:
    t = _t(0.3)
    whoosh = _noise(0.3, 1500, 8000) * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) * 0.25
    return _mix((whoosh, 0.0), (bell(midi_hz(D6 + 24), 0.5) * 0.15, 0.0), (bell(midi_hz(A5 + 24), 0.5) * 0.1, 0.03))


def _sun_release() -> np.ndarray:
    t = _t(2.6)
    swell = (_sweep(73, 147, 2.6) * 0.5 + _sweep(147, 294, 2.6) * 0.25) * np.sin(np.pi * np.clip(t / 2.6, 0, 1)) * 0.35
    chord = _chimes([D5 - 12, A5 - 12, D5, FS5, A5, D6, FS5 + 12, A5 + 12], 0.12, 1.6, 0.13)
    rush = _noise(2.6, 300, 6000) * np.sin(np.pi * np.clip(t / 2.6, 0, 1)) ** 2 * 0.18
    return _mix((swell, 0.0), (chord, 0.1), (rush, 0.0))


def _elephant() -> np.ndarray:
    """A great brass trumpet: a bent horn tone, harmonics and growl."""
    t = _t(1.3)
    progress = t / 1.3
    pitch = 300 + 330 * np.sin(np.pi * np.clip(progress * 1.2, 0, 1)) - 60 * progress
    phase = np.cumsum(pitch) / SR * math.tau
    growl = 1 + 0.35 * np.sin(math.tau * 31 * t)
    tone = sum(np.sin(phase * h) / h ** 1.1 for h in range(1, 9)) * growl
    envelope = np.clip(t / 0.08, 0, 1) * np.clip((1.3 - t) / 0.35, 0, 1)
    breath = _noise(1.3, 300, 3000) * envelope * 0.12
    return np.tanh(tone * 0.9) * envelope * 0.32 + breath


def _phoenix() -> np.ndarray:
    return _mix((bell(midi_hz(D5 - 24), 2.2) * 0.4, 0.0), (bell(midi_hz(A5 - 24), 1.6) * 0.15, 0.0),
                (_chimes([D6, A5, FS5 + 12], 0.12, 0.8, 0.1), 0.05))


def _serpent_fling() -> np.ndarray:
    t = _t(0.4)
    return _noise(0.4, 500, 5000) * np.sin(np.pi * np.clip(t / 0.4, 0, 1)) * 0.3


def _sunball_bounce() -> np.ndarray:
    t = _t(0.35)
    thump = _sweep(160, 70, 0.2) * _env(_t(0.2), 0.001, 18) * 0.4
    sizzle = _noise(0.35, 3000, 9000) * _env(t, 0.005, 9) * 0.15
    return _mix((thump, 0.0), (sizzle, 0.0))


# --- the thieves' tricks ---------------------------------------------------------------------------------
def _inhale() -> np.ndarray:
    t = _t(0.55)
    breath = _noise(0.55, 300, 3000) * (t / 0.55) ** 1.5 * 0.3
    crackle = _noise(0.55, 3000, 8000) * (np.abs(np.sin(math.tau * 17 * t)) > 0.9) * 0.2
    return breath + crackle


def _fire_breath() -> np.ndarray:
    t = _t(0.85)
    roar = _noise(0.85, 70, 1500) * (0.75 + 0.25 * np.sin(math.tau * 9 * t)) * _env(t, 0.03, 1.8) * 0.6
    hiss = _noise(0.85, 2000, 7000) * _env(t, 0.02, 3) * 0.15
    return roar + hiss


def _poi() -> np.ndarray:
    t = _t(1.2)
    return _noise(1.2, 500, 4000) * (0.4 + 0.6 * np.abs(np.sin(math.tau * 4 * t))) * np.sin(np.pi * np.clip(t / 1.2, 0, 1)) * 0.3


def _embers() -> np.ndarray:
    return _mix(*[(_noise(0.03, 1500, 7000) * _env(_t(0.03), 0.0005, 100) * 0.3, k * 0.07) for k in range(5)])


def _cobra_hiss() -> np.ndarray:
    t = _t(0.55)
    hiss = _noise(0.55, 3000, 11000) * _env(t, 0.03, 3.5) * 0.3
    rattle = _noise(0.55, 2000, 5000) * (np.sin(math.tau * 26 * t) > 0.6) * _env(t, 0.02, 4) * 0.15
    return hiss + rattle


def _cobra_strike() -> np.ndarray:
    return _mix((_noise(0.08, 1500, 8000) * _env(_t(0.08), 0.001, 40) * 0.4, 0.0), (tek(_rng) * 0.4, 0.02),
                (bell(1200, 0.3) * 0.08, 0.02))


def _basket() -> np.ndarray:
    return _mix(*[(_noise(0.025, 1200, 4500) * _env(_t(0.025), 0.0005, 90) * 0.3, k * 0.045) for k in range(9)])


def _basket_pop() -> np.ndarray:
    pop = _sweep(300, 900, 0.08) * _env(_t(0.08), 0.001, 30) * 0.35
    flourish = _mix(*[(pluck(midi_hz(n), 0.4, 0.9, _rng) * 0.25, k * 0.06) for k, n in enumerate((D5, FS5, A5, D6))])
    return _mix((pop, 0.0), (flourish, 0.05))


def _summon() -> np.ndarray:
    t = _t(1.0)
    drone = (_sweep(147, 147, 1.0) * 0.5 + _sweep(220, 220, 1.0) * 0.3) * np.sin(np.pi * np.clip(t / 1.0, 0, 1)) * 0.25
    reed = np.sin(np.cumsum(midi_hz(A5) * (1 + 0.012 * np.sin(math.tau * 6 * t))) / SR * math.tau)
    reed = np.tanh(reed * 3) * _env(t, 0.05, 1.5) * 0.12
    return drone + reed


def _leap() -> np.ndarray:
    t = _t(0.35)
    return _noise(0.35, 800, 6000) * np.sin(np.pi * np.clip(t / 0.35, 0, 1)) * 0.25 + \
        _sweep(300, 700, 0.35) * _env(t, 0.01, 6) * 0.08


def _coins() -> np.ndarray:
    return _mix(*[(pluck(midi_hz(n + 12), 0.25, 0.97, _rng, 0.995) * 0.2, k * 0.05)
                  for k, n in enumerate((A5, D6, FS5, A5, D6))], (doum(_rng, 1.6) * 0.15, 0.0))


RECIPES = {
    "power_qalam": _power_qalam,
    "wonder_ink_flick": _ink_flick,
    "wonder_ink_splat": _ink_splat,
    "wonder_ink_dry": _ink_dry,
    "wonder_ink_hiss": _ink_hiss,
    "wonder_clang": _clang,
    "wonder_beam_charge": _beam_charge,
    "wonder_lance": _lance,
    "wonder_fizzle": _fizzle,
    "wonder_glint": _glint,
    "wonder_sun_release": _sun_release,
    "wonder_elephant": _elephant,
    "wonder_phoenix": _phoenix,
    "wonder_serpent_fling": _serpent_fling,
    "wonder_sunball_bounce": _sunball_bounce,
    "wonder_inhale": _inhale,
    "wonder_fire_breath": _fire_breath,
    "wonder_poi": _poi,
    "wonder_embers": _embers,
    "wonder_cobra_hiss": _cobra_hiss,
    "wonder_cobra_strike": _cobra_strike,
    "wonder_basket": _basket,
    "wonder_basket_pop": _basket_pop,
    "wonder_summon": _summon,
    "wonder_leap": _leap,
    "wonder_coins": _coins,
}
