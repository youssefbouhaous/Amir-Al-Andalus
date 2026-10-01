"""Procedurally composed Andalusian music.

Every track is *composed* from a seed (melody, ornaments, bass line) and then
*synthesised* sample by sample with numpy, so the game ships no audio files.

Instruments
    oud     plucked string: Karplus-Strong (a noise burst in a delay line
            that is repeatedly averaged, so high harmonics die first)
    qanun   the same, brighter and higher, doubling the melody
    ney     breathy reed flute: a few harmonics with vibrato plus
            band-limited breath noise
    drone   soft sustained tonic and fifth
    darbuka "doum" (low pitch-dropping thump) and "tek" (dry slap)
    riq     frame-drum jingles

Scales are real maqamat, including their quarter tones (Bayati's E
half-flat, Rast's third), since frequencies are computed from fractional
MIDI numbers. Rhythms are classic iqa'at: maqsum, baladi, sama'i thaqil,
ayyub, and a 6/8 for the mountains.

A track is rendered slightly longer than its loop and the reverb tail is
folded back onto the start, so it loops without a seam.
"""

import math
import random
from dataclasses import dataclass

import numpy as np

SR = 44100

MAQAMAT: dict[str, tuple[float, ...]] = {
    "hijaz": (0, 1, 4, 5, 7, 8, 10),
    "bayati": (0, 1.5, 3, 5, 7, 8, 10),
    "rast": (0, 2, 3.5, 5, 7, 9, 10.5),
    "nahawand": (0, 2, 3, 5, 7, 8, 11),
    "kurd": (0, 1, 3, 5, 7, 8, 10),
    "saba": (0, 1.5, 3, 4, 7, 8, 10),
    "ajam": (0, 2, 4, 5, 7, 9, 11),
}

# Rhythms on an eighth-note grid: D = doum, T = tek, k = soft ka, . = rest.
IQAAT: dict[str, str] = {
    "maqsum": "DT.TD.T.",
    "baladi": "DD.TD.T.",
    "wahda": "D..kT.k.",
    "samai": "D..T.DDT..",
    "ayyub": "D.kTD.T.",
    "sixeight": "D.TDT.",
    "malfuf": "D..T..T.",
}


@dataclass(frozen=True)
class TrackSpec:
    maqam: str
    tonic: float           # MIDI note of the tonic (lead register)
    bpm: float             # eighth notes per minute / 2 (i.e. quarter = bpm)
    rhythm: str
    bars: int = 16
    lead: str = "oud"      # "oud" | "ney" | "qanun"
    density: float = 0.7   # 0 = sparse long notes, 1 = busy
    drone: bool = True
    drums: float = 1.0     # drum volume
    riq: bool = True
    qanun: bool = True
    reverb: float = 0.25
    bells: bool = False
    seed: int = 1
    volume: float = 0.8


TRACKS: dict[str, TrackSpec] = {
    # Title: slow and wistful, ney over a soft drone.
    "title": TrackSpec("hijaz", 62, 76, "wahda", bars=16, lead="ney", density=0.35, drums=0.55,
                       riq=False, reverb=0.4, seed=11),
    # Story book and world map: gentle oud in Nahawand.
    "map": TrackSpec("nahawand", 60, 84, "samai", bars=12, lead="oud", density=0.5, drums=0.45,
                     riq=False, reverb=0.35, seed=5),
    "story": TrackSpec("bayati", 62, 70, "wahda", bars=12, lead="ney", density=0.3, drums=0.3,
                       riq=False, qanun=False, reverb=0.45, seed=17),
    # The journey, dawn to midnight.
    "level1": TrackSpec("rast", 60, 112, "maqsum", bars=16, lead="oud", density=0.7, seed=21),
    "level2": TrackSpec("ajam", 62, 118, "baladi", bars=16, lead="qanun", density=0.75, seed=22),
    "level3": TrackSpec("bayati", 62, 124, "maqsum", bars=16, lead="oud", density=0.8, seed=23),
    "level4": TrackSpec("hijaz", 62, 104, "samai", bars=12, lead="oud", density=0.6, reverb=0.3, seed=24),
    "level5": TrackSpec("kurd", 64, 96, "sixeight", bars=16, lead="ney", density=0.5, drums=0.7,
                        riq=False, reverb=0.4, bells=True, seed=25),
    "level6": TrackSpec("saba", 62, 100, "baladi", bars=16, lead="oud", density=0.65, reverb=0.35,
                        bells=True, seed=26),
    "boss": TrackSpec("hijaz", 57, 150, "ayyub", bars=16, lead="oud", density=0.9, drums=1.3,
                      reverb=0.2, seed=27),
    "ending": TrackSpec("rast", 60, 80, "samai", bars=12, lead="ney", density=0.45, drums=0.5,
                        reverb=0.45, bells=True, seed=31),
    # The Moon Troupe's show at the orchard fountain: a quick, glittering dance.
    "troupe": TrackSpec("hijaz", 62, 138, "baladi", bars=16, lead="qanun", density=0.85, drums=1.15,
                        reverb=0.3, bells=True, seed=41),
    # The Gilded Thieves' rooftop heist under a stolen sun: a driving, sorrowful saba.
    "gilded": TrackSpec("saba", 62, 126, "maqsum", bars=16, lead="oud", density=0.8, drums=1.2,
                        reverb=0.3, bells=True, seed=52),
    # The Castle of Borrowed Hours: a slow night waltz of bells and qanun in a sleeping library.
    "borrowed": TrackSpec("nahawand", 60, 96, "samai", bars=12, lead="qanun", density=0.6, drums=0.7,
                          reverb=0.5, bells=True, seed=63),
}


def midi_hz(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


# --- Instruments -----------------------------------------------------------------
def _band_noise(n: int, low: float, high: float, rng: np.random.Generator) -> np.ndarray:
    """White noise restricted to [low, high] Hz, built in the frequency domain."""
    size = max(2, n)
    spectrum = rng.normal(size=size // 2 + 1) + 1j * rng.normal(size=size // 2 + 1)
    freqs = np.fft.rfftfreq(size, 1 / SR)
    spectrum[(freqs < low) | (freqs > high)] = 0
    noise = np.fft.irfft(spectrum, size)
    peak = np.max(np.abs(noise)) or 1.0
    return noise[:n] / peak


def pluck(freq: float, duration: float, brightness: float, rng: np.random.Generator, decay: float = 0.996) -> np.ndarray:
    """Karplus-Strong plucked string, processed one period at a time."""
    n = int(duration * SR)
    period = max(2, int(SR / freq))
    excitation = rng.uniform(-1, 1, period)
    # Softer pick = lowpassed excitation (a few passes of a 2-tap average).
    for _ in range(int((1.0 - brightness) * 4)):
        excitation = 0.5 * (excitation + np.roll(excitation, 1))
    out = np.empty(n + period)
    out[:period] = excitation
    position = period
    while position < n + period:
        end = min(position + period, n + period)
        count = end - position
        previous = out[position - period:position - period + count]
        shifted = out[position - period - 1:position - period - 1 + count] if position - period - 1 >= 0 else np.concatenate(([0.0], previous[:-1]))
        out[position:end] = decay * 0.5 * (previous + shifted)
        position = end
    tone = out[period:]
    # Gentle fade to avoid a click where the note is cut.
    fade = min(n, int(0.02 * SR))
    if fade:
        tone[-fade:] *= np.linspace(1, 0, fade)
    return tone


def ney(freq: float, duration: float, rng: np.random.Generator) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n) / SR
    vibrato = 1.0 + 0.004 * np.sin(math.tau * 5.2 * t) * np.clip(t / 0.35, 0, 1)
    phase = np.cumsum(freq * vibrato) / SR * math.tau
    tone = np.sin(phase) + 0.28 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase) + 0.05 * np.sin(4 * phase)
    breath = _band_noise(n, freq * 0.8, freq * 4.0, rng) * 0.22
    attack = np.clip(t / 0.07, 0, 1)
    release = np.clip((duration - t) / 0.12, 0, 1)
    swell = 0.85 + 0.15 * np.sin(math.pi * np.clip(t / max(duration, 0.01), 0, 1))
    return (tone * 0.75 + breath) * attack * release * swell


def drone(freq: float, duration: float) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n) / SR
    tone = np.zeros(n)
    for harmonic, amp in ((1, 1.0), (2, 0.35), (3, 0.2), (4, 0.08)):
        detune = 1.0 + 0.0015 * harmonic
        tone += amp * (np.sin(math.tau * freq * harmonic * t) + np.sin(math.tau * freq * harmonic * detune * t)) * 0.5
    slow = 0.8 + 0.2 * np.sin(math.tau * 0.11 * t)
    return tone * slow


def doum(rng: np.random.Generator, pitch: float = 1.0) -> np.ndarray:
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    freq = (95 + 70 * np.exp(-t * 30)) * pitch
    phase = np.cumsum(freq) / SR * math.tau
    body = np.sin(phase) * np.exp(-t * 9)
    click = _band_noise(n, 200, 1800, rng) * np.exp(-t * 90) * 0.3
    return body + click


def tek(rng: np.random.Generator, soft: bool = False) -> np.ndarray:
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    slap = _band_noise(n, 1800, 7500, rng) * np.exp(-t * (70 if not soft else 90))
    ping = np.sin(math.tau * 880 * t) * np.exp(-t * 60) * 0.35
    return (slap + ping) * (0.45 if soft else 0.8)


def riq(rng: np.random.Generator) -> np.ndarray:
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    shimmer = _band_noise(n, 6000, 14000, rng)
    return shimmer * np.exp(-t * 32) * (0.6 + 0.4 * np.sin(math.tau * 45 * t))


def bell(freq: float, duration: float) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n) / SR
    partials = ((1.0, 1.0, 2.5), (2.76, 0.45, 4.0), (5.4, 0.25, 6.5), (8.9, 0.12, 9.0))
    tone = sum(amp * np.sin(math.tau * freq * ratio * t) * np.exp(-t * rate) for ratio, amp, rate in partials)
    return tone * np.clip(t / 0.004, 0, 1)


# --- Composition ------------------------------------------------------------------
@dataclass
class _Note:
    start: float   # seconds
    duration: float
    pitch: float   # MIDI
    velocity: float
    voice: str


class _Composer:
    def __init__(self, spec: TrackSpec) -> None:
        self.spec = spec
        self.rng = random.Random(spec.seed)
        self.scale = MAQAMAT[spec.maqam]
        self.eighth = 60.0 / spec.bpm / 2
        pattern = IQAAT[spec.rhythm]
        self.bar_eighths = len(pattern)
        self.pattern = pattern
        self.bar = self.bar_eighths * self.eighth

    @property
    def length(self) -> float:
        return self.spec.bars * self.bar

    def degree_pitch(self, degree: int) -> float:
        octave, step = divmod(degree, len(self.scale))
        return self.spec.tonic + 12 * octave + self.scale[step]

    def _rhythm_cell(self) -> list[int]:
        """Durations in eighths filling one beat group (2 eighths)."""
        density = self.spec.density
        options = [([2], 1.0 - density), ([1, 1], 0.6 + density), ([1, 1], 0.3)]
        if density > 0.6:
            options.append(([0.5, 0.5, 1], density * 0.7))  # type: ignore[list-item]
        weights = [w for _, w in options]
        return list(self.rng.choices([cell for cell, _ in options], weights)[0])

    def phrase(self, start_degree: int, eighths: int, register: int, cadence: int) -> list[tuple[float, int]]:
        """A melodic phrase: list of (duration in eighths, degree)."""
        notes: list[tuple[float, int]] = []
        degree = start_degree
        filled = 0.0
        low, high = register - 3, register + 6
        while filled < eighths - 2:
            for duration in self._rhythm_cell():
                if filled >= eighths - 2:
                    break
                roll = self.rng.random()
                if roll < 0.62:
                    degree += self.rng.choice((-1, 1))
                elif roll < 0.8:
                    degree += self.rng.choice((-2, 2))
                elif roll < 0.88:
                    degree += self.rng.choice((-3, 3, 4))
                degree = max(low, min(high, degree))
                notes.append((duration, degree))
                filled += duration
        # Resolve: approach the cadence degree stepwise and hold it.
        notes.append((max(0.5, eighths - 2 - filled), cadence + 1))
        notes.append((2, cadence))
        return notes

    def compose(self) -> list[_Note]:
        spec = self.spec
        notes: list[_Note] = []
        phrase_bars = 2 if self.bar_eighths >= 8 else 4
        eighths = phrase_bars * self.bar_eighths
        phrase_count = max(1, spec.bars // phrase_bars)
        # A A' B A'' form, repeated to fill the track.
        a = self.phrase(0, eighths, 3, 0)
        a2 = a[:-2] + self.phrase(a[-3][1], 4, 3, 4)[-2:]
        b = self.phrase(4, eighths, 6, 4)
        b2 = self.phrase(5, eighths, 6, 0)
        form = [a, a2, b, b2]
        harmony = [0, 0, 3, 4]  # tonic, tonic, fourth, fifth (bass roots)
        time = 0.0
        for index in range(phrase_count):
            phrase = form[index % len(form)]
            voice = spec.lead
            self._emit_phrase(notes, phrase, time, voice)
            if spec.qanun and spec.lead != "qanun" and index % 4 >= 2:
                self._emit_phrase(notes, phrase, time, "qanun", octave=12, velocity=0.4)
            root = harmony[index % len(harmony)]
            for bar in range(phrase_bars):
                bar_start = time + bar * self.bar
                notes.append(_Note(bar_start, self.bar * 0.9, self.degree_pitch(root) - 24, 0.55, "bass"))
                half = self.bar_eighths // 2
                if half:
                    notes.append(_Note(bar_start + half * self.eighth, self.bar * 0.4,
                                       self.degree_pitch(root + 4) - 24, 0.4, "bass"))
            time += phrase_bars * self.bar
        return notes

    def _emit_phrase(self, notes: list[_Note], phrase: list[tuple[float, int]], start: float, voice: str,
                     octave: int = 0, velocity: float = 0.8) -> None:
        time = start
        for duration, degree in phrase:
            seconds = duration * self.eighth
            pitch = self.degree_pitch(degree) + octave
            # Ornament: a quick grace note from above before longer oud notes.
            if voice in ("oud", "qanun") and duration >= 2 and self.rng.random() < 0.35:
                grace = min(0.06, seconds * 0.2)
                notes.append(_Note(time, grace * 2, self.degree_pitch(degree + 1) + octave, velocity * 0.7, voice))
                notes.append(_Note(time + grace, seconds - grace, pitch, velocity, voice))
            else:
                accent = 1.0 if abs((time - start) / self.eighth % 2) < 0.01 else 0.85
                notes.append(_Note(time, seconds, pitch, velocity * accent, voice))
            # Oud tremolo on long notes in busy tracks.
            if voice == "oud" and duration >= 2 and self.spec.density > 0.75 and self.rng.random() < 0.3:
                step = self.eighth / 2
                for k in range(1, int(duration * 2)):
                    notes.append(_Note(time + k * step, step * 1.5, pitch, velocity * 0.55, voice))
            time += seconds


# --- Rendering -----------------------------------------------------------------------
def _pan(mono: np.ndarray, pan: float) -> np.ndarray:
    left = math.cos((pan + 1) * math.pi / 4)
    right = math.sin((pan + 1) * math.pi / 4)
    return np.stack((mono * left, mono * right), axis=1)


def _add(buffer: np.ndarray, sound: np.ndarray, start: float) -> None:
    offset = int(start * SR)
    if offset >= len(buffer):
        return
    end = min(len(buffer), offset + len(sound))
    buffer[offset:end] += sound[: end - offset]


def _reverb(signal: np.ndarray, amount: float, rng: np.random.Generator, seconds: float = 1.8) -> np.ndarray:
    """Convolve with a synthetic hall impulse (decaying, darkening noise)."""
    if amount <= 0:
        return signal
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.empty_like(signal)
    size = 1 << int(math.ceil(math.log2(len(signal) + n)))
    for channel in range(2):
        impulse = rng.normal(size=n) * np.exp(-t * 3.2)
        # Darken the tail: blend toward a smoothed copy over time.
        smooth = np.convolve(impulse, np.ones(12) / 12, mode="same")
        mix = np.clip(t / seconds * 1.5, 0, 1)
        impulse = impulse * (1 - mix) + smooth * mix
        impulse[: int(0.012 * SR)] = 0  # pre-delay
        impulse /= np.sqrt(np.sum(impulse ** 2)) or 1.0
        wet = np.fft.irfft(np.fft.rfft(signal[:, channel], size) * np.fft.rfft(impulse, size), size)
        out[:, channel] = signal[:, channel] + wet[: len(signal)] * amount * 2.2
    return out


def render_track(name: str) -> np.ndarray | None:
    """Stereo int16 samples of a seamless loop, or None if unknown."""
    spec = TRACKS.get(name)
    if spec is None:
        return None
    composer = _Composer(spec)
    rng = np.random.default_rng(spec.seed)
    length = composer.length
    tail = 2.5
    buffer = np.zeros((int((length + tail) * SR), 2))

    pluck_cache: dict[tuple[float, float, str], np.ndarray] = {}
    for note in composer.compose():
        freq = midi_hz(note.pitch)
        if note.voice in ("oud", "qanun", "bass"):
            ring = {"oud": 1.6, "qanun": 1.3, "bass": 1.2}[note.voice]
            brightness = {"oud": 0.55, "qanun": 0.95, "bass": 0.3}[note.voice]
            duration = min(2.5, max(0.25, note.duration * ring))
            key = (round(note.pitch, 2), round(duration, 2), note.voice)
            tone = pluck_cache.get(key)
            if tone is None:
                decay = 0.997 if note.voice != "qanun" else 0.995
                tone = pluck(freq, duration, brightness, rng, decay)
                if note.voice == "oud":
                    # A hint of the wooden body: a soft low octave.
                    t = np.arange(len(tone)) / SR
                    tone = tone + 0.25 * np.sin(math.tau * freq / 2 * t) * np.exp(-t * 6)
                pluck_cache[key] = tone
            pan = {"oud": -0.2, "qanun": 0.35, "bass": 0.0}[note.voice]
            gain = {"oud": 0.55, "qanun": 0.35, "bass": 0.5}[note.voice]
            _add(buffer, _pan(tone * note.velocity * gain, pan), note.start)
        elif note.voice == "ney":
            tone = ney(freq, max(0.12, note.duration * 1.05), rng)
            _add(buffer, _pan(tone * note.velocity * 0.4, 0.1), note.start)

    if spec.drone:
        tonic = midi_hz(spec.tonic - 24)
        fifth = midi_hz(spec.tonic - 17)
        drone_tone = (drone(tonic, length + tail) + 0.6 * drone(fifth, length + tail)) * 0.05
        # Fade in over the first bar and wrap: the loop fold keeps it continuous.
        buffer[:, 0] += drone_tone * 0.9
        buffer[:, 1] += drone_tone

    if spec.drums > 0:
        doums = [doum(rng, p) for p in (1.0, 0.94)]
        teks = [tek(rng) for _ in range(3)]
        kas = [tek(rng, soft=True) for _ in range(3)]
        jingles = [riq(rng) for _ in range(3)]
        eighth = composer.eighth
        bar_count = spec.bars
        for bar in range(bar_count):
            fill = bar % 4 == 3
            for step, hit in enumerate(composer.pattern):
                time = (bar * composer.bar_eighths + step) * eighth
                swing = 0.012 if step % 2 else 0.0
                if hit == "D":
                    _add(buffer, _pan(doums[step % 2] * 0.9 * spec.drums, -0.05), time)
                elif hit == "T":
                    _add(buffer, _pan(teks[(bar + step) % 3] * 0.55 * spec.drums, 0.15), time + swing)
                elif hit == "k":
                    _add(buffer, _pan(kas[step % 3] * 0.5 * spec.drums, 0.2), time + swing)
                elif fill or composer.rng.random() < spec.density * 0.35:
                    # Ghost "ka" strokes fill the gaps.
                    _add(buffer, _pan(kas[step % 3] * 0.28 * spec.drums, 0.25), time + swing)
                if spec.riq and step % 2 == 0:
                    _add(buffer, _pan(jingles[step % 3] * 0.2 * spec.drums, 0.4), time + 0.004)
                if fill and step >= composer.bar_eighths - 2:
                    _add(buffer, _pan(teks[step % 3] * 0.4 * spec.drums, 0.1), time + eighth / 2)

    if spec.bells:
        for bar in range(0, spec.bars, 4):
            pitch = composer.degree_pitch(composer.rng.choice((0, 2, 4))) + 12
            _add(buffer, _pan(bell(midi_hz(pitch), 3.0) * 0.12, composer.rng.uniform(-0.6, 0.6)), bar * composer.bar)

    buffer = _reverb(buffer, spec.reverb, rng)

    # Fold the tail over the start for a seamless loop.
    loop_samples = int(length * SR)
    looped = buffer[:loop_samples].copy()
    tail_part = buffer[loop_samples:]
    looped[: len(tail_part)] += tail_part

    peak = np.max(np.abs(looped)) or 1.0
    looped = np.tanh(looped / peak * 1.1) / math.tanh(1.1) * spec.volume
    return (looped * 32767 * 0.9).astype(np.int16)


def render_jingle(name: str) -> np.ndarray | None:
    """Short one-shot musical stingers (level clear, game over, sword)."""
    rng = np.random.default_rng(7)
    notes: list[tuple[float, float, float, str]]
    if name == "fanfare":
        scale = MAQAMAT["hijaz"]
        base = 62
        seq = [0, 1, 2, 3, 4, 5, 4, 7]
        notes = [(i * 0.11, 0.3, base + 12 * (d // 7) + scale[d % 7], "qanun") for i, d in enumerate(seq)]
        notes += [(0.9, 1.4, base + 12, "qanun"), (0.9, 1.4, base + 7, "oud"), (0.9, 1.6, base - 12, "bass")]
    elif name == "gameover":
        scale = MAQAMAT["kurd"]
        seq = [4, 3, 1, 0]
        notes = [(i * 0.35, 0.6, 57 + scale[d], "oud") for i, d in enumerate(seq)]
        notes += [(1.4, 2.0, 45, "bass")]
    elif name == "sword":
        notes = [(0.0, 3.5, p, "bell") for p in (74, 78, 81, 86)]
        notes += [(i * 0.09, 0.4, 74 + [0, 4, 7, 12, 16, 19, 24][i], "qanun") for i in range(7)]
    else:
        return None
    total = max(start + duration for start, duration, _, _ in notes) + 1.5
    buffer = np.zeros((int(total * SR), 2))
    for start, duration, pitch, voice in notes:
        freq = midi_hz(pitch)
        if voice == "bell":
            tone = bell(freq, duration) * 0.35
        else:
            brightness = {"oud": 0.55, "qanun": 0.95, "bass": 0.3}[voice]
            tone = pluck(freq, duration, brightness, rng) * (0.5 if voice != "bass" else 0.6)
        _add(buffer, _pan(tone, rng.uniform(-0.4, 0.4)), start)
    buffer = _reverb(buffer, 0.3, rng)
    peak = np.max(np.abs(buffer)) or 1.0
    return (buffer / peak * 32767 * 0.8).astype(np.int16)
