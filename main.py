from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from slideshow import Slideshow



class PhotoFrame(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation="vertical"

        # frame 1
        frame1 = BoxLayout()
        self.add_widget(frame1)
        frame1.size_hint_y = 0.9
        self.slideshow = Slideshow("photos/")
        frame1.add_widget(self.slideshow.show_photo())

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

class PhotoShowApp(App):

    def build(self):
        return PhotoFrame()


if __name__ == '__main__':
    PhotoShowApp().run()