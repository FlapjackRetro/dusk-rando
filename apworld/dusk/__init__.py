"""Archipelago world for DUSK (New Blood Interactive, 2018)."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from BaseClasses import CollectionState, ItemClassification as IC, Location, Region, Tutorial
from Options import OptionError
from worlds.AutoWorld import WebWorld, World

from .data import ALWAYS_CATEGORIES, BOSS_LEVELS, LEVELS, LEVELS_BY_CODE, LOCATIONS, VANILLA_ONLY_ITEMS, LevelData
from .key_logic import DEFAULT as KEY_DEFAULT, ITEM_RULES, KEY_RULES
from .items import (EXORCIST_WEAPONS, FILLER_WEIGHTS, FIREARMS, GAME, ITEM_GROUPS, ITEM_INFO, ITEM_NAME_TO_ID,
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
        if self.exorcist:
            self._setup_exorcist(episodes)

    # ---- exorcist combat logic (testing) ----------------------------------------------------------
    @property
    def exorcist(self) -> bool:
        return "weapons" in self.categories and \
            self.options.combat_logic == self.options.combat_logic.option_exorcist

    # Levels whose checks can be free on exorcist: all of E1M1, E2M1 except Level Complete, E3M1's key-less checks.
    EXORCIST_LEVELS = ("E1M1", "E2M1", "E3M1")
    exorcist_e3_only = False

    def _exorcist_free(self, code: str, name: str) -> bool:
        """Is this check (or Cleared event) in logic without the 10 weapons on exorcist?"""
        if code == "E1M1":
            return True
        if code == "E2M1":
            return name not in ("E2M1 - Level Complete", "E2M1 - Cleared")
        if code == "E3M1":
            if self.exorcist_e3_only:
                # Episode 3 alone: E3M1's 7 key-less checks can't hold 10 weapons, so treat it like E2M1.
                return name not in ("E3M1 - Level Complete", "E3M1 - Cleared")
            # Key-less as mapped in key_logic.py (E3M1's keys are precollected, so this can't use the state).
            rules = KEY_RULES.get(code, {})
            rule = rules.get(name, rules.get(KEY_DEFAULT))
            return rule == [] and name not in ITEM_RULES
        return False

    def _setup_exorcist(self, episodes: List[int]) -> None:
        """Everything except the free checks (see _exorcist_free) needs all 10 weapons, so they all go there."""
        # Keep the weapons in this world; otherwise they could also land in other players' early checks.
        self.options.local_items.value |= set(EXORCIST_WEAPONS)
        self.exorcist_e3_only = episodes == [3]
        included = {l.code for l in self.included_levels}
        free = [l.name for l in LOCATIONS if l.level in self.EXORCIST_LEVELS and l.level in included
                and self._is_location(l) and self._exorcist_free(l.level, l.name)]
        # Room for the 10 weapons, plus one more level Access item when nothing opens up after them (Episode 1
        # only: E1M1 is entirely free, so no check becomes reachable once the weapons are found).
        need = sum(EXORCIST_WEAPONS.values()) + (1 if episodes == [1] else 0)
        if len(free) < need:
            raise OptionError(
                f"{self.player_name}: combat_logic exorcist puts all 10 weapons in E1M1, E2M1 and E3M1's key-less "
                f"checks, but there are only {len(free)} of those with these options (needs {need}). Enable more "
                "check categories, e.g. randomize_secrets, randomize_powerups or randomize_ammo.")

    # Pickups that stay vanilla unless their own option is on (option attribute name).
    OPTIONAL_LOCATIONS = {"E3M4 - Flashlight": "randomize_e3m4_flashlight"}

    def _is_location(self, loc) -> bool:
        if loc.name in self.OPTIONAL_LOCATIONS and not getattr(self.options, self.OPTIONAL_LOCATIONS[loc.name]):
            return False
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

    # Distinct firearms required to enter a level on 'easy', by episode: [(from level number, count), ...].
    # 'normal' needs one fewer at every step.
    # Every episode starts with sickles only, so each episode's first level never needs any.
    COMBAT_TABLE = {
        1: [(3, 1), (6, 2)],
        2: [(2, 2), (6, 3)],
        3: [(2, 3), (6, 4)],
    }

    def firearms_needed(self, lvl: LevelData) -> int:
        combat = self.options.combat_logic
        if "weapons" not in self.categories or combat in (combat.option_unhinged, combat.option_exorcist):
            return 0  # exorcist is handled in can_enter
        need = 0
        for start, count in self.COMBAT_TABLE[lvl.episode]:
            if lvl.number >= start:
                need = count
        if combat == combat.option_normal:
            need = max(0, need - 1)
        return need

    def can_enter(self, state: CollectionState, lvl: LevelData) -> bool:
        if not state.has(f"{lvl.code} Access", self.player):
            return False
        if self.exorcist:
            # The free levels can be entered; their other checks get the weapon requirement in set_rules.
            return lvl.code in self.EXORCIST_LEVELS or state.has_all_counts(EXORCIST_WEAPONS, self.player)
        need = self.firearms_needed(lvl)
        return need == 0 or state.has_from_list_unique(FIREARMS, self.player, need)

    def set_rules(self) -> None:
        item_rules = ITEM_RULES if "weapons" in self.categories else {}
        for lvl in self.included_levels:
            keys = self.level_keys(lvl)
            # Locations listed in key_logic.KEY_RULES need only the keys given there. Everything else uses strict
            # key logic: every check in a level that has keys needs all of that level's keys, until the level's
            # door/key layout has been mapped (see key_logic.py). ITEM_RULES adds other required items.
            rules = KEY_RULES.get(lvl.code, {})
            region = self.multiworld.get_region(f"{lvl.code} {lvl.name}", self.player)
            for location in region.locations:
                needed: List[str] = []
                if keys:
                    rule = rules.get(location.name)
                    if rule is None and location.name == f"{lvl.code} - Cleared":
                        rule = rules.get(f"{lvl.code} - Level Complete")
                    if rule is None:
                        rule = rules.get(KEY_DEFAULT)
                    needed = keys if rule is None else [f"{lvl.code} {k}" for k in rule]
                extra = item_rules.get(location.name, [])
                needed = needed + [i for i in extra if isinstance(i, str)]
                any_of = [i for i in extra if not isinstance(i, str)]  # groups: any one item of each
                weapons = (self.exorcist and lvl.code in self.EXORCIST_LEVELS
                           and not self._exorcist_free(lvl.code, location.name))
                if needed or any_of or weapons:
                    location.access_rule = lambda state, k=needed, a=any_of, w=weapons: (
                        state.has_all(k, self.player)
                        and all(state.has_any(g, self.player) for g in a)
                        and (not w or state.has_all_counts(EXORCIST_WEAPONS, self.player)))

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
