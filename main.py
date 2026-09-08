from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from menu import MenuButton, PhotoMenu
from slideshow import Slideshow



class PhotoFrame(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation="vertical"

        # frame 1
        frame1 = FloatLayout()
        self.add_widget(frame1)
        frame1.size_hint_y = 0.9
        self.slideshow = Slideshow("photos/")
        self.slideshow.show_photo().pos_hint = {"x": 0, "y": 0}
        frame1.add_widget(self.slideshow.show_photo())

        self.menu = PhotoMenu()
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

        btn1 = Button(text = "previous")
        btn2 = Button(text= "play/pause")
        btn3 = Button(text= "next")
        frame2.add_widget(btn1)
        frame2.add_widget(btn2)
        frame2.add_widget(btn3)
        btn1.bind(on_press=lambda x: self.slideshow.prev_photo())
        # alternative syntax: btn2.bind(on_press=self.toggle_play)
        btn2.bind(on_press=lambda x: self.slideshow.toggle_play())
        btn3.bind(on_press=lambda x: self.slideshow.next_photo())

        #Examples on how to use size_hint and pos_hint
        #self.password.size_hint_y = 0.5
        #self.password.pos_hint = {"y" : 0.25}

    def _position_menu_button(self, photo_frame, *_args):
        self.menu_button.pos = (photo_frame.x + dp(12),
                                photo_frame.top - self.menu_button.height - dp(12))

    def _pause_for_menu(self, *_args):
        self._resume_after_menu = self.slideshow.is_playing
        self.slideshow.pause()

    def _restore_after_menu(self, _menu, parent):
        # ModalView is removed from its parent after its closing animation.
        if parent is None:
            resume = self._resume_after_menu
            self._resume_after_menu = False
            if resume:
                self.slideshow.play()

class PhotoShowApp(App):

    def build(self):
        return PhotoFrame()


if __name__ == '__main__':
    PhotoShowApp().run()
