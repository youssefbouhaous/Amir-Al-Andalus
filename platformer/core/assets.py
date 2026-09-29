"""Central, cached asset loading.

Every image/sound is loaded at most once. When a file is missing, a fallback
factory (usually procedurally generated placeholder art) is used instead, so
the game never depends on assets that don't exist yet. Drop a real PNG with
the expected name into ``assets/images`` and it replaces the placeholder.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import pygame

from core import settings

logger = logging.getLogger(__name__)

SOUND_EXTENSIONS = (".wav", ".ogg", ".mp3")
MISSING_IMAGE_SIZE = 32
MISSING_IMAGE_COLORS = ((255, 0, 255), (0, 0, 0))


class AssetManager:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._images: dict[str, pygame.Surface] = {}
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._fonts: dict[tuple[str, int], pygame.font.Font] = {}

    @property
    def root(self) -> Path:
        return self._root

    def get_image(
        self,
        relative_path: str,
        fallback: Callable[[], pygame.Surface] | None = None,
    ) -> pygame.Surface:
        cached = self._images.get(relative_path)
        if cached is not None:
            return cached

        image = self._load_image(self._root / "images" / relative_path)
        if image is None:
            image = fallback() if fallback else _missing_image()
            image = image.convert_alpha()
        self._images[relative_path] = image
        return image

    def get_sound(
        self,
        name: str,
        fallback: Callable[[], pygame.mixer.Sound | None] | None = None,
    ) -> pygame.mixer.Sound | None:
        if name in self._sounds:
            return self._sounds[name]
        if pygame.mixer.get_init() is None:
            self._sounds[name] = None
            return None

        sound = None
        path = self._find_file(self._root / "sounds", name)
        if path is not None:
            try:
                sound = pygame.mixer.Sound(path)
            except pygame.error as error:
                logger.warning("Could not load sound %s: %s", path, error)
        if sound is None and fallback is not None:
            sound = fallback()
        self._sounds[name] = sound
        return sound

    def find_music(self, name: str) -> Path | None:
        return self._find_file(self._root / "music", name)

    def get_font(self, size: int, role: str = "ui") -> pygame.font.Font:
        """Font for a role ("display", "arabic", "ui", "body") at a pixel size."""
        key = (role, size)
        font = self._fonts.get(key)
        if font is None:
            font = self._load_font(role, size)
            self._fonts[key] = font
        return font

    @staticmethod
    def _load_font(role: str, size: int) -> pygame.font.Font:
        file_name = settings.FONT_FILES.get(role)
        if file_name:
            path = settings.FONTS_DIR / file_name
            if path.is_file():
                try:
                    return pygame.font.Font(path, size)
                except (pygame.error, OSError) as error:
                    logger.warning("Could not load font %s: %s", path, error)
        # pygame's built-in font is much smaller at the same size.
        return pygame.font.Font(None, round(size * 1.25))

    @staticmethod
    def _load_image(path: Path) -> pygame.Surface | None:
        if not path.is_file():
            return None
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error as error:
            logger.warning("Could not load image %s: %s", path, error)
            return None

    @staticmethod
    def _find_file(directory: Path, name: str) -> Path | None:
        for extension in SOUND_EXTENSIONS:
            path = directory / f"{name}{extension}"
            if path.is_file():
                return path
        return None


def _missing_image() -> pygame.Surface:
    """Magenta checkerboard: impossible to miss, so broken paths get noticed."""
    size = MISSING_IMAGE_SIZE
    half = size // 2
    surface = pygame.Surface((size, size))
    for index, (x, y) in enumerate(((0, 0), (half, 0), (half, half), (0, half))):
        surface.fill(MISSING_IMAGE_COLORS[index % 2], (x, y, half, half))
    return surface
