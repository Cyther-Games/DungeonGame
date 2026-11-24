"""Start the game.

Android apps built with buildozer / python-for-android always start from main.py, so this
just runs move.py from the game folder. On a PC it works the same: `python main.py`.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
runpy.run_path(os.path.join(HERE, "move.py"), run_name="__main__")
