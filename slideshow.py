import random
from kivy.uix.image import Image
from kivy.clock import Clock
from sources import load_local_photos

PHOTO_DURATIONS = (5, 15, 30, 60)

class Slideshow:
    def __init__(self, folder=None):
        self.folder = folder
        self.photos = []
        self.index = 0
        self.image = Image(source="", opacity=0)
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
        self.image.source = self.photos[0] if self.photos else ""
        self.image.opacity = 1 if self.photos else 0
        self.image.reload()
        if was_playing:
            self.play()

    def show_photo(self):
        return self.image

    def next_photo(self, dt = None):
        if not self.photos:
            return
        self.index = (self.index + 1) % len(self.photos)
        self.image.source = self.photos[self.index]

    def prev_photo(self):
        if not self.photos:
            return
        self.index = (self.index - 1) % len(self.photos)
        self.image.source = self.photos[self.index]

    @property
    def is_playing(self):
        return self.event is not None

    def play(self):
        if self.event is None and self.photos:
            self.event = Clock.schedule_interval(self.next_photo, self.photo_duration)

    def set_photo_duration(self, seconds):
        """Apply photo timing immediately, preserving the playback state."""
        if seconds not in PHOTO_DURATIONS:
            raise ValueError("Photo duration must be 5, 15, 30, or 60 seconds")
        if seconds == self.photo_duration:
            return
        self.photo_duration = seconds
        if self.is_playing:
            self.pause()
            self.play()

    def pause(self):
        if self.event is not None:
            self.event.cancel()
            self.event = None

    def toggle_play(self, instance=None):
        if self.is_playing:
            self.pause()
        else:
            self.play()
