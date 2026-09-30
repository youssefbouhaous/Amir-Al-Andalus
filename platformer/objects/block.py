"""Interactive blocks that occupy a cell of the collision map.

Plain solid blocks (ground, stone) are just cells in the CollisionMap and need
no object. Only blocks with behaviour get a class. They also occupy a SOLID
cell in the collision map, so physics treats them like any other wall; the
World looks up the Block when the player's head hits that cell.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import BLOCKS
from entities.items import release_block_contents, release_coin
from rendering import emitters
from rendering.camera import Camera
from world.collision_map import TileCollision

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

MULTICOIN_WINDOW = 4.0
MULTICOIN_MAX = 10
CRUMBLE_DELAY = 0.45
CRUMBLE_RESPAWN = 3.5
SHAKE_AMPLITUDE = 1.6


class Block:
    def __init__(self, cell: tuple[int, int], tile_size: int, image: pygame.Surface) -> None:
        self.cell = cell
        self.rect = pygame.Rect(cell[0] * tile_size, cell[1] * tile_size, tile_size, tile_size)
        self.image = image
        self._bump_timer = 0.0

    @property
    def solid(self) -> bool:
        return True

    def update(self, dt: float, world: "World") -> None:
        if self._bump_timer > 0:
            self._bump_timer = max(0.0, self._bump_timer - dt)

    def hit_from_below(self, player: "Player", world: "World") -> None:
        self._bump(world)

    def smash(self, how: str, player: "Player", world: "World") -> bool:
        """Hit by a move: ``how`` is "dash", "slide" or "pound" (from above).

        Returns True if the block is gone and the move should carry on."""
        if how == "pound":
            self.hit_from_below(player, world)
        return False

    def _bump(self, world: "World") -> None:
        self._bump_timer = BLOCKS.bump_duration
        world.events.emit(EventType.BLOCK_BUMPED, self.rect.midtop)
        world.bump_from_below(self.rect)

    def _bump_offset(self) -> float:
        # Visual only: the block pops up and back along half a sine wave.
        if self._bump_timer <= 0:
            return 0.0
        progress = 1.0 - self._bump_timer / BLOCKS.bump_duration
        return -math.sin(math.pi * progress) * BLOCKS.bump_height

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self.image, camera.to_screen(self.rect.x, self.rect.y + self._bump_offset()))


class BrickBlock(Block):
    """Breaks when hit by a powered-up player, otherwise just bumps."""

    def hit_from_below(self, player: "Player", world: "World") -> None:
        if player.powered:
            world.break_block(self)
        else:
            self._bump(world)

    def smash(self, how: str, player: "Player", world: "World") -> bool:
        # A ground pound is heavy enough to break brick in any robe.
        if how == "pound":
            world.break_block(self)
            return True
        return False


class QuestionBlock(Block):
    """Releases its contents once, then turns into a used block.

    ``multicoin`` blocks keep paying out coins for a few seconds after the
    first hit, up to ten.
    """

    def __init__(
        self,
        cell: tuple[int, int],
        tile_size: int,
        image: pygame.Surface,
        used_image: pygame.Surface,
        contents: str,
    ) -> None:
        super().__init__(cell, tile_size, image)
        self._used_image = used_image
        self.contents = contents
        self.used = False
        self._coins_left = MULTICOIN_MAX if contents == "multicoin" else 0
        self._multicoin_timer = 0.0
        self._time = cell[0] * 0.37

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self._time += dt
        if self._multicoin_timer > 0:
            self._multicoin_timer -= dt
            if self._multicoin_timer <= 0:
                self._coins_left = 0
                self._use_up()

    def hit_from_below(self, player: "Player", world: "World") -> None:
        self._bump(world)
        if self.used:
            return
        if self.contents == "multicoin":
            release_coin(self.rect, world)
            if self._multicoin_timer <= 0:
                self._multicoin_timer = MULTICOIN_WINDOW
            self._coins_left -= 1
            if self._coins_left <= 0:
                self._use_up()
            return
        self._use_up()
        release_block_contents(self.contents, self.rect, world)

    def _use_up(self) -> None:
        self.used = True
        self.image = self._used_image
        self._multicoin_timer = 0.0

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        super().draw(surface, camera)
        if not self.used:
            # A glint sweeps across unused blocks every few seconds.
            phase = (self._time % 3.2) / 0.5
            if phase < 1.0:
                x, y = camera.to_screen(self.rect.x, self.rect.y + self._bump_offset())
                gx = x + round(phase * (self.rect.width + 12)) - 6
                clip = surface.get_clip()
                surface.set_clip(pygame.Rect(x, y, self.rect.width, self.rect.height).clip(clip))
                pygame.draw.line(surface, (255, 255, 240), (gx, y + self.rect.height), (gx + 10, y), 3)
                surface.set_clip(clip)


class CrumbleBlock(Block):
    """A sandstone slab that shakes when stood on, then drops away.

    It comes back a few seconds later (unless something is in the way).
    """

    def __init__(self, cell: tuple[int, int], tile_size: int, image: pygame.Surface) -> None:
        super().__init__(cell, tile_size, image)
        self._timer = 0.0
        self._state = "solid"  # solid | shaking | gone | returning
        self._fade = 1.0

    @property
    def solid(self) -> bool:
        return self._state in ("solid", "shaking")

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        if self._state == "solid":
            if self.cell in world.cells_under_player():
                self._state = "shaking"
                self._timer = CRUMBLE_DELAY
        elif self._state == "shaking":
            self._timer -= dt
            if int(self._timer * 30) % 3 == 0:
                emitters.debris(world.particles, self.rect.centerx, self.rect.bottom, ((190, 150, 96),), 1, 0.2)
            if self._timer <= 0:
                self._state = "gone"
                self._timer = CRUMBLE_RESPAWN
                world.collision.set(*self.cell, TileCollision.EMPTY)
                emitters.debris(world.particles, self.rect.centerx, self.rect.centery,
                                ((210, 170, 110), (170, 128, 80), (236, 204, 150)), 12, 0.6)
                world.events.emit(EventType.PLATFORM_CRUMBLED, self.rect.center)
        elif self._state == "gone":
            self._timer -= dt
            if self._timer <= 0 and not world.anything_overlaps(self.rect):
                self._state = "returning"
                self._fade = 0.0
                world.collision.set(*self.cell, TileCollision.SOLID)
        elif self._state == "returning":
            self._fade = min(1.0, self._fade + dt * 3)
            if self._fade >= 1.0:
                self._state = "solid"

    def hit_from_below(self, player: "Player", world: "World") -> None:
        self._bump(world)

    def smash(self, how: str, player: "Player", world: "World") -> bool:
        if how != "pound" or not self.solid:
            return False
        self._state = "shaking"
        self._timer = 0.0
        self.update(0.0, world)  # collapse right now
        return True

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self._state == "gone":
            return
        dx = 0.0
        if self._state == "shaking":
            dx = math.sin(self._timer * 90) * SHAKE_AMPLITUDE
        x, y = camera.to_screen(self.rect.x + dx, self.rect.y + self._bump_offset())
        if self._state == "returning":
            image = self.image.copy()
            image.set_alpha(round(255 * self._fade))
            surface.blit(image, (x, y))
        else:
            surface.blit(self.image, (x, y))


class SwitchBlock(Block):
    """Sun or moon block: solid only while its colour is the active one.

    A block that should become solid while something overlaps it waits until
    the space is clear, so nobody is ever crushed or trapped by a toggle.
    """

    def __init__(self, cell: tuple[int, int], tile_size: int, image: pygame.Surface,
                 ghost: pygame.Surface, color: str) -> None:
        super().__init__(cell, tile_size, image)
        self.color = color
        self._ghost = ghost
        self._active = False
        self._pending = False
        self._warning = False
        self._time = 0.0

    @property
    def solid(self) -> bool:
        return self._active and not self._pending

    def set_active(self, active: bool, world: "World") -> None:
        self._active = active
        self._warning = False
        if active and world.anything_overlaps(self.rect):
            self._pending = True
            world.collision.set(*self.cell, TileCollision.EMPTY)
            return
        self._pending = False
        world.collision.set(*self.cell, TileCollision.SOLID if active else TileCollision.EMPTY)
        if active:
            emitters.sparkle_burst(world.particles, self.rect.centerx, self.rect.centery,
                                   (255, 220, 120) if self.color == "sun" else (170, 190, 255), 4, 60)

    def warn(self) -> None:
        self._warning = True

    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self._time += dt
        if self._pending and not world.anything_overlaps(self.rect):
            self._pending = False
            world.collision.set(*self.cell, TileCollision.SOLID)

    def hit_from_below(self, player: "Player", world: "World") -> None:
        self._bump(world)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        position = camera.to_screen(self.rect.x, self.rect.y + self._bump_offset())
        if self.solid:
            if self._warning and int(self._time * 12) % 2 == 0:
                image = self.image.copy()
                image.fill((70, 70, 70), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(image, position)
            else:
                surface.blit(self.image, position)
        else:
            surface.blit(self._ghost, position)


class SwitchToggleBlock(Block):
    """Hitting this block flips which of sun/moon is solid (manual mode)."""

    def hit_from_below(self, player: "Player", world: "World") -> None:
        self._bump(world)
        if world.switch is not None:
            world.switch.toggle(world)


class CrackedBlock(Block):
    """Cracked sandstone. A dash, slide or ground pound bursts through it."""

    def smash(self, how: str, player: "Player", world: "World") -> bool:
        world.break_block(self)
        emitters.debris(world.particles, self.rect.centerx, self.rect.centery,
                        ((214, 176, 118), (182, 140, 88), (236, 206, 150)), 14, 0.9)
        return True

    def hit_from_below(self, player: "Player", world: "World") -> None:
        if player.powered:
            self.smash("bump", player, world)
        else:
            self._bump(world)
