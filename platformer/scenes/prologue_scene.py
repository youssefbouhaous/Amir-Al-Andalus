"""The playable journey's opening film, before the first chapter card."""

import pygame

from core.input import Action
from core.prologue import DURATION, PROLOGUE_KEY, SHOTS, SOUND_CUES, sample
from rendering.prologue_stage import PrologueStage
from scenes.message_scene import INPUT_GRACE_PERIOD
from scenes.scene import Scene
from ui.text import GOLD_TITLE, draw_text, wrap_text


class PrologueScene(Scene):
    def __init__(self, context, following: Scene):
        super().__init__(context)
        self.following = following
        self.elapsed = 0.0
        self._since_input = 0.0
        self._done = False
        self._stage = PrologueStage(context.assets, context.sprites)
        self._font = context.assets.get_font(22, "body")
        self._small = context.assets.get_font(16, "ui")
        self._title = context.assets.get_font(38, "display")
        self._captions = tuple(wrap_text(self._font, shot.text, 838) for shot in SHOTS)
        self._caption_panel = pygame.Surface((960, 108), pygame.SRCALPHA)
        self._caption_panel.fill((16, 14, 25, 234))
        self._fade = pygame.Surface((960, 540))
        self._fade.fill((10, 9, 18))

    def on_enter(self):
        self.context.audio.play_music("story")

    def update(self, dt):
        if self._done:
            return
        dt = max(0.0, dt)
        self._since_input += dt
        inputs = self.context.input
        if self._since_input >= INPUT_GRACE_PERIOD:
            if inputs.was_pressed(Action.BACK) or inputs.was_pressed(Action.PAUSE):
                self.finish()
                return
            if inputs.was_pressed(Action.CONFIRM):
                self.next_shot()
                return
        previous = self.elapsed
        self.elapsed = min(DURATION, self.elapsed + dt)
        self._stage.update(dt)
        # Skips/large catch-up frames never produce a burst of out-of-context SFX.
        if dt <= .25:
            for at, sound, volume in SOUND_CUES:
                if previous < at <= self.elapsed:
                    self.context.audio.play(sound, volume)
        if self.elapsed >= DURATION:
            self.finish()

    def next_shot(self):
        if self._done:
            return
        current = sample(self.elapsed).shot
        if current == len(SHOTS) - 1:
            self.finish()
            return
        self.elapsed = SHOTS[current + 1].start
        self._since_input = 0.0
        self.context.input.end_step()

    def finish(self):
        if self._done:
            return
        self._done = True
        # A new key intentionally lets owners of the earlier text-only opening
        # see this film once on Continue, without resetting their saved journey.
        self.context.save.data.story_seen.update((PROLOGUE_KEY, "arrival:level1"))
        self.context.save.save()
        self.context.input.end_step()
        self.context.scenes.replace(self.following)

    def draw(self, surface):
        frame = sample(self.elapsed)
        self._stage.draw(surface, self.elapsed)
        pygame.draw.rect(surface, (16, 14, 25), (0, 0, 960, 34))
        draw_text(surface, self._small, "AMIR AL-ANDALUS  /  PROLOGUE", (219, 192, 133), topleft=(24, 8))
        draw_text(surface, self._small, "Enter: next moment   Esc: skip", (193, 186, 174), topright=(936, 8))
        if 1 < self.elapsed < 6:
            draw_text(surface, self._title, "The lantern promise", style=GOLD_TITLE, center=(480, 101))
        surface.blit(self._caption_panel, (0, 432))
        draw_text(surface, self._small, "AMIR", (249, 203, 121), center=(480, 448))
        lines = self._captions[frame.shot]
        first_y = 480 if len(lines) == 2 else 468 if len(lines) == 3 else 491
        for row, line in enumerate(lines):
            draw_text(surface, self._font, line, (247, 237, 214), center=(480, first_y + row * 25))
        if frame.fade > 0:
            self._fade.set_alpha(round(255 * frame.fade))
            surface.blit(self._fade, (0, 0))
