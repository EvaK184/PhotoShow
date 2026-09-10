import random
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from media_video import MediaVideo as Video
from kivy.clock import Clock
from sources import is_video, load_local_photos

PHOTO_DURATIONS = (5, 15, 30, 60)

class Slideshow(EventDispatcher):
    is_playing = BooleanProperty(False)

    def __init__(self, folder=None):
        super().__init__()
        self.folder = folder
        self.photos = []
        self.index = 0
        self.image = Image(source="", opacity=0, pos_hint={"x": 0, "y": 0})
        self.display = FloatLayout()
        self.display.add_widget(self.image)
        self.video = None
        self.event = None
        self.photo_duration = PHOTO_DURATIONS[0]
        if folder is not None:
            self.set_photos(load_local_photos(folder))

    def set_photos(self, photos):
        """Replace the source and reset timing, preserving playback intent."""
        was_playing = self.is_playing
        self.pause()
        self.photos = list(photos)
        random.shuffle(self.photos)
        self.index = 0
        self._show_current()
        if was_playing:
            self.play()

    def show_photo(self):
        return self.display

    def _release_video(self):
        video = self.video
        self.video = None
        if video is not None:
            video.unbind(eos=self._video_finished)
            video.state = "stop"
            # Clear the source as well: a pending asynchronous load must not
            # reopen this file after it has been skipped or its cache deleted.
            video.source = ""
            video.unload()
            self.display.remove_widget(video)

    def _show_current(self):
        self._cancel_timer()
        self._release_video()
        source = self.photos[self.index] if self.photos else ""
        if source and is_video(source):
            self.image.opacity = 0
            self.video = Video(source=source, options={"eos": "stop"},
                               pos_hint={"x": 0, "y": 0})
            self.video.bind(eos=self._video_finished)
            self.display.add_widget(self.video)
        else:
            self.image.source = source
            self.image.opacity = 1 if source else 0
            self.image.reload()
        if self.is_playing:
            self._start_current()

    def _video_finished(self, video, finished):
        if finished and video is self.video and self.is_playing:
            self.next_photo()

    def _start_current(self):
        if self.video is not None:
            if self.video.eos:
                self.next_photo()
            else:
                self.video.state = "play"
        else:
            self.event = Clock.schedule_interval(self.next_photo, self.photo_duration)

    def next_photo(self, dt = None):
        if not self.photos:
            return
        self.index = (self.index + 1) % len(self.photos)
        self._show_current()

    def prev_photo(self):
        if not self.photos:
            return
        self.index = (self.index - 1) % len(self.photos)
        self._show_current()

    def play(self):
        if not self.is_playing and self.photos:
            self.is_playing = True
            self._start_current()

    def set_photo_duration(self, seconds):
        """Apply photo timing immediately, preserving the playback state."""
        if seconds not in PHOTO_DURATIONS:
            raise ValueError("Photo duration must be 5, 15, 30, or 60 seconds")
        if seconds == self.photo_duration:
            return
        self.photo_duration = seconds
        if self.is_playing and self.video is None:
            self._cancel_timer()
            self._start_current()

    def _cancel_timer(self):
        if self.event is not None:
            self.event.cancel()
            self.event = None

    def pause(self):
        self.is_playing = False
        self._cancel_timer()
        if self.video is not None and self.video.state == "play":
            self.video.state = "pause"

    def close(self):
        self.pause()
        self._release_video()

    def toggle_play(self, instance=None):
        if self.is_playing:
            self.pause()
        else:
            self.play()
