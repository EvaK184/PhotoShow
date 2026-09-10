import os

# Select before importing Kivy: this backend honors camera rotation metadata
# and delivers frames as they become ready instead of polling at 30 Hz.
os.environ.setdefault("KIVY_VIDEO", "ffpyplayer")

from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.utils import platform
from pathlib import Path
from threading import Thread
from folder_picker import AndroidFolderPicker, FolderPicker
from menu import MenuButton, PhotoMenu
from playback_controls import PlaybackButton, PLAY_COLOUR, PAUSE_COLOUR
from slideshow import Slideshow
from sources import FolderSource, load_source, read_source, save_source



class PhotoFrame(BoxLayout):

    def __init__(self, settings_path=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation="vertical"
        self.settings_path = settings_path
        self.source = None
        self._loaded_photos = None
        self._closed = False
        self.folder_picker = None
        self._resume_after_load = False
        self._autoplay_pending = True

        # frame 1
        frame1 = FloatLayout()
        self.add_widget(frame1)
        frame1.size_hint_y = 0.9
        self.slideshow = Slideshow()
        self.slideshow.show_photo().pos_hint = {"x": 0, "y": 0}
        frame1.add_widget(self.slideshow.show_photo())
        self.empty_message = Label(
            text="Choose a source folder from the menu to start your slideshow.",
            halign="center", valign="middle", padding=(dp(32), dp(32)),
            pos_hint={"x": 0, "y": 0})
        self.empty_message.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        frame1.add_widget(self.empty_message)

        self.menu = PhotoMenu(photo_duration=self.slideshow.photo_duration)
        self.menu.bind(on_choose_source=self.choose_source,
                       on_use_default_source=self.use_default_source)
        self.menu.bind(photo_duration=lambda _menu, seconds:
                       self.slideshow.set_photo_duration(seconds))
        self._resume_after_menu = False
        self.menu.bind(on_pre_open=self._pause_for_menu,
                       parent=self._restore_after_menu)
        self.menu_button = MenuButton()
        frame1.add_widget(self.menu_button)
        frame1.bind(pos=self._position_menu_button,
                    size=self._position_menu_button)
        self._position_menu_button(frame1)
        self.menu_button.bind(on_release=self.menu.open)

        # frame 2
        frame2 = BoxLayout()
        self.add_widget(frame2)
        frame2.size_hint_y = 0.1
        frame2.padding = [20, 10, 20, 10]
        frame2.spacing = 30

        btn1 = PlaybackButton(icon="previous")
        btn2 = PlaybackButton(icon="play")
        btn3 = PlaybackButton(icon="next")
        frame2.add_widget(btn1)
        frame2.add_widget(btn2)
        frame2.add_widget(btn3)
        btn1.bind(on_press=lambda x: self.slideshow.prev_photo())
        btn2.bind(on_press=lambda x: self.slideshow.toggle_play())
        btn3.bind(on_press=lambda x: self.slideshow.next_photo())
        self.playback_buttons = (btn1, btn2, btn3)
        self.slideshow.bind(is_playing=self._update_controls)
        self._update_controls()
        if self.settings_path:
            Clock.schedule_once(self._restore_source, 0)

        #Examples on how to use size_hint and pos_hint
        #self.password.size_hint_y = 0.5
        #self.password.pos_hint = {"y" : 0.25}

    def _position_menu_button(self, photo_frame, *_args):
        self.menu_button.pos = (photo_frame.x + dp(12),
                                photo_frame.top - self.menu_button.height - dp(12))

    def _pause_for_menu(self, *_args):
        self.empty_message.opacity = 0
        self._resume_after_menu = self.slideshow.is_playing or self._resume_after_load
        self.slideshow.pause()

    def _restore_after_menu(self, _menu, parent):
        # ModalView is removed from its parent after its closing animation.
        if parent is None:
            self.empty_message.opacity = 1
            resume = self._resume_after_menu
            self._resume_after_menu = False
            if resume and not self.menu.source_busy:
                self.slideshow.play()

    def _update_controls(self, *_args):
        for button in self.playback_buttons:
            button.disabled = not self.slideshow.photos or self.menu.source_busy
        toggle = self.playback_buttons[1]
        toggle.icon = "pause" if self.slideshow.is_playing else "play"
        toggle.background_color = PAUSE_COLOUR if self.slideshow.is_playing else PLAY_COLOUR

    def _restore_source(self, _dt):
        if self._closed:
            return
        try:
            source = read_source(self.settings_path)
            if source is None:
                default = self._default_source()
                if Path(default.location).is_dir():
                    source = default
            if source is not None:
                self.select_source(source, remember=False)
        except (OSError, ValueError) as exc:
            self._source_failed(str(exc))

    @staticmethod
    def _default_source():
        folder = Path(__file__).resolve().parent / "photos"
        return FolderSource("local", str(folder), str(folder))

    def use_default_source(self, *_args):
        self.select_source(self._default_source())

    def choose_source(self, *_args):
        if self.menu.source_busy:
            return
        if platform == "android":
            if self.folder_picker is None:
                self.folder_picker = AndroidFolderPicker(self.select_source, self._source_failed)
        else:
            initial = self.source.location if self.source and self.source.kind == "local" else None
            self.folder_picker = FolderPicker(self.select_source, initial)
        try:
            self.folder_picker.open()
        except Exception:
            Logger.exception("PhotoShow: Unable to open folder picker")
            self._source_failed("The folder picker could not be opened. Please try again.")

    def select_source(self, source, remember=True):
        if self.menu.source_busy or self._closed:
            return
        self._resume_after_load = (self._autoplay_pending or self.slideshow.is_playing
                                   or self._resume_after_menu)
        self.slideshow.pause()
        self.menu.source_busy = True
        self.menu.source_status = "Loading photos and videos..."
        self._update_controls()

        def load():
            try:
                result = load_source(source)
            except Exception as exc:
                Logger.exception("PhotoShow: Unable to load source folder")
                message = (str(exc) if isinstance(exc, ValueError) else
                           "Cannot read this folder. Check that it is available and choose it again.")
                Clock.schedule_once(lambda _dt: self._finish_source(error=message), 0)
            else:
                Clock.schedule_once(lambda _dt: self._finish_source(
                    source, result, remember), 0)

        Thread(target=load, daemon=True).start()

    def _finish_source(self, source=None, result=None, remember=True, error=None):
        if self._closed:
            if result is not None:
                result.close()
            return
        self.menu.source_busy = False
        if error:
            self._source_failed(error)
        else:
            previous = self._loaded_photos
            self.slideshow.set_photos(result.paths)
            self.slideshow.folder = source.location
            self._loaded_photos = result
            self.source = source
            self._autoplay_pending = False
            self.empty_message.text = ""
            self.menu.source_label = source.label
            count = len(result.paths)
            self.menu.source_status = f"{count} file{'s' if count != 1 else ''} ready."
            if remember and self.settings_path:
                try:
                    save_source(self.settings_path, source)
                except OSError:
                    self.menu.source_status += " This folder could not be saved for next time."
            if previous is not None:
                previous.close()
        self._update_controls()
        resume = self._resume_after_load
        self._resume_after_load = False
        if self.menu.parent is not None:
            self._resume_after_menu = resume
        elif resume:
            self.slideshow.play()

    def _source_failed(self, message):
        self.menu.source_status = message
        if not self.slideshow.photos:
            self.empty_message.text = message + "\nOpen Menu > Source Folder to choose a folder."

    def close(self):
        self._closed = True
        self.slideshow.close()
        if isinstance(self.folder_picker, AndroidFolderPicker):
            self.folder_picker.close()
        if self._loaded_photos is not None:
            self._loaded_photos.close()

class PhotoShowApp(App):

    def build(self):
        return PhotoFrame(settings_path=Path(self.user_data_dir) / "source.json")

    def on_pause(self):
        # Keep the app alive while Android's system folder picker is foreground.
        return True

    def on_stop(self):
        if self.root is not None:
            self.root.close()


if __name__ == '__main__':
    PhotoShowApp().run()
