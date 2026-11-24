# Android build settings for buildozer (https://github.com/kivy/buildozer).
# The APK is built by GitHub Actions (.github/workflows/android.yml); to build it yourself
# on Linux or WSL:  pip install buildozer cython  then  buildozer android debug

[app]
title = Dungeon
package.name = dungeon
package.domain = com.cythergames
version = 0.1

source.dir = .
source.include_exts = py,png,json
# files that are only for making art or for the PC launchers
source.exclude_dirs = .github, .buildozer, bin, saves, .venv, __pycache__, p4a-recipes, tiles, Beta, Prompts, images/_original_stock
source.exclude_patterns = make_element_icons.py, make_pixel_art.py, make_true_icons.py, make_vfx.py, make_vow_cards.py, DND.py, code.py, icons/_sheet_*, images/_sheet_*, vfx/_sheet_*

# python-for-android's own pygame recipe is patched in p4a-recipes/pygame (see there)
requirements = python3, pygame, numpy

icon.filename = %(source.dir)s/icons/Portal.png
orientation = landscape
fullscreen = 1

android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
# The Android SDK's licence has to be accepted for the build to download the SDK.
android.accept_sdk_license = True

p4a.branch = v2026.05.09
p4a.bootstrap = sdl2
p4a.local_recipes = ./p4a-recipes

[buildozer]
log_level = 2
warn_on_root = 1
