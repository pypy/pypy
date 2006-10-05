from pypy.translator.cli.ilgenerator import IlasmGenerator

class StackOptMixin(object):

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

    def label(self, lbl):
        self.pending_ops.append(('LABEL', (lbl,)))            

    def _varname(self, op, args):
        if op in ('ldloc', 'ldarg', 'stloc'):
            return args[0]
        elif op.startswith('ld'):
            return ('PLACEHOLDER', op, args)
        else:
            assert False, "undefined varname of %s" % op

    def _is_load(self, op):
        return op is not None and op.startswith('ld')

    def _is_simple_load(self, op):
        return op is not None and (op.startswith('ldloc') or
                                   op.startswith('ldarg') or
                                   op.startswith('ldsfld') or
                                   op.startswith('ldc'))

    def _optimize(self):
        self._collect_stats()
        self._remove_renaming()

    def _collect_stats(self):
        assign_count = {}
        read_count = {}
        for item in self.pending_ops:
            if item is None:
                continue
            op, args = item
            if op == 'stloc':
                varname, = args
                assign_count[varname] = assign_count.get(varname, 0) + 1
            elif op == 'ldloc':
                varname, = args
                read_count[varname] = read_count.get(varname, 0) + 1
        self.assign_count = assign_count
        self.read_count = read_count

    def _remove_renaming(self):
        assign_count = self.assign_count
        read_count = self.read_count
        prev_op, prev_args = None, None
        for i, (op, args) in enumerate(self.pending_ops):
            if op == 'stloc' and self._is_simple_load(prev_op):
                # ldloc x, stloc x0 --> remove both, map x0 to x
                varname, = args
                if assign_count[varname] == 1:
                    self.mapping[varname] = self.mapping.get(self._varname(prev_op, prev_args), (prev_op, prev_args))
                    self.pending_ops[i-1] = None
                    self.pending_ops[i] = None
                    op, args = None, None # to prevent the next opcode thinking the previous was a store
            elif op == 'ldloc':
                if prev_op == 'stloc' and args == prev_args and read_count[args[0]] == 1:
                    # stloc x, ldloc x --> remove both
                    self.pending_ops[i-1] = None
                    self.pending_ops[i] = None
                    op, args = None, None # to prevent the next opcode thinking the previous was a load
                else:
                    # ldloc x, stloc x1, ..., ldloc x1 --> ..., ldloc x
                    try:
                        self.pending_ops[i] = self.mapping[self._varname(op, args)]
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
            elif opcode == 'LABEL':
                self.super.label(*args)
            else:
                self.super.opcode(opcode, *args)
        self._reset()

class StackOptGenerator(StackOptMixin, IlasmGenerator):
    pass

