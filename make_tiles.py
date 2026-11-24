"""
Pixel-art tileset for the overworld and caves (16x16 base tiles, drawn at 3x in game).

Everything is generated from code — textures from seeded noise, rounded shapes from
shaded blobs, the player from hand-drawn pixel maps — so there are no external art files
to keep in sync. The game calls build_tileset() at startup. To replace a tile with your own
art, drop a PNG with the same name into tiles/custom/ (e.g. tiles/custom/grass_0.png or
tiles/custom/tree.png) and the game uses it instead.

Run directly to write every tile to tiles/ plus a review sheet:
    python make_tiles.py
"""
import math
import os

import numpy as np
import pygame

T = 16
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tiles")

RARITY_GEMS = {"Common": (220, 220, 220), "Uncommon": (60, 220, 90), "Rare": (70, 130, 255),
               "Epic": (176, 80, 230), "Legendary": (255, 200, 40), "Mythical": (255, 70, 200)}


# ---------------------------------------------------------------------------- helpers

def to_surface(arr):
    """(h, w, 4) uint8 array -> pygame Surface with alpha."""
    arr = np.ascontiguousarray(arr.astype(np.uint8))
    h, w = arr.shape[:2]
    return pygame.image.frombuffer(arr.tobytes(), (w, h), "RGBA").copy()


def blank(w=T, h=T):
    return np.zeros((h, w, 4), np.uint8)


def put(a, x, y, col, alpha=255):
    h, w = a.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        a[y, x, :3] = col
        a[y, x, 3] = alpha


def mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def textured(base, dark, light, seed, p_dark=0.055, p_light=0.045, extra=None):
    """A ground tile: base colour speckled with darker and lighter pixels."""
    rng = np.random.default_rng(seed)
    a = blank()
    a[..., :3] = base
    a[..., 3] = 255
    r = rng.random((T, T))
    a[r < p_dark, :3] = dark
    a[(r >= p_dark) & (r < p_dark + p_light), :3] = light
    if extra:
        extra(a, rng)
    return a


def outline(a, col):
    """Draw a 1px outline around the opaque shape (outside it)."""
    alpha = a[..., 3] > 0
    p = np.pad(alpha, 1)
    near = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    ring = near & ~alpha
    a[ring, :3] = col
    a[ring, 3] = 255
    return a


def blob(w, h, ellipses, palette, rng=None, light=(-0.55, -0.75, 0.5), noise=0.08):
    """Shaded pixel blob: union of ellipses (cx, cy, rx, ry), lit from the top-left and
    quantised to the palette (dark -> light)."""
    a = blank(w, h)
    L = np.array(light, float); L /= np.linalg.norm(L)
    rng = rng or np.random.default_rng(1)
    yy, xx = np.mgrid[0:h, 0:w] + 0.5
    best_d = np.full((h, w), 9.0); nx = np.zeros((h, w)); ny = np.zeros((h, w))
    for cx, cy, rx, ry in ellipses:
        dx = (xx - cx) / rx; dy = (yy - cy) / ry
        d = dx * dx + dy * dy
        better = d < best_d
        best_d = np.where(better, d, best_d)
        nx = np.where(better, dx, nx); ny = np.where(better, dy, ny)
    inside = best_d <= 1.0
    nz = np.sqrt(np.clip(1 - best_d, 0, 1))
    lum = (nx * L[0] + ny * L[1] + nz * L[2])
    lum = (lum + 1) / 2 + rng.normal(0, noise, (h, w))
    idx = np.clip((lum * len(palette)).astype(int), 0, len(palette) - 1)
    pal = np.array(palette, np.uint8)
    a[inside, :3] = pal[idx[inside]]
    a[inside, 3] = 255
    return a


def from_map(rows, colors):
    """Pixel map: list of equal-length strings, '.' = transparent."""
    h, w = len(rows), len(rows[0])
    a = blank(w, h)
    for y, row in enumerate(rows):
        assert len(row) == w, (y, len(row), row)
        for x, ch in enumerate(row):
            if ch != ".":
                put(a, x, y, colors[ch])
    return a


# ---------------------------------------------------------------------------- ground

GROUNDS = {
    # name: (base, dark, light, detail)
    "grass":         ((86, 164, 74), (62, 134, 62), (124, 194, 92), "blades"),
    "snow":          ((236, 242, 250), (206, 218, 238), (255, 255, 255), "sparkle"),
    "sand":          ((230, 204, 140), (208, 178, 114), (244, 224, 170), "ripples"),
    "ash":           ((96, 88, 86), (70, 64, 64), (120, 110, 106), "cracks"),
    "slate":         ((76, 82, 104), (58, 62, 82), (100, 106, 130), "cracks"),
    "path_meadow":   ((186, 148, 98), (158, 120, 78), (206, 172, 122), "pebbles"),
    "path_tundra":   ((204, 212, 224), (174, 186, 204), (226, 232, 242), "pebbles"),
    "path_desert":   ((206, 168, 106), (178, 140, 84), (224, 192, 132), "pebbles"),
    "path_volcanic": ((76, 58, 54), (56, 42, 40), (100, 76, 68), "pebbles"),
    "path_storm":    ((122, 124, 142), (98, 100, 118), (148, 150, 168), "pebbles"),
    "ice":           ((180, 222, 242), (146, 194, 224), (226, 244, 252), "streaks"),
    "bridge":        ((150, 106, 62), (112, 76, 42), (178, 132, 82), "planks"),
}
CAVE_THEMES = {
    # floor (base, dark, light, accent), wall face (dark, mid, light), wall top, extra
    "meadow":   {"floor": ((88, 84, 74), (66, 62, 56), (110, 104, 92), (78, 118, 62)),
                 "face": ((60, 54, 48), (86, 78, 68), (114, 104, 90)), "top": (30, 28, 26), "trim": (82, 130, 66)},
    "tundra":   {"floor": ((150, 186, 210), (122, 158, 188), (186, 214, 234), (226, 244, 255)),
                 "face": ((84, 124, 168), (116, 160, 200), (164, 204, 232)), "top": (34, 52, 78), "trim": (220, 240, 255)},
    "desert":   {"floor": ((192, 158, 106), (154, 120, 80), (212, 180, 128), (150, 116, 76)),
                 "face": ((136, 100, 62), (172, 132, 86), (204, 164, 110)), "top": (62, 46, 30), "trim": (226, 190, 130)},
    "volcanic": {"floor": ((60, 50, 50), (42, 34, 34), (82, 68, 64), (170, 60, 30)),
                 "face": ((44, 32, 30), (68, 50, 46), (94, 70, 62)), "top": (20, 14, 14), "trim": (220, 90, 40)},
    "storm":    {"floor": ((64, 60, 88), (48, 44, 68), (86, 80, 114), (176, 140, 236)),
                 "face": ((54, 48, 82), (78, 70, 114), (106, 96, 146)), "top": (22, 18, 36), "trim": (190, 150, 255)},
    # dungeons: dressed grey stone — flagstone floors, brick walls
    "dungeon":  {"floor": ((104, 104, 112), (78, 78, 88), (128, 128, 136), (88, 88, 96)),
                 "face": ((70, 70, 82), (98, 98, 110), (130, 130, 142)), "top": (24, 22, 30), "trim": (150, 150, 162)},
}


def _detail(kind, dark, light):
    def blades(a, rng):
        for _ in range(5):
            x, y = int(rng.integers(0, 16)), int(rng.integers(2, 16))
            put(a, x, y, dark); put(a, x, y - 1, light)
            if rng.random() < 0.5:
                put(a, x + 1, y, dark)

    def sparkle(a, rng):
        for _ in range(3):
            put(a, int(rng.integers(0, 16)), int(rng.integers(0, 16)), (255, 255, 255))
        for _ in range(4):
            x, y = int(rng.integers(0, 15)), int(rng.integers(0, 16))
            put(a, x, y, dark); put(a, x + 1, y, dark)

    def ripples(a, rng):
        for _ in range(3):
            x0, y0 = int(rng.integers(-4, 14)), int(rng.integers(0, 16))
            for i in range(5):
                put(a, x0 + i, y0 - i // 2, dark)

    def cracks(a, rng):
        x, y = int(rng.integers(2, 14)), int(rng.integers(2, 14))
        for _ in range(int(rng.integers(3, 7))):
            put(a, x, y, shade(dark, 0.75))
            x += int(rng.integers(-1, 2)); y += int(rng.integers(0, 2))

    def pebbles(a, rng):
        for _ in range(4):
            x, y = int(rng.integers(0, 15)), int(rng.integers(0, 15))
            put(a, x, y, light); put(a, x, y + 1, dark)

    def planks(a, rng):
        for y in (3, 7, 11, 15):                  # board seams
            for x in range(16):
                put(a, x, y, dark)
        for y in range(16):                       # rope rails along the sides
            put(a, 0, y, (90, 70, 46)); put(a, 15, y, (90, 70, 46))
        for _ in range(3):
            put(a, int(rng.integers(2, 14)), int(rng.integers(0, 16)), light)

    def streaks(a, rng):
        for _ in range(2):
            x0, y0 = int(rng.integers(0, 16)), int(rng.integers(0, 16))
            for i in range(4):
                put(a, x0 + i, y0 + i, (255, 255, 255))
    return {"blades": blades, "sparkle": sparkle, "ripples": ripples, "cracks": cracks,
            "pebbles": pebbles, "streaks": streaks, "planks": planks}[kind]


def ground_tiles(name, n=4):
    base, dark, light, kind = GROUNDS[name]
    return [textured(base, dark, light, hash((name, i)) & 0xFFFFFF, extra=_detail(kind, dark, light))
            for i in range(n)]


def liquid_frames(base, dark, light, hi, seed, n=4, glow=False):
    """Animated water / lava: wave dashes that drift sideways frame to frame."""
    rng = np.random.default_rng(seed)
    marks = [(int(rng.integers(0, 16)), int(rng.integers(0, 16)), int(rng.integers(2, 5))) for _ in range(6)]
    frames = []
    for f in range(n):
        a = textured(base, dark, light, seed + f * 7, p_dark=0.10, p_light=0.06)
        for (x, y, ln) in marks:
            yy = (y + (f if glow else 0)) % 16
            for i in range(ln):
                put(a, (x + i + f * 2) % 16, yy, hi)
            put(a, (x + f * 2 - 1) % 16, (yy + 1) % 16, light)
        frames.append(a)
    return frames


def cave_floor(theme, i):
    base, dark, light, accent = CAVE_THEMES[theme]["floor"]
    if theme in ("desert", "dungeon"):       # flagstones
        a = textured(base, dark, light, 900 + i, p_dark=0.06, p_light=0.08)
        for y in range(T):
            for x in range(T):
                off = 4 if (y // 8) % 2 else 0
                if y % 8 == 7 or (x + off) % 8 == 7:
                    put(a, x, y, dark)
        return a

    def det(a, rng):
        for _ in range(3):
            x, y = int(rng.integers(0, 15)), int(rng.integers(0, 15))
            put(a, x, y, light); put(a, x + 1, y + 1, dark)
        if rng.random() < 0.6:
            put(a, int(rng.integers(0, 16)), int(rng.integers(0, 16)), accent)
    return textured(base, dark, light, 1000 + i + hash(theme) % 1000, extra=det)


def cave_face(theme, i):
    """Front face of a cave wall: strata, lit from above, darker toward the floor."""
    th = CAVE_THEMES[theme]
    d, m, l = th["face"]
    rng = np.random.default_rng(2000 + i + hash(theme) % 1000)
    a = blank(); a[..., 3] = 255
    for y in range(T):
        c = mix(l, d, y / 15)
        a[y, :, :3] = c
    if theme in ("desert", "dungeon"):       # cut blocks
        for y in range(T):
            for x in range(T):
                off = 5 if (y // 5) % 2 else 0
                if y % 5 == 4 or (x + off) % 10 == 9:
                    put(a, x, y, shade(d, 0.8))
    else:
        for _ in range(3):                   # strata lines
            y = int(rng.integers(3, 15)); x0 = int(rng.integers(-4, 8))
            for x in range(x0, x0 + int(rng.integers(6, 12))):
                put(a, x, y, shade(d, 0.85)); put(a, x, y - 1, l)
        for _ in range(10):
            put(a, int(rng.integers(0, 16)), int(rng.integers(0, 16)), mix(m, d, rng.random()))
    for x in range(T):                       # bright lip at the top edge
        put(a, x, 0, th["trim"] if theme in ("meadow", "volcanic", "storm") and rng.random() < 0.5 else l)
    if theme == "volcanic":
        x = int(rng.integers(3, 13))
        for y in range(4, 14):
            if rng.random() < 0.7:
                put(a, x, y, (230, 100, 40))
            x += int(rng.integers(-1, 2))
    if theme == "storm":
        for _ in range(2):
            x, y = int(rng.integers(2, 14)), int(rng.integers(3, 13))
            put(a, x, y, th["trim"]); put(a, x, y + 1, shade(th["trim"], 0.7))
    return a


def cave_top(theme, i):
    top = CAVE_THEMES[theme]["top"]
    return textured(top, shade(top, 0.75), shade(top, 1.3), 3000 + i + hash(theme) % 999,
                    p_dark=0.2, p_light=0.08)


# ---------------------------------------------------------------------------- decor

def tallgrass(dark, mid, light, seed):
    """Two rows of grass tufts per tile, tiling seamlessly into a field (the lower row is
    what's drawn over a walker's legs)."""
    rng = np.random.default_rng(seed)
    a = blank()
    heights = [3, 5, 4, 6, 4, 5, 3]
    for cx, base in ((4, 7), (12, 7), (0, 15), (8, 15), (16, 15)):
        jitter = int(rng.integers(0, 2))
        for i, hgt in enumerate(heights):
            x = cx - 3 + i
            hgt += jitter if i == 3 else 0
            for k in range(hgt):
                y = base - k
                c = light if k >= hgt - 1 else (mid if k >= 1 else dark)
                put(a, x % 16, y, c)
        for i in range(7):                    # dark root line
            put(a, (cx - 3 + i) % 16, base, dark)
    outline(a, shade(dark, 0.6))
    return a


def alert_bubble(mark=(214, 40, 40), fill=(255, 255, 255), edge=(30, 22, 32)):
    """The "!" balloon that pops over the player's head when something stirs in the grass."""
    rows = ["  #######  ",
            " #.......# ",
            "#....!....#",
            "#....!....#",
            "#....!....#",
            "#....!....#",
            "#.........#",
            "#....!....#",
            " #.......# ",
            "  ###.###  ",
            "     ##    ",
            "     #     "]
    a = blank(len(rows[0]), len(rows))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                put(a, x, y, edge)
            elif ch == ".":
                put(a, x, y, fill)
            elif ch == "!":
                put(a, x, y, mark)
    for x in range(2, 9):                     # a little shading along the bottom of the balloon
        if a[8, x, :3].tolist() == list(fill):
            put(a, x, 8, shade(fill, 0.84))
    return a


def flowers(petal, seed):
    rng = np.random.default_rng(seed)
    a = blank()
    for _ in range(3):
        x, y = int(rng.integers(2, 13)), int(rng.integers(3, 13))
        put(a, x, y + 2, (50, 120, 50))
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put(a, x + dx, y + dy, petal)
        put(a, x, y, (250, 230, 90))
    return a


def scatter(cols, n, seed, size=1):
    rng = np.random.default_rng(seed)
    a = blank()
    for _ in range(n):
        x, y = int(rng.integers(1, 14)), int(rng.integers(2, 14))
        c = cols[int(rng.integers(0, len(cols)))]
        for dx in range(size):
            put(a, x + dx, y, c)
        if size > 1:
            put(a, x, y + 1, shade(c, 0.7))
    return a


def bones():
    a = blank()
    w, sh = (236, 230, 214), (180, 170, 150)
    for x in range(4, 12):
        put(a, x, 9, w); put(a, x, 10, sh)
    for (x, y) in ((3, 8), (3, 11), (12, 8), (12, 11)):
        put(a, x, y, w)
    for (x, y) in ((9, 4), (10, 4), (9, 5), (10, 5)):
        put(a, x, y, w)
    put(a, 9, 6, sh)
    return a


def embers():
    a = scatter([(250, 120, 40), (255, 190, 70), (200, 60, 30)], 6, 77)
    return a


def mushroom_small(seed):
    a = blank()
    rng = np.random.default_rng(seed)
    for _ in range(2):
        x, y = int(rng.integers(3, 12)), int(rng.integers(6, 13))
        put(a, x, y + 1, (230, 220, 200)); put(a, x, y + 2, (200, 190, 170))
        for dx in (-1, 0, 1):
            put(a, x + dx, y, (200, 60, 60))
        put(a, x, y - 1, (220, 80, 70)); put(a, x - 1, y, (250, 240, 230))
    return a


def exit_glow():
    """Cave exit: a pool of daylight falling through the opening."""
    a = blank()
    for y in range(T):
        for x in range(T):
            d = math.hypot((x - 7.5) / 7.5, (y - 9) / 6.5)
            if d < 1:
                al = int(150 * (1 - d) ** 1.2)
                a[y, x] = (255, 244, 200, al)
    for x in range(4, 12):                    # a couple of rough steps
        put(a, x, 13, (150, 140, 120)); put(a, x, 14, (110, 100, 90))
    for x in range(5, 11):
        put(a, x, 10, (170, 160, 140)); put(a, x, 11, (120, 110, 96))
    return a


# ---------------------------------------------------------------------------- objects

ROCK_PALETTES = {
    "meadow":   [(84, 86, 92), (114, 116, 122), (146, 148, 152), (182, 182, 184)],
    "tundra":   [(92, 100, 118), (124, 134, 152), (160, 170, 188), (204, 214, 228)],
    "desert":   [(142, 98, 58), (180, 134, 84), (208, 166, 112), (232, 200, 146)],
    "volcanic": [(30, 26, 28), (50, 44, 46), (76, 68, 68), (104, 94, 92)],
    "storm":    [(48, 52, 74), (68, 74, 100), (94, 100, 132), (128, 134, 170)],
}


ROCK_SHAPES = [[(8, 10, 7, 5.5), (6, 9, 4.5, 4.5), (10.5, 9.5, 4.5, 4)],
               [(7.5, 10.5, 6.5, 5), (10.5, 8.5, 4, 4.5)],
               [(8, 11, 7.2, 4.5), (5.5, 9.5, 3.5, 3.5), (9, 8.5, 4, 4)]]


def rock(biome, seed=5):
    pal = ROCK_PALETTES[biome]
    rng = np.random.default_rng(seed)
    a = blob(16, 16, ROCK_SHAPES[seed % len(ROCK_SHAPES)], pal, rng)
    a[15, :, 3] = 0
    if biome == "tundra":                    # snow cap
        for y in range(16):
            for x in range(16):
                if a[y, x, 3] and y < 8 and rng.random() < 0.9:
                    put(a, x, y, (240, 246, 255) if y < 7 else (210, 222, 240))
    if biome == "desert":                    # layered sandstone
        for y in (9, 12):
            for x in range(16):
                if a[y, x, 3]:
                    put(a, x, y, pal[0])
    if biome == "volcanic":                  # glowing cracks
        x = 6
        for y in range(7, 14):
            if a[y, x, 3]:
                put(a, x, y, (240, 110, 40))
            x += 1 if y % 2 else 0
    outline(a, shade(pal[0], 0.55))
    return a


def tree(seed=3):
    pal = [(30, 84, 44), (44, 112, 52), (66, 146, 64), (102, 180, 80), (140, 206, 100)]
    if seed % 2:                              # a slightly olive second variety
        pal = [mix(c, (120, 140, 60), 0.18) for c in pal]
    rng = np.random.default_rng(seed)
    a = blank(16, 24)
    trunk = [(84, 56, 34), (112, 76, 44), (140, 98, 58)]
    for y in range(13, 23):
        for x in range(6, 10):
            put(a, x, y, trunk[0] if x == 6 else trunk[2] if x == 9 else trunk[1])
    for x in range(5, 11):
        put(a, x, 22, trunk[0])
    shapes = [[(8, 9, 7.5, 7), (4.5, 11, 4, 4), (11.5, 11, 4, 4), (8, 5, 5, 4.5)],
              [(8, 8.5, 7.5, 7.5), (5, 11.5, 3.5, 3.5), (11, 11, 4.5, 4.5), (9, 5, 4.5, 4)],
              [(8, 9.5, 7.6, 6.6), (4, 10, 3.5, 4), (12, 10.5, 3.6, 4), (7, 5, 4.5, 4.5)]]
    canopy = blob(16, 18, shapes[seed % 3], pal, rng)
    m = canopy[..., 3] > 0
    a[:18][m] = canopy[m]
    outline(a, (18, 52, 30))
    return a


def pine(seed=4):
    a = blank(16, 28)
    dark, mid, light = (24, 74, 58), (40, 104, 74), (66, 136, 92)
    snow, snow2 = (240, 246, 255), (200, 214, 236)
    for x in range(7, 9):
        for y in range(22, 27):
            put(a, x, y, (90, 62, 40))
    tiers = [(2, 9, 4), (7, 15, 6), (12, 22, 7.5)]
    for top, bot, half in tiers:
        for y in range(top, bot + 1):
            w = half * (y - top) / max(1, bot - top) + 0.6
            for x in range(16):
                dx = x + 0.5 - 8
                if abs(dx) <= w:
                    c = light if dx < -w * 0.3 else (mid if dx < w * 0.4 else dark)
                    if y <= top + 1 or (y == bot and abs(dx) > w - 1.5):
                        c = snow if dx < 0 else snow2
                    put(a, x, y, c)
    outline(a, (16, 40, 34))
    return a


def cactus():
    a = blank(16, 22)
    d, m, l = (38, 110, 60), (62, 150, 78), (110, 192, 106)

    def col(x0, x1, y0, y1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                put(a, x, y, l if x == x0 else (d if x == x1 - 1 else m))
    col(6, 10, 2, 21)
    col(2, 5, 7, 13); col(3, 6, 12, 14)
    col(11, 14, 5, 11); col(10, 13, 10, 12)
    for y in (4, 8, 12, 16):
        put(a, 7, y, (230, 230, 190))
    outline(a, (20, 60, 36))
    return a


def deadtree():
    a = blank(16, 24)
    bark, dark = (58, 46, 44), (34, 26, 26)
    for y in range(8, 23):
        put(a, 7, y, bark); put(a, 8, y, dark)
    for (x, y) in ((6, 12), (5, 11), (4, 10), (4, 9), (9, 10), (10, 9), (11, 8), (11, 7), (12, 6),
                   (6, 7), (5, 6), (5, 5), (8, 7), (9, 5), (9, 4), (8, 3)):
        put(a, x, y, bark)
    for (x, y) in ((7, 18), (8, 14), (12, 6)):
        put(a, x, y, (240, 110, 40))
    for x in range(5, 11):
        put(a, x, 23, dark)
    outline(a, (16, 10, 10))
    return a


def crystal(small=False, seed=6):
    w, h = (16, 14) if small else (16, 22)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    dark, mid, light, hi = (96, 60, 170), (140, 96, 220), (186, 150, 250), (240, 226, 255)
    shards = [(8, 2, 3.2, h - 1), (4, 7, 2.2, h - 1), (12, 6, 2.4, h - 1)] if not small else \
             [(8, 3, 2.8, h - 1), (4.5, 7, 2, h - 1), (11.5, 6, 2, h - 1)]
    for cx, top, half, bot in shards:
        pygame.draw.polygon(s, mid, [(cx - half, bot), (cx - half, top + 3), (cx, top), (cx + half, top + 3), (cx + half, bot)])
        pygame.draw.polygon(s, light, [(cx - half, bot), (cx - half, top + 3), (cx, top), (cx, bot)])
        pygame.draw.line(s, hi, (cx - half + 1, top + 4), (cx - half + 1, bot - 2))
        pygame.draw.polygon(s, dark, [(cx + half, top + 3), (cx + half, bot), (cx + 0.5, bot), (cx + 0.5, top + 1)])
    # the surface's pixels as an (h, w, 4) array; via bytes rather than surfarray so it
    # works with any pygame / numpy pair (Android's pygame is 2.1.0)
    _tobytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    out = np.frombuffer(_tobytes(s, "RGBA"), np.uint8).reshape(s.get_height(), s.get_width(), 4).copy()
    outline(out, (40, 20, 80))
    return out


def bush():
    pal = [(30, 84, 44), (48, 118, 54), (72, 152, 66), (110, 186, 86)]
    a = blob(16, 16, [(8, 10, 7, 5.5), (4.5, 11, 4, 4), (11.5, 11, 4, 4)], pal, np.random.default_rng(9))
    a[15, :, 3] = 0
    outline(a, (18, 52, 30))
    return a


def stalagmite(theme):
    d, m, l = CAVE_THEMES[theme]["face"]
    a = blank(16, 20)
    for y in range(3, 20):
        half = 0.8 + 4.5 * (y - 3) / 16
        for x in range(16):
            dx = x + 0.5 - 8
            if abs(dx) <= half:
                put(a, x, y, l if dx < -half * 0.3 else (m if dx < half * 0.4 else d))
    outline(a, shade(d, 0.5))
    return a


def icespike():
    a = blank(16, 20)
    for cx, top, half in ((8, 1, 3.5), (4, 8, 2.2), (12, 6, 2.4)):
        for y in range(top, 20):
            w = half * (y - top) / (19 - top) + 0.4
            for x in range(16):
                dx = x + 0.5 - cx
                if abs(dx) <= w:
                    put(a, x, y, (236, 248, 255) if dx < -w * 0.2 else (170, 214, 240) if dx < w * 0.5 else (120, 170, 214))
    outline(a, (60, 100, 150))
    return a


def mushroom_big():
    a = blank(16, 18)
    for y in range(9, 18):
        for x in range(6, 10):
            put(a, x, y, (236, 226, 206) if x < 8 else (200, 190, 170))
    cap = blob(16, 10, [(8, 7, 7.5, 5)], [(120, 30, 40), (170, 50, 56), (210, 76, 70), (236, 110, 96)])
    m = cap[..., 3] > 0
    a[:10][m] = cap[m]
    for (x, y) in ((5, 4), (10, 3), (8, 6), (3, 7), (12, 7)):
        put(a, x, y, (250, 236, 220))
    outline(a, (60, 20, 24))
    return a


def pillar():
    a = blank(16, 26)
    d, m, l = (136, 100, 62), (176, 136, 88), (214, 176, 120)
    for y in range(4, 24):
        for x in range(4, 12):
            put(a, x, y, l if x < 6 else (m if x < 10 else d))
    for y in (0, 1, 2, 3, 24, 25):
        for x in range(2, 14):
            put(a, x, y, l if y in (0, 24) else d)
    for y in range(6, 22, 4):
        put(a, 7, y, d); put(a, 8, y, d)
    outline(a, (70, 50, 30))
    return a


def urn():
    pal = [(110, 64, 40), (150, 92, 56), (190, 124, 76), (220, 160, 100)]
    a = blob(16, 16, [(8, 10, 5.5, 5)], pal, np.random.default_rng(2))
    for x in range(6, 10):
        put(a, x, 4, pal[1]); put(a, x, 5, pal[0])
    for x in range(4, 12):
        if a[10, x, 3]:
            put(a, x, 10, (230, 200, 120))
    outline(a, (60, 34, 20))
    return a


def vent():
    a = blob(16, 14, [(8, 9, 6.5, 4)], ROCK_PALETTES["volcanic"], np.random.default_rng(4))
    for x in range(6, 11):
        put(a, x, 8, (255, 150, 50)); put(a, x, 9, (220, 80, 30))
    outline(a, (16, 10, 10))
    return a


def outcrop(biome):
    """A 3x2-tile rock outcrop with a cave mouth in the middle of its base (48x40)."""
    w, h = 48, 40
    pal = ROCK_PALETTES[biome]
    cap = {"meadow": [(62, 134, 62), (96, 174, 80)], "tundra": [(210, 222, 240), (246, 250, 255)],
           "desert": [(206, 176, 112), (236, 212, 150)], "volcanic": [(64, 58, 58), (92, 84, 82)],
           "storm": [(52, 84, 84), (76, 116, 108)]}[biome]
    rng = np.random.default_rng(hash(biome) & 0xFFFF)
    a = blank(w, h)
    tops = []
    for x in range(w):
        t = 3 + 13 * abs((x + 0.5 - w / 2) / (w / 2)) ** 2.4 + rng.integers(0, 2)
        tops.append(int(t))
    for x in range(w):
        for y in range(tops[x], h):
            k = (y - tops[x]) / (h - tops[x])
            lit = 0.75 if x < w * 0.35 else (0.5 if x < w * 0.7 else 0.3)
            v = lit * (1 - 0.45 * k) + rng.normal(0, 0.05)
            put(a, x, y, pal[int(np.clip(v * len(pal), 0, len(pal) - 1))])
        for y in range(tops[x], tops[x] + 3 + int(rng.integers(0, 2))):
            put(a, x, y, cap[1] if y == tops[x] else cap[0])
    for _ in range(5):                       # strata
        y = int(rng.integers(14, 36)); x0 = int(rng.integers(0, 30))
        for x in range(x0, x0 + int(rng.integers(8, 18))):
            if a[y, x, 3]:
                put(a, x, y, pal[0])
    # the mouth: a dark arch, lightest at the rim
    mx, mw, mtop = 24, 15, 20
    for y in range(mtop, h):
        for x in range(w):
            dx = (x + 0.5 - mx) / (mw / 2)
            dy = (y - (mtop + 7)) / 7
            if abs(dx) <= 1 and (y >= mtop + 7 or dx * dx + dy * dy <= 1):
                depth = min(1, (y - mtop) / 14)
                put(a, x, y, mix((40, 34, 34), (6, 4, 6), 0.5 + 0.5 * depth))
    for x in range(w):                       # rim stones
        for y in range(mtop - 1, h):
            if a[y, x, 3] and a[y, x, 0] > 20:
                inside = abs(x + 0.5 - mx) < mw / 2 + 1 and y >= mtop
                if inside and abs(x + 0.5 - mx) > mw / 2 - 0.5:
                    put(a, x, y, pal[0])
    outline(a, shade(pal[0], 0.5))
    return a


# ---------------------------------------------------------------------------- hills
# Raised ground in the style of the DS games: the plateau's own turf curls over a lip at the
# top of each face, the face is banded rock lit from the upper left, and a soft shadow sits
# where it meets the ground below. Stairs are cut steps; waterfalls pour over a face.

CLIFF_PALETTES = {      # darkest -> lightest rock of the face
    "meadow":   [(74, 52, 38), (110, 78, 52), (148, 108, 70), (184, 146, 96), (212, 182, 126)],
    "tundra":   [(70, 82, 104), (104, 120, 146), (142, 160, 186), (182, 198, 220), (222, 232, 244)],
    "desert":   [(122, 70, 40), (164, 102, 56), (198, 138, 76), (226, 172, 104), (244, 206, 140)],
    "volcanic": [(22, 18, 20), (40, 34, 36), (62, 54, 54), (88, 78, 76), (116, 104, 98)],
    "storm":    [(36, 34, 56), (56, 54, 84), (80, 78, 112), (108, 106, 144), (142, 140, 178)],
}
CLIFF_LIP = {"meadow": "grass", "tundra": "snow", "desert": "sand", "volcanic": "ash", "storm": "slate"}


def _rock_face(a, pal, rng, y0, y1, x0=0, x1=T):
    """Banded rock between rows y0..y1: chunky blocks with lit tops, cracks and shadowed feet."""
    bands = []
    y = y0
    while y < y1:
        hgt = int(rng.integers(3, 6))
        bands.append((y, min(y1, y + hgt)))
        y += hgt
    for (by0, by1) in bands:
        x = x0 - int(rng.integers(0, 4))
        while x < x1:
            bw = int(rng.integers(4, 8))
            for yy in range(by0, by1):
                for xx in range(max(x0, x), min(x1, x + bw)):
                    k = (yy - by0) / max(1, by1 - by0 - 1)
                    lvl = 3 if yy == by0 else (2 if k < 0.6 else 1)
                    if xx == x:
                        lvl = min(lvl + 1, 4) if yy == by0 else 2     # lit left edge of each block
                    if xx == x + bw - 1:
                        lvl = 1
                    put(a, xx, yy, pal[lvl])
            for yy in range(by0, by1):                              # the crack between blocks
                if x0 <= x - 1 < x1:
                    put(a, x - 1, yy, pal[0])
            x += bw
        for xx in range(x0, x1):                                    # seam under each band
            if by1 - 1 >= by0 and rng.random() < 0.85:
                put(a, xx, by1 - 1, pal[0] if rng.random() < 0.6 else pal[1])
    for _ in range(3):                                              # glints
        put(a, int(rng.integers(x0, x1)), int(rng.integers(y0, y1)), pal[4])


def _lip(a, biome, rng, depth=4, x0=0, x1=T):
    """The turf of the plateau curling over the top of the face, with a dark rim beneath."""
    base, dark, light, _ = GROUNDS[CLIFF_LIP[biome]]
    edge = []
    for x in range(x0, x1):
        d = depth - 1 + (1 if rng.random() < 0.45 else 0) - (1 if rng.random() < 0.15 else 0)
        edge.append(d)
        for y in range(0, d):
            put(a, x, y, light if y == d - 1 and rng.random() < 0.4 else (dark if rng.random() < 0.08 else base))
        put(a, x, d - 1, light)
        put(a, x, d, shade(dark, 0.55))                              # rim shadow on the rock
    return edge


def cliff(biome, variant=0, seed=0):
    """One tile of cliff face. variant 0 = middle, 1 = west end, 2 = east end."""
    pal = CLIFF_PALETTES[biome]
    rng = np.random.default_rng((hash(biome) & 0xFFFF) * 7 + seed * 31 + variant)
    a = blank()
    a[..., 3] = 255
    a[..., :3] = pal[1]
    _rock_face(a, pal, rng, 3, 15)
    _lip(a, biome, rng)
    for x in range(T):                                               # contact shadow at the foot
        put(a, x, 15, shade(pal[0], 0.7))
        if rng.random() < 0.5:
            put(a, x, 14, pal[0])
    if variant == 1:                                                 # rounded west shoulder
        for y in range(T):
            put(a, 0, y, shade(pal[0], 0.6)); put(a, 1, y, pal[3] if y > 3 else a[y, 1, :3])
        put(a, 1, 3, pal[4]); put(a, 0, 0, a[0, 2, :3]); put(a, 1, 0, a[0, 2, :3])
    elif variant == 2:                                               # shaded east shoulder
        for y in range(T):
            put(a, 15, y, shade(pal[0], 0.6)); put(a, 14, y, pal[0] if y > 3 else a[y, 14, :3])
    return a


def stairs(biome):
    """Steps cut straight up through a cliff face, framed by the rock on each side."""
    pal = CLIFF_PALETTES[biome]
    rng = np.random.default_rng((hash(biome) & 0xFFFF) + 404)
    a = blank()
    a[..., 3] = 255
    a[..., :3] = pal[1]
    _rock_face(a, pal, rng, 3, 15, 0, 3)
    _rock_face(a, pal, rng, 3, 15, 13, 16)
    edge = _lip(a, biome, rng, 4, 0, 3)
    _lip(a, biome, rng, 4, 13, 16)
    tread, riser, nose = pal[3], pal[1], pal[4]
    base, dark, light, _ = GROUNDS[CLIFF_LIP[biome]]
    for x in range(3, 13):                                           # turf at the head of the stairs
        put(a, x, 0, base); put(a, x, 1, light if x % 3 else base)
    for i, sy in enumerate((2, 6, 10)):
        for x in range(3, 13):
            put(a, x, sy, nose)                                      # lit nosing
            put(a, x, sy + 1, tread); put(a, x, sy + 2, tread)
            put(a, x, sy + 3, riser)                                 # shadowed riser
        put(a, 3, sy + 3, pal[0]); put(a, 12, sy + 3, pal[0])
        for _ in range(2):
            put(a, int(rng.integers(4, 12)), sy + 1 + int(rng.integers(0, 2)), pal[2])
    for x in range(3, 13):
        put(a, x, 14, tread); put(a, x, 15, shade(pal[0], 0.8))
    for y in range(2, 16):                                           # cut edges of the stairwell
        put(a, 3, y, shade(pal[0], 0.9)); put(a, 12, y, pal[2])
    return a


def waterfall_frames(n=4):
    """Water pouring over a cliff lip, the streaks sliding down a little each frame."""
    rng = np.random.default_rng(77)
    cols = [(56, 118, 204), (82, 148, 224), (128, 186, 240), (196, 230, 252), (250, 252, 255)]
    streaks = [(x, int(rng.integers(0, 16)), int(rng.integers(3, 7)), int(rng.integers(2, 5))) for x in range(1, 15)]
    frames = []
    for f in range(n):
        a = blank()
        a[..., 3] = 255
        for y in range(T):
            for x in range(T):
                edge = x in (0, 15)
                put(a, x, y, (40, 62, 96) if edge else cols[1 if (x * 7 + y) % 5 else 0])
        for (x, y0, ln, c) in streaks:
            for i in range(ln):
                put(a, x, (y0 + i + f * 4) % 16, cols[c])
        for x in range(1, 15):                                       # glassy lip where it spills over
            put(a, x, 0, cols[3]); put(a, x, 1, cols[4] if (x + f) % 3 else cols[3]); put(a, x, 2, cols[2])
        for x in range(1, 15):                                       # churn at the foot
            for y in (13, 14, 15):
                if (x + y + f) % 3 != 0 or y == 15:
                    put(a, x, y, cols[4] if (x + f + y) % 2 else cols[3])
        frames.append(a)
    return frames


def walltorch():
    """A torch in an iron bracket, hung on a wall face."""
    a = blank()
    for y in range(7, 13):
        put(a, 7, y, (110, 74, 40)); put(a, 8, y, (80, 52, 30))
    for x in range(5, 11):
        put(a, x, 12, (70, 70, 80))
    for (x, y, c) in ((7, 3, (255, 240, 170)), (8, 3, (255, 210, 90)), (7, 4, (255, 210, 90)), (8, 4, (255, 170, 60)),
                      (6, 5, (250, 140, 40)), (7, 5, (255, 200, 80)), (8, 5, (250, 150, 50)), (9, 5, (220, 90, 30)),
                      (7, 6, (230, 110, 40)), (8, 6, (230, 110, 40)), (7, 2, (255, 250, 220))):
        put(a, x, y, c)
    outline(a, (24, 18, 20))
    return a


def door(opened):
    """An iron portcullis in a stone arch; raised when open."""
    a = blank()
    stone, dark, iron, iron_d = (120, 120, 132), (64, 64, 76), (88, 92, 104), (52, 54, 64)
    for y in range(16):
        for x in range(16):
            if x < 2 or x > 13 or y < 2:
                put(a, x, y, stone if (x + y) % 5 else dark)
    for y in range(2, 16):
        for x in range(2, 14):
            put(a, x, y, (20, 16, 22) if opened else (34, 30, 36))
    if opened:
        for x in range(2, 14):                        # bars pulled up into the arch
            put(a, x, 2, iron); put(a, x, 3, iron_d)
    else:
        for x in (3, 6, 9, 12):
            for y in range(2, 16):
                put(a, x, y, iron); put(a, x + 1, y, iron_d)
        for y in (6, 11):
            for x in range(2, 14):
                put(a, x, y, iron)
        for x in (3, 6, 9, 12):
            put(a, x, 15, (150, 154, 166))
    return a


def gate(biome):
    """A dungeon gate: a ruined stone facade with a dark arched doorway (48x40)."""
    w, h = 48, 40
    a = blank(w, h)
    banner = {"meadow": (60, 140, 70), "tundra": (110, 170, 220), "desert": (200, 150, 60),
              "volcanic": (200, 60, 40), "storm": (130, 90, 200)}[biome]
    stone = [(70, 70, 82), (98, 98, 110), (130, 130, 142), (160, 160, 170)]
    rng = np.random.default_rng(hash(biome) & 0xFFF)
    for y in range(6, h):
        for x in range(2, w - 2):
            off = 4 if (y // 5) % 2 else 0
            lit = 2 if x < w * 0.4 else 1
            c = stone[lit] if (y % 5 and (x + off) % 9) else stone[0]
            if rng.random() < 0.05:
                c = stone[3]
            put(a, x, y, c)
    for x in range(0, w):                           # battlements
        if (x // 6) % 2 == 0:
            for y in range(1, 7):
                put(a, x, y, stone[2] if x < w * 0.4 else stone[1])
    for px in (4, 40):                               # pillars
        for y in range(4, h):
            for x in range(px, px + 5):
                put(a, x, y, stone[3] if x == px else (stone[2] if x < px + 3 else stone[1]))
    mx, mw, mtop = 24, 14, 17                        # arched doorway
    for y in range(mtop, h):
        for x in range(w):
            dx = (x + 0.5 - mx) / (mw / 2)
            dy = (y - (mtop + 7)) / 7
            if abs(dx) <= 1 and (y >= mtop + 7 or dx * dx + dy * dy <= 1):
                put(a, x, y, mix((30, 26, 30), (4, 2, 6), min(1, (y - mtop) / 14)))
    for y in range(9, 17):                           # banners
        for x in list(range(12, 16)) + list(range(32, 36)):
            put(a, x, y, banner if x not in (12, 35) else shade(banner, 0.7))
    for x in (13, 14, 33, 34):
        put(a, x, 17, shade(banner, 0.6))
    outline(a, (24, 22, 30))
    return a


def chest(rarity, opened=False):
    gem = RARITY_GEMS[rarity]
    wood_d, wood, wood_l = (92, 56, 30), (138, 86, 46), (176, 118, 64)
    band = mix(gem, (255, 255, 255), 0.15) if rarity != "Common" else (170, 170, 176)
    a = blank()
    body_top = 8
    for y in range(body_top, 15):
        for x in range(2, 14):
            put(a, x, y, wood_l if y == body_top else (wood if y < 13 else wood_d))
    if opened:
        for y in range(3, 7):
            for x in range(2, 14):
                put(a, x, y, wood_d if y < 5 else wood)
        for x in range(3, 13):
            put(a, x, 7, (24, 14, 10))
    else:
        for y in range(4, body_top):
            for x in range(2, 14):
                put(a, x, y, wood_l if y == 4 else wood)
        put(a, 7, 8, gem); put(a, 8, 8, gem); put(a, 7, 9, shade(gem, 0.7)); put(a, 8, 9, shade(gem, 0.7))
    for y in range(3 if opened else 4, 15):
        put(a, 3, y, band); put(a, 12, y, band)
    outline(a, (40, 24, 14))
    return a


def shadow(w=12, h=5):
    a = blank(16, 8)
    for y in range(8):
        for x in range(16):
            d = ((x + 0.5 - 8) / (w / 2)) ** 2 + ((y + 0.5 - 4) / (h / 2)) ** 2
            if d < 1:
                a[y, x] = (0, 0, 0, int(90 * (1 - d * 0.6)))
    return a


# ---------------------------------------------------------------------------- player

# Pixel maps, 16 wide. Head+body are 16 rows, legs add 4 (20 tall). Letters:
#   o outline   C/c/h outfit colour (main/shade/highlight)   S/s skin   E eyes   H hair
#   M/m/W armour metal   R plume (hair colour)   w hand wraps   B belt   P legs   b boots
MAGE = {
    "down": [
        ".....oooooo.....",
        "....ohhCCCCo....",
        "...ohCCCCCCCo...",
        "...oCCCCCCCCo...",
        "..ocCHHHHHHCco..",
        "..ocCSSSSSSCco..",
        "..ocSESSSSESco..",
        "..ocSESSSSESco..",
        "...ocSSSSSSco...",
        "...oCcssssCCo...",
        "..oCCCCCCCCCCo..",
        ".ohCCCCCCCCCCco.",
        ".oSCCCBBBBCCCSo.",
        ".oSCCCCCCCCCCSo.",
        "..ocCCCCCCCCco..",
        "...occCCCCcco...",
    ],
    "up": [
        ".....oooooo.....",
        "....ohhCCCCo....",
        "...ohCCCCCCCo...",
        "...oCCCCCCCCo...",
        "..ocCCCCCCCCco..",
        "..ocCCCCCCCCco..",
        "..ocCChhhhCCco..",
        "..ocCCCCCCCCco..",
        "...ocCCCCCCco...",
        "...oCccccccCo...",
        "..oCCCCCCCCCCo..",
        ".ohCCCCCCCCCCco.",
        ".oSCCCCCCCCCCSo.",
        ".oSCCCCCCCCCCSo.",
        "..ocCCCCCCCCco..",
        "...occCCCCcco...",
    ],
    "right": [
        "......ooooo.....",
        ".....ohhCCCo....",
        "....ohCCCCCCo...",
        "....oCCCCCCCCo..",
        "...ocCCHHHHHCo..",
        "...ocCCSSSSSSo..",
        "...ocCCSSSSESo..",
        "...ocCCSSSSESo..",
        "....ocCSSSSSo...",
        "....oCCcsssCo...",
        "...oCCCCCCCCo...",
        "...ohCCCCCCCco..",
        "...ohCCCSSCCCo..",
        "...oCCCCSSCCco..",
        "....ocCCCCCco...",
        "....occCCCcco...",
    ],
}
BRAWLER = {
    "down": [
        ".....oooooo.....",
        "....oHHHHHHo....",
        "...oHHHHHHHHo...",
        "...oHHHHHHHHo...",
        "..oHCCCCCCCCHo..",
        "..oHSSSSSSSSHo..",
        "..oHSESSSSESHo..",
        "..oSSESSSSESSo..",
        "...oSSSSSSSSo...",
        "....osssssso....",
        "..oSSCCCCCCSSo..",
        ".oSSCCCCCCCCSSo.",
        ".oSsCCCBBCCCsSo.",
        ".owwCCCCCCCCwwo.",
        "..oocCCCCCCcoo..",
        "...ocCCCCCCco...",
    ],
    "up": [
        ".....oooooo.....",
        "....oHHHHHHo....",
        "...oHHHHHHHHo...",
        "...oHHHHHHHHo...",
        "..oHCCCCCCCCHo..",
        "..oHHHHHHHHHHo..",
        "..oHHHHHHHHHHo..",
        "..oSHHHHHHHHSo..",
        "...oSHHHHHHSo...",
        "....osssssso....",
        "..oSSCCCCCCSSo..",
        ".oSSCCCCCCCCSSo.",
        ".oSsCCCCCCCCsSo.",
        ".owwCCCCCCCCwwo.",
        "..oocCCCCCCcoo..",
        "...ocCCCCCCco...",
    ],
    "right": [
        "......ooooo.....",
        ".....oHHHHHo....",
        "....oHHHHHHHo...",
        "....oHHHHHHHHo..",
        "...oHCCCCCCCCo..",
        "...oHHSSSSSSSo..",
        "...oHHSSSSSESo..",
        "...oHSSSSSSESo..",
        "....oSSSSSSSo...",
        ".....ossssso....",
        "....oCCCCCCo....",
        "...oSCCCCCCCo...",
        "...oSCCCSSCCo...",
        "...owCCCwwCCo...",
        "....ocCCCCCo....",
        "....occCCcco....",
    ],
}
KNIGHT = {
    "down": [
        ".......oo.......",
        "......oRRo......",
        "....ooRRRRoo....",
        "...oWWMMMMMMo...",
        "..oWMMMMMMMMmo..",
        "..oMMSSSSSSMmo..",
        "..oMSESSSSESmo..",
        "..oMSESSSSESmo..",
        "..oMMSSSSSSMmo..",
        "...oMMmmmmMMo...",
        "..oCMMMMMMMMCo..",
        ".oCCMWMMMMMmCCo.",
        ".oSCMMMBBMMmCSo.",
        ".oSCMMMMMMMmCSo.",
        "..ocCmMMMMmCco..",
        "...occCCCCcco...",
    ],
    "up": [
        ".......oo.......",
        "......oRRo......",
        "....ooRRRRoo....",
        "...oWWMMMMMMo...",
        "..oWMMMMMMMMmo..",
        "..oMMMMMMMMMmo..",
        "..oMMMMMMMMMmo..",
        "..oMMMMMMMMMmo..",
        "..oMMMMMMMMMmo..",
        "...oMMmmmmMMo...",
        "..oCCCCCCCCCCo..",
        ".ohCCCCCCCCCCco.",
        ".oSCCCCCCCCCCSo.",
        ".oSCCCCCCCCCCSo.",
        "..ocCCCCCCCCco..",
        "...occCCCCcco...",
    ],
    "right": [
        "........oo......",
        ".......oRRo.....",
        ".....ooRRRoo....",
        "....oWWMMMMMo...",
        "...oWMMMMMMMMo..",
        "...oMMMMSSSSMo..",
        "...oMMMSSSSESo..",
        "...oMMMSSSSESo..",
        "...oMMMMSSSSMo..",
        "....oMMmmmmMo...",
        "...oCMMMMMMMo...",
        "...oCMWMMMMMmo..",
        "...oCMMMSSMMmo..",
        "...oCMMMSSMMmo..",
        "....ocMMMMMmo...",
        "....occCCCcco...",
    ],
}
OUTFITS = {"Mage": MAGE, "Brawler": BRAWLER, "Knight": KNIGHT}
_LEGS_FRONT = {
    0: ["....oPPooPPo....", "....oPPooPPo....", "....obboobbo....", ".....oo..oo....."],
    1: ["....oPPooPPo....", "....oPPo.oPo....", "....obbo.obo....", ".....oo...o....."],
    2: ["....oPPooPPo....", "....oPo.oPPo....", "....obo.obbo....", ".....o...oo....."],
}
_LEGS_SIDE = {
    0: [".....oPPPPo.....", ".....oPPPPo.....", ".....obbbbo.....", "......oooo......"],
    1: ["....oPPooPPo....", "...oPPo..oPPo...", "...obbo..obbo...", "....oo....oo...."],
    2: [".....oPPPPo.....", "......oPPo......", "......obbo......", ".......oo......."],
}

# Hairstyles. The overworld walker draws its head from these maps whenever the hood (or the
# Knight's helmet) is off. Each style has, per facing, the head rows (9 rows, or 11 when it
# rises into the 2 rows of headroom above the head) and an optional overlay laid over the
# body from the neck row down — hair that hangs past the chin.
#   H hair   L hair highlight   D hair shadow   C outfit colour (ties and bands)
HAIRSTYLES = ["Short", "Spiky", "Shaggy", "Long", "Ponytail", "Twin Tails", "Bun", "Mohawk", "Bob", "Swept"]
HAIR_SPILLS = {"Long", "Ponytail"}          # still hangs out from under a raised hood
WALKER_HEADROOM = 2

WALKER_HAIR = {
    "Short": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "...oHHHHHHHDo...",
                  "..oHHDHHHHDHHo..",
                  "..oHSSSSSSSSHo..",
                  "..oDSESSSSESDo..",
                  "..oSSESSSSESSo..",
                  "...oSSSSSSSSo..."], []),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "...oHHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oSDHHHHHHDSo..",
                "...oSSSSSSSSo..."], []),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "....oHHHHHHHHo..",
                   "...oHHHHHHHDHo..",
                   "...oHHDSSSSSSo..",
                   "...oHHSSSSSESo..",
                   "...oDSSSSSSESo..",
                   "....oSSSSSSSo..."], []),
    },
    # Spiky is drawn as fill only (no 'o'): its ragged silhouette gets its outline from
    # _auto_outline below. Locks of uneven length lean outward instead of standing in a row.
    "Spiky": {
        "down": (["..D......D......",
                  "..HL....LH...D..",
                  "...HL..HHH..HH..",
                  "...HHLHHLHHHHH..",
                  ".DHHHHHHHHHHHH..",
                  "..HHHHHHHHHHHHD.",
                  "...HDHHHDHHHDH..",
                  "...HSDSSSSDSH...",
                  "...DSESSSSESD...",
                  "...SSESSSSESS...",
                  "....SSSSSSSS...."], []),
        "up": (["..D......D......",
                "..HL....LH...D..",
                "...HL..HHH..HH..",
                "...HHLHHLHHHHH..",
                ".DHHHHHHHHHHHH..",
                "..HHHHHHDHHHHHD.",
                "...HHDHHHHDHH...",
                "...HDHHDHHDHD...",
                "...HHHDHHHHDH...",
                "...SDHDHHDHDS...",
                "....SSSSSSSS...."], []),
        "right": ([".D....D.........",
                   ".HL...HL....D...",
                   "..HH...HHL..H...",
                   "...HHLHHHHHHH...",
                   ".DHHHHHHLHHHH...",
                   "..HHHHHHHHHHHH..",
                   "...HHHHHHHHDH...",
                   "...HHHDSSSSSS...",
                   "....HHSSSSSES...",
                   "....DSSSSSSES...",
                   ".....SSSSSSS...."], []),
    },
    "Shaggy": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "..oHHHHHHHHHHo..",
                  "..oHHHHDHHHHHo..",
                  "..oHHSHSSHSHHo..",
                  "..oHSESSSSESHo..",
                  "..oHSESSSSESHo..",
                  "..oDoSSSSSSoDo.."], []),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHDHHHHDHHo..",
                "..oHHHHHHHHHHo..",
                "..oHDHHDHHDHHo..",
                "..oDHDHHHHDHDo.."], []),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "...oHHHHHHHHHo..",
                   "...oHHHHHHHHHo..",
                   "..oHHHHHSSHSHo..",
                   "..oHHHHSSSSESo..",
                   "..oHDHSSSSSESo..",
                   "...oDHSSSSSSo..."], []),
    },
    "Long": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "..oHHHHHHHHHHo..",
                  "..oHHHDHHDHHHo..",
                  "..oHHSSSSSSHHo..",
                  "..oHSESSSSESHo..",
                  "..oHSESSSSESHo..",
                  "..oHDSSSSSSDHo.."],
                 ["..oHDo....oDHo..",
                  "..oHHo....oHHo..",
                  "..oDHo....oHDo..",
                  "...oo......oo..."]),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oDHHHHHHHHDo.."],
               ["..oDHHHHHHHHDo..",
                "...oDHHHHHHDo...",
                "...oDHHHHHHDo...",
                "....oDDDDDDo....",
                ".....oooooo....."]),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "...oHHHHHHHHHo..",
                   "...oHHHHHHHDHo..",
                   "...oHHHDSSSSSo..",
                   "...oHHHSSSSESo..",
                   "...oHHHSSSSESo..",
                   "...oHHDSSSSSo..."],
                  ["...oHHDo........",
                   "...oHHDo........",
                   "...oDHDo........",
                   "....ooo........."]),
    },
    "Ponytail": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "...oHHHHHHHDo...",
                  "..oHHHHDDHHHHo..",
                  "..oHSSSSSSSSHo..",
                  "..oSSESSSSESSo..",
                  "..oSSESSSSESSo..",
                  "...oSSSSSSSSo..."], []),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "...oHHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHLHHHHHo..",
                "..oHHHHCCHHHHo..",
                "..oSHHHHHHHHSo..",
                "...oSSoHHoSSo..."],
               ["......oHHo......",
                "......oHDo......",
                "......oDHo......",
                ".......oo......."]),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "....oHHHHHHHHo..",
                   "...oHHHHHHHHSo..",
                   "..oCHHHHSSSSSo..",
                   "..oHHHHSSSSESo..",
                   ".oHDoHSSSSSESo..",
                   ".oHDooSSSSSSo..."],
                  [".oDHo...........",
                   "..oDo...........",
                   "...o............"]),
    },
    "Twin Tails": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "...oHHHHHHHHo...",
                  "..oHHHHDDHHHHo..",
                  ".ooHSSSSSSSSHoo.",
                  "oCoSSESSSSESSoCo",
                  "oHoSSESSSSESSoHo",
                  "oHDoSSSSSSSSoDHo"],
                 ["oHDo........oDHo",
                  "oDHo........oHDo",
                  ".oo..........oo."]),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "...oHHHHHHHHo...",
                "..oHHHHDDHHHHo..",
                ".ooHHHHDDHHHHoo.",
                "oCoHHHHHHHHHHoCo",
                "oHoHHHHHHHHHHoHo",
                "oHDoSHHHHHHSoDHo"],
               ["oHDo........oDHo",
                "oDHo........oHDo",
                ".oo..........oo."]),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "....oHHHHHHHHo..",
                   "...oHHHHHHHDHo..",
                   "..ooHHHSSSSSSo..",
                   ".oCoHHSSSSSESo..",
                   ".oHoHSSSSSSESo..",
                   ".oHDoSSSSSSSo..."],
                  [".oHDo...........",
                   ".oDHo...........",
                   "..oo............"]),
    },
    "Bun": {
        "down": (["......oooo......",
                  ".....oLHHDo.....",
                  "....ooCCCCoo....",
                  "....oLHHHHHo....",
                  "...oLHHHHHHHo...",
                  "...oHHHHHHHHo...",
                  "..oHHHHDDHHHHo..",
                  "..oHSSSSSSSSHo..",
                  "..oSSESSSSESSo..",
                  "..oSSESSSSESSo..",
                  "...oSSSSSSSSo..."], []),
        "up": (["......oooo......",
                ".....oLHHDo.....",
                "....ooCCCCoo....",
                "....oHHHHHHo....",
                "...oLHHHHHHHo...",
                "...oHHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oSDHHHHHHDSo..",
                "...oSSSSSSSSo..."], []),
        "right": ([".....oooo.......",
                   "....oLHHDo......",
                   "....ooCCCoo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "....oHHHHHHHHo..",
                   "...oHHHHHHHDHo..",
                   "...oHHDSSSSSSo..",
                   "...oHSSSSSSESo..",
                   "...oDSSSSSSESo..",
                   "....oSSSSSSSo..."], []),
    },
    "Mohawk": {
        "down": ([".......oo.......",
                  "......oLHo......",
                  ".....ooLHoo.....",
                  "....oSsLHsSo....",
                  "...oSSsLHsSSo...",
                  "...oSSsHDsSSo...",
                  "..oSSSSHDSSSSo..",
                  "..oSSSSSSSSSSo..",
                  "..osSESSSSESso..",
                  "..oSSESSSSESSo..",
                  "...oSSSSSSSSo..."], []),
        "up": ([".......oo.......",
                "......oLHo......",
                ".....ooLHoo.....",
                "....oSsLHsSo....",
                "...oSSsLHsSSo...",
                "...oSSsHHsSSo...",
                "..oSSSsHHsSSSo..",
                "..oSSSsHHsSSSo..",
                "..oSSSsHDsSSSo..",
                "..oSSSSDDSSSSo..",
                "...oSSSSSSSSo..."], []),
        "right": ([".......ooo......",
                   "......oLHHo.....",
                   ".....oLHHHDo....",
                   ".....oLHHHDo....",
                   "....oSsHHHsSo...",
                   "....oSSsssssSo..",
                   "...oSSSSSSSSSo..",
                   "...oSSSSSSSSSo..",
                   "...oSSSSSSSESo..",
                   "...oSSSSSSSESo..",
                   "....oSSSSSSSo..."], []),
    },
    "Bob": {
        "down": ([".....oooooo.....",
                  "....oLLHHHHo....",
                  "...oLHHHHHHHo...",
                  "..oHHHHHHHHHHo..",
                  "..oHHHHHHHHHHo..",
                  "..oHHSSSSSSHHo..",
                  "..oHSESSSSESHo..",
                  "..oHSESSSSESHo..",
                  "..oDHSSSSSSHDo.."],
                 ["..ooo......ooo.."]),
        "up": ([".....oooooo.....",
                "....oLLHHHHo....",
                "...oLHHHHHHHo...",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oDDDDDDDDDDo.."],
               ["...oooooooooo..."]),
        "right": (["......ooooo.....",
                   ".....oLHHHHo....",
                   "....oLHHHHHHo...",
                   "...oHHHHHHHHHo..",
                   "...oHHHHHHHHHo..",
                   "...oHHHHDSSSSo..",
                   "...oHHHHSSSESo..",
                   "...oHHHHSSSESo..",
                   "...oDDDDoSSSo..."],
                  ["....oooo........"]),
    },
    "Swept": {
        "down": ([".....oooooo.....",
                  "....oHHLLLHo....",
                  "...oHHHHLLHHo...",
                  "..oHHHHHHHLHHo..",
                  "..oHDSSSHHHHHo..",
                  "..oHSSSSSSHHDo..",
                  "..oHSESSSSEHHo..",
                  "..oSSESSSSESDo..",
                  "...oSSSSSSSSo..."], []),
        "up": ([".....oooooo.....",
                "....oHHLLLHo....",
                "...oHHHHLLHHo...",
                "..oHHHHHHHLHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oHHHHHHHHHHo..",
                "..oSDHHHHHHHDo..",
                "...oSSSSSSSSo..."], []),
        "right": (["......ooooo.....",
                   ".....oHLLLLo....",
                   "....oHHHHLLLo...",
                   "....oHHHHHHLLo..",
                   "...oHHHHHHHHHo..",
                   "...oHHDSSSSHHo..",
                   "...oHHSSSSSESo..",
                   "...oDSSSSSSESo..",
                   "....oSSSSSSSo..."], []),
    },
}
def _auto_outline(rows):
    """Ring a fill-only head map with outline pixels (4-neighbours of the fill)."""
    h, w = len(rows), len(rows[0])
    filled = [[ch != "." for ch in r] for r in rows]
    out = []
    for y, r in enumerate(rows):
        line = []
        for x, ch in enumerate(r):
            if ch == "." and any(0 <= y + dy < h and 0 <= x + dx < w and filled[y + dy][x + dx]
                                 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                ch = "o"
            line.append(ch)
        out.append("".join(line))
    return out


for _d, (_head, _over) in list(WALKER_HAIR["Spiky"].items()):
    WALKER_HAIR["Spiky"][_d] = (_auto_outline(_head), _over)
for _s, _dirs in WALKER_HAIR.items():
    for _d, (_head, _over) in _dirs.items():
        assert len(_head) in (9, 11) and all(len(r) == 16 for r in _head + _over), (_s, _d)


def walker_rows(cls, d, style="Short", hood=True):
    """The 22 map rows (headroom + head + body, no legs) for a class seen from `d`, and the
    hair overlay to lay over the body from the neck row down."""
    body = OUTFITS.get(cls, MAGE)[d]
    knight = cls == "Knight"
    style = style if style in WALKER_HAIR else "Short"
    blank_row = "." * 16
    if hood:          # the raised hood (any class but the Knight), or the Knight's helmet
        rows = [blank_row] * WALKER_HEADROOM + list((KNIGHT if knight else MAGE)[d][:10]) + list(body[10:])
        overlay = WALKER_HAIR[style][d][1] if style in HAIR_SPILLS and not knight else []
    else:
        head, overlay = WALKER_HAIR[style][d]
        rows = [blank_row] * (WALKER_HEADROOM + 9 - len(head)) + list(head) + list(body[9:])
        if cls == "Brawler":      # the Brawler keeps the headband across the brow
            r = WALKER_HEADROOM + 4
            rows[r] = "".join("C" if ch in "HLDSs" else ch for ch in rows[r])
    top = WALKER_HEADROOM + 9
    for i, orow in enumerate(overlay):
        rows[top + i] = "".join(o if o != "." else b for o, b in zip(orow, rows[top + i]))
    return rows


# Look options offered on the character screen
SKIN_TONES = {"Porcelain": (252, 222, 196), "Fair": (246, 204, 166), "Tan": (222, 168, 120),
              "Bronze": (176, 116, 74), "Umber": (118, 74, 48),
              # elves
              "Moonlit": (240, 236, 228), "Sylvan": (212, 228, 190), "Dusk": (176, 156, 196),
              # orcs
              "Moss": (122, 158, 82), "Jade": (88, 148, 104), "Olive": (142, 140, 72), "Slate Grey": (124, 128, 120),
              # skeletons
              "Bone": (226, 220, 196), "Ivory": (242, 238, 222), "Ashen": (184, 180, 168), "Obsidian": (78, 72, 84),
              # goblins
              "Swamp": (110, 140, 70), "Lime": (150, 190, 80), "Mustard": (190, 170, 70), "Clay": (170, 120, 80)}
# Which skin tones each race may pick (first = default)
RACE_SKINS = {
    "Human": ["Fair", "Porcelain", "Tan", "Bronze", "Umber"],
    "Elf": ["Moonlit", "Fair", "Sylvan", "Dusk", "Tan"],
    "Orc": ["Moss", "Jade", "Olive", "Slate Grey"],
    "Dwarf": ["Fair", "Porcelain", "Tan", "Bronze", "Umber"],
    "Skeleton": ["Bone", "Ivory", "Ashen", "Obsidian"],
    "Goblin": ["Swamp", "Lime", "Mustard", "Clay"],
}
HAIR_COLORS = {"Raven": (40, 34, 44), "Chestnut": (112, 66, 36), "Auburn": (164, 64, 40),
               "Golden": (232, 190, 80), "Ash": (176, 176, 184), "Snow": (240, 240, 246),
               "Violet": (130, 84, 190)}
OUTFIT_COLORS = {"Crimson": (178, 40, 50), "Ember": (220, 110, 40), "Gold": (214, 170, 60),
                 "Forest": (52, 130, 70), "Teal": (40, 140, 140), "Azure": (60, 110, 210),
                 "Indigo": (78, 60, 160), "Violet": (150, 70, 180), "Rose": (210, 100, 150),
                 "Slate": (90, 98, 116), "Ivory": (226, 220, 200)}


_OUTLINE = (30, 22, 32)


def _put_outlined(a, x, y, col):
    """A pixel that grows the silhouette: outline any empty neighbour so it reads as part
    of the sprite rather than a stray dot."""
    h, w = a.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return
    put(a, x, y, col)
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nx < w and 0 <= ny < h and a[ny, nx, 3] == 0:
            put(a, nx, ny, _OUTLINE)


def race_features(a, rows, race, d, skin, hair, top=0, ears=True):
    """Draw a race's tell-tale features onto one frame: elf and goblin ears, orc tusks,
    a dwarf's beard, a skeleton's skull."""
    eyes = [(x, y) for y, row in enumerate(rows) for x, ch in enumerate(row) if ch == "E"]
    if eyes:
        ey = min(y for _, y in eyes)
        exs = sorted({x for x, _ in eyes})
        left, right = exs[0], exs[-1]
    else:                                   # seen from behind
        ey, left, right = 6 + top, 5, 10
    opaque = np.nonzero(a[ey, :, 3])[0]
    lx, rx = (int(opaque.min()), int(opaque.max())) if len(opaque) else (2, 13)
    if race in ("Elf", "Goblin") and ears:
        long_ = race == "Goblin"
        if d in ("down", "up"):
            for side, x0, step in (("l", lx, -1), ("r", rx, 1)):
                pts = ([(x0 + step, ey), (x0 + step * 2, ey), (x0 + step, ey + 1)] if long_ else
                       [(x0 + step, ey), (x0 + step, ey - 1), (x0 + step * 2, ey - 1)])
                for (x, y) in pts:                    # solid shape first, then its outline
                    put(a, x, y, skin)
                for (x, y) in pts:
                    _put_outlined(a, x, y, skin)
                put(a, x0, ey, skin)                  # joins the ear to the head
        else:                               # profile: the ear sits mid-head
            x = (lx + rx) // 2 - 1
            put(a, x, ey, skin); put(a, x, ey + 1, shade(skin, 0.85))
            put(a, x - 1, ey - 1, skin)
            if long_:
                put(a, x - 2, ey - 1, skin); put(a, x - 1, ey, skin)
    if not eyes:
        return
    if race == "Orc":
        white = (246, 240, 220)
        if d == "down":
            put(a, left + 1, ey + 2, white); put(a, right - 1, ey + 2, white)
        else:
            put(a, right, ey + 2, white)
    if race == "Dwarf":
        x0, x1 = (left - 1, right + 1) if d == "down" else (right - 3, right + 1)
        for y in range(ey + 1, ey + 5):
            for x in range(x0 + (1 if y == ey + 4 else 0), x1 + 1 - (1 if y == ey + 4 else 0)):
                if 0 <= x < a.shape[1] and a[y, x, 3]:
                    put(a, x, y, hair if (x + y) % 3 else shade(hair, 0.8))
        if d == "down":                     # the mouth peeks through
            put(a, (left + right) // 2, ey + 2, shade(hair, 0.55))
    if race == "Skeleton":
        dark = (24, 18, 26)
        for (x, y) in eyes:
            put(a, x, y, dark)
            nx = x + (1 if x == left else -1) if d == "down" else x - 1
            put(a, nx, y, dark)
        c = (left + right) // 2 if d == "down" else right - 1
        put(a, c, ey + 2, dark)
        if d == "down":
            put(a, c + 1, ey + 2, dark)
        for x in range(left, right + 1) if d == "down" else range(right - 3, right + 1):
            if x % 2 == 0:
                put(a, x, ey + 3, dark)


def player_frames(look):
    """{"down"/"up"/"left"/"right": [stand, step_a, step_b]} of 16x22 sprites (2 rows of
    headroom over the head for spikes, buns and crests).

    `look` is {"class", "color", "skin", "hair", "style", "hood"} (colours as RGB, style a
    HAIRSTYLES name, hood True/False), or just an RGB tuple for the original hooded figure."""
    if not isinstance(look, dict):
        look = {"class": "Mage", "color": look}
    outfit = OUTFITS.get(look.get("class"), MAGE)
    cloak = tuple(int(v) for v in look.get("color", (70, 110, 220)))
    if sum(cloak) < 150:
        cloak = mix(cloak, (180, 180, 200), 0.45)
    if sum(cloak) / 3 > 200:
        cloak = shade(cloak, 0.82)
    skin = tuple(look.get("skin", SKIN_TONES["Fair"]))
    hair = tuple(look.get("hair", HAIR_COLORS["Chestnut"]))
    style = look.get("style", "Short")
    hood = look.get("hood", True)
    knight = outfit is KNIGHT
    colors = {"o": (30, 22, 32), "C": cloak, "c": shade(cloak, 0.66), "h": mix(cloak, (255, 255, 255), 0.42),
              "S": skin, "s": shade(skin, 0.82), "E": (34, 28, 44), "B": (110, 74, 44),
              "H": hair, "L": mix(hair, (255, 255, 255), 0.32), "D": shade(hair, 0.7), "R": hair, "M": (176, 184, 200), "m": (116, 124, 146), "W": (232, 236, 246),
              "w": (236, 226, 206),
              "P": (98, 104, 124) if knight else (64, 62, 86), "b": (70, 76, 92) if knight else (70, 46, 32)}
    out = {}
    for d, legs in (("down", _LEGS_FRONT), ("up", _LEGS_FRONT), ("right", _LEGS_SIDE)):
        frames = []
        for f in range(3):
            rows = walker_rows(look.get("class") if look.get("class") in OUTFITS else "Mage", d, style, hood)
            a = from_map(rows + legs[f], colors)
            race_features(a, rows, look.get("race", "Human"), d, skin, hair, top=WALKER_HEADROOM,
                          ears=hood or style != "Twin Tails")
            if f:                            # a 1px bob on the stepping frames
                a = np.roll(a, 1, axis=0)
                a[0] = 0
            frames.append(to_surface(a))
        out[d] = frames
    out["left"] = [pygame.transform.flip(s, True, False) for s in out["right"]]
    return out


# ---------------------------------------------------------------------------- build

def build_tileset():
    """{name: Surface or [Surface, …]} — every tile and sprite the world renderer draws."""
    t = {}
    for name in GROUNDS:
        t[name] = [to_surface(a) for a in ground_tiles(name)]
    t["water"] = [to_surface(a) for a in liquid_frames((64, 130, 210), (48, 106, 186), (100, 160, 226), (206, 234, 252), 11)]
    t["lava"] = [to_surface(a) for a in liquid_frames((226, 96, 28), (178, 52, 20), (246, 140, 40), (255, 214, 96), 12, glow=True)]
    t["cwater"] = [to_surface(a) for a in liquid_frames((36, 82, 116), (26, 62, 94), (56, 110, 146), (140, 196, 220), 13)]
    t["clava"] = t["lava"]
    t["cice"] = [to_surface(a) for a in ground_tiles("ice")]
    for theme in CAVE_THEMES:
        t["cfloor_" + theme] = [to_surface(cave_floor(theme, i)) for i in range(4)]
        t["cface_" + theme] = [to_surface(cave_face(theme, i)) for i in range(3)]
        t["ctop_" + theme] = [to_surface(cave_top(theme, i)) for i in range(3)]
        t["stalagmite_" + theme] = to_surface(stalagmite(theme))
    # decor
    t["tallgrass"] = [to_surface(tallgrass((40, 112, 52), (66, 150, 64), (120, 196, 92), s)) for s in (1, 2, 3)]
    t["stormgrass"] = [to_surface(tallgrass((40, 70, 76), (60, 104, 104), (110, 150, 150), s)) for s in (4, 5, 6)]
    t["frostgrass"] = [to_surface(tallgrass((70, 120, 120), (120, 176, 170), (226, 244, 250), s)) for s in (7, 8, 9)]
    t["drygrass"] = [to_surface(tallgrass((150, 112, 50), (196, 158, 74), (236, 210, 120), s)) for s in (10, 11, 12)]
    t["ashgrass"] = [to_surface(tallgrass((60, 34, 30), (112, 52, 36), (220, 110, 50), s)) for s in (13, 14, 15)]
    t["alert"] = to_surface(alert_bubble())
    t["alert_item"] = to_surface(alert_bubble(mark=(214, 150, 20), fill=(255, 248, 214)))
    t["flowers_red"] = to_surface(flowers((230, 70, 70), 21))
    t["flowers_yellow"] = to_surface(flowers((250, 210, 60), 22))
    t["flowers_white"] = to_surface(flowers((248, 248, 248), 23))
    t["pebbles"] = to_surface(scatter([(170, 140, 96), (140, 110, 74)], 6, 31, 2))
    t["snowtuft"] = to_surface(scatter([(255, 255, 255), (214, 226, 244)], 6, 32, 2))
    t["bones"] = to_surface(bones())
    t["embers"] = to_surface(embers())
    t["shards"] = to_surface(scatter([(190, 150, 250), (150, 110, 230)], 5, 33, 1))
    t["moss"] = to_surface(scatter([(78, 130, 62), (100, 160, 76)], 9, 34, 2))
    t["mushroom"] = to_surface(mushroom_small(35))
    t["frost"] = to_surface(scatter([(240, 250, 255), (200, 230, 250)], 8, 36, 1))
    t["rubble"] = to_surface(scatter([(90, 82, 74), (130, 120, 108)], 6, 37, 2))
    t["exit"] = to_surface(exit_glow())
    t["walltorch"] = to_surface(walltorch())
    t["door_closed"] = to_surface(door(False))
    t["door_open"] = to_surface(door(True))
    # objects
    t["tree"] = [to_surface(tree(s)) for s in (3, 4, 5)]
    t["pine"] = to_surface(pine())
    t["cactus"] = to_surface(cactus())
    t["deadtree"] = to_surface(deadtree())
    t["crystal"] = to_surface(crystal())
    t["crystal_small"] = to_surface(crystal(True))
    t["bush"] = to_surface(bush())
    t["icespike"] = to_surface(icespike())
    t["mushroom_big"] = to_surface(mushroom_big())
    t["pillar"] = to_surface(pillar())
    t["urn"] = to_surface(urn())
    t["vent"] = to_surface(vent())
    for b in ROCK_PALETTES:
        t["rock_" + b] = [to_surface(rock(b, s)) for s in (5, 6, 7)]
        t["outcrop_" + b] = to_surface(outcrop(b))
        t["gate_" + b] = to_surface(gate(b))
    for b in CLIFF_PALETTES:
        t["cliff_" + b] = [to_surface(cliff(b, v, s)) for v in (0, 1, 2) for s in (0, 1)]
        t["stairs_" + b] = to_surface(stairs(b))
    t["waterfall"] = [to_surface(a) for a in waterfall_frames()]
    for r in RARITY_GEMS:
        t["chest_" + r] = to_surface(chest(r))
        t["chest_open_" + r] = to_surface(chest(r, True))
    t["shadow"] = to_surface(shadow())
    t["shadow_big"] = to_surface(shadow(15, 6))
    import make_village                      # villages, houses and their interiors
    for k, v in make_village.village_tiles().items():
        t[k] = [to_surface(a) for a in v] if isinstance(v, list) else to_surface(v)
    return t


def contact_sheet(tiles, scale=3):
    items = []
    for name, v in sorted(tiles.items()):
        for i, s in enumerate(v if isinstance(v, list) else [v]):
            items.append((f"{name}" if not isinstance(v, list) else f"{name}{i}", s))
    cell = 50 * scale // 3 + 0
    cols = 12
    rows = (len(items) + cols - 1) // cols
    sheet = pygame.Surface((cols * cell * 1, rows * (cell + 14)))
    sheet.fill((24, 20, 18))
    font = pygame.font.SysFont("consolas", 10)
    for i, (n, s) in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * (cell + 14)
        big = pygame.transform.scale(s, (s.get_width() * 2, s.get_height() * 2))
        sheet.blit(big, (x + (cell - big.get_width()) // 2, y + 2))
        sheet.blit(font.render(n[:13], True, (200, 190, 160)), (x + 2, y + cell))
    return sheet


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    tiles = build_tileset()
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for name, v in tiles.items():
        for i, s in enumerate(v if isinstance(v, list) else [v]):
            fname = f"{name}_{i}.png" if isinstance(v, list) else f"{name}.png"
            pygame.image.save(s, os.path.join(OUT, fname)); n += 1
    combos = (("Mage", "Azure", "Fair", "Golden", "Human"), ("Mage", "Teal", "Moonlit", "Snow", "Elf"),
              ("Brawler", "Crimson", "Moss", "Raven", "Orc"), ("Knight", "Forest", "Tan", "Auburn", "Dwarf"),
              ("Knight", "Slate", "Bone", "Ash", "Skeleton"), ("Brawler", "Ember", "Lime", "Raven", "Goblin"))
    looks = [{"class": cls, "color": OUTFIT_COLORS[col], "skin": SKIN_TONES[skin],
              "hair": HAIR_COLORS[hair], "race": race} for cls, col, skin, hair, race in combos]
    looks += [{"class": "Brawler" if i % 3 == 1 else "Knight" if i % 3 == 2 else "Mage", "color": OUTFIT_COLORS["Azure"],
               "skin": SKIN_TONES["Fair"], "hair": HAIR_COLORS["Auburn"], "race": "Human", "style": st, "hood": False}
              for i, st in enumerate(HAIRSTYLES)]
    strip = pygame.Surface((16 * 12, 22 * len(looks)), pygame.SRCALPHA)
    for row, lk in enumerate(looks):
        pf = player_frames(lk)
        for k, d in enumerate(("down", "up", "left", "right")):
            for f in range(3):
                strip.blit(pf[d][f], ((k * 3 + f) * 16, row * 22))
    pygame.image.save(pygame.transform.scale(strip, (16 * 12 * 4, strip.get_height() * 4)), os.path.join(OUT, "_player_preview.png"))
    pygame.image.save(contact_sheet(tiles), os.path.join(OUT, "_sheet.png"))
    print(f"Wrote {n} tiles to {OUT} (+ _sheet.png, _player_preview.png)")


if __name__ == "__main__":
    main()
