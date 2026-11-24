"""
Enemy sprites: overworld walkers (16x22, drawn at 3x on the map) and battle sprites
(48x48, drawn at 3x in battle, bosses at 4x).

Every sprite takes an `accent` colour — the enemy's element — so a Fire slime is orange,
a Water skeleton's eyes burn blue and an Earth goblin wears brown. Bosses add a crown.
The game builds these on demand and caches them; run this file to write a review sheet:

    python make_monsters.py
"""
import os

import numpy as np
import pygame

from make_tiles import blank, put, blob, outline, mix, shade, to_surface, from_map, _LEGS_FRONT, _LEGS_SIDE

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ["Goblin", "Skeleton", "Orc", "Slime", "Shadow Lurker"]
GOLD = [(150, 104, 20), (214, 166, 40), (250, 214, 80), (255, 244, 170)]
METAL = [(70, 76, 92), (112, 120, 140), (164, 172, 190), (220, 226, 238)]
OUT = (24, 18, 28)


def accent_palette(c):
    c = tuple(int(v) for v in c[:3])
    if sum(c) < 150:
        c = mix(c, (170, 170, 190), 0.4)
    return [shade(c, 0.42), shade(c, 0.68), c, mix(c, (255, 255, 255), 0.38)]


# ---------------------------------------------------------------------------- overworld

GOBLIN = {
    "down": ["................", ".....oooooo.....", "....oGGGGGGo....", ".o.oGGGGGGGGo.o.",
             "oGooGGGGGGGGooGo", "ogGGGYYGGYYGGGgo", ".ooGGYkGGYkGGoo.", "...oGGGGGGGGo...",
             "...ogGwGGwGgo...", "....oggggggo....", "...oXXXXXXXXo...", "..oGXXXXXXXXGo..",
             "..oGoXXBBXXoGo..", "..ooXXXXXXXXoo..", "...oxXXXXXXxo...", "...oxxxxxxxxo..."],
    "up": ["................", ".....oooooo.....", "....oGGGGGGo....", ".o.oGGGGGGGGo.o.",
           "oGooGGGGGGGGooGo", "ogGGGGGGGGGGGGgo", ".ooGGGGGGGGGGoo.", "...oGGGGGGGGo...",
           "...ogGGGGGGgo...", "....oggggggo....", "...oXXXXXXXXo...", "..oGXXXXXXXXGo..",
           "..oGXXXXXXXXGo..", "..ooXXXXXXXXoo..", "...oxXXXXXXxo...", "...oxxxxxxxxo..."],
    "right": ["................", "......ooooo.....", ".....oGGGGGo....", "..o.oGGGGGGGo...",
              ".oGooGGGGGGGGo..", ".ogGGGGGGGYYGGo.", "..ooGGGGGGYkGGGo", "....oGGGGGGGGoo.",
              "....ogGGGGwGo...", ".....oggggggo...", "....oXXXXXXo....", "...oGXXXXXXXo...",
              "...oGXXXBBXXo...", "....oXXXXXXGo...", "....oxXXXXxo....", "....oxxxxxxo...."],
}
SKELETON = {
    "down": ["................", ".....oooooo.....", "....oWWWWWWo....", "...oWWWWWWWWo...",
             "...oWWWWWWWWo...", "...oWkkWWkkWo...", "...oWkXWWXkWo...", "...oWWWwwWWWo...",
             "....owkwkwko....", ".....oWWWWo.....", "...ooowWWwooo...", "..oWokWkkWkoWo..",
             "..oWowWWWWwoWo..", "..oWokWkkWkoWo..", "...ooXXXXXXoo...", "....oxXXXXxo...."],
    "up": ["................", ".....oooooo.....", "....oWWWWWWo....", "...oWWWWWWWWo...",
           "...oWWWWWWWWo...", "...oWWWWWWWWo...", "...owWWWWWWwo...", "...oWWWWWWWWo...",
           "....owWWWWwo....", ".....oWWWWo.....", "...ooowkkwooo...", "..oWowWkkWwoWo..",
           "..oWowWkkWwoWo..", "..oWowWkkWwoWo..", "...ooXXXXXXoo...", "....oxXXXXxo...."],
    "right": ["................", "......ooooo.....", ".....oWWWWWo....", "....oWWWWWWWo...",
              "....oWWWWWWWWo..", "....oWWWWWkkWo..", "....oWWWWWkXWo..", "....owWWWWWWwo..",
              ".....owWkwkwo...", "......oWWWWo....", "....oooWWooo....", "....oWkWkWo.....",
              "...oWowWWwo.....", "....oWkWkWo.....", "....oXXXXXo.....", "....oxXXXxo....."],
}
ORC = {
    "down": ["......oooo......", "....ooMMMMoo....", "...oMMXXXXMMo...", "...oMMMMMMMMo...",
             "..ooGGGGGGGGoo..", "..oGGYGGGGYGGo..", "..oGGkGGGGkGGo..", "..oGGGGGGGGGGo..",
             "..ogwGGGGGGwgo..", "...ogwggggwgo...", ".ooMoggggggoMoo.", "oMMXoXXXXXXoXMMo",
             "oGgoXXXBBXXXogGo", ".ooxXXXXXXXXxoo.", "...oxXXXXXXxo...", "...oxxxxxxxxo..."],
    "up": ["......oooo......", "....ooMMMMoo....", "...oMMMMMMMMo...", "...oMMMMMMMMo...",
           "..ooMMMMMMMMoo..", "..oGMMMMMMMMGo..", "..oGGGGGGGGGGo..", "..oGGGGGGGGGGo..",
           "..ogGGGGGGGGgo..", "...ogggggggo....", ".ooMoggggggoMoo.", "oMMXoXXXXXXoXMMo",
           "oGgoXXXXXXXXogGo", ".ooxXXXXXXXXxoo.", "...oxXXXXXXxo...", "...oxxxxxxxxo..."],
    "right": [".......oooo.....", ".....ooMMMMo....", "....oMMXXXXMo...", "....oMMMMMMMMo..",
              "...ooMGGGGGGGo..", "...oMGGGGGYGGo..", "...oGGGGGGkGGGo.", "...oGGGGGGGGGGo.",
              "...ogGGGGGGGwgo.", "....ogggggwggo..", "...ooMoggggoo...", "..oMMXoXXXXXo...",
              "..oGgoXXXBBXo...", "...ooxXXXXXXo...", "....oxXXXXXo....", "....oxxxxxxo...."],
}
SLIME = ["................"] * 6 + [
    "......oooo......", "....ooXXXXoo....", "...oXhhXXXXXo...", "..oXhXXXXXXXXo..",
    "..oXXXXXXXXXXo..", ".oXXEEXXXXEEXXo.", ".oXXEkXXXXEkXXo.", ".oXXXXXXXXXXXXo.",
    ".oXXXXXkkXXXXXo.", ".oxXXXXXXXXXXxo.", ".oxxXXXXXXXXxxo.", "..oxxxxxxxxxxo..",
    "...oooooooooo...", "................"]
SHADOW = ["................", "......oooo......", "....oollllo.....", "...olDDDDDDo....",
          "..olDDDDDDDDo...", "..oDDddddddDDo..", "..oDdkkkkkkdDo..", "..oDdkXkkXkdDo..",
          "..oDdkkkkkkdDo..", "..oDDdkkkkdDDo..", ".olDDDDDDDDDDDo.", ".oDDDDDDDDDDDDo.",
          "oDDdDDDDDDDDdDDo", "olDdDDDDDDDDdDlo", ".oDdDDDDDDDDdDo.", ".oddDDdDDdDDddo.",
          "..odDdoDDodDdo..", "...odo.od.odo...", "....o...o...o...", "................"]


def _crown(a):
    """Put a small gold crown above the topmost row of the sprite."""
    rows = np.nonzero(a[..., 3].any(axis=1))[0]
    cols = np.nonzero(a[..., 3].any(axis=0))[0]
    if not len(rows):
        return
    top, cx = int(rows[0]), int((cols[0] + cols[-1]) // 2)
    for dx in (-2, 0, 2):
        put(a, cx + dx, top - 3, GOLD[2])
    for dx in range(-2, 3):
        put(a, cx + dx, top - 2, GOLD[2] if dx else (220, 60, 60))
        put(a, cx + dx, top - 1, GOLD[1])
    outline(a, OUT)


def overworld_frames(kind, accent, boss=False):
    """{"down"/"up"/"left"/"right": [stand, step_a, step_b]} of 16x22 surfaces."""
    pal = accent_palette(accent)
    X, x, h = pal[2], pal[1], pal[3]
    out = {}
    if kind in ("Goblin", "Skeleton", "Orc"):
        maps = {"Goblin": GOBLIN, "Skeleton": SKELETON, "Orc": ORC}[kind]
        skin = {"Goblin": ((108, 162, 70), (76, 120, 50)), "Orc": ((116, 138, 94), (84, 102, 68)),
                "Skeleton": ((228, 224, 206), (176, 170, 154))}[kind]
        colors = {"o": OUT, "G": skin[0], "g": skin[1], "W": skin[0], "w": skin[1],
                  "Y": (250, 222, 80) if kind == "Goblin" else (236, 64, 44), "k": (26, 18, 24),
                  "X": X, "x": x, "B": (92, 62, 40), "M": METAL[2],
                  "P": skin[1] if kind != "Orc" else (74, 62, 52),
                  "b": (60, 44, 30) if kind != "Skeleton" else skin[1], "E": (30, 22, 30)}
        if kind == "Skeleton":
            colors["X"] = mix(X, (255, 255, 255), 0.25)      # the glow in the sockets
            colors["x"] = shade(X, 0.6)
        for d, legs in (("down", _LEGS_FRONT), ("up", _LEGS_FRONT), ("right", _LEGS_SIDE)):
            frames = []
            for f in range(3):
                a = np.zeros((22, 16, 4), np.uint8)
                a[2:] = from_map(maps[d] + legs[f], colors)
                if f:
                    a = np.roll(a, 1, axis=0); a[0] = 0
                if boss:
                    _crown(a)
                frames.append(to_surface(a))
            out[d] = frames
    elif kind == "Slime":
        colors = {"o": OUT, "X": X, "x": pal[1], "h": h, "E": (250, 250, 250), "k": (26, 18, 24)}
        for d in ("down", "up", "right"):
            rows = [r for r in SLIME]
            if d == "up":
                rows = [r.replace("E", "X").replace("k", "X") for r in rows]
            elif d == "right":
                rows = [r if "E" not in r and "kk" not in r else r[:2] + r[2:14][-2:] + r[2:14][:-2] + r[14:]
                        for r in rows]
            base = np.zeros((22, 16, 4), np.uint8)
            base[2:] = from_map(rows, colors)
            frames = []
            for f in range(3):
                a = base.copy()
                if f == 1:                                    # squash
                    body = a[8:21].copy()
                    a[8:21] = 0
                    a[9:21] = body[1:]
                elif f == 2:                                  # stretch
                    a = np.roll(a, -1, axis=0); a[-1] = 0
                if boss:
                    _crown(a)
                frames.append(to_surface(a))
            out[d] = frames
    else:                                                     # Shadow Lurker floats
        colors = {"o": OUT, "D": (46, 36, 68), "d": (30, 22, 46), "l": (76, 62, 104),
                  "k": (6, 4, 10), "X": mix(X, (255, 255, 255), 0.3)}
        for d in ("down", "up", "right"):
            rows = list(SHADOW)
            if d == "up":
                rows = [r.replace("k", "d").replace("X", "d") if 5 <= i <= 9 else r for i, r in enumerate(rows)]
            elif d == "right":
                face = {5: "..oDDDDdddddDo..", 6: "..oDDDDdkkkkdo..", 7: "..oDDDDdkkXkdo..",
                        8: "..oDDDDdkkkkdo..", 9: "..oDDDDDdkkdDo.."}
                rows = [face.get(i, r) for i, r in enumerate(rows)]
            base = np.zeros((22, 16, 4), np.uint8)
            base[2:] = from_map(rows, colors)
            frames = []
            for f, dy in enumerate((0, -1, 1)):
                a = np.roll(base, dy, axis=0)
                if dy < 0: a[-1] = 0
                if dy > 0: a[0] = 0
                if boss:
                    _crown(a)
                frames.append(to_surface(a))
            out[d] = frames
    out["left"] = [pygame.transform.flip(s, True, False) for s in out["right"]]
    return out


# ---------------------------------------------------------------------------- battle

def _layer(a, b):
    m = b[..., 3] > 0
    a[m] = b[m]
    return a


def _poly(a, pts, col, width=0):
    s = to_surface(a)
    pygame.draw.polygon(s, col, pts, width)
    return _from(s)


def _line(a, p0, p1, col, width=1):
    s = to_surface(a)
    pygame.draw.line(s, col, p0, p1, width)
    return _from(s)


def _from(s):
    """The surface's pixels as an (h, w, 4) array. Via bytes rather than surfarray so it
    works with any pygame / numpy pair (Android's pygame is 2.1.0)."""
    tobytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    return np.frombuffer(tobytes(s, "RGBA"), np.uint8).reshape(s.get_height(), s.get_width(), 4).copy()


def _b(ellipses, pal, seed=1, noise=0.05):
    return blob(48, 48, ellipses, pal, np.random.default_rng(seed), noise=noise)


def _battle_crown(a, cx, top):
    pts = [(cx - 9, top + 8), (cx - 9, top + 1), (cx - 5, top + 5), (cx, top - 2), (cx + 5, top + 5),
           (cx + 9, top + 1), (cx + 9, top + 8)]
    a = _poly(a, pts, GOLD[2])
    a = _poly(a, pts, GOLD[0], 1)
    a = _line(a, (cx - 8, top + 7), (cx + 8, top + 7), GOLD[1], 2)
    for gx, col in ((cx - 5, (90, 160, 255)), (cx, (230, 50, 60)), (cx + 5, (90, 220, 120))):
        put(a, gx, top + 5, col); put(a, gx, top + 6, shade(col, 0.7))
    put(a, cx, top - 1, GOLD[3])
    return a


def battle_goblin(acc):
    pal = accent_palette(acc)
    skin = [(46, 82, 34), (74, 122, 50), (106, 162, 70), (146, 196, 96)]
    a = blank(48, 48)
    a = _layer(a, _b([(18, 42, 4, 5), (30, 42, 4, 5)], skin, 2))                 # legs
    a = _layer(a, _b([(17, 46.5, 5, 2), (31, 46.5, 5, 2)], [(40, 28, 20), (70, 48, 30)], 3))
    a = _layer(a, _b([(24, 33, 10, 8.5)], pal, 4))                               # tunic
    for x in range(15, 34):
        put(a, x, 36, (92, 62, 40)); put(a, x, 37, (70, 46, 30))
    a = _layer(a, _b([(12, 32, 4, 6), (36, 31, 4, 6)], skin, 5))                 # arms
    a = _poly(a, [(38, 28), (41, 27), (46, 12), (44, 11)], METAL[2])              # dagger
    a = _line(a, (39, 27), (45, 12), METAL[3])
    a = _line(a, (35, 29), (42, 26), (110, 74, 44), 2)
    a = _poly(a, [(14, 15), (1, 6), (6, 18)], skin[2])                            # ears
    a = _poly(a, [(34, 15), (47, 6), (42, 18)], skin[1])
    a = _layer(a, _b([(24, 17, 12, 10), (24, 21, 9, 6)], skin, 6))               # head
    for (ex, ey) in ((19, 17), (29, 17)):
        a = _layer(a, _b([(ex, ey, 3.2, 2.6)], [(200, 150, 30), (250, 210, 60), (255, 240, 140)], 7, 0.02))
        put(a, ex, ey, (20, 14, 14)); put(a, ex + 1, ey, (20, 14, 14))
    a = _line(a, (15, 13), (21, 15), skin[0], 2); a = _line(a, (33, 13), (27, 15), skin[0], 2)
    a = _line(a, (18, 23), (30, 23), (40, 20, 20), 2)
    for x in (19, 22, 26, 29):
        put(a, x, 22, (244, 238, 220))
    outline(a, OUT)
    return a, 7


def battle_skeleton(acc):
    pal = accent_palette(acc)
    bone = [(120, 114, 98), (178, 172, 154), (220, 216, 198), (246, 244, 232)]
    a = blank(48, 48)
    for x0 in (19, 28):                                                            # legs
        a = _line(a, (x0, 38), (x0, 46), bone[2], 3)
        a = _line(a, (x0 - 2, 47), (x0 + 3, 47), bone[1], 2)
    a = _layer(a, _b([(24, 37, 7, 3)], bone, 3))                                  # pelvis
    a = _poly(a, [(15, 34), (33, 34), (36, 41), (30, 39), (26, 44), (22, 40), (16, 42)], pal[2])   # sash
    a = _poly(a, [(15, 34), (33, 34), (36, 41), (30, 39), (26, 44), (22, 40), (16, 42)], pal[0], 1)
    a = _line(a, (24, 22), (24, 35), bone[2], 3)                                  # spine
    for i, y in enumerate((25, 28, 31)):
        w = 9 - i
        a = _line(a, (24 - w, y + 1), (24 + w, y + 1), bone[2], 2)
        a = _line(a, (24 - w, y + 2), (24 + w, y + 2), bone[0], 1)
    a = _line(a, (13, 23), (35, 23), bone[3], 3)                                  # shoulders
    a = _line(a, (13, 24), (10, 37), bone[2], 3)                                  # arms
    a = _line(a, (35, 24), (38, 34), bone[2], 3)
    a = _poly(a, [(38, 34), (41, 35), (45, 4), (43, 3)], METAL[2])               # sword
    a = _line(a, (40, 34), (44, 5), METAL[3])
    a = _line(a, (35, 33), (45, 35), GOLD[1], 2)
    a = _layer(a, _b([(24, 12, 9.5, 9), (24, 17, 7, 5)], bone, 6))                # skull
    for x in range(19, 30):
        put(a, x, 19, bone[0] if x % 2 else bone[3])
    for (ex, ey) in ((20, 12), (28, 12)):
        a = _layer(a, _b([(ex, ey, 3, 3)], [(10, 6, 12), (20, 14, 24)], 8, 0.01))
        glow = mix(pal[2], (255, 255, 255), 0.35)
        put(a, ex, ey, glow); put(a, ex - 1, ey, pal[2]); put(a, ex, ey - 1, pal[2])
    a = _poly(a, [(23, 15), (25, 15), (24, 17)], (24, 18, 26))
    outline(a, OUT)
    return a, 3


def battle_orc(acc):
    pal = accent_palette(acc)
    skin = [(58, 74, 46), (88, 108, 66), (118, 140, 92), (152, 172, 118)]
    a = blank(48, 48)
    a = _layer(a, _b([(17, 42, 5, 5), (31, 42, 5, 5)], [(48, 40, 34), (74, 62, 52), (98, 84, 70), (120, 104, 86)], 2))
    a = _layer(a, _b([(16, 46.5, 6, 2), (32, 46.5, 6, 2)], [(30, 24, 20), (56, 44, 36)], 3))
    a = _layer(a, _b([(24, 32, 13, 9)], skin, 4))                                # torso
    a = _layer(a, _b([(24, 33, 10, 7)], METAL, 5))                               # chest plate
    a = _line(a, (15, 30), (33, 30), pal[2], 2)
    a = _layer(a, _b([(24, 33, 2.5, 2.5)], pal, 9))                              # gem
    a = _layer(a, _b([(7, 34, 4.5, 7), (41, 33, 4.5, 7)], skin, 6))              # arms
    a = _line(a, (43, 44), (43, 6), (104, 70, 42), 3)                            # axe
    a = _poly(a, [(43, 7), (47, 4), (48, 18), (43, 15)], METAL[2])
    a = _poly(a, [(43, 7), (37, 5), (38, 17), (43, 15)], METAL[1])
    a = _layer(a, _b([(10, 24, 6.5, 5), (38, 24, 6.5, 5)], METAL, 7))           # pauldrons
    for sx in (8, 12, 36, 40):
        a = _poly(a, [(sx - 1, 20), (sx + 1, 20), (sx, 16)], METAL[3])
    a = _layer(a, _b([(24, 15, 10, 9)], skin, 8))                                # head
    a = _layer(a, _b([(24, 9, 10.5, 6)], METAL, 10))                             # helmet
    a = _poly(a, [(15, 8), (9, 0), (17, 5)], (236, 228, 206))                   # horns
    a = _poly(a, [(33, 8), (39, 0), (31, 5)], (206, 198, 176))
    a = _line(a, (14, 11), (34, 11), pal[2], 2)
    for ex in (20, 28):
        put(a, ex, 15, (240, 60, 40)); put(a, ex + 1, 15, (240, 60, 40)); put(a, ex, 16, (150, 30, 24))
    a = _line(a, (17, 13), (22, 14), skin[0], 2); a = _line(a, (31, 13), (26, 14), skin[0], 2)
    a = _line(a, (19, 21), (29, 21), (30, 20, 18), 2)
    a = _poly(a, [(19, 21), (21, 21), (20, 17)], (246, 240, 220))               # tusks
    a = _poly(a, [(27, 21), (29, 21), (28, 17)], (246, 240, 220))
    outline(a, OUT)
    return a, 0


def battle_slime(acc):
    pal = accent_palette(acc)
    a = blank(48, 48)
    a = _layer(a, _b([(24, 32, 20, 13), (24, 24, 13, 10)], pal, 4, 0.03))      # body
    for (dx, dy, r) in ((12, 44, 3), (35, 44.5, 2.5)):                           # drips
        a = _layer(a, _b([(dx, dy, r, r)], pal, 5))
    for (bx, by, r) in ((33, 37, 2.2), (14, 35, 1.6), (29, 41, 1.3)):           # bubbles
        a = _layer(a, _b([(bx, by, r, r)], [pal[2], pal[3], (255, 255, 255)], 6, 0.0))
    for (hx, hy) in ((15, 21), (16, 20), (14, 23), (17, 19)):                    # gloss
        put(a, hx, hy, (255, 255, 255))
    for ex in (17, 31):
        a = _layer(a, _b([(ex, 29, 3.6, 4.6)], [(200, 200, 210), (255, 255, 255)], 7, 0.0))
        a = _layer(a, _b([(ex + 0.5, 30, 1.8, 2.6)], [(16, 10, 20), (30, 22, 36)], 8, 0.0))
        put(a, ex - 1, 27, (255, 255, 255))
    a = _layer(a, _b([(24, 37, 4, 2.2)], [(40, 10, 20), (70, 20, 34)], 9, 0.0))
    outline(a, OUT)
    return a, 14


def battle_shadow(acc):
    pal = accent_palette(acc)
    robe = [(16, 10, 26), (34, 26, 52), (54, 42, 80), (82, 66, 116)]
    a = blank(48, 48)
    a = _poly(a, [(12, 20), (36, 20), (42, 44), (36, 40), (31, 46), (24, 41), (17, 46), (12, 40), (6, 44)],
              robe[1])                                                            # robe
    a = _poly(a, [(12, 20), (24, 20), (24, 41), (17, 46), (12, 40), (6, 44)], robe[2])
    for x0, x1 in ((10, 2), (38, 46)):                                            # claws
        a = _line(a, (x0, 26), (x1 + (2 if x1 < 10 else -2), 33), robe[2], 4)
        for k in (-1, 1, 3):
            a = _line(a, (x1 + (2 if x1 < 10 else -2), 33), (x1 + k * (1 if x1 < 10 else -1), 38), (200, 196, 210), 1)
    a = _layer(a, _b([(24, 14, 12, 12), (24, 20, 10, 6)], robe, 6))             # hood
    a = _layer(a, _b([(24, 16, 7, 7)], [(2, 0, 4), (8, 4, 12)], 7, 0.0))         # void face
    for ex in (21, 27):
        glow = mix(pal[2], (255, 255, 255), 0.4)
        put(a, ex, 16, glow); put(a, ex + 1, 16, glow); put(a, ex, 17, pal[2]); put(a, ex + 1, 17, pal[2])
        put(a, ex - 1, 16, pal[1]); put(a, ex + 2, 16, pal[1])
    outline(a, OUT)
    return a, 4


_BATTLE = {"Goblin": battle_goblin, "Skeleton": battle_skeleton, "Orc": battle_orc,
           "Slime": battle_slime, "Shadow Lurker": battle_shadow}


def battle_sprite(kind, accent, boss=False):
    """48x48 front-facing battle sprite (crowned for bosses)."""
    a, head_top = _BATTLE.get(kind, battle_slime)(accent)
    if boss:
        a = np.vstack([np.zeros((8, 48, 4), np.uint8), a])[:48 + 8]
        a = _battle_crown(a, 24, head_top - 1)
        a = a[:, :]
    return to_surface(a)


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    accents = [(255, 165, 0), (0, 0, 255), (139, 69, 19), (255, 255, 0), (128, 0, 128)]
    sheet = pygame.Surface((5 * 160, 5 * 230 // 1), pygame.SRCALPHA)
    sheet = pygame.Surface((5 * 170, 2 * 300))
    sheet.fill((40, 52, 40))
    for i, kind in enumerate(KINDS):
        for row, boss in enumerate((False, True)):
            spr = battle_sprite(kind, accents[i], boss)
            big = pygame.transform.scale(spr, (spr.get_width() * 3, spr.get_height() * 3))
            sheet.blit(big, (i * 170 + 4, row * 300))
            fr = overworld_frames(kind, accents[i], boss)
            for k, d in enumerate(("down", "up", "left", "right")):
                s = pygame.transform.scale(fr[d][0], (48, 66))
                sheet.blit(s, (i * 170 + 4 + (k % 2) * 52 + 50, row * 300 + 170 + (k // 2) * 0) if False else (i * 170 + k * 40, row * 300 + 180))
    out = os.path.join(HERE, "tiles", "_sheet_monsters.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pygame.image.save(sheet, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
