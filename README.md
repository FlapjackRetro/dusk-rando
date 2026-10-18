This is a randomizer for the video game Dusk (https://store.steampowered.com/app/519860/DUSK/) by David Szymanski,
built for Archipelago (https://archipelago.gg).

Initially this is item randomization, with access to levels and keys reworked to match other boomer shooters on
Archipelago (DOOM and Duke Nukem): levels are unlocked by items, and each level's keys are items too.

**Installing / playing:** see the [Setup Guide](docs/setup.md). The mod and APWorld are on the
[Releases page](https://github.com/FlapjackRetro/dusk-rando/releases). macOS and Linux (including Steam Deck) have their own
set of instructions in the Setup Guide.

## Layout

| Path | What it is |
|---|---|
| `apworld/dusk/` | The Archipelago world (Python). Package it with `python tools/build_apworld.py`. |
| `apworld/dusk/data/locations.json` | Every location with a stable ID, generated from the game's level files. Shared by the APWorld and the mod. |
| `DuskRando/` | The BepInEx 5 game mod (C#): sends checks, receives items, gates levels. |
| `docs/setup.md` | Player setup guide: BepInEx, the mod zip, the APWorld. |
| `docs/ITEMS.md` | Item/location reference: categories, counts per level, oddities. |
| `docs/LOCATIONS.csv` | All 3,216 locations with names, IDs, objects and positions. |
| `data/raw_pickups.json` | Raw dump of every pickup in every scene. |
| `tools/asset_extract/` | Reads the Unity level files to produce `raw_pickups.json`. |
| `tools/gen_data.py` | Turns the raw dump into `locations.json`, `LOCATIONS.csv` and `ITEMS.md`. |

## Building the mod

Requires the .NET SDK. NuGet pulls in BepInEx and Archipelago.MultiClient.Net; the game's own DLLs are referenced
from the Steam install (override with `-p:DuskDir=...`).

```
dotnet build DuskRando/DuskRando.csproj -c Release
python tools/build_apworld.py
```

The Release build writes `dist/DuskRando-v<version>.zip` (the three DLLs in `BepInEx/plugins/DuskRando/`) and the
second command writes `dist/dusk.apworld`; those two files are what goes on the Releases page. See
[docs/setup.md](docs/setup.md#for-maintainers-building-a-release) for the release checklist.

## TODO

 - [x] Document all items in Dusk that need to be randomized: `docs/ITEMS.md`. Pickups are grouped into toggleable
   categories (weapons, keys, powerups, secrets, treasure chests, health, morale, ammo), plus a "Level Complete"
   check per level.
 - [x] Randomize items with logic that prevents softlocks: the APWorld (`apworld/dusk`). Generates and passes
   Archipelago's world tests.
   - [ ] Replace *strict* key logic (every check in a keyed level needs all of its keys) with per-location key rules in `apworld/dusk/key_logic.py`, level by level. Done: E2M1. Partly: E1M5, E1M6, E1M8, E2M4, E2M7, E3M1, E3M2.
   - [ ] Tune combat logic (minimum firearms per level) from playtesting.
 - [x] Intercept the game's vanilla item handler and hand out Archipelago items instead: written (Harmony patch on
   `PlayerPickupScript.TryPickupItem`, secrets, chests, item granting) and tested in game.
 - [x] Unlock levels in an arbitrary order: written (`<level> Access` items; `SceneManager` and map-screen patches)
   and tested in game.
 - [ ] Check in game: what DUSK's save/quickload does with collected pickups, and which scenes count as "level
   complete" (currently: moving from a level to `WinLevelScene` / `TextScene*` / `EndStoryScene` / `CreditsScene`).
 - [x] BONUS: update models of randomized items on scene load (#4): DUSK items take their DUSK model (learned from
   levels as you visit them), other games' items show a grey / colour / arrow Archipelago logo. Written but need tweaking.
