"""Parchment speech bubbles for signs and story captions."""

import pygame

from core import settings
from ui.text import wrap_text

PADDING = 10
TAIL = 9
MAX_WIDTH = 260
LINE_GAP = 2
BORDER = (120, 84, 44)


def make_bubble(font: pygame.font.Font, text: str, max_width: int = MAX_WIDTH) -> pygame.Surface:
    """A rounded parchment box with a tail pointing down at its centre."""
    lines = wrap_text(font, text, max_width - PADDING * 2)
    rendered = [font.render(line, True, settings.INK) for line in lines]
    line_height = font.get_linesize() + LINE_GAP
    width = max((image.get_width() for image in rendered), default=20) + PADDING * 2
    height = line_height * len(rendered) - LINE_GAP + PADDING * 2
    surface = pygame.Surface((width, height + TAIL), pygame.SRCALPHA)
    box = pygame.Rect(0, 0, width, height)
    pygame.draw.rect(surface, (40, 26, 20, 90), box.move(0, 3), border_radius=9)
    pygame.draw.rect(surface, settings.PARCHMENT, box, border_radius=9)
    pygame.draw.rect(surface, BORDER, box, 2, border_radius=9)
    cx = width // 2
    tail = [(cx - TAIL, height - 2), (cx + TAIL, height - 2), (cx, height + TAIL - 1)]
    pygame.draw.polygon(surface, settings.PARCHMENT, tail)
    pygame.draw.lines(surface, BORDER, False, [tail[0], tail[2], tail[1]], 2)
    for index, image in enumerate(rendered):
        surface.blit(image, image.get_rect(midtop=(cx, PADDING + index * line_height)))
    return surface
