from pypy.translator.cli.ilgenerator import IlasmGenerator

class StackOptMixin(object):
    def __init__(self, *args):
        self.super = super(StackOptMixin, self)
        self.super.__init__(*args)
        self._reset()

    def _reset(self):
        self.pending_ops = []

    def opcode(self, op, *args):
        self.pending_ops.append((op, args))

    def writeline(self, s=''):
        self.pending_ops.append(('WRITELINE', (s,)))

    def write(self, s, indent=0):
        self.pending_ops.append(('WRITE', (s, indent)))

    def _optimize(self):
        pass

    def do_load(self, vartype, var):
        if vartype == 'local':
            self.super.load_local(var)
        elif vartype == 'arg':
            self.super.load_arg(var)
        elif vartype == 'self':
            assert var is None
            self.super.load_self()
        else:
            assert False

    def do_store(self, vartype, var):
        assert vartype == 'local'
        self.super.store_local(var)

    def do_opcode(self, opcode, *args):
        self.super.opcode(opcode, *args)

    def flush(self):
        self._optimize()
        for opcode, args in self.pending_ops:
            if opcode == 'WRITELINE':
                self.super.writeline(*args)
            elif opcode == 'WRITE':
                self.super.write(*args)
            else:
                self.super.opcode(opcode, *args)
        self._reset()

class StackOptGenerator(StackOptMixin, IlasmGenerator):
    pass

