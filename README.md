# Dungeon

A top-down elemental RPG made with pygame. It runs on Windows, macOS and Linux.

## Playing

**Windows:** double-click `run.bat`.

**macOS:** double-click `run.command`. The first time, macOS may say it can't be opened
because it's from an unidentified developer: right-click it, choose **Open**, then **Open**
again. You can also open Terminal in the game folder and run:

```sh
bash run.sh
```

**Linux:** open a terminal in the game folder and run:

```sh
bash run.sh
```

The first time it runs, `run.sh` makes a private Python environment in a `.venv` folder
next to the game and installs pygame and numpy into it, so it needs an internet connection
once. After that it starts straight away. Delete `.venv` to make it set up again, and run
`bash run.sh check` to see which Python and pygame it uses.

Press **F11** (or **Alt+Enter**) at any time to switch between fullscreen and a window.

**Android:** the app is built by GitHub Actions: open the repository's **Actions** tab,
choose **Android build**, then **Run workflow**. When it finishes (the first build takes
about an hour), download **Dungeon-android** from the run's Artifacts, unzip it and install
the `.apk` on your phone (Android asks you to allow installing apps from that source).
On a phone there's a stick to walk (push it to the edge to run), a **Use** button to talk
and interact, a pause button top right, and everything else is tapped. To try the touch
controls on a PC, start the game with `python main.py --touch`.

## What it needs

- **Python 3.9 or newer.** On Python 3.9–3.13 the game uses pygame; on 3.14 and newer
  (which pygame doesn't support yet) it uses pygame-ce, a drop-in fork. `requirements.txt`
  picks the right one.
- **macOS:** Python from [python.org](https://www.python.org/downloads/) or Homebrew
  (`brew install python`).
- **Ubuntu / Debian:** the venv module, if it isn't installed already:
  `sudo apt install python3-venv`.
- **Fonts:** the game is laid out for Georgia, which Windows and macOS include. On Linux,
  where Georgia usually isn't installed, it uses the closest serif font available (Noto
  Serif, Liberation Serif, DejaVu Serif, ...) at a size that measures the same, so
  everything still fits.

## Files

Saves, and your Video and Audio settings, go in `saves/` inside the game folder, on every
system.
