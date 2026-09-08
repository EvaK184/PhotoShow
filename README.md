# PhotoShow
An app that runs a slideshow with the photos and videos that it is fed with. Basically, turning your device (eg. pc, phone, tablet) into a digital frame.

## Development dependencies

`requirements.txt` records the desktop development environment, including Windows-specific packages. Keep those dependencies in the desktop virtual environment. Buildozer is a separate build tool and is installed in the Android build environment described below.

The `requirements` setting under `[app]` in `buildozer.spec` controls the Python packages included in the mobile app. It currently lists `python3,kivy`; add mobile runtime dependencies there as the app needs them. Do not install `requirements.txt` wholesale into the Android build environment or copy its Windows-specific packages into the spec.

## Android debug build

1. Set up a separate Linux build environment; on Windows, use WSL2. Follow the [official Buildozer installation guide](https://buildozer.readthedocs.io/en/stable/installation/) for your operating system and Python version. It covers system packages, a compatible Python virtual environment, Buildozer installation, and the remaining toolchain dependencies. Apply any toolchain settings the guide requires for that environment.
2. Clone or copy the project into the Linux filesystem, for example `~/PhotoShow`. Under WSL2, build there rather than in `/mnt/c/...`, and keep the Linux build environment separate from the Windows virtual environment.
3. Activate the build virtual environment created in step 1, then run:

   ```bash
   cd ~/PhotoShow
   buildozer -v android debug
   ```

Use the existing `buildozer.spec`. The first build downloads additional Android tools; generated packages are written to `bin/`. See the [official quickstart](https://buildozer.readthedocs.io/en/stable/quickstart/) for deployment commands.
