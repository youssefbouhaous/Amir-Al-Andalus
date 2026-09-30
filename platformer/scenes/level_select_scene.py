"""Browse campaign progress and launch standalone runs without erasing saves."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from core import settings
from core.campaign import OPTIONAL_LEVELS, next_level
from core.input import Action
from core.save import LevelRecord
from core.session import GameSession
from rendering.background import ParallaxBackground
from scenes.scene import Scene
from ui.text import GOLD_TITLE, draw_text, wrap_text
from world.level_data import LevelData
from world.level_loader import LevelLoadError

if TYPE_CHECKING:
    from core.context import GameContext

PAGE_SIZE = 6
GOLD = (244, 207, 128)
MUTED = (165, 164, 177)
PANEL = (27, 27, 43)


def format_time(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return "--:--"
    tenths = max(0, round(seconds * 10))
    minutes, remainder = divmod(tenths, 600)
    return f"{minutes}:{remainder // 10:02d}.{remainder % 10}"


@dataclass(frozen=True)
class LevelEntry:
    level: LevelData
    unlocked: bool
    record: LevelRecord

    @property
    def page_count(self) -> int:
        return len(self.level.objects_of("page"))

    @property
    def found_pages(self) -> int:
        return len({page for page in self.record.pages if 0 <= page < self.page_count})

    def goals(self) -> list[str]:
        missing = self.page_count - self.found_pages
        pages = f"Find {missing} missing page{'s' if missing != 1 else ''}" if missing else "All pages collected!"
        if self.record.best_time is not None:
            timing = f"Beat your time: {format_time(self.record.best_time)}"
        else:
            par = self.level.get_float("par_time", 0.0)
            timing = f"Finish under par: {format_time(par)}" if par > 0 and math.isfinite(par) else "Finish this level"
        score = self.record.best_replay_score
        scoring = f"Beat your replay score: {score:,}" if score is not None else "Set your first replay score"
        return [pages, timing, scoring]


class LevelSelectScene(Scene):
    def __init__(self, context: "GameContext", selected_file: str | None = None) -> None:
        super().__init__(context)
        self._background = ParallaxBackground((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), settings.MENU_SKY_THEME)
        self._shade = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        self._shade.fill((10, 12, 24, 165))
        self._title_font = context.assets.get_font(42, "display")
        self._font = context.assets.get_font(22, "ui")
        self._small = context.assets.get_font(17, "ui")
        self._heading = context.assets.get_font(27, "display")
        self._elapsed = 0.0
        self._error = ""
        self.entries: list[LevelEntry] = []
        self._load_entries()
        self.selected = next((i for i, entry in enumerate(self.entries)
                              if entry.level.file_name == selected_file), 0)
        if selected_file is None:
            self.selected = next((i for i, entry in enumerate(self.entries)
                                  if entry.unlocked and not entry.record.completed), 0)
        self._back = pygame.Rect(32, 456, 120, 40)
        self._previous = pygame.Rect(236, 456, 112, 40)
        self._next = pygame.Rect(360, 456, 112, 40)
        self._play = pygame.Rect(548, 456, 360, 40)

    def _load_entries(self) -> None:
        file_name = settings.FIRST_LEVEL
        visited = set()
        previous_completed = True
        try:
            while file_name:
                if file_name in visited:
                    raise LevelLoadError("The campaign contains a circular next_level link")
                visited.add(file_name)
                level = self.context.levels.load(file_name)
                # Browsing must not create or overwrite saved records.
                record = self.context.save.data.levels.get(file_name, LevelRecord())
                self.entries.append(LevelEntry(level, previous_completed or record.completed, record))
                previous_completed = record.completed
                file_name = next_level(level.file_name, level.next_level)
        except LevelLoadError as error:
            self._error = str(error)
        for file_name in OPTIONAL_LEVELS:
            try:
                level = self.context.levels.load(file_name)
            except LevelLoadError:
                continue  # Optional content need not be installed in custom campaigns.
            record = self.context.save.data.levels.get(file_name, LevelRecord())
            self.entries.append(LevelEntry(level, True, record))

    @property
    def page(self) -> int:
        return self.selected // PAGE_SIZE

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(len(self.entries) / PAGE_SIZE))

    def on_enter(self) -> None:
        self.context.audio.play_music(settings.MENU_MUSIC)

    def _select(self, index: int) -> None:
        if not self.entries:
            return
        index = max(0, min(len(self.entries) - 1, index))
        if self.selected != index:
            self.selected = index
            self.context.audio.play("menu_move")

    def _change_page(self, delta: int) -> None:
        page = max(0, min(self.page_count - 1, self.page + delta))
        self._select(page * PAGE_SIZE + self.selected % PAGE_SIZE)

    def _back_to_title(self) -> None:
        from scenes.title_scene import TitleScene

        self.context.scenes.replace(TitleScene(self.context))

    def _start_selected(self) -> None:
        if not self.entries or not self.entries[self.selected].unlocked:
            return
        from scenes.level_intro_scene import LevelIntroScene

        entry = self.entries[self.selected]
        self.context.audio.play("menu_select")
        self.context.save.data.seen_intro = True
        self.context.save.save()
        self.context.scenes.replace(LevelIntroScene(
            self.context, GameSession(entry.level.file_name, replay=True)
        ))

    def update(self, dt: float) -> None:
        self._elapsed += dt
        self._background.update(dt)
        inputs = self.context.input
        if inputs.was_pressed(Action.BACK) or inputs.was_pressed(Action.PAUSE):
            self._back_to_title()
        elif inputs.was_pressed(Action.UP):
            self._select(self.selected - 1)
        elif inputs.was_pressed(Action.DOWN):
            self._select(self.selected + 1)
        elif inputs.was_pressed(Action.LEFT):
            self._change_page(-1)
        elif inputs.was_pressed(Action.RIGHT):
            self._change_page(1)
        elif inputs.was_pressed(Action.CONFIRM):
            self._start_selected()

    def _rows(self):
        start = self.page * PAGE_SIZE
        for row, index in enumerate(range(start, min(start + PAGE_SIZE, len(self.entries)))):
            yield index, pygame.Rect(32, 124 + row * 52, 468, 46)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self._select(self.selected - event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back.collidepoint(event.pos):
                self._back_to_title()
            elif self._previous.collidepoint(event.pos):
                self._change_page(-1)
            elif self._next.collidepoint(event.pos):
                self._change_page(1)
            elif self._play.collidepoint(event.pos):
                self._start_selected()
            else:
                for index, rect in self._rows():
                    if rect.collidepoint(event.pos):
                        self._select(index)
                        break

    def _button(self, surface, rect, label, enabled=True) -> None:
        pygame.draw.rect(surface, (64, 48, 54) if enabled else PANEL, rect, border_radius=7)
        pygame.draw.rect(surface, GOLD if enabled else MUTED, rect, 1, border_radius=7)
        draw_text(surface, self._small, label, GOLD if enabled else MUTED, center=rect.center)

    def draw(self, surface: pygame.Surface) -> None:
        self._background.draw(surface, scroll=self._elapsed * 12)
        surface.blit(self._shade, (0, 0))
        draw_text(surface, self._title_font, "Choose your chapter", style=GOLD_TITLE, center=(480, 48))
        completed = sum(entry.record.completed for entry in self.entries)
        draw_text(surface, self._small, f"{completed} / {len(self.entries)} completed   |   Page {self.page + 1} / {self.page_count}",
                  MUTED, center=(480, 94))
        for index, rect in self._rows():
            entry = self.entries[index]
            selected = index == self.selected
            pygame.draw.rect(surface, (62, 47, 55) if selected else PANEL, rect, border_radius=8)
            if selected:
                pygame.draw.rect(surface, GOLD, rect, 2, border_radius=8)
            color = GOLD if entry.unlocked else MUTED
            number = "+" if entry.level.file_name in OPTIONAL_LEVELS else f"{index + 1:02d}"
            draw_text(surface, self._small, number, color, midleft=(rect.left + 12, rect.centery))
            name = entry.level.name
            while self._small.size(name)[0] > 305:
                name = name[:-4].rstrip() + "..."
            draw_text(surface, self._small, name, color, midleft=(rect.left + 49, rect.centery))
            status = "CLEAR" if entry.record.completed else ("OPEN" if entry.unlocked else "LOCKED")
            if entry.level.file_name in OPTIONAL_LEVELS and not entry.record.completed:
                status = "BONUS"
            draw_text(surface, self._small, status, color, midright=(rect.right - 12, rect.centery))

        pygame.draw.rect(surface, PANEL, (524, 124, 404, 306), border_radius=12)
        if self.entries:
            self._draw_details(surface, self.entries[self.selected])
        else:
            draw_text(surface, self._font, "No levels available", center=(726, 240))
        self._button(surface, self._back, "Back")
        self._button(surface, self._previous, "< Previous", self.page > 0)
        self._button(surface, self._next, "Next >", self.page + 1 < self.page_count)
        unlocked = bool(self.entries and self.entries[self.selected].unlocked)
        self._button(surface, self._play, "Play / replay level" if unlocked else "Locked", unlocked)
        footer = "Up / Down: choose   Left / Right: page   Enter: play   Esc: back"
        if self._error:
            footer = "Some levels could not load. Return to the title and try again."
        draw_text(surface, self._small, footer, MUTED, center=(480, 517))

    def _draw_details(self, surface, entry: LevelEntry) -> None:
        record = entry.record
        heading = "REPLAY & PERSONAL BESTS" if entry.unlocked else "LOCKED CHAPTER"
        if entry.level.file_name in OPTIONAL_LEVELS:
            heading = "OPTIONAL MOVEMENT PLAYGROUND"
        draw_text(surface, self._small, heading,
                  GOLD, topleft=(548, 137))
        for index, line in enumerate(wrap_text(self._heading, entry.level.name, 350)[:2]):
            draw_text(surface, self._heading, line, GOLD, topleft=(548, 164 + index * 29))
        if not entry.unlocked:
            previous = self.entries[self.selected - 1].level.name
            lines = wrap_text(self._font, f"Complete {previous} to unlock this chapter.", 350)
            for index, line in enumerate(lines):
                draw_text(surface, self._font, line, MUTED, topleft=(548, 253 + index * 28))
            return
        score = f"{record.best_replay_score:,}" if record.best_replay_score is not None else "Not set"
        rows = [("Best time", format_time(record.best_time)), ("Best replay score", score),
                ("Manuscript pages", f"{entry.found_pages} / {entry.page_count}")]
        for index, (label, value) in enumerate(rows):
            y = 244 + index * 27
            draw_text(surface, self._small, label, MUTED, topleft=(548, y))
            draw_text(surface, self._small, value, GOLD, topright=(907, y))
        draw_text(surface, self._small, "YOUR NEXT GOALS", GOLD, topleft=(548, 334))
        for index, goal in enumerate(entry.goals()):
            draw_text(surface, self._small, goal, topleft=(548, 359 + index * 21))
