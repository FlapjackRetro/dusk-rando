# Asset extraction

Reads DUSK's Unity scene files directly (no Unity editor, AssetStudio or decompiler needed) and dumps every
pickup, secret, treasure chest, level-exit button and item spawner to `data/raw_pickups.json`.

- `sf.py`: minimal reader for Unity 2018.2 SerializedFile (format 17) without type trees: GameObject, Transform,
  MonoBehaviour headers, MonoScript.
- `layout.py`: works out each MonoBehaviour's serialized field layout from `Assembly-CSharp.dll` metadata (via
  `dnfile`) so script fields such as `WeaponPickupScript.weaponcontent` can be decoded.
- `survey.py`: loads tags/scene list from `globalgamemanagers` and gives a `Level` helper (hierarchy paths,
  world positions).
- `extract.py`: writes the JSON.
- `members.py`: prints fields/methods of game classes, handy when writing Harmony patches
  (`python members.py SelectionScript PlayerPickupScript`).

```
pip install dnfile numpy
set DUSK_DATA=C:\Program Files (x86)\Steam\steamapps\common\Dusk\Dusk_Data
python extract.py ..\..\data\raw_pickups.json
python ..\gen_data.py
```

`gen_data.py` keeps existing location IDs stable, so re-running it after a game update is safe.
