"""Decorations: they make the world feel alive but never block the prince.

Placed as ``decor`` objects with a ``style`` property. Some are simple
images; many are animated: orange trees sway and shed blossoms, pigeons
scatter when the prince runs by, gears and astrolabes turn, lamps swing,
koi leap from the pools, banners ripple and the great water clock drips in
time with the sun/moon blocks.
"""

import math
import random
from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from core.settings import Color
from objects.prop import Prop
from rendering import emitters
from rendering.art import objects as art
from rendering.art import scenery
from rendering.art.backdrops import gear_image
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind
from world.level_data import ObjectSpec

if TYPE_CHECKING:
    from world.world import World

_cache: dict[tuple, pygame.Surface] = {}


def _cached(key: tuple, factory: Callable[[], pygame.Surface]) -> pygame.Surface:
    image = _cache.get(key)
    if image is None:
        image = factory()
        _cache[key] = image
    return image


class ImageDecor(Prop):
    def __init__(self, midbottom: tuple[float, float], image: pygame.Surface, layer: str = "back") -> None:
        rect = image.get_rect(midbottom=(round(midbottom[0]), round(midbottom[1])))
        super().__init__(rect)
        self._image = image
        self._layer = layer

    @property
    def layer(self) -> str:  # type: ignore[override]
        return self._layer

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self._image, camera.to_screen(self.rect.x, self.rect.y))


class SwayingTree(ImageDecor):
    """Sways from its base in the breeze; orange trees shed blossoms."""

    FRAMES = 9

    def __init__(self, midbottom: tuple[float, float], image: pygame.Surface, key: str, blossoms: bool,
                 layer: str = "back") -> None:
        super().__init__(midbottom, image, layer)
        self._frames = [
            _cached((key, "sway", k), lambda k=k: pygame.transform.rotate(image, math.sin(k / self.FRAMES * math.tau) * 1.6))
            for k in range(self.FRAMES)
        ]
        self._time = midbottom[0] * 0.01
        self._blossoms = blossoms

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if self._blossoms and world.on_screen(self.rect, 0) and world.particles.rng.random() < dt * 0.8:
            rng = world.particles.rng
            world.particles.spawn(
                rng.uniform(self.rect.left + 10, self.rect.right - 10), rng.uniform(self.rect.top + 10, self.rect.centery),
                rng.uniform(-20, 5), rng.uniform(10, 30), life=rng.uniform(2.0, 3.0), kind=Kind.PETAL,
                size=rng.uniform(1.8, 2.6), color=(255, 250, 240), gravity=18, wobble=40, front=False,
            )

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        wind = world_wind = 0.0
        index = int((self._time * 0.9) * self.FRAMES) % self.FRAMES
        image = self._frames[index]
        bottom = camera.to_screen(self.rect.centerx, self.rect.bottom)
        surface.blit(image, image.get_rect(midbottom=(bottom[0], bottom[1] + 2)))


class HangingLamp(Prop):
    layer = "back"

    def __init__(self, point: tuple[float, float], chain: float) -> None:
        super().__init__(pygame.Rect(point[0] - 12, point[1], 24, chain + 30))
        self._pivot = point
        self._chain = chain
        self._time = point[0] * 0.02
        self._image = _cached(("lamp",), art.hanging_lamp)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt

    def _end(self) -> tuple[float, float]:
        angle = math.sin(self._time * 1.4) * 0.12
        return self._pivot[0] + math.sin(angle) * self._chain, self._pivot[1] + math.cos(angle) * self._chain

    def lights(self) -> list[Light]:
        x, y = self._end()
        return [Light(x, y + 16, 150, (255, 196, 110), 0.95, flicker=0.35, bloom=0.3)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        start = camera.to_screen(*self._pivot)
        end = camera.to_screen(*self._end())
        pygame.draw.line(surface, (60, 40, 30), start, end, 2)
        surface.blit(self._image, self._image.get_rect(midtop=end))
        blit_glow(surface, (end[0], end[1] + 14), 22, (255, 170, 80), 0.6)


class Banner(Prop):
    layer = "back"

    def __init__(self, point: tuple[float, float], color: Color) -> None:
        super().__init__(pygame.Rect(point[0], point[1], 20, 44))
        self._image = _cached(("banner", color), lambda: art.banner(color=color))
        self._time = point[0] * 0.03
        self._wind = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        self._wind = world.wind_at(self.rect.centerx, self.rect.centery)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x0, y0 = camera.to_screen(self.rect.x, self.rect.y)
        height = self._image.get_height()
        pygame.draw.line(surface, (90, 60, 40), (x0 - 2, y0 - 2), (x0 + 22, y0 - 2), 3)
        for y in range(0, height, 2):
            t = y / height
            wave = math.sin(self._time * 5 - y * 0.2) * 3 * t + self._wind * 0.05 * t
            surface.blit(self._image, (x0 + round(wave), y0 + y), pygame.Rect(0, y, self._image.get_width(), 2))


class Rotator(Prop):
    """A gear or astrolabe ring turning at a constant speed."""

    layer = "back"

    def __init__(self, center: tuple[float, float], image: pygame.Surface, speed: float) -> None:
        super().__init__(image.get_rect(center=(round(center[0]), round(center[1]))))
        self._image = image
        self._speed = speed
        self._angle = 0.0
        self._frames: dict[int, pygame.Surface] = {}

    def update(self, dt: float, world: "World") -> None:
        self._angle = (self._angle + self._speed * dt) % 360

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        step = int(self._angle / 3) % 120
        frame = self._frames.get(step)
        if frame is None:
            frame = pygame.transform.rotate(self._image, step * 3)
            self._frames[step] = frame
        surface.blit(frame, frame.get_rect(center=camera.to_screen(*self.rect.center)))


class Astrolabe(Prop):
    layer = "back"

    def __init__(self, midbottom: tuple[float, float]) -> None:
        super().__init__(pygame.Rect(midbottom[0] - 40, midbottom[1] - 110, 80, 110))
        self._rings = [Rotator((midbottom[0], midbottom[1] - 70), art.astrolabe_ring(r, c), s)
                       for r, c, s in ((34, (226, 172, 52)), (24, (200, 150, 60)), (14, (240, 200, 90))) for s in [0]]
        self._speeds = (12.0, -20.0, 35.0)

    def update(self, dt: float, world: "World") -> None:
        for ring, speed in zip(self._rings, self._speeds):
            ring._speed = speed
            ring.update(dt, world)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        base = camera.to_screen(self.rect.centerx, self.rect.bottom)
        pygame.draw.polygon(surface, (90, 60, 40), ((base[0] - 16, base[1]), (base[0] + 16, base[1]), (base[0] + 4, base[1] - 36), (base[0] - 4, base[1] - 36)))
        for ring in self._rings:
            ring.draw(surface, camera)


class WaterClock(Prop):
    """The great clepsydra: water drips from the upper basin to the lower one
    and the dial's hand sweeps in step with the sun/moon switch."""

    layer = "back"

    def __init__(self, midbottom: tuple[float, float]) -> None:
        super().__init__(pygame.Rect(midbottom[0] - 60, midbottom[1] - 200, 120, 200))
        self._face = _cached(("clock_face",), art.water_clock_face)
        self._progress = 0.0
        self._active = "sun"
        self._time = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if world.switch is not None and world.switch.automatic:
            self._progress = world.switch.progress
            self._active = world.switch.active
        else:
            self._progress = (self._time / 8) % 1.0

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.rect.x, self.rect.y)
        wood, brass, water = (96, 60, 38), (220, 170, 60), (110, 180, 230)
        pygame.draw.rect(surface, wood, (x + 8, y + 90, 104, 110), border_radius=6)
        pygame.draw.rect(surface, (70, 42, 28), (x + 8, y + 90, 104, 110), 3, border_radius=6)
        # Upper and lower vessels with levels following the countdown.
        upper = pygame.Rect(x + 18, y + 100, 36, 40)
        lower = pygame.Rect(x + 66, y + 150, 36, 40)
        for vessel, level in ((upper, 1.0 - self._progress), (lower, self._progress)):
            pygame.draw.rect(surface, (40, 50, 70), vessel)
            fill = round(vessel.height * level)
            pygame.draw.rect(surface, water, (vessel.x, vessel.bottom - fill, vessel.width, fill))
            pygame.draw.rect(surface, brass, vessel, 2)
        drip_y = upper.bottom + (self._time * 120) % 40
        pygame.draw.circle(surface, water, (upper.right + 6, round(drip_y)), 2)
        pygame.draw.line(surface, brass, (upper.right, upper.bottom - 4), (upper.right + 8, upper.bottom - 4), 2)
        face_rect = self._face.get_rect(center=(x + 60, y + 44))
        surface.blit(self._face, face_rect)
        angle = self._progress * math.tau - math.pi / 2
        hand = (face_rect.centerx + math.cos(angle) * 30, face_rect.centery + math.sin(angle) * 30)
        pygame.draw.line(surface, (60, 30, 20), face_rect.center, hand, 3)
        icon = (246, 190, 60) if self._active == "sun" else (120, 150, 230)
        pygame.draw.circle(surface, icon, face_rect.center, 6)


class Pigeons(Prop):
    """A little flock pecking at the ground; startled, it bursts into the air
    and flutters off, returning after a while."""

    layer = "mid"

    def __init__(self, midbottom: tuple[float, float], count: int = 5) -> None:
        super().__init__(pygame.Rect(midbottom[0] - 40, midbottom[1] - 12, 80, 12))
        rng = random.Random(int(midbottom[0]))
        self._home = [(midbottom[0] + rng.uniform(-36, 36), midbottom[1]) for _ in range(count)]
        self._birds = [[x, y, 0.0, 0.0, rng.uniform(0, 6), 1 if rng.random() < 0.5 else -1] for x, y in self._home]
        self._flying = False
        self._timer = 0.0
        self._frames = scenery.bird_frames((96, 96, 110), 9)
        self._flipped = [pygame.transform.flip(f, True, False) for f in self._frames]

    def update(self, dt: float, world: "World") -> None:
        player = world.player
        near = abs(player.body.centerx - self.rect.centerx) < 110 and abs(player.body.bottom - self.rect.bottom) < 80
        if not self._flying and near and (abs(player.body.velocity.x) > 60 or not player.body.on_ground):
            self._flying = True
            self._timer = 0.0
            rng = world.particles.rng
            for bird in self._birds:
                direction = 1 if bird[0] >= player.body.centerx else -1
                bird[2] = direction * rng.uniform(90, 170)
                bird[3] = -rng.uniform(160, 260)
                bird[5] = direction
            world.events.emit(EventType.BAT_SCREECH, self.rect.center, "pigeons")
        if self._flying:
            self._timer += dt
            for bird in self._birds:
                bird[3] -= 60 * dt
                bird[0] += bird[2] * dt
                bird[1] += bird[3] * dt
                bird[4] += dt * 3
            if self._timer > 7.0 and not near:
                self._flying = False
                for bird, home in zip(self._birds, self._home):
                    bird[0], bird[1] = home
        else:
            for bird in self._birds:
                bird[4] += dt

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        for x, y, _vx, _vy, phase, facing in self._birds:
            sx, sy = camera.to_screen(x, y)
            if self._flying:
                frames = self._frames if facing > 0 else self._flipped
                frame = frames[int(phase * 4) % 4]
                surface.blit(frame, frame.get_rect(midbottom=(sx, sy)))
            else:
                peck = 2 if int(phase * 2 + x) % 5 == 0 else 0
                pygame.draw.ellipse(surface, (120, 120, 134), (sx - 5, sy - 7, 10, 7))
                pygame.draw.circle(surface, (100, 100, 116), (sx + 4 * facing, sy - 7 + peck), 3)
                pygame.draw.line(surface, (220, 150, 60), (sx + 6 * facing, sy - 7 + peck), (sx + 8 * facing, sy - 6 + peck), 1)
                pygame.draw.circle(surface, (80, 180, 120), (sx + 3 * facing, sy - 5 + peck), 1)


class Butterflies(Prop):
    layer = "front"

    def __init__(self, center: tuple[float, float], count: int = 3) -> None:
        super().__init__(pygame.Rect(center[0] - 60, center[1] - 60, 120, 120))
        rng = random.Random(int(center[0]))
        self._flies = [(rng.uniform(0, math.tau), rng.uniform(0.6, 1.2), rng.choice(((250, 220, 90), (250, 250, 250), (240, 140, 60))))
                       for _ in range(count)]
        self._time = 0.0

    def update(self, dt: float, world: "World") -> None:
        self._time += dt

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        cx, cy = camera.to_screen(*self.rect.center)
        for phase, speed, color in self._flies:
            t = self._time * speed + phase
            x = cx + math.sin(t * 1.3) * 50 + math.sin(t * 3.1) * 10
            y = cy + math.sin(t * 2.1) * 30 + math.cos(t * 5.0) * 6
            flap = abs(math.sin(t * 22))
            w = max(1, round(5 * flap))
            pygame.draw.ellipse(surface, color, (x - w, y - 3, w, 5))
            pygame.draw.ellipse(surface, color, (x, y - 3, w, 5))
            pygame.draw.line(surface, (40, 30, 30), (x, y - 3), (x, y + 2), 1)


class Koi(Prop):
    """A golden carp that leaps from a pool every few seconds."""

    layer = "front"

    def __init__(self, point: tuple[float, float], span: float = 70.0) -> None:
        super().__init__(pygame.Rect(point[0] - span / 2, point[1] - 80, span, 80))
        self._surface_y = point[1]
        self._span = span
        self._time = random.Random(int(point[0])).uniform(0, 3)
        self._period = 4.2
        self._splashed = (False, False)

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        t = self._time % self._period
        jumping = t < 1.0
        entered = t >= 1.0
        if t < dt:
            emitters.splash(world.particles, self.rect.left, self._surface_y, 0.4)
        if 1.0 <= t < 1.0 + dt:
            emitters.splash(world.particles, self.rect.right, self._surface_y, 0.4)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        t = self._time % self._period
        if t >= 1.0:
            return
        x = self.rect.left + self._span * t
        y = self._surface_y - math.sin(t * math.pi) * 70
        angle = -math.degrees(math.atan2(-math.cos(t * math.pi) * 70 * math.pi, self._span))
        fish = _cached(("koi",), _make_koi)
        image = pygame.transform.rotate(fish, angle)
        surface.blit(image, image.get_rect(center=camera.to_screen(x, y)))


def _make_koi() -> pygame.Surface:
    from rendering.art.kit import Canvas

    c = Canvas(22, 12, fringe=(120, 50, 20))
    c.ellipse((250, 140, 40), (3, 2, 15, 8), (120, 50, 20), 0.6)
    c.polygon((250, 170, 80), [(4, 6), (0, 1.5), (0, 10.5)], (120, 50, 20), 0.5)
    c.ellipse((255, 250, 240), (9, 3, 5, 3))
    c.circle((30, 20, 20), (15.5, 5.5), 0.8)
    return c.finish()


class Torch(Prop):
    """A wall torch: flickering flame, embers and warm light."""

    layer = "back"

    def __init__(self, point: tuple[float, float]) -> None:
        super().__init__(pygame.Rect(point[0] - 10, point[1] - 30, 20, 40))
        self._time = point[0] * 0.07
        from objects.triggers import flames

        self._flames = flames()

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if world.on_screen(self.rect, 0) and world.particles.rng.random() < dt * 6:
            emitters.embers(world.particles, self.rect.centerx, self.rect.top + 6, 1, 3)

    def lights(self) -> list[Light]:
        return [Light(self.rect.centerx, self.rect.top + 10, 190, (255, 170, 90), 1.0, flicker=0.9, bloom=0.4)]

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        x, y = camera.to_screen(self.rect.centerx, self.rect.bottom)
        pygame.draw.polygon(surface, (60, 40, 30), ((x - 4, y), (x + 4, y), (x + 6, y - 16), (x - 6, y - 16)))
        pygame.draw.rect(surface, (200, 150, 60), (x - 7, y - 20, 14, 5), border_radius=2)
        flame = self._flames[int(self._time * 12) % len(self._flames)]
        surface.blit(flame, flame.get_rect(midbottom=(x, y - 16)))


class LightShaft(Prop):
    """A slanted beam of sunlight from a high window, with dust in it."""

    layer = "front"

    def __init__(self, rect: pygame.Rect, color: Color = (255, 236, 190)) -> None:
        super().__init__(rect)
        self._color = color
        self._image = _cached(("shaft", rect.width, rect.height, color), lambda: _make_shaft(rect.width, rect.height, color))
        self._time = rect.x * 0.01

    def update(self, dt: float, world: "World") -> None:
        self._time += dt
        if world.on_screen(self.rect, 0) and world.particles.rng.random() < dt * 5:
            rng = world.particles.rng
            y = rng.uniform(self.rect.top, self.rect.bottom)
            x = self.rect.left + (y - self.rect.top) * 0.5 + rng.uniform(0, self.rect.width * 0.5)
            world.particles.spawn(x, y, rng.uniform(-4, 4), rng.uniform(-6, 6), life=rng.uniform(1.5, 3.0),
                                  kind=Kind.GLOW, size=3, size_end=3, color=(255, 236, 190), alpha=0.5)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        pulse = 0.85 + 0.15 * math.sin(self._time * 0.8)
        self._image.set_alpha(round(255 * pulse))
        surface.blit(self._image, camera.to_screen(self.rect.x, self.rect.y), special_flags=pygame.BLEND_RGB_ADD)


def _make_shaft(width: int, height: int, color: Color) -> pygame.Surface:
    s = pygame.Surface((width + height // 2, height))
    s.fill((0, 0, 0))
    for y in range(height):
        fade = (1.0 - y / height) ** 1.3 * 0.22
        offset = y // 2
        for x in range(width):
            edge = min(x, width - x) / (width / 2)
            k = fade * min(1.0, edge * 1.5)
            s.set_at((x + offset, y), (round(color[0] * k), round(color[1] * k), round(color[2] * k)))
    return s


class Fountainlet(Prop):
    """A small decorative fountain with arcs of water."""

    layer = "back"

    def __init__(self, midbottom: tuple[float, float]) -> None:
        super().__init__(pygame.Rect(midbottom[0] - 24, midbottom[1] - 40, 48, 40))
        self._basin = _cached(("fountain_basin",), art.fountain_basin)

    def update(self, dt: float, world: "World") -> None:
        if world.on_screen(self.rect, 0):
            rng = world.particles.rng
            for _ in range(2):
                side = rng.choice((-1, 1))
                emitters.droplet(world.particles, self.rect.centerx, self.rect.bottom - 18,
                                 side * rng.uniform(20, 60), -rng.uniform(150, 220))

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        bottom = camera.to_screen(self.rect.centerx, self.rect.bottom)
        surface.blit(self._basin, self._basin.get_rect(midbottom=bottom))


def create_decor(spec: ObjectSpec) -> Prop | None:
    style = spec.get_str("style", "").lower()
    x, y = spec.midbottom
    layer = spec.get_str("layer", "back")
    if style == "orange_tree":
        size = max(1, spec.get_int("size", 1))
        return SwayingTree((x, y), _cached(("orange_tree", size), lambda: art.orange_tree(size)), f"orange{size}", True, layer)
    if style == "cypress":
        height = spec.get_int("height", 110)
        return SwayingTree((x, y), _cached(("cypress", height), lambda: art.cypress(height)), f"cypress{height}", False, layer)
    if style == "palm":
        height = spec.get_int("height", 120)
        return SwayingTree((x, y), _cached(("palm", height), lambda: art.palm(height)), f"palm{height}", False, layer)
    if style == "column":
        height = spec.get_int("height", 96)
        return ImageDecor((x, y), _cached(("column", height), lambda: art.column(height)), layer)
    if style == "urn":
        return ImageDecor((x, y), _cached(("urn",), art.urn), layer)
    if style == "lion_statue":
        image = _cached(("lion_statue",), art.lion_statue)
        if spec.get_str("facing", "right") == "left":
            image = pygame.transform.flip(image, True, False)
        return ImageDecor((x, y), image, layer)
    if style == "lion_fountain":
        return LionFountain((x, y))
    if style == "lamp":
        return HangingLamp((spec.rect.centerx, spec.rect.top), spec.get_float("chain", 40))
    if style == "banner":
        color = (170, 30, 44) if spec.get_str("color", "red") == "red" else (40, 90, 160)
        return Banner((spec.rect.x + 6, spec.rect.top), color)
    if style == "gear":
        radius = spec.get_int("radius", 48)
        image = _cached(("gear", radius), lambda: gear_image(radius, (150, 104, 56)))
        return Rotator(spec.rect.center, image, spec.get_float("speed", 30))
    if style == "astrolabe":
        return Astrolabe((x, y))
    if style == "water_clock":
        return WaterClock((x, y))
    if style == "pigeons":
        return Pigeons((x, y), spec.get_int("count", 5))
    if style == "butterflies":
        return Butterflies(spec.rect.center, spec.get_int("count", 3))
    if style == "koi":
        return Koi((x, y), spec.get_float("span", 70))
    if style == "torch":
        return Torch((x, y))
    if style == "light_shaft":
        return LightShaft(spec.rect)
    if style == "fountain":
        return Fountainlet((x, y))
    return None


class LionFountain(Prop):
    """The Fountain of the Lions, with water arcing from the lions' mouths."""

    layer = "back"

    def __init__(self, midbottom: tuple[float, float]) -> None:
        image = _cached(("lion_fountain",), art.lion_fountain)
        super().__init__(image.get_rect(midbottom=(round(midbottom[0]), round(midbottom[1]))))
        self._image = image
        self.flowing = True

    def update(self, dt: float, world: "World") -> None:
        if not self.flowing or not world.on_screen(self.rect, 0):
            return
        rng = world.particles.rng
        for mouth_x, direction in ((self.rect.left + 44, -1), (self.rect.right - 44, 1), (self.rect.centerx, 0)):
            if rng.random() < 0.6:
                vx = direction * rng.uniform(40, 70) if direction else rng.uniform(-30, 30)
                y = self.rect.top + (4 if direction == 0 else 70)
                vy = -rng.uniform(140, 200) if direction == 0 else -rng.uniform(40, 80)
                emitters.droplet(world.particles, mouth_x, y, vx, vy)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        surface.blit(self._image, camera.to_screen(self.rect.x, self.rect.y))
