from pypy.rpython.l3interp import model
from pypy.rpython.memory import lladdress
from pypy.rpython.rarithmetic import r_uint
from pypy.interpreter.miscutils import InitializedClass
from pypy.rpython.lltypesystem.llmemory import fakeaddress, AddressOffset
from pypy.rpython.lltypesystem import lltype

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

class L3Nothing(L3Value):
    pass

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
    if nint == 0 and ndbl == 0 and nptr == 0:
        return L3Nothing()
    raise AssertionError("stacks corrupted")

constant_offset = AddressOffset()
constant_fakeaddress = fakeaddress(None)

class L3Frame(object):
    
    def __init__(self, graph, stack_int, stack_dbl, stack_ptr):
        self.graph = graph
        self.block = self.graph.startblock
        # XXX aaaaaaaargh!
        if self.block.constants_int is None:
            self.block.constants_int = [0]
            self.block.constants_int = None
        if self.block.constants_ptr is None:
            self.block.constants_ptr = [constant_fakeaddress]
            self.block.constants_ptr = None
        if self.block.constants_offset is None:
            self.block.constants_offset = [constant_offset]
            self.block.constants_offset = None
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
        block = self.block
        followlink1(self.stack_int, self.base_int,
                    link.targetregs_int, block.constants_int)
        followlink1(self.stack_dbl, self.base_dbl,
                    link.targetregs_dbl, block.constants_dbl)
        followlink1(self.stack_ptr, self.base_ptr,
                    link.targetregs_ptr, block.constants_ptr)
        self.block = link.target
        self.i = 0

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        "NOT_RPYTHON"
        def make_missing_handler(opname):
            def missing_handler(self):
                raise NotImplementedError('XXX missing handler for %r'%opname)
            return missing_handler
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

    def getoffset(self):
        op = self.nextop()
        assert op >= 0
        return self.block.constants_offset[op]

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

    def op_adr_return(self):
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

    def op_int_is_true(self):
        x = self.getint()
        if x:
            self.stack_int.append(1)
        else:
            self.stack_int.append(0)

    def op_getfield_int(self):
        p = self.getptr()
        o = self.getoffset()
        self.stack_int.append((p + o).signed[0])

    def op_getfield_ptr(self):
        p = self.getptr()
        o = self.getoffset()
        self.stack_ptr.append((p + o).address[0])

    def op_setfield_int(self):
        p = self.getptr()
        o = self.getoffset()
        v = self.getint()
        (p + o).signed[0] = v

    def op_getarrayitem_int(self):
        a = self.getptr()
        i = self.getint()
        items_offset = self.getoffset()
        s = self.getoffset()
        v = (a + items_offset + s * i).signed[0]
        self.stack_int.append(v)
        
    def op_flavored_malloc(self):
        self.stack_ptr.append(constant_fakeaddress)

    def op_direct_call(self):
        block = self.block
        assert block.called_graphs is not None
        graph = block.called_graphs[self.nextuop()]
        directcall1(self.stack_int, graph.nargs_int,
                    block.constants_int, self.nextop)
        directcall1(self.stack_dbl, graph.nargs_dbl,
                    block.constants_dbl, self.nextop)
        directcall1(self.stack_ptr, graph.nargs_ptr,
                    block.constants_ptr, self.nextop)
        frame = L3Frame(graph, self.stack_int, self.stack_dbl, self.stack_ptr)
        frame.execute()

    # ____________________________________________________________

class L3Return(Exception):
    pass

def followlink1(stack, stackbase, targetregs, constants):
    if targetregs is None:
        del stack[stackbase:]
    else:
        top = r_uint(len(stack))
        for op in targetregs:
            if op >= 0: newval = constants[op]
            else:       newval = stack[top + op]
            stack.append(newval)
        targetlen = len(targetregs)
        for i in range(targetlen):
            stack[stackbase + i] = stack[top + i]
        del stack[stackbase + targetlen:]
followlink1._annspecialcase_ = 'specialize:arglistitemtype0'

def directcall1(stack, nargs, constants, nextop):
    if nargs > 0:
        top = r_uint(len(stack))
        for i in range(nargs):
            op = nextop()
            if op >= 0: newval = constants[op]
            else:       newval = stack[top + op]
            stack.append(newval)
directcall1._annspecialcase_ = 'specialize:arglistitemtype0'
