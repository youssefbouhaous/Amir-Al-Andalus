"""Moving one-way platforms.

Every platform exposes the ``PlatformSurface`` interface (left, right, top,
previous_top, delta): ``delta`` is how far it moved this step, which bodies
standing on it add to their own movement, so riding goes through normal
collision instead of teleporting.

* ``MovingPlatform``: back and forth along one axis, eased at the ends.
* ``PendulumPlatform``: a brass lamp swinging on a chain.
* ``Wheel`` + ``WheelSeat``: seats that stay level on a turning wheel.
* ``LilyPad``: floats on water and dips under the prince's weight.
* ``Carpet``: a flying carpet that follows a path once you step on it.
"""

import bisect
import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from objects.prop import Prop
from rendering import emitters
from rendering.art import objects as art
from rendering.camera import Camera
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from world.world import World


class Platform:
    is_carpet = False

    def __init__(self, x: float, y: float, width: int, height: int) -> None:
        self.position = pygame.Vector2(x, y)
        self.width = width
        self.height = height
        self.delta = pygame.Vector2()
        self._previous_top = y

    @property
    def left(self) -> float:
        return self.position.x

    @property
    def right(self) -> float:
        return self.position.x + self.width

    @property
    def top(self) -> float:
        return self.position.y

    @property
    def previous_top(self) -> float:
        return self._previous_top

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.position.x), round(self.position.y), self.width, self.height)

    def _move_to(self, x: float, y: float) -> None:
        previous = pygame.Vector2(self.position)
        self.position.update(x, y)
        self.delta = self.position - previous
        self._previous_top = previous.y

    def carries_player(self, world: "World") -> bool:
        return world.player.body.ground_platform is self

    def update(self, dt: float, world: "World") -> None:
        pass

    def lights(self) -> list[Light]:
        return []

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        pass


class MovingPlatform(Platform):
    """Motion follows a cosine curve so it eases in and out at the ends
    instead of snapping direction."""

    def __init__(
        self,
        rect: pygame.Rect,
        horizontal: bool,
        distance: float,
        speed: float,
        image: pygame.Surface,
        reverse: bool = False,
    ) -> None:
        super().__init__(rect.x, rect.y, rect.width, rect.height)
        self._origin = pygame.Vector2(rect.x, rect.y)
        direction = pygame.Vector2(1, 0) if horizontal else pygame.Vector2(0, 1)
        self._direction = -direction if reverse else direction
        self._distance = distance
        # Chosen so the average speed over one pass equals ``speed``.
        self._angular_speed = math.pi * speed / distance if distance > 0 else 0.0
        self._phase = 0.0
        self._image = image

    def update(self, dt: float, world: "World" = None) -> None:  # type: ignore[assignment]
        self._phase += self._angular_speed * dt
        offset = self._distance * (1.0 - math.cos(self._phase)) / 2.0
        target = self._origin + self._direction * offset
        self._move_to(target.x, target.y)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        tile_width = self._image.get_width()
        for x in range(0, self.width, tile_width):
            area = pygame.Rect(0, 0, min(tile_width, self.width - x), self._image.get_height())
            surface.blit(self._image, camera.to_screen(self.position.x + x, self.position.y), area)


class PendulumPlatform(Platform):
    def __init__(self, pivot: tuple[float, float], length: float, amplitude_deg: float,
                 period: float, width: int = 64, phase: float = 0.0) -> None:
        self._pivot = pivot
        self._length = length
        self._amplitude = math.radians(amplitude_deg)
        self._omega = math.tau / max(0.5, period)
        self._phase = phase
        self._time = 0.0
        x, y = self._point(0.0)
        super().__init__(x - width / 2, y, width, 12)
        self._image = art.pendulum_lamp(width)
        self._angle = 0.0

    def _point(self, time: float) -> tuple[float, float]:
        angle = self._amplitude * math.sin(self._omega * time + self._phase)
        self._angle = angle
        return self._pivot[0] + math.sin(angle) * self._length, self._pivot[1] + math.cos(angle) * self._length

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        x, y = self._point(self._time)
        self._move_to(x - self.width / 2, y)

    def lights(self) -> list[Light]:
        return [Light(self.position.x + self.width / 2, self.position.y + 12, 110, (255, 206, 120), 0.8, flicker=0.3)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        px, py = camera.to_screen(*self._pivot)
        cx, cy = camera.to_screen(self.position.x + self.width / 2, self.position.y)
        links = max(2, int(self._length / 10))
        for k in range(links):
            t0, t1 = k / links, (k + 0.7) / links
            a = (px + (cx - px) * t0, py + (cy - py) * t0)
            b = (px + (cx - px) * t1, py + (cy - py) * t1)
            pygame.draw.line(surface, (60, 40, 30), a, b, 4)
            pygame.draw.line(surface, (200, 160, 70), a, b, 2)
        pygame.draw.circle(surface, (60, 40, 30), (px, py), 5)
        pygame.draw.circle(surface, (220, 180, 80), (px, py), 3)
        surface.blit(self._image, (cx - self.width // 2, cy))


class Wheel(Prop):
    """A turning wheel (water wheel, astrolabe, gear) carrying level seats."""

    layer = "back"

    def __init__(self, center: tuple[float, float], radius: float, seats: int, speed_deg: float,
                 style: str = "noria", seat_width: int = 56) -> None:
        super().__init__(pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2))
        self.center = center
        self.radius = radius
        self.speed = math.radians(speed_deg)
        self.style = style
        self.angle = 0.0
        self.seats = [WheelSeat(self, index * math.tau / seats, seat_width) for index in range(seats)]
        size = int(radius * 2 + 40)
        self._frame = self._render_frame(size)

    def _render_frame(self, size: int) -> pygame.Surface:
        from rendering.art.backdrops import gear_image

        if self.style == "gear":
            return gear_image(int(self.radius * 0.9), (120, 86, 48))
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        r = self.radius
        rim = (110, 70, 40) if self.style == "noria" else (200, 150, 60)
        pygame.draw.circle(surface, (50, 30, 20), (c, c), r + 6, 8)
        pygame.draw.circle(surface, rim, (c, c), r + 5, 5)
        pygame.draw.circle(surface, rim, (c, c), r * 0.35, 4)
        for k in range(12):
            a = k * math.tau / 12
            pygame.draw.line(surface, (50, 30, 20), (c, c), (c + math.cos(a) * r, c + math.sin(a) * r), 6)
            pygame.draw.line(surface, rim, (c, c), (c + math.cos(a) * r, c + math.sin(a) * r), 3)
            if self.style == "noria":
                bucket = (c + math.cos(a) * (r + 6), c + math.sin(a) * (r + 6))
                pygame.draw.rect(surface, (80, 110, 150), (bucket[0] - 4, bucket[1] - 4, 8, 8), border_radius=2)
        pygame.draw.circle(surface, (230, 190, 80), (c, c), 7)
        return surface

    def update(self, dt: float, world: "World") -> None:
        self.angle = world.time * self.speed

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        image = pygame.transform.rotate(self._frame, -math.degrees(self.angle) % 360)
        surface.blit(image, image.get_rect(center=camera.to_screen(*self.center)))


class WheelSeat(Platform):
    def __init__(self, wheel: Wheel, offset: float, width: int) -> None:
        self._wheel = wheel
        self._offset = offset
        x, y = self._point(0.0)
        super().__init__(x - width / 2, y, width, 10)
        self._image = art.wheel_seat(width)

    def _point(self, angle: float) -> tuple[float, float]:
        a = angle + self._offset
        cx, cy = self._wheel.center
        return cx + math.cos(a) * self._wheel.radius, cy + math.sin(a) * self._wheel.radius

    def update(self, dt: float, world: "World") -> None:
        x, y = self._point(world.time * self._wheel.speed)
        self._move_to(x - self.width / 2, y)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        ax, ay = camera.to_screen(self.position.x + self.width / 2, self.position.y)
        pygame.draw.line(surface, (60, 40, 30), (ax, ay), (ax, ay - 6), 3)
        surface.blit(self._image, (ax - self.width // 2, ay))


class LilyPad(Platform):
    SINK_DEPTH = 7.0

    def __init__(self, midtop: tuple[float, float], width: int, flower: bool, phase: float) -> None:
        super().__init__(midtop[0] - width / 2, midtop[1], width, 10)
        self._rest_y = midtop[1]
        self._sink = 0.0
        self._sink_velocity = 0.0
        self._time = phase
        self._image = art.lily_pad(width, flower)
        self._was_carrying = False

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        carrying = self.carries_player(world)
        target = self.SINK_DEPTH if carrying else 0.0
        # Springy: dips quickly, bobs back up with a little overshoot.
        acceleration = -90.0 * (self._sink - target) - 9.0 * self._sink_velocity
        self._sink_velocity += acceleration * dt
        self._sink += self._sink_velocity * dt
        if carrying and not self._was_carrying:
            self._sink_velocity += 30.0
            world.particles.spawn(self.position.x + self.width / 2, self._rest_y + 6, life=0.6,
                                  kind=Kind.RING, size=8, size_end=40, color=(200, 230, 250), front=False)
        self._was_carrying = carrying
        bob = math.sin(self._time * 2.1) * 1.2
        self._move_to(self.position.x, self._rest_y + self._sink + bob)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self._image, camera.to_screen(self.position.x, self.position.y - 4))


class _Path:
    """A smooth Catmull-Rom curve through points, sampled by arc length."""

    def __init__(self, points: list[tuple[float, float]]) -> None:
        if len(points) < 2:
            points = points + [(points[0][0] + 1, points[0][1])]
        extended = [points[0]] + points + [points[-1]]
        self.samples: list[tuple[float, float]] = []
        for index in range(1, len(extended) - 2):
            p0, p1, p2, p3 = extended[index - 1:index + 3]
            for step in range(16):
                t = step / 16
                t2, t3 = t * t, t * t * t
                x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                           + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
                y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                           + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
                self.samples.append((x, y))
        self.samples.append(points[-1])
        self.lengths = [0.0]
        for a, b in zip(self.samples, self.samples[1:]):
            self.lengths.append(self.lengths[-1] + math.dist(a, b))

    @property
    def length(self) -> float:
        return self.lengths[-1]

    def at(self, distance: float) -> tuple[float, float]:
        distance = max(0.0, min(self.length, distance))
        index = max(1, bisect.bisect_left(self.lengths, distance))
        index = min(index, len(self.samples) - 1)
        d0, d1 = self.lengths[index - 1], self.lengths[index]
        t = 0.0 if d1 == d0 else (distance - d0) / (d1 - d0)
        (x0, y0), (x1, y1) = self.samples[index - 1], self.samples[index]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t


class Carpet(Platform):
    """Waits until the prince steps on, then flies its path; comes back when
    left alone at the far end, so it can be taken again."""

    is_carpet = True
    WAIT_BEFORE_RETURN = 1.8
    RAMP = 0.7

    def __init__(self, points: list[tuple[float, float]], width: int = 96, speed: float = 150.0) -> None:
        self._path = _Path(points)
        start = self._path.at(0.0)
        super().__init__(start[0] - width / 2, start[1], width, 10)
        self._speed = speed
        self._distance = 0.0
        self._direction = 0  # 0 waiting, 1 forward, -1 returning
        self._idle_timer = 0.0
        self._time = 0.0
        self._texture = art.carpet_texture(width)
        self._velocity = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        carrying = self.carries_player(world)
        at_start = self._distance <= 0.0
        at_end = self._distance >= self._path.length
        if self._direction == 0:
            if carrying and at_start:
                self._direction = 1
                world.events.emit(EventType.CARPET_LAUNCHED, (self.position.x + self.width / 2, self.position.y))
            elif at_end and not carrying:
                self._idle_timer += dt
                if self._idle_timer > self.WAIT_BEFORE_RETURN:
                    self._direction = -1
            elif carrying and at_end:
                self._idle_timer = 0.0
        target_speed = self._speed if self._direction != 0 else 0.0
        # Ease out near either end of the path.
        remaining = (self._path.length - self._distance) if self._direction > 0 else self._distance
        if self._direction != 0:
            target_speed = min(target_speed, max(30.0, remaining * 1.8))
        self._velocity += (target_speed - self._velocity) * min(1.0, dt / self.RAMP * 3)
        self._distance += self._velocity * dt * (self._direction if self._direction else 0)
        if self._direction > 0 and self._distance >= self._path.length:
            self._distance = self._path.length
            self._direction = 0
            self._idle_timer = 0.0
            self._velocity = 0.0
        elif self._direction < 0 and self._distance <= 0.0:
            self._distance = 0.0
            self._direction = 0
            self._velocity = 0.0
        x, y = self._path.at(self._distance)
        bob = math.sin(self._time * 2.6) * 2.0
        self._move_to(x - self.width / 2, y + bob)
        if self._direction != 0 and int(self._time * 60) % 2 == 0:
            emitters.magic_trail(world.particles, self.position.x + world.particles.rng.uniform(0, self.width),
                                 self.position.y + 10, (255, 210, 140))

    def lights(self) -> list[Light]:
        return [Light(self.position.x + self.width / 2, self.position.y, 90, (255, 200, 150), 0.6)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x0, y0 = camera.to_screen(self.position.x, self.position.y)
        amplitude = 3.0 if self._direction else 1.6
        texture = self._texture
        height = texture.get_height()
        for x in range(0, self.width, 2):
            wave = math.sin(x * 0.11 - self._time * 7.0) * amplitude * (0.35 + 0.65 * x / self.width)
            surface.blit(texture, (x0 + x, y0 + round(wave)), pygame.Rect(x, 0, 2, height))
        for end, sign in ((0, -1), (self.width, 1)):
            wave = math.sin(end * 0.11 - self._time * 7.0) * amplitude * (0.35 + 0.65 * end / self.width)
            for k in range(4):
                tx = x0 + end + sign * 1
                ty = y0 + round(wave) + 2 + k * 2.4
                sway = math.sin(self._time * 9 + k) * 2
                pygame.draw.line(surface, (230, 180, 70), (tx, ty), (tx + sign * (5 + sway), ty + 1), 1)
