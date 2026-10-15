#!/usr/bin/env bash
# Run make-shorts.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$HERE/.venv/bin/python" ]; then
    echo "ytshorts is not set up yet. Run ./setup.sh first."
    exit 1
fi
exec "$HERE/.venv/bin/python" -m ytshorts.make_shorts "$@"
