"""Skippable, save-aware interludes; existing menus and gameplay UI stay intact."""

import pygame

from core.input import Action
from core.story import StorySequence, should_play
from rendering.story_stage import StoryStage
from scenes.message_scene import INPUT_GRACE_PERIOD
from scenes.scene import Scene
from ui.text import GOLD_TITLE, draw_text, wrap_text


def with_story(context, session, sequence, following):
    """Wrap a destination only on a journey's first visit, never on retries/replays."""
    return StoryScene(context, sequence, following) if should_play(sequence, session, context.save.data) else following


class StoryScene(Scene):
    def __init__(self, context, sequence: StorySequence, following: Scene):
        super().__init__(context)
        self.sequence = sequence
        self.following = following
        self.index = 0
        self.elapsed = 0.0
        self._done = False
        self._stage = StoryStage(sequence, context.sprites, (960, 540))
        self._title_font = context.assets.get_font(36, "display")
        self._body_font = context.assets.get_font(24, "body")
        self._small_font = context.assets.get_font(17, "ui")
        self._lines = [wrap_text(self._body_font, beat.text, 790) for beat in sequence.beats]
        self._panel = pygame.Surface((960, 192), pygame.SRCALPHA)
        self._panel.fill((14, 13, 27, 224))

    def on_enter(self):
        self.context.audio.play_music(self.sequence.music)

    def update(self, dt):
        if self._done:
            return
        self.elapsed += dt
        self._stage.update(dt)
        inputs = self.context.input
        if self.elapsed >= INPUT_GRACE_PERIOD:
            if inputs.was_pressed(Action.BACK) or inputs.was_pressed(Action.PAUSE):
                self.finish()
                return
            if inputs.was_pressed(Action.CONFIRM):
                self._next()
                return
        if self.elapsed >= self.sequence.beats[self.index].duration:
            self._next()

    def _next(self):
        if self.index + 1 == len(self.sequence.beats):
            self.finish()
        else:
            self.index += 1
            self.elapsed = 0.0

    def finish(self):
        if self._done:
            return
        self._done = True
        self.context.save.data.story_seen.add(self.sequence.key)
        self.context.save.save()
        # A Confirm/Jump used for the story must not become the first game input.
        self.context.input.end_step()
        self.context.scenes.replace(self.following)

    def draw(self, surface):
        beat = self.sequence.beats[self.index]
        self._stage.draw(surface, beat, self.elapsed)
        draw_text(surface, self._title_font, self.sequence.title, style=GOLD_TITLE, center=(480, 53))
        surface.blit(self._panel, (0, 348))
        pygame.draw.line(surface, (152, 119, 66), (85, 348), (875, 348))
        draw_text(surface, self._small_font, beat.speaker, (245, 207, 133), center=(480, 373))
        for row, line in enumerate(self._lines[self.index]):
            draw_text(surface, self._body_font, line, (249, 239, 215), center=(480, 407 + row * 31))
        draw_text(surface, self._small_font, "Enter: continue   Esc: skip scene", (191, 180, 171), center=(480, 516))
