"""Side-scrolling camera.

World objects never move to fake scrolling. Everything keeps its world
coordinates, and only at draw time do we convert:

    screen_position = world_position - camera_position

The camera itself is just a position (its top-left corner in the world) plus
rules for moving that position: a dead zone, exponential smoothing, and
clamping to bounds so it never shows outside the map.
"""

import math

import pygame

from core.settings import CAMERA, CameraSettings


class Camera:
    def __init__(
        self,
        viewport_size: tuple[int, int],
        bounds: pygame.Rect,
        config: CameraSettings = CAMERA,
    ) -> None:
        self.width, self.height = viewport_size
        self.position = pygame.Vector2()
        self._bounds = pygame.Rect(bounds)
        self._config = config
        # Added to the rounded offset at draw time; set by the screen shake.
        self.shake = (0.0, 0.0)
        # Horizontal lead toward where the player is heading.
        self._lead = 0.0

    @property
    def bounds(self) -> pygame.Rect:
        return self._bounds

    def set_bounds(self, bounds: pygame.Rect) -> None:
        self._bounds = pygame.Rect(bounds)

    @property
    def offset(self) -> tuple[int, int]:
        # Rounded once here so every object on screen shifts by the same whole
        # pixel amount; rounding each object separately causes shimmering.
        return round(self.position.x + self.shake[0]), round(self.position.y + self.shake[1])

    @property
    def view_rect(self) -> pygame.Rect:
        x, y = self.offset
        return pygame.Rect(x, y, self.width, self.height)

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        offset_x, offset_y = self.offset
        return round(x) - offset_x, round(y) - offset_y

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        offset_x, offset_y = self.offset
        return rect.move(-offset_x, -offset_y)

    def dead_zone(self) -> pygame.Rect:
        """The dead zone in world coordinates (for the debug overlay)."""
        zone = pygame.Rect(0, 0, self._config.dead_zone_width, self._config.dead_zone_height)
        zone.center = (
            round(self.position.x + self.width / 2),
            round(self.position.y + self.height / 2 - self._config.vertical_offset),
        )
        return zone

    def snap_to(self, target: tuple[float, float], lead_direction: int = 0) -> None:
        self._lead = lead_direction * self._config.look_ahead
        self.position.update(
            target[0] + self._lead - self.width / 2,
            target[1] + self._config.vertical_offset - self.height / 2,
        )
        self._clamp()

    def follow(self, target: tuple[float, float], dt: float, lead_direction: int = 0) -> None:
        """Track ``target``; ``lead_direction`` (-1/0/1) shifts the view ahead."""
        lead_blend = 1.0 - math.exp(-self._config.look_ahead_smoothing * dt)
        self._lead += (lead_direction * self._config.look_ahead - self._lead) * lead_blend
        desired = self._desired_position((target[0] + self._lead, target[1]))
        blend = 1.0 - math.exp(-self._config.smoothing * dt)
        self.position += (desired - self.position) * blend
        self._clamp()

    def pan_to(self, target: tuple[float, float], dt: float, smoothing: float = 3.0) -> None:
        """Cinematic move: glide the view centre toward ``target`` ignoring the dead zone."""
        desired = pygame.Vector2(target[0] - self.width / 2, target[1] - self.height / 2)
        self.position += (desired - self.position) * (1.0 - math.exp(-smoothing * dt))
        self._clamp()

    def _desired_position(self, target: tuple[float, float]) -> pygame.Vector2:
        focus_x = self.position.x + self.width / 2
        focus_y = self.position.y + self.height / 2 - self._config.vertical_offset
        half_zone_w = self._config.dead_zone_width / 2
        half_zone_h = self._config.dead_zone_height / 2

        # Only move once the target leaves the dead zone, and only far enough
        # to put it back on the zone's edge.
        if target[0] > focus_x + half_zone_w:
            focus_x = target[0] - half_zone_w
        elif target[0] < focus_x - half_zone_w:
            focus_x = target[0] + half_zone_w
        if target[1] > focus_y + half_zone_h:
            focus_y = target[1] - half_zone_h
        elif target[1] < focus_y - half_zone_h:
            focus_y = target[1] + half_zone_h

        return pygame.Vector2(
            focus_x - self.width / 2,
            focus_y + self._config.vertical_offset - self.height / 2,
        )

    def _clamp(self) -> None:
        self.position.x = _clamp_axis(self.position.x, self.width, self._bounds.left, self._bounds.right)
        self.position.y = _clamp_axis(self.position.y, self.height, self._bounds.top, self._bounds.bottom)


def _clamp_axis(value: float, view_size: float, low: float, high: float) -> float:
    if high - low <= view_size:
        # Area smaller than the screen: centre it instead of clamping.
        return low + (high - low - view_size) / 2
    return max(low, min(value, high - view_size))
