"""Human foes for the manuscript finales: people drawn on Amir's own rig.

A Performer has hit points and a small state machine (offstage, enter, fight,
stunned, hurt, defeated, vanished); it takes the prince's blows (slash,
stomp, dash or slide, ground pound, thrown stars) and falls in a short
defeat. Each finale's machine gives its performers a *ward* - level 1's
bubble of moon-water, level 2's gilding of stolen sunlight - that the
subclasses implement through the ``ward`` hooks below. While warded, a blow
connects but does no harm.
"""

import math
import random
from typing import TYPE_CHECKING, ClassVar

import pygame

from core.events import EventType
from core.settings import Color
from physics.body import Body
from physics.collision import apply_gravity, move_body
from rendering import emitters
from rendering.animation import Animator
from rendering.camera import Camera
from rendering.lighting import Light
from rendering.sprite_library import SheetSpec, SpriteLibrary

if TYPE_CHECKING:
    from world.world import World

GRAVITY = 2100.0
HIT_GRACE = 0.3
HOVER = 22.0          # how high a floating performer drifts above the floor


def strike_player(world: "World", direction: int, push: float = 300.0) -> None:
    """A performer's blow: it hurts, and (if he survives it) knocks the prince back."""
    player = world.player
    if not player.can_be_hurt:
        return
    player.take_damage(world)
    if player.is_controllable:
        if player.state.name in ("SWING", "DASH"):
            player._reset_moves()
        player.body.velocity.update(direction * push, -260)
        player.body.ground_platform = None
        player._wall_lock_timer = max(player._wall_lock_timer, 0.25)


class Performer:
    kind: ClassVar[str] = ""
    title: ClassVar[str] = ""
    sheet: ClassVar[SheetSpec]
    max_hp: ClassVar[int] = 2
    floats: ClassVar[bool] = False
    element: ClassVar[Color] = (255, 255, 255)

    def __init__(self, x: float, floor: float, sprites: SpriteLibrary, bounds: tuple[float, float]) -> None:
        self.body = Body.from_midbottom((x, floor), 20, 28)
        self.floor = floor
        self.bounds = bounds
        self.animations = sprites.animations(self.sheet)
        self.animator = Animator(self.animations, "idle")
        self.facing = -1
        self.hp = self.max_hp
        self.state = "offstage"
        self.timer = 0.0
        self.time = random.random() * 10
        self.grace = 0.0
        self.flash = 0.0
        self.stun_time = 0.0
        self.gone = False
        self.engaged = True
        self._defeat_time = 0.0

    # --- queries ------------------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect()

    @property
    def center(self) -> tuple[float, float]:
        return self.body.centerx, self.body.centery

    @property
    def active(self) -> bool:
        return self.state not in ("offstage", "defeated") and not self.gone

    @property
    def targetable(self) -> bool:
        return self.active and self.state not in ("enter", "vanished")

    @property
    def exposed(self) -> bool:
        """Ward down: the performer turns wary and keeps out of reach."""
        return not self.warded and self.state == "fight"

    # --- the ward (subclasses) -------------------------------------------------------------------
    @property
    def warded(self) -> bool:
        return False

    def begin_ward(self) -> None:
        """The performer steps on stage wrapped in its machine's gift."""

    def ward_blow(self, world: "World", direction: int, source: str) -> None:
        """A blow landed on the ward instead of the performer."""

    def break_ward(self, world: "World") -> None:
        """The manuscript power strips the ward away."""

    def drop_ward(self) -> None:
        """Defeated: the ward is gone for good."""

    def update_ward(self, dt: float, world: "World") -> None:
        pass

    def draw_ward(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def ward_lights(self) -> list[Light]:
        return []

    # --- staging ----------------------------------------------------------------------------
    def enter(self, world: "World") -> None:
        self.state = "enter"
        self.timer = 0.0
        self.begin_ward()
        self.animator.play("bow", restart=True)
        world.events.emit(EventType.MACHINE_CLUNK, self.center, "bow")

    # --- taking blows ---------------------------------------------------------------------------
    def hit(self, world: "World", direction: int, source: str = "blow") -> bool:
        """Returns True if the blow connected (on the ward or the body)."""
        if not self.targetable or self.grace > 0:
            return False
        self.grace = HIT_GRACE
        if self.warded:
            self.ward_blow(world, direction, source)
            return True
        self.hp -= 1
        self.flash = 1.0
        self.body.velocity.update(direction * 220, -260 if not self.floats else 0)
        world.events.emit(EventType.ENEMY_KNOCKED_OUT, (self.body.centerx, self.body.top))
        if self.hp <= 0:
            self.defeat(world)
        elif self.state != "stunned":
            self.state = "hurt"
            self.timer = 0.0
            self.animator.play("hurt", restart=True)
            self.on_interrupted(world)
        elif source not in ("peck", "ink"):
            # A blow shakes a stunned performer out of it soon after (the power's own touch doesn't).
            self.stun_time = min(self.stun_time, 0.45)
        return True

    def stun(self, world: "World", seconds: float) -> None:
        if not self.targetable:
            return
        self.break_ward(world)
        self.state = "stunned"
        self.stun_time = seconds
        self.timer = 0.0
        self.animator.play("stunned", restart=True)
        self.on_interrupted(world)

    def defeat(self, world: "World") -> None:
        self.state = "defeated"
        self._defeat_time = 0.0
        self.drop_ward()
        self.animator.play("defeated", restart=True)
        self.on_interrupted(world)
        self.silence(world, None)
        self.shed(world)
        world.events.emit(EventType.GUARDIAN_AWAKE, self.center, f"{self.title} falls!")

    def shed(self, world: "World") -> None:
        """Something flies off a beaten performer (a mask, stolen coins...)."""

    def on_interrupted(self, world: "World") -> None:
        """Cancel whatever trick was under way (subclasses)."""

    def silence(self, world: "World", effect) -> None:  # noqa: ANN001
        """The manuscript power (or defeat) breaks this performer's missiles; ``effect`` may limit the reach."""

    # --- the prince's moves ------------------------------------------------------------------------
    def _take_blows(self, world: "World") -> None:
        player = world.player
        rect = self.rect
        direction = 1 if self.body.centerx >= player.body.centerx else -1
        attack = player.attack_rect
        if attack is not None and attack.colliderect(rect.inflate(14, 10)):
            self.hit(world, player.attack_facing)
            return
        falling_on = player.body.velocity.y > 0 and player.previous_bottom <= rect.top + 10 and player.rect.colliderect(rect)
        if falling_on:
            player.bounce()
            self.hit(world, direction, "stomp")
            return
        if (player.is_dashing or player.state.name == "SLIDE") and player.rect.inflate(8, 6).colliderect(rect):
            self.hit(world, direction, "dash")
            return
        for event in world.events._events:
            if event.type == EventType.PLAYER_POUNDED and abs(event.position[0] - self.body.centerx) < 70 \
                    and abs(event.position[1] - self.body.bottom) < 48:
                self.hit(world, direction, "pound")
                return
        for projectile in world.projectiles:
            if projectile.friendly and projectile.alive and projectile.rect.colliderect(rect):
                projectile.expire(world)
                self.hit(world, 1 if projectile.body.velocity.x > 0 else -1, "star")
                return

    # --- update ---------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        self.time += dt
        self.timer += dt
        self.grace = max(0.0, self.grace - dt)
        self.flash = max(0.0, self.flash - dt * 3)
        if self.state == "offstage" or self.gone:
            return
        if self.state == "defeated":
            self._defeat_time += dt
            self._physics(dt, world, friction=True)
            if self._defeat_time > 1.3:
                self.dissolve(world)
                self.gone = True
            self.animator.update(dt)
            return
        self.update_ward(dt, world)
        if self.state == "enter":
            self._physics(dt, world, friction=True)
            if self.animator.finished and self.timer > 0.9:
                self.state = "fight"
                self.timer = 0.0
                self.animator.play("idle")
        elif self.state == "stunned":
            self.stun_time -= dt
            self._physics(dt, world, friction=True)
            if self.stun_time <= 0:
                self.state = "fight"
                self.timer = 0.0
                self.animator.play("idle")
        elif self.state == "hurt":
            self._physics(dt, world, friction=True)
            if self.timer > 0.45:
                self.state = "fight"
                self.timer = 0.0
                self.animator.play("idle")
        elif self.engaged:
            self.think(dt, world)
        else:
            # The prince has stepped off the stage: wait for him.
            self.body.velocity.x = 0
            self._physics(dt, world, friction=True)
            if self.animator.finished or self.animator.current not in ("idle", "walk"):
                self.animator.play("idle")
        self._take_blows(world)
        self.animator.update(dt)

    def think(self, dt: float, world: "World") -> None:
        """The performer's routine while fighting (subclasses)."""
        self._physics(dt, world, friction=True)

    def hover_height(self) -> float:
        return HOVER

    def _physics(self, dt: float, world: "World", friction: bool = False) -> None:
        body = self.body
        if friction and abs(body.velocity.x) > 0:
            body.velocity.x *= max(0.0, 1.0 - 8 * dt)
        if self.floats:
            target = self.floor - self.hover_height() + math.sin(self.time * 2.2) * 4
            body.velocity.y = (target - body.bottom) * 5
            body.x += body.velocity.x * dt
            body.y += body.velocity.y * dt
        else:
            apply_gravity(body, GRAVITY, 900.0, dt)
            move_body(body, dt, world.collision, world.platforms)
        left, right = self.bounds
        body.x = max(left, min(right - body.width, body.x))

    def face_player(self, world: "World") -> None:
        self.facing = 1 if world.player.body.centerx > self.body.centerx else -1

    def walk_to(self, target_x: float, speed: float) -> bool:
        dx = target_x - self.body.centerx
        if abs(dx) < 8:
            self.body.velocity.x = 0
            return True
        self.body.velocity.x = math.copysign(speed, dx)
        return False

    def dissolve(self, world: "World") -> None:
        emitters.smoke_poof(world.particles, *self.center, self.element, 12)

    # --- drawing ------------------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        if not self.active:
            return []
        return [Light(*self.center, 70, self.element, 0.5)] + self.ward_lights()

    def draw_back(self, surface: pygame.Surface, camera: Camera) -> None:
        pass

    def sprite(self) -> pygame.Surface:
        """This frame's image (subclasses may tint it: gilded, ink-blotted...)."""
        return self.animator.image(flip_x=self.facing < 0)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        if self.state == "offstage" or self.gone or self.state == "vanished":
            return
        image = self.sprite()
        if self.flash > 0:
            image = image.copy()
            image.fill((round(160 * self.flash),) * 3, special_flags=pygame.BLEND_RGB_ADD)
        x, y = camera.to_screen(*self.body.midbottom)
        surface.blit(image, image.get_rect(midbottom=(x, y + 2)))
        self.draw_extras(surface, camera)
        if self.state == "stunned":
            hx, hy = x, y - 44
            for k in range(3):
                a = self.time * 5 + k * math.tau / 3
                sx, sy = hx + math.cos(a) * 12, hy + math.sin(a) * 4
                pygame.draw.polygon(surface, (255, 236, 120), [(sx, sy - 3), (sx + 1, sy - 1), (sx + 3, sy), (sx + 1, sy + 1),
                                                                (sx, sy + 3), (sx - 1, sy + 1), (sx - 3, sy), (sx - 1, sy - 1)])
        if self.state != "defeated":
            self.draw_ward(surface, camera)
            if self.hp < self.max_hp:
                for k in range(self.max_hp):
                    px = x - (self.max_hp - 1) * 5 + k * 10
                    color = (255, 206, 90) if k < self.hp else (70, 50, 60)
                    pygame.draw.polygon(surface, (40, 20, 24), [(px, y - 60), (px + 4, y - 56), (px, y - 52), (px - 4, y - 56)])
                    pygame.draw.polygon(surface, color, [(px, y - 59), (px + 3, y - 56), (px, y - 53), (px - 3, y - 56)])

    def draw_extras(self, surface: pygame.Surface, camera: Camera) -> None:
        pass
