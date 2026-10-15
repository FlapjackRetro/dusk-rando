from __future__ import annotations

from typing import Dict, List, NamedTuple

from BaseClasses import Item, ItemClassification as IC

from .data import ITEM_BASE_ID, LEVELS


class ItemInfo(NamedTuple):
    name: str
    classification: IC
    group: str


GAME = "DUSK"


class DuskItem(Item):
    game = GAME


# Weapons as they are granted in game. Progressive items stack: the 2nd Progressive Pistol gives dual pistols.
WEAPON_ITEMS = {
    "Progressive Pistol": 2,
    "Progressive Shotgun": 2,
    "Super Shotgun": 1,
    "Assault Rifle": 1,
    "Hunting Rifle": 1,
    "Crossbow": 1,
    "Mortar": 1,
    "Riveter": 1,
    "Sword": 1,
}
# Vanilla weapon pickup label -> item that represents it
VANILLA_WEAPON_TO_ITEM = {
    "Pistol": "Progressive Pistol", "Shotgun": "Progressive Shotgun", "Super Shotgun": "Super Shotgun",
    "Assault Rifle": "Assault Rifle", "Hunting Rifle": "Hunting Rifle", "Crossbow": "Crossbow",
    "Mortar": "Mortar", "Riveter": "Riveter", "Sword": "Sword",
}
FIREARMS = [w for w in WEAPON_ITEMS if w != "Sword"]

POWERUP_ITEMS = ["Hallowed Health", "Fast Fire Totem", "Serum of Blistering Heat", "Flashlight", "Backpack"]
HEALTH_ITEMS = ["Medical Kit", "Small Medical Kit", "Magic Potion"]
ARMOR_ITEMS = ["Gold Coin", "Bag of Gems", "Diamond"]
AMMO_ITEMS = ["Pistol Bullet", "Pistol Clip", "Box of Pistol Bullets", "Shotgun Shell", "Box of Shotgun Shells",
              "Assault Rifle Magazine", "Hunting Rifle Bullet", "Box of Hunting Rifle Bullets", "Crossbow Bolts",
              "Mortar Grenade", "Box of Mortar Grenades", "Rivets"]

# Weighted list used when the pool needs generic filler.
FILLER_WEIGHTS = {
    "Medical Kit": 6, "Bag of Gems": 4, "Box of Shotgun Shells": 4, "Pistol Clip": 3,
    "Assault Rifle Magazine": 3, "Crossbow Bolts": 2, "Box of Hunting Rifle Bullets": 2,
    "Box of Mortar Grenades": 2, "Rivets": 2, "Diamond": 1,
}


def _build_table() -> List[ItemInfo]:
    table: List[ItemInfo] = []
    # Order matters: IDs are assigned by position. Only ever append to this list.
    for lvl in LEVELS:
        table.append(ItemInfo(f"{lvl.code} Access", IC.progression, "Level Access"))
    for lvl in LEVELS:
        for color in ("Red Key", "Blue Key", "Yellow Key"):
            table.append(ItemInfo(f"{lvl.code} {color}", IC.progression, "Keys"))
    for w in WEAPON_ITEMS:
        table.append(ItemInfo(w, IC.progression | IC.useful, "Weapons"))
    for p in POWERUP_ITEMS:
        table.append(ItemInfo(p, IC.useful if p in ("Backpack", "Flashlight", "Hallowed Health") else IC.filler,
                              "Powerups"))
    for h in HEALTH_ITEMS:
        table.append(ItemInfo(h, IC.filler, "Health"))
    for a in ARMOR_ITEMS:
        table.append(ItemInfo(a, IC.filler, "Morale"))
    for a in AMMO_ITEMS:
        table.append(ItemInfo(a, IC.filler, "Ammo"))
    return table


ITEM_TABLE = _build_table()
ITEM_INFO: Dict[str, ItemInfo] = {i.name: i for i in ITEM_TABLE}
ITEM_NAME_TO_ID: Dict[str, int] = {i.name: ITEM_BASE_ID + n for n, i in enumerate(ITEM_TABLE)}

ITEM_GROUPS: Dict[str, set] = {}
for _i in ITEM_TABLE:
    ITEM_GROUPS.setdefault(_i.group, set()).add(_i.name)
for _lvl in LEVELS:
    ITEM_GROUPS[f"{_lvl.code} Keys"] = {f"{_lvl.code} {c}" for c in ("Red Key", "Blue Key", "Yellow Key")}
