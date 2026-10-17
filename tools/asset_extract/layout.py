"""Compute Unity serialized field layouts from .NET metadata (no decompiler)."""
import sys, os, glob
import dnfile  # pip install dnfile

DUSK_DATA = os.environ.get("DUSK_DATA", r"C:\Program Files (x86)\Steam\steamapps\common\Dusk\Dusk_Data")
MANAGED = os.path.join(DUSK_DATA, "Managed", "")

E = dict(BOOLEAN=2, CHAR=3, I1=4, U1=5, I2=6, U2=7, I4=8, U4=9, I8=0xA, U8=0xB,
         R4=0xC, R8=0xD, STRING=0xE, PTR=0xF, BYREF=0x10, VALUETYPE=0x11, CLASS=0x12,
         VAR=0x13, ARRAY=0x14, GENERICINST=0x15, I=0x18, U=0x19, OBJECT=0x1C, SZARRAY=0x1D,
         MVAR=0x1E, CMOD_REQD=0x1F, CMOD_OPT=0x20)
PRIM = {2: "bool", 3: "char", 4: "i8", 5: "u8", 6: "i16", 7: "u16", 8: "i32", 9: "u32",
        0xA: "i64", 0xB: "u64", 0xC: "f32", 0xD: "f64", 0xE: "string"}

UNITY_STRUCTS = {
    "UnityEngine.Vector2": [("x", "f32"), ("y", "f32")],
    "UnityEngine.Vector3": [("x", "f32"), ("y", "f32"), ("z", "f32")],
    "UnityEngine.Vector4": [("x", "f32"), ("y", "f32"), ("z", "f32"), ("w", "f32")],
    "UnityEngine.Quaternion": [("x", "f32"), ("y", "f32"), ("z", "f32"), ("w", "f32")],
    "UnityEngine.Color": [("r", "f32"), ("g", "f32"), ("b", "f32"), ("a", "f32")],
    "UnityEngine.Color32": [("rgba", "u32")],
    "UnityEngine.Rect": [("x", "f32"), ("y", "f32"), ("w", "f32"), ("h", "f32")],
    "UnityEngine.LayerMask": [("m_Bits", "u32")],
    "UnityEngine.Bounds": [("c", ("struct", "UnityEngine.Vector3")), ("e", ("struct", "UnityEngine.Vector3"))],
    "UnityEngine.Vector2Int": [("x", "i32"), ("y", "i32")],
    "UnityEngine.Vector3Int": [("x", "i32"), ("y", "i32"), ("z", "i32")],
    "UnityEngine.RectOffset": [("m_Left", "i32"), ("m_Right", "i32"), ("m_Top", "i32"), ("m_Bottom", "i32")],
}
UNSUPPORTED = {"UnityEngine.AnimationCurve", "UnityEngine.Gradient", "UnityEngine.GUIStyle",
               "UnityEngine.Matrix4x4"}


def read_compressed(b, i):
    x = b[i]
    if x & 0x80 == 0:
        return x, i + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[i + 1], i + 2
    return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4


class Assemblies:
    def __init__(self):
        self.pes = {}
        self.typedefs = {}  # fullname -> (pe, row)
        self.def_names = {}
        for p in glob.glob(MANAGED + "*.dll"):
            try:
                pe = dnfile.dnPE(p, fast_load=False)
            except Exception:
                continue
            if not pe.net or not pe.net.mdtables or not pe.net.mdtables.TypeDef:
                continue
            name = os.path.basename(p)
            self.pes[name] = pe
            nested = {}
            if pe.net.mdtables.NestedClass:
                for n in pe.net.mdtables.NestedClass.rows:
                    nested[n.NestedClass.row_index] = n.EnclosingClass.row_index
            rows = pe.net.mdtables.TypeDef.rows
            for idx, r in enumerate(rows, 1):
                fn = self._fullname(rows, idx, nested)
                self.typedefs.setdefault(fn, (pe, r))
                self.def_names[(id(pe), id(r))] = fn
        self.cache = {}

    def _fullname(self, rows, idx, nested):
        r = rows[idx - 1]
        if idx in nested:
            return self._fullname(rows, nested[idx], nested) + "/" + str(r.TypeName)
        return (str(r.TypeNamespace) + "." if str(r.TypeNamespace) else "") + str(r.TypeName)

    @staticmethod
    def ref_fullname(row):
        # TypeDefRow or TypeRefRow
        if hasattr(row, "ResolutionScope") and row.ResolutionScope and \
                row.ResolutionScope.table and row.ResolutionScope.table.name == "TypeRef":
            return Assemblies.ref_fullname(row.ResolutionScope.row) + "/" + str(row.TypeName)
        return (str(row.TypeNamespace) + "." if str(row.TypeNamespace) else "") + str(row.TypeName)

    def resolve_coded(self, pe, tag_index):
        """TypeDefOrRef coded index from a signature blob -> fullname."""
        tbl = ["TypeDef", "TypeRef", "TypeSpec"][tag_index & 3]
        idx = tag_index >> 2
        table = getattr(pe.net.mdtables, tbl)
        row = table.rows[idx - 1]
        if tbl == "TypeSpec":
            return None
        if tbl == "TypeDef":
            # find fullname of this typedef in this pe
            return self.def_names[(id(pe), id(row))]
        return self.ref_fullname(row)

    def base_name(self, fullname):
        pe, row = self.typedefs.get(fullname, (None, None))
        if row is None or not row.Extends or not row.Extends.row:
            return None
        ext = row.Extends
        if ext.table.name == "TypeSpec":
            return "?generic"
        return self.ref_fullname(ext.row) if ext.table.name == "TypeRef" else \
            self._lookup_def(pe, ext.row)

    def _lookup_def(self, pe, row):
        return self.def_names.get((id(pe), id(row)))

    def is_unity_object(self, fullname):
        n = fullname
        for _ in range(30):
            if n == "UnityEngine.Object":
                return True
            if n is None:
                return False
            n = self.base_name(n)
        return False

    def is_enum(self, fullname):
        return self.base_name(fullname) == "System.Enum"

    def _extends_generic_unityevent(self, fullname):
        pe, row = self.typedefs[fullname]
        try:
            spec = row.Extends.row
            sig = spec.Signature.value
            # GENERICINST CLASS <typedeforref> ...
            t, _ = self.parse_type(pe, sig, 0)
            return t[0] == "generic" and t[1][1] and t[1][1].startswith("UnityEngine.Events.UnityEvent")
        except Exception:
            return False

    def is_serializable(self, fullname):
        pe, row = self.typedefs.get(fullname, (None, None))
        if row is None:
            return False
        if row.Flags.tdSerializable:
            return True
        # UnityEvent subclasses (e.g. Button.ButtonClickedEvent) are serialized even without [Serializable]
        n = fullname
        for _ in range(10):
            n = self.base_name(n)
            if n is None:
                return False
            if n == "UnityEngine.Events.UnityEventBase":
                return True
            if n == "?generic":
                return self._extends_generic_unityevent(fullname)
        return False

    def parse_type(self, pe, b, i):
        """Parse a type in a signature blob; returns (typedesc, i)."""
        et = b[i]
        i += 1
        while et in (E["CMOD_REQD"], E["CMOD_OPT"]):
            _, i = read_compressed(b, i)
            et = b[i]
            i += 1
        if et in PRIM:
            return PRIM[et], i
        if et in (E["CLASS"], E["VALUETYPE"]):
            tok, i = read_compressed(b, i)
            return ("ref", self.resolve_coded(pe, tok), et == E["VALUETYPE"]), i
        if et == E["SZARRAY"]:
            t, i = self.parse_type(pe, b, i)
            return ("array", t), i
        if et == E["GENERICINST"]:
            t, i = self.parse_type(pe, b, i)
            n, i = read_compressed(b, i)
            args = []
            for _ in range(n):
                a, i = self.parse_type(pe, b, i)
                args.append(a)
            return ("generic", t, args), i
        return ("other", et), i

    def serialized_fields(self, fullname):
        """[(name, typedesc)] in serialization order, including base classes."""
        if fullname in self.cache:
            return self.cache[fullname]
        pe, row = self.typedefs[fullname]
        out = []
        base = self.base_name(fullname)
        if base == "?generic" and self._extends_generic_unityevent(fullname):
            base = "UnityEngine.Events.UnityEventBase"  # UnityEvent<T> subclasses (EventTrigger.TriggerEvent...)
        if base and base in self.typedefs and base not in ("UnityEngine.MonoBehaviour", "System.Object"):
            out += self.serialized_fields(base)
        serfield_rows = self._serializefield_rows(pe)
        for fr in row.FieldList:
            f = fr.row
            fl = f.Flags
            if fl.fdStatic or fl.fdLiteral or fl.fdInitOnly or fl.fdNotSerialized:
                continue
            if not fl.fdPublic and id(f) not in serfield_rows:
                continue
            sig = f.Signature.value
            assert sig[0] == 6
            t, _ = self.parse_type(pe, sig, 1)
            out.append((str(f.Name), t))
        self.cache[fullname] = out
        return out

    def _serializefield_rows(self, pe):
        key = ("sf", id(pe))
        if key in self.cache:
            return self.cache[key]
        s = set()
        md = pe.net.mdtables
        # ctor MethodDef -> owning type name (for attributes defined in the same module, e.g. CoreModule)
        owner = {}
        if md.TypeDef:
            for t in md.TypeDef.rows:
                for m in t.MethodList:
                    owner[id(m.row)] = str(t.TypeName)
        ca = md.CustomAttribute
        if ca:
            for r in ca.rows:
                try:
                    if r.Parent.table.name != "Field":
                        continue
                    ctor = r.Type.row
                    if r.Type.table.name == "MethodDef":
                        cname = owner.get(id(ctor))
                    else:
                        cls = ctor.Class.row if hasattr(ctor, "Class") else None
                        cname = str(cls.TypeName) if cls is not None else None
                    if cname == "SerializeField":
                        s.add(id(r.Parent.row))
                except Exception:
                    pass
        self.cache[key] = s
        return s


class Unsupported(Exception):
    pass


class FieldReader:
    def __init__(self, asm):
        self.asm = asm

    def read(self, r, t, depth=0):
        if depth > 7:
            raise Unsupported("depth")
        if isinstance(t, str):
            if t == "bool":
                v = r.u8() != 0
                r.align()
                return v
            if t in ("u8", "i8"):
                v = r.u8()
                r.align()
                return v
            if t in ("i16", "u16", "char"):
                v = r.i16() if t == "i16" else r.u16()
                r.align()
                return v
            if t == "i32": return r.i32()
            if t == "u32": return r.u32()
            if t == "f32": return r.f32()
            if t in ("i64", "u64"): return r.i64()
            if t == "f64":
                import struct
                v = struct.unpack_from("<d", r.d, r.p)[0]
                r.p += 8
                return v
            if t == "string": return r.string()
            raise Unsupported(t)
        kind = t[0]
        if kind == "struct":
            return {n: self.read(r, ft, depth + 1) for n, ft in UNITY_STRUCTS[t[1]]}
        if kind == "array":
            n = r.i32()
            if n < 0 or n > 100000:
                raise Unsupported("bad array len %d" % n)
            return [self.read(r, t[1], depth + 1) for _ in range(n)]
        if kind == "generic":
            gt = t[1]
            if gt[0] == "ref" and gt[1] == "System.Collections.Generic.List`1":
                return self.read(r, ("array", t[2][0]), depth)
            raise Unsupported(str(t))
        if kind == "ref":
            name, isval = t[1], t[2]
            if name in UNITY_STRUCTS:
                return self.read(r, ("struct", name), depth)
            if name in UNSUPPORTED:
                raise Unsupported(name)
            if name is None:
                raise Unsupported("typespec")
            if self.asm.is_enum(name):
                return r.i32()
            if self.asm.is_unity_object(name):
                return ("pptr",) + r.pptr()
            if name in self.asm.typedefs and self.asm.is_serializable(name):
                return {n: self.read(r, ft, depth + 1) for n, ft in self.asm.serialized_fields(name)}
            if name.startswith("System."):
                raise Unsupported(name)
            if not isval and name in self.asm.typedefs:
                # non-serializable class: skipped by Unity
                return None
            raise Unsupported(name)
        raise Unsupported(str(t))

    def read_mb(self, r, cls):
        out = {}
        for n, t in self.asm.serialized_fields(cls):
            try:
                v = self.read(r, t)
            except Unsupported as ex:
                out["__stopped__"] = f"{n}: {ex}"
                break
            if v is not None:
                out[n] = v
        return out


if __name__ == "__main__":
    a = Assemblies()
    for c in sys.argv[1:]:
        print(c, a.base_name(c))
        for n, t in a.serialized_fields(c):
            print("   ", n, t)
