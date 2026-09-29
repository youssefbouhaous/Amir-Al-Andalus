"""Procedural sound recipes must work when their gameplay events fire."""

import os
import unittest

os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame

from audio.music import SR, render_jingle
from audio.synth import SOUND_RECIPES, _mix, synthesize, to_sound


class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=512)

    @classmethod
    def tearDownClass(cls):
        pygame.mixer.quit()

    def test_every_gameplay_sound_can_be_played(self):
        for name in SOUND_RECIPES:
            with self.subTest(sound=name):
                sound = synthesize(name)
                self.assertIsNotNone(sound)
                self.assertGreater(sound.get_length(), 0)

    def test_end_screen_jingles_can_be_played(self):
        for name in ("fanfare", "gameover", "sword"):
            with self.subTest(jingle=name):
                samples = render_jingle(name)
                self.assertIsNotNone(samples)
                self.assertEqual(samples.shape[1], 2)
                self.assertIsNotNone(to_sound(samples))

    def test_delayed_notes_are_not_cut_off(self):
        first = np.ones(100)
        last = np.full(200, 0.5)
        delay = 0.1
        mixed = _mix((first, 0), (last, delay))
        self.assertEqual(len(mixed), int(delay * SR) + len(last))
        np.testing.assert_array_equal(mixed[-len(last):], last)


if __name__ == "__main__":
    unittest.main()
