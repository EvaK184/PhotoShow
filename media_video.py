"""Rotation-aware video with GPU conversion for full-range camera footage."""

from kivy.core.video.video_ffpyplayer import VideoFFPy
from kivy.resources import resource_find
from kivy.uix.video import Video


class CameraVideoProvider(VideoFFPy):
    def _next_frame_run(self, player):
        # Kivy's planar GPU path recognizes yuv420p, but camera clips commonly
        # use its full-range variant, yuvj420p. Keep those planes at their native
        # range/resolution instead of converting every frame to RGBA on the CPU.
        while not self._ffplayer_need_quit:
            pixel_format = player.get_metadata().get("src_pix_fmt")
            if pixel_format:
                if pixel_format in ("yuvj420p", b"yuvj420p"):
                    self._out_fmt = "yuv420p"  # Kivy's planar rendering path
                    player.set_output_pix_fmt("yuvj420p")
                break
            self._wait_for_wakeup(0.005)
        super()._next_frame_run(player)


class MediaVideo(Video):
    def texture_update(self, *_args):
        # Video inherits Image; do not try decoding an MP4 as a still image.
        if self.preview:
            self.set_texture_from_resource(self.preview)
        else:
            self.texture = None

    def _do_video_load(self, *_args):
        # Follow Kivy 2.3.1's Video load lifecycle with our explicit provider.
        # FFPyPlayer applies the presentation rotation metadata automatically.
        self.unload()
        if not self.source:
            self._video = None
            self.texture = None
            return
        filename = self.source
        if "://" not in filename:
            filename = resource_find(filename)
        self._video = CameraVideoProvider(filename=filename, **self.options)
        self._video.volume = self.volume
        self._video.bind(on_load=self._on_load, on_frame=self._on_video_frame,
                         on_eos=self._on_eos)
        if self.state == "play":
            self._video.play()
        self.duration = 1
        self.position = 0
