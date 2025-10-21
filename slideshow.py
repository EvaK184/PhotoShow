import os, random
from kivy.uix.image import Image
from kivy.clock import Clock

class Slideshow:
    def __init__(self, folder):
        self.folder = folder
        self.photos = [os.path.join(folder, f) for f in os.listdir(folder)
                       if f.lower().endswith((".jpg", ".png"))]
        random.shuffle(self.photos)
        self.index = 0
        self.image = Image(source = self.photos[self.index])
        self.event = None

    def show_photo(self):
        return self.image

    def next_photo(self, dt = None):
        self.index = (self.index + 1) % len(self.photos)
        self.image.source = self.photos[self.index]

    def prev_photo(self):
        self.index = (self.index - 1) % len(self.photos)
        self.image.source = self.photos[self.index]

    def toggle_play(self, instance=None):
        if self.event is None:
            self.event = Clock.schedule_interval(self.next_photo, 5)
        else:
            self.event.cancel()
            self.event = None
