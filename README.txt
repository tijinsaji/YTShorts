YTShorts - make YouTube Shorts from a longer video
==================================================

Pick the moments you want from a long video (a sermon, a talk, a livestream),
give their start and end times, and YTShorts cuts them out and joins them into
one Short. It can also turn a wide video into the vertical 9:16 shape Shorts use.

Works on Windows, macOS and Linux.


WHAT YOU NEED
-------------

  * Python 3.10 or newer  - https://www.python.org/downloads/
      Windows: during installation, tick "Add python.exe to PATH".
      macOS:   the installer from python.org, or "brew install python".
      Linux:   usually already installed. On Ubuntu/Debian also run:
               sudo apt install python3-venv

That's all. The setup script installs everything else, including ffmpeg (the
video program that does the actual cutting). If you already have ffmpeg
installed, YTShorts uses yours instead.

The full list of Python packages is in requirements.txt.


SETUP (ONCE)
------------

1. Download this project:
     - On GitHub, click the green "Code" button, then "Download ZIP",
       and unzip it somewhere you'll find it again, or
     - git clone <this repository's URL>

2. Run the setup script from the project folder:

     Windows:        double-click setup.bat
     macOS / Linux:  open a Terminal in the project folder and run:
                       bash setup.sh

   This creates a ".venv" folder inside the project with everything installed.
   It does not change anything else on your computer. To uninstall, just
   delete the project folder.


MAKING A SHORT
--------------

Windows:        double-click make_shorts.bat
                (or drag your video file onto make_shorts.bat)
macOS / Linux:  ./make_shorts.sh

It asks for the video, then for your clips, one per line, in the order they
should appear in the Short:

    Clip 1: 1:09:34 1:10:18 Intro
    Clip 2: 1:11:45 1:12:21 The main point
    Clip 3:                         <- press Enter on an empty line to finish

Each line is:   start end label

  * Times can be h:mm:ss, m:ss or seconds (decimals are fine: 1:05.5).
  * A dash between the times is fine too: 1:09:34 - 1:10:18
  * The label is optional. It's only shown while the Short is being made.

Finally it asks where to save the Short. Press Enter to save it next to the
video as "<video name>_short.mp4", or type (or drag in) a folder or a file name.
New folders are created for you, and it asks before replacing an existing file.

Using a clips file instead of typing
  Write the clips in a text file (see examples/clips_example.txt) and run:

    Windows:        make_shorts.bat my_video.mp4 --clips my_clips.txt
    macOS / Linux:  ./make_shorts.sh my_video.mp4 --clips my_clips.txt

  In a clips file, blank lines and lines starting with # are ignored, so you
  can keep notes or switch clips off by putting # in front of them.

Options
  --clips FILE      read the clips from a text file instead of typing them
  -o, --output PATH where to save the Short: a file name, or a folder to save
                    "<video name>_short.mp4" into. Skips the question.
  --mode original   keep the video's own shape (default)
  --mode crop       fill the vertical 9:16 frame by cutting off the sides
  --mode blur       vertical 9:16 with the whole video in the middle and a
                    blurred copy of it behind
  --padding SECONDS extra time added before and after every clip so words
                    aren't cut off (default: 0.5)
  --separate        also save each clip as its own file, in a
                    "<short name>_clips" folder next to the Short
  -h, --help        show all options

Example:
  make_shorts.bat sermon.mp4 --clips clips.txt --mode blur -o sermon_short.mp4

YouTube Shorts can be up to 3 minutes long. YTShorts warns you if yours is longer.


USING IT FROM A TERMINAL
------------------------

If you're comfortable with a terminal, activate the environment and use the
command directly from any folder:

  Windows:        .venv\Scripts\activate
  macOS / Linux:  source .venv/bin/activate

  make-shorts my_video.mp4 --clips my_clips.txt --mode crop

Or install it into any Python environment with:   pip install .


TROUBLESHOOTING
---------------

"Python was not found"
    Install Python 3.10+ (see WHAT YOU NEED), then run the setup script again.
    On Windows, make sure "Add python.exe to PATH" was ticked.

"ytshorts is not set up yet"
    Run setup.bat (Windows) or bash setup.sh (macOS / Linux) first.

"Permission denied" when running ./make_shorts.sh
    Run:  chmod +x *.sh   (setup.sh does this for you.)

macOS says the script can't be opened
    Run the scripts from Terminal as shown above rather than double-clicking.

A clip starts or ends mid-word
    Increase --padding, for example --padding 1


PROJECT LAYOUT
--------------

  README.txt                this file
  requirements.txt          Python packages needed
  pyproject.toml            package definition (used by pip / setup scripts)
  setup.bat / setup.sh      one-time setup for Windows / macOS + Linux
  make_shorts.bat / .sh     run make-shorts
  examples/                 example clips file
  ytshorts/                 the Python code
