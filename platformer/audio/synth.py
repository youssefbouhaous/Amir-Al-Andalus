"""Tiny chiptune-style sound synthesis for placeholder sound effects.

Generates square-wave blips and noise bursts directly into a sample buffer,
so the game has audible feedback without shipping any sound files. Drop a
``.wav``/``.ogg`` with the same name into ``assets/sounds`` to replace one.
"""

import logging
import random
from array import array
from collections.abc import Callable, Sequence

import pygame

from core.settings import SYNTH_AMPLITUDE

logger = logging.getLogger(__name__)

SIGNED_16_BIT = -16
MAX_SAMPLE = 32767
# Fixed seed so noise-based sounds are identical every run.
NOISE_SEED = 1234

Note = tuple[float, float]  # (frequency Hz, duration s); frequency 0 = rest


def _render(
    segments: Sequence[tuple[float, float, float]], noise: bool = False
) -> pygame.mixer.Sound | None:
    """Render (start_freq, end_freq, duration) segments with a decay envelope."""
    init = pygame.mixer.get_init()
    if init is None:
        return None
    rate, sample_format, channels = init
    if sample_format != SIGNED_16_BIT:
        logger.info("Mixer format %s unsupported by synth; sounds disabled", sample_format)
        return None

    rng = random.Random(NOISE_SEED)
    samples = array("h")
    for start_freq, end_freq, duration in segments:
        count = max(1, int(rate * duration))
        phase = 0.0
        for index in range(count):
            progress = index / count
            envelope = (1.0 - progress) ** 1.5
            if noise:
                value = rng.uniform(-1.0, 1.0)
            else:
                frequency = start_freq + (end_freq - start_freq) * progress
                phase = (phase + frequency / rate) % 1.0
                value = 1.0 if phase < 0.5 else -1.0
                if frequency <= 0:
                    value = 0.0
            sample = int(value * envelope * SYNTH_AMPLITUDE * MAX_SAMPLE)
            samples.extend([sample] * channels)
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _sweep(start: float, end: float, duration: float) -> Callable[[], pygame.mixer.Sound | None]:
    return lambda: _render([(start, end, duration)])


def _notes(notes: Sequence[Note]) -> Callable[[], pygame.mixer.Sound | None]:
    return lambda: _render([(freq, freq, duration) for freq, duration in notes])


def _noise(duration: float) -> Callable[[], pygame.mixer.Sound | None]:
    return lambda: _render([(0.0, 0.0, duration)], noise=True)


# Melodic sounds use the Hijaz scale (D Eb F# G A Bb C), the augmented-second
# colour typical of Andalusian and Arabic music.
D5, EB5, FS5, G5, A5, BB5, C6, D6 = 587, 622, 740, 784, 880, 932, 1047, 1175
A4 = 440

SOUND_RECIPES: dict[str, Callable[[], pygame.mixer.Sound | None]] = {
    "jump": _sweep(320, 720, 0.14),
    "coin": _notes([(A5, 0.05), (D6, 0.2)]),
    "stomp": _sweep(420, 140, 0.12),
    "kick": _sweep(700, 200, 0.15),
    "bump": _sweep(160, 90, 0.08),
    "break": _noise(0.18),
    "item_appear": _notes([(D5, 0.06), (EB5, 0.06), (FS5, 0.06), (G5, 0.12)]),
    "powerup": _notes([(D5, 0.06), (EB5, 0.06), (FS5, 0.06), (G5, 0.06), (A5, 0.06), (D6, 0.14)]),
    "extra_life": _notes([(A5, 0.08), (BB5, 0.08), (A5, 0.08), (FS5, 0.08), (G5, 0.08), (D6, 0.2)]),
    "hurt": _sweep(700, 180, 0.3),
    "death": _notes([(A5, 0.13), (G5, 0.13), (FS5, 0.13), (EB5, 0.16), (D5, 0.35)]),
    "checkpoint": _notes([(FS5, 0.08), (A5, 0.08), (D6, 0.2)]),
    "level_complete": _notes([
        (D5, 0.1), (EB5, 0.1), (FS5, 0.1), (G5, 0.1), (A5, 0.14),
        (BB5, 0.1), (A5, 0.1), (G5, 0.1), (FS5, 0.1), (D6, 0.4),
    ]),
    "door": _sweep(520, 110, 0.4),
    "menu_move": _notes([(A5, 0.04)]),
    "menu_select": _notes([(FS5, 0.05), (A5, 0.08)]),
    "pause": _notes([(A5, 0.05), (A4, 0.08)]),
}


def synthesize(name: str) -> pygame.mixer.Sound | None:
    recipe = SOUND_RECIPES.get(name)
    return recipe() if recipe is not None else None
