import pygame
import sys
import os
import math
import random

# --- Constants ---
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK               = (0, 0, 0)
WHITE               = (255, 255, 255)
DARKER_GRAY         = (15, 15, 20)
GOLD                = (255, 215, 0)
GOLD_DIM            = (180, 140, 0)
BUTTON_IDLE         = (40, 40, 55)
BUTTON_HOVER        = (70, 60, 90)
BUTTON_BORDER       = (100, 80, 130)
BUTTON_BORDER_HOVER = (200, 160, 255)
TEXT_NORMAL         = (200, 190, 220)
TEXT_HOVER          = (255, 255, 255)
WIP_COLOR           = (160, 120, 60)
SUBTITLE_COLOR      = (140, 120, 170)
CREDITS_COLOR       = (180, 170, 200)

# Sub-screen identifiers
SCREEN_MAIN    = "main"
SCREEN_PLAY    = "play"
SCREEN_OPTIONS = "options"
SCREEN_VIDEO   = "video"
SCREEN_AUDIO   = "audio"
SCREEN_CREDITS = "credits"
_LAUNCH        = "__launch__"  # sentinel for fade-then-return

# --- Font handles (populated by _init_fonts once pygame is ready) ---
font_title         = None
font_sub           = None
font_btn           = None
font_wip           = None
font_small         = None
font_credit        = None
font_credit_header = None

def _init_fonts():
    global font_title, font_sub, font_btn, font_wip, font_small, font_credit, font_credit_header
    from fonts import serif                  # Georgia, or a serif sized to match it (Linux)
    font_title         = serif(80, bold=True)
    font_sub           = serif(22, italic=True)
    font_btn           = serif(32)
    font_wip           = serif(18, italic=True)
    font_small         = serif(20)
    font_credit        = serif(24)
    font_credit_header = serif(28, bold=True)


# --- Settings state (shared so move.py can read them later if needed) ---
settings = {
    "resolution": "800x600",
    "fullscreen": False,
    "quality":    "Medium",
    "master_vol": 80,
    "music_vol":  70,
    "sfx_vol":    70,
}
RESOLUTIONS  = ["800x600", "1280x720", "1920x1080"]
QUALITY_OPTS = ["Low", "Medium", "High"]

# On Android the game is always fullscreen, and a wide picture suits a phone better.
from touch import ON_ANDROID
if ON_ANDROID:
    RESOLUTIONS = ["Fit screen"]
    settings["resolution"] = "Fit screen"
    settings["fullscreen"] = True


FIT_SCREEN = "Fit screen"


def parse_resolution(res_str):
    """'1280x720' -> (1280, 720); "Fit screen" -> the phone's shape, 600 tall."""
    if res_str == FIT_SCREEN:
        return fit_screen_size()
    w, h = res_str.lower().split("x")
    return int(w), int(h)


def fit_screen_size():
    """A picture 600 tall (the height the game's screens are laid out for) and as wide as
    the display's shape, so a phone shows it edge to edge with no black bars. 600 rather
    than 720 also means less to draw each frame, and bigger text and buttons."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
        if dh > dw:
            dw, dh = dh, dw                          # landscape
        w = int(round(600 * dw / dh / 2)) * 2
    except Exception:
        w = 1066
    return max(800, min(1440, w)), 600


# ---------------------------------------------------------------------------
# The window
#
# Every window the game opens goes through open_window(), so the menu, the game and the
# F11 / Alt+Enter shortcut all make it the same way.
#
# The game always draws onto a fixed-size picture (800x600 in the menu, the chosen
# Resolution in game) and pygame.SCALED stretches that to the real window, keeping its
# shape (black bars where the screen is a different shape) and mapping the mouse back.
# Frames are shown with present(), which keeps the stretched picture sharp.
# Fullscreen is "desktop" fullscreen: the monitor keeps its own resolution, so switching
# is instant and doesn't shuffle the desktop.
# ---------------------------------------------------------------------------
CAPTION = "Dungeon"
_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves", "settings.json")


def prepare_display():
    """Set the SDL options the window relies on. Call before pygame.init()."""
    # smooth scaling rather than blocky
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")
    if sys.platform == "win32":
        # Work in real screen pixels. Without this, on a display scaled above 100% Windows
        # stretches the finished picture a second time after SDL has, which blurs
        # fullscreen; open_window() sizes the window for the display's scale itself.
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")


_window_handle = None


def _sdl_window():
    """A handle on the game window (to size and centre it). pygame files this handle in the
    window itself without holding on to it, and if the handle is thrown away the next
    window event reads freed memory and crashes the game — so the latest one is kept."""
    global _window_handle
    try:
        from pygame._sdl2.video import Window
        _window_handle = Window.from_display_module()
    except Exception:
        _window_handle = None
    return _window_handle


_sdl_lib = None


def _allow_smaller_window(win, min_size):
    """pygame won't let a SCALED window be smaller than the picture it shows, which leaves a
    1920x1080 game hanging off a 1920x1080 screen. Lower that limit (pygame-ce has a setting
    for it; for pygame, ask the SDL library pygame itself loaded). True if it worked."""
    global _sdl_lib
    if hasattr(type(win), "minimum_size"):
        try:
            win.minimum_size = min_size
            return True
        except Exception:
            return False
    try:
        import ctypes, glob
        if _sdl_lib is None:
            here = os.path.dirname(pygame.__file__)
            names = (glob.glob(os.path.join(here, "SDL2.dll"))                          # Windows
                     + glob.glob(os.path.join(here, ".dylibs", "libSDL2*.dylib"))       # macOS
                     + glob.glob(os.path.join(here, "..", "pygame.libs", "libSDL2*.so*")))  # Linux
            if not names:
                _sdl_lib = False
                return False
            lib = ctypes.CDLL(names[0])           # the copy pygame already has loaded
            lib.SDL_GetWindowFromID.restype = ctypes.c_void_p
            lib.SDL_GetWindowFromID.argtypes = [ctypes.c_uint32]
            lib.SDL_SetWindowMinimumSize.restype = None
            lib.SDL_SetWindowMinimumSize.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            _sdl_lib = lib
        if not _sdl_lib:
            return False
        ptr = _sdl_lib.SDL_GetWindowFromID(win.id)
        if not ptr:
            return False
        _sdl_lib.SDL_SetWindowMinimumSize(ptr, int(min_size[0]), int(min_size[1]))
        return True
    except Exception:
        _sdl_lib = False
        return False


def _display_scale():
    """How much bigger than 100% the desktop is scaled (1.25 at 125%). Only Windows needs
    this; macOS and Linux size windows in scaled units already."""
    if sys.platform != "win32":
        return 1.0
    try:
        import ctypes
        u = ctypes.windll.user32
        dpi = 0
        if pygame.display.get_surface() is not None:
            u.GetDpiForWindow.argtypes = [ctypes.c_void_p]
            dpi = u.GetDpiForWindow(pygame.display.get_wm_info()["window"])
        if not dpi:
            dpi = u.GetDpiForSystem()
        return dpi / 96.0 if dpi else 1.0
    except Exception:
        return 1.0


def _desktop_size():
    sizes = pygame.display.get_desktop_sizes()
    idx = 0
    if pygame.display.get_surface() is not None:
        win = _sdl_window()
        idx = getattr(win, "display_index", 0) or 0
    return sizes[idx] if idx < len(sizes) else sizes[0]


def _shown_size(size, fullscreen):
    """How big the picture will be on screen, in real pixels: the whole desktop when
    fullscreen; otherwise sized for the display's scaling and kept inside the desktop
    (with room for the taskbar and title bar)."""
    try:
        desk = _desktop_size()
    except Exception:
        return size
    if fullscreen:
        return desk
    w, h = size
    s = min(_display_scale(), 0.92 * desk[0] / w, 0.86 * desk[1] / h)
    return max(1, round(w * s)), max(1, round(h * s))


def _sharp_factor(size, shown):
    """How many times bigger to hand the picture over for sharp scaling (see open_window).
    1 when it isn't being enlarged."""
    if ON_ANDROID:
        return 1      # a phone's graphics chip scales fine, and the extra work drains battery
    f = min(shown[0] / size[0], shown[1] / size[1])
    if f <= 1.05:
        return 1
    k = math.ceil(f - 0.05)
    while k > 1 and k * k * size[0] * size[1] > 8_300_000:   # keep it quick: about one 4K frame
        k -= 1
    return k


def _fit_window(shown):
    """Give a windowed game its on-screen size, centred when that changed. False if the
    window couldn't be made that size."""
    win = _sdl_window()
    if win is None:
        return False
    try:
        cur = pygame.display.get_surface().get_size()
        if shown[0] < cur[0] or shown[1] < cur[1]:
            if not _allow_smaller_window(win, (min(cur[0], shown[0]), min(cur[1], shown[1]))):
                return False
        if tuple(win.size) != tuple(shown):
            from pygame._sdl2.video import WINDOWPOS_CENTERED
            win.size = shown
            win.position = WINDOWPOS_CENTERED
        return tuple(win.size) == tuple(shown)
    except Exception:
        return False


_renderer_handle = None


def _set_logical_size(size):
    """Tell SDL the picture is `size` (it's handed over bigger, see open_window), so it
    fills the window at that shape and the mouse keeps reporting game pixels."""
    global _renderer_handle
    try:
        from pygame._sdl2.video import Renderer
        _renderer_handle = Renderer.from_window(_sdl_window())
        _renderer_handle.logical_size = size
        return tuple(_renderer_handle.logical_size) == tuple(size)
    except Exception:
        _renderer_handle = None
        return False


def _set_mode(size, k, fullscreen):
    """pygame.display.set_mode for a SCALED window showing a picture k times `size`.
    Returns (display surface, k, fullscreen, scaled) as they actually came out."""
    flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
    big = (size[0] * k, size[1] * k)
    for attempt in range(2):
        try:
            return pygame.display.set_mode(big, flags), k, fullscreen, True
        except pygame.error:
            # SCALED needs an SDL renderer, and can't be added to a window that was made
            # without one. Start the display afresh once and try again.
            if attempt == 0:
                pygame.display.quit()
                pygame.display.init()
    # No renderer at all (rare software-only setups): an unscaled window. Never a plain
    # fullscreen, which would change the monitor's resolution.
    return pygame.display.set_mode(size), 1, False, False


# What the game draws on, and how it reaches the screen (see present()).
_view = {"canvas": None, "size": None, "k": 1}


def open_window(size=None, fullscreen=None):
    """Open (or re-open) the game window. `size` is the size of the picture the game draws
    (default: the menu's 800x600); `fullscreen` defaults to the Fullscreen setting.
    Returns the surface to draw on; show it with present(). If fullscreen can't be had,
    the window comes up windowed and the setting is turned off to match.

    Sharp scaling: the picture usually has to be enlarged by an awkward amount (800x600 to
    a 1920x1080 screen is 1.8x), and enlarging smoothly by that much blurs everything.
    So present() first enlarges it by a whole number with hard pixel edges (2x: 1600x1200),
    which loses nothing, and SDL then only has to shrink that a little to fit (to 1440x1080),
    which stays sharp. Pixel art keeps its crisp pixels and text stays clean."""
    size = tuple(size or (SCREEN_WIDTH, SCREEN_HEIGHT))
    if fullscreen is None:
        fullscreen = settings["fullscreen"]
    if ON_ANDROID:
        fullscreen = True
    shown = _shown_size(size, fullscreen)
    disp, k, fullscreen, scaled = _set_mode(size, _sharp_factor(size, shown), fullscreen)
    if scaled and not fullscreen and not _fit_window(shown) and k > 1:
        disp, k, fullscreen, scaled = _set_mode(size, 1, fullscreen)    # plain scaling then
        _fit_window(shown)
    if k > 1 and not _set_logical_size(size):
        disp, k, fullscreen, scaled = _set_mode(size, 1, fullscreen)
        if scaled and not fullscreen:
            _fit_window(shown)
    canvas = pygame.Surface(size).convert() if k > 1 else disp
    _view.update(canvas=canvas, size=size, k=k)
    settings["fullscreen"] = bool(fullscreen)
    pygame.display.set_caption(CAPTION)
    return canvas


def current_surface():
    """The surface the game draws on (the one open_window() last returned)."""
    return _view["canvas"] or pygame.display.get_surface()


def present():
    """Show the finished frame: use this instead of pygame.display.flip()."""
    if _view["k"] > 1 and _view["canvas"] is not None:
        disp = pygame.display.get_surface()
        if disp is not None:
            pygame.transform.scale(_view["canvas"], disp.get_size(), disp)   # hard-edged k times
            r = _renderer_handle
            try:
                if r is not None and tuple(r.logical_size) != _view["size"]:
                    r.logical_size = _view["size"]          # in case anything reset it
            except Exception:
                pass
    pygame.display.flip()


def is_fullscreen_key(event):
    """F11, or Alt+Enter: the keys that switch fullscreen on and off anywhere."""
    if event.type != pygame.KEYDOWN:
        return False
    return (event.key == pygame.K_F11
            or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                and event.mod & pygame.KMOD_ALT and not event.mod & pygame.KMOD_CTRL))


def toggle_fullscreen(size=None):
    """Flip the Fullscreen setting, re-open the window to match, remember the choice."""
    surf = open_window(size, not settings["fullscreen"])
    save_settings()
    return surf


def build_window():
    """The menu's window, from the current settings."""
    return open_window()


def load_settings():
    """Bring back the Video and Audio settings from last time (saves/settings.json)."""
    try:
        import json
        with open(_SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        return
    for key, default in list(settings.items()):
        val = saved.get(key)
        if isinstance(default, bool):
            if isinstance(val, bool):
                settings[key] = val
        elif isinstance(default, int):
            if isinstance(val, int) and not isinstance(val, bool):
                settings[key] = max(0, min(100, val))
        elif key == "resolution":
            if val in RESOLUTIONS:
                settings[key] = val
        elif key == "quality":
            if val in QUALITY_OPTS:
                settings[key] = val


def save_settings():
    """Remember the Video and Audio settings for next time. Never fails the game."""
    try:
        import json
        os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
        tmp = _SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=1)
        os.replace(tmp, _SETTINGS_FILE)
    except Exception:
        pass


load_settings()


# ---------------------------------------------------------------------------
# Background particles
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self):
        self.reset(randomize_y=True)

    def reset(self, randomize_y=False):
        self.x     = random.uniform(0, SCREEN_WIDTH)
        self.y     = random.uniform(0, SCREEN_HEIGHT) if randomize_y else SCREEN_HEIGHT + 5
        self.speed = random.uniform(0.3, 1.0)
        self.alpha = random.randint(40, 140)
        self.size  = random.randint(1, 3)

    def update(self):
        self.y -= self.speed
        if self.y < -5:
            self.reset()

    def draw(self, surface):
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (200, 180, 255, self.alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------------
# UI widgets
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, text, center_x, y, width=300, height=52, wip=False):
        self.text    = text
        self.rect    = pygame.Rect(0, 0, width, height)
        self.rect.centerx = center_x
        self.rect.y  = y
        self.wip     = wip
        self._anim   = 0.0

    def update(self, mouse_pos):
        target     = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        self._anim += (target - self._anim) * 0.18

    def draw(self, surface):
        t      = self._anim
        bg     = tuple(int(BUTTON_IDLE[i]   + (BUTTON_HOVER[i]        - BUTTON_IDLE[i])   * t) for i in range(3))
        border = tuple(int(BUTTON_BORDER[i] + (BUTTON_BORDER_HOVER[i] - BUTTON_BORDER[i]) * t) for i in range(3))
        r = self.rect
        pygame.draw.rect(surface, bg,     r, border_radius=10)
        pygame.draw.rect(surface, border, r, width=2, border_radius=10)
        col   = tuple(int(TEXT_NORMAL[i] + (TEXT_HOVER[i] - TEXT_NORMAL[i]) * t) for i in range(3))
        label = font_btn.render(self.text, True, col)
        surface.blit(label, (r.centerx - label.get_width() // 2,
                              r.centery - label.get_height() // 2))
        if self.wip:
            w = font_wip.render("W.I.P.", True, WIP_COLOR)
            surface.blit(w, (r.right - w.get_width() - 8, r.bottom - w.get_height() - 4))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


class Slider:
    def __init__(self, label, x, y, width, key):
        self.label    = label
        self.rect     = pygame.Rect(x, y, width, 8)
        self.key      = key
        self.dragging = False

    def _handle_x(self):
        return self.rect.x + int(settings[self.key] / 100 * self.rect.width)

    def update(self, events, mouse_pos):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # anywhere on the bar, not just the small handle, so a finger can grab it
                bar = pygame.Rect(self.rect.x - 10, self.rect.centery - 16, self.rect.width + 20, 32)
                if bar.collidepoint(e.pos):
                    self.dragging = True
                    mouse_pos = e.pos
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.dragging = False
        if self.dragging:
            settings[self.key] = max(0, min(100, int(
                (mouse_pos[0] - self.rect.x) / self.rect.width * 100)))

    def draw(self, surface):
        surface.blit(font_small.render(f"{self.label}: {settings[self.key]}%", True, TEXT_NORMAL),
                     (self.rect.x, self.rect.y - 24))
        pygame.draw.rect(surface, BUTTON_IDLE,         self.rect, border_radius=4)
        pygame.draw.rect(surface, BUTTON_BORDER,       self.rect, width=1, border_radius=4)
        fill = self.rect.copy()
        fill.width = int(settings[self.key] / 100 * self.rect.width)
        pygame.draw.rect(surface, BUTTON_BORDER_HOVER, fill, border_radius=4)
        hx = self._handle_x()
        pygame.draw.circle(surface, GOLD,  (hx, self.rect.centery), 9)
        pygame.draw.circle(surface, WHITE, (hx, self.rect.centery), 9, width=2)


class CycleOption:
    def __init__(self, label, x, y, key, choices, on_change=None):
        self.label     = label
        self.key       = key
        self.choices   = choices
        self.btn_l     = pygame.Rect(x,       y, 36, 36)
        self.btn_r     = pygame.Rect(x + 260, y, 36, 36)
        self.text_rect = pygame.Rect(x + 40,  y, 220, 36)
        self._y        = y
        self.on_change = on_change

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self.choices.index(settings[self.key])
            changed = False
            if self.btn_l.collidepoint(event.pos):
                settings[self.key] = self.choices[(idx - 1) % len(self.choices)]
                changed = True
            if self.btn_r.collidepoint(event.pos):
                settings[self.key] = self.choices[(idx + 1) % len(self.choices)]
                changed = True
            if changed and self.on_change:
                self.on_change()

    def draw(self, surface):
        surface.blit(font_small.render(self.label, True, TEXT_NORMAL),
                     (self.btn_l.x, self._y - 24))
        for btn, arrow in [(self.btn_l, "<"), (self.btn_r, ">")]:
            pygame.draw.rect(surface, BUTTON_IDLE,   btn, border_radius=6)
            pygame.draw.rect(surface, BUTTON_BORDER, btn, width=1, border_radius=6)
            a = font_btn.render(arrow, True, TEXT_NORMAL)
            surface.blit(a, (btn.centerx - a.get_width() // 2,
                             btn.centery - a.get_height() // 2))
        val = font_small.render(settings[self.key], True, GOLD)
        surface.blit(val, (self.text_rect.centerx - val.get_width() // 2,
                           self.text_rect.centery - val.get_height() // 2))


class ToggleButton:
    def __init__(self, label, x, y, key, on_change=None):
        self.label = label
        self.key   = key
        self.rect  = pygame.Rect(x, y, 72, 28)
        self._y    = y
        self.on_change = on_change

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                settings[self.key] = not settings[self.key]
                if self.on_change:
                    self.on_change()

    def draw(self, surface):
        surface.blit(font_small.render(self.label, True, TEXT_NORMAL),
                     (self.rect.x, self._y - 24))
        on = settings[self.key]
        pygame.draw.rect(surface, (50, 160, 80) if on else BUTTON_IDLE,
                         self.rect, border_radius=14)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, width=1, border_radius=14)
        cx = self.rect.right - 16 if on else self.rect.left + 16
        pygame.draw.circle(surface, WHITE, (cx, self.rect.centery), 10)
        t = font_wip.render("ON" if on else "OFF", True, WHITE)
        # the word sits on the side away from the knob
        tx = self.rect.x + 8 if on else self.rect.right - 8 - t.get_width()
        surface.blit(t, (tx, self.rect.centery - t.get_height() // 2))


# ---------------------------------------------------------------------------
# Credits content
# ---------------------------------------------------------------------------
CREDITS_LINES = [
    ("header", "Developer"),
    ("body",   "tayeh"),
    ("gap",    ""),
    ("header", "Designer"),
    ("body",   "tayeh"),
    ("gap",    ""),
    ("header", "Music & Assets"),
    ("body",   "pygame community"),
    ("gap",    ""),
    ("header", "Special Thanks"),
    ("body",   "Everyone who played Dungeon"),
]


# ---------------------------------------------------------------------------
# run_menu(screen, clock) → "continue" | "openworld" | "limitless" | "exit"
#
# Runs the full menu using an already-initialised pygame screen and clock.
# Returns a string so the caller decides what to do next.
# ---------------------------------------------------------------------------
def run_menu(screen, clock):
    _init_fonts()
    screen = build_window()  # ensure the window matches saved settings (e.g. fullscreen)

    def _apply_fullscreen():
        nonlocal screen
        screen = build_window()
        save_settings()

    CX = SCREEN_WIDTH // 2

    # Build buttons fresh each call so hover state is clean
    try:
        import savegame
        save_meta = savegame.meta()
    except Exception:
        save_meta = None
    if save_meta is not None:                  # an open-world save to pick back up
        btns_main = [
            Button("Continue", CX, 232),
            Button("Play",     CX, 296),
            Button("Options",  CX, 360),
            Button("Credits",  CX, 424),
            Button("Exit",     CX, 488),
        ]
    else:
        btns_main = [
            Button("Play",    CX, 240),
            Button("Options", CX, 310),
            Button("Credits", CX, 380),
            Button("Exit",    CX, 450),
        ]
    main_actions = (["continue"] if save_meta is not None else []) + ["play", "options", "credits", "exit"]
    if save_meta:
        who = " ".join(x for x in (save_meta.get("race"), save_meta.get("class")) if x)
        save_line = (f"Open World  ·  Level {save_meta.get('level', '?')} {who}  ·  "
                     f"{save_meta.get('location', '')}  ·  Day {save_meta.get('day', '?')}")
    else:
        save_line = "Open World  ·  saved game"
    btns_play = [
        Button("Story Mode",     CX, 220, wip=True),
        Button("Open World",     CX, 290),
        Button("Limitless Mode", CX, 360),
        Button("Back",           CX, 450, width=180),
    ]
    play_blurbs = {1: "Roam a vast land of villages, caves and dungeons. Save at village shrines.",
                   2: "Descend through endless dungeon chambers, wave after wave."}
    launch_mode = ["openworld"]
    btns_options = [
        Button("Video Settings", CX, 260),
        Button("Audio Settings", CX, 330),
        Button("Back",           CX, 440, width=180),
    ]
    _vx = CX - 148
    _res_opt  = CycleOption("Resolution",       _vx, 270, "resolution", RESOLUTIONS)
    _fs_tog   = ToggleButton("Fullscreen",       _vx, 362, "fullscreen", on_change=_apply_fullscreen)
    _qual_opt = CycleOption("Graphics Quality",  _vx, 432, "quality",   QUALITY_OPTS)
    btn_video_back = Button("Back", CX, 510, width=180)

    _ax = CX - 148
    _sliders = [
        Slider("Master Volume", _ax, 290, 300, "master_vol"),
        Slider("Music Volume",  _ax, 370, 300, "music_vol"),
        Slider("SFX Volume",    _ax, 450, 300, "sfx_vol"),
    ]
    btn_audio_back   = Button("Back", CX, 520, width=180)
    btn_credits_back = Button("Back", CX, 520, width=180)

    particles = [Particle() for _ in range(80)]

    # Fade state
    fade_alpha  = 255   # start faded-in (fade from black into menu)
    fade_dir    = -1    # -1 = fade in
    fade_target = SCREEN_MAIN
    fade_speed  = 8

    current_screen = SCREEN_MAIN
    tick = 0
    _saved_settings = dict(settings)

    # ── inner helpers ──────────────────────────────────────────────────────
    def start_fade_to(target):
        nonlocal fade_dir, fade_target, fade_alpha
        fade_dir    = 1
        fade_target = target
        fade_alpha  = 0

    def draw_background():
        screen.fill(DARKER_GRAY)
        for y in range(SCREEN_HEIGHT // 2):
            pygame.draw.line(screen, (20, 10, 30), (0, y), (SCREEN_WIDTH, y))
        for p in particles:
            p.draw(screen)

    def draw_title():
        pulse = math.sin(tick * 0.04) * 0.15 + 0.85
        col   = tuple(int(c * pulse) for c in GOLD)
        t = font_title.render("DUNGEON", True, col)
        screen.blit(t, (CX - t.get_width() // 2, 100))
        s = font_sub.render("Enter the darkness — if you dare.", True, SUBTITLE_COLOR)
        screen.blit(s, (CX - s.get_width() // 2, 190))

    def draw_section_title(text):
        t = font_credit_header.render(text, True, GOLD_DIM)
        screen.blit(t, (CX - t.get_width() // 2, 140))
        pygame.draw.line(screen, BUTTON_BORDER,
                         (CX - 150, 175), (CX + 150, 175), 1)

    def draw_fade():
        if fade_alpha > 0:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            s.fill(BLACK)
            s.set_alpha(fade_alpha)
            screen.blit(s, (0, 0))

    # ── main loop ──────────────────────────────────────────────────────────
    while True:
        clock.tick(FPS)
        mouse  = pygame.mouse.get_pos()
        events = pygame.event.get()

        if any(is_fullscreen_key(e) for e in events):
            screen = toggle_fullscreen()
            # the shortcut's Enter mustn't also press a button
            events = [e for e in events if not is_fullscreen_key(e)]
        if settings != _saved_settings:       # a Video / Audio setting changed
            save_settings()
            _saved_settings.update(settings)

        for e in events:
            if e.type == pygame.QUIT:
                return "exit"
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, getattr(pygame, "K_AC_BACK", -1)):
                if current_screen in (SCREEN_PLAY, SCREEN_OPTIONS, SCREEN_CREDITS):
                    start_fade_to(SCREEN_MAIN)
                elif current_screen in (SCREEN_VIDEO, SCREEN_AUDIO):
                    start_fade_to(SCREEN_OPTIONS)

        for p in particles:
            p.update()

        # ── fade logic ──
        if fade_dir == 1:
            fade_alpha = min(255, fade_alpha + fade_speed)
            if fade_alpha >= 255:
                if fade_target == _LAUNCH:
                    return launch_mode[0]   # hand off to game
                current_screen = fade_target
                fade_dir = -1
        elif fade_dir == -1:
            fade_alpha = max(0, fade_alpha - fade_speed)
            if fade_alpha <= 0:
                fade_dir = 0

        can_interact = (fade_dir == 0)

        # ── MAIN MENU ──────────────────────────────────────────────────────
        if current_screen == SCREEN_MAIN:
            for btn in btns_main:
                btn.update(mouse)
            if can_interact:
                for e in events:
                    for btn, act in zip(btns_main, main_actions):
                        if not btn.is_clicked(e):
                            continue
                        if act == "continue":
                            launch_mode[0] = "continue"; start_fade_to(_LAUNCH)
                        elif act == "play":
                            start_fade_to(SCREEN_PLAY)
                        elif act == "options":
                            start_fade_to(SCREEN_OPTIONS)
                        elif act == "credits":
                            start_fade_to(SCREEN_CREDITS)
                        else:
                            return "exit"

            draw_background()
            draw_title()
            for btn in btns_main:
                btn.draw(screen)
            if main_actions[0] == "continue" and btns_main[0].rect.collidepoint(mouse):
                t = font_small.render(save_line, True, SUBTITLE_COLOR)
                screen.blit(t, (CX - t.get_width() // 2, 556))

        # ── PLAY ───────────────────────────────────────────────────────────
        elif current_screen == SCREEN_PLAY:
            for btn in btns_play:
                btn.update(mouse)
            if can_interact:
                for e in events:
                    if btns_play[1].is_clicked(e):
                        launch_mode[0] = "openworld"; start_fade_to(_LAUNCH)
                    if btns_play[2].is_clicked(e):
                        launch_mode[0] = "limitless"; start_fade_to(_LAUNCH)
                    if btns_play[3].is_clicked(e): start_fade_to(SCREEN_MAIN)

            draw_background()
            draw_section_title("Play")
            for btn in btns_play:
                btn.draw(screen)
            for i, blurb in play_blurbs.items():
                if btns_play[i].rect.collidepoint(mouse):
                    t = font_small.render(blurb, True, SUBTITLE_COLOR)
                    screen.blit(t, (CX - t.get_width() // 2, 520))

        # ── OPTIONS ────────────────────────────────────────────────────────
        elif current_screen == SCREEN_OPTIONS:
            for btn in btns_options:
                btn.update(mouse)
            if can_interact:
                for e in events:
                    if btns_options[0].is_clicked(e): start_fade_to(SCREEN_VIDEO)
                    if btns_options[1].is_clicked(e): start_fade_to(SCREEN_AUDIO)
                    if btns_options[2].is_clicked(e): start_fade_to(SCREEN_MAIN)

            draw_background()
            draw_section_title("Options")
            for btn in btns_options:
                btn.draw(screen)

        # ── VIDEO SETTINGS ─────────────────────────────────────────────────
        elif current_screen == SCREEN_VIDEO:
            btn_video_back.update(mouse)
            if can_interact:
                for e in events:
                    _res_opt.handle_event(e)
                    _fs_tog.handle_event(e)
                    _qual_opt.handle_event(e)
                    if btn_video_back.is_clicked(e): start_fade_to(SCREEN_OPTIONS)

            draw_background()
            draw_section_title("Video Settings")
            _res_opt.draw(screen)
            hint = font_wip.render("(resolution applies when you enter the game)", True, WIP_COLOR)
            screen.blit(hint, (_res_opt.text_rect.centerx - hint.get_width() // 2, 316))
            _fs_tog.draw(screen)
            fs_hint = font_wip.render("or press F11 / Alt+Enter at any time", True, WIP_COLOR)
            screen.blit(fs_hint, (_fs_tog.rect.right + 16,
                                  _fs_tog.rect.centery - fs_hint.get_height() // 2))
            _qual_opt.draw(screen)
            btn_video_back.draw(screen)

        # ── AUDIO SETTINGS ─────────────────────────────────────────────────
        elif current_screen == SCREEN_AUDIO:
            btn_audio_back.update(mouse)
            if can_interact:
                for e in events:
                    for sl in _sliders:
                        sl.update(events, mouse)
                    if btn_audio_back.is_clicked(e): start_fade_to(SCREEN_OPTIONS)

            draw_background()
            draw_section_title("Audio Settings")
            for sl in _sliders:
                sl.draw(screen)
            btn_audio_back.draw(screen)

        # ── CREDITS ────────────────────────────────────────────────────────
        elif current_screen == SCREEN_CREDITS:
            btn_credits_back.update(mouse)
            if can_interact:
                for e in events:
                    if btn_credits_back.is_clicked(e): start_fade_to(SCREEN_MAIN)

            draw_background()
            draw_section_title("Credits")
            cy = 200
            for kind, text in CREDITS_LINES:
                if kind == "header":
                    s = font_credit_header.render(text, True, GOLD_DIM)
                    screen.blit(s, (CX - s.get_width() // 2, cy))
                    cy += 32
                elif kind == "body":
                    s = font_credit.render(text, True, CREDITS_COLOR)
                    screen.blit(s, (CX - s.get_width() // 2, cy))
                    cy += 28
                elif kind == "gap":
                    cy += 16
            btn_credits_back.draw(screen)

        draw_fade()
        present()
        tick += 1


# ---------------------------------------------------------------------------
# Stand-alone entry point (run main_menu.py directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    prepare_display()
    pygame.init()
    _screen = open_window()
    _clock = pygame.time.Clock()
    result = run_menu(_screen, _clock)
    if result in ("continue", "openworld", "limitless"):
        import subprocess, os
        game = os.path.join(os.path.dirname(os.path.abspath(__file__)), "move.py")
        pygame.quit()
        subprocess.run([sys.executable, game, "--no-menu"])
    else:
        pygame.quit()
        sys.exit()
