import math

import pygame

from rendering.camera import Camera


class MovingPlatform:
    """A one-way platform moving back and forth along one axis.

    Motion follows a cosine curve so it eases in and out at the ends instead of
    snapping direction. ``delta`` (how far it moved this step) is what bodies
    standing on it add to their own movement, which is how the player rides it
    through the normal collision code rather than being teleported.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        horizontal: bool,
        distance: float,
        speed: float,
        image: pygame.Surface,
        reverse: bool = False,
    ) -> None:
        self._origin = pygame.Vector2(rect.x, rect.y)
        self.width = rect.width
        self.height = rect.height
        direction = pygame.Vector2(1, 0) if horizontal else pygame.Vector2(0, 1)
        self._direction = -direction if reverse else direction
        self._distance = distance
        # Chosen so the average speed over one pass equals ``speed``.
        self._angular_speed = math.pi * speed / distance if distance > 0 else 0.0
        self._phase = 0.0
        self._image = image

        self.position = pygame.Vector2(self._origin)
        self.delta = pygame.Vector2()
        self._previous_top = self.position.y

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

    def update(self, dt: float) -> None:
        previous = pygame.Vector2(self.position)
        self._phase += self._angular_speed * dt
        offset = self._distance * (1.0 - math.cos(self._phase)) / 2.0
        self.position = self._origin + self._direction * offset
        self.delta = self.position - previous
        self._previous_top = previous.y

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        tile_width = self._image.get_width()
        for x in range(0, self.width, tile_width):
            surface.blit(self._image, camera.to_screen(self.position.x + x, self.position.y))
