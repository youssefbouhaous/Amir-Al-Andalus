"""Sprite sheets -> Animations, with placeholder fallback.

A ``SheetSpec`` describes a sheet's layout: frame size and which row holds
which animation. If ``assets/images/<image_path>`` exists it is sliced using
that layout; otherwise a placeholder sheet with the *same* layout is painted
procedurally. So to use real art, draw a PNG following the spec and drop it
in; no code changes needed.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pygame

from core.assets import AssetManager
from rendering.animation import Animation

# Paints one frame: (target surface, animation name, frame index).
Painter = Callable[[pygame.Surface, str, int], None]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnimationSpec:
    row: int
    frame_count: int
    frame_duration: float
    loop: bool = True


@dataclass(frozen=True, eq=False)
class SheetSpec:
    image_path: str
    frame_width: int
    frame_height: int
    animations: Mapping[str, AnimationSpec]
    placeholder_painter: Painter

    @property
    def sheet_size(self) -> tuple[int, int]:
        columns = max(spec.frame_count for spec in self.animations.values())
        rows = max(spec.row for spec in self.animations.values()) + 1
        return columns * self.frame_width, rows * self.frame_height


def build_placeholder_sheet(spec: SheetSpec) -> pygame.Surface:
    sheet = pygame.Surface(spec.sheet_size, pygame.SRCALPHA)
    for name, animation in spec.animations.items():
        for index in range(animation.frame_count):
            frame = pygame.Surface((spec.frame_width, spec.frame_height), pygame.SRCALPHA)
            spec.placeholder_painter(frame, name, index)
            sheet.blit(frame, (index * spec.frame_width, animation.row * spec.frame_height))
    return sheet


class SpriteLibrary:
    def __init__(self, assets: AssetManager) -> None:
        self._assets = assets
        self._cache: dict[str, dict[str, Animation]] = {}

    def animations(self, spec: SheetSpec) -> dict[str, Animation]:
        cached = self._cache.get(spec.image_path)
        if cached is None:
            cached = self._slice(spec)
            self._cache[spec.image_path] = cached
        return cached

    def _slice(self, spec: SheetSpec) -> dict[str, Animation]:
        sheet = self._assets.get_image(spec.image_path, lambda: build_placeholder_sheet(spec))
        needed_width, needed_height = spec.sheet_size
        if sheet.get_width() < needed_width or sheet.get_height() < needed_height:
            logger.warning(
                "%s is %dx%d but its layout needs %dx%d; using placeholder",
                spec.image_path, sheet.get_width(), sheet.get_height(),
                needed_width, needed_height,
            )
            sheet = build_placeholder_sheet(spec).convert_alpha()

        animations: dict[str, Animation] = {}
        for name, animation in spec.animations.items():
            frames = tuple(
                sheet.subsurface(
                    (
                        index * spec.frame_width,
                        animation.row * spec.frame_height,
                        spec.frame_width,
                        spec.frame_height,
                    )
                ).copy()
                for index in range(animation.frame_count)
            )
            animations[name] = Animation(frames, animation.frame_duration, animation.loop)
        return animations
