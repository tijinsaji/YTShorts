#!/usr/bin/env bash
# One-time setup for macOS and Linux: creates a .venv folder and installs ytshorts into it.
set -e
cd "$(dirname "$0")"

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "Python was not found. Install Python 3.10 or newer:"
    echo "  macOS:         https://www.python.org/downloads/  (or: brew install python)"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    exit 1
fi

if ! "$PY" -c "import sys; sys.exit(sys.version_info < (3, 10))"; then
    echo "Python 3.10 or newer is required. You have: $("$PY" --version)"
    exit 1
fi

echo "Creating virtual environment in .venv ..."
if ! "$PY" -m venv .venv; then
    echo "Could not create the virtual environment."
    echo "On Ubuntu/Debian, install venv support with: sudo apt install python3-venv"
    exit 1
fi

echo "Installing ytshorts and its requirements ..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

chmod +x make_shorts.sh make_subtitles.sh
echo
echo "Setup complete. Run ./make_shorts.sh to get started."
