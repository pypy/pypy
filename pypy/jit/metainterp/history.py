
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import we_are_translated, r_dict, Symbolic
from pypy.rlib.rarithmetic import intmask
from pypy.tool.uid import uid
from pypy.conftest import option

from pypy.jit.metainterp.resoperation import ResOperation, rop

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('compiler')
py.log.setconsumer('compiler', ansi_log)

# ____________________________________________________________

def getkind(TYPE):
    if TYPE is lltype.Void:
        return "void"
    elif isinstance(TYPE, lltype.Primitive):
        return "int"
    elif isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'raw':
            return "int"
        else:
            return "ptr"
    else:
        raise NotImplementedError("type %s not supported" % TYPE)

def getkind_num(cpu, TYPE):
    if TYPE is lltype.Void:
        return "void"
    elif isinstance(TYPE, lltype.Primitive):
        return "_%d" % cpu.numof(TYPE)
    else:
        assert isinstance(TYPE, lltype.Ptr)
        if TYPE.TO._gckind == 'raw':
            return "_%d" % cpu.numof(TYPE)
        return "ptr"

def repr_pointer(box):
    try:
        return '*%s' % (box.value._obj.container._TYPE._name,)
    except AttributeError:
        return box.value


class AbstractValue(object):
    __slots__ = ()

    def getint(self):
        raise NotImplementedError

    def getptr_base(self):
        raise NotImplementedError

    def getptr(self, PTR):
        return lltype.cast_opaque_ptr(PTR, self.getptr_base())
    getptr._annspecialcase_ = 'specialize:arg(1)'

    def get_(self):
        raise NotImplementedError

    def clonebox(self):
        raise NotImplementedError

    def constbox(self):
        raise NotImplementedError

    def nonconstbox(self):
        raise NotImplementedError

    def getaddr(self, cpu):
        raise NotImplementedError

    def equals(self, other):
        raise NotImplementedError

class Const(AbstractValue):
    __slots__ = ()

    def _new(x, cpu):
        "NOT_RPYTHON"
        T = lltype.typeOf(x)
        kind = getkind(T)
        if kind == "int":
            if isinstance(T, lltype.Ptr):
                if not we_are_translated():
                    # cannot store integers representing casted addresses
                    # inside ConstInt() instances that are going through
                    # translation; must use the special ConstAddr instead.
                    return ConstAddr(x, cpu)
                intval = cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(x))
            else:
                intval = lltype.cast_primitive(lltype.Signed, x)
            return ConstInt(intval)
        elif kind == "ptr":
            ptrval = lltype.cast_opaque_ptr(llmemory.GCREF, x)
            return ConstPtr(ptrval)
        else:
            raise NotImplementedError(kind)
    _new._annspecialcase_ = 'specialize:argtype(0)'
    _new = staticmethod(_new)

    def constbox(self):
        return self

    def __repr__(self):
        return 'Const(%s)' % self._getrepr_()

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if isinstance(self.value, Symbolic):
            v = id(self.value)
        else:
            v = self.value
        if isinstance(other.value, Symbolic):
            v2 = id(other.value)
        else:
            v2 = other.value
        return v == v2

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if isinstance(self.value, Symbolic):
            return id(self.value)
        return self.get_()


class ConstInt(Const):
    type = 'int'

    def __init__(self, value):
        if not we_are_translated():
            if isinstance(value, int):
                value = int(value)    # bool -> int
            else:
                assert isinstance(value, Symbolic)
        self.value = value

    def clonebox(self):
        return BoxInt(self.value)

    nonconstbox = clonebox

    def getint(self):
        return self.value

    def getaddr(self, cpu):
        return cpu.cast_int_to_adr(self.value)

    def get_(self):
        return self.value

    def equals(self, other):
        return self.value == other.getint()

    def _getrepr_(self):
        return self.value

CONST_FALSE = ConstInt(0)
CONST_TRUE  = ConstInt(1)

class ConstAddr(Const):       # only for constants built before translation
    type = 'int'

    def __init__(self, adrvalue, cpu):
        "NOT_RPYTHON"
        assert not we_are_translated()
        if isinstance(lltype.typeOf(adrvalue), lltype.Ptr):
            adrvalue = llmemory.cast_ptr_to_adr(adrvalue)    # convenience
        else:
            assert lltype.typeOf(adrvalue) == llmemory.Address
        self.value = adrvalue
        self.cpu = cpu

    def clonebox(self):
        return BoxInt(self.cpu.cast_adr_to_int(self.value))

    nonconstbox = clonebox

    def getint(self):
        return self.cpu.cast_adr_to_int(self.value)

    def getaddr(self, cpu):
        return self.value

    def get_(self):
        return llmemory.cast_adr_to_int(self.value)

    def equals(self, other):
        return self.value == other.getaddr(self.cpu)

    def _getrepr_(self):
        return self.value

class ConstPtr(Const):
    type = 'ptr'

    def __init__(self, value):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.value = value

    def clonebox(self):
        return BoxPtr(self.value)

    nonconstbox = clonebox

    def getptr_base(self):
        return self.value

    def get_(self):
        return lltype.cast_ptr_to_int(self.value)

    def getaddr(self, cpu):
        return llmemory.cast_ptr_to_adr(self.value)

    def equals(self, other):
        return self.value == other.getptr_base()

    _getrepr_ = repr_pointer

class Box(AbstractValue):
    __slots__ = ()
    _extended_display = True
    _counter = 0

    @staticmethod
    def _new(x, cpu):
        "NOT_RPYTHON"
        kind = getkind(lltype.typeOf(x))
        if kind == "int":
            intval = lltype.cast_primitive(lltype.Signed, x)
            return BoxInt(intval)
        elif kind == "ptr":
            ptrval = lltype.cast_opaque_ptr(llmemory.GCREF, x)
            return BoxPtr(ptrval)
        else:
            raise NotImplementedError(kind)

    def equals(self, other):
        return self is other

    def nonconstbox(self):
        return self

    def __repr__(self):
        result = str(self)
        if self._extended_display:
            result += '(%s)' % self._getrepr_()
        return result

    def __str__(self):
        if not hasattr(self, '_str'):
            self._str = '%s%d' % (self.type[0], Box._counter)
            Box._counter += 1
        return self._str

class BoxInt(Box):
    type = 'int'

    def __init__(self, value=0):
        if not we_are_translated():
            if isinstance(value, int):
                value = int(value)    # bool -> int
            else:
                assert isinstance(value, Symbolic)
        self.value = value

    def clonebox(self):
        return BoxInt(self.value)

    def constbox(self):
        return ConstInt(self.value)

    def getint(self):
        return self.value

    def get_(self):
        return self.value

    def _getrepr_(self):
        return self.value

class BoxPtr(Box):
    type = 'ptr'

    def __init__(self, value=lltype.nullptr(llmemory.GCREF.TO)):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.value = value

    def clonebox(self):
        return BoxPtr(self.value)

    def constbox(self):
        return ConstPtr(self.value)

    def getptr_base(self):
        return self.value

    def get_(self):
        return lltype.cast_ptr_to_int(self.value)

    _getrepr_ = repr_pointer

NULLBOX = BoxPtr()

# ____________________________________________________________

# The Graph class is to store a loop or a bridge.
# Unclear if it's really useful any more; just the list of operations
# is enough in most cases.

class Graph(object):

    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.operations = []

    def get_operations(self):
        return self.operations

    def summary(self, adding_insns={}):    # for debugging
        insns = adding_insns.copy()
        for op in self.operations:
            opname = op.getopname()
            insns[opname] = insns.get(opname, 0) + 1
        return insns

    def get_display_text(self):    # for graphpage.py
        return self.name

    def show(self, in_stats=None, errmsg=None, highlightops={}):
        if in_stats is None:
            from pypy.jit.metainterp.graphpage import ResOpGraphPage
            ResOpGraphPage([self], errmsg, highlightops).display()
        else:
            h = dict.fromkeys(self.operations)
            h.update(highlightops)
            in_stats.view(errmsg=errmsg, extragraphs=[self],
                          highlightops=h)

    def copy(self):    # for testing only
        g = Graph(self.name, self.color)
        g.operations = self.operations[:]
        return g

    def check_consistency(self):     # for testing
        "NOT_RPYTHON"
        operations = self.operations
        op = operations[0]
        assert op.opnum in (rop.MERGE_POINT, rop.CATCH)
        seen = dict.fromkeys(op.args)
        for op in operations:
            for box in op.args:
                if isinstance(box, Box):
                    assert box in seen
                elif isinstance(box, Const):
                    assert op.opnum != rop.MERGE_POINT, (
                        "no Constant arguments allowed in: %s" % (op,))
            box = op.result
            if box is not None:
                assert isinstance(box, Box)
                assert box not in seen
                seen[box] = True
        assert operations[-1].opnum == rop.JUMP
        assert operations[-1].jump_target.opnum == rop.MERGE_POINT

    def __repr__(self):
        return '<%s>' % (self.name,)

# ____________________________________________________________


class Matcher(object):
    pass

class RunningMatcher(Matcher):
    def __init__(self, cpu):
        self.cpu = cpu
        self.operations = []
    def record(self, opnum, argboxes, resbox, descr=None):
        raise NotImplementedError

class History(RunningMatcher):
    def record(self, opnum, argboxes, resbox, descr=None):
        op = ResOperation(opnum, argboxes, resbox, descr)
        self.operations.append(op)
        return op

class BlackHole(RunningMatcher):
    def record(self, opnum, argboxes, resbox, descr=None):
        return None

def mp_eq(greenkey1, greenkey2):
    assert len(greenkey1) == len(greenkey2)
    for i in range(len(greenkey1)):
        g1 = greenkey1[i]
        g2 = greenkey2[i]
        if g1.get_() != g2.get_():
            return False
    return True

def mp_hash(greenkey):
    h = 0x345678
    for g in greenkey:
        h = (h ^ g.get_()) * 1000003        # XXX Boehm only
    return intmask(h)

# ____________________________________________________________


class Stats(object):
    """For tests."""

    def __init__(self):
        self.history_graph = Graph('History', '#8080ff')
        self.loops = []

    def get_all_graphs(self):
        graphs = [self.history_graph] + self.loops
        return graphs

    def check_history(self, expected=None, **check):
        insns = self.history_graph.summary()
        if expected is not None:
            expected.setdefault('catch', 1)   # it always starts with a catch
            assert insns == expected
        for insn, expected_count in check.items():
            assert insns.get(insn, 0) == expected_count
        return insns

    def check_loops(self, expected=None, **check):
        insns = {}
        for loop in self.loops:
            insns = loop.summary(adding_insns=insns)
        if expected is not None:
            assert insns == expected
        for insn, expected_count in check.items():
            assert insns.get(insn, 0) == expected_count
        return insns

    def check_consistency(self):
        "NOT_RPYTHON"
        for loop in self.loops:
            loop.check_consistency()

    def maybe_view(self):
        if option.view:
            self.view()

    def view(self, errmsg=None, extragraphs=[], highlightops={}):
        from pypy.jit.metainterp.graphpage import ResOpGraphPage
        graphs = self.get_all_graphs()
        for graph in extragraphs:
            if graph in graphs:
                graphs.remove(graph)
            graphs.append(graph)
        ResOpGraphPage(graphs, errmsg, highlightops).display()


class CrashInJIT(Exception):
    pass

# ----------------------------------------------------------------

class Options:
    def __init__(self, specialize=True, listops=False):
        self.specialize = specialize
        self.listops = listops
    def _freeze_(self):
        return True
