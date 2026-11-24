import pygame
import math
import random
import sys
import json
import os
import copy
import time
import zlib

# Updated with new Element List from Elementlist.pdf

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
MAP_WIDTH = 64 # Larger map for more interesting generation
MAP_HEIGHT = 24
TILE_SIZE = 64 # Still not used for rendering, but conceptually useful
NUM_STAGES = 5 # Total number of stages to win

FOV = math.pi / 3; HALF_FOV = FOV / 2
NUM_RAYS = SCREEN_WIDTH; MAX_DEPTH = 20; RAY_ANGLE_STEP = FOV / NUM_RAYS
TORCH_RADIUS = 5.5   # tiles — how far the torch illuminates before full darkness
PLAYER_SPEED = 1.5; PLAYER_ROT_SPEED = 0.025 * 60
PLAYER_START_ANGLE = math.pi / 4

# --- Map Generation Constants ---
NUM_ROOMS = 15
MIN_ROOM_SIZE = 4
MAX_ROOM_SIZE = 8
NUM_ENEMIES = 20 # Total enemies to place randomly

# --- XP and Leveling Constants ---
BASE_XP_TO_LEVEL_UP = 10
NORMAL_REROLL_COST = 1
T5_REROLL_COST = 5
# Spin drops: one spin per chance that comes up, never a flat payout. A normal foe uses
# fixed odds for how many of its 3 chances come up (percent for 0, 1, 2, 3 spins); a boss
# rolls 5 chances at 60% each. Gambler's Oath rolls everything twice.
SPIN_DROP_TABLE = {"normal": [45, 27, 24, 4]}
SPIN_DROP_CHANCES = {"boss": (5, 0.60)}

# --- Tier Damage Multipliers ---
TIER_DAMAGE_MULTIPLIERS = {
    1: 1.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 18.0, 6: 30.0, 7: 50.0, 8: 9999.0
}

# --- Awakening Constants ---
AWAKENING_LEVEL_REQ = 4
AWAKENING_BASE_DURATION = 3 # Turns the awakening lasts
AWAKENING_BASE_COOLDOWN = 5 # Turns before awakening can be used again
AWAKENING_ATK_BONUS = 5
AWAKENING_DEF_BONUS = 3
ENEMY_SPRITE_SIZE = 0.6 # size relative to tile size (e.g., 0.6 means 60% of tile height)

# --- Combat Delay Constants ---
COMBAT_DELAY_DURATION = 2500 # milliseconds (5 seconds)
ENEMY_DROP_CHANCE = 30 # Percentage chance for an item to drop

# Colors
WHITE = (255, 255, 255); BLACK = (0, 0, 0); RED = (255, 0, 0); DARK_RED = (150, 0, 0); GREEN = (0, 255, 0); DARK_GREEN = (0, 150, 0); BLUE = (0, 0, 255); GRAY = (100, 100, 100); DARK_GRAY = (60, 60, 60); SKY_BLUE = (135, 206, 235); FLOOR_GRAY = (50, 50, 50); YELLOW = (255, 255, 0); PURPLE = (128, 0, 128); ORANGE = (255, 165, 0); BROWN = (139, 69, 19); CYAN = (0, 255, 255); PINK = (255, 192, 203); LIGHT_GRAY = (211, 211, 211); GOLD = (255, 215, 0); MAGENTA = (255, 0, 255); TAN = (210, 180, 140); DARK_BROWN = (101, 67, 33); DARK_PURPLE_BLUE = (40, 0, 60)
INDIGO = (75, 0, 130); SIENNA = (160, 82, 45); DARKEST_GRAY = (40, 40, 40); OFA_GREEN = (0, 230, 120)

# --- Arcane Grimoire UI Palette ---
# A single dark-fantasy visual language: ink grounds, aged-gold filigree, parchment type.
GRIM_INK          = (10, 8, 6)      # page/void ground
GRIM_INK2         = (18, 13, 8)     # screen ground
GRIM_PANEL        = (24, 17, 10)    # panel umber fill
GRIM_PANEL2       = (30, 22, 13)    # raised panel / button fill
GRIM_GOLD         = (201, 162, 75)  # aged gold — primary accent / borders
GRIM_GOLD_BRIGHT  = (232, 200, 116) # gold leaf — highlights / headings
GRIM_GOLD_DIM     = (122, 95, 44)   # muted gold — quiet borders
GRIM_GOLD_DEEP    = (74, 56, 24)    # deepest gold — bar frames / hairlines
GRIM_CREAM        = (236, 224, 196) # parchment — primary text
GRIM_CREAM_DIM    = (156, 141, 110) # secondary text
GRIM_CREAM_FAINT  = (109, 99, 80)   # faint hints
GRIM_HP           = (192, 67, 63);  GRIM_HP_DEEP = (82, 20, 20)
GRIM_MP           = (90, 134, 200); GRIM_MP_DEEP = (22, 48, 94)
GRIM_XP           = (212, 175, 55); GRIM_XP_DEEP = (122, 84, 16)
GRIM_OC           = (224, 139, 255); GRIM_OC_DEEP = (122, 30, 192)
GRIM_WARD         = (143, 191, 106) # good / super-effective
GRIM_WARN         = (201, 138, 58)  # caution
GRIM_BAD          = (192, 67, 63)   # danger / not-effective
GRIM_BOSS         = (192, 67, 63)   # boss accent (crimson)
# Enchanted-vessel bar fills — the exact two-stop gradients from the design document
BAR_HP_TOP = GRIM_HP;  BAR_HP_BOT = GRIM_HP_DEEP;  BAR_HP_GLOW = GRIM_HP
BAR_MP_TOP = GRIM_MP;  BAR_MP_BOT = GRIM_MP_DEEP;  BAR_MP_GLOW = GRIM_MP
BAR_OC_TOP = GRIM_OC;  BAR_OC_BOT = GRIM_OC_DEEP;  BAR_OC_GLOW = GRIM_OC
BAR_XP_TOP = GRIM_XP;  BAR_XP_BOT = GRIM_XP_DEEP
BAR_WELL_TOP = (14, 10, 6); BAR_WELL_BOT = (7, 5, 3)   # the recessed reservoir

# --- Weighted Element Definitions ---
tier1_elements = ["Water", "Earth", "Fire", "Wind", "Lightning"]
tier2_elements = ["Ice", "Mist", "Blood", "Sand", "Metal", "Mud", "Dust", "Combustion", "Inferno", "Storm", "Gale", "Plasma", "Lava"]
tier3_elements = ["Frost Fire", "Wood", "Energy", "Nuclear"]
tier4_elements = ["Kinetic", "Potential", "Matter", "Dark Matter"]
tier5_elements = ["Dark", "Light", "Time", "Reality", "Space", "Gravity"]
tier6_elements = ["Shadow", "Lunar", "Solar"]
tier7_elements = ["Eclipse", "Star Force"]
tier8_elements = ["OFA"]  # Admin-only. Never spawns naturally (weight 0).

all_element_tiers = [tier1_elements, tier2_elements, tier3_elements, tier4_elements, tier5_elements, tier6_elements, tier7_elements, tier8_elements]; tier_weights = [400, 300, 150, 80, 50, 15, 5, 0]

# --- True Forms (Tier 1 mastery) ---
# A player still bound to a Tier 1 element at level 15 masters it into its True form —
# a catch-up for anyone the evolution rolls never favoured.
#
# These are deliberately NOT part of all_element_tiers: inserting a list would renumber
# every tier after it (Ice would silently become Tier 3 and hit for x5), and appending
# would read as "Tier 9 — stronger than OFA". They're resolved explicitly instead, which
# also keeps them out of the weighted spawn table, so they never roll onto an enemy.
TRUE_ELEMENT_LEVEL_REQ = 15
TRUE_ELEMENTS = {
    "Fire":      "Hell Fire",
    "Earth":     "Tectonic Earth",
    "Water":     "Abyssal Water",
    "Wind":      "Tempest Wind",
    "Lightning": "Celestial Lightning",
}
TRUE_ELEMENT_NAMES = list(TRUE_ELEMENTS.values())
TRUE_TO_BASE = {v: k for k, v in TRUE_ELEMENTS.items()}
TRUE_ELEMENT_TIER = 2          # sits at Tier 2 in the ladder…
TRUE_ELEMENT_DAMAGE_MULT = 4.0 # …but hits harder than a lucky Tier 2 roll (x3)

# True Sigils: a consumable per Tier 1 element that masters it into its True form at the
# required level. The auto-unlock only fires on level-up, so a player who rerolls onto a
# fresh Tier 1 element after level 15 needs this to master it. Named for the form it grants.
TRUE_SIGILS = {base: f"{true} Sigil" for base, true in TRUE_ELEMENTS.items()}
TRUE_SIGIL_TO_BASE = {name: base for base, name in TRUE_SIGILS.items()}
TRUE_SIGIL_RARITY = "Legendary"

# Oathbreaker's Seal: the one way out of a sworn vow. Consumed to break a single vow of the
# player's choice, reversing anything the vow changed when it was sworn. Only turns up once
# the player actually holds a vow.
OATHBREAKER = "Oathbreaker's Seal"
OATHBREAKER_RARITY = "Legendary"
OATHBREAKER_CHEST_CHANCE = 0.20   # Legendary / Mythical chests
OATHBREAKER_BOSS_CHANCE = 0.04    # boss kills

ALL_ELEMENTS = []
for tier_list in all_element_tiers: ALL_ELEMENTS.extend(tier_list)
ALL_ELEMENTS.extend(TRUE_ELEMENT_NAMES)   # admin-settable, but never randomly spawned

CRIMSON = (178, 18, 44)   # Blood — a deep arterial red, distinct from Inferno's hot RED

ELEMENT_COLORS = {
    # Tier 1
    "Water": BLUE, "Earth": BROWN, "Fire": ORANGE, "Wind": LIGHT_GRAY, "Lightning": YELLOW,
    # Tier 2
    "Ice": CYAN, "Mist": LIGHT_GRAY, "Blood": CRIMSON, "Sand": TAN, "Metal": GRAY, "Mud": SIENNA, "Dust": TAN,
    "Combustion": ORANGE, "Inferno": RED, "Storm": DARK_GRAY, "Gale": LIGHT_GRAY, "Plasma": YELLOW, "Lava": DARK_RED,
    # Tier 3
    "Frost Fire": ORANGE, "Wood": DARK_BROWN, "Energy": YELLOW, "Nuclear": RED,
    # Tier 4
    "Kinetic": GREEN, "Potential": GREEN, "Matter": GRAY, "Dark Matter": BLACK,
    # Tier 5
    "Dark": BLACK, "Light": WHITE, "Time": PURPLE, "Reality": MAGENTA, "Space": DARK_PURPLE_BLUE, "Gravity": INDIGO,
    # Tier 6
    "Shadow": DARKEST_GRAY, "Lunar": LIGHT_GRAY, "Solar": YELLOW,
    # Tier 7
    "Eclipse": DARKEST_GRAY, "Star Force": WHITE,
    # Tier 8 (Admin Only)
    "OFA": OFA_GREEN,
    # True Forms — a deepened take on their base element's hue
    "Hell Fire": RED, "Tectonic Earth": SIENNA, "Abyssal Water": INDIGO,
    "Tempest Wind": (170, 195, 215), "Celestial Lightning": GOLD,
    None: WHITE
}

# --- Element Skills ---
ELEMENT_SKILLS = {
    # Tier 1
    "Water": [{'name': 'Water Gun', 'power': 0.9},{'name': 'Aqua Jet', 'power': 1.1},{'name': 'Hydro Pump', 'power': 1.3},],
    "Earth": [{'name': 'Rock Fall', 'power': 1.0},{'name': 'Earthquake', 'power': 1.4},{'name': 'Stone Edge', 'power': 1.1},],
    "Fire": [{'name': 'Ember', 'power': 0.9}, {'name': 'Fireball', 'power': 1.2}, {'name': 'Flame Burst', 'power': 1.0},],
    "Wind": [{'name': 'Gust', 'power': 0.8},{'name': 'Wind Cutter', 'power': 1.1},{'name': 'Tornado', 'power': 1.3},],
    "Lightning": [{'name': 'Spark', 'power': 0.9},{'name': 'Thunderbolt', 'power': 1.2},{'name': 'Thunder', 'power': 1.4},],
    # Tier 2
    "Ice": [{'name': 'Ice Shard', 'power': 0.8},{'name': 'Icicle Spear', 'power': 1.1},{'name': 'Blizzard', 'power': 1.3},],
    "Mist": [{'name': 'Obscuring Mist', 'power': 0.9}, {'name': 'Misty Veil', 'power': 1.0}],
    "Sand": [{'name': 'Sand Attack', 'power': 0.8},{'name': 'Sand Tomb', 'power': 1.2},],
    "Metal": [{'name': 'Iron Head', 'power': 1.1},{'name': 'Metal Claw', 'power': 1.0},{'name': 'Heavy Slam', 'power': 1.3},],
    "Mud": [{'name': 'Mud Shot', 'power': 0.9}, {'name': 'Mud Bomb', 'power': 1.2}],
    "Dust": [{'name': 'Dust Devil', 'power': 0.8}, {'name': 'Sandstorm', 'power': 1.1}],
    "Combustion": [{'name': 'Ignite', 'power': 1.0}, {'name': 'Explosion', 'power': 1.5}],
    "Inferno": [{'name': 'Hellfire', 'power': 1.4}, {'name': 'Firestorm', 'power': 1.6}],
    "Storm": [{'name': 'Thunderstorm', 'power': 1.3}, {'name': 'Gale Force', 'power': 1.1}],
    "Gale": [{'name': 'Wind Blast', 'power': 0.9}, {'name': 'Cyclone', 'power': 1.2}],
    "Plasma": [{'name': 'Plasma Beam', 'power': 1.2}, {'name': 'Energy Surge', 'power': 1.4}],
    "Lava": [{'name': 'Lava Plume', 'power': 1.1}, {'name': 'Magma Storm', 'power': 1.3}],
    "Blood": [{'name': 'Blood Lash', 'power': 0.9}, {'name': 'Piercing Blood', 'power': 1.2}, {'name': 'Crimson Tide', 'power': 1.4}],
    # Tier 3
    "Frost Fire": [{'name': 'Frozen Ember', 'power': 1.1}, {'name': 'Blazing Frost', 'power': 1.3}],
    "Wood": [{'name': 'Vine Whip', 'power': 1.0},{'name': 'Leaf Blade', 'power': 1.2},{'name': 'Wood Hammer', 'power': 1.4},],
    "Energy": [{'name': 'Energy Ball', 'power': 1.2}, {'name': 'Power Gem', 'power': 1.4}],
    "Nuclear": [{'name': 'Radiation Burst', 'power': 1.5}, {'name': 'Fission Wave', 'power': 1.6}],
    # Tier 4
    "Kinetic": [{'name': 'Force Push', 'power': 1.0},{'name': 'Kinetic Blast', 'power': 1.3},],
    "Potential": [{'name': 'Stored Power', 'power': 1.0}, {'name': 'Unleash Potential', 'power': 1.3}],
    "Matter": [{'name': 'Matter Manipulation', 'power': 1.0}, {'name': 'Density Shift', 'power': 1.1}],
    "Dark Matter": [{'name': 'Void Sphere', 'power': 1.2},{'name': 'Dark Energy', 'power': 1.3},],
    # Tier 5
    "Dark": [{'name': 'Dark Pulse', 'power': 1.1}, {'name': 'Night Daze', 'power': 1.3}],
    "Light": [{'name': 'Flash', 'power': 0.7},{'name': 'Holy Beam', 'power': 1.2},{'name': 'Judgement', 'power': 1.5},],
    "Time": [{'name': 'Temporal Pulse', 'power': 1.1},{'name': 'Time Warp', 'power': 1.0},{'name': 'Future Sight', 'power': 1.5},],
    "Reality": [{'name': 'Distortion', 'power': 1.1},{'name': 'Reality Break', 'power': 1.4},],
    "Space": [{'name': 'Spatial Rend', 'power': 1.3},{'name': 'Gravity Well', 'power': 1.0},],
    "Gravity": [{'name': 'Gravitational Crush', 'power': 1.2},{'name': 'Singularity', 'power': 1.4},{'name': 'Event Horizon', 'power': 1.5},],
    # Tier 6
    "Shadow": [{'name': 'Shadow Sneak', 'power': 0.9},{'name': 'Night Shade', 'power': 1.1},{'name': 'Phantom Force', 'power': 1.3},],
    "Lunar": [{'name': 'Moonlight Ray', 'power': 1.0}, {'name': 'Tidal Pull', 'power': 1.2}],
    "Solar": [{'name': 'Solar Flare', 'power': 1.3}, {'name': 'Sunstrike', 'power': 1.5}],
    # Tier 7
    "Eclipse": [{'name': 'Darkness Veil', 'power': 1.1}, {'name': 'Shadow Nova', 'power': 1.3}],
    "Star Force": [{'name': 'Starlight Blast', 'power': 1.4}, {'name': 'Cosmic Beam', 'power': 1.6}],
    # True Forms — the Tier 1 kits grown into their full expression
    "Hell Fire": [{'name': 'Cinder Storm', 'power': 1.1}, {'name': 'Hellfire Lance', 'power': 1.4}, {'name': 'Damnation', 'power': 1.7}],
    "Tectonic Earth": [{'name': 'Fault Line', 'power': 1.1}, {'name': 'Continental Slam', 'power': 1.4}, {'name': 'Pangaea Break', 'power': 1.7}],
    "Abyssal Water": [{'name': 'Riptide', 'power': 1.1}, {'name': 'Crushing Depths', 'power': 1.4}, {'name': 'Maelstrom', 'power': 1.7}],
    "Tempest Wind": [{'name': 'Shear Line', 'power': 1.1}, {'name': 'Typhoon', 'power': 1.4}, {'name': 'Eye of the Storm', 'power': 1.7}],
    "Celestial Lightning": [{'name': 'Arc Flash', 'power': 1.1}, {'name': 'Thunder Crown', 'power': 1.4}, {'name': "Heaven's Judgement", 'power': 1.7}],
    # Tier 8 — OFA (Admin Only) — all moves instakill regardless of power value
    "OFA": [
        {'name': 'Full Cowl Smash',           'power': 9.0},  # OFA base — Izuku / Yoichi
        {'name': 'Gear Shift: Overdrive',      'power': 9.5},  # 2nd user quirk
        {'name': 'Fa Jin: Kinetic Burst',      'power': 9.3},  # 3rd user quirk
        {'name': 'Danger Sense: Counter',      'power': 9.2},  # 4th user — Hikage Shinomori
        {'name': 'Black Whip Barrage',         'power': 9.4},  # 5th user — Daigoro Banjo
        {'name': 'Smokescreen Blitz',          'power': 8.8},  # 6th user — En
        {'name': 'Float: Aerial Assault',      'power': 9.1},  # 7th user — Nana Shimura
        {'name': 'United States of Smash',     'power': 10.0}, # Deku signature ultimate
    ],
}
DEFAULT_SKILLS = [{'name': 'Struggle', 'power': 0.7}]

def get_skill_mana_cost(element, skill_name):
    """Returns mana cost: 10 (weakest), 30 (strongest), 20 (in-between)."""
    skills = ELEMENT_SKILLS.get(element, DEFAULT_SKILLS)
    if len(skills) <= 1:
        return 10
    sorted_powers = sorted(set(s['power'] for s in skills))
    skill_power = next((s['power'] for s in skills if s['name'] == skill_name), sorted_powers[0])
    if skill_power >= sorted_powers[-1]:
        return 30
    elif skill_power <= sorted_powers[0]:
        return 10
    else:
        return 20

def get_skill_cooldown_max(element, skill_name):
    """Returns max cooldown turns: 0 (weakest), 1 (in-between), 2 (strongest)."""
    skills = ELEMENT_SKILLS.get(element, DEFAULT_SKILLS)
    if len(skills) <= 1:
        return 0
    sorted_powers = sorted(set(s['power'] for s in skills))
    skill_power = next((s['power'] for s in skills if s['name'] == skill_name), sorted_powers[0])
    if skill_power >= sorted_powers[-1]:
        return 3
    elif skill_power <= sorted_powers[0]:
        return 1
    else:
        return 2

# --- Miss Chance ---
# Heavier attacks are harder to land: miss chance climbs linearly with a move's power, from
# 0% at the weakest move in the game (Flash / Struggle, 0.7) to a hard cap of 10% at the
# strongest normal move (the True-form finishers, 1.7). Anything above that stays at 10%.
MISS_CHANCE_MAX = 0.10
MISS_POWER_FLOOR = 0.7
MISS_POWER_CEIL = 1.7
MELEE_POWER = 1.0          # a basic swing counts as a mid-weight move (3%)


def get_miss_chance(power):
    """0.0 - MISS_CHANCE_MAX for an attack of the given power."""
    t = (power - MISS_POWER_FLOOR) / (MISS_POWER_CEIL - MISS_POWER_FLOOR)
    return MISS_CHANCE_MAX * max(0.0, min(1.0, t))


def roll_miss(power):
    """True if an attack of this power misses."""
    return random.random() < get_miss_chance(power)


def format_miss_chance(power):
    return f"{get_miss_chance(power) * 100:.0f}%"

# --- Awakening Names ---
AWAKENING_NAMES = {
    # Tier 1
    "Fire": "Inferno Incarnate", "Water": "Tidal Tyrant", "Earth": "Seismic Juggernaut", "Wind": "Gale Force Overlord", "Lightning": "Voltaic Cataclysm",
    # Tier 2
    "Ice": "Glacial Domination", "Mist": "Ethereal Veil", "Sand": "Desert Fury", "Metal": "Adamantine Rampage", "Mud": "Quagmire Terror", "Dust": "Sandstorm Genesis",
    "Combustion": "Ignited Fury", "Inferno": "Infernal Dominion", "Storm": "Tempest King", "Gale": "Hurricane Sovereign", "Plasma": "Arcane Plasma", "Lava": "Volcanic Cataclysm", "Blood": "Blood Coagulation",
    # Tier 3
    "Frost Fire": "Blizzard Inferno", "Wood": "Verdant Behemoth", "Energy": "Raw Power", "Nuclear": "Atomic Cataclysm",
    # Tier 4
    "Kinetic": "Unstoppable Force", "Potential": "Latent Power Unbound", "Matter": "Material Transcendence", "Dark Matter": "Void Singularity",
    # Tier 5
    "Dark": "Nightmare Unbound", "Light": "Celestial Judgement", "Time": "Chronoscape Collapse", "Reality": "Warped Domain", "Space": "Cosmic Rupture", "Gravity": "Universal Singularity",
    # Tier 6
    "Shadow": "Umbral Annihilation", "Lunar": "Moonlit Revelation", "Solar": "Solar Zenith",
    # Tier 7
    "Eclipse": "Total Obscurity", "Star Force": "Stellar Annihilation",
    # Tier 8 (Admin Only)
    "OFA": "One For All: Plus Ultra",
    # True Forms
    "Hell Fire": "Infernal Apotheosis", "Tectonic Earth": "Continental Wrath",
    "Abyssal Water": "Leviathan Ascendant", "Tempest Wind": "Stormlord Ascendant",
    "Celestial Lightning": "Heaven's Verdict",
    None: "Power Unleashed"
}

# --- Element Codex Descriptions (Info page) ---
ELEMENT_INFO = {
    # Tier 1
    "Water": "The patient element. Water wears down what it cannot break, and smothers flame outright.",
    "Earth": "Unmoving and enduring. Earth answers force with mass, and buries what stands against it.",
    "Fire": "Hunger given form. Fire consumes whatever it touches and grows stronger for the eating.",
    "Wind": "The unseen hand. Wind slips past every guard and strikes from a direction that does not exist.",
    "Lightning": "Judgement at the speed of thought. Lightning does not travel to its target — it arrives.",
    # Tier 2
    "Ice": "Water taught cruelty. Ice halts motion itself, and what stops moving does not start again.",
    "Mist": "A veil of drowned air. Mist steals sight, and a blinded enemy is already beaten.",
    "Sand": "A mountain ground to powder, and no lighter for it. Sand fills lungs and buries armies.",
    "Metal": "Earth refined to an edge. Metal is the first element that was made rather than found.",
    "Mud": "Earth and water in unhappy union. Mud drags down everything that tries to stand.",
    "Dust": "What remains when stone forgets it was stone. Dust chokes, blinds, and never settles.",
    "Combustion": "Fire with intent. Combustion chooses the exact moment it becomes an explosion.",
    "Inferno": "Fire past all reason. Inferno does not spread — it claims.",
    "Storm": "Wind and lightning conspiring. A storm is not weather; it is a siege.",
    "Gale": "Wind with somewhere to be. A gale strips the ground bare, and the enemy with it.",
    "Plasma": "Matter too excited to stay matter. Plasma burns in colours fire never learned.",
    "Lava": "Earth remembering it was once fire. Slow, certain, and utterly final.",
    "Blood": "Water given a pulse. Blood answers the heart that commands it, hardening into needles that pierce any guard.",
    # Tier 3
    "Frost Fire": "Two deaths in one flame. Frost Fire burns cold, and the wound never closes.",
    "Wood": "Life as a weapon. Wood grows through stone given only time — and it is always given time.",
    "Energy": "The common tongue of every element. Energy is what all the others are made of.",
    "Nuclear": "The fire inside matter itself, let out. Nuclear leaves a place that stays wrong.",
    # Tier 4
    "Kinetic": "Motion without a mover. Kinetic force is the punch that was never thrown.",
    "Potential": "Every blow you have not struck yet, held in reserve. Potential pays out all at once.",
    "Matter": "Authority over substance. Matter asks what a thing is, then answers differently.",
    "Dark Matter": "The mass that hides. Dark Matter presses on the world without ever touching it.",
    # Tier 5
    "Dark": "Not the absence of light, but the appetite for it. Dark is older, and it is patient.",
    "Light": "The first thing that ever was. Light does not illuminate — it reveals, and revelation burns.",
    "Time": "The one element no armour turns. Time takes everything eventually; you merely hurry it.",
    "Reality": "The rules, held loosely. Reality decides what is true, and truth is negotiable.",
    "Space": "Distance as a weapon. Space puts the enemy where you want them — or nowhere at all.",
    "Gravity": "The quiet tyrant. Gravity never lets go, and everything falls to it in the end.",
    # Tier 6
    "Shadow": "Dark that learned a shape. Shadow goes where light has been and takes its place.",
    "Lunar": "Borrowed light with its own hunger. Lunar pulls at blood the way it pulls at tides.",
    "Solar": "A star's temper held at arm's length. Solar does not burn things; it ends them.",
    # Tier 7
    "Eclipse": "Sun and moon in the same hand. Eclipse is the moment the sky admits it can be stopped.",
    "Star Force": "The furnace that lights galaxies, wearing a person. Star Force answers to nothing.",
    # Tier 8
    "OFA": "One For All. Every past user's strength, stacked and handed down. Admin-only — it never spawns.",
    # True Forms — mastery of a Tier 1 element rather than evolution away from it
    "Hell Fire": "Fire that stopped pretending to be warmth. Hell Fire burns the idea of a thing, and the thing follows.",
    "Tectonic Earth": "Earth remembering it is a moving thing. Tectonic Earth does not throw stones — it moves the plate beneath you.",
    "Abyssal Water": "Water at the pressure where light gives up. Abyssal Water does not drown you; it simply closes.",
    "Tempest Wind": "Wind that stopped moving on and settled in. A tempest has a centre, and it chooses where.",
    "Celestial Lightning": "Lightning that answers to a higher court. It does not strike where it must, but where it judges.",
    None: "No element bound. Seek a rebinding.",
}

# --- SIMPLIFIED Elemental Matchups ---
SUPER_EFFECTIVE_MULTIPLIER = 1.5; NOT_EFFECTIVE_MULTIPLIER = 0.5

# --- Elemental Matchup Wheel ---
# The five base elements sit on a pentagon. Reading the cycle forward, each element is
# STRONG against the next two and WEAK against the previous two — so every element beats
# two others and is beaten by two others. No element is strictly better than another.
#
#   Lightning -> Water -> Fire -> Earth -> Wind -> (back to Lightning)
#
#   Lightning  beats Water (conducts through it), Fire (raw energy overwhelms flame)
#   Water      beats Fire (douses), Earth (erodes)
#   Fire       beats Earth (scorches), Wind (a firestorm eats the air)
#   Earth      beats Wind (mountains break the gale), Lightning (grounds it)
#   Wind       beats Lightning (scatters the storm), Water (whips the sea)
#
# This keeps every relationship the old four-element table defined and adds Lightning.
MATCHUP_CYCLE = ["Lightning", "Water", "Fire", "Earth", "Wind"]

def _build_matchup_table():
    n = len(MATCHUP_CYCLE)
    table = {}
    for i, attacker in enumerate(MATCHUP_CYCLE):
        row = {}
        for j, defender in enumerate(MATCHUP_CYCLE):
            step = (j - i) % n          # how far ahead the defender sits in the cycle
            if step in (1, 2):
                row[defender] = SUPER_EFFECTIVE_MULTIPLIER
            elif step in (n - 2, n - 1):
                row[defender] = NOT_EFFECTIVE_MULTIPLIER
            else:
                row[defender] = 1.0     # mirror match
        table[attacker] = row
    return table

ELEMENTAL_MATCHUPS = _build_matchup_table()

# --- Item Rarity Mappings ---
RARITY_DEFENSE_BOOSTS = {
    "Common": 5, "Uncommon": 10, "Rare": 15, "Epic": 20, "Legendary": 25, "Mythical": 30
}
RARITY_ELEMENT_BOOSTS = {
    "Common": 2, "Uncommon": 5, "Rare": 10, "Epic": 15, "Legendary": 20, "Mythical": 30
}
RARITY_COLORS = {"Common": WHITE, "Uncommon": GREEN, "Rare": BLUE,
                 "Epic": PURPLE, "Legendary": GOLD, "Mythical": MAGENTA}

# --- Treasure Chest Constants ---
CHEST_BASE_COUNT = 4        # chests on stage 1
CHEST_PER_STAGE = 2         # additional chests each stage deeper
CHEST_MAX_PER_STAGE = 10    # hard cap — never more than this on a stage
CHEST_SPRITE_SIZE = 0.5     # size relative to tile height (enemies use 0.6)
CHEST_TOAST_MS = 3500       # how long the loot banner lingers
CHEST_RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"]
# Stage 1 odds. Each stage multiplies every step up the table by CHEST_STAGE_SHIFT,
# so deeper stages pull steadily harder toward the top rarities.
CHEST_BASE_WEIGHTS = [60.0, 26.0, 10.0, 3.5, 1.2, 0.3]
CHEST_STAGE_SHIFT = 1.45
CHEST_ATTUNED_CHANCE = 0.6  # odds of favouring gear matching the player's element
CHEST_POTION_CHANCE = 0.25  # odds a chest holds a potion instead of gear
CHEST_SIGIL_CHANCE = 0.20   # odds a high-tier chest holds the player's True Sigil (when eligible)

# --- Potions ---
# Tiered consumables sharing the game's rarity ladder, so they colour-code in the satchel
# and can drop from chests at the chest's own tier.
#
# Restore is a PERCENTAGE of the player's own maximum with a flat floor, because max HP/MP
# grow with level and stat points — a flat-only potion would be worthless by stage 5.
#   kind: "hp" | "mp" | "both" | "mp_overcharge"
POTION_DATA = {
    "Minor Health Potion":      {"kind": "hp", "rarity": "Common",    "pct": 0.25, "min": 25},
    "Health Potion":            {"kind": "hp", "rarity": "Uncommon",  "pct": 0.40, "min": 50},
    "Greater Health Potion":    {"kind": "hp", "rarity": "Rare",      "pct": 0.60, "min": 120},
    "Superior Health Potion":   {"kind": "hp", "rarity": "Epic",      "pct": 0.85, "min": 250},
    "Sovereign Health Potion":  {"kind": "hp", "rarity": "Legendary", "pct": 1.00, "min": 99999},
    "Elixir of Life":           {"kind": "both", "rarity": "Mythical", "pct": 1.00, "min": 99999},

    "Minor Mana Potion":        {"kind": "mp", "rarity": "Common",    "pct": 0.25, "min": 25},
    "Mana Potion":              {"kind": "mp", "rarity": "Uncommon",  "pct": 0.40, "min": 50},
    "Greater Mana Potion":      {"kind": "mp", "rarity": "Rare",      "pct": 0.60, "min": 120},
    "Superior Mana Potion":     {"kind": "mp", "rarity": "Epic",      "pct": 0.85, "min": 250},
    "Sovereign Mana Potion":    {"kind": "mp", "rarity": "Legendary", "pct": 1.00, "min": 99999},
    "Elixir of Ether":          {"kind": "mp_overcharge", "rarity": "Mythical", "pct": 1.00, "min": 99999},
}

def make_potion(name):
    """Build an inventory-ready potion item."""
    data = POTION_DATA.get(name)
    if not data:
        return None
    return {"name": name, "slot": "Consumables", "rarity": data["rarity"]}

def potions_of_rarity(rarity):
    return [make_potion(n) for n, d in POTION_DATA.items() if d["rarity"] == rarity]

def item_glyph(item):
    """Short label for a satchel grid cell. A bare first initial can't tell 'Minor Health
    Potion' from 'Minor Mana Potion', so consumables get a purpose-built code instead."""
    name = item.get("name", "?")
    data = POTION_DATA.get(name)
    if data:
        return {"hp": "HP", "mp": "MP", "both": "EL", "mp_overcharge": "EE"}[data["kind"]]
    if name.startswith("Evo Stone"):
        return "EV"
    if name in TRUE_SIGIL_TO_BASE:
        return "TS"   # True Sigil
    if name == OATHBREAKER:
        return "OB"
    return name[:1].upper()

def potion_effect_text(name):
    """Human-readable effect, for the satchel detail panel."""
    data = POTION_DATA.get(name)
    if not data:
        return ""
    kind = data["kind"]
    pct = int(data["pct"] * 100)
    if kind == "both":
        return "Restores all HP and MP"
    if kind == "mp_overcharge":
        return "Fills MP and grants OVERCHARGE"
    stat = "HP" if kind == "hp" else "MP"
    if pct >= 100:
        return f"Restores all {stat}"
    return f"Restores {pct}% of max {stat}"

# --- Load Item Data ---
WEAPON_DATA = []
ARMOR_DATA = {}

def load_item_data():
    global WEAPON_DATA, ARMOR_DATA
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        weapons_path = os.path.join(script_dir, "Items", "weapons.json")
        armor_path = os.path.join(script_dir, "Items", "armor.json")
        
        if os.path.exists(weapons_path):
            # UTF-8 explicitly: several item names use curly apostrophes (’), which the
            # platform-default cp1252 mangled into "â€™".
            with open(weapons_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                WEAPON_DATA = data.get("weapons", [])
            print(f"Loaded {len(WEAPON_DATA)} weapon tiers.")
        else:
            print(f"Warning: {weapons_path} not found.")

        if os.path.exists(armor_path):
            with open(armor_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ARMOR_DATA = data.get("armour", {})
            print(f"Loaded {len(ARMOR_DATA)} armor slots.")
        else:
            print(f"Warning: {armor_path} not found.")
            
    except Exception as e:
        print(f"Error loading item data: {e}")

load_item_data()

def get_item_stats(item):
    """Calculates stats for an item based on its data/rarity."""
    stats = {"melee_boost": 0, "defense_boost": 0}
    # Consumables are never equipped and carry no passive stats. Without this they fall
    # into the armour branch below and report a defence bonus they don't actually grant.
    if item.get("slot") == "Consumables" or item.get("name", "") in POTION_DATA \
            or item.get("name", "").startswith("Evo Stone"):
        return stats
    if item.get("slot") == "Weapon":
        # Search WEAPON_DATA for rarity boost
        item_rarity = item.get("rarity", "Common").lower().strip()
        for tier in WEAPON_DATA:
            if tier.get("rarity", "Common").lower().strip() == item_rarity:
                # Magic weapons (staves, orbs, tomes…) feed element strength, not melee
                if item.get("type") == "Magic":
                    stats["magic_boost"] = tier.get("magicBoost", tier.get("meleeBoost", 0))
                else:
                    stats["melee_boost"] = tier.get("meleeBoost", 0)
                break
    else: # Armor slots: helmet, chest, boots
        rarity = item.get("rarity", "Common")
        stats["defense_boost"] = RARITY_DEFENSE_BOOSTS.get(rarity, 5)
        stats["element_boost"] = RARITY_ELEMENT_BOOSTS.get(rarity, 2)
    return stats

def get_random_drop(enemy_element, is_boss=False):
    """Determines if an enemy drops an item and returns the item data."""
    # Combine all weapon tiers and armor types for potential drops
    potential_drops = []
    
    # 1. Weapons
    for tier in WEAPON_DATA:
        rarity = tier["rarity"]
        drop_rate = tier["dropRate"]
        for item_data in tier["items"]:
            # Element-bound weapons (Elemental or Magic) drop only from that element's
            # enemies; element-free ones can drop from anything
            if item_data.get("element", "None") not in (None, "None"):
                if item_data["element"] == enemy_element:
                    potential_drops.append({**item_data, "rarity": rarity, "dropRate": drop_rate, "slot": "Weapon"})
            else:
                potential_drops.append({**item_data, "rarity": rarity, "dropRate": drop_rate, "slot": "Weapon"})

    # 2. Armor
    for slot in ["helmet", "chest", "boots"]:
        slot_items = ARMOR_DATA.get(slot, [])
        for item_data in slot_items:
            # Simple drop rate for armor based on rarity (using weapon rates as proxy if needed, or fixed)
            # Find matching rarity in WEAPON_DATA to get drop rate
            rarity_rate = 10 # Default
            for tier in WEAPON_DATA:
                if tier["rarity"] == item_data["rarity"]:
                    rarity_rate = tier["dropRate"]
                    break
            
            # Elemental armor rule (optional, but let's allow it or restrict like weapons if user said 'elements drop from respected elemental enemy')
            if item_data.get("element") != "None":
                if item_data["element"] == enemy_element:
                    potential_drops.append({**item_data, "dropRate": rarity_rate, "slot": slot.capitalize()})
            else:
                potential_drops.append({**item_data, "dropRate": rarity_rate, "slot": slot.capitalize()})

    if not potential_drops:
        return None

    # Roll for a drop (luck boosts base drop chance)
    if has_vow(V_POVERTY):
        return None                              # Vow of Poverty: enemies never drop items
    base_chance = ENEMY_DROP_CHANCE * (2 if has_vow(V_HUNTER) else 1)
    effective_drop_chance = base_chance + player_stats.get("luck", 0)
    weights = [item["dropRate"] for item in potential_drops]
    if is_boss and player_stats.get("vows") and random.random() < OATHBREAKER_BOSS_CHANCE:
        return make_oathbreaker()
    if random.randint(1, 100) <= min(effective_drop_chance, 100):
        # Check for Evo Stone drop first - Boss Only
        if is_boss:
            tier = get_element_tier(enemy_element)
            # Tier-specific rates: 1:25%, 2:20%, 3:10%, 4:5%, 5:1%
            tier_rates = {1: 25, 2: 20, 3: 10, 4: 5, 5: 1}
            stone_chance = tier_rates.get(tier, 0)
            
            if random.randint(1, 100) <= stone_chance:
                return {"name": f"Evo Stone (Tier {tier})", "tier": tier, "slot": "Consumables"}

        return random.choices(potential_drops, weights=weights, k=1)[0]
    
    return None

def chest_rarity_weights(stage, luck=0):
    """Rarity odds for a chest on a given stage. Deeper stages (and luck) shift the
    curve toward the top of the table, so loot genuinely improves as you descend."""
    shift = CHEST_STAGE_SHIFT ** max(0, stage - 1)
    shift *= 1.0 + luck / 200.0
    return [w * (shift ** i) for i, w in enumerate(CHEST_BASE_WEIGHTS)]


def roll_chest_rarity(stage, luck=0):
    rolled = random.choices(CHEST_RARITIES, weights=chest_rarity_weights(stage, luck), k=1)[0]
    return vow_chest_rarity(rolled)


def items_of_rarity(rarity):
    """Every gear item at a rarity.

    Deliberately NOT filtered by element: a weapon's melee boost and armour's defence
    boost are derived from rarity alone (see get_item_stats), so off-element gear is
    still a real upgrade — matching the element only adds the extra element bonus.
    Filtering by element here would empty the Rare/Epic/Legendary tiers entirely, since
    every weapon at those rarities is Elemental."""
    pool = []
    for tier in WEAPON_DATA:
        if tier.get("rarity") != rarity:
            continue
        for it in tier.get("items", []):
            pool.append({**it, "rarity": rarity, "slot": "Weapon"})
    for slot, items in ARMOR_DATA.items():
        for it in items:
            if it.get("rarity") != rarity:
                continue
            pool.append({**it, "rarity": rarity, "slot": slot.capitalize()})
    return pool


def roll_chest_loot(rarity, element):
    """Pick an item at the chest's rarity, favouring gear attuned to the player's own
    element when that tier offers any. Steps down a tier only if a rarity is genuinely
    empty in the data."""
    # A rich chest may hold the True Sigil for the player's element — but only if they're
    # still on that Tier 1 element and could actually use it (at/near the mastery level).
    if (element in TRUE_SIGILS
            and rarity in ("Epic", "Legendary", "Mythical")
            and player_stats.get("level", 1) >= true_form_level() - 3
            and random.random() < CHEST_SIGIL_CHANCE):
        return make_true_sigil(element)

    if (rarity in ("Legendary", "Mythical") and player_stats.get("vows")
            and random.random() < OATHBREAKER_CHEST_CHANCE):
        return make_oathbreaker()

    # Some chests hold a potion of the same tier rather than gear
    if random.random() < CHEST_POTION_CHANCE:
        brews = potions_of_rarity(rarity)
        if brews:
            return dict(random.choice(brews))

    start = CHEST_RARITIES.index(rarity) if rarity in CHEST_RARITIES else 0
    for i in range(start, -1, -1):
        pool = items_of_rarity(CHEST_RARITIES[i])
        if not pool:
            continue
        attuned = [it for it in pool if it.get("element") == element]
        if attuned and random.random() < CHEST_ATTUNED_CHANCE:
            item = dict(random.choice(attuned))
        else:
            item = dict(random.choice(pool))
        item["rarity"] = CHEST_RARITIES[i]
        return item
    return None


def make_oathbreaker():
    return {"name": OATHBREAKER, "slot": "Consumables", "rarity": OATHBREAKER_RARITY}


def make_true_sigil(base):
    """Build an inventory-ready True Sigil item for a Tier 1 element."""
    name = TRUE_SIGILS.get(base)
    if not name:
        return None
    return {"name": name, "slot": "Consumables", "rarity": TRUE_SIGIL_RARITY, "true_base": base}


def grant_true_form(base):
    """Master a Tier 1 element into its True form. Shared by the level-15 auto-unlock and
    the True Sigil item, so both paths stay identical."""
    global level_up_message
    true_name = TRUE_ELEMENTS.get(base)
    if not true_name:
        return False
    player_stats["element"] = true_name
    record_element_change(true_name, evolved=True)
    player_stats["skill_cooldowns"] = {}   # new kit, clean slate
    # Full cinematic the first time you reach THIS form; the short reveal on repeats, so
    # rerolling back to Fire and re-mastering it doesn't replay the whole ceremony.
    seen = player_stats.setdefault("true_forms_seen", [])
    first_time = true_name not in seen
    if first_time:
        seen.append(true_name)
    level_up_message = f"TRUE FORM — {base} becomes {true_name}!"
    begin_ascension(base, true_name, full=first_time)
    print(level_up_message + ("  (first time)" if first_time else "  (repeat)"))
    return True


def use_true_sigil(index):
    """Consume a True Sigil to master the matching Tier 1 element, if the player is that
    element and at the required level. Refuses (without consuming) otherwise, explaining why."""
    item = player_stats["inventory"][index]
    base = item.get("true_base") or TRUE_SIGIL_TO_BASE.get(item.get("name", ""))
    if base is None:
        return
    current = player_stats["element"]
    if current != base:
        show_notice("Wrong Element", item["name"],
                    f"Only a {base} user can invoke this.", GRIM_WARN)
    elif player_stats["level"] < true_form_level():
        show_notice("Not Ready", item["name"],
                    f"Reach level {true_form_level()} to master {base}.", GRIM_WARN)
    else:
        grant_true_form(base)
        player_stats["inventory"].pop(index)


def use_item(index):
    """Handles using an item from the inventory (equip or consume)."""
    if index < 0 or index >= len(player_stats["inventory"]):
        return

    item = player_stats["inventory"][index]
    name = item.get("name", "")

    if name.startswith("Evo Stone"):
        current_tier = get_element_tier(player_stats["element"])
        stone_tier = item.get("tier", 0)

        if stone_tier == current_tier:
            player_stats["inventory"].pop(index)
            global game_state
            game_state = STATE_EVOLVE
            print(f"Used {name}! Time to evolve!")
        else:
            print(f"Cannot use {name} on current tier {current_tier} element.")
    elif name in TRUE_SIGIL_TO_BASE:
        use_true_sigil(index)
    elif name == OATHBREAKER:
        begin_unbind()
    elif name in POTION_DATA:
        use_potion(index)
    else:
        # Default to equip for gear
        equip_item(index)


def use_potion(index):
    """Drink a tiered potion. Restores a percentage of the player's own maximum (with a
    flat floor) so potions stay relevant as max HP/MP grow. Refuses to be wasted when
    there's nothing to restore, so the item isn't consumed for no benefit."""
    item = player_stats["inventory"][index]
    name = item.get("name", "")
    data = POTION_DATA.get(name)
    if not data:
        return False

    kind = data["kind"]
    healed = restored = 0
    forbidden = potion_block_reason(kind)
    if forbidden:
        show_notice("Vow Forbids", name, forbidden, GRIM_BAD)
        return False

    if kind in ("hp", "both"):
        amount = max(data["min"], int(player_stats["max_hp"] * data["pct"]))
        amount = int(amount * race_value("potion_heal"))   # Skeleton: bones knit slowly
        before = player_stats["hp"]
        player_stats["hp"] = min(player_stats["max_hp"], player_stats["hp"] + amount)
        healed = player_stats["hp"] - before

    if kind in ("mp", "both"):
        amount = max(data["min"], int(player_stats["max_mana"] * data["pct"]))
        before = min(player_stats["mana"], player_stats["max_mana"])
        player_stats["mana"] = min(player_stats["max_mana"], before + amount)
        restored = player_stats["mana"] - before

    if kind == "mp_overcharge":
        before = player_stats["mana"]
        player_stats["mana"] = player_stats["max_mana"] + 40
        player_stats["is_overcharged"] = True
        restored = player_stats["mana"] - before

    if healed <= 0 and restored <= 0:
        show_notice("Nothing to Restore", name,
                    "You are already at full strength.", GRIM_WARN)
        return False

    player_stats["inventory"].pop(index)
    parts = []
    if healed:
        parts.append(f"+{healed} HP")
    if restored:
        parts.append(f"+{restored} MP")
    if kind == "mp_overcharge":
        parts.append("OVERCHARGE")
    show_notice("Potion Used", name, "  ·  ".join(parts),
                RARITY_COLORS.get(data["rarity"], GRIM_CREAM))
    print(f"Used {name}: {', '.join(parts)}")
    return True

def equip_item(index):
    """Equips an item from the player's inventory."""
    if index < 0 or index >= len(player_stats["inventory"]):
        return

    slot = player_stats["inventory"][index].get("slot")
    forbidden = equip_block_reason(slot)
    if forbidden:
        show_notice("Vow Forbids", player_stats["inventory"][index].get("name", ""), forbidden, GRIM_BAD)
        return
    item = player_stats["inventory"].pop(index)

    if slot in player_stats["equipment"]:
        old_item = player_stats["equipment"][slot]
        if old_item:
            player_stats["inventory"].append(old_item)
        player_stats["equipment"][slot] = item
        print(f"Equipped {item['name']} to {slot}.")
    else:
        # If not a gear item, put it back
        player_stats["inventory"].insert(index, item)
        print(f"Cannot equip {item['name']}. Not a gear item.")

def unequip_item(slot):
    """Move an equipped item from a slot back into the satchel, if there is room."""
    item = player_stats["equipment"].get(slot)
    if not item:
        return False
    if len(player_stats["inventory"]) >= ITEM_GRID_ROWS * ITEM_GRID_COLS:
        show_notice("Satchel Full", "No room", "Make space before unequipping.", GRIM_WARN)
        return False
    player_stats["equipment"][slot] = None
    player_stats["inventory"].append(item)
    show_notice("Unequipped", item["name"], f"{slot} slot emptied",
                RARITY_COLORS.get(item.get("rarity", "Common"), GRIM_CREAM))
    print(f"Unequipped {item['name']} from {slot}.")
    return True

# --- Character classes (chosen on the character screen) ---
# Base stats replace the defaults when the run starts; the multipliers apply on top of
# everything else for the whole run, so each class keeps its identity as it levels.
PLAYER_CLASSES = {
    "Mage": {
        "role": "Master of the elements",
        "blurb": "Best with magic, weaker in close combat.",
        "stats": {"max_hp": 90, "max_mana": 130, "melee_strength": 12, "element_strength": 14, "defense": 4},
        "mult": {"melee": 0.8, "element": 1.3, "defense": 1.0},
        "weapon": 1.0, "magic_weapon": 2.0, "unarmed": 1.0,
        "perk": "Arcane Focus", "perk_text": "Magic weapons give double their bonus.",
        "perk_short": "magic weapons x2",
    },
    "Brawler": {
        "role": "Fists before steel",
        "blurb": "Unmatched bare-handed; can use magic, but below average.",
        "stats": {"max_hp": 115, "max_mana": 90, "melee_strength": 17, "element_strength": 9, "defense": 6},
        "mult": {"melee": 1.0, "element": 0.85, "defense": 1.0},
        "weapon": 0.5, "magic_weapon": 1.0, "unarmed": 1.35,
        "perk": "Iron Fists", "perk_text": "+35% melee while unarmed; weapons give half their bonus.",
        "perk_short": "+35% melee unarmed, weapons x0.5",
    },
    "Knight": {
        "role": "Sworn to the blade",
        "blurb": "Best with weapons; below-average magic.",
        "stats": {"max_hp": 110, "max_mana": 90, "melee_strength": 15, "element_strength": 9, "defense": 8},
        "mult": {"melee": 1.0, "element": 0.85, "defense": 1.15},
        "weapon": 3.0, "magic_weapon": 1.0, "unarmed": 1.0,
        "perk": "Weapon Master", "perk_text": "Weapon melee bonuses are tripled.",
        "perk_short": "weapon bonuses x3",
    },
}
CLASS_ORDER = ["Mage", "Brawler", "Knight"]
FREE_STAT_POINTS = 5       # handed out on the character screen; anything unspent carries over
STAT_POINT_VALUE = {"max_hp": 5, "max_mana": 10, "melee_strength": 1, "element_strength": 1, "defense": 1}


# --- Races (also chosen on the character screen) ---
# "add" is applied to the starting stats; "mult" stacks with the class multipliers for the
# whole run. Each race also has a look feature drawn on the sprite (make_tiles.race_features).
PLAYER_RACES = {
    "Human":    {"blurb": "Adaptable, and quick to learn.", "perk": "Versatile",
                 "perk_text": "+1 free stat point and +10% XP from every kill.",
                 "add": {}, "mult": {}, "free_points": 1, "xp": 1.10},
    "Elf":      {"blurb": "Old blood of the deep forests.", "perk": "Fey Blood",
                 "perk_text": "Element x1.15 and +20 MP, but -10 max HP.",
                 "add": {"max_mana": 20, "max_hp": -10}, "mult": {"element": 1.15}},
    "Orc":      {"blurb": "Born to the war-band.", "perk": "Bloodrage",
                 "perk_text": "Melee x1.15 and +20 max HP, but Element x0.9.",
                 "add": {"max_hp": 20}, "mult": {"melee": 1.15, "element": 0.9}},
    "Dwarf":    {"blurb": "Stubborn as the mountain.", "perk": "Stoneborn",
                 "perk_text": "Defense x1.2 and +10 max HP, but -10 MP.",
                 "add": {"max_hp": 10, "max_mana": -10}, "mult": {"defense": 1.2}},
    "Skeleton": {"blurb": "Death was only a setback.", "perk": "Undying",
                 "perk_text": "12% chance to shrug off a hit; -15 max HP; healing potions restore half.",
                 "add": {"max_hp": -15}, "mult": {}, "shrug": 0.12, "potion_heal": 0.5},
    "Goblin":   {"blurb": "Small, sly and always looting.", "perk": "Sticky Fingers",
                 "perk_text": "+10 luck (more drops, richer chests), but -10 max HP.",
                 "add": {"max_hp": -10}, "mult": {}, "luck": 10},
}
RACE_ORDER = ["Human", "Elf", "Orc", "Dwarf", "Skeleton", "Goblin"]


def player_race():
    return PLAYER_RACES.get(player_stats.get("race"))


def race_value(key, default=1.0):
    r = player_race()
    if not r:
        return default
    return r["mult"].get(key, default) if key in ("melee", "element", "defense") else r.get(key, default)


# Elemental Infusion — an Elf who walks the Mage's path wreathes their melee in their
# element: the blow shows it, deals part of their element strength on top, and the
# element's matchup counts. Nobody else (foes included) swings with an element.
INFUSION_ELEMENT_SHARE = 0.25      # share of element strength added to an infused swing
INFUSION_DAMAGE_PENALTY = 3        # an infused swing hits 3 points softer than the formula


def has_elemental_infusion():
    return player_stats.get("race") == "Elf" and player_stats.get("class") == "Mage"


def race_xp_mult():
    return race_value("xp")


def player_class():
    return PLAYER_CLASSES.get(player_stats.get("class"))


def class_factor(key):
    """A class modifier: "melee" / "element" / "defense" multipliers, or the weapon,
    magic-weapon and unarmed factors. 1.0 when no class has been chosen."""
    c = player_class()
    base = 1.0 if not c else (c["mult"][key] if key in c["mult"] else c.get(key, 1.0))
    if key in ("melee", "element", "defense"):
        base *= race_value(key)            # race multipliers stack with the class's
    return base


def unarmed_bonus_active():
    return class_factor("unarmed") != 1.0 and not player_stats["equipment"].get("Weapon")


def class_summary():
    """One line for the Stats page: the class, its perk and its multipliers."""
    c = player_class()
    if not c:
        return ""
    r = player_race()
    mods = [f"{lbl} ×{round(class_factor(k), 2):g}" for k, lbl in (("melee", "Melee"), ("element", "Element"),
                                                                  ("defense", "Defense")) if round(class_factor(k), 3) != 1.0]
    perk = f"{c['perk']}: {c['perk_short']}"
    if c.get("unarmed", 1.0) != 1.0:
        perk += " (active)" if unarmed_bonus_active() else " (inactive: weapon equipped)"
    who = f"{player_stats['race']} {player_stats['class']}" if r else player_stats["class"]
    parts = [f"{who} — {perk}"]
    if r:
        parts.append(r["perk"])
    return "  ·  ".join(parts + mods)


def item_bonus_parts(slot, item):
    """Every stat bonus an equipped item carries, as (stat, label, percent, active).
    Inactive parts are ones the item has but isn't applying right now — armour attuned to
    another element, or any element boost under Covenant of Bare Iron. This is the single
    source for both the stat maths and the Stats page, so the two can't disagree."""
    st = get_item_stats(item)
    parts = []
    if st.get("melee_boost"):           # weapons: the class decides how much they help
        parts.append(("melee", "Melee", int(round(st["melee_boost"] * class_factor("weapon"))), True))
    if st.get("magic_boost"):
        parts.append(("element", "Magic", int(round(st["magic_boost"] * class_factor("magic_weapon"))), True))
    if slot != "Weapon":
        d = st.get("defense_boost", 0) * (2 if has_vow(V_BARE_IRON) else 1)   # Bare Iron doubles
        if d:
            parts.append(("defense", "Defense", d, True))
        el, eb = item.get("element"), st.get("element_boost", 0)
        if eb and el not in (None, "None"):
            # Elemental buff: only while the armour matches the player's element
            parts.append(("element", el, eb, el == player_stats["element"] and not has_vow(V_BARE_IRON)))
    return parts


def gear_bonus_pcts():
    """Combined active gear bonus per stat, in percent."""
    total = {"melee": 0, "element": 0, "defense": 0}
    for slot, item in player_stats["equipment"].items():
        if item:
            for stat, _label, pct, active in item_bonus_parts(slot, item):
                if active:
                    total[stat] += pct
    return total


def calculate_total_stats():
    """Calculates player stats including equipment bonuses as percentages of base stats."""
    # Base stats from player_stats
    base_hp = player_stats["max_hp"]
    base_melee = player_stats["melee_strength"]
    base_element = player_stats["element_strength"]
    base_defense = player_stats["defense"]

    gear = gear_bonus_pcts()
    total_melee_pct = gear["melee"]
    total_defense_pct = gear["defense"]
    total_element_pct = gear["element"]

    return {
        "max_hp": base_hp, # Currently no HP boosts from items
        "max_mana": player_stats["max_mana"],
        "melee_strength": int(base_melee * (1 + total_melee_pct / 100) * vow_stat_mult("melee")
                              * class_factor("melee") * (class_factor("unarmed") if unarmed_bonus_active() else 1.0)),
        "element_strength": int(base_element * (1 + total_element_pct / 100) * vow_stat_mult("element")
                                * class_factor("element")),
        "defense": int(base_defense * (1 + total_defense_pct / 100) * vow_stat_mult("defense")
                       * class_factor("defense"))
    }

# --- Game States & Combat Constants ---
STATE_EXPLORE = 0; STATE_COMBAT = 1; STATE_GAME_OVER = 2; STATE_VICTORY = 3; STATE_REROLL_PROMPT = 4; STATE_STAGE_CLEAR = 5; STATE_EVOLVE = 6; STATE_MENU = 7; STATE_ADMIN_COMMAND = 8; STATE_PAUSE = 9; STATE_CREATE = 10; STATE_MAP = 11; STATE_DIALOGUE = 12; STATE_QUESTS = 13
COMBAT_ACTION_ATTACK = 0; COMBAT_ACTION_DEFEND = 1; COMBAT_ACTION_FLEE = 2; COMBAT_ACTION_AWAKEN = 99; COMBAT_ACTION_CHARGE = 3
COMBAT_ACTION_ITEM = 4
MENU_TABS = ["Stats", "Inventory", "Info", "Evolution", "Bindings"]
INFO_PAGES = ["Overview", "Evolution", "Abilities"]   # sub-pages of the Info tab

# Bindings — vows the player can swear for a boon at a cost. Every vow in VOWS is listed on
# the Bindings page. Swearing one spends VOW_STAT_COST stat points, at most VOW_LIMIT can be
# sworn per run, and a sworn vow is permanent. Entry format:
#   {"name": "Vow of Embers",          # unique — sworn vows are stored by name
#    "circle": "Element",              # one of VOW_CIRCLES — the dropdown it's listed under
#    "boon": "+20% skill damage",      # shown in green
#    "cost": "-25% max HP",            # shown in red
#    "apply": fn}                      # optional: fn(player_stats) runs once when sworn
VOWS = []
VOW_LIMIT = 3
VOW_STAT_COST = 10
# The circles vows are grouped into on the Bindings page, in display order, each with the
# accent colour its dropdown header wears.
VOW_CIRCLES = [
    ("Flesh",     (192, 67, 63)),    # the body — crimson
    ("Element",   (90, 134, 200)),   # arcane blue
    ("Restriction", (205, 140, 60)), # amber — sealed locks
    ("Fate",      (212, 175, 55)),   # gold
    ("Hunt",      (143, 191, 106)),  # ward green
    ("Dark",      (140, 108, 196)),  # violet
    ("Forbidden", (220, 80, 150)),   # sickly magenta
]
VOW_UNBOUND = "Unbound"   # catch-all for a vow whose circle is missing or misspelled


def load_vows(path=os.path.join("bindings", "vows.json")):
    """Fill VOWS from bindings/vows.json. Circle titles like "First Circle — Vows of Flesh"
    map onto VOW_CIRCLES by keyword; "Magic Restriction — Vow of the Sealed Blade" is split
    into a subtitle and the vow's name."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"Warning: could not load vows ({path}): {e}")
        return
    keys = [n for n, _ in VOW_CIRCLES]
    VOWS.clear()
    for group in data:
        title = group.get("circle", "")
        circle = next((k for k in keys if k.lower() in title.lower()), VOW_UNBOUND)
        for v in group.get("vows", []):
            name = v.get("name", "")
            subtitle = ""
            if " — " in name:
                subtitle, name = name.split(" — ", 1)
            VOWS.append({"name": name, "subtitle": subtitle, "circle": circle,
                         "boon": v.get("boon", ""), "cost": v.get("cost", ""),
                         "flavour": v.get("flavour", "")})
    print(f"Loaded {len(VOWS)} vows.")


load_vows()

# ==================== Vow Effects ====================
# Every vow in bindings/vows.json, by the name the game keys its effect on.
V_OPEN_WOUND = "Vow of the Open Wound"
V_IRON_SKIN = "Oath of Iron Skin"
V_LAST_BREATH = "Pact of the Last Breath"
V_BLOOD_TITHE = "Blood Tithe"
V_MARTYR = "Covenant of the Martyr"
V_UNCHANGING = "Covenant of the Unchanging"
V_HOLLOW = "Oath of the Hollow Vessel"
V_OVERFLOW = "Vow of the Overflow"
V_WEAK_POINT = "Oath of the Weak Point"
V_SPENT_STAR = "Vow of the Spent Star"
V_SEALED_BLADE = "Vow of the Sealed Blade"
V_SILENT_TONGUE = "Vow of the Silent Tongue"
V_BARE_SOUL = "Vow of the Bare Soul"
V_EMPTY_SATCHEL = "Oath of the Empty Satchel"
V_SLUMBER = "Vow of Eternal Slumber"
V_DRY_WELL = "Vow of the Dry Well"
V_HUMBLE_ROOT = "Oath of the Humble Root"
V_CHANGING_STEP = "Oath of the Changing Step"
V_UNFLINCHING = "Vow of the Unflinching"
V_GAMBLER = "Gambler's Oath"
V_RISING_TIER = "Vow of the Rising Tier"
V_ROOTLESS = "Oath of the Rootless"
V_SCARRED = "Vow of the Scarred Page"
V_NO_RETREAT = "Vow of No Retreat"
V_FIRST_STRIKE = "Oath of the First Strike"
V_LONG_AWAKE = "Vow of the Long Awakening"
V_EARLY_WAKE = "Oath of the Early Waking"
V_HUNTER = "Hunter's Vow"
V_TORCH = "Vow of the Guttering Torch"
V_STARVED = "Oath of the Starved"
V_EMPTY_HAND = "Vow of the Empty Hand"
V_BARE_IRON = "Covenant of Bare Iron"
V_POVERTY = "Vow of Poverty"
V_ECLIPSE = "The Eclipse Covenant"
V_ONE = "Oath of One"
V_UNBOUND_VOW = "Vow of the Unbound"
V_FINAL_STAGE = "Pact of the Final Stage"
V_BERSERKER = "Berserker"

_missing = [n for k, n in list(globals().items()) if k.startswith("V_") and isinstance(n, str)
            and n not in {v["name"] for v in VOWS}]
if VOWS and _missing:
    print(f"Warning: vows.json has no entry for: {', '.join(_missing)}")

# Percentage stat changes, applied in calculate_total_stats (one multiplier per vow)
VOW_STAT_MULTS = {
    V_OPEN_WOUND:    {"melee": 1.40},
    V_IRON_SKIN:     {"defense": 1.50, "melee": 0.70},
    V_BLOOD_TITHE:   {"element": 1.30},
    V_UNCHANGING:    {"element": 1.25},
    V_SEALED_BLADE:  {"element": 1.60},
    V_SILENT_TONGUE: {"melee": 1.60},
    V_BARE_SOUL:     {"melee": 1.35, "element": 1.35},
    V_SLUMBER:       {"melee": 1.20, "element": 1.20, "defense": 1.20},
}
# Max HP / MP changes, applied once when the vow is sworn (they rescale the stat itself)
VOW_MAX_MULTS = {
    V_MARTYR:        {"max_hp": 0.75},
    V_EMPTY_SATCHEL: {"max_hp": 1.30},
    V_SLUMBER:       {"max_hp": 1.20, "max_mana": 1.20},
    V_HOLLOW:        {"max_mana": 0.50},
}
# Pairs that can't be sworn together — the doc's "opposing vows", plus Unbound/Unchanging
# (you'd be left with no element and no way to bind one) and Humble Root/Rising Tier (a
# rebind landing above Tier 1 would break the Root).
VOW_CONFLICTS = [(V_SEALED_BLADE, V_SILENT_TONGUE), (V_SEALED_BLADE, V_EMPTY_HAND),
                 (V_UNBOUND_VOW, V_UNCHANGING), (V_HUMBLE_ROOT, V_RISING_TIER)]
FORBIDDEN_UNLOCK_STAGE = 3        # the Forbidden Circle opens once this stage is cleared (0: always open)
RISING_TIER_CHANCE = 0.35         # Rising Tier: odds a rebind lands one tier higher
HUMBLE_ROOT_TRUE_MULT = 6.0
ECLIPSE_BURN_PCT = 0.03
EARLY_WAKE_COST_PCT = 0.20
BERSERKER_HP_STEP = 10            # Berserker: +1% damage per this much missing HP
BERSERKER_DAMAGE_TAKEN = 1.15     # …and enemies hit 15% harder
STARVED_REGEN_SECONDS = 2.0       # Oath of the Starved: +1% max HP this often while exploring
_starved_regen = [0.0]
_gamble = {"cost": None}          # Gambler's Oath: this prompt's rolled rebind cost
_kill_ctx = {"boss": False, "final": False, "spins": (0, 0)}   # the last kill (Rootless; spins it dropped)


def roll_spin_drops(is_boss):
    """Roll this win's spin chances. Returns (spins won, chances rolled)."""
    kind = "boss" if is_boss else "normal"
    rolls = 2 if has_vow(V_GAMBLER) else 1
    won = chances = 0
    for _ in range(rolls):
        if kind in SPIN_DROP_TABLE:
            table = SPIN_DROP_TABLE[kind]
            won += random.choices(range(len(table)), weights=table)[0]
            chances += len(table) - 1
        else:
            n, odds = SPIN_DROP_CHANCES[kind]
            won += sum(1 for _ in range(n) if random.random() < odds)
            chances += n
    return won, chances
# Notes shown under a card's hover preview where the game needs to say a little more
VOW_NOTES = {
    V_RISING_TIER: "Each rebind has a 35% chance to land one tier higher (Tier 2, or Tier 6 from Tier 5).",
    V_HUNTER: "The extra enemies arrive from the next stage.",
    V_FINAL_STAGE: "Double chests begin from the next stage.",
    V_SCARRED: "Stat points can't be refunded in this game, so the cost is already true.",
    V_UNBOUND_VOW: "Swearing it grants 10 spins and unbinds your element; rebind after your next fight.",
    V_ONE: "You choose the stat when you swear.",
    V_EMPTY_SATCHEL: "No potions at all, in or out of combat.",
    V_UNCHANGING: "Mastery needs no True Sigil — open it from the Evolution tab at level 10.",
}


def has_vow(name):
    return name in player_stats.get("vows", ())


def vow_stat_mult(stat):
    m = 1.0
    for name in player_stats.get("vows", ()):
        m *= VOW_STAT_MULTS.get(name, {}).get(stat, 1.0)
    return m


def vow_stat_summary():
    """Combined effect of every sworn vow on each stat, as a percentage (+40, -25, …).
    Stats no vow touches are left out."""
    keys = [("max_hp", None), ("max_mana", None), ("melee_strength", "melee"),
            ("element_strength", "element"), ("defense", "defense")]
    out = {}
    for key, live in keys:
        m = 1.0
        for name in player_stats.get("vows", ()):
            m *= VOW_MAX_MULTS.get(name, {}).get(key, 1.0)
            if live:
                m *= VOW_STAT_MULTS.get(name, {}).get(live, 1.0)
        pct = int(round((m - 1.0) * 100))
        if pct:
            out[key] = pct
    return out


def vow_by_name(name):
    return next((v for v in VOWS if v["name"] == name), None)


def vow_conflict(vow):
    """The sworn vow this one clashes with, if any."""
    for a, b in VOW_CONFLICTS:
        if vow["name"] == a and has_vow(b):
            return b
        if vow["name"] == b and has_vow(a):
            return a
    return None


def vow_forbidden_locked(vow):
    return vow.get("circle") == "Forbidden" and progress_stage() <= FORBIDDEN_UNLOCK_STAGE


def vow_ineligible(vow):
    """A reason the player's current build can't take this vow, or None."""
    if vow["name"] == V_HUMBLE_ROOT:
        el = player_stats.get("element")
        if not (el is None or el in tier1_elements or el in TRUE_ELEMENT_NAMES):
            return "Only while bound to a Tier 1 element or a True Form."
    return None


def vow_block_detail(vow):
    """Full explanation of why a vow can't be sworn (for the hover preview)."""
    if vow_is_sworn(vow):
        return f"Sworn — only an {OATHBREAKER} can break it."
    if len(player_stats.get("vows", [])) >= VOW_LIMIT:
        return f"You already hold {VOW_LIMIT} vows."
    if vow_forbidden_locked(vow):
        return f"The Forbidden Circle opens after you clear stage {FORBIDDEN_UNLOCK_STAGE}."
    other = vow_conflict(vow)
    if other:
        return f"Clashes with {other}."
    why = vow_ineligible(vow)
    if why:
        return why
    if player_stats["stat_points"] < VOW_STAT_COST:
        return f"Needs {VOW_STAT_COST} stat points (you have {player_stats['stat_points']})."
    return None


def awaken_level_req():
    return 1 if has_vow(V_EARLY_WAKE) else AWAKENING_LEVEL_REQ


def early_wake_cost():
    return max(1, int(player_stats["max_hp"] * EARLY_WAKE_COST_PCT))


def true_form_level():
    return 10 if has_vow(V_UNCHANGING) else TRUE_ELEMENT_LEVEL_REQ


def torch_radius():
    return 3.0 if has_vow(V_TORCH) else TORCH_RADIUS


def vow_xp_mult():
    m = race_xp_mult()                       # Human: Versatile
    if has_vow(V_NO_RETREAT):
        m *= 1.25
    if has_vow(V_FINAL_STAGE):
        m *= 2.0
    return m


def vow_matchup(mult):
    """Oath of the Weak Point sharpens both ends of the matchup wheel for the player's hits."""
    if has_vow(V_WEAK_POINT):
        if mult >= SUPER_EFFECTIVE_MULTIPLIER:
            return 2.0
        if mult <= NOT_EFFECTIVE_MULTIPLIER:
            return 0.25
    return mult


def vow_tier_factor(player_element, enemy_element):
    """Scales the player's tier damage multiplier (Eclipse, Spent Star)."""
    f = 1.0
    if has_vow(V_ECLIPSE):
        f *= 2.0
    if has_vow(V_SPENT_STAR):
        pt, et = get_element_tier(player_element), get_element_tier(enemy_element)
        if et < pt:
            f *= 1.5
        elif et > pt:
            f *= 0.5
    return f


def berserker_bonus_pct():
    """Berserker's current damage bonus: 1% for every 10 HP missing (0 without the vow)."""
    if not has_vow(V_BERSERKER):
        return 0
    missing = max(0, player_stats["max_hp"] - player_stats["hp"])
    return missing // BERSERKER_HP_STEP


def vow_damage_factor():
    """Multiplier on everything the player deals this attack. Uses up First Strike."""
    f = 1.0
    if has_vow(V_LAST_BREATH) and player_stats["hp"] < player_stats["max_hp"] * 0.25:
        f *= 2.0
    if has_vow(V_CHANGING_STEP):
        f *= 1.4
    f *= 1.0 + berserker_bonus_pct() / 100.0
    if player_stats.get("first_strike_ready"):
        player_stats["first_strike_ready"] = False
        f *= 3.0
    return f


def martyr_can_save():
    return (has_vow(V_MARTYR) and not player_stats.get("martyr_used")
            and not has_vow(V_FINAL_STAGE))


def combat_items():
    """Potions in the satchel that can be drunk in battle: [(name, count)], in potion order."""
    counts = {}
    for it in player_stats["inventory"]:
        n = it.get("name")
        if n in POTION_DATA:
            counts[n] = counts.get(n, 0) + 1
    return [(n, counts[n]) for n in POTION_DATA if n in counts]


def combat_item_problem(name):
    """Why this potion can't be drunk right now (vow, nothing to restore), or None."""
    data = POTION_DATA.get(name)
    if not data:
        return "That can't be used in battle."
    why = potion_block_reason(data["kind"])
    if why:
        return why
    kind = data["kind"]
    hp_full = player_stats["hp"] >= player_stats["max_hp"]
    mp_full = player_stats["mana"] >= player_stats["max_mana"]
    if (kind == "hp" and hp_full) or (kind == "mp" and mp_full) or (kind == "both" and hp_full and mp_full) \
            or (kind == "mp_overcharge" and player_stats.get("is_overcharged")):
        return f"The {name} would do nothing — you're already full."
    return None


def potion_block_reason(kind):
    if has_vow(V_EMPTY_SATCHEL):
        return "Oath of the Empty Satchel forbids potions."
    if has_vow(V_STARVED):
        return "Oath of the Starved forbids potions."
    if has_vow(V_LAST_BREATH) and kind in ("hp", "both"):
        return "Pact of the Last Breath forbids HP potions."
    return None


def equip_block_reason(slot):
    if slot == "Weapon" and has_vow(V_EMPTY_HAND):
        return "Vow of the Empty Hand forbids weapons."
    if slot in ("Helmet", "Chest", "Boots") and has_vow(V_BARE_SOUL):
        return "Vow of the Bare Soul forbids armour."
    return None


def vow_chest_rarity(rarity, vows=None):
    """Guttering Torch lifts a chest one rarity step; Poverty floors it at Rare."""
    vows = player_stats.get("vows", ()) if vows is None else vows
    i = CHEST_RARITIES.index(rarity) if rarity in CHEST_RARITIES else 0
    if V_TORCH in vows:
        i += 1
    if V_POVERTY in vows:
        i = max(i, CHEST_RARITIES.index("Rare"))
    return CHEST_RARITIES[min(i, len(CHEST_RARITIES) - 1)]


def combat_action_block(kind):
    """Why a combat action ("skills", "melee", "defend", "awaken", "charge", "flee") is
    unavailable right now, or None."""
    ps = player_stats
    if _bonus_turn["active"] and kind != "skills":
        return "Overcharge bonus strike: only an elemental attack can be used!"
    if kind == "melee" and has_vow(V_SEALED_BLADE):
        return "Vow of the Sealed Blade: you cannot use melee attacks."
    if kind == "skills" and has_vow(V_SILENT_TONGUE):
        return "Vow of the Silent Tongue: you cannot use elemental attacks."
    if kind == "defend" and (has_vow(V_OPEN_WOUND) or has_vow(V_UNFLINCHING)):
        return "Your vow forbids you to Defend."
    if kind == "flee" and (has_vow(V_NO_RETREAT) or has_vow(V_UNFLINCHING)):
        return "Your vow forbids you to Flee."
    if kind == "charge" and has_vow(V_DRY_WELL):
        return "Vow of the Dry Well: you cannot Charge."
    if kind == "items":
        if has_vow(V_EMPTY_SATCHEL):
            return "Oath of the Empty Satchel forbids potions."
        if has_vow(V_STARVED):
            return "Oath of the Starved forbids potions."
        if not combat_items():
            return "You have no potions to use."
    if kind == "awaken":
        if has_vow(V_SLUMBER):
            return "Vow of Eternal Slumber: you can never Awaken."
        if ps["level"] < awaken_level_req():
            return "Level not high enough to Awaken!"
        if ps["is_awakened"]:
            return "Already Awakened!"
        if ps["awakening_cooldown"] > 0:
            return "Awakening is on cooldown!"
        if has_vow(V_EARLY_WAKE) and ps["hp"] <= early_wake_cost():
            return f"Too weak to Awaken early — it costs {early_wake_cost()} HP."
    if has_vow(V_CHANGING_STEP) and ps.get("last_action") == kind:
        return "Oath of the Changing Step: never the same action twice in a row."
    return None


def skill_cost_label(cost):
    return f"{cost} HP" if has_vow(V_BLOOD_TITHE) else f"{cost} MP"


def overcharge_strike_ready():
    """Whether any elemental skill could be used right now (off cooldown and affordable)."""
    if has_vow(V_SILENT_TONGUE):
        return False
    el = player_stats["element"]
    for sk in ELEMENT_SKILLS.get(el, DEFAULT_SKILLS):
        cd = 0 if player_stats.get("cooldowns_disabled") else player_stats["skill_cooldowns"].get(sk["name"], 0)
        if cd == 0 and skill_affordable(get_skill_mana_cost(el, sk["name"])):
            return True
    return False


def skill_affordable(cost):
    if has_vow(V_BLOOD_TITHE):
        return player_stats["hp"] > cost
    return player_stats["mana"] >= cost


def rebind_terms(element):
    """(cost, block_reason, note) for rebinding from the reroll prompt."""
    if has_vow(V_UNCHANGING):
        return 0, "Covenant of the Unchanging: your element can never be rebound.", ""
    if has_vow(V_ROOTLESS) and (_kill_ctx["boss"] or _kill_ctx["final"]):
        return 0, "Oath of the Rootless: no rebinding after a boss or a stage's final foe.", ""
    is_high = element in tier5_elements or element in tier6_elements or element in tier7_elements
    cost = T5_REROLL_COST if is_high else NORMAL_REROLL_COST
    note = ""
    if has_vow(V_GAMBLER):
        if _gamble["cost"] is None:
            _gamble["cost"] = random.randint(1, 6)
        cost = _gamble["cost"]
        note = "Gambler's Oath rolled the price."
    if has_vow(V_ROOTLESS) and player_stats.get("rootless_stage") != current_stage:
        cost = 0
        note = "Oath of the Rootless: your first rebind this stage is free."
    return cost, None, note


def _scale_max(stat, cur, factor):
    old = player_stats[stat]
    new = max(1, int(round(old * factor)))
    player_stats[stat] = new
    player_stats[cur] = max(1, min(new, player_stats[cur] + max(0, new - old)))


def _force_unequip(slot):
    item = player_stats["equipment"].get(slot)
    if item:
        player_stats["equipment"][slot] = None
        player_stats["inventory"].append(item)


def _on_vow_sworn(name):
    """One-time consequences of swearing a vow. Everything else is read live via has_vow."""
    ps = player_stats
    for stat, factor in VOW_MAX_MULTS.get(name, {}).items():
        _scale_max(stat, "hp" if stat == "max_hp" else "mana", factor)
    if name == V_RISING_TIER:
        ps["xp_to_next_level"] = int(ps["xp_to_next_level"] * 1.5)
    elif name == V_EMPTY_HAND:
        _force_unequip("Weapon")
    elif name == V_BARE_SOUL:
        for slot in ("Helmet", "Chest", "Boots"):
            _force_unequip(slot)
    elif name in (V_TORCH, V_POVERTY):
        for chest in chests:              # unopened chests on this stage improve at once
            if not chest.opened:
                chest.rarity = vow_chest_rarity(chest.rarity, vows=(name,))
    elif name == V_UNBOUND_VOW:
        ps["reroll_spins"] += 10
        ps["element"] = None
        record_element_change(None)
# ==================== end Vow Effects ====================

# Inventory Sub-states
INVENTORY_SUBSTATE_VIEWING = 0
INVENTORY_SUBSTATE_NAVIGATING_ITEMS = 1
INVENTORY_SUBSTATE_NAVIGATING_EQUIP = 2   # cursor on the equipment column (to unequip)
EQUIP_SLOTS = ["Helmet", "Chest", "Boots", "Weapon"]

# Stats Sub-states
STATS_SUBSTATE_VIEWING = 0
STATS_SUBSTATE_NAVIGATING = 1

# Item Grid Constants
ITEM_GRID_ROWS = 5
ITEM_GRID_COLS = 10
ITEM_BOX_SIZE = 38 # Size of each item box (e.g., 48x48 pixels)
ITEM_BOX_PADDING = 5 # Padding between item boxes

ITEM_BOX_COLOR = (50, 50, 50)
ITEM_HIGHLIGHT_COLOR = (200, 200, 0) # Yellow for selected item

# Stats Highlight Color
STAT_HIGHLIGHT_COLOR = (0, 200, 200) # Cyan for selected stat

# --- Element Evolution Mapping ---
EVOLUTION_MAP = {
    # Tier 1 -> Tier 2
    "Water": ["Ice", "Mist", "Blood"],
    "Earth": ["Sand", "Metal", "Mud", "Dust"],
    "Fire": ["Combustion", "Inferno", "Mist", "Lava"],
    "Wind": ["Storm", "Gale"],
    "Lightning": ["Plasma", "Storm"],
    
    # Tier 2 -> Tier 3
    "Ice": ["Frost Fire"],
    "Mud": ["Wood"],
    "Plasma": ["Energy", "Nuclear"],
    
    # Tier 3 -> Tier 4
    "Energy": ["Kinetic", "Potential", "Matter", "Dark Matter"],
    
    # Tier 4 -> Tier 5 (Universal)
    "Kinetic": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Potential": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Matter": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Dark Matter": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Frost Fire": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Wood": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],
    "Nuclear": ["Dark", "Light", "Time", "Reality", "Space", "Gravity"],

    # Tier 5 -> Tier 6
    "Dark": ["Shadow", "Lunar"],
    "Light": ["Solar"],
    "Time": ["Shadow", "Lunar", "Solar"],
    "Reality": ["Shadow", "Lunar", "Solar"],
    "Space": ["Shadow", "Lunar", "Solar"],
    "Gravity": ["Shadow", "Lunar", "Solar"],
    
    # Tier 6 -> Tier 7
    "Shadow": ["Eclipse"],
    "Lunar": ["Eclipse"],
    "Solar": ["Eclipse", "Star Force"],
}

# --- Element Affinity (which base element an evolution fights as) ---
# An evolution inherits its ancestor's place on the matchup wheel: Ice is Water's child, so
# Ice scalds a Lava (Fire) enemy exactly as Water would. Affinity is DERIVED by walking
# EVOLUTION_MAP back to a Tier 1 root, so adding an evolution automatically inherits the
# right matchups instead of needing a second table kept in sync by hand.
#
# Elements whose lineage converges from several different roots are genuinely hybrid.
# Tier 5+ ("Universal") descends from every branch at once, so those transcend the wheel
# and deal neutral damage both ways — their enormous tier multipliers are their edge.
ELEMENT_AFFINITY_OVERRIDES = {
    "Mist":  "Water",      # steam reads as water, and it's the Water line's own Tier 2
    "Storm": "Lightning",  # the thunderhead; Gale already carries the Wind line
}

def _build_element_affinity():
    parents = {}
    for parent, children in EVOLUTION_MAP.items():
        for child in children:
            parents.setdefault(child, set()).add(parent)

    def roots(element, seen=None):
        seen = seen or set()
        if element in tier1_elements:
            return {element}
        if element in seen:
            return set()
        seen.add(element)
        found = set()
        for p in parents.get(element, ()):
            found |= roots(p, seen)
        return found

    affinity = {}
    for element in ALL_ELEMENTS:
        if element in ELEMENT_AFFINITY_OVERRIDES:
            affinity[element] = ELEMENT_AFFINITY_OVERRIDES[element]
            continue
        if element in TRUE_TO_BASE:          # True forms fight as the element they mastered
            affinity[element] = TRUE_TO_BASE[element]
            continue
        found = roots(element)
        if len(found) == 1:                  # one clean ancestor -> inherit its matchups
            affinity[element] = next(iter(found))
    return affinity

ELEMENT_AFFINITY = _build_element_affinity()


# --- Player lineage (the branch actually taken) ---
# The affinity table can't say which base a player came from when an element has several
# parents: Mist is reached from Water OR Fire, Storm from Wind OR Lightning, and every
# Universal element from all of them. So the player's path is recorded as it happens, and
# spell effects carry hints of wherever it started.
def record_element_change(new_element, evolved=False, sidestep=False):
    """Keep player_stats["lineage"] in step with the element.
    evolved  -> the new element grew out of the current one (evolution, True form, ascension)
    sidestep -> swapped at the same stage (a Tier 5 reroll), so the root is kept
    otherwise    a fresh start (Tier 1 reroll, new game, admin override)"""
    lineage = list(player_stats.get("lineage") or [])
    if evolved and lineage:
        lineage.append(new_element)
    elif sidestep and lineage:
        lineage[-1] = new_element
    else:
        lineage = [new_element]
    player_stats["lineage"] = lineage


def branch_root(element, lineage=None):
    """The Tier 1 element `element` descends from, following `lineage` when it's known to
    lead to this element. None for a Tier 1 element itself, or when no single root exists."""
    if lineage and lineage[-1] == element:
        root = lineage[0]
        if root not in tier1_elements:
            root = ELEMENT_AFFINITY.get(root)
    else:
        root = ELEMENT_AFFINITY.get(element)
    return root if root in tier1_elements and root != element else None

# --- Combat Sub-States ---
COMBAT_SUBSTATE_CHOOSE_ACTION = 0; COMBAT_SUBSTATE_CHOOSE_SKILL = 1; COMBAT_SUBSTATE_CHOOSE_ITEM = 2
_combat_item = {"pick": None}      # the potion chosen from the battle bag, until the turn plays it
# Overcharging grants an immediate bonus strike before the foe can answer — but the surge
# only has an outlet in the element: the bonus action must be an elemental skill.
_bonus_turn = {"active": False}
SKILL_ROW_H = 26   # row pitch in the combat skill list; the strip sizes itself from this

# --- Enemy Type Definitions ---
ENEMY_TYPES = [
    {"name": "Goblin", "image_path": "images/goblin.png", "hp": 50, "attack": 10, "defense": 3 }, {"name": "Skeleton", "image_path": "images/skeleton.png", "hp": 40, "attack": 12, "defense": 2 },
    {"name": "Orc", "image_path": "images/orc.png", "hp": 80, "attack": 15, "defense": 5 }, {"name": "Slime", "image_path": "images/slime.png", "hp": 60, "attack": 8, "defense": 6 },
    {"name": "Shadow Lurker", "image_path": "images/shadow.png", "hp": 45, "attack": 14, "defense": 1 }
]
DEFAULT_ENEMY_IMAGE_PATH = "images/missing.png"

# --- Foes scale with the hero's level ---
# When a fight starts, the foe takes a level near yours and its stats grow with it, on top
# of the danger tier / dungeon room / wave scaling it was made with. Per level above 1:
FOE_LEVEL_HP = 0.10          # HP:      x(1 + 0.10 per level)
FOE_LEVEL_ATK_PCT = 0.04     # Attack:  x(1 + 0.04 per level) + 1.5 per level — keeps pace with
FOE_LEVEL_ATK_FLAT = 1.5     #          the defence a hero gains, so hits keep landing
FOE_LEVEL_DEF_FLAT = 0.6     # Defense: +0.6 per level
FOE_LEVEL_XP = 0.05          # XP:      x(1 + 0.05 per level) — tougher foes are worth more
FOE_LEVEL_SPREAD = (-1, 0, 0, 1)   # a foe is your level, give or take one...
FOE_BOSS_LEVELS = 2                # ...and a boss is two above
WALL_TEXTURE_PATH = "images/wall_brick.png"

# --- Element Icons Mapping ---
ELEMENT_ICONS_MAP = {
    "Wind": "icons/Wind.png", "Combustion": "icons/Combustion.png", "Dark Matter": "icons/Dark_matter.png", "Dark": "icons/Darkness.png",
    "Dust": "icons/Dust.png", "Earth": "icons/Earth.png", "Energy": "icons/Energy.png", "Fire": "icons/Fire.png",
    "Frost Fire": "icons/Frost_fire.png", "Gale": "icons/Gale.png", "Gravity": "icons/Gravity.png", "Ice": "icons/Ice.png",
    "Inferno": "icons/Inferno.png", "Kinetic": "icons/Kinetic.png", "Lava": "icons/Lava.png", "Light": "icons/Light.png",
    "Lightning": "icons/Lightning.png", "Lunar": "icons/Lunar.png", "Matter": "icons/Matter.png", "Metal": "icons/Metal.png",
    "Mist": "icons/Mist.png", "Mud": "icons/Mud.png", "Nuclear": "icons/Nuclear.png", "Plasma": "icons/Plasma.png",
    "Space": "icons/Portal.png", "Potential": "icons/Potential.png", "Reality": "icons/Reality.png", "Sand": "icons/Sand.png",
    "Shadow": "icons/Shadow.png", "Solar": "icons/Solar.png", "Storm": "icons/Storm.png", "Time": "icons/Time.png",
    "Water": "icons/Water.png", "Wood": "icons/Wood.png", "Blood": "icons/Blood.png",
    # True Forms — graded from their base art by make_true_icons.py (same frame, fiercer interior)
    "Hell Fire": "icons/Hell_Fire.png", "Tectonic Earth": "icons/Tectonic_Earth.png",
    "Abyssal Water": "icons/Abyssal_Water.png", "Tempest Wind": "icons/Tempest_Wind.png",
    "Celestial Lightning": "icons/Celestial_Lightning.png"
}

# --- Map Data (will be generated) ---
world_map = []; PLAYER_START_X = 1.5; PLAYER_START_Y = 1.5

# --- Map Generation ---
# The world is built by worldgen.py: a biome overworld per stage plus a cave per biome.
# --- Helper Functions for Element and Items ---
def get_element_tier(element):
    """Returns the tier index (1-8) of a given element. True forms report Tier 2 —
    they aren't in all_element_tiers, so they'd otherwise fall through to Tier 1."""
    if element in TRUE_ELEMENT_NAMES:
        return TRUE_ELEMENT_TIER
    for i, tier_list in enumerate(all_element_tiers):
        if element in tier_list:
            return i + 1
    return 1

def get_element_damage_multiplier(element):
    """Damage multiplier for an element. True forms sit a cut above a normal Tier 2."""
    if element in TRUE_ELEMENT_NAMES:
        return HUMBLE_ROOT_TRUE_MULT if has_vow(V_HUMBLE_ROOT) else TRUE_ELEMENT_DAMAGE_MULT
    return TIER_DAMAGE_MULTIPLIERS.get(get_element_tier(element), 1.0)

def matchup_key(element):
    """The base element this one fights as on the matchup wheel.

    Evolutions inherit their ancestor's place (Ice fights as Water, Lava as Fire), and
    True forms fight as the element they mastered. Universal (Tier 5+) elements have no
    affinity and fall through unchanged, so they land outside the wheel — neutral both ways."""
    return ELEMENT_AFFINITY.get(element, element)

def get_random_weighted_element(level=1, force_tier1=False, force_tier5=False):
    if force_tier5:
        chosen_tier_list = tier5_elements
    elif force_tier1 or level < 5:
        # If forcing tier 1, or if below level 5, only Tier 1 elements are available
        chosen_tier_list = all_element_tiers[0]
    else:
        # Level 5 or higher, all tiers are available based on weights
        chosen_tier_list = random.choices(all_element_tiers, weights=tier_weights, k=1)[0]
    
    chosen_element = random.choice(chosen_tier_list)
    return chosen_element

# --- Player ---
player_x = PLAYER_START_X; player_y = PLAYER_START_Y; player_angle = PLAYER_START_ANGLE
player_stats = {
    "max_hp": 100, "hp": 100, "max_mana": 100, "mana": 100, "is_overcharged": False, "melee_strength": 15, "element_strength": 10, "defense": 5, "is_defending": False, "element": None, "reroll_spins": 0,
    "level": 1, "xp": 0, "xp_to_next_level": BASE_XP_TO_LEVEL_UP, "is_awakened": False, "awakening_duration": 0, "awakening_cooldown": 0,
    # Start empty: the old placeholders had no slot/rarity, so equip_item rejected them.
    # Real gear now comes from chests and enemy drops.
    "stat_points": 5, "vows": [], "inventory": [], "equipment": {"Helmet": None, "Chest": None, "Boots": None, "Weapon": None}, "pending_evolution": False,
    "class": None, "race": None, "look": None,   # set on the character screen
    "true_forms_seen": [],   # True forms already witnessed, so the cinematic only plays once each
    "is_god": False,
    "luck": 0,
    "skill_cooldowns": {}
}
player_stats["element"] = get_random_weighted_element(player_stats["level"])
record_element_change(player_stats["element"])

# --- Enemies ---
class Enemy:
    def __init__(self, x, y, map_x, map_y, enemy_data, p_level=1, is_boss=False):
        self.x, self.y = x, y; self.map_x, self.map_y = map_x, map_y; self.alive = True
        self.element = get_random_weighted_element(p_level); self.name = enemy_data.get("name", "Unknown")
        # Keep the un-suffixed name so art lookups still work once "(BOSS)" is appended
        self.base_name = self.name
        self.is_boss = is_boss
        
        base_hp = enemy_data.get("hp", 50); base_attack = enemy_data.get("attack", 10); base_defense = enemy_data.get("defense", 3)
        
        if self.is_boss:
            self.name = f"{self.name} (BOSS)"
            base_hp *= 3
            base_attack = int(base_attack * 1.5)
            base_defense = int(base_defense * 1.5)

        self.max_hp = max(10, base_hp + random.randint(-5, 5)); self.hp = self.max_hp
        self.attack = max(1, base_attack + random.randint(-2, 2)); self.defense = max(0, base_defense + random.randint(-1, 1))
        self.max_mana = 60 if not is_boss else 100
        self.mana = self.max_mana
        self.mana_regen = 15  # mana restored at the start of each enemy turn
        self.skill_cooldowns = {}
        burst = random.uniform(1.2, 2.8) if not is_boss else random.uniform(0.5, 1.0)
        self.target_x = float(map_x) + 0.5   # world-space destination (tile centre)
        self.target_y = float(map_y) + 0.5
        self.move_pause_timer = random.uniform(0.2, 1.5)  # stagger so they don't all lurch at once
        self.move_pause_duration = random.uniform(0.2, 0.8) if not is_boss else random.uniform(0.8, 1.6)
        # Enemies used to dash a tile at `burst` speed then stand still for the pause, every
        # tile. They now glide without stopping, so cruise at that old average pace instead —
        # same distance covered per second, just smooth, and no harder to outrun than before.
        self.speed = 1.0 / (1.0 / burst + self.move_pause_duration)
        # The overworld is walked tile by tile at WALK_SPEED; keep the old ratio of enemy
        # pace to player pace so chases feel the same as they did in first person.
        self.speed *= ENEMY_WORLD_PACE
        self.detection_range = random.uniform(4.0, 8.0) if not is_boss else random.uniform(8.0, 14.0)
        self.ai_state = "wander"   # "wander" | "chase"
        self.flee_cooldown = 0.0   # seconds before this enemy can trigger combat again
        self.cur_speed = 0.0       # eased speed, so starts and stops aren't instant
        self.heading = (0, 0)      # last tile step taken, so walks keep their direction
        self.pause_next = False    # brake to an idle pause at the tile it's heading for
enemies = []


# --- Treasure Chests ---
class Chest:
    """A strongbox sitting on a floor tile. Rarity is rolled at spawn time from the
    stage, so the lock gem can advertise how good the contents are before you cross
    the room. Walking onto the tile opens it."""
    def __init__(self, map_x, map_y, rarity):
        self.map_x, self.map_y = map_x, map_y
        self.x, self.y = map_x + 0.5, map_y + 0.5
        self.rarity = rarity
        self.opened = False
        self.loot = None
chests = []

# --- Game State Variables ---
game_state = STATE_EXPLORE; current_enemy_encounter = None; combat_turn = 'player'
combat_message = ""; player_combat_action = None; level_up_message = ""
combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION; player_selected_skill = None
current_stage = 1
menu_tab = "Stats"
info_page = 0   # index into INFO_PAGES
bindings_focus = None   # ("circle", name) or ("vow", index) the cursor is on, or None
bindings_open = set()   # circles whose dropdown is expanded (kept while the game runs)
bindings_scroll = 0     # px the vow list is scrolled
inventory_sub_state = INVENTORY_SUBSTATE_VIEWING
selected_item_row = -1
selected_item_col = -1
selected_equip_index = 0
stats_sub_state = STATS_SUBSTATE_VIEWING
selected_stat_index = -1
# --- Delay Timer Variables --- 
is_in_combat_delay = False
combat_delay_start_time = 0
next_combat_turn_after_delay = None
# --- End Delay Timer Variables ---

# --- Transient Notice Banner (chest loot, potions, …) ---
notice_title = ""
notice_message = ""
notice_sub = ""
notice_color = WHITE
notice_until = 0   # pygame ticks at which the banner expires

# --- Admin Console Variables ---
admin_input_text = ""
admin_feedback = "" # For on-screen feedback
previous_game_state = None
ADMIN_COMMANDS = ["level", "element", "item", "xp", "hp", "reroll", "stage", "give stone", "give item", "give xp", "give hp", "give spins", "give stones", "god", "killall", "heal", "speed", "teleport", "luck", "cooldowns", "help", "data", "debug", "tiers"]
admin_last_input_prefix = ""
admin_suggestion_index = 0
# --- End Admin Console Variables ---

# --- Pygame Setup ---
# The window is made by main_menu.open_window() everywhere (here, the menu, Video Settings
# and F11), as a pygame.SCALED window: the game draws at a fixed size and SDL stretches it
# to the window or the whole screen. It has to be SCALED from the very first window, since
# SDL can't add scaling to a window made without it.
import main_menu
import touch                          # on-screen controls for Android / touchscreens
touch_controls = touch.TouchControls()
main_menu.prepare_display()           # smooth scaling, real pixels on Windows; before init
pygame.init()
screen = main_menu.open_window((SCREEN_WIDTH, SCREEN_HEIGHT))
is_fullscreen = main_menu.settings["fullscreen"]
clock = pygame.time.Clock(); dt = 0
# pygame 2.1.3 renamed image.tostring/fromstring to tobytes/frombytes; Android's pygame
# is 2.1.0, so use whichever this pygame has.
_img_tobytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
_img_frombytes = getattr(pygame.image, "frombytes", None) or pygame.image.fromstring

# Every image the game loads goes through load_image(). The Android build also makes an
# .rgbz copy of each PNG: "RGBZ", width, height, then zlib-packed RGBA pixels - no image
# library needed (see .github/workflows/pack_images.py). On Android those copies are used
# first (on the phone, pygame's PNG support can be there in name but fail on every file,
# and the copies are smaller and quicker to load anyway); anywhere, a PNG that fails to
# load falls back to its copy. _image_errors keeps the first failures, for the timing line.
_PNG_OK = pygame.image.get_extended()
_image_errors = []


def _load_rgbz(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RGBZ":
        raise pygame.error(f"{path}: not an RGBZ file")
    w = int.from_bytes(data[4:8], "little")
    h = int.from_bytes(data[8:12], "little")
    return _img_frombytes(zlib.decompress(data[12:]), (w, h), "RGBA")


def load_image(path):
    alt = os.path.splitext(path)[0] + ".rgbz"
    has_alt = os.path.exists(alt)
    if has_alt and (touch.ON_ANDROID or not _PNG_OK):
        try:
            return _load_rgbz(alt)
        except Exception as e:
            _image_errors.append(f"{os.path.basename(alt)}: {e}")
    try:
        return pygame.image.load(path)
    except (pygame.error, FileNotFoundError, OSError) as e:
        if len(_image_errors) < 5:
            _image_errors.append(f"{os.path.basename(path)}: {e}")
        if has_alt:
            return _load_rgbz(alt)
        raise


def _load_serif(size, bold=False):
    """The Grimoire serif face: Georgia, or on systems without it (most Linux) the closest
    installed serif, sized to measure the same (see fonts.py)."""
    import fonts
    return fonts.serif(size, bold=bold)

font              = _load_serif(28)          # standard UI / dialogue
small_font        = _load_serif(19)          # labels, bar text
effectiveness_font = _load_serif(17)         # combat effectiveness line
xp_font           = _load_serif(15)          # tiny bar numerals
vow_font          = _load_serif(22)          # vow names on the Bindings cards
title_font        = _load_serif(34, bold=True)  # chapter / panel titles
big_font          = _load_serif(54, bold=True)  # ceremony display words

def _build_sky_backgrounds():
    """(Re)generate the night/day background art sized for the current SCREEN_WIDTH/HEIGHT.
    Re-run after resolution changes so the panorama and gradients match the new canvas."""
    global _sky_width, _bg_surface, _half_h, _day_bg_surface

    # --- Night background: full 360° panorama so stars scroll at the correct rate ---
    # Width = SCREEN_WIDTH * (2π / FOV) so one full player rotation scrolls exactly one surface width
    _sky_width = int(SCREEN_WIDTH * (2 * math.pi / FOV))
    _bg_surface = pygame.Surface((_sky_width, SCREEN_HEIGHT))
    _bg_surface.fill((0, 0, 0))
    _half_h = SCREEN_HEIGHT // 2
    for _y in range(_half_h, SCREEN_HEIGHT):
        _t = 1.0 - (_y - _half_h) / max(1, _half_h - 1)
        _c = (int(30 * _t), int(22 * _t), int(14 * _t))
        pygame.draw.line(_bg_surface, _c, (0, _y), (_sky_width - 1, _y))
    _rng = random.Random(42)
    _num_stars = int(1200 * (SCREEN_WIDTH / 800))  # keep star density consistent across resolutions
    for _ in range(_num_stars):
        _sx = _rng.randint(0, _sky_width - 1)
        _sy = _rng.randint(0, _half_h - 1)
        _brightness = _rng.randint(120, 255)
        _bg_surface.set_at((_sx, _sy), (_brightness, _brightness, int(_brightness * 0.9)))

    # --- Day background: blue sky gradient + warm lit floor ---
    _day_bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for _y in range(_half_h):                          # sky: deep blue at top → lighter at horizon
        _t = _y / max(1, _half_h - 1)
        _c = (int(30 + 90 * _t), int(80 + 100 * _t), int(160 + 70 * _t), 255)
        pygame.draw.line(_day_bg_surface, _c, (0, _y), (SCREEN_WIDTH - 1, _y))
    for _y in range(_half_h, SCREEN_HEIGHT):           # floor: warm stone, brighter at horizon
        _t = 1.0 - (_y - _half_h) / max(1, _half_h - 1)
        _c = (int(20 + 60 * _t), int(16 + 46 * _t), int(10 + 28 * _t), 255)
        pygame.draw.line(_day_bg_surface, _c, (0, _y), (SCREEN_WIDTH - 1, _y))

_build_sky_backgrounds()

DAY_CYCLE_START_MS = 4 * 60 * 1000   # 4 min into the 10 min cycle: bright morning
DAY_CYCLE_MS = 10 * 60 * 1000        # one full day and night


def get_day_factor():
    """0.0 = full night, 1.0 = full day. Cycle = 10 min, each transition = 5 min."""
    _cycle_ms = DAY_CYCLE_MS
    # Offset so a run opens in mid-morning rather than at midnight
    _t = ((pygame.time.get_ticks() + DAY_CYCLE_START_MS) % _cycle_ms) / _cycle_ms
    return (math.sin(_t * 2 * math.pi - math.pi / 2) + 1) / 2

# --- Load Assets ---
# The source icons are ~825px. Keep a mid-size master per element and derive every
# on-screen size from THAT, rather than from a 32px thumbnail: the reroll and victory
# screens draw runes at 64px, and upscaling a 32px thumbnail to 64 is what made them
# blurry (worst on the soft, bloom-heavy True form art).
ICON_MASTER_SIZE = 256          # well above any size we draw, so runes can go large and stay crisp
element_icon_masters = {}
element_icons = {}              # 32px convenience copies — membership tests use these
_icon_size_cache = {}           # (element, size) -> Surface

print("Loading element icons...")
for element, filename in ELEMENT_ICONS_MAP.items():
    try:
        img = load_image(filename).convert_alpha()
        master = pygame.transform.smoothscale(img, (ICON_MASTER_SIZE, ICON_MASTER_SIZE))
        element_icon_masters[element] = master
        element_icons[element] = pygame.transform.smoothscale(master, (32, 32))
        print(f" - Loaded icon: {filename}")
    except (FileNotFoundError, pygame.error) as e:
        print(f"Warning: Icon for {element} not found or failed to load ({filename}): {e}")


def get_element_icon(element, size):
    """An element icon at `size`, scaled from its high-res master and cached.

    Always downscales from the master rather than resampling a small copy, so a 64px
    rune keeps its detail instead of turning to mush."""
    key = (element, size)
    cached = _icon_size_cache.get(key)
    if cached is not None:
        return cached
    master = element_icon_masters.get(element)
    if master is None:
        return None
    icon = master if master.get_size() == (size, size) else pygame.transform.smoothscale(master, (size, size))
    _icon_size_cache[key] = icon
    return icon

# --- Load Enemy Images ---
enemy_images = {}; default_enemy_image = None
try:
    default_enemy_image = load_image(DEFAULT_ENEMY_IMAGE_PATH).convert_alpha()
    print(f"Loaded default enemy image: {DEFAULT_ENEMY_IMAGE_PATH}")
except (FileNotFoundError, pygame.error) as e: print(f"Warning: Default enemy image not found or failed to load ({DEFAULT_ENEMY_IMAGE_PATH}): {e}")

wall_texture = None
USE_WALL_TEXTURE = True          # Graphics Quality: Low disables texture mapping for speed
ENEMY_SPRITE_SCALE_FN = pygame.transform.scale  # nearest-neighbour: enemies are pixel art
try:
    wall_texture = load_image(WALL_TEXTURE_PATH).convert()
    print(f"Loaded wall texture: {WALL_TEXTURE_PATH}")
except (FileNotFoundError, pygame.error) as e: print(f"Warning: Wall texture not found or failed to load ({WALL_TEXTURE_PATH}): {e}")

print("Loading enemy images...")
for enemy_type in ENEMY_TYPES:
    path = enemy_type["image_path"]; name = enemy_type["name"]
    try: image = load_image(path).convert_alpha(); enemy_images[name] = image; print(f" - Loaded: {path} for {name}")
    except (FileNotFoundError, pygame.error) as e: print(f"Warning: Image for {name} not found or failed to load ({path}): {e}. Using default."); enemy_images[name] = default_enemy_image

# Empowered boss art: images/<name>_boss.png alongside each base sprite (see make_pixel_art.py)
boss_images = {}
for enemy_type in ENEMY_TYPES:
    name = enemy_type["name"]
    boss_path = enemy_type["image_path"].rsplit(".", 1)[0] + "_boss.png"
    try:
        boss_images[name] = load_image(boss_path).convert_alpha()
        print(f" - Loaded boss art: {boss_path} for {name}")
    except (FileNotFoundError, pygame.error):
        print(f"Note: No boss art for {name} ({boss_path}); falling back to its base sprite.")

# Chest art: one closed sprite per rarity (the lock gem carries the colour) + one opened
chest_images = {}
chest_open_image = None
for _rar in CHEST_RARITIES:
    _p = f"images/chest_{_rar.lower()}.png"
    try:
        chest_images[_rar] = load_image(_p).convert_alpha()
    except (FileNotFoundError, pygame.error) as e:
        print(f"Warning: Chest art missing for {_rar} ({_p}): {e}")
try:
    chest_open_image = load_image("images/chest_open.png").convert_alpha()
    print(f"Loaded chest art: {len(chest_images)} rarities + opened")
except (FileNotFoundError, pygame.error) as e:
    print(f"Warning: images/chest_open.png not found: {e}")


def get_chest_image(chest):
    if chest.opened:
        return chest_open_image or chest_images.get(chest.rarity)
    return chest_images.get(chest.rarity) or chest_open_image


# --- Enemy sprites (make_monsters.py): overworld walkers and battle sprites, tinted by
# the enemy's element and crowned for bosses. Built on first sight and cached.
import make_monsters
_monster_cache = {}
_HEADING_DIR = {(0, 1): "down", (0, -1): "up", (-1, 0): "left", (1, 0): "right"}


def _enemy_kind(enemy):
    kind = getattr(enemy, "base_name", enemy.name)
    return kind if kind in make_monsters.KINDS else None


def enemy_accent(enemy):
    return tuple((ELEMENT_COLORS.get(enemy.element) or GRIM_GOLD)[:3])


def enemy_overworld_frames(enemy):
    kind = _enemy_kind(enemy)
    if kind is None:
        return None
    key = ("ow", kind, enemy_accent(enemy), bool(enemy.is_boss))
    if key not in _monster_cache:
        _monster_cache[key] = {d: [f.convert_alpha() for f in fr]
                               for d, fr in make_monsters.overworld_frames(kind, enemy_accent(enemy), enemy.is_boss).items()}
    return _monster_cache[key]


def enemy_battle_sprite(enemy):
    kind = _enemy_kind(enemy)
    if kind is None:
        return None
    key = ("battle", kind, enemy_accent(enemy), bool(enemy.is_boss))
    if key not in _monster_cache:
        _monster_cache[key] = make_monsters.battle_sprite(kind, enemy_accent(enemy), enemy.is_boss).convert_alpha()
    return _monster_cache[key]


def get_enemy_image(enemy):
    """Art for an enemy. Bosses get their empowered variant; the lookup uses base_name
    because a boss's display name carries a '(BOSS)' suffix."""
    base = getattr(enemy, "base_name", enemy.name)
    if getattr(enemy, "is_boss", False):
        img = boss_images.get(base)
        if img:
            return img
    return enemy_images.get(base) or enemy_images.get(enemy.name) or default_enemy_image

# ==================== Spell VFX ====================
# The textures in vfx/ are greyscale (see make_vfx.py). At runtime each sprite is
# multiplied by the casting element's colour and blitted additively, so one asset set
# serves all 37 elements — a Hell Fire ember and an Abyssal Water droplet are the same
# file wearing different paint. Black pixels add nothing, which is why additive works.
VFX_NAMES = ("ember", "mote", "spark", "orb", "ring", "burst", "slash", "shard", "puff")
VFX_MAX_PARTICLES = 240        # hard cap so a long fight can never pile up
VFX_SHAKE_LIMIT = 7.0          # px

vfx_images = {}
_vfx_sprite_cache = {}
vfx_particles = []
vfx_timers = []                # [seconds_remaining, callable]
_vfx_flash = [(0, 0, 0), 0.0]  # colour, amount 0..1
_vfx_shake = [0.0]

print("Loading spell VFX...")
for _vn in VFX_NAMES:
    _vp = os.path.join("vfx", _vn + ".png")
    try:
        vfx_images[_vn] = load_image(_vp).convert_alpha()
    except (FileNotFoundError, pygame.error) as _ve:
        print(f"Warning: VFX texture missing ({_vp}): {_ve}")
print(f" - Loaded {len(vfx_images)}/{len(VFX_NAMES)} VFX textures")


# Per-element-family particle behaviour. Resolved through the matchup wheel's affinity, so
# every evolution automatically animates like its ancestor (Ice drips like Water, Lava
# rises like Fire) without a second table to keep in sync.
VFX_STYLES = {
    "Fire":      {"tex": "ember", "grav": -170.0, "drag": 1.5, "speed": (60, 150),
                  "life": (0.45, 0.85), "size": (16, 30), "spin": 0.0, "additive": True},
    "Water":     {"tex": "ember", "grav": 230.0,  "drag": 0.9, "speed": (50, 130),
                  "life": (0.45, 0.80), "size": (12, 24), "spin": 0.0, "additive": True},
    "Lightning": {"tex": "spark", "grav": 0.0,    "drag": 3.2, "speed": (150, 330),
                  "life": (0.18, 0.38), "size": (14, 26), "spin": 7.0, "additive": True},
    "Earth":     {"tex": "shard", "grav": 430.0,  "drag": 0.3, "speed": (70, 180),
                  "life": (0.50, 0.90), "size": (10, 20), "spin": 6.0, "additive": False},
    "Wind":      {"tex": "mote",  "grav": -45.0,  "drag": 0.7, "speed": (90, 210),
                  "life": (0.50, 0.90), "size": (8, 17),  "spin": 0.0, "additive": True},
}
# Universal (Tier 5+) elements sit outside the wheel, so they get their own arcane drift.
VFX_STYLE_UNIVERSAL = {"tex": "mote", "grav": -70.0, "drag": 1.1, "speed": (60, 150),
                       "life": (0.55, 1.00), "size": (10, 20), "spin": 0.0, "additive": True}


def vfx_style(element):
    return VFX_STYLES.get(matchup_key(element), VFX_STYLE_UNIVERSAL)


def vfx_color(element):
    """The element's colour, lifted if it's near-black — additive blending would make a
    Dark or Shadow effect literally invisible otherwise."""
    c = ELEMENT_COLORS.get(element) or GRIM_GOLD
    if sum(c[:3]) <= 140:
        c = lighten(c, 0.65)
    return (c[0], c[1], c[2])


class VfxParticle:
    __slots__ = ("tex", "x", "y", "vx", "vy", "ax", "ay", "drag", "life", "max_life",
                 "size", "end_size", "color", "rot", "spin", "additive", "trail", "_tt")

    def __init__(self, tex, x, y, vx=0.0, vy=0.0, ax=0.0, ay=0.0, drag=0.0, life=0.6,
                 size=24, end_size=None, color=(255, 255, 255), rot=0.0, spin=0.0,
                 additive=True, trail=False):
        self.tex = tex; self.x = x; self.y = y
        self.vx = vx; self.vy = vy; self.ax = ax; self.ay = ay; self.drag = drag
        self.life = life; self.max_life = max(0.001, life)
        self.size = size; self.end_size = size if end_size is None else end_size
        self.color = color; self.rot = rot; self.spin = spin
        self.additive = additive; self.trail = trail; self._tt = 0.0


def _vfx_add(p):
    if len(vfx_particles) < VFX_MAX_PARTICLES:
        vfx_particles.append(p)


def vfx_after(delay, fn):
    """Run fn() after `delay` seconds of combat time — lets a cast be choreographed."""
    vfx_timers.append([delay, fn])


def vfx_clear():
    vfx_particles.clear()
    _vfx_shapes.clear()
    vfx_timers.clear()
    _vfx_flash[1] = 0.0
    _vfx_shake[0] = 0.0


def vfx_flash(color, amount=0.5):
    _vfx_flash[0] = color
    _vfx_flash[1] = min(1.0, max(_vfx_flash[1], amount))


def vfx_shake(amount):
    _vfx_shake[0] = min(VFX_SHAKE_LIMIT, max(_vfx_shake[0], amount))


def _vfx_sprite(tex, size, color, fade):
    """Tinted + faded sprite, cached. Fade is quantised to 16 steps so the cache stays
    small while still reading as a smooth fade."""
    size = max(2, int(size))
    q = max(0, min(15, int(fade * 15.0)))
    key = (tex, size, color, q)
    hit = _vfx_sprite_cache.get(key)
    if hit is not None:
        return hit
    base = vfx_images.get(tex)
    if base is None:
        return None
    bw, bh = base.get_size()
    scaled = pygame.transform.smoothscale(base, (size, max(2, int(size * bh / bw))))
    f = (q + 1) / 16.0
    scaled.fill((int(color[0] * f), int(color[1] * f), int(color[2] * f), 255),
                special_flags=pygame.BLEND_RGBA_MULT)
    if len(_vfx_sprite_cache) > 1400:
        _vfx_sprite_cache.clear()
    _vfx_sprite_cache[key] = scaled
    return scaled


def update_vfx(dt):
    dt = min(dt, 0.05)          # a frame hitch shouldn't teleport particles
    if dt <= 0:
        return

    for t in vfx_timers[:]:
        t[0] -= dt
        if t[0] <= 0:
            vfx_timers.remove(t)
            try:
                t[1]()
            except Exception as e:      # a broken effect must never kill the fight
                print(f"VFX timer error: {e}")

    for p in vfx_particles[:]:
        p.life -= dt
        if p.life <= 0:
            vfx_particles.remove(p)
            continue
        p.vx += p.ax * dt
        p.vy += p.ay * dt
        if p.drag:
            damp = max(0.0, 1.0 - p.drag * dt)
            p.vx *= damp; p.vy *= damp
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.rot += p.spin * dt
        if p.trail:
            p._tt -= dt
            if p._tt <= 0:
                p._tt = 0.02
                _vfx_add(VfxParticle("mote", p.x, p.y,
                                     vx=random.uniform(-18, 18), vy=random.uniform(-18, 18),
                                     drag=2.0, life=0.28, size=max(5, p.size // 3),
                                     end_size=2, color=p.color))

    update_vfx_shapes(dt)

    if _vfx_flash[1] > 0:
        _vfx_flash[1] = max(0.0, _vfx_flash[1] - dt * 3.2)
    if _vfx_shake[0] > 0:
        _vfx_shake[0] = max(0.0, _vfx_shake[0] - dt * 26.0)


def draw_vfx(surface):
    draw_vfx_shapes(surface)
    for p in vfx_particles:
        t = max(0.0, min(1.0, p.life / p.max_life))
        size = p.end_size + (p.size - p.end_size) * t
        spr = _vfx_sprite(p.tex, size, p.color, t)
        if spr is None:
            continue
        if p.rot:
            spr = pygame.transform.rotate(spr, math.degrees(p.rot))
        rect = spr.get_rect(center=(int(p.x), int(p.y)))
        surface.blit(spr, rect, special_flags=pygame.BLEND_RGB_ADD if p.additive else 0)


def draw_vfx_overlay(surface):
    """Screen flash + shake. Called last so it sits over the whole combat frame."""
    amt = _vfx_flash[1]
    if amt > 0.01:
        col = _vfx_flash[0]
        wash = pygame.Surface(surface.get_size())
        wash.fill((int(col[0] * amt * 0.28), int(col[1] * amt * 0.28), int(col[2] * amt * 0.28)))
        surface.blit(wash, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    if _vfx_shake[0] > 0.3:
        a = _vfx_shake[0]
        snap = surface.copy()
        surface.fill((0, 0, 0))
        surface.blit(snap, (int(random.uniform(-a, a)), int(random.uniform(-a, a))))


# ---------------------------------------------------------------- emitters
def combat_anchor_player():
    L = battle_layout()
    return (int(L["px"]), int(L["py"] - 80))


def combat_anchor_enemy():
    L = battle_layout()
    return (int(L["ex"]), int(L["ey"] - 70))


def vfx_burst(element, pos, power=1.0, rings=1):
    """A flare, a shockwave ring and a shower of element-flavoured debris."""
    col = vfx_color(element)
    st = vfx_style(element)
    x, y = pos
    # White-hot core collapsing inward gives the hit its punch locally, which reads far
    # better than brightening the entire screen.
    _vfx_add(VfxParticle("burst", x, y, life=0.16 * power, size=int(170 * power),
                         end_size=int(50 * power), color=lighten(col, 0.65)))
    _vfx_add(VfxParticle("burst", x, y, life=0.34 * power, size=int(104 * power),
                         end_size=int(40 * power), color=col))
    for i in range(rings):
        vfx_after(i * 0.09, lambda x=x, y=y, c=col, p=power: _vfx_add(
            VfxParticle("ring", x, y, life=0.42, size=int(28 * p), end_size=int(150 * p),
                        color=c)))
    lo, hi = st["speed"]
    smin, smax = st["size"]
    lmin, lmax = st["life"]
    for _ in range(int(14 * power)):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(lo, hi) * power
        _vfx_add(VfxParticle(st["tex"], x, y,
                             vx=math.cos(ang) * spd, vy=math.sin(ang) * spd,
                             ay=st["grav"], drag=st["drag"],
                             life=random.uniform(lmin, lmax),
                             size=random.randint(smin, smax), end_size=2,
                             color=col, spin=random.uniform(-st["spin"], st["spin"]),
                             additive=st["additive"]))


def vfx_charge(element, pos, count=16):
    """Motes rushing inward — the wind-up before a spell lands."""
    col = vfx_color(element)
    st = vfx_style(element)
    x, y = pos
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        dist = random.uniform(55, 120)
        life = random.uniform(0.25, 0.45)
        sx, sy = x + math.cos(ang) * dist, y + math.sin(ang) * dist
        _vfx_add(VfxParticle(st["tex"], sx, sy,
                             vx=(x - sx) / life, vy=(y - sy) / life,
                             life=life, size=random.randint(8, 16), end_size=14,
                             color=col, additive=True))


# --- Branch hints ---
# An evolved element's cast carries traces of the Tier 1 element its line began with:
# Fire-line casts shed rising orange embers, Water-line casts drip, Earth-line casts throw
# grit, Wind-line casts leave drifting motes, Lightning-line casts crackle. The hints use
# the ROOT's own style and colour, so they read as "this came from Fire" even when the
# evolved element's colour (Inferno red, Plasma violet) is nothing like it.
def hint_color(root):
    """The root's colour, lifted a little: hints are small and additive, and a pure
    primary (Water's blue especially) all but vanishes against a dark screen."""
    return lighten(vfx_color(root), 0.3)


def player_branch_root():
    return branch_root(player_stats["element"], player_stats.get("lineage"))


def _hint_particle(root, x, y, vx, vy, size_scale=1.0, life_scale=1.0):
    st = VFX_STYLES.get(root)
    if not st:
        return
    smin, smax = st["size"]
    lmin, lmax = st["life"]
    _vfx_add(VfxParticle(st["tex"], x, y, vx=vx, vy=vy, ay=st["grav"], drag=st["drag"],
                         life=random.uniform(lmin, lmax) * life_scale,
                         size=int(random.randint(smin, smax) * size_scale), end_size=2,
                         color=hint_color(root), spin=random.uniform(-st["spin"], st["spin"]),
                         additive=st["additive"]))


def vfx_hint_charge(root, pos, count=7):
    """A few of the root's particles joining the wind-up."""
    if not root:
        return
    x, y = pos
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        dist = random.uniform(40, 95)
        _hint_particle(root, x + math.cos(ang) * dist, y + math.sin(ang) * dist,
                       -math.cos(ang) * 60, -math.sin(ang) * 60, size_scale=0.8, life_scale=0.7)


def vfx_hint_trail(root, origin, end, travel, drops=5):
    """The bolt sheds the root's particles along its flight path."""
    if not root:
        return
    ox, oy = origin
    ex, ey = end
    for i in range(1, drops + 1):
        f = i / (drops + 1)
        def _shed(f=f):
            px, py = ox + (ex - ox) * f, oy + (ey - oy) * f
            for _ in range(2):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(20, 70)
                _hint_particle(root, px, py, math.cos(ang) * spd, math.sin(ang) * spd,
                               size_scale=0.75, life_scale=0.8)
        vfx_after(travel * f, _shed)


def vfx_hint_burst(root, pos, power=1.0, count=9):
    """A thin ring and a spray of debris in the root's style at the point of impact."""
    if not root:
        return
    x, y = pos
    col = hint_color(root)
    vfx_after(0.05, lambda: _vfx_add(VfxParticle("ring", x, y, life=0.36, size=int(20 * power),
                                                 end_size=int(115 * power), color=col)))
    lo, hi = VFX_STYLES[root]["speed"]
    for _ in range(int(count * power)):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(lo, hi) * power
        _hint_particle(root, x, y, math.cos(ang) * spd, math.sin(ang) * spd)


def vfx_projectile(element, origin, target, on_arrive=None, speed=900.0):
    """A cored orb that streaks from caster to target, trailing motes."""
    col = vfx_color(element)
    ox, oy = origin
    tx, ty = target
    dist = max(1.0, math.hypot(tx - ox, ty - oy))
    travel = dist / speed
    _vfx_add(VfxParticle("orb", ox, oy, vx=(tx - ox) / travel, vy=(ty - oy) / travel,
                         life=travel, size=34, end_size=26, color=col, trail=True))
    if on_arrive:
        vfx_after(travel, on_arrive)
    return travel


def vfx_slash(pos, color=(255, 240, 220), flip=False):
    """Melee arc."""
    x, y = pos
    _vfx_add(VfxParticle("slash", x, y, life=0.26, size=110, end_size=130, color=color,
                         rot=math.radians(200 if flip else 20), spin=6.0))
    for _ in range(8):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(90, 230)
        _vfx_add(VfxParticle("spark", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd,
                             drag=3.0, life=random.uniform(0.18, 0.32),
                             size=random.randint(10, 20), end_size=2, color=color))


def vfx_aura(element, pos, root=None):
    """Awakening — a column of the element's own light, threaded with its root's."""
    col = vfx_color(element)
    x, y = pos
    for i in range(3):
        vfx_after(i * 0.12, lambda x=x, y=y, c=col: _vfx_add(
            VfxParticle("ring", x, y, life=0.55, size=20, end_size=190, color=c)))
    for _ in range(26):
        _vfx_add(VfxParticle("ember", x + random.uniform(-70, 70), y + random.uniform(-20, 90),
                             vy=random.uniform(-260, -110), drag=0.8,
                             life=random.uniform(0.6, 1.1),
                             size=random.randint(12, 26), end_size=2, color=col))
    if root:
        # A ring of the root's colour between the element's own, and the root's particles
        # thrown up the column — its own gravity then shapes them: Fire embers keep
        # climbing, Water drips fall back, Earth grit tumbles, Wind motes drift.
        rc = hint_color(root)
        vfx_after(0.06, lambda: _vfx_add(VfxParticle("ring", x, y, life=0.5, size=16,
                                                     end_size=150, color=rc)))
        for _ in range(12):
            _hint_particle(root, x + random.uniform(-60, 60), y + random.uniform(-10, 80),
                           random.uniform(-40, 40), random.uniform(-170, -70))
    vfx_flash(col, 0.32)


def vfx_gather(element, pos, root=None):
    """Charging mana — motes rush in, with a few of the root's among them."""
    vfx_charge(element, pos, count=22)
    col = vfx_color(element)
    _vfx_add(VfxParticle("ring", pos[0], pos[1], life=0.5, size=140, end_size=18, color=col))
    if root:
        vfx_hint_charge(root, pos, count=9)
        rc = hint_color(root)
        vfx_after(0.08, lambda: _vfx_add(VfxParticle("ring", pos[0], pos[1], life=0.42,
                                                     size=110, end_size=16, color=rc)))


def vfx_death(element, pos):
    """An enemy coming apart."""
    vfx_burst(element, pos, power=1.35, rings=2)
    vfx_hint_burst(branch_root(element), pos, power=1.1)
    col = vfx_color(element)
    for _ in range(10):
        _vfx_add(VfxParticle("puff", pos[0] + random.uniform(-26, 26),
                             pos[1] + random.uniform(-26, 26),
                             vy=random.uniform(-70, -20), drag=1.2,
                             life=random.uniform(0.5, 0.9),
                             size=random.randint(26, 52), end_size=70,
                             color=tuple(int(c * 0.45) for c in col), additive=True))
    vfx_shake(5.0)


def vfx_fizzle(element, pos):
    """A spent bolt dissipating in the air — no burst, no shake."""
    col = vfx_color(element)
    x, y = pos
    _vfx_add(VfxParticle("ring", x, y, life=0.3, size=16, end_size=60,
                         color=tuple(int(c * 0.6) for c in col)))
    for _ in range(9):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(40, 120)
        _vfx_add(VfxParticle("ember", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd - 30,
                             drag=2.0, life=random.uniform(0.3, 0.55),
                             size=random.randint(8, 16), end_size=1, color=col))


def miss_point(origin, target):
    """Where a missed shot ends up: sailing on past the target and off to one side."""
    ox, oy = origin
    tx, ty = target
    dx, dy = tx - ox, ty - oy
    dist = math.hypot(dx, dy) or 1.0
    nx, ny = dx / dist, dy / dist
    side = random.choice((-1, 1))
    return (tx + nx * 90 - ny * 85 * side, ty + ny * 90 + nx * 85 * side)


CAST_WINDUP = 0.32          # seconds of wind-up before the bolt leaves the caster
PROJECTILE_SPEED = 900.0


def vfx_skill_cast(element, origin, target, power=1.0, on_impact=None, miss=False, root=None, skill=None):
    """Full choreography for a cast: wind-up at the caster, the element's own attack form
    (comet, jet, spears, spikes, blades, bolt, beam, void orb...) crossing to the target, then
    the impact. A miss sends it wide, where it fizzles instead of bursting.

    Returns the seconds until it lands, so callers can time follow-ups to it.
    `root` is the Tier 1 element the caster's line began with; its hints ride along.
    `skill` is the move's name, which can pick a form (Earthquake, Blizzard, Hydro Pump)."""
    col = vfx_color(element)
    form = attack_form(element, skill)
    vfx_charge(element, origin)
    vfx_hint_charge(root, origin)
    vfx_flash(col, 0.14)
    end = miss_point(origin, target) if miss else target
    travel = _travel_for(form, origin, end)

    def _launch():
        if form not in ("spikes", "vortex", "bolt", "beam"):
            vfx_hint_trail(root, origin, end, travel)
        _launch_form(form, element, col, origin, end, travel, power, skill)

        def _impact():
            if miss:
                vfx_fizzle(element, end)
                vfx_hint_burst(root, end, power=0.45, count=6)
            else:
                vfx_burst(element, target, power=power * 0.8, rings=1)
                _impact_form(form, element, col, target, power, skill)
                vfx_hint_burst(root, target, power=power)
                vfx_flash(col, 0.30)
                vfx_shake(4.0 + 2.0 * power)
            if on_impact:
                on_impact()
        vfx_after(travel, _impact)

    vfx_after(CAST_WINDUP, _launch)
    return CAST_WINDUP + travel


MELEE_IMPACT = 0.12         # a swing lands almost at once


def vfx_melee(target, color, flip=False, miss=False, root=None, element=None):
    """A swing: lands on the target with a shake, or whiffs through the air beside it.
    With an element, the blow is wrapped in it — a flaming slash, a splash of water, a
    crack of rock, a gust, a spark — matching that element's attack form."""
    if miss:
        x, y = target
        wx, wy = x + (-70 if flip else 70), y - 40
        vfx_slash((wx, wy), tuple(int(c * 0.55) for c in color), flip=flip)
        if element:
            _melee_trace(element, vfx_color(element), (wx, wy))
    else:
        vfx_slash(target, color, flip=flip)
        if element:
            _melee_form(attack_form(element), element, vfx_color(element), target, flip)
        vfx_shake(2.5)
        vfx_hint_burst(root, target, power=0.6, count=8)


def _melee_trace(element, col, pos):
    """A whiffed swing still leaves a wisp of its element in the air."""
    st = vfx_style(element)
    x, y = pos
    for _ in range(7):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(40, 110)
        _vfx_add(VfxParticle(st["tex"], x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd,
                             ay=st["grav"] * 0.5, drag=st["drag"], life=random.uniform(0.25, 0.45),
                             size=random.randint(8, 14), end_size=2, color=col, additive=st["additive"]))


def _melee_form(form, element, col, pos, flip):
    """The element riding on a landed melee blow — a smaller cousin of its spell form."""
    x, y = pos
    side = -1 if flip else 1
    gy, gscale = _ground_under(pos)
    if form == "fireball":                                     # the blade bursts into flame
        tongues = [(i * math.tau / 7 + random.uniform(-0.2, 0.2), random.uniform(36, 58), random.uniform(7, 11))
                   for i in range(7)]
        _shape("flames", 0.4, False, col=col, x=x, y=y, tongues=tongues)
        for _ in range(10):
            _vfx_add(VfxParticle("ember", x + random.uniform(-30, 30), y + random.uniform(-20, 20),
                                 vx=random.uniform(-60, 60), vy=random.uniform(-200, -80), drag=1.4,
                                 life=random.uniform(0.35, 0.6), size=random.randint(10, 18), end_size=2, color=col))
    elif form == "jet" or (form == "vortex" and matchup_key(element) == "Water"):   # a slap of water
        for _ in range(12):
            ang = -math.pi / 2 + random.uniform(-1.2, 1.2)
            spd = random.uniform(120, 240)
            _vfx_add(VfxParticle("ember", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd, ay=620,
                                 drag=0.4, life=random.uniform(0.4, 0.6), size=random.randint(9, 15),
                                 end_size=3, color=lighten(col, 0.3)))
        _shape("ripple", 0.4, False, col=(235, 248, 255), x=x, y=y + 26, w=50)
        ox_, oy_, ex_, ey_ = x - side * 75, y - 45, x + side * 55, y + 25        # the swing trails a wave
        ln = math.hypot(ex_ - ox_, ey_ - oy_)
        _shape("jet", 0.32, False, col=col, ox=ox_, oy=oy_, ex=ex_, ey=ey_, travel=0.1,
               nx=-(ey_ - oy_) / ln, ny=(ex_ - ox_) / ln, w=11)
    elif form == "spear":                                      # ice / blood / metal splinters off
        for _ in range(11):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80, 200)
            _vfx_add(VfxParticle("shard", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd - 50, ay=520,
                                 drag=0.3, life=random.uniform(0.35, 0.6), size=random.randint(8, 14), end_size=3,
                                 color=lighten(col, 0.25), spin=random.uniform(-8, 8), additive=False))
        # a pair of short spikes of the element jab through the cut
        dx, dy = side * 0.8, -0.6
        for k, off in enumerate((-14, 14)):
            sx, sy = x - dx * 30 + off * 0.6, y - dy * 30 + off
            _shape("spears", 0.22, False, col=col, spears=[(k * 0.03, sx - dx * 40, sy - dy * 40, sx + dx * 40, sy + dy * 40)],
                   travel=0.12, len=42, w=7)
    elif form in ("spikes", "boulder") or (form == "vortex" and matchup_key(element) == "Earth"):
        spikes = [((i - 1) * 26 * gscale + random.uniform(-6, 6), random.uniform(38, 56) * gscale * (1.1 - 0.25 * abs(i - 1)),
                   random.uniform(10, 15) * gscale, abs(i - 1) * 0.05) for i in range(3)]
        _shape("spikes", 0.5, False, col=_rock_col(col), gx=x, gy=gy, spikes=spikes, span=34 * gscale)
        _shape("dust", 0.5, False, col=lerp_color(_rock_col(col), (200, 190, 170), 0.4), x=x, y=gy - 10,
               puffs=[(random.uniform(-36, 36) * gscale, random.uniform(-12, 12), random.uniform(10, 18) * gscale) for _ in range(6)])
    elif form in ("blade", "vortex"):                          # a gust shears past with the blow
        blades = [(i * 0.05, x - side * 90, y - 30 + i * 30, x + side * 60, y + 10 + i * 10, 0.22 * (1 if i else -1))
                  for i in range(2)]
        _shape("blades", 0.32, False, col=col, blades=blades, travel=0.16, r=34)
        for _ in range(8):
            ang = random.uniform(0, math.tau)
            _vfx_add(VfxParticle("mote", x, y, vx=math.cos(ang) * 200, vy=math.sin(ang) * 200, drag=3.0,
                                 life=0.35, size=10, end_size=2, color=lighten(col, 0.4)))
    elif form == "bolt":                                       # sparks crackle off the hit
        for k in range(3):
            ang = random.uniform(0, math.tau)
            ln = random.uniform(50, 80)
            _shape("bolt", 0.2, True, col=col, sx=x, sy=y, ex=x + math.cos(ang) * ln, ey=y + math.sin(ang) * ln,
                   rough=26, branches=1, scale=0.6, regen=-1, paths=[])
        for _ in range(12):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(180, 360)
            _vfx_add(VfxParticle("spark", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd, drag=4.0,
                                 life=random.uniform(0.12, 0.26), size=random.randint(10, 18), end_size=2,
                                 color=lighten(col, 0.3), spin=8.0))
    elif form == "beam":                                       # a flare of light bursts from the cut
        _shape("beam", 0.25, True, col=col, ox=x - 55, oy=y, ex=x + 55, ey=y, w=10)
        _shape("beam", 0.25, True, col=col, ox=x, oy=y - 55, ex=x, ey=y + 55, w=10)
        _vfx_add(VfxParticle("ring", x, y, life=0.35, size=24, end_size=140, color=lighten(col, 0.4)))
    elif form == "void":                                       # the wound drinks the light in
        _shape("implode", 0.45, False, col=col, x=x, y=y, r=30)
        _vfx_add(VfxParticle("ring", x, y, life=0.35, size=130, end_size=10, color=col))
    else:
        _melee_trace(element, col, pos)
# ---------------------------------------------------------------- attack forms
# Every elemental attack has a shape of its own instead of a tinted orb: Fire throws a
# comet, Water a jet, Ice and Blood fly as spears, Earth erupts in spikes or hurls a rock,
# Wind cuts with crescent blades, Lightning strikes as a bolt, Light burns a beam, the
# void elements send a dark orb that implodes. The skill's name can steer it (Earthquake
# splits the ground, Blizzard is a vortex, Hydro Pump a jet), and the element's own colour
# paints it — so Abyssal Water's jet is indigo and Mud's is brown, but both are jets.
# Shapes are drawn procedurally on two layers: "glow" blitted additively (fire, light,
# lightning) and "solid" alpha-blended (water, rock, ice, the void).

_vfx_shapes = []
_vfx_layers = {}

ELEMENT_FORM = {
    "Fire": "fireball", "Combustion": "fireball", "Inferno": "fireball", "Hell Fire": "fireball",
    "Frost Fire": "fireball", "Nuclear": "fireball",
    "Water": "jet", "Abyssal Water": "jet", "Mud": "jet", "Mist": "vortex",
    "Ice": "spear", "Blood": "spear", "Metal": "spear",
    "Earth": "spikes", "Tectonic Earth": "spikes", "Wood": "spikes",
    "Lava": "boulder", "Matter": "boulder", "Sand": "vortex", "Dust": "vortex",
    "Wind": "blade", "Gale": "blade", "Tempest Wind": "blade", "Kinetic": "blade",
    "Lightning": "bolt", "Plasma": "bolt", "Storm": "bolt", "Energy": "bolt", "Celestial Lightning": "bolt",
    "Light": "beam", "Solar": "beam", "Star Force": "beam", "Lunar": "beam", "OFA": "beam",
    "Dark": "void", "Shadow": "void", "Dark Matter": "void", "Gravity": "void", "Eclipse": "void",
    "Space": "void", "Time": "void", "Reality": "void", "Potential": "void",
}
# skill-name keywords, checked in order (only for elements on the Tier 1 wheel)
SKILL_FORM_KEYWORDS = (
    ("bolt", ("thunder", "bolt", "spark", "arc flash")),
    ("beam", ("beam", "lance", " ray", "flare")),
    ("vortex", ("storm", "blizzard", "tornado", "cyclone", "devil", "tomb", "typhoon", "maelstrom", "eye of")),
    ("spikes", ("quake", "edge", "fault", "pangaea")),
    ("boulder", ("fall", "slam", "hammer", "bomb", "rock")),
    ("spear", ("shard", "icicle", "spear", "piercing", "needle")),
    ("blade", ("cutter", "gust", "blade", "lash", "shear", "claw", "whip")),
    ("jet", ("gun", "pump", "jet", "tide", "shot", "depths", "plume")),
    ("fireball", ("ball", "ember", "burst", "ignite", "explosion")),
)
QUAKE_WORDS = ("quake", "fault", "pangaea")


def attack_form(element, skill=None):
    form = ELEMENT_FORM.get(element) or ELEMENT_FORM.get(matchup_key(element), "orb")
    if skill and matchup_key(element) in tier1_elements:
        name = " " + skill.lower()
        for f, words in SKILL_FORM_KEYWORDS:
            if any(w in name for w in words):
                return f
    return form


class VfxShape:
    def __init__(self, kind, life, additive=True, **kw):
        self.kind = kind; self.life = life; self.max_life = max(0.001, life)
        self.additive = additive; self.age = 0.0
        self.__dict__.update(kw)


def _shape(kind, life, additive=True, **kw):
    s = VfxShape(kind, life, additive, **kw)
    if len(_vfx_shapes) < 80:
        _vfx_shapes.append(s)
    return s


def _lerp(a, b, t):
    return a + (b - a) * t


def _scale_col(c, f):
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))), max(0, min(255, int(c[2] * f))))


def _fade(s, fade_in=0.0, fade_out=0.25):
    """0..1 visibility from the shape's age: eases in, holds, eases out."""
    a = 1.0
    if fade_in > 0:
        a = min(a, s.age / fade_in)
    if fade_out > 0:
        a = min(a, s.life / (s.max_life * fade_out) if s.max_life * fade_out > 0 else 1.0)
    return max(0.0, min(1.0, a))


def _ground_under(target):
    """The floor line beneath a battler (and how big things look there)."""
    L = battle_layout()
    pa = combat_anchor_player()
    if abs(target[0] - pa[0]) + abs(target[1] - pa[1]) < 160:
        return L["py"] - 4, 1.35
    return L["ey"] + 2, 1.0


def _jag(x0, y0, x1, y1, rough, depth=5):
    """A jagged lightning path between two points (midpoint displacement)."""
    pts = [(x0, y0), (x1, y1)]
    for _ in range(depth):
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            mx, my = (ax + bx) / 2, (ay + by) / 2
            dx, dy = bx - ax, by - ay
            ln = math.hypot(dx, dy) or 1
            off = random.uniform(-rough, rough) * ln / 140
            out += [(mx - dy / ln * off, my + dx / ln * off), (bx, by)]
        pts = out
        rough *= 0.55
    return pts


# --- per-kind drawing (surface is the glow or solid layer) ---
def _draw_comet(surf, s):
    col = s.col
    dark = _scale_col(col, 0.6)
    n = len(s.hist)
    for i, (hx, hy) in enumerate(s.hist):                      # a tapering tail of flame
        f = (i + 1) / max(1, n)
        r = max(1, int(s.r * (0.3 + 0.8 * f)))
        pygame.draw.circle(surf, dark + (int(150 * f),), (int(hx), int(hy) - int((1 - f) * 10)), r)
    for i, (hx, hy) in enumerate(s.hist):
        f = (i + 1) / max(1, n)
        r = max(1, int(s.r * 0.6 * f))
        pygame.draw.circle(surf, lighten(col, 0.35) + (int(200 * f),), (int(hx), int(hy) - int((1 - f) * 10)), r)
    if s.age < s.travel:
        fl = random.uniform(-2, 2)
        pygame.draw.circle(surf, col + (235,), (int(s.x), int(s.y)), int(s.r + 5 + fl))
        pygame.draw.circle(surf, lighten(col, 0.45) + (250,), (int(s.x), int(s.y)), int(s.r * 0.78 + fl))
        pygame.draw.circle(surf, (255, 248, 210, 255), (int(s.x), int(s.y)), int(s.r * 0.45))


def _tick_comet(s, dt):
    p = min(1.0, s.age / s.travel)
    s.x, s.y = _lerp(s.ox, s.ex, p), _lerp(s.oy, s.ey, p)
    if s.age < s.travel:
        s.hist.append((s.x + random.uniform(-2, 2), s.y + random.uniform(-2, 2)))
        s.hist = s.hist[-18:]
        if random.random() < 0.8:
            st = vfx_style(s.element)
            _vfx_add(VfxParticle(st["tex"] if st["additive"] else "ember", s.x, s.y,
                                 vx=random.uniform(-40, 40), vy=random.uniform(-90, -20),
                                 drag=1.5, life=random.uniform(0.25, 0.45), size=random.randint(10, 18),
                                 end_size=2, color=s.col))
    elif s.hist:
        s.hist = s.hist[2:]


def _draw_flames(surf, s):
    k = s.age / s.max_life
    a = _fade(s, 0.0, 0.5)
    for (ang, ln, w) in s.tongues:
        L = ln * (0.35 + 0.65 * min(1.0, k * 2.4))
        c, sn = math.cos(ang), math.sin(ang)
        bx, by = s.x + c * 10, s.y + sn * 10
        tip = (s.x + c * L, s.y + sn * L - 22 * k)              # flames lick upward as they go
        l = (bx - sn * w, by + c * w)
        r = (bx + sn * w, by - c * w)
        pygame.draw.polygon(surf, s.col + (int(235 * a),), [l, tip, r])
        mid = (s.x + c * L * 0.6, s.y + sn * L * 0.6 - 14 * k)
        pygame.draw.polygon(surf, (255, 214, 110, int(245 * a)), [(bx - sn * w * 0.5, by + c * w * 0.5), mid,
                                                                  (bx + sn * w * 0.5, by - c * w * 0.5)])
    pygame.draw.circle(surf, (255, 244, 210, int(255 * a)), (int(s.x), int(s.y)), int(30 * (1 - k) + 6))


def _draw_jet(surf, s):
    ph = min(1.0, s.age / s.travel)
    pt = max(0.0, (s.age - s.travel - 0.14) / (s.travel * 0.8))
    if pt >= 1.0:
        return
    span = math.hypot(s.ex - s.ox, s.ey - s.oy) * (ph - pt)
    steps = max(12, int(span / 4))
    for i in range(steps + 1):
        f = _lerp(pt, ph, i / steps)
        x, y = _lerp(s.ox, s.ex, f), _lerp(s.oy, s.ey, f)
        wob = math.sin(s.age * 26 + f * 14) * 5
        x += s.nx * wob; y += s.ny * wob
        head = 1.0 - abs(f - ph) * 2.2
        w = s.w * (0.55 + 0.45 * f) + max(0.0, head) * 5
        pygame.draw.circle(surf, lighten(s.col, 0.15) + (230,), (int(x), int(y)), int(w))
    for i in range(steps + 1):                                        # glassy highlight down the middle
        f = _lerp(pt, ph, i / steps)
        x, y = _lerp(s.ox, s.ex, f), _lerp(s.oy, s.ey, f)
        wob = math.sin(s.age * 26 + f * 14) * 5 - 3
        x += s.nx * wob; y += s.ny * wob
        pygame.draw.circle(surf, lighten(s.col, 0.55) + (235,), (int(x), int(y)), max(1, int(s.w * 0.32 * (0.5 + 0.5 * f))))
    for _ in range(3):                                                # spray flecks
        f = random.uniform(pt, ph)
        x, y = _lerp(s.ox, s.ex, f), _lerp(s.oy, s.ey, f)
        pygame.draw.circle(surf, (245, 252, 255, 230), (int(x + random.uniform(-s.w, s.w)), int(y + random.uniform(-s.w, s.w))), 2)


def _spear_poly(x, y, dx, dy, ln, w):
    tip = (x + dx * ln * 0.55, y + dy * ln * 0.55)
    tail = (x - dx * ln * 0.45, y - dy * ln * 0.45)
    mx, my = x + dx * ln * 0.12, y + dy * ln * 0.12
    return [tip, (mx - dy * w, my + dx * w), tail, (mx + dy * w, my - dx * w)]


def _draw_spears(surf, s):
    for (d, ox, oy, ex, ey) in s.spears:
        p = (s.age - d) / s.travel
        if not (0 <= p <= 1):
            continue
        x, y = _lerp(ox, ex, p), _lerp(oy, ey, p)
        dx, dy = ex - ox, ey - oy
        ln = math.hypot(dx, dy) or 1
        dx, dy = dx / ln, dy / ln
        poly = _spear_poly(x, y, dx, dy, s.len, s.w)
        pygame.draw.polygon(surf, s.col + (235,), poly)
        pygame.draw.polygon(surf, lighten(s.col, 0.6) + (255,), [poly[0], poly[1], (x, y)])   # lit facet
        pygame.draw.polygon(surf, _scale_col(s.col, 0.45) + (255,), poly, 2)
        for k in range(1, 4):                                         # motion streak behind
            tx, ty = x - dx * (s.len * 0.45 + k * 9), y - dy * (s.len * 0.45 + k * 9)
            pygame.draw.circle(surf, lighten(s.col, 0.4) + (int(160 / k),), (int(tx), int(ty)), max(1, int(s.w * 0.5 / k)))


def _tick_spears(s, dt):
    for (d, ox, oy, ex, ey) in s.spears:
        p = (s.age - d) / s.travel
        if 0 <= p <= 1 and random.random() < 0.5:
            _vfx_add(VfxParticle("mote", _lerp(ox, ex, p), _lerp(oy, ey, p), vx=random.uniform(-20, 20),
                                 vy=random.uniform(-20, 20), drag=2.0, life=0.3, size=8, end_size=2, color=s.col))


def _draw_boulder(surf, s):
    p = min(1.0, s.age / s.travel)
    if p >= 1.0:
        return
    x = _lerp(s.ox, s.ex, p)
    y = _lerp(s.oy, s.ey, p) - s.arc * 4 * p * (1 - p)
    rot = s.age * s.spin
    pts = [(x + math.cos(rot + a) * s.r * m, y + math.sin(rot + a) * s.r * m) for a, m in s.shape_]
    pygame.draw.polygon(surf, s.col + (255,), pts)
    lit = [(x - s.r * 0.18 + (px - x) * 0.62, y - s.r * 0.22 + (py - y) * 0.62) for px, py in pts]
    pygame.draw.polygon(surf, lighten(s.col, 0.35) + (255,), lit)
    pygame.draw.polygon(surf, (s.edge if s.edge else _scale_col(s.col, 0.4)) + (255,), pts, 3 if s.edge else 2)


def _draw_spikes(surf, s):
    for (dx_, h, w, d) in s.spikes:
        t = s.age - d
        if t <= 0:
            continue
        rise = min(1.0, t / 0.14)
        rise = 1 - (1 - rise) ** 3
        sink = min(1.0, s.life / 0.22)
        hh = h * rise * sink
        if hh < 2:
            continue
        bx, by = s.gx + dx_, s.gy
        tip = (bx + w * 0.15, by - hh)
        left = [(bx - w, by), (bx - w * 0.45, by - hh * 0.45), tip, (bx, by)]
        right = [(bx, by), tip, (bx + w * 0.55, by - hh * 0.5), (bx + w, by)]
        pygame.draw.polygon(surf, lighten(s.col, 0.3) + (255,), left)
        pygame.draw.polygon(surf, _scale_col(s.col, 0.7) + (255,), right)
        pygame.draw.polygon(surf, _scale_col(s.col, 0.35) + (255,),
                            [(bx - w, by), (bx - w * 0.45, by - hh * 0.45), tip, (bx + w * 0.55, by - hh * 0.5), (bx + w, by)], 2)
    # cracked earth at the base
    a = int(200 * min(1.0, s.age / 0.1) * min(1.0, s.life / 0.3))
    pygame.draw.ellipse(surf, _scale_col(s.col, 0.3) + (a,), (s.gx - s.span - 20, s.gy - 7, 2 * s.span + 40, 14))


def _draw_blades(surf, s):
    a = _fade(s, 0.04, 0.2)
    for (d, ox, oy, ex, ey, bend) in s.blades:
        p = (s.age - d) / s.travel
        if not (0 <= p <= 1.05):
            continue
        p = min(1.0, p)
        mx, my = (ox + ex) / 2 - (ey - oy) * bend, (oy + ey) / 2 + (ex - ox) * bend
        x = (1 - p) ** 2 * ox + 2 * (1 - p) * p * mx + p * p * ex
        y = (1 - p) ** 2 * oy + 2 * (1 - p) * p * my + p * p * ey
        rot = s.age * 14 + d * 9
        R = s.r
        outer = [(x + math.cos(rot + t) * R, y + math.sin(rot + t) * R * 0.75) for t in [i * 0.2 - 1.3 for i in range(14)]]
        inner = [(x + math.cos(rot + t) * R * 0.62 + math.cos(rot) * R * 0.2,
                  y + (math.sin(rot + t) * R * 0.62 + math.sin(rot) * R * 0.2) * 0.75) for t in [1.3 - i * 0.2 for i in range(14)]]
        pygame.draw.polygon(surf, lighten(s.col, 0.55) + (int(185 * a),), outer + inner)
        pygame.draw.lines(surf, (255, 255, 255, int(255 * a)), False, outer, 3)
        pygame.draw.lines(surf, _scale_col(s.col, 0.7) + (int(220 * a),), False, inner, 2)


def _draw_vortex(surf, s):
    a = _fade(s, 0.12, 0.35)
    rings = 9
    for i in range(rings):
        f = i / (rings - 1)
        w = _lerp(s.w * 0.25, s.w, f) * (0.9 + 0.1 * math.sin(s.age * 9 + i))
        y = s.gy - f * s.h
        x = s.x + math.sin(s.age * 6 + f * 4) * 8 * f
        rect = pygame.Rect(int(x - w / 2), int(y - w * 0.14), int(w), max(4, int(w * 0.28)))
        start = s.age * 9 + i * 0.7
        pygame.draw.arc(surf, s.col + (int(200 * a * (0.55 + 0.45 * f)),), rect, start, start + 4.4, 6)
        pygame.draw.arc(surf, lighten(s.col, 0.6) + (int(255 * a),), rect, start + 0.5, start + 1.6, 3)


def _tick_vortex(s, dt):
    if random.random() < 0.9 and s.life > 0.15:
        f = random.random()
        ang = random.uniform(0, math.tau)
        w = _lerp(s.w * 0.25, s.w, f) / 2
        _vfx_add(VfxParticle(s.tex, s.x + math.cos(ang) * w, s.gy - f * s.h + math.sin(ang) * w * 0.28,
                             vx=-math.sin(ang) * 160, vy=-60, drag=2.0, life=0.35,
                             size=random.randint(8, 16), end_size=2, color=s.col, additive=s.tex != "shard"))


def _draw_bolt(surf, s):
    if int(s.age * 40) % 4 == 3:                                     # flicker
        return
    a = _fade(s, 0.0, 0.5)
    if s.age - s.regen > 0.045:
        s.regen = s.age
        s.paths = [_jag(s.sx, s.sy, s.ex, s.ey, s.rough)]
        for _ in range(s.branches):
            i = random.randint(len(s.paths[0]) // 4, len(s.paths[0]) * 3 // 4)
            bx, by = s.paths[0][i]
            ang = math.atan2(s.ey - s.sy, s.ex - s.sx) + random.choice((-1, 1)) * random.uniform(0.5, 1.1)
            ln = random.uniform(30, 80)
            s.paths.append(_jag(bx, by, bx + math.cos(ang) * ln, by + math.sin(ang) * ln, s.rough * 0.4, 3))
    for k, pts in enumerate(s.paths):
        wide = 1.0 if k == 0 else 0.5
        pygame.draw.lines(surf, _scale_col(s.col, 0.35 * a), False, pts, max(1, int(14 * wide * s.scale)))
        pygame.draw.lines(surf, _scale_col(s.col, a), False, pts, max(1, int(6 * wide * s.scale)))
        pygame.draw.lines(surf, _scale_col((255, 255, 255), a), False, pts, max(1, int(2 * wide * s.scale)))


def _draw_beam(surf, s):
    grow = min(1.0, s.age / 0.08)
    a = _fade(s, 0.0, 0.4)
    ex, ey = _lerp(s.ox, s.ex, grow), _lerp(s.oy, s.ey, grow)
    w = s.w * (0.8 + 0.2 * math.sin(s.age * 45)) * (0.4 + 0.6 * a)
    dx, dy = ex - s.ox, ey - s.oy
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    for width, col in ((w * 2.2, _scale_col(s.col, 0.3 * a)), (w, _scale_col(s.col, a)),
                       (w * 0.38, _scale_col((255, 255, 255), a))):
        hw = width / 2
        pygame.draw.polygon(surf, col, [(s.ox + nx * hw * 0.5, s.oy + ny * hw * 0.5), (ex + nx * hw, ey + ny * hw),
                                        (ex - nx * hw, ey - ny * hw), (s.ox - nx * hw * 0.5, s.oy - ny * hw * 0.5)])
        pygame.draw.circle(surf, col, (int(ex), int(ey)), int(hw * 1.2))
    pygame.draw.circle(surf, _scale_col(s.col, a), (int(s.ox), int(s.oy)), int(w * 0.9))


def _draw_void(surf, s):
    p = min(1.0, s.age / s.travel)
    if p >= 1.0:
        return
    x, y = _lerp(s.ox, s.ex, p), _lerp(s.oy, s.ey, p)
    for i, (hx, hy) in enumerate(s.hist):
        f = (i + 1) / max(1, len(s.hist))
        pygame.draw.circle(surf, (10, 4, 18, int(120 * f)), (int(hx), int(hy)), int(s.r * 0.8 * f))
    s.hist.append((x, y)); s.hist = s.hist[-10:]
    pygame.draw.circle(surf, (8, 2, 14, 245), (int(x), int(y)), int(s.r))
    rim = int(s.r + 3 + math.sin(s.age * 30) * 2)
    pygame.draw.circle(surf, s.col + (255,), (int(x), int(y)), rim, 3)
    ang = s.age * 10
    for k in range(3):
        a_ = ang + k * 2.1
        pygame.draw.circle(surf, lighten(s.col, 0.5) + (255,),
                           (int(x + math.cos(a_) * rim), int(y + math.sin(a_) * rim)), 3)


def _draw_implode(surf, s):
    k = s.age / s.max_life
    r = s.r * (math.sin(min(1.0, k * 1.6) * math.pi) if k < 0.62 else max(0.0, 1 - (k - 0.62) / 0.38) * 0.9)
    if r < 2:
        return
    pygame.draw.circle(surf, (6, 0, 12, 235), (int(s.x), int(s.y)), int(r))
    pygame.draw.circle(surf, s.col + (255,), (int(s.x), int(s.y)), int(r), 3)
    pygame.draw.circle(surf, lighten(s.col, 0.5) + (200,), (int(s.x), int(s.y)), int(r * 1.5 * (1 - k) + r), 2)


def _draw_ripple(surf, s):
    k = s.age / s.max_life
    a = int(220 * (1 - k))
    w = s.w * (0.3 + k)
    pygame.draw.ellipse(surf, s.col + (a,), (int(s.x - w), int(s.y - w * 0.22), int(2 * w), max(4, int(w * 0.44))), 3)


def _draw_dust(surf, s):
    k = s.age / s.max_life
    for (dx_, dy_, r0) in s.puffs:
        r = r0 * (0.5 + 1.1 * k)
        pygame.draw.circle(surf, s.col + (int(150 * (1 - k)),), (int(s.x + dx_ * (0.4 + k)), int(s.y + dy_ * (0.4 + k) - 16 * k)), int(r))


_SHAPE_DRAW = {"comet": _draw_comet, "flames": _draw_flames, "jet": _draw_jet, "spears": _draw_spears,
               "boulder": _draw_boulder, "spikes": _draw_spikes, "blades": _draw_blades, "vortex": _draw_vortex,
               "bolt": _draw_bolt, "beam": _draw_beam, "void": _draw_void, "implode": _draw_implode,
               "ripple": _draw_ripple, "dust": _draw_dust}
_SHAPE_TICK = {"comet": _tick_comet, "spears": _tick_spears, "vortex": _tick_vortex}


def update_vfx_shapes(dt):
    for s in _vfx_shapes[:]:
        s.age += dt
        s.life -= dt
        tick = _SHAPE_TICK.get(s.kind)
        if tick:
            tick(s, dt)
        if s.life <= 0:
            _vfx_shapes.remove(s)


def _vfx_layer(name, size, alpha):
    key = (name, size)
    lay = _vfx_layers.get(key)
    if lay is None:
        lay = pygame.Surface(size, pygame.SRCALPHA) if alpha else pygame.Surface(size)
        _vfx_layers[key] = lay
    return lay


def draw_vfx_shapes(surface):
    if not _vfx_shapes:
        return
    size = surface.get_size()
    glow = solid = None
    for s in _vfx_shapes:
        if s.additive:
            if glow is None:
                glow = _vfx_layer("glow", size, False); glow.fill((0, 0, 0))
        elif solid is None:
            solid = _vfx_layer("solid", size, True); solid.fill((0, 0, 0, 0))
    for s in _vfx_shapes:
        try:
            _SHAPE_DRAW[s.kind](glow if s.additive else solid, s)
        except (ValueError, TypeError) as e:         # a degenerate polygon must never kill the fight
            print(f"VFX shape error ({s.kind}): {e}")
    if solid is not None:
        surface.blit(solid, (0, 0))
    if glow is not None:
        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# --- the forms: each launches its shape and returns (seconds to impact) ---
def _travel_for(form, origin, end):
    dist = max(1.0, math.hypot(end[0] - origin[0], end[1] - origin[1]))
    return {"fireball": dist / 760, "jet": dist / 1150, "spear": dist / 1300, "boulder": 0.55,
            "spikes": 0.16, "blade": dist / 820, "vortex": 0.28, "bolt": 0.06, "beam": 0.09,
            "void": dist / 620}.get(form, dist / PROJECTILE_SPEED)


def _rock_col(col):
    return lerp_color(col, (120, 110, 100), 0.35)


def _launch_form(form, element, col, origin, end, travel, power, skill):
    ox, oy = origin
    ex, ey = end
    dx, dy = ex - ox, ey - oy
    ln = math.hypot(dx, dy) or 1.0
    gy, gscale = _ground_under(end)
    if form == "fireball":
        _shape("comet", travel + 0.25, False, element=element, col=col, ox=ox, oy=oy, ex=ex, ey=ey,
               travel=travel, x=ox, y=oy, r=int(22 * power ** 0.5), hist=[])
    elif form == "jet":
        _shape("jet", travel * 1.8 + 0.2, False, col=col, ox=ox, oy=oy, ex=ex, ey=ey, travel=travel,
               nx=-dy / ln, ny=dx / ln, w=int(14 * power ** 0.5))
    elif form == "spear":
        spears = []
        for i in range(3 if power < 1.3 else 4):
            off = (i - 1) * 22
            spears.append((i * 0.07, ox - dy / ln * off, oy + dx / ln * off,
                           ex - dy / ln * off * 0.25, ey + dx / ln * off * 0.25))
        _shape("spears", travel + 0.3, False, col=col, spears=spears, travel=travel, len=74, w=11)
    elif form == "boulder":
        molten = matchup_key(element) == "Fire"
        shape_ = [(i * math.tau / 9 + random.uniform(-0.2, 0.2), random.uniform(0.75, 1.1)) for i in range(9)]
        _shape("boulder", travel, False, col=_scale_col(_rock_col(col), 0.85) if not molten else (70, 40, 34),
               ox=ox, oy=oy - 30, ex=ex, ey=ey, travel=travel, arc=110, r=int(32 * power ** 0.5),
               spin=random.choice((-1, 1)) * 7, shape_=shape_, edge=(255, 120, 40) if molten else None)
    elif form == "spikes":
        wide = bool(skill) and any(w in skill.lower() for w in QUAKE_WORDS)
        n = 7 if wide else 4
        span = (150 if wide else 62) * gscale
        spikes = []
        for i in range(n):
            f = (i / (n - 1)) * 2 - 1 if n > 1 else 0
            spikes.append((f * span + random.uniform(-8, 8), random.uniform(70, 110) * gscale * (1.15 - 0.4 * abs(f)),
                           random.uniform(14, 22) * gscale, abs(f) * 0.08 + random.uniform(0, 0.03)))
        _shape("spikes", 0.75, False, col=_rock_col(col), gx=ex, gy=gy, spikes=spikes, span=span)
    elif form == "blade":
        blades = []
        for i in range(2 if power < 1.2 else 3):
            blades.append((i * 0.08, ox, oy, ex, ey, (0.28 if i % 2 == 0 else -0.28) * random.uniform(0.6, 1.0)))
        _shape("blades", travel + 0.35, False, col=col, blades=blades, travel=travel, r=46)
    elif form == "vortex":
        root = matchup_key(element)
        tex = {"Earth": "shard", "Fire": "ember", "Water": "mote"}.get(root, "mote")
        _shape("vortex", 0.85, False, col=col, x=ex, gy=gy, w=120 * gscale, h=160 * gscale, tex=tex)
    elif form == "bolt":
        _shape("bolt", 0.34, True, col=col, sx=ox, sy=oy, ex=ex, ey=ey, rough=60, branches=2, scale=1.0,
               regen=-1, paths=[])
        if power >= 1.2:                                                # the big ones come down from the sky too
            _shape("bolt", 0.3, True, col=col, sx=ex + random.uniform(-40, 40), sy=-10, ex=ex, ey=ey,
                   rough=70, branches=3, scale=1.3, regen=-1, paths=[])
    elif form == "beam":
        _shape("beam", 0.5, True, col=col, ox=ox, oy=oy, ex=ex + dx / ln * 30, ey=ey + dy / ln * 30,
               w=26 * power ** 0.5)
    elif form == "void":
        _shape("void", travel, False, col=col, ox=ox, oy=oy, ex=ex, ey=ey, travel=travel, r=17, hist=[])
    else:
        vfx_projectile(element, origin, end, speed=PROJECTILE_SPEED)


def _impact_form(form, element, col, pos, power, skill):
    x, y = pos
    gy, gscale = _ground_under(pos)
    if form == "fireball":
        tongues = [(i * math.tau / 9 + random.uniform(-0.2, 0.2), random.uniform(50, 85) * power, random.uniform(9, 14))
                   for i in range(9)]
        _shape("flames", 0.5, False, col=col, x=x, y=y, tongues=tongues)
    elif form == "jet":
        for i in range(16):                                            # a crown of droplets
            ang = -math.pi / 2 + random.uniform(-1.1, 1.1)
            spd = random.uniform(150, 300)
            _vfx_add(VfxParticle("ember", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd, ay=620,
                                 drag=0.4, life=random.uniform(0.45, 0.7), size=random.randint(10, 18),
                                 end_size=4, color=lighten(col, 0.3)))
        _shape("ripple", 0.5, False, col=(235, 248, 255), x=x, y=y + 30, w=70)
    elif form == "spear":
        for _ in range(14):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(90, 240)
            _vfx_add(VfxParticle("shard", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd - 60, ay=520,
                                 drag=0.3, life=random.uniform(0.4, 0.7), size=random.randint(9, 16), end_size=3,
                                 color=lighten(col, 0.25), spin=random.uniform(-8, 8), additive=False))
    elif form in ("boulder", "spikes"):
        dcol = _scale_col(lerp_color(_rock_col(col), (200, 190, 170), 0.4), 1.0)
        cy = y if form == "boulder" else gy - 10
        _shape("dust", 0.7, False, col=dcol, x=x, y=cy,
               puffs=[(random.uniform(-60, 60) * gscale, random.uniform(-20, 20), random.uniform(14, 26) * gscale) for _ in range(9)])
        for _ in range(12):
            ang = random.uniform(math.pi * 1.1, math.pi * 1.9)
            spd = random.uniform(120, 260)
            _vfx_add(VfxParticle("shard", x + random.uniform(-30, 30), cy, vx=math.cos(ang) * spd,
                                 vy=math.sin(ang) * spd, ay=700, drag=0.2, life=random.uniform(0.5, 0.8),
                                 size=random.randint(10, 18), end_size=6, color=_rock_col(col),
                                 spin=random.uniform(-8, 8), additive=False))
        if form == "spikes" and skill and any(w in skill.lower() for w in QUAKE_WORDS):
            vfx_shake(7.0)
    elif form == "blade":
        for i in range(10):
            ang = random.uniform(0, math.tau)
            if i < 3:                                                  # criss-cross cuts
                _vfx_add(VfxParticle("slash", x + math.cos(ang) * 10, y + math.sin(ang) * 10, life=0.22,
                                     size=60, end_size=90, color=lighten(col, 0.3), rot=ang, spin=4.0))
            else:
                _vfx_add(VfxParticle("mote", x, y, vx=math.cos(ang) * 220, vy=math.sin(ang) * 220, drag=3.0,
                                     life=0.35, size=10, end_size=2, color=lighten(col, 0.4)))
    elif form == "bolt":
        for _ in range(16):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(200, 420)
            _vfx_add(VfxParticle("spark", x, y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd, drag=4.0,
                                 life=random.uniform(0.15, 0.32), size=random.randint(12, 22), end_size=2,
                                 color=lighten(col, 0.3), spin=8.0))
        vfx_flash((255, 255, 255), 0.35)
    elif form == "beam":
        _vfx_add(VfxParticle("ring", x, y, life=0.4, size=30, end_size=200, color=lighten(col, 0.4)))
    elif form == "void":
        _shape("implode", 0.6, False, col=col, x=x, y=y, r=48 * power ** 0.5)
        for i in range(3):
            vfx_after(i * 0.08, lambda: _vfx_add(VfxParticle("ring", x, y, life=0.4, size=200, end_size=10, color=col)))
# ==================== end Spell VFX ====================


# ==================== Semantic Signals ====================
# The four callouts from the UI mockup's "Semantic Signals" card. Meaning-colour is kept
# separate from the gold accent so a combat readout reads at a glance:
#   super effective  -> ward green      not very effective -> crimson
#   level up         -> xp gold         mana surge         -> arcane blue
# The mockup marks each with a glyph (✦ ✧ ★ ◈), but Georgia has none of them — they come
# out as tofu boxes — so the marks are drawn as vector shapes instead.
SIGNAL_STYLES = {
    "super":   {"color": GRIM_WARD, "icon": "sparkle", "life": 2.3},
    "weak":    {"color": GRIM_BAD,  "icon": "hollow",  "life": 2.3},
    "levelup": {"color": GRIM_XP,   "icon": "star",    "life": 3.6},
    "surge":   {"color": GRIM_MP,   "icon": "diamond", "life": 2.3},
    "miss":    {"color": GRIM_CREAM_DIM, "icon": "miss", "life": 2.0},
}
COMBAT_SIGNALS = ("super", "weak", "surge", "miss")
_signals = []              # {"kind", "text", "age"}
_signal_clock = [None]     # wall time of the last draw, so signals age only while on screen


def raise_signal(kind, text):
    """Show a semantic callout. Re-raising a kind replaces it rather than stacking."""
    if kind not in SIGNAL_STYLES:
        return
    _signals[:] = [s for s in _signals if s["kind"] != kind]
    _signals.append({"kind": kind, "text": text, "age": 0.0})


def clear_signals(kinds=None):
    if kinds is None:
        _signals.clear()
    else:
        _signals[:] = [s for s in _signals if s["kind"] not in kinds]


def signal_effectiveness(multiplier):
    if multiplier >= SUPER_EFFECTIVE_MULTIPLIER:
        raise_signal("super", "It's super effective!")
    elif multiplier <= NOT_EFFECTIVE_MULTIPLIER:
        raise_signal("weak", "It's not very effective…")


def draw_signal_icon(surface, icon, center, r, color):
    cx, cy = center
    if icon in ("sparkle", "hollow"):           # ✦ / ✧ — four-point sparkle
        pts = [(cx + math.cos(-math.pi / 2 + i * math.pi / 4) * (r if i % 2 == 0 else r * 0.34),
                cy + math.sin(-math.pi / 2 + i * math.pi / 4) * (r if i % 2 == 0 else r * 0.34))
               for i in range(8)]
        pygame.draw.polygon(surface, color, pts, 0 if icon == "sparkle" else 2)
    elif icon == "star":                        # ★ — five-point star
        pts = [(cx + math.cos(-math.pi / 2 + i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45),
                cy + math.sin(-math.pi / 2 + i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45))
               for i in range(10)]
        pygame.draw.polygon(surface, color, pts)
    elif icon == "diamond":                     # ◈ — diamond within a diamond
        ir = r * 0.45
        pygame.draw.polygon(surface, color, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], 2)
        pygame.draw.polygon(surface, color, [(cx, cy - ir), (cx + ir, cy), (cx, cy + ir), (cx - ir, cy)])
    elif icon == "miss":                        # ⊘ — struck-through ring
        pygame.draw.circle(surface, color, (int(cx), int(cy)), int(r), 2)
        d = r * 0.72
        pygame.draw.line(surface, color, (cx - d, cy + d), (cx + d, cy - d), 2)


def draw_signals(surface, cx, y, kinds=None, max_lines=2, direction=-1, font_obj=None):
    """Draw live signals as centred icon + text lines, stacking away from y.

    Only signals actually drawn here age, so a level-up raised on the killing blow is still
    fresh when the post-fight screen shows it, instead of expiring off-screen."""
    font_obj = font_obj or small_font
    now = pygame.time.get_ticks() / 1000.0
    last = _signal_clock[0]
    dt = 0.0 if last is None else max(0.0, min(0.1, now - last))
    _signal_clock[0] = now

    for s in _signals:
        if kinds is None or s["kind"] in kinds:
            s["age"] += dt
    _signals[:] = [s for s in _signals if s["age"] < SIGNAL_STYLES[s["kind"]]["life"]]
    live = [s for s in _signals if kinds is None or s["kind"] in kinds][-max_lines:]

    line_h = font_obj.get_height() + 6
    r = max(5, font_obj.get_height() // 3)
    for i, s in enumerate(reversed(live)):      # newest sits nearest the anchor
        st = SIGNAL_STYLES[s["kind"]]
        fade = min(1.0, s["age"] / 0.15, max(0.0, (st["life"] - s["age"]) / 0.45))
        alpha = int(255 * fade)
        text = font_obj.render(s["text"], True, st["color"])
        shadow = font_obj.render(s["text"], True, (0, 0, 0))
        icon = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        draw_signal_icon(icon, st["icon"], (r + 2, r + 2), r, st["color"])
        for surf in (text, shadow, icon):
            surf.set_alpha(alpha)
        gap = 8
        total = r * 2 + gap + text.get_width()
        ly = y + direction * i * line_h
        x0 = cx - total // 2
        surface.blit(icon, (x0 - 2, ly - r - 2))
        tx, ty = x0 + r * 2 + gap, ly - text.get_height() // 2
        surface.blit(shadow, (tx + 1, ty + 1))
        surface.blit(text, (tx, ty))
# ==================== end Semantic Signals ====================



# ==================== Screen Transition ====================
# A pixel-dissolve wipe. The current frame is frozen and progressively crushed into chunky
# blocks as it darkens; the state switch happens at the blackout; then the new screen
# resolves back out of the blocks. Used when the player runs into an enemy, so dropping
# from the dungeon into the duel board reads as a deliberate cut instead of a hard snap.
TRANSITION_OUT = 0.20       # seconds to dissolve the old frame
TRANSITION_IN = 0.24        # seconds to resolve the new one
TRANSITION_BLOCK = 46       # largest block edge in pixels at full dissolve
TRANSITION_DARK = 205       # peak darkening, 0-255

_trans = {"active": False, "phase": "out", "t": 0.0, "snap": None, "on_switch": None}


def transition_active():
    return _trans["active"]


def begin_transition(on_switch):
    """Freeze the frame, dissolve it, run on_switch at the blackout, then resolve back in."""
    _trans["snap"] = main_menu.snapshot(screen)
    _trans["phase"] = "out"
    _trans["t"] = 0.0
    _trans["on_switch"] = on_switch
    _trans["active"] = True


def begin_game_intro(snapshot=None):
    """Enter gameplay the way an encounter is entered: the outgoing screen (the main menu,
    or the Defeated / Victory card on a retry) dissolves into blocks and the dungeon
    resolves out of them. The snapshot is taken before any video-mode change, so it's
    rescaled if the resolution moved in between."""
    snap = snapshot if snapshot is not None else main_menu.snapshot(screen)
    if snap.get_size() != screen.get_size():
        snap = pygame.transform.smoothscale(snap, screen.get_size())
    begin_transition(None)
    _trans["snap"] = snap


def update_transition(dt):
    if not _trans["active"]:
        return
    dur = TRANSITION_OUT if _trans["phase"] == "out" else TRANSITION_IN
    _trans["t"] += dt / max(0.001, dur)
    if _trans["t"] < 1.0:
        return
    if _trans["phase"] == "out":
        fn = _trans["on_switch"]
        _trans["on_switch"] = None
        _trans["phase"] = "in"
        _trans["t"] = 0.0
        if fn:
            fn()                    # the state actually changes while the screen is dark
    else:
        _trans["active"] = False
        _trans["snap"] = None


def _pixelate(surface, amount):
    """Crush a surface into blocks. amount 0 = untouched, 1 = chunkiest."""
    if amount <= 0.01:
        return surface
    w, h = surface.get_size()
    k = 1.0 + amount * (TRANSITION_BLOCK - 1)
    # plain scale is nearest-neighbour, which is what keeps the block edges hard
    small = pygame.transform.scale(surface, (max(1, int(w / k)), max(1, int(h / k))))
    return pygame.transform.scale(small, (w, h))


def draw_transition(render_current):
    """Draw the wipe. On the way back in it re-renders the live screen underneath."""
    # Clamp first: update_transition and draw_transition run in the same frame, so on the
    # last tick t overshoots 1.0 — and a negative base to a fractional power yields a
    # complex number in Python, which blows up the comparison below.
    prog = 0.0 if _trans["t"] < 0.0 else (1.0 if _trans["t"] > 1.0 else _trans["t"])
    if _trans["phase"] == "out":
        base = _trans["snap"]
        amount = prog ** 1.5
    else:
        render_current()            # draw the new state, then crush it
        base = main_menu.snapshot(screen)
        amount = (1.0 - prog) ** 1.5
    if base is None:
        return
    screen.blit(_pixelate(base, amount), (0, 0))
    dark = int(TRANSITION_DARK * amount)
    if dark > 0:
        veil = pygame.Surface(screen.get_size())
        veil.fill((0, 0, 0))
        veil.set_alpha(dark)
        screen.blit(veil, (0, 0))


def render_current_state():
    """Render the current state without advancing it — the transition drives the frame."""
    if game_state == STATE_COMBAT:
        render_combat()
    elif game_state == STATE_CREATE:
        render_create()
    else:
        render_explore()


def foe_level_for(e):
    """The level this foe fights at: near the hero's own (rolled once per foe)."""
    if not hasattr(e, "level_offset"):
        e.level_offset = random.choice(FOE_LEVEL_SPREAD) + (FOE_BOSS_LEVELS if e.is_boss else 0)
    return max(1, player_stats["level"] + e.level_offset)


def match_foe_to_player(e):
    """Set a foe's stats for the hero's current level, from the stats it was made with.
    A foe met again (after fleeing) is rescaled, keeping the share of HP it had left."""
    if not hasattr(e, "base_stats"):
        e.base_stats = (e.max_hp, e.attack, e.defense)
    hp0, atk0, def0 = e.base_stats
    lv = foe_level_for(e)
    n = lv - 1
    left = e.hp / e.max_hp if e.max_hp else 1.0
    e.level = lv
    e.max_hp = max(10, int(round(hp0 * (1 + FOE_LEVEL_HP * n))))
    e.hp = max(1, int(round(e.max_hp * left)))
    e.attack = max(1, int(round(atk0 * (1 + FOE_LEVEL_ATK_PCT * n) + FOE_LEVEL_ATK_FLAT * n)))
    e.defense = max(0, int(round(def0 + FOE_LEVEL_DEF_FLAT * n)))


def start_encounter(enemy, message):
    """Enter combat behind the pixel-dissolve instead of snapping straight to it."""
    def _enter():
        global current_enemy_encounter, game_state, combat_message, combat_turn
        global player_combat_action, combat_sub_state
        vfx_clear()
        clear_signals(COMBAT_SIGNALS)
        _bonus_turn["active"] = False
        _battle["t0"] = pygame.time.get_ticks() / 1000.0     # combatants slide in
        cancel_kill_hold()
        global is_in_combat_delay, combat_delay_start_time, next_combat_turn_after_delay
        current_enemy_encounter = enemy
        match_foe_to_player(enemy)
        game_state = STATE_COMBAT
        combat_message = message
        combat_turn = 'player'
        player_stats["is_defending"] = False
        player_stats["last_action"] = None
        player_stats["first_strike_ready"] = has_vow(V_FIRST_STRIKE)
        if has_vow(V_OVERFLOW):                    # Vow of the Overflow: begin at half MP
            player_stats["is_overcharged"] = False
            player_stats["mana"] = player_stats["max_mana"] // 2
        player_combat_action = None
        combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
        if has_vow(V_FIRST_STRIKE):                # …but the enemy always acts first
            combat_message = message + " It strikes first!"
            combat_turn = 'delay'
            is_in_combat_delay = True
            combat_delay_start_time = pygame.time.get_ticks()
            next_combat_turn_after_delay = 'enemy'
    begin_transition(_enter)
# ==================== end Screen Transition ====================


# ==================== Overworld (Pokémon-DS style exploration) ====================
# Exploration is a top-down tile world walked one tile at a time: hold a direction to walk,
# tap it to turn on the spot, hold Shift to run, walk south off a ledge to hop down it.
# Tall grass may hide a wild foe or an item.
# Each stage is an overworld of five biomes
# (worldgen.py); every biome has a cave mouth leading to a cave themed to match. Areas keep
# their own enemies and chests, and the game's world_map / enemies / chests / MAP_WIDTH /
# MAP_HEIGHT always point at the area the player is standing in.
import worldgen
import make_tiles

TILE_PX = worldgen.TILE            # tile size in the base-resolution art
WALK_SPEED = 4.0                   # tiles per second
RUN_SPEED = 7.5                    # while Shift is held
ENEMY_WORLD_PACE = WALK_SPEED / 1.5   # first-person walk was 1.5 tiles/s; foes keep that ratio
TURN_TAP = 0.09                    # a tap shorter than this only turns the player
BUMP_TIME = 0.22                   # stumble against something solid
GRASS_ENCOUNTER_CHANCE = 0.10      # per step into tall grass that something stirs
GRASS_ITEM_SHARE = 0.25            # of those, how many turn up an item instead of a foe
GRASS_SAFE_STEPS = 3               # grass steps after a find before the next can happen
GRASS_ALERT_TIME = 0.75            # how long the "!" hangs over your head before it plays out
WILD_BOSS_CHANCE = 0.03            # a wild foe from the grass is rarely a boss
WILD_BIOME_ELEMENT = 0.5           # and often shares the element of the land it lives in
_GRASS_LEAF = {"tallgrass": (120, 196, 92), "stormgrass": (110, 150, 150), "frostgrass": (226, 244, 250),
               "drygrass": (236, 210, 120), "ashgrass": (220, 110, 50)}
LEDGE_HOP_TIME = 0.42              # seconds to hop down a ledge (two tiles, whatever your pace)
LEDGE_HOP_HEIGHT = 9               # peak of the hop, in base pixels
OVERWORLD_ENEMY_SHARE = 0.55       # the rest of a stage's foes lurk in its caves
OVERWORLD_CHEST_SHARE = 0.40       # caves hold most of the loot

stage_areas = {}                   # area id -> worldgen.Area
_CLIFFS = worldgen.CLIFF_GROUND           # cliff faces, stairs and waterfalls: drawn whole, never blended


def _art_biome(area, x, y):
    """Which biome's art a tile wears (the neutral crossroads borrows the meadow's)."""
    if area.biome is None or not area.in_bounds(x, y):
        return "meadow"
    b = area.biome[y][x]
    return "meadow" if b == "hub" else b
area_enemies = {}                  # area id -> [Enemy]
area_chests = {}                   # area id -> [Chest]
current_area = None
_world_cache = {}                  # area id -> pre-rendered ground and the dynamic layers
_minimap = {}                      # area id -> {"color", "fog"} 1px-per-tile minimap layers

# --- Location banner (Pokémon-style place name when you cross into a new area) ---
_loc = {"name": "", "since": -99.0}
LOC_SHOW = 2.6


def announce_location(name, force=False):
    if force or name != _loc["name"]:
        _loc["name"] = name
        _loc["since"] = pygame.time.get_ticks() / 1000.0


_DIR_VEC = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
_DIR_KEYS = {"up": (pygame.K_UP, pygame.K_w), "down": (pygame.K_DOWN, pygame.K_s),
             "left": (pygame.K_LEFT, pygame.K_a), "right": (pygame.K_RIGHT, pygame.K_d)}
_pm = {"tile": (0, 0), "from": (0, 0), "to": (0, 0), "facing": "down", "moving": False,
       "t": 0.0, "turn": 0.0, "bump": 0.0, "steps": 0, "held": [], "busy": False, "running": False,
       "hop": False, "landed": None, "alert": None, "rustle": None, "grass_safe": 0}


def all_stage_enemies():
    """Every enemy the stage needs cleared: the overworld and its caves. Dungeon waves are
    optional side content, so they never hold up the stage."""
    return [e for aid, lst in area_enemies.items() if not aid.startswith("dungeon_") for e in lst]


def player_tile():
    """The tile the player occupies — their destination while mid-step."""
    if _pm["moving"]:
        return _pm["to"]
    return int(player_x), int(player_y)


def set_player_tile(x, y, facing=None):
    global player_x, player_y
    _pm.update(tile=(x, y), frm=(x, y), to=(x, y), moving=False, t=0.0, turn=0.0, bump=0.0, hop=False, alert=None)
    if facing:
        _pm["facing"] = facing
    player_x, player_y = x + 0.5, y + 0.5


def area_portals():
    return current_area.portals if current_area is not None else {}


def switch_area(area_id, tile=None, facing=None):
    """Make an area the live one and put the player in it."""
    global current_area, world_map, enemies, chests, MAP_WIDTH, MAP_HEIGHT
    area = stage_areas[area_id]
    current_area = area
    world_map = area.solid
    MAP_WIDTH, MAP_HEIGHT = area.w, area.h
    enemies = area_enemies[area_id]
    chests = area_chests[area_id]
    tx, ty = tile or area.start
    set_player_tile(tx, ty, facing)
    _pm["busy"] = False
    announce_location(area.label_at(tx, ty), force=True)
    reveal_minimap()


def _make_enemy(tx, ty, stage_number, is_boss):
    data = random.choice(ENEMY_TYPES).copy()
    mult = 2 ** (stage_number - 1)          # stats scale 2x per stage
    for k in ("hp", "attack", "defense"):
        data[k] = int(data[k] * mult)
    e = Enemy(tx + 0.5, ty + 0.5, tx, ty, enemy_data=data, p_level=player_stats["level"], is_boss=is_boss)
    e.tier = stage_number                   # danger tier (the stage, in a stage run): scales XP too
    print(f"Placed {data['name']} (Stats Scaled x{mult:,.0f}): HP={data['hp']}, ATK={data['attack']}, DEF={data['defense']}")
    return e


def setup_stage(stage_number, seed=None):
    """Generate the stage's overworld and caves, then populate them with foes and chests."""
    global stage_areas, area_enemies, area_chests

    if GAME_MODE == "limitless":
        setup_limitless()
        return
    open_world = GAME_MODE == "openworld"
    print(f"--- Setting up {'the Open World' if open_world else f'Stage {stage_number}'} ---")
    settle_quests_for_new_stage()
    if open_world:
        _loading.update(title="Forging the World", frac=0.0, last=-1.0)
        _loading_progress(0.0)
    _world_seed[0] = seed if seed is not None else random.randrange(2 ** 31)
    stage_areas = worldgen.generate_stage(_world_seed[0], stage_number,
                                          "open" if open_world else "stage",
                                          progress=_loading_progress if open_world else None)
    for a in stage_areas.values():
        a.tier = stage_number
    _world_cache.clear()
    _minimap.clear()
    area_enemies = {aid: [] for aid in stage_areas}
    area_chests = {aid: [] for aid in stage_areas}
    over = stage_areas["overworld"]
    caves = [aid for aid, a in stage_areas.items() if a.kind == "cave"]
    print(f"World generated: overworld {over.w}x{over.h}, caves: {', '.join(stage_areas[c].name for c in caves)}")

    def share(total, frac):
        """Split a count between the overworld and the caves (round-robin)."""
        n_over = int(round(total * frac)) if caves else total
        out = {"overworld": n_over}
        for i in range(total - n_over):
            c = caves[i % len(caves)]
            out[c] = out.get(c, 0) + 1
        return out

    pools = {}
    for aid, area in stage_areas.items():
        if area.kind in ("house", "dungeon"):
            continue
        tiles = area.spawn_tiles(avoid=area.safe, min_dist=7 if aid == "overworld" else 5)
        random.shuffle(tiles)
        pools[aid] = tiles
    luck = player_stats.get("luck", 0)

    if open_world:
        _populate_open_world(over, pools, luck)
        _spawner["t"] = 6.0
        _world_day[0] = world_day()
    else:
        _place_stage_foes_and_chests(stage_number, caves, pools, luck, share)

    # --- House chests: 0-2 in every home, on top of the field chests ---
    house_chests = 0
    for aid, area in stage_areas.items():
        if area.kind != "house":
            continue
        for (hx, hy) in area.chest_spots:
            rarity = roll_chest_rarity(getattr(area, "tier", stage_number), luck)
            if random.random() < HOUSE_CHEST_DOWNGRADE:
                rarity = CHEST_RARITIES[max(0, CHEST_RARITIES.index(rarity) - 1)]
            area_chests[aid].append(Chest(hx, hy, rarity))
            area.solid[hy][hx] = 1
            house_chests += 1
    print(f"Placed {house_chests} chests in {sum(1 for a in stage_areas.values() if a.kind == 'house')} houses")
    spawn_villagers()
    if open_world:
        _loading_progress(1.0)

    _pm["held"] = []
    switch_area("overworld", over.start, "down")


def _place_stage_foes_and_chests(stage_number, caves, pools, luck, share):
    """The classic stage: a set number of foes (the stage clears when they all fall)."""
    # --- Foes ---
    num_enemies_for_stage = NUM_ENEMIES + (stage_number - 1) * 2 # Increase enemies per stage
    if has_vow(V_HUNTER):
        num_enemies_for_stage = int(num_enemies_for_stage * 1.5)   # Hunter's Vow
    print(f"Placing {num_enemies_for_stage} enemies...")
    plan = share(num_enemies_for_stage, OVERWORLD_ENEMY_SHARE)
    order = [aid for aid in ([random.choice(caves)] if caves else []) + list(plan)]
    placed = 0
    for aid in order:
        while plan.get(aid, 0) > 0 and pools[aid]:
            tx, ty = pools[aid].pop()
            is_boss = placed == 0 or random.random() < 0.2   # the first foe (deep in a cave) is always a boss
            area_enemies[aid].append(_make_enemy(tx, ty, stage_number, is_boss))
            plan[aid] -= 1
            placed += 1
            if aid == order[0] and placed == 1:
                break                                         # just the guaranteed boss here first
    if placed < num_enemies_for_stage:
        print(f"Warning: Could only place {placed}/{num_enemies_for_stage} enemies.")
    else:
        print(f"Successfully placed {placed} enemies for Stage {stage_number}.")

    # --- Treasure chests: a fresh set every stage, richer the deeper you go ---
    num_chests = min(CHEST_MAX_PER_STAGE,
                     CHEST_BASE_COUNT + (stage_number - 1) * CHEST_PER_STAGE)
    if has_vow(V_FINAL_STAGE):
        num_chests *= 2                                           # Pact of the Final Stage
    chests_placed = 0
    for aid, n in share(num_chests, OVERWORLD_CHEST_SHARE).items():
        area = stage_areas[aid]
        for _ in range(n):
            if not pools[aid]:
                break
            rx, ry = pools[aid].pop()
            area_chests[aid].append(Chest(rx, ry, roll_chest_rarity(stage_number, luck)))
            area.solid[ry][rx] = 1                                # chests block the way
            chests_placed += 1
    every = [c for lst in area_chests.values() for c in lst]
    if chests_placed < num_chests:
        print(f"Warning: Could only place {chests_placed}/{num_chests} chests.")
    else:
        tally = {}
        for c in every:
            tally[c.rarity] = tally.get(c.rarity, 0) + 1
        summary = ", ".join(f"{n}x {r}" for r, n in
                            sorted(tally.items(), key=lambda kv: CHEST_RARITIES.index(kv[0])))
        print(f"Placed {chests_placed} chests for Stage {stage_number} (cap {CHEST_MAX_PER_STAGE}): {summary}")


# ---------------------------------------------------------------- movement

# ==================== Tall grass ====================
# Each step into tall grass may stir something up, Pokémon-style: a "!" pops over the
# player's head, then either a wild foe leaps out (a fight that never counts toward
# clearing the stage) or there's an item lying in the grass.

def _grass_stir():
    """Just stepped onto a tile. True if something stirred in the grass (movement stops)."""
    area = current_area
    tile = _pm["tile"]
    kind = area.decor.get(tile) if area is not None else None
    if kind not in worldgen.GRASS_KINDS:
        return False
    now = pygame.time.get_ticks() / 1000.0
    _pm["rustle"] = (tile, kind, now)
    if _pm["grass_safe"] > 0:
        _pm["grass_safe"] -= 1
        return False
    chance = GRASS_ENCOUNTER_CHANCE * (1.5 if has_vow(V_HUNTER) else 1.0)
    if random.random() >= chance:
        return False
    found = "item" if random.random() < GRASS_ITEM_SHARE else "foe"
    _pm.update(busy=True, alert=[found, 0.0])          # [what, seconds shown] — game time, not wall time
    return True


def _make_wild_enemy():
    tx, ty = _pm["tile"]
    e = _make_enemy(tx, ty, world_tier_at(tx, ty), random.random() < WILD_BOSS_CHANCE)
    area = current_area
    if area.biome is not None and area.in_bounds(tx, ty):
        el = worldgen.BIOMES[area.biome[ty][tx]]["element"]
        if el and random.random() < WILD_BIOME_ELEMENT:
            e.element = el
    e.wild = True                       # lives only for this fight; never on the map or the stage count
    return e


def _grass_find():
    """Something glinting in the grass: mostly brews, sometimes gear, a tier below a chest."""
    if len(player_stats["inventory"]) >= ITEM_GRID_ROWS * ITEM_GRID_COLS:
        player_stats["reroll_spins"] += 1
        show_notice("Found in the Grass", "1 Reroll Spin", "Your satchel is full — a spin instead.", GRIM_XP)
        return None
    rolled = roll_chest_rarity(current_tier(), player_stats.get("luck", 0))
    rarity = CHEST_RARITIES[max(0, CHEST_RARITIES.index(rolled) - 1)]
    item = None
    if random.random() < 0.6:
        brews = potions_of_rarity(rarity) or potions_of_rarity("Common")
        if brews:
            item = dict(random.choice(brews))
    if item is None:
        item = roll_chest_loot(rarity, player_stats["element"])
    if not item:
        player_stats["reroll_spins"] += 1
        show_notice("Found in the Grass", "1 Reroll Spin", "", GRIM_XP)
        return None
    player_stats["inventory"].append(item)
    r = item.get("rarity", rarity)
    show_notice("Found in the Grass", item["name"], f"{r} {item.get('slot', 'Item')}", RARITY_COLORS.get(r, GRIM_CREAM))
    print(f"Found in the grass -> {r} {item['name']}")
    return item


def update_grass_alert():
    """Let the "!" hang for a beat, then play out whatever was found."""
    al = _pm.get("alert")
    if not al:
        return
    al[1] += dt
    if al[1] < GRASS_ALERT_TIME:
        return
    _pm.update(alert=None, busy=False, grass_safe=GRASS_SAFE_STEPS)
    if al[0] == "item":
        _grass_find()
    else:
        foe = _make_wild_enemy()
        start_encounter(foe, f"A wild {foe.name} ({foe.element}) leaps out of the grass!")


def _ledge_landing(x, y, d):
    """Walking south off the top of a ledge hops you over it, Pokémon-style: one way only,
    down. Returns the tile you'd land on, or None if this isn't a ledge you can jump."""
    area = current_area
    if d != "down" or area is None or area.height is None:
        return None
    if not (area.in_bounds(x, y + 2) and area.ground[y + 1][x] == "cliff"):
        return None
    if area.height[y][x] <= area.height[y + 2][x] or not area.walkable(x, y + 2):
        return None
    if any((c.map_x, c.map_y) == (x, y + 2) for c in chests):
        return None
    if any(e.alive and (e.map_x, e.map_y) == (x, y + 2) for e in enemies):
        return None
    return (x, y + 2)


def _try_step(d):
    """Start a step one tile in direction d, or bump / open / fight whatever is there."""
    dx, dy = _DIR_VEC[d]
    x, y = _pm["tile"]
    nx, ny = x + dx, y + dy
    # a foe or chest only counts if you could actually step there — not across a cliff
    reach = current_area.can_step((x, y), (nx, ny), ignore_solid=True)
    if reach and villager_at(nx, ny):
        _pm["bump"] = BUMP_TIME                   # villagers stand their ground — talk to them instead
        return False
    foe = check_enemy_encounter(nx, ny) if reach else None
    if foe:
        start_encounter(foe, f"A wild {foe.name} ({foe.element}) appears!")
        return False
    for c in chests:
        if reach and (c.map_x, c.map_y) == (nx, ny):
            if not c.opened:
                open_chest_at(nx, ny)
            _pm["bump"] = BUMP_TIME
            return False
    if current_area.can_step((x, y), (nx, ny)):
        _pm.update(moving=True, frm=(x, y), to=(nx, ny), t=0.0, hop=False)
        _pm["steps"] += 1
        return True
    land = _ledge_landing(x, y, d)
    if land:
        _pm.update(moving=True, frm=(x, y), to=land, t=0.0, hop=True)
        return True
    _pm["bump"] = BUMP_TIME
    return False


def _on_arrive():
    """Arrived on a tile: take a portal if it's one. True if the player is now leaving."""
    portal = current_area.portals.get(_pm["tile"])
    if not portal:
        return False
    area_id, dest, facing = portal
    _pm["busy"] = True
    begin_transition(lambda: switch_area(area_id, dest, facing))
    return True


def interact_facing():
    """Space / Enter / E: talk to the villager, read the sign or open the chest in front."""
    if _pm["moving"] or _pm["busy"]:
        return
    dx, dy = _DIR_VEC[_pm["facing"]]
    x, y = _pm["tile"]
    v = villager_at(x + dx, y + dy)
    if v:
        talk_to(v)
        return
    if current_area.objects.get((x + dx, y + dy)) == "shrine" and current_area.can_step((x, y), (x + dx, y + dy), ignore_solid=True):
        use_shrine()
        return
    vil = village_of_sign(x + dx, y + dy) if current_area.objects.get((x + dx, y + dy)) == "sign" else None
    if vil:
        open_dialogue("Signpost", [f"Welcome to {vil['name']}!",
                                   f"{len(vil['houses'])} homes. Travellers welcome — our folk often need a hand "
                                   f"with the beasts outside the fence."])
        return
    if current_area.can_step((x, y), (x + dx, y + dy), ignore_solid=True) and open_chest_at(x + dx, y + dy):
        _pm["bump"] = BUMP_TIME


# ==================== Dungeons ====================
# Five rooms in a chain. Walking into a room bars the gate behind you and the foes come in
# waves; clear every wave and both gates lift. The last room ends in a reliquary chest and
# a way back to the gate you came in by.
DUNGEON_START_DELAY = 0.8          # seconds between stepping in and the first wave
DUNGEON_WAVE_DELAY = 1.1
DUNGEON_ROOM_SCALING = 0.12        # foes hit 12% harder per room deeper
DUNGEON_REWARD_SPINS = 5
DUNGEON_REWARD_POINTS = 2
_dungeon_clock = [0.0]             # advances only while exploring, so waves wait out battles and menus


def dungeon_state(area):
    if not hasattr(area, "dstate"):
        area.dstate = {"active": None, "wave": 0, "pending": None, "cleared": set(), "done": False}
    return area.dstate


def _set_door(area, tile, open_):
    if tile:
        area.solid[tile[1]][tile[0]] = 0 if open_ else 1


def _spawn_wave(area, ridx, wi):
    room = area.rooms[ridx]
    count, bosses = room["waves"][wi]
    x0, y0, x1, y1 = room["rect"]
    ptx, pty = player_tile()
    spots = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
             if area.walkable(x, y) and (x, y) not in area.portals and abs(x - ptx) + abs(y - pty) >= 3
             and not any(e.alive and (e.map_x, e.map_y) == (x, y) for e in enemies)]
    random.shuffle(spots)
    now = pygame.time.get_ticks() / 1000.0
    boost = 1.0 + DUNGEON_ROOM_SCALING * ridx
    for i in range(count + bosses):
        if not spots:
            break
        tx, ty = spots.pop()
        e = _make_enemy(tx, ty, getattr(area, "tier", current_stage), i >= count)
        e.max_hp = int(e.max_hp * boost); e.hp = e.max_hp
        e.attack = int(e.attack * boost)
        e.detection_range = 40.0          # nowhere to hide in an arena
        e.move_pause_timer = 0.5
        e.room = ridx
        e.spawn_t = now
        enemies.append(e)


def _dungeon_complete(area):
    st = dungeon_state(area)
    st["done"] = True
    quest_note_dungeon(area.id)
    rx, ry = area.reward_tile
    base = roll_chest_rarity(getattr(area, "tier", current_stage), player_stats.get("luck", 0))
    idx = max(CHEST_RARITIES.index(base), CHEST_RARITIES.index("Epic"))
    if random.random() < 0.4:
        idx += 1
    chest = Chest(rx, ry, CHEST_RARITIES[min(idx, len(CHEST_RARITIES) - 1)])
    chest.special = True
    chests.append(chest)
    area.solid[ry][rx] = 1
    home = area.portals[area.entry]
    area.portals[area.final_exit] = home
    show_notice("Dungeon Cleared!", area.name, "A reliquary chest and the way home appear.", GRIM_XP)


def update_dungeon():
    area = current_area
    if area is None or area.kind != "dungeon":
        return
    st = dungeon_state(area)
    _dungeon_clock[0] += dt
    now = _dungeon_clock[0]
    r = area.room_at(*player_tile())
    if st["active"] is None and r is not None and r not in st["cleared"]:
        st.update(active=r, wave=0, pending=now + DUNGEON_START_DELAY)
        _set_door(area, area.rooms[r]["back"], False)          # the gate slams shut behind you
        n = len(area.rooms[r]["waves"])
        show_notice("Ambush!", f"Room {r + 1} of {len(area.rooms)}", f"Survive {n} waves", GRIM_BAD)
    if st["active"] is None:
        return
    ridx = st["active"]
    room = area.rooms[ridx]
    if st["pending"] is not None:
        if now >= st["pending"]:
            _spawn_wave(area, ridx, st["wave"])
            st["pending"] = None
        return
    if any(e.alive and getattr(e, "room", None) == ridx for e in enemies):
        return
    st["wave"] += 1
    if st["wave"] < len(room["waves"]):
        st["pending"] = now + DUNGEON_WAVE_DELAY
        show_notice("Wave Cleared", f"Wave {st['wave'] + 1} of {len(room['waves'])}", "More are coming…", GRIM_WARN)
        return
    st["cleared"].add(ridx)
    st["active"] = None
    _set_door(area, room["back"], True)
    _set_door(area, room["door"], True)
    if ridx == len(area.rooms) - 1:
        _dungeon_complete(area)
    else:
        show_notice("Room Cleared", "The gate grinds open", f"Room {ridx + 2} awaits", GRIM_WARD)


def dungeon_status_text():
    area = current_area
    if area is None or area.kind != "dungeon":
        return ""
    st = dungeon_state(area)
    if st["done"]:
        return "Cleared — the reliquary awaits"
    if st["active"] is not None:
        room = area.rooms[st["active"]]
        return f"Room {st['active'] + 1}/{len(area.rooms)}  ·  Wave {min(st['wave'] + 1, len(room['waves']))}/{len(room['waves'])}"
    return f"Rooms cleared {len(st['cleared'])}/{len(area.rooms)}"


# ==================== Game modes: Open World and Limitless ====================
# "openworld": one vast land (worldgen's "open" profile, 10x the area of a stage map) that
#   never ends. There's no kill count to clear: foes keep turning up around you — packs, and
#   now and then a boss — and the further you roam from the crossroads, the more dangerous
#   the land (Danger I-V). Villagers hand out fresh work every new day.
# "limitless": an endless descent through dungeon chambers. Each chamber is five waves; a
#   wave is 5 foes, 5 more every 10 waves, and every 10th wave brings a boss. Beat a
#   chamber's waves and a chest with a decent piece of gear appears, and the barred door
#   opens onto the next chamber.
# "stages": the classic five-stage run (kept for the test suite; not on the menu).
OPEN_MAX_TIER = 5                  # Danger I (the crossroads) .. V (the far edges)
OPEN_FOE_CAP = 45                  # foes alive on the open world's surface at once
OPEN_START_FOES = 40               # scattered over the land when the world is made
OPEN_CAVE_FOES = (4, 6)            # in each cave at the start
OPEN_CAVE_CAP = 6                  # caves top themselves back up to this
OPEN_FIELD_CHESTS = 50
OPEN_CAVE_CHESTS = 2
OPEN_SPAWN_EVERY = (9.0, 16.0)     # seconds of exploring between new arrivals
OPEN_SPAWN_RING = (14, 30)         # how far from you (tiles) they turn up
OPEN_PACK = (1, 3)                 # foes per arrival
OPEN_BOSS_CHANCE = 0.12            # odds an arrival brings a boss
OPEN_DESPAWN_DIST = 45             # stragglers this far away make room for new arrivals
LIMITLESS_WAVES_PER_CHAMBER = 5
LIMITLESS_WAVE_SIZE = 5            # foes in a wave...
LIMITLESS_WAVE_GROWTH = 5          # ...plus this many more every 10 waves
LIMITLESS_BOSS_EVERY = 10          # a boss joins every 10th wave
LIMITLESS_FIRST_DELAY = 1.6        # seconds before a chamber's first wave
LIMITLESS_WAVE_DELAY = 1.4
LIMITLESS_STAT_GROWTH = 1.5        # foes' stats x this every 10 waves...
LIMITLESS_STEP_GROWTH = 0.04       # ...and +4% each wave in between

GAME_MODE = "stages"
_spawner = {"t": 6.0}
_world_day = [0]
_ll = {"area": None, "chamber": 1, "wave": 0, "local": 0, "pending": None, "cleared": False, "clock": 0.0}
_loading = {"last": -1.0, "frac": 0.0, "title": ""}


def set_game_mode(mode):
    global GAME_MODE
    GAME_MODE = mode if mode in ("openworld", "limitless", "stages") else "stages"
    print(f"Game mode: {GAME_MODE}")


def progress_stage():
    """How far the run has come, in stages: the stage itself, or in the endless modes the
    fiercest danger tier you've beaten a foe at."""
    if GAME_MODE == "stages":
        return current_stage
    return player_stats.get("peak_tier", 1)


def world_tier_at(x, y, area=None):
    """Danger tier of a spot (1-5). Only the open world varies: further from the
    crossroads is fiercer. Caves, dungeons and houses take the tier of their entrance."""
    area = area or current_area
    if GAME_MODE != "openworld":
        return getattr(area, "tier", current_stage) if area is not None else current_stage
    if area is not None and area.kind != "overworld":
        return getattr(area, "tier", 1)
    over = stage_areas.get("overworld")
    if over is None:
        return 1
    sx, sy = over.start
    d = math.hypot(x - sx, (y - sy) * over.w / over.h) / (over.w / 2)
    return max(1, min(OPEN_MAX_TIER, 1 + int(d * 4.6)))


def current_tier():
    tx, ty = player_tile()
    return world_tier_at(tx, ty)


def world_day():
    return (pygame.time.get_ticks() + DAY_CYCLE_START_MS) // DAY_CYCLE_MS + 1 + _day_offset[0]


def _loading_progress(frac):
    """Keep the window alive (and show how far along it is) while a big world is made."""
    if frac is not None:
        _loading["frac"] = frac
    now = pygame.time.get_ticks() / 1000.0
    if now - _loading["last"] < 0.05 and frac not in (0.0, 1.0):
        return
    _loading["last"] = now
    pygame.event.pump()
    # plain pygame only: the first world is made before the UI helpers are defined
    for y in range(0, SCREEN_HEIGHT, 4):
        k = y / SCREEN_HEIGHT
        screen.fill((int(24 - 18 * k), int(18 - 14 * k), int(12 - 9 * k)), (0, y, SCREEN_WIDTH, 4))
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    title = title_font.render((_loading["title"] or "Forging the World").upper(), True, GRIM_GOLD_BRIGHT)
    screen.blit(title, title.get_rect(center=(cx, cy - 50)))
    bar = pygame.Rect(0, 0, 420, 18)
    bar.center = (cx, cy + 10)
    pygame.draw.rect(screen, (20, 14, 8), bar, border_radius=6)
    fill = bar.copy(); fill.width = int(bar.width * max(0.02, min(1.0, _loading["frac"])))
    pygame.draw.rect(screen, GRIM_GOLD, fill, border_radius=6)
    pygame.draw.rect(screen, GRIM_GOLD_DEEP, bar, width=1, border_radius=6)
    sub = small_font.render("Raising hills, carving caves, building villages…", True, GRIM_CREAM_DIM)
    screen.blit(sub, sub.get_rect(center=(cx, cy + 46)))
    main_menu.present()


# ---------------------------------------------------------------- open world

def _open_spot(area, near, ring, avoid=()):
    """A free walkable tile `ring` tiles from `near` (None if none turns up)."""
    px, py = near
    for _ in range(60):
        ang = random.uniform(0, math.tau)
        d = random.uniform(*ring)
        x, y = int(px + math.cos(ang) * d), int(py + math.sin(ang) * d)
        if not area.walkable(x, y) or (x, y) in area.safe or (x, y) in area.portals or (x, y) in avoid:
            continue
        if any(e.alive and (e.map_x, e.map_y) == (x, y) for e in enemies):
            continue
        if any((c.map_x, c.map_y) == (x, y) for c in chests):
            continue
        return (x, y)
    return None


def update_open_world():
    """New foes turn up around you every so often; a fresh day brings fresh quests."""
    if GAME_MODE != "openworld" or current_area is None:
        return
    day = world_day()
    if day != _world_day[0]:
        first = _world_day[0] == 0
        _world_day[0] = day
        if not first:
            refresh_village_quests()
            _quest_note(f"Day {day}", "A new day dawns", "The villagers have new work for you.", GRIM_GOLD_BRIGHT)
    area = current_area
    if area.kind not in ("overworld", "cave"):
        return
    _spawner["t"] -= dt
    if _spawner["t"] > 0:
        return
    _spawner["t"] = random.uniform(*OPEN_SPAWN_EVERY)
    if len(enemies) > 160:                                       # forget the fallen
        enemies[:] = [e for e in enemies if e.alive or e is current_enemy_encounter]
    alive = [e for e in enemies if e.alive]
    here = player_tile()
    if area.kind == "cave":
        if len(alive) >= OPEN_CAVE_CAP:
            return
        n = 1
        ring = (7, 18)
    else:
        n = random.randint(*OPEN_PACK)
        ring = OPEN_SPAWN_RING
        room = OPEN_FOE_CAP - len(alive)
        if room < n:                                            # make room: drop far-off stragglers
            far = sorted((e for e in alive if e.ai_state != "chase"
                          and abs(e.map_x - here[0]) + abs(e.map_y - here[1]) > OPEN_DESPAWN_DIST),
                         key=lambda e: -(abs(e.map_x - here[0]) + abs(e.map_y - here[1])))
            for e in far[:n - room]:
                enemies.remove(e)
            n = min(n, OPEN_FOE_CAP - sum(1 for e in enemies if e.alive))
        if n <= 0:
            return
    first = _open_spot(area, here, ring)
    if first is None:
        return
    now = pygame.time.get_ticks() / 1000.0
    boss_slot = 0 if random.random() < OPEN_BOSS_CHANCE * (1.5 if has_vow(V_HUNTER) else 1.0) else -1
    spots = [first]
    for _ in range(n - 1):
        s = _open_spot(area, first, (1, 3), avoid=spots)
        if s:
            spots.append(s)
    for i, (x, y) in enumerate(spots):
        e = _make_enemy(x, y, world_tier_at(x, y, area), i == boss_slot)
        if area.kind == "overworld" and random.random() < WILD_BIOME_ELEMENT:
            el = worldgen.BIOMES[area.biome[y][x]]["element"]
            if el:
                e.element = el
        e.spawn_t = now
        enemies.append(e)
    if boss_slot == 0:
        show_notice("A Boss Draws Near", f"{enemies[-len(spots)].name}", "Something big is prowling close by.",
                    GRIM_BAD, ms=2600)


def refresh_village_quests():
    """A new day: villagers without a job under way think up new ones."""
    by_village = {}
    for v in villagers:
        by_village.setdefault(id(v.village), (v.village, []))[1].append(v)
    fresh = 0
    for village, folk in by_village.values():
        busy = [v for v in folk if v.quest and v.quest["status"] in ("active", "ready")]
        taken = {(v.quest["kind"], v.quest["target"]) for v in busy}
        idle = [v for v in folk if v not in busy]
        for v in idle:
            v.quest = None
        for v in random.sample(idle, min(len(idle), max(0, random.randint(*QUEST_GIVERS) - len(busy)))):
            v.quest = make_quest(v, village, taken)
            fresh += v.quest is not None
    print(f"Day {_world_day[0]}: {fresh} new quests posted")


def _populate_open_world(over, pools, luck):
    """Foes, chests and tiers for a freshly made open world."""
    for aid, a in stage_areas.items():                    # what tier each indoor place is
        if a.kind == "cave":
            a.tier = world_tier_at(*over.mouths[aid[len("cave_"):]], over)
        elif a.kind == "dungeon":
            a.tier = world_tier_at(*over.gates[aid[len("dungeon_"):]], over)
    for v in over.villages:
        for h in v["houses"]:
            if h.get("area") in stage_areas:
                stage_areas[h["area"]].tier = world_tier_at(*v["plaza"], over)
    sx, sy = over.start
    placed = 0
    for (tx, ty) in pools["overworld"]:
        if placed >= OPEN_START_FOES:
            break
        if abs(tx - sx) + abs(ty - sy) < 14:
            continue
        e = _make_enemy(tx, ty, world_tier_at(tx, ty, over), random.random() < OPEN_BOSS_CHANCE)
        area_enemies["overworld"].append(e)
        placed += 1
    for aid, a in stage_areas.items():
        if a.kind != "cave":
            continue
        for _ in range(random.randint(*OPEN_CAVE_FOES)):
            if pools[aid]:
                tx, ty = pools[aid].pop()
                area_enemies[aid].append(_make_enemy(tx, ty, a.tier, random.random() < 0.15))
    chests_placed = 0
    for aid, n in [("overworld", OPEN_FIELD_CHESTS)] + [(aid, OPEN_CAVE_CHESTS) for aid, a in stage_areas.items()
                                                         if a.kind == "cave"]:
        a = stage_areas[aid]
        for _ in range(n):
            if not pools[aid]:
                break
            rx, ry = pools[aid].pop()
            area_chests[aid].append(Chest(rx, ry, roll_chest_rarity(world_tier_at(rx, ry, a), luck)))
            a.solid[ry][rx] = 1
            chests_placed += 1
    print(f"Open world: {placed} foes roam the land, {sum(len(area_enemies[aid]) for aid in area_enemies) - placed} "
          f"in caves, {chests_placed} chests")


# ---------------------------------------------------------------- Limitless

def limitless_wave_size(k):
    return LIMITLESS_WAVE_SIZE + LIMITLESS_WAVE_GROWTH * ((k - 1) // 10)


def limitless_tier(k):
    return 1 + (k - 1) // 10


def setup_limitless():
    global stage_areas, area_enemies, area_chests
    print("--- Limitless: entering Chamber 1 ---")
    _world_cache.clear()
    _minimap.clear()
    chamber = worldgen.generate_chamber(random.Random(random.randrange(2 ** 31)), 1)
    chamber.number = 1
    chamber.tier = 1
    stage_areas = {chamber.id: chamber}
    area_enemies = {chamber.id: []}
    area_chests = {chamber.id: []}
    spawn_villagers()                                    # no villages down here
    _ll.update(area=None, chamber=1, wave=0, local=0, pending=None, cleared=False, clock=0.0)
    _pm["held"] = []
    switch_area(chamber.id, chamber.start, "up")


def _spawn_limitless_wave(area):
    _ll["wave"] += 1
    _ll["local"] += 1
    k = _ll["wave"]
    count = limitless_wave_size(k)
    boss = k % LIMITLESS_BOSS_EVERY == 0
    x0, y0, x1, y1 = area.rect
    ptx, pty = player_tile()
    spots = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
             if area.walkable(x, y) and abs(x - ptx) + abs(y - pty) >= 4
             and not any((c.map_x, c.map_y) == (x, y) for c in chests)]
    random.shuffle(spots)
    mult = LIMITLESS_STAT_GROWTH ** ((k - 1) // 10) * (1 + LIMITLESS_STEP_GROWTH * ((k - 1) % 10))
    now = pygame.time.get_ticks() / 1000.0
    for i in range(count + (1 if boss else 0)):
        if not spots:
            break
        tx, ty = spots.pop()
        e = _make_enemy(tx, ty, 1, boss and i == count)
        e.tier = limitless_tier(k)
        e.max_hp = int(e.max_hp * mult); e.hp = e.max_hp
        e.attack = int(e.attack * mult); e.defense = int(e.defense * mult)
        e.detection_range = 40.0
        e.move_pause_timer = 0.6 + random.random() * 0.6
        e.spawn_t = now
        enemies.append(e)
    sub = f"{count} foes" + ("  ·  and a BOSS!" if boss else "")
    show_notice(f"Chamber {_ll['chamber']}  ·  Wave {_ll['local']}/{LIMITLESS_WAVES_PER_CHAMBER}",
                f"Wave {k}", sub, GRIM_BAD if boss else GRIM_WARN, ms=2200)
    print(f"Limitless wave {k}: {count} foes{' + boss' if boss else ''} (stats x{mult:.2f})")


def _limitless_chamber_cleared(area):
    _ll["cleared"] = True
    n = _ll["chamber"]
    # a chest with a decent piece of gear, better after a boss
    x0, y0, x1, y1 = area.rect
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    spot = min(((x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                if area.walkable(x, y) and (x, y) != player_tile()
                and not any(e.alive and (e.map_x, e.map_y) == (x, y) for e in enemies)),
               key=lambda t: abs(t[0] - cx) + abs(t[1] - cy))
    k = _ll["wave"]
    base = roll_chest_rarity(limitless_tier(k), player_stats.get("luck", 0))
    idx = max(CHEST_RARITIES.index(base) + 1, CHEST_RARITIES.index("Rare"))
    if any(w % LIMITLESS_BOSS_EVERY == 0 for w in range(k - LIMITLESS_WAVES_PER_CHAMBER + 1, k + 1)):
        idx += 1                                                  # a boss fell in this chamber
    chest = Chest(spot[0], spot[1], CHEST_RARITIES[min(idx, len(CHEST_RARITIES) - 1)])
    chest.gear = True
    chests.append(chest)
    area.solid[spot[1]][spot[0]] = 1
    # the way deeper
    nxt = worldgen.generate_chamber(random.Random(random.randrange(2 ** 31)), n + 1)
    nxt.number = n + 1
    nxt.tier = limitless_tier(k + 1)
    stage_areas[nxt.id] = nxt
    area_enemies[nxt.id] = []
    area_chests[nxt.id] = []
    dx, dy = area.door
    area.solid[dy][dx] = 0
    area.portals[(dx, dy)] = (nxt.id, nxt.start, "up")
    show_notice("Chamber Cleared!", f"Chamber {n}", f"A {chest.rarity} chest appears, and the door north opens.",
                GRIM_XP)


def update_limitless():
    area = current_area
    if GAME_MODE != "limitless" or area is None or area.kind != "chamber":
        return
    _ll["clock"] += dt
    now = _ll["clock"]
    if _ll["area"] != area.id:                                    # just walked in
        for old in [aid for aid in stage_areas if aid != area.id]:
            if not any(p[0] == old for p in area.portals.values()):
                stage_areas.pop(old, None); area_enemies.pop(old, None); area_chests.pop(old, None)
                _world_cache.pop(old, None); _minimap.pop(old, None)
        _ll.update(area=area.id, chamber=getattr(area, "number", 1), local=0, cleared=False,
                   pending=now + LIMITLESS_FIRST_DELAY)
        return
    if _ll["cleared"]:
        return
    if _ll["pending"] is not None:
        if now >= _ll["pending"]:
            _ll["pending"] = None
            _spawn_limitless_wave(area)
        return
    if any(e.alive for e in enemies):
        return
    if _ll["local"] < LIMITLESS_WAVES_PER_CHAMBER:
        _ll["pending"] = now + LIMITLESS_WAVE_DELAY
        show_notice("Wave Cleared", f"Wave {_ll['wave']} down", "The next one is coming…", GRIM_WARD, ms=1600)
    else:
        _limitless_chamber_cleared(area)


def limitless_status_text():
    area = current_area
    if area is None or area.kind != "chamber":
        return ""
    if _ll["cleared"]:
        return f"Chamber {_ll['chamber']} cleared — the door north is open"
    alive = sum(1 for e in enemies if e.alive)
    return (f"Chamber {_ll['chamber']}  ·  Wave {max(1, _ll['local'])}/{LIMITLESS_WAVES_PER_CHAMBER}"
            f"  (#{max(1, _ll['wave'])})  ·  {alive} left")


# ==================== Villages, villagers and quests ====================
# Every stage has 1-3 villages (worldgen.py). Villagers wander the plaza; a few have work
# for you — a gold "!" floats over them. Talk to one (face them, Space/E) to hear the job and
# accept or decline it. Progress counts itself as you fight; when a job is done a blue "?"
# marks the villager to report back to for the reward. [P] opens the quest log.
# Leaving a stage delivers the rewards of finished jobs; unfinished ones are lost.
QUEST_MAX_ACTIVE = 5               # quests you can carry at once
QUEST_GIVERS = (2, 3)              # villagers per village with a job to give
VILLAGER_SPEED = 2.2               # tiles per second when they stroll
VILLAGER_IDLE = (1.6, 5.0)         # seconds between a villager's strolls
DIALOGUE_CPS = 75                  # characters per second as dialogue types out
HOUSE_CHEST_DOWNGRADE = 0.5        # odds a house chest is a tier poorer than a field chest

villagers = []                     # this stage's villagers (all on the overworld)
quest_log = []                     # every quest accepted this run (old stages kept as history)
_quest_notices = []                # queued banners, shown one at a time while exploring
_quest_ids = [0]
_dlg = {"name": "", "pages": [], "page": 0, "shown": 0.0, "choices": None, "sel": 0,
        "on_choice": None, "on_done": None, "npc": None}
_qlog = {"sel": 0, "confirm": False}

_VILLAGER_NAMES = ["Alda", "Bram", "Corin", "Dessa", "Edric", "Fenna", "Gil", "Hollis", "Ida", "Jory", "Kael",
                   "Liss", "Mabel", "Nils", "Odette", "Pell", "Quinn", "Rosa", "Silas", "Tamsin", "Ulric",
                   "Vera", "Wynn", "Yara", "Zeb", "Agnes", "Bertram", "Cleo", "Dunstan", "Elsie", "Finch",
                   "Greta", "Harlow", "Ivo", "Juniper", "Lark", "Merrick", "Nell", "Otto", "Pippa"]
_VILLAGER_CHATTER = [
    "Tall grass hides more than rabbits these days. Watch your step out there.",
    "If you're lost, the map's always a Tab away. Or so the travellers tell me.",
    "The caves run deep. Folk say the biggest brutes lurk at the bottom.",
    "Those old dungeon gates? Nobody comes back from them without a fight. Or treasure.",
    "My grandmother swore every ledge is a shortcut — if you only ever go down.",
    "Help yourself to a look round the houses. Just... don't tell my neighbours I said so.",
    "Some of us have work that needs doing. Look for the ones with a worried face.",
    "The well water's the sweetest for a hundred miles. Don't drink from the river.",
    "Stairs are the only way up the hills. Cliffs don't care how strong you are.",
    "A traveller like you could do a lot of good round here.",
    "Lamps are lit at dusk. Nothing dares come into the village after dark.",
    "They say the bindings can make you stronger — at a price.",
]
_PLURAL = {"Goblin": "Goblins", "Skeleton": "Skeletons", "Orc": "Orcs", "Slime": "Slimes",
           "Shadow Lurker": "Shadow Lurkers"}
_QUEST_STATUS_COLOR = {"ready": GRIM_XP, "active": GRIM_CREAM, "done": GRIM_WARD, "failed": GRIM_BAD}
_QUEST_STATUS_TEXT = {"ready": "Complete — return for your reward", "active": "In progress",
                      "done": "Finished", "failed": "Failed"}


class Villager:
    """A villager standing on (and strolling about) their village's plaza."""
    def __init__(self, name, tile, village, look):
        self.name, self.village, self.look = name, village, look
        self.tile = self.frm = self.to = tile
        self.t, self.moving, self.steps = 0.0, False, 0
        self.facing = random.choice(("down", "left", "right", "up"))
        self.timer = random.uniform(*VILLAGER_IDLE)
        self.quest = None
        self.line = random.choice(_VILLAGER_CHATTER)
        self.frames = None

    def pos(self):
        (fx, fy), (tx, ty) = self.frm, self.to
        k = self.t if self.moving else 0.0
        return fx + (tx - fx) * k + 0.5, fy + (ty - fy) * k + 0.5


def _villager_look():
    race = random.choices(["Human", "Elf", "Dwarf", "Orc", "Goblin"], weights=[50, 15, 15, 10, 10])[0]
    cls = random.choices(["Mage", "Brawler", "Knight"], weights=[45, 40, 15])[0]
    hood = random.random() < (0.7 if cls == "Knight" else 0.15)
    return {"class": cls, "race": race, "color": random.choice(list(make_tiles.OUTFIT_COLORS.values())),
            "skin": make_tiles.SKIN_TONES[random.choice(make_tiles.RACE_SKINS[race])],
            "hair": random.choice(list(make_tiles.HAIR_COLORS.values())),
            "style": random.choice(make_tiles.HAIRSTYLES), "hood": hood}


def villager_frames(v):
    if v.frames is None:
        v.frames = {d: [f.convert_alpha() for f in fr] for d, fr in make_tiles.player_frames(v.look).items()}
    return v.frames


def villager_at(x, y):
    """The villager standing on (or stepping into) this overworld tile, if any."""
    if current_area is None or current_area.id != "overworld":
        return None
    for v in villagers:
        if v.tile == (x, y) or (v.moving and v.to == (x, y)):
            return v
    return None


def village_of_sign(x, y):
    for v in getattr(current_area, "villages", ()):
        if v["sign"] == (x, y):
            return v
    return None


# ---------------------------------------------------------------- quests

def _quest_options(taken):
    opts = []
    for t in ENEMY_TYPES:
        opts.append((7.0, "hunt", t["name"]))
    for el in tier1_elements:
        opts.append((4.0, "element", el))
    opts.append((12.0, "boss", None))
    opts.append((12.0, "grass", None))
    caves = [aid for aid, a in stage_areas.items()
             if a.kind == "cave" and sum(1 for e in area_enemies.get(aid, ()) if e.alive) >= 2]
    for aid in caves:
        opts.append((12.0 / len(caves), "cave", aid))
    duns = [aid for aid, a in stage_areas.items() if a.kind == "dungeon" and not dungeon_state(a)["done"]]
    for aid in duns:
        opts.append((9.0 / len(duns), "dungeon", aid))
    return [o for o in opts if (o[1], o[2]) not in taken]


def _quest_reward(kind, n, tier=None):
    tier = tier or current_stage
    weight = {"boss": 4, "dungeon": 7, "cave": n + 1}.get(kind, n)
    # a kill is worth 5 XP and a level costs 10 x level, so a job pays about 2-5 kills' worth
    xp = int((4 + 3 * weight) * (1 + 0.5 * (tier - 1)))
    big = kind in ("boss", "dungeon")
    r = random.random()
    if kind == "dungeon" or r < 0.4:
        base = roll_chest_rarity(tier, player_stats.get("luck", 0))
        idx = min(len(CHEST_RARITIES) - 1, CHEST_RARITIES.index(base) + (2 if big else 1))
        return {"xp": xp, "kind": "item", "rarity": CHEST_RARITIES[idx]}
    if r < 0.75:
        return {"xp": xp, "kind": "spins", "amount": 3 + tier + (3 if big else 0)}
    return {"xp": xp, "kind": "points", "amount": 2 if big else 1}


def reward_text(rw):
    extra = {"item": f"a {rw.get('rarity')} item",
             "spins": f"{rw.get('amount')} Reroll Spins",
             "points": f"{rw.get('amount')} Stat Point{'s' if rw.get('amount') != 1 else ''}"}[rw["kind"]]
    return f"{rw['xp']} XP  +  {extra}"


def make_quest(giver, village, taken):
    opts = _quest_options(taken)
    if not opts:
        return None
    _w, kind, target = random.choices(opts, weights=[o[0] for o in opts])[0]
    taken.add((kind, target))
    if kind == "hunt":
        n = random.randint(2, 4)
        pl = _PLURAL.get(target, target + "s")
        title, objective = f"Thin the {pl}", f"Defeat {n} {pl}"
        pitch = random.choice((
            f"{pl} have been raiding our stores at night. Could you thin their numbers? Defeat {n} of them.",
            f"I can't take my cart out with all these {pl} about. Put {n} of them down for me, would you?",
            f"My brother was chased home by {pl} again. Teach them a lesson — {n} ought to do it."))
    elif kind == "element":
        n = random.randint(2, 4)
        title, objective = f"{target} Unrest", f"Defeat {n} {target}-family foes"
        pitch = (f"Something has stirred up the {target}-touched beasts out there. Put down {n} of them "
                 f"before they reach our fields.")
    elif kind == "boss":
        n = 1
        title, objective = "Head of the Pack", "Defeat a boss foe"
        pitch = "A great brute leads the beasts around here. Bring a boss down and the rest will scatter."
    elif kind == "grass":
        n = random.randint(2, 3)
        title, objective = "Trouble in the Grass", f"Defeat {n} wild foes from tall grass"
        pitch = (f"Our children can't play in the meadows — things leap out of the tall grass! "
                 f"Flush out {n} of them and see them off.")
    elif kind == "cave":
        n = 2
        name = stage_areas[target].name
        title, objective = f"Clear the {name}", f"Defeat {n} foes in the {name}"
        pitch = f"Our miners won't go near the {name} any more. Something lives down there. Defeat {n} of them."
    else:
        n = 1
        name = stage_areas[target].name
        title, objective = f"Conquer the {name}", f"Clear every room of the {name}"
        pitch = f"The old {name} has woken. Fight through every room of it and break its hold on this land."
    _quest_ids[0] += 1
    return {"id": _quest_ids[0], "kind": kind, "target": target, "count": n, "progress": 0,
            "title": title, "objective": objective, "pitch": pitch,
            "reward": _quest_reward(kind, n, world_tier_at(*village["plaza"], stage_areas.get("overworld"))),
            "giver": giver.name, "village": village["name"], "status": "offer", "stage": current_stage}


def active_quests():
    return [q for q in quest_log if q["status"] in ("active", "ready")]


def _quest_note(title, msg, sub, color, ms=CHEST_TOAST_MS):
    _quest_notices.append((title, msg, sub, color, ms))


def _quest_advance(q, amount=1):
    q["progress"] = min(q["count"], q["progress"] + amount)
    if q["progress"] >= q["count"]:
        q["status"] = "ready"
        _quest_note("Quest Complete", q["title"], f"Return to {q['giver']} in {q['village']}", GRIM_XP)
        print(f"Quest ready: {q['title']}")
    else:
        _quest_note("Quest Progress", q["title"], f"{q['objective']}: {q['progress']}/{q['count']}",
                    GRIM_CREAM, ms=1800)


def quest_note_kill(e):
    """A foe fell: count it toward any quest it fits."""
    aid = current_area.id if current_area is not None else ""
    for q in quest_log:
        if q["status"] != "active":
            continue
        k = q["kind"]
        if ((k == "hunt" and getattr(e, "base_name", e.name) == q["target"])
                or (k == "element" and matchup_key(e.element) == q["target"])
                or (k == "boss" and e.is_boss)
                or (k == "grass" and getattr(e, "wild", False))
                or (k == "cave" and aid == q["target"])):
            _quest_advance(q)


def quest_note_dungeon(area_id):
    for q in quest_log:
        if q["status"] == "active" and q["kind"] == "dungeon" and q["target"] == area_id:
            _quest_advance(q)


def grant_quest_reward(q):
    """Pay out a finished quest. Returns the reward lines for the banner."""
    rw = q["reward"]
    parts = [f"+{rw['xp']} XP"]
    if rw["kind"] == "item":
        if len(player_stats["inventory"]) >= ITEM_GRID_ROWS * ITEM_GRID_COLS:
            player_stats["reroll_spins"] += 3
            parts.append("+3 spins (satchel full)")
        else:
            item = roll_chest_loot(rw["rarity"], player_stats["element"])
            if item:
                player_stats["inventory"].append(item)
                parts.append(f"{item.get('rarity', rw['rarity'])} {item['name']}")
            else:
                player_stats["reroll_spins"] += 3
                parts.append("+3 spins")
    elif rw["kind"] == "spins":
        player_stats["reroll_spins"] += rw["amount"]
        parts.append(f"+{rw['amount']} spins")
    else:
        player_stats["stat_points"] += rw["amount"]
        parts.append(f"+{rw['amount']} stat point{'s' if rw['amount'] != 1 else ''}")
    player_stats["xp"] += rw["xp"]
    check_for_level_up()
    q["status"] = "done"
    q["done_day"] = _world_day[0]
    print(f"Quest rewarded: {q['title']} -> {', '.join(parts)}")
    return parts


def settle_quests_for_new_stage():
    """Moving on: finished jobs are paid by courier, unfinished ones are lost."""
    delivered = [q for q in quest_log if q["status"] == "ready"]
    for q in delivered:
        grant_quest_reward(q)
    lost = 0
    for q in quest_log:
        if q["status"] == "active":
            q["status"] = "failed"
            lost += 1
    if delivered:
        _quest_note("Rewards Delivered", f"{len(delivered)} finished quest{'s' if len(delivered) != 1 else ''}",
                    "A courier caught up with you on the road.", GRIM_XP)
    if lost:
        _quest_note("Quests Abandoned", f"{lost} unfinished quest{'s' if lost != 1 else ''}",
                    "They stayed behind with the last stage.", GRIM_WARN)


def spawn_villagers():
    """Fill this stage's villages with folk; a few of them have a job for you."""
    global villagers
    villagers = []
    over = stage_areas.get("overworld")
    if over is None:
        return
    names = random.sample(_VILLAGER_NAMES, len(_VILLAGER_NAMES))
    for v in over.villages:
        v["walkset"] = set(v["walk"])
        n = min(len(v["walk"]), len(v["houses"]) + random.randint(1, 2))
        spots = random.sample(v["walk"], n)
        givers = min(n, random.randint(*QUEST_GIVERS))
        taken = set()
        for i, t in enumerate(spots):
            vil = Villager(names.pop() if names else "Villager", t, v, _villager_look())
            if i < givers:
                vil.quest = make_quest(vil, v, taken)
            villagers.append(vil)
    print(f"Villages: {', '.join(v['name'] for v in over.villages) or 'none'} — {len(villagers)} villagers, "
          f"{sum(1 for v in villagers if v.quest)} with quests")


def update_villagers():
    if current_area is None or current_area.id != "overworld":
        return
    here, going = _pm["tile"], player_tile()
    for v in villagers:
        if v.moving:
            v.t += VILLAGER_SPEED * dt
            if v.t >= 1.0:
                v.moving, v.t, v.tile, v.frm = False, 0.0, v.to, v.to
            continue
        v.timer -= dt
        if v.timer > 0:
            continue
        v.timer = random.uniform(*VILLAGER_IDLE)
        d = random.choice(("down", "left", "right", "up"))
        v.facing = d
        if random.random() < 0.35:
            continue                                     # just looks around
        dx, dy = _DIR_VEC[d]
        nt = (v.tile[0] + dx, v.tile[1] + dy)
        if nt not in v.village["walkset"] or nt in (here, going) or not current_area.walkable(*nt):
            continue
        if villager_at(*nt) or any((c.map_x, c.map_y) == nt for c in chests):
            continue
        v.frm, v.to, v.t, v.moving = v.tile, nt, 0.0, True
        v.steps += 1


def talk_to(v):
    """Start a conversation with a villager: chatter, a job offer, or the reward."""
    back = {"up": "down", "down": "up", "left": "right", "right": "left"}
    v.facing = back[_pm["facing"]]
    q = v.quest
    vname = v.village["name"]
    if q is None:
        open_dialogue(v.name, [v.line], npc=v)
    elif q["status"] == "offer":
        if len(active_quests()) >= QUEST_MAX_ACTIVE:
            open_dialogue(v.name, [f"You look like you've your hands full already. Finish some of your other "
                                   f"work and come back — the job will keep."], npc=v)
            return

        def answer(i, q=q):
            if i == 0:
                q["status"] = "active"
                q["stage"] = current_stage
                quest_log.append(q)
                show_notice("Quest Accepted", q["title"], q["objective"], GRIM_GOLD_BRIGHT)
                print(f"Quest accepted: {q['title']} ({q['objective']})")
            else:
                show_notice(v.name, "Maybe another time, then.", "", GRIM_CREAM_DIM, ms=1800)
        open_dialogue(v.name, [f"Ah, a traveller! Welcome to {vname}.", q["pitch"],
                               f"Do this for me and I'll give you {reward_text(q['reward'])}."],
                      choices=["Accept", "Decline"], on_choice=answer, npc=v)
    elif q["status"] == "active":
        open_dialogue(v.name, [f"How goes it? {q['objective']} — {q['progress']} of {q['count']} so far."], npc=v)
    elif q["status"] == "ready":
        def pay(q=q):
            parts = grant_quest_reward(q)
            show_notice("Quest Complete!", q["title"], "  ·  ".join(parts), GRIM_XP)
        open_dialogue(v.name, ["You did it! I knew you were the one for the job.",
                               f"As promised — {reward_text(q['reward'])}. {vname} won't forget this."],
                      on_done=pay, npc=v)
    else:
        open_dialogue(v.name, [f"Thank you again, traveller. {vname} is safer for your work."], npc=v)


def facing_interactable():
    """What the player could talk to or read right now: (verb, name) or None."""
    if current_area is None or _pm["moving"] or _pm["busy"]:
        return None
    dx, dy = _DIR_VEC[_pm["facing"]]
    x, y = _pm["tile"][0] + dx, _pm["tile"][1] + dy
    v = villager_at(x, y)
    if v:
        return ("Talk to", v.name)
    if current_area.objects.get((x, y)) == "sign":
        return ("Read", "the signpost")
    if current_area.objects.get((x, y)) == "shrine":
        return ("Save at", "the shrine")
    return None


# ---------------------------------------------------------------- dialogue box

def open_dialogue(name, pages, choices=None, on_choice=None, on_done=None, npc=None):
    global game_state
    _dlg.update(name=name, pages=list(pages), page=0, shown=0.0, choices=choices, sel=0,
                on_choice=on_choice, on_done=on_done, npc=npc)
    _pm["held"] = []
    game_state = STATE_DIALOGUE


def _dlg_text():
    return _dlg["pages"][_dlg["page"]] if _dlg["pages"] else ""


def _dlg_choosing():
    return (_dlg["choices"] and _dlg["page"] == len(_dlg["pages"]) - 1
            and _dlg["shown"] >= len(_dlg_text()))


def _close_dialogue():
    global game_state
    if game_state == STATE_DIALOGUE:
        game_state = STATE_EXPLORE


def dialogue_choose(i):
    cb = _dlg["on_choice"]
    _close_dialogue()
    if cb:
        cb(i)


def dialogue_advance():
    if _dlg["shown"] < len(_dlg_text()):
        _dlg["shown"] = float(len(_dlg_text()))          # finish typing the page first
        return
    if _dlg_choosing():
        dialogue_choose(_dlg["sel"])
        return
    if _dlg["page"] < len(_dlg["pages"]) - 1:
        _dlg["page"] += 1
        _dlg["shown"] = 0.0
        return
    cb = _dlg["on_done"]
    _close_dialogue()
    if cb:
        cb()


def handle_dialogue_event(event):
    k = event.key
    if _dlg_choosing():
        if k in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
            _dlg["sel"] = 0
        elif k in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
            _dlg["sel"] = 1
        elif k == pygame.K_y:
            dialogue_choose(0)
        elif k in (pygame.K_n, pygame.K_ESCAPE):
            dialogue_choose(len(_dlg["choices"]) - 1)
        elif k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
            dialogue_choose(_dlg["sel"])
        return
    if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
        dialogue_advance()
    elif k == pygame.K_ESCAPE:
        if _dlg["choices"]:
            dialogue_choose(len(_dlg["choices"]) - 1)
        else:
            _dlg["page"] = len(_dlg["pages"]) - 1
            _dlg["shown"] = float(len(_dlg_text()))
            dialogue_advance()


def update_dialogue():
    _dlg["shown"] = min(float(len(_dlg_text())), _dlg["shown"] + dt * DIALOGUE_CPS)


def draw_dialogue():
    begin_click_frame()
    W, H = SCREEN_WIDTH, SCREEN_HEIGHT
    box = pygame.Rect(20, H - 154, W - 40, 134)
    draw_panel(screen, box, border_radius=8, alpha=242)
    add_click(box, pygame.K_RETURN, hover=None)
    tag_w = font.size(_dlg["name"])[0] + 36
    tag = pygame.Rect(box.left + 18, box.top - 30, tag_w, 34)
    draw_panel(screen, tag, border_radius=6, alpha=250, filigree=False)
    draw_text(_dlg["name"], font, GRIM_GOLD_BRIGHT, screen, tag.centerx, tag.centery, center=True)
    text = _dlg_text()[:int(_dlg["shown"])]
    f = font
    lines = wrap_text(_dlg_text(), f, box.width - 56)
    if len(lines) > 4:
        f = small_font
        lines = wrap_text(_dlg_text(), f, box.width - 56)
    # type the visible part out over the full page's line breaks, so words don't jump
    shown, y = len(text), box.top + 22
    for line in lines:
        part = line[:max(0, shown)]
        shown -= len(line) + 1
        draw_text(part, f, GRIM_CREAM, screen, box.left + 28, y)
        y += f.get_height() + 4
    now = pygame.time.get_ticks() / 1000.0
    done = _dlg["shown"] >= len(_dlg_text())
    if done and not _dlg_choosing() and int(now * 2.5) % 2 == 0:
        cx, cy = box.right - 30, box.bottom - 22
        pygame.draw.polygon(screen, GRIM_GOLD_BRIGHT, [(cx - 7, cy - 4), (cx + 7, cy - 4), (cx, cy + 4)])
    if _dlg_choosing():
        opts = _dlg["choices"]
        cw = 190
        ch = 20 + 36 * len(opts)
        cbox = pygame.Rect(box.right - cw - 10, box.top - ch - 8, cw, ch)
        draw_panel(screen, cbox, border_radius=6, alpha=248, filigree=False)
        for i, label in enumerate(opts):
            r = pygame.Rect(cbox.left + 10, cbox.top + 10 + i * 36, cw - 20, 32)
            hot = i == _dlg["sel"] or is_hovered(r)
            if hot:
                pygame.draw.rect(screen, darken(GRIM_GOLD, 0.55), r, border_radius=5)
                pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, r, width=1, border_radius=5)
            key = "Y" if i == 0 else "N"
            draw_text(f"{'>' if i == _dlg['sel'] else ' '} {label}", font,
                      GRIM_GOLD_BRIGHT if hot else GRIM_CREAM, screen, r.left + 10, r.centery - font.get_height() // 2)
            draw_text(f"[{key}]", xp_font, GRIM_CREAM_FAINT, screen, r.right - 30, r.centery - xp_font.get_height() // 2)
            add_click(r, pygame.K_y if i == 0 else pygame.K_n, hover=None)


# ---------------------------------------------------------------- quest log ([P])

def open_quest_log():
    global game_state
    if game_state == STATE_EXPLORE and not _pm["busy"]:
        _pm["held"] = []
        _qlog.update(sel=0, confirm=False)
        game_state = STATE_QUESTS


def close_quest_log():
    global game_state
    if game_state == STATE_QUESTS:
        game_state = STATE_EXPLORE


def quest_log_entries():
    order = {"ready": 0, "active": 1, "done": 2}
    cur = [q for q in quest_log if q.get("stage") == current_stage and q["status"] in order
           and not (GAME_MODE == "openworld" and q["status"] == "done" and q.get("done_day") != _world_day[0])]
    return sorted(cur, key=lambda q: (order[q["status"]], q["id"]))


def abandon_quest(q):
    """Hand a job back: it can be taken up again from the villager who gave it."""
    if q in quest_log and q["status"] == "active":
        quest_log.remove(q)
        q["status"], q["progress"] = "offer", 0
        show_notice("Quest Abandoned", q["title"], f"{q['giver']} still needs the help.", GRIM_WARN)


def handle_quest_event(event):
    k = event.key
    entries = quest_log_entries()
    if k in (pygame.K_p, pygame.K_ESCAPE):
        close_quest_log()
    elif k in (pygame.K_UP, pygame.K_w) and entries:
        _qlog.update(sel=(_qlog["sel"] - 1) % len(entries), confirm=False)
    elif k in (pygame.K_DOWN, pygame.K_s) and entries:
        _qlog.update(sel=(_qlog["sel"] + 1) % len(entries), confirm=False)
    elif k == pygame.K_x and entries:
        q = entries[min(_qlog["sel"], len(entries) - 1)]
        if q["status"] != "active":
            return
        if _qlog["confirm"]:
            abandon_quest(q)
            _qlog.update(sel=0, confirm=False)
        else:
            _qlog["confirm"] = True


def _progress_bar(rect, ratio, col):
    pygame.draw.rect(screen, (24, 18, 12), rect, border_radius=3)
    fill = rect.copy()
    fill.width = int(rect.width * max(0.0, min(1.0, ratio)))
    if fill.width > 0:
        pygame.draw.rect(screen, col, fill, border_radius=3)
    pygame.draw.rect(screen, GRIM_GOLD_DEEP, rect, width=1, border_radius=3)


def draw_quest_log():
    shade_ = _view_cache.get(("map_dim", SCREEN_WIDTH, SCREEN_HEIGHT))
    if shade_ is None:
        shade_ = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); shade_.fill((6, 5, 10)); shade_.set_alpha(190)
        _view_cache[("map_dim", SCREEN_WIDTH, SCREEN_HEIGHT)] = shade_
    screen.blit(shade_, (0, 0))
    begin_click_frame()
    rect = pygame.Rect(24, 20, SCREEN_WIDTH - 48, SCREEN_HEIGHT - 40)
    draw_panel(screen, rect, border_radius=8, alpha=238)
    draw_heading("Quest Log", title_font, GRIM_GOLD_BRIGHT, screen, rect.centerx, rect.top + 26, spacing=4)
    over = stage_areas.get("overworld")
    vnames = ", ".join(v["name"] for v in getattr(over, "villages", ())) or "none"
    draw_text(fit_text(f"Active {len(active_quests())}/{QUEST_MAX_ACTIVE}   ·   Villages this stage: {vnames}",
                       small_font, rect.width - 60), small_font, GRIM_CREAM, screen, rect.centerx, rect.top + 58, center=True)
    close = pygame.Rect(rect.right - 126, rect.top + 12, 112, 26)
    draw_panel(screen, close, border_radius=5, alpha=220, filigree=False)
    draw_text("Close  [P]", small_font, GRIM_GOLD if is_hovered(close) else GRIM_CREAM, screen, close.centerx,
              close.centery, center=True)
    add_click(close, pygame.K_p, tip="Close the quest log  [P]")

    entries = quest_log_entries()
    sel = min(_qlog["sel"], len(entries) - 1) if entries else 0
    _qlog["sel"] = sel
    lst = pygame.Rect(rect.left + 18, rect.top + 80, 300, rect.height - 130)
    det = pygame.Rect(lst.right + 14, lst.top, rect.right - lst.right - 32, lst.height)
    draw_panel(screen, lst, border_radius=6, alpha=200, glow=False, filigree=False)
    draw_panel(screen, det, border_radius=6, alpha=200, glow=False, filigree=False)
    if not entries:
        y = lst.top + 18
        for line in wrap_text("No quests yet. Villagers with a gold ! over their heads have work for you — "
                              "face them and press Space or E.", small_font, lst.width - 28):
            draw_text(line, small_font, GRIM_CREAM_DIM, screen, lst.left + 14, y); y += 22
    for i, q in enumerate(entries[:9]):
        r = pygame.Rect(lst.left + 8, lst.top + 8 + i * 52, lst.width - 16, 48)
        hot = i == sel
        if hot:
            pygame.draw.rect(screen, darken(GRIM_GOLD, 0.6), r, border_radius=5)
            pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, r, width=1, border_radius=5)
        col = _QUEST_STATUS_COLOR[q["status"]]
        pygame.draw.circle(screen, (0, 0, 0), (r.left + 12, r.top + 14), 6)
        pygame.draw.circle(screen, col, (r.left + 12, r.top + 14), 5)
        draw_text(fit_text(q["title"], small_font, r.width - 34), small_font, GRIM_GOLD_BRIGHT if hot else GRIM_CREAM,
                  screen, r.left + 24, r.top + 5)
        if q["status"] == "done":
            draw_text("Finished", xp_font, GRIM_WARD, screen, r.left + 24, r.top + 28)
        else:
            _progress_bar(pygame.Rect(r.left + 24, r.top + 30, r.width - 90, 10), q["progress"] / q["count"], col)
            draw_text(f"{q['progress']}/{q['count']}", xp_font, col, screen, r.right - 56, r.top + 26)
        add_click(r, lambda i=i: _qlog.update(sel=i, confirm=False), hover=None)

    if entries:
        q = entries[sel]
        x, y, w = det.left + 18, det.top + 14, det.width - 36
        draw_text(fit_text(q["title"], font, w), font, GRIM_GOLD_BRIGHT, screen, x, y); y += 34
        draw_text(f"From {q['giver']} of {q['village']}", small_font, GRIM_CREAM_DIM, screen, x, y); y += 30
        col = _QUEST_STATUS_COLOR[q["status"]]
        draw_text("Objective", xp_font, GRIM_GOLD, screen, x, y); y += 18
        draw_text(fit_text(q["objective"], small_font, w), small_font, GRIM_CREAM, screen, x, y); y += 24
        _progress_bar(pygame.Rect(x, y, w - 70, 12), q["progress"] / q["count"], col)
        draw_text(f"{q['progress']}/{q['count']}", small_font, col, screen, x + w - 60, y - 4); y += 28
        draw_text("Reward", xp_font, GRIM_GOLD, screen, x, y); y += 18
        draw_text(fit_text(reward_text(q["reward"]), small_font, w), small_font, GRIM_XP, screen, x, y); y += 30
        draw_text("Status", xp_font, GRIM_GOLD, screen, x, y); y += 18
        draw_text(_QUEST_STATUS_TEXT[q["status"]] if q["status"] != "ready"
                  else f"Complete — return to {q['giver']} in {q['village']}", small_font, col, screen, x, y); y += 34
        for line in wrap_text(f"“{q['pitch']}”", small_font, w)[:5]:
            draw_text(line, small_font, GRIM_CREAM_FAINT, screen, x, y); y += 21
        if q["status"] == "active":
            hint = "Press X again to abandon this quest" if _qlog["confirm"] else "[X] Abandon quest"
            ab = pygame.Rect(det.left + 18, det.bottom - 40, small_font.size(hint)[0] + 24, 28)
            draw_panel(screen, ab, border_radius=5, alpha=220, filigree=False,
                       border_color=GRIM_BAD if _qlog["confirm"] else None)
            draw_text(hint, small_font, GRIM_BAD if _qlog["confirm"] else GRIM_CREAM, screen, ab.centerx, ab.centery,
                      center=True)
            add_click(ab, pygame.K_x, hover=None)
    old = [q for q in quest_log if q.get("stage") != current_stage]
    foot = "[Up/Down] Select   [X] Abandon   [P] Close"
    if old:
        n_done = sum(1 for q in old if q["status"] == "done")
        foot += f"      Earlier stages: {n_done} finished, {len(old) - n_done} failed"
    draw_text(fit_text(foot, small_font, rect.width - 40), small_font, GRIM_CREAM_FAINT, screen, rect.centerx,
              rect.bottom - 24, center=True)
    draw_text("Finished quests are paid out if you leave the stage; unfinished ones are lost.", xp_font,
              GRIM_CREAM_FAINT, screen, rect.centerx, rect.bottom - 44, center=True)


def draw_quest_tracker():
    """Top right: the quests you're carrying, at a glance."""
    qs = active_quests()
    if not qs:
        return
    qs = sorted(qs, key=lambda q: (q["status"] != "ready", q["id"]))[:3]
    w = 236
    h = 30 + 40 * len(qs)
    r = pygame.Rect(SCREEN_WIDTH - w - 10, 44, w, h)
    draw_panel(screen, r, border_radius=6, alpha=190, glow=False, filigree=False)
    draw_text("Quests  [P]", xp_font, GRIM_GOLD, screen, r.left + 10, r.top + 7)
    add_click(r, pygame.K_p, hover=None, tip="Open the quest log  [P]")
    for i, q in enumerate(qs):
        y = r.top + 26 + i * 40
        col = _QUEST_STATUS_COLOR[q["status"]]
        draw_text(fit_text(q["title"], small_font, w - 20), small_font, col if q["status"] == "ready" else GRIM_CREAM,
                  screen, r.left + 10, y)
        if q["status"] == "ready":
            draw_text(fit_text(f"Return to {q['giver']} ({q['village']})", xp_font, w - 20), xp_font, GRIM_XP,
                      screen, r.left + 10, y + 20)
        else:
            _progress_bar(pygame.Rect(r.left + 10, y + 23, w - 64, 8), q["progress"] / q["count"], GRIM_GOLD)
            draw_text(f"{q['progress']}/{q['count']}", xp_font, GRIM_CREAM, screen, r.right - 46, y + 18)


# ==================== Saving (Open World) ====================
# Every open-world village has a save shrine on its plaza. Saving keeps the world's seed
# (the land itself regrows exactly from it) plus everything that has changed: the hero,
# where they stand, every chest, the villagers and their quests, dungeon progress, the
# explored map and the day. "Continue" on the main menu picks the run back up.
import savegame

_world_seed = [None]
_day_offset = [0]


def _chest_record(c):
    return {"x": c.map_x, "y": c.map_y, "rarity": c.rarity, "opened": c.opened,
            "special": getattr(c, "special", False), "gear": getattr(c, "gear", False)}


def save_game():
    """Write the open-world run to the save slot. Returns True on success."""
    over = stage_areas.get("overworld")
    if GAME_MODE != "openworld" or over is None or _world_seed[0] is None:
        return False
    vindex = {id(v): i for i, v in enumerate(over.villages)}
    fog = {}
    for aid, lay in _minimap.items():
        if aid in stage_areas and "fog" in lay:
            f = lay["fog"]
            fog[aid] = {"size": f.get_size(), "data": zlib.compress(_img_tobytes(f, "RGBA"), 6),
                        "visited": set(lay.get("visited", ()))}
    tx, ty = player_tile()
    data = {
        "mode": "openworld",
        "seed": _world_seed[0],
        "player": copy.deepcopy(player_stats),
        "creation": {k: (dict(v) if isinstance(v, dict) else v) for k, v in _creation.items()},
        "where": (current_area.id, (tx, ty), _pm["facing"]),
        "chests": {aid: [_chest_record(c) for c in lst] for aid, lst in area_chests.items()},
        "villagers": [{"name": v.name, "tile": v.tile, "facing": v.facing, "look": v.look, "line": v.line,
                       "village": vindex.get(id(v.village), 0), "quest": v.quest} for v in villagers],
        "quest_log": quest_log,
        "quest_ids": _quest_ids[0],
        "dungeons": {aid: {"cleared": sorted(dungeon_state(a)["cleared"]), "done": dungeon_state(a)["done"]}
                     for aid, a in stage_areas.items() if a.kind == "dungeon"},
        "fog": fog,
        "day": _world_day[0],
    }
    here = current_area.label_at(tx, ty) if current_area is not None else ""
    meta = {"mode": "openworld", "level": player_stats["level"], "race": player_stats.get("race") or "",
            "class": player_stats.get("class") or "", "element": player_stats.get("element") or "",
            "location": here, "day": _world_day[0], "saved_at": time.strftime("%Y-%m-%d %H:%M")}
    try:
        savegame.write(data, meta)
    except Exception as e:                          # disk full, permissions, …
        print(f"Save failed: {e}")
        show_notice("Save Failed", "The shrine flickers", str(e)[:60], GRIM_BAD)
        return False
    print(f"Saved: Level {meta['level']} at {here}, day {meta['day']} (seed {_world_seed[0]})")
    return True


def load_game():
    """Rebuild the saved open world and put the hero back where they saved. False if there
    is no usable save."""
    global game_state
    data = savegame.read()
    if not data or data.get("mode") != "openworld":
        return False
    set_game_mode("openworld")
    _loading.update(title="Returning to the World")
    reset_game(seed=data["seed"])                  # the same seed grows the same land
    over = stage_areas["overworld"]
    # the hero
    player_stats.clear()
    player_stats.update(copy.deepcopy(data["player"]))
    _creation.update(data.get("creation", {}))
    # chests: drop the freshly rolled ones, put back the saved ones as they were
    for aid, lst in area_chests.items():
        a = stage_areas[aid]
        for c in lst:
            a.solid[c.map_y][c.map_x] = 1 if (a.ground[c.map_y][c.map_x] in worldgen.SOLID_GROUND
                                              or (c.map_x, c.map_y) in a.objects) else 0
        lst.clear()
    for aid, recs in data["chests"].items():
        a = stage_areas.get(aid)
        if a is None:
            continue
        for r in recs:
            c = Chest(r["x"], r["y"], r["rarity"])
            c.opened = r["opened"]
            if r.get("special"):
                c.special = True
            if r.get("gear"):
                c.gear = True
            area_chests.setdefault(aid, []).append(c)
            a.solid[r["y"]][r["x"]] = 1
    # foes never stand on a chest
    for aid, lst in area_enemies.items():
        taken = {(c.map_x, c.map_y) for c in area_chests.get(aid, ())}
        lst[:] = [e for e in lst if (e.map_x, e.map_y) not in taken]
    # villagers and their quests (the quest dicts are shared with the log, as when saved)
    quest_log[:] = data["quest_log"]
    _quest_ids[0] = data.get("quest_ids", _quest_ids[0])
    villagers.clear()
    for r in data["villagers"]:
        if r["village"] >= len(over.villages):
            continue
        v = Villager(r["name"], tuple(r["tile"]), over.villages[r["village"]], r["look"])
        v.facing, v.line, v.quest = r["facing"], r["line"], r["quest"]
        villagers.append(v)
    # dungeons: rooms already won stay open; a conquered dungeon keeps its way home
    for aid, st_ in data["dungeons"].items():
        a = stage_areas.get(aid)
        if a is None:
            continue
        st = dungeon_state(a)
        st["cleared"] = set(st_["cleared"])
        for r in st["cleared"]:
            _set_door(a, a.rooms[r]["back"], True)
            _set_door(a, a.rooms[r]["door"], True)
        if st_["done"]:
            st["done"] = True
            a.portals[a.final_exit] = a.portals[a.entry]
    # the explored map
    for aid, f in data.get("fog", {}).items():
        if aid in stage_areas:
            lay = _minimap_layers(stage_areas[aid])
            lay["fog"] = _img_frombytes(zlib.decompress(f["data"]), tuple(f["size"]), "RGBA")
            lay["visited"] = set(f.get("visited", ()))
    # the day
    _day_offset[0] = 0
    _day_offset[0] = data.get("day", 1) - world_day()
    _world_day[0] = world_day()
    # and the hero, back where they stood
    aid, tile, facing = data["where"]
    if aid not in stage_areas:
        aid, tile, facing = "overworld", over.start, "down"
    switch_area(aid, tuple(tile), facing)
    game_state = STATE_EXPLORE
    show_notice("Welcome Back", f"Day {_world_day[0]}", f"Level {player_stats['level']}  ·  "
                f"{current_area.label_at(*player_tile())}", GRIM_GOLD_BRIGHT)
    print(f"Loaded the saved world (seed {data['seed']}), day {_world_day[0]}")
    return True


def shrine_heal():
    """The shrine's light restores the hero: full HP, and mana back up to full (an
    overcharge above the cap is kept). Returns True if anything was restored."""
    hp0, mp0 = player_stats["hp"], player_stats["mana"]
    player_stats["hp"] = max(player_stats["hp"], player_stats["max_hp"])
    player_stats["mana"] = max(player_stats["mana"], player_stats["max_mana"])
    return player_stats["hp"] != hp0 or player_stats["mana"] != mp0


def use_shrine():
    healed = shrine_heal()                     # touching the crystal heals, save or not
    def answer(i):
        if i == 0 and save_game():
            show_notice("Game Saved", current_area.label_at(*player_tile()),
                        "Choose Continue on the main menu to pick up from here.", GRIM_WARD)
        elif healed:
            show_notice("Restored", "The shrine's light mends you", "HP and mana restored to full.", GRIM_WARD)
    first = ("Its light washes over you. HP and mana are restored." if healed
             else "A soft light hums inside the crystal.")
    open_dialogue("Save Shrine", [first, "Record your journey here?"],
                  choices=["Save", "Cancel"], on_choice=answer)


def start_from_menu(result):
    """Begin what the main menu chose: a mode, or the saved open world."""
    if result == "continue":
        if load_game():
            return
        result = "openworld"                     # no usable save: start a fresh world instead
    set_game_mode(result)
    reset_game()


# ==================== Minimap ====================
MINIMAP_REVEAL = {"overworld": 7, "cave": 5, "dungeon": 4, "chamber": 8}
_MINI_COLORS = {"grass": (86, 164, 74), "snow": (226, 234, 246), "sand": (226, 200, 136), "ash": (100, 92, 90),
                "slate": (80, 86, 110), "water": (64, 128, 210), "lava": (228, 100, 30), "ice": (170, 214, 236),
                "bridge": (150, 106, 62), "cwater": (40, 90, 126), "clava": (228, 100, 30), "cice": (170, 214, 236),
                "cobble": (172, 166, 156)}


def _minimap_layers(area):
    lay = _minimap.get(area.id)
    if lay is not None:
        return lay
    buf = bytearray(area.w * area.h * 3)
    theme = make_tiles.CAVE_THEMES.get(area.theme) if area.theme else None
    memo = {}

    def colour(g, art, grassy, obj, h):
        if g.startswith("path_"):
            c = (196, 160, 110)
        elif g == "cfloor":
            c = theme["floor"][2] if theme else (110, 104, 92)
        elif g == "cwall":
            c = make_tiles.shade(theme["top"], 1.6) if theme else (30, 28, 26)
        else:
            c = _MINI_COLORS.get(g, (90, 90, 90))
        if g in ("cliff", "stairs"):
            pal = make_tiles.CLIFF_PALETTES[art]
            c = pal[3] if g == "stairs" else pal[0]
        elif g == "waterfall":
            c = (200, 232, 255)
        if grassy:
            c = make_tiles.shade(c, 0.74)                  # tall grass: a darker patch
        if obj and obj.startswith("house_"):
            c = (176, 92, 70)                              # roofs
        elif obj:
            c = (40, 96, 48) if obj in ("tree", "pine", "bush") else make_tiles.shade(c, 0.5)
        if h and g not in _CLIFFS:
            c = make_tiles.mix(c, (255, 255, 255), 0.14 * h)   # higher = paler
        return bytes(c[:3])

    grass_kinds = worldgen.GRASS_KINDS
    objects, decor, ground, height = area.objects, area.decor, area.ground, area.height
    i = 0
    for y in range(area.h):
        row = ground[y]
        hrow = height[y] if height is not None else None
        for x in range(area.w):
            g = row[x]
            art = _art_biome(area, x, y - 1) if g in ("cliff", "stairs") else None
            obj = objects.get((x, y))
            key = (g, art, decor.get((x, y)) in grass_kinds, obj, hrow[x] if hrow else 0)
            c = memo.get(key)
            if c is None:
                c = memo[key] = colour(*key)
            buf[i:i + 3] = c
            i += 3
    col = pygame.image.frombuffer(bytes(buf), (area.w, area.h), "RGB").copy()
    fog = pygame.Surface((area.w, area.h), pygame.SRCALPHA)
    fog.fill((10, 8, 6, 255))
    lay = {"color": col, "fog": fog}
    _minimap[area.id] = lay
    return lay


def reveal_minimap():
    """Clear the fog around the player (and the whole room they stand in, in a dungeon)."""
    area = current_area
    if area is None:
        return
    fog = _minimap_layers(area)["fog"]
    tx, ty = player_tile()
    pygame.draw.circle(fog, (0, 0, 0, 0), (tx, ty), MINIMAP_REVEAL.get(area.kind, 5))
    if area.biome is not None and area.in_bounds(tx, ty):
        vis = _minimap_layers(area).setdefault("visited", set())
        vis.add(area.biome[ty][tx])
        names = getattr(area, "region_names", None)
        if names is not None:                       # each region of the open world on its own
            vis.add(names[area.region_map[ty, tx]])
    if area.kind == "dungeon":
        r = area.room_at(tx, ty)
        if r is not None:
            x0, y0, x1, y1 = area.rooms[r]["rect"]
            pygame.draw.rect(fog, (0, 0, 0, 0), (x0 - 1, y0 - 1, x1 - x0 + 3, y1 - y0 + 3))


def _seen(area, x, y):
    fog = _minimap_layers(area)["fog"]
    return 0 <= x < area.w and 0 <= y < area.h and fog.get_at((x, y)).a == 0


def draw_minimap(top):
    """The explored map of the current area under the HUD card."""
    area = current_area
    if area is None:
        return
    rect = pygame.Rect(10, top, 230, 158)
    draw_panel(screen, rect, border_radius=6, alpha=200, filigree=False)
    name = area.name if area.kind != "overworld" else f"Stage {_roman(current_stage)}"
    draw_text(fit_text(name, xp_font, rect.width - 20), xp_font, GRIM_GOLD, screen, rect.left + 10, rect.top + 6)
    status = dungeon_status_text()
    inner = pygame.Rect(rect.left + 8, rect.top + 24, rect.width - 16, rect.height - (48 if status else 32))
    lay = _minimap_layers(area)
    comp = lay["color"].copy()
    comp.blit(lay["fog"], (0, 0))
    k = min(inner.width / area.w, inner.height / area.h)
    size = (max(1, int(area.w * k)), max(1, int(area.h * k)))
    ox, oy = inner.centerx - size[0] // 2, inner.centery - size[1] // 2
    screen.blit(pygame.transform.scale(comp, size), (ox, oy))
    pygame.draw.rect(screen, GRIM_GOLD_DEEP, (ox - 1, oy - 1, size[0] + 2, size[1] + 2), 1)

    def dot(x, y, col, r=2):
        pygame.draw.circle(screen, col, (int(ox + (x + 0.5) * k), int(oy + (y + 0.5) * k)), r)

    for (x, y), (target, _d, _f) in area.portals.items():
        if _seen(area, x, y):
            col = (230, 190, 255) if target.startswith("cave_") else (
                GRIM_GOLD_BRIGHT if target.startswith("dungeon_") else (255, 244, 200))
            dot(x, y, (0, 0, 0), 4); dot(x, y, col, 3)
    if area.kind == "dungeon":
        for (x, y) in area.doors:
            if area.solid[y][x] and _seen(area, x, y):
                dot(x, y, GRIM_BAD, 2)
    for c in chests:
        if not c.opened and _seen(area, c.map_x, c.map_y):
            dot(c.map_x, c.map_y, (255, 214, 60), 2)
    px, py = player_tile()
    for e in enemies:
        if e.alive and abs(e.map_x - px) + abs(e.map_y - py) <= MINIMAP_REVEAL.get(area.kind, 5) + 2:
            dot(e.map_x, e.map_y, (230, 60, 50), 2)
    blink = int(pygame.time.get_ticks() / 350) % 2
    dot(px, py, (0, 0, 0), 4)
    dot(px, py, (255, 255, 255) if blink else GRIM_GOLD_BRIGHT, 3)
    if status:
        draw_text(fit_text(status, xp_font, rect.width - 20), xp_font, GRIM_CREAM, screen, rect.centerx,
                  rect.bottom - 14, center=True)


# ==================== Full map ====================
# [Tab] in the field opens the explored map of the current area full-screen; the world is
# paused behind it. [Tab] or [Esc] closes it.

def open_full_map():
    global game_state
    if game_state == STATE_EXPLORE and not _pm["busy"] and current_area is not None:
        _pm["held"] = []
        game_state = STATE_MAP


def close_full_map():
    global game_state
    if game_state == STATE_MAP:
        game_state = STATE_EXPLORE


def draw_full_map():
    area = current_area
    if area is None:
        return
    shade_ = _view_cache.get(("map_dim", SCREEN_WIDTH, SCREEN_HEIGHT))
    if shade_ is None:
        shade_ = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); shade_.fill((6, 5, 10)); shade_.set_alpha(190)
        _view_cache[("map_dim", SCREEN_WIDTH, SCREEN_HEIGHT)] = shade_
    screen.blit(shade_, (0, 0))
    begin_click_frame()                        # the frozen HUD underneath is not clickable
    rect = pygame.Rect(24, 20, SCREEN_WIDTH - 48, SCREEN_HEIGHT - 40)
    draw_panel(screen, rect, border_radius=8, alpha=235)
    title = area.name if area.kind != "overworld" else (
        "The Open World" if GAME_MODE == "openworld" else f"Stage {_roman(current_stage)}  ·  The Wilds")
    draw_heading(title, title_font if title_font.size(title)[0] < rect.width - 160 else font, GRIM_GOLD_BRIGHT,
                 screen, rect.centerx, rect.top + 24, spacing=2, upper=False)
    tx, ty = player_tile()
    here = area.label_at(tx, ty)
    status = dungeon_status_text() or limitless_status_text()
    sub = here + (f"   —   {status}" if status else "")
    draw_text(fit_text(sub, small_font, rect.width - 60), small_font, GRIM_CREAM, screen, rect.centerx,
              rect.top + 58, center=True)
    close = pygame.Rect(rect.right - 126, rect.top + 12, 112, 26)
    draw_panel(screen, close, border_radius=5, alpha=220, filigree=False)
    draw_text("Close  [Tab]", small_font, GRIM_GOLD if is_hovered(close) else GRIM_CREAM, screen, close.centerx,
              close.centery, center=True)
    add_click(close, pygame.K_TAB, tip="Close the map  [Tab]")

    legend_h = 30
    inner = pygame.Rect(rect.left + 20, rect.top + 80, rect.width - 40, rect.height - 80 - legend_h - 16)
    lay = _minimap_layers(area)
    comp = lay["color"].copy()
    comp.blit(lay["fog"], (0, 0))
    k = min(inner.width / area.w, inner.height / area.h)
    if k >= 1:
        k = float(int(k)) if k >= 2 else k          # whole-pixel tiles stay crisp
    size = (max(1, int(area.w * k)), max(1, int(area.h * k)))
    ox, oy = inner.centerx - size[0] // 2, inner.centery - size[1] // 2
    pygame.draw.rect(screen, (8, 6, 10), (ox - 3, oy - 3, size[0] + 6, size[1] + 6))
    screen.blit(pygame.transform.scale(comp, size), (ox, oy))
    pygame.draw.rect(screen, GRIM_GOLD_DEEP, (ox - 3, oy - 3, size[0] + 6, size[1] + 6), 1)

    def at(x, y):
        return int(ox + (x + 0.5) * k), int(oy + (y + 0.5) * k)

    def dot(x, y, col, r=3):
        c = at(x, y)
        pygame.draw.circle(screen, (0, 0, 0), c, r + 1)
        pygame.draw.circle(screen, col, c, r)

    # region names, once you've walked in them
    plazas = [v["plaza"] for v in getattr(area, "villages", ())]
    for b, (bx, by) in getattr(area, "biome_centers", {}).items():
        if b in lay.get("visited", ()):
            name = worldgen.BIOMES[worldgen.base_biome(b)]["name"]
            cx, cy = at(bx, by)
            if any(abs(bx - px_) < 20 and abs(by - py_) < 14 for px_, py_ in plazas):
                cy = at(bx, min(py_ for px_, py_ in plazas if abs(bx - px_) < 20 and abs(by - py_) < 14) - 12)[1]
            draw_text(name, small_font, (0, 0, 0), screen, cx + 1, cy + 1, center=True)
            draw_text(name, small_font, GRIM_GOLD_BRIGHT, screen, cx, cy, center=True)
    # waterfalls and stairs worth finding
    for (x, y) in getattr(area, "waterfalls", ()):
        if _seen(area, x, y):
            dot(x, y, (200, 232, 255), 2)
    # cave mouths, dungeon gates, exits — named
    for v in getattr(area, "villages", ()):
        px_, py_ = v["plaza"]
        if _seen(area, px_, py_):
            x0, y0, x1, y1 = v["rect"]
            a0, a1 = at(x0, y0), at(x1, y1)
            pygame.draw.rect(screen, (200, 140, 90), (a0[0] - 2, a0[1] - 2, a1[0] - a0[0] + 4, a1[1] - a0[1] + 4), 1)
            cx, cy = at(px_, y1 + 1)
            cy += 8
            draw_text(v["name"], small_font, (0, 0, 0), screen, cx + 1, cy + 1, center=True)
            draw_text(v["name"], small_font, (255, 214, 160), screen, cx, cy, center=True)
    for v in getattr(area, "villages", ()):
        if v.get("shrine") and _seen(area, *v["shrine"]):
            dot(*v["shrine"], (120, 200, 255), 3)
    if area.id == "overworld":
        for vil in villagers:
            q = vil.quest
            if q and q["status"] in ("offer", "ready") and _seen(area, *vil.tile):
                dot(*vil.tile, GRIM_XP if q["status"] == "ready" else GRIM_GOLD_BRIGHT, 3)
    for (x, y), (target, _d, _f) in area.portals.items():
        if not _seen(area, x, y):
            continue
        if target.startswith("house_"):
            dot(x, y, (200, 140, 90), 2)
            continue
        if target.startswith("cave_"):
            col, label = (230, 190, 255), stage_areas[target].name if target in stage_areas else "Cave"
        elif target.startswith("dungeon_"):
            col, label = GRIM_GOLD_BRIGHT, stage_areas[target].name if target in stage_areas else "Dungeon"
        else:
            col, label = (255, 244, 200), "Exit"
        dot(x, y, col, 5)
        cx, cy = at(x, y)
        draw_text(label, xp_font, (0, 0, 0), screen, cx + 1, cy - 15, center=True)
        draw_text(label, xp_font, col, screen, cx, cy - 16, center=True)
    if area.kind == "dungeon":
        for (x, y) in area.doors:
            if _seen(area, x, y):
                dot(x, y, GRIM_BAD if area.solid[y][x] else GRIM_WARD, 3)
        if dungeon_state(area)["done"] and _seen(area, *area.final_exit):
            dot(*area.final_exit, (255, 244, 200), 5)
    for c in chests:
        if not c.opened and _seen(area, c.map_x, c.map_y):
            dot(c.map_x, c.map_y, (255, 214, 60), 3)
    for e in enemies:
        if e.alive and abs(e.map_x - tx) + abs(e.map_y - ty) <= MINIMAP_REVEAL.get(area.kind, 5) + 2:
            dot(e.map_x, e.map_y, (230, 60, 50), 3)
    # you, with a pointer the way you face
    blink = int(pygame.time.get_ticks() / 350) % 2
    cx, cy = at(tx, ty)
    dx, dy = _DIR_VEC[_pm["facing"]]
    tip = (cx + dx * 11, cy + dy * 11)
    l = (cx + dx * 4 - dy * 5, cy + dy * 4 + dx * 5)
    r = (cx + dx * 4 + dy * 5, cy + dy * 4 - dx * 5)
    pygame.draw.polygon(screen, (0, 0, 0), [tip, l, r]); pygame.draw.polygon(screen, GRIM_GOLD_BRIGHT, [tip, l, r], 0)
    pygame.draw.circle(screen, (0, 0, 0), (cx, cy), 6)
    pygame.draw.circle(screen, (255, 255, 255) if blink else GRIM_GOLD_BRIGHT, (cx, cy), 5)

    # legend
    items = [("You", (255, 255, 255)), ("Cave", (230, 190, 255)), ("Dungeon", GRIM_GOLD_BRIGHT),
             ("Chest", (255, 214, 60)), ("Foe", (230, 60, 50)), ("Waterfall", (200, 232, 255))]
    if area.kind == "overworld":
        items.append(("Stairs", make_tiles.CLIFF_PALETTES["meadow"][3]))
        items += [("Village", (200, 140, 90)), ("Quest", GRIM_GOLD_BRIGHT)]
        if any(v.get("shrine") for v in area.villages):
            items.append(("Save", (120, 200, 255)))
    widths = [small_font.size(n)[0] + 30 for n, _ in items]
    if sum(widths) > rect.width - 30:
        widths = [small_font.size(n)[0] + 20 for n, _ in items]
    lx = rect.centerx - sum(widths) // 2
    ly = rect.bottom - legend_h - 8
    for (n, col), w in zip(items, widths):
        pygame.draw.circle(screen, (0, 0, 0), (lx + 7, ly + 9), 6)
        pygame.draw.circle(screen, col, (lx + 7, ly + 9), 5)
        draw_text(n, small_font, GRIM_CREAM, screen, lx + 18, ly + 9 - small_font.get_height() // 2 + 1)
        lx += w


def update_player_movement():
    global player_x, player_y
    keys = touch_controls.keys(pygame.key.get_pressed())   # the touch stick counts as keys
    held = _pm["held"]
    for d, (k1, k2) in _DIR_KEYS.items():          # most recently pressed direction wins
        down = keys[k1] or keys[k2]
        if down and d not in held:
            held.append(d)
        elif not down and d in held:
            held.remove(d)
    want = held[-1] if held else None
    running = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
    speed = (RUN_SPEED if running else WALK_SPEED) * (PLAYER_SPEED / 1.5)
    if _pm["bump"] > 0:
        _pm["bump"] -= dt

    if not _pm["busy"]:
        if _pm["moving"]:
            _pm["t"] += (dt / LEDGE_HOP_TIME) if _pm["hop"] else speed * dt
            if _pm["t"] >= 1.0:
                left = 0.0 if _pm["hop"] else _pm["t"] - 1.0
                if _pm["hop"]:
                    _pm["landed"] = (_pm["to"], pygame.time.get_ticks() / 1000.0)
                _pm.update(moving=False, tile=_pm["to"], t=0.0, hop=False)
                if not _on_arrive() and not _grass_stir() and want and game_state == STATE_EXPLORE:
                    _pm["facing"] = want                 # already walking: turn and carry on
                    if _try_step(want):
                        _pm["t"] = min(left, 0.95)
        else:
            if _pm["turn"] > 0:
                _pm["turn"] -= dt
            if want and _pm["bump"] <= 0 and game_state == STATE_EXPLORE:
                if _pm["facing"] != want:
                    _pm["facing"] = want                 # tap: turn on the spot
                    _pm["turn"] = TURN_TAP
                elif _pm["turn"] <= 0:
                    _try_step(want)
    _pm["running"] = running and _pm["moving"]

    if _pm["moving"]:
        (fx, fy), (tx, ty) = _pm["frm"], _pm["to"]
        t = _pm["t"]
        player_x, player_y = fx + (tx - fx) * t + 0.5, fy + (ty - fy) * t + 0.5
    else:
        player_x, player_y = _pm["tile"][0] + 0.5, _pm["tile"][1] + 0.5
    announce_location(current_area.label_at(*player_tile()))
    reveal_minimap()


# --- Main Menu ---
# Run the menu inside the same pygame window; returns "limitless" or "exit".
import main_menu
from main_menu import run_menu as _run_main_menu

def _apply_video_settings_for_gameplay():
    """Read main_menu.settings (Resolution / Fullscreen / Graphics Quality, set on the
    Video Settings screen) and (re)build the game window plus every resolution-dependent
    rendering global to match. Called once after the main menu and again any time the
    player returns to the main menu mid-run and re-launches, so changes always take effect."""
    global SCREEN_WIDTH, SCREEN_HEIGHT, NUM_RAYS, RAY_ANGLE_STEP, MAX_DEPTH
    global USE_WALL_TEXTURE, ENEMY_SPRITE_SCALE_FN, is_fullscreen, screen

    SCREEN_WIDTH, SCREEN_HEIGHT = main_menu.parse_resolution(main_menu.settings["resolution"])
    is_fullscreen = main_menu.settings["fullscreen"]

    quality = main_menu.settings.get("quality", "Medium")
    if quality == "Low":
        NUM_RAYS = max(1, SCREEN_WIDTH // 2)   # half the rays: chunkier walls, ~2x faster to cast
        MAX_DEPTH = 14                          # shorter view distance: fewer DDA steps per ray
        USE_WALL_TEXTURE = False                # flat-shaded walls: skip texture sampling entirely
        ENEMY_SPRITE_SCALE_FN = pygame.transform.scale
    elif quality == "High":
        NUM_RAYS = SCREEN_WIDTH
        MAX_DEPTH = 20
        USE_WALL_TEXTURE = True
        # Enemies are pixel art — they must stay nearest-neighbour at every quality level,
        # or upscaling smears them into mush. High still gets textured walls + full draw distance.
        ENEMY_SPRITE_SCALE_FN = pygame.transform.scale
    else:  # Medium (default) — matches the game's original fixed behavior exactly
        NUM_RAYS = SCREEN_WIDTH
        MAX_DEPTH = 20
        USE_WALL_TEXTURE = True
        ENEMY_SPRITE_SCALE_FN = pygame.transform.scale
    RAY_ANGLE_STEP = FOV / NUM_RAYS

    screen = main_menu.open_window((SCREEN_WIDTH, SCREEN_HEIGHT), is_fullscreen)
    is_fullscreen = main_menu.settings["fullscreen"]   # off again if fullscreen couldn't be had

    _build_sky_backgrounds()


def _main_menu():
    """Show the main menu and return its choice. The menu may re-open the window (Fullscreen,
    F11), so pick the window's surface back up afterwards."""
    global screen
    result = _run_main_menu(screen, clock)
    screen = main_menu.current_surface()
    return result


# What the touch controls show on each screen: the stick and Use button while exploring
# (Use also moves dialogue on), and the corner button to pause or close. Everything else
# is tapped directly - the game's buttons all take clicks.
_TOUCH_CORNER = {STATE_EXPLORE: "pause", STATE_COMBAT: "pause", STATE_MAP: "close",
                 STATE_QUESTS: "close", STATE_MENU: "close", STATE_PAUSE: "close"}


def _touch_layout():
    busy = transition_active() or ascension_active()
    touch_controls.layout((SCREEN_WIDTH, SCREEN_HEIGHT),
                          stick=not busy and game_state == STATE_EXPLORE,
                          use=not busy and game_state in (STATE_EXPLORE, STATE_DIALOGUE),
                          corner=None if busy else _TOUCH_CORNER.get(game_state))


def toggle_fullscreen():
    """F11 / Alt+Enter in game: switch fullscreen at the current resolution."""
    global screen, is_fullscreen
    screen = main_menu.toggle_fullscreen((SCREEN_WIDTH, SCREEN_HEIGHT))
    is_fullscreen = main_menu.settings["fullscreen"]

_menu_result = _main_menu()
if _menu_result not in ("continue", "openworld", "limitless", "stages"):
    pygame.quit()
    sys.exit()
_menu_snapshot = main_menu.snapshot(screen)        # the menu's last frame, dissolved on the way in
_apply_video_settings_for_gameplay()


# --- Helper Functions ---
def draw_text(text, font_obj, color, surface, x, y, center=False):
    try:
        adj_x = x if not center else x - font_obj.size(text)[0] // 2; adj_y = y if not center else y - font_obj.size(text)[1] // 2
        check_x = max(0, min(adj_x, SCREEN_WIDTH - 1)); check_y = max(0, min(adj_y, SCREEN_HEIGHT - 1))
        bg_color = surface.get_at((check_x, check_y))
        if color == BLACK and (bg_color == BLACK or bg_color == DARK_GRAY): textobj = font_obj.render(text, True, WHITE)
        elif color == DARKEST_GRAY and (bg_color == BLACK or bg_color == DARK_GRAY): textobj = font_obj.render(text, True, LIGHT_GRAY)
        else: textobj = font_obj.render(text, True, color)
    except IndexError: textobj = font_obj.render(text, True, color)
    textrect = textobj.get_rect()
    if center: textrect.center = (x, y)
    else: textrect.topleft = (x, y)
    surface.blit(textobj, textrect)

def wrap_text(text, font_obj, max_width):
    """Greedy word-wrap to a pixel width."""
    lines, cur = [], ""
    for word in text.split():
        probe = (cur + " " + word).strip()
        if font_obj.size(probe)[0] <= max_width:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# ==================== Mouse / Click Regions ====================
# Every screen was keyboard-only. Rather than write a second input path per screen, each
# renderer registers the rects it draws along with what a click there should do:
#   * an int pygame key  -> replayed through the existing keyboard handlers, so a click
#                           and its hotkey can never drift apart
#   * a callable         -> for things no single key expresses (jump to a tab, pick a cell)
#   * None               -> hover/cursor only; the widget handles its own clicks
# Regions are rebuilt every frame, and the event loop runs before the next render, so a
# click is always tested against exactly what the player was looking at.
_click_regions = []            # [(rect, action, hover, tip)]
_cursor_state = [None]


def begin_click_frame():
    _click_regions.clear()


def add_click(rect, action, hover="outline", tip=None):
    """Register a clickable rect. hover: "outline" draws a gold hover frame; None leaves
    the look to the widget (e.g. draw_button, which kindles itself when hot)."""
    _click_regions.append((pygame.Rect(rect), action, hover, tip))
    return rect


def click_region_at(pos):
    for region in reversed(_click_regions):      # last drawn sits on top
        if region[0].collidepoint(pos):
            return region
    return None


def is_hovered(rect):
    return pygame.Rect(rect).collidepoint(pygame.mouse.get_pos())


def _set_cursor(hand):
    if _cursor_state[0] == hand:
        return
    _cursor_state[0] = hand
    try:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW)
    except (pygame.error, AttributeError):
        pass


def draw_click_hover(surface):
    """Hover feedback for whatever clickable is under the cursor: a hand cursor, a soft
    gold frame for plain regions, and an optional tooltip."""
    if touch_controls.seen_touch:
        return                    # on a touchscreen there's no cursor to hover with
    region = click_region_at(pygame.mouse.get_pos())
    _set_cursor(region is not None)
    if not region:
        return
    rect, _action, hover, tip = region
    if hover == "outline":
        # A frame, not a fill: the glow helpers are additive and meant to sit BEHIND a
        # widget — drawn on top they wash the hovered text out to solid gold.
        pad = 3
        halo = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
        inner = pygame.Rect(pad, pad, rect.width, rect.height)
        pygame.draw.rect(halo, (*GRIM_GOLD, 16), inner, border_radius=5)                  # faint tint
        pygame.draw.rect(halo, (*GRIM_GOLD, 60), inner.inflate(4, 4), width=1, border_radius=7)
        surface.blit(halo, (rect.x - pad, rect.y - pad))
        pygame.draw.rect(surface, GRIM_GOLD_BRIGHT, rect, width=1, border_radius=5)
    if tip:
        mx, my = pygame.mouse.get_pos()
        tw, th = small_font.size(tip)
        box = pygame.Rect(mx + 14, my + 16, tw + 16, th + 8)
        box.right = min(box.right, SCREEN_WIDTH - 4); box.bottom = min(box.bottom, SCREEN_HEIGHT - 4)
        bg = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (14, 10, 6, 235), bg.get_rect(), border_radius=4)
        surface.blit(bg, box.topleft)
        pygame.draw.rect(surface, GRIM_GOLD_DIM, box, width=1, border_radius=4)
        draw_text(tip, small_font, GRIM_CREAM, surface, box.x + 8, box.y + 4)


def click_to_event(action):
    """The KEYDOWN a key-type click region stands for."""
    return pygame.event.Event(pygame.KEYDOWN, key=action, mod=0, unicode="", scancode=0)
# ==================== end Mouse / Click Regions ====================


def fit_text(text, font_obj, max_width):
    """Truncate text with a trailing ellipsis so it fits within max_width pixels."""
    if font_obj.size(text)[0] <= max_width:
        return text
    ell = "…"
    while text and font_obj.size(text + ell)[0] > max_width:
        text = text[:-1]
    return text.rstrip() + ell

def draw_scrolling_text(surface, text, font_obj, color, x, y, max_width, phase=0.0):
    """Draw text at (x, y). If it's wider than max_width, marquee it: hold at the start,
    slide left to reveal the end, hold, slide back — all clipped to max_width so it never
    spills out. Used for long equipment names in the narrow equipment panel."""
    tw = font_obj.size(text)[0]
    if tw <= max_width:
        draw_text(text, font_obj, color, surface, x, y)
        return
    overflow = tw - max_width
    speed = 26.0      # px/sec
    pause = 1.3       # sec held at each end
    travel = overflow / speed
    total = 2 * (pause + travel)
    tt = (pygame.time.get_ticks() / 1000.0 + phase) % total
    if tt < pause:
        off = 0.0
    elif tt < pause + travel:
        off = overflow * (tt - pause) / travel
    elif tt < 2 * pause + travel:
        off = overflow
    else:
        off = overflow * (1.0 - (tt - 2 * pause - travel) / travel)
    prev = surface.get_clip()
    surface.set_clip(pygame.Rect(x, y - 2, max_width, font_obj.get_height() + 4))
    draw_text(text, font_obj, color, surface, int(x - off), y)
    surface.set_clip(prev)

def draw_heading(text, font_obj, color, surface, x, y, spacing=4, center=True, upper=True, shadow=True):
    """Grimoire chapter/panel title: uppercase serif with manual letter-spacing (tracking)
    and a soft ink shadow so it reads as carved gold-leaf."""
    if upper: text = text.upper()
    glyphs = [(ch, font_obj.render(ch, True, color)) for ch in text]
    total = sum(g.get_width() for _, g in glyphs) + spacing * max(0, len(glyphs) - 1)
    h = font_obj.get_height()
    start_x = x - total // 2 if center else x
    top_y = y - h // 2 if center else y
    if shadow:
        cx = start_x
        for ch, g in glyphs:
            sh = font_obj.render(ch, True, (0, 0, 0))
            surface.blit(sh, (cx + 2, top_y + 2))
            cx += g.get_width() + spacing
    cx = start_x
    for ch, g in glyphs:
        surface.blit(g, (cx, top_y))
        cx += g.get_width() + spacing
    return total

# --- Magic UI Helpers ---
def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color[:3])

def darken(color, amount):
    return tuple(max(0, int(c * (1 - amount))) for c in color[:3])

# Gradients and glows are drawn row by row / ring by ring, which is slow in Python (and
# much slower on a phone), but the same size and colours always give the same picture -
# so each one is made once and reused. Bounded so odd one-offs can't pile up.
_GFX_CACHE = {}
_GFX_CACHE_MAX = 600


def _gfx_cached(key, make):
    surf = _GFX_CACHE.get(key)
    if surf is None:
        if len(_GFX_CACHE) >= _GFX_CACHE_MAX:
            _GFX_CACHE.clear()
        surf = _GFX_CACHE[key] = make()
    return surf


def draw_gradient_rect(surface, rect, color_top, color_bottom, border_radius=0):
    """Vertical gradient fill inside rect, with optional rounded corners."""
    if rect.width <= 0 or rect.height <= 0:
        return
    key = ("grad", rect.width, rect.height, tuple(color_top), tuple(color_bottom), border_radius)
    surface.blit(_gfx_cached(key, lambda: _make_gradient(rect.width, rect.height, color_top,
                                                         color_bottom, border_radius)), rect.topleft)


def _make_gradient(w, h, color_top, color_bottom, border_radius):
    rect = pygame.Rect(0, 0, w, h)
    grad = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for row in range(rect.height):
        t = row / max(1, rect.height - 1)
        pygame.draw.line(grad, lerp_color(color_top, color_bottom, t), (0, row), (rect.width, row))
    if border_radius > 0:
        r = min(border_radius, rect.width // 2, rect.height // 2)
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=r)
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return grad

def draw_glow_rect(surface, rect, color, border_radius=6, layers=5, max_alpha=90, spread=8):
    """Soft additive aura behind a rect, for a magical glow feel."""
    if rect.width <= 0 or rect.height <= 0:
        return
    key = ("glow", rect.width, rect.height, tuple(color[:3]), border_radius, layers, max_alpha, spread)
    glow = _gfx_cached(key, lambda: _make_glow(rect.width, rect.height, color, border_radius,
                                               layers, max_alpha, spread))
    if surface is screen and main_menu.world_under():
        # Two-layer drawing (Android): the world isn't on this canvas for the glow to add
        # its light to, so draw the bright ring that adding would have made instead.
        ring = _gfx_cached(("glow-over", key), lambda: _glow_as_ring(glow))
        surface.blit(ring, (rect.x - spread, rect.y - spread))
        return
    surface.blit(glow, (rect.x - spread, rect.y - spread), special_flags=pygame.BLEND_RGBA_ADD)


def _glow_as_ring(glow):
    """An additive glow turned into an ordinary see-through one that looks about the same
    over the world: where the glow has any light, a lighter, mostly opaque ring."""
    import numpy as np
    w, h = glow.get_size()
    px = np.frombuffer(_img_tobytes(glow, "RGBA"), np.uint8).reshape(h, w, 4).astype(np.int32)
    # adding light ignores alpha: any pixel with colour brightens what's under it, even
    # the glow's outer band, whose alpha is 0
    # what adding it to typical ground (~(70, 110, 60)) gives, nearly opaque
    lit = px[..., :3].max(axis=2) > 0
    added = np.minimum(255, px[..., :3] + np.array([70, 110, 60]))
    px[..., :3] = np.where(lit[..., None], added, px[..., :3])
    px[..., 3] = np.where(lit, 235, 0)
    return _img_frombytes(px.astype(np.uint8).tobytes(), (w, h), "RGBA").convert_alpha()


def _make_glow(w, h, color, border_radius, layers, max_alpha, spread):
    glow_w, glow_h = w + spread * 2, h + spread * 2
    glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
    # Draw largest+faintest band first, smallest+brightest last, so the halo
    # fades outward from the object instead of washing the whole area evenly.
    for i in range(layers, 0, -1):
        frac = i / layers
        inset = int(spread * (1 - frac))
        alpha = int(max_alpha * (1 - frac) ** 2)
        band = pygame.Rect(inset, inset, glow_w - inset * 2, glow_h - inset * 2)
        pygame.draw.rect(glow, (*color[:3], alpha), band, border_radius=max(0, border_radius + spread - inset))
    return glow

def draw_filigree_corners(surface, rect, color=GRIM_GOLD, arm=14, inset=5, node=6):
    """The Grimoire corner motif: an L-bracket of two gold lines with a small
    diamond node at each of the four corners. Ties every panel together."""
    x1, y1 = rect.left + inset, rect.top + inset
    x2, y2 = rect.right - inset, rect.bottom - inset
    arm = min(arm, rect.width // 2 - inset, rect.height // 2 - inset)
    if arm < 3:
        return
    for cx, cy, sx, sy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        pygame.draw.line(surface, color, (cx, cy), (cx + sx * arm, cy), 2)
        pygame.draw.line(surface, color, (cx, cy), (cx, cy + sy * arm), 2)
        d = node // 2 + 1
        pygame.draw.polygon(surface, color, [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)])

def draw_panel(surface, rect, bg_color=None, border_color=None, border_radius=6,
               alpha=210, glow=True, glow_color=None, filigree=True):
    """Arcane Grimoire panel: umber parchment fill, aged-gold border with an inner
    hairline, a soft gold aura, and filigree corners."""
    bg_color = GRIM_PANEL if bg_color is None else bg_color
    border_color = GRIM_GOLD_DIM if border_color is None else border_color
    glow_color = glow_color or GRIM_GOLD
    if glow:
        draw_glow_rect(surface, rect, glow_color, border_radius=border_radius,
                        layers=3, max_alpha=34, spread=3)
    def _make_panel():
        p = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(p, (*bg_color, alpha), p.get_rect(), border_radius=border_radius)
        return p
    surface.blit(_gfx_cached(("panel", rect.width, rect.height, tuple(bg_color[:3]), alpha,
                              border_radius), _make_panel), rect.topleft)
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=border_radius)
    inner = rect.inflate(-6, -6)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, GRIM_GOLD_DEEP, inner, width=1,
                         border_radius=max(0, border_radius - 3))
    if filigree:
        draw_filigree_corners(surface, rect, color=GRIM_GOLD)

def draw_button(surface, rect, label, font_obj, hot=False, accent=None, upper=True):
    """A runic button: umber fill, gold border that kindles brighter when hot
    (hovered/selected). Returns the rect for hit-testing."""
    accent = accent or GRIM_GOLD
    border = GRIM_GOLD_BRIGHT if hot else GRIM_GOLD_DIM
    text_col = (255, 255, 255) if hot else GRIM_CREAM
    if hot:
        # A tight halo — the button's own panel covers the middle, so the spread IS the
        # visible glow width. 3px matches the hairline hover frames used elsewhere.
        draw_glow_rect(surface, rect, accent, border_radius=4, layers=3, max_alpha=55, spread=3)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*GRIM_PANEL2, 235), panel.get_rect(), border_radius=4)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=4)
    draw_text(label.upper() if upper else label, font_obj, text_col, surface,
              rect.centerx, rect.centery, center=True)
    return rect

def rune_side(size=32, pad=2):
    """Total footprint of a rune tile, so callers can lay text out beside it."""
    return size + pad * 2

def draw_rune(surface, center, element, size=32, pad=2, frame=True):
    """An element icon mounted in a tight square tile sized to the icon itself.

    Everything is drawn strictly inside the returned rect (no outer glow, no ring),
    so a rune can never bleed over neighbouring text such as the element name or the
    spin count. Returns the tile rect."""
    color = ELEMENT_COLORS.get(element, GRIM_GOLD)
    edge = color if sum(color[:3]) > 60 else lighten(color, 0.5)
    side = rune_side(size, pad)
    rect = pygame.Rect(0, 0, side, side); rect.center = center
    if frame:
        tile = pygame.Surface((side, side), pygame.SRCALPHA)
        pygame.draw.rect(tile, (*GRIM_PANEL2, 235), tile.get_rect(), border_radius=3)
        # element-tinted wash, kept inside the tile so nothing spills outward
        inner = tile.get_rect().inflate(-2, -2)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(tile, (*edge, 46), inner, border_radius=2)
        surface.blit(tile, rect.topleft)
        pygame.draw.rect(surface, edge, rect, width=1, border_radius=3)
    icon = get_element_icon(element, size)
    if icon:
        surface.blit(icon, (rect.x + pad, rect.y + pad))
    return rect

def _roman(n):
    """Small Roman numeral for stage titles (falls back to the number for odd values)."""
    if not isinstance(n, int) or n <= 0 or n >= 4000:
        return str(n)
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s); n -= v
    return "".join(out)

def fill_grim_bg(surface, top=(22, 16, 9), bottom=(6, 4, 2)):
    """A warm ink vertical vignette — the ground for every ceremony / modal screen."""
    draw_gradient_rect(surface, surface.get_rect(), top, bottom)

def draw_grim_divider(surface, y, half_width=170, color=GRIM_GOLD_DIM):
    """A centered gold hairline with a diamond node — the section rule from the mockup."""
    cx = SCREEN_WIDTH // 2
    pygame.draw.line(surface, color, (cx - half_width, y), (cx - 12, y), 1)
    pygame.draw.line(surface, color, (cx + 12, y), (cx + half_width, y), 1)
    pygame.draw.polygon(surface, GRIM_GOLD, [(cx, y - 4), (cx + 4, y), (cx, y + 4), (cx - 4, y)])

# Elements whose overcharge surges in their own colour instead of their family's
SIGNATURE_COLOR_ELEMENTS = {"Blood"}


def get_overcharge_colors(element):
    """Overcharge palette taken from the element's BASE element — the Tier 1 family it
    descends from on the matchup wheel — so Hell Fire, Inferno and Lava all surge in Fire's
    colour and Abyssal Water, Ice and Mist all surge in Water's. Universal (Tier 5+)
    elements have no base, so they use their own colour. Near-black colours are lifted
    first so the fill can't vanish into the reservoir."""
    family = element if element in SIGNATURE_COLOR_ELEMENTS else (ELEMENT_AFFINITY.get(element) or element)
    base = ELEMENT_COLORS.get(family, GRIM_OC)
    if sum(base[:3]) <= 60:
        base = lighten(base, 0.55)
    return lighten(base, 0.30), darken(base, 0.55), base


_bar_ghosts = {}  # bar_id -> {"ghost","last","hit_t","call_t"} for recent-damage trails

def draw_magic_bar(surface, x, y, width, height, ratio, fill_top, fill_bottom, glow_color=None,
                    label=None, label_font=None, label_color=None, border_radius=3,
                    bg_color=None, pulse_phase=0.0, shimmer=True,
                    warn_below=0.0, warn_color=None, bar_id=None, surge=False):
    """An enchanted vessel, exactly as illustrated in the design document: a dark recessed
    reservoir, a single deep-gold hairline, a straight two-stop gradient charge with a 1px
    crest highlight, and one slow shimmer sweep. No halo and no ornament — the frame does
    the work. Two behaviours ride along without disturbing that: a low-level warning that
    pulses the hairline (warn_below / warn_color), and — when bar_id is given — a pale
    ghost trail that drains from the previous level after a hit."""
    label_color = GRIM_CREAM if label_color is None else label_color
    warn_color = GRIM_BAD if warn_color is None else warn_color
    ratio = max(0.0, min(1.0, ratio))
    rect = pygame.Rect(x, y, width, height)
    t = pygame.time.get_ticks() / 1000.0

    # Recent-damage ghost trail (per-bar memory). Remembers the high-water mark on a
    # drop, holds briefly, then drains a pale remnant down to the new level.
    ghost_ratio = ratio
    if bar_id is not None:
        st = _bar_ghosts.get(bar_id)
        if st is None:
            _bar_ghosts[bar_id] = {"ghost": ratio, "last": ratio, "hit_t": 0.0, "call_t": t}
        else:
            dt_local = max(0.0, min(0.1, t - st["call_t"]))
            st["call_t"] = t
            if ratio < st["last"] - 1e-4:
                st["ghost"] = max(st["ghost"], st["last"])  # raise to the pre-hit level
                st["hit_t"] = t
            if ratio >= st["ghost"]:
                st["ghost"] = ratio                          # healed / refilled past it
            elif t - st["hit_t"] > 0.25:                     # hold, then drain the trail
                st["ghost"] = max(ratio, st["ghost"] - 0.9 * dt_local)
            st["last"] = ratio
            ghost_ratio = st["ghost"]

    # Warning: pulses the hairline rather than throwing a halo, so the frame still reads
    warn = 0.0
    if warn_below > 0.0 and ratio <= warn_below:
        warn = 0.5 + 0.5 * math.sin(t * 7.0)

    # Overcharge surge: the one state allowed a halo — the vessel is holding more than it
    # should, and the spilling light says so. Fast pulse in the element's own colour.
    glow_color = glow_color or fill_top
    surge_pulse = 0.0
    if surge:
        surge_pulse = 0.5 + 0.5 * math.sin(t * 5.2 + pulse_phase)
        draw_glow_rect(surface, rect, glow_color, border_radius=border_radius, layers=3,
                        max_alpha=int(40 + 48 * surge_pulse), spread=3)

    # Reservoir — dark vertical gradient, with a recessed shadow along the top lip
    top_c = bg_color if bg_color is not None else BAR_WELL_TOP
    draw_gradient_rect(surface, rect, top_c, BAR_WELL_BOT, border_radius=border_radius)
    lip = pygame.Surface((width, 2), pygame.SRCALPHA)
    lip.fill((0, 0, 0, 170))
    surface.blit(lip, (x, y))

    fill_width = int(width * ratio)

    # Ghost trail — pale remnant of just-lost charge, right of the current fill
    if ghost_ratio > ratio + 0.005:
        gx = x + fill_width
        gw = min(width - fill_width, int(width * (ghost_ratio - ratio)) + 1)
        if gw > 0:
            trail = pygame.Surface((gw, height), pygame.SRCALPHA)
            trail.fill((*lighten(fill_top, 0.5), 120))
            surface.blit(trail, (gx, y))

    if fill_width > 0:
        fill_rect = pygame.Rect(x, y, fill_width, height)
        # Straight two-stop gradient, exactly as specified — no lightening of the top stop
        draw_gradient_rect(surface, fill_rect, fill_top, fill_bottom,
                           border_radius=max(0, border_radius - 1))

        # Glass gloss: a soft white highlight fading down the top ~40% of the charge,
        # over a crisp 1px crest line. This is what gives the fill its lit, glossy read.
        gloss_h = max(2, int(height * 0.42))
        gloss = pygame.Surface((fill_width, gloss_h), pygame.SRCALPHA)
        for gy in range(gloss_h):
            a = int(70 * (1.0 - gy / gloss_h))
            pygame.draw.line(gloss, (255, 255, 255, a), (0, gy), (fill_width, gy))
        surface.blit(gloss, (x, y + 1))
        pygame.draw.line(surface, (255, 255, 255), (x + 1, y + 1), (x + fill_width - 1, y + 1))

        # One slow shimmer glint. Encode the falloff in the RGB value (grey), not in the
        # alpha: BLEND_RGB_ADD reads RGB, so a white line at any alpha adds full white and
        # renders as a hard block — the old bug. A soft grey ramp adds a gentle sweep.
        if shimmer and fill_width > 14:
            bw = 18
            band = pygame.Surface((bw, height), pygame.SRCALPHA)
            for i in range(bw):
                v = int(64 * (1.0 - abs(i - (bw - 1) / 2) / ((bw - 1) / 2)) ** 1.5)
                pygame.draw.line(band, (v, v, v), (i, 0), (i, height))
            phase = ((t / 3.0) + pulse_phase * 0.13) % 1.0
            sx = x - bw + int(phase * (fill_width + bw))
            prev_clip = surface.get_clip()
            surface.set_clip(pygame.Rect(x, y, fill_width, height))
            surface.blit(band, (sx, y), special_flags=pygame.BLEND_RGB_ADD)
            surface.set_clip(prev_clip)

        # Surge motes: sparks of the element's own light crackling along the charge.
        # Positions are pure functions of time, so no per-bar state is needed.
        if surge and fill_width > 12 and height > 6:
            mote_hue = lighten(fill_top, 0.45)
            for i in range(7):
                ph = (t * (0.45 + 0.11 * i) + i * 0.317) % 1.0
                mx = x + 3 + int(ph * (fill_width - 8))
                my = y + 2 + int((height - 6) * (0.5 + 0.48 * math.sin(t * 4.1 + i * 1.9)))
                v = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 6.3 + i * 2.1))
                spark = pygame.Surface((2, 2))
                spark.fill(tuple(int(c * v) for c in mote_hue))
                surface.blit(spark, (mx, my), special_flags=pygame.BLEND_RGB_ADD)

    # A single deep-gold hairline — the only frame the vessel gets. While surging it
    # kindles in the element's colour instead of the crimson warning tint.
    if surge:
        frame_col = lerp_color(GRIM_GOLD_DEEP, glow_color, 0.35 + 0.55 * surge_pulse)
    else:
        frame_col = lerp_color(GRIM_GOLD_DEEP, warn_color, warn * 0.9)
    pygame.draw.rect(surface, frame_col, rect, width=1, border_radius=border_radius)

    if label and label_font:
        # Shrink the label to a smaller font if it's wider than the bar, so long strings
        # (e.g. "MP 200+40 OVERCHARGE") can't spill past the ends of a narrow bar.
        lf = label_font
        if lf.size(label)[0] > width - 8 and lf is not xp_font:
            lf = xp_font
        shadow = lf.render(label, True, (0, 0, 0))
        surface.blit(shadow, shadow.get_rect(center=(rect.centerx + 1, rect.centery + 1)))
        text = lf.render(label, True, label_color)
        surface.blit(text, text.get_rect(center=rect.center))

def show_notice(title, message, sub="", color=None, ms=CHEST_TOAST_MS):
    """Raise a short-lived banner (chest loot, potion used, …) over explore/menu."""
    global notice_title, notice_message, notice_sub, notice_color, notice_until
    notice_title = title
    notice_message = message
    notice_sub = sub
    notice_color = color or GRIM_CREAM
    notice_until = pygame.time.get_ticks() + ms


def notice_active():
    return bool(notice_message) and pygame.time.get_ticks() < notice_until


def draw_notice_banner(surface, center_y=None):
    """The banner itself. Rendered by both explore and the menu so feedback follows the
    player wherever the action happened.

    Height is derived from the actual font metrics and the lines are laid out with a
    running cursor — a fixed 74px box was too short for three stacked lines, so the
    title and the item name printed straight through each other."""
    if not notice_active():
        return
    pad, gap = 8, 3
    th = xp_font.get_height()
    mh = font.get_height()
    sh = small_font.get_height() if notice_sub else 0

    h = pad + th + gap + mh + ((gap + sh) if notice_sub else 0) + pad
    tw = max(font.size(notice_message)[0],
             small_font.size(notice_sub)[0],
             xp_font.size(notice_title)[0] + 30)
    banner = pygame.Rect(0, 0, max(260, tw + 48), h)
    banner.center = (SCREEN_WIDTH // 2,
                     center_y if center_y is not None else SCREEN_HEIGHT - 84)
    draw_panel(surface, banner, border_color=notice_color,
               glow_color=notice_color, border_radius=6, alpha=228)

    y = banner.top + pad + th // 2
    draw_heading(notice_title, xp_font, GRIM_GOLD, surface, banner.centerx, y, spacing=3)
    y += th // 2 + gap + mh // 2
    draw_text(notice_message, font, notice_color, surface, banner.centerx, y, center=True)
    if notice_sub:
        y += mh // 2 + gap + sh // 2
        draw_text(notice_sub, small_font, GRIM_CREAM_DIM, surface, banner.centerx, y, center=True)


def open_chest_at(map_x, map_y):
    """Open an unopened chest on this tile, banking its loot. Returns the chest, or None."""
    for chest in chests:
        if chest.opened or chest.map_x != map_x or chest.map_y != map_y:
            continue
        # Leave it shut if there's nowhere to put the contents, so it can be come back to
        if len(player_stats["inventory"]) >= ITEM_GRID_ROWS * ITEM_GRID_COLS:
            show_notice("Satchel Full", "No room",
                        "Make space before opening this chest.", GRIM_WARN)
            return None

        item = roll_chest_loot(chest.rarity, player_stats["element"])
        if getattr(chest, "special", False) or getattr(chest, "gear", False):   # reliquaries hold gear
            for _ in range(12):
                if not item or item.get("name") not in POTION_DATA:
                    break
                item = roll_chest_loot(chest.rarity, player_stats["element"])
        chest.opened = True
        chest.loot = item
        if item:
            player_stats["inventory"].append(item)
            rarity = item.get("rarity", "Common")
            sub = f"{rarity} {item.get('slot', 'Item')}"
            if getattr(chest, "special", False):           # a dungeon's reliquary
                player_stats["reroll_spins"] += DUNGEON_REWARD_SPINS
                player_stats["stat_points"] += DUNGEON_REWARD_POINTS
                sub += f"  ·  +{DUNGEON_REWARD_SPINS} spins  ·  +{DUNGEON_REWARD_POINTS} stat points"
            show_notice("Reliquary Opened" if getattr(chest, "special", False) else "Chest Opened", item["name"],
                        sub, RARITY_COLORS.get(rarity, GRIM_CREAM))
            print(f"Chest opened ({chest.rarity}) -> {rarity} {item['name']}")
        else:
            show_notice("Chest Opened", "Empty",
                        "It holds nothing of use.", GRIM_CREAM_DIM)
        return chest
    return None


def check_enemy_encounter(map_x, map_y):
    for enemy in enemies:
        if not enemy.alive:
            continue
        if enemy.flee_cooldown > 0:
            continue
        # Logical tile match OR close enough visually (catches mid-transit enemies)
        if enemy.map_x == map_x and enemy.map_y == map_y:
            return enemy
        if int(enemy.x) == map_x and int(enemy.y) == map_y:
            return enemy
    return None

def update_explore():
    global game_state, level_up_message, combat_sub_state
    level_up_message = ""; combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
    if has_vow(V_STARVED) and player_stats["hp"] < player_stats["max_hp"]:
        _starved_regen[0] += dt
        while _starved_regen[0] >= STARVED_REGEN_SECONDS:
            _starved_regen[0] -= STARVED_REGEN_SECONDS
            player_stats["hp"] = min(player_stats["max_hp"],
                                     player_stats["hp"] + max(1, player_stats["max_hp"] // 100))
    update_player_movement()
    update_grass_alert()
    if game_state == STATE_EXPLORE and not _pm["busy"]:
        update_villagers()
    if _quest_notices and not notice_active():
        show_notice(*_quest_notices.pop(0))
    if game_state == STATE_EXPLORE and not _pm["busy"]:
        update_enemies()
    if game_state == STATE_EXPLORE and not _pm["busy"]:
        update_dungeon()
        update_open_world()
        update_limitless()
    # Advance the moment the last foe falls, no matter how it died (combat, killall, a
    # straggler finally caught) — counting every area of the stage, caves included. Only a
    # stage run has an end: the open world and the Limitless descent go on.
    if GAME_MODE == "stages":
        everyone = all_stage_enemies()
        if game_state == STATE_EXPLORE and everyone and not any(e.alive for e in everyone):
            game_state = STATE_STAGE_CLEAR

def update_enemies():
    global game_state, current_enemy_encounter, combat_message, combat_turn, player_combat_action, combat_sub_state
    player_tile_x, player_tile_y = player_tile()

    for enemy in enemies:
        if not enemy.alive:
            continue

        # Tick flee cooldown
        if enemy.flee_cooldown > 0:
            enemy.flee_cooldown = max(0.0, enemy.flee_cooldown - dt)

        # Update AI state based on distance to player
        dist_to_player = math.sqrt((enemy.x - player_x) ** 2 + (enemy.y - player_y) ** 2)
        if enemy.flee_cooldown > 0:
            # Actively retreat away from the player while the flee grace period is active
            enemy.ai_state = "retreat"
        elif dist_to_player <= enemy.detection_range:
            enemy.ai_state = "chase"
        elif dist_to_player > enemy.detection_range * 1.3:
            # Hysteresis: only drop back to wander once clearly out of range
            enemy.ai_state = "wander"

        # --- Glide along the tile path ---
        # Enemies used to stop dead at every tile centre, pause, then snap off in a new
        # direction — a stop-start lurch next to the player's continuous glide. Now the next
        # tile is chosen the moment the current one is reached and leftover movement carries
        # straight into it; speed eases up from a standstill and brakes into the occasional
        # idle pause (wandering only). Motion still runs between tile centres, so an enemy can
        # never cut a corner into a wall.
        at_target = abs(enemy.target_x - enemy.x) < 1e-6 and abs(enemy.target_y - enemy.y) < 1e-6
        if at_target:
            if enemy.move_pause_timer > 0:
                enemy.move_pause_timer -= dt
                enemy.cur_speed = 0.0
                continue
            if _enemy_step(enemy, player_tile_x, player_tile_y) == "combat":
                return

        dist = math.hypot(enemy.target_x - enemy.x, enemy.target_y - enemy.y)
        want = enemy.speed
        # Nearly there with every way on blocked (a crowd converging)? Brake now rather than
        # arrive at full speed and stop dead.
        if (not enemy.pause_next and dist < enemy.speed / ENEMY_BRAKE
                and not _enemy_has_exit(enemy)):
            enemy.pause_next = True
        if enemy.pause_next:                      # ease down into the pause
            want = min(want, max(ENEMY_MIN_BRAKE_SPEED, dist * ENEMY_BRAKE))
        enemy.cur_speed += (want - enemy.cur_speed) * min(1.0, ENEMY_ACCEL * dt)
        budget = enemy.cur_speed * dt

        for _ in range(3):                        # a fast enemy may cross a tile in one frame
            tdx, tdy = enemy.target_x - enemy.x, enemy.target_y - enemy.y
            dist = math.hypot(tdx, tdy)
            if dist <= 1e-9:
                break
            if budget < dist:
                enemy.x += tdx / dist * budget
                enemy.y += tdy / dist * budget
                break
            enemy.x, enemy.y = enemy.target_x, enemy.target_y
            budget -= dist
            if enemy.pause_next:
                enemy.pause_next = False
                enemy.move_pause_timer = enemy.move_pause_duration
                enemy.cur_speed = 0.0
                break
            outcome = _enemy_step(enemy, player_tile_x, player_tile_y)
            if outcome == "combat":
                return
            if outcome is None:                   # boxed in: wait here for a moment
                enemy.move_pause_timer = 0.25
                enemy.cur_speed = 0.0
                break


ENEMY_ACCEL = 7.0             # how quickly speed eases toward its target (per second)
ENEMY_BRAKE = 3.2             # braking: speed allowed per tile left before a pause
ENEMY_MIN_BRAKE_SPEED = 0.12  # never crawl slower than this while braking
ENEMY_WANDER_PAUSE = 0.22     # chance a wandering step ends in an idle pause (bosses: double)
ENEMY_KEEP_HEADING = 0.7      # chance a wanderer carries on in the same direction


def _enemy_has_exit(enemy):
    """Whether any tile next to the one this enemy is heading for is free to step into."""
    for cdx, cdy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = enemy.map_x + cdx, enemy.map_y + cdy
        if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT) or world_map[ny][nx] != 0:
            continue
        if not current_area.can_step((enemy.map_x, enemy.map_y), (nx, ny), ignore_solid=True):
            continue
        if (nx, ny) in area_portals() or (nx, ny) in current_area.safe:
            continue
        if not any(e.alive and e is not enemy and e.map_x == nx and e.map_y == ny for e in enemies):
            return True
    return False


def _enemy_step(enemy, player_tile_x, player_tile_y):
    """Choose and claim the next tile. Returns "combat" if the step lands on the player,
    "moved" when a tile was claimed, or None when every way is blocked."""
    ex, ey = enemy.map_x, enemy.map_y
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    random.shuffle(dirs)
    back = (-enemy.heading[0], -enemy.heading[1])

    def toward(dx, dy):
        # the axis with further to go first, then the other; never a reversal first
        order = []
        if abs(dx) >= abs(dy):
            if dx: order.append((1 if dx > 0 else -1, 0))
            if dy: order.append((0, 1 if dy > 0 else -1))
        else:
            if dy: order.append((0, 1 if dy > 0 else -1))
            if dx: order.append((1 if dx > 0 else -1, 0))
        return order

    if enemy.ai_state == "chase":
        preferred = toward(player_tile_x - ex, player_tile_y - ey)
        # mostly commit to closing the distance; now and then sidestep so a wall can't pin it
        candidates = (preferred if random.random() < 0.85 else []) + dirs
    elif enemy.ai_state == "retreat":
        candidates = toward(ex - player_tile_x, ey - player_tile_y) + dirs
    else:
        keep = [enemy.heading] if enemy.heading != (0, 0) and random.random() < ENEMY_KEEP_HEADING else []
        candidates = keep + dirs
    # a reversal is only ever the last resort (dead ends)
    seen, ordered = set(), []
    for d in candidates:
        if d not in seen and d != back:
            seen.add(d); ordered.append(d)
    if back != (0, 0):
        ordered.append(back)

    for cdx, cdy in ordered:
        nx, ny = ex + cdx, ey + cdy
        if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT): continue
        if world_map[ny][nx] != 0: continue
        if not current_area.can_step((ex, ey), (nx, ny), ignore_solid=True): continue   # cliffs
        if (nx, ny) in area_portals(): continue            # foes never wander through cave mouths
        if (nx, ny) in current_area.safe: continue          # …or into a village
        if any(e.alive and e is not enemy and e.map_x == nx and e.map_y == ny for e in enemies): continue

        enemy.map_x, enemy.map_y = nx, ny
        enemy.target_x, enemy.target_y = nx + 0.5, ny + 0.5
        enemy.heading = (cdx, cdy)
        pause_odds = ENEMY_WANDER_PAUSE * (2 if enemy.is_boss else 1)
        enemy.pause_next = enemy.ai_state == "wander" and random.random() < pause_odds

        # Only trigger combat if flee cooldown has expired
        if nx == player_tile_x and ny == player_tile_y and enemy.flee_cooldown <= 0:
            start_encounter(enemy, f"A {enemy.name} ({enemy.element}) ambushes you!")
            return "combat"
        return "moved"
    return None

def calculate_elemental_multiplier(attacker_element, defender_element):
    if not attacker_element or not defender_element: return 1.0
    attacker = matchup_key(attacker_element); defender = matchup_key(defender_element)
    if attacker in ELEMENTAL_MATCHUPS: return ELEMENTAL_MATCHUPS[attacker].get(defender, 1.0)
    else: return 1.0

def check_true_element_unlock():
    """At TRUE_ELEMENT_LEVEL_REQ, a player still bound to a Tier 1 element masters it into
    its True form. This is a catch-up: reaching level 15 on Tier 1 means the evolution
    milestones never landed, so the element matures instead of branching."""
    if player_stats["level"] < true_form_level():
        return None
    base = player_stats["element"]
    if base not in TRUE_ELEMENTS:
        return None
    grant_true_form(base)
    return TRUE_ELEMENTS[base]


def check_for_level_up():
    global level_up_message
    leveled_up = False
    while player_stats["xp"] >= player_stats["xp_to_next_level"]:
        leveled_up = True; overflow_xp = player_stats["xp"] - player_stats["xp_to_next_level"]
        player_stats["level"] += 1; player_stats["xp"] = overflow_xp
        new_xp_needed = BASE_XP_TO_LEVEL_UP * player_stats["level"]
        if has_vow(V_RISING_TIER):
            new_xp_needed = int(new_xp_needed * 1.5)
        player_stats["xp_to_next_level"] = new_xp_needed
        player_stats["max_hp"] += 5; player_stats["melee_strength"] += 1; player_stats["element_strength"] += 1; player_stats["defense"] += 1
        if has_vow(V_EMPTY_HAND):
            player_stats["melee_strength"] += 2
        player_stats["stat_points"] += 3 + (2 if has_vow(V_SCARRED) else 0) + (1 if has_vow(V_STARVED) else 0)
        player_stats["hp"] = player_stats["max_hp"]
        level_up_message = f"LEVEL UP! Reached Level {player_stats['level']}!"
        print(level_up_message); print(f"  Stats Increased! MaxHP:{player_stats['max_hp']}, MEL:{player_stats['melee_strength']}, ELE:{player_stats['element_strength']}, DEF:{player_stats['defense']}")
        print(f"  XP: {player_stats['xp']}/{player_stats['xp_to_next_level']} for next level.")
    if leveled_up:
        raise_signal("levelup", f"LEVEL UP — Reached Level {player_stats['level']}!")
    # Note: mastery into a True form is no longer automatic at level 15. It's now a choice
    # offered on the Evolution screen (needs the element's True Sigil), so the auto-unlock
    # here would pre-empt that. The Sigil can also still be used directly from the satchel.
    return leveled_up

# --- Game Reset (used by Quit to Main Menu) ---
def reset_game(seed=None):
    global game_state, current_stage, current_enemy_encounter, combat_turn, combat_message
    global player_combat_action, level_up_message, combat_sub_state, player_selected_skill
    global menu_tab, inventory_sub_state, selected_item_row, selected_item_col, selected_equip_index
    global stats_sub_state, selected_stat_index, previous_game_state, info_page
    global is_in_combat_delay, combat_delay_start_time, next_combat_turn_after_delay
    global notice_title, notice_message, notice_sub, notice_until

    player_stats.update({
        "max_hp": 100, "hp": 100, "max_mana": 100, "mana": 100, "is_overcharged": False, "melee_strength": 15, "element_strength": 10,
        "defense": 5, "is_defending": False, "reroll_spins": 0,
        "level": 1, "xp": 0, "xp_to_next_level": BASE_XP_TO_LEVEL_UP,
        "is_awakened": False, "awakening_duration": 0, "awakening_cooldown": 0,
        "stat_points": 5, "vows": [], "pending_evolution": False, "is_god": False, "luck": 0,
        "class": None, "race": None, "look": None,
        "martyr_used": False, "oath_one_stat": None, "one_carry": {}, "rootless_stage": 0, "peak_tier": 1,
        "last_action": None, "first_strike_ready": False,
        "true_forms_seen": [],
        "inventory": [],   # start empty — gear comes from chests and drops
        "equipment": {"Helmet": None, "Chest": None, "Boots": None, "Weapon": None},
        "skill_cooldowns": {},
    })
    player_stats["element"] = get_random_weighted_element(1)
    record_element_change(player_stats["element"])

    current_stage = 1
    game_state = STATE_EXPLORE
    current_enemy_encounter = None
    combat_turn = 'player'
    cancel_kill_hold()
    combat_message = ""
    player_combat_action = None
    level_up_message = ""
    combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
    player_selected_skill = None
    menu_tab = "Stats"
    info_page = 0
    inventory_sub_state = INVENTORY_SUBSTATE_VIEWING
    selected_item_row = -1; selected_item_col = -1; selected_equip_index = 0
    stats_sub_state = STATS_SUBSTATE_VIEWING
    selected_stat_index = -1
    previous_game_state = None
    is_in_combat_delay = False
    combat_delay_start_time = 0
    next_combat_turn_after_delay = None
    notice_title = ""
    notice_message = ""
    notice_sub = ""
    notice_until = 0

    quest_log.clear()
    _quest_notices.clear()
    _day_offset[0] = 0
    setup_stage(current_stage, seed)   # also clears and respawns this stage's chests
    game_state = STATE_CREATE    # every new run starts on the character screen (choices kept)


# --- Rendering Functions ---
TRACKER_THRESHOLD = 8   # start pointing out foes once fewer than this remain

def world_scale():
    """Screen pixels per art pixel: 3x at 800x600 (a DS-like ~16x12 tiles on screen)."""
    return max(2, int(round(SCREEN_HEIGHT / 200)))


_tiles = {}
_player_sprite_cache = {}
_view_cache = {}
_light_cache = {}
_LIQUIDS = {"water", "lava", "cwater", "clava"}


def _cliff_tile(area, x, y):
    """The face, stairs or waterfall art for a cliff tile, matched to the plateau above."""
    tiles = world_tiles()
    g = area.ground[y][x]
    b = _art_biome(area, x, y - 1)
    if g == "stairs":
        return tiles["stairs_" + b]
    west = area.in_bounds(x - 1, y) and area.ground[y][x - 1] in _CLIFFS
    east = area.in_bounds(x + 1, y) and area.ground[y][x + 1] in _CLIFFS
    v = 0 if (west and east) else (1 if not west else 2)
    return tiles["cliff_" + b][v * 2 + (x + y) % 2]


def _draw_rims(surf, area, x, y, px, py):
    """Edge a raised tile where its plateau drops away west, east or north, and drop a soft
    shadow onto ground lying at the foot of a cliff."""
    T = TILE_PX
    h = area.height[y][x]
    lip = make_tiles.GROUNDS.get(make_tiles.CLIFF_LIP.get(_art_biome(area, x, y), "grass"))
    dark = make_tiles.shade(lip[1], 0.55) if lip else (40, 40, 40)
    light = lip[2] if lip else (200, 200, 200)

    def lower(nx, ny):
        return area.in_bounds(nx, ny) and area.height[ny][nx] < h and area.ground[ny][nx] not in _CLIFFS

    if h > 0:
        k = 7 * h                                               # high ground sits a touch brighter
        surf.fill((k, k, k), (px, py, T, T), special_flags=pygame.BLEND_RGB_ADD)
        pal = make_tiles.CLIFF_PALETTES[_art_biome(area, x, y)]
        rock_dark = make_tiles.shade(pal[0], 0.7)
        if lower(x, y - 1):                                     # back edge: a rocky rim
            surf.fill(rock_dark, (px, py, T, 1)); surf.fill(pal[3], (px, py + 1, T, 1))
            surf.fill(pal[2], (px, py + 2, T, 1)); surf.fill(light, (px, py + 3, T, 1))
        if lower(x - 1, y):                                     # west side wall, catching the light
            surf.fill(rock_dark, (px, py, 1, T)); surf.fill(pal[3], (px + 1, py, 2, T))
            surf.fill(pal[2], (px + 3, py, 2, T)); surf.fill(light, (px + 5, py, 1, T))
            for yy in range(2, T, 5):
                surf.fill(pal[1], (px + 1, py + yy, 4, 1)); surf.fill(pal[4], (px + 1, py + yy - 1, 2, 1))
        if lower(x + 1, y):                                     # east side wall, in shade
            surf.fill(rock_dark, (px + T - 1, py, 1, T)); surf.fill(pal[1], (px + T - 3, py, 2, T))
            surf.fill(pal[2], (px + T - 5, py, 2, T)); surf.fill(dark, (px + T - 6, py, 1, T))
            for yy in range(4, T, 5):
                surf.fill(pal[0], (px + T - 5, py + yy, 4, 1))
    if y > 0 and area.ground[y - 1][x] in _CLIFFS:
        sh = _light_cache.get("cliff_shadow")
        if sh is None:
            sh = pygame.Surface((T, 3), pygame.SRCALPHA)
            for i, a in enumerate((90, 55, 25)):
                sh.fill((0, 0, 0, a), (0, i, T, 1))
            _light_cache["cliff_shadow"] = sh
        surf.blit(sh, (px, py))
_BLEND_PRIO = {"water": 0, "lava": 0, "cwater": 0, "clava": 0, "ice": 1, "cice": 1,
               "path_meadow": 2, "path_tundra": 2, "path_desert": 2, "path_volcanic": 2,
               "path_storm": 2, "cfloor": 2, "bridge": 1, "sand": 3, "ash": 3, "slate": 3, "grass": 4, "snow": 5}
_FOAM = (222, 240, 255)
CAVE_AMBIENT = {"meadow": (62, 70, 60), "tundra": (84, 104, 134), "desert": (80, 66, 52),
                "volcanic": (74, 46, 40), "storm": (60, 52, 92), "dungeon": (58, 54, 68),
                "house": (176, 156, 132)}
_OBJ_LIGHTS = {"crystal": ((150, 100, 255), 2.4), "crystal_small": ((150, 100, 255), 1.6),
               "vent": ((255, 120, 40), 2.2), "lamppost": ((255, 210, 140), 3.0),
               "fireplace": ((255, 150, 70), 3.4), "shrine": ((120, 200, 255), 2.4)}


def world_tiles():
    """The tileset (built from make_tiles.py on first use); PNGs in tiles/custom/ override."""
    if not _tiles:
        for k, v in make_tiles.build_tileset().items():
            _tiles[k] = [t.convert_alpha() for t in v] if isinstance(v, list) else v.convert_alpha()
        custom = os.path.join("tiles", "custom")
        if os.path.isdir(custom):
            for f in os.listdir(custom):
                if not f.lower().endswith(".png"):
                    continue
                stem = f[:-4]
                try:
                    img = load_image(os.path.join(custom, f)).convert_alpha()
                except pygame.error:
                    continue
                base, _, idx = stem.rpartition("_")
                if base in _tiles and isinstance(_tiles[base], list) and idx.isdigit() and int(idx) < len(_tiles[base]):
                    _tiles[base][int(idx)] = img
                elif stem in _tiles and not isinstance(_tiles[stem], list):
                    _tiles[stem] = img
        print(f" - Built world tileset: {len(_tiles)} tile sets")
    return _tiles


def look_frames(cls, color, skin, hair, race="Human", style="Short", hood="On"):
    """Walk-cycle frames for a look. color "Element" follows the player's current element;
    style is a hairstyle, shown when hood is "Off" (hood down / the Knight's helmet off)."""
    if color == "Element" or color not in make_tiles.OUTFIT_COLORS:
        rgb = tuple((ELEMENT_COLORS.get(player_stats.get("element")) or GRIM_GOLD)[:3])
    else:
        rgb = make_tiles.OUTFIT_COLORS[color]
    key = (cls, rgb, skin, hair, race, style, hood)
    if key not in _player_sprite_cache:
        look = {"class": cls, "color": rgb,
                "skin": make_tiles.SKIN_TONES.get(skin, make_tiles.SKIN_TONES["Fair"]),
                "hair": make_tiles.HAIR_COLORS.get(hair, make_tiles.HAIR_COLORS["Chestnut"]), "race": race,
                "style": style, "hood": hood != "Off"}
        _player_sprite_cache[key] = {d: [f.convert_alpha() for f in fr]
                                     for d, fr in make_tiles.player_frames(look).items()}
    return _player_sprite_cache[key]


import make_heroes


def hero_battle_sprite(cls, color, skin, hair, race="Human", view="back", style="Short", hood="On"):
    """The detailed 48px hero (make_heroes.py): from behind in battle, from the front on
    the character screen. The Mage's staff orb glows in the current element's colour."""
    elem_rgb = tuple((ELEMENT_COLORS.get(player_stats.get("element")) or GRIM_GOLD)[:3])
    rgb = elem_rgb if color == "Element" or color not in make_tiles.OUTFIT_COLORS else make_tiles.OUTFIT_COLORS[color]
    key = ("hero", view, cls, rgb, skin, hair, race, elem_rgb, style, hood)
    if key not in _player_sprite_cache:
        look = {"class": cls, "race": race, "color": rgb, "orb": lighten(elem_rgb, 0.25),
                "skin": make_tiles.SKIN_TONES.get(skin, make_tiles.SKIN_TONES["Fair"]),
                "hair": make_tiles.HAIR_COLORS.get(hair, make_tiles.HAIR_COLORS["Chestnut"]),
                "style": style, "hood": hood != "Off"}
        _player_sprite_cache[key] = make_heroes.hero_sprite(look, view).convert_alpha()
    return _player_sprite_cache[key]


def player_battle_sprite():
    look = player_stats.get("look") or {}
    return hero_battle_sprite(player_stats.get("class") or "Mage", look.get("color", "Element"),
                              look.get("skin", "Fair"), look.get("hair", "Chestnut"),
                              player_stats.get("race") or "Human", "back",
                              look.get("style", "Short"), look.get("hood", "On"))


def player_sprites():
    look = player_stats.get("look") or {}
    return look_frames(player_stats.get("class") or "Mage", look.get("color", "Element"),
                       look.get("skin", "Fair"), look.get("hair", "Chestnut"), player_stats.get("race") or "Human",
                       look.get("style", "Short"), look.get("hood", "On"))


def _pick(lst, x, y):
    return lst[(x * 7349 + y * 1973 + (x ^ y) * 31) % len(lst)]


def _edge_masks():
    """Ragged alpha masks for blending one ground into the next, per side, plus foam lines."""
    if "masks" in _light_cache:
        return _light_cache["masks"]
    rng = random.Random(7)
    masks = {}
    for side in ("up", "down", "left", "right"):
        variants = []
        for v in range(3):
            depth = [2 + int(1.6 * math.sin(i * 0.9 + v * 2.1) + rng.random() * 1.4) for i in range(TILE_PX)]
            m = pygame.Surface((TILE_PX, TILE_PX), pygame.SRCALPHA)
            foam = pygame.Surface((TILE_PX, TILE_PX), pygame.SRCALPHA)
            for i, dpt in enumerate(depth):
                for k in range(dpt):
                    pos = {"up": (i, k), "down": (i, TILE_PX - 1 - k), "left": (k, i), "right": (TILE_PX - 1 - k, i)}[side]
                    m.set_at(pos, (255, 255, 255, 255))
                fp = {"up": (i, dpt), "down": (i, TILE_PX - 1 - dpt), "left": (dpt, i), "right": (TILE_PX - 1 - dpt, i)}[side]
                if rng.random() < 0.75:
                    foam.set_at(fp, (*_FOAM, 210))
            variants.append((m, foam))
        masks[side] = variants
    _light_cache["masks"] = masks
    return masks


def _ground_key(area, name):
    return "cfloor_" + area.theme if name == "cfloor" else name


def _object_sprite(area, name, x=0, y=0):
    tiles = world_tiles()
    if name == "stalagmite":
        return tiles["stalagmite_" + area.theme]
    img = tiles.get(name)
    return _pick(img, x, y) if isinstance(img, list) else img


CHUNK = 32                         # tiles per side of a pre-rendered piece of the world
CHUNK_CACHE = 48                   # pieces kept rendered at once (the open world has ~190)


def _prerender(area, cx=None, cy=None):
    """Ground, blended edges, decor and short objects baked into a surface; liquids, tall
    objects and lights are kept aside for per-frame drawing. With (cx, cy) it renders one
    CHUNK x CHUNK piece of the area, so even the open world never needs one giant image."""
    T = TILE_PX
    tiles = world_tiles()
    masks = _edge_masks()
    if cx is None:
        x0, y0, x1, y1 = 0, 0, area.w, area.h
    else:
        x0, y0 = cx * CHUNK, cy * CHUNK
        x1, y1 = min(area.w, x0 + CHUNK), min(area.h, y0 + CHUNK)
    surf = pygame.Surface(((x1 - x0) * T, (y1 - y0) * T)).convert()
    anim, tall, lights = {}, {}, []
    sides = (("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0))
    for y in range(y0, y1):
        for x in range(x0, x1):
            g = area.ground[y][x]
            px, py = (x - x0) * T, (y - y0) * T
            wx, wy = x * T, y * T
            if g == "cwall":
                below = area.ground[y + 1][x] if y + 1 < area.h else "cwall"
                key = ("cface_" if below != "cwall" else "ctop_") + area.theme
                surf.blit(_pick(tiles[key], x, y), (px, py))
                dec = area.decor.get((x, y))
                if dec and dec in tiles:                     # wall torches
                    surf.blit(tiles[dec], (px, py))
                    if dec == "walltorch":
                        lights.append((x + 0.5, y + 0.4, (255, 170, 90), 3.2))
                continue
            if g in _CLIFFS:                                 # hill faces, stairs, falls
                if g == "waterfall":
                    surf.blit(tiles["waterfall"][0], (px, py))
                    anim[(x, y)] = ("waterfall", None)
                else:
                    surf.blit(_cliff_tile(area, x, y), (px, py))
                continue
            key = _ground_key(area, g)
            lst = tiles[key]
            surf.blit(lst[0] if g in _LIQUIDS else _pick(lst, x, y), (px, py))
            overlay = None
            for side, dx, dy in sides:
                nx, ny = x + dx, y + dy
                if not area.in_bounds(nx, ny):
                    continue
                n = area.ground[ny][nx]
                if n == g or n == "cwall" or n in _CLIFFS or _BLEND_PRIO.get(n, 2) <= _BLEND_PRIO.get(g, 2):
                    continue
                if area.height is not None and area.height[ny][nx] != area.height[y][x]:
                    continue                                 # no blending across a level change
                mask, foam = masks[side][(x * 3 + y * 5) % 3]
                piece = _pick(tiles[_ground_key(area, n)], x, y).copy()
                piece.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                if g in _LIQUIDS:
                    if overlay is None:
                        overlay = pygame.Surface((T, T), pygame.SRCALPHA)
                    overlay.blit(piece, (0, 0))
                    if g in ("water", "cwater"):
                        overlay.blit(foam, (0, 0))
                else:
                    surf.blit(piece, (px, py))
            if area.height is not None and g not in _LIQUIDS:
                _draw_rims(surf, area, x, y, px, py)
            if g in _LIQUIDS:
                if overlay is not None:
                    surf.blit(overlay, (px, py))
                anim[(x, y)] = (key, overlay)
                if g in ("lava", "clava"):
                    lights.append((x + 0.5, y + 0.5, (255, 110, 40), 1.7))
            dec = area.decor.get((x, y))
            if dec:
                img = tiles.get(dec)
                if isinstance(img, list):
                    img = _pick(img, x, y)
                if img is not None:
                    surf.blit(img, (px, py))
            obj = area.objects.get((x, y))
            if obj and not obj.endswith("_part"):
                img = _object_sprite(area, obj, x, y)
                if img is None:
                    continue
                w, h = img.get_size()
                if obj.startswith("house_"):                 # anchored at the footprint's bottom-left
                    tall[(x, y)] = (img, x * T, (y + 1) * T - h, (y + 1) * T)
                elif obj.startswith("outcrop_") or obj.startswith("gate_"):
                    tall[(x, y)] = (img, (x - 1) * T, (y + 2) * T - h, (y + 2) * T)
                elif h <= T:
                    surf.blit(img, (px + (T - w) // 2, py + T - h))
                else:
                    tall[(x, y)] = (img, wx + (T - w) // 2, wy + T - h, wy + T)
                if obj in _OBJ_LIGHTS:
                    col, rad = _OBJ_LIGHTS[obj]
                    lights.append((x + 0.5, y + 0.4, col, rad))
    for (x, y), (target, _dest, _f) in area.portals.items():
        if area.kind in ("cave", "dungeon") and x0 <= x < x1 and y0 <= y < y1:
            surf.blit(tiles["exit"], ((x - x0) * T, (y - y0) * T))
            lights.append((x + 0.5, y + 0.5, (255, 236, 190), 3.4))
    return {"surf": surf, "anim": anim, "tall": tall, "lights": lights}


def _area_layers(area):
    """Per-area render state: rendered chunk surfaces (an LRU cache) plus what every
    rendered chunk found — animated tiles, tall sprites and lights — kept for good."""
    lay = _world_cache.get(area.id)
    if lay is None:
        lay = {"chunks": {}, "seen": set(), "anim": {}, "tall": {}, "lights": {},
               "anim_k": {}, "tall_k": {}}       # the same two, listed per chunk
        _world_cache[area.id] = lay
    return lay


def _chunk(area, cx, cy):
    lay = _area_layers(area)
    key = (cx, cy)
    surf = lay["chunks"].pop(key, None)
    if surf is None:
        r = _prerender(area, cx, cy)
        surf = r["surf"]
        if key not in lay["seen"]:
            lay["seen"].add(key)
            lay["anim"].update(r["anim"])
            lay["tall"].update(r["tall"])
            lay["lights"][key] = r["lights"]
            lay["anim_k"][key] = sorted(r["anim"].items(), key=lambda kv: (kv[0][1], kv[0][0]))
            lay["tall_k"][key] = sorted(r["tall"].items(), key=lambda kv: (kv[0][1], kv[0][0]))
        while len(lay["chunks"]) >= CHUNK_CACHE:
            lay["chunks"].pop(next(iter(lay["chunks"])))          # the least recently used
    lay["chunks"][key] = surf                                     # most recently used last
    return surf


def _light_sprite(radius_px, color):
    """A soft radial light, cached per size and colour."""
    key = (int(radius_px), color)
    spr = _light_cache.get(key)
    if spr is None:
        base = _light_cache.get("base")
        if base is None:
            n = 64
            base = pygame.Surface((n, n))
            for yy in range(n):
                for xx in range(n):
                    d = math.hypot(xx + 0.5 - n / 2, yy + 0.5 - n / 2) / (n / 2)
                    v = int(255 * max(0.0, 1.0 - d) ** 1.15)
                    base.set_at((xx, yy), (v, v, v))
            _light_cache["base"] = base
        d = max(2, int(radius_px * 2))
        spr = pygame.transform.smoothscale(base, (d, d))
        tint = pygame.Surface((d, d))
        tint.fill(color)
        spr.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if len(_light_cache) > 120:
            for k in [k for k in _light_cache if isinstance(k, tuple)][:60]:
                del _light_cache[k]
        _light_cache[key] = spr
    return spr


def _mist_sprite(level):
    """A soft puff of spray, in four strengths (0 faint .. 3 dense)."""
    key = ("mist", level)
    spr = _light_cache.get(key)
    if spr is None:
        spr = pygame.Surface((7, 7), pygame.SRCALPHA)
        for yy in range(7):
            for xx in range(7):
                d = math.hypot(xx - 3, yy - 3) / 3.5
                if d < 1:
                    spr.set_at((xx, yy), (236, 246, 255, int((1 - d) * 60 * (level + 1))))
        _light_cache[key] = spr
    return spr


def _cloud_sprite():
    spr = _light_cache.get("cloud")
    if spr is None:
        w, h = 160, 96
        spr = pygame.Surface((w, h))
        rng = random.Random(3)
        blobs = [(rng.uniform(40, 120), rng.uniform(30, 66), rng.uniform(22, 40)) for _ in range(6)]
        for yy in range(0, h):
            for xx in range(0, w):
                v = 0.0
                for bx, by, br in blobs:
                    d = math.hypot(xx - bx, (yy - by) * 1.3) / br
                    v = max(v, max(0.0, 1.0 - d))
                c = int(34 * min(1.0, v * 1.6))
                spr.set_at((xx, yy), (c, c, int(c * 0.8)))
        _light_cache["cloud"] = spr
    return spr


def _outdoor_ambient():
    """Daylight tint from the day/night cycle: white by day, warm at dusk, blue at night."""
    f = get_day_factor()
    k = f * f * (3 - 2 * f)
    night, day, dusk = (64, 76, 132), (255, 255, 255), (255, 188, 140)
    amb = lerp_color(night, day, k)
    warm = max(0.0, 1.0 - abs(f - 0.45) * 4)
    return lerp_color(amb, dusk, 0.35 * warm), f


# --- Ambience: birds, weather, smoke and glints (see ambience.py) ---
import ambience

_ambience = ambience.Ambience()
_battle_ambience = ambience.Ambience(battle=True)
_AMB_SOURCES = {"lamppost": ("lamp", -0.9), "fireplace": ("fire", 0.1), "vent": ("vent", 0.2),
                "shrine": ("shrine", -0.8), "crystal": ("crystal", -0.2), "crystal_small": ("crystal", 0.0)}


def _update_world_ambience(area, cam_x, cam_y, vw, vh, now, light_list, tx0, ty0, tx1, ty1):
    T = TILE_PX
    objects, ground = area.objects, area.ground

    def biome_at(x, y):
        return _art_biome(area, int(x // T), int(y // T))

    def tile_kind(tx, ty):
        if not area.in_bounds(tx, ty):
            return None
        obj = objects.get((tx, ty))
        if obj is not None:
            return "tree" if obj == "tree" else "blocked"
        return "water" if ground[ty][tx] == "water" else "open"

    def walkable(x, y):
        tx, ty = int(x // T), int(y // T)
        return (area.in_bounds(tx, ty) and not area.solid[ty][tx] and (tx, ty) not in objects
                and ground[ty][tx] not in _LIQUIDS and (tx, ty) not in area.portals)

    chimneys = []
    if area.outdoor:
        tall = _area_layers(area)["tall"]
        for y in range(ty0, min(area.h - 1, ty1 + 4) + 1):
            for x in range(max(0, tx0 - 5), min(area.w - 1, tx1 + 1) + 1):
                obj = objects.get((x, y))
                if obj and obj.startswith("house_") and (x, y) in tall:
                    _img, ox, oy, _sy = tall[(x, y)]
                    if obj == "house_desert":
                        chimneys.append((ox + 66, oy + 7, False))       # the flat roof's vent
                    else:
                        chimneys.append((ox + 62.5, oy + 1, obj == "house_volcanic"))
    sources = []
    for (lx, ly, _c, _r) in light_list:
        src = _AMB_SOURCES.get(objects.get((int(lx), int(ly))))
        if src and cam_x - 32 < lx * T < cam_x + vw + 32 and cam_y - 32 < ly * T < cam_y + vh + 48:
            sources.append((lx * T, (int(ly) + 0.5 + src[1]) * T, src[0]))
    fx, fy = _pm.get("frm", _pm["tile"])
    step_ground = ground[fy][fx] if area.in_bounds(fx, fy) else ""
    ptx, pty = player_tile()
    ctx = {"key": (area.id, id(area)), "now": now, "view": (cam_x, cam_y, vw, vh), "tile": T,
           "outdoor": area.outdoor, "theme": "house" if area.kind == "house" else area.theme,
           "day": get_day_factor() if area.outdoor else 1.0, "biome_at": biome_at, "tile_kind": tile_kind,
           "walkable": walkable, "chimneys": chimneys, "sources": sources,
           "player": (player_x * T, player_y * T + T / 2), "moving": _pm["moving"],
           "player_biome": _art_biome(area, ptx, pty) if area.outdoor else None,
           "step": _pm["steps"], "step_from": (fx * T + 8, fy * T + 13, step_ground, _pm["facing"])}
    _ambience.update(ctx)


def _vignette(size, strength):
    """Soft darkening toward the corners, multiplied into the light map."""
    key = ("vignette", size, strength)
    v = _view_cache.get(key)
    if v is None:
        n, m = 40, 30
        small = pygame.Surface((n, m))
        for yy in range(m):
            for xx in range(n):
                d = min(1.0, math.hypot((xx + 0.5) / n * 2 - 1, (yy + 0.5) / m * 2 - 1) / 1.414)
                c = int(255 * (1 - strength * max(0.0, (d - 0.45) / 0.55) ** 1.6))
                small.set_at((xx, yy), (c, c, c))
        v = pygame.transform.smoothscale(small, size)
        _view_cache[key] = v
    return v


def _draw_battle_ambience(theme, outdoor, L, now):
    s = 3
    W, field = L["W"], L["field"]
    ctx = {"key": ("battle", theme, outdoor), "now": now, "view": (0, 0, W // s, field // s), "tile": TILE_PX,
           "outdoor": outdoor, "theme": theme, "day": get_day_factor() if outdoor else 1.0,
           "biome_at": lambda x, y: theme, "sky": int(field * 0.34) // s,
           "tint": _outdoor_ambient()[0] if outdoor else None, "player_biome": theme}
    _battle_ambience.update(ctx)
    clip = screen.get_clip()
    screen.set_clip(pygame.Rect(0, 0, W, field))
    _battle_ambience.draw_air(screen, (0, 0), s)
    _battle_ambience.draw_glow(screen, (0, 0), s)
    screen.set_clip(clip)


def _chunk_items(by_chunk, x0, y0, x1, y1):
    """The (tile, value) pairs listed per chunk that fall inside tiles x0..x1, y0..y1, in
    row order (rows top to bottom, left to right within a row) like a tile-by-tile scan."""
    found = []
    for ky in range(y0 // CHUNK, y1 // CHUNK + 1):
        for kx in range(x0 // CHUNK, x1 // CHUNK + 1):
            for item in by_chunk.get((kx, ky), ()):
                x, y = item[0]
                if x0 <= x <= x1 and y0 <= y <= y1:
                    found.append(item)
    found.sort(key=lambda kv: (kv[0][1], kv[0][0]))
    return found


def draw_world(view, cam_x, cam_y):
    """Draw the live area into the base-resolution view at the given camera offset."""
    T = TILE_PX
    area = current_area
    layers = _area_layers(area)
    tiles = world_tiles()
    vw, vh = view.get_size()
    view.fill((14, 22, 16) if area.outdoor else (6, 5, 8))
    now = pygame.time.get_ticks() / 1000.0
    tx0, ty0 = max(0, cam_x // T), max(0, cam_y // T)
    tx1, ty1 = min(area.w - 1, (cam_x + vw) // T + 1), min(area.h - 1, (cam_y + vh) // T + 1)
    # the chunks on screen, plus those whose tall sprites or lights could reach onto it
    ncx, ncy = (area.w + CHUNK - 1) // CHUNK, (area.h + CHUNK - 1) // CHUNK
    kx0, kx1 = max(0, (tx0 - 6) // CHUNK), min(ncx - 1, (tx1 + 4) // CHUNK)
    ky0, ky1 = max(0, (ty0 - 4) // CHUNK), min(ncy - 1, (ty1 + 5) // CHUNK)
    for ky in range(ky0, ky1 + 1):
        for kx in range(kx0, kx1 + 1):
            surf = _chunk(area, kx, ky)
            ox, oy = kx * CHUNK * T - cam_x, ky * CHUNK * T - cam_y
            if ox < vw and oy < vh and ox + surf.get_width() > 0 and oy + surf.get_height() > 0:
                view.blit(surf, (ox, oy))
    light_list = [l for ky in range(ky0, ky1 + 1) for kx in range(kx0, kx1 + 1)
                  for l in layers["lights"].get((kx, ky), ())]
    # warm one more chunk around the view each frame, so walking on never hitches
    for ky in range(max(0, ky0 - 1), min(ncy, ky1 + 2)):
        for kx in range(max(0, kx0 - 1), min(ncx, kx1 + 2)):
            if (kx, ky) not in layers["chunks"]:
                _chunk(area, kx, ky)
                break
        else:
            continue
        break
    _update_world_ambience(area, cam_x, cam_y, vw, vh, now, light_list, tx0, ty0, tx1, ty1)

    # animated liquids (from the per-chunk lists: checking every tile on screen each frame
    # is slow on a phone)
    frame = int(now * 3.2)
    for (x, y), (key, overlay) in _chunk_items(layers["anim_k"], tx0, ty0, tx1, ty1):
        lst = tiles[key]
        dest = (x * T - cam_x, y * T - cam_y)
        f = int(now * 9) if key == "waterfall" else frame + x + y * 2
        view.blit(lst[f % len(lst)], dest)
        if overlay is not None:
            view.blit(overlay, dest)

    # spray rising from the plunge pool under each waterfall
    for (wx, wy) in getattr(area, "waterfalls", ()):
        if tx0 - 1 <= wx <= tx1 + 1 and ty0 - 1 <= wy <= ty1 + 2:
            bx, by = (wx + 0.5) * T - cam_x, (wy + 1) * T - cam_y + 3
            for i in range(7):
                ph = (now * 0.9 + i / 7.0) % 1.0
                mx = bx + math.sin(i * 2.4 + now * 1.3) * 7 * (0.4 + ph)
                my = by - ph * 9 + (i % 3)
                view.blit(_mist_sprite(int((1.0 - ph) * 3.99)), (int(mx) - 3, int(my) - 3))

    # dungeon gates (barred or raised) and, once won, the way home
    dyn_lights = []
    if area.kind == "chamber":
        dx, dy = area.door
        view.blit(tiles["door_closed" if area.solid[dy][dx] else "door_open"], (dx * T - cam_x, dy * T - cam_y))
        if not area.solid[dy][dx]:
            view.blit(tiles["exit"], (dx * T - cam_x, dy * T - cam_y))
            dyn_lights.append((dx + 0.5, dy + 0.6, (255, 236, 190), 3.6))
    if area.kind == "dungeon":
        for (dx, dy) in area.doors:
            view.blit(tiles["door_closed" if area.solid[dy][dx] else "door_open"], (dx * T - cam_x, dy * T - cam_y))
        if dungeon_state(area)["done"]:
            fx, fy = area.final_exit
            view.blit(tiles["exit"], (fx * T - cam_x, fy * T - cam_y))
            dyn_lights.append((fx + 0.5, fy + 0.5, (255, 236, 190), 3.4))
            rx, ry = area.reward_tile
            dyn_lights.append((rx + 0.5, ry + 0.5, (255, 214, 120), 2.6))

    # y-sorted: tall objects, chests, foes, the player
    draws = []
    spawn_rings = []
    for _xy, (img, ox, oy, sort_y) in _chunk_items(layers["tall_k"], max(0, tx0 - 5), ty0,
                                                    min(area.w - 1, tx1 + 2), min(area.h - 1, ty1 + 3)):
        draws.append((sort_y, 0, img, ox, oy))
    grass = worldgen.GRASS_KINDS

    def grass_front(fx, fy):
        dec = area.decor.get((fx, fy))
        if dec in grass:
            img = _pick(tiles[dec], fx, fy)
            h = 7
            return (img.subsurface((0, T - h, T, h)), fx * T, fy * T + T - h)
        return None

    for c in chests:
        img = tiles[("chest_open_" if c.opened else "chest_") + c.rarity]
        draws.append(((c.map_y + 1) * T - 1, 1, img, c.map_x * T, c.map_y * T))
    for e in enemies:
        if not e.alive:
            continue
        ex, ey = e.x * T, e.y * T + T / 2
        if ex < cam_x - 40 or ex > cam_x + vw + 40 or ey < cam_y - 10 or ey > cam_y + vh + 40:
            continue
        moving = abs(e.target_x - e.x) + abs(e.target_y - e.y) > 0.01
        frames = enemy_overworld_frames(e)
        if frames:
            facing = _HEADING_DIR.get(tuple(e.heading), "down")
            if moving:                            # step frames alternate tile to tile
                travel = abs(e.x - e.target_x) + abs(e.y - e.target_y)
                step = (1 + (e.map_x + e.map_y) % 2) if 0.2 < travel < 0.8 else 0
            else:
                step = 0
            if _enemy_kind(e) == "Shadow Lurker":    # it floats: always bobbing
                step = int(now * 3 + id(e) % 3) % 3
            elif _enemy_kind(e) == "Slime" and not moving:
                step = (0, 1, 0, 2)[int(now * 3 + id(e) % 4) % 4]
            img = frames[facing][step]
            bob = 0
        else:
            img = get_enemy_image(e)
            if img is None:
                continue
            bob = int(round(math.sin(now * 9 + id(e) % 7) * 1)) if moving else int(round(math.sin(now * 2 + id(e) % 5) * 0.6))
        age = now - getattr(e, "spawn_t", -99.0)
        if age < 0.6:                                     # a fresh wave fades in
            img = img.copy(); img.set_alpha(int(255 * age / 0.6))
            spawn_rings.append((ex, ey - 8, age / 0.6))
        if e.flee_cooldown > 0 and int(now * 8) % 2:
            img = img.copy(); img.set_alpha(110)
        w, h = img.get_size()
        draws.append((ey, 2, ("enemy", img, ex - w / 2, ey - h + 2 + bob, grass_front(int(e.x), int(e.y)))))
    npc_marks = []
    if area.id == "overworld":
        for v in villagers:
            vx, vy = v.pos()
            fx, fy = vx * T, vy * T + T / 2
            if fx < cam_x - 30 or fx > cam_x + vw + 30 or fy < cam_y - 10 or fy > cam_y + vh + 40:
                continue
            step = (1 + v.steps % 2) if v.moving and 0.15 < v.t < 0.8 else 0
            img = villager_frames(v)[v.facing][step]
            draws.append((fy, 2, ("npc", img, fx - 8, fy - img.get_height(), None)))
            q = v.quest
            mark = None if q is None else {"offer": "alert_item", "active": "bubble_dots",
                                           "ready": "bubble_q"}.get(q["status"])
            if mark:
                npc_marks.append((mark, fx, fy - 20))
    pf = player_sprites()[_pm["facing"]]
    if _pm["moving"]:
        step = 1 + _pm["steps"] % 2 if 0.15 < _pm["t"] < 0.8 else 0
    elif _pm["bump"] > 0:
        step = 1 + int(_pm["bump"] * 10) % 2
    else:
        step = 0
    lift = 0
    if _pm["moving"] and _pm["hop"]:
        step = 1 if _pm["t"] < 0.5 else 2                 # legs tucked on the way up, out on the way down
        lift = int(round(math.sin(math.pi * _pm["t"]) * LEDGE_HOP_HEIGHT))
    pimg = pf[step]
    pxw, pyb = player_x * T, player_y * T + T / 2
    if _pm["bump"] > 0:
        bdx, bdy = _DIR_VEC[_pm["facing"]]
        pxw += bdx; pyb += bdy
    draws.append((pyb, 3, ("player", pimg, pxw - 8, pyb - pimg.get_height() - lift,
                           None if lift else grass_front(*player_tile()))))
    landed = _pm.get("landed")
    if landed:
        (lx, ly), lt = landed
        age = now - lt
        if age > 0.35:
            _pm["landed"] = None
        else:
            k = age / 0.35
            for side in (-1, 1):
                for j in range(2):
                    dx_ = side * (3 + 7 * k + j * 3)
                    view.blit(_mist_sprite(max(0, int((1 - k) * 3.99) - j)),
                              (int((lx + 0.5) * T + dx_) - 3 - cam_x, int((ly + 1) * T - 3 - 2 * k) - 3 - cam_y))
    _ambience.draw_ground(view, (cam_x, cam_y))         # footprints, glints, birds on the ground
    draws.sort(key=lambda d: (d[0], d[1]))
    shadow, shadow_big = tiles["shadow"], tiles["shadow_big"]
    for d in draws:
        if d[1] < 2:
            _, _, img, ox, oy = d
            view.blit(img, (int(ox) - cam_x, int(oy) - cam_y))
            continue
        kind, img, ox, oy, front = d[2]
        sh = shadow_big if kind == "enemy" and img.get_width() > 20 else shadow
        foot_y = d[0]
        view.blit(sh, (int(ox + img.get_width() / 2 - 8) - cam_x, int(foot_y) - 5 - cam_y))
        view.blit(img, (int(ox) - cam_x, int(oy) - cam_y))
        if front:
            fimg, fx, fy = front
            view.blit(fimg, (fx - cam_x, fy - cam_y))
    rustle = _pm.get("rustle")
    if rustle:
        (gx, gy), gkind, gt = rustle
        age = now - gt
        if age > 0.3:
            _pm["rustle"] = None
        else:
            col = _GRASS_LEAF.get(gkind, (120, 196, 92))
            for i in range(4):
                ang = -math.pi / 2 + (i - 1.5) * 0.7
                d_ = 2 + 9 * age / 0.3
                lx_ = (gx + 0.5) * T + math.cos(ang) * d_ - cam_x
                ly_ = (gy + 0.7) * T + math.sin(ang) * d_ + 14 * age * age / 0.09 * 0.3 - cam_y
                view.fill(col, (int(lx_), int(ly_), 2 if i % 2 else 1, 1))
    for (mark, mx_, my_) in npc_marks:
        img = tiles[mark]
        bob_ = int(round(math.sin(now * 3 + mx_ * 0.1) * 1.5))
        view.blit(img, (int(mx_) - img.get_width() // 2 - cam_x, int(my_) - img.get_height() - 1 + bob_ - cam_y))
    al = _pm.get("alert")
    if al:
        img = tiles["alert_item" if al[0] == "item" else "alert"]
        age = al[1]
        pop = -3 if age < 0.07 else (1 if age < 0.13 else 0)          # springs up, settles
        bx = int(player_x * T) - img.get_width() // 2 - cam_x
        by = int(player_y * T + T / 2) - 20 - img.get_height() - 1 + pop - cam_y
        view.blit(img, (bx, by))
    for (rx_, ry_, k) in spawn_rings:
        pygame.draw.circle(view, (230, 90, 70), (int(rx_ - cam_x), int(ry_ - cam_y)), int(4 + 14 * k), 1)
    _ambience.draw_air(view, (cam_x, cam_y))            # weather, smoke, birds overhead

    # lighting
    if area.outdoor:
        ambient, day = _outdoor_ambient()
        torch = 1.0 - day
    else:
        ambient, torch = CAVE_AMBIENT.get(area.theme, (40, 40, 48)), 1.0
        if area.kind == "chamber":                       # an arena: lit well enough to fight in
            ambient = lerp_color(ambient, (176, 168, 184), 0.55)
    lit = view.get_size()
    light = _view_cache.get(("light", lit))
    if light is None:
        light = pygame.Surface(lit)
        _view_cache[("light", lit)] = light
    light.fill(ambient)
    if area.outdoor and get_day_factor() > 0.15:
        cloud = _cloud_sprite()
        drift = now * 6.0
        span = area.w * T + 320
        for i, (sx, sy) in enumerate(((60, 80), (520, 330), (980, 140), (1340, 620), (300, 860))):
            cx = (sx + drift * (0.8 + i * 0.12)) % span - 160 - cam_x
            cy = (sy + i * 37) % (area.h * T) - cam_y
            if -170 < cx < vw and -100 < cy < vh:
                light.blit(cloud, (int(cx), int(cy)), special_flags=pygame.BLEND_RGB_SUB)
    if torch > 0.05:
        flick = 1.0 + 0.035 * math.sin(now * 13) + 0.02 * math.sin(now * 29)
        rad = torch_radius() * T * flick
        col = (255, 214, 160) if not area.outdoor else (170, 160, 140)
        col = tuple(int(c * min(1.0, torch * 1.2)) for c in col)
        spr = _light_sprite(rad, col)
        light.blit(spr, (int(pxw - cam_x - spr.get_width() / 2), int(pyb - 8 - cam_y - spr.get_height() / 2)),
                   special_flags=pygame.BLEND_RGB_ADD)
        for (lx, ly, lcol, lrad) in light_list + dyn_lights:
            sx, sy = lx * T - cam_x, ly * T - cam_y
            r = lrad * T * (1.0 + 0.05 * math.sin(now * 5 + lx))
            if -r < sx < vw + r and -r < sy < vh + r:
                spr = _light_sprite(r, tuple(int(c * min(1.0, torch * 1.3)) for c in lcol))
                light.blit(spr, (int(sx - spr.get_width() / 2), int(sy - spr.get_height() / 2)),
                           special_flags=pygame.BLEND_RGB_ADD)
    light.blit(_vignette(lit, 0.26 if area.outdoor else 0.42), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    view.blit(light, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    _ambience.draw_glow(view, (cam_x, cam_y))           # fireflies, embers, sparks — bright in the dark


def world_camera():
    """Camera top-left in base pixels: centred on the player, clamped to the area, snapped
    to whole art pixels so the pixel art never shimmers."""
    S = world_scale()
    vw, vh = -(-SCREEN_WIDTH // S), -(-SCREEN_HEIGHT // S)
    T = TILE_PX
    cx, cy = player_x * T - vw / 2, player_y * T - 6 - vh / 2
    mw, mh = current_area.w * T, current_area.h * T
    cx = (mw - vw) / 2 if mw <= vw else max(0, min(cx, mw - vw))
    cy = (mh - vh) / 2 if mh <= vh else max(0, min(cy, mh - vh))
    return int(round(cx)), int(round(cy)), vw, vh, S


def draw_location_banner():
    now = pygame.time.get_ticks() / 1000.0
    age = now - _loc["since"]
    stage_txt = {"openworld": f"Open World  ·  Danger {_roman(current_tier())}",
                 "limitless": f"Limitless  ·  Wave {max(1, _ll['wave'])}"}.get(GAME_MODE, f"Stage {_roman(current_stage)}")
    if age < LOC_SHOW:
        # slides down, holds, slides back up
        k = min(1.0, age / 0.25, max(0.0, (LOC_SHOW - age) / 0.3))
        room = SCREEN_WIDTH - 262                         # space right of the HUD card
        name_font = font if font.size(_loc["name"])[0] + 60 <= room else small_font
        w = min(room, max(260, name_font.size(_loc["name"])[0] + 60))
        rect = pygame.Rect(0, 0, w, 64)
        rect.centerx = max(SCREEN_WIDTH // 2, 252 + w // 2)
        rect.top = int(-70 + 80 * (1 - (1 - k) ** 3))
        draw_panel(screen, rect, border_radius=6, alpha=232)
        draw_text(stage_txt, xp_font, GRIM_GOLD, screen, rect.centerx, rect.top + 14, center=True)
        draw_heading(fit_text(_loc["name"], name_font, w - 24), name_font, GRIM_GOLD_BRIGHT, screen, rect.centerx,
                     rect.top + 40, spacing=2 if name_font is font else 1, upper=False)
    else:
        txt = fit_text(f"{stage_txt}  ·  {_loc['name']}", small_font, SCREEN_WIDTH - 290)
        w = small_font.size(txt)[0] + 28
        rect = pygame.Rect(0, 8, w, 28)
        rect.centerx = max(SCREEN_WIDTH // 2, 252 + w // 2)
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (12, 9, 5, 170), bg.get_rect(), border_radius=5)
        screen.blit(bg, rect.topleft)
        pygame.draw.rect(screen, GRIM_GOLD_DEEP, rect, width=1, border_radius=5)
        draw_text(txt, small_font, GRIM_CREAM, screen, rect.centerx, rect.centery, center=True)


# --- Foe trackers ---
TRACKER_THRESHOLD = 8   # start pointing out foes once fewer than this remain


def draw_enemy_trackers(cam_x, cam_y, S):
    """Once fewer than TRACKER_THRESHOLD foes remain on the stage, mark where they are: a
    bobbing caret over foes on screen and an arrow at the screen edge for the rest. A foe
    in another area is pointed to through the cave mouth (or exit) that leads to it."""
    if GAME_MODE == "openworld":
        return                                    # foes never run out out there
    alive = [(aid, e) for aid, lst in area_enemies.items() if not aid.startswith("dungeon_")
             for e in lst if e.alive]
    if not (0 < len(alive) < TRACKER_THRESHOLD):
        return
    T = TILE_PX
    targets = {}
    for aid, e in alive:
        if aid == current_area.id:
            targets[("foe", id(e))] = [e.x, e.y - 0.9, 1, None]
        elif current_area.kind == "overworld":
            mx, my = current_area.mouths.get(aid[len("cave_"):], current_area.start)
            t = targets.setdefault(("portal", aid), [mx + 0.5, my - 1.2, 0, stage_areas[aid].name])
            t[2] += 1
        else:
            ex, ey = current_area.exit
            t = targets.setdefault(("portal", "exit"), [ex + 0.5, ey + 0.2, 0, "Exit"])
            t[2] += 1
    now = pygame.time.get_ticks() / 1000.0
    bob = int(4 * math.sin(now * 4.0))
    col = lerp_color(GRIM_BAD, (255, 190, 170), 0.5 + 0.5 * math.sin(now * 5.0))
    cxs, cys = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
    for (kind, _k), (wx, wy, count, label) in targets.items():
        sx, sy = (wx * T - cam_x) * S, (wy * T - cam_y) * S
        dist = math.hypot(wx - player_x, wy - player_y)
        if 20 < sx < SCREEN_WIDTH - 20 and 50 < sy < SCREEN_HEIGHT - 20:
            y = sy + bob
            pygame.draw.polygon(screen, col, [(sx - 9, y - 12), (sx + 9, y - 12), (sx, y)])
            pygame.draw.polygon(screen, (0, 0, 0), [(sx - 9, y - 12), (sx + 9, y - 12), (sx, y)], 1)
            if kind == "portal":
                draw_text(f"{count} foe{'s' if count != 1 else ''} inside", xp_font, GRIM_CREAM, screen,
                          int(sx), int(y - 22), center=True)
            continue
        dx, dy = sx - cxs, sy - cys
        k = min((cxs - 30) / abs(dx) if dx else 1e9, (cys - 40) / abs(dy) if dy else 1e9)
        ax, ay = cxs + dx * k, cys + dy * k
        ay = max(ay, 64)                          # below the location banner
        if ax < 256 and ay < 312:                 # never under the HUD panel or its buttons
            ax, ay = (256, ay) if abs(dx) < abs(dy) else (ax, 316)
        ang = math.atan2(dy, dx)
        tip = (ax + math.cos(ang) * 14, ay + math.sin(ang) * 14)
        l = (ax + math.cos(ang + 2.5) * 12, ay + math.sin(ang + 2.5) * 12)
        r = (ax + math.cos(ang - 2.5) * 12, ay + math.sin(ang - 2.5) * 12)
        pygame.draw.polygon(screen, col, [tip, l, r])
        pygame.draw.polygon(screen, (0, 0, 0), [tip, l, r], 1)
        tag = f"{dist:.0f}" if kind == "foe" else f"{count} · {dist:.0f}"
        draw_text(tag, xp_font, GRIM_CREAM, screen, int(ax - math.cos(ang) * 18), int(ay - math.sin(ang) * 18), center=True)


def render_explore():
    global level_up_message
    cam_x, cam_y, vw, vh, S = world_camera()
    view = _view_cache.get((vw, vh))
    if view is None:
        view = pygame.Surface((vw, vh)).convert()
        _view_cache[(vw, vh)] = view
    draw_world(view, cam_x, cam_y)
    if main_menu.gpu_layers_on() and not transition_active() and not ascension_active():
        # the graphics chip enlarges the world under everything drawn from here on
        screen.fill((0, 0, 0, 0))
        main_menu.world_layer(view, S)
    else:
        scaled = _view_cache.get(("scaled", vw, vh, S))
        if scaled is None:
            scaled = pygame.Surface((vw * S, vh * S)).convert()
            _view_cache[("scaled", vw, vh, S)] = scaled
        pygame.transform.scale(view, (vw * S, vh * S), scaled)
        screen.blit(scaled, (0, 0))

    draw_location_banner()
    draw_enemy_trackers(cam_x, cam_y, S)
    draw_explore_hud()


def draw_explore_hud():
    global level_up_message
    # Draw Player UI — a frosted-glass magic HUD card
    player_elem = player_stats["element"]; elem_color = ELEMENT_COLORS.get(player_elem, WHITE)
    has_icon = player_elem in element_icons
    hud_rect = pygame.Rect(10, 10, 230, 210 if has_icon else 195)
    draw_panel(screen, hud_rect, border_radius=6, alpha=200)
    add_click(hud_rect, pygame.K_m, tip="Open the Codex  [M]")
    cx = hud_rect.x + 14; bar_w = hud_rect.width - 28; cy = hud_rect.y + 12

    hp_ratio = player_stats["hp"] / player_stats["max_hp"]
    draw_magic_bar(screen, cx, cy, bar_w, 20, hp_ratio, fill_top=BAR_HP_TOP, fill_bottom=BAR_HP_BOT,
                    glow_color=BAR_HP_GLOW, bar_id="player_hp", label=f"HP {player_stats['hp']}/{player_stats['max_hp']}",
                    label_font=small_font, pulse_phase=0.0, warn_below=0.25)
    cy += 20 + 8

    if player_stats.get("is_overcharged"):
        oc_amt = player_stats["mana"] - player_stats["max_mana"]
        mp_top, mp_bottom, mp_glow = get_overcharge_colors(player_stats["element"])
        mp_ratio = 1.0
        mp_label = f"MP {player_stats['max_mana']}+{oc_amt} OVERCHARGE"
    else:
        mp_ratio = min(player_stats["mana"], player_stats["max_mana"]) / max(1, player_stats["max_mana"])
        mp_top, mp_bottom, mp_glow = BAR_MP_TOP, BAR_MP_BOT, BAR_MP_GLOW
        mp_label = f"MP {player_stats['mana']}/{player_stats['max_mana']}"
    draw_magic_bar(screen, cx, cy, bar_w, 16, mp_ratio, fill_top=mp_top, fill_bottom=mp_bottom,
                    glow_color=mp_glow, label=mp_label, label_font=small_font, pulse_phase=1.3,
                    warn_below=0.15, warn_color=BAR_MP_GLOW,
                    surge=player_stats.get("is_overcharged", False))
    cy += 16 + 8

    draw_text(f"Level {player_stats['level']}" + (f"  {player_stats.get('race') or ''} {player_stats['class']}".rstrip() if player_stats.get("class") else ""),
              small_font, GRIM_GOLD_BRIGHT, screen, cx, cy); cy += 20
    xp_ratio = 0.0
    if player_stats["xp_to_next_level"] > 0: xp_ratio = max(0.0, min(1.0, player_stats["xp"] / player_stats["xp_to_next_level"]))
    draw_magic_bar(screen, cx, cy, bar_w, 14, xp_ratio, fill_top=BAR_XP_TOP, fill_bottom=BAR_XP_BOT,
                    glow_color=GRIM_XP, label=f"{player_stats['xp']}/{player_stats['xp_to_next_level']}",
                    label_font=xp_font, pulse_phase=2.6)
    cy += 14 + 10

    elem_label_color = elem_color if sum(elem_color[:3]) > 60 else lighten(elem_color, 0.5)
    if has_icon:
        side = rune_side(32)
        draw_rune(screen, (cx + side // 2, cy + side // 2), player_elem, size=32)
        # Name sits to the right of the tile, vertically centred on it
        draw_text(player_elem, small_font, elem_label_color, screen,
                  cx + side + 8, cy + side // 2 - small_font.get_height() // 2)
        cy += side + 6
    else:
        draw_text(f"Element: {player_elem}", small_font, elem_label_color, screen, cx, cy); cy += 20
    draw_text(f"•  Spins: {player_stats['reroll_spins']}", small_font, GRIM_XP, screen, cx, cy); cy += 20
    # Remaining foes — so the player knows how many stragglers stand between them and the
    # next stage (the stage clears the instant this hits zero).
    if GAME_MODE == "openworld":
        tier = current_tier()
        draw_text(f"•  Danger {_roman(tier)}  ·  Day {_world_day[0]}", small_font,
                  lerp_color(GRIM_CREAM, GRIM_BAD, (tier - 1) / max(1, OPEN_MAX_TIER - 1)), screen, cx, cy)
    elif GAME_MODE == "limitless":
        draw_text(f"•  Wave {max(1, _ll['wave'])}  ·  Foes {sum(1 for e in enemies if e.alive)}", small_font,
                  GRIM_CREAM, screen, cx, cy)
    else:
        foes_left = sum(1 for e in all_stage_enemies() if e.alive)
        foe_color = GRIM_WARD if foes_left == 0 else GRIM_CREAM
        draw_text(f"•  Foes: {foes_left}", small_font, foe_color, screen, cx, cy)
    status = dungeon_status_text() or limitless_status_text()
    tab = pygame.Rect(10, hud_rect.bottom + 6, hud_rect.width if status else 120, 48 if status else 28)
    draw_panel(screen, tab, border_radius=6, alpha=200, filigree=False)
    draw_text("[Tab]  Map", small_font, GRIM_GOLD_BRIGHT if is_hovered(tab) else GRIM_GOLD, screen,
              tab.left + 12, tab.top + 14 - small_font.get_height() // 2)
    if status:                                    # dungeon / chamber progress on its own line
        draw_text(fit_text(status, xp_font, tab.width - 24), xp_font, GRIM_CREAM, screen, tab.left + 12,
                  tab.top + 27)
    add_click(tab, pygame.K_TAB, tip="Open the map  [Tab]")
    if GAME_MODE == "limitless":                  # no villages down in the chambers
        draw_notice_banner(screen)
        if level_up_message: draw_heading(level_up_message, title_font, GRIM_XP, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, spacing=3, upper=False)
        return
    qb = pygame.Rect(10, tab.bottom + 6, 150, 28)
    draw_panel(screen, qb, border_radius=6, alpha=200, filigree=False)
    draw_text("[P]  Quests", small_font, GRIM_GOLD_BRIGHT if is_hovered(qb) else GRIM_GOLD, screen,
              qb.left + 12, qb.centery - small_font.get_height() // 2)
    n_q = len(active_quests())
    if n_q:
        ready = any(q["status"] == "ready" for q in active_quests())
        pygame.draw.circle(screen, (0, 0, 0), (qb.right - 18, qb.centery), 10)
        pygame.draw.circle(screen, GRIM_XP if ready else GRIM_GOLD, (qb.right - 18, qb.centery), 9)
        draw_text(str(n_q), xp_font, (20, 14, 8), screen, qb.right - 18, qb.centery, center=True)
    add_click(qb, pygame.K_p, tip="Open the quest log  [P]")
    draw_quest_tracker()
    near = facing_interactable()
    if near and not notice_active():
        txt = f"[E]  {near[0]} {near[1]}"
        pr = pygame.Rect(0, 0, small_font.size(txt)[0] + 30, 30)
        pr.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)
        draw_panel(screen, pr, border_radius=6, alpha=215, filigree=False)
        draw_text(txt, small_font, GRIM_GOLD_BRIGHT, screen, pr.centerx, pr.centery, center=True)
        add_click(pr, pygame.K_e, hover=None)

    draw_notice_banner(screen)

    if level_up_message: draw_heading(level_up_message, title_font, GRIM_XP, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, spacing=3, upper=False)

# <<< MODIFIED RENDER COMBAT >>>
# ==================== Battle screen (Pokémon-DS style) ====================
# The foe stands on a platform at the top right with its info box opposite; the hero is
# seen from behind on a platform at the bottom left, info box beside them. A text box and a
# command grid fill the bottom, and the backdrop matches where the fight broke out.
BATTLE_BOX_H = 168
BATTLE_SLIDE = 0.55                # seconds for the combatants to slide in
_battle = {"t0": -99.0}
_BATTLE_SKY = {"meadow": ((112, 178, 238), (204, 232, 250)), "tundra": ((160, 190, 226), (232, 240, 250)),
               "desert": ((232, 168, 96), (250, 224, 166)), "volcanic": ((60, 32, 34), (150, 76, 48)),
               "storm": ((52, 52, 90), (126, 116, 168))}
_BATTLE_HILLS = {"meadow": (70, 130, 80), "tundra": (180, 196, 218), "desert": (206, 150, 92),
                 "volcanic": (54, 40, 40), "storm": (66, 64, 96)}
_BATTLE_DECOR = {"meadow": "tree", "tundra": "pine", "desert": "cactus", "volcanic": "deadtree", "storm": "crystal"}
_CAVE_DECOR = {"meadow": "stalagmite", "tundra": "icespike", "desert": "pillar", "volcanic": "stalagmite",
               "storm": "crystal", "dungeon": "pillar"}
_ACTION_STYLE = {   # kind: (label, key, accent)
    "skills": ("Skills", pygame.K_w, (196, 72, 62)), "melee": ("Melee", pygame.K_a, (214, 132, 52)),
    "defend": ("Defend", pygame.K_d, (86, 156, 92)), "charge": ("Charge", pygame.K_c, (78, 120, 210)),
    "awaken": ("Awaken", pygame.K_v, (212, 175, 55)), "flee": ("Flee", pygame.K_f, (118, 128, 150)),
    "items": ("Items", pygame.K_i, (150, 92, 196)),
}
_ACTION_GRID = [["skills", "melee"], ["defend", "charge"], ["items", "awaken"], ["flee"]]


def battle_layout():
    W, H = SCREEN_WIDTH, SCREEN_HEIGHT
    field = H - BATTLE_BOX_H
    return {"W": W, "H": H, "field": field,
            "ex": W * 0.72, "ey": field * 0.53,          # foe's platform centre
            "px": W * 0.27, "py": field * 0.93}          # hero's platform centre


def battle_theme():
    """(biome / cave theme, outdoors?) for wherever the player is standing."""
    a = current_area
    if a is None:
        return "meadow", True
    if not a.outdoor:
        return a.theme, False
    tx, ty = player_tile()
    return _art_biome(a, tx, ty), True


def _battle_backdrop(theme, outdoor):
    L = battle_layout()
    amb = _outdoor_ambient()[0] if outdoor else (255, 255, 255)
    key = ("battle_bg", theme, outdoor, tuple(c // 12 for c in amb), L["W"], L["H"])
    bg = _view_cache.get(key)
    if bg is not None:
        return bg
    for k in [k for k in _view_cache if isinstance(k, tuple) and k and k[0] == "battle_bg"]:
        del _view_cache[k]
    tiles = world_tiles()
    W, field = L["W"], L["field"]
    bg = pygame.Surface((W, field)).convert()
    horizon = int(field * 0.34)
    T4 = TILE_PX * 4
    if outdoor:
        top, bot = _BATTLE_SKY.get(theme, _BATTLE_SKY["meadow"])
        for y in range(horizon):
            pygame.draw.line(bg, lerp_color(top, bot, y / max(1, horizon - 1)), (0, y), (W, y))
        hills = _BATTLE_HILLS.get(theme, (80, 120, 80))
        for x in range(0, W, 2):
            hgt = 26 + 14 * math.sin(x * 0.013) + 9 * math.sin(x * 0.031 + 1.7)
            pygame.draw.rect(bg, hills, (x, int(horizon - hgt), 2, int(hgt) + 1))
        ground = tiles[worldgen.BIOMES.get(theme, worldgen.BIOMES["meadow"])["ground"]]
        haze = bot
    else:
        face = tiles["cface_" + theme]
        for y in range(0, horizon, T4):
            for x in range(0, W, T4):
                bg.blit(pygame.transform.scale(_pick(face, x // T4, y // T4), (T4, T4)), (x, y))
        ground = tiles["cfloor_" + theme]
        haze = (0, 0, 0)
    for y in range(horizon, field, T4):
        for x in range(0, W, T4):
            bg.blit(pygame.transform.scale(_pick(ground, x // T4, y // T4), (T4, T4)), (x, y))
    # distance haze toward the horizon
    for y in range(horizon, min(field, horizon + 120)):
        k = 1.0 - (y - horizon) / 120.0
        line = pygame.Surface((W, 1)); line.fill(haze); line.set_alpha(int(150 * k * k))
        bg.blit(line, (0, y))
    # a line of the biome's own trees / rocks / crystals along the horizon
    deco = tiles.get(_BATTLE_DECOR.get(theme) if outdoor else _CAVE_DECOR.get(theme))
    if deco is not None or not outdoor:
        rng = random.Random(hash(theme) & 0xFFFF)
        x = rng.randint(-20, 30)
        while x < W:
            img = _object_sprite(current_area, _CAVE_DECOR[theme], x, 0) if not outdoor else (
                _pick(deco, x, 0) if isinstance(deco, list) else deco)
            if img is not None:
                sc = 3 if outdoor else 4
                big = pygame.transform.scale(img, (img.get_width() * sc, img.get_height() * sc))
                big.fill((175, 180, 190), special_flags=pygame.BLEND_RGB_MULT)   # distant: dimmer
                bg.blit(big, (x, horizon - big.get_height() + 10))
            x += rng.randint(70, 150)
    if outdoor:
        tint = pygame.Surface(bg.get_size()); tint.fill(amb)
        bg.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    else:
        # torch-lit cavern: light pooled around the two platforms, dark at the edges
        lightmap = pygame.Surface(bg.get_size()); lightmap.fill(CAVE_AMBIENT.get(theme, (50, 50, 60)))
        for cx, cy, r in ((L["ex"], L["ey"], 230), (L["px"], L["py"], 280)):
            spr = _light_sprite(r, (255, 220, 170))
            lightmap.blit(spr, (int(cx - r), int(cy - r)), special_flags=pygame.BLEND_RGB_ADD)
        bg.blit(lightmap, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    _view_cache[key] = bg
    return bg


def _platform(surface, cx, cy, rx, ry, base):
    """An oval patch of ground for a combatant to stand on."""
    rect = pygame.Rect(0, 0, int(rx * 2), int(ry * 2)); rect.center = (int(cx), int(cy))
    pygame.draw.ellipse(surface, darken(base, 0.45), rect.inflate(10, 6))
    pygame.draw.ellipse(surface, darken(base, 0.15), rect)
    pygame.draw.ellipse(surface, lighten(base, 0.18), rect.inflate(-int(rx * 0.5), -int(ry * 0.6)))
    pygame.draw.ellipse(surface, darken(base, 0.55), rect, 2)


def _bar_row(x, y, w, h, ratio, top, bottom, glow, label=None, bar_id=None, surge=False, warn=0.0):
    draw_magic_bar(screen, x, y, w, h, max(0.0, min(1.0, ratio)), fill_top=top, fill_bottom=bottom,
                   glow_color=glow, bar_id=bar_id, label=label, label_font=xp_font if h < 18 else small_font,
                   pulse_phase=0.0, warn_below=warn, surge=surge)


def render_combat():
    global level_up_message
    L = battle_layout()
    W, H, field = L["W"], L["H"], L["field"]
    now = pygame.time.get_ticks() / 1000.0
    theme, outdoor = battle_theme()
    screen.blit(_battle_backdrop(theme, outdoor), (0, 0))
    _draw_battle_ambience(theme, outdoor, L, now)
    k = min(1.0, max(0.0, (now - _battle["t0"]) / BATTLE_SLIDE))
    slide = (1 - k) ** 3                                  # ease-out
    tiles = world_tiles()
    ground_key = worldgen.BIOMES.get(theme, worldgen.BIOMES["meadow"])["ground"] if outdoor else "cfloor_" + theme
    plat_col = tuple(pygame.transform.average_color(tiles[ground_key][0])[:3])
    if not outdoor:
        plat_col = darken(plat_col, 0.15)
    enemy = current_enemy_encounter

    # --- the foe: platform + sprite, sliding in from the left ---
    ex, ey = L["ex"] - slide * W * 0.9, L["ey"]
    _platform(screen, ex, ey, 128, 30, plat_col)
    if enemy:
        img = enemy_battle_sprite(enemy)
        sc = 4 if enemy.is_boss else 3
        if img is None:
            img, sc = get_enemy_image(enemy), 5
        if img:
            big = pygame.transform.scale(img, (img.get_width() * sc, img.get_height() * sc))
            since = kill_hold_landed() if _kill_hold["victory"] else None
            if since is not None:                         # slain: fades behind the death burst
                big.set_alpha(int(255 * max(0.0, 1.0 - since / 0.6)))
            bob = int(3 * math.sin(now * 2.2))
            screen.blit(big, (int(ex - big.get_width() / 2), int(ey + 14 - big.get_height() + bob)))

    # --- the hero, from behind, sliding in from the right ---
    px, py = L["px"] + slide * W * 0.9, L["py"]
    _platform(screen, px, py, 150, 34, plat_col)
    back = player_battle_sprite()
    sc = 4                                     # nearer the camera, so larger than the foe
    hero = pygame.transform.scale(back, (back.get_width() * sc, back.get_height() * sc))
    if combat_turn == "hold" and not _kill_hold["victory"]:
        since = kill_hold_landed()
        if since is not None:
            hero.set_alpha(int(255 * max(0.25, 1.0 - since / 0.8)))
    breath = int(2 * math.sin(now * 2.0 + 1.3))
    screen.blit(hero, (int(px - hero.get_width() / 2), int(py + 16 - hero.get_height() + breath)))

    # spells fly between the two, over the field but under the boxes
    draw_vfx(screen)

    # --- foe info box (top left) ---
    if enemy:
        box = pygame.Rect(int(20 - slide * W * 0.6), 18, 310, 112)
        is_boss = enemy.is_boss
        draw_panel(screen, box, bg_color=(28, 12, 10) if is_boss else GRIM_PANEL,
                   border_color=GRIM_BOSS if is_boss else GRIM_GOLD_DIM, border_radius=8, alpha=225,
                   glow_color=GRIM_BOSS if is_boss else GRIM_GOLD, filigree=False)
        name = getattr(enemy, "base_name", enemy.name)
        draw_text(name, font, GRIM_BOSS if is_boss else GRIM_GOLD_BRIGHT, screen, box.left + 16, box.top + 8)
        nx = box.left + 16 + font.size(name)[0] + 10
        if is_boss:
            chip = pygame.Rect(nx, box.top + 14, small_font.size("BOSS")[0] + 14, 20)
            pygame.draw.rect(screen, (40, 12, 10), chip, border_radius=4)
            pygame.draw.rect(screen, GRIM_BOSS, chip, width=1, border_radius=4)
            draw_text("BOSS", small_font, GRIM_GOLD_BRIGHT, screen, chip.centerx, chip.centery, center=True)
        el = enemy.element
        if el in element_icons:
            draw_rune(screen, (box.right - 24, box.top + 24), el, size=26)
        _bar_row(box.left + 16, box.top + 46, box.width - 32, 18, enemy.hp / enemy.max_hp,
                 BAR_HP_TOP, BAR_HP_BOT, BAR_HP_GLOW, f"HP {enemy.hp}/{enemy.max_hp}", bar_id="enemy_hp", warn=0.25)
        _bar_row(box.left + 16, box.top + 70, box.width - 32, 12, enemy.mana / max(1, enemy.max_mana),
                 BAR_MP_TOP, BAR_MP_BOT, BAR_MP_GLOW, f"MP {enemy.mana}/{enemy.max_mana}")
        ecol = ELEMENT_COLORS.get(el, GRIM_GOLD)
        lv_txt = f"Lv {enemy.level}  ·  " if getattr(enemy, "level", None) else ""
        draw_text(lv_txt, xp_font, GRIM_CREAM, screen, box.left + 16, box.top + 88)
        draw_text(f"{el}", xp_font, lighten(ecol, 0.45), screen, box.left + 16 + xp_font.size(lv_txt)[0], box.top + 88)
        stat = f"ATK {enemy.attack}  ·  DEF {enemy.defense}"
        draw_text(stat, xp_font, GRIM_CREAM_DIM, screen, box.right - 16 - xp_font.size(stat)[0], box.top + 88)

    # --- hero info box (right, above the text box) ---
    pbox = pygame.Rect(int(W - 330 + slide * W * 0.6), field - 136, 312, 128)
    draw_panel(screen, pbox, border_radius=8, alpha=225, filigree=False)
    who = " ".join(x for x in (player_stats.get("race"), player_stats.get("class")) if x) or "Hero"
    draw_text(who, small_font, GRIM_GOLD_BRIGHT, screen, pbox.left + 16, pbox.top + 8)
    lv = f"Lv {player_stats['level']}"
    draw_text(lv, small_font, GRIM_CREAM, screen, pbox.right - 50 - small_font.size(lv)[0], pbox.top + 8)
    pel = player_stats["element"]
    if pel in element_icons:
        draw_rune(screen, (pbox.right - 26, pbox.top + 20), pel, size=24)
    _bar_row(pbox.left + 16, pbox.top + 36, pbox.width - 32, 18, player_stats["hp"] / player_stats["max_hp"],
             BAR_HP_TOP, BAR_HP_BOT, BAR_HP_GLOW, f"HP {player_stats['hp']}/{player_stats['max_hp']}",
             bar_id="player_hp", warn=0.25)
    if player_stats.get("is_overcharged"):
        oc = player_stats["mana"] - player_stats["max_mana"]
        mt, mb, mg = get_overcharge_colors(pel)
        mratio = 1.0 if oc > 0 else max(0, player_stats["mana"]) / max(1, player_stats["max_mana"])
        mlabel = (f"MP {player_stats['max_mana']}+{oc} OVERCHARGE" if oc > 0
                  else f"MP {player_stats['mana']}/{player_stats['max_mana']} OVERCHARGE")
    else:
        mt, mb, mg = BAR_MP_TOP, BAR_MP_BOT, BAR_MP_GLOW
        mratio = min(player_stats["mana"], player_stats["max_mana"]) / max(1, player_stats["max_mana"])
        mlabel = f"MP {player_stats['mana']}/{player_stats['max_mana']}"
    _bar_row(pbox.left + 16, pbox.top + 60, pbox.width - 32, 14, mratio, mt, mb, mg, mlabel,
             surge=player_stats.get("is_overcharged", False))
    xr = player_stats["xp"] / player_stats["xp_to_next_level"] if player_stats["xp_to_next_level"] else 0
    _bar_row(pbox.left + 16, pbox.top + 80, pbox.width - 32, 6, xr, BAR_XP_TOP, BAR_XP_BOT, GRIM_XP)
    status = []
    if player_stats["is_awakened"]:
        status.append((f"AWAKENED {player_stats['awakening_duration']}", GRIM_XP))
    elif player_stats["awakening_cooldown"] > 0:
        status.append((f"Awaken CD {player_stats['awakening_cooldown']}", GRIM_CREAM_FAINT))
    if player_stats["is_defending"]:
        status.append(("Defending", GRIM_WARN))
    if has_vow(V_BERSERKER):
        status.append((f"Berserk +{berserker_bonus_pct()}%", GRIM_HP if berserker_bonus_pct() else GRIM_CREAM_FAINT))
    if player_stats.get("is_god"):
        status.append(("GOD", GRIM_WARD))
    if player_stats.get("luck", 0) > 0:
        status.append((f"Luck +{player_stats['luck']}%", GRIM_XP))
    sx = pbox.left + 16
    stat_line = f"MEL {calculate_total_stats()['melee_strength']} · ELE {calculate_total_stats()['element_strength']} · DEF {calculate_total_stats()['defense']}"
    draw_text(stat_line, xp_font, GRIM_CREAM_DIM, screen, sx, pbox.top + 94)
    sx2 = sx
    for txt, col in status:
        if sx2 + xp_font.size(txt)[0] > pbox.right - 12:
            break
        draw_text(txt, xp_font, col, screen, sx2, pbox.top + 109)
        sx2 += xp_font.size(txt)[0] + 12

    # --- the bottom: text box + commands ---
    box_top = field
    pygame.draw.rect(screen, (8, 6, 4), (0, box_top, W, BATTLE_BOX_H))
    pygame.draw.line(screen, GRIM_GOLD, (0, box_top), (W, box_top), 2)
    showing_skills = (combat_turn == 'player' and not is_in_combat_delay
                      and combat_sub_state == COMBAT_SUBSTATE_CHOOSE_SKILL)
    showing_items = (combat_turn == 'player' and not is_in_combat_delay
                     and combat_sub_state == COMBAT_SUBSTATE_CHOOSE_ITEM)
    commands = combat_turn == 'player' and not is_in_combat_delay
    msg_rect = pygame.Rect(12, box_top + 12, (W - 24) if not commands and combat_turn != "hold" else int(W * 0.58), BATTLE_BOX_H - 24)
    if showing_skills:
        _draw_skill_picker(pygame.Rect(12, box_top + 12, W - 24, BATTLE_BOX_H - 24))
    elif showing_items:
        _draw_item_picker(pygame.Rect(12, box_top + 12, W - 24, BATTLE_BOX_H - 24))
    else:
        draw_panel(screen, msg_rect, border_radius=8, alpha=240, glow=False)
        text = combat_message or ("What will you do?" if commands else "")
        msg_font = small_font
        lines = wrap_text(text, msg_font, msg_rect.width - 36)
        if len(lines) > 4:
            msg_font = xp_font
            lines = wrap_text(text, msg_font, msg_rect.width - 36)
        lines = lines[:5]
        lh = msg_font.get_height() + 4
        for i, line in enumerate(lines):
            draw_text(line, msg_font, GRIM_CREAM, screen, msg_rect.left + 18, msg_rect.top + 14 + i * lh)
        if is_in_combat_delay and int(now * 2.5) % 2:     # Pokémon's "more to come" arrow
            ax, ay = msg_rect.right - 24, msg_rect.bottom - 20
            pygame.draw.polygon(screen, GRIM_GOLD_BRIGHT, [(ax - 7, ay - 4), (ax + 7, ay - 4), (ax, ay + 4)])
        side = pygame.Rect(msg_rect.right + 10, msg_rect.top, W - 12 - msg_rect.right - 10, msg_rect.height)
        if combat_turn == 'hold':
            since = kill_hold_landed()
            if since is not None:
                won = _kill_hold["victory"]
                draw_panel(screen, side, border_radius=8, alpha=240, glow=False,
                           border_color=GRIM_XP if won else GRIM_BAD)
                draw_heading("Victory" if won else "Defeated", title_font, GRIM_XP if won else GRIM_BAD,
                             screen, side.centerx, side.centery - 14, spacing=4)
                if since > 0.3:
                    draw_text("[Space / Click] Continue", xp_font, GRIM_CREAM_FAINT, screen,
                              side.centerx, side.centery + 24, center=True)
            add_click(screen.get_rect(), pygame.K_SPACE, hover=None)
        elif commands and combat_sub_state == COMBAT_SUBSTATE_CHOOSE_ACTION:
            _draw_command_grid(side)

    if _bonus_turn["active"] and commands:
        txt = "OVERCHARGE  ·  BONUS ELEMENTAL STRIKE"
        oc = get_overcharge_colors(player_stats["element"])[0]
        tag = pygame.Rect(0, 0, small_font.size(txt)[0] + 40, 26)
        tag.midbottom = (W // 2, box_top - 6)
        pulse = 0.5 + 0.5 * math.sin(now * 6)
        draw_glow_rect(screen, tag, oc, border_radius=13, layers=3, max_alpha=int(40 + 50 * pulse), spread=3)
        pygame.draw.rect(screen, darken(oc, 0.6), tag, border_radius=13)
        pygame.draw.rect(screen, lighten(oc, 0.35), tag, width=2, border_radius=13)
        draw_text(txt, small_font, (255, 255, 255), screen, tag.centerx, tag.centery, center=True)

    # callouts and level-ups float over the field
    draw_signals(screen, W // 2, int(field * 0.40), kinds=COMBAT_SIGNALS, max_lines=2)
    if level_up_message and not showing_skills:
        draw_heading(level_up_message, title_font, GRIM_XP, screen, W // 2, int(field * 0.20), spacing=3, upper=False)
    draw_vfx_overlay(screen)


def _draw_command_grid(area):
    """Pokémon's command menu: the actions in a two-column grid (a lone last action spans
    both columns), greyed when unavailable."""
    gap = 6
    rows = len(_ACTION_GRID)
    cw = (area.width - gap) // 2
    ch = (area.height - gap * (rows - 1)) // rows
    for r, row in enumerate(_ACTION_GRID):
        for c, kind in enumerate(row):
            label, key, accent = _ACTION_STYLE[kind]
            if kind == "charge" and player_stats.get("is_overcharged"):
                label, accent = "Overcharged", get_overcharge_colors(player_stats["element"])[0]
            cell = pygame.Rect(area.left + c * (cw + gap), area.top + r * (ch + gap),
                               cw if len(row) > 1 else area.width, ch)
            blocked = combat_action_block(kind)
            hot = is_hovered(cell) and not blocked
            fill = darken(accent, 0.72) if blocked else (darken(accent, 0.25) if hot else darken(accent, 0.45))
            if hot:
                draw_glow_rect(screen, cell, accent, border_radius=8, layers=3, max_alpha=55, spread=3)
            pygame.draw.rect(screen, fill, cell, border_radius=8)
            pygame.draw.rect(screen, lighten(accent, 0.3) if not blocked else darken(accent, 0.5), cell,
                             width=2, border_radius=8)
            txt_col = GRIM_CREAM_FAINT if blocked else (255, 255, 255)
            draw_text(label, small_font, txt_col, screen, cell.centerx, cell.centery, center=True)
            draw_text(pygame.key.name(key).upper(), xp_font, darken(txt_col, 0.2) if not blocked else GRIM_CREAM_FAINT,
                      screen, cell.left + 8, cell.top + 4)
            add_click(cell, key, hover=None)


def _draw_skill_picker(area):
    """Move selection: the element's skills in a grid, details of the one under the cursor."""
    el = player_stats["element"]
    skills = ELEMENT_SKILLS.get(el, DEFAULT_SKILLS)[:8]
    info = pygame.Rect(area.right - 232, area.top, 232, area.height)
    grid = pygame.Rect(area.left, area.top, area.width - 242, area.height)
    rows = max(1, (len(skills) + 1) // 2)
    gap = 6
    cw = (grid.width - gap) // 2
    ch = min(56, (grid.height - gap * (rows - 1)) // rows)
    ecol = ELEMENT_COLORS.get(el, GRIM_GOLD)
    accent = ecol if sum(ecol[:3]) > 90 else lighten(ecol, 0.5)
    focus = 0
    for i, sk in enumerate(skills):
        cell = pygame.Rect(grid.left + (i % 2) * (cw + gap), grid.top + (i // 2) * (ch + gap), cw, ch)
        if is_hovered(cell):
            focus = i
    for i, sk in enumerate(skills):
        cell = pygame.Rect(grid.left + (i % 2) * (cw + gap), grid.top + (i // 2) * (ch + gap), cw, ch)
        cost = get_skill_mana_cost(el, sk["name"])
        cd = 0 if player_stats.get("cooldowns_disabled") else player_stats["skill_cooldowns"].get(sk["name"], 0)
        usable = cd == 0 and skill_affordable(cost)
        hot = i == focus and usable
        base = darken(accent, 0.55 if usable else 0.78)
        if hot:
            draw_glow_rect(screen, cell, accent, border_radius=8, layers=3, max_alpha=55, spread=3)
            base = darken(accent, 0.35)
        pygame.draw.rect(screen, base, cell, border_radius=8)
        pygame.draw.rect(screen, lighten(accent, 0.25) if usable else darken(accent, 0.4), cell, width=2, border_radius=8)
        col = (255, 255, 255) if usable else (GRIM_BAD if cd == 0 else GRIM_CREAM_FAINT)
        f = small_font if ch >= 34 else xp_font
        draw_text(fit_text(f"{i + 1}  {sk['name']}", f, cell.width - 16), f, col, screen, cell.left + 10,
                  cell.centery - f.get_height() // 2)
        add_click(cell, pygame.K_1 + i, hover=None)
    # details
    draw_panel(screen, info, border_radius=8, alpha=240, glow=False)
    sk = skills[focus]
    cost = get_skill_mana_cost(el, sk["name"])
    cd_max = get_skill_cooldown_max(el, sk["name"])
    cd = 0 if player_stats.get("cooldowns_disabled") else player_stats["skill_cooldowns"].get(sk["name"], 0)
    y = info.top + 10
    draw_text(fit_text(sk["name"], small_font, info.width - 24), small_font, GRIM_GOLD_BRIGHT, screen, info.left + 12, y); y += 23
    rows_info = [("Type", el, accent), ("Cost", skill_cost_label(cost),
                                         (GRIM_HP if has_vow(V_BLOOD_TITHE) else GRIM_MP) if skill_affordable(cost) else GRIM_BAD),
                 ("Power", f"{sk['power']:.1f}", GRIM_CREAM)]
    if cd_max and not player_stats.get("cooldowns_disabled"):
        rows_info.append(("Cooldown", f"{cd}/{cd_max}" if cd else f"{cd_max} turn{'s' if cd_max != 1 else ''}", GRIM_WARN if cd else GRIM_CREAM_DIM))
    if el != "OFA":
        mp = get_miss_chance(sk["power"])
        rows_info.append(("Miss", format_miss_chance(sk["power"]), GRIM_WARN if mp >= MISS_CHANCE_MAX * 0.7 else GRIM_CREAM_DIM))
    for lbl, val, col in rows_info:
        draw_text(lbl, xp_font, GRIM_CREAM_FAINT, screen, info.left + 12, y)
        draw_text(val, xp_font, col, screen, info.right - 12 - xp_font.size(val)[0], y)
        y += 15
    back = pygame.Rect(info.left + 12, info.bottom - 28, info.width - 24, 22)
    draw_button(screen, back, "B  Back", xp_font, hot=is_hovered(back), upper=False)
    add_click(back, pygame.K_b, hover=None)


def _draw_item_picker(area):
    """The battle bag: potions you're carrying, with what the one under the cursor does."""
    items = combat_items()[:8]
    info = pygame.Rect(area.right - 232, area.top, 232, area.height)
    grid = pygame.Rect(area.left, area.top, area.width - 242, area.height)
    accent = _ACTION_STYLE["items"][2]
    gap = 6
    rows = max(1, (len(items) + 1) // 2)
    cw = (grid.width - gap) // 2
    ch = min(56, (grid.height - gap * (rows - 1)) // rows)
    if not items:
        draw_panel(screen, grid, border_radius=8, alpha=240, glow=False)
        draw_text("Your satchel holds no potions.", small_font, GRIM_CREAM_DIM, screen, grid.centerx, grid.centery, center=True)
    focus = 0
    for i, (name, n) in enumerate(items):
        cell = pygame.Rect(grid.left + (i % 2) * (cw + gap), grid.top + (i // 2) * (ch + gap), cw, ch)
        if is_hovered(cell):
            focus = i
    for i, (name, n) in enumerate(items):
        cell = pygame.Rect(grid.left + (i % 2) * (cw + gap), grid.top + (i // 2) * (ch + gap), cw, ch)
        rcol = RARITY_COLORS.get(POTION_DATA[name]["rarity"], GRIM_CREAM)
        usable = combat_item_problem(name) is None
        hot = i == focus and usable
        base = darken(accent, 0.55 if usable else 0.78)
        if hot:
            draw_glow_rect(screen, cell, accent, border_radius=8, layers=3, max_alpha=55, spread=3)
            base = darken(accent, 0.35)
        pygame.draw.rect(screen, base, cell, border_radius=8)
        pygame.draw.rect(screen, lighten(accent, 0.25) if usable else darken(accent, 0.4), cell, width=2, border_radius=8)
        pygame.draw.circle(screen, rcol, (cell.left + 14, cell.centery), 5)          # rarity pip
        f = small_font if ch >= 34 else xp_font
        label = f"{i + 1}  {name}"
        cnt = f"x{n}"
        draw_text(fit_text(label, f, cell.width - 46 - f.size(cnt)[0]), f, (255, 255, 255) if usable else GRIM_CREAM_FAINT,
                  screen, cell.left + 26, cell.centery - f.get_height() // 2)
        draw_text(cnt, f, GRIM_GOLD_BRIGHT if usable else GRIM_CREAM_FAINT, screen,
                  cell.right - 10 - f.size(cnt)[0], cell.centery - f.get_height() // 2)
        add_click(cell, pygame.K_1 + i, hover=None)
    draw_panel(screen, info, border_radius=8, alpha=240, glow=False)
    y = info.top + 10
    if items:
        name, n = items[focus]
        data = POTION_DATA[name]
        draw_text(fit_text(name, small_font, info.width - 24), small_font, GRIM_GOLD_BRIGHT, screen, info.left + 12, y); y += 23
        for lbl, val, col in (("Rarity", data["rarity"], RARITY_COLORS.get(data["rarity"], GRIM_CREAM)),
                              ("Carrying", str(n), GRIM_CREAM)):
            draw_text(lbl, xp_font, GRIM_CREAM_FAINT, screen, info.left + 12, y)
            draw_text(val, xp_font, col, screen, info.right - 12 - xp_font.size(val)[0], y)
            y += 15
        for line in wrap_text(potion_effect_text(name), xp_font, info.width - 24)[:2]:
            draw_text(line, xp_font, GRIM_WARD, screen, info.left + 12, y); y += 15
        why = combat_item_problem(name)
        if why:
            for line in wrap_text(why, xp_font, info.width - 24)[:2]:
                draw_text(line, xp_font, GRIM_BAD, screen, info.left + 12, y); y += 15
    else:
        draw_text("Battle Bag", small_font, GRIM_GOLD_BRIGHT, screen, info.left + 12, y)
    back = pygame.Rect(info.left + 12, info.bottom - 28, info.width - 24, 22)
    draw_button(screen, back, "B  Back", xp_font, hot=is_hovered(back), upper=False)
    add_click(back, pygame.K_b, hover=None)


def vfx_potion(kind, pos):
    """Drinking in battle: restorative light rising around the hero."""
    col = {"hp": (90, 230, 120), "mp": (90, 150, 255), "both": (255, 214, 90),
           "mp_overcharge": (190, 120, 255)}.get(kind, (220, 220, 220))
    x, y = pos
    for i in range(3):
        vfx_after(i * 0.1, lambda: _vfx_add(VfxParticle("ring", x, y + 40, life=0.5, size=40, end_size=170, color=col)))
    for _ in range(22):
        _vfx_add(VfxParticle("mote", x + random.uniform(-60, 60), y + random.uniform(0, 90),
                             vy=random.uniform(-180, -70), drag=0.6, life=random.uniform(0.6, 1.0),
                             size=random.randint(10, 18), end_size=2, color=col))
    for _ in range(8):
        _vfx_add(VfxParticle("spark", x + random.uniform(-50, 50), y + random.uniform(-20, 60),
                             vy=random.uniform(-90, -30), drag=1.0, life=random.uniform(0.4, 0.7),
                             size=random.randint(10, 16), end_size=2, color=lighten(col, 0.4), spin=4.0))
    vfx_flash(col, 0.22)


def _quiet_notice():
    """Combat reports a drink in its own text box; don't leave a banner waiting outside."""
    global notice_until
    notice_until = 0


# <<< END MODIFIED RENDER COMBAT >>>


# ==================== True Form Ascension ====================
# Mastering a Tier 1 element used to be a one-line notice. It's the biggest thing that can
# happen to a build, so the first time you reach a given True form it gets a full cinematic:
# the base rune winds up, whites out, and the True form is revealed. Reaching the SAME form
# again later (after rerolling back to that element) plays only the short reveal, so the
# long version stays a first-time moment.
ASCEND_GATHER = 1.15        # base rune winding up
ASCEND_FLARE = 0.40         # white-out
ASCEND_REVEAL = 1.95        # the True form held on screen
ASCEND_SHORT = 1.15         # repeat masteries: reveal only

_ascend = {"active": False, "t": 0.0, "base": None, "true": None,
           "snap": None, "full": True, "fired": set(), "tick": 0.0}


def ascension_active():
    return _ascend["active"]


def ascension_total():
    return (ASCEND_GATHER + ASCEND_FLARE + ASCEND_REVEAL) if _ascend["full"] else ASCEND_SHORT


def begin_ascension(base, true_name, full=True):
    _ascend.update({"active": True, "t": 0.0, "base": base, "true": true_name,
                    "snap": main_menu.snapshot(screen), "full": full, "fired": set(), "tick": 0.0})
    vfx_clear()


ASCEND_SKIP_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE)


def skip_ascension():
    """First press jumps to the reveal, so a skip still shows you what you became; a
    second press dismisses it. The element was committed before the cinematic began, so
    skipping can never cost you the result."""
    if not _ascend["active"]:
        return False
    phase, p = _ascend_phase()
    if phase == "reveal":
        if p < 0.30:              # let the name land before a second tap can dismiss it
            return False
        _ascend["active"] = False
        _ascend["snap"] = None
        return True
    _ascend["t"] = ASCEND_GATHER + ASCEND_FLARE if _ascend["full"] else 0.0
    return True


def _ascend_phase():
    """(phase_name, 0..1 progress within that phase)."""
    t = _ascend["t"]
    if not _ascend["full"]:
        return "reveal", min(1.0, t / ASCEND_SHORT)
    if t < ASCEND_GATHER:
        return "gather", t / ASCEND_GATHER
    t -= ASCEND_GATHER
    if t < ASCEND_FLARE:
        return "flare", t / ASCEND_FLARE
    t -= ASCEND_FLARE
    return "reveal", min(1.0, t / ASCEND_REVEAL)


def _ascend_centre():
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)


def update_ascension(dt):
    if not _ascend["active"]:
        return
    _ascend["t"] += dt
    phase, p = _ascend_phase()
    centre = _ascend_centre()
    fired = _ascend["fired"]
    _ascend["tick"] -= dt

    if phase == "gather":
        if _ascend["tick"] <= 0:                    # energy drawn steadily inward
            _ascend["tick"] = 0.16
            vfx_charge(_ascend["base"], centre, count=7)
        if p > 0.75 and "rumble" not in fired:
            fired.add("rumble"); vfx_shake(3.0)

    elif phase == "flare":
        if "flare" not in fired:
            fired.add("flare")
            vfx_burst(_ascend["true"], centre, power=1.8, rings=3)
            vfx_flash((255, 255, 255), 0.95)
            vfx_shake(8.0)

    else:  # reveal
        if "reveal" not in fired:
            fired.add("reveal")
            vfx_burst(_ascend["true"], centre, power=1.4, rings=2)
            vfx_flash(vfx_color(_ascend["true"]), 0.40)
        if _ascend["tick"] <= 0:                    # a slow rain of the new element
            _ascend["tick"] = 0.20
            col = vfx_color(_ascend["true"])
            for _ in range(4):
                _vfx_add(VfxParticle(
                    "ember", centre[0] + random.uniform(-150, 150), centre[1] + random.uniform(20, 90),
                    vy=random.uniform(-150, -60), drag=0.8, life=random.uniform(0.7, 1.2),
                    size=random.randint(12, 26), end_size=2, color=col))

    if _ascend["t"] >= ascension_total():
        _ascend["active"] = False
        _ascend["snap"] = None


def draw_ascension():
    if not _ascend["active"]:
        return
    phase, p = _ascend_phase()
    centre = _ascend_centre()

    # Backdrop: the frozen frame, pushed down so the rune owns the screen
    if _ascend["snap"] is not None:
        screen.blit(_ascend["snap"], (0, 0))
    else:
        screen.fill((6, 4, 2))
    # Ramp down during the wind-up so you still see where you are, then go essentially
    # black — at alpha 230 the Evolution screen's gold text still read through and fought
    # with the reveal.
    veil_a = 150 + int(85 * p) if phase == "gather" else 250
    veil = pygame.Surface(screen.get_size()); veil.fill((0, 0, 0))
    veil.set_alpha(veil_a); screen.blit(veil, (0, 0))

    if phase == "gather":
        # base rune swelling and shaking as it's forced past its limit
        jitter = int(7 * p * p)
        pos = (centre[0] + random.randint(-jitter, jitter), centre[1] + random.randint(-jitter, jitter))
        draw_rune(screen, pos, _ascend["base"], size=int(104 + 34 * p))
        draw_vfx(screen)
        draw_heading(f"The {_ascend['base']} within stirs…", small_font, GRIM_CREAM_DIM,
                     screen, SCREEN_WIDTH // 2, centre[1] + 130, spacing=3, upper=False)

    elif phase == "flare":
        draw_vfx(screen)
        wash = pygame.Surface(screen.get_size()); wash.fill((255, 255, 255))
        wash.set_alpha(int(255 * math.sin(p * math.pi)))    # peaks mid-phase
        screen.blit(wash, (0, 0))

    else:
        # reveal: scale pop with a little overshoot, then hold
        k = min(1.0, p / 0.32)
        scale = 0.45 + 0.75 * k - 0.20 * math.sin(k * math.pi)
        draw_rune(screen, centre, _ascend["true"], size=max(8, int(150 * scale)))
        draw_vfx(screen)
        if p > 0.18:
            col = vfx_color(_ascend["true"])
            draw_heading("True Form", small_font, GRIM_GOLD, screen,
                         SCREEN_WIDTH // 2, centre[1] + 118, spacing=6)
            draw_heading(_ascend["true"], big_font, col, screen,
                         SCREEN_WIDTH // 2, centre[1] + 158, spacing=4)
        if p > 0.45:
            draw_heading(f"{_ascend['base']} has mastered its true nature.", small_font,
                         GRIM_CREAM_DIM, screen, SCREEN_WIDTH // 2, centre[1] + 206,
                         spacing=2, upper=False)

    draw_text("[Space] Skip", small_font, GRIM_CREAM_FAINT, screen,
              SCREEN_WIDTH - 118, SCREEN_HEIGHT - 34)
    draw_vfx_overlay(screen)
# ==================== end True Form Ascension ====================


# ==================== Element Spin ====================
# Rebinding used to swap the element instantly. Now the rune cycles through the elements
# that could actually come up, slowing on an easing curve before it lands — the outcome is
# still rolled up front, so this is presentation only and can't change what you get.
SPIN_DURATION = 1.65        # seconds of cycling before it lands
SPIN_FAST = 0.035           # seconds between swaps at the start
SPIN_SLOW = 0.30            # seconds between swaps just before it lands
SPIN_SETTLE = 0.70          # hold after landing, for the pop and the burst

_spin = {"active": False, "t": 0.0, "next": 0.0, "display": None,
         "final": None, "pool": [], "settle": 0.0, "landed": False}


def spin_active():
    return _spin["active"]


def spin_landed():
    """True once the result is showing — the [N] Continue prompt waits for this."""
    return _spin["landed"]


def spin_display_element():
    """What the reroll screen should draw right now."""
    if _spin["active"] and _spin["display"] is not None:
        return _spin["display"]
    return player_stats["element"]


def start_spin(final_element, pool):
    """Begin the wheel. `final_element` is already decided; `pool` is what flashes past."""
    _spin["active"] = True
    _spin["t"] = 0.0
    _spin["next"] = 0.0
    _spin["final"] = final_element
    _spin["pool"] = [e for e in pool if e] or [final_element]
    _spin["display"] = player_stats["element"]
    _spin["settle"] = 0.0
    _spin["landed"] = False


SPIN_SKIP_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE)


def skip_spin():
    """Fast-forward the wheel. The result was rolled the moment [Y] was pressed, so this
    only skips the presentation — it lands on exactly the same element. A second press
    during the hold dismisses the result card."""
    if not _spin["active"]:
        return False
    if _spin["landed"]:
        # Don't let a mashed key blow straight past the result you just won
        if _spin["settle"] > SPIN_SETTLE * 0.65:
            return False
        _spin["settle"] = 0.0
        _spin["active"] = False
        return True
    _spin["t"] = SPIN_DURATION      # update_spin lands it next tick, via the normal path
    return True


def cancel_spin():
    _spin["active"] = False
    _spin["landed"] = False
    _spin["display"] = None


def update_spin(dt):
    if not _spin["active"]:
        return

    if _spin["landed"]:
        _spin["settle"] -= dt
        if _spin["settle"] <= 0:
            _spin["active"] = False
        return

    _spin["t"] += dt
    _spin["next"] -= dt

    if _spin["t"] >= SPIN_DURATION:
        # Land: commit the element for real, then celebrate it
        _spin["display"] = _spin["final"]
        player_stats["element"] = _spin["final"]
        # A Tier 5 reroll swaps one Universal for another; the line it grew from stays
        record_element_change(_spin["final"], sidestep=_spin["final"] in tier5_elements)
        _spin["landed"] = True
        _spin["settle"] = SPIN_SETTLE
        centre = (SCREEN_WIDTH // 2, 198)
        vfx_burst(_spin["final"], centre, power=1.25, rings=2)
        vfx_flash(vfx_color(_spin["final"]), 0.34)
        print(f"Rebound to {_spin['final']}.")
        return

    if _spin["next"] <= 0:
        p = _spin["t"] / SPIN_DURATION
        _spin["next"] = SPIN_FAST + (SPIN_SLOW - SPIN_FAST) * (p ** 2.2)
        # never show the same face twice in a row, or the wheel looks stuck
        choices = [e for e in _spin["pool"] if e != _spin["display"]] or _spin["pool"]
        _spin["display"] = random.choice(choices)


def draw_spin_dial(centre, radius):
    """Counter-rotating arcs around the rune, slowing as the wheel does."""
    if not _spin["active"]:
        return
    cx, cy = centre
    p = min(1.0, _spin["t"] / SPIN_DURATION)
    speed = 9.0 * (1.0 - p) + 0.6            # rad/sec, eases down with the swaps
    ang = pygame.time.get_ticks() / 1000.0 * speed
    # Gold-forward so the dial stays legible even for murky elements (Earth's brown on a
    # brown ground vanished), with the element tint still showing through.
    col = lerp_color(GRIM_GOLD, vfx_color(spin_display_element()), 0.55)
    for i, (r_off, width, sweep, direction) in enumerate(
            ((16, 4, 1.5, 1), (30, 3, 1.1, -1), (44, 2, 0.8, 1))):
        r = radius + r_off
        box = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        base = ang * direction + i * 2.1
        shade = col if i == 0 else tuple(int(c * (0.75 - 0.2 * i)) for c in col)
        for k in range(2):                    # two opposed arcs per ring
            start = base + k * math.pi
            pygame.draw.arc(screen, shade, box, start, start + sweep, width)


def spin_rune_scale():
    """A quick pop on landing, so the result punches instead of just appearing."""
    if not (_spin["active"] and _spin["landed"]):
        return 1.0
    done = 1.0 - max(0.0, _spin["settle"]) / SPIN_SETTLE   # 0 -> 1 after landing
    if done >= 0.45:
        return 1.0
    k = done / 0.45
    return 1.0 + 0.35 * math.sin(k * math.pi)
# ==================== end Element Spin ====================


def render_reroll_prompt():
    fill_grim_bg(screen, top=(22, 16, 9), bottom=(6, 4, 2))
    # While the wheel turns this is the flashing face, not the committed element
    current_elem = spin_display_element(); elem_color = ELEMENT_COLORS.get(current_elem, GRIM_GOLD)
    spin_count = player_stats["reroll_spins"]
    spinning = spin_active()

    draw_heading("Enemy Vanquished", big_font, GRIM_WARD, screen, SCREEN_WIDTH // 2, 90, spacing=3)
    draw_grim_divider(screen, 135)

    # Both of these are centre-anchored, so each needs half its own height of clearance —
    # at the old spacing the element name and the spin count overlapped by ~13px.
    icon_y = 198
    rune_px = int(96 * spin_rune_scale())
    draw_rune(screen, (SCREEN_WIDTH // 2, icon_y), current_elem, size=rune_px)
    draw_spin_dial((SCREEN_WIDTH // 2, icon_y), rune_px // 2)
    label = (current_elem or "Unbound") if spinning else f"Current Element — {current_elem or 'Unbound'}"
    draw_heading(label, title_font,
                 elem_color if sum(elem_color[:3]) > 60 else lighten(elem_color, 0.5),
                 screen, SCREEN_WIDTH // 2, icon_y + 82, spacing=3, upper=False)

    won, chances = _kill_ctx.get("spins", (0, 0))
    found = f"   (+{won} from {chances} chances)" if chances else ""
    draw_text(f"•  Reroll Spins: {spin_count}{found}", font, GRIM_XP, screen, SCREEN_WIDTH // 2, 322, center=True)

    is_t5_or_higher = current_elem in tier5_elements or current_elem in tier6_elements or current_elem in tier7_elements
    reroll_cost, rebind_block, rebind_note = rebind_terms(current_elem)

    btn_w, btn_h = 250, 54
    if spinning:
        if spin_landed():
            draw_heading("Rebound!", title_font, GRIM_XP, screen, SCREEN_WIDTH // 2, 356, spacing=4)
        else:
            draw_text("Rebinding…", font, GRIM_CREAM_DIM, screen, SCREEN_WIDTH // 2, 356, center=True)
            draw_text("[Space / Click] Skip", small_font, GRIM_CREAM_FAINT, screen,
                      SCREEN_WIDTH // 2, 392, center=True)
            add_click(screen.get_rect(), pygame.K_SPACE, hover=None)
        draw_signals(screen, SCREEN_WIDTH // 2, 492, kinds=("levelup",), max_lines=1)
        draw_vfx(screen)
        draw_vfx_overlay(screen)
        return
    if rebind_block:
        draw_text(rebind_block, small_font, GRIM_BAD, screen, SCREEN_WIDTH // 2, 356, center=True)
        no_rect = pygame.Rect(0, 0, btn_w, btn_h); no_rect.center = (SCREEN_WIDTH // 2, 420)
        draw_button(screen, no_rect, "[N] Keep & Continue", small_font, hot=True)
        add_click(no_rect, pygame.K_n, hover=None)
    elif spin_count >= reroll_cost:
        if rebind_note:
            draw_text(rebind_note, small_font, GRIM_XP, screen, SCREEN_WIDTH // 2, 356, center=True)
        elif is_t5_or_higher:
            draw_text("Rebinding will draw a new Tier 5 element.", small_font, GRIM_XP, screen, SCREEN_WIDTH // 2, 356, center=True)
        else:
            draw_text("Rebinding will draw a new Tier 1 element.", small_font, GRIM_BAD, screen, SCREEN_WIDTH // 2, 356, center=True)
        yes_rect = pygame.Rect(0, 0, btn_w, btn_h); yes_rect.center = (SCREEN_WIDTH // 2 - 140, 420)
        no_rect = pygame.Rect(0, 0, btn_w, btn_h); no_rect.center = (SCREEN_WIDTH // 2 + 140, 420)
        # Rebind is the default (lit); hovering Keep moves the glow across to it
        no_hot = is_hovered(no_rect)
        cost_txt = "free" if reroll_cost == 0 else f"{reroll_cost} spin{'s' if reroll_cost != 1 else ''}"
        draw_button(screen, yes_rect, f"[Y] Rebind · {cost_txt}", small_font, hot=not no_hot)
        draw_button(screen, no_rect, "[N] Keep & Continue", small_font, hot=no_hot)
        add_click(yes_rect, pygame.K_y, hover=None)
        add_click(no_rect, pygame.K_n, hover=None)
    else:
        draw_text(f"Not enough spins (cost: {reroll_cost}).", small_font, GRIM_BAD, screen, SCREEN_WIDTH // 2, 356, center=True)
        no_rect = pygame.Rect(0, 0, btn_w, btn_h); no_rect.center = (SCREEN_WIDTH // 2, 420)
        draw_button(screen, no_rect, "[N] Keep & Continue", small_font, hot=True)
        add_click(no_rect, pygame.K_n, hover=None)
    # A level-up earned on the killing blow surfaces here, since combat ends instantly
    draw_signals(screen, SCREEN_WIDTH // 2, 492, kinds=("levelup",), max_lines=1)

def true_master_available():
    """If the player could master their current Tier 1 element right now — at the required
    level and holding its True Sigil — return (base_element, sigil_inventory_index).
    Otherwise (None, -1). Used to offer the True form as a choice on the Evolution screen."""
    base = player_stats["element"]
    if base not in TRUE_ELEMENTS or player_stats["level"] < true_form_level():
        return None, -1
    sigil_name = TRUE_SIGILS[base]
    for i, it in enumerate(player_stats["inventory"]):
        if it.get("name") == sigil_name:
            return base, i
    # Covenant of the Unchanging: mastery opens at its level with no Sigil. A player who
    # can never rebind shouldn't be left waiting on a rare chest roll (index -1: nothing
    # to consume).
    if has_vow(V_UNCHANGING):
        return base, -1
    return None, -1


def render_evolve():
    fill_grim_bg(screen, top=(24, 18, 30), bottom=(6, 4, 8))
    current_elem = player_stats["element"]
    available_evolutions = EVOLUTION_MAP.get(current_elem, [])

    draw_heading("Element Evolution", title_font, GRIM_GOLD_BRIGHT, screen, SCREEN_WIDTH // 2, 48, spacing=6)
    draw_grim_divider(screen, 78)

    if not available_evolutions:
        draw_text(f"Your {current_elem} element has reached its peak.", font, GRIM_CREAM, screen, SCREEN_WIDTH // 2, 120, center=True)
        draw_text("Ascend to a random Universal (Tier 5) element?", small_font, GRIM_CREAM_DIM, screen, SCREEN_WIDTH // 2, 155, center=True)

        yes_rect = pygame.Rect(0, 0, 200, 60); yes_rect.center = (SCREEN_WIDTH // 2 - 120, 290)
        no_rect = pygame.Rect(0, 0, 200, 60); no_rect.center = (SCREEN_WIDTH // 2 + 120, 290)
        no_hot = is_hovered(no_rect)
        if has_vow(V_HUMBLE_ROOT):
            draw_text("Oath of the Humble Root: your element may not rise.", small_font, GRIM_BAD,
                      screen, SCREEN_WIDTH // 2, 214, center=True)
            draw_button(screen, yes_rect, "[Y] Ascend", font, accent=GRIM_CREAM_FAINT)
            draw_button(screen, no_rect, "[N] Remain", font, accent=GRIM_BAD, hot=True)
        else:
            draw_button(screen, yes_rect, "[Y] Ascend", font, hot=not no_hot)
            draw_button(screen, no_rect, "[N] Remain", font, accent=GRIM_BAD, hot=no_hot)
            add_click(yes_rect, pygame.K_y, hover=None)
        add_click(no_rect, pygame.K_n, hover=None)
    else:
        draw_text(f"Your {current_elem} element can evolve.", font, GRIM_CREAM, screen, SCREEN_WIDTH // 2, 116, center=True)
        if has_vow(V_HUMBLE_ROOT):
            draw_text("Oath of the Humble Root seals every branch — only a True Form may bloom.",
                      small_font, GRIM_BAD, screen, SCREEN_WIDTH // 2, 146, center=True)
        else:
            draw_text("Choose your next-tier element:", small_font, GRIM_CREAM_DIM, screen, SCREEN_WIDTH // 2, 146, center=True)

        card_w = 420; card_h = 44; row_pitch = card_h + 8
        card_x = SCREEN_WIDTH // 2 - card_w // 2
        y = 174

        # Premium option: master into the True form. Only shown when the player holds the
        # matching Sigil at the required level. Rendered gold and glowing to stand apart.
        true_base, _ = true_master_available()
        if true_base:
            true_name = TRUE_ELEMENTS[true_base]
            trect = pygame.Rect(card_x, y, card_w, card_h)
            draw_glow_rect(screen, trect, GRIM_XP, border_radius=6, layers=3, max_alpha=80, spread=4)
            draw_gradient_rect(screen, trect, (74, 55, 20), (34, 25, 10), border_radius=6)
            pygame.draw.rect(screen, GRIM_GOLD, trect, width=2, border_radius=6)
            draw_filigree_corners(screen, trect, color=GRIM_GOLD, arm=9, inset=4, node=5)
            r = draw_rune(screen, (trect.x + 8 + rune_side(28) // 2, trect.centery), true_name, size=28)
            draw_text(f"(T)  {true_name}", font, GRIM_GOLD_BRIGHT, screen, r.right + 10,
                      trect.centery - font.get_height() // 2)
            tag = "TRUE FORM"
            draw_text(tag, small_font, GRIM_XP, screen,
                      trect.right - small_font.size(tag)[0] - 14, trect.centery - small_font.get_height() // 2)
            add_click(trect, pygame.K_t)
            y += row_pitch

        for i, evolution in enumerate(available_evolutions):
            color = ELEMENT_COLORS.get(evolution, GRIM_GOLD)
            outline_color = color if sum(color[:3]) > 60 else lighten(color, 0.4)
            card_rect = pygame.Rect(card_x, y + i * row_pitch, card_w, card_h)
            draw_glow_rect(screen, card_rect, outline_color, border_radius=6, layers=3, max_alpha=50, spread=3)
            panel = pygame.Surface(card_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (*GRIM_PANEL2, 235), panel.get_rect(), border_radius=6)
            # a thin band of the element's own hue on the leading edge
            pygame.draw.rect(panel, (*darken(color, 0.2), 220), pygame.Rect(0, 0, 6, card_h), border_radius=6)
            screen.blit(panel, card_rect.topleft)
            pygame.draw.rect(screen, GRIM_GOLD_DIM, card_rect, width=1, border_radius=6)
            draw_filigree_corners(screen, card_rect, color=GRIM_GOLD, arm=9, inset=4, node=5)

            if evolution in element_icons:
                r = draw_rune(screen, (card_rect.x + 8 + rune_side(28) // 2, card_rect.centery), evolution, size=28)
                text_x = r.right + 10
            else:
                text_x = card_rect.x + 18
            draw_text(f"({i + 1})  {evolution}", font, lighten(color, 0.4) if sum(color[:3]) > 60 else GRIM_CREAM,
                      screen, text_x, card_rect.centery - font.get_height() // 2)
            if has_vow(V_HUMBLE_ROOT):
                seal = pygame.Surface(card_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(seal, (6, 5, 4, 170), seal.get_rect(), border_radius=6)
                screen.blit(seal, card_rect.topleft)
            elif i < 9:
                add_click(card_rect, pygame.K_1 + i)

        decline_rect = pygame.Rect(card_x, y + len(available_evolutions) * row_pitch, card_w, card_h)
        draw_button(screen, decline_rect, "(0) Decline Evolution", font, accent=GRIM_GOLD_DIM,
                    hot=is_hovered(decline_rect))
        add_click(decline_rect, pygame.K_0, hover=None)
    draw_signals(screen, SCREEN_WIDTH // 2, 540, kinds=("levelup",), max_lines=1)

def render_stage_clear():
    fill_grim_bg(screen, top=(20, 16, 9), bottom=(5, 3, 2))
    draw_heading("Stage Cleared", big_font, GRIM_WARD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40, spacing=8)
    draw_grim_divider(screen, SCREEN_HEIGHT // 2 + 8)
    draw_text("The way deeper opens…", small_font, GRIM_CREAM, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 45, center=True)
    draw_text("Press any key or click to descend to the next stage", small_font, GRIM_CREAM_FAINT, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 78, center=True)
    add_click(screen.get_rect(), pygame.K_SPACE, hover=None)

# --- End Screen Buttons (shared by Game Over and Victory) ---
# Index order is the contract between the renderer, the click handler and the hotkeys.
END_BTN_RETRY, END_BTN_MENU, END_BTN_QUIT = 0, 1, 2
_END_BTNS = ["[R] Retry", "[M] Main Menu", "[Esc] Quit"]
_end_btn_rects = [pygame.Rect(0, 0, 196, 46) for _ in _END_BTNS]
_end_hover_anim = [0.0 for _ in _END_BTNS]

def _update_end_rects():
    """Lay the buttons out in a centred row. Called by both the renderer and the click
    handler so the hitboxes always match what's on screen, whatever the resolution."""
    gap = 14
    total = sum(r.width for r in _end_btn_rects) + gap * (len(_end_btn_rects) - 1)
    x = SCREEN_WIDTH // 2 - total // 2
    y = SCREEN_HEIGHT // 2 + 116
    for r in _end_btn_rects:
        r.topleft = (x, y)
        x += r.width + gap

def draw_end_buttons():
    _update_end_rects()
    mouse = pygame.mouse.get_pos()
    for i, label in enumerate(_END_BTNS):
        rect = _end_btn_rects[i]
        target = 1.0 if rect.collidepoint(mouse) else 0.0
        _end_hover_anim[i] += (target - _end_hover_anim[i]) * 0.2
        accent = GRIM_BAD if i == END_BTN_QUIT else GRIM_GOLD
        draw_button(screen, rect, label, small_font,
                    hot=_end_hover_anim[i] > 0.5, accent=accent)
        add_click(rect, None, hover=None)   # clicks handled by end_screen_action

# ==================== Character Creation ====================
# Shown at the start of every run: pick a class, a look, and spend the free stat points.
# Choices are remembered, so a Retry opens on the same hero ready to go.
_creation = {"class": "Mage", "race": "Human", "color": "Element", "skin": "Fair", "hair": "Chestnut",
             "style": "Short", "hood": "On", "alloc": {k: 0 for k in STAT_POINT_VALUE}, "row": 0}
CREATE_ROWS = ["class", "race", "color", "skin", "hair", "style", "hood"] + list(STAT_POINT_VALUE) + ["begin"]
HOOD_OPTIONS = ["On", "Off"]


def hood_label(cls):
    """The Knight's headgear is a helmet; everyone else wears a hood."""
    return "Helmet" if cls == "Knight" else "Hood"


def hood_text(cls, value):
    if cls == "Knight":
        return "Helmet on" if value != "Off" else "Helmet off"
    return "Hood up" if value != "Off" else "Hood down"
_STAT_LABELS = {"max_hp": "Health", "max_mana": "Mana", "melee_strength": "Melee",
                "element_strength": "Element", "defense": "Defense"}


def _look_options(field):
    if field == "color":
        return ["Element"] + list(make_tiles.OUTFIT_COLORS)
    if field == "skin":
        return list(make_tiles.RACE_SKINS.get(_creation["race"], make_tiles.RACE_SKINS["Human"]))
    if field == "style":
        return list(make_tiles.HAIRSTYLES)
    if field == "hood":
        return list(HOOD_OPTIONS)
    return list(make_tiles.HAIR_COLORS)


def creation_free_points():
    return FREE_STAT_POINTS + PLAYER_RACES[_creation["race"]].get("free_points", 0)


def set_creation_race(name):
    """Pick a race; the skin tone snaps to one that race can have."""
    _creation["race"] = name
    skins = make_tiles.RACE_SKINS.get(name, make_tiles.RACE_SKINS["Human"])
    if _creation["skin"] not in skins:
        _creation["skin"] = skins[0]
    while sum(_creation["alloc"].values()) > creation_free_points():   # a lost bonus point
        k = max(_creation["alloc"], key=_creation["alloc"].get)
        _creation["alloc"][k] -= 1


def creation_points_left():
    return creation_free_points() - sum(_creation["alloc"].values())


def create_cycle(field, step):
    if field == "class":
        i = CLASS_ORDER.index(_creation["class"])
        _creation["class"] = CLASS_ORDER[(i + step) % len(CLASS_ORDER)]
    elif field == "race":
        i = RACE_ORDER.index(_creation["race"])
        set_creation_race(RACE_ORDER[(i + step) % len(RACE_ORDER)])
    else:
        opts = _look_options(field)
        cur = _creation[field] if _creation[field] in opts else opts[0]
        _creation[field] = opts[(opts.index(cur) + step) % len(opts)]


def create_alloc(stat, step):
    n = _creation["alloc"][stat]
    if step > 0 and creation_points_left() > 0:
        _creation["alloc"][stat] = n + 1
    elif step < 0 and n > 0:
        _creation["alloc"][stat] = n - 1


def creation_preview_stats():
    base = PLAYER_CLASSES[_creation["class"]]["stats"]
    add = PLAYER_RACES[_creation["race"]]["add"]
    return {k: base[k] + add.get(k, 0) + _creation["alloc"][k] * STAT_POINT_VALUE[k] for k in STAT_POINT_VALUE}


def apply_character():
    """Turn the screen's choices into the run's starting character."""
    stats = creation_preview_stats()
    player_stats.update(stats)
    player_stats["hp"] = player_stats["max_hp"]
    player_stats["mana"] = player_stats["max_mana"]
    player_stats["stat_points"] = creation_points_left()     # unspent points carry into the run
    player_stats["class"] = _creation["class"]
    player_stats["race"] = _creation["race"]
    player_stats["luck"] = player_stats.get("luck", 0) + PLAYER_RACES[_creation["race"]].get("luck", 0)
    player_stats["look"] = {"color": _creation["color"], "skin": _creation["skin"], "hair": _creation["hair"],
                            "style": _creation["style"], "hood": _creation["hood"]}
    print(f"Character: {_creation['race']} {_creation['class']} ({_creation['color']} / {_creation['skin']} / {_creation['hair']} "
          f"{_creation['style']} / {hood_text(_creation['class'], _creation['hood'])}) "
          f"stats {stats}, {player_stats['stat_points']} points unspent")


def create_begin():
    def _enter_world():
        global game_state
        game_state = STATE_EXPLORE
        announce_location(current_area.label_at(*player_tile()), force=True)
    apply_character()
    begin_transition(_enter_world)


def handle_create_event(event):
    if event.type != pygame.KEYDOWN or transition_active():
        return
    row = CREATE_ROWS[_creation["row"]]
    k = event.key
    if k in (pygame.K_UP, pygame.K_w):
        _creation["row"] = (_creation["row"] - 1) % len(CREATE_ROWS)
    elif k in (pygame.K_DOWN, pygame.K_s):
        _creation["row"] = (_creation["row"] + 1) % len(CREATE_ROWS)
    elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
        step = 1 if k in (pygame.K_RIGHT, pygame.K_d) else -1
        if row in STAT_POINT_VALUE:
            create_alloc(row, step)
        elif row != "begin":
            create_cycle(row, step)
    elif pygame.K_1 <= k <= pygame.K_3:
        _creation["class"] = CLASS_ORDER[k - pygame.K_1]
    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        if row == "begin":
            create_begin()
        elif row in STAT_POINT_VALUE:
            create_alloc(row, 1)
        else:
            _creation["row"] = CREATE_ROWS.index("begin")


def _create_row_frame(rect, row_name):
    """Gold frame on the row the keyboard cursor is on."""
    if CREATE_ROWS[_creation["row"]] == row_name:
        pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, rect.inflate(6, 4), width=1, border_radius=5)


def render_create():
    fill_grim_bg(screen, top=(24, 18, 12), bottom=(6, 4, 3))
    draw_heading("Create Your Hero", title_font, GRIM_GOLD_BRIGHT, screen, SCREEN_WIDTH // 2, 34, spacing=5)
    W = SCREEN_WIDTH
    # --- class cards ---
    gap = 12
    cw = (W - 40 - gap * 2) // 3
    for i, name in enumerate(CLASS_ORDER):
        c = PLAYER_CLASSES[name]
        r = pygame.Rect(20 + i * (cw + gap), 56, cw, 160)
        chosen = name == _creation["class"]
        if chosen:
            draw_glow_rect(screen, r, GRIM_GOLD, border_radius=6, layers=3, max_alpha=60, spread=3)
            draw_gradient_rect(screen, r, (62, 48, 22), (28, 21, 11), border_radius=6)
            pygame.draw.rect(screen, GRIM_GOLD, r, width=2, border_radius=6)
            draw_filigree_corners(screen, r, color=GRIM_GOLD, arm=9, inset=4, node=5)
        else:
            draw_panel(screen, r, border_radius=6, alpha=200, glow=False, filigree=False)
        _create_row_frame(r, "class") if chosen else None
        draw_heading(f"{i + 1}  {name}", font, GRIM_GOLD_BRIGHT if chosen else GRIM_CREAM,
                     screen, r.centerx, r.top + 20, spacing=2)
        st = c["stats"]
        draw_text(f"HP {st['max_hp']} · MP {st['max_mana']} · MEL {st['melee_strength']}",
                  xp_font, GRIM_CREAM, screen, r.centerx, r.top + 42, center=True)
        draw_text(f"ELE {st['element_strength']} · DEF {st['defense']}",
                  xp_font, GRIM_CREAM, screen, r.centerx, r.top + 58, center=True)
        y = r.top + 70
        for line in wrap_text(c["blurb"], xp_font, r.width - 20)[:2]:
            draw_text(line, xp_font, GRIM_CREAM_DIM, screen, r.centerx, y + 8, center=True); y += 16
        draw_text(c["perk"], small_font, GRIM_XP, screen, r.centerx, y + 12, center=True); y += 20
        for line in wrap_text(c["perk_text"], xp_font, r.width - 20)[:2]:
            draw_text(line, xp_font, GRIM_WARD, screen, r.centerx, y + 8, center=True); y += 16
        add_click(r, lambda n=name: _creation.update({"class": n}))

    # --- race strip ---
    rw = (W - 40 - 5 * 6) // 6
    for i, name in enumerate(RACE_ORDER):
        rr = pygame.Rect(20 + i * (rw + 6), 224, rw, 30)
        chosen = name == _creation["race"]
        draw_button(screen, rr, name, small_font, hot=chosen or is_hovered(rr), upper=False)
        if chosen:
            _create_row_frame(rr, "race")
        add_click(rr, lambda n=name: set_creation_race(n), hover=None)
    rc = PLAYER_RACES[_creation["race"]]
    line = f"{rc['perk']}: {rc['perk_text']}"
    if _creation["race"] == "Elf":
        line += ("  ·  Elemental Infusion: melee carries your element"
                 if _creation["class"] == "Mage" else "  ·  As a Mage: Elemental Infusion")
    draw_text(fit_text(line, xp_font, W - 40), xp_font, GRIM_WARD, screen, W // 2, 266, center=True)

    top = 280
    # --- preview ---
    pv = pygame.Rect(20, top, 200, 248)
    draw_panel(screen, pv, border_radius=6, alpha=205, glow=False)
    draw_text("Preview", xp_font, GRIM_GOLD, screen, pv.centerx, pv.top + 14, center=True)
    tiles = world_tiles()
    now = pygame.time.get_ticks() / 1000.0
    # the detailed hero, front on, standing on a patch of ground
    stage = pygame.Rect(0, 0, 150, 34); stage.center = (pv.centerx, pv.top + 168)
    pygame.draw.ellipse(screen, (46, 92, 50), stage)
    pygame.draw.ellipse(screen, (70, 130, 70), stage.inflate(-40, -12))
    portrait = hero_battle_sprite(_creation["class"], _creation["color"], _creation["skin"], _creation["hair"],
                                  _creation["race"], "front", _creation["style"], _creation["hood"])
    big = pygame.transform.scale(portrait, (144, 144))
    breath = int(2 * math.sin(now * 2.0))
    screen.blit(big, (pv.centerx - 72, stage.centery + 10 - 144 + breath))
    # the overworld walker beside the element, turning through its directions
    facing = ("down", "left", "up", "right")[int(now / 1.6) % 4]
    step = (0, 1, 0, 2)[int(now * 6) % 4]
    frames = look_frames(_creation["class"], _creation["color"], _creation["skin"], _creation["hair"], _creation["race"],
                         _creation["style"], _creation["hood"])
    fr = frames[facing][step]
    walker = pygame.transform.scale(fr, (fr.get_width() * 2, fr.get_height() * 2))
    screen.blit(walker, (pv.left + 16, pv.bottom - 10 - walker.get_height()))
    el = player_stats.get("element")
    draw_text("Starting element", xp_font, GRIM_CREAM_FAINT, screen, pv.centerx + 18, pv.bottom - 46, center=True)
    if el:
        draw_rune(screen, (pv.centerx + 18 - small_font.size(el)[0] // 2 - 14, pv.bottom - 22), el, size=20)
        draw_text(el, small_font, GRIM_CREAM, screen, pv.centerx + 30, pv.bottom - 22, center=True)

    # --- appearance ---
    ap = pygame.Rect(232, top, 260, 248)
    draw_panel(screen, ap, border_radius=6, alpha=205, glow=False)
    draw_heading("Appearance", small_font, GRIM_GOLD_BRIGHT, screen, ap.centerx, ap.top + 18, spacing=2)
    fields = (("color", "Outfit"), ("skin", "Skin"), ("hair", "Hair"), ("style", "Style"),
              ("hood", hood_label(_creation["class"])))
    for n, (field, label) in enumerate(fields):
        row = pygame.Rect(ap.left + 10, ap.top + 34 + n * 37, ap.width - 20, 33)
        _create_row_frame(row, field)
        draw_text(label, xp_font, GRIM_CREAM_DIM, screen, row.left + 4, row.top + 10)
        value = _creation[field]
        rgb = None
        if field == "color":
            rgb = tuple((ELEMENT_COLORS.get(el) or GRIM_GOLD)[:3]) if value == "Element" else make_tiles.OUTFIT_COLORS[value]
            shown = value
        elif field in ("skin", "hair"):
            rgb = (make_tiles.SKIN_TONES if field == "skin" else make_tiles.HAIR_COLORS)[value]
            shown = value
        elif field == "style":
            shown = f"{value}  ({make_tiles.HAIRSTYLES.index(value) + 1}/{len(make_tiles.HAIRSTYLES)})"
        else:
            shown = hood_text(_creation["class"], value)
        left = pygame.Rect(row.left + 58, row.top + 3, 27, 27)
        right = pygame.Rect(row.right - 27, row.top + 3, 27, 27)
        draw_button(screen, left, "<", small_font, hot=is_hovered(left), upper=False)
        draw_button(screen, right, ">", small_font, hot=is_hovered(right), upper=False)
        add_click(left, lambda f=field: create_cycle(f, -1), hover=None)
        add_click(right, lambda f=field: create_cycle(f, 1), hover=None)
        tx = left.right + 8
        if rgb is not None:
            sw = pygame.Rect(tx, row.top + 8, 16, 16)
            pygame.draw.rect(screen, rgb, sw, border_radius=3)
            pygame.draw.rect(screen, GRIM_GOLD_DIM, sw, width=1, border_radius=3)
            tx = sw.right + 7
        draw_text(fit_text(shown, small_font, right.left - tx - 6), small_font, GRIM_CREAM, screen, tx, row.top + 7)
    if _creation["hood"] != "Off":
        tip = ("Helmet hides hair; it tints the plume." if _creation["class"] == "Knight"
               else "Hood up hides most of the hair.")
    elif _creation["color"] == "Element":
        tip = "Outfit follows your element."
    else:
        tip = ""
    if tip:
        draw_text(fit_text(tip, xp_font, ap.width - 16), xp_font, GRIM_CREAM_FAINT, screen, ap.centerx, ap.bottom - 14, center=True)

    # --- free stat points ---
    sp = pygame.Rect(504, top, W - 524, 248)
    draw_panel(screen, sp, border_radius=6, alpha=205, glow=False)
    left_pts = creation_points_left()
    draw_heading("Free Points", small_font, GRIM_GOLD_BRIGHT, screen, sp.centerx, sp.top + 18, spacing=2)
    draw_text(f"{left_pts} of {creation_free_points()} left", xp_font, GRIM_XP if left_pts else GRIM_CREAM_FAINT,
              screen, sp.centerx, sp.top + 38, center=True)
    preview = creation_preview_stats()
    for n, stat in enumerate(STAT_POINT_VALUE):
        ry = sp.top + 52 + n * 38
        row = pygame.Rect(sp.left + 12, ry, sp.width - 24, 34)
        _create_row_frame(row, stat)
        added = _creation["alloc"][stat]
        draw_text(_STAT_LABELS[stat], small_font, GRIM_CREAM, screen, row.left + 4, row.top + 8)
        val = f"{preview[stat]}"
        vx = row.right - 142
        draw_text(val, small_font, GRIM_WARD if added else GRIM_CREAM_DIM, screen, vx, row.top + 8)
        minus = pygame.Rect(row.right - 64, row.top + 4, 28, 28)
        plus = pygame.Rect(row.right - 30, row.top + 4, 28, 28)
        if added:
            draw_button(screen, minus, "-", font, hot=is_hovered(minus), upper=False)
            add_click(minus, lambda st=stat: create_alloc(st, -1), hover=None)
        if left_pts:
            draw_button(screen, plus, "+", font, hot=is_hovered(plus), upper=False)
            add_click(plus, lambda st=stat: create_alloc(st, 1), hover=None)
        if added:
            draw_text(f"+{added * STAT_POINT_VALUE[stat]}", xp_font, GRIM_WARD, screen, vx + small_font.size(val)[0] + 5, row.top + 11)

    # --- begin ---
    begin = pygame.Rect(0, 0, 260, 40)
    begin.center = (W // 2, top + 248 + 26)
    _create_row_frame(begin, "begin")
    draw_button(screen, begin, "Begin Journey", font, hot=is_hovered(begin) or CREATE_ROWS[_creation["row"]] == "begin",
                upper=False)
    add_click(begin, create_begin, hover=None)
    draw_text("[Up/Down] Choose   [Left/Right] Change   [1-3] Class   [Enter] Begin", xp_font,
              GRIM_CREAM_FAINT, screen, W // 2, SCREEN_HEIGHT - 12, center=True)


def end_screen_action(index):
    """Retry / Main Menu / Quit, from either a click or a hotkey."""
    global running, game_state
    if index == END_BTN_RETRY:
        snap = main_menu.snapshot(screen)
        reset_game()          # fresh run from Stage 1; also returns to STATE_EXPLORE
        begin_game_intro(snap)
        print("Retrying from Stage 1.")
    elif index == END_BTN_MENU:
        result = _main_menu()     # choose the mode first, then build its world
        if result not in ("continue", "openworld", "limitless", "stages"):
            running = False
        else:
            _apply_video_settings_for_gameplay()   # pick up any video setting changes
            start_from_menu(result)
            snap = main_menu.snapshot(screen)
            begin_game_intro(snap)
    else:
        running = False


def render_game_over():
    fill_grim_bg(screen, top=(30, 10, 10), bottom=(6, 2, 2))
    draw_heading("Defeated", big_font, GRIM_BAD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40, spacing=10)
    draw_grim_divider(screen, SCREEN_HEIGHT // 2 + 8, color=(120, 50, 44))
    draw_text("The dungeon claims another soul.", small_font, GRIM_CREAM, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 45, center=True)
    where = {"openworld": f"Fell in the Wilds at Danger {_roman(current_tier())}",
             "limitless": f"Fell in Chamber {_ll['chamber']} on wave {max(1, _ll['wave'])}"}.get(
        GAME_MODE, f"Fell on Stage {_roman(current_stage)}")
    draw_text(f"{where}  ·  Level {player_stats['level']}", small_font, GRIM_CREAM_FAINT, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 74, center=True)
    draw_end_buttons()

def render_victory():
    fill_grim_bg(screen, top=(30, 22, 10), bottom=(6, 4, 2))
    draw_rune(screen, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 116), player_stats["element"], size=104)
    draw_heading("Victory", big_font, GRIM_XP, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 18, spacing=12)
    draw_grim_divider(screen, SCREEN_HEIGHT // 2 + 28)
    draw_text("Every binding in the dungeon is broken.", small_font, GRIM_CREAM, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 62, center=True)
    draw_end_buttons()

def element_matchups(element):
    """(strong_against, weak_against) for an element, via its affinity on the wheel.

    Evolutions report their ancestor's matchups. Universal (Tier 5+) elements sit outside
    the wheel, so they honestly return empty lists rather than inventing relationships."""
    strong, weak = [], []
    row = ELEMENTAL_MATCHUPS.get(matchup_key(element), {})
    for other, mult in row.items():
        if mult >= SUPER_EFFECTIVE_MULTIPLIER:
            strong.append(other)
        elif mult <= NOT_EFFECTIVE_MULTIPLIER:
            weak.append(other)
    return strong, weak


def render_info_page(content_rect):
    """The Info tab: a codex for whatever element the player is currently bound to."""
    elem = player_stats["element"]
    color = ELEMENT_COLORS.get(elem, GRIM_GOLD)
    label_color = color if sum(color[:3]) > 60 else lighten(color, 0.5)
    tier = get_element_tier(elem)

    # --- Sub-page pills ---
    pill_y = content_rect.top + 12
    pill_w, pill_h = 128, 28
    total_w = pill_w * len(INFO_PAGES) + 8 * (len(INFO_PAGES) - 1)
    px0 = content_rect.centerx - total_w // 2
    for i, name in enumerate(INFO_PAGES):
        r = pygame.Rect(px0 + i * (pill_w + 8), pill_y, pill_w, pill_h)
        if i == info_page:
            # Only the selected page gets a box — a clean rounded gold frame with a soft
            # glow — so it reads as chosen instead of three competing outlines.
            draw_glow_rect(screen, r, GRIM_GOLD, border_radius=6, layers=3, max_alpha=42, spread=3)
            draw_gradient_rect(screen, r, (60, 46, 20), (30, 22, 11), border_radius=6)
            pygame.draw.rect(screen, GRIM_GOLD, r, width=2, border_radius=6)
            draw_heading(name, small_font, GRIM_GOLD_BRIGHT, screen, r.centerx, r.centery, spacing=2)
        else:
            draw_heading(name, small_font, GRIM_CREAM_FAINT, screen, r.centerx, r.centery, spacing=2)
            add_click(r, lambda i=i: set_info_page(i))
    # Page-switch hint, right-aligned so it can't run off the panel edge
    hint = "[Up/Down]"
    draw_text(hint, small_font, GRIM_CREAM_FAINT, screen,
              content_rect.right - small_font.size(hint)[0] - 16, pill_y + 5)

    body_top = pill_y + pill_h + 16
    left = content_rect.left + 24
    inner_w = content_rect.width - 48
    page = INFO_PAGES[info_page]

    # --- Header: rune + name + tier, shared by every sub-page ---
    # draw_heading with center=False anchors by the TOP of the glyphs, so the tier line
    # has to clear the title's full height rather than a nominal baseline.
    title_h = title_font.get_height()
    draw_rune(screen, (left + 22, body_top + title_h // 2), elem, size=40)
    draw_heading(str(elem), title_font, label_color, screen, left + 56, body_top,
                 spacing=4, center=False)
    mult = get_element_damage_multiplier(elem)
    tier_label = f"Tier {tier}  ·  True form" if elem in TRUE_TO_BASE else f"Tier {tier}"
    draw_text(f"{tier_label}  ·  damage ×{mult:g}", small_font, GRIM_CREAM_DIM,
              screen, left + 56, body_top + title_h - 2)
    y = body_top + title_h + 24
    pygame.draw.line(screen, GRIM_GOLD_DEEP, (left, y), (content_rect.right - 24, y), 1)
    y += 14

    if page == "Overview":
        for line in wrap_text(ELEMENT_INFO.get(elem, "No records survive for this element."),
                              small_font, inner_w):
            draw_text(line, small_font, GRIM_CREAM, screen, left, y); y += 22
        y += 10
        draw_text(f"Awakening:  {AWAKENING_NAMES.get(elem, 'Power Unleashed')}",
                  small_font, GRIM_XP, screen, left, y); y += 26

        strong, weak = element_matchups(elem)
        # Inherited elements say whose place they take on the wheel
        akin = matchup_key(elem)
        if akin != elem:
            draw_text(f"Fights as {akin} on the matchup wheel.",
                      small_font, GRIM_CREAM_FAINT, screen, left, y); y += 22
        if strong:
            draw_text("Strong against:  " + ", ".join(strong), small_font, GRIM_WARD,
                      screen, left, y); y += 22
        if weak:
            draw_text("Weak against:  " + ", ".join(weak), small_font, GRIM_BAD,
                      screen, left, y); y += 22
        if not strong and not weak:
            draw_text("Universal — outside the wheel; neutral damage both ways.",
                      small_font, GRIM_CREAM_FAINT, screen, left, y); y += 22
        # Advertise the mastery reward to anyone still on a Tier 1 element
        if elem in TRUE_ELEMENTS:
            y += 8
            draw_text(f"At level {true_form_level()} this masters into {TRUE_ELEMENTS[elem]}.",
                      small_font, GRIM_XP, screen, left, y)

    elif page == "Evolution":
        evolutions = EVOLUTION_MAP.get(elem, [])
        sources = sorted(k for k, v in EVOLUTION_MAP.items() if elem in v)
        if elem in TRUE_TO_BASE:
            draw_text(f"Mastered from:  {TRUE_TO_BASE[elem]}  (at level {true_form_level()})",
                      small_font, GRIM_XP, screen, left, y); y += 28
        elif sources:
            # Tier-5 elements evolve from up to seven sources — wrap so the list can't
            # run off the panel's right edge.
            for ln in wrap_text("Evolves from:  " + ", ".join(sources), small_font, inner_w):
                draw_text(ln, small_font, GRIM_CREAM_DIM, screen, left, y); y += 22
            y += 6
        else:
            draw_text("A base element — nothing evolves into it.", small_font,
                      GRIM_CREAM_FAINT, screen, left, y); y += 28

        if not evolutions:
            draw_text("This element has reached its peak.", small_font, GRIM_CREAM, screen, left, y); y += 22
            draw_text("At a milestone it may ascend to a random Universal (Tier 5) element.",
                      small_font, GRIM_CREAM_FAINT, screen, left, y)
        else:
            draw_text(f"Evolves into  ({len(evolutions)} paths):", small_font, GRIM_GOLD_BRIGHT,
                      screen, left, y); y += 24
            # Two columns so six-way Tier 5 branches still fit. Tier sits inline after the
            # name — stacking it underneath collided with the row below.
            col_w = inner_w // 2
            for i, evo in enumerate(evolutions):
                cx = left + (i % 2) * col_w
                cy = y + (i // 2) * 32
                ec = ELEMENT_COLORS.get(evo, GRIM_GOLD)
                draw_rune(screen, (cx + 14, cy + 12), evo, size=24)
                draw_text(evo, small_font,
                          ec if sum(ec[:3]) > 60 else lighten(ec, 0.5),
                          screen, cx + 34, cy + 2)
                draw_text(f"Tier {get_element_tier(evo)}", xp_font, GRIM_CREAM_FAINT,
                          screen, cx + 34 + small_font.size(evo)[0] + 10, cy + 6)

    elif page == "Abilities":
        skills = ELEMENT_SKILLS.get(elem, DEFAULT_SKILLS)
        total = calculate_total_stats()
        ele_stat = total["element_strength"]

        cols = [left, left + 208, left + 288, left + 338, left + 388, left + 458]
        for cx, head in zip(cols, ["Ability", "Power", "MP", "CD", "Miss", "Est. damage"]):
            draw_heading(head, xp_font, GRIM_GOLD, screen, cx, y, spacing=2, center=False)
        y += 20
        pygame.draw.line(screen, GRIM_GOLD_DEEP, (left, y), (content_rect.right - 24, y), 1)
        y += 8

        for skill in skills[:8]:
            cost = get_skill_mana_cost(elem, skill["name"])
            cd = get_skill_cooldown_max(elem, skill["name"])
            est = int(ele_stat * mult * skill["power"])
            afford = player_stats["mana"] >= cost
            draw_text(skill["name"], small_font, GRIM_CREAM if afford else GRIM_CREAM_FAINT,
                      screen, cols[0], y)
            draw_text(f"{skill['power']:.1f}", small_font, GRIM_CREAM_DIM, screen, cols[1], y)
            draw_text(str(cost), small_font, GRIM_MP if afford else GRIM_BAD, screen, cols[2], y)
            draw_text(str(cd) if cd else "—", small_font, GRIM_CREAM_DIM, screen, cols[3], y)
            miss_txt = "—" if elem == "OFA" else format_miss_chance(skill["power"])
            draw_text(miss_txt, small_font, GRIM_CREAM_DIM, screen, cols[4], y)
            draw_text(str(est), small_font, GRIM_XP, screen, cols[5], y)
            y += 24

        y += 6
        draw_text(f"Estimate = element strength ({ele_stat}) × tier ×{mult:g} × power.",
                  xp_font, GRIM_CREAM_FAINT, screen, left, y); y += 16
        draw_text("Before enemy defence and matchup multipliers. Awakening adds "
                  f"+{AWAKENING_ATK_BONUS} element strength.",
                  xp_font, GRIM_CREAM_FAINT, screen, left, y); y += 16
        if elem != "OFA":   # OFA never misses — and its 8-skill table has no room for the line
            draw_text(f"Stronger moves are riskier: up to {MISS_CHANCE_MAX * 100:.0f}% miss chance "
                      f"(melee {format_miss_chance(MELEE_POWER)}).",
                      xp_font, GRIM_CREAM_FAINT, screen, left, y)


VOW_CARD_H = 78
VOW_CARD_GAP = 10
VOW_THUMB_W, VOW_THUMB_H = 96, 144        # card art on the Bindings page (the art is 2:3)
VOW_PREVIEW_W, VOW_PREVIEW_H = 240, 360   # the card shown on hover
VOW_CARD_DIR = os.path.join("bindings", "cards")
_vow_card_cache = {}
_vow_card_files = []
_vow_preview = {"index": None, "rect": None}


def _vow_slug(name):
    out, last = [], ""
    for c in name.lower():
        c = c if c.isalnum() else "_"
        if c == "_" and last == "_":
            continue
        out.append(c); last = c
    return "".join(out).strip("_")


def vow_card_image(vow, kind):
    """The vow's card art: "thumb", "grey" (unavailable) or "preview". Loaded lazily from
    bindings/cards/NN_<slug>.png and cached. None if the file is missing."""
    key = (vow["name"], kind)
    if key in _vow_card_cache:
        return _vow_card_cache[key]
    src_key = (vow["name"], "src")
    if src_key not in _vow_card_cache:
        if not _vow_card_files:
            try:
                _vow_card_files.extend(sorted(os.listdir(VOW_CARD_DIR)))
            except OSError:
                _vow_card_files.append("")        # remember the folder is missing
        slug = _vow_slug(vow["name"])
        fname = next((f for f in _vow_card_files
                      if f.lower().endswith(".png") and f[:-4].split("_", 1)[-1] == slug), None)
        src = None
        if fname:
            try:
                src = load_image(os.path.join(VOW_CARD_DIR, fname)).convert_alpha()
            except pygame.error as e:
                print(f"Warning: vow card {fname} failed to load: {e}")
        _vow_card_cache[src_key] = src
    src = _vow_card_cache[src_key]
    img = None
    if src is not None:
        if kind == "preview":
            img = pygame.transform.smoothscale(src, (VOW_PREVIEW_W, VOW_PREVIEW_H))
        else:
            img = pygame.transform.smoothscale(src, (VOW_THUMB_W, VOW_THUMB_H))
            if kind == "grey":
                try:
                    img = pygame.transform.grayscale(img)
                except AttributeError:
                    pass
                shade = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                shade.fill((0, 0, 0, 120))
                img.blit(shade, (0, 0))
    _vow_card_cache[key] = img
    return img


def render_bindings_page(content_rect):
    """Bindings tab — one dropdown per circle (Flesh, Element, Fate, …), each opening onto
    its vows as cards. Sworn vows glow gold; vows that can't be sworn right now (all slots
    used, or not enough stat points) are greyed out."""
    global bindings_scroll
    _vow_preview.update(index=None, rect=None)
    draw_heading("Bindings", font, GRIM_GOLD_BRIGHT, screen, content_rect.centerx,
                 content_rect.top + 28, spacing=3)
    draw_text("Swear a vow for power — every vow exacts a cost.", small_font, GRIM_CREAM_DIM,
              screen, content_rect.centerx, content_rect.top + 54, center=True)

    # --- Status row: slots (pips) on the left, stat points on the right ---
    sworn = player_stats.get("vows", [])
    pts = player_stats["stat_points"]
    row_y = content_rect.top + 78
    left = content_rect.left + 24
    draw_text("Vows sworn", small_font, GRIM_CREAM_DIM, screen, left, row_y)
    px = left + small_font.size("Vows sworn")[0] + 14
    for i in range(VOW_LIMIT):
        c = (px + i * 20 + 6, row_y + small_font.get_height() // 2)
        pts_d = [(c[0], c[1] - 6), (c[0] + 6, c[1]), (c[0], c[1] + 6), (c[0] - 6, c[1])]
        if i < len(sworn):
            pygame.draw.polygon(screen, GRIM_XP, pts_d)
        else:
            pygame.draw.polygon(screen, GRIM_GOLD_DIM, pts_d, 1)
    full = len(sworn) >= VOW_LIMIT
    pts_txt = f"Stat points {pts}  ·  {VOW_STAT_COST} per vow"
    pts_col = GRIM_CREAM_DIM if full else (GRIM_XP if pts >= VOW_STAT_COST else GRIM_BAD)
    draw_text(pts_txt, small_font, pts_col, screen,
              content_rect.right - 24 - small_font.size(pts_txt)[0], row_y)

    # --- Circles: a dropdown header each, its vow cards beneath when open ---
    list_rect = pygame.Rect(content_rect.left + 18, row_y + 30,
                            content_rect.width - 36, content_rect.bottom - 12 - (row_y + 30))
    pad = 3                                   # room for focus outlines inside the clip
    inner_w = list_rect.width - 14            # 14px kept for a scrollbar
    list_x = list_rect.left + 3
    indent = 12                               # cards sit a step in from their header
    card_w = VOW_THUMB_W
    cols = max(1, (inner_w - indent + VOW_CARD_GAP) // (card_w + VOW_CARD_GAP))
    pitch = VOW_THUMB_H + VOW_CARD_GAP
    head_h = 34

    # Layout pass (content coordinates, before scrolling)
    layout = []                               # (kind, key, rect, extra)
    y = pad
    for name, col, idxs in bindings_sections():
        layout.append(("circle", name, pygame.Rect(list_x, y, inner_w - 6, head_h), (col, idxs)))
        y += head_h + 6
        if name in bindings_open:
            if idxs:
                for n, vi in enumerate(idxs):
                    layout.append(("vow", vi, pygame.Rect(list_x + indent + (n % cols) * (card_w + VOW_CARD_GAP),
                                                          y + (n // cols) * pitch, card_w, VOW_THUMB_H), col))
                y += ((len(idxs) + cols - 1) // cols) * pitch + 4
            else:
                layout.append(("empty", name, pygame.Rect(list_x + indent, y, inner_w - indent, 24), None))
                y += 30
    content_h = y + pad
    max_scroll = max(0, content_h - list_rect.height)

    # Keep whatever the keyboard picked in view
    for kind, key, r, _ in layout:
        if (kind, key) == bindings_focus:
            if r.top - pad < bindings_scroll:
                bindings_scroll = r.top - pad
            elif r.bottom + pad > bindings_scroll + list_rect.height:
                bindings_scroll = r.bottom + pad - list_rect.height
    bindings_scroll = max(0, min(bindings_scroll, max_scroll))

    prev_clip = screen.get_clip()
    screen.set_clip(list_rect)
    for kind, key, r0, extra in layout:
        r = r0.move(0, list_rect.top - bindings_scroll)
        if r.bottom < list_rect.top or r.top > list_rect.bottom:
            continue
        focused = (kind, key) == bindings_focus
        if kind == "circle":
            _draw_circle_header(r, key, extra[0], extra[1], focused)
            vis = r.clip(list_rect)
            if vis.height > 8:
                add_click(vis, lambda n=key: toggle_circle(n))
        elif kind == "empty":
            draw_text("No vows in this circle yet.", small_font, GRIM_CREAM_FAINT, screen,
                      r.left + 6, r.top + 2)
        else:
            _draw_vow_thumb(r, key, extra, focused)
            vis = r.clip(list_rect)
            if vis.height > 8:
                add_click(vis, lambda i=key: click_vow(i))
    screen.set_clip(prev_clip)

    # Scrollbar, only when there's more than fits
    if max_scroll > 0:
        track = pygame.Rect(list_rect.right - 6, list_rect.top, 4, list_rect.height)
        pygame.draw.rect(screen, GRIM_GOLD_DEEP, track, border_radius=2)
        thumb_h = max(24, int(track.height * list_rect.height / content_h))
        thumb_y = track.top + int((track.height - thumb_h) * bindings_scroll / max_scroll)
        pygame.draw.rect(screen, GRIM_GOLD, (track.left, thumb_y, 4, thumb_h), border_radius=2)

    # Which card to preview: the one under the mouse, else the one the keyboard picked
    if not _oath_one["open"]:
        mouse = pygame.mouse.get_pos()
        focus_hit = None
        for kind, key, r0, _ in layout:
            if kind != "vow":
                continue
            vis = r0.move(0, list_rect.top - bindings_scroll).clip(list_rect)
            if vis.height <= 8:
                continue
            if vis.collidepoint(mouse):
                _vow_preview.update(index=key, rect=vis)
                break
            if bindings_focus == ("vow", key):
                focus_hit = (key, vis)
        else:
            if focus_hit:
                _vow_preview.update(index=focus_hit[0], rect=focus_hit[1])

    if _oath_one["open"]:
        _draw_oath_one_chooser(content_rect)


def _draw_vow_thumb(r, i, circle_col, focused):
    """A vow's card art: gold-framed when sworn, greyed when it can't be sworn now."""
    vow = VOWS[i]
    is_sworn = vow_is_sworn(vow)
    reason = vow_block_reason(vow)
    locked = reason is not None and not is_sworn
    img = vow_card_image(vow, "grey" if locked else "thumb")
    if img is None:                      # no art on disk: fall back to a plain card
        bg = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*GRIM_PANEL2, 235), bg.get_rect(), border_radius=5)
        screen.blit(bg, r.topleft)
        for n, line in enumerate(wrap_text(vow["name"], xp_font, r.width - 10)[:5]):
            draw_text(line, xp_font, GRIM_CREAM_FAINT if locked else GRIM_CREAM, screen,
                      r.left + 5, r.top + 8 + n * (xp_font.get_height() + 1))
    else:
        if is_sworn:
            draw_glow_rect(screen, r, GRIM_XP, border_radius=5, layers=3, max_alpha=70, spread=3)
        screen.blit(img, r.topleft)
    if is_sworn:
        pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, r, width=2, border_radius=5)
    elif locked:
        pygame.draw.rect(screen, (58, 53, 46), r, width=1, border_radius=5)
    else:
        pygame.draw.rect(screen, darken(circle_col, 0.2), r, width=1, border_radius=5)
    if focused:
        pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, r.inflate(6, 6), width=1, border_radius=7)
    if _vow_flash["name"] == vow["name"]:
        k = 1.0 - (pygame.time.get_ticks() - _vow_flash["at"]) / VOW_FLASH_MS
        if k > 0:
            flare = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(flare, (*GRIM_XP, int(140 * k)), flare.get_rect(), border_radius=5)
            screen.blit(flare, r.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    # Ribbon across the foot of the card: SWORN, the swear prompt, or why it's unavailable
    if is_sworn:
        tag, tag_col = "SWORN", GRIM_XP
    elif focused and not locked:
        tag, tag_col = "SWEAR?", GRIM_GOLD_BRIGHT
    elif focused:
        tag, tag_col = reason.upper(), GRIM_BAD
    else:
        tag = None
    if tag:
        band = pygame.Rect(r.left + 2, r.bottom - 21, r.width - 4, 19)
        bs = pygame.Surface(band.size, pygame.SRCALPHA)
        bs.fill((8, 6, 4, 225))
        screen.blit(bs, band.topleft)
        tag = fit_text(tag, xp_font, band.width - 6)
        draw_text(tag, xp_font, tag_col, screen, band.centerx - xp_font.size(tag)[0] // 2,
                  band.centery - xp_font.get_height() // 2)


def draw_vow_preview(surface):
    """The full card beside the hovered (or keyboard-picked) thumbnail, with its status."""
    i, anchor = _vow_preview["index"], _vow_preview["rect"]
    if i is None or anchor is None or not 0 <= i < len(VOWS):
        return
    vow = VOWS[i]
    img = vow_card_image(vow, "preview")
    w = VOW_PREVIEW_W
    detail = vow_block_detail(vow)
    if vow_is_sworn(vow):
        status, status_col = detail, GRIM_XP
    elif detail:
        status, status_col = detail, GRIM_BAD
    elif bindings_focus == ("vow", i):
        status, status_col = f"Click again or press Enter to swear ({VOW_STAT_COST} stat points).", GRIM_GOLD_BRIGHT
    else:
        status, status_col = f"Click to choose it, then click again to swear ({VOW_STAT_COST} pts).", GRIM_CREAM
    notes = []
    if VOW_NOTES.get(vow["name"]):
        notes.append(VOW_NOTES[vow["name"]])
    if vow["name"] == V_MARTYR and has_vow(V_FINAL_STAGE):
        notes.append("Silenced by Pact of the Final Stage.")
    if vow["name"] == V_ONE and vow_is_sworn(vow) and player_stats.get("oath_one_stat"):
        pillar = dict(ONE_STAT_CHOICES).get(player_stats["oath_one_stat"], "")
        notes.append(f"Your pillar: {pillar}.")
    lines = [(l, status_col) for l in wrap_text(status, xp_font, w - 16)]
    for n in notes:
        lines += [(l, GRIM_CREAM_DIM) for l in wrap_text(n, xp_font, w - 16)]
    line_h = xp_font.get_height() + 2
    text_h = len(lines) * line_h + 12

    if img is None:                      # no art: a text card in its place
        body = [(vow["name"], GRIM_GOLD_BRIGHT)]
        if vow.get("subtitle"):
            body.append((vow["subtitle"], GRIM_CREAM_DIM))
        body += [("+ " + vow.get("boon", ""), GRIM_WARD), ("− " + vow.get("cost", ""), GRIM_BAD)]
        wrapped = [(l, c) for t, c in body for l in wrap_text(t, small_font, w - 20)]
        card_h = len(wrapped) * (small_font.get_height() + 2) + 20
    else:
        card_h = VOW_PREVIEW_H
    total_h = card_h + text_h
    x = anchor.right + 12 if anchor.centerx < SCREEN_WIDTH // 2 else anchor.left - 12 - w
    x = max(6, min(SCREEN_WIDTH - w - 6, x))
    y = max(6, min(SCREEN_HEIGHT - total_h - 6, anchor.centery - total_h // 2))
    box = pygame.Rect(x - 4, y - 4, w + 8, total_h + 8)
    draw_glow_rect(surface, box, GRIM_GOLD, border_radius=8, layers=3, max_alpha=40, spread=4)
    bg = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.rect(bg, (10, 8, 6, 245), bg.get_rect(), border_radius=8)
    surface.blit(bg, box.topleft)
    pygame.draw.rect(surface, GRIM_GOLD_DIM, box, width=1, border_radius=8)
    if img is None:
        ty = y + 10
        for l, c in wrapped:
            draw_text(l, small_font, c, surface, x + 10, ty); ty += small_font.get_height() + 2
    else:
        surface.blit(img, (x, y))
    ty = y + card_h + 6
    for l, c in lines:
        draw_text(l, xp_font, c, surface, x + 8, ty); ty += line_h


def _draw_oath_one_chooser(content_rect):
    """Oath of One asks which stat becomes the pillar before the vow is sworn."""
    add_click(content_rect, None, hover=None)            # swallow clicks behind the panel
    veil = pygame.Surface(content_rect.size, pygame.SRCALPHA)
    veil.fill((4, 3, 2, 200))
    screen.blit(veil, content_rect.topleft)
    panel = pygame.Rect(0, 0, 468, 214)
    panel.center = content_rect.center
    draw_panel(screen, panel, border_radius=6, alpha=245)
    draw_heading("Oath of One", font, GRIM_GOLD_BRIGHT, screen, panel.centerx, panel.top + 26, spacing=3)
    draw_text("Choose your pillar. Points spent there count 1.5x;", small_font, GRIM_CREAM_DIM,
              screen, panel.centerx, panel.top + 58, center=True)
    draw_text("every other stat is locked.", small_font, GRIM_CREAM_DIM,
              screen, panel.centerx, panel.top + 80, center=True)
    bw, gap = 82, 8
    x0 = panel.centerx - (5 * bw + 4 * gap) // 2
    for n, (key, label) in enumerate(ONE_STAT_CHOICES):
        r = pygame.Rect(x0 + n * (bw + gap), panel.top + 104, bw, 42)
        draw_button(screen, r, f"{n + 1} {label}", xp_font, hot=is_hovered(r), upper=False)
        add_click(r, lambda k=key: finish_oath_one(k), hover=None)
    cancel = pygame.Rect(0, 0, 130, 32)
    cancel.center = (panel.centerx, panel.top + 176)
    draw_button(screen, cancel, "Cancel  [Esc]", xp_font, hot=is_hovered(cancel), accent=GRIM_BAD, upper=False)
    add_click(cancel, cancel_oath_one, hover=None)


def _draw_circle_header(r, name, col, idxs, focused):
    """A dropdown header: accent band, chevron, circle name, vow and sworn counts."""
    is_open = name in bindings_open
    bg = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(bg, (26, 19, 11, 235) if is_open else (18, 13, 8, 225), bg.get_rect(), border_radius=5)
    screen.blit(bg, r.topleft)
    pygame.draw.rect(screen, darken(col, 0.35) if is_open else GRIM_GOLD_DEEP, r, width=1, border_radius=5)
    pygame.draw.rect(screen, col, pygame.Rect(r.left, r.top, 4, r.height), border_top_left_radius=5,
                     border_bottom_left_radius=5)
    if focused:
        pygame.draw.rect(screen, GRIM_GOLD_BRIGHT, r.inflate(4, 4), width=1, border_radius=7)

    # Chevron: points right when closed, down when open
    cx, cy = r.left + 22, r.centery
    tip = lighten(col, 0.3)
    if is_open:
        pygame.draw.polygon(screen, tip, [(cx - 6, cy - 3), (cx + 6, cy - 3), (cx, cy + 4)])
    else:
        pygame.draw.polygon(screen, tip, [(cx - 3, cy - 6), (cx - 3, cy + 6), (cx + 4, cy)])

    name_col = lighten(col, 0.35) if (is_open or focused) else lighten(col, 0.15)
    draw_heading(name, small_font, name_col, screen, r.left + 38,
                 r.centery - small_font.get_height() // 2, spacing=2, center=False)

    sworn_here = sum(1 for i in idxs if vow_is_sworn(VOWS[i]))
    count_txt = f"{len(idxs)} vow{'s' if len(idxs) != 1 else ''}"
    x = r.right - 14
    sw = f"{sworn_here} active"
    x -= xp_font.size(sw)[0]
    draw_text(sw, xp_font, GRIM_XP if sworn_here else GRIM_CREAM_FAINT, screen, x,
              r.centery - xp_font.get_height() // 2)
    dot = "  ·  "
    x -= xp_font.size(dot)[0]
    draw_text(dot, xp_font, GRIM_CREAM_FAINT, screen, x, r.centery - xp_font.get_height() // 2)
    x -= xp_font.size(count_txt)[0]
    draw_text(count_txt, xp_font, GRIM_CREAM_DIM if idxs else GRIM_CREAM_FAINT, screen, x,
              r.centery - xp_font.get_height() // 2)


def render_menu():
    # Near-opaque backdrop. The menu overlays the last rendered frame, so at a lighter
    # alpha the explore HUD and stage title bled through and sat behind the Codex title
    # and tabs — two lots of text competing in the same place.
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 5, 3, 248))
    screen.blit(overlay, (0, 0))

    # Menu Title
    draw_heading("Codex", title_font, GRIM_GOLD_BRIGHT, screen, SCREEN_WIDTH // 2, 30, spacing=8)

    # Draw Tabs
    tab_width = SCREEN_WIDTH // len(MENU_TABS)
    # Pick one font that fits the widest label in a tab, so a fourth tab ("EVOLUTION")
    # can't spill past its box. Uniform size keeps the row consistent.
    tab_inner = tab_width - 8 - 18
    tab_label_font = font
    if any(sum(font.size(c)[0] for c in n.upper()) + (len(n) - 1) > tab_inner for n in MENU_TABS):
        tab_label_font = small_font
    for i, tab_name in enumerate(MENU_TABS):
        is_active = (menu_tab == tab_name)
        tab_rect = pygame.Rect(i * tab_width + 4, 70, tab_width - 8, 50)
        if is_active:
            draw_glow_rect(screen, tab_rect, GRIM_GOLD, border_radius=6, layers=3, max_alpha=60, spread=3)
            draw_gradient_rect(screen, tab_rect, (58, 44, 18), (28, 21, 11), border_radius=6)
            pygame.draw.rect(screen, GRIM_GOLD, tab_rect, width=2, border_radius=6)
            draw_filigree_corners(screen, tab_rect, color=GRIM_GOLD, arm=10, inset=4, node=5)
            color = GRIM_GOLD_BRIGHT
        else:
            tab_bg = pygame.Surface(tab_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(tab_bg, (20, 15, 9, 190), tab_bg.get_rect(), border_radius=6)
            screen.blit(tab_bg, tab_rect.topleft)
            pygame.draw.rect(screen, GRIM_GOLD_DEEP, tab_rect, width=1, border_radius=6)
            color = GRIM_CREAM_DIM
        draw_heading(tab_name, tab_label_font, color, screen, tab_rect.centerx, tab_rect.centery, spacing=1)
        if not is_active:
            add_click(tab_rect, lambda n=tab_name: select_menu_tab(n))

    # Tab Content
    content_rect = pygame.Rect(50, 140, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 200)
    draw_panel(screen, content_rect, border_radius=6, alpha=215)

    if menu_tab == "Stats":
        # Level and points share one line so the page has room for gear and vows below
        y = content_rect.top + 24
        lvl_txt = f"Level {player_stats['level']}" + (f" {player_stats['class']}" if player_stats.get("class") else "")
        pts_txt = f"Stat Points Available: {player_stats['stat_points']}"
        gap_txt = "     ·     "
        lx = content_rect.centerx - (font.size(lvl_txt)[0] + small_font.size(gap_txt)[0] + font.size(pts_txt)[0]) // 2
        draw_text(lvl_txt, font, GRIM_CREAM, screen, lx, y - font.get_height() // 2)
        lx += font.size(lvl_txt)[0]
        draw_text(gap_txt, small_font, GRIM_CREAM_FAINT, screen, lx, y - small_font.get_height() // 2)
        lx += small_font.size(gap_txt)[0]
        draw_text(pts_txt, font, GRIM_XP, screen, lx, y - font.get_height() // 2)
        summary = class_summary()
        if summary:
            draw_text(fit_text(summary, xp_font, content_rect.width - 60), xp_font, GRIM_CREAM_DIM,
                      screen, content_rect.centerx, content_rect.top + 46, center=True)
        y = content_rect.top + (60 if summary else 46)
        
        total_stats = calculate_total_stats()
        stats_to_show = [
            ("Health", player_stats['max_hp'], total_stats['max_hp'], "max_hp"),
            ("Mana", player_stats['max_mana'], total_stats['max_mana'], "max_mana"),
            ("Melee Strength", player_stats['melee_strength'], total_stats['melee_strength'], "melee_strength"),
            ("Element Strength", player_stats['element_strength'], total_stats['element_strength'], "element_strength"),
            ("Defense", player_stats['defense'], total_stats['defense'], "defense")
        ]
        
        for i, (name, base_val, total_val, stat_key) in enumerate(stats_to_show):
            is_sel = (stats_sub_state == STATS_SUBSTATE_NAVIGATING and selected_stat_index == i)
            stat_text = f"{name}: {total_val} ({base_val} base)"
            text_rect = font.size(stat_text)
            text_rect = pygame.Rect(content_rect.left + 50, y, text_rect[0], text_rect[1])

            # Highlight the selected stat: a SOLID dark backing under a soft gold frame, so
            # the text reads clearly. (A gold glow alone, with gold-bright text on top,
            # washed the two golds together and made the selection invisible.)
            if is_sel:
                # exactly one row tall, so it can't cover the rows above and below
                highlight_rect = pygame.Rect(text_rect.x - 12, y - 1, text_rect.width + 24, 30)
                draw_glow_rect(screen, highlight_rect, GRIM_GOLD, border_radius=6, layers=2, max_alpha=40, spread=2)
                fill = pygame.Surface(highlight_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(fill, (26, 19, 9, 248), fill.get_rect(), border_radius=6)
                screen.blit(fill, highlight_rect.topleft)
                pygame.draw.rect(screen, GRIM_GOLD, highlight_rect, 2, border_radius=6)
                draw_filigree_corners(screen, highlight_rect, color=GRIM_GOLD, arm=8, inset=3, node=5)

            text_surf = font.render(stat_text, True, GRIM_GOLD_BRIGHT if is_sel else GRIM_CREAM)
            screen.blit(text_surf, text_rect.topleft) # Draw the stat text
            pillar = player_stats.get("oath_one_stat") if has_vow(V_ONE) else None
            stat_locked = pillar is not None and stat_key != pillar
            has_points = player_stats["stat_points"] > 0 and not stat_locked
            plus_rect = pygame.Rect(content_rect.right - 44, y - 2, 28, 28)
            per_pt = "(locked by Oath of One)" if stat_locked else ("(x1.5 per point)" if pillar else "(+1 per point)")
            # With a [+] button showing, the note right-aligns against it instead of under it
            per_x = (plus_rect.left - 10 - small_font.size(per_pt)[0]) if has_points \
                else content_rect.right - 24 - small_font.size(per_pt)[0]
            draw_text(per_pt, small_font, GRIM_CREAM_FAINT, screen, per_x, y)
            if has_points:
                draw_button(screen, plus_rect, "+", font)
                add_click(plus_rect, lambda k=stat_key: allocate_stat_point(k),
                          tip="Spend a stat point")
            y += 30

        # --- Gear: what each equipped item gives, then the combined bonus ---
        gy = y + 4
        pygame.draw.line(screen, GRIM_GOLD_DEEP, (content_rect.left + 40, gy),
                         (content_rect.right - 40, gy), 1)
        gy += 7
        col_slot, col_name, col_bonus = content_rect.left + 44, content_rect.left + 116, content_rect.left + 372
        row_h = xp_font.get_height() + 3
        for slot in EQUIP_SLOTS:
            item = player_stats["equipment"].get(slot)
            draw_text(slot, xp_font, GRIM_CREAM_FAINT, screen, col_slot, gy)
            if not item:
                draw_text("Empty", xp_font, GRIM_CREAM_FAINT, screen, col_name, gy)
            else:
                rc = RARITY_COLORS.get(item.get("rarity", "Common"), GRIM_CREAM)
                draw_text(fit_text(item["name"], xp_font, col_bonus - col_name - 12), xp_font, rc, screen, col_name, gy)
                bx = col_bonus
                parts = item_bonus_parts(slot, item)
                if not parts:
                    draw_text("no stat bonus", xp_font, GRIM_CREAM_FAINT, screen, bx, gy)
                for n, (_stat, label, pct, active) in enumerate(parts):
                    seg = ("" if n == 0 else "  ·  ") + f"{label} +{pct}%" + ("" if active else " (inactive)")
                    draw_text(seg, xp_font, GRIM_WARD if active else GRIM_CREAM_FAINT, screen, bx, gy)
                    bx += xp_font.size(seg)[0]
            gy += row_h
        gear = gear_bonus_pcts()
        g_segs = [("Gear bonuses:  ", GRIM_GOLD)]
        shown = [(lbl, gear[k]) for k, lbl in (("melee", "Melee"), ("element", "Element"), ("defense", "Defense")) if gear[k]]
        if shown:
            for n, (lbl, pct) in enumerate(shown):
                if n:
                    g_segs.append(("  ·  ", GRIM_CREAM_FAINT))
                g_segs.append((f"{lbl} +{pct}%", GRIM_WARD))
        else:
            g_segs.append(("none — equip gear from your satchel", GRIM_CREAM_FAINT))
        gx = content_rect.centerx - sum(small_font.size(t)[0] for t, _ in g_segs) // 2
        for t, c in g_segs:
            draw_text(t, small_font, c, screen, gx, gy + 3)
            gx += small_font.size(t)[0]

        # --- Vows: combined stat bonuses of everything sworn, then which vows those are ---
        sworn = player_stats.get("vows", [])
        vy = content_rect.bottom - 58
        pygame.draw.line(screen, GRIM_GOLD_DEEP, (content_rect.left + 40, vy - 8),
                         (content_rect.right - 40, vy - 8), 1)
        if not sworn:
            draw_text("No vows sworn — swear them on the Bindings tab.", small_font, GRIM_CREAM_FAINT,
                      screen, content_rect.centerx, vy + 10, center=True)
        else:
            labels = {"max_hp": "Health", "max_mana": "Mana", "melee_strength": "Melee",
                      "element_strength": "Element", "defense": "Defense"}
            summary = vow_stat_summary()
            segs = [("Vow bonuses:  ", GRIM_GOLD)]
            if summary:
                for n, (key, pct) in enumerate(summary.items()):
                    if n:
                        segs.append(("  ·  ", GRIM_CREAM_FAINT))
                    segs.append((f"{labels[key]} {'+' if pct > 0 else '−'}{abs(pct)}%",
                                 GRIM_WARD if pct > 0 else GRIM_BAD))
            else:
                segs.append(("none to stats", GRIM_CREAM_FAINT))
            # Every stat can be touched (Eternal Slumber): step down to the small font, then
            # drop the label, until the line fits inside the panel
            max_w = content_rect.width - 40
            seg_font = small_font
            if sum(seg_font.size(t)[0] for t, _ in segs) > max_w:
                seg_font = xp_font
            if sum(seg_font.size(t)[0] for t, _ in segs) > max_w:
                segs = segs[1:]
            total_w = sum(seg_font.size(t)[0] for t, _ in segs)
            sx = content_rect.centerx - total_w // 2
            for t, c in segs:
                draw_text(t, seg_font, c, screen, sx, vy + (small_font.get_height() - seg_font.get_height()) // 2)
                sx += seg_font.size(t)[0]
            names = "Sworn:  " + "  ·  ".join(sworn)
            draw_text(fit_text(names, xp_font, content_rect.width - 60), xp_font, GRIM_CREAM_DIM,
                      screen, content_rect.centerx, vy + 32, center=True)

    elif menu_tab == "Inventory":
        # Define the equipment box on the left side
        equipment_box_width = content_rect.width // 3
        equipment_rect = pygame.Rect(content_rect.left + 10, content_rect.top + 10, equipment_box_width - 15, content_rect.height - 20)
        draw_panel(screen, equipment_rect, bg_color=(16, 12, 7), border_radius=6, alpha=200,
                   glow=False, filigree=False)

        # Display Equipment within the new box
        eq_y = equipment_rect.top + 18
        draw_heading("Equipment", font, GRIM_GOLD_BRIGHT, screen, equipment_rect.centerx, eq_y + 6, spacing=3); eq_y += 40
        for eq_i, (slot, item) in enumerate(player_stats['equipment'].items()):
            row_rect = pygame.Rect(equipment_rect.left + 8, eq_y - 3, equipment_rect.width - 16, 24)
            eq_selected = (inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_EQUIP
                           and selected_equip_index == eq_i)
            row_bg = pygame.Surface(row_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(row_bg, (201, 162, 75, 16), row_bg.get_rect(), border_radius=4)
            screen.blit(row_bg, row_rect.topleft)
            if eq_selected:
                pygame.draw.rect(screen, GRIM_GOLD, row_rect, width=2, border_radius=4)
            if item:
                dot_color = RARITY_COLORS.get(item.get("rarity", "Common"), GRIM_CREAM)
                pygame.draw.circle(screen, dot_color, (row_rect.left + 9, row_rect.centery), 4)
                item_name = item['name']; name_color = GRIM_CREAM
            else:
                item_name = "Empty"; name_color = GRIM_CREAM_FAINT
            # Long gear names scroll within the panel instead of spilling out. A per-row
            # phase offset staggers them so they don't all slide in lock-step.
            text_x = row_rect.left + 20
            draw_scrolling_text(screen, f"{slot}: {item_name}", small_font, name_color,
                                text_x, eq_y, row_rect.right - text_x - 6, phase=eq_y * 0.05)
            add_click(row_rect, lambda i=eq_i: click_equip_slot(i))
            eq_y += 25

        # --- Item Grid Rendering ---
        items_area_x_start = equipment_rect.right + 20
        items_area_width = content_rect.right - items_area_x_start - 10
        items_area_y_start = content_rect.top + 20
        items_area_height = content_rect.height - 40

        # Title for Items section
        draw_heading("Satchel", font, GRIM_GOLD_BRIGHT, screen, items_area_x_start + items_area_width // 2, items_area_y_start + 6, spacing=4)

        # Calculate grid starting position to be centered in the remaining area
        grid_total_width = ITEM_GRID_COLS * ITEM_BOX_SIZE + (ITEM_GRID_COLS - 1) * ITEM_BOX_PADDING
        grid_total_height = ITEM_GRID_ROWS * ITEM_BOX_SIZE + (ITEM_GRID_ROWS - 1) * ITEM_BOX_PADDING

        grid_start_x = items_area_x_start + (items_area_width - grid_total_width) // 2
        grid_start_y = items_area_y_start + 50 + (items_area_height - 50 - grid_total_height) // 2 - 20 # Move up by 20 pixels

        for row in range(ITEM_GRID_ROWS):
            for col in range(ITEM_GRID_COLS):
                box_x = grid_start_x + col * (ITEM_BOX_SIZE + ITEM_BOX_PADDING)
                box_y = grid_start_y + row * (ITEM_BOX_SIZE + ITEM_BOX_PADDING)
                box_rect = pygame.Rect(box_x, box_y, ITEM_BOX_SIZE, ITEM_BOX_SIZE)

                is_selected = (inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_ITEMS and
                               selected_item_row == row and selected_item_col == col)
                item_index = row * ITEM_GRID_COLS + col
                has_item = item_index < len(player_stats['inventory'])
                add_click(box_rect, lambda r=row, c=col: click_satchel_cell(r, c))

                if has_item:
                    item = player_stats['inventory'][item_index]
                    slot_color = RARITY_COLORS.get(item.get("rarity", "Common"), WHITE)
                    glyph_color = slot_color if sum(slot_color[:3]) > 90 else lighten(slot_color, 0.55)
                    if is_selected:
                        draw_glow_rect(screen, box_rect, slot_color, border_radius=5, layers=3, max_alpha=100, spread=6)
                    # Dark neutral cell with a rarity-coloured frame — the rarity reads from
                    # the outline and the glyph, not a loud fill (matches the mockup satchel).
                    draw_gradient_rect(screen, box_rect, (42, 32, 18), (20, 15, 8), border_radius=5)
                    pygame.draw.rect(screen, slot_color, box_rect, width=3 if is_selected else 2, border_radius=5)
                    draw_text(item_glyph(item), xp_font, glyph_color, screen, box_rect.centerx, box_rect.centery, center=True)
                else:
                    empty_bg = pygame.Surface(box_rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(empty_bg, (255, 255, 255, 10), empty_bg.get_rect(), border_radius=5)
                    screen.blit(empty_bg, box_rect.topleft)
                    if is_selected:
                        draw_glow_rect(screen, box_rect, ITEM_HIGHLIGHT_COLOR, border_radius=5, layers=3, max_alpha=90, spread=6)
                        pygame.draw.rect(screen, ITEM_HIGHLIGHT_COLOR, box_rect, width=3, border_radius=5)
                    else:
                        pygame.draw.rect(screen, GRIM_GOLD_DEEP, box_rect, width=1, border_radius=5)

        # Show selected item details. The notice banner occupies this same slot, so the
        # detail panel yields to it for the few seconds a notice is up.
        if inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_ITEMS and not notice_active():
            sel_index = selected_item_row * ITEM_GRID_COLS + selected_item_col
            if sel_index < len(player_stats['inventory']):
                sel_item = player_stats['inventory'][sel_index]
                sel_rarity_color = RARITY_COLORS.get(sel_item.get("rarity", "Common"), WHITE)
                detail_rect = pygame.Rect(items_area_x_start, grid_start_y + grid_total_height + 12,
                                           items_area_width, 68)
                draw_panel(screen, detail_rect, border_color=sel_rarity_color,
                           border_radius=6, alpha=205, glow_color=sel_rarity_color, glow=True,
                           filigree=False)
                detail_y = detail_rect.top + 8
                draw_text(f"Selected: {sel_item['name']}", small_font, GRIM_GOLD_BRIGHT, screen, detail_rect.left + 12, detail_y)

                stats = get_item_stats(sel_item)
                stat_desc = []
                if sel_item.get("name") in POTION_DATA:
                    stat_desc.append(potion_effect_text(sel_item["name"]))
                elif sel_item.get("name") == OATHBREAKER:
                    stat_desc.append("Breaks one sworn vow")
                elif sel_item.get("name") in TRUE_SIGIL_TO_BASE:
                    _b = TRUE_SIGIL_TO_BASE[sel_item["name"]]
                    stat_desc.append(f"Masters {_b} » {TRUE_ELEMENTS[_b]} at Lv{true_form_level()}")
                if stats.get("melee_boost", 0) > 0: stat_desc.append(f"Melee +{stats['melee_boost']}")
                if stats.get("magic_boost", 0) > 0: stat_desc.append(f"Magic +{stats['magic_boost']}")
                if stats.get("defense_boost", 0) > 0: stat_desc.append(f"Defense +{stats['defense_boost']}")
                if stats.get("element_boost", 0) > 0 and sel_item.get("element") not in [None, "None"]:
                    stat_desc.append(f"{sel_item.get('element')} Buff +{stats['element_boost']}")

                if stat_desc:
                    draw_text("  " + ", ".join(stat_desc), small_font, GRIM_WARD, screen, detail_rect.left + 12, detail_y + 18)

                rarity = sel_item.get("rarity", "Common")
                slot = sel_item.get("slot", "Item")
                draw_text(f"  {rarity} {slot}", small_font, sel_rarity_color, screen, detail_rect.left + 12, detail_y + 36)
                # Hint sits on the bottom row: long item names used to run straight into it
                is_consumable = (sel_item.get("name") in POTION_DATA
                                 or sel_item.get("name") in TRUE_SIGIL_TO_BASE
                                 or sel_item.get("name") == OATHBREAKER
                                 or sel_item.get("name", "").startswith("Evo Stone"))
                hint = "[ENTER] Use" if is_consumable else "[ENTER] Equip"
                hint_w = small_font.size(hint)[0]
                draw_text(hint, small_font, GRIM_CREAM, screen,
                          detail_rect.right - hint_w - 12, detail_y + 36)
                add_click(pygame.Rect(detail_rect.right - hint_w - 12, detail_y + 36, hint_w,
                                      small_font.get_height()).inflate(12, 6), use_selected_item)

        # Selected equipped item: its details + an unequip hint
        elif inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_EQUIP and not notice_active():
            eq_slot = EQUIP_SLOTS[selected_equip_index]
            eq_item = player_stats["equipment"].get(eq_slot)
            detail_rect = pygame.Rect(items_area_x_start, grid_start_y + grid_total_height + 12,
                                       items_area_width, 68)
            ec = RARITY_COLORS.get(eq_item.get("rarity", "Common"), WHITE) if eq_item else GRIM_GOLD_DIM
            draw_panel(screen, detail_rect, border_color=ec, border_radius=6, alpha=205,
                       glow_color=ec, glow=bool(eq_item), filigree=False)
            detail_y = detail_rect.top + 8
            if eq_item:
                draw_text(f"Equipped: {eq_item['name']}", small_font, GRIM_GOLD_BRIGHT, screen, detail_rect.left + 12, detail_y)
                stats = get_item_stats(eq_item)
                desc = []
                if stats.get("melee_boost", 0) > 0: desc.append(f"Melee +{stats['melee_boost']}")
                if stats.get("magic_boost", 0) > 0: desc.append(f"Magic +{stats['magic_boost']}")
                if stats.get("defense_boost", 0) > 0: desc.append(f"Defense +{stats['defense_boost']}")
                if stats.get("element_boost", 0) > 0 and eq_item.get("element") not in [None, "None"]:
                    desc.append(f"{eq_item.get('element')} Buff +{stats['element_boost']}")
                if desc:
                    draw_text("  " + ", ".join(desc), small_font, GRIM_WARD, screen, detail_rect.left + 12, detail_y + 18)
                draw_text(f"  {eq_item.get('rarity', 'Common')} {eq_slot}", small_font, ec, screen, detail_rect.left + 12, detail_y + 36)
                hint = "[ENTER] Unequip"
                hint_w = small_font.size(hint)[0]
                draw_text(hint, small_font, GRIM_CREAM, screen,
                          detail_rect.right - hint_w - 12, detail_y + 36)
                add_click(pygame.Rect(detail_rect.right - hint_w - 12, detail_y + 36, hint_w,
                                      small_font.get_height()).inflate(12, 6), unequip_selected)
            else:
                draw_text(f"{eq_slot}: Empty", small_font, GRIM_CREAM_DIM, screen, detail_rect.left + 12, detail_y)
                draw_text("Nothing equipped in this slot.", small_font, GRIM_CREAM_FAINT, screen, detail_rect.left + 12, detail_y + 20)

        # Fallback text when the grid is empty — hidden while a detail panel occupies that
        # same lower area (e.g. inspecting an equipped item to unequip it).
        if not player_stats['inventory'] and inventory_sub_state != INVENTORY_SUBSTATE_NAVIGATING_EQUIP:
            draw_text("Your satchel is empty.", small_font, GRIM_CREAM_FAINT, screen, items_area_x_start + items_area_width // 2, items_area_y_start + items_area_height - 30, center=True)

    elif menu_tab == "Info":
        render_info_page(content_rect)

    elif menu_tab == "Bindings":
        render_bindings_page(content_rect)

    elif menu_tab == "Evolution":
        current_elem = player_stats["element"]
        badge_rect = pygame.Rect(content_rect.centerx - 40, content_rect.top + 30, 80, 80)
        mastery_ready = true_master_available()[0] is not None
        if player_stats["pending_evolution"] or mastery_ready:
            draw_glow_rect(screen, badge_rect, GRIM_GOLD, border_radius=40, layers=5, max_alpha=110, spread=14)
            draw_gradient_rect(screen, badge_rect, (110, 90, 20), (50, 40, 5), border_radius=40)
            pygame.draw.circle(screen, GRIM_GOLD, badge_rect.center, 40, 3)
            if current_elem in element_icons:
                icon = get_element_icon(current_elem, 44)
                screen.blit(icon, icon.get_rect(center=badge_rect.center))
            y = badge_rect.bottom + 25
            draw_heading("Evolution Awaits" if player_stats["pending_evolution"] else "Mastery Awaits",
                         font, GRIM_WARD, screen, content_rect.centerx, y, spacing=3); y += 40
            draw_text("Press [ENTER] to open the Evolution rite", small_font, GRIM_CREAM, screen, content_rect.centerx, y, center=True)
            add_click(badge_rect, pygame.K_RETURN, tip="Open the Evolution rite")
            rite_w = small_font.size("Press [ENTER] to open the Evolution rite")[0]
            add_click(pygame.Rect(0, 0, rite_w + 16, small_font.get_height() + 8).move(
                content_rect.centerx - rite_w // 2 - 8, y - small_font.get_height() // 2 - 4), pygame.K_RETURN)
        else:
            dim_bg = pygame.Surface(badge_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(dim_bg, (40, 32, 18, 150), dim_bg.get_rect(), border_radius=40)
            screen.blit(dim_bg, badge_rect.topleft)
            pygame.draw.circle(screen, GRIM_GOLD_DEEP, badge_rect.center, 40, 2)
            if current_elem in element_icons:
                # copy(): the cache hands back a shared surface — set_alpha on it would
                # dim this element's icon everywhere else on screen too
                icon = get_element_icon(current_elem, 36).copy()
                icon.set_alpha(130)
                screen.blit(icon, icon.get_rect(center=badge_rect.center))
            y = badge_rect.bottom + 25
            draw_text("No evolutions currently available.", font, GRIM_CREAM_DIM, screen, content_rect.centerx, y, center=True); y += 40
            draw_text("Reach level 5, 10, 15… to unlock.", small_font, GRIM_CREAM_FAINT, screen, content_rect.centerx, y, center=True)

    draw_notice_banner(screen)   # potion feedback, where the item was used
    # Context-aware footer hint
    if menu_tab == "Inventory" and inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_EQUIP:
        footer = "[Up/Down] Slot   [Enter] Unequip   [Right] Satchel   [Esc] Back"
    elif menu_tab == "Inventory" and inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_ITEMS:
        footer = "[Arrows] Move   [Enter] Equip/Use   [Left] Equipment   [Esc] Back"
    elif menu_tab == "Bindings":
        footer = "[M / Esc] Back to Game    [Up/Down] Choose    [Enter / Click] Open · Swear"
    else:
        footer = "[M / Esc] Back to Game     [Left / Right] Change Tab"
    if footer.startswith("[M / Esc] Back to Game"):
        back_w = small_font.size("[M / Esc] Back to Game")[0]
        foot_x = SCREEN_WIDTH // 2 - small_font.size(footer)[0] // 2
        add_click(pygame.Rect(foot_x, SCREEN_HEIGHT - 30 - small_font.get_height() // 2, back_w,
                              small_font.get_height()).inflate(12, 8), pygame.K_ESCAPE)
    draw_text(footer, small_font, GRIM_CREAM_DIM, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30, center=True)
    if menu_tab == "Bindings":
        draw_vow_preview(screen)
    if _unbind["open"]:
        _draw_unbind_chooser(content_rect)

STAT_ALLOC_KEYS = ["max_hp", "max_mana", "melee_strength", "element_strength", "defense"]  # order matches the Stats tab


def allocate_stat_point(stat_key):
    """Spend one stat point on stat_key (from Enter or a click on its [+])."""
    if player_stats["stat_points"] <= 0:
        return
    pillar = player_stats.get("oath_one_stat") if has_vow(V_ONE) else None
    if pillar and stat_key != pillar:
        show_notice("Oath of One", "That stat is locked", "Only your chosen pillar may grow.", GRIM_WARN)
        return
    player_stats["stat_points"] -= 1
    per_point = STAT_POINT_VALUE.get(stat_key, 1)
    # Oath of One: the pillar gains 1.5x per point; fractions carry to the next point
    carry = player_stats.setdefault("one_carry", {})
    gain = per_point * (1.5 if pillar else 1.0) + carry.get(stat_key, 0.0)
    whole = int(gain)
    carry[stat_key] = gain - whole
    player_stats[stat_key] += whole
    if stat_key == "max_hp":
        player_stats["hp"] += whole # Also heal the player when increasing max HP
    elif stat_key == "max_mana":
        player_stats["mana"] += whole # Also restore mana when increasing max mana
    print(f"Allocated point to {stat_key}. New value: {player_stats[stat_key]}. Stat points left: {player_stats['stat_points']}")


# --- Bindings (vows) ---
_vow_flash = {"name": None, "at": 0}
VOW_FLASH_MS = 700


def vow_is_sworn(vow):
    return vow["name"] in player_stats.get("vows", [])


def vow_block_reason(vow):
    """Why this vow can't be sworn right now (short tag), or None if it can."""
    if vow_is_sworn(vow):
        return "Sworn"
    if len(player_stats.get("vows", [])) >= VOW_LIMIT:
        return f"{VOW_LIMIT} / {VOW_LIMIT} sworn"
    if vow_forbidden_locked(vow):
        return f"Stage {FORBIDDEN_UNLOCK_STAGE + 1}+"
    if vow_conflict(vow):
        return "Clashes"
    if vow_ineligible(vow):
        return "Ineligible"
    if player_stats["stat_points"] < VOW_STAT_COST:
        return f"Needs {VOW_STAT_COST} pts"
    return None


_oath_one = {"open": False, "index": None}   # Oath of One's stat chooser
ONE_STAT_CHOICES = [("max_hp", "Health"), ("max_mana", "Mana"), ("melee_strength", "Melee"),
                    ("element_strength", "Element"), ("defense", "Defense")]


_unbind = {"open": False}   # the Oathbreaker's Seal chooser


def begin_unbind():
    if not player_stats.get("vows"):
        show_notice("No Vows", OATHBREAKER, "You hold no vow to break.", GRIM_WARN)
        return
    _unbind["open"] = True


def cancel_unbind():
    _unbind["open"] = False


def unbind_vow(name):
    """Consume an Oathbreaker's Seal to break a sworn vow, undoing its one-time changes.
    The stat points spent on it are not returned — the seal frees the slot."""
    ps = player_stats
    seal = next((i for i, it in enumerate(ps["inventory"]) if it.get("name") == OATHBREAKER), None)
    _unbind["open"] = False
    if seal is None or name not in ps.get("vows", []):
        return False
    ps["inventory"].pop(seal)
    ps["vows"].remove(name)
    for stat, factor in VOW_MAX_MULTS.get(name, {}).items():
        _scale_max(stat, "hp" if stat == "max_hp" else "mana", 1.0 / factor)
    if name == V_RISING_TIER:
        ps["xp_to_next_level"] = max(1, int(round(ps["xp_to_next_level"] / 1.5)))
        check_for_level_up()
    elif name == V_ONE:
        ps["oath_one_stat"] = None
        ps["one_carry"] = {}
    show_notice("Vow Broken", name, "The seal shatters; the binding falls away.",
                RARITY_COLORS.get(OATHBREAKER_RARITY, GRIM_XP))
    print(f"Broke vow: {name}")
    return True


def _draw_unbind_chooser(content_rect):
    """Pick which sworn vow the Oathbreaker's Seal breaks."""
    sworn = list(player_stats.get("vows", []))
    add_click(content_rect, None, hover=None)            # swallow clicks behind the panel
    veil = pygame.Surface(content_rect.size, pygame.SRCALPHA)
    veil.fill((4, 3, 2, 200))
    screen.blit(veil, content_rect.topleft)
    row_h, bw = 42, 420
    panel = pygame.Rect(0, 0, 480, 132 + len(sworn) * (row_h + 8) + 44)
    panel.center = content_rect.center
    seal_col = RARITY_COLORS.get(OATHBREAKER_RARITY, GRIM_GOLD)
    draw_panel(screen, panel, border_radius=6, alpha=245, glow_color=seal_col)
    draw_heading(OATHBREAKER, font, seal_col, screen, panel.centerx, panel.top + 26, spacing=3, upper=False)
    draw_text("Choose a vow to break. The seal is consumed;", small_font, GRIM_CREAM_DIM,
              screen, panel.centerx, panel.top + 58, center=True)
    draw_text("the stat points spent on the vow are not returned.", small_font, GRIM_CREAM_DIM,
              screen, panel.centerx, panel.top + 80, center=True)
    y = panel.top + 104
    for n, name in enumerate(sworn):
        r = pygame.Rect(panel.centerx - bw // 2, y, bw, row_h)
        vow = vow_by_name(name) or {}
        accent = dict(VOW_CIRCLES).get(vow.get("circle"), GRIM_GOLD)
        draw_button(screen, r, f"{n + 1}   {name}", small_font, hot=is_hovered(r), accent=accent, upper=False)
        add_click(r, lambda v=name: unbind_vow(v), hover=None)
        y += row_h + 8
    cancel = pygame.Rect(0, 0, 130, 32)
    cancel.center = (panel.centerx, panel.bottom - 26)
    draw_button(screen, cancel, "Cancel  [Esc]", xp_font, hot=is_hovered(cancel), accent=GRIM_BAD, upper=False)
    add_click(cancel, cancel_unbind, hover=None)


def finish_oath_one(stat_key):
    index = _oath_one["index"]
    _oath_one.update(open=False, index=None)
    if index is not None:
        swear_vow(index, choice=stat_key)


def cancel_oath_one():
    _oath_one.update(open=False, index=None)


def swear_vow(index, choice=None):
    """Spend VOW_STAT_COST stat points and bind the vow. Permanent. Oath of One first asks
    which stat to raise (choice)."""
    if not 0 <= index < len(VOWS):
        return False
    vow = VOWS[index]
    if vow_block_reason(vow):
        return False
    if vow["name"] == V_ONE and choice is None:
        _oath_one.update(open=True, index=index)
        return False
    player_stats["stat_points"] -= VOW_STAT_COST
    player_stats.setdefault("vows", []).append(vow["name"])
    if vow["name"] == V_ONE:
        player_stats["oath_one_stat"] = choice
    _on_vow_sworn(vow["name"])
    if callable(vow.get("apply")):
        vow["apply"](player_stats)
    # The card itself flares gold (a banner would sit right over the vow list)
    _vow_flash["name"] = vow["name"]
    _vow_flash["at"] = pygame.time.get_ticks()
    print(f"Swore vow: {vow['name']}. Stat points left: {player_stats['stat_points']}")
    return True


def click_vow(index):
    """First click picks a vow; clicking the picked vow again swears it."""
    global bindings_focus
    if bindings_focus == ("vow", index):
        swear_vow(index)
    else:
        bindings_focus = ("vow", index)


def vow_circle_of(vow):
    circle = vow.get("circle")
    return circle if circle in dict(VOW_CIRCLES) else VOW_UNBOUND


def bindings_sections():
    """[(circle, colour, [vow indices])] in display order. Every circle is listed even when
    empty; the Unbound section appears only if some vow needs it."""
    sections = [(name, col, [i for i, v in enumerate(VOWS) if vow_circle_of(v) == name])
                for name, col in VOW_CIRCLES]
    stray = [i for i, v in enumerate(VOWS) if vow_circle_of(v) == VOW_UNBOUND]
    if stray:
        sections.append((VOW_UNBOUND, GRIM_CREAM_DIM, stray))
    return sections


def bindings_nav_items():
    """Everything Up/Down can land on, top to bottom: each header, then its cards if open."""
    items = []
    for name, _col, idxs in bindings_sections():
        items.append(("circle", name))
        if name in bindings_open:
            items.extend(("vow", i) for i in idxs)
    return items


def toggle_circle(name):
    global bindings_focus
    if name in bindings_open:
        bindings_open.discard(name)
    else:
        bindings_open.add(name)
    bindings_focus = ("circle", name)


def scroll_bindings(dy):
    global bindings_scroll
    bindings_scroll = max(0, bindings_scroll + dy)   # the renderer clamps the far end


# --- Mouse actions for the Codex menu (things no single hotkey expresses) ---
def select_menu_tab(name):
    global menu_tab, inventory_sub_state, selected_item_row, selected_item_col, stats_sub_state, selected_stat_index
    global bindings_focus
    menu_tab = name
    bindings_focus = None
    cancel_oath_one()
    cancel_unbind()
    inventory_sub_state = INVENTORY_SUBSTATE_VIEWING; selected_item_row = -1; selected_item_col = -1
    stats_sub_state = STATS_SUBSTATE_VIEWING; selected_stat_index = -1


def set_info_page(index):
    global info_page
    info_page = index


def click_satchel_cell(row, col):
    """First click selects a cell; clicking the selected cell again uses/equips it."""
    global inventory_sub_state, selected_item_row, selected_item_col
    if (inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_ITEMS
            and (selected_item_row, selected_item_col) == (row, col)):
        use_selected_item()
        return
    inventory_sub_state = INVENTORY_SUBSTATE_NAVIGATING_ITEMS
    selected_item_row, selected_item_col = row, col


def use_selected_item():
    index = selected_item_row * ITEM_GRID_COLS + selected_item_col
    if 0 <= index < len(player_stats["inventory"]):
        use_item(index)


def click_equip_slot(index):
    """First click selects an equipment slot; clicking it again unequips."""
    global inventory_sub_state, selected_equip_index
    if inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_EQUIP and selected_equip_index == index:
        unequip_item(EQUIP_SLOTS[index])
        return
    inventory_sub_state = INVENTORY_SUBSTATE_NAVIGATING_EQUIP
    selected_equip_index = index


def unequip_selected():
    unequip_item(EQUIP_SLOTS[selected_equip_index])


def handle_menu_event(event):
    global game_state, menu_tab, inventory_sub_state, selected_item_row, selected_item_col, stats_sub_state, selected_stat_index, info_page, selected_equip_index
    global bindings_focus
    if event.type == pygame.KEYDOWN and _unbind["open"]:
        sworn = player_stats.get("vows", [])
        if pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < len(sworn):
            unbind_vow(sworn[event.key - pygame.K_1])
        elif event.key in (pygame.K_ESCAPE, pygame.K_b, pygame.K_BACKSPACE):
            cancel_unbind()
        return
    if event.type == pygame.KEYDOWN and _oath_one["open"]:
        if pygame.K_1 <= event.key <= pygame.K_5:
            finish_oath_one(ONE_STAT_CHOICES[event.key - pygame.K_1][0])
        elif event.key in (pygame.K_ESCAPE, pygame.K_b, pygame.K_BACKSPACE):
            cancel_oath_one()
        return
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
            game_state = STATE_EXPLORE
            return
        
        # Tab Switching
        if inventory_sub_state == INVENTORY_SUBSTATE_VIEWING: # Only allow tab switching when not navigating items
            if event.key == pygame.K_RIGHT:
                current_index = MENU_TABS.index(menu_tab)
                menu_tab = MENU_TABS[(current_index + 1) % len(MENU_TABS)]
            elif event.key == pygame.K_LEFT:
                current_index = MENU_TABS.index(menu_tab)
                menu_tab = MENU_TABS[(current_index - 1) % len(MENU_TABS)]
        # Tab Specific Logic
        if menu_tab == "Stats":
            stats_to_show_keys = STAT_ALLOC_KEYS
            
            if stats_sub_state == STATS_SUBSTATE_VIEWING:
                if event.key == pygame.K_RETURN:
                    stats_sub_state = STATS_SUBSTATE_NAVIGATING
                    selected_stat_index = 0 # Select the first stat by default
            elif stats_sub_state == STATS_SUBSTATE_NAVIGATING:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_m or event.key == pygame.K_b:
                    stats_sub_state = STATS_SUBSTATE_VIEWING
                    selected_stat_index = -1
                elif event.key == pygame.K_UP:
                    selected_stat_index = max(0, selected_stat_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_stat_index = min(len(stats_to_show_keys) - 1, selected_stat_index + 1)
                elif event.key == pygame.K_RETURN:
                    if 0 <= selected_stat_index < len(stats_to_show_keys):
                        allocate_stat_point(stats_to_show_keys[selected_stat_index])
        
        elif menu_tab == "Info":
            # Up/Down cycles the sub-pages (Left/Right is already taken by tab switching)
            if event.key == pygame.K_UP:
                info_page = (info_page - 1) % len(INFO_PAGES)
            elif event.key == pygame.K_DOWN:
                info_page = (info_page + 1) % len(INFO_PAGES)

        elif menu_tab == "Evolution":
            if ((player_stats["pending_evolution"] or true_master_available()[0] is not None)
                    and event.key == pygame.K_RETURN):
                game_state = STATE_EVOLVE
                return

        elif menu_tab == "Bindings":
            # Up/Down walks the headers and any open cards (Left/Right is tab switching).
            # Enter on a header opens/closes it; Enter on a picked vow swears it.
            items = bindings_nav_items()
            pos = items.index(bindings_focus) if bindings_focus in items else -1
            if event.key == pygame.K_UP:
                bindings_focus = items[max(0, pos - 1)]
            elif event.key == pygame.K_DOWN:
                bindings_focus = items[min(len(items) - 1, pos + 1)]
            elif event.key == pygame.K_RETURN:
                if pos < 0:
                    bindings_focus = items[0]
                elif bindings_focus[0] == "circle":
                    toggle_circle(bindings_focus[1])
                else:
                    swear_vow(bindings_focus[1])
        
        elif menu_tab == "Inventory":

            if inventory_sub_state == INVENTORY_SUBSTATE_VIEWING:
                if event.key == pygame.K_RETURN:
                    inventory_sub_state = INVENTORY_SUBSTATE_NAVIGATING_ITEMS
                    selected_item_row = 0
                    selected_item_col = 0
            elif inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_ITEMS:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_m or event.key == pygame.K_b:
                    inventory_sub_state = INVENTORY_SUBSTATE_VIEWING
                    selected_item_row = -1
                    selected_item_col = -1
                elif event.key == pygame.K_UP:
                    selected_item_row = max(0, selected_item_row - 1)
                elif event.key == pygame.K_DOWN:
                    selected_item_row = min(ITEM_GRID_ROWS - 1, selected_item_row + 1)
                elif event.key == pygame.K_LEFT:
                    if selected_item_col == 0:
                        # Step off the left edge of the grid onto the equipment column
                        inventory_sub_state = INVENTORY_SUBSTATE_NAVIGATING_EQUIP
                        selected_equip_index = min(selected_equip_index, len(EQUIP_SLOTS) - 1)
                    else:
                        selected_item_col -= 1
                elif event.key == pygame.K_RIGHT:
                    selected_item_col = min(ITEM_GRID_COLS - 1, selected_item_col + 1)
                elif event.key == pygame.K_RETURN:
                    # Calculate inventory index from selected row and col
                    item_index = selected_item_row * ITEM_GRID_COLS + selected_item_col
                    if item_index < len(player_stats["inventory"]):
                        use_item(item_index)
            elif inventory_sub_state == INVENTORY_SUBSTATE_NAVIGATING_EQUIP:
                if event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_b):
                    inventory_sub_state = INVENTORY_SUBSTATE_VIEWING
                    selected_item_row = -1; selected_item_col = -1
                elif event.key == pygame.K_UP:
                    selected_equip_index = (selected_equip_index - 1) % len(EQUIP_SLOTS)
                elif event.key == pygame.K_DOWN:
                    selected_equip_index = (selected_equip_index + 1) % len(EQUIP_SLOTS)
                elif event.key == pygame.K_RIGHT:
                    # Back to the satchel grid
                    inventory_sub_state = INVENTORY_SUBSTATE_NAVIGATING_ITEMS
                    selected_item_col = 0
                elif event.key == pygame.K_RETURN:
                    unequip_item(EQUIP_SLOTS[selected_equip_index])


# <<< MODIFIED UPDATE COMBAT >>>
# ==================== Kill Hold ====================
# A killing blow used to switch straight to the reroll/evolve (or game-over) screen on the
# same frame, so the bolt, the death burst and any "super effective" callout never showed.
# Instead combat is held on screen until the blow lands, plus a beat for the aftermath.
# The timer runs on frame dt, so it pauses along with the game.
KILL_HOLD_AFTER_IMPACT = 1.1
KILL_HOLD_SKIP_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
_kill_hold = {"active": False, "t": 0.0, "impact": 0.0, "dur": 0.0,
              "next": None, "on_finish": None, "victory": True}


def begin_kill_hold(next_state, impact_delay, victory=True, on_finish=None):
    global combat_turn, is_in_combat_delay
    _kill_hold.update(active=True, t=0.0, impact=impact_delay,
                      dur=impact_delay + KILL_HOLD_AFTER_IMPACT,
                      next=next_state, on_finish=on_finish, victory=victory)
    combat_turn = 'hold'
    is_in_combat_delay = False


def kill_hold_active():
    return _kill_hold["active"]


def kill_hold_landed():
    """Seconds since the killing blow landed, or None before it has."""
    h = _kill_hold
    if not h["active"] or h["t"] < h["impact"]:
        return None
    return h["t"] - h["impact"]


def tick_kill_hold(dt):
    if _kill_hold["active"]:
        _kill_hold["t"] += dt
        if _kill_hold["t"] >= _kill_hold["dur"]:
            _finish_kill_hold()


def skip_kill_hold():
    # Only once the blow has landed, so a key still held from the attack can't swallow it
    if kill_hold_landed() is not None:
        _finish_kill_hold()


def cancel_kill_hold():
    _kill_hold["active"] = False
    _kill_hold["on_finish"] = None


def _finish_kill_hold():
    global game_state, combat_turn
    h = _kill_hold
    h["active"] = False
    if h["on_finish"]:
        h["on_finish"]()
        h["on_finish"] = None
    game_state = h["next"]
    combat_turn = 'player'
# ==================== end Kill Hold ====================


def update_combat():
    global combat_turn, combat_message, game_state, player_combat_action, level_up_message, combat_sub_state, player_selected_skill
    global is_in_combat_delay, combat_delay_start_time, next_combat_turn_after_delay # Declare globals

    level_up_message = "" # Clear level up message at start of combat update

    if combat_turn == 'hold':   # a killing blow is still playing out
        return

    # --- Check Combat Delay ---
    if is_in_combat_delay:
        current_time = pygame.time.get_ticks()
        if current_time - combat_delay_start_time >= COMBAT_DELAY_DURATION:
            is_in_combat_delay = False # Delay over
            combat_turn = next_combat_turn_after_delay # Set the next turn
            combat_message = "" # Clear message after delay
            if combat_turn == 'player':
                 combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION # Reset sub-state for player
                 if has_vow(V_DRY_WELL) and player_stats["mana"] < player_stats["max_mana"]:
                     player_stats["mana"] = min(player_stats["max_mana"],
                                                player_stats["mana"] + max(1, player_stats["max_mana"] // 10))
            print(f"Delay ended. Starting {combat_turn}'s turn.") # Debug
        else:
            return # Still waiting for delay, skip rest of update
    # --- End Combat Delay Check ---


    # --- Start of Turn Updates (Cooldown) ---
    if combat_turn == 'player' and not is_in_combat_delay:
        if player_combat_action is None and combat_sub_state == COMBAT_SUBSTATE_CHOOSE_ACTION:
             if player_stats['awakening_cooldown'] > 0:
                 player_stats['awakening_cooldown'] -= 1
    # --- End Start of Turn ---


    if combat_turn == 'player':
        if player_combat_action is not None: # An action (A, W->Skill, D, F, V) has been selected
            action_to_process = player_combat_action
            selected_skill_info = player_selected_skill # Store potential skill info

            player_combat_action = None # Consume the action choice
            # Keep player_selected_skill for effectiveness check after attack
            player_stats["last_action"] = {
                COMBAT_ACTION_ATTACK: "skills" if selected_skill_info else "melee",
                COMBAT_ACTION_DEFEND: "defend", COMBAT_ACTION_FLEE: "flee",
                COMBAT_ACTION_CHARGE: "charge", COMBAT_ACTION_AWAKEN: "awaken",
                COMBAT_ACTION_ITEM: "items",
            }.get(action_to_process)

            player_stats["is_defending"] = False

            # --- Handle Awakening Activation ---
            if action_to_process == COMBAT_ACTION_AWAKEN:
                 player_stats["is_awakened"] = True
                 player_stats["awakening_duration"] = AWAKENING_BASE_DURATION + (2 if has_vow(V_LONG_AWAKE) else 0)
                 player_stats["awakening_cooldown"] = AWAKENING_BASE_COOLDOWN * (2 if has_vow(V_LONG_AWAKE) else 1) + 1
                 if has_vow(V_EARLY_WAKE):
                     player_stats["hp"] = max(1, player_stats["hp"] - early_wake_cost())
                 awakening_name = AWAKENING_NAMES.get(player_stats["element"], "Power Unleashed")
                 combat_message = f"You unleash {awakening_name}!"; print(f"Player Awakened! Duration: {player_stats['awakening_duration']}, Cooldown: {player_stats['awakening_cooldown']}")
                 vfx_aura(player_stats["element"], combat_anchor_player(), root=player_branch_root())
                 # Awakening consumes the turn, EOT processing will happen below

            # --- Handle Mana Charge ---
            elif action_to_process == COMBAT_ACTION_CHARGE:
                charge_amt = 40 if has_vow(V_HOLLOW) else 20
                if player_stats.get("is_overcharged") and player_stats["mana"] >= player_stats["max_mana"]:
                    combat_message = "You are already overcharged!"
                elif player_stats.get("is_overcharged"):
                    player_stats["mana"] = min(player_stats["mana"] + charge_amt, player_stats["max_mana"])
                    combat_message = f"You charge mana! ({player_stats['mana']}/{player_stats['max_mana']} MP)"
                elif player_stats["mana"] >= player_stats["max_mana"]:
                    player_stats["is_overcharged"] = True
                    player_stats["mana"] = player_stats["max_mana"] + 40
                    if overcharge_strike_ready():
                        _bonus_turn["active"] = True
                        combat_message = "OVERCHARGE! Strike again before the foe can act — elemental attacks only!"
                        raise_signal("surge", "Overcharge! Bonus elemental strike!")
                    else:
                        combat_message = "OVERCHARGE! Your next skill strikes 20% harder."
                        raise_signal("surge", "Mana surges beyond its limit!")
                else:
                    player_stats["mana"] = min(player_stats["mana"] + charge_amt, player_stats["max_mana"])
                    combat_message = f"You charge mana! ({player_stats['mana']}/{player_stats['max_mana']} MP)"
                vfx_gather(player_stats["element"], combat_anchor_player(), root=player_branch_root())
                if player_stats.get("is_overcharged"):
                    vfx_flash(vfx_color(player_stats["element"]), 0.4)

            # --- Handle Attack (Skill or Melee) ---
            elif action_to_process == COMBAT_ACTION_ATTACK:
                _bonus_turn["active"] = False          # a bonus strike, if this was one, is spent
                damage = 0; attack_name = "Attack"; player_element = player_stats["element"]

                # Cast VFX: a bolt of the element for a skill, a bright arc for a swing.
                # Choreographed to land inside the turn's COMBAT_DELAY_DURATION window.
                # Miss roll — heavier moves are riskier (see get_miss_chance). One For All is
                # the admin instakill, so it always connects.
                if player_element == "OFA":
                    attack_missed = False
                else:
                    attack_power = selected_skill_info.get('power', 1.0) if selected_skill_info else MELEE_POWER
                    attack_missed = roll_miss(attack_power)
                if selected_skill_info or player_element == "OFA":
                    _mult = vow_matchup(calculate_elemental_multiplier(player_element, current_enemy_encounter.element))
                    if attack_missed:
                        _on_hit = lambda: raise_signal("miss", "Your attack missed!")
                    else:
                        _on_hit = lambda m=_mult: signal_effectiveness(m)
                    _impact_delay = vfx_skill_cast(player_element, combat_anchor_player(), combat_anchor_enemy(),
                                                   power=1.6 if player_element == "OFA" else 1.0,
                                                   on_impact=_on_hit, miss=attack_missed,
                                                   root=player_branch_root(),
                                                   skill=selected_skill_info.get('name') if selected_skill_info else None)
                else:
                    _impact_delay = MELEE_IMPACT
                    vfx_melee(combat_anchor_enemy(), vfx_color(player_element), miss=attack_missed,
                              element=player_element if has_elemental_infusion() else None,
                              root=player_branch_root())
                    if attack_missed:
                        vfx_after(0.15, lambda: raise_signal("miss", "Your attack missed!"))

                # --- OFA Instakill (Tier 8 — Admin Only) ---
                if player_element == "OFA":
                    attack_name = selected_skill_info.get('name', 'One For All') if selected_skill_info else "One For All"
                    damage = current_enemy_encounter.hp  # Wipes remaining HP exactly
                    combat_message = f"ONE FOR ALL — {attack_name}! INSTANT KO!"

                elif selected_skill_info: # Using a Skill
                    attack_name = selected_skill_info.get('name', 'Skill Attack')
                    total_stats = calculate_total_stats()
                    current_ele_stat = total_stats["element_strength"] + (AWAKENING_ATK_BONUS if player_stats["is_awakened"] else 0)
                    # Single source of truth — the old if/elif chain didn't know about
                    # True forms and would have silently given them a x1.0 multiplier.
                    tier_multiplier = (get_element_damage_multiplier(player_element)
                                       * vow_tier_factor(player_element, current_enemy_encounter.element))
                    base_atk_power = current_ele_stat * tier_multiplier * selected_skill_info.get('power', 1.0)

                    elemental_multiplier = vow_matchup(calculate_elemental_multiplier(player_element, current_enemy_encounter.element))
                    base_damage = max(0, base_atk_power - current_enemy_encounter.defense)
                    damage = int(base_damage * elemental_multiplier * vow_damage_factor())
                    # Apply overcharge bonus and clear overcharge state (Vow of the Overflow
                    # keeps it for the rest of the fight)
                    overcharge_bonus = ""
                    if player_stats.get("is_overcharged"):
                        damage = int(damage * 1.2)
                        if not has_vow(V_OVERFLOW):
                            player_stats["is_overcharged"] = False
                            player_stats["mana"] = player_stats["max_mana"]
                        overcharge_bonus = " (OVERCHARGE +20%!)"
                    mana_cost = get_skill_mana_cost(player_element, attack_name)
                    if has_vow(V_BLOOD_TITHE):            # Blood Tithe: the element drinks HP
                        player_stats["hp"] = max(1, player_stats["hp"] - mana_cost)
                    else:
                        player_stats["mana"] = max(0, player_stats["mana"] - mana_cost)
                    cd_max = get_skill_cooldown_max(player_element, attack_name)
                    if cd_max > 0 and not player_stats.get("cooldowns_disabled"):
                        player_stats["skill_cooldowns"][attack_name] = cd_max
                    if attack_missed:
                        # Mana, cooldown and any overcharge are still spent: the move was
                        # thrown, it just didn't connect.
                        damage = 0
                        overcharge_bonus = " (the overcharge is spent)" if overcharge_bonus else ""
                        combat_message = f"You use {attack_name}, but it misses the {current_enemy_encounter.name}!{overcharge_bonus}"
                    else:
                        combat_message = f"You use {attack_name} on the {current_enemy_encounter.name} for {damage} damage points!{overcharge_bonus}"
                else: # ATTACK WITH MELEE
                    attack_name = "Melee Attack"
                    total_stats = calculate_total_stats()
                    current_melee_stat = total_stats["melee_strength"] + (AWAKENING_ATK_BONUS if player_stats["is_awakened"] else 0)
                    infused = has_elemental_infusion() and player_element != "OFA"
                    if infused:              # Elf Mage: the element rides on the swing
                        current_melee_stat += int(total_stats["element_strength"] * INFUSION_ELEMENT_SHARE)
                    base_damage = max(0, current_melee_stat - current_enemy_encounter.defense)
                    infuse_mult = (vow_matchup(calculate_elemental_multiplier(player_element, current_enemy_encounter.element))
                                   if infused else 1.0)
                    damage = int(base_damage * infuse_mult * vow_damage_factor())
                    if infused:
                        damage = max(1, damage - INFUSION_DAMAGE_PENALTY)
                    if attack_missed:
                        damage = 0
                        combat_message = f"You swing at the {current_enemy_encounter.name}, but miss!"
                    elif infused:
                        attack_name = f"{player_element}-Infused Strike"
                        combat_message = f"You use {attack_name} on the {current_enemy_encounter.name} for {damage} damage!"
                        vfx_after(MELEE_IMPACT, lambda m=infuse_mult: signal_effectiveness(m))
                    else:
                        combat_message = f"You use {attack_name} on the {current_enemy_encounter.name} for {damage} damage!"

                # Apply damage and check defeat
                current_enemy_encounter.hp -= damage
                if current_enemy_encounter.hp <= 0:
                    current_enemy_encounter.hp = 0; current_enemy_encounter.alive = False; combat_message += f" You defeated the {current_enemy_encounter.name}!"
                    # The enemy comes apart when the blow actually lands, not when it's thrown
                    vfx_after(_impact_delay, lambda el=current_enemy_encounter.element:
                              vfx_death(el, combat_anchor_enemy()))

                    # --- AWARD VARIABLE XP BASED ON TIER (Corrected Formatting)--- <<< FIXED HERE
                    defeated_enemy_element = current_enemy_encounter.element
                    xp_gain = 0
                    if defeated_enemy_element in tier1_elements:
                        xp_gain = 5
                    elif defeated_enemy_element in tier2_elements:
                        xp_gain = 10
                    elif defeated_enemy_element in tier3_elements:
                        xp_gain = 15
                    elif defeated_enemy_element in tier4_elements:
                        xp_gain = 25
                    elif defeated_enemy_element in tier5_elements:
                        xp_gain = 50
                    elif defeated_enemy_element in tier6_elements:
                        xp_gain = 80
                    elif defeated_enemy_element in tier7_elements:
                        xp_gain = 120
                    else:
                        xp_gain = 5 # Default fallback
                    
                    # Scale XP based on current stage (2x per stage)
                    stage_multiplier = 2 ** (getattr(current_enemy_encounter, "tier", current_stage) - 1)
                    xp_gain = int(xp_gain * stage_multiplier)
                    
                    if current_enemy_encounter.is_boss:
                        xp_gain *= 3
                    
                    # --- END CORRECTED XP LOGIC BLOCK ---

                    xp_gain = int(xp_gain * (1 + FOE_LEVEL_XP * (getattr(current_enemy_encounter, "level", 1) - 1)))
                    xp_gain = int(xp_gain * vow_xp_mult())
                    player_stats["xp"] += xp_gain; combat_message += f" Gained {xp_gain} XP!"
                    if has_vow(V_UNFLINCHING):          # Stand. Strike. Feed.
                        heal = max(1, int(player_stats["max_hp"] * 0.15))
                        player_stats["hp"] = min(player_stats["max_hp"], player_stats["hp"] + heal)
                        combat_message += f" You feed: +{heal} HP."
                    quest_note_kill(current_enemy_encounter)
                    player_stats["peak_tier"] = max(player_stats.get("peak_tier", 1),
                                                    getattr(current_enemy_encounter, "tier", 1))
                    _kill_ctx["boss"] = bool(current_enemy_encounter.is_boss)
                    _kill_ctx["final"] = GAME_MODE == "stages" and all(not e.alive for e in all_stage_enemies())
                    _gamble["cost"] = None
                    print(f"Defeated {defeated_enemy_element} enemy. Gained {xp_gain} XP. Player XP now: {player_stats['xp']}")
                    
                    old_level = player_stats["level"]
                    leveled_up = check_for_level_up()
                    new_level = player_stats["level"]

                    spins_won, spin_chances = roll_spin_drops(current_enemy_encounter.is_boss)
                    player_stats["reroll_spins"] += spins_won
                    _kill_ctx["spins"] = (spins_won, spin_chances)
                    combat_message += (f" {spins_won} spin{'s' if spins_won != 1 else ''} dropped!" if spins_won
                                       else " No spins dropped.")
                    print(f"Spin chances: {spins_won}/{spin_chances} came up. Total: {player_stats['reroll_spins']}")
                    
                    # --- ITEM DROP TRIGGER ---
                    drop = get_random_drop(current_enemy_encounter.element, is_boss=current_enemy_encounter.is_boss)
                    if drop:
                        player_stats["inventory"].append(drop)
                        combat_message += f" Found a {drop['name']}!"
                        print(f"Dropped item: {drop['name']} ({drop['slot']})")

                    # Check if any multiple of 5 was crossed
                    crossed_milestone = False
                    for lvl in range(old_level + 1, new_level + 1):
                        if lvl % 5 == 0:
                            crossed_milestone = True
                            break

                    if crossed_milestone and player_stats["element"] in EVOLUTION_MAP:
                        next_state = STATE_EVOLVE
                    else:
                        next_state = STATE_REROLL_PROMPT

                    def _restore_after_combat():
                        player_stats["mana"] = player_stats["max_mana"]; player_stats["is_overcharged"] = False; player_stats["skill_cooldowns"] = {}
                    combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION; player_selected_skill = None
                    # Hold on the fight until the killing blow and death burst have played
                    begin_kill_hold(next_state, _impact_delay, victory=True, on_finish=_restore_after_combat)
                    return # Exit update after defeat processing

            # --- Handle Items (the battle bag) ---
            elif action_to_process == COMBAT_ACTION_ITEM:
                name = _combat_item["pick"]; _combat_item["pick"] = None
                idx = next((i for i, it in enumerate(player_stats["inventory"]) if it.get("name") == name), None)
                hp0, mp0 = player_stats["hp"], player_stats["mana"]
                oc0 = player_stats.get("is_overcharged", False)
                if idx is not None and use_potion(idx):
                    _quiet_notice()
                    gains = []
                    if player_stats["hp"] > hp0:
                        gains.append(f"+{player_stats['hp'] - hp0} HP")
                    if player_stats["mana"] > mp0:
                        gains.append(f"+{player_stats['mana'] - mp0} MP")
                    if player_stats.get("is_overcharged") and POTION_DATA[name]["kind"] == "mp_overcharge":
                        gains.append("OVERCHARGE")
                    combat_message = f"You drink the {name}! " + "  ".join(gains)
                    # An overcharge potion surges just like Charge does: a bonus elemental strike
                    if (not oc0 and player_stats.get("is_overcharged")
                            and POTION_DATA[name]["kind"] == "mp_overcharge" and overcharge_strike_ready()):
                        _bonus_turn["active"] = True
                        combat_message += "  Strike again before the foe can act — elemental attacks only!"
                        raise_signal("surge", "Overcharge! Bonus elemental strike!")
                    vfx_potion(POTION_DATA[name]["kind"], combat_anchor_player())
                else:
                    _quiet_notice()
                    combat_message = f"The {name} has no effect."

            # --- Handle Defend / Flee ---
            elif action_to_process == COMBAT_ACTION_DEFEND: player_stats["is_defending"] = True; combat_message = "You brace yourself!"
            elif action_to_process == COMBAT_ACTION_FLEE:
                if random.random() < 0.5:
                    current_enemy_encounter.flee_cooldown = 5.0  # 5 s grace before it can ambush again
                    current_enemy_encounter.ai_state = "retreat"  # actively move away from player
                    combat_message = "Successfully fled!"
                    player_stats["mana"] = player_stats["max_mana"]; player_stats["is_overcharged"] = False; player_stats["skill_cooldowns"] = {}
                    game_state = STATE_EXPLORE; combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION; player_selected_skill = None; is_in_combat_delay = False; return
                else: combat_message = "Failed to flee!" # Turn ends, delay starts

            # --- End of Player Turn Processing ---
            # Keep player_selected_skill until after effectiveness message might need it in render_combat next frame

            # Overcharge's bonus strike: the charge and the strike count as one turn, so skip
            # the end-of-turn ticks and hand control straight back with the skills open.
            if (_bonus_turn["active"] and action_to_process in (COMBAT_ACTION_CHARGE, COMBAT_ACTION_ITEM)
                    and game_state == STATE_COMBAT):
                combat_sub_state = COMBAT_SUBSTATE_CHOOSE_SKILL
                player_selected_skill = None
                return

            if player_stats["is_awakened"]:
                player_stats["awakening_duration"] -= 1; #print(f"Awakening duration left: {player_stats['awakening_duration']}")
                if player_stats["awakening_duration"] <= 0: player_stats["is_awakened"] = False; combat_message += " The power fades..."; print("Awakening faded.")

            # --- Tick Skill Cooldowns ---
            player_stats["skill_cooldowns"] = {
                k: v - 1 for k, v in player_stats["skill_cooldowns"].items() if v - 1 > 0
            }
            # --- End Tick Skill Cooldowns ---

            # --- Start Delay instead of switching turn ---
            if game_state == STATE_COMBAT:
                print("Player turn ended. Starting delay...")
                is_in_combat_delay = True
                combat_delay_start_time = pygame.time.get_ticks()
                next_combat_turn_after_delay = 'enemy'
                combat_turn = 'delay' # Set turn to intermediate state during delay
            # --- End Start Delay ---

    elif combat_turn == 'enemy':
        enemy = current_enemy_encounter
        total_stats = calculate_total_stats()
        awakened_defense = total_stats["defense"] + (AWAKENING_DEF_BONUS if player_stats["is_awakened"] else 0)
        player_current_defense = awakened_defense * 2 if player_stats["is_defending"] else awakened_defense
        player_stats["is_defending"] = False

        # Regen mana and tick cooldowns at turn start
        enemy.mana = min(enemy.max_mana, enemy.mana + enemy.mana_regen)
        enemy.skill_cooldowns = {k: v - 1 for k, v in enemy.skill_cooldowns.items() if v - 1 > 0}

        # Decide: use an elemental skill (65% chance) or melee
        available_skills = ELEMENT_SKILLS.get(enemy.element, DEFAULT_SKILLS)
        usable_skills = [
            s for s in available_skills
            if enemy.mana >= get_skill_mana_cost(enemy.element, s['name'])
            and enemy.skill_cooldowns.get(s['name'], 0) == 0
        ]

        if usable_skills and random.random() < 0.65:
            skill = random.choice(usable_skills)
            mana_cost = get_skill_mana_cost(enemy.element, skill['name'])
            cd_max = get_skill_cooldown_max(enemy.element, skill['name'])
            enemy.mana -= mana_cost
            if cd_max > 0:
                enemy.skill_cooldowns[skill['name']] = cd_max
            base_damage = max(0, enemy.attack * skill['power'] - player_current_defense)
            elemental_mult = calculate_elemental_multiplier(enemy.element, player_stats["element"])
            damage = int(base_damage * elemental_mult)
            enemy_missed = roll_miss(skill['power'])
            if enemy_missed:
                damage = 0
                combat_message = f"The {enemy.name} uses {skill['name']}, but it misses you!"
                _on_hit = lambda: raise_signal("miss", f"The {enemy.name} missed!")
            else:
                combat_message = f"The {enemy.name} uses {skill['name']} on you for {damage} damage!"
                _on_hit = lambda m=elemental_mult: signal_effectiveness(m)
            _impact_delay = vfx_skill_cast(enemy.element, combat_anchor_enemy(), combat_anchor_player(),
                                           on_impact=_on_hit, miss=enemy_missed,
                                           root=branch_root(enemy.element), skill=skill['name'])
        else:
            # Melee — still apply elemental matchup as a flavour of the creature's nature
            base_damage = max(0, enemy.attack - player_current_defense)
            damage = int(base_damage)
            enemy_missed = roll_miss(MELEE_POWER)
            if enemy_missed:
                damage = 0
                combat_message = f"The {enemy.name} lunges at you, but misses!"
                vfx_after(0.15, lambda: raise_signal("miss", f"The {enemy.name} missed!"))
            else:
                combat_message = f"The {enemy.name} attacks you for {damage} damage!"
            _impact_delay = MELEE_IMPACT
            vfx_melee(combat_anchor_player(), vfx_color(enemy.element), flip=True, miss=enemy_missed,
                      element=None,
                      root=branch_root(enemy.element))

        if has_vow(V_BERSERKER):
            damage = int(round(damage * BERSERKER_DAMAGE_TAKEN))
        if damage > 0 and random.random() < race_value("shrug", 0.0):   # Skeleton: Undying
            damage = 0
            combat_message += " It rattles harmlessly off your bones!"
        if player_stats.get("is_god"):
            damage = 0
        elif has_vow(V_ECLIPSE):                  # the hand holding sun and moon is burning
            burn = max(1, int(round(player_stats["max_hp"] * ECLIPSE_BURN_PCT)))
            damage += burn
            combat_message += f" The eclipse sears you for {burn}."
        player_stats["hp"] -= damage
        if player_stats["hp"] <= 0 and martyr_can_save():
            player_stats["hp"] = 1
            player_stats["martyr_used"] = True
            combat_message += " Covenant of the Martyr — death is refused!"

        if player_stats["hp"] <= 0:
            player_stats["hp"] = 0; combat_message += " You have been defeated!"
            vfx_after(_impact_delay, lambda: (vfx_flash(GRIM_HP, 0.45), vfx_shake(7.0)))
            begin_kill_hold(STATE_GAME_OVER, _impact_delay, victory=False)
            return

        # --- Start Delay ---
        if game_state != STATE_GAME_OVER:
            is_in_combat_delay = True
            combat_delay_start_time = pygame.time.get_ticks()
            next_combat_turn_after_delay = 'player'
            combat_turn = 'delay'
# <<< END MODIFIED UPDATE COMBAT >>>

def execute_admin_command(command_str):
    """Parses and executes an admin command."""
    global current_stage
    # Helpfully strip leading slash if user included it
    clean_command = command_str.strip()
    if clean_command.startswith('/'):
        clean_command = clean_command[1:]
    
    parts = clean_command.split()
    if not parts:
        return "No command entered."

    cmd = parts[0].lower()
    args = parts[1:]

    try:
        if cmd == "level" and args:
            new_level = int(args[0])
            player_stats["level"] = new_level
            player_stats["xp_to_next_level"] = BASE_XP_TO_LEVEL_UP * new_level
            player_stats["xp"] = 0
            # Recalculate stats roughly
            player_stats["max_hp"] = 100 + (new_level - 1) * 5
            player_stats["hp"] = player_stats["max_hp"]
            player_stats["max_mana"] = 100
            player_stats["mana"] = player_stats["max_mana"]
            player_stats["melee_strength"] = 15 + (new_level - 1)
            player_stats["element_strength"] = 10 + (new_level - 1)
            player_stats["defense"] = 5 + (new_level - 1)
            player_stats["stat_points"] = (new_level - 1) * 3 + 5
            # This path sets the level directly rather than going through
            # check_for_level_up, so the True form unlock has to be run explicitly.
            unlocked = check_true_element_unlock()
            if unlocked:
                return f"Set level to {new_level}. TRUE FORM unlocked: {unlocked}."
            return f"Set level to {new_level}."

        elif cmd == "element" and args:
            ele_name = " ".join(args)
            matched = next((e for e in ALL_ELEMENTS if e.lower() == ele_name.lower()), None)
            if matched:
                player_stats["element"] = matched
                record_element_change(matched)
                return f"Element changed to {matched}."
            else:
                return f"Invalid element: {ele_name}."

        elif cmd == "item" and args:
            item_name = " ".join(args)
            found_item = find_item_by_name(item_name)
            if found_item:
                player_stats["inventory"].append(found_item)
                return f"Gave {found_item['name']} ({found_item.get('rarity', 'Common')})"
            else:
                return f"Error: '{item_name}' not in Database."

        elif cmd == "data":
            w_count = sum(len(t["items"]) for t in WEAPON_DATA)
            a_count = sum(len(items) for items in ARMOR_DATA.values())
            return f"Wps: {w_count}, Arm: {a_count}"

        elif cmd == "xp" and args:
            xp_to_add = int(args[0])
            player_stats["xp"] += xp_to_add
            check_for_level_up()
            return f"Added {xp_to_add} XP."

        elif cmd == "hp" and args:
            new_hp = int(args[0])
            player_stats["hp"] = min(new_hp, player_stats["max_hp"])
            return f"Set HP to {player_stats['hp']}."

        elif cmd == "reroll" and args:
            new_spins = int(args[0])
            player_stats["reroll_spins"] = new_spins
            return f"Set reroll spins to {new_spins}."

        elif cmd == "stage" and args:
            new_stage = int(args[0])
            global current_stage
            current_stage = new_stage
            setup_stage(current_stage)
            return f"Jumped to Stage {new_stage}."

        elif cmd == "god":
            player_stats["is_god"] = not player_stats["is_god"]
            return f"God Mode: {'ON' if player_stats['is_god'] else 'OFF'}."

        elif cmd == "cooldowns":
            current = player_stats.get("cooldowns_disabled", False)
            player_stats["cooldowns_disabled"] = not current
            return f"Skill cooldowns: {'DISABLED' if player_stats['cooldowns_disabled'] else 'ENABLED'}."

        elif cmd == "killall":
            count = 0
            for enemy in all_stage_enemies():
                if enemy.alive:
                    enemy.hp = 0
                    enemy.alive = False
                    count += 1
            return f"Killed {count} enemies."

        elif cmd == "heal":
            player_stats["hp"] = player_stats["max_hp"]
            return "Healed to full HP."

        elif cmd == "speed" and args:
            try:
                factor = float(args[0])
                global PLAYER_SPEED
                PLAYER_SPEED *= factor
                return f"Player speed multiplied by {factor}."
            except ValueError:
                return "Usage: speed <factor>"

        elif cmd == "teleport" and len(args) >= 2:
            try:
                tx = float(args[0])
                ty = float(args[1])
                # Clamp to map bounds and ensure it's an open tile
                tx = max(0.5, min(tx, MAP_WIDTH - 1.5))
                ty = max(0.5, min(ty, MAP_HEIGHT - 1.5))
                if 0 <= int(ty) < len(world_map) and 0 <= int(tx) < len(world_map[0]):
                    if world_map[int(ty)][int(tx)] == 0:  # 0 = floor tile
                        set_player_tile(int(tx), int(ty))
                        return f"Teleported to ({int(tx)}, {int(ty)})."
                    else:
                        return f"Tile ({int(tx)}, {int(ty)}) is a wall!"
                else:
                    return "Coordinates out of bounds."
            except ValueError:
                return "Usage: teleport <x> <y>"

        elif cmd == "luck" and args:
            try:
                luck_val = int(args[0])
                player_stats["luck"] = max(0, min(luck_val, 100))
                return f"Luck set to {player_stats['luck']}% (adds to drop chance)."
            except ValueError:
                return "Usage: luck <0-100>"

        elif cmd == "give" and args:
            sub = args[0].lower()
            val = args[1:] if len(args) > 1 else []
            
            if sub == "item" and val:
                item_name = " ".join(val)
                found_item = find_item_by_name(item_name)
                
                if found_item:
                    player_stats["inventory"].append(found_item)
                    rarity = found_item.get('rarity', 'Unknown')
                    return f"Gave {found_item['name']} (Tier: {rarity})"
                else:
                    return f"Error: '{item_name}' not found."
            elif sub == "stone" and val:
                try:
                    tier = int(val[0])
                    player_stats["inventory"].append({"name": f"Evo Stone (Tier {tier})", "tier": tier, "slot": "Consumables"})
                    return f"Gave Evo Stone (Tier {tier})"
                except ValueError: return "Usage: give stone <tier>"
            elif sub == "xp" and val:
                xp = int(val[0])
                player_stats["xp"] += xp
                check_for_level_up()
                return f"Gave {xp} XP."
            elif sub == "hp" and val:
                hp = int(val[0])
                player_stats["hp"] = min(player_stats["hp"] + hp, player_stats["max_hp"])
                return f"Gave {hp} HP."
            elif sub == "spins" and val:
                spins = int(val[0])
                player_stats["reroll_spins"] += spins
                return f"Gave {spins} spins."
            elif sub == "stones":
                for t in range(1, 8):
                    player_stats["inventory"].append({"name": f"Evo Stone (Tier {t})", "tier": t, "slot": "Consumables"})
                return "Gave all Tier Evo Stones."
            else:
                return "Usage: give <item|stone|xp|hp|spins> <value>"

        elif cmd == "help":
            return "Cmds: level, element, item, xp, hp, reroll, stage, give, god, killall, heal, speed, data, debug"

        elif cmd == "tiers":
            # List some weapons by tier
            lines = []
            for t in WEAPON_DATA:
                names = [it["name"] for it in t["items"][:2]] # first 2
                lines.append(f"{t['rarity']}: {', '.join(names)}...")
            return " | ".join(lines)

        elif cmd == "debug" and args:
            if args[0] == "inv":
                print("--- Inventory Debug ---")
                for i, item in enumerate(player_stats["inventory"]):
                    print(f"{i}: {item}")
                return "Dumped inventory to console."
            elif args[0] == "stats":
                atk, element_atk, defense, element_def_pct = calculate_total_stats()
                return f"Atk:{atk}, E_Atk:{element_atk}, Def:{defense}"
            return "Usage: debug <inv|stats>"

        else:
            return f"Unknown command: {cmd}"
    except Exception as e:
        return f"Error: {e}"

def find_item_by_name(name):
    """Searches potions, WEAPON_DATA and ARMOR_DATA for an item by name."""
    if not name: return None
    clean_name = name.strip().lower()
    print(f"[FIND_ITEM] Searching for: '{clean_name}' | WEAPON_DATA has {len(WEAPON_DATA)} tiers")

    # Potions
    for potion_name in POTION_DATA:
        if potion_name.lower() == clean_name:
            found = make_potion(potion_name)
            print(f"[FIND_ITEM] Found potion! {found}")
            return found

    if clean_name == OATHBREAKER.lower():
        return make_oathbreaker()

    # True Sigils
    for base, sigil_name in TRUE_SIGILS.items():
        if sigil_name.lower() == clean_name:
            found = make_true_sigil(base)
            print(f"[FIND_ITEM] Found True Sigil! {found}")
            return found

    # Search Weapons
    for tier in WEAPON_DATA:
        tier_rarity = tier.get("rarity", "Common")
        for item in tier.get("items", []):
            if item.get("name", "").lower().strip() == clean_name:
                copied_item = item.copy()
                copied_item["rarity"] = tier_rarity
                copied_item["slot"] = "Weapon"
                print(f"[FIND_ITEM] Found weapon! rarity='{tier_rarity}', item={copied_item}")
                return copied_item
    
    # Search Armor
    for slot, items in ARMOR_DATA.items():
        for item in items:
            if item.get("name", "").lower().strip() == clean_name:
                copied_item = item.copy()
                copied_item["slot"] = slot.capitalize()
                print(f"[FIND_ITEM] Found armor! rarity='{copied_item.get('rarity')}', item={copied_item}")
                return copied_item
    
    print(f"[FIND_ITEM] NOT FOUND: '{clean_name}'")
    return None

def get_admin_suggestions(text):
    """Returns a list of matching command suggestions based on current input."""
    text_lower = text.lower()
    
    if text_lower.startswith("give item "):
        prefix = "give item "
        query = text_lower[len(prefix):]
        all_items = list(POTION_DATA.keys()) + list(TRUE_SIGILS.values())
        for tier in WEAPON_DATA:
            for item in tier["items"]: all_items.append(item["name"])
        for slot in ARMOR_DATA:
            for item in ARMOR_DATA[slot]: all_items.append(item["name"])
        return [prefix + name for name in all_items if name.lower().startswith(query)]
    
    elif text_lower.startswith("give stone "):
        prefix = "give stone "
        query = text_lower[len(prefix):]
        return [prefix + str(t) for t in range(1, 8) if str(t).startswith(query)]

    elif text_lower.startswith("element "):
        prefix = "element "
        query = text_lower[len(prefix):]
        return ["element " + e for e in ALL_ELEMENTS if e.lower().startswith(query)]

    elif text_lower.startswith("teleport "):
        return ["teleport <x> <y>  — e.g., teleport 5 10"]

    # Default base command suggestions
    return [cmd for cmd in ADMIN_COMMANDS if cmd.startswith(text_lower)]

def render_admin_console():
    # Ink slab pinned to the bottom, ruled off with a ward-green hairline
    box_h = 120
    box_y = SCREEN_HEIGHT - box_h
    overlay = pygame.Surface((SCREEN_WIDTH, box_h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (6, 9, 6, 238), overlay.get_rect())
    screen.blit(overlay, (0, box_y))
    pygame.draw.line(screen, GRIM_WARD, (0, box_y), (SCREEN_WIDTH, box_y), 1)

    # Input line — the arcane sigil marks the prompt
    draw_text(f"»  Admin  /{admin_input_text}_", font, GRIM_WARD, screen, 20, box_y + 18)

    # Command suggestions
    if admin_input_text:
        suggestions = get_admin_suggestions(admin_input_text)
        if suggestions:
            suggestion_text = "suggestions: " + " · ".join(suggestions[:3])
            if len(suggestions) > 3: suggestion_text += " …"
            draw_text(suggestion_text, small_font, GRIM_CREAM_FAINT, screen, 20, box_y + 52)

    # Last result
    if admin_feedback:
        ok = any(w in admin_feedback for w in ("Gave", "Set", "Changed", "Jumped", "Added", "Healed", "Killed", "Teleported", "ON", "OFF"))
        color = GRIM_WARD if ok else GRIM_BAD
        draw_text(f"result: {admin_feedback}", small_font, color, screen, 20, box_y + 80)

    draw_text("[Enter] run   [Esc] close", small_font, GRIM_CREAM_DIM, screen, SCREEN_WIDTH - 240, box_y + 80)


# --- Pause Menu ---
_PAUSE_BTNS   = ["Resume", "Quit to Main Menu"]
_PAUSE_ACCENTS = [GRIM_GOLD, GRIM_BAD]   # Quit kindles crimson on hover
_pause_btn_rects  = [pygame.Rect(0, 0, 280, 52), pygame.Rect(0, 0, 280, 52)]
_pause_hover_anim = [0.0, 0.0]   # smooth hover blend per button

# Panel dimensions — buttons are positioned relative to panel top (py)
_PANEL_W  = 360
_PANEL_H  = 260   # tall enough to contain title + divider + 2 buttons + hint
_BTN_OFFSETS = [80, 152]  # y offset from py for each button

def _update_pause_rects():
    """Recalculate button rects from the panel position. Called each frame."""
    cx = SCREEN_WIDTH // 2
    py = SCREEN_HEIGHT // 2 - _PANEL_H // 2
    for i, offset in enumerate(_BTN_OFFSETS):
        _pause_btn_rects[i].centerx = cx
        _pause_btn_rects[i].y = py + offset

def render_pause_menu(frozen_state_fn):
    """Render the background game state then draw the pause overlay on top."""
    frozen_state_fn()
    begin_click_frame()   # the frozen screen underneath must not take clicks

    # Recalculate button positions so clicks and drawing always match
    _update_pause_rects()

    # Dark translucent overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 3, 2, 160))
    screen.blit(overlay, (0, 0))

    # Grimoire panel
    px = SCREEN_WIDTH  // 2 - _PANEL_W // 2
    py = SCREEN_HEIGHT // 2 - _PANEL_H // 2
    draw_panel(screen, pygame.Rect(px, py, _PANEL_W, _PANEL_H), border_radius=6, alpha=225)

    # Title + section rule
    draw_heading("Paused", title_font, GRIM_GOLD_BRIGHT, screen, SCREEN_WIDTH // 2, py + 34, spacing=8)
    draw_grim_divider(screen, py + 62, half_width=_PANEL_W // 2 - 24)

    # Buttons — shared runic button, hover kindles the border (crimson for Quit)
    mouse = pygame.mouse.get_pos()
    for i, (rect, label) in enumerate(zip(_pause_btn_rects, _PAUSE_BTNS)):
        target = 1.0 if rect.collidepoint(mouse) else 0.0
        _pause_hover_anim[i] += (target - _pause_hover_anim[i]) * 0.2
        draw_button(screen, rect, label, font, hot=_pause_hover_anim[i] > 0.5,
                    accent=_PAUSE_ACCENTS[i], upper=False)
        add_click(rect, None, hover=None)   # clicks handled in the event loop

    # Hint text — sits inside the panel below the last button
    hint_y = py + _BTN_OFFSETS[-1] + 52 + 14
    draw_text("[Esc] Resume", small_font, GRIM_CREAM_FAINT, screen,
              SCREEN_WIDTH // 2, hint_y, center=True)
    # how smoothly the game was running before the pause (for tuning slower devices)
    if _fps_meter["fps"]:
        draw_text(f"{_fps_meter['fps']:.0f} fps while playing", small_font, GRIM_CREAM_FAINT, screen,
                  SCREEN_WIDTH // 2, py + _PANEL_H + 18, center=True)


# Phones run the game at 30 frames a second: a steady 30 looks smoother than an uneven
# 40-60, and it halves the work, so the phone doesn't heat up and slow itself down.
TARGET_FPS = 30 if touch.ON_ANDROID else 60

# Frames per second while playing (not paused), smoothed; shown on the pause screen.
_fps_meter = {"fps": 0.0}

# On Android, a small timing line at the bottom of the screen: where each frame's time
# goes on the phone (logic, world drawing, the rest of the drawing, showing the frame),
# in milliseconds. For tuning; set SHOW_TIMINGS = False to hide it.
SHOW_TIMINGS = touch.ON_ANDROID
_timing = {"logic": 0.0, "world": 0.0, "draw": 0.0, "show": 0.0, "frame": 0.0}


def _timed(name, fn):
    def run(*a, **k):
        t = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            _timing_add(name, time.perf_counter() - t)
    return run


def _timing_add(name, seconds):
    _timing[name] += (seconds * 1000.0 - _timing[name]) * 0.1


if SHOW_TIMINGS:
    update_explore = _timed("logic", update_explore)
    draw_world = _timed("world", draw_world)
    render_explore = _timed("draw", render_explore)


def _draw_timings():
    if not SHOW_TIMINGS or game_state not in (STATE_EXPLORE, STATE_COMBAT):
        return
    t = _timing
    line = (f"{_fps_meter['fps']:.0f} fps  |  logic {t['logic']:.0f}  world {t['world']:.0f}  "
            f"ui {max(0.0, t['draw'] - t['world']):.0f}  show {t['show']:.0f}  frame {t['frame']:.0f} ms  |  "
            f"PNG {'yes' if _PNG_OK else 'no'}  icons {len(element_icons)}/{len(ELEMENT_ICONS_MAP)}"
            + (f"  [{_image_errors[0][:60]}]" if _image_errors else ""))
    img = small_font.render(line, True, (255, 240, 200))
    bg = pygame.Surface((img.get_width() + 12, img.get_height() + 4), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    x = SCREEN_WIDTH // 2 - bg.get_width() // 2
    screen.blit(bg, (x, SCREEN_HEIGHT - bg.get_height()))
    screen.blit(img, (x + 6, SCREEN_HEIGHT - bg.get_height() + 2))


def _measure_fps(frame_dt):
    if game_state in (STATE_EXPLORE, STATE_COMBAT) and 0 < frame_dt < 1.0:
        f = 1.0 / frame_dt
        m = _fps_meter
        m["fps"] = f if not m["fps"] else m["fps"] + (f - m["fps"]) * 0.05


# --- Generate Map and Place Player/Enemies ---
# (here, once everything above is defined: a Continue needs the whole game to rebuild a save)
print(f"Player Element: {player_stats['element']}")
print(f"Level: {player_stats['level']}, XP: {player_stats['xp']}/{player_stats['xp_to_next_level']}")
start_from_menu(_menu_result)        # a new run opens on the character screen; Continue resumes the save
begin_game_intro(_menu_snapshot)     # which resolves out of the menu, like an encounter

# --- Main Game Loop ---
running = True
try:
    while running:
        skill_used_last_turn = player_selected_skill # Store for effectiveness check

        _t_frame = time.perf_counter()
        _touch_layout()
        _events = touch_controls.process(pygame.event.get())
        for event in _events:   # a list, so clicks can append the KEYDOWN they stand for
            if event.type == pygame.QUIT: running = False
            # F11 / Alt+Enter switch fullscreen in every state, even mid-transition, and
            # the key does nothing else (Alt+Enter mustn't also confirm a dialogue)
            if main_menu.is_fullscreen_key(event):
                toggle_fullscreen()
                continue
            # The wipe is non-interactive — only quitting gets through
            if ascension_active():
                if ((event.type == pygame.KEYDOWN and event.key in ASCEND_SKIP_KEYS)
                        or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                    skip_ascension()
                if event.type != pygame.QUIT:
                    continue
            if transition_active() and event.type != pygame.QUIT:
                continue

            if (event.type == pygame.MOUSEWHEEL and game_state == STATE_MENU
                    and menu_tab == "Bindings"):
                scroll_bindings(-event.y * 40)

            # --- Generic clicks: replay the region's hotkey, or run its action ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _hit = click_region_at(event.pos)
                if _hit and _hit[1] is not None:
                    if callable(_hit[1]):
                        _hit[1]()
                    else:
                        _events.append(click_to_event(_hit[1]))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SLASH and game_state != STATE_ADMIN_COMMAND:
                previous_game_state = game_state
                game_state = STATE_ADMIN_COMMAND
                admin_input_text = ""
                continue
            
            if event.type == pygame.QUIT: running = False

            # --- Pause menu mouse clicks ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_state == STATE_PAUSE:
                _update_pause_rects()
                mx, my = event.pos
                if _pause_btn_rects[0].collidepoint(mx, my):   # Resume
                    game_state = previous_game_state
                elif _pause_btn_rects[1].collidepoint(mx, my): # Quit to Main Menu
                    _menu_result = _main_menu()
                    if _menu_result not in ("continue", "openworld", "limitless", "stages"):
                        running = False
                    else:
                        _apply_video_settings_for_gameplay() # pick up any video setting changes
                        start_from_menu(_menu_result)
                        _menu_snapshot = main_menu.snapshot(screen)
                        begin_game_intro(_menu_snapshot)

            # --- End screen (Game Over / Victory) mouse clicks ---
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and game_state in (STATE_GAME_OVER, STATE_VICTORY)):
                _update_end_rects()
                for _i, _r in enumerate(_end_btn_rects):
                    if _r.collidepoint(event.pos):
                        end_screen_action(_i)
                        break

            if event.type == pygame.KEYDOWN:
                if game_state == STATE_EXPLORE:
                    if event.key == pygame.K_ESCAPE:
                        previous_game_state = game_state
                        game_state = STATE_PAUSE
                    elif event.key == pygame.K_m:
                        game_state = STATE_MENU
                    elif event.key == pygame.K_TAB:
                        open_full_map()
                    elif event.key == pygame.K_p:
                        open_quest_log()
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
                        interact_facing()
                    elif event.key == pygame.K_SLASH:
                        previous_game_state = game_state
                        game_state = STATE_ADMIN_COMMAND
                        admin_input_text = ""
                elif game_state == STATE_COMBAT:
                    if event.key == pygame.K_ESCAPE:
                        previous_game_state = game_state
                        game_state = STATE_PAUSE
                    elif kill_hold_active() and event.key in KILL_HOLD_SKIP_KEYS:
                        skip_kill_hold()
                elif game_state == STATE_MAP:
                    if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                        close_full_map()
                elif game_state == STATE_DIALOGUE:
                    handle_dialogue_event(event)
                elif game_state == STATE_QUESTS:
                    handle_quest_event(event)
                elif game_state == STATE_PAUSE:
                    if event.key == pygame.K_ESCAPE:
                        game_state = previous_game_state
                elif game_state in (STATE_GAME_OVER, STATE_VICTORY):
                    # These screens previously had NO key handler at all — the old
                    # "[Esc] to quit" prompt did nothing and left the player stuck.
                    if event.key == pygame.K_r:
                        end_screen_action(END_BTN_RETRY)
                    elif event.key == pygame.K_m:
                        end_screen_action(END_BTN_MENU)
                    elif event.key == pygame.K_ESCAPE:
                        end_screen_action(END_BTN_QUIT)
                elif game_state == STATE_MENU:
                    handle_menu_event(event)
                elif game_state == STATE_CREATE:
                    handle_create_event(event)
                
                # Global slash command access if not in admin state
                if game_state != STATE_ADMIN_COMMAND and event.key == pygame.K_SLASH:
                    previous_game_state = game_state
                    game_state = STATE_ADMIN_COMMAND
                    admin_input_text = ""
                
                elif game_state == STATE_ADMIN_COMMAND:
                    if event.key == pygame.K_ESCAPE:
                        game_state = previous_game_state
                    elif event.key == pygame.K_TAB:
                        suggestions = get_admin_suggestions(admin_last_input_prefix)
                        if suggestions:
                            admin_input_text = suggestions[admin_suggestion_index % len(suggestions)]
                            admin_suggestion_index += 1
                    elif event.key == pygame.K_RETURN:
                        admin_feedback = execute_admin_command(admin_input_text)
                        print(f"Admin: {admin_feedback}")
                        admin_input_text = ""
                        admin_last_input_prefix = ""
                        admin_suggestion_index = 0
                    elif event.key == pygame.K_BACKSPACE:
                        admin_input_text = admin_input_text[:-1]
                        admin_last_input_prefix = admin_input_text
                        admin_suggestion_index = 0
                    else:
                        admin_input_text += event.unicode
                        admin_last_input_prefix = admin_input_text
                        admin_suggestion_index = 0
                
                if level_up_message and event.key: level_up_message = ""

                if game_state == STATE_REROLL_PROMPT:
                    if spin_active():
                        if event.key in SPIN_SKIP_KEYS:
                            skip_spin()           # everything else is ignored mid-spin
                    elif event.key == pygame.K_y:
                        old_element = player_stats["element"]
                        is_t5_or_higher = old_element in tier5_elements or old_element in tier6_elements or old_element in tier7_elements
                        reroll_cost, _rb_block, _rb_note = rebind_terms(old_element)

                        if not _rb_block and player_stats["reroll_spins"] >= reroll_cost:
                            player_stats["reroll_spins"] -= reroll_cost
                            if has_vow(V_ROOTLESS) and player_stats.get("rootless_stage") != current_stage:
                                player_stats["rootless_stage"] = current_stage   # the free one is spent
                            _gamble["cost"] = None
                            
                            # Roll the result up front, then let the wheel present it.
                            # start_spin commits it to player_stats only when it lands.
                            if is_t5_or_higher:
                                landed = get_random_weighted_element(player_stats["level"], force_tier5=True)
                                pool = list(tier5_elements)
                            else:
                                landed = get_random_weighted_element(player_stats["level"], force_tier1=True)
                                pool = list(tier1_elements)
                            if has_vow(V_RISING_TIER) and random.random() < RISING_TIER_CHANCE:
                                pool = list(tier6_elements if is_t5_or_higher else tier2_elements)
                                landed = random.choice(pool)       # the dice climb a tier
                            vfx_clear()
                            start_spin(landed, pool)
                            print(f"Rerolling! {old_element} -> {landed}. Spins left: {player_stats['reroll_spins']}")
                        else: 
                            pass # Not enough spins, do nothing
                    elif event.key == pygame.K_n:
                        print("Continuing game..."); level_up_message = ""; combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
                        if all(not enemy.alive for enemy in all_stage_enemies()):
                            game_state = STATE_STAGE_CLEAR # Go to stage clear screen
                        else:
                            game_state = STATE_EXPLORE

                elif game_state == STATE_EVOLVE:
                    current_elem = player_stats["element"]
                    available_evolutions = EVOLUTION_MAP.get(current_elem, [])

                    if not available_evolutions:
                        # Max evolution logic
                        if event.key == pygame.K_y and not has_vow(V_HUMBLE_ROOT):
                            old_element = player_stats["element"]
                            new_element = random.choice(tier5_elements)
                            player_stats["element"] = new_element
                            record_element_change(new_element, evolved=True)
                            print(f"Ascended! {old_element} -> {player_stats['element']}")
                            player_stats["pending_evolution"] = False
                            game_state = STATE_REROLL_PROMPT
                        elif event.key == pygame.K_n:
                            print(f"Declined ascension. Remaining as {current_elem}.")
                            player_stats["pending_evolution"] = True
                            game_state = STATE_REROLL_PROMPT
                    else:
                        # Standard evolution logic, plus the True-form option ([T]) when the
                        # player holds the Sigil at the required level.
                        true_base, sigil_idx = true_master_available()
                        if true_base and event.key == pygame.K_t:
                            if sigil_idx >= 0:
                                player_stats["inventory"].pop(sigil_idx)   # consume the Sigil
                            grant_true_form(true_base)
                            player_stats["pending_evolution"] = False
                            game_state = STATE_REROLL_PROMPT
                        elif pygame.K_1 <= event.key <= pygame.K_9 and not has_vow(V_HUMBLE_ROOT):
                            idx = event.key - pygame.K_1
                            if idx < len(available_evolutions):
                                old_element = player_stats["element"]
                                player_stats["element"] = available_evolutions[idx]
                                record_element_change(available_evolutions[idx], evolved=True)
                                print(f"Evolved! {old_element} -> {player_stats['element']}")
                                player_stats["pending_evolution"] = False
                                game_state = STATE_REROLL_PROMPT
                        elif event.key == pygame.K_0:
                            print(f"Declined evolution. Remaining as {current_elem}.")
                            player_stats["pending_evolution"] = True
                            game_state = STATE_REROLL_PROMPT

                elif game_state == STATE_STAGE_CLEAR:
                    current_stage += 1
                    if current_stage > NUM_STAGES:
                        game_state = STATE_VICTORY
                    else:
                        setup_stage(current_stage)
                        player_stats["hp"] = player_stats["max_hp"] # Heal player
                        game_state = STATE_EXPLORE
                        level_up_message = ""

                # --- Modified Combat Input Handling ---
                elif game_state == STATE_COMBAT and combat_turn == 'player' and not is_in_combat_delay: # <<< Check for delay here too
                    if combat_sub_state == COMBAT_SUBSTATE_CHOOSE_ACTION:
                        _kinds = {pygame.K_w: "skills", pygame.K_a: "melee", pygame.K_d: "defend",
                                  pygame.K_c: "charge", pygame.K_f: "flee", pygame.K_v: "awaken",
                                  pygame.K_i: "items"}
                        if event.key in _kinds:
                            _kind = _kinds[event.key]
                            _block = combat_action_block(_kind)   # vows, cooldowns, level
                            if _block:
                                combat_message = _block; player_combat_action = None
                            elif _kind == "skills":
                                combat_sub_state = COMBAT_SUBSTATE_CHOOSE_SKILL; player_combat_action = None; player_selected_skill = None
                            elif _kind == "items":
                                combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ITEM; player_combat_action = None; player_selected_skill = None
                            else:
                                player_combat_action = {"melee": COMBAT_ACTION_ATTACK, "defend": COMBAT_ACTION_DEFEND,
                                                        "charge": COMBAT_ACTION_CHARGE, "flee": COMBAT_ACTION_FLEE,
                                                        "awaken": COMBAT_ACTION_AWAKEN}[_kind]
                                player_selected_skill = None
                    elif combat_sub_state == COMBAT_SUBSTATE_CHOOSE_ITEM:
                        if event.key in (pygame.K_b, pygame.K_i):
                            combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
                        elif pygame.K_1 <= event.key <= pygame.K_8:
                            _bag = combat_items()
                            _bi = event.key - pygame.K_1
                            if _bi < len(_bag):
                                _why = combat_item_problem(_bag[_bi][0])
                                if _why:
                                    combat_message = _why
                                else:
                                    _combat_item["pick"] = _bag[_bi][0]
                                    player_combat_action = COMBAT_ACTION_ITEM; player_selected_skill = None
                                    combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
                    elif combat_sub_state == COMBAT_SUBSTATE_CHOOSE_SKILL:
                        if event.key == pygame.K_b: combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION; player_combat_action = None; player_selected_skill = None
                        elif pygame.K_1 <= event.key <= pygame.K_9:
                             skill_index = event.key - pygame.K_1; player_element = player_stats['element']; available_skills = ELEMENT_SKILLS.get(player_element, DEFAULT_SKILLS)
                             if 0 <= skill_index < len(available_skills):
                                 chosen_skill = available_skills[skill_index]
                                 cd_remaining = 0 if player_stats.get("cooldowns_disabled") else player_stats["skill_cooldowns"].get(chosen_skill['name'], 0)
                                 if cd_remaining > 0:
                                     combat_message = f"{chosen_skill['name']} is on cooldown for {cd_remaining} more turn(s)!"
                                 else:
                                     mana_cost = get_skill_mana_cost(player_element, chosen_skill['name'])
                                     if skill_affordable(mana_cost):
                                         player_selected_skill = chosen_skill; player_combat_action = COMBAT_ACTION_ATTACK; combat_sub_state = COMBAT_SUBSTATE_CHOOSE_ACTION
                                     elif has_vow(V_BLOOD_TITHE):
                                         combat_message = f"Too weak to pay the tithe! Needs more than {mana_cost} HP."
                                     else:
                                         combat_message = f"Not enough mana! Need {mana_cost} MP, have {player_stats['mana']} MP."
                             else: print(f"Invalid skill number: {skill_index + 1}")
            # --- End Modified Combat Input ---

        # Game State Logic & Rendering (Outside Event Loop)
        begin_click_frame()          # renderers re-register what's clickable this frame
        _overlay_busy = ascension_active() or transition_active()

        if ascension_active():
            update_ascension(dt); update_vfx(dt); draw_ascension()

        elif transition_active():
            update_transition(min(dt, 1 / 30)); draw_transition(render_current_state)

        elif game_state == STATE_EXPLORE: update_explore(); render_explore()

        elif game_state == STATE_MAP: render_explore(); draw_full_map()

        elif game_state == STATE_DIALOGUE: update_dialogue(); render_explore(); draw_dialogue()

        elif game_state == STATE_QUESTS: render_explore(); draw_quest_log()

        elif game_state == STATE_COMBAT: update_combat(); update_vfx(dt); tick_kill_hold(dt); render_combat()

        elif game_state == STATE_REROLL_PROMPT: update_spin(dt); update_vfx(dt); render_reroll_prompt()

        elif game_state == STATE_EVOLVE: render_evolve()

        elif game_state == STATE_STAGE_CLEAR: render_stage_clear()

        elif game_state == STATE_MENU: render_menu()

        elif game_state == STATE_CREATE: render_create()

        elif game_state == STATE_GAME_OVER: render_game_over()

        elif game_state == STATE_VICTORY: render_victory()

        elif game_state == STATE_PAUSE:
            # Render the frozen background state, then overlay the pause panel
            frozen_fn = {
                STATE_EXPLORE: render_explore,
                STATE_COMBAT:  render_combat,
                STATE_MENU:    render_menu,
            }.get(previous_game_state, render_explore)
            render_pause_menu(frozen_fn)

        elif game_state == STATE_ADMIN_COMMAND:
            # Render previous state first, then overlay
            if previous_game_state == STATE_EXPLORE: render_explore()
            elif previous_game_state == STATE_COMBAT: render_combat()
            elif previous_game_state == STATE_MENU: render_menu()
            elif previous_game_state == STATE_EVOLVE: render_evolve()
            elif previous_game_state == STATE_REROLL_PROMPT: render_reroll_prompt()
            elif previous_game_state == STATE_STAGE_CLEAR: render_stage_clear()
            elif previous_game_state == STATE_GAME_OVER: render_game_over()
            elif previous_game_state == STATE_VICTORY: render_victory()
            elif previous_game_state == STATE_CREATE: render_create()
            elif previous_game_state == STATE_PAUSE: render_pause_menu(render_explore)
            begin_click_frame()      # the console is keyboard-only; nothing behind it is live
            render_admin_console()

        if _overlay_busy:
            begin_click_frame()      # cinematics swallow input, so nothing is hoverable
        draw_click_hover(screen)
        touch_controls.draw(screen)
        _draw_timings()

        # Reset player selected skill tracker *after* processing logic and rendering
        # Store the skill used just before the event loop clears things for the next frame.
        # Effectiveness msg rendering now uses this stored value from the previous frame.
        player_selected_skill = skill_used_last_turn # Restore skill used for potential effectiveness display

        _t_show = time.perf_counter()
        main_menu.present()
        if SHOW_TIMINGS:
            _timing_add("show", time.perf_counter() - _t_show)
            _timing_add("frame", time.perf_counter() - _t_frame)
        dt = clock.tick(TARGET_FPS) / 1000.0
        _measure_fps(dt)
except Exception as e:
    print(f"CRASH DETECTED: {e}")
    import traceback
    traceback.print_exc()
    if sys.stdin is not None and sys.stdin.isatty():
        input("Press Enter to exit...")        # keep a console window open to read it
    else:
        raise                                  # no console (e.g. Android): main.py reports it

pygame.quit()
sys.exit()

    