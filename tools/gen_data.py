"""Build the randomizer's location table from data/raw_pickups.json.

    python tools/gen_data.py

Writes:
  apworld/dusk/data/locations.json   (consumed by the APWorld and the mod)
  docs/LOCATIONS.csv                  (spreadsheet-friendly copy)

Location IDs are preserved across runs: an existing locations.json is read first and
any location whose key (scene + object name + position) is unchanged keeps its ID.
"""
import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw_pickups.json")
OUT = os.path.join(ROOT, "apworld", "dusk", "data", "locations.json")
CSV = os.path.join(ROOT, "docs", "LOCATIONS.csv")

LOCATION_BASE_ID = 0xD05C_0000 + 100_000

# Unity scene name -> (level code shown in game, level name)
LEVELS = {
    "E1M1": ("E1M1", "Head Cheese"), "E1M2": ("E1M2", "Down on the Farm"),
    "E1M3": ("E1M3", "Old Time Religion"), "E1M4": ("E1M4", "Steamworks"),
    "E1M5": ("E1M5", "Sawdust"), "E1M5AndAHalf": ("E1M6", "The Cutty Mine"),
    "E1M6-2": ("E1M7", "Dead of the Night"), "E1M7": ("E1M8", "Through the Gate"),
    "E1M8": ("E1M9", "Ghost Town"), "E1M9": ("E1M10", "Creations"),
    "E1MS": ("E1MS", "The Dim Slough"),
    "E2M1": ("E2M1", "The Grainery"), "E2M2": ("E2M2", "Unseen"),
    "E2M3": ("E2M3", "Into the Thresher"), "E2M4": ("E2M4", "The Infernal Machine"),
    "E2M5": ("E2M5", "The Escher Labs"), "E2M6": ("E2M6", "The Erebus Reactor"),
    "E2M7": ("E2M7", "Neobabel"), "E2M8": ("E2M8", "Blood and Bone"),
    "E2M9": ("E2M9", "The Dig"), "E2M10": ("E2M10", "The Gauntlet"),
    "E2MS": ("E2MS", "The Foundry"),
    "E3M1": ("E3M1", "The Iron Cathedral"), "e3m2": ("E3M2", "Fire and Ice"),
    "E3M3": ("E3M3", "City of Shadows"), "E3M4": ("E3M4", "Crypt of the Flesh"),
    "E3M5": ("E3M5", "Blasphemy"), "E3M6": ("E3M6", "Brimstone Ghetto"),
    "E3M7": ("E3M7", "Homecoming"), "E3M8": ("E3M8", "As Above, So Below"),
    "E3M9": ("E3M9", "The Dweller in Darkness"), "E3M10": ("E3M10", "Dusk"),
    "E3MS": ("E3MS", "The Ratacombs"),
}

WEAPONS = {1: "Pistol", 2: "Shotgun", 3: "Super Shotgun", 4: "Assault Rifle",
           5: "Hunting Rifle", 6: "Crossbow", 7: "Mortar", 8: "Riveter"}
AMMO = {
    "PICKUP_BULLETS_1": "Pistol Bullet", "PICKUP_BULLETS_12": "Pistol Clip",
    "PICKUP_BULLETS_36": "Box of Pistol Bullets", "PICKUP_SHELLS_1": "Shotgun Shell",
    "PICKUP_SHELLS_12": "Box of Shotgun Shells", "PICKUP_ASSAULT_BULLETS_24": "Assault Rifle Magazine",
    "PICKUP_RIFLE_BULLETS_1": "Hunting Rifle Bullet", "PICKUP_RIFLE_BULLETS_5": "Box of Hunting Rifle Bullets",
    "PICKUP_CROSSBOW_10": "Crossbow Bolts", "PICKUP_GRENADE_1": "Mortar Grenade",
    "PICKUP_GRENADES_6": "Box of Mortar Grenades", "PICKUP_RIVET": "Rivets",
}
HEALTH = {"PICKUP_HEALTH_PACK": ("Medical Kit", "health"), "PICKUP_HEALTH_SMALL": ("Small Medical Kit", "health"),
          "PICKUP_HEALTH_BONUS": ("Magic Potion", "health"), "PICKUP_ARMOR_BONUS": ("Gold Coin", "armor"),
          "PICKUP_ARMOR_10": ("Bag of Gems", "armor"), "PICKUP_DIAMOND": ("Diamond", "armor")}
POWERUPS = {"HolyHealthTag": "Hallowed Health", "HolyHealthNoSoundTag": "Hallowed Health",
            "Weapon Speed Pickup": "Fast Fire Totem", "Superhot Powerup": "Serum of Blistering Heat",
            "LavaSuitPickup": "Thermal Suit", "FlashlightPickupTag": "Flashlight",
            "BackpackTag": "Backpack", "WeaponEnhanceTag": "Weapon Enhancer"}
KEYS = {"RedKeyTag": "Red Key", "BlueKeyTag": "Blue Key", "YellowKeyTag": "Yellow Key"}
# Treasure chest contents (prefab names in sharedassets) -> item label
CHEST_PREFABS = {"tenarmor": "Bag of Gems", "riveterammo": "Rivets", "minihealthpack": "Small Medical Kit",
                 "healthpack": "Medical Kit", "shotgunshells": "Box of Shotgun Shells",
                 "singleshotgunshellpickup": "Shotgun Shell", "RifleBoxPickup": "Box of Hunting Rifle Bullets",
                 "CrossbowAmmoPickup": "Crossbow Bolts", "m16clip": "Assault Rifle Magazine",
                 "grenadebox": "Box of Mortar Grenades"}
CHEST_PATHIDS = {("sharedassets2.assets", 911): "tenarmor", ("sharedassets2.assets", 1032): "riveterammo",
                 ("sharedassets2.assets", 856): "minihealthpack", ("sharedassets2.assets", 834): "healthpack",
                 ("sharedassets2.assets", 1046): "shotgunshells", ("sharedassets2.assets", 1026): "singleshotgunshellpickup",
                 ("sharedassets2.assets", 1029): "RifleBoxPickup", ("sharedassets2.assets", 962): "CrossbowAmmoPickup",
                 ("sharedassets2.assets", 961): "m16clip", ("sharedassets36.assets", 16): "grenadebox"}


def classify(rec):
    """-> (category, vanilla item label) or None to skip."""
    tag = rec["tag"]
    if tag in ("Weapon Pickup", "SuperShotgunTag"):
        w = rec["WeaponPickupScript"]
        if w["giveweapon"]:
            return "weapons", WEAPONS[w["weaponcontent"]]
        return "ammo", AMMO[w["message"]]
    if tag == "SwordTag":
        return "weapons", "Sword"
    if tag == "Health Pickup":
        return HEALTH[rec["HealthPickupScript"]["message"]][::-1]
    if tag in POWERUPS:
        return "powerups", POWERUPS[tag]
    if tag in KEYS:
        return "keys", KEYS[tag]
    if tag == "SecretTag":
        return "secrets", None
    if tag == "TreasureChestTag":
        it = rec["TreasureChestScript"]["myitem"]
        prefab = CHEST_PATHIDS[(it["external"], it["pathID"])]
        return "treasure_chests", CHEST_PREFABS[prefab]
    return None  # ItemSpawner (respawning climbing powerups), EndButtonTag handled separately


def main():
    raw = json.load(open(RAW))
    old = {}
    if os.path.exists(OUT):
        for l in json.load(open(OUT))["locations"]:
            old[l["key"]] = l["id"]
    next_id = max(list(old.values()) + [LOCATION_BASE_ID - 1]) + 1

    per_level = defaultdict(list)
    exits = defaultdict(list)
    for rec in raw:
        if rec["scene"] not in LEVELS:
            continue  # endless arenas, menus
        if rec["tag"] == "EndButtonTag":
            exits[rec["scene"]].append(rec["path"])
            continue
        c = classify(rec)
        if c:
            per_level[rec["scene"]].append((c, rec))

    locations = []
    for scene, (code, lname) in LEVELS.items():
        entries = per_level[scene]
        # deterministic ordering: category, label, object name, position
        entries.sort(key=lambda e: (e[0][0], e[0][1] or "", e[1]["name"], e[1]["pos"]))
        counts = Counter((cat, label) for (cat, label), _ in entries)
        seen = Counter()
        for (cat, label), rec in entries:
            nice = label or "Secret Area"
            if cat == "treasure_chests":
                nice = "Treasure Chest"
            key_pair = (cat, label)
            seen[key_pair] += 1
            total = counts[key_pair]
            if cat == "treasure_chests":
                total = sum(1 for (c2, _), _r in entries if c2 == "treasure_chests")
                seen_chest = sum(1 for l in locations if l["scene"] == scene and l["category"] == "treasure_chests") + 1
                name = f"{code} - Treasure Chest" + (f" {seen_chest}" if total > 1 else "")
            else:
                name = f"{code} - {nice}" + (f" {seen[key_pair]}" if total > 1 else "")
            pos = [round(v, 2) for v in rec["pos"]]
            key = f"{scene}|{rec['name']}|{pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}"
            if key in old:
                lid = old[key]
            else:
                lid = next_id
                next_id += 1
            locations.append({
                "id": lid, "name": name, "level": code, "level_name": lname, "scene": scene,
                "category": cat, "vanilla_item": label, "tag": rec["tag"], "object": rec["name"],
                "path": rec["path"], "pos": pos, "key": key,
            })
        # one "complete the level" check per level, sent when the level is finished
        key = f"{scene}|__exit__"
        lid = old.get(key)
        if lid is None:
            lid = next_id
            next_id += 1
        locations.append({
            "id": lid, "name": f"{code} - Level Complete", "level": code, "level_name": lname,
            "scene": scene, "category": "level_complete", "vanilla_item": None, "tag": None,
            "object": None, "path": None, "pos": None, "key": key,
        })

    ids = [l["id"] for l in locations]
    names = [l["name"] for l in locations]
    assert len(set(ids)) == len(ids), "duplicate ids"
    keys = [l["key"] for l in locations]
    assert len(set(keys)) == len(keys), [k for k, c in Counter(keys).items() if c > 1][:10]
    assert len(set(names)) == len(names), [n for n, c in Counter(names).items() if c > 1][:10]

    levels = [{"scene": s, "code": c, "name": n, "episode": int(c[1]), "secret": c.endswith("S"),
               "keys": sorted({l["vanilla_item"] for l in locations if l["scene"] == s and l["category"] == "keys"}),
               "exit_objects": exits.get(s, [])}
              for s, (c, n) in LEVELS.items()]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"levels": levels, "locations": locations}, fh, indent=1)
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with open(CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "level", "level_name", "scene", "category", "vanilla_item", "object", "x", "y", "z"])
        for l in locations:
            p = l["pos"] or ["", "", ""]
            w.writerow([l["id"], l["name"], l["level"], l["level_name"], l["scene"], l["category"],
                        l["vanilla_item"] or "", l["object"] or "", *p])
    print(len(locations), "locations;", Counter(l["category"] for l in locations))


if __name__ == "__main__":
    main()


DOC = os.path.join(ROOT, "docs", "ITEMS.md")
CAT_TITLES = [("weapons", "Weapons"), ("keys", "Keys"), ("powerups", "Powerups"), ("secrets", "Secrets"),
              ("treasure_chests", "Chests"), ("health", "Health"), ("armor", "Morale"), ("ammo", "Ammo"),
              ("level_complete", "Exit")]


def write_docs():
    d = json.load(open(OUT))
    locs = d["locations"]
    out = ["# DUSK item & location reference", "",
           "Generated by `tools/gen_data.py` from the game's level files (`data/raw_pickups.json`). "
           "Every pickup below is placed in a campaign level; endless-mode arenas are excluded.", "",
           "## Categories", "",
           "Each category is a separate YAML toggle so the number of checks can grow or shrink.", "",
           "| Category | Option | Default | Checks | What's in it |", "|---|---|---|---:|---|"]
    info = {
        "weapons": ("randomize_weapons", "on", "Pistol, Shotgun, Super Shotgun, Assault Rifle, Hunting Rifle, Crossbow, Mortar, Riveter, Sword pickups"),
        "keys": ("randomize_keys", "on", "Red / Blue / Yellow keys (per level)"),
        "powerups": ("randomize_powerups", "on", "Hallowed Health, Fast Fire Totem, Serum of Blistering Heat, Flashlight, Backpack"),
        "secrets": ("randomize_secrets", "on", "Secret area triggers"),
        "treasure_chests": ("randomize_treasure_chests", "on", "Treasure chests (fixed contents)"),
        "health": ("randomize_health", "off", "Medical Kit (+15), Small Medical Kit (+7), Magic Potion (+1, overcharge)"),
        "armor": ("randomize_armor", "off", "Gold Coin (+1), Bag of Gems (+10), Diamond (+50) morale"),
        "ammo": ("randomize_ammo", "off", "All ammo pickups"),
        "level_complete": ("(always)", "on", "Finishing the level"),
    }
    # Thermal Suits are in the table (category powerups) but the APWorld never makes them checks.
    cat_counts = Counter(l["category"] for l in locs if l["vanilla_item"] != "Thermal Suit")
    for cat, _ in CAT_TITLES:
        opt, default, desc = info[cat]
        out.append(f"| {cat} | `{opt}` | {default} | {cat_counts[cat]} | {desc} |")
    out += ["", f"Total: **{sum(cat_counts.values())}** possible checks.", "",
            "### Never randomized", "",
            "- **Thermal Suits** (5): timed lava immunity the level layouts depend on.",
            "- **Climbing powerups**: spawned every 30 s by `ItemSpawnerScript` (17 spawners in E2/E3).",
            "- **Breakable / enemy drops**: `DestructibleObjectScript.itemstospawn` picks randomly.",
            "- Endless-mode arenas.", "",
            "### Oddities worth knowing", "",
            "- E2M1 has a pile of 16 extra blue keys next to its real Blue Card; they are separate key locations but the "
            "level still only has one `E2M1 Blue Key` item.",
            "- E1M3 and E3MS each have two Blue Key pickups.", "",
            "## Vanilla item counts", ""]
    by_item = Counter((l["category"], l["vanilla_item"]) for l in locs if l["vanilla_item"])
    out += ["| Category | Item | Count |", "|---|---|---:|"]
    for (cat, item), n in sorted(by_item.items()):
        out.append(f"| {cat} | {item} | {n} |")
    out += ["", "## Checks per level", "",
            "| Level | Name | Scene | Keys | " + " | ".join(t for _, t in CAT_TITLES) + " | Total |",
            "|---|---|---|---|" + "---:|" * (len(CAT_TITLES) + 1)]
    for lvl in d["levels"]:
        c = Counter(l["category"] for l in locs if l["scene"] == lvl["scene"])
        keys = ", ".join(k.split()[0] for k in lvl["keys"]) or "-"
        out.append(f"| {lvl['code']} | {lvl['name']} | `{lvl['scene']}` | {keys} | "
                   + " | ".join(str(c[cat]) for cat, _ in CAT_TITLES) + f" | {sum(c.values())} |")
    out += ["", "The full list (names, IDs, positions) is in [`LOCATIONS.csv`](LOCATIONS.csv).", ""]
    with open(DOC, "w") as fh:
        fh.write("\n".join(out))


if __name__ == "__main__":
    write_docs()
