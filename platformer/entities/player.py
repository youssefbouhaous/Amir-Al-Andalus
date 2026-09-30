"""The player: platformer physics plus an explicit state machine.

State is a single enum instead of a pile of booleans (is_jumping, is_dead,
is_in_pipe...). Each update does exactly one thing depending on the state,
and the animation is chosen from the state plus a few short-lived poses
(skidding, throwing, hurt).

On top of the physics sits the "juice": squash and stretch on jumps and
landings (a damped spring on the sprite's scale), dust at the feet, and the
simulated turban tail.
"""

import math
from collections.abc import Mapping
from enum import Enum, IntEnum, auto
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.events import EventType
from core.settings import PLAYER_PHYSICS, PlayerPhysics
from entities.entity import Entity
from entities.player_controller import PlayerIntent
from entities.player_moves import PlayerMoves
from entities.scarf import Scarf
from physics.body import Body
from physics.collision import apply_gravity, approach, move_body
from rendering import emitters
from rendering.animation import Animation, Animator
from rendering.art import prince
from rendering.camera import Camera
from rendering.lighting import Light

if TYPE_CHECKING:
    from objects.triggers import Door
    from world.world import World


class PlayerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    JUMPING = auto()
    FALLING = auto()
    WALL_SLIDE = auto()
    DEAD = auto()
    ENTERING_DOOR = auto()
    EXITING_DOOR = auto()
    VICTORY = auto()
    DASH = auto()
    SLIDE = auto()
    POUND = auto()
    GLIDE = auto()
    SWING = auto()


class PowerLevel(IntEnum):
    NONE = 0
    POMEGRANATE = 1  # golden robe: two hits, breaks bricks
    STAR = 2         # midnight robe: also throws stars


CONTROLLABLE_STATES = frozenset(
    {PlayerState.IDLE, PlayerState.RUNNING, PlayerState.JUMPING, PlayerState.FALLING, PlayerState.WALL_SLIDE,
     PlayerState.DASH, PlayerState.SLIDE, PlayerState.POUND, PlayerState.GLIDE, PlayerState.SWING}
)

# Squash-and-stretch spring (stiffness, damping): one visible wobble.
SPRING_STIFFNESS = 260.0
SPRING_DAMPING = 15.0
JUMP_STRETCH = 1.24
HURT_POSE_TIME = 0.35
SIT_DELAY = 0.7
RUN_DUST_INTERVAL = 0.11
WALL_DUST_INTERVAL = 0.06
SKID_SPEED = 110.0

_ANCHORS: dict[tuple[str, int], tuple[float, float]] = {}


def _anchor(animation: str, frame: int, frame_count: int) -> tuple[float, float]:
    key = (animation, frame)
    value = _ANCHORS.get(key)
    if value is None:
        value = prince.turban_anchor(animation, frame, frame_count)
        _ANCHORS[key] = value
    return value


class Player(PlayerMoves, Entity):
    def __init__(
        self,
        midbottom: tuple[float, float],
        animation_sets: Mapping[PowerLevel, Mapping[str, Animation]],
        power: PowerLevel = PowerLevel.NONE,
        physics: PlayerPhysics = PLAYER_PHYSICS,
    ) -> None:
        super().__init__()
        self.physics = physics
        self.body = Body.from_midbottom(midbottom, physics.hitbox_width, physics.hitbox_height)
        self.state = PlayerState.IDLE
        self.facing = 1
        self.power = PowerLevel(power)
        self.intent = PlayerIntent()
        # Bottom edge before this step's movement; used to detect stomps.
        self.previous_bottom = self.body.bottom
        self.door: "Door | None" = None
        self.stomp_combo = 0

        self._animation_sets = animation_sets
        self._animator = Animator(self._animation_set(), "idle")
        self._state_time = 0.0
        self._coyote_timer = 0.0
        self._jump_buffer_timer = 0.0
        self._jump_min_hold_timer = 0.0
        # True while rising from a jump that can still be cut short.
        self._jump_cuttable = False
        self._invulnerable_timer = 0.0
        self._death_bounced = False
        self._wall_side = 0
        self._last_wall_side = 0
        self._wall_timer = 0.0
        self._wall_lock_timer = 0.0
        self._throw_cooldown = 0.0
        self._throw_timer = 0.0
        self._attack_timer = 0.0
        self._attack_facing = 1
        self._hurt_timer = 0.0
        self._idle_time = 0.0
        self._fall_speed = 0.0
        self._lift: tuple[float, float] | None = None
        self._scale = 1.0
        self._scale_velocity = 0.0
        self._dust_timer = 0.0
        self._was_on_ground = True
        palette = self._palette()
        self.scarf = Scarf(self._scarf_anchor(), palette.scarf, palette.scarf_tip)
        self._init_moves()

    # --- Queries ----------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect()

    @property
    def powered(self) -> bool:
        return self.power > PowerLevel.NONE

    @property
    def is_controllable(self) -> bool:
        return self.state in CONTROLLABLE_STATES

    @property
    def can_be_hurt(self) -> bool:
        return self.is_controllable and self._invulnerable_timer <= 0

    @property
    def attack_facing(self) -> int:
        return self._attack_facing

    @property
    def attack_rect(self) -> pygame.Rect | None:
        if not self.is_controllable or self._attack_timer <= 0:
            return None
        x = self.body.centerx
        if self._attack_facing < 0:
            x -= settings.MELEE_REACH
        return pygame.Rect(round(x), round(self.body.top - 4), settings.MELEE_REACH,
                           round(self.body.height + 1))

    def protect_on_spawn(self) -> None:
        self._invulnerable_timer = settings.SPAWN_PROTECTION_TIME

    @property
    def death_finished(self) -> bool:
        return self.state == PlayerState.DEAD and self._state_time >= self.physics.death_duration

    @property
    def door_entered(self) -> bool:
        return (
            self.state == PlayerState.ENTERING_DOOR
            and self._state_time >= self.physics.door_enter_duration
        )

    @property
    def victory_finished(self) -> bool:
        return self.state == PlayerState.VICTORY and self._state_time >= self.physics.victory_duration

    @property
    def state_time(self) -> float:
        return self._state_time

    # --- Commands from the world / interactions ---------------------------------
    def bounce(self) -> None:
        """Called after stomping an enemy. Holding jump bounces higher."""
        self.end_pound()
        held = self.intent.jump_held
        speed = (
            self.physics.stomp_bounce_held_velocity if held else self.physics.stomp_bounce_velocity
        )
        self.body.velocity.y = -speed
        self._jump_cuttable = held
        self._stretch(1.18)

    def spring_bounce(self) -> None:
        """Launched by a drum: holding jump goes much higher, and can't be cut.

        Pounding onto a drum is the strongest launch of all."""
        held = self.intent.jump_held
        self.body.velocity.y = -(self.physics.spring_held_velocity if held else self.physics.spring_velocity)
        if self.is_pounding:
            self.body.velocity.y = -self.physics.pound_drum_velocity
            self.end_pound()
        self._gliding = False
        self.body.ground_platform = None
        self._jump_cuttable = False
        self._coyote_timer = 0.0
        self._stretch(1.34)

    def apply_lift(self, target_speed: float, acceleration: float) -> None:
        """Rising air or water (fountains): steer vertical speed toward ``target_speed``."""
        self._lift = (target_speed, acceleration)
        self._jump_cuttable = False

    def take_damage(self, world: "World") -> None:
        if not self.can_be_hurt:
            return
        if self.power > PowerLevel.NONE:
            self._set_power(PowerLevel(self.power - 1))
            self._invulnerable_timer = self.physics.hurt_invulnerability_time
            self._hurt_timer = HURT_POSE_TIME
            world.events.emit(EventType.PLAYER_HURT, self.body.midbottom, int(self.power))
        else:
            self.die(world)

    def die(self, world: "World", fell: bool = False) -> None:
        if self.state == PlayerState.DEAD:
            return
        self._reset_moves()
        self._set_state(PlayerState.DEAD)
        self._set_power(PowerLevel.NONE)
        self.body.velocity.update(0, 0)
        # Falling into a pit skips the hop: the player is already off screen.
        self._death_bounced = fell
        self._invulnerable_timer = 0.0
        world.events.emit(EventType.PLAYER_DIED, self.body.midbottom, "fell" if fell else "hit")

    def power_up(self, world: "World", level: PowerLevel = PowerLevel.POMEGRANATE) -> None:
        # A pomegranate never downgrades the star robe.
        new_level = max(self.power, level) if level == PowerLevel.POMEGRANATE else level
        self._set_power(PowerLevel(new_level))
        self._stretch(1.3)
        world.events.emit(EventType.PLAYER_POWERED_UP, self.body.midbottom, int(new_level))

    def enter_door(self, door: "Door") -> None:
        self._reset_moves()
        self.door = door
        self.body.velocity.update(0, 0)
        self._set_state(PlayerState.ENTERING_DOOR)

    def arrive_at(self, midbottom: tuple[float, float]) -> None:
        self.body.place_midbottom(midbottom)
        self.body.velocity.update(0, 0)
        self.body.clear_contacts()
        self.previous_bottom = self.body.bottom
        self._attack_timer = self._throw_timer = self._throw_cooldown = 0.0
        self._reset_moves()
        self.door = None
        self._set_state(PlayerState.IDLE)
        self.scarf.reset(self._scarf_anchor(), self.facing)

    def emerge_from(self, door: "Door") -> None:
        """Rise out of a well (or fade in at a doorway) after a warp."""
        self.arrive_at(door.arrival_point)
        self.door = door
        self._set_state(PlayerState.EXITING_DOOR)

    def celebrate(self) -> None:
        self._set_state(PlayerState.VICTORY)

    # --- Update -------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self._state_time += dt
        self._invulnerable_timer = max(0.0, self._invulnerable_timer - dt)
        self._throw_cooldown = max(0.0, self._throw_cooldown - dt)
        self._throw_timer = max(0.0, self._throw_timer - dt)
        self._attack_timer = max(0.0, self._attack_timer - dt)
        self._hurt_timer = max(0.0, self._hurt_timer - dt)
        self._wall_lock_timer = max(0.0, self._wall_lock_timer - dt)
        self._update_moves_timers(dt)
        self.previous_bottom = self.body.bottom

        match self.state:
            case PlayerState.DEAD:
                self._update_dead(dt)
            case PlayerState.ENTERING_DOOR:
                if self.door is None or self.door.enter_direction != "up":
                    self.body.y += self.physics.door_sink_speed * dt
            case PlayerState.EXITING_DOOR:
                if self._state_time >= self.physics.door_exit_duration:
                    self.door = None
                    self._set_state(PlayerState.IDLE)
            case PlayerState.VICTORY:
                self._update_victory(dt, world)
            case _:
                self._update_controlled(dt, world)

        self._lift = None
        self.body.external.update(0, 0)
        self._update_spring(dt)
        self._update_animation(dt)
        self._update_scarf_charge()
        wind = world.wind_at(self.body.centerx, self.body.centery) if hasattr(world, "wind_at") else 0.0
        self.scarf.update(dt, self._scarf_anchor(), self.facing, wind * 1.5 - self.body.velocity.x * 0.8)

    def _update_controlled(self, dt: float, world: "World") -> None:
        # Capture presses even while a special move owns the simulation.
        self._buffer_movement_inputs(dt)
        if self._update_special(dt, world):
            return
        if self._try_start_moves(world):
            return
        self._update_horizontal(dt)
        self._update_jump(dt, world)
        if self._lift is not None or not self._glide_gravity(dt, world):
            self._apply_gravity(dt)
        self._update_throw(world)

        falling_speed = self.body.velocity.y
        result = move_body(self.body, dt, world.collision, world.platforms)
        if result.ceiling_cells:
            world.bump_blocks(result.ceiling_cells, self)
        if self.body.on_ground or self.body.hit_ceiling:
            self._jump_cuttable = False
        self._update_wall_contact(dt, world)
        self._update_landing(falling_speed, world)
        self._emit_movement_dust(dt, world)
        self._set_state(self._movement_state())

    def _update_horizontal(self, dt: float) -> None:
        p = self.physics
        if self._wall_lock_timer > 0:
            return  # just wall-jumped: keep the kick-off speed for a moment
        axis = self.intent.move_axis
        on_ground = self.body.on_ground
        velocity_x = self.body.velocity.x

        if axis:
            self.facing = axis
            turning = velocity_x * axis < 0
            top_speed = p.glide_run_speed if self._gliding and not on_ground else p.max_run_speed
            if on_ground:
                acceleration = p.turn_acceleration if turning else p.ground_acceleration
            else:
                acceleration = p.air_turn_acceleration if turning else p.air_acceleration
            if abs(velocity_x) > top_speed and velocity_x * axis > 0:
                # Keep dash/slide momentum; only air friction bleeds it off.
                velocity_x = approach(velocity_x, axis * top_speed, p.air_friction * dt)
            else:
                velocity_x = approach(velocity_x, axis * top_speed, acceleration * dt)
        else:
            friction = p.ground_friction if on_ground else p.air_friction
            velocity_x = approach(velocity_x, 0.0, friction * dt)

        self.body.velocity.x = velocity_x

    def _buffer_movement_inputs(self, dt: float) -> None:
        p = self.physics
        intent = self.intent
        self._jump_min_hold_timer = max(0.0, self._jump_min_hold_timer - dt)
        if self.body.on_ground and self.body.velocity.y >= 0:
            self._coyote_timer = p.coyote_time
        else:
            self._coyote_timer = max(0.0, self._coyote_timer - dt)
        self._wall_timer = max(0.0, self._wall_timer - dt)

        if intent.jump_pressed:
            self._jump_buffer_timer = p.jump_buffer_time
        else:
            self._jump_buffer_timer = max(0.0, self._jump_buffer_timer - dt)
        self._buffer_dash_input(dt)

    def _consume_jump(self) -> None:
        self._jump_buffer_timer = self._coyote_timer = self._wall_timer = 0.0
        self._jump_min_hold_timer = self.physics.jump_min_hold_time
        self._jump_cuttable = True
        self.body.on_ground = False
        self.body.ground_platform = None

    def _update_jump(self, dt: float, world: "World") -> None:
        p = self.physics
        intent = self.intent
        self._update_glide_input(world)

        if self._jump_buffer_timer > 0 and self._coyote_timer > 0:
            self.body.velocity.y = -p.jump_velocity
            self._consume_jump()
            self._stretch(JUMP_STRETCH)
            emitters.jump_puff(world.particles, self.body.centerx, self.body.bottom, world.dust_color)
            world.events.emit(EventType.PLAYER_JUMPED, self.body.midbottom)
        elif self._jump_buffer_timer > 0 and self._wall_timer > 0 and not self.body.on_ground:
            side = self._last_wall_side
            self.body.velocity.update(-side * p.wall_jump_velocity_x, -p.wall_jump_velocity_y)
            self.facing = -side
            self._consume_jump()
            self._wall_lock_timer = p.wall_jump_lock_time
            self._stretch(JUMP_STRETCH)
            wall_x = self.body.right if side > 0 else self.body.left
            emitters.wall_jump_burst(world.particles, wall_x, self.body.centery, side, world.dust_color)
            world.events.emit(EventType.PLAYER_WALL_JUMPED, self.body.midbottom, side)

        # Variable jump height: letting go early cuts the upward speed once.
        if self._jump_cuttable and not intent.jump_held and self._jump_min_hold_timer <= 0:
            self._jump_cuttable = False
            if self.body.velocity.y < 0:
                self.body.velocity.y *= p.jump_cut_multiplier

    def _apply_gravity(self, dt: float) -> None:
        p = self.physics
        if self._lift is not None:
            target, acceleration = self._lift
            self.body.velocity.y = approach(self.body.velocity.y, target, acceleration * dt)
            return
        gravity = p.gravity
        if self.body.velocity.y > 0:
            gravity *= p.fall_gravity_multiplier
        apply_gravity(self.body, gravity, p.terminal_velocity, dt)
        if self.state == PlayerState.WALL_SLIDE and self.body.velocity.y > p.wall_slide_speed:
            self.body.velocity.y = approach(self.body.velocity.y, p.wall_slide_speed, 5000 * dt)

    def _update_wall_contact(self, dt: float, world: "World") -> None:
        body = self.body
        self._wall_side = 0
        if not body.on_ground:
            for side in (-1, 1):
                if world.collision.solid_beside(body.left, body.top, body.right, body.bottom, side):
                    self._wall_side = side
                    break
        if self._wall_side:
            self._last_wall_side = self._wall_side
            self._wall_timer = self.physics.wall_coyote_time

    def _update_throw(self, world: "World") -> None:
        if not self.intent.attack_pressed or self._throw_cooldown > 0:
            return
        # Every robe can slash, on the ground or in the air. The star robe
        # adds a projectile; reaching its projectile cap never disables melee.
        self._attack_facing = self.facing
        self._attack_timer = settings.MELEE_DURATION
        self._throw_cooldown = settings.MELEE_COOLDOWN
        self._throw_timer = self.physics.throw_pose_time
        self._animator.play("throw", restart=True)
        hand = (self.body.centerx + self.facing * 12, self.body.top + 8)
        if self.power == PowerLevel.STAR and world.count_player_projectiles() < self.physics.max_projectiles:
            from entities.projectiles import StarProjectile

            world.spawn_projectile(StarProjectile(hand, self.facing, world.sprites))
            world.events.emit(EventType.STAR_THROWN, hand)
        else:
            world.events.emit(EventType.PLAYER_ATTACKED, hand)

    def _update_landing(self, falling_speed: float, world: "World") -> None:
        on_ground = self.body.on_ground
        if on_ground and not self._was_on_ground and falling_speed > 60:
            self.stomp_combo = 0
            strength = min(1.0, falling_speed / 900)
            if falling_speed > self.physics.hard_landing_speed:
                self._squash(1.0 - 0.32 * strength)
                emitters.landing_dust(world.particles, self.body.centerx, self.body.bottom, strength, world.dust_color)
            else:
                self._squash(1.0 - 0.14 * strength)
            world.events.emit(EventType.PLAYER_LANDED, self.body.midbottom, round(falling_speed))
        elif on_ground:
            self.stomp_combo = 0
        if on_ground and self.dash_charges < self.physics.dash_charges:
            self.dash_charges = self.physics.dash_charges
        self._was_on_ground = on_ground

    def _emit_movement_dust(self, dt: float, world: "World") -> None:
        self._dust_timer -= dt
        if self._dust_timer > 0:
            return
        body = self.body
        speed = abs(body.velocity.x)
        if body.on_ground and self._is_skidding():
            emitters.skid_dust(world.particles, body.centerx, body.bottom, self.facing, world.dust_color)
            self._dust_timer = 0.05
        elif body.on_ground and speed > self.physics.max_run_speed * 0.7:
            emitters.run_dust(world.particles, body.centerx, body.bottom, self.facing, world.dust_color)
            self._dust_timer = RUN_DUST_INTERVAL
        elif self.state == PlayerState.WALL_SLIDE:
            wall_x = body.right if self._wall_side > 0 else body.left
            emitters.wall_dust(world.particles, wall_x, body.top + 6, self._wall_side, world.dust_color)
            self._dust_timer = WALL_DUST_INTERVAL

    def _is_skidding(self) -> bool:
        axis = self.intent.move_axis
        return axis != 0 and self.body.velocity.x * axis < 0 and abs(self.body.velocity.x) > SKID_SPEED

    def _movement_state(self) -> PlayerState:
        body = self.body
        if not body.on_ground:
            sliding = (
                self._wall_side != 0
                and self.intent.move_axis == self._wall_side
                and body.velocity.y > 0
                and self._wall_lock_timer <= 0
            )
            if sliding:
                self.facing = self._wall_side
                return PlayerState.WALL_SLIDE
            if self._gliding and (body.velocity.y >= -40 or not self._jump_cuttable):
                return PlayerState.GLIDE
            return PlayerState.JUMPING if body.velocity.y < 0 else PlayerState.FALLING
        if abs(body.velocity.x) > self.physics.idle_speed_threshold or self.intent.move_axis:
            return PlayerState.RUNNING
        return PlayerState.IDLE

    def _update_dead(self, dt: float) -> None:
        p = self.physics
        if self._state_time < p.death_freeze_time:
            return
        if not self._death_bounced:
            self._death_bounced = True
            self.body.velocity.y = -p.death_bounce_velocity
        # No collision while dying: the body falls straight off the screen.
        apply_gravity(self.body, p.gravity, p.terminal_velocity, dt)
        self.body.y += self.body.velocity.y * dt

    def _update_victory(self, dt: float, world: "World") -> None:
        p = self.physics
        self.body.velocity.x = approach(self.body.velocity.x, 0.0, p.ground_friction * dt)
        self._apply_gravity(dt)
        move_body(self.body, dt, world.collision, world.platforms)

    # --- Animation ------------------------------------------------------------------
    def _animation_name(self) -> str:
        state = self.state
        vy = self.body.velocity.y
        if state == PlayerState.DEAD:
            return "death"
        if state in (PlayerState.ENTERING_DOOR, PlayerState.EXITING_DOOR):
            return "door"
        if state == PlayerState.VICTORY:
            return "victory"
        special = {
            PlayerState.DASH: "dash", PlayerState.SLIDE: "slide", PlayerState.POUND: "pound",
            PlayerState.GLIDE: "glide", PlayerState.SWING: "hang",
        }.get(state)
        if special is not None:
            return special
        if self._hurt_timer > 0:
            return "hurt"
        if self._throw_timer > 0:
            return "throw"
        if state == PlayerState.WALL_SLIDE:
            return "wall_slide"
        if state == PlayerState.JUMPING:
            return "jump" if vy < -170 else "apex"
        if state == PlayerState.FALLING:
            return "apex" if vy < 170 else "fall"
        if state == PlayerState.RUNNING:
            return "skid" if self._is_skidding() else "run"
        platform = self.body.ground_platform
        if platform is not None and getattr(platform, "is_carpet", False) and self._idle_time > SIT_DELAY:
            return "sit"
        return "idle"

    def _update_animation(self, dt: float) -> None:
        self._idle_time = self._idle_time + dt if self.state == PlayerState.IDLE else 0.0
        name = self._animation_name()
        self._animator.play(name)
        speed = 1.0
        if name == "run":
            speed = max(
                self.physics.min_run_animation_speed,
                abs(self.body.velocity.x) / self.physics.max_run_speed,
            )
        self._animator.update(dt, speed)
        if name == "hang" and self._ring is not None:
            # Pick the frame from the swing angle instead of from time.
            swing = max(-1.0, min(1.0, self._ring.angle * self.facing / 1.1))
            self._animator.seek(round((swing + 1) / 2 * 4) * 1.0)
        elif name == "pound":
            frame = 0 if not self._pound_falling else 1 + int(self._state_time * 16) % 2
            self._animator.seek(frame * 0.06)

    def _stretch(self, amount: float) -> None:
        self._scale = amount
        self._scale_velocity = 0.0

    def _squash(self, amount: float) -> None:
        self._scale = min(self._scale, amount)
        self._scale_velocity = 0.0

    def _update_spring(self, dt: float) -> None:
        acceleration = -SPRING_STIFFNESS * (self._scale - 1.0) - SPRING_DAMPING * self._scale_velocity
        self._scale_velocity += acceleration * dt
        self._scale += self._scale_velocity * dt
        if abs(self._scale - 1.0) < 0.002 and abs(self._scale_velocity) < 0.01:
            self._scale, self._scale_velocity = 1.0, 0.0

    def _set_state(self, state: PlayerState) -> None:
        if state != self.state:
            self.state = state
            self._state_time = 0.0

    def _set_power(self, power: PowerLevel) -> None:
        self.power = power
        self._animator.set_animations(self._animation_set())
        palette = self._palette()
        self.scarf.set_colors(palette.scarf, palette.scarf_tip)
        self._scarf_spent = False

    def _animation_set(self) -> Mapping[str, Animation]:
        return self._animation_sets[self.power]

    def _palette(self) -> prince.PrincePalette:
        return (prince.PRINCE_PALETTE, prince.PRINCE_POWERED_PALETTE, prince.PRINCE_STAR_PALETTE)[int(self.power)]

    def _scale_xy(self) -> tuple[float, float]:
        sy = self._scale
        sx = 1.0 + (1.0 - sy) * 0.85
        return sx, sy

    def _scarf_anchor(self) -> tuple[float, float]:
        name = self._animator.current
        animation = self._animation_set()[name]
        dx, dy = _anchor(name, self._animator.frame_index, len(animation.frames))
        sx, sy = self._scale_xy()
        return self.body.centerx + dx * self.facing * sx, self.body.bottom + dy * sy

    # --- Lights -------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        glow = (255, 220, 170) if self.power < PowerLevel.STAR else (160, 200, 255)
        return [Light(self.body.centerx, self.body.centery, 110 if self.power == PowerLevel.STAR else 90, glow, 0.75)]

    # --- Draw ---------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        self._draw_afterimages(surface, camera)
        if self._invulnerable_timer > 0 and self.state != PlayerState.DEAD:
            blink_phase = int(self._invulnerable_timer * self.physics.invulnerability_blink_rate)
            if blink_phase % 2 == 0:
                return
        image = self._animator.image(flip_x=self.facing < 0)
        sx, sy = self._scale_xy()
        if abs(sx - 1.0) > 0.01 or abs(sy - 1.0) > 0.01:
            width, height = image.get_size()
            image = pygame.transform.scale(image, (max(1, round(width * sx)), max(1, round(height * sy))))
        screen_x, screen_y = camera.to_screen(*self.body.midbottom)
        rect = image.get_rect(midbottom=(screen_x, screen_y))
        if self.state == PlayerState.POUND and not self._pound_falling:
            # Wind-up somersault before the plunge.
            progress = 1.0 - max(0.0, self._pound_timer) / self.physics.pound_windup
            image = pygame.transform.rotate(image, -360 * progress * self.facing)
            rect = image.get_rect(center=camera.to_screen(self.body.centerx, self.body.centery))
        elif self.state == PlayerState.DASH and self._dash_dir.y:
            angle = -math.degrees(math.atan2(self._dash_dir.y, abs(self._dash_dir.x) + 1e-6)) * 0.6
            image = pygame.transform.rotate(image, angle * self.facing)
            rect = image.get_rect(center=camera.to_screen(self.body.centerx, self.body.centery))

        clip_y = None
        if self.state in (PlayerState.ENTERING_DOOR, PlayerState.EXITING_DOOR) and self.door is not None:
            if self.door.enter_direction == "up":
                progress = self._door_progress()
                image = image.copy()
                image.set_alpha(round(255 * (1.0 - progress)))
            else:
                clip_y = camera.to_screen(0, self.door.rect.bottom)[1]
                if self.state == PlayerState.EXITING_DOOR:
                    # Rise from inside the well: shift the sprite down, then up.
                    rect.y += round(rect.height * (1.0 - self._door_progress()))
        if self.state != PlayerState.DEAD and clip_y is None:
            self.scarf.draw(surface, camera)
        if clip_y is not None:
            visible = max(0, min(rect.height, clip_y - rect.top))
            if visible > 0:
                surface.blit(image, rect.topleft, pygame.Rect(0, 0, rect.width, visible))
            return
        surface.blit(image, rect)
        self._draw_glide_shawl(surface, camera)
        self._draw_held_ring(surface, camera)
        if self.attack_rect is not None:
            cx, cy = camera.to_screen(self.body.centerx, self.body.centery)
            progress = 1.0 - self._attack_timer / settings.MELEE_DURATION
            points = []
            for i in range(13):
                angle = -1.15 + i * 0.17 + progress * 0.25
                points.append((round(cx + math.cos(angle) * settings.MELEE_REACH * self._attack_facing),
                               round(cy + math.sin(angle) * 22)))
            pygame.draw.lines(surface, (242, 186, 82), False, points, 5)
            pygame.draw.lines(surface, (255, 247, 210), False, points, 2)

    def _door_progress(self) -> float:
        p = self.physics
        if self.state == PlayerState.ENTERING_DOOR:
            return min(1.0, self._state_time / p.door_enter_duration)
        return min(1.0, self._state_time / p.door_exit_duration)
