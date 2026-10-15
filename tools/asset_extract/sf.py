"""Minimal Unity 2018.2 SerializedFile (format 17) reader for DUSK level data.

Reads the object table and decodes the handful of engine classes we need
(GameObject, Transform, MonoBehaviour header, MonoScript) without typetrees.
"""
import struct

CLASS_GAMEOBJECT = 1
CLASS_TRANSFORM = 4
CLASS_MONOBEHAVIOUR = 114
CLASS_MONOSCRIPT = 115
CLASS_RECTTRANSFORM = 224
CLASS_BOXCOLLIDER = 65
CLASS_TAGMANAGER = 78
CLASS_BUILDSETTINGS = 141


class Reader:
    def __init__(self, data, pos=0, endian="<"):
        self.d = data
        self.p = pos
        self.e = endian

    def align(self, n=4):
        self.p = (self.p + n - 1) // n * n

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def _f(self, fmt, size):
        v = struct.unpack_from(self.e + fmt, self.d, self.p)[0]
        self.p += size
        return v

    def i16(self): return self._f("h", 2)
    def u16(self): return self._f("H", 2)
    def i32(self): return self._f("i", 4)
    def u32(self): return self._f("I", 4)
    def i64(self): return self._f("q", 8)
    def f32(self): return self._f("f", 4)

    def bool(self):
        return self.u8() != 0

    def cstr(self):
        end = self.d.index(b"\0", self.p)
        s = self.d[self.p:end].decode("utf-8", "replace")
        self.p = end + 1
        return s

    def string(self):
        n = self.i32()
        s = self.d[self.p:self.p + n].decode("utf-8", "replace")
        self.p += n
        self.align()
        return s

    def bytes(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def pptr(self):
        return (self.i32(), self.i64())

    def vec3(self):
        return (self.f32(), self.f32(), self.f32())

    def quat(self):
        return (self.f32(), self.f32(), self.f32(), self.f32())


class SerializedFile:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.data = fh.read()
        r = Reader(self.data, 0, ">")
        self.metadata_size = r.u32()
        self.file_size = r.u32()
        self.version = r.u32()
        self.data_offset = r.u32()
        big = r.u8()
        r.bytes(3)
        assert self.version == 17, self.version
        r.e = ">" if big else "<"
        self.unity_version = r.cstr()
        self.platform = r.i32()
        self.typetree = r.bool()
        assert not self.typetree, "typetree parsing not implemented"
        ntypes = r.i32()
        self.types = []
        for _ in range(ntypes):
            cid = r.i32()
            r.u8()  # stripped
            script_idx = r.i16()
            if cid == CLASS_MONOBEHAVIOUR or cid < 0:
                r.bytes(16)
            r.bytes(16)
            self.types.append((cid, script_idx))
        nobj = r.i32()
        self.objects = {}
        for _ in range(nobj):
            r.align()
            pid = r.i64()
            start = r.u32()
            size = r.u32()
            tidx = r.i32()
            cid, sidx = self.types[tidx]
            self.objects[pid] = (cid, self.data_offset + start, size, sidx)
        nscripts = r.i32()
        self.script_types = []
        for _ in range(nscripts):
            fi = r.i32()
            r.align()
            lid = r.i64()
            self.script_types.append((fi, lid))
        next_ = r.i32()
        self.externals = []
        for _ in range(next_):
            r.cstr()
            r.bytes(16)
            r.i32()
            self.externals.append(r.cstr())

    def reader(self, pid):
        cid, off, size, _ = self.objects[pid]
        return Reader(self.data, off, "<")

    def raw(self, pid):
        cid, off, size, _ = self.objects[pid]
        return self.data[off:off + size]

    def of_class(self, cid):
        return [p for p, o in self.objects.items() if o[0] == cid]

    # --- engine classes -------------------------------------------------
    def gameobject(self, pid):
        r = self.reader(pid)
        comps = [r.pptr() for _ in range(r.i32())]
        layer = r.u32()
        name = r.string()
        tag = r.u16()
        active = r.bool()
        return {"components": comps, "layer": layer, "name": name,
                "tag": tag, "active": active}

    def transform(self, pid):
        r = self.reader(pid)
        go = r.pptr()
        rot = r.quat()
        pos = r.vec3()
        scale = r.vec3()
        children = [r.pptr() for _ in range(r.i32())]
        father = r.pptr()
        return {"go": go, "rot": rot, "pos": pos, "scale": scale,
                "children": children, "father": father}

    def monobehaviour_header(self, pid):
        """Returns (go, enabled, script pptr, name, reader positioned at fields)."""
        r = self.reader(pid)
        go = r.pptr()
        enabled = r.u8()
        r.align()
        script = r.pptr()
        name = r.string()
        return go, enabled, script, name, r

    def monoscript(self, pid):
        r = self.reader(pid)
        name = r.string()
        r.i32()
        r.bytes(16)
        cls = r.string()
        ns = r.string()
        asm = r.string()
        return {"name": name, "class": cls, "namespace": ns, "assembly": asm}
