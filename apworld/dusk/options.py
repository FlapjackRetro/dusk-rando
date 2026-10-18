from dataclasses import dataclass

from Options import Choice, DeathLink, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Toggle


class Episode1(DefaultOnToggle):
    """Include Episode 1: The Foothills."""
    display_name = "Episode 1"


class Episode2(DefaultOnToggle):
    """Include Episode 2: The Facilities."""
    display_name = "Episode 2"


class Episode3(DefaultOnToggle):
    """Include Episode 3: The Nameless City."""
    display_name = "Episode 3"


class SecretLevels(DefaultOnToggle):
    """Include each included episode's secret level (E1MS, E2MS, E3MS). Their access is an item like any other level."""
    display_name = "Secret Levels"


class Goal(Choice):
    """
    bosses: finish the final level of every included episode (E1M10, E2M10, E3M10).
    all_levels: finish every included level.
    """
    display_name = "Goal"
    option_bosses = 0
    option_all_levels = 1
    default = 0


# ---- location categories -------------------------------------------------------------------
# Each toggle adds that kind of pickup to the pool of checks. Pickups in a category that is off
# behave exactly like the vanilla game.

class RandomizeWeapons(DefaultOnToggle):
    """Weapon pickups (Pistol, Shotgun, Super Shotgun, Assault Rifle, Hunting Rifle, Crossbow, Mortar, Riveter, Sword)
    become checks, and the weapons themselves are shuffled into the multiworld. ~270 checks."""
    display_name = "Randomize Weapons"


class RandomizeKeys(DefaultOnToggle):
    """Red/Blue/Yellow key pickups become checks, and each level's keys become items. ~90 checks."""
    display_name = "Randomize Keys"


class RandomizePowerups(DefaultOnToggle):
    """Hallowed Health, Fast Fire Totem, Serum of Blistering Heat, Flashlight and Backpack pickups become checks.
    Thermal Suits are never randomized. ~105 checks."""
    display_name = "Randomize Powerups"


class RandomizeSecrets(DefaultOnToggle):
    """Discovering a secret area is a check. ~165 checks."""
    display_name = "Randomize Secrets"


class RandomizeTreasureChests(DefaultOnToggle):
    """Opening a treasure chest is a check. 16 checks."""
    display_name = "Randomize Treasure Chests"


class RandomizeHealth(Toggle):
    """Medical kits, small medical kits and magic potions become checks. ~525 checks."""
    display_name = "Randomize Health"


class RandomizeArmor(Toggle):
    """Morale pickups (gold coins, bags of gems, diamonds) become checks. ~580 checks."""
    display_name = "Randomize Morale (Armor)"


class RandomizeAmmo(Toggle):
    """Every ammo pickup becomes a check. ~1440 checks; this makes for a very long seed."""
    display_name = "Randomize Ammo"


class CombatLogic(Choice):
    """
    Only matters when weapons are randomized. How many distinct firearms (weapons other than the starting sickles
    and the sword) the logic expects before a level is considered in logic. More required firearms means you arrive
    better armed. Each episode's first level never needs any; secret levels need as many as the end of their episode.
    exorcist: for testing. Every check outside E1M1 needs all 10 weapons (both Progressive Pistols, both Progressive
              Shotguns and the other six; not the Sword), so all 10 are placed in E1M1. If Episode 1 is off, the
              first included episode's first level takes E1M1's place.
    easy: Episode 1 needs 1 from E1M3 and 2 from E1M6; Episode 2 needs 2 from E2M2 and 3 from E2M6; Episode 3
          needs 3 from E3M2 and 4 from E3M6.
    normal: Episode 1 needs 1 from E1M6; Episode 2 needs 1 from E2M2 and 2 from E2M6; Episode 3 needs 2 from E3M2
            and 3 from E3M6.
    unhinged: no combat logic. Sickles are enough for everything; you may play a long time with only them.
    """
    display_name = "Combat Logic"
    option_exorcist = 0
    option_easy = 1
    option_normal = 2
    option_unhinged = 3
    alias_lenient = 2
    alias_none = 3
    default = 1


@dataclass
class DuskOptions(PerGameCommonOptions):
    episode1: Episode1
    episode2: Episode2
    episode3: Episode3
    secret_levels: SecretLevels
    goal: Goal
    randomize_weapons: RandomizeWeapons
    randomize_keys: RandomizeKeys
    randomize_powerups: RandomizePowerups
    randomize_secrets: RandomizeSecrets
    randomize_treasure_chests: RandomizeTreasureChests
    randomize_health: RandomizeHealth
    randomize_armor: RandomizeArmor
    randomize_ammo: RandomizeAmmo
    combat_logic: CombatLogic
    death_link: DeathLink


option_groups = [
    OptionGroup("Levels", [Episode1, Episode2, Episode3, SecretLevels, Goal]),
    OptionGroup("Checks", [RandomizeWeapons, RandomizeKeys, RandomizePowerups, RandomizeSecrets,
                           RandomizeTreasureChests, RandomizeHealth, RandomizeArmor, RandomizeAmmo]),
    OptionGroup("Logic", [CombatLogic]),
]

CATEGORY_OPTIONS = {
    "weapons": "randomize_weapons", "keys": "randomize_keys", "powerups": "randomize_powerups",
    "secrets": "randomize_secrets", "treasure_chests": "randomize_treasure_chests",
    "health": "randomize_health", "armor": "randomize_armor", "ammo": "randomize_ammo",
}
