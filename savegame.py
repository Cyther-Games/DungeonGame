"""
Save files for the Open World mode — one slot, written at a village save shrine.

    saves/openworld.sav   the run itself (pickled, zlib-compressed)
    saves/openworld.json  a small summary the main menu shows next to "Continue"

Writes go to a temp file first and are swapped in, so a crash mid-save can't wreck the
previous save. Shared by move.py (save / load) and main_menu.py (is there a save?).
"""
import json
import os
import pickle
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(HERE, "saves")
SLOT = "openworld"
VERSION = 1


def _paths():
    return os.path.join(SAVE_DIR, SLOT + ".sav"), os.path.join(SAVE_DIR, SLOT + ".json")


def _write_atomic(path, blob):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)


def write(data, meta):
    """Save the run. Raises on failure (the caller tells the player)."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    sav, js = _paths()
    data = dict(data, version=VERSION)
    _write_atomic(sav, zlib.compress(pickle.dumps(data, protocol=4), 6))
    _write_atomic(js, json.dumps(dict(meta, version=VERSION), indent=1).encode("utf-8"))


def read():
    """The saved run, or None if there's no usable save."""
    sav, _ = _paths()
    try:
        with open(sav, "rb") as f:
            data = pickle.loads(zlib.decompress(f.read()))
    except (OSError, ValueError, EOFError, pickle.UnpicklingError, zlib.error, AttributeError, ImportError):
        return None
    return data if isinstance(data, dict) and data.get("version") == VERSION else None


def meta():
    """The summary for the main menu, or None."""
    sav, js = _paths()
    if not os.path.exists(sav):
        return None
    try:
        with open(js, "r", encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return {}
    return m if m.get("version") == VERSION else None


def exists():
    return meta() is not None
