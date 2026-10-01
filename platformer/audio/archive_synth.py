"""Dry ivory clicks, ratchets and falling counterweights for level 3 only."""

import numpy as np

from audio.music import SR


def strike(pitch=780, duration=.12, weight=.25):
    t = np.arange(round(SR * duration)) / SR
    envelope = (1 - np.exp(-t * 2200)) * np.exp(-t * 44)
    return (np.sin(t * pitch * np.pi * 2) + .24 * np.sin(t * pitch * 2.71 * np.pi * 2)) * envelope * weight


def ratchet():
    result = np.zeros(round(SR * .62))
    # Accelerating, unequal clicks, followed by a decisive wooden stop.
    for i, when in enumerate((0, .11, .20, .27, .32, .36)):
        sound = strike(910 - i * 75, .14, .17 + i * .014)
        start = round(when * SR)
        result[start:start + len(sound)] += sound
    sound = strike(125, .2, .4)
    start = round(.41 * SR)
    result[start:start + len(sound)] += sound
    return result


def weight():
    t = np.arange(round(SR * .55)) / SR
    thud = np.sin(2 * np.pi * (96 * t - 44 * t * t)) * np.exp(-t * 11) * .36
    thud += strike(390, .55, .25)
    return thud


RECIPES = {
    "power_fulcrum": ratchet,
    "wonder_archive_tick": lambda: strike(1400, .07, .09),
    "wonder_archive_brace": lambda: strike(180, .22, .4),
    "wonder_archive_open": lambda: strike(420, .14, .23),
    "wonder_archive_closed": lambda: strike(120, .10, .16),
    "wonder_archive_tooth": lambda: strike(660, .18, .32),
    "wonder_archive_weight": weight,
}
