"""Package apworld/dusk into dist/dusk.apworld (a zip whose root folder is `dusk/`).

    python tools/build_apworld.py
Then copy dist/dusk.apworld into <Archipelago>/custom_worlds/.
"""
import os
import zipfile

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
            z.write(full, os.path.join("dusk", os.path.relpath(full, SRC)))
print("wrote", out)
