"""Make an .rgbz copy of each of the game's PNGs for the Android build.

pygame on Android may be unable to read PNGs (its PNG module needs libraries the build
doesn't always include). The game's load_image() then reads these instead: "RGBZ",
width and height (4 bytes each, little-endian), then the RGBA pixels packed with zlib.

Each copy is no bigger than the game ever draws that picture: element icons at most
256x256 (the game's own master size) and vow cards at most 240x360 (the size they're
shown at), so the app stays small and loads quickly.

usage: python .github/workflows/pack_images.py   (from the repository's top folder)
"""
import glob
import os
import zlib

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

LIMITS = {"icons": (256, 256), "bindings/cards": (240, 360)}

pygame.init()
pygame.display.set_mode((1, 1))
made = skipped = 0
for path in sorted(glob.glob("icons/*.png") + glob.glob("images/*.png") + glob.glob("vfx/*.png")
                   + glob.glob("bindings/cards/*.png")):
    if os.path.basename(path).startswith("_sheet_"):
        continue
    try:
        img = pygame.image.load(path).convert_alpha()
    except pygame.error as e:
        print(f"skip {path}: {e}")
        skipped += 1
        continue
    limit = LIMITS.get(os.path.dirname(path).replace("\\", "/"))
    w, h = img.get_size()
    if limit and (w > limit[0] or h > limit[1]):
        s = min(limit[0] / w, limit[1] / h)
        img = pygame.transform.smoothscale(img, (max(1, round(w * s)), max(1, round(h * s))))
        w, h = img.get_size()
    data = b"RGBZ" + w.to_bytes(4, "little") + h.to_bytes(4, "little") + \
        zlib.compress(pygame.image.tobytes(img, "RGBA"), 9)
    with open(os.path.splitext(path)[0] + ".rgbz", "wb") as f:
        f.write(data)
    made += 1
print(f"{made} .rgbz copies made, {skipped} skipped")
