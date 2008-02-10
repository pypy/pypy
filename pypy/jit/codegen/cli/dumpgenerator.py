class DumpGenerator:
    def __init__(self, il, filename='dynamicmethod.il'):
        self.il = il
        self.out = file(filename, 'w')
        self.localcount = 0
        self.labels = {}

    def _fmt(self, arg):
        from System.Reflection import Emit
        if isinstance(arg, Emit.LocalBuilder):
            return 'v%d' % arg.LocalIndex
        elif isinstance(arg, Emit.Label):
            return 'label%d' % self.labels[arg]
        return repr(arg)

    def Emit(self, opcode, *args):
        arglist = ', '.join(map(self._fmt, args))
        self.out.write('    %s %s\n' % (opcode.Name, arglist))
        return self.il.Emit(opcode, *args)

    def DeclareLocal(self, t):
        return self.il.DeclareLocal(t)

    def DefineLabel(self):
        lbl = self.il.DefineLabel()
        count = len(self.labels)
        self.labels[lbl] = count
        return lbl

    def MarkLabel(self, lbl):
        self.out.write('\n%s:\n' % self._fmt(lbl))
        return self.il.MarkLabel(lbl)

