import sys, json, os
from collections import Counter, defaultdict
from sf import *
from layout import DUSK_DATA

D = os.path.join(DUSK_DATA, "")
g = SerializedFile(D + "globalgamemanagers")
r = g.reader(g.of_class(CLASS_TAGMANAGER)[0])
TAGS = {20000 + i: t for i, t in enumerate(r.string() for _ in range(r.i32()))}
TAGS.update({0: "Untagged", 1: "Respawn", 2: "Finish", 3: "EditorOnly", 5: "MainCamera", 6: "Player", 7: "GameController"})
r = g.reader(g.of_class(CLASS_BUILDSETTINGS)[0])
SCENES = [r.string().split("/")[-1][:-6] for _ in range(r.i32())]

GA = SerializedFile(D + "globalgamemanagers.assets")
SCRIPTS = {pid: GA.monoscript(pid) for pid in GA.of_class(CLASS_MONOSCRIPT)}


def script_class(sf, pptr):
    fi, pid = pptr
    if fi == 0 or sf.externals[fi - 1] != "globalgamemanagers.assets":
        return None
    s = SCRIPTS.get(pid)
    return s and s["class"]


class Level:
    def __init__(self, idx):
        self.idx = idx
        self.scene = SCENES[idx]
        self.sf = sf = SerializedFile(D + f"level{idx}")
        self.go = {p: sf.gameobject(p) for p in sf.of_class(CLASS_GAMEOBJECT)}
        self.tr = {}
        for cid in (CLASS_TRANSFORM, CLASS_RECTTRANSFORM):
            for p in sf.of_class(cid):
                self.tr[p] = sf.transform(p)
        self.go_tr = {t["go"][1]: p for p, t in self.tr.items()}
        self.mb = {}
        self.go_scripts = defaultdict(list)
        for p in sf.of_class(CLASS_MONOBEHAVIOUR):
            go, en, script, name, rd = sf.monobehaviour_header(p)
            cls = script_class(sf, script)
            self.mb[p] = (go[1], en, cls, rd.p)
            self.go_scripts[go[1]].append((cls, p))

    def path(self, gopid):
        names = []
        t = self.go_tr.get(gopid)
        while t:
            tt = self.tr[t]
            names.append(self.go[tt["go"][1]]["name"])
            t = tt["father"][1] or None
        return "/".join(reversed(names))

    def active_in_hierarchy(self, gopid):
        t = self.go_tr.get(gopid)
        while t:
            tt = self.tr[t]
            if not self.go[tt["go"][1]]["active"]:
                return False
            t = tt["father"][1] or None
        return True

    def world_pos(self, gopid):
        import numpy as np
        t = self.go_tr.get(gopid)
        chain = []
        while t:
            chain.append(self.tr[t])
            t = self.tr[t]["father"][1] or None
        p = np.zeros(3)
        for tt in chain:  # leaf to root
            p = p * np.array(tt["scale"])
            x, y, z, w = tt["rot"]
            q = np.array([x, y, z])
            p = p + 2 * np.cross(q, np.cross(q, p) + w * p)
            p = p + np.array(tt["pos"])
        return tuple(round(float(v), 3) for v in p)


if __name__ == "__main__":
    total = Counter()
    for i in range(len(SCENES)):
        L = Level(i)
        c = Counter(TAGS.get(g["tag"], g["tag"]) for g in L.go.values())
        c = {k: v for k, v in c.items() if k not in ("Untagged",)}
        print(i, L.scene, c)
