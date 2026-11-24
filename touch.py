"""
On-screen touch controls, for Android (and touchscreen PCs).

    * a movement stick, bottom left  - push it the way you want to walk; push it to the
      edge to run (it presses the arrow keys and Shift for the game)
    * the Use button, bottom right    - talk, open, interact (Enter)
    * the corner button, top right    - pause / close (Escape)

Everything else in the game already works by tapping: Android turns a tap into a mouse
click, and the game's buttons, cards, menus and dialogue boxes all take clicks.

The controls show on Android always, on a PC once its touchscreen is used, and anywhere
when the game is started with --touch (or DUNGEON_TOUCH=1), which also lets the mouse
drive them for testing.

move.py uses it like this, once per frame:
    touch_controls.layout(size, stick=..., use=..., corner=...)   # what this screen needs
    events = touch_controls.process(pygame.event.get())
    keys   = touch_controls.keys(pygame.key.get_pressed())       # movement
    touch_controls.draw(screen)                                   # on top of the frame
"""
import math
import os
import sys

import pygame

ON_ANDROID = (hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
              or "ANDROID_PRIVATE" in os.environ)

DEAD_ZONE = 0.28        # of the stick's radius: smaller pushes don't move
RUN_AT = 0.92           # pushed this far out: run

_DIR_KEYS = {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}
_MOUSE = "mouse"        # the finger id used when the mouse drives the controls (--touch)


class _Keys:
    """pygame.key.get_pressed(), plus the keys the stick is holding down."""

    def __init__(self, real, held):
        self._real, self._held = real, held

    def __getitem__(self, k):
        return bool(self._real[k]) or k in self._held


class TouchControls:
    def __init__(self):
        self.forced = (ON_ANDROID or os.environ.get("DUNGEON_TOUCH") == "1"
                       or "--touch" in sys.argv)
        self.mouse_drives = not ON_ANDROID and self.forced   # testing on a PC
        self.seen_touch = False
        self.size = (800, 600)
        self.show = {"stick": False, "use": False, "corner": None}
        self.fingers = {}        # finger -> "stick" / "use" / "corner" / None (tapping the game)
        self.stick_vec = None    # (x, y), -1..1 each, while the stick is held
        self.mouse_finger = None # the finger Android is also turning into mouse events
        self.mouse_on_control = False
        self._font = None
        self._font_size = 0

    # ---- what shows -------------------------------------------------------------------
    @property
    def active(self):
        return self.forced or self.seen_touch

    def layout(self, size, stick=False, use=False, corner=None):
        """Say what the current screen needs: the stick, the Use button, and the corner
        button ("pause", "close" or None). Controls that go away are let go."""
        self.size = tuple(size)
        new = {"stick": bool(stick), "use": bool(use), "corner": corner}
        if not new["stick"]:
            self.stick_vec = None
        for f, what in list(self.fingers.items()):
            if what and not (new[what] if what != "corner" else new["corner"]):
                self.fingers[f] = None
        self.show = new

    def _geometry(self):
        w, h = self.size
        u = h / 600.0
        return {
            "stick": ((int(118 * u), h - int(118 * u)), int(72 * u)),
            "use": ((w - int(92 * u), h - int(104 * u)), int(46 * u)),
            "corner": ((w - int(42 * u), int(42 * u)), int(26 * u)),
        }

    def _hit(self, pos):
        """Which shown control is at `pos` (game pixels), if any."""
        if not self.active:
            return None
        g = self._geometry()
        for name, reach in (("use", 1.25), ("corner", 1.5), ("stick", 1.6)):
            on = self.show[name] if name != "corner" else self.show["corner"]
            if not on:
                continue
            (cx, cy), r = g[name]
            if math.hypot(pos[0] - cx, pos[1] - cy) <= r * reach:
                return name
        return None

    # ---- input ------------------------------------------------------------------------
    def _to_game(self, fx, fy):
        """A finger's position (0..1 across the window) in game pixels, allowing for the
        black bars around the picture."""
        try:
            ww, wh = pygame.display.get_window_size()
        except Exception:
            ww, wh = self.size
        lw, lh = self.size
        s = min(ww / lw, wh / lh) or 1.0
        ox, oy = (ww - lw * s) / 2, (wh - lh * s) / 2
        return (int((fx * ww - ox) / s), int((fy * wh - oy) / s))

    def _aim(self, pos):
        (cx, cy), r = self._geometry()["stick"]
        dx, dy = (pos[0] - cx) / r, (pos[1] - cy) / r
        m = math.hypot(dx, dy)
        if m > 1:
            dx, dy = dx / m, dy / m
        self.stick_vec = (dx, dy)

    def _key(self, kind, key):
        return pygame.event.Event(kind, key=key, mod=0, unicode="\r" if key == pygame.K_RETURN else "",
                                  scancode=0, from_touch=True)

    def _down(self, finger, pos, out):
        what = self._hit(pos)
        self.fingers[finger] = what
        if what == "stick":
            self._aim(pos)
        elif what == "use":
            out.append(self._key(pygame.KEYDOWN, pygame.K_RETURN))
        elif what == "corner":
            out.append(self._key(pygame.KEYDOWN, pygame.K_ESCAPE))
        return what

    def _up(self, finger, out):
        what = self.fingers.pop(finger, None)
        if what == "stick":
            self.stick_vec = None
        elif what == "use":
            out.append(self._key(pygame.KEYUP, pygame.K_RETURN))
        elif what == "corner":
            out.append(self._key(pygame.KEYUP, pygame.K_ESCAPE))

    def process(self, events):
        """Turn touches on the controls into the keys they stand for, keep taps elsewhere
        as clicks, and drop the clicks Android makes from touches on the controls."""
        out = []
        for e in events:
            t = e.type
            if t in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                self.seen_touch = True
                finger = (getattr(e, "touch_id", 0), getattr(e, "finger_id", 0))
                pos = self._to_game(e.x, e.y)
                if t == pygame.FINGERDOWN:
                    if not self.fingers:
                        self.mouse_finger = finger       # Android makes mouse events from this one
                    what = self._down(finger, pos, out)
                    if what is None and finger != self.mouse_finger:
                        # a second finger tapping the game: Android won't click for it
                        out.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos,
                                                      touch=False, from_touch=True))
                elif t == pygame.FINGERMOTION:
                    if self.fingers.get(finger) == "stick":
                        self._aim(pos)
                else:
                    was = self.fingers.get(finger)
                    self._up(finger, out)
                    if was is None and finger != self.mouse_finger and finger is not None:
                        out.append(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos,
                                                      touch=False, from_touch=True))
                    if finger == self.mouse_finger:
                        self.mouse_finger = None
                continue
            if t in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                if getattr(e, "from_touch", False):
                    out.append(e)
                    continue
                if getattr(e, "touch", False):
                    # Android's copy of a touch as a mouse event: drop it if the touch is on
                    # a control (the finger events above handle those)
                    self.seen_touch = True
                    if t == pygame.MOUSEBUTTONDOWN:
                        self.mouse_on_control = self._hit(e.pos) is not None
                    drop = self.mouse_on_control
                    if t == pygame.MOUSEBUTTONUP:
                        self.mouse_on_control = False
                    if not drop:
                        out.append(e)
                    continue
                if self.mouse_drives:
                    # testing on a PC: the mouse works the controls like a finger
                    if t == pygame.MOUSEBUTTONDOWN and e.button == 1 and self._hit(e.pos):
                        self._down(_MOUSE, e.pos, out)
                        continue
                    if _MOUSE in self.fingers:
                        if t == pygame.MOUSEMOTION and self.fingers[_MOUSE] == "stick":
                            self._aim(e.pos)
                        elif t == pygame.MOUSEBUTTONUP and e.button == 1:
                            self._up(_MOUSE, out)
                        continue
                out.append(e)
                continue
            if t in (pygame.KEYDOWN, pygame.KEYUP) and getattr(e, "key", None) == getattr(pygame, "K_AC_BACK", -1):
                # Android's Back button: Escape
                out.append(pygame.event.Event(t, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0))
                continue
            out.append(e)
        return out

    def held_keys(self):
        """The keys the stick is holding down."""
        v = self.stick_vec
        if not v or not self.show["stick"]:
            return set()
        x, y = v
        m = math.hypot(x, y)
        if m < DEAD_ZONE:
            return set()
        if abs(x) > abs(y):
            held = {_DIR_KEYS["right" if x > 0 else "left"]}
        else:
            held = {_DIR_KEYS["down" if y > 0 else "up"]}
        if m >= RUN_AT:
            held.add(pygame.K_LSHIFT)
        return held

    def keys(self, real):
        """Wrap pygame.key.get_pressed() so the stick counts as held keys."""
        return _Keys(real, self.held_keys()) if self.active else real

    # ---- drawing ------------------------------------------------------------------------
    def _label_font(self, size):
        if self._font is None or self._font_size != size:
            try:
                import fonts
                self._font = fonts.serif(size, bold=True)
            except Exception:
                self._font = pygame.font.Font(None, size)
            self._font_size = size
        return self._font

    def _sprite(self, kind, held, variant, r, u):
        """One control drawn on its own small surface; cached, since redrawing them (or a
        whole-screen layer) every frame is slow on a phone."""
        key = (kind, held, variant, r, round(u, 3))
        cache = self.__dict__.setdefault("_sprites", {})
        spr = cache.get(key)
        if spr is not None:
            return spr
        pad = max(2, int(3 * u))
        spr = pygame.Surface((2 * r + 2 * pad, 2 * r + 2 * pad), pygame.SRCALPHA)
        cx = cy = r + pad
        line = max(2, int(2 * u))
        if kind == "base":
            pygame.draw.circle(spr, (10, 8, 6, 90), (cx, cy), r)
            pygame.draw.circle(spr, (232, 205, 140, 150), (cx, cy), r, line)
            for a in range(4):                                   # little direction marks
                ang = a * math.pi / 2
                c, s_ = math.cos(ang), math.sin(ang)
                tip = (cx + c * r * 0.82, cy + s_ * r * 0.82)
                side = r * 0.12
                pts = [tip,
                       (tip[0] - c * side * 1.4 + s_ * side, tip[1] - s_ * side * 1.4 - c * side),
                       (tip[0] - c * side * 1.4 - s_ * side, tip[1] - s_ * side * 1.4 + c * side)]
                pygame.draw.polygon(spr, (232, 205, 140, 140), pts)
        elif kind == "knob":
            pygame.draw.circle(spr, (250, 228, 170, 200 if held else 150), (cx, cy), r)
            pygame.draw.circle(spr, (60, 44, 20, 200), (cx, cy), r, max(1, int(2 * u)))
        elif kind == "use":
            pygame.draw.circle(spr, (60, 120, 70, 210 if held else 150), (cx, cy), r)
            pygame.draw.circle(spr, (232, 205, 140, 220), (cx, cy), r, line)
            t = self._label_font(max(10, int(22 * u))).render("Use", True, (255, 248, 230))
            spr.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
        elif kind == "corner":
            pygame.draw.circle(spr, (10, 8, 6, 200 if held else 140), (cx, cy), r)
            pygame.draw.circle(spr, (232, 205, 140, 220), (cx, cy), r, line)
            col = (250, 236, 200, 240)
            if variant == "pause":
                bw, bh = max(3, int(5 * u)), int(r * 0.9)
                for dx in (-int(r * 0.25), int(r * 0.25)):
                    pygame.draw.rect(spr, col, (cx + dx - bw // 2, cy - bh // 2, bw, bh))
            else:
                k = r * 0.38
                lw = max(2, int(4 * u))
                pygame.draw.line(spr, col, (cx - k, cy - k), (cx + k, cy + k), lw)
                pygame.draw.line(spr, col, (cx - k, cy + k), (cx + k, cy - k), lw)
        cache[key] = spr
        return spr

    def draw(self, surface):
        if not self.active:
            return
        g = self._geometry()
        u = self.size[1] / 600.0
        pressed = set(w for w in self.fingers.values() if w)

        def put(spr, cx, cy):
            surface.blit(spr, (int(cx) - spr.get_width() // 2, int(cy) - spr.get_height() // 2))

        if self.show["stick"]:
            (cx, cy), r = g["stick"]
            put(self._sprite("base", False, None, r, u), cx, cy)
            kx, ky = cx, cy
            if self.stick_vec:
                kx, ky = cx + self.stick_vec[0] * r * 0.62, cy + self.stick_vec[1] * r * 0.62
            put(self._sprite("knob", "stick" in pressed, None, int(30 * u), u), kx, ky)
        if self.show["use"]:
            (cx, cy), r = g["use"]
            put(self._sprite("use", "use" in pressed, None, r, u), cx, cy)
        if self.show["corner"]:
            (cx, cy), r = g["corner"]
            put(self._sprite("corner", "corner" in pressed, self.show["corner"], r, u), cx, cy)
