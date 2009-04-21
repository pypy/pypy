
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
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

INT = 0
PTR = 1

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
    elif isinstance(TYPE, ootype.OOType):
        return "obj"
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

def repr_object(box):
    try:
        if box.value.obj._TYPE is ootype.String:
            return '(%r)' % box.value.obj._str
        return repr(box.value.obj._TYPE)
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

    def getobj(self):
        raise NotImplementedError

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

    def sort_key(self):
        raise NotImplementedError

class AbstractDescr(AbstractValue):
    def handle_fail_op(self, metainterp, fail_op):
        raise NotImplementedError
    def compile_and_attach(self, metainterp, new_loop):
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
        elif kind == "obj":
            obj = ootype.cast_to_object(x)
            return ConstObj(obj)
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
        try:
            return self.get_()
        except lltype.DelayedPointer:
            return -2      # xxx risk of changing hash...


class ConstInt(Const):
    type = INT
    _attrs_ = ('value',)

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

    sort_key = getint

CONST_FALSE = ConstInt(0)
CONST_TRUE  = ConstInt(1)

class ConstAddr(Const):       # only for constants built before translation
    type = INT
    _attrs_ = ('value', 'cpu')

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
    type = PTR
    value = lltype.nullptr(llmemory.GCREF.TO)
    _attrs_ = ('value',)

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

class ConstObj(Const):
    type = ootype.Object
    value = ootype.NULL
    _attrs_ = ('value',)

    def __init__(self, value):
        assert ootype.typeOf(value) is ootype.Object
        self.value = value

    def clonebox(self):
        return BoxObj(self.value)

    nonconstbox = clonebox

    def getobj(self):
       return self.value

    def get_(self):
        return ootype.ooidentityhash(self.value) # XXX: check me

    def getaddr(self, cpu):
        # so far this is used only when calling
        # CodeWriter.IndirectCallset.bytecode_for_address.  We don't need a
        # real addr, but just a key for the dictionary
        return self.value

    def equals(self, other):
        assert False
        #return self.value == other.getptr_base()

    _getrepr_ = repr_object

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
            if self.type == INT:
                t = 'i'
            else:
                t = 'p'
            self._str = '%s%d' % (t, Box._counter)
            Box._counter += 1
        return self._str

class BoxInt(Box):
    type = INT
    _attrs_ = ('value',)

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

    changevalue_int = __init__

class BoxPtr(Box):
    type = PTR
    _attrs_ = ('value',)

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
    changevalue_ptr = __init__

NULLBOX = BoxPtr()


class BoxObj(Box):
    type = ootype.Object
    _attrs_ = ('value',)

    def __init__(self, value=ootype.NULL):
        assert ootype.typeOf(value) is ootype.Object
        self.value = value

    def clonebox(self):
        return BoxObj(self.value)

    def constbox(self):
        return ConstObj(self.value)

    def getobj(self):
        return self.value

    def get_(self):
        return ootype.ooidentityhash(self.value) # XXX: check me

    _getrepr_ = repr_object
    changevalue_obj = __init__


# ____________________________________________________________

# The TreeLoop class contains a loop or a generalized loop, i.e. a tree
# of operations.  Each branch ends in a jump which can go either to
# the top of the same loop, or to another TreeLoop.

class Base(object):
    """Common base class for TreeLoop and History."""

class TreeLoop(Base):
    inputargs = None
    specnodes = None
    operations = None

    def __init__(self, name):
        self.name = name
        # self.inputargs = list of distinct Boxes
        # self.operations = list of ResOperations
        #   ops of the kind 'guard_xxx' contain a further list of operations,
        #   which may itself contain 'guard_xxx' and so on, making a tree.

    def _all_operations(self, omit_fails=False):
        "NOT_RPYTHON"
        result = []
        _list_all_operations(result, self.operations, omit_fails)
        return result

    def summary(self, adding_insns={}):    # for debugging
        "NOT_RPYTHON"
        insns = adding_insns.copy()
        for op in self._all_operations(omit_fails=True):
            opname = op.getopname()
            insns[opname] = insns.get(opname, 0) + 1
        return insns

    def get_operations(self):
        return self.operations

    def get_display_text(self):    # for graphpage.py
        return self.name + '\n' + repr(self.inputargs)

    def show(self, errmsg=None):
        "NOT_RPYTHON"
        from pypy.jit.metainterp.graphpage import display_loops
        display_loops([self], errmsg)

    def check_consistency(self):     # for testing
        "NOT_RPYTHON"
        for box in self.inputargs:
            assert isinstance(box, Box), "Loop.inputargs contains %r" % (box,)
        seen = dict.fromkeys(self.inputargs)
        assert len(seen) == len(self.inputargs), (
               "duplicate Box in the Loop.inputargs")
        self.check_consistency_of_branch(self.operations, seen)

    def check_consistency_of_branch(self, operations, seen):
        "NOT_RPYTHON"
        for op in operations:
            for box in op.args:
                if isinstance(box, Box):
                    assert box in seen
            assert (op.suboperations is not None) == op.is_guard()
            if op.is_guard():
                self.check_consistency_of_branch(op.suboperations, seen.copy())
            box = op.result
            if box is not None:
                assert isinstance(box, Box)
                assert box not in seen
                seen[box] = True
        assert operations[-1].is_final()
        if operations[-1].opnum == rop.JUMP:
            assert isinstance(operations[-1].jump_target, TreeLoop)

    def __repr__(self):
        return '<%s>' % (self.name,)

def _list_all_operations(result, operations, omit_fails=True):
    if omit_fails and operations[-1].opnum == rop.FAIL:
        return
    result.extend(operations)
    for op in operations:
        if op.is_guard():
            _list_all_operations(result, op.suboperations, omit_fails)

# ____________________________________________________________


class RunningMatcher(Base):
    def __init__(self, cpu):
        self.cpu = cpu
        self.inputargs = None
        self.operations = []
    def record(self, opnum, argboxes, resbox, descr=None):
        raise NotImplementedError

class History(RunningMatcher):
    extratext = ''
    def record(self, opnum, argboxes, resbox, descr=None):
        op = ResOperation(opnum, argboxes, resbox, descr)
        self.operations.append(op)
        return op

class BlackHole(RunningMatcher):
    extratext = ' (BlackHole)'
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

    compiled_count = 0
    enter_count = 0

    def __init__(self):
        self.loops = []

    def get_all_loops(self):
        return self.loops

    def check_history(self, expected=None, **check):
        insns = {}
        for op in self.history.operations:
            opname = op.getopname()
            insns[opname] = insns.get(opname, 0) + 1
        if expected is not None:
            assert insns == expected
        for insn, expected_count in check.items():
            assert insns.get(insn, 0) == expected_count
        return insns

    def check_loops(self, expected=None, **check):
        insns = {}
        for loop in self.loops:
            if getattr(loop, '_ignore_during_counting', False):
                continue
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

    def view(self, errmsg=None, extraloops=[]):
        from pypy.jit.metainterp.graphpage import display_loops
        loops = self.get_all_loops()
        for loop in extraloops:
            if loop in loops:
                loops.remove(loop)
            loops.append(loop)
        display_loops(loops, errmsg, extraloops)


class CrashInJIT(Exception):
    pass

# ----------------------------------------------------------------

class Options:
    def __init__(self, specialize=True, listops=False):
        self.specialize = specialize
        self.listops = listops
    def _freeze_(self):
        return True

# ----------------------------------------------------------------

def check_descr(x):
    """Check that 'x' is None or an instance of AbstractDescr.
    Explodes if the annotator only thinks it is an instance of AbstractValue.
    """
    if x is not None:
        assert isinstance(x, AbstractDescr)

class Entry(ExtRegistryEntry):
    _about_ = check_descr

    def compute_result_annotation(self, s_x):
        from pypy.annotation import model as annmodel
        if not annmodel.s_None.contains(s_x):
            assert isinstance(s_x, annmodel.SomeInstance)
            # the following assert fails if we somehow did not manage
            # to ensure that the 'descr' field of ResOperation is really
            # an instance of AbstractDescr, a subclass of AbstractValue.
            assert issubclass(s_x.classdef.classdesc.pyobj, AbstractDescr)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
