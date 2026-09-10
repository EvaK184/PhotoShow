"""Photo viewer menu and photo timing controls."""

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from slideshow import PHOTO_DURATIONS


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
    """A text button with press feedback."""

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


class PhotoSpeedControl(FloatLayout):
    """Four equally spaced stops, each labelled with its photo duration."""

    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(88), **kwargs)
        self.slider = Slider(
            min=0, max=len(PHOTO_DURATIONS) - 1, step=1,
            orientation="horizontal", size_hint=(1, None), height=dp(48),
            pos_hint={"x": 0, "top": 1}, padding=dp(24),
            value_track=True, value_track_width=dp(3),
            value_track_color=(0.35, 0.75, 1, 1),
        )
        self.add_widget(self.slider)
        with self.slider.canvas.after:
            Color(0.75, 0.8, 0.88, 1)
            self.ticks = [Line(width=dp(1)) for _ in PHOTO_DURATIONS]
        self.labels = []
        for seconds in PHOTO_DURATIONS:
            label = Label(text=f"{seconds} s", font_size=sp(16),
                          size_hint=(None, None), size=(dp(48), dp(28)))
            self.labels.append(label)
            self.add_widget(label)
        self.slider.bind(pos=self._position_stops, size=self._position_stops,
                         padding=self._position_stops)
        self._position_stops()

    def _position_stops(self, *_args):
        slider = self.slider
        start = slider.x + slider.padding
        span = max(0, slider.width - 2 * slider.padding)
        center_y = slider.y + slider.height / 2
        for index, (tick, label) in enumerate(zip(self.ticks, self.labels)):
            x = start + span * index / (len(PHOTO_DURATIONS) - 1)
            tick.points = [x, center_y - dp(17), x, center_y - dp(24)]
            label.center_x = x
            label.top = slider.y


class PhotoMenu(ModalView):
    photo_duration = NumericProperty(PHOTO_DURATIONS[0])
    source_label = StringProperty("No folder selected")
    source_status = StringProperty("Choose a folder containing photos or videos.")
    source_busy = BooleanProperty(False)

    __events__ = ("on_choose_source", "on_use_default_source")

    def on_choose_source(self):
        pass

    def on_use_default_source(self):
        pass

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
        self._speed_visible = False
        self._source_visible = False
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
            if title == "Speed":
                button.bind(on_release=self.show_speed)
            elif title == "Source Folder":
                button.bind(on_release=self.show_source)
            self.option_buttons.append(button)
            options.add_widget(button)
            button.bind(pos=self._refresh_hover, size=self._refresh_hover)
        self.scroll.add_widget(options)
        self.scroll.bind(pos=self._refresh_hover, size=self._refresh_hover,
                         scroll_y=self._refresh_hover)
        content.add_widget(self.scroll)
        self.main_content = content
        self.speed_content = self._build_speed_content()
        self.source_content = self._build_source_content()
        self.overlay = FloatLayout()
        self.overlay.add_widget(content)
        self.close_button = Button(
            text="X", font_size=sp(24), size_hint=(None, None),
            size=(dp(44), dp(44)), background_normal="", background_down="",
            background_color=(0.08, 0.10, 0.13, 0.78),
        )
        self.close_button.bind(on_release=self.dismiss)
        self.overlay.add_widget(self.close_button)
        self.add_widget(self.overlay)
        self.bind(right=self._position_close_button,
                  top=self._position_close_button)
        self._position_close_button()

    def _build_source_content(self):
        content = BoxLayout(orientation="vertical", padding=dp(16),
                            spacing=dp(12), pos_hint={"x": 0, "y": 0})
        header = BoxLayout(size_hint_y=None, height=dp(48))
        back = MenuOption(text="< Back", size_hint_x=None, width=dp(88))
        back.bind(on_release=self.show_main)
        header.add_widget(back)
        header.add_widget(Label(text="SOURCE FOLDER", bold=True, font_size=sp(18)))
        content.add_widget(header)
        folder = Label(text=self.source_label, font_size=sp(16), halign="center",
                       valign="middle", shorten=True, shorten_from="left")
        status = Label(text=self.source_status, font_size=sp(16), halign="center",
                       valign="middle")
        for label in (folder, status):
            label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            content.add_widget(label)
        choose = Button(text="Choose folder", size_hint_y=None, height=dp(48))
        choose.bind(on_release=lambda *_args: self.dispatch("on_choose_source"))
        self.bind(source_label=lambda _menu, value: setattr(folder, "text", value),
                  source_status=lambda _menu, value: setattr(status, "text", value),
                  source_busy=lambda _menu, value: setattr(choose, "disabled", value))
        content.add_widget(choose)
        self.default_source_button = Button(
            text="Use default folder", size_hint_y=None, height=dp(48))
        self.default_source_button.bind(
            on_release=lambda *_args: self.dispatch("on_use_default_source"))
        self.bind(source_busy=lambda _menu, value:
                  setattr(self.default_source_button, "disabled", value))
        content.add_widget(self.default_source_button)
        return content

    def show_source(self, *_args):
        self.show_main()
        self._clear_hover()
        self._source_visible = True
        self.overlay.remove_widget(self.main_content)
        self.overlay.add_widget(self.source_content)
        self._resize_panel()

    def _build_speed_content(self):
        content = BoxLayout(orientation="vertical", padding=dp(16),
                            spacing=dp(8), pos_hint={"x": 0, "y": 0})
        header = BoxLayout(size_hint_y=None, height=dp(44))
        self.back_button = MenuOption(text="< Back", size_hint_x=None,
                                      width=dp(88))
        self.back_button.bind(on_release=self.show_main)
        header.add_widget(self.back_button)
        header.add_widget(Label(text="SPEED", font_size=sp(22), bold=True))
        # Match the Back button's width to keep the title centered.
        header.add_widget(Label(size_hint_x=None, width=dp(88)))
        content.add_widget(header)
        self.duration_label = Label(font_size=sp(18), size_hint_y=None,
                                    height=dp(28))
        content.add_widget(self.duration_label)
        self.speed_control = PhotoSpeedControl()
        self.speed_control.slider.bind(value=self._select_duration)
        self.bind(photo_duration=self._sync_duration)
        self._sync_duration()
        content.add_widget(self.speed_control)
        return content

    def _select_duration(self, _slider, value):
        self.photo_duration = PHOTO_DURATIONS[int(value)]

    def _sync_duration(self, *_args):
        self.speed_control.slider.value = PHOTO_DURATIONS.index(self.photo_duration)
        self.duration_label.text = f"{int(self.photo_duration)} seconds per photo"

    def show_speed(self, *_args):
        if self._speed_visible:
            return
        self.show_main()
        self._clear_hover()
        self._speed_visible = True
        self.overlay.remove_widget(self.main_content)
        self.overlay.add_widget(self.speed_content)
        self._resize_panel()

    def show_main(self, *_args):
        if not self._speed_visible and not self._source_visible:
            return
        current = self.speed_content if self._speed_visible else self.source_content
        self._speed_visible = False
        self._source_visible = False
        self.overlay.remove_widget(current)
        self.overlay.add_widget(self.main_content)
        self._resize_panel()
        self._refresh_hover()

    def _position_close_button(self, *_args):
        self.close_button.pos = (self.right - self.close_button.width,
                                 self.top + dp(8))

    def _resize_panel(self, *_args):
        # Reserve room above the centered panel for the external close button.
        margin = self.close_button.height + dp(8) + dp(12)
        self.size_hint_max_x = dp(440 if self._source_visible else
                                  320 if self._speed_visible else 360)
        desired_height = dp(380 if self._source_visible else
                            224 if self._speed_visible else 432)
        self.height = min(desired_height, max(0, Window.height - 2 * margin))

    def collide_point(self, x, y):
        # Route input to the close button even though it is outside the panel.
        return (super().collide_point(x, y)
                or self.close_button.collide_point(x, y))

    def on_pre_open(self):
        self.show_main()
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
        visible = self._hover_active and not (self._speed_visible or self._source_visible) and self.scroll.collide_point(
            *self.scroll.parent.to_widget(*Window.mouse_pos)
        )
        for button in self.option_buttons:
            button.underline = visible and button.collide_point(
                *button.to_widget(*Window.mouse_pos)
            )
