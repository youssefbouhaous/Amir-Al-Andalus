"""Heads-up display. Drawn in screen space after the world, so it never
scrolls; it only *reads* the session and never changes it."""

import pygame

from core import settings
from core.assets import AssetManager
from core.session import GameSession
from rendering.placeholder_art import make_coin_icon, make_heart_icon
from ui.text import render_text

MAX_CACHED_TEXTS = 64
HEALTH_SLOTS = 2


class Hud:
    def __init__(self, assets: AssetManager) -> None:
        self._font = assets.get_font(settings.HUD_FONT_SIZE)
        self._coin_icon = assets.get_image("hud_coin.png", make_coin_icon)
        heart = assets.get_image("hud_heart.png", make_heart_icon)
        self._heart_full = heart
        self._heart_empty = heart.copy()
        self._heart_empty.set_alpha(70)
        # Text only changes when values change, so cache rendered surfaces.
        self._texts: dict[str, pygame.Surface] = {}

    def draw(self, surface: pygame.Surface, session: GameSession, powered: bool) -> None:
        margin = settings.HUD_MARGIN
        gap = settings.HUD_ICON_GAP
        width = surface.get_width()

        surface.blit(self._text(f"SCORE {session.score:07d}"), (margin, margin))

        coins = self._text(f"x {session.coins:02d}")
        coins_x = width // 3
        surface.blit(self._coin_icon, (coins_x, margin + 2))
        surface.blit(coins, (coins_x + self._coin_icon.get_width() + gap, margin))

        level = self._text(session.level_name)
        surface.blit(level, level.get_rect(midtop=(width * 3 // 5, margin)))

        lives = self._text(f"LIVES {session.lives}")
        lives_rect = lives.get_rect(topright=(width - margin, margin))
        surface.blit(lives, lives_rect)

        health = 2 if powered else 1
        heart_width = self._heart_full.get_width()
        x = lives_rect.left - gap - HEALTH_SLOTS * (heart_width + gap)
        for slot in range(HEALTH_SLOTS):
            heart = self._heart_full if slot < health else self._heart_empty
            surface.blit(heart, (x + slot * (heart_width + gap), margin))

    def _text(self, text: str) -> pygame.Surface:
        image = self._texts.get(text)
        if image is None:
            if len(self._texts) > MAX_CACHED_TEXTS:
                self._texts.clear()
            image = render_text(self._font, text)
            self._texts[text] = image
        return image
