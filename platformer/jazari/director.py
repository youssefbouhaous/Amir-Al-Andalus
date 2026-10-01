"""Runs one level's Ingenious Device and the power from its three pages.

The director is installed by the world builder when a level has an entry in
``jazari.catalog``. It

* places the level's guardian near the finish and *locks the exit* (the
  arch is bolted with al-Jazari's four-bolt lock) until it is beaten;
* grants the level's power when all three manuscript pages are known
  (collected now or on an earlier visit), and fires it on the POWER key;
* opens the manuscript overlay when a page is found, and the grant
  ceremony when the third one completes the set.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.input import Action, InputState
from jazari import art
from jazari.base import Guardian, Power
from jazari.manuscript import GrantCeremony, ManuscriptOverlay
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from ui.text import HUD_STYLE, render_styled

if TYPE_CHECKING:
    from core.assets import AssetManager
    from jazari.catalog import Entry
    from world.world import World

T = 32
ALL_PAGES = frozenset({0, 1, 2})
BOLT_TIME = 1.1


_prewarmed = False


def _prewarm_sounds(assets: "AssetManager") -> None:
    """Synthesize the machines' sounds in the background so the first tide doesn't hitch."""
    global _prewarmed
    if _prewarmed:
        return
    _prewarmed = True
    import threading

    from audio.synth import SOUND_RECIPES, synthesize

    names = [name for name in SOUND_RECIPES if name.startswith(("wonder_", "power_"))]

    def work() -> None:
        for name in names:
            assets.get_sound(name, lambda name=name: synthesize(name))

    threading.Thread(target=work, name="wonder-sounds", daemon=True).start()


class WonderDirector:
    def __init__(self, world: "World", entry: "Entry", known_pages: set[int], assets: "AssetManager",
                 resolved: bool = False, progress: int = 0) -> None:
        self.world = world
        self.entry = entry
        self.assets = assets
        self.known_pages = set(known_pages)
        # How far the fight got before the prince fell (kept for the retry).
        self.progress = progress
        x = entry.anchor_col * T + T / 2
        floor = entry.floor_row * T
        self.guardian: Guardian = entry.guardian(self, x, floor)
        self.power: Power | None = entry.power(self) if ALL_PAGES <= self.known_pages else None
        self.overlay: ManuscriptOverlay | GrantCeremony | None = None
        self._queue: list[ManuscriptOverlay | GrantCeremony] = []
        self._held_goals = []
        self._bolt_timer = 0.0
        self.time = 0.0
        self._font = assets.get_font(15, "ui")
        self._key_font = assets.get_font(13, "ui")
        if resolved:
            self.guardian.resolved = True
            self.guardian.resolution = "already"
        else:
            self._lock(world)
        _prewarm_sounds(assets)

    # --- the lock on the exit ------------------------------------------------------------
    @property
    def locked(self) -> bool:
        return bool(self._held_goals) or self._gate_locked

    _gate_locked = False

    def _lock(self, world: "World") -> None:
        if self.entry.lock == "arena_gate":
            self._gate_locked = True
            for gate in world.gates_in("arena"):
                gate.open = False
                gate._openness = 0.0
                gate.register(world)
            return
        self._held_goals = list(world.goals)
        world.goals.clear()

    def _unlock(self, world: "World") -> None:
        if self._gate_locked:
            self._gate_locked = False
            for gate in world.gates_in("arena"):
                gate.set_open(True, world)
        if self._held_goals:
            world.goals.extend(self._held_goals)
            self._bolt_timer = BOLT_TIME
            self._unlocked_goals = list(self._held_goals)
            self._held_goals = []
        world.events.emit(EventType.GATE_OPENED, (self.guardian.x, self.guardian.floor))

    # --- pages and powers ------------------------------------------------------------------
    @property
    def overlay_active(self) -> bool:
        return self.overlay is not None

    def on_page_collected(self, index: int) -> None:
        if index < 0 or index > 2:
            return
        fresh = index not in self.known_pages
        self.known_pages.add(index)
        if fresh:
            self._push(ManuscriptOverlay(self.entry, index, self.assets, len(self.known_pages)))
        if self.power is None and ALL_PAGES <= self.known_pages:
            self._push(GrantCeremony(self.entry, self.assets))

    def _push(self, overlay: "ManuscriptOverlay | GrantCeremony") -> None:
        if self.overlay is None:
            self.overlay = overlay
        else:
            self._queue.append(overlay)

    def update_overlay(self, dt: float, input_state: InputState) -> None:
        if self.overlay is None:
            return
        confirm = input_state.was_pressed(Action.CONFIRM) or input_state.was_pressed(Action.JUMP) \
            or input_state.was_pressed(Action.POWER)
        player = self.world.player
        screen_pos = self._prince_on_screen
        if isinstance(self.overlay, GrantCeremony):
            self.overlay.prince = screen_pos
        if self.overlay.update(dt, confirm):
            finished = self.overlay
            if isinstance(finished, GrantCeremony) and self.power is None:
                self.power = self.entry.power(self)
                self.world.events.emit(EventType.POWER_GRANTED, player.body.midbottom, self.power.key)
            self.overlay = self._queue.pop(0) if self._queue else None

    _prince_on_screen: tuple[float, float] = (480, 300)

    # --- simulation -----------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self._bolt_timer = max(0.0, self._bolt_timer - dt)
        power = self.power
        if power is not None:
            if world.player.intent.power_pressed:
                power.use(world)
            power.update(dt, world)
        self.guardian.update(dt, world)
        if self.guardian.resolved and self.locked:
            self._unlock(world)

    # --- what the scene asks of the machine ---------------------------------------------------
    @property
    def camera_focus(self) -> tuple[float, float] | None:
        return self.guardian.camera_focus

    def ambient(self, base: "tuple[int, int, int] | None") -> "tuple[int, int, int] | None":
        """The level's light, darkened toward moonlit night by the machine's dusk."""
        dusk = self.guardian.dusk
        if dusk <= 0.01:
            return base
        day = base if base is not None else (255, 255, 255)
        return tuple(round(a + (b - a) * dusk) for a, b in zip(day, self.guardian.night))

    def lights(self) -> list[Light]:
        lights = list(self.guardian.lights())
        if self.power is not None:
            lights += self.power.lights()
        return lights

    # --- drawing ------------------------------------------------------------------------------------
    def draw_scenery(self, surface: pygame.Surface, camera: Camera) -> None:
        self.guardian.draw_scenery(surface, camera)

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        self._prince_on_screen = camera.to_screen(self.world.player.body.centerx, self.world.player.body.centery)
        for goal in self._held_goals:
            goal.draw(surface, camera)
            self._draw_bolts(surface, camera, goal.rect, 0.0)
        if self._bolt_timer > 0:
            for goal in getattr(self, "_unlocked_goals", []):
                self._draw_bolts(surface, camera, goal.rect, 1.0 - self._bolt_timer / BOLT_TIME)
        self.guardian.draw_back(surface, camera)
        if self.power is not None:
            self.power.draw_back(surface, camera)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        self.guardian.draw(surface, camera)
        if self.power is not None:
            self.power.draw(surface, camera)

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        self.guardian.draw_front(surface, camera)
        if self.power is not None:
            self.power.draw_front(surface, camera)

    def _draw_bolts(self, surface: pygame.Surface, camera: Camera, goal_rect: pygame.Rect, opened: float) -> None:
        """Al-Jazari's four-bolt door lock across the arch; bolts slide back when opened."""
        cx, bottom = camera.to_screen(goal_rect.centerx, goal_rect.bottom)
        plate = pygame.Rect(0, 0, 34, 42)
        plate.center = (cx, bottom - 46)
        fade = 1.0 - opened
        if fade <= 0:
            return
        for k in range(4):
            y = plate.top + 7 + k * 10
            length = round(34 * fade)
            pygame.draw.rect(surface, art.OUTLINE, (plate.centerx - 17 - length, y - 3, length * 2 + 34, 6))
            pygame.draw.rect(surface, art.IRON_LIGHT, (plate.centerx - 16 - length, y - 2, length * 2 + 32, 4))
        pygame.draw.rect(surface, art.OUTLINE, plate.inflate(4, 4), border_radius=5)
        pygame.draw.rect(surface, art.BRASS, plate, border_radius=4)
        for k in range(4):
            angle = self.time * 0.6 + k
            art.dial(surface, (plate.centerx, plate.top + 7 + k * 10), 4, angle, "....")
        blit_glow(surface, plate.center, 26, (255, 200, 110), 0.25 * fade)

    def draw_screen(self, surface: pygame.Surface) -> None:
        self._draw_power_slot(surface)
        if self.overlay is not None:
            self.overlay.draw(surface)

    def _draw_power_slot(self, surface: pygame.Surface) -> None:
        center = (36, 104)
        radius = 22
        power = self.power
        color = power.color if power is not None else (90, 80, 100)
        art.emblem_frame(surface, center, radius, (30, 22, 36))
        icon_rect = pygame.Rect(0, 0, 30, 30)
        icon_rect.center = center
        if power is not None:
            power.icon(surface, icon_rect, self.time)
            if not power.ready:
                fraction = power.cooldown_left / max(0.01, power.cooldown)
                arc = pygame.Rect(0, 0, radius * 2 + 6, radius * 2 + 6)
                arc.center = center
                pygame.draw.arc(surface, (40, 30, 40), arc, math.pi / 2, math.pi / 2 + math.tau * fraction, 4)
            elif power.flash > 0 or int(self.time * 2) % 2 == 0:
                blit_glow(surface, center, radius + 8, color, 0.25 + 0.4 * power.flash)
            key = render_styled(self._key_font, "V", HUD_STYLE)
            surface.blit(key, key.get_rect(center=(center[0] + radius, center[1] + radius - 2)))
            name = render_styled(self._font, power.name, HUD_STYLE)
            surface.blit(name, name.get_rect(midleft=(center[0] + radius + 12, center[1])))
        else:
            count = len(self.known_pages & ALL_PAGES)
            label = render_styled(self._font, f"{count}/3 pages", HUD_STYLE)
            q = render_styled(self._font, "?", HUD_STYLE)
            surface.blit(q, q.get_rect(center=center))
            surface.blit(label, label.get_rect(midleft=(center[0] + radius + 12, center[1])))
