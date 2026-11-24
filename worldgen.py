"""
Overworld and cave generation, Pokémon-DS style.

Each stage is one overworld split into five biomes, one per Tier 1 element family, laid
around a central crossroads. Every biome holds a cave mouth set in a rock outcrop; walking
into it leads to a cave themed to match (meadow -> mossy grotto, tundra -> ice cavern, …).

This module is pure data — no pygame — so it can be generated and tested headless.
An Area is a grid of tiles plus what stands on them:

    ground[y][x]   material name used by the renderer ("grass", "sand", "water", "cfloor", …)
    solid[y][x]    1 = blocked, 0 = walkable — this is the game's world_map
    decor          {(x, y): name}   flat, walkable details (flowers, tall grass, bones, …)
    objects        {(x, y): name}   solid things with a sprite (trees, rocks, crystals, …)
    portals        {(x, y): (area_id, (x, y), facing)}   step onto it to change area

Every walkable tile of an area is guaranteed reachable from its arrival point.
"""
import heapq
import random

import numpy as np

TILE = 16                  # pixels per tile in the base-resolution art

# Biome keys double as cave themes. Element = the Tier 1 family the biome belongs to.
BIOMES = {
    "meadow":   {"name": "Verdant Meadow",   "element": "Wind",      "ground": "grass",
                 "path": "path_meadow",   "cave": "Mossy Grotto"},
    "tundra":   {"name": "Frostfell Tundra", "element": "Water",     "ground": "snow",
                 "path": "path_tundra",   "cave": "Rime Cavern"},
    "desert":   {"name": "Sunscorch Dunes",  "element": "Earth",     "ground": "sand",
                 "path": "path_desert",   "cave": "Sandstone Tomb"},
    "volcanic": {"name": "Ember Wastes",     "element": "Fire",      "ground": "ash",
                 "path": "path_volcanic", "cave": "Magma Hollow"},
    "storm":    {"name": "Stormspire Crags", "element": "Lightning", "ground": "slate",
                 "path": "path_storm",    "cave": "Crystal Vault"},
    # the neutral plain at the centre of every stage, where the five routes begin
    "hub":      {"name": "Wayfarer's Crossing", "element": None, "ground": "grass",
                 "path": "path_meadow",   "cave": None},
}
# Tall grass per biome — walking through it can flush out a wild foe or turn up an item
TALL_GRASS = {"meadow": "tallgrass", "hub": "tallgrass", "storm": "stormgrass", "tundra": "frostgrass",
              "desert": "drygrass", "volcanic": "ashgrass"}
GRASS_KINDS = set(TALL_GRASS.values())
BIOME_ORDER = [b for b in BIOMES if b != "hub"]       # the five that get a region, cave and dungeon
HUB_RADIUS = 12

OVERWORLD_W, OVERWORLD_H = 160, 120          # was 120x90 — grown to make room for villages
_AREA_SCALE = OVERWORLD_W * OVERWORLD_H / (120 * 90)

# Villages: up to three per stage, each 3-7 houses round a cobbled plaza. Every house door
# leads to its own interior (0-2 chests inside). Villages are safe ground: no tall grass,
# and foes never wander in.
VILLAGE_MAX = 3
VILLAGE_COUNT_WEIGHTS = (2, 4, 4)            # odds of 1, 2 or 3 villages
VILLAGE_HOUSES = (3, 7)
VILLAGE_H = 14                               # rows in a village plan
HOUSE_W, HOUSE_H = 5, 3                      # footprint in tiles (the roof rises a tile above)
HOUSE_CHEST_WEIGHTS = (25, 45, 30)           # odds of 0, 1 or 2 chests in a house
_VILLAGE_FIRST = ["Ash", "Bright", "Elder", "Fern", "Glen", "Hearth", "Iron", "Kestrel", "Linden", "Marrow",
                  "Oak", "Pine", "Quill", "Raven", "Silver", "Thistle", "Willow", "Amber", "Briar", "Cinder",
                  "Dusk", "Frost", "Gale", "Moss", "Stone", "Sun", "Wren", "Copper", "Hollow", "Rush"]
_VILLAGE_LAST = ["ford", "brook", "haven", "stead", "wick", "vale", "field", "hollow", "moor", "crest",
                 "dale", "bury", "mere", "ton", "well", "reach", "gate", "fall"]
FAMILY_NAMES = ["Ashby", "Brook", "Carver", "Dunmore", "Elwood", "Fairweather", "Greaves", "Hale", "Ingram",
                "Juniper", "Kettle", "Larkin", "Mallow", "Nettle", "Oakley", "Pellow", "Quarry", "Rowan",
                "Stroud", "Thorne", "Underhill", "Vance", "Whitlow", "Yarrow", "Bramble", "Cobb", "Penny"]
DUNGEONS_PER_STAGE = 2
DUNGEON_ROOMS = 5
DUNGEON_NAMES = {"meadow": "Overgrown Keep", "tundra": "Frostbound Crypt", "desert": "Buried Temple",
                 "volcanic": "Cinder Bastion", "storm": "Thunderspire Vault"}
CAVE_W, CAVE_H = 56, 40

# World profiles. "stage" is the classic stage map; "open" is the Open World mode — ten
# times the area (506x380 vs 160x120), three regions of every biome, a cave in each,
# more dungeons, a second river and villages to match.
WORLD_PROFILES = {
    "stage": {"size": (OVERWORLD_W, OVERWORLD_H), "regions": 1, "villages": (1, 3),
              "village_weights": VILLAGE_COUNT_WEIGHTS, "dungeons": DUNGEONS_PER_STAGE, "rivers": 1,
              "network": False},
    "open": {"size": (506, 380), "regions": 3, "villages": (18, 24), "village_weights": None,
             "dungeons": 6, "rivers": 2, "network": True, "save_points": True},
}
_ROMAN = ["", "", " II", " III", " IV", " V"]


def base_biome(key):
    """Region keys look like "meadow" or "meadow#2"; the biome is the part before '#'."""
    return key.split("#")[0]



# What lines the map edge in each biome (solid, impassable)
BORDER_OBJECT = {"meadow": "tree", "tundra": "pine", "desert": "rock_desert",
                 "volcanic": "rock_volcanic", "storm": "rock_storm", "hub": "tree"}
# Small solid filler used to seal off pockets that can't be reached
FILLER_OBJECT = {"meadow": "bush", "tundra": "rock_tundra", "desert": "rock_desert",
                 "volcanic": "rock_volcanic", "storm": "rock_storm", "hub": "bush"}
# Cave feature set: pool material, solid object kinds, decor kinds
CAVE_FEATURES = {
    "meadow":   {"pool": "cwater", "objects": ["stalagmite", "mushroom_big"], "decor": ["moss", "mushroom"]},
    "tundra":   {"pool": "cice",   "objects": ["icespike", "stalagmite"],     "decor": ["frost", "frost"]},
    "desert":   {"pool": None,     "objects": ["pillar", "urn"],              "decor": ["bones", "rubble"]},
    "volcanic": {"pool": "clava",  "objects": ["stalagmite", "vent"],         "decor": ["embers", "rubble"]},
    "storm":    {"pool": "cwater", "objects": ["crystal", "crystal_small"],   "decor": ["shards", "moss"]},
}
# Materials that block movement
SOLID_GROUND = {"water", "lava", "cwater", "clava", "cwall", "cliff", "waterfall"}   # "bridge", "stairs" walk
CLIFF_GROUND = {"cliff", "stairs", "waterfall"}       # the faces of hills: never blended, never carved
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


class Area:
    def __init__(self, area_id, kind, theme, name, w, h):
        self.id, self.kind, self.theme, self.name = area_id, kind, theme, name
        self.w, self.h = w, h
        self.ground = [[""] * w for _ in range(h)]
        self.solid = [[0] * w for _ in range(h)]
        self.biome = None                  # overworld only: biome key per tile
        self.decor, self.objects, self.portals = {}, {}, {}
        self.start = (w // 2, h // 2)      # arrival tile
        self.outdoor = kind == "overworld"
        self.height = None                 # overworld: ground level per tile (0 low, 1 hill, 2 mountain)
        self.mouths = {}                   # overworld: biome -> mouth tile
        self.gates = {}                    # overworld: biome -> dungeon gate tile
        self.rooms = []                    # dungeon: [{"rect", "door", "back", "waves", "center"}]
        self.villages = []                 # overworld: [{"name", "biome", "rect", "plaza", "houses", ...}]
        self.safe = set()                  # overworld: village ground foes never step on
        self.chest_spots = []              # house: where its chests stand
        self.doors = {}                    # dungeon: door tile -> index of the room it leads out of

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def walkable(self, x, y):
        return self.in_bounds(x, y) and not self.solid[y][x]

    def can_step(self, a, b, ignore_solid=False):
        """Whether one step from tile a to tile b is allowed. On the overworld you can only
        change level on stairs, and stairs climb north-south."""
        (x, y), (nx, ny) = a, b
        if not self.in_bounds(nx, ny):
            return False
        if not ignore_solid and self.solid[ny][nx]:
            return False
        if self.height is None or not self.in_bounds(x, y):
            return True
        if self.ground[y][x] == "stairs" or self.ground[ny][nx] == "stairs":
            return nx == x
        return self.height[y][x] == self.height[ny][nx]

    def room_at(self, x, y):
        """Dungeon room index containing this tile (interior only), or None."""
        for i, r in enumerate(self.rooms):
            x0, y0, x1, y1 = r["rect"]
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None

    def label_at(self, x, y):
        """Location name shown to the player for this tile."""
        for v in self.villages:
            x0, y0, x1, y1 = v["rect"]
            if x0 <= x <= x1 and y0 <= y <= y1:
                return v["name"]
        if self.biome is not None and self.in_bounds(x, y):
            return BIOMES[self.biome[y][x]]["name"]
        if self.kind == "dungeon":
            i = self.room_at(x, y)
            if i is not None:
                return f"{self.name} · Room {i + 1}/{len(self.rooms)}"
        return self.name

    def refresh_solid(self):
        """Rebuild the collision grid from ground + objects."""
        for y in range(self.h):
            row_g, row_s = self.ground[y], self.solid[y]
            for x in range(self.w):
                row_s[x] = 1 if row_g[x] in SOLID_GROUND or (x, y) in self.objects else 0

    def reachable(self, start=None):
        """Every tile walkable from `start`. The same rules as can_step, inlined: this runs
        over the whole map many times while a stage is generated."""
        sx, sy = start or self.start
        W, H = self.w, self.h
        solid, ground, height = self.solid, self.ground, self.height
        seen = {(sx, sy)}
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            on_stairs = height is not None and ground[y][x] == "stairs"
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H) or solid[ny][nx] or (nx, ny) in seen:
                    continue
                if height is not None:
                    if on_stairs or ground[ny][nx] == "stairs":
                        if dx:
                            continue
                    elif height[y][x] != height[ny][nx]:
                        continue
                seen.add((nx, ny))
                stack.append((nx, ny))
        return seen

    def spawn_tiles(self, avoid=(), min_dist=0):
        """Reachable walkable tiles that are not portals (for enemies and chests)."""
        sx, sy = self.start
        out = []
        for t in self.reachable():
            if t in self.portals or t in avoid:
                continue
            if min_dist and abs(t[0] - sx) + abs(t[1] - sy) < min_dist:
                continue
            out.append(t)
        out.sort()
        return out


# ---------------------------------------------------------------------------- noise

def value_noise(w, h, cell, rng, octaves=3):
    """Smooth 0..1 noise of shape (h, w); `cell` = feature size in tiles."""
    total = np.zeros((h, w))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = max(1.0, cell / (2 ** o))
        gw, gh = int(w / c) + 3, int(h / c) + 3
        grid = rng.random((gh, gw))
        ys = np.arange(h) / c
        xs = np.arange(w) / c
        y0 = ys.astype(int); x0 = xs.astype(int)
        fy = ys - y0; fx = xs - x0
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        a = grid[np.ix_(y0, x0)]; b = grid[np.ix_(y0, x0 + 1)]
        c_ = grid[np.ix_(y0 + 1, x0)]; d = grid[np.ix_(y0 + 1, x0 + 1)]
        top = a + (b - a) * fx[None, :]
        bot = c_ + (d - c_) * fx[None, :]
        total += amp * (top + (bot - top) * fy[:, None])
        norm += amp
        amp *= 0.5
    return total / norm


# ---------------------------------------------------------------------------- paths

def astar(area, start, goal, cost_fn):
    """Cheapest 4-way path; cost_fn(x, y) -> step cost or None if impassable."""
    if start == goal:
        return [start]
    W, H, ground, height = area.w, area.h, area.ground, area.height
    gx, gy = goal
    openq = [(0, 0, start)]
    came = {start: None}
    best = {start: 0}
    n = 0
    while openq:
        _, g, cur = heapq.heappop(openq)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        if g > best.get(cur, 1e18):
            continue
        x, y = cur
        on_stairs = height is not None and ground[y][x] == "stairs"
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if height is not None:                     # can_step(ignore_solid=True), inlined
                if on_stairs or ground[ny][nx] == "stairs":
                    if dx:
                        continue
                elif height[y][x] != height[ny][nx]:
                    continue
            c = cost_fn(nx, ny)
            if c is None:
                continue
            ng = g + c
            if ng < best.get((nx, ny), 1e18):
                best[(nx, ny)] = ng
                came[(nx, ny)] = cur
                n += 1
                heapq.heappush(openq, (ng + abs(nx - gx) + abs(ny - gy), ng, (nx, ny)))
    return None


def _resolid(area, x, y):
    area.solid[y][x] = 1 if area.ground[y][x] in SOLID_GROUND or (x, y) in area.objects else 0


def _flood_new(area, start, known):
    """Tiles walkable from `start` that aren't in `known` yet (the flood stops at known
    tiles). Returns (new tiles, whether it ran into `known`)."""
    W, H = area.w, area.h
    solid, ground, height = area.solid, area.ground, area.height
    seen = {start}
    stack = [start]
    touched = False
    while stack:
        x, y = stack.pop()
        on_stairs = height is not None and ground[y][x] == "stairs"
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H) or solid[ny][nx] or (nx, ny) in seen:
                continue
            if height is not None:
                if on_stairs or ground[ny][nx] == "stairs":
                    if dx:
                        continue
                elif height[y][x] != height[ny][nx]:
                    continue
            if (nx, ny) in known:
                touched = True
                continue
            seen.add((nx, ny))
            stack.append((nx, ny))
    return seen, touched


def _path_to_set(area, start, targets, cost_fn):
    """Cheapest route from start to the nearest tile of `targets` (Dijkstra)."""
    W, H, ground, height = area.w, area.h, area.ground, area.height
    openq = [(0, start)]
    came = {start: None}
    best = {start: 0}
    while openq:
        g, cur = heapq.heappop(openq)
        if cur in targets and cur != start:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        if g > best.get(cur, 1e18):
            continue
        x, y = cur
        on_stairs = height is not None and ground[y][x] == "stairs"
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if height is not None:                     # can_step(ignore_solid=True), inlined
                if on_stairs or ground[ny][nx] == "stairs":
                    if dx:
                        continue
                elif height[y][x] != height[ny][nx]:
                    continue
            c = cost_fn(nx, ny)
            if c is None:
                continue
            ng = g + c
            if ng < best.get((nx, ny), 1e18):
                best[(nx, ny)] = ng
                came[(nx, ny)] = cur
                heapq.heappush(openq, (ng, (nx, ny)))
    return None


def connect_pockets(area, carve, fill, min_pocket=10, protected=(), progress=None):
    """Make every walkable tile reachable from area.start. Pockets of at least `min_pocket`
    tiles are joined by carving the cheapest route; smaller ones are filled in.

    One pass over the map with a moving cursor: filled pockets turn solid and joined ones
    join `main`, so nothing behind the cursor ever needs looking at again, and `main` grows
    by flooding out from each joined pocket instead of being recomputed from scratch."""
    area.refresh_solid()
    W, H = area.w, area.h

    def cost(x, y):
        if (x, y) in protected or x in (0, W - 1) or y in (0, H - 1):
            return None
        if area.ground[y][x] in CLIFF_GROUND:
            return None                                  # cliffs are only crossed by stairs
        return 1 if not area.solid[y][x] else 5

    for _pass in range(4):
        main = area.reachable()
        pos, steps, left_open = 0, 0, False
        while True:
            pocket = None
            while pos < W * H:
                y, x = divmod(pos, W)
                if not area.solid[y][x] and (x, y) not in main:
                    pocket = (x, y)
                    break
                pos += 1
            if pocket is None:
                break
            steps += 1
            if progress and steps % 25 == 0:
                progress(None)
            comp = area.reachable(pocket)
            if len(comp) < min_pocket:
                for t in comp:
                    fill(*t)
                    _resolid(area, *t)
                continue
            path = _path_to_set(area, pocket, main, cost)
            if path is None:
                # walled in by cliffs: cut stairs into a face that leads out of the pocket
                exits = []
                for (x, y) in comp:
                    for d in (-1, 1):
                        cy_, oy = y + d, y + 2 * d
                        if 0 <= oy < H and area.ground[cy_][x] == "cliff" and not area.solid[oy][x] \
                                and (x, oy) not in comp:
                            exits.append((x, cy_))
                if exits:
                    ex, ey = min(exits)
                    area.ground[ey][ex] = "stairs"
                    _resolid(area, ex, ey)
                else:
                    for t in comp:
                        fill(*t)
                        _resolid(area, *t)
                    continue
            else:
                for t in path:
                    carve(*t)
                    _resolid(area, *t)
            new, touched = _flood_new(area, pocket, main)
            if touched:
                main |= new
            else:
                left_open = True                      # joined to another pocket — next pass
                main |= new                           # (skip it for the rest of this pass)
        if not left_open:
            return


# ---------------------------------------------------------------------------- overworld

def _merge_fragments(labels):
    """Keep one connected region per label; any smaller stray piece joins whichever
    region surrounds it most."""
    H, W = labels.shape
    comp = -np.ones((H, W), int)
    comps = []                                            # (label, tiles)
    for y in range(H):
        for x in range(W):
            if comp[y, x] >= 0:
                continue
            lab, cid = labels[y, x], len(comps)
            stack, tiles = [(x, y)], []
            comp[y, x] = cid
            while stack:
                cx_, cy_ = stack.pop()
                tiles.append((cx_, cy_))
                for dx, dy in DIRS:
                    nx, ny = cx_ + dx, cy_ + dy
                    if 0 <= nx < W and 0 <= ny < H and comp[ny, nx] < 0 and labels[ny, nx] == lab:
                        comp[ny, nx] = cid
                        stack.append((nx, ny))
            comps.append((lab, tiles))
    biggest = {}
    for cid, (lab, tiles) in enumerate(comps):
        if lab not in biggest or len(tiles) > len(comps[biggest[lab]][1]):
            biggest[lab] = cid
    out = labels.copy()
    for cid, (lab, tiles) in sorted(enumerate(comps), key=lambda c: len(c[1][1])):
        if biggest[lab] == cid:
            continue
        votes = {}
        for (x, y) in tiles:
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and out[ny, nx] != lab:
                    votes[out[ny, nx]] = votes.get(out[ny, nx], 0) + 1
        if votes:
            new = max(votes, key=votes.get)
            for (x, y) in tiles:
                out[y, x] = new
    return out


def _open_mask(m, it=1):
    """Morphological opening: strips spurs and one-tile necks from a boolean mask."""
    for _ in range(it):
        p = np.pad(m, 1)
        m = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    for _ in range(it):
        p = np.pad(m, 1)
        m = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m


def _erode(m, it):
    for _ in range(it):
        p = np.pad(m, 1)
        m = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] \
            & p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return m


def _build_hills(area, rng, nrng, avoid):
    """Raise plateaus (level 1) and mountains on them (level 2). Every drop to the south gets
    a cliff face — Pokémon's 3/4 view — and each face run has stairs cut into it. A few
    faces carry a waterfall from a stream on top into a pool below."""
    W, H = area.w, area.h
    # Sample the height noise on a coarse 3-tile grid and blow it back up: plateaus come out
    # blocky with long straight faces, like hand-placed Pokémon ledges, not ragged blobs.
    BLK = 5
    coarse = value_noise(W // BLK + 2, H // BLK + 2, 4, nrng, octaves=2)
    elev = np.repeat(np.repeat(coarse, BLK, axis=0), BLK, axis=1)[:H, :W]
    ok = np.ones((H, W), bool)
    ok[:5, :] = ok[-6:, :] = False
    ok[:, :5] = ok[:, -6:] = False
    for (x, y) in avoid:
        ok[max(0, y - 3):y + 4, max(0, x - 3):x + 4] = False
    for y in range(H):
        for x in range(W):
            if area.biome[y][x] == "hub":
                ok[y, x] = False
    lvl1 = _open_mask((elev > 0.57) & ok, 2)
    lvl2 = _open_mask((elev > 0.74) & _erode(lvl1, 3), 2)
    height = lvl1.astype(int) + lvl2.astype(int)
    area.height = [[int(height[y, x]) for x in range(W)] for y in range(H)]
    # plateau tops are open lookouts: thin the woods up there to a few lone trees
    for (x, y) in list(area.objects):
        if area.height[y][x] > 0 and rng.random() > 0.12:
            del area.objects[(x, y)]
    # cliff faces: the tile just south of any drop
    faces = []
    for y in range(H - 1):
        for x in range(W):
            if area.height[y][x] > area.height[y + 1][x]:
                area.ground[y + 1][x] = "cliff"
                area.objects.pop((x, y + 1), None)
                area.decor.pop((x, y + 1), None)
                faces.append((x, y + 1))
    # stairs (and the odd waterfall) along each horizontal run of face
    face_set = set(faces)
    seen = set()
    for (x, y) in sorted(faces, key=lambda t: (t[1], t[0])):
        if (x, y) in seen:
            continue
        run = []
        while (x, y) in face_set:
            run.append((x, y)); seen.add((x, y)); x += 1
        if len(run) < 3:
            continue
        inner = run[1:-1]
        n_stairs = max(1, len(run) // 9)
        picks = sorted(rng.sample(inner, min(n_stairs, len(inner))))
        for (sx, sy) in picks:
            area.ground[sy][sx] = "stairs"
            for (cx, cy) in ((sx, sy - 1), (sx, sy + 1)):      # clear landings top and bottom
                area.objects.pop((cx, cy), None)
                if area.ground[cy][cx] in ("water", "lava", "ice"):
                    area.ground[cy][cx] = BIOMES[area.biome[cy][cx]]["ground"]
        free = [t for t in inner if area.ground[t[1]][t[0]] == "cliff"
                and all(abs(t[0] - p[0]) > 2 for p in picks)]
        if len(run) >= 4 and free and rng.random() < 0.8 and area.biome[run[0][1]][run[0][0]] != "volcanic":
            wx, wy = rng.choice(free)
            area.ground[wy][wx] = "waterfall"
            top_h = area.height[wy - 1][wx]
            for k in range(1, rng.randint(3, 6)):                  # a stream feeding it
                ty = wy - k
                if ty < 3 or area.height[ty][wx] != top_h or area.ground[ty][wx] in CLIFF_GROUND:
                    break
                area.ground[ty][wx] = "water"; area.objects.pop((wx, ty), None); area.decor.pop((wx, ty), None)
            for py in (wy + 1, wy + 2):                            # and the pool it lands in
                for px in (wx - 1, wx, wx + 1):
                    if area.in_bounds(px, py) and area.ground[py][px] not in CLIFF_GROUND:
                        area.ground[py][px] = "water"; area.objects.pop((px, py), None); area.decor.pop((px, py), None)
            area.waterfalls = getattr(area, "waterfalls", []) + [(wx, wy)]
    # every plateau gets at least one way up, cut into the middle of its longest face
    seen = set()
    for y in range(H):
        for x in range(W):
            h = area.height[y][x]
            if h == 0 or (x, y) in seen or area.ground[y][x] in CLIFF_GROUND:
                continue
            region, stack = [], [(x, y)]
            seen.add((x, y))
            while stack:
                cx_, cy_ = stack.pop()
                region.append((cx_, cy_))
                for dx, dy in DIRS:
                    nx, ny = cx_ + dx, cy_ + dy
                    if area.in_bounds(nx, ny) and (nx, ny) not in seen and area.height[ny][nx] == h                             and area.ground[ny][nx] not in CLIFF_GROUND:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            rs = set(region)
            if any(area.ground[ty + 1][tx] == "stairs" or area.ground[ty - 1][tx] == "stairs" for (tx, ty) in region):
                continue
            cands = [(tx, ty + 1) for (tx, ty) in region
                     if area.ground[ty + 1][tx] == "cliff" and ty + 2 < H
                     and area.ground[ty + 2][tx] not in CLIFF_GROUND and (tx - 1, ty) in rs and (tx + 1, ty) in rs]
            if not cands:
                continue
            sx, sy = cands[len(cands) // 2]
            area.ground[sy][sx] = "stairs"
            for (cx_, cy_) in ((sx, sy - 1), (sx, sy + 1)):
                area.objects.pop((cx_, cy_), None)
                if area.ground[cy_][cx_] in ("water", "lava", "ice"):
                    area.ground[cy_][cx_] = BIOMES[area.biome[cy_][cx_]]["ground"]


def _clear_tile(area, x, y, material=None):
    area.objects.pop((x, y), None)
    area.decor.pop((x, y), None)
    if area.ground[y][x] in ("water", "lava"):
        area.ground[y][x] = BIOMES[area.biome[y][x]]["ground"]
    if material:
        area.ground[y][x] = material


def _scatter_seeds(rng, keys, W, H):
    """Region seeds spread over the map (best-candidate sampling), clear of the centre."""
    pts = []
    cx, cy = W / 2, H / 2
    for _ in keys:
        best = None
        for _ in range(40):
            x, y = rng.uniform(W * 0.06, W * 0.94), rng.uniform(H * 0.06, H * 0.94)
            if (x - cx) ** 2 + ((y - cy) * 1.25) ** 2 < (HUB_RADIUS * 3) ** 2:
                continue
            d = min([(x - px) ** 2 + (y - py) ** 2 for px, py in pts] + [((x - cx) ** 2 + (y - cy) ** 2) * 0.6])
            if best is None or d > best[0]:
                best = (d, x, y)
        pts.append((best[1], best[2]))
    order = keys[:]
    rng.shuffle(order)
    return [(k, x, y) for k, (x, y) in zip(order, pts)]


def generate_overworld(rng, stage=1, profile="stage", progress=None):
    prof = WORLD_PROFILES[profile]
    W, H = prof["size"]
    scale = W * H / (120 * 90)
    tick = progress or (lambda f: None)
    nrng = np.random.default_rng(rng.randrange(2 ** 32))
    area = Area("overworld", "overworld", None, "Overworld", W, H)
    area.profile = profile

    # Biome regions: seeds (five on a jittered ring for a stage; three of every biome spread
    # across the map in the open world), nearest-seed with a noise warp so the borders
    # wander instead of running in straight lines.
    cx, cy = W / 2, H / 2
    if prof["regions"] == 1:
        order = BIOME_ORDER[:]
        rng.shuffle(order)
        base = rng.random() * 6.283
        seeds = []
        for i, b in enumerate(order):
            a = base + i * 6.283 / len(order) + rng.uniform(-0.3, 0.3)
            r = rng.uniform(0.26, 0.36)
            seeds.append((b, cx + np.cos(a) * W * r, cy + np.sin(a) * H * r))
    else:
        keys = [b if k == 0 else f"{b}#{k + 1}" for b in BIOME_ORDER for k in range(prof["regions"])]
        seeds = _scatter_seeds(rng, keys, W, H)
    # A gentle warp only: a strong one scattered stray islands of one biome inside another,
    # so walking across a little patch announced a whole different region.
    warp_x = (value_noise(W, H, 20, nrng) - 0.5) * 12
    warp_y = (value_noise(W, H, 20, nrng) - 0.5) * 12
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx + warp_x, yy + warp_y
    dists = np.stack([(px - sx) ** 2 + ((py - sy) * 1.25) ** 2 for _, sx, sy in seeds])
    labels = np.argmin(dists, axis=0)
    hub = len(seeds)                                      # the neutral plain in the middle
    labels[(px - cx) ** 2 + ((py - cy) * 1.25) ** 2 < HUB_RADIUS ** 2] = hub
    labels = _merge_fragments(labels)
    tick(0.08)
    names = [b for b, _, _ in seeds] + ["hub"]
    bases = [base_biome(n) for n in names]
    area.biome = [[bases[labels[y, x]] for x in range(W)] for y in range(H)]
    area.region_names = names
    area.region_map = labels                       # region index per tile (numpy)
    area.biome_centers = {}
    for i, b in enumerate(names):
        ys, xs = np.nonzero(labels == i)
        if len(xs):
            area.biome_centers[b] = (int(xs.mean()), int(ys.mean()))

    clusters = value_noise(W, H, 7, nrng)
    pools = value_noise(W, H, 9, nrng)
    grass = value_noise(W, H, 5, nrng)
    for y in range(H):
        for x in range(W):
            b = area.biome[y][x]
            area.ground[y][x] = BIOMES[b]["ground"]
            edge = x < 2 or y < 2 or x >= W - 2 or y >= H - 2
            if edge:
                area.objects[(x, y)] = BORDER_OBJECT[b]
                continue
            c, p, g, r = clusters[y, x], pools[y, x], grass[y, x], rng.random()
            if b == "meadow":
                if p > 0.72: area.ground[y][x] = "water"
                elif c > 0.66 or r < 0.015: area.objects[(x, y)] = "tree"
                elif g > 0.58: area.decor[(x, y)] = "tallgrass"
                elif r < 0.06: area.decor[(x, y)] = rng.choice(("flowers_red", "flowers_yellow", "flowers_white"))
                elif r < 0.07: area.objects[(x, y)] = "rock_meadow"
            elif b == "tundra":
                if p > 0.70: area.ground[y][x] = "ice"
                elif c > 0.64 or r < 0.018: area.objects[(x, y)] = "pine"
                elif g > 0.62: area.decor[(x, y)] = "frostgrass"
                elif r < 0.03: area.objects[(x, y)] = "rock_tundra"
                elif r < 0.07: area.decor[(x, y)] = "snowtuft"
            elif b == "desert":
                if p > 0.82: area.ground[y][x] = "water"          # oasis
                elif c > 0.74: area.objects[(x, y)] = "rock_desert"
                elif g > 0.66: area.decor[(x, y)] = "drygrass"
                elif r < 0.022: area.objects[(x, y)] = "cactus"
                elif r < 0.035: area.decor[(x, y)] = "bones"
                elif r < 0.07: area.decor[(x, y)] = "pebbles"
            elif b == "volcanic":
                if p > 0.70: area.ground[y][x] = "lava"
                elif c > 0.66: area.objects[(x, y)] = "rock_volcanic"
                elif r < 0.016: area.objects[(x, y)] = "deadtree"
                elif g > 0.64: area.decor[(x, y)] = "ashgrass"
                elif r < 0.06: area.decor[(x, y)] = "embers"
            elif b == "hub":                                   # an open, flowered plain
                if c > 0.80: area.objects[(x, y)] = "tree"
                elif g > 0.70: area.decor[(x, y)] = "tallgrass"
                elif r < 0.10: area.decor[(x, y)] = rng.choice(("flowers_red", "flowers_yellow", "flowers_white"))
            elif b == "storm":
                if p > 0.80: area.ground[y][x] = "water"
                elif c > 0.70 or r < 0.01: area.objects[(x, y)] = "crystal"
                elif r < 0.025: area.objects[(x, y)] = "rock_storm"
                elif g > 0.62: area.decor[(x, y)] = "stormgrass"
                elif r < 0.05: area.decor[(x, y)] = "shards"

    tick(0.18)
    # --- Obstacles, so routes have to be found rather than walked in straight lines ---
    # 1) Region borders become walls (tree lines, rock ridges) with only a few passes.
    passes = value_noise(W, H, 3, nrng)
    for y in range(2, H - 3):
        for x in range(2, W - 3):
            b = area.biome[y][x]
            lab = labels[y, x]
            if (labels[y, x + 1] != lab or labels[y + 1, x] != lab) and passes[y, x] < 0.75 \
                    and "hub" not in (b, area.biome[y][x + 1], area.biome[y + 1][x]):
                area.objects[(x, y)] = BORDER_OBJECT[b]
                area.decor.pop((x, y), None)
                if area.ground[y][x] in ("water", "lava", "ice"):
                    area.ground[y][x] = BIOMES[b]["ground"]
    # 2) Bent ridges inside the biomes, each with a gap to slip through.
    for _ in range(int(12 * scale)):
        x, y = rng.randint(8, W - 9), rng.randint(8, H - 9)
        dx, dy = rng.choice(DIRS)
        length = rng.randint(12, 26)
        gap = rng.randint(3, length - 4)
        for i in range(length):
            if abs(i - gap) > 1 and 3 <= x < W - 3 and 3 <= y < H - 3:
                area.objects[(x, y)] = BORDER_OBJECT[area.biome[y][x]]
                area.decor.pop((x, y), None)
            if rng.random() < 0.22:
                dx, dy = rng.choice(((dy, dx), (-dy, -dx)))     # turn a corner
            x += dx; y += dy
    # 3) Rivers (lava through the Ember Wastes) cutting across the map; bridges cross them.
    river = []
    first_vertical = rng.random() < 0.5
    for ri in range(prof["rivers"]):
        vertical = first_vertical if ri % 2 == 0 else not first_vertical
        span, across = (H, W) if vertical else (W, H)
        pos = rng.randint(int(across * 0.3), int(across * 0.7))
        course = {}                                       # t -> where the river runs at t
        for t in range(2, span - 2):
            if rng.random() < 0.45:
                pos = max(6, min(across - 8, pos + rng.choice((-1, 1))))
            course[t] = pos
            for k in (0, 1):
                x, y = (pos + k, t) if vertical else (t, pos + k)
                area.ground[y][x] = "lava" if area.biome[y][x] == "volcanic" else "water"
                area.objects.pop((x, y), None)
                area.decor.pop((x, y), None)
                river.append((x, y))
        n_bridges = max(3, span // 40)
        piece = (span - 16) // n_bridges
        for i in range(n_bridges):                        # bridges spread along its length
            t = rng.randint(8 + i * piece, 8 + (i + 1) * piece - 1)
            for k in range(-1, 3):
                x, y = (course[t] + k, t) if vertical else (t, course[t] + k)
                if area.in_bounds(x, y) and area.ground[y][x] in ("water", "lava"):
                    area.ground[y][x] = "bridge"
    area.river = river
    tick(0.26)
    _build_hills(area, rng, nrng, avoid=river)
    tick(0.40)
    for (x, y), obj in list(area.objects.items()):
        if area.ground[y][x] in CLIFF_GROUND:
            del area.objects[(x, y)]

    # Central crossroads where every stage begins
    sx, sy = W // 2, H // 2
    area.start = (sx, sy)
    for y in range(sy - 3, sy + 4):
        for x in range(sx - 3, sx + 4):
            if abs(x - sx) + abs(y - sy) <= 4:
                _clear_tile(area, x, y)

    # Villages: flat open ground away from the crossroads and from each other
    protected = set()
    village_zone = _place_villages(area, rng, (sx, sy), river, protected, prof)
    tick(0.50)

    # Cave mouths (one per biome, in a 3x2 rock outcrop) and dungeon gates (3x2 stone
    # ruins) — each a structure whose middle-bottom tile is the way in.

    def place_structure(b, bx, by, spread, sprite, part, store):
        best = None
        taken = list(area.mouths.values()) + list(area.gates.values())
        for _ in range(500):
            mx = int(bx + rng.uniform(-spread, spread)); my = int(by + rng.uniform(-spread * 0.8, spread * 0.8))
            if not (5 <= mx < W - 5 and 5 <= my < H - 6):
                continue
            if any(names[labels[yy, xx]] != b or area.ground[yy][xx] in CLIFF_GROUND
                   or area.height[yy][xx] != area.height[my][mx]
                   for yy in range(my - 2, my + 3) for xx in range(mx - 2, mx + 3)):
                continue
            if abs(mx - sx) + abs(my - sy) < 12:
                continue
            if any((xx, yy) in village_zone for yy in range(my - 3, my + 4) for xx in range(mx - 3, mx + 4)):
                continue
            if any(abs(mx - ox) + abs(my - oy) < 10 for ox, oy in taken):
                continue
            score = (mx - bx) ** 2 + (my - by) ** 2
            if best is None or score < best[0]:
                best = (score, mx, my)
        if best is None:
            return
        _, mx, my = best
        for yy in range(my - 2, my + 3):
            for xx in range(mx - 2, mx + 3):
                _clear_tile(area, xx, yy)
        for xx in (mx - 1, mx, mx + 1):
            for yy in (my - 1, my):
                if (xx, yy) != (mx, my):
                    area.objects[(xx, yy)] = part
                protected.add((xx, yy))
        area.objects[(mx, my - 1)] = sprite              # the sprite anchors here
        store[b] = (mx, my)
        protected.add((mx, my + 1))

    spread = scale ** 0.5 if prof["regions"] == 1 else (scale / prof["regions"] / 5) ** 0.5 * 2
    for b, bx, by in seeds:
        place_structure(b, bx, by, 9 * spread, "outcrop_" + base_biome(b), "outcrop_part", area.mouths)
    for b, bx, by in rng.sample(seeds, min(prof["dungeons"], len(seeds))):
        # deeper into the biome than its cave, so the two don't crowd each other
        ox, oy = bx + (bx - W / 2) * 0.35, by + (by - H / 2) * 0.35
        if prof["regions"] > 1:
            ox, oy = bx + rng.uniform(-12, 12), by + rng.uniform(-10, 10)
        place_structure(b, ox, oy, 14 * spread, "gate_" + base_biome(b), "outcrop_part", area.gates)
    tick(0.56)

    area.refresh_solid()

    # Paths from the crossroads to each cave mouth — routes through each biome
    fronts = [(m[0], m[1] + 1) for m in list(area.mouths.values()) + list(area.gates.values())]

    def path_cost(x, y):
        if (x, y) in protected and (x, y) not in fronts:
            return None
        if x < 2 or y < 2 or x >= W - 2 or y >= H - 2:
            return None
        if area.ground[y][x] in ("cliff", "waterfall"):
            return None
        if area.ground[y][x] == "stairs":
            return 1.0
        if area.ground[y][x] == "bridge":
            return 0.6
        if area.ground[y][x] in ("water", "lava"):
            return 80                                # only cross where it must — as a bridge
        if (x, y) in area.objects:
            return 60                                # walls and woods are walked around
        if area.ground[y][x].startswith("path_"):
            return 0.4
        return 1.0 + (0.6 if area.decor.get((x, y)) in GRASS_KINDS else 0)
    places = [(mx, my + 1) for (mx, my) in list(area.mouths.values()) + list(area.gates.values())]
    in_village = set()
    for v in area.villages:
        x0, y0, x1, y1 = v["rect"]
        in_village |= {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
    near = lambda a_, b_: abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
    # Villages are the road's waystations: they're joined up first, and both their gates
    # (the south road and the north lane) become places a road can set out from — so a
    # road to a cave or a dungeon runs through the village nearest it when that's shorter.
    vgoals = sorted((v["approach"] for v in area.villages), key=lambda t: near(t, (sx, sy)))
    places.sort(key=lambda t: near(t, (sx, sy)))
    total = max(1, len(vgoals) + len(places))
    nodes = [(sx, sy)]
    routes = []
    for gi, goal in enumerate(vgoals + places):
        src = min(nodes, key=lambda t: near(t, goal))
        route = astar(area, src, goal, path_cost)
        routes.append(route)
        if route:
            if prof["network"]:
                nodes.extend(route[::6])      # big maps: join whatever road is nearest
            nodes.append(goal)
            vil = next((v for v in area.villages if v["approach"] == goal), None)
            if vil is not None:
                nodes.append(vil["north"])
        tick(0.56 + 0.2 * (gi + 1) / total)
    for route in routes:
        for (x, y) in route or ():
            if (x, y) in in_village:
                continue
            if area.ground[y][x] == "stairs":
                area.objects.pop((x, y), None)
            elif area.ground[y][x] in ("water", "lava", "bridge"):
                area.objects.pop((x, y), None)
                area.ground[y][x] = "bridge"
            else:
                _clear_tile(area, x, y, BIOMES[area.biome[y][x]]["path"])
    for v in area.villages:                    # the road runs right up to each gate
        for (x, y) in v["stubs"]:
            _clear_tile(area, x, y, BIOMES[area.biome[y][x]]["path"])
            protected.add((x, y))
    for y in range(sy - 1, sy + 2):
        for x in range(sx - 1, sx + 2):
            area.ground[y][x] = BIOMES[area.biome[y][x]]["path"]

    # Portals: the mouth tile itself
    for b, (mx, my) in area.mouths.items():
        area.objects.pop((mx, my), None)
        area.decor.pop((mx, my), None)
        area.portals[(mx, my)] = ("cave_" + b, None, "up")   # arrival filled in by the cave
    for b, (gx, gy) in area.gates.items():
        area.objects.pop((gx, gy), None)
        area.decor.pop((gx, gy), None)
        area.portals[(gx, gy)] = ("dungeon_" + b, None, "up")
    for vi, v in enumerate(area.villages):                 # house doors (arrivals wired by the stage)
        for hi, h in enumerate(v["houses"]):
            area.portals[h["door"]] = (f"house_{vi}_{hi}", None, "up")

    def fill(x, y):
        area.objects[(x, y)] = FILLER_OBJECT[area.biome[y][x]]

    def carve(x, y):
        if (x, y) in protected or area.ground[y][x] in CLIFF_GROUND:
            return
        _clear_tile(area, x, y)

    tick(0.78)
    connect_pockets(area, carve, fill, min_pocket=10, protected=protected, progress=tick)
    tick(0.92)
    return area


# ---------------------------------------------------------------------------- villages

def _village_name(rng, used):
    for _ in range(50):
        n = rng.choice(_VILLAGE_FIRST) + rng.choice(_VILLAGE_LAST)
        if n not in used:
            return n
    return n


def _village_plan(n):
    """Houses in two rows facing south, a plaza between them and a road below the second
    row. Returns (width, [house top-left offsets])."""
    top, bot = (n + 1) // 2, n // 2
    w = top * 7 + 2
    houses = [(2 + i * 7, 2) for i in range(top)]
    off = (top - bot) * 7 // 2
    houses += [(2 + off + i * 7, 9) for i in range(bot)]
    return w, houses


def _place_villages(area, rng, start, river, protected, prof=None):
    """Lay out 1-3 villages. Fills area.villages / area.safe, adds their structures to
    `protected`, and returns the zone other structures must keep clear of."""
    W, H = area.w, area.h
    river_set = set(river)
    zone = set()
    used = set()
    prof = prof or WORLD_PROFILES["stage"]
    lo, hi = prof["villages"]
    if prof.get("village_weights"):
        count = min(VILLAGE_MAX, rng.choices(range(lo, hi + 1), weights=prof["village_weights"])[0])
    else:
        count = rng.randint(lo, hi)
    for vi in range(count):
        n = rng.randint(*VILLAGE_HOUSES)
        vw, plan = _village_plan(n)
        vh = VILLAGE_H
        best = None
        big = W * H > 40000
        for _ in range(2500 if big else 500):
            x0, y0 = rng.randint(5, W - vw - 6), rng.randint(5, H - vh - 6)
            cx, cy = x0 + vw // 2, y0 + vh // 2
            if abs(cx - start[0]) + abs(cy - start[1]) < 28:
                continue
            if any(abs(cx - v["plaza"][0]) + abs(cy - v["plaza"][1]) < (30 if big else 36) for v in area.villages):
                continue
            lvl = area.height[y0][x0]
            ok = True
            for y in range(y0 - 2, y0 + vh + 2):
                for x in range(x0 - 2, x0 + vw + 2):
                    g = area.ground[y][x]
                    if (g in CLIFF_GROUND or g in ("water", "lava", "bridge", "ice") or area.height[y][x] != lvl
                            or (x, y) in river_set):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            bs = [area.biome[y][x] for y in range(y0, y0 + vh, 2) for x in range(x0, x0 + vw, 2)]
            main = max(sorted(set(bs)), key=bs.count)     # sorted: same world every session
            score = bs.count(main) / len(bs) - (0.6 if main == "hub" else 0) + rng.random() * 0.2
            if best is None or score > best[0]:
                best = (score, x0, y0, main)
                if score > 1.0:
                    break
        if best is None:
            continue
        _, x0, y0, main = best
        v = _build_village(area, rng, x0, y0, vw, vh, plan, main, _village_name(rng, used), protected,
                           save_point=prof.get("save_points", False))
        used.add(v["name"])
        area.villages.append(v)
        x1, y1 = x0 + vw - 1, y0 + vh - 1
        area.safe |= {(x, y) for y in range(y0 - 1, y1 + 2) for x in range(x0 - 1, x1 + 2)}
        zone |= {(x, y) for y in range(y0 - 4, y1 + 5) for x in range(x0 - 4, x1 + 5)}
    return zone


def _build_village(area, rng, x0, y0, vw, vh, plan, biome, name, protected, save_point=False):
    ground = BIOMES[biome]["ground"]
    # clear the plot and a two-tile margin round it
    for y in range(y0 - 2, y0 + vh + 2):
        for x in range(x0 - 2, x0 + vw + 2):
            area.objects.pop((x, y), None)
            area.decor.pop((x, y), None)
            inside = x0 <= x < x0 + vw and y0 <= y < y0 + vh
            area.ground[y][x] = ground if inside else BIOMES[area.biome[y][x]]["ground"]
            if inside:
                area.biome[y][x] = biome

    def at(dx, dy):
        return x0 + dx, y0 + dy

    def pave(dx, dy):
        x, y = at(dx, dy)
        area.ground[y][x] = "cobble"

    def put_obj(dx, dy, name_):
        t = at(dx, dy)
        area.objects[t] = name_
        protected.add(t)

    house_cols_b = set()
    for (hx, hy) in plan:
        if hy == 9:
            house_cols_b |= set(range(hx, hx + HOUSE_W))
    # plaza between the rows, the road below row two, and lanes linking them
    for dx in range(1, vw - 1):
        for dy in (5, 6, 7, 8, 12):
            pave(dx, dy)
        if dx not in house_cols_b:
            for dy in (9, 10, 11):
                pave(dx, dy)
    gaps = [hx + HOUSE_W for (hx, hy) in plan if hy == 2][:-1]       # columns between row-one houses
    lane = min(gaps, key=lambda g: abs(g + 1 - vw // 2)) if gaps else vw // 2
    for dy in range(0, 5):
        pave(lane, dy); pave(lane + 1, dy)
    for dx in (vw // 2 - 1, vw // 2, vw // 2 + 1):
        pave(dx, vh - 1)
    for dy in (5, 6, 7, 8):
        pave(0, dy); pave(vw - 1, dy)
    # fences round the edge, open at the lanes
    for dx in range(vw):
        if dx not in (lane, lane + 1):
            put_obj(dx, 0, "fence")
        if dx not in (vw // 2 - 1, vw // 2, vw // 2 + 1):
            put_obj(dx, vh - 1, "fence")
    for dy in range(1, vh - 1):
        if dy not in (5, 6, 7, 8):
            put_obj(0, dy, "fence_v"); put_obj(vw - 1, dy, "fence_v")
    # houses
    houses = []
    for (hx, hy) in plan:
        for dy in range(HOUSE_H):
            for dx in range(HOUSE_W):
                put_obj(hx + dx, hy + dy, "house_part")
        door = at(hx + 2, hy + HOUSE_H - 1)
        area.objects.pop(door, None)
        area.objects[at(hx, hy + HOUSE_H - 1)] = "house_" + biome      # the sprite anchors bottom-left
        protected.add(door)
        protected.add((door[0], door[1] + 1))
        houses.append({"door": door, "rect": (x0 + hx, y0 + hy, x0 + hx + HOUSE_W - 1, y0 + hy + HOUSE_H - 1)})
        for fx in (hx, hx + HOUSE_W - 1):                       # flower beds by the doorstep
            if rng.random() < 0.6:
                area.decor[at(fx, hy + HOUSE_H)] = "flowerbed"
        if hy == 2 and hx + HOUSE_W not in (lane, lane + 1) and hx + HOUSE_W < vw - 1 and rng.random() < 0.5:
            put_obj(hx + HOUSE_W, hy + HOUSE_H - 1, rng.choice(("barrel", "crate")))
    # the well, lamps and a signpost by the south gate (and in the open world, a save shrine)
    put_obj(vw // 2, 7, "well")
    shrine = None
    if save_point:
        shrine = at(vw // 2 + 3, 7)
        put_obj(vw // 2 + 3, 7, "shrine")
    for (dx, dy) in ((1, 4), (vw - 2, 4), (1, 10), (vw - 2, 10)):
        if area.objects.get(at(dx, dy)) is None:
            put_obj(dx, dy, "lamppost")
    sign = at(vw // 2 + 2, vh - 1)
    area.objects[sign] = "sign"
    protected.add(sign)
    fronts = {(h["door"][0], h["door"][1] + 1) for h in houses}
    walk = [at(dx, dy) for dy in (5, 6, 7, 8, 12) for dx in range(1, vw - 1)
            if at(dx, dy) not in area.objects and at(dx, dy) not in fronts]
    return {"name": name, "biome": biome, "rect": (x0, y0, x0 + vw - 1, y0 + vh - 1),
            "plaza": at(vw // 2, 6), "houses": houses, "walk": walk, "sign": sign, "shrine": shrine,
            "approach": at(vw // 2, vh + 1), "north": at(lane, -2),
            # short stubs of road from each gate out to where the road network meets it
            "stubs": [at(vw // 2, vh), at(vw // 2, vh + 1), at(lane, -1), at(lane, -2),
                      at(lane + 1, -1)]}


def generate_house(rng, vid, hid, village):
    """A one-room home: plank floor, a fireplace or shelves on the back wall, a bed, a
    table on a rug, odds and ends in the corners, and 0-2 chests."""
    W, H = rng.choice((10, 11, 12)), rng.choice((8, 9))
    family = rng.choice(FAMILY_NAMES)
    area = Area(f"house_{vid}_{hid}", "house", "house", f"{family} House", W, H)
    area.outdoor = False
    area.village = village["name"]
    for y in range(H):
        for x in range(W):
            area.ground[y][x] = "cfloor" if (1 <= x <= W - 2 and 2 <= y <= H - 2) else "cwall"
    cx = W // 2
    area.ground[H - 1][cx] = "cfloor"
    area.exit = (cx, H - 1)
    area.start = (cx, H - 2)
    floor = [(x, y) for y in range(2, H - 1) for x in range(1, W - 1)]
    keep_clear = {area.start, (cx, H - 3), (cx - 1, H - 2), (cx + 1, H - 2)}
    n_chests = rng.choices((0, 1, 2), weights=HOUSE_CHEST_WEIGHTS)[0]
    for attempt in range(60):
        objects, decor = {}, {}
        # the back wall: a fireplace, shelves, a cupboard, a plant
        back = rng.sample(range(1, W - 1), rng.randint(2, 4))
        kinds = ["fireplace"] + [rng.choice(("bookshelf", "cupboard", "plant", "bookshelf")) for _ in back[1:]]
        for x, k in zip(back, kinds):
            objects[(x, 2)] = k
        for x in rng.sample([x for x in range(2, W - 2) if x not in back], 2):
            decor[(x, 1)] = "window"
        # a bed against a side wall
        bx = rng.choice((1, W - 2))
        if (bx, 2) in objects:
            del objects[(bx, 2)]
        objects[(bx, 2)] = "bed_part"
        objects[(bx, 3)] = "bed"
        # a table on a rug in the middle of the room
        ty = 2 + (H - 3) // 2
        tx = cx + rng.choice((-2, -1, 1, 2))
        objects[(tx, ty)] = "table"
        for sx in (tx - 1, tx + 1):
            if rng.random() < 0.7:
                objects[(sx, ty)] = "stool"
        for ry in (ty, ty + 1):
            for rx in (tx - 1, tx, tx + 1):
                edge = (1 if ry == ty else 2) | (4 if rx == tx - 1 else 8 if rx == tx + 1 else 0)
                decor[(rx, ry)] = f"rug_{edge}"
        for (x, y) in ((1, H - 2), (W - 2, H - 2)):
            if rng.random() < 0.6 and (x, y) not in objects:
                objects[(x, y)] = rng.choice(("barrel", "jar", "crate"))
        if any(t in objects for t in keep_clear):
            continue
        # chests stand against a wall
        cands = [(x, y) for (x, y) in floor if (x in (1, W - 2) or y == 2) and (x, y) not in objects
                 and (x, y) not in keep_clear]
        if len(cands) < n_chests:
            continue
        spots = rng.sample(cands, n_chests)
        blocked = set(objects) | set(spots)
        seen, stack = {area.start}, [area.start]
        while stack:
            x, y = stack.pop()
            for dx, dy in DIRS:
                n = (x + dx, y + dy)
                if n in seen or n in blocked or not (1 <= n[0] <= W - 2 and 2 <= n[1] <= H - 2):
                    continue
                seen.add(n)
                stack.append(n)
        free = [t for t in floor if t not in blocked]
        if len(seen) != len(free):
            continue
        if any(not any((x + dx, y + dy) in seen for dx, dy in DIRS) for (x, y) in spots):
            continue
        area.objects, area.decor = objects, decor
        area.chest_spots = spots
        break
    area.decor[area.exit] = "doormat"
    area.refresh_solid()
    return area


# ---------------------------------------------------------------------------- caves

def generate_cave(rng, theme, area_id=None, name=None):
    W, H = CAVE_W, CAVE_H
    nrng = np.random.default_rng(rng.randrange(2 ** 32))
    area = Area(area_id or "cave_" + theme, "cave", theme, name or BIOMES[theme]["cave"], W, H)

    # Cellular-automata caverns
    cells = nrng.random((H, W)) < 0.45
    cells[0, :] = cells[-1, :] = True
    cells[:, 0] = cells[:, -1] = True
    for it in range(5):
        p = np.pad(cells, 1, constant_values=True)
        n = sum(p[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx].astype(int)
                for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
        cells = np.where(cells, n >= 4, n >= 5)
        cells[0, :] = cells[-1, :] = True
        cells[:, 0] = cells[:, -1] = True
    for y in range(H):
        for x in range(W):
            area.ground[y][x] = "cwall" if cells[y, x] else "cfloor"

    # Keep the largest cavern
    area.refresh_solid()
    floors = [(x, y) for y in range(H) for x in range(W) if not area.solid[y][x]]
    seen, biggest = set(), set()
    for t in floors:
        if t in seen:
            continue
        comp = area.reachable(t)
        seen |= comp
        if len(comp) > len(biggest):
            biggest = comp
    for (x, y) in floors:
        if (x, y) not in biggest:
            area.ground[y][x] = "cwall"

    # The way out: the southernmost floor tile with wall below it (an opening in the
    # south face), so you arrive facing into the cave the way you walked in
    cand = [(x, y) for (x, y) in biggest if y + 1 < H and area.ground[y + 1][x] == "cwall"]
    ex, ey = max(cand, key=lambda t: (t[1], -abs(t[0] - W // 2)))
    area.start = (ex, ey - 1) if area.ground[ey - 1][ex] == "cfloor" else (ex, ey)
    area.exit = (ex, ey)

    feats = CAVE_FEATURES[theme]
    pool_noise = value_noise(W, H, 6, nrng)
    for (x, y) in biggest:
        if abs(x - ex) + abs(y - ey) < 6:
            continue
        r = rng.random()
        if feats["pool"] and pool_noise[y, x] > 0.68:
            area.ground[y][x] = feats["pool"]
        elif r < 0.035:
            area.objects[(x, y)] = rng.choice(feats["objects"])
        elif r < 0.10:
            area.decor[(x, y)] = rng.choice(feats["decor"])

    area.portals[(ex, ey)] = ("overworld", None, "down")

    def fill(x, y):
        area.ground[y][x] = "cwall"
        area.objects.pop((x, y), None)
        area.decor.pop((x, y), None)

    def carve(x, y):
        area.objects.pop((x, y), None)
        if area.ground[y][x] != "cfloor":
            area.ground[y][x] = "cfloor"
    connect_pockets(area, carve, fill, min_pocket=8, protected={(ex, ey)})
    return area


# ---------------------------------------------------------------------------- dungeons

def generate_dungeon(rng, biome, area_id=None, name=None):
    """Five rooms in a chain, joined by corridors with barred doors. Each room holds waves
    of foes (spawned by the game when the player walks in); the last ends in a reward."""
    cols, rows = 4, 3
    pitch_x, pitch_y = 17, 14
    W, H = cols * pitch_x + 3, rows * pitch_y + 3
    area = Area(area_id or "dungeon_" + biome, "dungeon", "dungeon", name or DUNGEON_NAMES[biome], W, H)
    area.outdoor = False
    area.biome_theme = biome
    for y in range(H):
        for x in range(W):
            area.ground[y][x] = "cwall"

    # a self-avoiding walk through the room grid, entering from the bottom row
    for _ in range(200):
        cell = (rng.randrange(cols), rows - 1)
        chain = [cell]
        while len(chain) < DUNGEON_ROOMS:
            cx, cy = chain[-1]
            opts = [(cx + dx, cy + dy) for dx, dy in DIRS
                    if 0 <= cx + dx < cols and 0 <= cy + dy < rows and (cx + dx, cy + dy) not in chain]
            if not opts:
                break
            chain.append(rng.choice(opts))
        if len(chain) == DUNGEON_ROOMS:
            break

    for i, (cx, cy) in enumerate(chain):
        w, h = rng.randint(10, 12), rng.randint(7, 9)
        x0 = cx * pitch_x + 2 + (12 - w) // 2
        y0 = cy * pitch_y + 2 + (9 - h) // 2
        x1, y1 = x0 + w - 1, y0 + h - 1
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                area.ground[y][x] = "cfloor"
        last = i == DUNGEON_ROOMS - 1
        waves = [(3, 0), (3, 0), (2, 1)] if last else [(2 + i // 2, 0)] * (2 + (i >= 2))
        area.rooms.append({"rect": (x0, y0, x1, y1), "door": None, "back": None, "waves": waves,
                           "center": ((x0 + x1) // 2, (y0 + y1) // 2)})
        # pillars in the corners of the bigger rooms, torches on the back wall
        if w >= 11:
            for (px, py) in ((x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (x0 + 2, y1 - 2), (x1 - 2, y1 - 2)):
                area.objects[(px, py)] = "pillar"
        for tx in (x0 + 1, (x0 + x1) // 2, x1 - 1):
            area.decor[(tx, y0 - 1)] = "walltorch"
        for _ in range(4):
            dx, dy = rng.randint(x0, x1), rng.randint(y0, y1)
            if (dx, dy) not in area.objects:
                area.decor[(dx, dy)] = rng.choice(("rubble", "bones"))

    # corridors with a barred door, from each room to the next
    for i in range(DUNGEON_ROOMS - 1):
        a, b = area.rooms[i], area.rooms[i + 1]
        ax0, ay0, ax1, ay1 = a["rect"]; bx0, by0, bx1, by1 = b["rect"]
        (ca, ra), (cb, rb) = chain[i], chain[i + 1]
        if ra == rb:                                     # side by side
            y = (max(ay0, by0) + min(ay1, by1)) // 2
            xs = range(ax1 + 1, bx0) if cb > ca else range(bx1 + 1, ax0)
            tiles = [(x, y) for x in xs]
            if cb < ca:
                tiles.reverse()
        else:                                            # one above the other
            x = (max(ax0, bx0) + min(ax1, bx1)) // 2
            ys = range(ay1 + 1, by0) if rb > ra else range(by1 + 1, ay0)
            tiles = [(x, y) for y in ys]
            if rb < ra:
                tiles.reverse()
        for (x, y) in tiles:
            area.ground[y][x] = "cfloor"
            area.decor.pop((x, y), None)
        door = tiles[len(tiles) // 2]
        a["door"] = door
        b["back"] = door
        area.doors[door] = i

    # the way in (and out): an opening in the first room's south wall
    x0, y0, x1, y1 = area.rooms[0]["rect"]
    ex = (x0 + x1) // 2
    area.ground[y1 + 1][ex] = "cfloor"
    area.entry = (ex, y1 + 1)
    area.exit = area.entry
    area.start = (ex, y1)
    for (px, py) in [(ex, y1), (ex, y1 - 1)]:
        area.objects.pop((px, py), None); area.decor.pop((px, py), None)
    # where the reward and the way home appear once the last room falls
    fx0, fy0, fx1, fy1 = area.rooms[-1]["rect"]
    area.reward_tile = area.rooms[-1]["center"]
    area.final_exit = ((fx0 + fx1) // 2, fy0)
    for t in (area.reward_tile, area.final_exit):
        area.objects.pop(t, None); area.decor.pop(t, None)
    area.refresh_solid()
    for door in area.doors:
        area.solid[door[1]][door[0]] = 1                 # barred until the room is cleared
    return area


# ---------------------------------------------------------------------------- stage

def _numbered(key, name):
    """"Mossy Grotto" for a biome's first region, "Mossy Grotto II" for its second, …"""
    n = int(key.split("#")[1]) if "#" in key else 1
    return name + _ROMAN[n] if n < len(_ROMAN) else f"{name} {n}"


def generate_stage(seed, stage=1, profile="stage", progress=None):
    """The overworld plus one cave per region, with portals wired both ways."""
    rng = random.Random(seed)
    over = generate_overworld(rng, stage, profile, progress)
    areas = {"overworld": over}
    for b, (mx, my) in over.mouths.items():
        theme = base_biome(b)
        cave = generate_cave(rng, theme, "cave_" + b, _numbered(b, BIOMES[theme]["cave"]))
        areas[cave.id] = cave
        # into the cave: arrive just inside its exit, facing in
        over.portals[(mx, my)] = (cave.id, cave.start, "up")
        # back out: arrive on the path in front of the mouth, facing away from it
        cave.portals[cave.exit] = ("overworld", (mx, my + 1), "down")
    for b, (gx, gy) in over.gates.items():
        theme = base_biome(b)
        dun = generate_dungeon(rng, theme, "dungeon_" + b, _numbered(b, DUNGEON_NAMES[theme]))
        areas[dun.id] = dun
        over.portals[(gx, gy)] = (dun.id, dun.start, "up")
        dun.portals[dun.entry] = ("overworld", (gx, gy + 1), "down")
    for vi, v in enumerate(over.villages):
        for hi, h in enumerate(v["houses"]):
            house = generate_house(rng, vi, hi, v)
            areas[house.id] = house
            dx, dy = h["door"]
            h["area"] = house.id
            over.portals[(dx, dy)] = (house.id, house.start, "up")
            house.portals[house.exit] = ("overworld", (dx, dy + 1), "down")
    return areas


# ---------------------------------------------------------------------------- Limitless chambers

CHAMBER_THEMES = ["dungeon", "volcanic", "tundra", "storm", "desert", "meadow"]


def generate_chamber(rng, n, theme=None):
    """One arena of the Limitless descent: a walled hall with pillars and torches, a barred
    door in the north wall (it opens onto the next chamber once the waves are beaten) and
    no way back."""
    W, H = 24, 18
    theme = theme or CHAMBER_THEMES[((n - 1) // 2) % len(CHAMBER_THEMES)]
    area = Area(f"chamber_{n}", "chamber", theme, f"Chamber {n}", W, H)
    area.outdoor = False
    x0, y0, x1, y1 = 2, 3, W - 3, H - 3
    for y in range(H):
        for x in range(W):
            area.ground[y][x] = "cfloor" if (x0 <= x <= x1 and y0 <= y <= y1) else "cwall"
    for (cx_, cy_) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):     # cut the corners
        area.ground[cy_][cx_] = "cwall"
    cx = W // 2
    area.door = (cx, y0 - 1)
    area.ground[y0 - 1][cx] = "cfloor"                               # the doorway in the face row
    area.start = (cx, y1 - 1)
    area.rect = (x0, y0, x1, y1)
    pillars = [(x0 + 3, y0 + 3), (x1 - 3, y0 + 3), (x0 + 3, y1 - 3), (x1 - 3, y1 - 3)]
    if rng.random() < 0.5:
        pillars += [(cx - 5, (y0 + y1) // 2), (cx + 5, (y0 + y1) // 2)]
    obj = {"dungeon": "pillar", "desert": "pillar", "volcanic": "stalagmite", "tundra": "icespike",
           "storm": "crystal", "meadow": "stalagmite"}[theme]
    for t in pillars:
        area.objects[t] = obj
    for tx in (x0 + 2, cx - 4, cx + 4, x1 - 2):
        area.decor[(tx, y0 - 1)] = "walltorch"
    feats = CAVE_FEATURES.get(theme, {"decor": ["rubble", "bones"]})
    for _ in range(10):
        dx, dy = rng.randint(x0, x1), rng.randint(y0, y1)
        if (dx, dy) not in area.objects and (dx, dy) != area.start:
            area.decor[(dx, dy)] = rng.choice(feats["decor"] if theme != "dungeon" else ["rubble", "bones"])
    area.refresh_solid()
    area.solid[area.door[1]][area.door[0]] = 1                        # barred until the chamber falls
    return area
