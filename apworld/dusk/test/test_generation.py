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

    def test_e2m4(self) -> None:
        self.collect_by_name(["E2M4 Access"])
        for name in ("E2M4 - Shotgun 1", "E2M4 - Red Key"):
            self.assertTrue(self.can_reach_location(name), name)
        for name in ("E2M4 - Shotgun 2", "E2M4 - Blue Key", "E2M4 - Level Complete"):
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
    """exorcist: E1M1 is free; everything else needs all 10 weapons, which all land in E1M1."""
    options = {"combat_logic": "exorcist"}
    ALL = ["Progressive Pistol", "Progressive Pistol", "Progressive Shotgun", "Progressive Shotgun", "Super Shotgun",
           "Assault Rifle", "Hunting Rifle", "Crossbow", "Mortar", "Riveter"]

    def test_rules(self) -> None:
        self.assertTrue(self.can_reach_location("E1M1 - Level Complete"))
        self.collect_by_name(["E1M2 Access"])
        self.collect_by_name(self.ALL[:-1])
        for name in ("E1M2 Down on the Farm", "E2M1 The Grainery", "E3M1 The Iron Cathedral"):
            self.assertFalse(self.can_reach_region(name), name)
        self.collect_by_name(self.ALL[-1:])
        for name in ("E1M2 Down on the Farm", "E2M1 The Grainery", "E3M1 The Iron Cathedral"):
            self.assertTrue(self.can_reach_region(name), name)

    def test_weapons_in_e1m1(self) -> None:
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        placed = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.item and loc.item.player == self.player and loc.item.name in self.ALL]
        self.assertEqual(len(placed), 10)
        self.assertTrue(all(loc.name.startswith("E1M1 - ") for loc in placed), [l.name for l in placed])


class TestExorcistEpisode2Only(DuskTestBase):
    """Without Episode 1, E2M1 takes E1M1's place."""
    options = {"combat_logic": "exorcist", "episode1": False, "episode3": False, "secret_levels": False}

    def test_weapons_in_e2m1(self) -> None:
        from Fill import distribute_items_restrictive
        distribute_items_restrictive(self.multiworld)
        placed = [loc for loc in self.multiworld.get_locations(self.player)
                  if loc.item and loc.item.player == self.player and loc.item.name in TestExorcist.ALL]
        self.assertEqual(len(placed), 10)
        self.assertTrue(all(loc.name.startswith("E2M1 - ") for loc in placed), [l.name for l in placed])


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
