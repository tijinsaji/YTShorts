#!/usr/bin/env python3
"""
Create subtitles for a video, shown on a light grey rectangle placed over the video.

The subtitles are read from a plain text file (.txt) or an .srt file. Each subtitle needs a start
time, an end time and the text. The times are measured from the start of the video you are
subtitling (so the first subtitle of a Short is near 0:00).

Accepted layouts (mix and match, one subtitle per entry):

    0:00 - 0:04  Why did Aaron's sons fail?          <- everything on one line
    [00:05 - 00:09] Copying someone will not bring the blessing
    00:00:10.000 --> 00:00:13.500 There are no shortcuts

    00:00:14,000 --> 00:00:17,000                    <- or SRT style, text on the next line(s)
    It has to come from within

Times can be m:ss, h:mm:ss, or with decimals (0:04.5 or 00:00:04,500).

Uses the system ffmpeg if installed, otherwise the one from the imageio-ffmpeg package.
ffmpeg needs its standard 'libass' subtitle support, which both include.

Usage:
    make-subtitles short.mp4
    make-subtitles short.mp4 subtitles.txt
    make-subtitles short.mp4 subtitles.txt -o short_final.mp4
    make-subtitles short.mp4 subtitles.txt --box-y 0.7 --font-size 70 --box-opacity 0.9
    make-subtitles short.mp4 subtitles.txt --box-until 1:15    # box disappears at 1:15
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from ytshorts.ffmpeg import find_ffmpeg
except ImportError:                 # run directly as a script: python ytshorts/make_subtitles.py
    from ffmpeg import find_ffmpeg

# A time such as 4, 0:04, 1:09:35, 0:04.5 or 00:00:04,500
_TIME = r"\d+(?::\d+){0,2}(?:[.,]\d+)?"
# Two times joined by "-->", a dash, "to" ... e.g. "0:00 - 0:04" or "[00:05 --> 00:09]"
RANGE_RE = re.compile(
    rf"^\W*?({_TIME})\s*(?:-->|–|—|-|to)\s*({_TIME})\W*?(?=\s|$|[\]\)\-:])"
)


def to_seconds(value: str) -> float:
    """Convert 'ss', 'm:ss', 'h:mm:ss' (optionally with .fraction or ,fraction) to seconds."""
    value = value.replace(",", ".")
    seconds = 0.0
    for part in value.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)                              # drop <i>, <b> ... tags
    text = text.replace("\\", " ").replace("{", "(").replace("}", ")")  # keep ASS safe
    return re.sub(r"\s+", " ", text).strip()


def parse_subtitles(path: Path) -> list:
    """
    Read a .txt or .srt subtitle file into a list of (start, end, text).

    A line that starts with two times is the start of a subtitle. Any text after the times on the
    same line belongs to it; if there is none, the following lines (until a blank line or the next
    time range) are used. Lines that are only a number (SRT counters) are ignored.
    """
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    current = None   # [start, end, [text parts]]

    def finish() -> None:
        if current:
            text = clean_text(" ".join(current[2]))
            if text:
                cues.append((current[0], current[1], text))

    for line in raw.split("\n"):
        stripped = line.strip()
        match = RANGE_RE.match(stripped)
        if match:
            finish()
            current = [to_seconds(match.group(1)), to_seconds(match.group(2)), []]
            rest = stripped[match.end():].lstrip(" \t]):-–—|")
            if rest:
                current[2].append(rest)
        elif not stripped:
            finish()
            current = None
        elif current is not None and not re.fullmatch(r"\d+", stripped):
            current[2].append(stripped)
    finish()
    return cues


def ass_time(seconds: float) -> str:
    """Format seconds as an ASS timestamp (H:MM:SS.cc)."""
    centis = max(0, int(round(seconds * 100)))
    hours, rest = divmod(centis, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centis = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def hex_to_bgr(value: str) -> str:
    """'D3D3D3' or '#d3d3d3' (RGB) -> 'D3D3D3' in ASS order (BGR)."""
    value = value.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        sys.exit(f"Colours must be 6-digit hex like D3D3D3, got: {value}")
    r, g, b = value[0:2], value[2:4], value[4:6]
    return f"{b}{g}{r}".upper()


def probe(ffmpeg: str, video: Path) -> tuple:
    """Return (width, height, duration_in_seconds) of the video.

    Reads what 'ffmpeg -i' reports, so ffprobe isn't needed (the ffmpeg that setup
    installs doesn't come with it).
    """
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    size = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})[\s,\[]", result.stderr)
    length = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr)
    if not size or not length:
        sys.exit(f"Could not read the size and length of {video}. Is it a video file?")
    hours, minutes, seconds = length.groups()
    return (int(size.group(1)), int(size.group(2)),
            int(hours) * 3600 + int(minutes) * 60 + float(seconds))


# Character widths of Arial (the same as Helvetica) in 1/1000 of the font's em size.
_ARIAL_WIDTHS = dict(zip(
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
    [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
     556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015,
     667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722,
     667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333,
     556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333,
     500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584],
))
_ARIAL_WIDTHS.update({"‘": 222, "’": 222, "“": 333, "”": 333, "–": 556, "—": 1000, "…": 1000})
_ARIAL_LIKE = {"arial", "helvetica", "liberation sans", "arimo"}


class TextMeasure:
    """Estimate how wide a line of text is drawn, in video pixels.

    libass scales a font so that its full height (ascent + descent) equals the font
    size; for Arial that makes the em about font_size / 1.117. Other fonts are
    measured with Arial's widths plus a safety margin, so the box errs on the large side.
    """

    def __init__(self, font: str, font_size: int, bold: bool):
        arial = font.lower() in _ARIAL_LIKE
        self.em = font_size / 1.117 if arial else font_size * 1.1
        self.scale = 1.1 if bold else 1.0          # bold glyphs are wider

    def width(self, text: str) -> float:
        units = sum(_ARIAL_WIDTHS.get(ch, 700) for ch in text)
        return units / 1000 * self.em * self.scale

    def wrap(self, text: str, max_width: float) -> list:
        """Break text into lines no wider than max_width (very long words are split)."""
        lines, line = [], ""
        for word in text.split():
            while self.width(word) > max_width and len(word) > 1:
                cut = len(word) - 1
                while cut > 1 and self.width(word[:cut]) > max_width:
                    cut -= 1
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:cut])
                word = word[cut:]
            candidate = f"{line} {word}" if line else word
            if line and self.width(candidate) > max_width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        return lines


def build_ass(cues, width, height, duration, args) -> str:
    font_size = args.font_size or int(height * 0.042)
    text_bgr = hex_to_bgr(args.text_color)
    box_bgr = hex_to_bgr(args.box_color)
    box_alpha = f"{int(round((1 - args.box_opacity) * 255)):02X}"   # ASS: 00 = solid, FF = invisible

    # Box geometry: each subtitle is wrapped to fit inside the frame (with side gaps),
    # then its box is sized to the wrapped text plus padding, centred around --box-y.
    measure = TextMeasure(args.font, font_size, args.bold)
    side = int(width * 0.05)
    pad = int(font_size * 0.4)
    line_h = font_size * 1.15                  # libass line spacing is about the font size
    max_text_w = width - 2 * side - 2 * pad

    def box_for(lines) -> tuple:
        text_w = max((measure.width(line) for line in lines), default=0)
        text_h = max(len(lines), args.lines) * line_h
        return int(text_w + 2 * pad + 0.5), int(text_h + 2 * pad + 0.5)

    wrapped = [(start, end, measure.wrap(text, max_text_w)) for start, end, text in cues]
    centre_y = int(height * args.box_y)

    def box_tags(box_w, box_h) -> tuple:
        """Return the ASS drawing for a box of this size, and the centre point for its text."""
        box_x = (width - box_w) // 2
        box_y = max(0, min(centre_y - box_h // 2, height - box_h))
        drawing = ("{\\an7\\pos(" + f"{box_x},{box_y}" + ")\\p1\\1c&H" + box_bgr + "&\\1a&H" + box_alpha +
                   "&\\bord0\\shad0}" + f"m 0 0 l {box_w} 0 {box_w} {box_h} 0 {box_h}" + "{\\p0}")
        return drawing, (width // 2, box_y + box_h // 2)

    bold = -1 if args.bold else 0
    out = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",                        # no automatic wrapping: lines are broken here

        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{args.font},{font_size},&H00{text_bgr},&H00{text_bgr},&H00000000,&H00000000,"
        f"{bold},0,0,0,100,100,0,0,1,0,0,5,{side + pad},{side + pad},0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def add_text(start, end, lines, centre) -> None:
        out.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,"
                   "{\\an5\\pos(" + f"{centre[0]},{centre[1]}" + ")}" + "\\N".join(lines))

    if args.box_mode == "always":
        # One box that stays on screen (until --box-until, if given), big enough for the largest subtitle.
        sizes = [box_for(lines) for _, _, lines in wrapped] or [box_for([])]
        drawing, centre = box_tags(max(w for w, _ in sizes), max(h for _, h in sizes))
        box_end = args.box_until if args.box_until is not None else duration + 1
        out.append(f"Dialogue: 0,{ass_time(0)},{ass_time(box_end)},Caption,,0,0,0,,{drawing}")
        for start, end, lines in wrapped:
            add_text(start, end, lines, centre)
    else:
        # A box per subtitle, fitted to that subtitle's text.
        for start, end, lines in wrapped:
            drawing, centre = box_tags(*box_for(lines))
            out.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{drawing}")
            add_text(start, end, lines, centre)
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="make-subtitles",
                                     description="Burn subtitles onto a light grey box over a video.")
    parser.add_argument("video", help="the video to add subtitles to (e.g. short.mp4)")
    parser.add_argument("subs", nargs="?", default="subtitles.txt",
                        help="the English subtitle text file with timestamps (.txt or .srt; "
                             "default: subtitles.txt)")
    parser.add_argument("-o", "--output", default=None,
                        help="output file (default: <video name>_subtitled.mp4)")
    parser.add_argument("--box-color", default="D3D3D3", help="rectangle colour, hex RGB (default: D3D3D3, light grey)")
    parser.add_argument("--box-opacity", type=float, default=0.85,
                        help="0 = invisible, 1 = solid (default: 0.85)")
    parser.add_argument("--box-mode", choices=["always", "with-text"], default="always",
                        help="always = one box stays on screen, sized for the longest subtitle; "
                             "with-text = a box fitted to each subtitle, shown only while it shows")
    parser.add_argument("--box-y", type=float, default=0.72,
                        help="vertical position of the box centre as a fraction of the height "
                             "(0 = top, 1 = bottom; default: 0.72)")
    parser.add_argument("--lines", type=int, default=1,
                        help="minimum box height, in text lines; the box always grows to fit the "
                             "text (default: 1)")
    parser.add_argument("--text-color", default="202020", help="text colour, hex RGB (default: 202020, dark grey)")
    parser.add_argument("--font", default="Arial", help="font name (default: Arial)")
    parser.add_argument("--font-size", type=int, default=0,
                        help="font size in pixels (default: about 4.2%% of the video height)")
    parser.add_argument("--bold", action="store_true", help="use bold text")
    parser.add_argument("--box-until", metavar="TIME", default=None,
                        help="time at which the box (and any subtitle still showing) disappears, "
                             "e.g. 1:15 or 75.5; subtitles starting after it are left out "
                             "(default: the box stays until the end of the video)")
    parser.add_argument("--keep-ass", action="store_true",
                        help="also save the generated .ass file next to the output, for manual tweaking")
    args = parser.parse_args()

    if args.box_until is not None:
        try:
            args.box_until = to_seconds(args.box_until.strip())
        except ValueError:
            sys.exit(f"--box-until must be a time like 1:15 or 75.5, got: {args.box_until}")

    ffmpeg = find_ffmpeg()

    video = Path(args.video).resolve()
    subs = Path(args.subs)
    if not video.is_file():
        sys.exit(f"Video file not found: {video}")
    if not subs.is_file():
        sys.exit(f"Subtitle file not found: {subs}")

    output = Path(args.output).resolve() if args.output else video.with_name(video.stem + "_subtitled.mp4")

    cues = parse_subtitles(subs)
    if not cues:
        sys.exit(f"No subtitles were found in {subs}. Each subtitle needs a time range and some text, "
                 "e.g. '0:00 - 0:04  Your subtitle text'. See the top of this script for the accepted layouts.")
    cues.sort(key=lambda cue: cue[0])

    if args.box_until is not None:
        limit = args.box_until
        dropped = sum(1 for start, _, _ in cues if start >= limit)
        trimmed = sum(1 for start, end, _ in cues if start < limit < end)
        cues = [(start, min(end, limit), text) for start, end, text in cues if start < limit]
        print(f"Box ends at {ass_time(limit)}." +
              (f" {trimmed} subtitle(s) cut short there." if trimmed else "") +
              (f" {dropped} later subtitle(s) left out." if dropped else ""))
        if not cues:
            sys.exit("No subtitles start before --box-until, so there is nothing to show.")

    width, height, duration = probe(ffmpeg, video)
    print(f"Video: {width}x{height}, {duration:.1f} s   Subtitles: {len(cues)} lines")
    if max(end for _, end, _ in cues) > duration + 1:
        print("Warning: the subtitles run longer than the video. "
              "Check that the times in the subtitle file are measured from the start of this video.")

    ass_text = build_ass(cues, width, height, duration, args)

    with tempfile.TemporaryDirectory() as tmp:
        ass_path = Path(tmp) / "subs.ass"
        ass_path.write_text(ass_text, encoding="utf-8")

        # Run inside the temp folder so the filter path is a plain file name (avoids Windows path issues).
        command = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video),
            "-vf", "ass=subs.ass",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart",
            str(output),
        ]
        print("Adding subtitles...")
        result = subprocess.run(command, cwd=tmp)
        if result.returncode != 0:
            sys.exit("ffmpeg failed. If the error mentions the 'ass' filter, your ffmpeg build lacks "
                     "libass; install a full build from https://ffmpeg.org/download.html")

        if args.keep_ass:
            shutil.copy(ass_path, output.with_suffix(".ass"))

    print(f"Done: {output}")


if __name__ == "__main__":
    main()
