"""Base classes for manuscript powers and the Ingenious Devices.

Design rules (the "lock and key"):

* Every guardian runs on a VISIBLE physical system (a waterline, a cam, a
  candle, a counterweight, an escapement) that the prince can read and
  interfere with. No magic: anything thrown is thrown by a mechanism.
* Guardians threaten rhythm more than health: most of their blows *shove*
  the prince (a knock-back that briefly takes his footing) rather than hurt.
* Each guardian has a hard way to beat it with ordinary moves, and a far
  easier way with the power of its level's three manuscript pages.
* Each power also works outside its guardian (traversal, secrets or
  ordinary enemies), so the pages are never a single-use key.
"""

from typing import TYPE_CHECKING, ClassVar

import pygame

from core.events import EventType
from core.settings import Color
from rendering.camera import Camera
from rendering.lighting import Light

if TYPE_CHECKING:
    from entities.player import Player
    from jazari.director import WonderDirector
    from world.world import World

T = 32


# --- helpers shared by guardians and powers ------------------------------------------------
def pending_events(world: "World", kind: EventType) -> list:
    """Events emitted this step that the scene hasn't drained yet."""
    return [event for event in world.events._events if event.type == kind]


def shove(world: "World", vx: float, vy: float, lock: float = 0.28) -> bool:
    """Knock the prince back without hurting him: a rhythm threat, not a wound."""
    player = world.player
    if not player.is_controllable or player._invulnerable_timer > 0:
        return False
    if player.state.name in ("SWING", "DASH"):
        player._reset_moves()
    player.body.velocity.update(vx, vy)
    player.body.ground_platform = None
    player._wall_lock_timer = max(player._wall_lock_timer, lock)
    player._jump_cuttable = False
    world.events.emit(EventType.PLAYER_SHOVED, player.body.midbottom)
    return True


def ground_below(world: "World", x: float, from_y: float) -> float:
    """The top of the first solid tile at or below ``from_y`` in column ``x``."""
    collision = world.collision
    tx = int(x // T)
    for ty in range(max(0, int(from_y // T) - 6), collision.height):
        if collision.get(tx, ty).name == "SOLID":
            return ty * T
    return float(collision.pixel_height)


def slashed(world: "World", rect: pygame.Rect) -> bool:
    attack = world.player.attack_rect
    return attack is not None and attack.colliderect(rect)


def pounded_on(world: "World", rect: pygame.Rect) -> bool:
    """Did a ground pound land on ``rect`` this step?"""
    for event in pending_events(world, EventType.PLAYER_POUNDED):
        x, y = event.position
        if rect.left - 10 <= x <= rect.right + 10 and rect.top - 12 <= y <= rect.bottom + 4:
            return True
    return False


def pounding_onto(world: "World", rect: pygame.Rect) -> bool:
    """A plunging pound currently overlapping the top of ``rect``."""
    player = world.player
    top = pygame.Rect(rect.x - 4, rect.y - 12, rect.width + 8, 26)
    return player.is_pounding and player._pound_falling and player.rect.colliderect(top)


def dashed_into(world: "World", rect: pygame.Rect) -> bool:
    player = world.player
    return player.is_dashing and player.rect.inflate(8, 6).colliderect(rect)


def slid_into(world: "World", rect: pygame.Rect) -> bool:
    player = world.player
    return player.state.name == "SLIDE" and player.rect.inflate(6, 6).colliderect(rect)


def stomped(world: "World", rect: pygame.Rect) -> bool:
    player = world.player
    return (player.body.velocity.y > 0 and player.previous_bottom <= rect.top + 8
            and player.rect.colliderect(rect))


# --- powers ---------------------------------------------------------------------------------
class Power:
    """A device from al-Jazari's book, rebuilt by the prince from three pages."""

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    arabic: ClassVar[str] = ""          # short Arabic title for the manuscript
    summary: ClassVar[str] = ""          # one line for the HUD and the grant card
    color: ClassVar[Color] = (255, 255, 255)
    cooldown: ClassVar[float] = 1.0

    def __init__(self, director: "WonderDirector") -> None:
        self.director = director
        self.cooldown_left = 0.0
        self.time = 0.0
        self.flash = 0.0

    @property
    def ready(self) -> bool:
        return self.cooldown_left <= 0

    def use(self, world: "World") -> bool:
        player = world.player
        if not self.ready or not player.is_controllable:
            return False
        if self.activate(world, player):
            self.cooldown_left = self.cooldown
            self.flash = 1.0
            world.events.emit(EventType.POWER_USED, player.body.midbottom, self.key)
            return True
        return False

    def activate(self, world: "World", player: "Player") -> bool:
        raise NotImplementedError

    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.cooldown_left = max(0.0, self.cooldown_left - dt)
        self.flash = max(0.0, self.flash - dt * 2)

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        """Drawn after the prince (a companion on his shoulder, a wave passing over him)."""

    def lights(self) -> list[Light]:
        return []

    # Visual identity -------------------------------------------------------------------
    @classmethod
    def icon(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        """The HUD emblem (and the engraving on its guardian's rondel)."""

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        """The device as drawn in the manuscript (ink style)."""
        cls.icon(surface, rect, t)

    @classmethod
    def ceremony(cls, surface: pygame.Surface, center: tuple[float, float], t: float) -> None:
        """This power's own grant animation, ``t`` from 0 to 1 over ~2.4 s."""


# --- guardians ------------------------------------------------------------------------------
class Guardian:
    """One of the Ingenious Devices, running unattended near a level's end."""

    name: ClassVar[str] = ""
    device: ClassVar[str] = ""           # which of al-Jazari's machines it is
    lethal: ClassVar[bool] = True        # False = disabled/rerouted/reprogrammed, not destroyed
    reach: ClassVar[int] = 14            # arena half-width in tiles
    intro: ClassVar[str] = ""            # the plaque text shown when it wakes

    def __init__(self, director: "WonderDirector", x: float, floor: float) -> None:
        self.director = director
        self.x = x
        self.floor = floor
        self.time = 0.0
        self.awake = False
        self.resolved = False
        self.resolution = ""
        self.flash = 0.0
        self.arena = pygame.Rect(round(x - self.reach * T), round(floor - 12 * T), self.reach * 2 * T, 12 * T)

    def wake_check(self, world: "World") -> None:
        if not self.awake and self.arena.collidepoint(world.player.body.centerx, world.player.body.centery):
            self.awake = True
            world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), self.name)

    def resolve(self, world: "World", how: str) -> None:
        if self.resolved:
            return
        self.resolved = True
        self.resolution = how
        world.events.emit(EventType.GUARDIAN_RESOLVED, (self.x, self.floor - 60), how)

    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.flash = max(0.0, self.flash - dt * 3)
        self.wake_check(world)

    def on_power(self, kind: str, thing: object, world: "World") -> bool:
        """A power's effect touched this guardian. Return True if it reacted."""
        return False

    def lock_rect(self) -> pygame.Rect:
        """Where the power must be applied (for effects that seek a target)."""
        return pygame.Rect(round(self.x) - 20, round(self.floor) - 60, 40, 40)

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def lights(self) -> list[Light]:
        return []

    @property
    def camera_focus(self) -> tuple[float, float] | None:
        """Where the camera should frame the fight (None = follow the prince)."""
        return None

    dusk: float = 0.0     # 0..1: how far this machine has pulled the night over the level

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float, solved: float) -> None:
        """The machine as a manuscript illustration; ``solved`` 0..1 shows it beaten."""

    @classmethod
    def miniature_lock(cls, rect: pygame.Rect) -> tuple[float, float]:
        """Where, in the miniature, the power is applied (for page 3's demo)."""
        return rect.center
