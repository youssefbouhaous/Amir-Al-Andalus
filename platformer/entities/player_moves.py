"""The prince's Book II moveset: dash, slide, ground pound, glide and swing.

Written as a mixin so ``player.py`` keeps the core platforming and this file
holds everything the new moves add. Each move is a PlayerState with its own
small update function; the shared rules are:

* Every move is interruptible by the one that naturally follows it (a dash
  out of a swing, a jump out of a slide, a glide after a dash...), so they
  chain into combos.
* The dash has one charge in the air. Landing, grabbing a ring or touching a
  dash lantern refills it.
* Moves that hit things (dash, slide, pound) knock enemies out and smash
  cracked stone, so each is both traversal and attack.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from physics.collision import apply_gravity, approach, move_body
from rendering import emitters
from rendering.camera import Camera
from rendering.particles import Kind
from world.collision_map import TileCollision

if TYPE_CHECKING:
    from entities.player import Player
    from objects.rings import Ring
    from world.world import World

AFTERIMAGE_INTERVAL = 0.022
AFTERIMAGE_LIFE = 0.22
DASH_TINT = (70, 150, 255)
POUND_TINT = (255, 170, 60)
SLIDE_RECOVERY = 0.12


class _Afterimage:
    __slots__ = ("image", "x", "y", "age")

    def __init__(self, image: pygame.Surface, x: float, y: float) -> None:
        self.image = image
        self.x = x
        self.y = y
        self.age = 0.0


def _tinted(image: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
    ghost = image.copy()
    ghost.fill((40, 40, 40), special_flags=pygame.BLEND_RGB_MULT)
    ghost.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
    return ghost


class PlayerMoves:
    """Mixin for Player. Relies on Player's body, physics, intent and state."""

    def _init_moves(self: "Player") -> None:
        if not hasattr(self, "locked_moves"):
            # Moves a level hasn't taught yet (map property "locked_moves").
            self.locked_moves: frozenset[str] = frozenset()
        self.dash_charges = self.physics.dash_charges
        self._dash_timer = 0.0
        self._dash_cooldown = 0.0
        self._dash_buffer_timer = 0.0
        self._dash_delay_timer = 0.0
        self._queued_dash_dir = pygame.Vector2(1, 0)
        self._dash_dir = pygame.Vector2(1, 0)
        self._slide_timer = 0.0
        self._slide_recovery = 0.0
        self._pound_timer = 0.0
        self._pound_falling = False
        self._gliding = False
        self._ring: "Ring | None" = None
        self._ring_cooldown = 0.0
        self._afterimages: list[_Afterimage] = []
        self._afterimage_timer = 0.0
        self._glide_time = 0.0

    def _reset_moves(self: "Player") -> None:
        self._restore_height(force=True)
        if self._ring is not None:
            self._ring.release()
        self._init_moves()
        self._jump_buffer_timer = self._jump_min_hold_timer = self._coyote_timer = 0.0
        self._wall_timer = self._wall_lock_timer = 0.0
        self._wall_side = self._last_wall_side = 0
        self._jump_cuttable = False

    # --- queries ------------------------------------------------------------------
    @property
    def is_pounding(self: "Player") -> bool:
        from entities.player import PlayerState

        return self.state == PlayerState.POUND

    @property
    def is_dashing(self: "Player") -> bool:
        from entities.player import PlayerState

        return self.state == PlayerState.DASH

    @property
    def is_gliding(self: "Player") -> bool:
        from entities.player import PlayerState

        return self.state == PlayerState.GLIDE

    def refill_dash(self: "Player") -> bool:
        """Dash lanterns call this. Returns False if nothing was refilled."""
        if self.dash_charges >= self.physics.dash_charges:
            return False
        self.dash_charges = self.physics.dash_charges
        self._dash_cooldown = 0.0
        return True

    # --- dispatch -------------------------------------------------------------------
    def _update_moves_timers(self: "Player", dt: float) -> None:
        self._dash_cooldown = max(0.0, self._dash_cooldown - dt)
        self._ring_cooldown = max(0.0, self._ring_cooldown - dt)
        self._slide_recovery = max(0.0, self._slide_recovery - dt)
        for ghost in self._afterimages:
            ghost.age += dt
        self._afterimages = [ghost for ghost in self._afterimages if ghost.age < AFTERIMAGE_LIFE]

    def _update_special(self: "Player", dt: float, world: "World") -> bool:
        """Run the current special move. Returns True if it handled this step."""
        from entities.player import PlayerState

        match self.state:
            case PlayerState.DASH:
                self._update_dash(dt, world)
            case PlayerState.SLIDE:
                self._update_slide(dt, world)
            case PlayerState.POUND:
                self._update_pound(dt, world)
            case PlayerState.SWING:
                self._update_swing(dt, world)
            case _:
                return False
        return True

    def _try_start_moves(self: "Player", world: "World") -> bool:
        """Check the inputs that begin a move from normal movement."""
        intent = self.intent
        body = self.body
        if self._jump_buffer_timer > 0 and (self._coyote_timer > 0 or self._wall_timer > 0):
            return False  # resolve a requested jump before its queued dash
        if self._dash_buffer_timer > 0 and self._dash_delay_timer <= 0 and self._can_dash():
            self._start_dash(world)
            return True
        if (not body.on_ground and intent.down_pressed and "pound" not in self.locked_moves
                and self._height_above_ground(world) > 40):
            self._start_pound(world)
            return True
        running = abs(body.velocity.x) > self.physics.slide_min_speed
        if (body.on_ground and intent.down_pressed and running and self._slide_recovery <= 0
                and "slide" not in self.locked_moves):
            self._start_slide(world)
            return True
        if not body.on_ground and self._ring_cooldown <= 0 and "swing" not in self.locked_moves:
            ring = self._find_ring(world)
            if ring is not None:
                self._grab_ring(ring, world)
                return True
        return False

    # --- dash -------------------------------------------------------------------------
    def _buffer_dash_input(self: "Player", dt: float) -> None:
        self._dash_buffer_timer = max(0.0, self._dash_buffer_timer - dt)
        self._dash_delay_timer = max(0.0, self._dash_delay_timer - dt)
        if not self.intent.dash_pressed or "dash" in self.locked_moves:
            return
        self._dash_buffer_timer = self.physics.dash_buffer_time
        self._queued_dash_dir = self._aim_dash()
        # Preserve both actions when the buttons are pressed together.
        jumping = self._jump_buffer_timer > 0 and (self._coyote_timer > 0 or self._wall_timer > 0)
        self._dash_delay_timer = self.physics.jump_dash_delay if jumping else 0.0

    def _aim_dash(self: "Player") -> pygame.Vector2:
        intent = self.intent
        dx = float(intent.move_axis)
        dy = -1.0 if intent.up_held else (1.0 if intent.down_held and not self.body.on_ground else 0.0)
        if dx == 0 and dy == 0:
            dx = float(self.facing)
        return pygame.Vector2(dx, dy).normalize()

    def _can_dash(self: "Player") -> bool:
        if "dash" in self.locked_moves:
            return False
        return self._dash_cooldown <= 0 and (self.body.on_ground or self.dash_charges > 0)

    def _start_dash(self: "Player", world: "World") -> None:
        from entities.player import PlayerState

        direction = self._queued_dash_dir.copy() if self._dash_buffer_timer > 0 else self._aim_dash()
        self._dash_buffer_timer = self._dash_delay_timer = 0.0
        self._dash_dir = direction
        if direction.x:
            self.facing = 1 if direction.x > 0 else -1
        if not self.body.on_ground:
            self.dash_charges -= 1
        self._restore_height(force=False)
        self._gliding = False
        self._jump_cuttable = False
        self._dash_timer = self.physics.dash_time
        self._dash_cooldown = self.physics.dash_cooldown
        self.body.velocity.update(direction * self.physics.dash_speed)
        self.body.ground_platform = None
        self._set_state(PlayerState.DASH)
        self._stretch(1.0)
        self._scale = 0.8  # squash toward the dash, the spring stretches back
        emitters.shockwave(world.particles, self.body.centerx, self.body.centery, 36, (170, 220, 255))
        world.events.emit(EventType.PLAYER_DASHED, self.body.midbottom)

    def _update_dash(self: "Player", dt: float, world: "World") -> None:
        p = self.physics
        self._dash_timer -= dt
        direction = self._dash_dir
        self.body.velocity.update(direction * p.dash_speed)
        result = move_body(self.body, dt, world.collision, world.platforms)
        self._spawn_afterimage(dt, DASH_TINT)
        if world.particles.rng.random() < 0.6:
            emitters.magic_trail(world.particles, self.body.centerx, self.body.centery, (150, 210, 255))
        self._strike_enemies(world, self.rect.inflate(10, 6), 1 if direction.x >= 0 else -1)

        blocked = False
        if self.body.hit_wall:
            cells = self._cells_beside(world, self.body.hit_wall)
            if world.smash_blocks(cells, "dash", self):
                # Punched straight through: keep going at full speed.
                self.body.velocity.update(direction * p.dash_speed)
            else:
                blocked = True
        if result.ceiling_cells:
            if not world.smash_blocks(result.ceiling_cells, "dash", self):
                world.bump_blocks(result.ceiling_cells, self)
                blocked = True
        if self.body.on_ground and direction.y > 0:
            blocked = True
        if self._dash_timer <= 0 or blocked:
            self._end_dash()

    def _end_dash(self: "Player") -> None:
        from entities.player import PlayerState

        direction = self._dash_dir
        p = self.physics
        self.body.velocity.x = direction.x * max(p.dash_end_speed, p.max_run_speed)
        self.body.velocity.y = direction.y * p.dash_end_speed if direction.y < 0 else max(0.0, direction.y * 200)
        self._set_state(PlayerState.FALLING if not self.body.on_ground else PlayerState.RUNNING)

    # --- slide ----------------------------------------------------------------------------
    def _start_slide(self: "Player", world: "World") -> None:
        from entities.player import PlayerState

        p = self.physics
        direction = 1 if self.body.velocity.x > 0 else -1
        self.facing = direction
        self._set_height(p.slide_height)
        self.body.velocity.x = direction * max(abs(self.body.velocity.x), p.slide_speed)
        self._slide_timer = 0.0
        self._set_state(PlayerState.SLIDE)
        emitters.skid_dust(world.particles, self.body.centerx, self.body.bottom, -direction, world.dust_color)
        world.events.emit(EventType.PLAYER_SLID, self.body.midbottom)

    def _update_slide(self: "Player", dt: float, world: "World") -> None:
        p = self.physics
        self._slide_timer += dt
        direction = 1 if self.body.velocity.x >= 0 else -1
        can_stand = self._can_stand(world)
        speed = approach(abs(self.body.velocity.x), 0.0, p.slide_friction * dt)
        if not can_stand:
            speed = max(speed, 130.0)  # squeeze through low gaps
        self.body.velocity.x = direction * speed
        apply_gravity(self.body, p.gravity, p.terminal_velocity, dt)
        move_body(self.body, dt, world.collision, world.platforms)
        self._strike_enemies(world, self.rect.inflate(8, 8), direction)
        if self.body.hit_wall:
            cells = self._cells_beside(world, self.body.hit_wall)
            if world.smash_blocks(cells, "slide", self):
                self.body.velocity.x = direction * speed
        if self.body.on_ground and int(self._slide_timer * 30) % 2 == 0:
            emitters.run_dust(world.particles, self.body.centerx - direction * 8, self.body.bottom, -direction,
                              world.dust_color)

        # Recheck at the new position: a press just before leaving a low
        # ceiling should launch as soon as there is room to stand.
        can_stand = self._can_stand(world)
        if self._jump_buffer_timer > 0 and can_stand:
            # Slide jump: a long, low leap that keeps the slide's speed.
            self._finish_slide()
            self.body.velocity.x = direction * max(speed, p.slide_jump_speed)
            self.body.velocity.y = -p.jump_velocity * 0.86
            self._consume_jump()
            self._stretch(1.2)
            emitters.jump_puff(world.particles, self.body.centerx, self.body.bottom, world.dust_color)
            world.events.emit(EventType.PLAYER_JUMPED, self.body.midbottom)
            return
        if not self.body.on_ground and can_stand:
            self._finish_slide()
            return
        stopped = speed < 70 or self._slide_timer > p.slide_max_time or self.body.hit_wall
        if stopped and can_stand:
            self._finish_slide()

    def _finish_slide(self: "Player") -> None:
        from entities.player import PlayerState

        self._restore_height(force=False)
        self._slide_recovery = SLIDE_RECOVERY
        self._set_state(PlayerState.RUNNING if self.body.on_ground else PlayerState.FALLING)

    # --- ground pound ---------------------------------------------------------------------
    def _start_pound(self: "Player", world: "World") -> None:
        from entities.player import PlayerState

        self._restore_height(force=False)
        self._gliding = False
        self._pound_timer = self.physics.pound_windup
        self._pound_falling = False
        self.body.velocity.update(0, 0)
        self._set_state(PlayerState.POUND)
        self._animator.play("pound", restart=True)

    def _update_pound(self: "Player", dt: float, world: "World") -> None:
        p = self.physics
        if not self._pound_falling:
            self._pound_timer -= dt
            self.body.velocity.update(0, 0)
            if self._pound_timer <= 0:
                self._pound_falling = True
                self.body.velocity.y = p.pound_speed
            return
        self.body.velocity.x = 0.0
        self.body.velocity.y = p.pound_speed
        move_body(self.body, dt, world.collision, world.platforms)
        self._spawn_afterimage(dt, POUND_TINT)
        if self.body.on_ground:
            cells = self._cells_below(world)
            if world.smash_blocks(cells, "pound", self):
                # Crashed through: keep plunging.
                self.body.on_ground = False
                emitters.debris(world.particles, self.body.centerx, self.body.bottom, ((200, 160, 110),), 6, 0.8)
                return
            self._land_pound(world)

    def _land_pound(self: "Player", world: "World") -> None:
        from entities.player import PlayerState

        p = self.physics
        x, y = self.body.centerx, self.body.bottom
        area = pygame.Rect(0, 0, round(p.pound_radius * 2), 44)
        area.midbottom = (round(x), round(y) + 4)
        for enemy in world.enemies:
            if enemy.alive and enemy.is_dangerous and enemy.rect.colliderect(area):
                enemy.on_slashed(world, 1 if enemy.body.centerx >= x else -1)
        world.press_plates(pygame.Rect(round(x) - 12, round(y) - 4, 24, 12))
        emitters.landing_dust(world.particles, x, y, 1.0, world.dust_color)
        emitters.shockwave(world.particles, x, y - 4, p.pound_radius, (255, 230, 180))
        emitters.debris(world.particles, x, y, (world.dust_color,), 10, 0.9)
        world.events.emit(EventType.PLAYER_POUNDED, (x, y), 1)
        self._squash(0.55)
        self.body.velocity.y = -p.pound_bounce
        self._jump_cuttable = False
        self._set_state(PlayerState.JUMPING)
        if world.boss is not None:
            # Notify after the normal landing response so a successful stun
            # can supply its own rebound without being overwritten here.
            world.boss.hit_by_pound(area, world)

    def end_pound(self: "Player") -> None:
        """A stomp or drum interrupted the plunge."""
        from entities.player import PlayerState

        if self.state == PlayerState.POUND:
            self._set_state(PlayerState.JUMPING)

    # --- glide ------------------------------------------------------------------------------
    def _update_glide_input(self: "Player", world: "World") -> None:
        """Called from the jump update: a mid-air press (no jump available) opens the shawl."""
        if self.body.on_ground:
            self._gliding = False
            return
        if (self.intent.jump_pressed and self._coyote_timer <= 0 and self._wall_timer <= 0
                and "glide" not in self.locked_moves):
            if not self._gliding:
                world.events.emit(EventType.PLAYER_GLIDED, self.body.midbottom)
            self._gliding = True
        if not self.intent.jump_held:
            self._gliding = False

    def _glide_gravity(self: "Player", dt: float, world: "World") -> bool:
        """Apply glide physics. Returns True if gliding handled vertical speed."""
        if not self._gliding:
            return False
        p = self.physics
        lift = world.updraft_at(self.body.centerx, self.body.centery)
        if self.body.velocity.y < -40 and lift <= 0:
            return False  # still rising from the jump: normal gravity
        if lift > 0:
            target = -min(p.glide_updraft_speed, lift)
            self.body.velocity.y = approach(self.body.velocity.y, target, 1400 * dt)
            if world.particles.rng.random() < 0.3:
                emitters.magic_trail(world.particles, self.body.centerx, self.body.bottom, (220, 240, 255))
        else:
            self.body.velocity.y = approach(self.body.velocity.y + p.gravity * 0.25 * dt, p.glide_fall_speed, 2200 * dt)
        return True

    # --- swing rings ------------------------------------------------------------------------
    def _hand_point(self: "Player") -> tuple[float, float]:
        return self.body.centerx, self.body.top - 6

    def _find_ring(self: "Player", world: "World") -> "Ring | None":
        hx, hy = self._hand_point()
        best = None
        best_distance = 26.0
        for ring in world.rings:
            if not ring.can_grab:
                continue
            rx, ry = ring.position
            distance = math.hypot(rx - hx, ry - hy)
            if distance < best_distance:
                best, best_distance = ring, distance
        return best

    def _grab_ring(self: "Player", ring: "Ring", world: "World") -> None:
        from entities.player import PlayerState

        self._ring = ring
        self._gliding = False
        self._restore_height(force=False)
        ring.grab(pygame.Vector2(self.body.velocity))
        self.dash_charges = self.physics.dash_charges
        self._set_state(PlayerState.SWING)
        emitters.sparkle_burst(world.particles, *ring.position, (255, 220, 140), 6, 80)
        world.events.emit(EventType.RING_GRABBED, ring.position)

    def _update_swing(self: "Player", dt: float, world: "World") -> None:
        ring = self._ring
        if ring is None:
            from entities.player import PlayerState

            self._set_state(PlayerState.FALLING)
            return
        p = self.physics
        axis = self.intent.move_axis
        ring.pump(dt, axis, p.swing_gravity, p.swing_pump)
        if axis:
            self.facing = axis
        elif abs(ring.angular_velocity) > 0.2:
            self.facing = 1 if ring.angular_velocity > 0 else -1
        # Follow the ring through normal collision, so walls stop the swing.
        hx, hy = ring.position
        target_x = hx - self.body.width / 2
        target_y = hy + 4
        self.body.velocity.update((target_x - self.body.x) / dt, (target_y - self.body.y) / dt)
        move_body(self.body, dt, world.collision)
        if self.body.hit_wall or self.body.hit_ceiling or self.body.on_ground:
            ring.bonk()
        self.body.velocity.update(ring.velocity)

        if self._jump_buffer_timer > 0:
            self._jump_buffer_timer = 0.0
            self._release_ring(world, boost=True)
        elif self.intent.down_pressed:
            self._release_ring(world, boost=False)
        elif self._dash_buffer_timer > 0 and self._can_dash():
            self._release_ring(world, boost=False)
            self._start_dash(world)

    def _release_ring(self: "Player", world: "World", boost: bool) -> None:
        from entities.player import PlayerState

        ring = self._ring
        if ring is None:
            return
        velocity = pygame.Vector2(ring.velocity) * self.physics.swing_release_scale
        if boost:
            velocity.y = min(velocity.y, 0.0) - self.physics.swing_release_boost
            self._stretch(1.25)
        self.body.velocity.update(velocity)
        ring.release()
        self._ring = None
        self._ring_cooldown = self.physics.swing_regrab_time
        self._jump_cuttable = False
        self._set_state(PlayerState.JUMPING if velocity.y < 0 else PlayerState.FALLING)
        world.events.emit(EventType.RING_RELEASED, self.body.midbottom)

    # --- shared helpers -----------------------------------------------------------------------
    def _strike_enemies(self: "Player", world: "World", area: pygame.Rect, direction: int) -> None:
        for enemy in world.enemies:
            if enemy.alive and enemy.is_dangerous and area.colliderect(enemy.rect):
                enemy.on_slashed(world, direction)
        if world.boss is not None:
            world.boss.hit_by_move(area, world, direction)

    def _cells_beside(self: "Player", world: "World", side: int) -> list[tuple[int, int]]:
        body = self.body
        size = world.collision.tile_size
        x = body.right + 1 if side > 0 else body.left - 1
        tx = math.floor(x / size)
        return [(tx, ty) for ty in range(math.floor(body.top / size), math.floor((body.bottom - 0.01) / size) + 1)]

    def _cells_below(self: "Player", world: "World") -> list[tuple[int, int]]:
        body = self.body
        size = world.collision.tile_size
        ty = math.floor((body.bottom + 1) / size)
        return [(tx, ty) for tx in range(math.floor(body.left / size), math.floor((body.right - 0.01) / size) + 1)]

    def _height_above_ground(self: "Player", world: "World") -> float:
        collision = world.collision
        size = collision.tile_size
        start = math.floor(self.body.bottom / size)
        for ty in range(start, start + 3):
            for tx in (math.floor(self.body.left / size), math.floor((self.body.right - 0.01) / size)):
                if collision.get(tx, ty) != TileCollision.EMPTY:
                    return ty * size - self.body.bottom
        return 999.0

    def _set_height(self: "Player", height: float) -> None:
        bottom = self.body.bottom
        self.body.height = height
        self.body.y = bottom - height

    def _can_stand(self: "Player", world: "World") -> bool:
        full = self.physics.hitbox_height
        body = self.body
        top = body.bottom - full
        for _tx, _ty, kind in world.collision.cells_overlapping(body.left, top, body.right, body.bottom):
            if kind == TileCollision.SOLID:
                return False
        return True

    def _restore_height(self: "Player", force: bool) -> None:
        if self.body.height != self.physics.hitbox_height:
            self._set_height(self.physics.hitbox_height)

    def _spawn_afterimage(self: "Player", dt: float, tint: tuple[int, int, int]) -> None:
        self._afterimage_timer -= dt
        if self._afterimage_timer > 0:
            return
        self._afterimage_timer = AFTERIMAGE_INTERVAL
        image = _tinted(self._animator.image(flip_x=self.facing < 0), tint)
        self._afterimages.append(_Afterimage(image, *self.body.midbottom))

    # --- drawing -------------------------------------------------------------------------------
    def _draw_afterimages(self: "Player", surface: pygame.Surface, camera: Camera) -> None:
        for ghost in self._afterimages:
            fade = 1.0 - ghost.age / AFTERIMAGE_LIFE
            ghost.image.set_alpha(round(150 * fade))
            x, y = camera.to_screen(ghost.x, ghost.y)
            surface.blit(ghost.image, ghost.image.get_rect(midbottom=(x, y)), special_flags=0)

    def _draw_glide_shawl(self: "Player", surface: pygame.Surface, camera: Camera) -> None:
        """A billowing shawl held overhead like a sail."""
        from entities.player import PlayerState

        if self.state != PlayerState.GLIDE:
            return
        self._glide_time += 1 / 60
        palette = self._palette()
        cx, top = camera.to_screen(self.body.centerx, self.body.top)
        t = self._glide_time
        width = 46
        lift = 14
        points_top = []
        points_bottom = []
        for k in range(9):
            u = k / 8
            x = cx - width / 2 + u * width - self.body.velocity.x * 0.02
            ripple = math.sin(t * 14 + u * 6) * 2.2
            arch = math.sin(u * math.pi) * lift
            points_top.append((x, top - 8 - arch + ripple))
            points_bottom.append((x, top - 2 - arch * 0.55 + ripple * 0.6))
        polygon = points_top + points_bottom[::-1]
        pygame.draw.polygon(surface, palette.scarf, polygon)
        pygame.draw.lines(surface, palette.scarf_tip, False, points_top, 2)
        for k in (2, 4, 6):
            pygame.draw.line(surface, (40, 24, 26), points_bottom[k], points_top[k], 1)
        # The hands holding the corners.
        for end in (points_bottom[0], points_bottom[-1]):
            pygame.draw.circle(surface, (236, 188, 150), (round(end[0]), round(end[1]) + 2), 3)

    def _draw_held_ring(self: "Player", surface: pygame.Surface, camera: Camera) -> None:
        ring = self._ring
        if ring is None:
            return
        x, y = camera.to_screen(*ring.position)
        # Two fists gripping the ring, drawn over the head.
        pygame.draw.circle(surface, (90, 56, 20), (x, y), 8, 4)
        pygame.draw.circle(surface, (236, 184, 64), (x, y), 7, 3)
        for dx in (-5, 5):
            pygame.draw.circle(surface, (42, 24, 26), (x + dx, y + 5), 4)
            pygame.draw.circle(surface, (236, 188, 150), (x + dx, y + 5), 3)

    def _update_scarf_charge(self: "Player") -> None:
        """The scarf pales when the air dash is spent, like a drained lamp."""
        palette = self._palette()
        spent = self.dash_charges <= 0 and not self.body.on_ground
        if spent != getattr(self, "_scarf_spent", False):
            self._scarf_spent = spent
            if spent:
                self.scarf.set_colors((150, 170, 200), (220, 230, 245))
            else:
                self.scarf.set_colors(palette.scarf, palette.scarf_tip)

    def _glide_particles(self: "Player", world: "World") -> None:
        if world.particles.rng.random() < 0.25:
            rng = world.particles.rng
            world.particles.spawn(self.body.centerx + rng.uniform(-20, 20), self.body.top - 10,
                                  rng.uniform(-10, 10), rng.uniform(-30, -10), life=0.6, kind=Kind.PETAL,
                                  size=1.6, color=(255, 240, 220), wobble=30, front=False)
