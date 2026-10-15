"""Package apworld/dusk into dist/dusk.apworld (a zip whose root folder is `dusk/`).

    python tools/build_apworld.py
Then copy dist/dusk.apworld into <Archipelago>/custom_worlds/.
"""
import json
import os
import zipfile

# Archipelago's APWorldContainer format version. A packaged .apworld's archipelago.json must carry
# "version" and "compatible_version" (normally added by the Launcher's "Build APWorlds"); without them
# Archipelago 0.6.x logs "Invalid or missing manifest" and 0.7.0 refuses to load the world.
CONTAINER_VERSION = 7

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "apworld", "dusk")
DIST = os.path.join(ROOT, "dist")

os.makedirs(DIST, exist_ok=True)
out = os.path.join(DIST, "dusk.apworld")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for folder, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            full = os.path.join(folder, f)
            rel = os.path.relpath(full, SRC)
            if rel == "archipelago.json":
                continue  # written below with the packaging fields added
            z.write(full, os.path.join("dusk", rel))
    with open(os.path.join(SRC, "archipelago.json")) as fh:
        manifest = json.load(fh)
    manifest.update({"version": CONTAINER_VERSION, "compatible_version": CONTAINER_VERSION})
    z.writestr("dusk/archipelago.json", json.dumps(manifest, indent=4))
print("wrote", out)
