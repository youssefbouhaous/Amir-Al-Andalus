"""The Folded Fulcrum: a portable spring jack and a camshaft brace.

No stopped time or conjured platforms: pinned ribs unfold from Amir's cuff,
stand on real ground and lift a wooden tread. Beside the Archivist the same
ribs brace its exposed drive, giving a long, safe treadle stroke instead.
"""

import math

import pygame

from core.events import EventType
from jazari.base import Power
from objects.platforms import Platform
from rendering.art import archivist as art
from world.collision_map import TileCollision

LIFT_HEIGHT = 104.0
LIFT_LIFE = 5.2
BRACE_REACH = 190.0
UNFOLD_TIME = .36


class FoldingStep(Platform):
    def __init__(self, x, floor, height):
        super().__init__(x - 32, floor, 64, 8)
        self.x = x
        self.floor = floor
        self.height_limit = height
        self.age = 0.0
        self.alive = True
        self.struck = set()

    def update(self, dt, world):
        self.age += dt
        extension = art.smooth(self.age / .8) * (1 - art.smooth((self.age - 4.1) / 1.1))
        height = self.height_limit * extension
        self._move_to(self.x - 32, self.floor - height)
        if self.age < .8:
            # The rising ribs physically catch creatures, but not incorporeal spirits.
            area = pygame.Rect(round(self.x - 35), round(self.top - 14), 70, round(height + 18))
            for enemy in world.enemies:
                if (enemy.alive and enemy.is_dangerous and not enemy.star_immune
                        and id(enemy) not in self.struck and enemy.rect.colliderect(area)):
                    enemy.on_slashed(world, 1 if enemy.body.centerx >= self.x else -1)
                    self.struck.add(id(enemy))
        if self.age >= LIFT_LIFE:
            self.alive = False

    def draw(self, surface, camera):
        x, floor = camera.to_screen(self.x, self.floor)
        art.lift(surface, x, floor, max(1, self.floor - self.top), min(self.age, .8))


def footing(world, x, bottom):
    """Find a full-width footing below the prince, with headroom for a real jack.

    It cannot deploy in a pit, through masonry, under a low roof or beside a
    ledge with unsupported feet. Placement never edits collision tiles.
    """
    collision = world.collision
    columns = (math.floor((x - 31) / 32), math.floor(x / 32), math.floor((x + 31) / 32))
    if min(columns) < 0 or max(columns) >= collision.width:
        return None
    row = math.ceil((bottom - 2) / 32)
    for ty in range(max(0, row), min(collision.height, row + 5)):
        if not all(collision.get(tx, ty) == TileCollision.SOLID for tx in columns):
            continue
        floor = ty * 32
        if floor < bottom - 2 or floor - bottom > 128:
            return None
        clearance = 0
        # Reserve the player's standing height above the entire moving deck.
        for upper in range(ty - 1, max(-1, ty - 7), -1):
            if any(collision.get(tx, upper) == TileCollision.SOLID for tx in columns):
                break
            clearance += 32
        height = min(LIFT_HEIGHT, clearance - world.player.body.height - 8)
        if height < 32:
            return None
        # Reject a footing reached by searching through the current platform.
        area = pygame.Rect(round(x - 31), round(bottom - 2), 62, max(1, round(floor - bottom)))
        if any(kind == TileCollision.SOLID for _, _, kind in collision.cells_overlapping(*area.topleft, *area.bottomright)):
            return None
        return floor, height
    return None


class FoldedFulcrum(Power):
    key = "fulcrum"
    name = "The Folded Fulcrum"
    arabic = "الرافعة المطوية"
    summary = "V: unfold a lifting step; near a drive, brace it. Then pound."
    color = art.RED
    cooldown = 3.1

    def __init__(self, director):
        super().__init__(director)
        self.step = None
        self.brace_age = -1.0
        self.brace_source = (0, 0)
        self.brace_target = (0, 0)
        self.brace_foot = (0, 0)
        self._latched = False

    def activate(self, world, player):
        guardian = self.director.guardian
        if getattr(guardian, "can_brace", lambda _p: False)(player):
            self.cooldown = 3.1
            self.brace_source = (player.body.centerx + player.facing * 12, player.body.top + 16)
            self.brace_target = guardian.lock_rect().center
            self.brace_foot = (self.brace_target[0] - 43, guardian.floor - 3)
            self.brace_age = 0.0
            self._latched = False
            return True
        # One physical tool, not a stack of infinitely ascending platforms.
        if self.step is not None and self.step.alive:
            return False
        ground = footing(world, player.body.centerx, player.body.bottom)
        if ground is None:
            return False
        floor, height = ground
        self.cooldown = LIFT_LIFE
        self.step = FoldingStep(player.body.centerx, floor, height)
        world.platforms.append(self.step)
        if player.body.on_ground and abs(player.body.bottom - floor) <= 2:
            player.body.ground_platform = self.step
        return True

    def update(self, dt, world):
        super().update(dt, world)
        if self.step is not None and not self.step.alive:
            if self.step in world.platforms:
                world.platforms.remove(self.step)
            if world.player.body.ground_platform is self.step:
                world.player.body.ground_platform = None
            self.step = None
        if self.brace_age >= 0:
            self.brace_age += dt
            if not self._latched and self.brace_age >= UNFOLD_TIME:
                self._latched = True
                self.director.guardian.on_power(self.key, self, world)
            if self.brace_age > 3.6:
                self.brace_age = -1

    def draw_front(self, surface, camera):
        player = self.director.world.player
        # A tiny closed tool strapped to the belt; never covers the prince's face.
        x, y = camera.to_screen(player.body.centerx - player.facing * 9, player.body.bottom - 12)
        art.folds(surface, (x - 3, y - 8), (x + 3, y + 8), 3, 3, .5)
        if self.brace_age >= 0:
            t = self.brace_age
            extension = art.smooth(t / UNFOLD_TIME)
            retract = art.smooth((t - 3.0) / .6)
            start = pygame.Vector2(camera.to_screen(*self.brace_source))
            foot = pygame.Vector2(camera.to_screen(*self.brace_foot))
            start = start.lerp(foot, extension)
            end = pygame.Vector2(camera.to_screen(*self.brace_target))
            end = start.lerp(end, extension * (1 - retract))
            art.folds(surface, start, end, 19 * extension * (1 - retract), 6)
            if self._latched and retract < .5:
                pygame.draw.line(surface, art.IRON, (foot.x - 12, foot.y), (foot.x + 12, foot.y), 5)
                pygame.draw.line(surface, art.BONE, (end.x - 11, end.y - 19), (end.x + 11, end.y + 19), 4)
                pygame.draw.line(surface, art.RED, (end.x + 11, end.y - 19), (end.x - 11, end.y + 19), 3)

    @classmethod
    def icon(cls, surface, rect, t):
        art.emblem(surface, rect, t)

    @classmethod
    def miniature(cls, surface, rect, t):
        art.emblem(surface, rect.inflate(-8, -8), t)

    @classmethod
    def ceremony(cls, surface, center, t):
        art.ceremony(surface, center, t)
