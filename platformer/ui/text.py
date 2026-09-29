"""Text rendering: drop shadows, outlines, gradient fills, and a render cache.

Rendering text with SDL_ttf is slow compared to blitting, and most text on
screen (menus, HUD labels) is identical from frame to frame, so every styled
render goes through a small LRU cache.
"""

from collections import OrderedDict
from dataclasses import dataclass

import pygame

from core import settings
from core.settings import Color
from ui.arabic import shape

SHADOW_OFFSET = 2
MAX_CACHED_TEXTS = 256


@dataclass(frozen=True)
class TextStyle:
    color: Color = settings.TEXT_COLOR
    # Vertical gradient (top, bottom) used instead of ``color`` when set.
    gradient: tuple[Color, Color] | None = None
    outline: Color | None = None
    outline_width: int = 0
    shadow: Color | None = settings.TEXT_SHADOW_COLOR
    shadow_offset: tuple[int, int] = (SHADOW_OFFSET, SHADOW_OFFSET)


PLAIN = TextStyle()
GOLD_TITLE = TextStyle(
    gradient=((255, 240, 170), (214, 146, 40)),
    outline=(70, 30, 20), outline_width=3,
    shadow=(20, 8, 16), shadow_offset=(0, 5),
)
HUD_STYLE = TextStyle(outline=(26, 16, 24), outline_width=2, shadow=None)
MENU_STYLE = TextStyle(outline=(30, 18, 26), outline_width=2, shadow=(10, 6, 12), shadow_offset=(0, 3))

_cache: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()


def _outline_offsets(width: int) -> list[tuple[int, int]]:
    offsets = []
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if (dx or dy) and dx * dx + dy * dy <= width * width + 1:
                offsets.append((dx, dy))
    return offsets


def _gradient_fill(image: pygame.Surface, top: Color, bottom: Color) -> pygame.Surface:
    """Tint white text with a vertical gradient (multiply keeps the alpha)."""
    width, height = image.get_size()
    gradient = pygame.Surface((1, max(1, height)), pygame.SRCALPHA)
    top_color, bottom_color = pygame.Color(*top), pygame.Color(*bottom)
    for y in range(height):
        gradient.set_at((0, y), top_color.lerp(bottom_color, y / max(1, height - 1)))
    gradient = pygame.transform.scale(gradient, (width, height))
    tinted = image.copy()
    tinted.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def render_styled(font: pygame.font.Font, text: str, style: TextStyle = PLAIN) -> pygame.Surface:
    key = (id(font), text, style)
    cached = _cache.get(key)
    if cached is not None:
        _cache.move_to_end(key)
        return cached

    if style.gradient is not None:
        fill = _gradient_fill(font.render(text, True, (255, 255, 255)), *style.gradient)
    else:
        fill = font.render(text, True, style.color)

    pad = style.outline_width if style.outline is not None else 0
    shadow_x, shadow_y = style.shadow_offset if style.shadow is not None else (0, 0)
    width = fill.get_width() + pad * 2 + abs(shadow_x)
    height = fill.get_height() + pad * 2 + abs(shadow_y)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    origin_x = pad + max(0, -shadow_x)
    origin_y = pad + max(0, -shadow_y)

    offsets = _outline_offsets(pad) if pad else []
    if style.shadow is not None:
        shadow = font.render(text, True, style.shadow)
        for dx, dy in offsets or [(0, 0)]:
            surface.blit(shadow, (origin_x + shadow_x + dx, origin_y + shadow_y + dy))
    if style.outline is not None and pad:
        outline = font.render(text, True, style.outline)
        for dx, dy in offsets:
            surface.blit(outline, (origin_x + dx, origin_y + dy))
    surface.blit(fill, (origin_x, origin_y))

    _cache[key] = surface
    if len(_cache) > MAX_CACHED_TEXTS:
        _cache.popitem(last=False)
    return surface


def render_text(
    font: pygame.font.Font, text: str, color: Color = settings.TEXT_COLOR, shadow: bool = True
) -> pygame.Surface:
    """Render text with an optional drop shadow for readability on any background."""
    style = TextStyle(color=color, shadow=settings.TEXT_SHADOW_COLOR if shadow else None)
    return render_styled(font, text, style)


def render_arabic(font: pygame.font.Font, text: str, style: TextStyle = PLAIN) -> pygame.Surface:
    return render_styled(font, shape(text), style)


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: Color = settings.TEXT_COLOR,
    style: TextStyle | None = None,
    **anchor: tuple[int, int] | int,
) -> pygame.Rect:
    """Draw text positioned by any Rect anchor, e.g. center=(x, y) or topleft=(x, y)."""
    image = render_styled(font, text, style) if style is not None else render_text(font, text, color)
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Greedy word wrap; explicit newlines start new paragraphs."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines
