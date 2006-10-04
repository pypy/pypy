from pypy.translator.cli.ilgenerator import IlasmGenerator

class StackOptMixin(object):
    LOADS = set(['ldloc', 'ldarg']) # maybe ldarg.0?
    STORES = set(['stloc'])
    
    def __init__(self, *args):
        self.super = super(StackOptMixin, self)
        self.super.__init__(*args)
        self._reset()

    def _reset(self):
        self.pending_ops = []
        self.mapping = {} # varname --> (opcode, args) needed to load it

    def opcode(self, op, *args):
        self.pending_ops.append((op, args))

    def writeline(self, s=''):
        self.pending_ops.append(('SUPER', ('writeline', s)))

    def write(self, s, indent=0):
        self.pending_ops.append(('SUPER', ('write', s, indent)))

    def openblock(self):
        self.pending_ops.append(('SUPER', ('openblock',)))

    def closeblock(self):
        self.pending_ops.append(('SUPER', ('closeblock',)))

    def _optimize(self):
        assign_count = {}
        read_count = {}
        for op, args in self.pending_ops:
            if op in self.STORES:
                varname, = args
                assign_count[varname] = assign_count.get(varname, 0) + 1
            elif op in self.LOADS:
                varname, = args
                read_count[varname] = read_count.get(varname, 0) + 1

        prev_op, prev_args = None, None
        for i, (op, args) in enumerate(self.pending_ops):
            if op in self.STORES and prev_op in self.LOADS:
                # ldloc x, stloc x0 --> remove both, map x0 to x
                varname, = args
                if assign_count[varname] == 1:
                    self.mapping[varname] = self.mapping.get(prev_args[0], (prev_op, prev_args))
                    self.pending_ops[i-1] = None
                    self.pending_ops[i] = None
                    op, args = None, None # to prevent the next opcode thinking the previous was a store
            elif op in self.LOADS:
                if prev_op in self.STORES and args == prev_args and read_count[args[0]] == 1:
                    # stloc x, ldloc x --> remove both
                    self.pending_ops[i-1] = None
                    self.pending_ops[i] = None
                    op, args = None, None # to prevent the next opcode thinking the previous was a load
                else:
                    # ldloc x, stloc x1, ..., ldloc x1 --> ..., ldloc x
                    varname, = args
                    try:
                        self.pending_ops[i] = self.mapping[varname]
                    except KeyError:
                        pass
            prev_op, prev_args = op, args

    def flush(self):
        self._optimize()
        for item in self.pending_ops:
            if item is None:
                continue
            opcode, args = item
            if opcode == 'SUPER':
                method = args[0]
                getattr(self.super, method)(*args[1:])
            else:
                self.super.opcode(opcode, *args)
        self._reset()

class StackOptGenerator(StackOptMixin, IlasmGenerator):
    pass

