
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import we_are_translated, r_dict, ComputedIntSymbolic
from pypy.rlib.rarithmetic import intmask
from pypy.tool.uid import uid
from pypy.conftest import option

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

    def getaddr(self, cpu):
        raise NotImplementedError

    def equals(self, other):
        raise NotImplementedError

class Const(AbstractValue):
    __slots__ = ()

    def _new(x, cpu):
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
        return self.__class__ is other.__class__ and self.value == other.value

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if isinstance(self.value, ComputedIntSymbolic):
            return id(self.value)
        return self.get_()


class ConstInt(Const):
    type = 'int'

    def __init__(self, value):
        if not we_are_translated():
            assert isinstance(value, (int, ComputedIntSymbolic))
        self.value = value

    def clonebox(self):
        return BoxInt(self.value)

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

class ConstAddr(Const):       # only for constants built before translation
    type = 'int'
    ever_seen = False

    def __init__(self, adrvalue, cpu):
        "NOT_RPYTHON"
        self.__class__.ever_seen = True
        assert not we_are_translated()
        if isinstance(lltype.typeOf(adrvalue), lltype.Ptr):
            adrvalue = llmemory.cast_ptr_to_adr(adrvalue)    # convenience
        else:
            assert lltype.typeOf(adrvalue) == llmemory.Address
        self.value = adrvalue
        self.cpu = cpu

    def clonebox(self):
        return BoxInt(self.cpu.cast_adr_to_int(self.value))

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

    def getptr_base(self):
        return self.value

    def get_(self):
        return lltype.cast_ptr_to_int(self.value)

    def equals(self, other):
        return self.value == other.getptr_base()

    def _getrepr_(self):
        return self.value

class Box(AbstractValue):
    __slots__ = ()
    _extended_display = True
    _counter = 0

    @staticmethod
    def _new(x, cpu):
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

    def _getrepr_(self):
        try:
            return self.value.ptr
        except AttributeError:
            return self.value

NULLBOX = BoxPtr()

# ____________________________________________________________

# The central ResOperation class, representing one operation.
# It's a bit unoptimized; it could be improved, but on the other hand it
# is unclear how much would really be gained by doing this as they are
# mostly temporaries.

class ResOperation(object):
    jump_target = None

    def __init__(self, opname, args, results):
        self.opname = opname
        self.args = list(args)
        self.results = list(results)

    def __repr__(self):
        results = self.results
        if len(results) == 1:
            sres = repr(results[0])
        else:
            sres = repr(results)
        return '%s = %s(%s)' % (sres, self.opname,
                                ', '.join(map(repr, self.args)))

    def clone(self):
        return ResOperation(self.opname, self.args, self.results)


class MergePoint(ResOperation):
    specnodes = None
    key = None

    def __new__(cls, opname, args, results):
        assert len(dict.fromkeys(args)) == len(args)
        return ResOperation.__new__(cls, opname, args, results)

    def clone(self):
        mp = MergePoint(self.opname, self.args, self.results)
        mp.specnodes = self.specnodes
        mp.key = self.key
        return mp


class Jump(ResOperation):
    target_mp = None

    def clone(self):
        return Jump(self.opname, self.args, self.results)


class GuardOp(ResOperation):
    key = None
    counter = 0
    storage_info = None

    def clone(self):
        op = GuardOp(self.opname, self.args, self.results)
        op.key = self.key
        return op

    def __repr__(self):
        result = ResOperation.__repr__(self)
        if hasattr(self, 'liveboxes'):
            result = '%s [%s]' % (result, ', '.join(map(repr, self.liveboxes)))
        return result

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
            insns[op.opname] = insns.get(op.opname, 0) + 1
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
        assert op.opname in ('merge_point', 'catch')
        seen = dict.fromkeys(op.args)
        for op in operations[1:]:
            for box in op.args:
                if isinstance(box, Box):
                    assert box in seen
                elif isinstance(box, Const):
                    assert op.opname not in ('merge_point', 'catch'), (
                        "no Constant arguments allowed in: %s" % (op,))
            for box in op.results:
                assert box not in seen
                seen[box] = True
        assert operations[-1].opname == 'jump'
        assert operations[-1].jump_target.opname == 'merge_point'

    def get_final_target_mp(self):
        op = self.operations[-1]
        return op.jump_target

    def __repr__(self):
        return '<%s>' % (self.name,)

# ____________________________________________________________


class Matcher(object):
    pass


class RunningMatcher(Matcher):

    def __init__(self, cpu):
        self.cpu = cpu
        self.operations = []

    def execute_and_record(self, step, argboxes, result_type, pure):
        # collect arguments
        canfold = False
        if pure:
            for box in argboxes:
                if not isinstance(box, Const):
                    break
            else:
                canfold = True
        # really run this operation
        resbox = self.cpu.execute_operation(step, argboxes, result_type)
        # collect the result(s)
        if resbox is None:
            resboxes = []
        elif canfold:
            resboxes = [resbox.constbox()]
        else:
            resboxes = [resbox]
        if not canfold:
            self.record(step, argboxes, resboxes)
        return resboxes
    execute_and_record._annspecialcase_ = 'specialize:arg(3, 4)'

    def record(self, opname, argboxes, resboxes, opcls=ResOperation):
        op = opcls(opname, argboxes, resboxes)
        self.operations.append(op)
        return op

    def generate_anything_since(self, old_index):
        return len(self.operations) > old_index

class History(RunningMatcher):
    pass

class BlackHole(RunningMatcher):
    def record(self, step, argboxes, resboxes, opcls=ResOperation):
        return None

    def generate_anything_since(self, old_index):
        return True

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

# ----------------------------------------------------------------
