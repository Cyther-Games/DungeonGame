"""
Village and house-interior art, in the same procedural pixel style as make_tiles.py:
houses for every biome (80x64, a 5x3-tile footprint with the roof rising a tile above it),
the village furniture (well, lamp posts, fences, signposts, barrels, crates, flower beds,
cobbles) and everything inside a house (plank floors, panelled walls, beds, shelves,
fireplaces, tables, rugs, windows, a doormat).

make_tiles.build_tileset() pulls these in through village_tiles().
Run directly for a review sheet:  python make_village.py
"""
import os

import numpy as np
import pygame

from make_tiles import T, blank, put, mix, shade, textured, outline, blob, to_surface, OUT

EDGE = (30, 22, 32)


# ---------------------------------------------------------------------------- helpers

def rect(a, x, y, w, h, col):
    hh, ww = a.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(ww, x + w), min(hh, y + h)
    if x1 > x0 and y1 > y0:
        a[y0:y1, x0:x1, :3] = col
        a[y0:y1, x0:x1, 3] = 255


def hline(a, x0, x1, y, col):
    rect(a, x0, y, x1 - x0 + 1, 1, col)


def vline(a, x, y0, y1, col):
    rect(a, x, y0, 1, y1 - y0 + 1, col)


# ---------------------------------------------------------------------------- houses

# biome: wall (base, dark, light), trim (timber/stone), roofs (3 variants: base colours), style
HOUSE_STYLES = {
    "meadow":   {"wall": ((232, 220, 190), (198, 184, 150), (246, 238, 214)), "trim": (112, 74, 44),
                 "roofs": [(184, 64, 52), (64, 112, 176), (78, 134, 74)], "kind": "gable", "base": (130, 124, 116)},
    "tundra":   {"wall": ((150, 104, 66), (116, 78, 48), (176, 128, 84)), "trim": (88, 58, 36),
                 "roofs": [(70, 96, 140), (120, 60, 56), (84, 90, 104)], "kind": "snowy", "base": (120, 128, 140)},
    "desert":   {"wall": ((218, 188, 136), (186, 152, 102), (236, 212, 164)), "trim": (160, 120, 76),
                 "roofs": [(196, 84, 60), (60, 130, 140), (200, 160, 60)], "kind": "flat", "base": (170, 138, 92)},
    "volcanic": {"wall": ((96, 86, 84), (70, 62, 62), (122, 110, 104)), "trim": (52, 44, 44),
                 "roofs": [(126, 40, 34), (60, 56, 64), (150, 78, 34)], "kind": "gable", "base": (60, 52, 52)},
    "storm":    {"wall": ((118, 124, 150), (90, 96, 122), (146, 152, 176)), "trim": (64, 66, 90),
                 "roofs": [(92, 70, 146), (50, 110, 120), (70, 74, 96)], "kind": "gable", "base": (76, 80, 100)},
}


def _wall(a, st, rng, top, bottom, x0, x1):
    base, dark, light = st["wall"]
    for y in range(top, bottom + 1):
        for x in range(x0, x1 + 1):
            r = rng.random()
            put(a, x, y, dark if r < 0.06 else light if r < 0.1 else base)
    if st is HOUSE_STYLES["tundra"]:            # stacked logs
        for y in range(top + 3, bottom, 4):
            hline(a, x0, x1, y, dark)
            for x in range(x0, x1 + 1, 9):
                put(a, x + (y % 3), y - 1, st["trim"])
    elif st is HOUSE_STYLES["meadow"]:          # timber frame
        hline(a, x0, x1, top, st["trim"]); hline(a, x0, x1, top + 1, shade(st["trim"], 0.8))
        for x in (x0, x0 + 24, x1 - 24, x1):
            vline(a, x, top, bottom, st["trim"])
    elif st is HOUSE_STYLES["desert"]:
        for y in range(top + 4, bottom, 6):     # mud-brick courses
            for x in range(x0, x1 + 1):
                if (x + (y // 6) * 4) % 9 == 0:
                    put(a, x, y, dark)
    else:                                       # dressed stone blocks
        for y in range(top, bottom + 1):
            for x in range(x0, x1 + 1):
                off = 5 if ((y - top) // 5) % 2 else 0
                if (y - top) % 5 == 4 or (x + off) % 10 == 9:
                    put(a, x, y, dark)
    rect(a, x0, bottom - 2, x1 - x0 + 1, 3, st["base"])
    hline(a, x0, x1, bottom - 3, shade(st["base"], 1.15))


def _window(a, x, y, lit=False):
    frame, glass = (236, 228, 206), ((255, 214, 120) if lit else (120, 170, 214))
    rect(a, x - 1, y - 1, 12, 11, EDGE)
    rect(a, x, y, 10, 9, frame)
    rect(a, x + 1, y + 1, 8, 7, glass)
    rect(a, x + 1, y + 1, 3, 2, mix(glass, (255, 255, 255), 0.5))
    vline(a, x + 5, y + 1, y + 7, frame); hline(a, x + 1, x + 8, y + 4, frame)


def _door(a, x, y, h, wood=(126, 80, 46)):
    rect(a, x - 1, y - 1, 16, h + 1, EDGE)
    rect(a, x, y, 14, h, wood)
    for xx in range(x + 3, x + 14, 4):
        vline(a, xx, y + 1, y + h - 1, shade(wood, 0.78))
    hline(a, x, x + 13, y, mix(wood, (255, 255, 255), 0.25))
    put(a, x + 10, y + h // 2, (230, 200, 90)); put(a, x + 10, y + h // 2 + 1, (160, 120, 50))
    rect(a, x - 2, y + h, 18, 2, (150, 140, 128))           # door step


def house(biome, variant):
    """80x64: walls along the bottom 26px, a roof above, the door in the middle tile."""
    st = HOUSE_STYLES[biome]
    roof = st["roofs"][variant % len(st["roofs"])]
    rng = np.random.default_rng(700 + variant * 31 + len(biome))
    a = blank(80, 64)
    wall_top, wall_bot = 38, 63
    _wall(a, st, rng, wall_top, wall_bot, 5, 74)
    lit = biome == "volcanic"
    _window(a, 12, 44, lit); _window(a, 58, 44, lit)
    _door(a, 33, 44, 18)
    rd, rm, rl = shade(roof, 0.66), roof, mix(roof, (255, 255, 255), 0.25)
    if st["kind"] == "flat":
        rect(a, 3, 20, 74, 19, shade(st["wall"][0], 0.9))           # parapet front
        rect(a, 3, 14, 74, 7, st["wall"][2])                        # roof top
        for x in range(3, 77, 6):
            rect(a, x, 12, 3, 3, st["wall"][1])                     # crenels
        for y in range(23, 38, 5):
            hline(a, 4, 75, y, st["wall"][1])
        # striped awning over the door
        for i, x in enumerate(range(26, 54, 4)):
            rect(a, x, 36, 4, 6, rm if i % 2 else (240, 232, 214))
        hline(a, 26, 53, 41, shade(rm, 0.7))
        rect(a, 62, 6, 8, 8, st["wall"][1]); rect(a, 63, 7, 6, 3, shade(st["wall"][1], 0.7))   # vent
    else:
        # a gable roof seen from the front: shingle rows widening toward the eaves
        top, eave = 6, 40
        for y in range(top, eave + 1):
            k = (y - top) / (eave - top)
            half = int(16 + k * 24)
            x0, x1 = 40 - half, 39 + half
            row = (y - top) // 4
            for x in range(x0, x1 + 1):
                if (y - top) % 4 == 3:
                    c = rd
                elif (x + row * 3) % 7 == 0:
                    c = shade(rm, 0.82)
                else:
                    c = rl if y < top + 3 else rm
                put(a, x, y, c)
        hline(a, 0, 79, eave, rd); hline(a, 1, 78, eave - 1, shade(rm, 0.9))
        hline(a, 24, 55, top, rl)
        # gable window under the ridge
        rect(a, 35, 18, 10, 10, EDGE); rect(a, 36, 19, 8, 8, (236, 228, 206))
        rect(a, 37, 20, 6, 6, (255, 214, 120) if lit else (110, 160, 206))
        vline(a, 39, 20, 25, (236, 228, 206))
        # chimney
        rect(a, 58, 0, 9, 16, (120, 70, 56)); rect(a, 57, 0, 11, 3, (90, 54, 44))
        for y in range(4, 16, 4):
            hline(a, 58, 66, y, (96, 56, 46))
        if st["kind"] == "snowy":                                   # snow along the ridge and eaves
            for y in range(top, top + 4):
                k = (y - top) / (eave - top)
                half = int(16 + k * 24)
                for x in range(40 - half, 40 + half):
                    if y < top + 3 or rng.random() < 0.5:
                        put(a, x, y, (244, 248, 255) if y < top + 2 else (214, 226, 242))
            for x in range(1, 79):
                if rng.random() < 0.7:
                    put(a, x, eave, (244, 248, 255))
                if rng.random() < 0.25:
                    put(a, x, eave + 1, (214, 226, 242))
            rect(a, 57, 0, 11, 2, (244, 248, 255))
    if biome == "meadow":                                            # flower boxes under the windows
        for wx in (12, 58):
            rect(a, wx - 1, 54, 12, 3, (120, 80, 48))
            for i in range(wx, wx + 10, 2):
                put(a, i, 53, ((230, 70, 70), (250, 210, 60), (248, 248, 248))[(i // 2) % 3])
                put(a, i + 1, 53, (66, 140, 60))
    outline(a, EDGE)
    return a


# ---------------------------------------------------------------------------- village props

def cobble(i):
    base, dark, light = (156, 150, 140), (116, 110, 104), (186, 180, 170)
    rng = np.random.default_rng(4100 + i)
    a = blank(); a[..., 3] = 255; a[..., :3] = dark
    # rounded setts in staggered rows
    for row, y0 in enumerate((0, 5, 10, 15)):
        off = int(rng.integers(0, 4)) + (2 if row % 2 else 0)
        x = -off
        while x < T:
            w = int(rng.integers(4, 7))
            col = mix(base, light if rng.random() < 0.4 else dark, rng.random() * 0.35)
            for yy in range(y0, min(T, y0 + 4)):
                for xx in range(max(0, x), min(T, x + w - 1)):
                    edge = yy == y0 + 3 or xx == x + w - 2
                    put(a, xx, yy, shade(col, 0.86) if edge else col)
            put(a, max(0, x), y0, light)
            x += w
    return a


def well():
    a = blank(16, 26)
    stone = [(96, 96, 104), (128, 128, 136), (160, 160, 168), (190, 190, 196)]
    ring = blob(16, 26, [(8, 19, 7.5, 5.5)], stone, np.random.default_rng(5))
    a[ring[..., 3] > 0] = ring[ring[..., 3] > 0]
    for x in range(4, 13):                                   # dark water in the shaft
        for y in range(16, 20):
            if (x - 8) ** 2 / 16 + (y - 18) ** 2 / 4 < 1:
                put(a, x, y, (30, 50, 74) if y > 17 else (60, 96, 130))
    vline(a, 2, 6, 19, (110, 72, 42)); vline(a, 13, 6, 19, (110, 72, 42))
    vline(a, 3, 6, 19, (82, 52, 30)); vline(a, 14, 6, 19, (82, 52, 30))
    hline(a, 3, 13, 9, (90, 60, 36))                          # winch
    vline(a, 8, 10, 15, (180, 160, 120)); rect(a, 7, 14, 3, 3, (120, 80, 46))
    for y in range(0, 7):                                     # little roof
        half = 2 + y
        hline(a, 8 - half, 7 + half, y, (170, 60, 50) if y % 2 else (196, 80, 64))
    outline(a, EDGE)
    return a


def lamppost():
    a = blank(16, 32)
    vline(a, 7, 9, 31, (56, 56, 66)); vline(a, 8, 9, 31, (84, 84, 96))
    rect(a, 5, 29, 6, 3, (56, 56, 66))
    rect(a, 4, 2, 8, 8, (48, 48, 58))
    rect(a, 5, 3, 6, 6, (255, 220, 130)); rect(a, 6, 4, 2, 2, (255, 250, 220))
    hline(a, 3, 12, 1, (48, 48, 58)); hline(a, 5, 10, 0, (48, 48, 58))
    outline(a, EDGE)
    return a


def fence(vertical=False):
    a = blank()
    wood, dark = (176, 132, 84), (120, 86, 52)
    if vertical:
        vline(a, 6, 0, 15, wood); vline(a, 9, 0, 15, wood)
        vline(a, 7, 0, 15, dark); vline(a, 8, 0, 15, dark)
        for y in (3, 11):
            rect(a, 5, y, 6, 2, wood)
    else:
        for x in (2, 13):
            rect(a, x, 3, 2, 12, wood); vline(a, x + 1, 4, 14, dark)
        for y in (6, 10):
            hline(a, 0, 15, y, wood); hline(a, 0, 15, y + 1, dark)
    outline(a, EDGE)
    return a


def sign():
    a = blank()
    vline(a, 7, 8, 15, (110, 72, 42)); vline(a, 8, 8, 15, (82, 52, 30))
    rect(a, 2, 2, 12, 8, (176, 132, 84)); hline(a, 2, 13, 2, (206, 166, 112))
    for y in (4, 6):
        hline(a, 4, 11, y, (110, 80, 50))
    outline(a, EDGE)
    return a


def barrel():
    pal = [(96, 60, 34), (132, 86, 50), (166, 114, 68), (196, 146, 92)]
    a = blob(16, 16, [(8, 9, 5.5, 6.5)], pal, np.random.default_rng(9))
    for y in (5, 12):
        for x in range(2, 14):
            if a[y, x, 3]:
                put(a, x, y, (70, 70, 80))
    outline(a, EDGE)
    return a


def crate():
    a = blank()
    rect(a, 2, 4, 12, 11, (170, 124, 72))
    rect(a, 2, 4, 12, 2, (200, 156, 100))
    for i in range(10):
        put(a, 3 + i, 5 + i if 5 + i < 15 else 14, (120, 84, 46))
    vline(a, 2, 4, 14, (120, 84, 46)); vline(a, 13, 4, 14, (120, 84, 46)); hline(a, 2, 13, 14, (120, 84, 46))
    outline(a, EDGE)
    return a


def shrine():
    """A village save shrine: a blue crystal floating over a carved stone plinth."""
    a = blank(16, 28)
    stone = [(88, 92, 104), (120, 124, 138), (156, 160, 174), (190, 194, 206)]
    base = blob(16, 28, [(8, 24, 6.5, 3.5)], stone, np.random.default_rng(21))
    a[base[..., 3] > 0] = base[base[..., 3] > 0]
    rect(a, 4, 17, 8, 6, stone[1]); rect(a, 4, 17, 8, 1, stone[3]); vline(a, 11, 17, 22, stone[0])
    for x in (5, 8, 10):                                      # carved runes
        put(a, x, 19, (110, 200, 255)); put(a, x, 20, (60, 130, 200))
    crystal = [(40, 90, 170), (70, 140, 230), (130, 200, 255), (220, 246, 255)]
    for y in range(2, 15):                                    # a long diamond
        half = int(4.5 * (1 - abs(y - 8) / 7.0)) + (1 if 6 <= y <= 10 else 0)
        for x in range(8 - half, 8 + half):
            k = 3 if x < 8 - half + 2 and y < 9 else 2 if x < 8 else 1 if y > 9 else 2
            put(a, x, y, crystal[k])
    vline(a, 8, 3, 13, crystal[3]); put(a, 6, 5, (255, 255, 255))
    outline(a, EDGE)
    return a


def flowerbed(seed):
    rng = np.random.default_rng(600 + seed)
    a = blank()
    rect(a, 1, 9, 14, 6, (104, 70, 44)); hline(a, 1, 14, 9, (130, 92, 58))
    cols = [(230, 70, 70), (250, 210, 60), (248, 248, 248), (200, 110, 220)]
    for x in range(2, 14, 2):
        h = int(rng.integers(3, 6))
        vline(a, x, 9 - h + 2, 9, (66, 140, 60))
        c = cols[int(rng.integers(0, len(cols)))]
        put(a, x, 9 - h + 1, c); put(a, x + 1, 9 - h + 2, c); put(a, x - 1, 9 - h + 2, c)
    return a


# ---------------------------------------------------------------------------- house interiors

HOUSE_THEME = {"floor": ((176, 126, 78), (140, 96, 56), (204, 154, 100), (120, 84, 48)),
               "face": ((150, 112, 74), (214, 196, 160), (236, 222, 190)), "top": (64, 44, 32),
               "trim": (120, 84, 50)}


def plank_floor(i):
    base, dark, light, seam = HOUSE_THEME["floor"]
    rng = np.random.default_rng(5100 + i)
    a = textured(base, dark, light, 5200 + i, p_dark=0.04, p_light=0.04)
    for y in (3, 7, 11, 15):
        hline(a, 0, 15, y, seam)
    for row, y in enumerate((0, 4, 8, 12)):
        x = int(rng.integers(0, 16))
        vline(a, x, y, y + 2, seam)
        if rng.random() < 0.5:
            put(a, (x + 6) % 16, y + 1, shade(base, 0.85))
    return a


def wall_face(i):
    """Wallpaper above wood panelling, with a light rail between them."""
    wood, paper, paper_l = HOUSE_THEME["face"]
    a = blank(); a[..., 3] = 255
    for y in range(T):
        for x in range(T):
            if y >= 10:
                c = wood if x % 8 else shade(wood, 0.75)
                if y == 10:
                    c = mix(wood, (255, 255, 255), 0.3)
            else:
                c = paper_l if (x + i) % 6 < 3 else paper
                if (x + i) % 6 == 0 and y % 4 == 1:
                    c = (178, 120, 110)                    # little floral print
            put(a, x, y, c)
    hline(a, 0, 15, 0, HOUSE_THEME["trim"])
    hline(a, 0, 15, 15, shade(wood, 0.6))
    return a


def wall_top(i):
    top = HOUSE_THEME["top"]
    a = textured(top, shade(top, 0.75), shade(top, 1.25), 5300 + i, p_dark=0.1, p_light=0.05)
    for x in range(0, 16, 8):
        vline(a, (x + i * 3) % 16, 0, 15, shade(top, 0.7))
    return a


def window_decor():
    a = blank()
    rect(a, 3, 1, 10, 9, (236, 228, 206))
    rect(a, 4, 2, 8, 7, (150, 200, 236))
    rect(a, 4, 2, 3, 2, (220, 240, 255))
    vline(a, 8, 2, 8, (236, 228, 206)); hline(a, 4, 11, 5, (236, 228, 206))
    rect(a, 2, 0, 3, 11, (180, 70, 70)); rect(a, 11, 0, 3, 11, (180, 70, 70))     # curtains
    hline(a, 1, 14, 10, (150, 112, 74))
    return a


def bed():
    a = blank(16, 32)
    rect(a, 1, 2, 14, 29, (120, 80, 46))                     # frame
    rect(a, 1, 0, 14, 5, (140, 94, 56)); hline(a, 1, 14, 0, (170, 120, 76))
    rect(a, 2, 5, 12, 25, (236, 236, 244))                   # sheet
    rect(a, 3, 6, 10, 6, (255, 255, 255)); hline(a, 3, 12, 11, (210, 210, 224))   # pillow
    rect(a, 2, 14, 12, 16, (70, 110, 180))                   # blanket
    hline(a, 2, 13, 14, (110, 150, 214))
    for y in range(17, 30, 4):
        hline(a, 2, 13, y, (60, 94, 160))
    outline(a, EDGE)
    return a


def bookshelf():
    a = blank(16, 28)
    rect(a, 1, 0, 14, 28, (110, 72, 42))
    rect(a, 2, 1, 12, 26, (76, 48, 28))
    rng = np.random.default_rng(77)
    cols = [(180, 60, 60), (60, 110, 170), (80, 150, 80), (200, 170, 70), (140, 80, 160), (220, 220, 210)]
    for shelf_y in (2, 10, 18):
        x = 2
        while x < 14:
            w = int(rng.integers(1, 3))
            h = int(rng.integers(5, 8))
            rect(a, x, shelf_y + 7 - h, w, h, cols[int(rng.integers(0, len(cols)))])
            x += w
        hline(a, 2, 13, shelf_y + 7, (130, 88, 52))
    outline(a, EDGE)
    return a


def cupboard():
    a = blank(16, 24)
    rect(a, 1, 0, 14, 24, (150, 100, 60))
    hline(a, 1, 14, 0, (186, 134, 86)); hline(a, 1, 14, 10, (110, 72, 42))
    for x0 in (2, 8):
        rect(a, x0, 11, 6, 12, (130, 86, 50))
    put(a, 7, 16, (230, 200, 90)); put(a, 8, 16, (230, 200, 90))
    for x in range(3, 13, 3):                                 # plates on the top shelf
        rect(a, x, 3, 2, 6, (230, 230, 236))
    outline(a, EDGE)
    return a


def fireplace():
    a = blank(16, 28)
    rect(a, 0, 4, 16, 24, (128, 116, 110))
    for y in range(4, 28, 4):
        for x in range(0, 16):
            if (x + (y // 4) * 3) % 8 == 0 or y % 4 == 3 and x % 2:
                put(a, x, y, (96, 86, 82))
    rect(a, 0, 2, 16, 3, (110, 72, 42))                       # mantel
    rect(a, 3, 12, 10, 16, (30, 20, 18))                       # hearth
    for x, h in ((5, 7), (7, 10), (9, 8), (11, 5)):          # flames
        vline(a, x, 27 - h, 26, (240, 120, 40))
        vline(a, x, 27 - h // 2, 26, (255, 220, 90))
    hline(a, 4, 12, 27, (90, 60, 40))
    outline(a, EDGE)
    return a


def table():
    a = blank()
    rect(a, 1, 3, 14, 7, (160, 108, 62)); hline(a, 1, 14, 3, (196, 142, 88))
    vline(a, 2, 10, 15, (110, 72, 42)); vline(a, 13, 10, 15, (110, 72, 42))
    rect(a, 5, 1, 3, 3, (230, 230, 236)); put(a, 10, 2, (200, 60, 60)); put(a, 11, 2, (200, 60, 60))
    outline(a, EDGE)
    return a


def stool():
    a = blank()
    rect(a, 4, 7, 8, 3, (176, 124, 72)); hline(a, 4, 11, 7, (206, 156, 100))
    vline(a, 5, 10, 14, (110, 72, 42)); vline(a, 10, 10, 14, (110, 72, 42))
    outline(a, EDGE)
    return a


def plant():
    a = blank(16, 22)
    pot = [(140, 70, 40), (176, 96, 56), (206, 124, 76), (226, 150, 100)]
    p = blob(16, 22, [(8, 18, 4.5, 3.8)], pot, np.random.default_rng(3))
    leaves = blob(16, 22, [(8, 9, 5, 5), (4.5, 12, 3, 3), (11.5, 11, 3.2, 3.4), (8, 4.5, 3, 3)],
                  [(40, 100, 50), (60, 140, 64), (90, 176, 80), (130, 206, 110)], np.random.default_rng(4))
    a[leaves[..., 3] > 0] = leaves[leaves[..., 3] > 0]
    a[p[..., 3] > 0] = p[p[..., 3] > 0]
    outline(a, EDGE)
    return a


def jar():
    pal = [(70, 90, 120), (100, 124, 160), (140, 164, 196), (190, 206, 226)]
    a = blob(16, 16, [(8, 10, 4.5, 5)], pal, np.random.default_rng(12))
    rect(a, 6, 3, 4, 3, pal[1]); hline(a, 6, 9, 3, pal[3])
    outline(a, EDGE)
    return a


def rug(i):
    """Seamless woven rug; i picks edge pieces so a 3x2 patch gets a border."""
    a = blank(); a[..., 3] = 255
    red, dark, gold = (160, 50, 50), (110, 30, 36), (220, 180, 90)
    for y in range(T):
        for x in range(T):
            c = red
            if (x + y) % 8 == 0 or (x - y) % 8 == 0:
                c = dark
            if (x + y) % 16 == 8 and (x - y) % 16 == 0:
                c = gold
            put(a, x, y, c)
    top, bottom, left, right = i & 1, i & 2, i & 4, i & 8
    if top:
        hline(a, 0, 15, 0, gold); hline(a, 0, 15, 1, dark)
    if bottom:
        hline(a, 0, 15, 15, gold); hline(a, 0, 15, 14, dark)
    if left:
        vline(a, 0, 0, 15, gold); vline(a, 1, 0, 15, dark)
    if right:
        vline(a, 15, 0, 15, gold); vline(a, 14, 0, 15, dark)
    return a


def doormat():
    a = blank()
    rect(a, 2, 5, 12, 8, (150, 110, 70))
    for y in range(6, 12, 2):
        hline(a, 3, 12, y, (120, 84, 50))
    hline(a, 2, 13, 5, (176, 134, 90))
    return a


def bubble_q():
    """The "?" balloon over a villager waiting to hear the quest is done."""
    rows = ["  #######  ",
            " #.......# ",
            "#...???...#",
            "#..?...?..#",
            "#......?..#",
            "#.....?...#",
            "#....?....#",
            "#.........#",
            " #...?...# ",
            "  ###.###  ",
            "     ##    ",
            "     #     "]
    a = blank(len(rows[0]), len(rows))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                put(a, x, y, EDGE)
            elif ch == ".":
                put(a, x, y, (255, 248, 214))
            elif ch == "?":
                put(a, x, y, (60, 150, 230))
    return a


def bubble_dots():
    """"…" — a quest under way."""
    rows = ["  #######  ",
            " #.......# ",
            "#.........#",
            "#.........#",
            "#.#..#..#.#",
            "#.........#",
            "#.........#",
            " #.......# ",
            "  ###.###  ",
            "     ##    ",
            "     #     "]
    a = blank(len(rows[0]), len(rows))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                put(a, x, y, EDGE if y != 4 or x in (0, 10) else (110, 110, 120))
            elif ch == ".":
                put(a, x, y, (236, 236, 240))
    return a


# ---------------------------------------------------------------------------- registry

def village_tiles():
    """{name: array or [arrays]} for build_tileset."""
    t = {}
    for b in HOUSE_STYLES:
        t["house_" + b] = [house(b, v) for v in range(3)]
    t["cobble"] = [cobble(i) for i in range(4)]
    t["well"] = well()
    t["lamppost"] = lamppost()
    t["fence"] = fence()
    t["fence_v"] = fence(True)
    t["sign"] = sign()
    t["barrel"] = barrel()
    t["crate"] = crate()
    t["shrine"] = shrine()
    t["flowerbed"] = [flowerbed(i) for i in range(3)]
    t["cfloor_house"] = [plank_floor(i) for i in range(4)]
    t["cface_house"] = [wall_face(i) for i in range(3)]
    t["ctop_house"] = [wall_top(i) for i in range(3)]
    t["window"] = window_decor()
    t["bed"] = bed()
    t["bookshelf"] = bookshelf()
    t["cupboard"] = cupboard()
    t["fireplace"] = fireplace()
    t["table"] = table()
    t["stool"] = stool()
    t["plant"] = plant()
    t["jar"] = jar()
    for i in range(16):
        t[f"rug_{i}"] = rug(i)
    t["doormat"] = doormat()
    t["bubble_q"] = bubble_q()
    t["bubble_dots"] = bubble_dots()
    return t


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    tiles = village_tiles()
    items = []
    for name, v in tiles.items():
        for i, arr in enumerate(v if isinstance(v, list) else [v]):
            items.append(to_surface(arr))
    cell = 90
    cols = 12
    sheet = pygame.Surface((cols * cell, ((len(items) + cols - 1) // cols) * cell))
    sheet.fill((70, 120, 70))
    for i, s in enumerate(items):
        big = pygame.transform.scale(s, (s.get_width() * (1 if s.get_width() > 40 else 2),
                                         s.get_height() * (1 if s.get_width() > 40 else 2)))
        sheet.blit(big, ((i % cols) * cell + 2, (i // cols) * cell + 2))
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "_sheet_village.png")
    pygame.image.save(sheet, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
