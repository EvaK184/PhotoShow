"""Playback icons drawn as shapes, independent of installed fonts."""

from kivy.graphics import Color, InstructionGroup, Rectangle, Triangle
from kivy.metrics import dp
from kivy.properties import OptionProperty
from kivy.uix.button import Button

PLAY_COLOUR = (0.10, 0.50, 0.24, 1)
PAUSE_COLOUR = (0.75, 0.10, 0.14, 1)


class PlaybackButton(Button):
    icon = OptionProperty("play", options=("previous", "play", "pause", "next"))

    def __init__(self, **kwargs):
        super().__init__(background_normal="", background_down="",
                         background_disabled_normal="",
                         background_color=(0.18, 0.20, 0.23, 1), **kwargs)
        self._icon_canvas = InstructionGroup()
        self.canvas.after.add(self._icon_canvas)
        self.bind(pos=self._draw_icon, size=self._draw_icon, icon=self._draw_icon,
                  state=self._draw_icon, disabled=self._draw_icon)
        self._draw_icon()

    def _draw_icon(self, *_args):
        group = self._icon_canvas
        group.clear()
        group.add(Color(1, 1, 1, .35 if self.disabled else .7 if self.state == "down" else 1))
        size = max(0, min(dp(26), self.width - dp(12), self.height - dp(12)))
        x, y = self.center
        half = size / 2
        if self.icon == "pause":
            for offset in (-.38, .13):
                group.add(Rectangle(pos=(x + offset * size, y - half), size=(size / 4, size)))
        elif self.icon == "play":
            group.add(Triangle(points=(x - size / 3, y - half,
                                       x - size / 3, y + half, x + size * 2 / 3, y)))
        else:
            direction = 1 if self.icon == "next" else -1
            group.add(Triangle(points=(x - direction * half, y - half,
                                       x - direction * half, y + half,
                                       x + direction * size / 3, y)))
            bar_x = x + size / 3 if direction == 1 else x - half
            group.add(Rectangle(pos=(bar_x, y - half), size=(size / 6, size)))
