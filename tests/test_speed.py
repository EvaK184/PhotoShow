"""Run with: python -m unittest discover -s tests -v."""

import os
import unittest
from unittest.mock import patch

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
# A hidden SDL window can report zero DPI on Windows.
os.environ["KIVY_DPI"] = "96"
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_METRICS_FONTSCALE"] = "1"

from kivy.config import Config

Config.set("graphics", "window_state", "hidden")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.image import Image

from main import PhotoFrame
from slideshow import PHOTO_DURATIONS, Slideshow


class PhotoTimingTests(unittest.TestCase):
    def setUp(self):
        self.schedule = patch("slideshow.Clock.schedule_interval").start()
        self.addCleanup(patch.stopall)
        # Use a real, empty Image widget without needing a user's photo folder.
        patch("slideshow.os.listdir", return_value=["photo.jpg"]).start()
        patch("slideshow.Image", side_effect=lambda **kwargs: Image()).start()

    def test_each_duration_is_used_when_playback_starts(self):
        show = Slideshow("unused")
        for seconds in PHOTO_DURATIONS:
            with self.subTest(seconds=seconds):
                show.set_photo_duration(seconds)
                self.assertFalse(show.is_playing)
                show.play()
                self.schedule.assert_called_with(show.next_photo, seconds)
                show.pause()

    def test_changing_duration_replaces_active_timer_once(self):
        show = Slideshow("unused")
        show.play()
        original_event = show.event
        show.set_photo_duration(30)
        original_event.cancel.assert_called_once()
        self.schedule.assert_called_with(show.next_photo, 30)
        self.assertTrue(show.is_playing)
        self.assertEqual(show.index, 0)
        show.set_photo_duration(30)
        self.assertEqual(self.schedule.call_count, 2)

    def test_invalid_duration_leaves_timer_unchanged(self):
        show = Slideshow("unused")
        show.play()
        with self.assertRaises(ValueError):
            show.set_photo_duration(10)
        self.assertEqual(show.photo_duration, 5)
        self.assertEqual(self.schedule.call_count, 1)

    def make_frame(self):
        frame = PhotoFrame()
        Window.add_widget(frame)
        self.addCleanup(Window.remove_widget, frame)
        self.addCleanup(lambda: frame.menu.dismiss(animation=False))
        return frame

    @staticmethod
    def settle_layout():
        for _ in range(5):
            Clock.tick()

    def test_speed_navigation_and_resume_with_selected_duration(self):
        frame = self.make_frame()
        frame.slideshow.play()
        menu = frame.menu
        menu.open(animation=False)
        self.settle_layout()
        main_size = menu.size[:]
        self.assertFalse(frame.slideshow.is_playing)
        menu.option_buttons[0].dispatch("on_release")
        self.settle_layout()
        self.assertLess(menu.height, main_size[1])
        self.assertLess(menu.width, main_size[0])
        self.assertIsNone(menu.main_content.parent)
        self.assertIs(menu.speed_content.parent, menu.overlay)

        slider = menu.speed_control.slider
        self.assertGreaterEqual(slider.x, menu.x)
        self.assertLessEqual(slider.right, menu.right)
        for tick in menu.speed_control.ticks:
            self.assertGreaterEqual(tick.points[3], slider.y)
            self.assertLess(tick.points[1], slider.center_y)
        for label in menu.speed_control.labels:
            self.assertGreaterEqual(label.x, menu.x)
            self.assertLessEqual(label.right, menu.right)
        for index, seconds in enumerate(PHOTO_DURATIONS):
            # Use cursor positions to exercise the slider's discrete mapping.
            slider.value_pos = (
                slider.x + slider.padding
                + (slider.width - 2 * slider.padding) * index / 3,
                slider.center_y,
            )
            self.assertEqual(frame.slideshow.photo_duration, seconds)
            self.assertEqual(menu.duration_label.text, f"{seconds} seconds per photo")

        menu.back_button.dispatch("on_release")
        self.settle_layout()
        self.assertEqual(menu.size, main_size)
        self.assertIs(menu.main_content.parent, menu.overlay)
        self.assertFalse(frame.slideshow.is_playing)
        menu.show_speed()
        self.assertEqual(slider.value, 3)
        menu.dismiss(animation=False)
        self.assertTrue(frame.slideshow.is_playing)
        self.schedule.assert_called_with(frame.slideshow.next_photo, 60)

        menu.open(animation=False)
        self.assertFalse(menu._speed_visible)
        menu.show_speed()
        self.assertEqual(slider.value, 3)

    def test_changing_speed_does_not_start_paused_slideshow(self):
        frame = self.make_frame()
        frame.menu.open(animation=False)
        frame.menu.show_speed()
        frame.menu.speed_control.slider.value = 1
        frame.menu.dismiss(animation=False)
        self.assertFalse(frame.slideshow.is_playing)
        self.assertEqual(frame.slideshow.photo_duration, 15)
        self.schedule.assert_not_called()


if __name__ == "__main__":
    unittest.main()
