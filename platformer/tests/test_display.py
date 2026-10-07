"""The window keeps the 960x540 frame sharp at any size: placement, pre-scale and mouse mapping.

Run with: python -m unittest tests.test_display -v
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from core.display import MAX_FACTOR, Display, enlargement, fit_view, frame_point


class DisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_a_maximised_1080p_window_is_letterboxed_and_prescaled_twice(self):
        view = fit_view((1920, 1011))
        self.assertEqual(view, pygame.Rect(62, 0, 1797, 1011))
        self.assertEqual(enlargement(view), 2, "enlarged past the window, so the fit only smooths seams")

    def test_exact_multiples_are_plain_whole_number_enlargements(self):
        self.assertEqual((fit_view((960, 540)), enlargement(fit_view((960, 540)))), (pygame.Rect(0, 0, 960, 540), 1))
        self.assertEqual((fit_view((1920, 1080)), enlargement(fit_view((1920, 1080)))), (pygame.Rect(0, 0, 1920, 1080), 2))
        self.assertEqual(enlargement(fit_view((3840, 2160))), 4)
        self.assertEqual(enlargement(fit_view((2560, 1440))), 3)
        self.assertEqual(enlargement(fit_view((7680, 4320))), MAX_FACTOR)

    def test_window_pixels_map_back_to_the_frame_pixel_shown_there(self):
        view = fit_view((1920, 1011))
        for fx, fy in [(0, 0), (100, 50), (480, 270), (959, 539)]:
            centre = (view.x + int((fx + 0.5) * view.width / 960), view.y + int((fy + 0.5) * view.height / 540))
            self.assertEqual(frame_point(view, centre), (fx, fy))
        self.assertLess(frame_point(view, (10, 500))[0], 0, "the black bars are outside the frame")

    def test_without_a_gpu_renderer_pygame_presents_the_frame_as_before(self):
        display = Display(fullscreen=False)
        self.assertFalse(display.sharp)
        self.assertEqual(display.frame.get_size(), (960, 540))
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(300, 200), button=1)
        self.assertIs(display.to_frame(click), click, "SDL already maps the mouse to the frame")
        display.frame.fill((40, 80, 120))
        display.present()
        display.close()


if __name__ == "__main__":
    unittest.main()
