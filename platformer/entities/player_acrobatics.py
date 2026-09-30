"""Courtyard-only acrobatics. Original campaign movement remains opt-out.

Ledge vaults use two collision-tested legs (up, then across), never a diagonal
teleport through terrain. Grappling reuses the established ring simulation.
"""

import math

import pygame

from physics.collision import move_body
from rendering import emitters
from world.collision_map import TileCollision


class PlayerAcrobatics:
    def _init_acrobatics(self):
        self.acrobatics_enabled = False
        self._reset_acrobatics()

    def _reset_acrobatics(self):
        self._ledge = None
        self._ledge_cooldown = 0.0
        self._grapple_cast = 0.0
        self._spin_timer = 0.0
        self._landing_pose = "land_soft"
        self._landing_timer = 0.0

    def _update_acrobatics(self, dt, world):
        from entities.player import PlayerState

        if not self.acrobatics_enabled:
            return False
        for name in ("_ledge_cooldown", "_grapple_cast", "_spin_timer", "_landing_timer"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        if self.state in (PlayerState.LEDGE_HANG, PlayerState.VAULT):
            self._update_ledge(dt, world)
            return True
        if (self.intent.up_pressed and not self.intent.dash_pressed and not self.intent.down_held
                and not self.body.on_ground and self._ring_cooldown <= 0
                and self.state in (PlayerState.JUMPING, PlayerState.FALLING, PlayerState.GLIDE,
                                   PlayerState.WALL_SLIDE)):
            hook = self._nearby_hook(world)
            if hook is not None:
                hook.prepare((self.body.centerx, self.body.top - 4))
                self._grab_ring(hook, world)
                self._jump_buffer_timer = 0.0
                self._jump_cuttable = False
                self._grapple_cast = .15
                return True
        return False

    def _clear_tether(self, world, start, end):
        delta = pygame.Vector2(end) - start
        steps = max(1, math.ceil(delta.length() / 8))
        for i in range(steps + 1):
            point = pygame.Vector2(start) + delta * (i / steps)
            if world.collision.get(*world.collision.tile_at(*point)) == TileCollision.SOLID:
                return False
        return True

    def _nearby_hook(self, world):
        hand = pygame.Vector2(self.body.centerx, self.body.top - 4)
        candidates = sorted(world.grapple_hooks, key=lambda h: hand.distance_squared_to(h.anchor))
        for hook in candidates:
            distance = hand.distance_to(hook.anchor)
            if (hook.can_grab and 30 <= distance <= hook.REACH and hook.anchor.y < hand.y - 12
                    and self._clear_tether(world, hand, hook.anchor)):
                return hook
        return None

    def _ledge_clear(self, world, rect):
        from objects.hazards import Spikes, Water
        from objects.mechanisms import BladeTrap

        if not world.bounds.contains(rect):
            return False
        if any(kind == TileCollision.SOLID for _, _, kind in world.collision.cells_overlapping(
                rect.left, rect.top, rect.right, rect.bottom)):
            return False
        return not any(isinstance(prop, (Spikes, Water, BladeTrap))
                       and prop.touch_rect().colliderect(rect) for prop in world.props)

    def _try_ledge(self, world):
        from entities.player import PlayerState

        body, side = self.body, self.intent.move_axis
        if (not self.acrobatics_enabled or self._ledge_cooldown > 0 or not side
                or body.on_ground or body.velocity.y < 0 or self.intent.down_held
                or self._gliding or self._jump_buffer_timer > 0):
            return False
        size = world.collision.tile_size
        tx = math.floor((body.right + 2 if side > 0 else body.left - 2) / size)
        for ty in range(math.floor((body.top - 16) / size), math.floor((body.top + 8) / size) + 1):
            top = ty * size
            if not -8 <= body.top - top <= 16:
                continue
            if (world.collision.get(tx, ty) != TileCollision.SOLID
                    or world.collision.get(tx, ty - 1) != TileCollision.EMPTY):
                continue
            hang_x = tx * size - body.width - 1 if side > 0 else (tx + 1) * size + 1
            target_x = tx * size + 2 if side > 0 else (tx + 1) * size - body.width - 2
            hang = pygame.Rect(round(hang_x), top + 4, body.width, body.height)
            target = pygame.Rect(round(target_x), top - body.height, body.width, body.height)
            raised = hang.copy()
            raised.bottom = top
            if not all(self._ledge_clear(world, r) for r in (hang, target, hang.union(raised), raised.union(target))):
                continue
            self._ledge = (hang_x, top + 4, target_x, top - body.height, side, tx, ty)
            body.x, body.y = hang_x, top + 4
            body.velocity.update(0, 0)
            body.clear_contacts()
            self._coyote_timer = self._wall_timer = 0.0
            self._jump_cuttable = False
            self.facing = side
            self._set_state(PlayerState.LEDGE_HANG)
            return True
        return False

    def _drop_ledge(self):
        from entities.player import PlayerState

        self._ledge = None
        self._ledge_cooldown = .35
        self.body.velocity.update(0, 50)
        self._jump_buffer_timer = self._wall_timer = self._coyote_timer = 0.0
        self._set_state(PlayerState.FALLING)

    def _update_ledge(self, dt, world):
        from entities.player import PlayerState

        if self._ledge is None:
            self._drop_ledge()
            return
        x0, y0, x1, y1, side, tx, ty = self._ledge
        if self.intent.down_held or world.collision.get(tx, ty) != TileCollision.SOLID:
            self._drop_ledge()
            return
        if self.state == PlayerState.LEDGE_HANG:
            self.body.velocity.update(0, 0)
            self._update_throw(world)
            if (self._jump_buffer_timer > 0 or self.intent.up_pressed
                    or (self._state_time > .18 and self.intent.move_axis == side)):
                self._jump_buffer_timer = 0.0
                self._set_state(PlayerState.VAULT)
            return
        t = min(1.0, self._state_time / .24)
        # Separate axes keeps both the collider and animation outside the ledge.
        target = (x0, y0 + (y1 - y0) * min(1, t / .6)) if t < .6 else (x0 + (x1 - x0) * ((t - .6) / .4), y1)
        candidate = self.rect.copy()
        candidate.topleft = (round(target[0]), round(target[1]))
        swept = self.rect.union(candidate)
        if not self._ledge_clear(world, swept):
            self._drop_ledge()
            return
        self.body.velocity.update((target[0] - self.body.x) / dt, (target[1] - self.body.y) / dt)
        move_body(self.body, dt, world.collision, world.platforms)
        self.body.velocity.update(0, 0)
        if t >= 1:
            self._ledge = None
            self.body.on_ground = True
            self._was_on_ground = True
            self.refill_dash()
            self._set_state(PlayerState.IDLE)
            emitters.run_dust(world.particles, self.body.centerx, self.body.bottom, side, world.dust_color)

    def _acrobatics_animation(self):
        from entities.player import PlayerState

        if not self.acrobatics_enabled:
            return None
        if self.state == PlayerState.LEDGE_HANG:
            return "ledge_hang"
        if self.state == PlayerState.VAULT:
            return "vault"
        if self.state == PlayerState.SWING and getattr(self._ring, "is_grapple_hook", False):
            return "scarf_cast" if self._grapple_cast > 0 else "scarf_swing"
        if self.state == PlayerState.SLIDE:
            return "sand_slide"
        if self.state not in (PlayerState.IDLE, PlayerState.RUNNING, PlayerState.JUMPING, PlayerState.FALLING):
            return None
        if self._hurt_timer > 0 or self._throw_timer > 0:
            return None
        if not self.body.on_ground:
            if self._spin_timer > 0:
                return "spin_jump"
            if self._wall_lock_timer > 0:
                return "wall_kick"
        elif self._landing_timer > 0 and abs(self.body.velocity.x) < 60 and not self.intent.move_axis:
            return self._landing_pose
        return None

    def _draw_grapple(self, surface, camera):
        hook = self._ring
        if not getattr(hook, "is_grapple_hook", False):
            return
        start = pygame.Vector2(self._scarf_anchor())
        delta = hook.anchor - start
        normal = pygame.Vector2(-delta.y, delta.x).normalize() if delta.length_squared() else pygame.Vector2()
        points = []
        for i in range(21):
            t = i / 20
            wave = math.sin(t * math.pi) * math.sin(t * math.tau * 2 - self._state_time * 18)
            point = start + delta * t + normal * wave * (2 + self._grapple_cast * 110)
            points.append(camera.to_screen(*point))
        pygame.draw.lines(surface, (42, 24, 26), False, points, 6)
        pygame.draw.lines(surface, self._palette().scarf, False, points, 4)
        pygame.draw.lines(surface, self._palette().scarf_tip, False, points, 1)
