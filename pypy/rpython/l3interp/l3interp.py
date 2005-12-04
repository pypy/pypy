from pypy.rpython.l3interp import model
from pypy.rpython.memory import lladdress
from pypy.rpython.rarithmetic import r_uint
from pypy.interpreter.miscutils import InitializedClass

class L3Exception(Exception):
    pass


class L3Value(object):
    pass

class L3Integer(L3Value):
    def __init__(self, intval):
        self.intval = intval

class L3Double(L3Value):
    def __init__(self, dblval):
        self.dblval = dblval

class L3Pointer(L3Value):
    def __init__(self, ptrval):
        self.ptrval = ptrval


def l3interpret(graph, args_int, args_dbl, args_ptr):
    assert len(args_int) == graph.nargs_int
    assert len(args_dbl) == graph.nargs_dbl
    assert len(args_ptr) == graph.nargs_ptr
    frame = L3Frame(graph, args_int, args_dbl, args_ptr)
    frame.execute()
    nint = len(args_int) - graph.nargs_int
    ndbl = len(args_dbl) - graph.nargs_dbl
    nptr = len(args_ptr) - graph.nargs_ptr
    if nint == 1 and ndbl == 0 and nptr == 0:
        return L3Integer(args_int.pop())
    if nint == 0 and ndbl == 1 and nptr == 0:
        return L3Double(args_dbl.pop())
    if nint == 0 and ndbl == 0 and nptr == 1:
        return L3Pointer(args_ptr.pop())
    raise AssertionError("stacks corrupted")

class L3Frame(object):
    
    def __init__(self, graph, stack_int, stack_dbl, stack_ptr):
        self.graph = graph
        self.block = self.graph.startblock
        self.i = 0
        self.stack_int = stack_int
        self.stack_dbl = stack_dbl
        self.stack_ptr = stack_ptr
        self.base_int = len(stack_int)
        self.base_dbl = len(stack_dbl)
        self.base_ptr = len(stack_ptr)

    def nextop(self):
        i = self.i
        self.i = i+1
        return self.block.insns[i]

    def nextuop(self):
        return r_uint(self.nextop())

    def execute(self):
        try:
            while True:
                op = self.nextuop()
                ophandler = L3Frame.dispatch_table[op]
                ophandler(self)
        except L3Return:
            pass

    def followlink(self, link):
        assert isinstance(link, model.Link)
        if link.targetregs_int is None:
            del self.stack_int[self.base_int:]
        else:
            buf = [0] * len(link.targetregs_int)
            for i in range(len(link.targetregs_int)):
                op = link.targetregs_int[i]
                if op >= 0: buf[i] = self.block.constants_int[op]
                else:       buf[i] = self.stack_int[op]
            del self.stack_int[self.base_int:]
            self.stack_int.extend(buf)
        if link.targetregs_dbl is None:
            del self.stack_dbl[self.base_dbl:]
        else:
            buf = [0.0] * len(link.targetregs_dbl)
            for i in range(len(link.targetregs_dbl)):
                op = link.targetregs_dbl[i]
                if op >= 0: buf[i] = self.block.constants_dbl[op]
                else:       buf[i] = self.stack_dbl[op]
            del self.stack_dbl[self.base_dbl:]
            self.stack_dbl.extend(buf)
        if link.targetregs_ptr is None:
            del self.stack_ptr[self.base_ptr:]
        else:
            buf = [lladdress.NULL] * len(link.targetregs_ptr)
            for i in range(len(link.targetregs_ptr)):
                op = link.targetregs_ptr[i]
                if op >= 0: buf[i] = self.block.constants_ptr[op]
                else:       buf[i] = self.stack_ptr[op]
            del self.stack_ptr[self.base_ptr:]
            self.stack_ptr.extend(buf)
        self.block = link.target
        self.i = 0

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        "NOT_RPYTHON"
        def make_missing_handler(opname):
            def missing_handler(self):
                print 'XXX missing handler for operation', opname
                raise NotImplementedError
        cls.dispatch_table = []
        for opname in model.very_low_level_ops:
            try:
                fn = getattr(cls, 'op_' + opname).im_func
            except AttributeError:
                fn = make_missing_handler(opname)
            cls.dispatch_table.append(fn)

    # ____________________________________________________________

    def getint(self):
        op = self.nextop()
        if op >= 0: return self.block.constants_int[op]
        else:       return self.stack_int[op]

    def getdbl(self):
        op = self.nextop()
        if op >= 0: return self.block.constants_dbl[op]
        else:       return self.stack_dbl[op]

    def getptr(self):
        op = self.nextop()
        if op >= 0: return self.block.constants_ptr[op]
        else:       return self.stack_ptr[op]

    def restorestacks(self):
        del self.stack_int[self.base_int:]
        del self.stack_dbl[self.base_dbl:]
        del self.stack_ptr[self.base_ptr:]

    def op_void_return(self):
        self.restorestacks()
        raise L3Return

    def op_int_return(self):
        x = self.getint()
        self.restorestacks()
        self.stack_int.append(x)
        raise L3Return

    def op_dbl_return(self):
        x = self.getdbl()
        self.restorestacks()
        self.stack_dbl.append(x)
        raise L3Return

    def op_ptr_return(self):
        x = self.getptr()
        self.restorestacks()
        self.stack_ptr.append(x)
        raise L3Return

    def op_jump(self):
        self.followlink(self.block.exit0)

    def op_jump_cond(self):
        x = self.getint()
        if x:
            link = self.block.exit1
        else:
            link = self.block.exit0
        self.followlink(link)

    def op_int_add(self):
        x = self.getint()
        y = self.getint()
        self.stack_int.append(x + y)

    def op_direct_call(self):
        assert self.block.called_graphs is not None
        graph = self.block.called_graphs[self.nextuop()]
        if graph.nargs_int:
            buf = [0] * graph.nargs_int
            for i in range(graph.nargs_int):
                buf[i] = self.getint()
            self.stack_int.extend(buf)
        if graph.nargs_dbl:
            buf = [0.0] * graph.nargs_dbl
            for i in range(graph.nargs_dbl):
                buf[i] = self.getdbl()
            self.stack_dbl.extend(buf)
        if graph.nargs_ptr:
            buf = [lladdress.NULL] * graph.nargs_ptr
            for i in range(graph.nargs_ptr):
                buf[i] = self.getptr()
            self.stack_ptr.extend(buf)
        frame = L3Frame(graph, self.stack_int, self.stack_dbl, self.stack_ptr)
        frame.execute()

    # ____________________________________________________________

class L3Return(Exception):
    pass
