"""Sounds for level 4's finale: the Sky-Noria, the River-Thieves and the Rose Fountain.

Water, wet timber and brass, in the Hijaz on D used everywhere, built from the
same primitives as the rest of the game's sound and merged into
``audio.synth.SOUND_RECIPES`` like the other finales' sounds.
"""

import math

import numpy as np

from audio.music import SR, _band_noise, bell, midi_hz, pluck, tek

_rng = np.random.default_rng(1206 + 4)
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


def _hump(t: np.ndarray, duration: float, power: float = 1.0) -> np.ndarray:
    return np.sin(np.pi * np.clip(t / duration, 0, 1)) ** power


# --- water -----------------------------------------------------------------------------------------
def _bloop(f0: float, f1: float, duration: float, level: float) -> np.ndarray:
    """A bubble or a plop: a quick pitch slide with a soft attack."""
    return _sweep(f0, f1, duration, 0.7) * _env(_t(duration), 0.004, 6 / duration) * level


def _splash(duration: float = 0.5, level: float = 0.45, low: float = 180) -> np.ndarray:
    t = _t(duration)
    body = _noise(duration, low, 6500) * _env(t, 0.003, 9 / duration) * level
    drops = _mix(*[(_bloop(900 + k * 140, 500 + k * 60, 0.05, 0.08), 0.04 + k * 0.05 + (k % 2) * 0.017) for k in range(6)])
    return _mix((body, 0.0), (drops, 0.02))


def _gurgle(duration: float, count: int, low: float, high: float, level: float) -> np.ndarray:
    parts = []
    for k in range(count):
        f = float(_rng.uniform(low, high))
        parts.append((_bloop(f, f * float(_rng.uniform(1.3, 1.8)), 0.06, level), float(_rng.uniform(0, duration - 0.08))))
    return _mix(*parts)


def _water_thud() -> np.ndarray:
    """A blow swallowed by the water: a deep plop and a gout of spray."""
    thump = _sweep(170, 60, 0.25) * _env(_t(0.25), 0.002, 14) * 0.5
    return _mix((thump, 0.0), (_splash(0.35, 0.3, 400), 0.0))


def _rooted() -> np.ndarray:
    """The river climbing a thief again: bubbles rising in a shimmer."""
    return _mix((_gurgle(0.5, 9, 500, 1200, 0.07), 0.0), (_chimes([A5 + 12, D6 + 12], 0.08, 0.5, 0.05), 0.15))


def _uproot() -> np.ndarray:
    """A thief yanked out of the flood: a big wet pop, then the fountain's rush carrying him up."""
    t = _t(0.7)
    pop = _bloop(140, 520, 0.18, 0.5)
    rush = _noise(0.7, 600, 8000) * _hump(t, 0.7, 1.4) * 0.3
    wobble = _sweep(300, 900, 0.5) * (0.5 + 0.5 * np.sin(math.tau * 14 * _t(0.5))) * _env(_t(0.5), 0.02, 4) * 0.12
    return _mix((pop, 0.0), (rush, 0.05), (wobble, 0.08))


def _wave_hit() -> np.ndarray:
    t = _t(0.45)
    slosh = _noise(0.45, 150, 3500) * _hump(t, 0.45, 0.7) * 0.4
    return _mix((slosh, 0.0), (_sweep(110, 55, 0.2) * _env(_t(0.2), 0.002, 12) * 0.4, 0.05))


def _flood_surge() -> np.ndarray:
    """The river coming back over the stage as a wave."""
    t = _t(1.3)
    roar = _noise(1.3, 120, 5000) * _hump(t, 1.3, 0.8) * 0.4
    roll = _sweep(60, 90, 1.3) * _hump(t, 1.3) * 0.25
    return _mix((roar, 0.0), (roll, 0.0), (_gurgle(1.2, 12, 300, 900, 0.06), 0.1))


# --- the noria and its ox ------------------------------------------------------------------------------
def _groan(duration: float, pitch: float, level: float) -> np.ndarray:
    """The groan of a great wooden wheel turning on its axle - the song of the Hama norias."""
    t = _t(duration)
    wobble = pitch * (1 + 0.04 * np.sin(math.tau * 0.8 * t) + 0.02 * np.sin(math.tau * 3.1 * t))
    phase = np.cumsum(wobble) / SR * math.tau
    tone = sum(np.sin(phase * h) / h for h in range(1, 7))
    stick = 0.55 + 0.45 * (np.sin(math.tau * 9 * t) > 0.3)          # the axle sticking and slipping
    rasp = _noise(duration, 200, 1600) * 0.3
    return np.tanh((tone + rasp) * 0.8) * stick * _hump(t, duration, 0.5) * level


def _ox_bellow(pitch: float = 1.0, level: float = 0.34) -> np.ndarray:
    """A brass ox's bellow: a low bent horn with a growl in it."""
    t = _t(1.1)
    progress = t / 1.1
    f = (105 + 55 * np.sin(np.pi * np.clip(progress * 1.3, 0, 1)) - 20 * progress) * pitch
    phase = np.cumsum(f) / SR * math.tau
    growl = 1 + 0.4 * np.sin(math.tau * 27 * t)
    tone = sum(np.sin(phase * h) / h ** 0.9 for h in range(1, 10)) * growl
    envelope = np.clip(t / 0.1, 0, 1) * np.clip((1.1 - t) / 0.3, 0, 1)
    breath = _noise(1.1, 200, 2500) * envelope * 0.1
    return np.tanh(tone * 0.8) * envelope * level + breath


def _ox_bell() -> np.ndarray:
    """The bell under the ox's throat, once each time round: a dull brass clank."""
    t = _t(0.9)
    clank = (np.sin(math.tau * 612 * t) * 0.6 + np.sin(math.tau * 931 * t) * 0.35 + np.sin(math.tau * 1427 * t) * 0.2)
    return clank * _env(t, 0.002, 5) * 0.16 + _noise(0.9, 2000, 6000) * _env(t, 0.001, 60) * 0.1


def _ox_drink() -> np.ndarray:
    """The wheel creaks to a stop; the ox slurps from its trough."""
    creak = _groan(0.6, 64, 0.2) * np.linspace(1, 0.2, int(0.6 * SR))
    gulps = _mix(*[(_bloop(220, 140, 0.16, 0.25), 0.55 + k * 0.32) for k in range(4)])
    return _mix((creak, 0.0), (gulps, 0.0), (_gurgle(1.6, 8, 200, 500, 0.05), 0.5))


def _noria_wake() -> np.ndarray:
    """The machine wakes: the wheel groans up to speed, the ox bellows, the river rushes into the sky."""
    t = _t(2.4)
    groan = _groan(2.4, 70, 0.3)
    rush = _noise(2.4, 400, 7000) * (t / 2.4) ** 1.5 * _hump(t, 2.4, 0.3) * 0.25
    return _mix((groan, 0.0), (rush, 0.0), (_ox_bellow(), 0.6), (_chimes([D5 - 12, A5 - 12, EB5], 0.18, 1.6, 0.12), 1.2))


def _rim_run() -> np.ndarray:
    steps = [(tek(_rng, soft=True) * 0.25, k * 0.11) for k in range(7)]
    return _mix(*steps, (_groan(0.8, 82, 0.1), 0.0))


def _ox_freed() -> np.ndarray:
    """The harness breaks: links of chain ring out, and the ox's bellow lifts, glad."""
    links = _mix(*[(bell(float(_rng.uniform(1800, 3200)), 0.25) * 0.12, k * 0.05) for k in range(6)])
    return _mix((links, 0.0), (_ox_bellow(1.35, 0.3), 0.25), (_chimes([D5, FS5, A5, D6], 0.1, 1.0, 0.12), 0.4))


def _river_home() -> np.ndarray:
    """The river falls back out of the sky: a long glittering rush and a rising arpeggio in Hijaz."""
    t = _t(3.0)
    rush = _noise(3.0, 300, 9000) * _hump(t, 3.0, 0.8) * 0.3
    arpeggio = _chimes([D5 - 12, FS5 - 12, A5 - 12, D5, EB5, FS5, G5, A5, BB5, C6, D6, FS5 + 12, A5 + 12, D6 + 12], 0.09, 1.4, 0.12)
    swell = (_sweep(73, 147, 3.0) * 0.5 + _sweep(147, 294, 3.0) * 0.25) * _hump(t, 3.0) * 0.25
    return _mix((rush, 0.0), (arpeggio, 0.2), (swell, 0.0))


def _aqueduct_song() -> np.ndarray:
    """The aqueduct's fountains spring up and sing: soft breathy tones over bubbling water."""
    t = _t(2.6)
    voices = np.zeros_like(t)
    for note, delay in ((D5 - 12, 0.0), (A5 - 12, 0.3), (D5, 0.6), (FS5, 0.9)):
        f = midi_hz(note)
        start = np.clip((t - delay) / 0.5, 0, 1)
        voices += np.sin(math.tau * f * t + 0.3 * np.sin(math.tau * 5 * t)) * start * 0.08
    breath = _noise(2.6, 1500, 6000) * 0.03
    return _mix(((voices + breath) * _hump(t, 2.6, 0.5), 0.0), (_gurgle(2.4, 18, 400, 1100, 0.05), 0.1))


# --- the thieves ---------------------------------------------------------------------------------------
def _qirba_squeeze() -> np.ndarray:
    """Leather stretching and a deep glug as the goatskin swells."""
    t = _t(0.55)
    leather = _noise(0.55, 300, 1400) * (0.5 + 0.5 * np.sin(math.tau * 38 * t)) * _hump(t, 0.55) * 0.25
    return _mix((leather, 0.0), (_bloop(120, 260, 0.3, 0.3), 0.15))


def _qirba_jet() -> np.ndarray:
    t = _t(0.65)
    gush = _noise(0.65, 500, 7000) * (0.8 + 0.2 * np.sin(math.tau * 31 * t)) * _env(t, 0.01, 2.2) * 0.4
    return _mix((gush, 0.0), (_bloop(300, 160, 0.12, 0.3), 0.0))


def _cup_ting() -> np.ndarray:
    return _mix((bell(2093, 0.5) * 0.16, 0.0), (bell(3136, 0.35) * 0.08, 0.0),
                (_noise(0.02, 4000, 11000) * _env(_t(0.02), 0.0005, 120) * 0.2, 0.0))


def _cup_throw() -> np.ndarray:
    t = _t(0.3)
    whoosh = _noise(0.3, 900, 6000) * _hump(t, 0.3) * 0.22
    return _mix((whoosh, 0.0), (_cup_ting() * 0.6, 0.02))


def _hop() -> np.ndarray:
    return _sweep(180, 420, 0.18) * _env(_t(0.18), 0.003, 12) * 0.25


def _belly_flop() -> np.ndarray:
    slap = _noise(0.06, 800, 6000) * _env(_t(0.06), 0.0005, 60) * 0.5
    return _mix((slap, 0.0), (_splash(0.7, 0.5, 150), 0.0), (_sweep(90, 45, 0.3) * _env(_t(0.3), 0.002, 10) * 0.45, 0.0))


def _refill() -> np.ndarray:
    return _gurgle(1.2, 16, 220, 700, 0.09)


def _net_twirl() -> np.ndarray:
    t = _t(0.5)
    return _noise(0.5, 400, 3000) * (0.5 + 0.5 * np.sin(math.tau * 9 * t)) * _hump(t, 0.5) * 0.25


def _net_cast() -> np.ndarray:
    t = _t(0.4)
    whoosh = _noise(0.4, 600, 5000) * _hump(t, 0.4) * 0.25
    rattle = _mix(*[(tek(_rng, soft=True) * 0.12, 0.05 + k * 0.035) for k in range(5)])
    return _mix((whoosh, 0.0), (rattle, 0.05))


def _net_toss() -> np.ndarray:
    return _mix((_splash(0.4, 0.3, 300), 0.0), (_net_twirl() * 0.5, 0.0))


def _line_cast() -> np.ndarray:
    """The reel paying out line as it flies up to the river."""
    t = _t(0.6)
    zip_ = np.sign(np.sin(np.cumsum(300 + 900 * (t / 0.6)) / SR * math.tau)) * _env(t, 0.005, 4) * 0.07
    return zip_ + _noise(0.6, 1500, 7000) * _hump(t, 0.6) * 0.1


def _line_yank() -> np.ndarray:
    twang = pluck(midi_hz(D5 - 12), 0.5, 0.8, _rng) * 0.3
    return _mix((twang, 0.0), (_bloop(500, 1200, 0.12, 0.15), 0.05))


def _fish_splash() -> np.ndarray:
    slap = _noise(0.05, 600, 5000) * _env(_t(0.05), 0.0005, 70) * 0.45
    return _mix((slap, 0.0), (_splash(0.6, 0.45, 160), 0.0))


def _fish_flop() -> np.ndarray:
    slap = _noise(0.04, 900, 5000) * _env(_t(0.04), 0.0005, 80) * 0.35
    return _mix((slap, 0.0), (_bloop(200, 120, 0.1, 0.2), 0.0))


def _fish_home() -> np.ndarray:
    return _mix((_bloop(300, 1200, 0.25, 0.25), 0.0), (_chimes([FS5 + 12, A5 + 12, D6 + 12], 0.06, 0.4, 0.07), 0.1))


def _spear_plant() -> np.ndarray:
    return _mix((tek(_rng) * 0.4, 0.0), (_splash(0.3, 0.2, 400), 0.0))


def _vault() -> np.ndarray:
    t = _t(0.5)
    creak = _sweep(240, 380, 0.25) * (0.5 + 0.5 * np.sin(math.tau * 40 * _t(0.25))) * _env(_t(0.25), 0.01, 8) * 0.12
    whoosh = _noise(0.5, 700, 6000) * _hump(t, 0.5) * 0.22
    return _mix((creak, 0.0), (whoosh, 0.1))


def _rain_call() -> np.ndarray:
    """Hamida's bells, a far roll of thunder, the first drops."""
    bells = _mix(*[(bell(midi_hz(note), 0.5) * 0.08, k * 0.07) for k, note in enumerate((A5 + 12, D6 + 12, FS5 + 12, A5 + 12, D6 + 12, FS5 + 24))])
    t = _t(1.2)
    thunder = _noise(1.2, 40, 300) * _hump(t, 1.2, 1.5) * 0.3
    drops = _mix(*[(_bloop(float(_rng.uniform(1200, 2400)), 900, 0.03, 0.05), 0.4 + k * 0.06) for k in range(10)])
    return _mix((bells, 0.0), (thunder, 0.1), (drops, 0.0))


def _rain_spear() -> np.ndarray:
    whistle = _sweep(2400, 900, 0.18) * _env(_t(0.18), 0.002, 8) * 0.12
    return _mix((whistle, 0.0), (_splash(0.35, 0.4, 500), 0.16))


def _parasol_open() -> np.ndarray:
    t = _t(0.3)
    fwump = _noise(0.3, 150, 1500) * _env(t, 0.01, 10) * 0.35
    return _mix((fwump, 0.0), (_chimes([D6 + 12, A5 + 12], 0.05, 0.4, 0.06), 0.05))


def _parasol_spin() -> np.ndarray:
    t = _t(0.9)
    whirr = _noise(0.9, 500, 4000) * (0.5 + 0.5 * np.sin(math.tau * 14 * t)) * _hump(t, 0.9, 0.6) * 0.22
    return _mix((whirr, 0.0), (_chimes([A5 + 12, D6 + 12, FS5 + 12], 0.12, 0.4, 0.05), 0.1))


def _parasol_push() -> np.ndarray:
    t = _t(0.3)
    return _noise(0.3, 200, 3000) * _env(t, 0.005, 9) * 0.35


# --- the Rose Fountain ------------------------------------------------------------------------------------
def _rose_throw() -> np.ndarray:
    t = _t(0.25)
    shing = (np.sin(math.tau * 2640 * t) + 0.5 * np.sin(math.tau * 3960 * t)) * (0.5 + 0.5 * np.sin(math.tau * 30 * t))
    return shing * _env(t, 0.003, 10) * 0.08 + _noise(0.25, 1500, 8000) * _hump(t, 0.25) * 0.1


def _fountain_rise() -> np.ndarray:
    """The column shooting up out of the rose, crowned with a chime."""
    t = _t(0.8)
    rush = _noise(0.8, 500, 9000) * np.clip(t / 0.15, 0, 1) * np.exp(-t * 2.5) * 0.4
    rise = _sweep(200, 900, 0.3) * _env(_t(0.3), 0.01, 6) * 0.15
    return _mix((rush, 0.0), (rise, 0.0), (_chimes([D6, FS5 + 12, A5 + 12], 0.07, 0.6, 0.08), 0.2))


def _power_fountain() -> np.ndarray:
    return _mix((_rose_throw(), 0.0), (_chimes([A5 + 12, D6 + 12], 0.06, 0.3, 0.05), 0.05))


RECIPES = {
    "power_fountain": _power_fountain,
    "wonder_rose_throw": _rose_throw,
    "wonder_fountain_rise": _fountain_rise,
    "wonder_water_thud": _water_thud,
    "wonder_rooted": _rooted,
    "wonder_uproot": _uproot,
    "wonder_wave_hit": _wave_hit,
    "wonder_flood_surge": _flood_surge,
    "wonder_ox_bellow": _ox_bellow,
    "wonder_ox_bell": _ox_bell,
    "wonder_ox_drink": _ox_drink,
    "wonder_noria_wake": _noria_wake,
    "wonder_rim_run": _rim_run,
    "wonder_ox_freed": _ox_freed,
    "wonder_river_home": _river_home,
    "wonder_aqueduct_song": _aqueduct_song,
    "wonder_qirba_squeeze": _qirba_squeeze,
    "wonder_qirba_jet": _qirba_jet,
    "wonder_cup_throw": _cup_throw,
    "wonder_cup_ting": _cup_ting,
    "wonder_hop": _hop,
    "wonder_belly_flop": _belly_flop,
    "wonder_refill": _refill,
    "wonder_net_twirl": _net_twirl,
    "wonder_net_cast": _net_cast,
    "wonder_net_toss": _net_toss,
    "wonder_line_cast": _line_cast,
    "wonder_line_yank": _line_yank,
    "wonder_fish_splash": _fish_splash,
    "wonder_fish_flop": _fish_flop,
    "wonder_fish_home": _fish_home,
    "wonder_spear_plant": _spear_plant,
    "wonder_vault": _vault,
    "wonder_rain_call": _rain_call,
    "wonder_rain_spear": _rain_spear,
    "wonder_parasol_open": _parasol_open,
    "wonder_parasol_spin": _parasol_spin,
    "wonder_parasol_push": _parasol_push,
}
