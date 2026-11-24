"""
Ambient life for the world and the battle screen — all of it purely visual.

    birds       flocks crossing overhead by day (with shadows on the ground below), bats
                at night, and small birds that land, peck about and scatter when you
                come close
    weather     per biome: pollen and butterflies in the meadow (fireflies at night),
                snowfall on the tundra, blowing sand in the dunes, embers and ash over
                the volcanic wastes, rain showers and lightning on the storm crags
    life        leaves drifting off trees, chimney smoke over village houses, sparkles
                on water, moths round lampposts at night, embers off fireplaces and
                vents, footprints in snow, sand and ash
    indoors     dust, glowing spores, frost glitter, sparks and embers per cave theme;
                drifting motes in houses

move.py builds a small `ctx` dict each frame (what's on screen and how to look at the
world) and calls update(), then the three draw passes at the right points of its draw
order: draw_ground (under everyone), draw_air (over everyone, still lit by day/night),
draw_glow (after lighting, so glowing things stay bright in the dark).
"""
import math
import os
import random
import sys

import pygame

STD_AREA = 267 * 200          # the base view at 800x600; densities are per one of these

# Particle kinds. cols: palette; sz: (w, h) choices; life (s); vx, vy: px/s ranges;
# sway: side-to-side amplitude (px) at frequency sf; wind: how much the wind pushes;
# alpha: base opacity; glow: drawn after lighting with a soft halo; pulse / flicker /
# twinkle: how the opacity breathes.
SPEC = {
    "pollen":  dict(cols=[(250, 238, 160), (255, 252, 214)], sz=[(1, 1)], life=(4, 7), vx=(-3, 3), vy=(-4, -1),
                    sway=3.0, sf=1.1, wind=0.5, alpha=210, twinkle=True),
    "leaf":    dict(cols=[(98, 160, 64), (140, 184, 76), (206, 170, 64), (196, 112, 56)], sz=[(2, 1), (1, 1)],
                    life=(3, 5), vx=(2, 6), vy=(9, 14), sway=7.0, sf=2.0, wind=1.0, alpha=255, flip=True),
    "firefly": dict(cols=[(214, 255, 120), (255, 240, 130)], sz=[(1, 1)], life=(5, 9), vx=(-1, 1), vy=(-1, 1),
                    sway=6.0, sf=0.7, wind=0.1, glow=True, pulse=True, halo=3),
    "snow":    dict(cols=[(255, 255, 255), (226, 236, 255)], sz=[(1, 1), (1, 1), (2, 2)], life=(4, 7),
                    vx=(-2, 4), vy=(12, 20), sway=5.0, sf=1.0, wind=1.0, alpha=240, shade=((140, 160, 196), 120)),
    "sand":    dict(cols=[(206, 174, 118), (190, 156, 104), (236, 216, 170)], sz=[(3, 1), (5, 1), (2, 1)],
                    life=(1.2, 2.4), vx=(55, 85), vy=(-2, 3), sway=1.5, sf=3.0, wind=1.0, alpha=190),
    "ember":   dict(cols=[(255, 170, 70), (255, 120, 40), (255, 214, 120)], sz=[(1, 1)], life=(2, 4),
                    vx=(-4, 4), vy=(-20, -10), sway=4.0, sf=2.2, wind=0.4, glow=True, flicker=True, halo=3),
    "ash":     dict(cols=[(130, 124, 124), (90, 86, 88), (160, 152, 150)], sz=[(1, 1)], life=(5, 8),
                    vx=(2, 6), vy=(5, 9), sway=5.0, sf=1.3, wind=0.8, alpha=220),
    "dust":    dict(cols=[(214, 204, 184)], sz=[(1, 1)], life=(6, 10), vx=(-2, 2), vy=(-2, 2),
                    sway=2.0, sf=0.5, wind=0.0, alpha=110, twinkle=True),
    "spore":   dict(cols=[(150, 240, 150), (190, 255, 170)], sz=[(1, 1)], life=(5, 8), vx=(-2, 2), vy=(-5, -2),
                    sway=3.0, sf=0.8, wind=0.0, glow=True, pulse=True, halo=2),
    "frost":   dict(cols=[(200, 230, 255), (255, 255, 255)], sz=[(1, 1)], life=(3, 6), vx=(-2, 2), vy=(2, 5),
                    sway=2.0, sf=0.8, wind=0.0, glow=True, twinkle=True),
    "arc":     dict(cols=[(190, 160, 255), (150, 200, 255)], sz=[(1, 1)], life=(1.5, 3), vx=(-6, 6), vy=(-6, 6),
                    sway=4.0, sf=3.0, wind=0.0, glow=True, flicker=True, halo=2),
    "mote":    dict(cols=[(255, 226, 170)], sz=[(1, 1)], life=(6, 10), vx=(-1.5, 1.5), vy=(-2, 1),
                    sway=2.0, sf=0.5, wind=0.0, alpha=150, twinkle=True),
    "wisp":    dict(cols=[(150, 220, 255), (210, 240, 255)], sz=[(1, 1)], life=(1.6, 2.6), vx=(-2, 2), vy=(-12, -7),
                    sway=3.0, sf=2.5, wind=0.0, glow=True, twinkle=True, halo=2),
}
SPECIAL = {"rain", "splash", "glint", "butterfly", "smoke", "moth", "print", "kick"}

# How many particles to keep, relative to the full amount: half on Android, where every
# particle costs a phone several times what it costs a PC.
DENSITY = 0.5 if (hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
                  or "ANDROID_PRIVATE" in os.environ) else 1.0

# What each place gives off: [(kind, density per standard view)], by day and by night.
OUTDOOR = {
    "meadow":   {"day": [("pollen", 14), ("butterfly", 3)], "night": [("firefly", 18)]},
    "tundra":   {"day": [("snow", 55)], "night": [("snow", 55)]},
    "desert":   {"day": [("sand", 16)], "night": [("sand", 5)]},
    "volcanic": {"day": [("ember", 16), ("ash", 14)], "night": [("ember", 24), ("ash", 10)]},
    "storm":    {"day": [("rain", 70)], "night": [("rain", 70), ("arc", 3)]},
}
INDOOR = {
    "meadow":   [("dust", 8), ("spore", 10)],
    "tundra":   [("frost", 14), ("dust", 4)],
    "desert":   [("dust", 18)],
    "volcanic": [("ember", 18), ("dust", 4)],
    "storm":    [("arc", 8), ("dust", 6)],
    "dungeon":  [("dust", 14)],
    "house":    [("mote", 10)],
}
BATTLE_EXTRA = {"meadow": [("leaf", 5)]}

# Birds: palette per look. body/head/beak for a bird on the ground; fly = silhouette in
# the air (tip = wingtip colour, if different).
BIRD_LOOKS = {
    "sparrow": {"body": (128, 96, 72), "head": (88, 64, 50), "beak": (232, 176, 72), "fly": (58, 46, 42)},
    "finch":   {"body": (180, 146, 98), "head": (132, 100, 64), "beak": (232, 176, 72), "fly": (96, 72, 50)},
    "gull":    {"body": (240, 242, 248), "head": (214, 220, 230), "beak": (240, 186, 60), "fly": (236, 240, 248),
                "tip": (96, 102, 118)},
    "crow":    {"body": (44, 40, 50), "head": (30, 26, 34), "beak": (70, 64, 70), "fly": (30, 26, 34)},
    "bat":     {"fly": (36, 28, 44)},
}
BIOME_BIRD = {"meadow": "sparrow", "desert": "finch", "tundra": "gull", "volcanic": "crow", "storm": "crow"}
_WINGS = (
    ((-2, -2), (-1, -1), (1, -1), (2, -2)),     # up
    ((-2, -1), (-1, 0), (1, 0), (2, -1)),       # level
    ((-2, 1), (-1, 0), (1, 0), (2, 1)),         # down
    ((-2, -1), (-1, 0), (1, 0), (2, -1)),       # level
)
# overhead birds are nearer the eye: a bigger, 7px-wide silhouette (body drawn separately)
_WINGS_BIG = (
    ((-3, -3), (-2, -2), (-1, -1), (1, -1), (2, -2), (3, -3)),
    ((-3, -1), (-2, -1), (-1, 0), (1, 0), (2, -1), (3, -1)),
    ((-3, 2), (-2, 1), (-1, 0), (1, 0), (2, 1), (3, 2)),
    ((-3, -1), (-2, -1), (-1, 0), (1, 0), (2, -1), (3, -1)),
)
PRINT_COL = {"snow": (176, 192, 220), "sand": (192, 162, 112), "ash": (64, 60, 62)}
KICK_COL = {"sand": (226, 204, 156), "snow": (240, 246, 255), "ash": (120, 114, 112),
            "path_desert": (220, 196, 150)}


def _clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def _smooth(k):
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- cached little images

_cache = {}


def _dot(col, w, h, a):
    key = ("d", col, w, h, a)
    s = _cache.get(key)
    if s is None:
        if len(_cache) > 4000:
            _cache.clear()
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((col[0], col[1], col[2], a))
        _cache[key] = s
    return s


def _puff(col, r, a):
    """A soft round puff of radius r (px) at peak opacity a."""
    key = ("p", col, r, a)
    s = _cache.get(key)
    if s is None:
        if len(_cache) > 4000:
            _cache.clear()
        d = r * 2 + 1
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            k = 1.0 - (i - 1) / r
            pygame.draw.circle(s, (col[0], col[1], col[2], int(a * (0.15 + 0.85 * k))), (r, r), i)
        _cache[key] = s
    return s


class _P:
    __slots__ = ("k", "x", "y", "vx", "vy", "age", "life", "col", "w", "h", "ph")

    def __init__(self, k, x, y, vx, vy, life, col, w=1, h=1, ph=0.0):
        self.k, self.x, self.y, self.vx, self.vy = k, x, y, vx, vy
        self.age, self.life, self.col, self.w, self.h, self.ph = 0.0, life, col, w, h, ph


class _Bird:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "flap", "look", "state", "t", "face", "tx", "ty",
                 "age", "peck", "hop", "d0", "z0", "ph", "big")

    def __init__(self, x, y, z, look, state="fly"):
        self.x, self.y, self.z, self.look, self.state = x, y, z, look, state
        self.vx = self.vy = self.vz = 0.0
        self.flap, self.t, self.face, self.age, self.peck, self.hop = 0.0, 0.0, 1, 0.0, 0.0, 0.0
        self.tx = self.ty = self.d0 = self.z0 = 0.0
        self.ph = random.random() * 6.28
        self.big = False


class Ambience:
    def __init__(self, battle=False):
        self.battle = battle
        self.rng = random.Random()
        self.reset(None)

    def reset(self, key):
        r = self.rng
        self.key = key
        self.parts, self.birds = [], []
        self.target, self.smoke_t, self.src_t = {}, {}, {}
        self.next_flock = r.uniform(2.0, 6.0)
        self.next_land = r.uniform(1.0, 4.0)
        self.flash_age = None
        self.next_flash = r.uniform(4.0, 10.0)
        self.fresh = True
        self.last = None
        self.step = None
        self.wind, self.rain, self.dayk = 1.0, 1.0, 1.0
        self.region = (0, 0, 0, 0)
        self.tint = None

    # ------------------------------------------------------------------ what's around

    def _emitters(self, ctx, x, y):
        extra = BATTLE_EXTRA.get(ctx.get("theme"), ()) if self.battle and ctx["outdoor"] else ()
        if ctx["outdoor"]:
            spec = OUTDOOR.get(ctx["biome_at"](x, y))
            if not spec:
                return extra
            k = self.dayk
            out = [(kind, d * k * (self.rain if kind == "rain" else 1)) for kind, d in spec["day"]]
            out += [(kind, d * (1 - k) * (self.rain if kind == "rain" else 1)) for kind, d in spec["night"]]
            return out + list(extra)
        return INDOOR.get(ctx.get("theme"), INDOOR["dungeon"])

    def _in_region(self, x, y, m=0):
        x0, y0, x1, y1 = self.region
        return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m

    # ------------------------------------------------------------------------ update

    def update(self, ctx):
        r = self.rng
        now = ctx["now"]
        if ctx["key"] != self.key:
            self.reset(ctx["key"])
        dt = 0.0 if self.last is None else _clamp(now - self.last, 0.0, 0.1)
        self.last = now
        self.tint = ctx.get("tint")
        vx0, vy0, vw, vh = ctx["view"]
        m = 24
        self.region = (vx0 - m, vy0 - m, vx0 + vw + m, vy0 + vh + m)
        x0, y0, x1, y1 = self.region
        self.wind = 0.75 + 0.35 * math.sin(now * 0.05) + 0.15 * math.sin(now * 0.31)
        self.rain = 0.2 + 0.8 * max(0.0, math.sin(now * 0.045 + 1.0))       # passing showers
        self.dayk = _smooth(_clamp((ctx["day"] - 0.2) / 0.35))
        scale = (vw * vh) / STD_AREA * DENSITY

        # how many of each kind the view should hold, from a few samples across it
        est = {}
        S = 10
        for _ in range(S):
            for kind, d in self._emitters(ctx, r.uniform(x0, x1), r.uniform(y0, y1)):
                est[kind] = est.get(kind, 0.0) + d / S * scale
        for kind in set(est) | set(self.target):
            t, e = self.target.get(kind, 0.0), est.get(kind, 0.0)
            self.target[kind] = e if self.fresh else t + (e - t) * min(1.0, dt * 1.5)
        counts = {}
        for p in self.parts:
            counts[p.k] = counts.get(p.k, 0) + 1
        for kind, t in self.target.items():
            need = int(t - counts.get(kind, 0) + r.random())
            if need > 0:
                for _ in range(need if self.fresh else min(need, 8 if kind == "rain" else 3)):
                    self._spawn_kind(ctx, kind, self.fresh)

        if not self.battle:
            self._world_sources(ctx, dt)
        self._update_flash(ctx, dt)
        self._step_parts(ctx, dt)
        self._update_birds(ctx, dt)
        self.fresh = False

    def _spawn_kind(self, ctx, kind, prefill):
        r = self.rng
        x0, y0, x1, y1 = self.region
        for _ in range(5):
            x, y = r.uniform(x0, x1), r.uniform(y0, y1)
            if any(k == kind and d > 0 for k, d in self._emitters(ctx, x, y)):
                break
        else:
            return
        p = self._make(kind, x, y)
        if p is None:
            return
        if prefill:
            p.age = r.uniform(0, p.life * 0.85)
        self.parts.append(p)

    def _make(self, kind, x, y):
        r = self.rng
        if kind == "rain":
            return _P("rain", x, y, 40.0 * self.wind + r.uniform(-4, 4), r.uniform(210, 250), r.uniform(0.25, 0.6),
                      r.choice(((176, 196, 232), (150, 170, 214))))
        if kind == "butterfly":
            col = r.choice(((250, 250, 244), (250, 214, 80), (240, 150, 60), (130, 180, 250), (230, 140, 200)))
            return _P("butterfly", x, y, 0.0, 0.0, r.uniform(10, 16), col, ph=r.uniform(0, 6.28))
        sp = SPEC[kind]
        w, h = r.choice(sp["sz"])
        return _P(kind, x, y, r.uniform(*sp["vx"]), r.uniform(*sp["vy"]), r.uniform(*sp["life"]),
                  r.choice(sp["cols"]), w, h, r.uniform(0, 6.28))

    def _world_sources(self, ctx, dt):
        """Things in the world itself that give off particles."""
        r = self.rng
        T = ctx["tile"]
        vx0, vy0, vw, vh = ctx["view"]
        tk = ctx["tile_kind"]
        if ctx["outdoor"]:
            for _ in range(4):
                tx, ty = int(r.uniform(vx0, vx0 + vw) // T), int(r.uniform(vy0, vy0 + vh + 2 * T) // T)
                kind = tk(tx, ty)
                if kind == "tree" and r.random() < 0.07 * (0.3 + 0.7 * self.dayk):
                    self.parts.append(self._make("leaf", tx * T + r.uniform(2, 14), ty * T - r.uniform(2, 14)))
                elif kind == "water" and r.random() < (0.35 if self.dayk > 0.3 else 0.08):
                    col = (255, 255, 240) if self.dayk > 0.3 else (190, 210, 255)
                    self.parts.append(_P("glint", tx * T + r.uniform(2, 14), ty * T + r.uniform(2, 14), 0, 0,
                                         r.uniform(0.5, 0.9), col))
        # chimney smoke
        seen = {}
        for (cx, cy, dark) in ctx.get("chimneys", ()):
            key = (int(cx), int(cy))
            acc = self.smoke_t.get(key, r.uniform(0, 0.3)) + dt
            if self.fresh:
                for i in range(10):
                    self._smoke(cx, cy, dark, i * 0.32)
            while acc > 0.32:
                acc -= 0.32
                self._smoke(cx, cy, dark, 0.0)
            seen[key] = acc
        self.smoke_t = seen
        # objects: fireplaces and vents spit embers, the shrine breathes light, moths
        # circle lampposts after dark
        moths = sum(1 for p in self.parts if p.k == "moth")
        lamps = 0
        seen = {}
        for (sx, sy, what) in ctx.get("sources", ()):
            key = (int(sx), int(sy))
            acc = self.src_t.get(key, r.uniform(0, 0.5)) + dt
            if what == "lamp":
                lamps += 1
                if self.dayk < 0.35 and moths < lamps * 2 and r.random() < dt * 0.8:
                    self.parts.append(_P("moth", sx, sy, sx, sy, r.uniform(6, 11), (236, 228, 200),
                                         ph=r.uniform(0, 6.28)))
                    moths += 1
            else:
                kind, every = {"fire": ("ember", 0.35), "vent": ("ember", 0.25), "shrine": ("wisp", 0.45),
                               "crystal": ("arc", 3.2)}[what]
                while acc > every:
                    acc -= every
                    p = self._make(kind, sx + r.uniform(-3, 3), sy + r.uniform(-2, 2))
                    if what == "crystal":
                        p.life *= 0.6
                    self.parts.append(p)
            seen[key] = acc
        self.src_t = seen
        # footprints and a kick of dust behind each step
        step = ctx.get("step")
        if step is not None and step != self.step:
            if self.step is not None:
                fx, fy, ground, facing = ctx["step_from"]
                pc = PRINT_COL.get(ground)
                vert = facing in ("up", "down")
                side = 1 if step % 2 else -1
                if pc:
                    ox, oy = (side * 2, 0) if vert else (0, side * 1.5)
                    self.parts.append(_P("print", fx + ox, fy + oy, 0, 0, 9.0, pc, 2 if not vert else 1,
                                         1 if not vert else 2))
                kc = KICK_COL.get(ground)
                if kc:
                    for _ in range(3):
                        self.parts.append(_P("kick", fx + r.uniform(-3, 3), fy + r.uniform(-1, 1),
                                             r.uniform(-10, 10), r.uniform(-9, -3), r.uniform(0.3, 0.5), kc))
            self.step = step

    def _smoke(self, cx, cy, dark, age):
        r = self.rng
        col = (70, 64, 66) if dark else (236, 236, 240)
        p = _P("smoke", cx + r.uniform(-1, 1), cy, r.uniform(-1.5, 1.5), r.uniform(-11, -8), r.uniform(2.6, 3.4), col)
        if age:
            p.age = min(age, p.life * 0.95)
            p.x += (p.vx + self.wind * 6) * p.age
            p.y += p.vy * p.age
        self.parts.append(p)

    def _update_flash(self, ctx, dt):
        stormy = ctx["outdoor"] and ctx.get("player_biome") == "storm" and self.rain > 0.55
        if self.flash_age is not None:
            self.flash_age += dt
            if self.flash_age > 0.5:
                self.flash_age = None
        if stormy:
            self.next_flash -= dt
            if self.next_flash <= 0:
                self.flash_age = 0.0
                self.next_flash = self.rng.uniform(8.0, 20.0)

    def _step_parts(self, ctx, dt):
        r = self.rng
        wind = self.wind
        keep = []
        ground_at = ctx.get("ground_at")
        for p in self.parts:
            p.age += dt
            if p.age >= p.life:
                if p.k == "rain" and r.random() < 0.6:
                    keep.append(_P("splash", p.x, p.y, 0, 0, 0.18, p.col))
                continue
            k = p.k
            if k in SPECIAL:
                if k == "rain":
                    p.x += p.vx * dt; p.y += p.vy * dt
                elif k == "butterfly":
                    p.ph += math.sin(p.age * 1.7 + p.x * 0.05) * 2.4 * dt
                    p.x += (math.cos(p.ph) * 12 + wind * 2) * dt
                    p.y += (math.sin(p.ph) * 8 + math.sin(p.age * 9) * 7) * dt
                elif k == "smoke":
                    p.x += (p.vx + wind * 6) * dt; p.y += p.vy * dt
                    p.vy *= (1 - 0.15 * dt)
                elif k == "moth":
                    p.ph += dt * (3.2 + math.sin(p.age * 1.3) * 1.5)
                elif k == "kick":
                    p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 30 * dt
                if k not in ("smoke", "moth", "print", "glint", "splash") and not self._in_region(p.x, p.y, 8):
                    continue
                keep.append(p)
                continue
            sp = SPEC[k]
            sway, sf = sp["sway"], sp["sf"]
            if k == "firefly":
                p.x += math.cos(p.age * sf + p.ph) * sway * sf * dt + p.vx * dt
                p.y += math.sin(p.age * sf * 1.3 + p.ph) * sway * sf * dt + p.vy * dt
            else:
                p.x += (p.vx + wind * sp["wind"] * 10 + math.cos(p.age * sf + p.ph) * sway * sf) * dt
                p.y += p.vy * dt
            if not self._in_region(p.x, p.y, 8):
                continue
            keep.append(p)
        self.parts = keep

    # ------------------------------------------------------------------------- birds

    def _look_at(self, ctx, x, y):
        if not ctx["outdoor"]:
            return "sparrow"
        return BIOME_BIRD.get(ctx["biome_at"](x, y), "sparrow")

    def _update_birds(self, ctx, dt):
        r = self.rng
        if not ctx["outdoor"]:
            self.birds = []
            return
        self.next_flock -= dt
        if self.next_flock <= 0:
            self.next_flock = r.uniform(7.0, 16.0)
            if self.dayk > 0.5:
                self._flock(ctx, bats=False)
            elif self.dayk < 0.2:
                self._flock(ctx, bats=True)
        if not self.battle:
            self.next_land -= dt
            if self.next_land <= 0:
                self.next_land = r.uniform(4.0, 10.0)
                if self.dayk > 0.55 and sum(1 for b in self.birds if b.state in ("perch", "land")) < 5:
                    self._land_group(ctx)
        px, py = ctx.get("player", (-9999, -9999))
        moving = ctx.get("moving", False)
        keep = []
        for b in self.birds:
            b.age += dt
            if b.look == "bat":
                b.flap += dt * 9
            elif b.state in ("takeoff", "land"):
                b.flap += dt * 7
            elif b.state == "fly":
                b.flap += dt * 4 if (b.age * 0.5 + b.ph) % 3 < 2 else 0      # flap, then glide
            if b.state == "fly":
                b.x += b.vx * dt; b.y += b.vy * dt
                if b.look == "bat":
                    wob = math.sin(b.age * 5 + b.ph) * 22 * dt
                    b.y += wob
                if not self._in_region(b.x, b.y - b.z, 220) or (b.age > 3 and not self._in_region(b.x, b.y - b.z, 60)
                                                                and self._heading_out(b)):
                    continue
            elif b.state == "takeoff":
                b.x += b.vx * dt; b.y += b.vy * dt
                b.z += b.vz * dt
                if b.z >= 42:
                    b.state = "fly"
            elif b.state == "land":
                dx, dy = b.tx - b.x, b.ty - b.y
                dist = math.hypot(dx, dy)
                sp = 46 * dt
                if dist <= sp:
                    b.x, b.y, b.z, b.state = b.tx, b.ty, 0.0, "perch"
                    b.t = r.uniform(0.3, 1.2)
                else:
                    b.x += dx / dist * sp; b.y += dy / dist * sp
                    b.z = b.z0 * min(1.0, dist / max(1.0, b.d0)) ** 1.4
                    b.face = 1 if dx >= 0 else -1
            elif b.state == "perch":
                if not self._in_region(b.x, b.y, 140):
                    continue
                d = math.hypot(b.x - px, b.y - py)
                if d < 38 or (moving and d < 58) or b.age > 45:
                    self._scare(b, px, py, startled=d < 70)
                    for o in self.birds:                      # the rest of the group goes too
                        if o is not b and o.state == "perch" and math.hypot(o.x - b.x, o.y - b.y) < 34:
                            self._scare(o, px, py, startled=d < 70)
                else:
                    if b.hop > 0:
                        b.hop -= dt
                        b.x += b.vx * dt; b.y += b.vy * dt
                        b.z = max(0.0, math.sin(math.pi * (1 - b.hop / 0.18)) * 2)
                        if b.hop <= 0:
                            b.z = 0.0
                    b.peck = max(0.0, b.peck - dt)
                    b.t -= dt
                    if b.t <= 0:
                        b.t = r.uniform(0.4, 1.4)
                        roll = r.random()
                        if roll < 0.5:
                            b.peck = 0.35
                        elif roll < 0.8:
                            ang = r.uniform(0, 6.28)
                            nx, ny = b.x + math.cos(ang) * 3, b.y + math.sin(ang) * 2
                            walk = ctx.get("walkable")
                            if walk is None or walk(nx, ny):
                                b.hop, b.vx, b.vy = 0.18, math.cos(ang) * 16, math.sin(ang) * 11
                                b.face = 1 if b.vx >= 0 else -1
                        else:
                            b.face = -b.face
            keep.append(b)
        self.birds = keep

    def _heading_out(self, b):
        x0, y0, x1, y1 = self.region
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return (b.x - cx) * b.vx + (b.y - b.z - cy) * b.vy > 0

    def _scare(self, b, px, py, startled):
        r = self.rng
        ang = math.atan2(b.y - py, b.x - px) if startled else r.uniform(0, 6.28)
        ang += r.uniform(-0.6, 0.6)
        sp = r.uniform(52, 64)
        b.vx, b.vy, b.vz = math.cos(ang) * sp, math.sin(ang) * sp * 0.7, r.uniform(30, 42)
        b.face = 1 if b.vx >= 0 else -1
        b.state, b.age = "takeoff", 0.0

    def _flock(self, ctx, bats):
        r = self.rng
        vx0, vy0, vw, vh = ctx["view"]
        n = r.randint(1, 3) if bats else r.choice((1, 2, 3, 3, 4, 5))
        right = r.random() < 0.5
        ang = (0.0 if right else math.pi) + r.uniform(-0.12, 0.12) * (1 if self.battle else 4)
        speed = r.uniform(40, 52) * (1.25 if bats else 1.0)
        dx, dy = math.cos(ang), math.sin(ang)
        if self.battle:
            ay = r.uniform(8, max(10, ctx.get("sky", vh * 0.3) - 10))
        else:
            ay = vy0 + vh * r.uniform(0.15, 0.85)
        ax = vx0 + vw * r.uniform(0.25, 0.75)
        reach = max(vw, vh) * 0.75 + 40
        sx, sy = ax - dx * reach, ay - dy * reach
        z = 0.0 if self.battle else r.uniform(40, 60)
        look = "bat" if bats else self._look_at(ctx, ax, ay + z)
        for i in range(n):
            rank = (i + 1) // 2
            side = 1 if i % 2 else -1
            back, lat = rank * 9, side * rank * 7
            bx, by = sx - dx * back - dy * lat, sy - dy * back + dx * lat
            b = _Bird(bx, by + z, z, look)
            b.vx, b.vy = dx * speed, dy * speed
            b.face = 1 if right else -1
            b.flap = r.random() * 4
            b.big = look != "bat" or not self.battle
            self.birds.append(b)

    def _land_group(self, ctx):
        r = self.rng
        vx0, vy0, vw, vh = ctx["view"]
        px, py = ctx.get("player", (-9999, -9999))
        walk = ctx.get("walkable")
        for _ in range(14):
            tx, ty = vx0 + r.uniform(20, vw - 20), vy0 + r.uniform(24, vh - 16)
            if math.hypot(tx - px, ty - py) < 80 or (walk is not None and not walk(tx, ty)):
                continue
            look = self._look_at(ctx, tx, ty)
            ang = r.uniform(0, 6.28)
            for i in range(r.randint(1, 3)):
                gx, gy = tx + r.uniform(-7, 7), ty + r.uniform(-4, 4)
                if walk is not None and not walk(gx, gy):
                    gx, gy = tx, ty
                dist = 170 + i * 14
                b = _Bird(gx + math.cos(ang) * dist, gy + math.sin(ang) * dist, 52.0, look, "land")
                b.tx, b.ty, b.d0, b.z0 = gx, gy, dist, 52.0
                self.birds.append(b)
            return

    # -------------------------------------------------------------------------- draw

    def _px(self, surf, col, x, y, w, h, a, cam, s, tint=True):
        if a <= 3:
            return
        if tint and self.tint is not None:
            t = self.tint
            col = (col[0] * t[0] // 255, col[1] * t[1] // 255, col[2] * t[2] // 255)
        sx, sy = int((x - cam[0]) * s), int((y - cam[1]) * s)
        if a >= 250:
            surf.fill(col, (sx, sy, w * s, h * s))
        else:
            surf.blit(_dot(col, w * s, h * s, int(a) // 16 * 16 + 15), (sx, sy))

    def _fade(self, p, fin=0.4, fout=0.6):
        return _clamp(min(p.age / fin, (p.life - p.age) / fout))

    def draw_ground(self, surf, cam, s=1):
        """Footprints, sparkles on water, splashes, bird shadows and birds on the ground."""
        for p in self.parts:
            k = p.k
            if k == "print":
                self._px(surf, p.col, p.x, p.y, p.w, p.h, 150 * self._fade(p, 0.05, 3.0), cam, s)
            elif k == "glint":
                a = math.sin(math.pi * p.age / p.life) * 235
                self._px(surf, p.col, p.x, p.y, 1, 1, a, cam, s)
                for (ox, oy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._px(surf, p.col, p.x + ox, p.y + oy, 1, 1, a * 0.45, cam, s)
            elif k == "splash":
                k_ = p.age / p.life
                a = 170 * (1 - k_)
                d = 1 + k_ * 2.5
                self._px(surf, p.col, p.x - d, p.y - k_ * 1.5, 1, 1, a, cam, s)
                self._px(surf, p.col, p.x + d, p.y - k_ * 1.5, 1, 1, a, cam, s)
            elif k == "kick":
                self._px(surf, p.col, p.x, p.y, 1, 1, 170 * (1 - p.age / p.life), cam, s)
        for b in self.birds:
            if self.battle:
                continue
            if b.z > 0.5 or b.state != "perch":
                a = max(0.0, 70 - b.z * 0.7)
                if b.big:
                    self._px(surf, (0, 0, 0), b.x - 3, b.y, 7, 1, a * 0.8, cam, s, tint=False)
                    self._px(surf, (0, 0, 0), b.x, b.y - 1, 1, 3, a * 0.8, cam, s, tint=False)
                else:
                    self._px(surf, (0, 0, 0), b.x - 1, b.y, 3, 1, a, cam, s, tint=False)
            else:
                self._draw_perched(surf, b, cam, s)

    def _draw_perched(self, surf, b, cam, s):
        L = BIRD_LOOKS[b.look]
        f = b.face
        x, y = b.x, b.y - b.z
        self._px(surf, (0, 0, 0), b.x - 1, b.y, 3, 1, 60, cam, s, tint=False)
        breast = tuple(min(255, c + 46) for c in L["body"])
        dark = tuple(c * 3 // 5 for c in L["body"])
        pix = [(-2 * f, -2, dark), (-1 * f, -2, L["body"]), (0, -2, L["body"]), (1 * f, -2, L["body"]),
               (-1 * f, -1, L["body"]), (0, -1, breast), (1 * f, -1, breast),
               (-1 * f, 0, (70, 50, 40)), (0, 0, (70, 50, 40))]
        if b.peck > 0:
            pix += [(2 * f, -1, L["head"]), (2 * f, -2, L["head"]), (3 * f, 0, L["beak"])]
        else:
            pix += [(1 * f, -3, L["head"]), (2 * f, -3, L["head"]), (3 * f, -3, L["beak"])]
        for (ox, oy, c) in pix:
            self._px(surf, c, x + ox, y + oy, 1, 1, 255, cam, s)

    def draw_air(self, surf, cam, s=1):
        """Weather and drifting things, smoke, butterflies, moths and flying birds."""
        for p in self.parts:
            k = p.k
            if k in ("print", "glint", "splash", "kick"):
                continue
            if k == "rain":
                a = 150 * self._fade(p, 0.05, 0.05)
                self._px(surf, p.col, p.x, p.y - 3, 1, 4, a, cam, s)
            elif k == "smoke":
                kk = p.age / p.life
                a = 185 * (1 - kk) ** 1.2 * min(1.0, p.age / 0.3)
                rad = max(1, int((2 + 3.5 * kk) * s))
                col = p.col
                if self.tint is not None:
                    col = tuple(c * t // 255 for c, t in zip(col, self.tint))
                img = _puff(col, rad, int(a) // 10 * 10 + 5)
                surf.blit(img, (int((p.x - cam[0]) * s) - rad, int((p.y - cam[1]) * s) - rad))
            elif k == "butterfly":
                a = 255 * self._fade(p, 0.8, 0.8)
                open_ = int(p.age * 10 + p.ph) % 2 == 0
                self._px(surf, (60, 44, 40), p.x, p.y, 1, 1, a, cam, s)
                if open_:
                    self._px(surf, p.col, p.x - 1, p.y - 1, 1, 2, a, cam, s)
                    self._px(surf, p.col, p.x + 1, p.y - 1, 1, 2, a, cam, s)
                else:
                    self._px(surf, p.col, p.x, p.y - 1, 1, 1, a, cam, s)
                self._px(surf, (0, 0, 0), p.x, p.y + 5, 1, 1, 40 * a / 255, cam, s, tint=False)
            elif k == "moth":
                rad = 5 + math.sin(p.age * 0.9) * 2
                mx = p.vx + math.cos(p.ph) * rad
                my = p.vy + math.sin(p.ph) * rad * 0.6 - 2
                a = 230 * self._fade(p, 0.6, 0.8)
                self._px(surf, p.col, mx, my, 1 + (int(p.age * 14) % 2), 1, a, cam, s, tint=False)
            else:
                sp = SPEC[k]
                if sp.get("glow"):
                    continue
                a = sp.get("alpha", 255) * self._fade(p)
                if sp.get("twinkle"):
                    a *= 0.55 + 0.45 * math.sin(p.age * 5 + p.ph)
                w = p.w
                if sp.get("flip") and int(p.age * 6 + p.ph) % 2:
                    w = 1
                shade = sp.get("shade")
                if shade:
                    self._px(surf, shade[0], p.x, p.y + p.h, w, 1, shade[1] * a / 255, cam, s)
                self._px(surf, p.col, p.x, p.y, w, p.h, a, cam, s)
        for b in self.birds:
            if b.state == "perch":
                continue
            L = BIRD_LOOKS[b.look]
            x, y = b.x, b.y - b.z
            if b.big:
                body = L["fly"]
                tip = L.get("tip", body)
                frame = _WINGS_BIG[int(b.flap * 4) % 4] if b.flap else _WINGS_BIG[1]
                self._px(surf, body, x, y - 1, 1, 3, 255, cam, s)               # head, body, tail
                for i, (ox, oy) in enumerate(frame):
                    self._px(surf, tip if i in (0, 5) else body, x + ox, y + oy, 1, 1, 255, cam, s)
                continue
            frame = _WINGS[int(b.flap * 4) % 4] if b.flap else _WINGS[1]
            body = L["fly"]
            tip = L.get("tip", body)
            if b.look != "bat" and b.state == "land" and b.z < 8:
                frame = _WINGS[0]                                  # wings up as it touches down
            self._px(surf, body, x, y, 1, 1, 255, cam, s)
            for i, (ox, oy) in enumerate(frame):
                self._px(surf, tip if i in (0, 3) else body, x + ox, y + oy, 1, 1, 255, cam, s)
            if b.look == "bat":
                self._px(surf, body, x, y - 1, 1, 1, 255, cam, s)

    def draw_glow(self, surf, cam, s=1):
        """Glowing motes, untouched by the dark, then any lightning."""
        for p in self.parts:
            sp = SPEC.get(p.k)
            if sp is None or not sp.get("glow"):
                continue
            a = 255 * self._fade(p)
            if sp.get("pulse"):
                a *= 0.25 + 0.75 * (0.5 + 0.5 * math.sin(p.age * 3 + p.ph))
            if sp.get("flicker"):
                a *= 0.6 + 0.4 * self.rng.random()
            if sp.get("twinkle"):
                a *= 0.5 + 0.5 * math.sin(p.age * 6 + p.ph)
            halo = sp.get("halo", 0)
            if halo and a > 20:
                rad = halo * s
                img = _puff(p.col, rad, int(a * 0.5) // 10 * 10 + 5)
                surf.blit(img, (int((p.x - cam[0] + 0.5) * s) - rad, int((p.y - cam[1] + 0.5) * s) - rad))
            self._px(surf, p.col, p.x, p.y, p.w, p.h, a, cam, s, tint=False)
        if self.flash_age is not None:
            t = self.flash_age
            k = (1 - t / 0.1) if t < 0.1 else (0.75 * (1 - (t - 0.18) / 0.3) if 0.18 <= t < 0.48 else 0)
            if k > 0:
                w, h = surf.get_size()
                key = ("flash", w, h)
                fl = _cache.get(key)
                if fl is None:
                    fl = pygame.Surface((w, h)); fl.fill((230, 236, 255))
                    _cache[key] = fl
                fl.set_alpha(int(150 * k))
                surf.blit(fl, (0, 0))
