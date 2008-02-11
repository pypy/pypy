class DumpGenerator:
    def __init__(self, il, filename='dynamicmethod.il'):
        self.il = il
        self.out = file(filename, 'w')
        self.locals = {}
        self.labels = {}

    def _fmt(self, arg):
        from System.Reflection import Emit, FieldInfo
        if isinstance(arg, Emit.LocalBuilder):
            return 'v%d' % arg.LocalIndex
        elif isinstance(arg, Emit.Label):
            return 'label%d' % self.labels[arg]
        elif isinstance(arg, FieldInfo):
            return '%s %s::%s' % (arg.FieldType.FullName, arg.DeclaringType.FullName, arg.Name)
        return repr(arg)

    def Emit(self, opcode, *args):
        arglist = ', '.join(map(self._fmt, args))
        self.out.write('    %s %s\n' % (opcode.Name, arglist))
        return self.il.Emit(opcode, *args)

    def EmitCall(self, opcode, meth, vartypes):
        assert vartypes is None
        rettype = meth.ReturnType.FullName
        clsname = meth.DeclaringType.FullName
        params = meth.GetParameters()
        types = [p.ParameterType.FullName for p in params]
        arglist = ', '.join(types)
        desc = '%s %s::%s(%s)' % (rettype, clsname, meth.Name, arglist)
        self.out.write('    %s %s\n' % (opcode.Name, desc))
        return self.il.EmitCall(opcode, meth, vartypes)

    def DeclareLocal(self, t):
        v = self.il.DeclareLocal(t)
        vname = self._fmt(v)
        self.locals[vname] = t
        return v

    def DefineLabel(self):
        lbl = self.il.DefineLabel()
        count = len(self.labels)
        self.labels[lbl] = count
        return lbl

    def MarkLabel(self, lbl):
        self.out.write('\n%s:\n' % self._fmt(lbl))
        return self.il.MarkLabel(lbl)

    def __del__(self):
        decls = ['%s %s' % (t.FullName, name) for name, t in self.locals.iteritems()]
        self.out.write('.locals init (')
        self.out.write(', '.join(decls))
        self.out.write(')\n')
