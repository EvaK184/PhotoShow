"""Decode a generated camera-style clip; no user media is required."""

import os
from pathlib import Path
import struct
import tempfile
import time
import unittest

os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_DPI"] = "96"
os.environ["KIVY_METRICS_DENSITY"] = "1"

from kivy.config import Config
Config.set("graphics", "window_state", "hidden")
from kivy.clock import Clock
from ffpyplayer.pic import Image
from ffpyplayer.player import MediaPlayer
from ffpyplayer.writer import MediaWriter
from media_video import MediaVideo


def camera_clip(path):
    # A small full-range, four-colour video, with camera-style rotation metadata.
    width, height = 96, 64
    colours = ((220, 30, 40), (20, 210, 40), (30, 40, 220), (210, 200, 30))
    pixels = bytes(channel for y in range(height) for x in range(width)
                   for channel in colours[(y >= height // 2) * 2 + (x >= width // 2)])
    frame = Image(plane_buffers=[pixels], pix_fmt="rgb24", size=(width, height))
    writer = MediaWriter(str(path), [{"pix_fmt_in": "rgb24", "pix_fmt_out": "yuvj420p",
                                     "width_in": width, "height_in": height,
                                     "codec": "mjpeg", "frame_rate": (30, 1)}])
    try:
        for index in range(180):
            writer.write_frame(frame, index / 30)
    finally:
        writer.close()
    data = bytearray(path.read_bytes())
    # This generated file has one track and a version-0 track header.
    header = data.index(b"tkhd") + 4
    assert data[header] == 0
    struct.pack_into(">9i", data, header + 40, 0, 65536, 0, -65536, 0, 0, 0, 0, 1 << 30)
    path.write_bytes(data)


class VideoBackendTests(unittest.TestCase):
    def wait_for(self, condition, timeout=15):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            Clock.tick()
        self.assertTrue(condition(), "Video playback timed out")

    def test_rotation_full_resolution_colour_and_pause_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "camera.mov"
            camera_clip(path)
            video = MediaVideo(source=str(path), state="play", options={"eos": "stop"})
            try:
                self.wait_for(lambda: video.loaded and video.position > .1)
                video.state = "pause"
                self.assertEqual(video.texture.size, (64, 96))
                self.assertEqual(video._video._out_fmt, "yuv420p")
                self.assertEqual(video._video._ffplayer.get_output_pix_fmt(), "yuvj420p")
                position = video.position
                for _ in range(5):
                    Clock.tick()
                self.assertAlmostEqual(video.position, position, delta=.1)

                # Compare GPU conversion against FFmpeg's RGBA conversion.
                reference = MediaPlayer(str(path), ff_opts={"an": True, "out_fmt": "rgba"})
                try:
                    frame = None
                    deadline = time.monotonic() + 10
                    while frame is None and time.monotonic() < deadline:
                        frame, _delay = reference.get_frame()
                        Clock.tick()
                    self.assertIsNotNone(frame)
                    expected = bytes(frame[0].to_bytearray()[0])
                    actual = video.texture.pixels
                    stride = 64 * 4
                    flipped = b"".join(actual[y * stride:(y + 1) * stride]
                                       for y in reversed(range(96)))
                    # Texture storage can be vertically flipped; compare interior
                    # colour samples to avoid chroma interpolation at tile edges.
                    samples = [(x + y * 64) * 4 + channel
                               for x in (16, 48) for y in (24, 72) for channel in range(3)]
                    error = min(max(abs(candidate[i] - expected[i]) for i in samples)
                                for candidate in (actual, flipped))
                    self.assertLessEqual(error, 4)
                finally:
                    reference.close_player()
                video.state = "play"
                self.wait_for(lambda: video.position > position + .1)
                video.seek(.9)
                self.wait_for(lambda: video.eos)
                self.assertEqual(video.state, "stop")
            finally:
                video.state = "stop"
                video.source = ""
                video.unload()
                Clock.tick()


if __name__ == "__main__":
    unittest.main()
