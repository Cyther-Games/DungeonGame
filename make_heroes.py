"""
Detailed 48x48 hero sprites for the battle screen (seen from behind) and the character
screen (seen from the front), built from the same look as the overworld walker:

    look = {"class": "Mage"/"Brawler"/"Knight", "race": "Human"/"Elf"/…,
            "color": outfit RGB, "skin": RGB, "hair": RGB, "orb": RGB (optional, the element)}

Run directly to write a review sheet of every class x race:  python make_heroes.py
"""
import os

import numpy as np
import pygame

from make_tiles import blank, put, outline, mix, shade, to_surface
from make_monsters import _b, _poly, _line, _layer, accent_palette, METAL, GOLD, OUT

HERE = os.path.dirname(os.path.abspath(__file__))


def _pal(c, lo=0.55, hi=0.3):
    c = tuple(int(v) for v in c[:3])
    return [shade(c, lo), shade(c, (1 + lo) / 2), c, mix(c, (255, 255, 255), hi)]


def _ears(a, race, skin, head_cy, front):
    """Elf / goblin ears out of the sides of the head."""
    if race not in ("Elf", "Goblin"):
        return a
    sp = _pal(skin)
    reach = 10 if race == "Goblin" else 7
    lift = 3 if race == "Goblin" else 6
    for side in (-1, 1):
        root = 24 + side * 8
        tip = (24 + side * (8 + reach), head_cy - lift)
        a = _poly(a, [(root, head_cy - 2), tip, (root, head_cy + 3)], sp[2] if side < 0 else sp[1])
        a = _line(a, (root + side, head_cy), (tip[0] - side * 2, tip[1] + 2), sp[0], 1)
    return a


def _face(a, race, skin, hair, cx, cy):
    """Eyes, mouth and race details for the front view."""
    dark = (28, 20, 30)
    if race == "Skeleton":
        for ex in (cx - 3, cx + 3):
            a = _layer(a, _b([(ex, cy, 2.2, 2.2)], [(8, 4, 10), (20, 14, 24)], 3, 0.0))
        a = _poly(a, [(cx - 1, cy + 3), (cx + 1, cy + 3), (cx, cy + 5)], dark)
        for x in range(cx - 3, cx + 4):
            put(a, x, cy + 6, dark if x % 2 else (250, 248, 236))
        return a
    for ex in (cx - 4, cx + 3):                    # 2x2 eyes with a catch-light
        for dx in (0, 1):
            put(a, ex + dx, cy, dark); put(a, ex + dx, cy + 1, dark)
        put(a, ex + (0 if ex < cx else 1), cy, (250, 250, 250))
    put(a, cx - 1, cy + 4, shade(skin, 0.6)); put(a, cx, cy + 4, shade(skin, 0.6)); put(a, cx + 1, cy + 4, shade(skin, 0.6))
    if race == "Orc":
        for tx in (cx - 2, cx + 2):
            put(a, tx, cy + 4, (246, 240, 220)); put(a, tx, cy + 3, (246, 240, 220))
    if race == "Dwarf":
        hp = _pal(hair)
        a = _layer(a, _b([(cx, cy + 6, 6.5, 5), (cx - 4, cy + 4, 3, 3), (cx + 4, cy + 4, 3, 3)], hp, 7))
        put(a, cx, cy + 4, shade(hair, 0.4)); put(a, cx - 1, cy + 4, shade(hair, 0.4))
    return a


# ---------------------------------------------------------------------------- hair
# A bare head (hood down / helmet off) with one of the ten hairstyles. Heads sit at
# HEAD_CY so spikes, buns and crests have room above them on the 48px canvas.
HEAD_CY = 13


def _hair_behind(a, look, front, cy=HEAD_CY):
    """Hair that falls behind the shoulders: drawn before the body in the front view."""
    if not front or not look.get("bare"):
        return a
    hp = _pal(look["hair"]); st = look.get("style", "Short")
    if st == "Long":
        a = _layer(a, _b([(24, cy + 9, 11, 12.5)], hp, 21))
    elif st == "Ponytail":
        a = _layer(a, _b([(33.5, cy + 6, 3, 6.5)], hp, 22))
    return a


def _spike_crest(a, hp, cy, nape=False):
    """Spiky hair: locks of uneven length radiating out of the whole crown and swept
    outward, the back ones darker so they read as layered hair rather than a row of
    points on a band."""
    import math
    cx0, cy0, rx, ry = 24, cy - 2, 8.4, 7.4
    # (angle from the head's centre, length, half-width at the root, sweep) — degrees, -90 = up
    locks = [(-176, 5, 2.6, -16), (-152, 9, 3.2, -18), (-128, 12, 3.4, -14), (-104, 9, 3.2, -6),
             (-84, 13, 3.4, 4), (-60, 10, 3.3, 14), (-36, 9, 3.1, 18), (-8, 5, 2.6, 16)]
    if nape:          # from behind, a few more stick out low at the sides and the neck
        locks += [(160, 6, 2.6, 18), (20, 6, 2.6, -18), (118, 5, 2.4, 10), (62, 5, 2.4, -10)]
    for layer in (0, 1):                        # back row first (darker), then the front row
        for i, (ang, ln, w, sweep) in enumerate(locks):
            if i % 2 != layer:
                continue
            t = math.radians(ang)
            dt = w / ((rx + ry) / 2)
            base = [(cx0 + rx * math.cos(t + s * dt), cy0 + ry * math.sin(t + s * dt)) for s in (-1, 1)]
            r = (rx + ry) / 2 + ln
            tip = (cx0 + r * math.cos(t + math.radians(sweep)), cy0 + r * math.sin(t + math.radians(sweep)))
            inner = (cx0 + 2 * math.cos(t), cy0 + 2 * math.sin(t))
            col = hp[1] if layer == 0 else (hp[2] if math.cos(t) < 0.35 else hp[1])
            a = _poly(a, [inner, base[0], tip, base[1]], col)
            if layer == 1 and math.cos(t) < 0.35 and ln >= 9:     # a lit edge on the bigger locks
                mid = ((base[0][0] + base[1][0]) / 2, (base[0][1] + base[1][1]) / 2)
                a = _line(a, mid, ((mid[0] * 2 + tip[0]) / 3, (mid[1] * 2 + tip[1]) / 3), hp[3], 1)
    return a


def _bare_head(a, look, front, cy=HEAD_CY):
    """Skull, hair and face for the hood-down / helmet-off look."""
    st = look.get("style", "Short")
    hp = _pal(look["hair"]); sp = _pal(look["skin"]); op = accent_palette(look["color"])
    a = _layer(a, _b([(24, cy + 8, 3.2, 2.6)], sp, 30))                       # neck
    if st == "Long" and not front:            # hair spills down the back, under the skull
        a = _layer(a, _b([(24, cy + 9, 10.5, 12)], hp, 31))
    if st == "Ponytail" and not front:
        a = _layer(a, _b([(24, cy + 11, 3.4, 8)], hp, 32))
    if st == "Twin Tails":                     # tails hang beside the head in either view
        a = _layer(a, _b([(13, cy + 8, 3.2, 7.5), (35, cy + 8, 3.2, 7.5)], hp, 33))
    stubble = [mix(c, look["skin"], 0.55) for c in hp]
    a = _layer(a, _b([(24, cy, 8.5, 8.5)], sp, 34))                           # skull

    if front:
        cap = {"Shaggy": [(24, cy - 2, 10, 7.6)], "Bob": [(24, cy - 1, 10, 8.6)],
               "Mohawk": [(24, cy - 3, 8.8, 6)], "Spiky": [(24, cy - 3, 10, 7)],
               "Long": [(24, cy - 2, 9.8, 7.5)]}.get(st, [(24, cy - 3, 9.4, 6.4)])
        if st == "Spiky":
            a = _spike_crest(a, hp, cy)
        a = _layer(a, _b(cap, stubble if st == "Mohawk" else hp, 35))
        if st == "Bob":                          # straight-cut sides down to the jaw
            a = _poly(a, [(14, cy - 1), (18.5, cy - 1), (18.5, cy + 7), (14, cy + 7)], hp[2])
            a = _poly(a, [(29.5, cy - 1), (34, cy - 1), (34, cy + 7), (29.5, cy + 7)], hp[1])
        face = (24, cy + 3, 6.3, 5.8) if st in ("Bob", "Shaggy", "Long") else (24, cy + 3, 6.8, 6.2)
        a = _layer(a, _b([face], sp, 36))
        if st == "Short":
            a = _poly(a, [(17, cy - 3), (31, cy - 3), (29, cy - 1), (26, cy - 2), (23, cy), (20, cy - 2), (18, cy - 1)], hp[2])
        elif st == "Spiky":                      # ragged locks falling over the brow
            for fx, ln, lean in ((17, 3, -1.5), (20.5, 5, -1), (24.5, 3, 0.5), (28, 5.5, 1.5), (31.5, 3, 2)):
                a = _poly(a, [(fx - 2.6, cy - 4), (fx + 2.6, cy - 4), (fx + lean, cy - 3 + ln)], hp[2] if fx < 26 else hp[1])
            a = _line(a, (19, cy - 6), (21, cy - 3), hp[3], 1)
        elif st == "Shaggy":
            for fx, ln in ((17.5, 3), (21, 4.5), (24.5, 3.5), (28, 4.5), (31, 3)):
                a = _poly(a, [(fx - 2.5, cy - 3), (fx + 2.5, cy - 3), (fx, cy - 2 + ln)], hp[2])
            a = _layer(a, _b([(15.5, cy + 3, 2.4, 4.6), (32.5, cy + 3, 2.4, 4.6)], hp, 37))
        elif st == "Long":
            a = _poly(a, [(24, cy - 6), (16, cy - 1), (15.5, cy + 4), (19, cy - 2)], hp[2])     # centre part
            a = _poly(a, [(24, cy - 6), (32, cy - 1), (32.5, cy + 4), (29, cy - 2)], hp[1])
            a = _layer(a, _b([(15, cy + 8, 2.8, 7.5), (33, cy + 8, 2.8, 7.5)], hp, 38))         # locks over the shoulders
        elif st == "Ponytail":
            a = _poly(a, [(17, cy - 3), (31, cy - 3), (30, cy - 1.5), (18, cy - 1.5)], hp[2])
            a = _line(a, (24, cy - 8), (24, cy - 3), hp[1], 1)
        elif st == "Twin Tails":
            a = _poly(a, [(17, cy - 3), (31, cy - 3), (31, cy - 1), (17, cy - 1)], hp[2])
            a = _layer(a, _b([(15, cy - 1, 2.2, 2), (33, cy - 1, 2.2, 2)], op, 39))           # ties
        elif st == "Bun":
            a = _layer(a, _b([(24, cy - 10, 4.6, 3.8)], hp, 40))
            a = _line(a, (20.5, cy - 7), (27.5, cy - 7), op[2], 2)
            a = _line(a, (24, cy - 6), (24, cy - 3), hp[1], 1)
        elif st == "Mohawk":
            a = _poly(a, [(21.5, cy - 4), (24, cy - 14), (26.5, cy - 4)], hp[2])
            a = _layer(a, _b([(24, cy - 7, 2.6, 5)], hp, 41))
        elif st == "Bob":
            a = _poly(a, [(17, cy - 4), (31, cy - 4), (31, cy - 0.5), (17, cy - 0.5)], hp[2])
        elif st == "Swept":
            a = _poly(a, [(15, cy - 4), (29, cy - 8), (33.5, cy - 3), (32, cy + 3), (27, cy - 2), (18, cy - 1)], hp[2])
            a = _line(a, (19, cy - 4), (30, cy - 6), hp[3], 1)
        a = _face(a, look.get("race"), look["skin"], look["hair"], 24, cy + 2)
    else:
        if st == "Mohawk":
            a = _layer(a, _b([(24, cy - 1, 8.8, 8)], stubble, 35))
            a = _layer(a, _b([(24, cy - 2, 2.8, 10)], hp, 36))
            a = _poly(a, [(21.5, cy - 6), (24, cy - 14), (26.5, cy - 6)], hp[2])
        else:
            back = {"Bob": [(24, cy, 10, 8.6)], "Shaggy": [(24, cy, 10, 9)], "Long": [(24, cy, 9.8, 8.8)],
                    "Spiky": [(24, cy - 1, 9.8, 8.4)]}.get(st, [(24, cy - 1, 9.3, 8)])
            if st == "Spiky":
                a = _spike_crest(a, hp, cy, nape=True)
            a = _layer(a, _b(back, hp, 35))
        if st == "Bob":
            a = _poly(a, [(14, cy), (34, cy), (34, cy + 7), (14, cy + 7)], hp[1])
            a = _line(a, (14, cy + 7), (34, cy + 7), hp[0], 1)
        elif st == "Spiky":
            a = _line(a, (18, cy - 5), (21, cy - 1), hp[3], 1)
            a = _line(a, (27, cy - 6), (29, cy - 2), hp[1], 1)
        elif st == "Shaggy":
            for nx in (16, 20, 24, 28, 32):
                a = _poly(a, [(nx - 2.5, cy + 4), (nx + 2.5, cy + 4), (nx, cy + 9)], hp[1])
        elif st == "Long":
            a = _line(a, (24, cy - 7), (24, cy + 18), hp[0], 1)
        elif st == "Ponytail":
            a = _layer(a, _b([(24, cy + 3, 2.4, 1.6)], op, 42))                        # tie
        elif st == "Twin Tails":
            a = _layer(a, _b([(15, cy - 1, 2.2, 2), (33, cy - 1, 2.2, 2)], op, 39))
            a = _line(a, (24, cy - 8), (24, cy + 6), hp[1], 1)
        elif st == "Bun":
            a = _layer(a, _b([(24, cy - 9, 4.8, 4.2)], hp, 40))
            a = _line(a, (20.5, cy - 6), (27.5, cy - 6), op[2], 2)
        elif st == "Swept":
            a = _line(a, (17, cy - 4), (31, cy - 7), hp[3], 1)
            a = _line(a, (18, cy), (32, cy - 3), hp[1], 1)
        if st not in ("Bob", "Long", "Shaggy", "Mohawk"):
            a = _line(a, (20, cy + 7), (28, cy + 7), sp[1], 1)                         # the nape
    return _ears(a, look.get("race"), look["skin"], cy + 1, front)


def _hood_up(a, look, front, cy=12):
    """The raised hood (and the face peeking out of it)."""
    op = accent_palette(look["color"]); sp = _pal(look["skin"]); hp = _pal(look["hair"])
    if look.get("style") == "Long" and front:
        a = _layer(a, _b([(15.5, cy + 9, 2.8, 7), (32.5, cy + 9, 2.8, 7)], hp, 43))   # spilling out the front
    a = _poly(a, [(17, cy - 6), (24, cy - 13), (31, cy - 6)], op[2])
    a = _layer(a, _b([(24, cy, 10, 9.5)], op, 6))
    if front:
        a = _layer(a, _b([(24, cy + 2, 6.5, 6.5)], sp, 7))                 # face in the hood
        a = _poly(a, [(18, cy - 1), (30, cy - 1), (28, cy + 1), (20, cy + 1)], hp[2])  # fringe
        a = _face(a, look.get("race"), look["skin"], look["hair"], 24, cy + 2)
    else:
        a = _line(a, (24, cy - 8), (24, cy + 8), op[1], 1)                  # hood seam
        if look.get("style") in ("Long", "Ponytail"):                        # hanging out the back
            a = _layer(a, _b([(24, cy + 15, 3 if look["style"] == "Ponytail" else 5.5, 7.5)], hp, 44))
    return _ears(a, look.get("race"), look["skin"], cy + 1, front)


def _mage(a, look, front):
    op = accent_palette(look["color"]); sp = _pal(look["skin"]); hp = _pal(look["hair"])
    orb = look.get("orb") or mix(look["color"], (255, 255, 255), 0.5)
    a = _hair_behind(a, look, front)
    # staff, held in the right hand (screen right from behind, screen left from the front)
    sx = 40 if not front else 8
    a = _line(a, (sx, 47), (sx + (1 if not front else -1), 6), (104, 70, 42), 3)
    a = _layer(a, _b([(sx + (1 if not front else -1), 5, 3.6, 3.6)], [shade(orb, 0.6), orb, mix(orb, (255, 255, 255), 0.6)], 11, 0.0))
    # robe
    robe = [(14, 22), (34, 22), (39, 46), (9, 46)]
    a = _poly(a, robe, op[2])
    a = _poly(a, [(14, 22), (24, 22), (24, 46), (9, 46)], op[3] if front else op[1])
    a = _line(a, (9, 45), (39, 45), GOLD[2], 2)                       # gold hem
    a = _line(a, (24, 24), (24, 45), op[0] if not front else GOLD[1], 1)
    a = _layer(a, _b([(12, 31, 4.5, 7), (36, 31, 4.5, 7)], op, 4))     # sleeves
    a = _layer(a, _b([(sx - (2 if not front else -2), 37, 2.6, 2.4), (11 if not front else 37, 37, 2.6, 2.4)], sp, 5))
    if front:
        a = _line(a, (15, 33), (33, 33), GOLD[1], 2)                   # belt
    if not look.get("bare"):
        return _hood_up(a, look, front)
    # hood down: it lies bunched round the shoulders
    a = _layer(a, _b([(24, 22, 10.5, 3.6)] if front else [(24, 24, 9, 5.5)], op, 6))
    return _bare_head(a, look, front)


def _brawler(a, look, front):
    op = accent_palette(look["color"]); sp = _pal(look["skin"]); hp = _pal(look["hair"])
    a = _hair_behind(a, look, front)
    pants = [(40, 38, 56), (60, 58, 82), (82, 80, 108), (110, 108, 136)]
    a = _layer(a, _b([(19, 41, 4.5, 6), (29, 41, 4.5, 6)], pants, 2))
    a = _layer(a, _b([(18, 46.5, 5, 2), (30, 46.5, 5, 2)], [(40, 28, 20), (70, 48, 30)], 3))
    a = _layer(a, _b([(24, 29, 11, 9)], sp, 4))                        # bare shoulders
    a = _layer(a, _b([(24, 31, 8.5, 8)], op, 5))                       # vest
    a = _line(a, (16, 36), (32, 36), (92, 62, 40), 2)
    a = _layer(a, _b([(10, 30, 4.5, 7.5), (38, 30, 4.5, 7.5)], sp, 6))  # arms
    a = _layer(a, _b([(10, 38, 4, 3), (38, 38, 4, 3)], [(196, 186, 166), (236, 228, 208), (250, 246, 236)], 7))
    if not look.get("bare"):                                           # hoodie up
        a = _layer(a, _b([(24, 22, 10, 3.4)], op, 8))
        return _hood_up(a, look, front)
    cy = HEAD_CY
    a = _bare_head(a, look, front, cy)
    a = _line(a, (15, cy - 2), (33, cy - 2), op[2], 2)                 # headband
    tail = ([(16, cy - 2), (8, cy + 1), (10, cy + 4), (16, cy)] if not front
            else [(32, cy - 2), (40, cy + 2), (38, cy + 4), (32, cy)])
    a = _poly(a, tail, op[1])
    return a


def _knight(a, look, front):
    op = accent_palette(look["color"]); hp = _pal(look["hair"]); sp = _pal(look["skin"])
    a = _hair_behind(a, look, front)
    a = _layer(a, _b([(19, 41, 4.5, 6), (29, 41, 4.5, 6)], METAL, 2))  # greaves
    a = _layer(a, _b([(18, 46.5, 5, 2), (30, 46.5, 5, 2)], [(40, 44, 56), (72, 78, 94)], 3))
    if not front:                                                      # the cape
        a = _poly(a, [(14, 21), (34, 21), (37, 43), (32, 40), (28, 44), (24, 41), (20, 44), (16, 40), (11, 43)], op[2])
        a = _poly(a, [(14, 21), (24, 21), (24, 41), (20, 44), (16, 40), (11, 43)], op[1])
        a = _line(a, (24, 22), (24, 40), op[0], 1)
    else:
        a = _layer(a, _b([(24, 30, 10, 9)], METAL, 4))                 # breastplate
        a = _line(a, (17, 27), (31, 27), op[2], 2)
        a = _poly(a, [(22, 29), (26, 29), (24, 33)], op[2])
    # sword up past the shoulder, shield on the off arm
    bx = 39 if not front else 9
    a = _poly(a, [(bx, 33), (bx + 3, 33), (bx + (6 if not front else -4), 6), (bx + (4 if not front else -6), 5)], METAL[2])
    a = _line(a, (bx - 2, 33), (bx + 5, 33), GOLD[1], 2)
    shx = 9 if not front else 39
    a = _layer(a, _b([(shx, 32, 5.5, 8)], op, 5))
    a = _layer(a, _b([(shx, 32, 2.2, 3)], [GOLD[1], GOLD[2], GOLD[3]], 6, 0.0))
    a = _layer(a, _b([(12, 23, 6, 4.5), (36, 23, 6, 4.5)], METAL, 7))  # pauldrons
    if look.get("bare"):                                               # helmet off
        a = _layer(a, _b([(24, 22, 6.5, 2.6)], METAL, 8))              # gorget
        return _bare_head(a, look, front)
    # helmet with plume
    a = _poly(a, [(24, 1), (30, -1), (36, 6), (31, 6)] if not front else [(24, 1), (18, -1), (12, 6), (17, 6)], hp[2])
    a = _layer(a, _b([(24, 12, 9.5, 9)], METAL, 8))
    if front:
        a = _layer(a, _b([(24, 15, 5.5, 4.5)], sp, 9))
        a = _line(a, (17, 11), (31, 11), METAL[0], 2)                  # visor edge
        a = _face(a, look.get("race"), look["skin"], look["hair"], 24, 14)
    else:
        a = _line(a, (24, 4), (24, 20), METAL[1], 1)
    return a


_CLASSES = {"Mage": _mage, "Brawler": _brawler, "Knight": _knight}


def hero_sprite(look, view="back"):
    """48x48 hero; view "back" for battle, "front" for the character screen."""
    look = dict(look)
    look.setdefault("color", (70, 110, 220)); look.setdefault("skin", (246, 204, 166))
    look.setdefault("hair", (112, 66, 36))
    look.setdefault("style", "Short")
    look["bare"] = not look.get("hood", True)      # hood down / helmet off: the hairstyle shows
    a = blank(48, 48)
    a = _CLASSES.get(look.get("class"), _mage)(a, look, view == "front")
    outline(a, OUT)
    return to_surface(a)


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    import make_tiles as mt
    races = list(mt.RACE_SKINS)
    looks = []
    for cls, col in (("Mage", "Azure"), ("Brawler", "Crimson"), ("Knight", "Forest")):
        for race in races:
            looks.append({"class": cls, "race": race, "color": mt.OUTFIT_COLORS[col],
                          "skin": mt.SKIN_TONES[mt.RACE_SKINS[race][0]], "hair": mt.HAIR_COLORS["Golden" if race == "Elf" else "Raven"],
                          "orb": (255, 140, 40)})
    cell = 104
    sheet = pygame.Surface((len(races) * cell, 6 * cell))
    sheet.fill((44, 56, 44))
    for i, lk in enumerate(looks):
        row, col = divmod(i, len(races))
        for v, view in enumerate(("front", "back")):
            spr = pygame.transform.scale(hero_sprite(lk, view), (96, 96))
            sheet.blit(spr, (col * cell + 4, (row * 2 + v) * cell + 4))
    out = os.path.join(HERE, "tiles", "_sheet_heroes.png")
    pygame.image.save(sheet, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
