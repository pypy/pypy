
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
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

INT = 'i'
PTR = 'p'
OBJ = 'o'

def getkind(TYPE):
    if TYPE is lltype.Void:
        return "void"
    elif isinstance(TYPE, lltype.Primitive):
        if TYPE in (lltype.Float, lltype.SingleFloat):
            raise NotImplementedError("type %s not supported" % TYPE)
        # XXX fix this for oo...
        if rffi.sizeof(TYPE) > rffi.sizeof(lltype.Signed):
            raise NotImplementedError("type %s is too large" % TYPE)
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

def repr_pointer(box):
    from pypy.rpython.lltypesystem import rstr
    try:
        T = box.value._obj.container._normalizedcontainer(check=False)._TYPE
        if T is rstr.STR:
            return repr(box._get_str())
        return '*%s' % (T._name,)
    except AttributeError:
        return box.value

def repr_object(box):
    try:
        TYPE = box.value.obj._TYPE
        if TYPE is ootype.String:
            return '(%r)' % box.value.obj._str
        if TYPE is ootype.Class or isinstance(TYPE, ootype.StaticMethod):
            return '(%r)' % box.value.obj
        if isinstance(box.value.obj, ootype._view):
            return repr(box.value.obj._inst._TYPE)
        else:
            return repr(TYPE)
    except AttributeError:
        return box.value

class ReprRPython:
    def __init__(self):
        self.seen = {}
    def repr_rpython(self, box, typechars):
        n = self.seen.setdefault(box, len(self.seen))
        return '%s/%s%d' % (box.get_(), typechars, n)

repr_rpython = ReprRPython().repr_rpython


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

    def nonnull(self):
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

    def set_future_value(self, cpu, j):
        raise NotImplementedError

    def repr_rpython(self):
        return '%s' % self

class AbstractDescr(AbstractValue):
    __slots__ = ()

    def handle_fail_op(self, metainterp, fail_op):
        raise NotImplementedError
    def compile_and_attach(self, metainterp, new_loop):
        raise NotImplementedError

class AbstractMethDescr(AbstractDescr):
    # the base class of the result of cpu.methdescrof()
    jitcodes = None
    def setup(self, jitcodes):
        # jitcodes maps { runtimeClass -> jitcode for runtimeClass.methname }
        self.jitcodes = jitcodes
    def get_jitcode_for_class(self, oocls):
        return self.jitcodes[oocls]


class Const(AbstractValue):
    __slots__ = ()

    @staticmethod
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

    def constbox(self):
        return self

    def __repr__(self):
        return 'Const(%s)' % self._getrepr_()

    def __eq__(self, other):
        "NOT_RPYTHON"
        # Remember that you should not compare Consts with '==' in RPython.
        # Consts have no special __hash__, in order to force different Consts
        # from being considered as different keys when stored in dicts
        # (as they always are after translation).  Use a dict_equal_consts()
        # to get the other behavior (i.e. using this __eq__).
        if self.__class__ is not other.__class__:
            return False
        if isinstance(self.value, Symbolic):
            v1 = "symbolic", id(self.value)
        else:
            v1 = self.value
        if isinstance(other.value, Symbolic):
            v2 = "symbolic", id(other.value)
        else:
            v2 = other.value
        return v1 == v2

    def __ne__(self, other):
        return not (self == other)


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

    def nonnull(self):
        return self.value != 0

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.value)

    def equals(self, other):
        return self.value == other.getint()

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'ci')

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

    def nonnull(self):
        return self.value != llmemory.NULL

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.getint())

    def equals(self, other):
        return self.value == other.getaddr(self.cpu)

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'ca')

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

    def nonnull(self):
        return bool(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ptr(j, self.value)

    def equals(self, other):
        return self.value == other.getptr_base()

    _getrepr_ = repr_pointer

    def repr_rpython(self):
        return repr_rpython(self, 'cp')

    def _get_str(self):    # for debugging only
        from pypy.rpython.annlowlevel import hlstr
        from pypy.rpython.lltypesystem import rstr
        return hlstr(lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), self.value))

class ConstObj(Const):
    type = OBJ
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
        if self.value:
            return ootype.ooidentityhash(self.value) # XXX: check me
        else:
            return 0

    def nonnull(self):
        return bool(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_obj(j, self.value)

##    def getaddr(self, cpu):
##        # so far this is used only when calling
##        # CodeWriter.IndirectCallset.bytecode_for_address.  We don't need a
##        # real addr, but just a key for the dictionary
##        return self.value

    def equals(self, other):
        return self.value == other.getobj()

    _getrepr_ = repr_object

    def repr_rpython(self):
        return repr_rpython(self, 'co')

    def _get_str(self):    # for debugging only
        from pypy.rpython.annlowlevel import hlstr
        return hlstr(ootype.cast_from_object(ootype.String, self.value))

class Box(AbstractValue):
    __slots__ = ()
    _extended_display = True
    _counter = 0
    is_box = True  # hint that we want to make links in graphviz from this

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
            try:
                if self.type == INT:
                    t = 'i'
                else:
                    t = 'p'
            except AttributeError:
                t = 'b'
            self._str = '%s%d' % (t, Box._counter)
            Box._counter += 1
        return self._str

    def _get_str(self):    # for debugging only
        return self.constbox()._get_str()

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

    def getaddr(self, cpu):
        return cpu.cast_int_to_adr(self.value)

    def get_(self):
        return self.value

    def nonnull(self):
        return self.value != 0

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.value)

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'bi')

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

    def getaddr(self, cpu):
        return llmemory.cast_ptr_to_adr(self.value)

    def get_(self):
        return lltype.cast_ptr_to_int(self.value)

    def nonnull(self):
        return bool(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ptr(j, self.value)

    def repr_rpython(self):
        return repr_rpython(self, 'bp')

    _getrepr_ = repr_pointer
    changevalue_ptr = __init__

NULLBOX = BoxPtr()


class BoxObj(Box):
    type = OBJ
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
        if self.value:
            return ootype.ooidentityhash(self.value) # XXX: check me
        else:
            return 0

    def nonnull(self):
        return bool(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_obj(j, self.value)

    def repr_rpython(self):
        return repr_rpython(self, 'bo')

    _getrepr_ = repr_object
    changevalue_obj = __init__


def set_future_values(cpu, boxes):
    for j in range(len(boxes)):
        boxes[j].set_future_value(cpu, j)

# ____________________________________________________________

def dict_equal_consts():
    "NOT_RPYTHON"
    # Returns a dict in which Consts that compare as equal
    # are identified when used as keys.
    return r_dict(dc_eq, dc_hash)

def dc_eq(c1, c2):
    return c1 == c2

def dc_hash(c):
    if not isinstance(c, Const):
        return hash(c)
    if isinstance(c.value, Symbolic):
        return id(c.value)
    try:
        return c.get_()
    except lltype.DelayedPointer:
        return -2      # xxx risk of changing hash...

# ____________________________________________________________

# The TreeLoop class contains a loop or a generalized loop, i.e. a tree
# of operations.  Each branch ends in a jump which can go either to
# the top of the same loop, or to another TreeLoop; or it ends in a FAIL.

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

    def dump(self):
        # RPython-friendly
        print '%r: inputargs =' % self, self._dump_args(self.inputargs)
        for op in self.operations:
            print '\t', op.getopname(), self._dump_args(op.args), \
                  self._dump_box(op.result)

    def _dump_args(self, boxes):
        return '[' + ', '.join([self._dump_box(box) for box in boxes]) + ']'

    def _dump_box(self, box):
        if box is None:
            return 'None'
        else:
            return box.repr_rpython()

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

# ____________________________________________________________


class Stats(object):
    """For tests."""

    compiled_count = 0
    enter_count = 0

    def __init__(self):
        self.loops = []
        self.locations = []

    def get_all_loops(self):
        return self.loops

    def check_history(self, expected=None, **check):
        insns = {}
        for op in self.history.operations:
            opname = op.getopname()
            insns[opname] = insns.get(opname, 0) + 1
        if expected is not None:
            insns.pop('debug_merge_point', None)
            assert insns == expected
        for insn, expected_count in check.items():
            getattr(rop, insn.upper())  # fails if 'rop.INSN' does not exist
            found = insns.get(insn, 0)
            assert found == expected_count, (
                "found %d %r, expected %d" % (found, insn, expected_count))
        return insns

    def check_loops(self, expected=None, **check):
        insns = {}
        for loop in self.loops:
            if getattr(loop, '_ignore_during_counting', False):
                continue
            insns = loop.summary(adding_insns=insns)
        if expected is not None:
            insns.pop('debug_merge_point', None)
            assert insns == expected
        for insn, expected_count in check.items():
            getattr(rop, insn.upper())  # fails if 'rop.INSN' does not exist
            found = insns.get(insn, 0)
            assert found == expected_count, (
                "found %d %r, expected %d" % (found, insn, expected_count))
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
    def __init__(self, specialize=True, listops=False, inline=False):
        self.specialize = specialize
        self.listops = listops
        self.inline = inline
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
        # Failures here mean that 'descr' is not correctly an AbstractDescr.
        # Please don't check in disabling of this test!
        from pypy.annotation import model as annmodel
        if not annmodel.s_None.contains(s_x):
            assert isinstance(s_x, annmodel.SomeInstance)
            # the following assert fails if we somehow did not manage
            # to ensure that the 'descr' field of ResOperation is really
            # an instance of AbstractDescr, a subclass of AbstractValue.
            assert issubclass(s_x.classdef.classdesc.pyobj, AbstractDescr)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
