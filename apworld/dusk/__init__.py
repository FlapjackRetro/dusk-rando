"""Archipelago world for DUSK (New Blood Interactive, 2018)."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from BaseClasses import CollectionState, ItemClassification as IC, Location, Region, Tutorial
from Options import OptionError
from worlds.AutoWorld import WebWorld, World

from .data import ALWAYS_CATEGORIES, BOSS_LEVELS, LEVELS, LEVELS_BY_CODE, LOCATIONS, VANILLA_ONLY_ITEMS, LevelData
from .items import (FILLER_WEIGHTS, FIREARMS, GAME, ITEM_GROUPS, ITEM_INFO, ITEM_NAME_TO_ID,
                    VANILLA_WEAPON_TO_ITEM, WEAPON_ITEMS, DuskItem)
from .options import CATEGORY_OPTIONS, DuskOptions, option_groups

LOCATION_NAME_TO_ID = {l.name: l.id for l in LOCATIONS}
LOCATION_GROUPS: Dict[str, Set[str]] = {}
for _l in LOCATIONS:
    LOCATION_GROUPS.setdefault(_l.level, set()).add(_l.name)
    LOCATION_GROUPS.setdefault(_l.category.replace("_", " ").title(), set()).add(_l.name)


class DuskLocation(Location):
    game = GAME


class DuskWeb(WebWorld):
    theme = "stone"
    option_groups = option_groups
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the DUSK randomizer for Archipelago.",
        "English", "setup_en.md", "setup/en", ["FlapjackRetro"],
    )]


class DuskWorld(World):
    """
    DUSK is a retro first-person shooter inspired by Quake, Blood and Heretic. Fight cultists, possessed scarecrows
    and worse through three episodes of rural horror, a twisted industrial complex and an ancient city.
    """
    game = GAME
    web = DuskWeb()
    options_dataclass = DuskOptions
    options: DuskOptions
    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID
    item_name_groups = ITEM_GROUPS
    location_name_groups = LOCATION_GROUPS
    origin_region_name = "Menu"

    included_levels: List[LevelData]
    categories: Set[str]

    # ---- setup --------------------------------------------------------------------------------
    def generate_early(self) -> None:
        episodes = [n for n, opt in ((1, self.options.episode1), (2, self.options.episode2),
                                     (3, self.options.episode3)) if opt]
        if not episodes:
            raise OptionError(f"{self.player_name}: DUSK needs at least one episode enabled.")
        self.included_levels = [l for l in LEVELS if l.episode in episodes
                                and (self.options.secret_levels or not l.secret)]
        self.categories = {c for c, opt in CATEGORY_OPTIONS.items() if getattr(self.options, opt)}
        self.categories.update(ALWAYS_CATEGORIES)
        # Each included episode starts with its first level unlocked. Its keys are given up front too,
        # otherwise strict key logic (see set_rules) would leave nothing reachable at the start of a seed.
        for ep in episodes:
            first = LEVELS_BY_CODE[f"E{ep}M1"]
            self.multiworld.push_precollected(self.create_item(f"{first.code} Access"))
            for key in self.level_keys(first):
                self.multiworld.push_precollected(self.create_item(key))

    def _is_location(self, loc) -> bool:
        return loc.category in self.categories and loc.vanilla_item not in VANILLA_ONLY_ITEMS

    # ---- regions & locations ------------------------------------------------------------------
    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        codes = {l.code for l in self.included_levels}
        by_level: Dict[str, Region] = {}
        for lvl in self.included_levels:
            region = Region(f"{lvl.code} {lvl.name}", self.player, self.multiworld)
            self.multiworld.regions.append(region)
            by_level[lvl.code] = region
            menu.connect(region, f"Enter {lvl.code}",
                         lambda state, l=lvl: self.can_enter(state, l))
        for loc in LOCATIONS:
            if loc.level not in codes or not self._is_location(loc):
                continue
            region = by_level[loc.level]
            region.locations.append(DuskLocation(self.player, loc.name, loc.id, region))
        # Events: one per finished level, used for the goal.
        for lvl in self.included_levels:
            region = by_level[lvl.code]
            ev = DuskLocation(self.player, f"{lvl.code} - Cleared", None, region)
            ev.place_locked_item(DuskItem(f"{lvl.code} Cleared", IC.progression, None, self.player))
            region.locations.append(ev)

    # ---- logic --------------------------------------------------------------------------------
    def level_keys(self, lvl: LevelData) -> List[str]:
        if "keys" not in self.categories:
            return []
        return [f"{lvl.code} {k}" for k in lvl.keys]

    # Distinct firearms required to enter a level, by episode: [(from level number, count), ...].
    # Every episode starts with sickles only, so each episode's first level never needs any.
    COMBAT_TABLE = {
        1: [(3, 1), (6, 2)],
        2: [(2, 2), (6, 3)],
        3: [(2, 3), (6, 4)],
    }

    def firearms_needed(self, lvl: LevelData) -> int:
        combat = self.options.combat_logic
        if "weapons" not in self.categories or combat == combat.option_unhinged:
            return 0
        if combat == combat.option_permissive:
            # Only the seed's very first level (E1M1, or the first level of the lowest included episode when
            # Episode 1 is off) is free; everything else needs one firearm.
            return 0 if lvl.code == self.free_level else 1
        need = 0
        for start, count in self.COMBAT_TABLE[lvl.episode]:
            if lvl.number >= start:
                need = count
        if combat == combat.option_lenient:
            need = max(0, need - 1)
        return need

    @property
    def free_level(self) -> str:
        return f"E{min(l.episode for l in self.included_levels)}M1"

    def can_enter(self, state: CollectionState, lvl: LevelData) -> bool:
        if not state.has(f"{lvl.code} Access", self.player):
            return False
        need = self.firearms_needed(lvl)
        return need == 0 or state.has_from_list_unique(FIREARMS, self.player, need)

    def set_rules(self) -> None:
        for lvl in self.included_levels:
            keys = self.level_keys(lvl)
            if not keys:
                continue
            # Strict key logic: we don't yet know which pickups sit behind which door, so every check in a
            # level that has keys is considered to need all of that level's keys.
            # TODO: replace with per-door regions once door/key placement is mapped out.
            region = self.multiworld.get_region(f"{lvl.code} {lvl.name}", self.player)
            for location in region.locations:
                location.access_rule = lambda state, k=keys: state.has_all(k, self.player)

        if self.options.goal == self.options.goal.option_bosses:
            targets = [f"{BOSS_LEVELS[ep]} Cleared" for ep in sorted({l.episode for l in self.included_levels})]
        else:
            targets = [f"{l.code} Cleared" for l in self.included_levels]
        self.multiworld.completion_condition[self.player] = lambda state: state.has_all(targets, self.player)

    # ---- items --------------------------------------------------------------------------------
    def create_item(self, name: str) -> DuskItem:
        info = ITEM_INFO[name]
        return DuskItem(name, info.classification, ITEM_NAME_TO_ID[name], self.player)

    def get_filler_item_name(self) -> str:
        names = list(FILLER_WEIGHTS)
        return self.random.choices(names, weights=[FILLER_WEIGHTS[n] for n in names])[0]

    def create_items(self) -> None:
        codes = {l.code for l in self.included_levels}
        starting = {f"E{l.episode}M1" for l in self.included_levels}
        locations = [l for l in LOCATIONS if l.level in codes and self._is_location(l)]
        total = len(locations)

        pool: List[DuskItem] = []
        for lvl in self.included_levels:
            if lvl.code in starting:
                continue  # access and keys were precollected in generate_early
            pool.append(self.create_item(f"{lvl.code} Access"))
            pool += [self.create_item(k) for k in self.level_keys(lvl)]
        if "weapons" in self.categories:
            for weapon, count in WEAPON_ITEMS.items():
                pool += [self.create_item(weapon) for _ in range(count)]

        # Every other check contributes its vanilla item, so the game's item balance roughly survives.
        # Duplicate weapons/keys (e.g. a second Shotgun pickup in a later level) become generic filler.
        filler_budget = []
        for loc in locations:
            if loc.category in ("weapons", "keys", "level_complete", "secrets") or loc.vanilla_item is None:
                continue
            item = VANILLA_WEAPON_TO_ITEM.get(loc.vanilla_item, loc.vanilla_item)
            filler_budget.append(item)
        self.random.shuffle(filler_budget)

        if len(pool) > total:
            raise OptionError(f"{self.player_name}: only {total} DUSK checks for {len(pool)} required items. "
                              "Enable more check categories (keys or secrets are good choices).")
        for name in filler_budget:
            if len(pool) >= total:
                break
            pool.append(self.create_item(name))
        while len(pool) < total:
            pool.append(self.create_item(self.get_filler_item_name()))
        self.multiworld.itempool += pool

    # ---- client data --------------------------------------------------------------------------
    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "levels": [l.code for l in self.included_levels],
            "categories": sorted(self.categories),
            "goal": self.options.goal.current_key,
            "death_link": bool(self.options.death_link),
        }
