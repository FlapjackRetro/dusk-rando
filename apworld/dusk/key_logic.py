"""Per-location key requirements, filled in level by level from playtesting.

KEY_RULES[level code][location name] = the keys (colours) that location needs. KEY_RULES[level code]["*"], if given,
is the rule for every location of that level not listed by name. Otherwise an unlisted location in a level that has
keys falls back to strict key logic: it needs all of that level's keys. Level Complete and the level's Cleared event
follow the same rules (list "<code> - Level Complete" to override them).

ITEM_RULES[location name] = other items that location needs, on top of its key rule (e.g. a weapon that breaks a
wall). Each entry is an item name (needed) or a tuple of item names (any one of them is enough). Only applied when
weapons are randomized; otherwise the weapons are in their vanilla spots.

JUNK_KEYS: keys that no check needs. They are still in the game (they may open doors), but they are classified as
filler instead of progression.

Only applies when keys are randomized; otherwise keys stay in their vanilla spots and there is no key logic.
"""
from typing import Dict, List, Set, Tuple, Union

NONE: List[str] = []
DEFAULT = "*"

KEY_RULES: Dict[str, Dict[str, List[str]]] = {
    "E2M1": {
        DEFAULT: NONE,
        "E2M1 - Level Complete": ["Red Key"],
    },
    "E2M3": {
        "E2M3 - Pistol 1": NONE,
        "E2M3 - Pistol 2": NONE,
        "E2M3 - Shotgun 2": NONE,
        "E2M3 - Assault Rifle 1": NONE,
        "E2M3 - Hunting Rifle": NONE,
        "E2M3 - Mortar": NONE,
        "E2M3 - Yellow Key": NONE,
        "E2M3 - Secret Area 1": NONE,
        "E2M3 - Secret Area 3": NONE,
    },
    "E2M4": {
        "E2M4 - Shotgun 1": NONE,
        "E2M4 - Red Key": NONE,
    },
    "E2M6": {
        "E2M6 - Pistol 1": NONE,
        "E2M6 - Pistol 3": NONE,
        "E2M6 - Shotgun 2": NONE,
        "E2M6 - Hallowed Health 2": NONE,
        "E2M6 - Secret Area 3": NONE,
        "E2M6 - Secret Area 6": NONE,
    },
    "E2M7": {
        "E2M7 - Pistol 1": NONE,
        "E2M7 - Pistol 2": NONE,
        "E2M7 - Shotgun 1": NONE,
        "E2M7 - Shotgun 2": NONE,
        "E2M7 - Hunting Rifle": NONE,
        "E2M7 - Mortar": NONE,
        "E2M7 - Blue Key": NONE,
    },
    "E3M1": {
        "E3M1 - Sword": NONE,
        "E3M1 - Crossbow 2": NONE,
        "E3M1 - Mortar 2": NONE,
        "E3M1 - Red Key": NONE,
        "E3M1 - Secret Area 3": NONE,
        "E3M1 - Secret Area 5": NONE,
        "E3M1 - Secret Area 6": NONE,
        "E3M1 - Super Shotgun": ["Blue Key", "Red Key"],  # plus the Mortar or the Riveter (ITEM_RULES)
    },
    "E3M2": {
        "E3M2 - Sword": NONE,
        "E3M2 - Pistol 1": NONE,
        "E3M2 - Pistol 2": NONE,
        "E3M2 - Shotgun 1": NONE,
        "E3M2 - Shotgun 2": NONE,
        "E3M2 - Blue Key": NONE,
        "E3M2 - Fast Fire Totem": NONE,
        "E3M2 - Secret Area 4": NONE,
        "E3M2 - Secret Area 7": NONE,
        "E3M2 - Secret Area 8": NONE,
    },
    "E1M5": {
        "E1M5 - Pistol 1": NONE,
        "E1M5 - Pistol 2": NONE,
        "E1M5 - Shotgun 2": NONE,
        "E1M5 - Super Shotgun 1": NONE,
        "E1M5 - Super Shotgun 2": NONE,
        "E1M5 - Assault Rifle": NONE,
        "E1M5 - Hunting Rifle": NONE,
        "E1M5 - Red Key": NONE,
        "E1M5 - Fast Fire Totem 2": NONE,
        "E1M5 - Hallowed Health 1": NONE,
    },
    "E1M6": {
        "E1M6 - Pistol 1": NONE,
        "E1M6 - Pistol 2": NONE,
        "E1M6 - Super Shotgun": NONE,
        "E1M6 - Assault Rifle": NONE,
        "E1M6 - Secret Area 2": NONE,
        "E1M6 - Yellow Key": NONE,
    },
    "E1M8": {
        "E1M8 - Super Shotgun": NONE,
        "E1M8 - Pistol 1": NONE,
        "E1M8 - Pistol 2": NONE,
        "E1M8 - Red Key": NONE,
        "E1M8 - Secret Area 2": NONE,
        "E1M8 - Secret Area 4": NONE,
        "E1M8 - Secret Area 6": NONE,
        "E1M8 - Assault Rifle 1": NONE,
        "E1M8 - Blue Key": NONE,
    },
}

ITEM_RULES: Dict[str, List[Union[str, Tuple[str, ...]]]] = {
    "E3M1 - Super Shotgun": [("Mortar", "Riveter")],
}

JUNK_KEYS: Set[str] = {
    # E2M1: only Level Complete needs a key (Red). Matters once E2M1 can start locked (E1M1-only starts).
    "E2M1 Blue Key", "E2M1 Yellow Key",
}
