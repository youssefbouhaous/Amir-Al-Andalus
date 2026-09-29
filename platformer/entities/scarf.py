"""The prince's turban tail: a tiny rope simulation (Verlet integration).

A chain of points is pinned at one end to the back of the turban. Each step
every free point keeps its previous velocity (position - previous position),
gets gravity and a little wind, then distance constraints pull neighbours
back to their rest length. The result trails, swings and flutters with every
movement for free, without any hand-made animation frames.
"""

import math

import pygame

from core.settings import Color
from rendering.camera import Camera

SEGMENTS = 7
SEGMENT_LENGTH = 3.4
GRAVITY = 520.0
DAMPING = 0.92
ITERATIONS = 4
OUTLINE: Color = (42, 24, 26)


class Scarf:
    def __init__(self, anchor: tuple[float, float], color: Color, tip_color: Color) -> None:
        self.color = color
        self.tip_color = tip_color
        self._points = [pygame.Vector2(anchor[0] - i * SEGMENT_LENGTH, anchor[1]) for i in range(SEGMENTS + 1)]
        self._previous = [pygame.Vector2(p) for p in self._points]
        self._time = 0.0

    def reset(self, anchor: tuple[float, float], facing: int) -> None:
        for index, (point, previous) in enumerate(zip(self._points, self._previous)):
            point.update(anchor[0] - facing * index * SEGMENT_LENGTH, anchor[1] + index * 0.5)
            previous.update(point)

    def set_colors(self, color: Color, tip_color: Color) -> None:
        self.color = color
        self.tip_color = tip_color

    def update(self, dt: float, anchor: tuple[float, float], facing: int, wind: float = 0.0) -> None:
        if dt <= 0:
            return
        self._time += dt
        points, previous = self._points, self._previous
        points[0].update(anchor)
        previous[0].update(anchor)
        # A gentle flutter pushes the tail away from the facing direction.
        flutter = math.sin(self._time * 9.0) * 22.0
        push_x = (-facing * 40.0 + wind) * dt * dt
        for index in range(1, len(points)):
            point, old = points[index], previous[index]
            velocity = (point - old) * DAMPING
            old.update(point)
            weight = index / SEGMENTS
            point.x += velocity.x + push_x * weight
            point.y += velocity.y + (GRAVITY + flutter * weight) * dt * dt
        for _ in range(ITERATIONS):
            for index in range(1, len(points)):
                a, b = points[index - 1], points[index]
                delta = b - a
                distance = delta.length()
                if distance == 0:
                    continue
                correction = delta * ((distance - SEGMENT_LENGTH) / distance)
                if index == 1:
                    b -= correction
                else:
                    a += correction * 0.5
                    b -= correction * 0.5
        # Never let the chain stretch out of shape after a teleport.
        for index in range(1, len(points)):
            a, b = points[index - 1], points[index]
            if a.distance_to(b) > SEGMENT_LENGTH * 3:
                b.update(a.x - facing * SEGMENT_LENGTH, a.y)
                previous[index].update(b)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        offset_x, offset_y = camera.offset
        screen = [(p.x - offset_x, p.y - offset_y) for p in self._points]
        count = len(screen)
        for index in range(count - 1):
            width = max(1, round(3.2 - 2.0 * index / count))
            pygame.draw.line(surface, OUTLINE, screen[index], screen[index + 1], width + 2)
        for index in range(count - 1):
            width = max(1, round(3.2 - 2.0 * index / count))
            color = self.tip_color if index >= count - 2 else self.color
            pygame.draw.line(surface, color, screen[index], screen[index + 1], width)
        tip = screen[-1]
        pygame.draw.circle(surface, self.tip_color, (round(tip[0]), round(tip[1])), 2)
