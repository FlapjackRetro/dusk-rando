"""Per-location key requirements, filled in level by level from playtesting.

KEY_RULES[level code][location name] = the keys (colours) that location needs. KEY_RULES[level code]["*"], if given,
is the rule for every location of that level not listed by name. Otherwise an unlisted location in a level that has
keys falls back to strict key logic: it needs all of that level's keys. Level Complete and the level's Cleared event
follow the same rules (list "<code> - Level Complete" to override them).

JUNK_KEYS: keys that no check needs. They are still in the game (they may open doors), but they are classified as
filler instead of progression.

Only applies when keys are randomized; otherwise keys stay in their vanilla spots and there is no key logic.
"""
from typing import Dict, List, Set

NONE: List[str] = []
DEFAULT = "*"

KEY_RULES: Dict[str, Dict[str, List[str]]] = {
    "E2M1": {
        DEFAULT: NONE,
        "E2M1 - Level Complete": ["Red Key"],
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

JUNK_KEYS: Set[str] = {
    # E2M1: only Level Complete needs a key (Red). Matters once E2M1 can start locked (E1M1-only starts).
    "E2M1 Blue Key", "E2M1 Yellow Key",
}
