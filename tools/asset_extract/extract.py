"""Extract every item pickup / secret / level-exit from DUSK level scenes into JSON.

Usage:  DUSK_DATA=<path to Dusk_Data> python extract.py raw_pickups.json

Breakable-object / enemy drops (DestructibleObjectScript.itemstospawn) are random
and are intentionally not extracted.
"""
import json, sys
from survey import *
from layout import Assemblies, FieldReader

ITEM_TAGS = {
    'Weapon Pickup', 'SuperShotgunTag', 'Health Pickup', 'HolyHealthTag', 'HolyHealthNoSoundTag',
    'SwordTag', 'WeaponEnhanceTag', 'RedKeyTag', 'BlueKeyTag', 'YellowKeyTag',
    'Weapon Speed Pickup', 'ClimbingPickupTag', 'Superhot Powerup', 'FlashlightPickupTag',
    'LavaSuitPickup', 'BackpackTag',
}
EXTRA_TAGS = {'SecretTag', 'TreasureChestTag', 'EndButtonTag'}
WANT = {'WeaponPickupScript', 'HealthPickupScript', 'SavePickupScript', 'BackpackScript',
        'TreasureChestScript', 'ButtonScript', 'ItemSpawnerScript'}

asm = Assemblies()
fr = FieldReader(asm)


def pptr_go(L, v):
    """Resolve a ('pptr', file, pid) to a scene GameObject name/path when local."""
    if not (isinstance(v, tuple) and v and v[0] == 'pptr'):
        return v
    _, fi, pid = v
    if pid == 0:
        return None
    if fi == 0:
        if pid in L.go:
            return {"scene_object": L.path(pid)}
        if pid in L.tr:
            return {"scene_object": L.path(L.tr[pid]["go"][1])}
        if pid in L.mb:
            return {"scene_object": L.path(L.mb[pid][0])}
        return {"local": pid}
    return {"external": L.sf.externals[fi - 1], "pathID": pid}


def clean(L, v):
    if isinstance(v, tuple) and v and v[0] == 'pptr':
        return pptr_go(L, v)
    if isinstance(v, dict):
        return {k: clean(L, x) for k, x in v.items()}
    if isinstance(v, list):
        return [clean(L, x) for x in v]
    return v


def main(levels):
    out = []
    for i in levels:
        L = Level(i)
        for p, g in L.go.items():
            tag = TAGS.get(g["tag"], g["tag"])
            scripts = {c: mp for c, mp in L.go_scripts[p]}
            kind = None
            if tag in ITEM_TAGS or tag in EXTRA_TAGS:
                kind = tag
            elif 'ItemSpawnerScript' in scripts:
                kind = 'ItemSpawner'
            if not kind:
                continue
            rec = {"level": i, "scene": L.scene, "tag": kind, "name": g["name"],
                   "path": L.path(p), "pathID": p, "active_self": g["active"],
                   "active": L.active_in_hierarchy(p), "pos": L.world_pos(p)}
            for c, mp in L.go_scripts[p]:
                if c in WANT:
                    _, en, _, off = L.mb[mp]
                    from sf import Reader
                    rd = Reader(L.sf.data, off)
                    rec[c] = clean(L, fr.read_mb(rd, c))
            out.append(rec)
        print(i, L.scene, len(out), file=sys.stderr)
    return out


if __name__ == "__main__":
    levels = [int(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else range(len(SCENES))
    json.dump(main(levels), open(sys.argv[1], "w"), indent=1)
