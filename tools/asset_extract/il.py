"""Tiny IL scanner: list the strings, fields and methods a game method touches.

Not a decompiler, but enough to see what e.g. MapNodeScript.Start reads and calls:

    python il.py MapNodeScript.Start MenuScript.Update
"""
import struct
import sys

from layout import Assemblies

# opcode -> operand size (bytes); tokens are 4 bytes. Two-byte opcodes are prefixed with 0xFE.
ONE = {**{op: 0 for op in range(0x00, 0x100)}}
for op in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x1F, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34,
           0x35, 0x36, 0x37, 0xDE):
    ONE[op] = 1
for op in (0x20, 0x22, 0x28, 0x29, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44,
           0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x79, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x8C, 0x8D,
           0x8F, 0xA3, 0xA4, 0xA5, 0xC2, 0xC6, 0xD0, 0xD1, 0xDD):
    ONE[op] = 4
ONE[0x21] = 8
ONE[0x23] = 8
TWO = {0x06: 4, 0x07: 4, 0x09: 2, 0x0A: 2, 0x0B: 2, 0x0C: 2, 0x0D: 2, 0x0E: 2, 0x12: 1, 0x15: 4, 0x16: 4, 0x19: 1,
       0x1C: 4, 0x1D: 0}
CALLS = {0x28: "call", 0x6F: "callvirt", 0x73: "newobj"}
FIELDS = {0x7B: "ldfld", 0x7C: "ldflda", 0x7D: "stfld", 0x7E: "ldsfld", 0x80: "stsfld"}


def token_name(pe, tok):
    table = tok >> 24
    idx = tok & 0xFFFFFF
    md = pe.net.mdtables
    try:
        if table == 0x06:
            r = md.MethodDef.rows[idx - 1]
            return f"{r.Name}"
        if table == 0x0A:
            r = md.MemberRef.rows[idx - 1]
            cls = r.Class.row
            cname = getattr(cls, "TypeName", "?")
            return f"{cname}.{r.Name}"
        if table == 0x04:
            return str(md.Field.rows[idx - 1].Name)
        if table == 0x2B:
            r = md.MethodSpec.rows[idx - 1]
            return "spec:" + token_name(pe, (0x0A if r.Method.table.name == "MemberRef" else 0x06) << 24 | r.Method.row_index)
    except Exception:
        pass
    return hex(tok)


def scan(asm, cls, method):
    pe, row = asm.typedefs[cls]
    for m in row.MethodList:
        if str(m.row.Name) != method:
            continue
        rva = m.row.Rva
        off = pe.get_offset_from_rva(rva)
        data = pe.__data__
        first = data[off]
        if first & 3 == 2:
            size = first >> 2
            code = data[off + 1: off + 1 + size]
        else:
            size = struct.unpack_from("<I", data, off + 4)[0]
            hdr = (struct.unpack_from("<H", data, off)[0] >> 12) * 4
            code = data[off + hdr: off + hdr + size]
        i = 0
        out = []
        us = pe.net.user_strings
        while i < len(code):
            op = code[i]
            i += 1
            if op == 0xFE:
                op2 = code[i]
                i += 1
                i += TWO.get(op2, 0)
                continue
            if op == 0x45:  # switch
                n = struct.unpack_from("<I", code, i)[0]
                i += 4 + 4 * n
                continue
            n = ONE.get(op, 0)
            arg = code[i:i + n]
            i += n
            if op == 0x72:
                tok = struct.unpack("<I", arg)[0]
                try:
                    out.append(("ldstr", repr(us.get(tok & 0xFFFFFF).value)))
                except Exception:
                    out.append(("ldstr", hex(tok)))
            elif op in CALLS:
                out.append((CALLS[op], token_name(pe, struct.unpack("<I", arg)[0])))
            elif op in FIELDS:
                out.append((FIELDS[op], token_name(pe, struct.unpack("<I", arg)[0])))
            elif op in (0x20,):
                out.append(("ldc.i4", struct.unpack("<i", arg)[0]))
            elif 0x16 <= op <= 0x1E:
                out.append(("ldc.i4", op - 0x16))
            elif op == 0x1F:
                out.append(("ldc.i4", struct.unpack("<b", arg)[0]))
        return out
    raise KeyError(f"{cls}.{method}")


if __name__ == "__main__":
    asm = Assemblies()
    for spec in sys.argv[1:]:
        cls, method = spec.rsplit(".", 1)
        print("==", spec)
        for op, arg in scan(asm, cls, method):
            print("  ", op, arg)
