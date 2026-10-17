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
        self.assertTrue(self.can_reach_location("E2M1 - Sword"))

    def test_combat_logic(self) -> None:
        self.collect_by_name(["E1M3 Access"])
        self.assertFalse(self.can_reach_region("E1M3 Old Time Religion"))
        self.collect_by_name(["Crossbow"])
        self.assertTrue(self.can_reach_region("E1M3 Old Time Religion"))


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


class TestPermissive(DuskTestBase):
    """E1M1 is free; E2M1/E3M1 can be explored with sickles but finishing them needs a firearm; everything else
    needs a firearm to enter."""
    options = {"combat_logic": "permissive"}

    def test_e1m1_free(self) -> None:
        self.assertTrue(self.can_reach_location("E1M1 - Level Complete"))

    def test_episode_starts(self) -> None:
        for code in ("E2M1", "E3M1"):
            self.assertTrue(self.can_reach_location(f"{code} - Sword"), code)
            self.assertFalse(self.can_reach_location(f"{code} - Level Complete"), code)
        self.collect_by_name(["Crossbow"])
        for code in ("E2M1", "E3M1"):
            self.assertTrue(self.can_reach_location(f"{code} - Level Complete"), code)

    def test_others_need_one_firearm(self) -> None:
        self.collect_by_name(["E1M2 Access", "E3M9 Access"])
        for region in ("E1M2 Down on the Farm", "E3M9 The Dweller in Darkness"):
            self.assertFalse(self.can_reach_region(region), region)
        self.collect_by_name(["Crossbow"])
        for region in ("E1M2 Down on the Farm", "E3M9 The Dweller in Darkness"):
            self.assertTrue(self.can_reach_region(region), region)


class TestPermissiveEpisode3Only(DuskTestBase):
    """Without Episode 1 the seed still starts: E3M1's pickups are in logic with sickles."""
    options = {"combat_logic": "permissive", "episode1": False, "episode2": False, "secret_levels": False}

    def test_episode_start(self) -> None:
        self.assertTrue(self.can_reach_region("E3M1 The Iron Cathedral"))
        self.assertFalse(self.can_reach_location("E3M1 - Level Complete"))
        self.collect_by_name(["E3M2 Access"])
        self.assertFalse(self.can_reach_region("E3M2 Fire and Ice"))


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
