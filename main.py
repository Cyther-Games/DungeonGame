"""Start the game.

Android apps built with buildozer / python-for-android always start from main.py, so this
runs move.py from the game folder. On a PC it works the same: `python main.py`.

On Android there's no console to read errors in, so this also reports crashes:
  * an error in the game shows in a pop-up (and is saved to saves/crash.txt)
  * if the app is killed outright (a crash inside pygame or SDL), Python's fault handler
    has written where it was to saves/crash.txt, and the next start shows that
"""
import faulthandler
import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ON_ANDROID = (hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
              or "ANDROID_PRIVATE" in os.environ)
CRASH_FILE = os.path.join(HERE, "saves", "crash.txt")


def show_message(title, text):
    """A pop-up through SDL itself, so it works even when pygame can't load. True if shown."""
    print(title + "\n" + text, flush=True)
    if not ON_ANDROID:
        return False
    try:
        import ctypes
        sdl = ctypes.CDLL("libSDL2.so")
        sdl.SDL_ShowSimpleMessageBox.argtypes = [ctypes.c_uint32, ctypes.c_char_p,
                                                 ctypes.c_char_p, ctypes.c_void_p]
        lines = text.strip().splitlines()
        if len(lines) > 40:
            lines = lines[:6] + ["..."] + lines[-30:]
        return sdl.SDL_ShowSimpleMessageBox(0x10, title.encode("utf-8"),
                                            "\n".join(lines).encode("utf-8", "replace"), None) == 0
    except Exception:
        traceback.print_exc()
        return False


def about():
    bits = ["Python " + sys.version.split()[0]]
    try:
        import pygame
        bits.append("pygame " + pygame.version.ver)
    except Exception:
        pass
    if ON_ANDROID:
        try:
            bits.append("Android API " + str(sys.getandroidapilevel()))
        except Exception:
            pass
    return ", ".join(bits)


crash_log = None
if ON_ANDROID:
    os.makedirs(os.path.dirname(CRASH_FILE), exist_ok=True)
    # what the last run's fault handler left behind, if it was killed
    try:
        with open(CRASH_FILE, encoding="utf-8", errors="replace") as f:
            last = f.read().strip()
    except OSError:
        last = ""
    if last:
        show_message("Dungeon crashed last time", last)
    crash_log = open(CRASH_FILE, "w", encoding="utf-8")
    faulthandler.enable(crash_log)

def game_file():
    """move.py - or, in the Android app, move.pyc: the build compiles the game's code and
    leaves out the .py files."""
    for name in ("move.py", "move.pyc"):
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            return path
    return os.path.join(HERE, "move.py")     # not there: let the error say so


try:
    runpy.run_path(game_file(), run_name="__main__")
except SystemExit:
    pass
except BaseException:
    report = traceback.format_exc() + "\n" + about()
    if crash_log is not None:
        faulthandler.disable()
        crash_log.close()
        crash_log = None
        with open(CRASH_FILE, "w", encoding="utf-8") as f:
            f.write(report)
    if show_message("Dungeon crashed", report + "\n\n(A screenshot of this helps fix it.)"):
        open(CRASH_FILE, "w").close()        # seen now; otherwise it shows at the next start
    if not ON_ANDROID:
        raise
finally:
    if crash_log is not None:                # a clean exit: nothing to report
        faulthandler.disable()
        crash_log.close()
        open(CRASH_FILE, "w").close()
