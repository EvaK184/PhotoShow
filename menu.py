"""Photo viewer menu and its placeholder controls."""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView


class MenuButton(Button):
    """A classic three-line menu icon drawn without an icon font."""

    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            background_normal="",
            background_down="",
            background_color=(0.08, 0.10, 0.13, 0.9),
            **kwargs,
        )
        with self.canvas.after:
            self.icon_color = Color(1, 1, 1, 1)
            self.lines = [Line(width=dp(1.2)) for _ in range(3)]
        self.bind(pos=self._update_icon, size=self._update_icon,
                  state=self._update_icon)
        self._update_icon()

    def _update_icon(self, *_args):
        self.icon_color.rgba = (
            (0.35, 0.75, 1, 1) if self.state == "down" else (1, 1, 1, 1)
        )
        for line, offset in zip(self.lines, (-7, 0, 7)):
            y = self.center_y + dp(offset)
            line.points = [self.center_x - dp(11), y,
                           self.center_x + dp(11), y]


class MenuOption(Button):
    """A text button with press feedback and no settings action yet."""

    def __init__(self, **kwargs):
        super().__init__(
            size_hint_y=None,
            height=dp(48),
            font_size=sp(20),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            **kwargs,
        )
        self.bind(state=self._update_color)
        self._update_color()

    def _update_color(self, *_args):
        self.color = (
            (0.35, 0.75, 1, 1) if self.state == "down" else (0.95, 0.96, 1, 1)
        )


class PhotoMenu(ModalView):
    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(0.9, None),
            size_hint_max=(dp(360), None),
            background="",
            background_color=(0.08, 0.10, 0.13, 0.78),
            overlay_color=(0, 0, 0, 0.25),
            **kwargs,
        )
        self._hover_active = False
        self._refresh_hover = Clock.create_trigger(self._update_hover, 0)
        content = BoxLayout(orientation="vertical", padding=dp(16),
                            spacing=dp(12), pos_hint={"x": 0, "y": 0})
        content.add_widget(Label(text="MENU", font_size=sp(26), bold=True,
                                 size_hint_y=None, height=dp(44)))

        # Keep the options reachable on short windows and landscape phones.
        self.scroll = ScrollView(do_scroll_x=False, scroll_timeout=55)
        options = BoxLayout(orientation="vertical", size_hint_y=None,
                            spacing=dp(8))
        options.bind(minimum_height=options.setter("height"))
        self.option_buttons = []
        for title in ("Speed", "Sound", "Brightness", "Schedule", "Clock",
                      "Source Folder"):
            button = MenuOption(text=title)
            self.option_buttons.append(button)
            options.add_widget(button)
            button.bind(pos=self._refresh_hover, size=self._refresh_hover)
        self.scroll.add_widget(options)
        self.scroll.bind(pos=self._refresh_hover, size=self._refresh_hover,
                         scroll_y=self._refresh_hover)
        content.add_widget(self.scroll)
        overlay = FloatLayout()
        overlay.add_widget(content)
        self.close_button = Button(
            text="X", font_size=sp(24), size_hint=(None, None),
            size=(dp(44), dp(44)), background_normal="", background_down="",
            background_color=(0.08, 0.10, 0.13, 0.78),
        )
        self.close_button.bind(on_release=self.dismiss)
        overlay.add_widget(self.close_button)
        self.add_widget(overlay)
        self.bind(right=self._position_close_button,
                  top=self._position_close_button)
        self._position_close_button()

    def _position_close_button(self, *_args):
        self.close_button.pos = (self.right - self.close_button.width,
                                 self.top + dp(8))

    def _resize_panel(self, *_args):
        # Reserve room above the centered panel for the external close button.
        margin = self.close_button.height + dp(8) + dp(12)
        self.height = min(dp(432), max(0, Window.height - 2 * margin))

    def collide_point(self, x, y):
        # Route input to the close button even though it is outside the panel.
        return (super().collide_point(x, y)
                or self.close_button.collide_point(x, y))

    def on_pre_open(self):
        Window.bind(size=self._resize_panel)
        self._resize_panel()

    def on_open(self):
        self._hover_active = True
        Window.bind(mouse_pos=self._update_hover,
                    on_cursor_leave=self._clear_hover)
        self._update_hover()

    def on_dismiss(self):
        self._hover_active = False
        self._refresh_hover.cancel()
        Window.unbind(mouse_pos=self._update_hover,
                      on_cursor_leave=self._clear_hover,
                      size=self._resize_panel)
        self._clear_hover()
        for button in self.option_buttons:
            button.state = "normal"

    def _clear_hover(self, *_args):
        for button in self.option_buttons:
            button.underline = False

    def _update_hover(self, *_args):
        visible = self._hover_active and self.scroll.collide_point(
            *self.scroll.parent.to_widget(*Window.mouse_pos)
        )
        for button in self.option_buttons:
            button.underline = visible and button.collide_point(
                *button.to_widget(*Window.mouse_pos)
            )
