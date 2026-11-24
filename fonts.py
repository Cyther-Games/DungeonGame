"""
The game's serif face, the same size on Windows, macOS and Linux.

The UI is laid out for Georgia, which Windows and macOS both ship. Most Linux systems
don't have it, so there the closest serif that is installed (Gelasio, Noto Serif,
Liberation Serif, DejaVu Serif, ...) is used instead, resized so that its text is as wide
as Georgia's would be. Labels, buttons and boxes therefore fit the same way everywhere.
"""
import os

import pygame

# Width of _REF in Georgia, per pixel of font size (measured on Windows; macOS ships the
# same font files). Georgia is the same height in every style: 1.14 x the size.
_REF = "The quick brown fox jumps over the lazy dog 0123456789"
_GEORGIA_W = {(False, False): 25.39, (True, False): 29.30, (False, True): 25.75, (True, True): 29.72}
_FALLBACKS = ["gelasio", "notoserif", "liberationserif", "tinos", "dejavuserif", "freeserif",
              "nimbusroman", "palatinolinotype", "timesnewroman", "times"]
# Android has no font lookup pygame can use, but every phone ships Noto Serif here.
_ANDROID_DIR = "/system/fonts"
_ANDROID_FILES = {(False, False): "NotoSerif-Regular.ttf", (True, False): "NotoSerif-Bold.ttf",
                  (False, True): "NotoSerif-Italic.ttf", (True, True): "NotoSerif-BoldItalic.ttf"}
_cache = {}
_face = {}


def _is_georgia(path):
    return bool(path) and os.path.basename(path).lower().startswith("georgia")


def _pick():
    """('georgia', None) when Georgia is installed, else (family name, None) of the first
    installed fallback, else (None, None) for pygame's built-in font."""
    if "pick" not in _face:
        if _is_georgia(pygame.font.match_font("georgia")):
            _face["pick"] = "georgia"
        else:
            # match_font quietly substitutes a look-alike for a missing name, so check the
            # file it found really is the family that was asked for
            _face["pick"] = None
            for name in _FALLBACKS:
                p = pygame.font.match_font(name)
                if p and name[:5] in os.path.basename(p).lower().replace(" ", "").replace("-", ""):
                    _face["pick"] = name
                    break
            if _face["pick"] is None and os.path.exists(
                    os.path.join(_ANDROID_DIR, _ANDROID_FILES[(False, False)])):
                _face["pick"] = "android:notoserif"
        print(f"Fonts: using {_face['pick'] or 'the built-in font'}"
              + ("" if _face["pick"] == "georgia" else " (Georgia isn't installed; sized to match it)"))
    return _face["pick"]


def _make(name, size, bold, italic):
    if name == "android:notoserif":
        path = os.path.join(_ANDROID_DIR, _ANDROID_FILES[(bool(bold), bool(italic))])
        styled = os.path.exists(path)
        f = pygame.font.Font(path if styled else
                             os.path.join(_ANDROID_DIR, _ANDROID_FILES[(False, False)]), size)
        if not styled:                       # that style isn't installed: fake it
            f.set_bold(bold)
            f.set_italic(italic)
        return f
    if name is None:
        f = pygame.font.Font(None, size)
        f.set_bold(bold)
        f.set_italic(italic)
        return f
    return pygame.font.SysFont(name, size, bold=bold, italic=italic)


def serif(size, bold=False, italic=False):
    """A Font at `size` that measures like Georgia at `size`."""
    key = (size, bool(bold), bool(italic))
    f = _cache.get(key)
    if f is not None:
        return f
    name = _pick()
    if name == "georgia":
        f = _make(name, size, bold, italic)
    else:
        target = _GEORGIA_W[(bool(bold), bool(italic))] * size
        lo, hi = max(4, int(size * 0.5)), int(size * 2.0) + 2
        best = None
        while lo <= hi:                          # the largest size that's no wider than Georgia
            mid = (lo + hi) // 2
            cand = _make(name, mid, bold, italic)
            if cand.size(_REF)[0] <= target:
                best, lo = cand, mid + 1
            else:
                hi = mid - 1
        f = best or _make(name, max(4, int(size * 0.5)), bold, italic)
    _cache[key] = f
    return f
