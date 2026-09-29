"""Base class for enemies.

The base handles what every enemy shares: body, animation, being stomped,
being knocked out, dying. Subclasses only implement ``behave`` (how they move
while alive). The player never contains enemy-specific logic; interactions ask
the enemy what happens (``on_stomped`` returns False for enemies that can't be
stomped, like the hedgehog).
"""

from abc import abstractmethod
from collections.abc import Mapping
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

import pygame

from core.events import EventType
from core.settings import ENEMY, Color
from entities.entity import Entity
from physics.body import Body
from physics.collision import apply_gravity
from rendering import emitters
from rendering.animation import Animation, Animator
from rendering.camera import Camera
from rendering.lighting import Light

if TYPE_CHECKING:
    from world.world import World

KNOCKOUT_SPIN_SPEED = 540.0


class EnemyState(Enum):
    ACTIVE = auto()
    SQUASHED = auto()
    KNOCKED_OUT = auto()


class Enemy(Entity):
    stompable: ClassVar[bool] = True
    # Ground enemies bounce off each other; flyers pass through.
    turns_on_enemy_contact: ClassVar[bool] = True
    # Thrown stars pass through spirits.
    star_immune: ClassVar[bool] = False
    # Bumping the block underneath knocks it out.
    bumpable: ClassVar[bool] = True
    poof_color: ClassVar[Color] = (220, 210, 200)

    def __init__(
        self,
        midbottom: tuple[float, float],
        hitbox: tuple[float, float],
        animations: Mapping[str, Animation],
        facing: int = -1,
    ) -> None:
        super().__init__()
        self.body = Body.from_midbottom(midbottom, *hitbox)
        self.facing = facing
        self.state = EnemyState.ACTIVE
        # Enemies stay frozen until they first come near the screen.
        self.activated = False
        self.animator = Animator(animations, "walk")
        self._state_time = 0.0
        self._spin = 0.0
        self._squash = 1.0
        self._flash = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return self.body.rect()

    @property
    def is_dangerous(self) -> bool:
        return self.state == EnemyState.ACTIVE

    def update(self, dt: float, world: "World") -> None:
        self._state_time += dt
        self._flash = max(0.0, self._flash - dt)
        match self.state:
            case EnemyState.ACTIVE:
                self.behave(dt, world)
            case EnemyState.SQUASHED:
                self._squash = max(0.3, self._squash - dt * 6)
                if self._state_time >= ENEMY.squash_duration:
                    self.alive = False
                    emitters.smoke_poof(world.particles, self.body.centerx, self.body.bottom - 6, self.poof_color, 8)
            case EnemyState.KNOCKED_OUT:
                apply_gravity(self.body, ENEMY.gravity, ENEMY.terminal_velocity, dt)
                self.body.x += self.body.velocity.x * dt
                self.body.y += self.body.velocity.y * dt
                self._spin += KNOCKOUT_SPIN_SPEED * dt * (1 if self.body.velocity.x >= 0 else -1)

        if self.body.top > world.collision.pixel_height:
            self.alive = False
        self.animator.update(dt)

    @abstractmethod
    def behave(self, dt: float, world: "World") -> None:
        """Movement/AI while alive."""

    def on_stomped(self, world: "World") -> bool:
        """Player landed on us. Return False if stomping doesn't work."""
        if not self.stompable:
            return False
        self._set_state(EnemyState.SQUASHED)
        if self.animator.has("squashed"):
            self.animator.play("squashed")
        self.body.velocity.update(0, 0)
        emitters.stomp_impact(world.particles, self.body.centerx, self.body.top)
        return True

    def knock_out(self, world: "World", direction: int) -> None:
        """Hit from below by a bumped block: flip over and fall off screen."""
        if self.state != EnemyState.ACTIVE:
            return
        self._set_state(EnemyState.KNOCKED_OUT)
        self.body.velocity.update(
            direction * ENEMY.knockout_horizontal_speed, -ENEMY.knockout_velocity
        )
        emitters.stomp_impact(world.particles, self.body.centerx, self.body.centery)
        world.events.emit(EventType.ENEMY_KNOCKED_OUT, (self.body.centerx, self.body.top))

    def on_starred(self, world: "World", direction: int) -> bool:
        """Hit by a thrown star. Return False if the star should pass through."""
        if self.star_immune or self.state != EnemyState.ACTIVE:
            return False
        self._set_state(EnemyState.KNOCKED_OUT)
        self.body.velocity.update(direction * ENEMY.knockout_horizontal_speed * 2, -ENEMY.knockout_velocity * 0.8)
        emitters.sparkle_burst(world.particles, self.body.centerx, self.body.centery, (170, 210, 255), 10, 150)
        world.events.emit(EventType.ENEMY_STARRED, (self.body.centerx, self.body.top))
        return True

    def turn_around(self) -> None:
        self.facing = -self.facing

    def lights(self) -> list[Light]:
        return []

    def _set_state(self, state: EnemyState) -> None:
        self.state = state
        self._state_time = 0.0

    def _image(self) -> pygame.Surface:
        # Art faces right, so mirror when walking left.
        return self.animator.image(flip_x=self.facing < 0)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        image = self._image()
        if self.state == EnemyState.KNOCKED_OUT:
            image = pygame.transform.rotate(pygame.transform.flip(image, False, True), self._spin)
            center = camera.to_screen(self.body.centerx, self.body.centery)
            surface.blit(image, image.get_rect(center=center))
            return
        if self.state == EnemyState.SQUASHED and self._squash < 1.0:
            width, height = image.get_size()
            image = pygame.transform.scale(image, (round(width * (2 - self._squash) * 0.8), max(1, round(height * self._squash))))
        screen = camera.to_screen(*self.body.midbottom)
        surface.blit(image, image.get_rect(midbottom=screen))
