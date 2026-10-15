"""Find an ffmpeg to use on any operating system."""

import shutil
import sys


def find_ffmpeg() -> str:
    """Return the path to ffmpeg.

    Uses the ffmpeg installed on the system if there is one, otherwise the copy
    that comes with the imageio-ffmpeg package (installed by setup).
    """
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        sys.exit("ffmpeg was not found. Run the setup script again, "
                 "or install ffmpeg yourself: https://ffmpeg.org/download.html")
