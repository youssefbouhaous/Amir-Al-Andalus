"""Heads-up display. Drawn in screen space after the world, so it never
scrolls; it only *reads* the session and world and never changes them.

Layout: a medallion with the prince's portrait, his hearts and lives on the
left; dinars and the three manuscript pages next to it; score and timer on
the right. Values that change "pop" (a quick scale bounce) so the eye
catches them. A sun/moon dial appears in levels with switch blocks, and a
health bar for the Ifrit during the final battle.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.assets import AssetManager
from core.session import GameSession
from rendering.art import prince
from rendering.art.items import make_coin_icon, make_page_icon
from rendering.art.kit import Canvas
from ui.text import HUD_STYLE, TextStyle, render_styled

if TYPE_CHECKING:
    from world.level_data import LevelData
    from world.world import World

HEART_RED = (228, 56, 86)
HEART_LIGHT = (255, 150, 170)
OUTLINE = (40, 20, 24)
PANEL = (20, 12, 28, 150)
TOAST_STYLE = TextStyle(gradient=((255, 244, 200), (240, 180, 70)), outline=(50, 24, 18), outline_width=2, shadow=None)
TITLE_STYLE = TextStyle(gradient=((255, 248, 214), (236, 172, 64)), outline=(46, 20, 16), outline_width=3,
                        shadow=(10, 4, 10), shadow_offset=(0, 4))
POP_TIME = 0.25
TOAST_TIME = 1.8
LEVEL_TITLE_TIME = 3.2


def _heart(full: bool, size: int = 18) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    s = size / 18
    points = [(9 * s, 16 * s), (1.5 * s, 8 * s), (1.5 * s, 4.5 * s), (4.5 * s, 2 * s), (7.5 * s, 2.5 * s),
              (9 * s, 4.5 * s), (10.5 * s, 2.5 * s), (13.5 * s, 2 * s), (16.5 * s, 4.5 * s), (16.5 * s, 8 * s)]
    if full:
        c.polygon(HEART_RED, points, OUTLINE, 1.2 * s)
        c.ellipse(HEART_LIGHT, (4 * s, 4 * s, 3.5 * s, 2.5 * s))
    else:
        c.polygon((70, 50, 64), points, OUTLINE, 1.2 * s)
    return c.finish()


def _medallion(size: int) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    r = size / 2
    c.star((214, 160, 60), (r, r), r - 1, outline=OUTLINE, width=1.2)
    c.circle((52, 30, 50), (r, r), r * 0.72, outline=(255, 226, 140), width=1.4)
    return c.finish()


def _dial(progress: float, active: str, size: int = 34) -> pygame.Surface:
    c = Canvas(size, size, fringe=OUTLINE)
    r = size / 2
    sun = (246, 190, 60)
    moon = (120, 150, 230)
    c.circle((40, 30, 50), (r, r), r - 1, outline=OUTLINE, width=1)
    color = sun if active == "sun" else moon
    # Remaining time as a filled wedge.
    points = [(r, r)]
    steps = 24
    remaining = 1.0 - progress
    for k in range(steps + 1):
        a = -math.pi / 2 + math.tau * remaining * k / steps
        points.append((r + math.cos(a) * (r - 3), r + math.sin(a) * (r - 3)))
    if remaining > 0.01:
        c.polygon(color, points)
    c.circle((250, 240, 220), (r, r), 4)
    return c.finish()


class _Pop:
    """Scale bounce when a displayed value changes."""

    def __init__(self) -> None:
        self.value: object = None
        self.timer = 0.0

    def watch(self, value: object) -> None:
        if value != self.value:
            if self.value is not None:
                self.timer = POP_TIME
            self.value = value

    def update(self, dt: float) -> None:
        self.timer = max(0.0, self.timer - dt)

    @property
    def scale(self) -> float:
        if self.timer <= 0:
            return 1.0
        t = 1.0 - self.timer / POP_TIME
        return 1.0 + 0.35 * math.sin(t * math.pi)


def _blit_scaled(surface: pygame.Surface, image: pygame.Surface, scale: float, **anchor) -> pygame.Rect:
    if abs(scale - 1.0) > 0.01:
        image = pygame.transform.smoothscale(
            image, (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
        )
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


class Hud:
    def __init__(self, assets: AssetManager, show_timer: bool = True) -> None:
        self._font = assets.get_font(settings.HUD_FONT_SIZE, "ui")
        self._small = assets.get_font(16, "ui")
        self._title_font = assets.get_font(46, "display")
        self._subtitle_font = assets.get_font(22, "body")
        self.show_timer = show_timer
        self._coin_icon = make_coin_icon(20).convert_alpha()
        self._page_on = make_page_icon(22, True).convert_alpha()
        self._page_off = make_page_icon(22, False).convert_alpha()
        # Pages found on an earlier visit: shown half-bright.
        self._page_known = self._page_on.copy()
        self._page_known.set_alpha(110)
        self.known_pages: set[int] = set()
        self._heart_full = _heart(True).convert_alpha()
        self._heart_empty = _heart(False).convert_alpha()
        self._medallion = _medallion(58).convert_alpha()
        self._portraits = [
            prince.portrait(palette, 36).convert_alpha()
            for palette in (prince.PRINCE_PALETTE, prince.PRINCE_POWERED_PALETTE, prince.PRINCE_STAR_PALETTE)
        ]
        self._pops = {name: _Pop() for name in ("coins", "lives", "score", "hearts", "pages")}
        self._page_flash = 0.0
        self._time = 0.0
        self._toast: pygame.Surface | None = None
        self._toast_timer = 0.0
        self._title: pygame.Surface | None = None
        self._subtitle: pygame.Surface | None = None
        self._title_timer = 0.0

    # --- updates ---------------------------------------------------------------
    def set_level(self, level: "LevelData") -> None:
        self._title = render_styled(self._title_font, level.name, TITLE_STYLE)
        self._subtitle = render_styled(self._subtitle_font, level.subtitle, HUD_STYLE) if level.subtitle else None
        self._title_timer = LEVEL_TITLE_TIME

    def toast(self, text: str) -> None:
        self._toast = render_styled(self._font, text, TOAST_STYLE)
        self._toast_timer = TOAST_TIME

    def flash_pages(self) -> None:
        self._page_flash = 1.0

    def update(self, dt: float, session: GameSession) -> None:
        self._time += dt
        self._toast_timer = max(0.0, self._toast_timer - dt)
        self._title_timer = max(0.0, self._title_timer - dt)
        self._page_flash = max(0.0, self._page_flash - dt * 1.5)
        self._pops["coins"].watch(session.coins)
        self._pops["lives"].watch(session.lives)
        self._pops["score"].watch(session.score)
        self._pops["hearts"].watch(session.power)
        self._pops["pages"].watch(len(session.pages_found))
        for pop in self._pops.values():
            pop.update(dt)

    # --- drawing ----------------------------------------------------------------
    def draw(self, surface: pygame.Surface, session: GameSession, world: "World") -> None:
        margin = settings.HUD_MARGIN
        width = surface.get_width()
        power = int(world.player.power)

        # Portrait medallion + hearts + lives.
        medallion_rect = surface.blit(self._medallion, (margin - 4, margin - 6))
        portrait = self._portraits[power]
        surface.blit(portrait, portrait.get_rect(center=medallion_rect.center))
        x = medallion_rect.right + 4
        for slot in range(3):
            heart = self._heart_full if slot <= power else self._heart_empty
            scale = self._pops["hearts"].scale if slot == power else 1.0
            _blit_scaled(surface, heart, scale, center=(x + 10 + slot * 21, margin + 9))
        lives = render_styled(self._font, f"x{session.lives}", HUD_STYLE)
        _blit_scaled(surface, lives, self._pops["lives"].scale, midleft=(x + 2, margin + 34))

        # Dinars.
        coins_x = x + 86
        surface.blit(self._coin_icon, self._coin_icon.get_rect(midleft=(coins_x, margin + 10)))
        coins = render_styled(self._font, f"{session.coins:02d}", HUD_STYLE)
        _blit_scaled(surface, coins, self._pops["coins"].scale, midleft=(coins_x + 24, margin + 10))

        # Manuscript pages (3 per level).
        pages_x = coins_x
        for index in range(settings.PAGES_PER_LEVEL):
            found = index in session.pages_found
            icon = self._page_on if found else self._page_off
            if not found and index in self.known_pages:
                icon = self._page_known
            center = (pages_x + 11 + index * 25, margin + 36)
            if found and self._page_flash > 0:
                bounce = 1.0 + 0.4 * self._page_flash * abs(math.sin(self._time * 12))
                _blit_scaled(surface, icon, bounce, center=center)
            else:
                surface.blit(icon, icon.get_rect(center=center))

        # Score and timer.
        score = render_styled(self._font, f"{session.score:07d}", HUD_STYLE)
        score_rect = _blit_scaled(surface, score, self._pops["score"].scale, topright=(width - margin, margin - 2))
        if self.show_timer:
            minutes, seconds = divmod(int(session.level_time), 60)
            timer = render_styled(self._small, f"{minutes}:{seconds:02d}", HUD_STYLE)
            surface.blit(timer, timer.get_rect(topright=(width - margin, score_rect.bottom)))

        switch = world.switch
        if switch is not None and switch.automatic and switch.blocks:
            dial = _dial(switch.progress, switch.active)
            surface.blit(dial, dial.get_rect(midtop=(width // 2, margin - 4)))

        if world.boss is not None:
            world.boss.draw_health_bar(surface, self._small)

        self._draw_title(surface)
        if self._toast is not None and self._toast_timer > 0:
            alpha = min(1.0, self._toast_timer / 0.4)
            image = self._toast.copy()
            image.set_alpha(round(255 * alpha))
            rise = (1.0 - min(1.0, (TOAST_TIME - self._toast_timer) / 0.25)) * 12
            surface.blit(image, image.get_rect(midtop=(width // 2, 64 + rise)))

    def _draw_title(self, surface: pygame.Surface) -> None:
        if self._title is None or self._title_timer <= 0:
            return
        elapsed = LEVEL_TITLE_TIME - self._title_timer
        appear = min(1.0, elapsed / 0.5)
        fade = min(1.0, self._title_timer / 0.6)
        alpha = round(255 * min(appear, fade))
        y = surface.get_height() * 0.28 + (1.0 - appear) ** 2 * 30
        title = self._title.copy()
        title.set_alpha(alpha)
        rect = surface.blit(title, title.get_rect(center=(surface.get_width() // 2, y)))
        if self._subtitle is not None:
            subtitle = self._subtitle.copy()
            subtitle.set_alpha(alpha)
            surface.blit(subtitle, subtitle.get_rect(midtop=(rect.centerx, rect.bottom + 2)))
