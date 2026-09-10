"""Mixed-media playback through the existing slideshow controls."""

import os
import unittest
from unittest.mock import patch

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_DPI"] = "96"
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_METRICS_FONTSCALE"] = "1"

from kivy.config import Config
Config.set("graphics", "window_state", "hidden")
from kivy.clock import Clock
from kivy.uix.video import Video

from main import PhotoFrame
from slideshow import PHOTO_DURATIONS, Slideshow
from test_speed import TimingImage


class PlaybackVideo(Video):
    """Real Kivy properties/events with decoding disabled for control tests."""

    def texture_update(self, *_args):
        pass

    def _do_video_load(self, *_args):
        pass


class VideoPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch("slideshow.random.shuffle").start()
        patch("slideshow.Image", TimingImage).start()
        patch("slideshow.Video", PlaybackVideo).start()
        self.schedule = patch("slideshow.Clock.schedule_interval").start()

    def make_show(self, paths):
        show = Slideshow()
        show.set_photos(paths)
        self.addCleanup(show.close)
        return show

    def test_media_follows_display_position_and_size_above_controls(self):
        frame = PhotoFrame(size_hint=(None, None))
        self.addCleanup(frame.close)
        show = frame.slideshow
        for size in ((800, 600), (400, 800), (1200, 500)):
            frame.size = size
            frame.pos = (30, 40)
            for source in ("photo.jpg", "clip.mp4", "another.png"):
                show.set_photos([source])
                for _ in range(5):
                    Clock.tick()
                media = show.video if show.video is not None else show.image
                self.assertEqual(media.pos, show.display.pos)
                self.assertEqual(media.size, show.display.size)
                controls = frame.playback_buttons[0].parent
                self.assertGreaterEqual(media.y, controls.top)
                self.assertEqual(media.top, frame.top)

    def test_video_uses_no_photo_timer_at_any_speed(self):
        show = self.make_show(["clip.MP4", "photo.jpg"])
        show.play()
        video = show.video
        video.position = 2.5
        for seconds in PHOTO_DURATIONS:
            show.set_photo_duration(seconds)
            self.assertIs(show.video, video)
            self.assertEqual(video.position, 2.5)
            self.assertEqual(video.state, "play")
            self.assertTrue(show.is_playing)
            self.assertEqual(show.index, 0)
        self.schedule.assert_not_called()

    def test_pause_resume_keeps_video_and_position(self):
        show = self.make_show(["clip.mp4"])
        self.assertFalse(show.is_playing)
        show.toggle_play()
        video = show.video
        video.position = 2.5
        show.toggle_play()
        self.assertEqual(video.state, "pause")
        self.assertFalse(show.is_playing)
        show.set_photo_duration(60)
        show.toggle_play()
        self.assertIs(show.video, video)
        self.assertEqual(video.position, 2.5)
        self.assertEqual(video.state, "play")
        self.schedule.assert_not_called()

    def test_photo_timer_is_cancelled_on_video_and_restarted_after_eos(self):
        show = self.make_show(["one.jpg", "clip.mp4", "two.png"])
        show.play()
        timer = show.event
        # Invoke the same callback that advances photos automatically.
        self.schedule.call_args.args[0](5)
        timer.cancel.assert_called_once()
        self.assertIsNone(show.event)
        self.assertEqual(show.video.state, "play")
        show.set_photo_duration(30)
        show.video._on_eos()
        self.assertEqual(show.index, 2)
        self.assertIsNone(show.video)
        self.assertEqual(show.image.opacity, 1)
        self.schedule.assert_called_with(show.next_photo, 30)

    def test_existing_buttons_pause_skip_and_go_back(self):
        frame = PhotoFrame()
        self.addCleanup(frame.close)
        frame.slideshow.set_photos(["one.mp4", "two.mov", "photo.jpg"])
        frame._update_controls()
        previous, play_pause, next_button = frame.playback_buttons
        play_pause.dispatch("on_press")
        first = frame.slideshow.video
        self.assertEqual(first.state, "play")
        next_button.dispatch("on_press")
        self.assertEqual(first.state, "stop")
        self.assertEqual(first.source, "")
        self.assertIsNone(first.parent)
        self.assertEqual(frame.slideshow.video.source, "two.mov")
        self.assertEqual(frame.slideshow.video.state, "play")
        play_pause.dispatch("on_press")
        previous.dispatch("on_press")
        self.assertFalse(frame.slideshow.is_playing)
        self.assertEqual(frame.slideshow.video.source, "one.mp4")
        self.assertEqual(frame.slideshow.video.state, "stop")
        next_button.dispatch("on_press")
        next_button.dispatch("on_press")
        self.assertEqual(frame.slideshow.image.source, "photo.jpg")
        self.schedule.assert_not_called()

    def test_late_eos_from_skipped_video_does_not_advance_new_video(self):
        show = self.make_show(["one.mp4", "two.mp4", "photo.jpg"])
        show.play()
        old = show.video
        show.next_photo()
        old.eos = True
        show._video_finished(old, True)
        self.assertEqual(show.index, 1)
        self.assertEqual(show.video.source, "two.mp4")

    def test_single_video_restarts_from_beginning_after_eos(self):
        show = self.make_show(["clip.mp4"])
        show.play()
        old = show.video
        old._on_eos()
        self.assertIsNot(show.video, old)
        self.assertEqual(show.video.source, "clip.mp4")
        self.assertEqual(show.video.state, "play")
        self.assertEqual(show.index, 0)
        self.schedule.assert_not_called()

    def test_menu_pauses_and_resumes_video_with_new_photo_speed(self):
        frame = PhotoFrame()
        self.addCleanup(frame.close)
        self.addCleanup(lambda: frame.menu.dismiss(animation=False))
        frame.slideshow.set_photos(["clip.mp4"])
        frame.slideshow.play()
        video = frame.slideshow.video
        video.position = 2.5
        frame.menu.open(animation=False)
        self.assertEqual(video.state, "pause")
        frame.menu.photo_duration = 60
        frame.menu.dismiss(animation=False)
        self.assertEqual(video.state, "play")
        self.assertEqual(video.position, 2.5)
        self.schedule.assert_not_called()

    def test_eos_arriving_while_paused_waits_until_play(self):
        show = self.make_show(["clip.mp4", "photo.jpg"])
        show.play()
        show.pause()
        show.video._on_eos()
        self.assertEqual(show.index, 0)
        self.assertFalse(show.is_playing)
        show.play()
        self.assertEqual(show.index, 1)
        self.schedule.assert_called_once_with(show.next_photo, 5)

    def test_replacing_source_and_closing_release_video(self):
        show = self.make_show(["clip.mp4"])
        show.play()
        old = show.video
        with patch.object(old, "unload") as unload:
            show.set_photos(["replacement.mov"])
            unload.assert_called_once()
        self.assertEqual(old.source, "")
        self.assertTrue(show.is_playing)
        self.assertEqual(show.video.state, "play")
        current = show.video
        with patch.object(current, "unload") as unload:
            show.close()
            unload.assert_called_once()
        self.assertEqual(current.source, "")
        self.assertFalse(show.is_playing)
        self.assertIsNone(show.video)


if __name__ == "__main__":
    unittest.main()
