from dataclasses import dataclass
from typing import TYPE_CHECKING

from audio.audio_manager import AudioManager
from core.assets import AssetManager
from core.input import InputState
from core.save import SaveManager
from rendering.sprite_library import SpriteLibrary
from ui.debug_overlay import DebugOverlay
from world.level_loader import LevelLoader

if TYPE_CHECKING:
    from scenes.scene_manager import SceneManager


@dataclass
class GameContext:
    """Long-lived services shared by all scenes.

    Passed explicitly to every scene instead of being global, which keeps
    dependencies visible and makes scenes testable in isolation.
    """

    assets: AssetManager
    audio: AudioManager
    input: InputState
    sprites: SpriteLibrary
    levels: LevelLoader
    debug: DebugOverlay
    scenes: "SceneManager"
    save: SaveManager
