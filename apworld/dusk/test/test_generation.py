from . import DuskTestBase


class TestDefaults(DuskTestBase):
    """Default options: weapons, keys, powerups, secrets and chests randomized."""

    def test_start_access(self) -> None:
        self.assertTrue(self.can_reach_region("E1M1 Head Cheese"))
        self.assertFalse(self.can_reach_region("E1M2 Down on the Farm"))

    def test_strict_key_logic(self) -> None:
        self.collect_by_name(["E1M2 Access"])
        self.assertFalse(self.can_reach_location("E1M2 - Sword"))
        self.collect_by_name(["E1M2 Red Key"])
        self.assertTrue(self.can_reach_location("E1M2 - Sword"))

    def test_episode_starts_have_keys(self) -> None:
        self.assertTrue(self.can_reach_location("E2M1 - Crossbow"))

    def test_combat_logic(self) -> None:
        """Default (easy): E1M3 needs one firearm."""
        self.collect_by_name(["E1M3 Access"])
        self.assertFalse(self.can_reach_region("E1M3 Old Time Religion"))
        self.collect_by_name(["Crossbow"])
        self.assertTrue(self.can_reach_region("E1M3 Old Time Religion"))


class TestKeyRules(DuskTestBase):
    """Per-location key rules (key_logic.KEY_RULES). Combat logic off so only keys matter."""
    options = {"combat_logic": "unhinged"}

    def test_rules_name_real_locations(self) -> None:
        from ..data import LEVELS_BY_CODE, LOCATIONS
        from ..key_logic import KEY_RULES
        names = {l.name for l in LOCATIONS} | {f"{c} - Level Complete" for c in LEVELS_BY_CODE}
        for code, rules in KEY_RULES.items():
            self.assertIn(code, LEVELS_BY_CODE)
            for name, keys in rules.items():
                if name == "*":
                    continue
                self.assertIn(name, names)
                self.assertTrue(name.startswith(code + " - "), name)
                self.assertTrue(set(keys) <= set(LEVELS_BY_CODE[code].keys), (name, keys))

    def test_e1m5(self) -> None:
        self.collect_by_name(["E1M5 Access"])
        for name in ("E1M5 - Shotgun 2", "E1M5 - Super Shotgun 1", "E1M5 - Red Key", "E1M5 - Hallowed Health 1"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E1M5 - Yellow Key", "E1M5 - Shotgun 1", "E1M5 - Fast Fire Totem 1", "E1M5 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e1m6(self) -> None:
        self.collect_by_name(["E1M6 Access"])
        for name in ("E1M6 - Pistol 1", "E1M6 - Super Shotgun", "E1M6 - Secret Area 2", "E1M6 - Yellow Key"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E1M6 - Red Key", "E1M6 - Secret Area 1", "E1M6 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)
        self.collect_by_name(["E1M6 Red Key", "E1M6 Yellow Key"])
        self.assertTrue(self.can_reach_location("E1M6 - Level Complete"))

    def test_e1m9(self) -> None:
        self.collect_by_name(["E1M9 Access"])
        for name in ("E1M9 - Shotgun 3", "E1M9 - Yellow Key", "E1M9 - Secret Area 8", "E1M9 - Hunting Rifle"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E1M9 - Shotgun 1", "E1M9 - Blue Key", "E1M9 - Secret Area 4", "E1M9 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e2m1(self) -> None:
        """E2M1 is a starting level, so its keys are precollected; remove them to test the rule itself."""
        state = self.multiworld.state
        for key in ("E2M1 Red Key", "E2M1 Blue Key", "E2M1 Yellow Key"):
            state.remove(self.world.create_item(key))
        for name in ("E2M1 - Crossbow", "E2M1 - Blue Key", "E2M1 - Yellow Key", "E2M1 - Red Key"):
            self.assertTrue(self.can_reach_location(name), name)
        self.assertFalse(self.can_reach_location("E2M1 - Level Complete"))
        state.collect(self.world.create_item("E2M1 Red Key"))
        self.assertTrue(self.can_reach_location("E2M1 - Level Complete"))

    def test_e2m3(self) -> None:
        self.collect_by_name(["E2M3 Access"])
        for name in ("E2M3 - Mortar", "E2M3 - Yellow Key", "E2M3 - Assault Rifle 1", "E2M3 - Secret Area 3"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E2M3 - Assault Rifle 2", "E2M3 - Red Key", "E2M3 - Secret Area 2", "E2M3 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e2m4(self) -> None:
        self.collect_by_name(["E2M4 Access"])
        for name in ("E2M4 - Shotgun 1", "E2M4 - Red Key"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E2M4 - Shotgun 2", "E2M4 - Blue Key", "E2M4 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e2m6(self) -> None:
        self.collect_by_name(["E2M6 Access"])
        for name in ("E2M6 - Pistol 3", "E2M6 - Shotgun 2", "E2M6 - Secret Area 6", "E2M6 - Hallowed Health 2"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E2M6 - Pistol 2", "E2M6 - Red Key", "E2M6 - Hallowed Health 1", "E2M6 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e2m7(self) -> None:
        self.collect_by_name(["E2M7 Access"])
        for name in ("E2M7 - Hunting Rifle", "E2M7 - Mortar", "E2M7 - Blue Key", "E2M7 - Shotgun 2"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E2M7 - Yellow Key", "E2M7 - Riveter", "E2M7 - Secret Area 1", "E2M7 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e3m1(self) -> None:
        """E3M1 is a starting level, so its keys are precollected; remove them to test the rule itself."""
        state = self.multiworld.state
        for key in ("E3M1 Red Key", "E3M1 Blue Key"):
            state.remove(self.world.create_item(key))
        for name in ("E3M1 - Sword", "E3M1 - Crossbow 2", "E3M1 - Red Key", "E3M1 - Secret Area 6"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E3M1 - Blue Key", "E3M1 - Crossbow 1", "E3M1 - Secret Area 1", "E3M1 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e3m2(self) -> None:
        self.collect_by_name(["E3M2 Access"])
        for name in ("E3M2 - Sword", "E3M2 - Blue Key", "E3M2 - Secret Area 8", "E3M2 - Fast Fire Totem"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E3M2 - Red Key", "E3M2 - Crossbow", "E3M2 - Treasure Chest 1", "E3M2 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_e3m7(self) -> None:
        self.collect_by_name(["E3M7 Access"])
        for name in ("E3M7 - Hunting Rifle", "E3M7 - Crossbow", "E3M7 - Red Key", "E3M7 - Secret Area 3"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E3M7 - Pistol 1", "E3M7 - Riveter", "E3M7 - Blue Key", "E3M7 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)

    def test_item_rules(self) -> None:
        from ..data import LOCATIONS
        from ..items import ITEM_NAME_TO_ID
        from ..key_logic import ITEM_RULES
        names = {l.name for l in LOCATIONS}
        for name, items in ITEM_RULES.items():
            self.assertIn(name, names)
            for item in items:
                self.assertIn(item, ITEM_NAME_TO_ID)
        # E3M1's keys are precollected (starting level), so only the Mortar matters here.
        self.assertFalse(self.can_reach_location("E3M1 - Super Shotgun"))
        self.collect_by_name(["Mortar"])
        self.assertTrue(self.can_reach_location("E3M1 - Super Shotgun"))

    def test_e3m1_super_shotgun(self) -> None:
        """E3M1 - Super Shotgun needs the Blue Key, the Red Key and the Mortar."""
        state = self.multiworld.state
        blue, red = self.world.create_item("E3M1 Blue Key"), self.world.create_item("E3M1 Red Key")
        state.remove(blue)
        state.remove(red)
        self.collect_by_name(["Mortar"])
        for keys in ((), (blue,), (red,)):
            for k in keys:
                state.collect(k)
            self.assertFalse(self.can_reach_location("E3M1 - Super Shotgun"), [k.name for k in keys])
            for k in keys:
                state.remove(k)
        state.collect(blue)
        state.collect(red)
        self.assertTrue(self.can_reach_location("E3M1 - Super Shotgun"))

    def test_junk_keys(self) -> None:
        from BaseClasses import ItemClassification as IC
        self.assertEqual(self.world.create_item("E2M1 Blue Key").classification, IC.filler)
        self.assertEqual(self.world.create_item("E2M1 Yellow Key").classification, IC.filler)
        self.assertTrue(self.world.create_item("E2M1 Red Key").advancement)

    def test_e1m8(self) -> None:
        self.collect_by_name(["E1M8 Access"])
        for name in ("E1M8 - Super Shotgun", "E1M8 - Red Key", "E1M8 - Blue Key", "E1M8 - Secret Area 4"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E1M8 - Yellow Key", "E1M8 - Riveter", "E1M8 - Level Complete"):
            self.assertFalse(self.can_reach_location(name), name)
        self.collect_by_name(["E1M8 Blue Key", "E1M8 Red Key", "E1M8 Yellow Key"])
        self.assertTrue(self.can_reach_location("E1M8 - Level Complete"))


class TestExorcist(DuskTestBase):
    """exorcist: E1M1, E2M1 (not Level Complete) and E3M1's key-less checks are free; everything else needs all 10
    weapons, which all land in those free checks."""
    options = {"combat_logic": "exorcist"}
    ALL = ["Progressive Pistol", "Progressive Pistol", "Progressive Shotgun", "Progressive Shotgun", "Super Shotgun",
           "Assault Rifle", "Hunting Rifle", "Crossbow", "Mortar", "Riveter"]
    FREE_PREFIXES = ("E1M1 - ", "E2M1 - ", "E3M1 - ")

    def test_rules(self) -> None:
        for name in ("E1M1 - Level Complete", "E2M1 - Crossbow", "E3M1 - Sword", "E3M1 - Red Key"):
            self.assertTrue(self.can_reach_location(name), name)
        locked = ("E2M1 - Level Complete", "E3M1 - Blue Key", "E3M1 - Crossbow 1", "E3M1 - Level Complete")
        for name in locked:
            self.assertFalse(self.can_reach_location(name), name)
        self.collect_by_name(["E1M2 Access"])
        self.collect_by_name(self.ALL[:-1])
        self.assertFalse(self.can_reach_region("E1M2 Down on the Farm"))
        self.assertFalse(self.can_reach_location("E2M1 - Level Complete"))
        self.collect_by_name(self.ALL[-1:])
        self.assertTrue(self.can_reach_region("E1M2 Down on the Farm"))
        for name in locked:
            self.assertTrue(self.can_reach_location(name), name)

    def test_weapons_in_free_checks(self) -> None:
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        placed = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.item and loc.item.player == self.player and loc.item.name in self.ALL]
        self.assertEqual(len(placed), 10)
        for loc in placed:
            self.assertTrue(loc.name.startswith(self.FREE_PREFIXES), loc.name)
            self.assertTrue(self.world._exorcist_free(loc.name.split(" - ")[0], loc.name), loc.name)


class TestExorcistEpisode2Only(DuskTestBase):
    """Without Episodes 1 and 3, the weapons go in E2M1 (not its Level Complete)."""
    options = {"combat_logic": "exorcist", "episode1": False, "episode3": False, "secret_levels": False}

    def test_weapons_in_e2m1(self) -> None:
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        placed = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.item and loc.item.player == self.player and loc.item.name in TestExorcist.ALL]
        self.assertEqual(len(placed), 10)
        self.assertTrue(all(loc.name.startswith("E2M1 - ") and loc.name != "E2M1 - Level Complete"
                            for loc in placed), [l.name for l in placed])


class TestUnhinged(DuskTestBase):
    """No combat logic: an unlocked level is in logic with sickles only."""
    options = {"combat_logic": "unhinged"}

    def test_no_firearms_needed(self) -> None:
        self.assertTrue(self.can_reach_region("E2M1 The Grainery"))
        self.collect_by_name(["E3M8 Access"])
        self.assertTrue(self.can_reach_region("E3M8 As Above, So Below"))


class TestUnhingedAlias(DuskTestBase):
    """Old YAMLs with combat_logic: none still work."""
    options = {"combat_logic": "none"}

    def test_alias(self) -> None:
        self.assertEqual(self.world.options.combat_logic.value, self.world.options.combat_logic.option_unhinged)


class TestNormal(DuskTestBase):
    """normal: E1M5 is free, E1M6 needs one firearm."""
    options = {"combat_logic": "normal"}

    def test_normal_thresholds(self) -> None:
        self.collect_by_name(["E1M5 Access", "E1M6 Access"])
        self.assertTrue(self.can_reach_region("E1M5 Sawdust"))
        self.assertFalse(self.can_reach_region("E1M6 The Cutty Mine"))
        self.collect_by_name(["Crossbow"])
        self.assertTrue(self.can_reach_region("E1M6 The Cutty Mine"))


class TestLenientAlias(DuskTestBase):
    """Old YAMLs with combat_logic: lenient get the same rules under their new name, normal."""
    options = {"combat_logic": "lenient"}

    def test_alias(self) -> None:
        self.assertEqual(self.world.options.combat_logic.value, self.world.options.combat_logic.option_normal)


class TestEverything(DuskTestBase):
    options = {"randomize_health": True, "randomize_armor": True, "randomize_ammo": True, "goal": "all_levels"}


class TestEpisode2Only(DuskTestBase):
    options = {"episode1": False, "episode3": False, "secret_levels": False}

    def test_only_episode_2(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertTrue(all(n.startswith("E2M") for n in names), [n for n in names if not n.startswith("E2M")][:5])


class TestSmallSeed(DuskTestBase):
    """Only keys, secrets and level completions."""
    options = {"randomize_weapons": False, "randomize_powerups": False, "randomize_treasure_chests": False}


class TestLevelCompleteOnly(DuskTestBase):
    """Every category off: only the per-level 'Level Complete' checks remain (level access shuffle only)."""
    options = {"randomize_weapons": False, "randomize_keys": False, "randomize_powerups": False,
               "randomize_secrets": False, "randomize_treasure_chests": False}

    def test_only_level_complete(self) -> None:
        names = [loc.name for loc in self.multiworld.get_locations(self.player) if loc.address is not None]
        self.assertTrue(all(n.endswith("Level Complete") for n in names))
