"""Level results, persistent records and the next step of the campaign."""

import math
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.campaign import next_level
from core.session import GameSession
from scenes.message_scene import MessageScene
from ui.text import GOLD_TITLE, draw_text
from world.level_data import LevelData

if TYPE_CHECKING:
    from core.context import GameContext


class TallyScene(MessageScene):
    def __init__(self, context: "GameContext", session: GameSession, level: LevelData) -> None:
        super().__init__(context, "Level Complete!", [])
        self._session = session
        self._level = level
        self._next_level = next_level(level.file_name, level.next_level)
        self._recorded = False
        self._title_font = context.assets.get_font(54, "display")
        self._small_font = context.assets.get_font(settings.SMALL_FONT_SIZE)
        par_time = level.get_float("par_time", 0.0)
        remaining = max(0, math.floor(par_time - session.level_time)) if math.isfinite(par_time) else 0
        self.time_bonus = remaining * settings.TIME_BONUS_PER_SECOND

    def on_enter(self) -> None:
        # Persist before input is accepted, even if the player quits here.
        if self._recorded:
            return
        self._recorded = True
        session = self._session
        session.score += self.time_bonus
        save = self.context.save
        record = save.data.record(self._level.file_name)
        record.completed = True
        if session.replay:
            record.best_replay_score = max(record.best_replay_score or 0, session.score)
        else:
            record.best_score = max(record.best_score, session.score)
        if record.best_time is None or session.level_time < record.best_time:
            record.best_time = session.level_time
        record.merge_pages(session.pages_found)
        if not self._next_level:
            save.data.game_completed = True
        save.save()
        self.context.audio.stop_music()
        self.context.audio.play_jingle("fanfare")

    def on_continue(self) -> None:
        from scenes.end_scenes import VictoryScene
        from scenes.level_intro_scene import LevelIntroScene

        if self._session.replay:
            from scenes.level_select_scene import LevelSelectScene

            self.context.scenes.replace(LevelSelectScene(self.context, self._level.file_name))
            return
        if self._next_level:
            self._session.enter_level(self._next_level)
            self.context.scenes.replace(LevelIntroScene(self.context, self._session))
        else:
            self.context.scenes.replace(VictoryScene(self.context, self._session))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(settings.MENU_BACKGROUND_COLOR)
        center_x = surface.get_width() // 2
        draw_text(surface, self._title_font, self._title, style=GOLD_TITLE, center=(center_x, 92))
        draw_text(surface, self._line_font, self._level.name, center=(center_x, 160))
        minutes, seconds = divmod(int(self._session.level_time), 60)
        page_count = len(self._level.objects_of("page"))
        rows = [
            ("Time", f"{minutes}:{seconds:02d}"),
            ("Dinars / enemies", f"{self._session.level_coins} / {self._session.level_enemies}"),
            ("Pages found", f"{len(self._session.pages_found)} / {page_count}"),
            ("Time bonus", f"+{self.time_bonus}"),
            ("Total score", str(self._session.score)),
        ]
        for index, (label, value) in enumerate(rows):
            y = 229 + index * 39
            draw_text(surface, self._line_font, label, midleft=(center_x - 240, y))
            draw_text(surface, self._line_font, value, settings.GOLD_LIGHT, midright=(center_x + 240, y))
        prompt = "Progress saved  -  Enter: level select" if self._session.replay else "Progress saved  -  Press Enter to continue"
        draw_text(surface, self._small_font, prompt, center=(center_x, 470))
