import sys
from layout import Assemblies
a=Assemblies()
for c in sys.argv[1:]:
    pe,row=a.typedefs[c]
    print("==",c,"base",a.base_name(c))
    print("  fields:", ", ".join(f"{'s:' if f.row.Flags.fdStatic else ''}{f.row.Name}" for f in row.FieldList))
    print("  methods:", ", ".join(str(m.row.Name) for m in row.MethodList))
