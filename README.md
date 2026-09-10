# PhotoShow
An app that runs a slideshow with the photos and videos that it is fed with. Basically, turning your device (eg. pc, phone, tablet) into a digital frame.

## Choose your photos and videos

On first launch, if no source folder has been saved, the app uses the `photos`
folder beside `main.py` in the repository. This works even when launched from
another working directory. If that folder is absent, choose a folder below.
Your saved selection takes priority on later launches.
To switch back, press **Menu > Source Folder > Use default folder**. A successful
reset saves the repository's `photos` folder as your source for future launches.
If it is empty or unavailable, your current source stays selected.

Open **Menu > Source Folder > Choose folder**. On desktop, browse to a folder
and press **Use this folder**. You can also enter a path and press **Go**; on
Windows, the drive selector lets you browse other drives. On Android, choose
a folder and grant access through the system folder picker.

The slideshow uses JPG, JPEG and PNG photos and MP4, M4V, MOV, AVI, MKV, WEBM
and OGV videos directly inside that folder, in shuffled order. Subfolders are
not included. Playback starts automatically when the first source loads at launch.
The bottom controls use previous, play/pause and next icons. The centre button is
red with a pause icon while playing, and green with a play icon while paused.
Videos play at their normal speed
from start to finish, then advance to the next file. **Speed** only sets how
long photos stay on screen. The existing **play/pause** button pauses and resumes
a video at its current position; **next** skips it, and **previous** goes back
one file. Each newly selected video starts at the beginning. Opening the menu
pauses playback and closing it resumes if it was playing.

Changing folders keeps your speed and playback state. Cancelling or
choosing an empty/unavailable folder keeps the existing slideshow.

The app remembers a successful selection in `source.json` in its user data
directory and loads it again at startup. If the folder is moved, disconnected,
or its access is revoked, choose it again from the menu. Choose the same folder
again to refresh its photos and videos after adding or removing files.

Photos are no longer bundled with the Android app. Desktop reads the selected
files in place. Android retains read access to the selected folder using the
[Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files)
and makes temporary copies in private app cache for display; allow enough free
space for those photos and videos. Loading runs in the background. The app never changes
the originals. Cloud sources are not implemented yet; source loading is kept
separate from slideshow playback to allow adding providers later.

Run the desktop regression checks with `python -m unittest discover -s tests -v`.
Android picker and persisted access should also be checked on a device after
building (choose, cancel, restart, and revoke access), along with mixed photo/video
playback, pause/resume, skipping, and automatic advance at the end of a video.

## Development dependencies

`requirements.txt` records the desktop development environment, including Windows-specific packages. Keep those dependencies in the desktop virtual environment. Buildozer is a separate build tool and is installed in the Android build environment described below.

The `requirements` setting under `[app]` in `buildozer.spec` controls the Python packages included in the mobile app. It currently lists `python3,kivy,pyjnius,ffpyplayer`; ffpyplayer provides Android video playback. Do not install `requirements.txt` wholesale into the Android build environment or copy its Windows-specific packages into the spec.

Install the updated desktop dependencies with `python -m pip install -r requirements.txt`.
Video playback uses ffpyplayer on desktop and Android, including automatic camera
rotation from presentation metadata. Full-range YUV420 camera footage uses GPU
colour conversion instead of creating a full RGBA frame on the CPU for each frame.
Videos retain their original resolution and colour range; the app does not
transcode them or automatically lower playback quality. GStreamer remains in the
desktop environment for comparison, but the slideshow uses its explicit ffpyplayer
provider. See the [FFPyPlayer documentation](https://matham.github.io/ffpyplayer/player.html)
for supported playback options and automatic rotation.

For playback diagnostics, compare the old and current paths with the same clip:

```powershell
python tools/benchmark_video.py --provider gstplayer --visible "path/to/video.mp4"
python tools/benchmark_video.py --provider photoshow --visible "path/to/video.mp4"
```

The tool reports delivered FPS, playback progress, frame dimensions, and CPU use.
Keep the window visible for representative presentation timings. Without
`--visible`, it renders offscreen and skips window presentation; those measurements
are useful for diagnostics but do not establish the FPS seen on screen.

## Android debug build

1. Set up a separate Linux build environment; on Windows, use WSL2. Follow the [official Buildozer installation guide](https://buildozer.readthedocs.io/en/stable/installation/) for your operating system and Python version. It covers system packages, a compatible Python virtual environment, Buildozer installation, and the remaining toolchain dependencies. Apply any toolchain settings the guide requires for that environment.
2. Clone or copy the project into the Linux filesystem, for example `~/PhotoShow`. Under WSL2, build there rather than in `/mnt/c/...`, and keep the Linux build environment separate from the Windows virtual environment.
3. Activate the build virtual environment created in step 1, then run:

   ```bash
   cd ~/PhotoShow
   buildozer -v android debug
   ```

Use the existing `buildozer.spec`. The first build downloads additional Android tools; generated packages are written to `bin/`. See the [official quickstart](https://buildozer.readthedocs.io/en/stable/quickstart/) for deployment commands.
