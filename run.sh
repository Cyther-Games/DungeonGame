#!/usr/bin/env bash
# Launch the game on macOS or Linux.
#
#     bash run.sh          play
#     bash run.sh check    show which Python it would use, and with what
#
# The first time, this makes a private Python environment in .venv/ next to the game and
# installs pygame and numpy into it (that needs an internet connection, once). After that
# it just starts the game. Delete .venv/ to make it set everything up again.
set -u
cd "$(dirname "$0")" || exit 1
VENV=".venv"

say()  { printf '%s\n' "$*"; }
fail() { say ""; say "  $*"; say ""; exit 1; }

has_libs() { "$1" -c "import pygame, numpy" >/dev/null 2>&1; }

version_ok() {   # Python 3.9 or newer
    "$1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1
}

PY=""

# 1) the game's own environment, from an earlier run
if [ -x "$VENV/bin/python" ] && has_libs "$VENV/bin/python"; then
    PY="$VENV/bin/python"
fi

# 2) a Python that already has pygame and numpy
if [ -z "$PY" ]; then
    for c in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python3.14 python; do
        p="$(command -v "$c" 2>/dev/null)" || continue
        if version_ok "$p" && has_libs "$p"; then PY="$p"; break; fi
    done
fi

# 3) set up .venv: prefer a Python that plain pygame supports (3.9-3.13); newer ones
#    get pygame-ce instead (requirements.txt picks the right one)
if [ -z "$PY" ]; then
    BASE=""
    for c in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python3.14 python; do
        p="$(command -v "$c" 2>/dev/null)" || continue
        if version_ok "$p"; then BASE="$p"; break; fi
    done
    if [ -z "$BASE" ]; then
        if [ "$(uname)" = "Darwin" ]; then
            fail "Python 3 wasn't found. Install it from https://www.python.org/downloads/ (or: brew install python), then run this again."
        fi
        fail "Python 3 wasn't found. Install it with your package manager (for example: sudo apt install python3 python3-venv), then run this again."
    fi
    say "First run: setting up the game's Python environment with $("$BASE" --version 2>&1)..."
    rm -rf "$VENV"
    if ! "$BASE" -m venv "$VENV" >/dev/null 2>&1; then
        rm -rf "$VENV"
        ver="$("$BASE" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
        fail "Couldn't create a Python environment. On Ubuntu/Debian install the venv module first:
      sudo apt install python3-venv      (or: sudo apt install python${ver}-venv)
  then run this again."
    fi
    say "Installing pygame and numpy (only this once)..."
    if ! "$VENV/bin/python" -m pip install --disable-pip-version-check -q -r requirements.txt; then
        rm -rf "$VENV"
        fail "Installing pygame/numpy failed (see above). Check your internet connection and run this again."
    fi
    PY="$VENV/bin/python"
fi

if [ "${1:-}" = "check" ]; then
    say "Would run with: $PY"
    "$PY" -c "import sys, pygame, numpy; print('Python', sys.version.split()[0], '|', 'pygame-ce' if getattr(pygame, 'IS_CE', False) else 'pygame', pygame.version.ver, '| numpy', numpy.__version__)"
    exit 0
fi

exec "$PY" move.py "$@"
