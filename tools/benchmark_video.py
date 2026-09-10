"""Compare original-resolution playback: python tools/benchmark_video.py --provider ffpyplayer file.mp4."""

import argparse
import json
import os
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("files", nargs="+", type=Path)
parser.add_argument("--provider", choices=("gstplayer", "ffpyplayer", "photoshow"), required=True)
parser.add_argument("--seconds", type=float, default=6)
parser.add_argument("--visible", action="store_true", help="Measure a visible window, including presentation.")
args = parser.parse_args()
os.environ["KIVY_VIDEO"] = "ffpyplayer" if args.provider == "photoshow" else args.provider
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_DPI"] = "96"
os.environ["KIVY_METRICS_DENSITY"] = "1"

from kivy.config import Config
Config.set("graphics", "window_state", "visible" if args.visible else "hidden")
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.uix.video import Video
if args.provider == "photoshow":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from media_video import MediaVideo as Video

# Windows can throttle buffer swaps for an invisible window. Still render
# the full canvas, but do not wait for an invisible surface to be presented.
if not args.visible:
    Window.bind(on_flip=lambda *_args: True)

def pump():
    EventLoop.idle()
    Window.mainloop()

for path in args.files:
    video = Video(source=str(path.resolve()), state="play",
                  options={"eos": "stop"})
    Window.add_widget(video)
    try:
        deadline = time.perf_counter() + 30
        while video.position < 1 and time.perf_counter() < deadline:
            pump()
        if not video.loaded:
            raise RuntimeError(f"Video did not load: {path}")
        frames = []
        video.bind(position=lambda _video, pos: frames.append(pos))
        start = time.perf_counter()
        cpu_start = time.process_time()
        position_start = video.position
        while time.perf_counter() - start < args.seconds and not video.eos:
            pump()
        elapsed = time.perf_counter() - start
        result = {
            "file": path.name,
            "provider": args.provider,
            "visible_window": args.visible,
            "texture_size": list(video.texture.size),
            "frames_per_second": round(len(frames) / elapsed, 1),
            "playback_seconds_per_second": round((video.position - position_start) / elapsed, 2),
            "cpu_cores_used": round((time.process_time() - cpu_start) / elapsed, 2),
        }
        player = getattr(video._video, "_ffplayer", None)
        if player is not None:
            metadata = player.get_metadata()
            result["source_size"] = metadata["src_vid_size"]
            result["source_frame_rate"] = metadata["frame_rate"]
            pixel_format = metadata["src_pix_fmt"]
            result["pixel_format"] = (pixel_format.decode() if isinstance(pixel_format, bytes)
                                      else pixel_format)
        print(json.dumps(result), flush=True)
    finally:
        video.state = "stop"
        video.source = ""
        video.unload()
        Window.remove_widget(video)
        pump()
