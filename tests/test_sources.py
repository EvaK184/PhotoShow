"""Source selection, persistence, and playback integration regressions."""

import base64
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_DPI"] = "96"
os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_METRICS_FONTSCALE"] = "1"

from kivy.config import Config
Config.set("graphics", "window_state", "hidden")
from kivy.clock import Clock
from kivy.core.window import Window

from folder_picker import AndroidFolderPicker, FolderPicker
from main import PhotoFrame
from slideshow import Slideshow
from sources import FolderSource, load_source, read_source, save_source

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=")


class SourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.folder = self.directory / "My pictures"
        self.folder.mkdir()
        (self.folder / "one.PNG").write_bytes(PNG)
        self.source = FolderSource("local", str(self.folder), str(self.folder))
        self.settings = self.directory / "settings" / "source.json"

    def make_frame(self, restore=False):
        frame = PhotoFrame(settings_path=self.settings if restore else None)
        Window.add_widget(frame)
        self.addCleanup(Window.remove_widget, frame)
        self.addCleanup(frame.close)
        self.addCleanup(lambda: frame.menu.dismiss(animation=False))
        return frame

    def finish_loading(self, frame):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            Clock.tick()
            if not frame.menu.source_busy:
                return
        self.fail("Source loading did not complete")

    def test_reads_only_supported_files_directly_in_selected_folder(self):
        (self.folder / "two.JPEG").write_bytes(PNG)
        (self.folder / "clip.MP4").write_bytes(b"video")
        (self.folder / "clip.mov").write_bytes(b"video")
        (self.folder / "notes.txt").write_text("ignore")
        (self.folder / "directory.jpg").mkdir()
        (self.folder / "directory.jpg" / "nested.png").write_bytes(PNG)
        loaded = load_source(self.source)
        self.assertEqual({Path(path).name for path in loaded.paths},
                         {"one.PNG", "two.JPEG", "clip.MP4", "clip.mov"})
        loaded.close()
        self.assertTrue((self.folder / "one.PNG").exists())

    def test_video_only_folder_is_accepted(self):
        (self.folder / "one.PNG").unlink()
        (self.folder / "clip.MKV").write_bytes(b"video")
        loaded = load_source(self.source)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded.paths, [str(self.folder / "clip.MKV")])

    def test_empty_and_missing_folders(self):
        (self.folder / "one.PNG").unlink()
        with self.assertRaisesRegex(ValueError, "No JPG"):
            load_source(self.source)
        self.folder.rmdir()
        with self.assertRaises(OSError):
            load_source(self.source)

    def test_save_restore_and_malformed_settings(self):
        self.assertIsNone(read_source(self.settings))
        save_source(self.settings, self.source)
        self.assertEqual(read_source(self.settings), self.source)
        for data in ('invalid json', '[]', '{"kind": "cloud"}'):
            self.settings.write_text(data)
            with self.assertRaises(ValueError):
                read_source(self.settings)

    def test_initial_state_and_empty_playback_controls(self):
        frame = self.make_frame()
        self.assertTrue(all(button.disabled for button in frame.playback_buttons))
        show = Slideshow()
        show.next_photo()
        show.prev_photo()
        show.toggle_play()
        self.assertFalse(show.is_playing)
        self.assertEqual(show.image.source, "")

    def test_picker_selects_folder_and_cancel_does_not_select(self):
        selected = Mock()
        picker = FolderPicker(selected, str(self.directory))
        picker.browser.selection = [str(self.folder)]
        picker.choose()
        selected.assert_called_once_with(self.source)
        for _ in range(5):
            Clock.tick()
        selected.reset_mock()
        picker.dismiss()
        selected.assert_not_called()
        picker.navigate(str(self.folder))
        picker.choose()
        selected.assert_called_once_with(self.source)
        for _ in range(5):
            Clock.tick()

    def test_selection_restores_at_startup_and_keeps_speed(self):
        frame = self.make_frame()
        frame.settings_path = self.settings
        frame.slideshow.set_photo_duration(30)
        frame.menu.open(animation=False)
        frame.menu.option_buttons[-1].dispatch("on_release")
        self.assertIs(frame.menu.source_content.parent, frame.menu.overlay)
        frame.select_source(self.source)
        self.finish_loading(frame)
        self.assertEqual(frame.source, self.source)
        self.assertEqual(frame.slideshow.photo_duration, 30)
        self.assertFalse(frame.slideshow.is_playing)
        self.assertEqual(frame.empty_message.text, "")
        self.assertTrue(all(not button.disabled for button in frame.playback_buttons))
        self.assertIsNotNone(frame.slideshow.image.texture)
        restored = self.make_frame(restore=True)
        self.finish_loading(restored)
        self.assertEqual(restored.source, self.source)
        self.assertTrue(restored.slideshow.is_playing)
        self.assertEqual(restored.playback_buttons[1].icon, "pause")

    def test_autoplay_and_toggle_colours_preserve_a_later_user_pause(self):
        from playback_controls import PAUSE_COLOUR, PLAY_COLOUR

        frame = self.make_frame()
        frame.select_source(self.source)
        self.finish_loading(frame)
        toggle = frame.playback_buttons[1]
        self.assertTrue(frame.slideshow.is_playing)
        self.assertEqual(toggle.icon, "pause")
        self.assertEqual(tuple(toggle.background_color), PAUSE_COLOUR)
        frame.menu.open(animation=False)
        self.assertEqual(toggle.icon, "play")
        self.assertEqual(tuple(toggle.background_color), PLAY_COLOUR)
        frame.menu.dismiss(animation=False)
        self.assertEqual(toggle.icon, "pause")
        toggle.dispatch("on_press")
        self.assertFalse(frame.slideshow.is_playing)
        self.assertEqual(toggle.icon, "play")
        self.assertEqual(tuple(toggle.background_color), PLAY_COLOUR)
        frame.select_source(self.source)
        self.finish_loading(frame)
        self.assertFalse(frame.slideshow.is_playing)
        self.assertEqual(toggle.icon, "play")
        toggle.dispatch("on_press")
        self.assertTrue(frame.slideshow.is_playing)
        self.assertEqual(toggle.icon, "pause")

    def test_first_launch_uses_repository_photos_then_saved_selection_takes_priority(self):
        default_folder = self.directory / "photos"
        default_folder.mkdir()
        (default_folder / "default.png").write_bytes(PNG)
        # The app directory differs from the process's working directory.
        with patch("main.__file__", str(self.directory / "main.py")):
            frame = self.make_frame(restore=True)
            self.finish_loading(frame)
            self.assertEqual(frame.source.location, str(default_folder))
            self.assertTrue(frame.slideshow.is_playing)
            self.assertEqual(frame.slideshow.image.source, str(default_folder / "default.png"))
            save_source(self.settings, self.source)
            restored = self.make_frame(restore=True)
            self.finish_loading(restored)
            self.assertEqual(restored.source, self.source)
            restored.slideshow.set_photo_duration(15)
            restored.slideshow.play()
            restored.menu.open(animation=False)
            restored.menu.show_source()
            restored.menu.default_source_button.dispatch("on_release")
            self.assertTrue(restored.menu.default_source_button.disabled)
            self.finish_loading(restored)
            self.assertEqual(restored.source.location, str(default_folder))
            self.assertEqual(read_source(self.settings), restored.source)
            self.assertFalse(restored.menu.default_source_button.disabled)
            self.assertEqual(restored.slideshow.photo_duration, 15)
            restored.menu.dismiss(animation=False)
            self.assertTrue(restored.slideshow.is_playing)

    def test_invalid_selection_preserves_current_photos_and_saved_folder(self):
        frame = self.make_frame()
        frame.settings_path = self.settings
        frame.select_source(self.source)
        self.finish_loading(frame)
        frame.slideshow.play()
        frame.menu.open(animation=False)
        photos = frame.slideshow.photos[:]
        missing = FolderSource("local", str(self.directory / "missing"), "missing")
        frame.select_source(missing)
        self.finish_loading(frame)
        self.assertEqual(frame.slideshow.photos, photos)
        self.assertEqual(frame.source, self.source)
        self.assertEqual(read_source(self.settings), self.source)
        self.assertIn("Cannot read", frame.menu.source_status)
        self.assertFalse(frame.slideshow.is_playing)
        frame.menu.dismiss(animation=False)
        self.assertTrue(frame.slideshow.is_playing)

    def test_switch_resets_index_and_resumes_when_menu_closes_during_load(self):
        frame = self.make_frame()
        frame.select_source(self.source)
        self.finish_loading(frame)
        frame.slideshow.play()
        frame.menu.open(animation=False)
        second = self.directory / "second"
        second.mkdir()
        (second / "new.png").write_bytes(PNG)
        frame.select_source(FolderSource("local", str(second), "second"))
        frame.menu.dismiss(animation=False)
        self.assertFalse(frame.slideshow.is_playing)
        self.finish_loading(frame)
        self.assertTrue(frame.slideshow.is_playing)
        self.assertEqual(frame.slideshow.index, 0)
        self.assertEqual(frame.slideshow.image.source, str(second / "new.png"))

    def test_unavailable_saved_source_starts_with_recovery_message(self):
        save_source(self.settings, FolderSource("local", str(self.directory / "gone"), "gone"))
        frame = self.make_frame(restore=True)
        self.finish_loading(frame)
        self.assertIn("choose a folder", frame.empty_message.text)
        self.assertTrue(all(button.disabled for button in frame.playback_buttons))

    def test_android_cancel_and_unrelated_results_do_not_change_selection(self):
        selected = Mock()
        failed = Mock()
        picker = AndroidFolderPicker(selected, failed)
        with patch.object(picker, "close") as close:
            picker._result(999, -1, Mock())
            close.assert_not_called()
            picker._result(picker.REQUEST_CODE, 0, None)
            close.assert_called_once()
        selected.assert_not_called()
        failed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
