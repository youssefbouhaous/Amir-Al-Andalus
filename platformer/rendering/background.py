"""Layered parallax background: sky, sun or moon, clouds, silhouettes, birds.

Scrolling a layer at a fraction of the camera speed makes it look far away.
Layers also scroll vertically (by the same fraction) so tall levels feel
tall: climb high and the city sinks below you. Everything is pre-rendered
once per theme; each frame is a handful of blits.
"""

import math
import random

import pygame

from core.settings import Color
from rendering.art import scenery
from rendering.art.kit import vertical_gradient
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.themes import Layer, Theme, get_theme

CLOUD_PARALLAX = (0.03, 0.09)
CLOUD_SPEED = (4.0, 14.0)
TWINKLE_STARS = 36


def create_vertical_gradient(size: tuple[int, int], top_color: Color, bottom_color: Color) -> pygame.Surface:
    """Pre-render a top-to-bottom gradient once, so each frame is a single blit."""
    return vertical_gradient(size, ((0.0, top_color), (1.0, bottom_color))).convert()


def _render_layer(layer: Layer) -> pygame.Surface:
    if layer.kind == "mountains":
        image = scenery.mountains(layer.height, layer.color, layer.snow, layer.seed)
    elif layer.kind == "hills":
        image = scenery.hills(layer.height, layer.color, layer.seed)
    elif layer.kind == "skyline":
        image = scenery.skyline(layer.style or "generic", layer.height, layer.color, layer.seed, layer.windows)
    else:
        image = scenery.tree_line(layer.style or "mixed", layer.height, layer.color, layer.seed, layer.snow)
    return image.convert_alpha()


class _Flock:
    def __init__(self, rng: random.Random, width: int, height: int, frames: list[pygame.Surface]) -> None:
        self.direction = rng.choice((-1, 1))
        self.x = -60.0 if self.direction > 0 else width + 60.0
        self.y = rng.uniform(height * 0.12, height * 0.4)
        self.speed = rng.uniform(40, 70)
        self.members = [(i * -18 * self.direction + rng.uniform(-4, 4), abs(i - 2) * 7 + rng.uniform(-3, 3), rng.random())
                        for i in range(rng.randrange(3, 7))]
        self.frames = frames if self.direction > 0 else [pygame.transform.flip(f, True, False) for f in frames]
        self.time = 0.0
        self.width = width

    @property
    def done(self) -> bool:
        return (self.direction > 0 and self.x > self.width + 200) or (self.direction < 0 and self.x < -200)

    def update(self, dt: float) -> None:
        self.time += dt
        self.x += self.direction * self.speed * dt
        self.y += math.sin(self.time * 1.3) * 6 * dt

    def draw(self, surface: pygame.Surface) -> None:
        for dx, dy, phase in self.members:
            frame = self.frames[int((self.time * 8 + phase * 4)) % len(self.frames)]
            surface.blit(frame, (round(self.x + dx), round(self.y + dy)))


class ParallaxBackground:
    def __init__(self, screen_size: tuple[int, int], theme_name: str, level_height: int | None = None) -> None:
        self.theme: Theme = get_theme(theme_name)
        theme = self.theme
        self._size = screen_size
        width, height = screen_size
        self._sky = vertical_gradient(screen_size, theme.sky).convert()
        self._rng = random.Random(hash(theme.name) & 0xFFFF)
        self._time = 0.0
        self._level_height = level_height if level_height is not None else height
        self._horizon = round(height * theme.horizon)

        # Stars: a static field baked into the sky plus a few that twinkle.
        self._twinkles: list[tuple[int, int, float, float]] = []
        if theme.stars:
            rng = random.Random(7)
            for _ in range(theme.stars):
                x, y = rng.randrange(width), rng.randrange(int(height * 0.75))
                level = rng.randrange(120, 230)
                self._sky.fill((level, level, min(255, level + 20)), (x, y, 1, 1))
            for _ in range(TWINKLE_STARS):
                self._twinkles.append((rng.randrange(width), rng.randrange(int(height * 0.6)),
                                       rng.uniform(0.6, 2.2), rng.uniform(0, math.tau)))

        self._celestial = None
        if theme.celestial == "moon":
            self._celestial = scenery.moon(theme.celestial_radius, theme.celestial_color).convert_alpha()
        elif theme.celestial == "sun":
            self._celestial = scenery.sun(theme.celestial_radius, theme.celestial_color).convert_alpha()

        self._clouds: list[list] = []
        for index in range(theme.clouds):
            w = self._rng.randrange(110, 240)
            image = scenery.cloud(w, w // 3, theme.cloud_color, theme.cloud_shade, index * 17 + 3).convert_alpha()
            image.set_alpha(self._rng.randrange(170, 240))
            self._clouds.append([
                self._rng.uniform(0, width + 300), self._rng.uniform(height * 0.05, height * 0.42),
                self._rng.uniform(*CLOUD_SPEED), self._rng.uniform(*CLOUD_PARALLAX), image,
            ])

        self._layers = [(layer, _render_layer(layer)) for layer in theme.layers]
        self._bird_frames = scenery.bird_frames(theme.bird_color) if theme.birds else []
        self._flocks: list[_Flock] = []
        self._next_flock = self._rng.uniform(2, 8)
        self._shooting: list[list[float]] = []
        self._next_shooting = self._rng.uniform(4, 10)

    # --- update -------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._time += dt
        width, height = self._size
        for cloud in self._clouds:
            cloud[0] -= cloud[2] * dt
            if cloud[0] < -cloud[4].get_width() - 200:
                cloud[0] = width + self._rng.uniform(100, 400)
                cloud[1] = self._rng.uniform(height * 0.05, height * 0.42)
        if self._bird_frames:
            self._next_flock -= dt
            if self._next_flock <= 0:
                self._flocks.append(_Flock(self._rng, width, height, self._bird_frames))
                self._next_flock = self._rng.uniform(9, 20)
            for flock in self._flocks:
                flock.update(dt)
            self._flocks = [f for f in self._flocks if not f.done]
        if self.theme.shooting_stars:
            self._next_shooting -= dt
            if self._next_shooting <= 0:
                self._next_shooting = self._rng.uniform(5, 14)
                self._shooting.append([self._rng.uniform(width * 0.2, width), self._rng.uniform(10, height * 0.3),
                                       self._rng.uniform(-520, -380), self._rng.uniform(140, 220), 0.0])
            for star in self._shooting:
                star[0] += star[2] * dt
                star[1] += star[3] * dt
                star[4] += dt
            self._shooting = [s for s in self._shooting if s[4] < 0.8]

    # --- draw -----------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera | None = None, scroll: float | None = None) -> None:
        width, height = self._size
        surface.blit(self._sky, (0, 0))
        cam_x = camera.position.x if camera is not None else (scroll or 0.0)
        cam_y = camera.position.y if camera is not None else self._level_height - height
        rise = (self._level_height - height) - cam_y  # how far the camera is above the bottom

        for x, y, speed, phase in self._twinkles:
            brightness = 0.5 + 0.5 * math.sin(self._time * speed + phase)
            value = int(150 + 105 * brightness)
            surface.fill((value, value, 255), (x, y, 2 if brightness > 0.85 else 1, 1))
        for star in self._shooting:
            fade = 1.0 - star[4] / 0.8
            tail = (star[0] - star[2] * 0.08, star[1] - star[3] * 0.08)
            pygame.draw.line(surface, (int(255 * fade), int(255 * fade), int(240 * fade)), tail, (star[0], star[1]), 2)

        theme = self.theme
        if self._celestial is not None:
            cx = width * theme.celestial_pos[0] - cam_x * 0.01
            cy = height * theme.celestial_pos[1] + rise * 0.02
            radius = theme.celestial_radius
            blit_glow(surface, (cx, cy), radius * 5, theme.celestial_glow, 0.55)
            blit_glow(surface, (cx, cy), int(radius * 2.2), theme.celestial_glow, 0.8)
            surface.blit(self._celestial, self._celestial.get_rect(center=(round(cx), round(cy))))

        for x, y, _speed, parallax, image in self._clouds:
            cloud_w = image.get_width()
            span = width + cloud_w + 400
            draw_x = (x - cam_x * parallax) % span - cloud_w - 200
            surface.blit(image, (round(draw_x), round(y + rise * parallax)))

        for flock in self._flocks:
            flock.draw(surface)

        for layer, image in self._layers:
            strip_w, strip_h = image.get_size()
            top = self._horizon + layer.drop - strip_h + round(rise * layer.parallax)
            offset = -round(cam_x * layer.parallax) % strip_w
            for x in (offset - strip_w, offset):
                if x < width and x + strip_w > 0:
                    surface.blit(image, (x, top))
            bottom = top + strip_h
            if bottom < height:
                surface.fill(layer.color, (0, bottom, width, height - bottom))
