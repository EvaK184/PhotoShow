"""Keep FFmpeg on the API supported by ffpyplayer 4.5.x."""

from pythonforandroid.recipes.ffmpeg import FFMpegRecipe


class PhotoShowFFmpegRecipe(FFMpegRecipe):
    version = "6.1.6"
    # Upstream's patches target FFmpeg 8. The 6.1 configure script can
    # discover the Android OpenSSL build through the recipe's flags.
    patches = []


recipe = PhotoShowFFmpegRecipe()
