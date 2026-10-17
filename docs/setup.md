# DUSK Archipelago Setup Guide

This guide covers installing the DUSK randomizer mod and the DUSK APWorld for
[Archipelago](https://archipelago.gg).

> **Status:** early development. The mod has not been fully tested in game yet, so expect rough edges and please
> report problems on the [issue tracker](https://github.com/FlapjackRetro/dusk-rando/issues).

## What you need

- **DUSK** (Steam version)
- **[Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases)** 0.6.7 or newer, to generate games and
  connect to them
- **BepInEx 5**, the mod loader (64-bit Windows build)
- From this project's [Releases page](https://github.com/FlapjackRetro/dusk-rando/releases):
  - `DuskRando-<version>.zip`, the game mod
  - `dusk.apworld`, the Archipelago world

## 1. Find your DUSK folder

In Steam, right-click **DUSK** → **Manage** → **Browse local files**. That folder, the one containing `Dusk.exe`,
is your *DUSK folder*. On a default install it is:

```
C:\Program Files (x86)\Steam\steamapps\common\Dusk
```

## 2. Install BepInEx 5

1. Open the [BepInEx releases page](https://github.com/BepInEx/BepInEx/releases) and download the latest
   **5.x** release for 64-bit Windows: `BepInEx_win_x64_5.4.<x>.zip`.
   Do **not** use BepInEx 6 or the "IL2CPP" builds; DUSK needs BepInEx 5 (Mono).
2. Extract the zip **into your DUSK folder**. Afterwards the folder should contain `winhttp.dll`,
   `doorstop_config.ini` and a `BepInEx` folder, right next to `Dusk.exe`.
3. Start DUSK once and quit at the main menu. This lets BepInEx create its folders; you should now have
   `BepInEx\plugins` and `BepInEx\config`.

**Linux / Steam Deck (Proton):** BepInEx only loads under Proton if you add this to DUSK's Steam launch options
(right-click DUSK → **Properties** → **General** → **Launch Options**):

```
WINEDLLOVERRIDES="winhttp=n,b" %command%
```

## 3. Install the DUSK mod

1. Download `DuskRando-<version>.zip` from the
   [Releases page](https://github.com/FlapjackRetro/dusk-rando/releases).
2. Extract it **into your DUSK folder**. The zip already contains the `BepInEx\plugins\DuskRando` folders, so you
   should end up with:

   ```
   Dusk\
     Dusk.exe
     BepInEx\
       plugins\
         DuskRando\
           DuskRando.dll
           Archipelago.MultiClient.Net.dll
           Newtonsoft.Json.dll
   ```

   If your unzip tool made an extra `DuskRando-<version>` folder, move its `BepInEx` folder up into the DUSK folder
   and let it merge with the existing one.
3. Start DUSK. A small **Archipelago** window should appear in the top-left corner; **F1** shows or hides it.
   If it doesn't appear, check `BepInEx\LogOutput.log` in your DUSK folder for errors.

## 4. Install the APWorld

The APWorld goes into your Archipelago installation (the machine that **generates** the game; when someone
else hosts, give them the file).

- **Easiest:** double-click `dusk.apworld` and Archipelago installs it.
- **Manually:** copy `dusk.apworld` into Archipelago's `custom_worlds` folder, e.g.
  `C:\ProgramData\Archipelago\custom_worlds\`.

Restart the Archipelago Launcher afterwards so it picks up the new world.

## 5. Create your options file

1. Open the **Archipelago Launcher** and click **Generate Template Options**. A folder opens containing
   `DUSK.yaml`.
2. Copy it, set your `name`, and change any options. The most important ones:

   | Option | Default | What it does |
   |---|---|---|
   | `episode1`, `episode2`, `episode3` | on | Which episodes are in the game |
   | `secret_levels` | on | Include E1MS, E2MS and E3MS |
   | `goal` | `bosses` | `bosses` = beat E1M10/E2M10/E3M10; `all_levels` = finish every level |
   | `randomize_weapons` / `keys` / `powerups` / `secrets` / `treasure_chests` | on | Which pickups are checks |
   | `randomize_health` / `armor` / `ammo` | off | Add many more checks (ammo alone adds ~1,400) |
   | `combat_logic` | `normal` | How many guns the logic expects before later levels |
   | `death_link` | off | Die when others die, and vice versa |

   See [ITEMS.md](ITEMS.md) for exactly what each category contains.
3. Put the YAML in Archipelago's `Players` folder and generate as usual (or send it to whoever is hosting).

## 6. Connect and play

1. Start DUSK. At the main menu, enter the **server** (e.g. `archipelago.gg:38281`), your **slot** name and the
   **password** (if any) in the Archipelago window, then click **Connect**. Always connect *before* starting a game.
2. Press **ARCHIPELAGO** (the new top button on the main menu) and pick a difficulty. You land on the level map of
   your first episode. At the start of a seed only each episode's first level (E1M1, E2M1, E3M1) is shown; more
   appear as you receive `<level> Access` items.
3. Hovering a level on the map shows its stats, plus a **KEYS** row: the level's keys in colour once you've
   received them, dark until then ("NONE" if the level has no keys).
4. On the map, the **E1 / E2 / E3** buttons above *Back to Main Menu* switch between episodes. Your current episode
   is highlighted; episodes you have no access to yet are greyed out.
5. In a level, the pause menu has a **LEVEL SELECT** button that takes you back to the episode map.
6. When you finish a level, the game tries to load the next one as usual. If you don't have access to it yet, you
   are sent to that episode's map instead.
7. CAMPAIGN and ENDLESS are still there, but Endless mode isn't part of the randomizer and CAMPAIGN follows the
   vanilla episode flow, so use ARCHIPELAGO.
8. Your connection details are saved in `BepInEx\config\flapjackretro.dusk.archipelago.cfg`. The same file has
   `KeepWindowMode` (on by default): DUSK no longer jumps back to fullscreen on the menu or when a level loads,
   so a windowed game (Alt+Enter) stays windowed. The game's own Fullscreen setting still works.
   `UseCompression` (on by default) makes the mod use a compressed connection to the server, as Archipelago
   recommends; if that doesn't work it quietly falls back to a normal connection. `BepInEx\LogOutput.log` shows
   "Connected to … (compressed)" when compression is in use.

### What you'll see

- Randomized pickups look like the item they hold. Your own DUSK items use the DUSK model (a shotgun pickup that
  holds a Riveter looks like a Riveter). Items for other players show an Archipelago logo: grey for filler, colour
  for useful items, colour with a yellow arrow for progression.
- Ammo, health, morale, keys and the backpack always show their DUSK model; every level carries those. Other DUSK
  models are learned from the levels you visit. Until then, a Box of Mortar Grenades shows as a single grenade, a key
  borrows another episode's key of the same colour, and weapons, Fast Fire Totems, Serums of Blistering Heat and
  Flashlights show the Archipelago logo.
- Before a level starts, the map's loadout picker ticks exactly the weapons you've received (you can't tick others),
  and MAX / Reset only change ammo for those weapons.
- Level stats on the map (best time, kills, secrets, awards) are kept per seed while you're connected, in
  `Dusk\config\archipelago\scores_<seed>_<slot>`. A new seed starts clean, the same seed picks up where you left
  off, and your normal DUSK stats in `Dusk\config\scores` are left untouched.
- Secret areas and treasure chests look normal; finding or opening them sends the check.

## Uninstalling

Delete the `BepInEx\plugins\DuskRando` folder to remove the randomizer. To remove BepInEx completely, also delete
`winhttp.dll`, `doorstop_config.ini`, `.doorstop_version` (if present) and the `BepInEx` folder from your DUSK
folder.

---

## For maintainers: building a release

1. Build the mod (requires the .NET SDK and DUSK installed; pass `-p:DuskDir=...` if it isn't in the default Steam
   location):

   ```
   dotnet build DuskRando/DuskRando.csproj -c Release
   ```

   A Release build writes `dist/DuskRando-v<Version>.zip` with the three DLLs already in `BepInEx/plugins/DuskRando/`.
   The version comes from `<Version>` in `DuskRando/DuskRando.csproj`.
2. Package the APWorld:

   ```
   python tools/build_apworld.py
   ```

   This writes `dist/dusk.apworld`. Keep `world_version` in `apworld/dusk/archipelago.json` in step with the mod
   version.
3. Create a GitHub release and attach `dist/DuskRando-v<Version>.zip` and `dist/dusk.apworld`.
