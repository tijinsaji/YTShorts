#!/usr/bin/env python3
"""
Cut timestamp ranges out of a video and join them into one Short.

Uses the system ffmpeg if installed, otherwise the one from the imageio-ffmpeg package.

Usage:
    make-shorts my_video.mp4                       # type the clips in when asked
    make-shorts my_video.mp4 --clips clips.txt     # read the clips from a file
    make-shorts my_video.mp4 --mode crop --padding 0.5
    make-shorts my_video.mp4 --separate            # also keep each clip as its own file

Clips are entered one per line, in the order they should appear in the Short:
    start end label
    1:09:35 1:09:40 What are the reason of our blessing
A "-" between the times is fine too (1:09:35 - 1:09:40). The label is optional.
In a clips file, blank lines and lines starting with # are ignored.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ytshorts.ffmpeg import find_ffmpeg

WIDTH, HEIGHT, FPS = 1080, 1920, 30


def to_seconds(ts: str) -> float:
    """Convert 'h:mm:ss', 'm:ss' or 'ss' to seconds."""
    parts = [float(p) for p in ts.split(":")]
    if len(parts) > 3 or any(p < 0 for p in parts):
        raise ValueError(ts)
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def parse_clip(line: str) -> tuple[str, str, str]:
    """Turn 'start end label' (or 'start - end label') into a clip tuple."""
    tokens = line.split()
    if len(tokens) >= 3 and tokens[1] == "-":
        del tokens[1]
    if len(tokens) < 2:
        raise ValueError("need a start and an end time, e.g. 1:09:35 1:09:40 My label")
    start_ts, end_ts, label = tokens[0], tokens[1], " ".join(tokens[2:])
    try:
        start, end = to_seconds(start_ts), to_seconds(end_ts)
    except ValueError:
        raise ValueError(f"'{start_ts}' or '{end_ts}' is not a valid time (use h:mm:ss, m:ss or ss)")
    if end <= start:
        raise ValueError(f"end time {end_ts} must be after start time {start_ts}")
    return start_ts, end_ts, label or f"Clip {start_ts}"


def read_clips_file(path: Path) -> list[tuple[str, str, str]]:
    """Read clips from a text file, one per line."""
    clips = []
    for n, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            clips.append(parse_clip(line))
        except ValueError as e:
            sys.exit(f"{path}, line {n}: {e}")
    return clips


def ask_for_clips() -> list[tuple[str, str, str]]:
    """Let the user type the clips in, one per line, until a blank line."""
    print("Enter your clips one per line, in the order they should appear:")
    print("    start end label      e.g.  1:09:35 1:09:40 What are the reason of our blessing")
    print("Press Enter on an empty line when you're done.\n")
    clips = []
    while True:
        try:
            line = input(f"Clip {len(clips) + 1}: ").strip("﻿ \t")
        except EOFError:
            break
        if not line:
            if clips:
                break
            print("  Please enter at least one clip.")
            continue
        try:
            clips.append(parse_clip(line))
        except ValueError as e:
            print(f"  {e} - try again.")
    return clips


def video_filter(mode: str) -> list[str]:
    """Return the ffmpeg filter arguments for the chosen layout."""
    tail = f"fps={FPS},format=yuv420p,setsar=1"
    if mode == "crop":
        # Fill the vertical frame by center-cropping (cuts off the sides).
        return ["-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                       f"crop={WIDTH}:{HEIGHT},{tail}"]
    if mode == "blur":
        # Whole video in the middle, blurred copy of it as the background.
        graph = (
            f"[0:v]split[a][b];"
            f"[a]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},boxblur=20:5[bg];"
            f"[b]scale={WIDTH}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{tail}[v]"
        )
        return ["-filter_complex", graph, "-map", "[v]", "-map", "0:a?"]
    # "original": keep the original shape, just normalise the frame rate.
    return ["-vf", tail]


def cut_clip(ffmpeg: str, src: Path, dest: Path, start: float, end: float, mode: str) -> None:
    """Cut one clip with exact timing (re-encodes so cuts are frame-accurate)."""
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{end - start:.3f}",
        *video_filter(mode),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="make-shorts", description="Cut timestamps from a video and join them.")
    parser.add_argument("video", nargs="?",
                        help="path to the source video file (if left out, you'll be asked for it)")
    parser.add_argument("-o", "--output", default="short.mp4", help="output file (default: short.mp4)")
    parser.add_argument("--padding", type=float, default=0.5,
                        help="seconds added before and after each clip so words aren't cut off (default: 0.5)")
    parser.add_argument("--mode", choices=["original", "crop", "blur"], default="original",
                        help="original = keep shape, crop = fill 9:16 by cropping sides, "
                             "blur = 9:16 with blurred background (default: original)")
    parser.add_argument("--separate", action="store_true",
                        help="also keep each clip as its own file in a 'clips' folder")
    parser.add_argument("--clips", metavar="FILE",
                        help="text file with one 'start end label' per line "
                             "(if left out, you'll be asked to type the clips in)")
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()

    video = args.video
    while not video:
        # Dragging a file into the terminal often adds quotes around the path.
        video = input("Path to the video (you can drag the file here): ").strip("﻿ \"'")
    src = Path(video)
    if not src.is_file():
        sys.exit(f"Video file not found: {src}")

    if args.clips:
        clips_file = Path(args.clips)
        if not clips_file.is_file():
            sys.exit(f"Clips file not found: {clips_file}")
        clips = read_clips_file(clips_file)
        if not clips:
            sys.exit(f"No clips found in {clips_file}")
    else:
        clips = ask_for_clips()
        if not clips:
            sys.exit("No clips entered.")

    clips_dir = Path("clips")
    if args.separate:
        clips_dir.mkdir(exist_ok=True)

    total = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        list_lines = []

        for i, (start_ts, end_ts, label) in enumerate(clips, start=1):
            start = max(0.0, to_seconds(start_ts) - args.padding)
            end = to_seconds(end_ts) + args.padding
            total += end - start

            part = tmp_dir / f"part_{i:02d}.mp4"
            print(f"[{i:02d}/{len(clips)}] {start_ts} - {end_ts}  {label}")
            cut_clip(ffmpeg, src, part, start, end, args.mode)

            list_lines.append(f"file '{part.as_posix()}'")
            if args.separate:
                shutil.copy(part, clips_dir / f"{i:02d}_{start_ts.replace(':', '-')}.mp4")

        list_file = tmp_dir / "list.txt"
        list_file.write_text("\n".join(list_lines) + "\n", encoding="utf-8")

        print("Joining clips...")
        subprocess.run([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", "-movflags", "+faststart", args.output,
        ], check=True)

    print(f"\nDone: {args.output}  (about {total:.0f} seconds)")
    if total > 180:
        print("Warning: this is longer than 3 minutes, which is over the YouTube Shorts limit.")


if __name__ == "__main__":
    main()
