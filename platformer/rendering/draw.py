import pygame

from rendering.camera import Camera


def blit_midbottom(
    surface: pygame.Surface,
    image: pygame.Surface,
    camera: Camera,
    midbottom: tuple[float, float],
) -> None:
    """Draw a sprite so its bottom-centre sits on a world-space point.

    Sprites are anchored at the feet because the hitbox is usually smaller
    than the image (hair, hats, wings stick out) but the feet must touch the
    ground exactly.
    """
    screen_point = camera.to_screen(*midbottom)
    surface.blit(image, image.get_rect(midbottom=screen_point))
