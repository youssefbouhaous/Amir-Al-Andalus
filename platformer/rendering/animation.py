"""Frame-based animation.

``Animation`` is immutable shared data (the frames), so a hundred enemies
share one set of Surfaces. ``Animator`` is the per-entity playback state
(which animation, how far into it).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

import pygame


@dataclass(frozen=True, eq=False)
class Animation:
    frames: tuple[pygame.Surface, ...]
    frame_duration: float
    loop: bool = True
    # Horizontally mirrored copies, built once instead of flipping per frame.
    flipped_frames: tuple[pygame.Surface, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("An animation needs at least one frame")
        if self.frame_duration <= 0:
            raise ValueError("frame_duration must be positive")
        flipped = tuple(pygame.transform.flip(frame, True, False) for frame in self.frames)
        object.__setattr__(self, "flipped_frames", flipped)

    @property
    def duration(self) -> float:
        return self.frame_duration * len(self.frames)

    def frame_index(self, elapsed: float) -> int:
        index = int(elapsed / self.frame_duration)
        if self.loop:
            return index % len(self.frames)
        return min(index, len(self.frames) - 1)

    def image(self, elapsed: float, flip_x: bool = False) -> pygame.Surface:
        frames = self.flipped_frames if flip_x else self.frames
        return frames[self.frame_index(elapsed)]


class Animator:
    def __init__(self, animations: Mapping[str, Animation], initial: str) -> None:
        self._animations = animations
        self._current = initial
        self._elapsed = 0.0
        self._require(initial)

    @property
    def current(self) -> str:
        return self._current

    @property
    def frame_index(self) -> int:
        return self._animations[self._current].frame_index(self._elapsed)

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def finished(self) -> bool:
        animation = self._animations[self._current]
        return not animation.loop and self._elapsed >= animation.duration

    def set_animations(self, animations: Mapping[str, Animation]) -> None:
        """Swap the frame set (e.g. powered-up palette) keeping playback position."""
        self._animations = animations
        self._require(self._current)

    def play(self, name: str, restart: bool = False) -> None:
        if name != self._current or restart:
            self._require(name)
            self._current = name
            self._elapsed = 0.0

    def has(self, name: str) -> bool:
        return name in self._animations

    def update(self, dt: float, speed: float = 1.0) -> None:
        self._elapsed += dt * speed

    def image(self, flip_x: bool = False) -> pygame.Surface:
        return self._animations[self._current].image(self._elapsed, flip_x)

    def _require(self, name: str) -> None:
        if name not in self._animations:
            available = ", ".join(sorted(self._animations))
            raise KeyError(f"Unknown animation {name!r} (available: {available})")
