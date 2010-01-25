
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import we_are_translated, r_dict, Symbolic
from pypy.rlib.objectmodel import compute_hash, compute_unique_id
from pypy.rlib.rarithmetic import intmask
from pypy.tool.uid import uid
from pypy.conftest import option

from pypy.jit.metainterp.resoperation import ResOperation, rop

# ____________________________________________________________

INT   = 'i'
REF   = 'r'
FLOAT = 'f'
HOLE  = '_'

FAILARGS_LIMIT = 1000

def getkind(TYPE, supports_floats=True):
    if TYPE is lltype.Void:
        return "void"
    elif isinstance(TYPE, lltype.Primitive):
        if TYPE is lltype.Float and supports_floats:
            return 'float'
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
            return "ref"
    elif isinstance(TYPE, ootype.OOType):
        return "ref"
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

def repr_rpython(box, typechars):
    return '%s/%s%d' % (box._get_hash_(), typechars,
                        compute_unique_id(box))


class AbstractValue(object):
    __slots__ = ()

    def getint(self):
        raise NotImplementedError

    def getfloat(self):
        raise NotImplementedError

    def getref_base(self):
        raise NotImplementedError

    def getref(self, TYPE):
        raise NotImplementedError
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        raise NotImplementedError

    def clonebox(self):
        raise NotImplementedError

    def constbox(self):
        raise NotImplementedError

    def nonconstbox(self):
        raise NotImplementedError

    def getaddr(self, cpu):
        raise NotImplementedError

    def sort_key(self):
        raise NotImplementedError

    def set_future_value(self, cpu, j):
        raise NotImplementedError

    def nonnull(self):
        raise NotImplementedError

    def repr_rpython(self):
        return '%s' % self

    def _get_str(self):
        raise NotImplementedError

class AbstractDescr(AbstractValue):
    __slots__ = ()

    def repr_of_descr(self):
        return '%r' % (self,)

    def _clone_if_mutable(self):
        return self

class AbstractFailDescr(AbstractDescr):
    index = -1

    def handle_fail(self, metainterp_sd):
        raise NotImplementedError
    def compile_and_attach(self, metainterp, new_loop):
        raise NotImplementedError

class BasicFailDescr(AbstractFailDescr):
    def __init__(self, identifier=None):
        self.identifier = identifier      # for testing

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
        elif kind == "ref":
            return cpu.ts.new_ConstRef(x)
        elif kind == "float":
            return ConstFloat(x)
        else:
            raise NotImplementedError(kind)

    def constbox(self):
        return self

    def same_constant(self, other):
        raise NotImplementedError

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

    def _get_hash_(self):
        return self.value

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.value)

    def same_constant(self, other):
        assert isinstance(other, Const)
        return self.value == other.getint()

    def nonnull(self):
        return self.value != 0

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

    def _get_hash_(self):
        return llmemory.cast_adr_to_int(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.getint())

    def same_constant(self, other):
        assert isinstance(other, Const)
        return self.value == other.getaddr(self.cpu)

    def nonnull(self):
        return bool(self.value)

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'ca')

class ConstFloat(Const):
    type = FLOAT
    value = 0.0
    _attrs_ = ('value',)

    def __init__(self, floatval):
        assert isinstance(floatval, float)
        self.value = floatval

    def clonebox(self):
        return BoxFloat(self.value)

    nonconstbox = clonebox

    def getfloat(self):
        return self.value

    def _get_hash_(self):
        return compute_hash(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_float(j, self.getfloat())

    def same_constant(self, other):
        assert isinstance(other, ConstFloat)
        return self.value == other.value

    def nonnull(self):
        return self.value != 0.0

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'cf')

class ConstPtr(Const):
    type = REF
    value = lltype.nullptr(llmemory.GCREF.TO)
    _attrs_ = ('value',)

    def __init__(self, value):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.value = value

    def clonebox(self):
        return BoxPtr(self.value)

    nonconstbox = clonebox

    def getref_base(self):
        return self.value

    def getref(self, PTR):
        return lltype.cast_opaque_ptr(PTR, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        if self.value:
            return lltype.identityhash(self.value)
        else:
            return 0

    def getaddr(self, cpu):
        return llmemory.cast_ptr_to_adr(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ref(j, self.value)

    def same_constant(self, other):
        assert isinstance(other, ConstPtr)
        return self.value == other.value

    def nonnull(self):
        return bool(self.value)

    _getrepr_ = repr_pointer

    def repr_rpython(self):
        return repr_rpython(self, 'cp')

    def _get_str(self):    # for debugging only
        from pypy.rpython.annlowlevel import hlstr
        from pypy.rpython.lltypesystem import rstr
        return hlstr(lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), self.value))

class ConstObj(Const):
    type = REF
    value = ootype.NULL
    _attrs_ = ('value',)

    def __init__(self, value):
        assert ootype.typeOf(value) is ootype.Object
        self.value = value

    def clonebox(self):
        return BoxObj(self.value)

    nonconstbox = clonebox

    def getref_base(self):
       return self.value

    def getref(self, OBJ):
        return ootype.cast_from_object(OBJ, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        if self.value:
            return ootype.identityhash(self.value)
        else:
            return 0

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ref(j, self.value)

##    def getaddr(self, cpu):
##        # so far this is used only when calling
##        # CodeWriter.IndirectCallset.bytecode_for_address.  We don't need a
##        # real addr, but just a key for the dictionary
##        return self.value

    def same_constant(self, other):
        assert isinstance(other, ConstObj)
        return self.value == other.value

    def nonnull(self):
        return bool(self.value)

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
        elif kind == "ref":
            # XXX add ootype support?
            ptrval = lltype.cast_opaque_ptr(llmemory.GCREF, x)
            return BoxPtr(ptrval)
        elif kind == "float":
            return BoxFloat(x)
        else:
            raise NotImplementedError(kind)

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
                elif self.type == FLOAT:
                    t = 'f'
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

    def _get_hash_(self):
        return self.value

    def set_future_value(self, cpu, j):
        cpu.set_future_value_int(j, self.value)

    def nonnull(self):
        return self.value != 0

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'bi')

class BoxFloat(Box):
    type = FLOAT
    _attrs_ = ('value',)
    
    def __init__(self, floatval=0.0):
        assert isinstance(floatval, float)
        self.value = floatval

    def clonebox(self):
        return BoxFloat(self.value)

    def constbox(self):
        return ConstFloat(self.value)

    def getfloat(self):
        return self.value

    def _get_hash_(self):
        return compute_hash(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_float(j, self.value)

    def nonnull(self):
        return self.value != 0.0

    def _getrepr_(self):
        return self.value

    def repr_rpython(self):
        return repr_rpython(self, 'bf')

class BoxPtr(Box):
    type = REF
    _attrs_ = ('value',)

    def __init__(self, value=lltype.nullptr(llmemory.GCREF.TO)):
        assert lltype.typeOf(value) == llmemory.GCREF
        self.value = value

    def clonebox(self):
        return BoxPtr(self.value)

    def constbox(self):
        return ConstPtr(self.value)

    def getref_base(self):
        return self.value

    def getref(self, PTR):
        return lltype.cast_opaque_ptr(PTR, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def getaddr(self, cpu):
        return llmemory.cast_ptr_to_adr(self.value)

    def _get_hash_(self):
        if self.value:
            return lltype.identityhash(self.value)
        else:
            return 0

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ref(j, self.value)

    def nonnull(self):
        return bool(self.value)

    def repr_rpython(self):
        return repr_rpython(self, 'bp')

    _getrepr_ = repr_pointer

NULLBOX = BoxPtr()


class BoxObj(Box):
    type = REF
    _attrs_ = ('value',)

    def __init__(self, value=ootype.NULL):
        assert ootype.typeOf(value) is ootype.Object
        self.value = value

    def clonebox(self):
        return BoxObj(self.value)

    def constbox(self):
        return ConstObj(self.value)

    def getref_base(self):
        return self.value

    def getref(self, OBJ):
        return ootype.cast_from_object(OBJ, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def _get_hash_(self):
        if self.value:
            return ootype.identityhash(self.value)
        else:
            return 0

    def nonnull(self):
        return bool(self.value)

    def set_future_value(self, cpu, j):
        cpu.set_future_value_ref(j, self.value)

    def repr_rpython(self):
        return repr_rpython(self, 'bo')

    _getrepr_ = repr_object


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
    "NOT_RPYTHON"
    # This is called during translation only.  Avoid using identityhash(),
    # to avoid forcing a hash, at least on lltype objects.
    if not isinstance(c, Const):
        return hash(c)
    if isinstance(c.value, Symbolic):
        return id(c.value)
    try:
        if isinstance(c, ConstPtr):
            p = lltype.normalizeptr(c.value)
            if p is not None:
                return hash(p._obj)
            else:
                return 0
        return c._get_hash_()
    except lltype.DelayedPointer:
        return -2      # xxx risk of changing hash...

# ____________________________________________________________

# The TreeLoop class contains a loop or a generalized loop, i.e. a tree
# of operations.  Each branch ends in a jump which can go either to
# the top of the same loop, or to another TreeLoop; or it ends in a FINISH.

class LoopToken(AbstractDescr):
    """Used for rop.JUMP, giving the target of the jump.
    This is different from TreeLoop: the TreeLoop class contains the
    whole loop, including 'operations', and goes away after the loop
    was compiled; but the LoopDescr remains alive and points to the
    generated assembler.
    """
    terminating = False # see TerminatingLoopToken in compile.py
    # specnodes = ...
    # and more data specified by the backend when the loop is compiled

    def __init__(self, number=0):
        self.number = number

    def repr_of_descr(self):
        return '<Loop%d>' % self.number

class TreeLoop(object):
    inputargs = None
    operations = None
    token = None

    def __init__(self, name):
        self.name = name
        # self.inputargs = list of distinct Boxes
        # self.operations = list of ResOperations
        #   ops of the kind 'guard_xxx' contain a further list of operations,
        #   which may itself contain 'guard_xxx' and so on, making a tree.

    def _all_operations(self, omit_finish=False):
        "NOT_RPYTHON"
        result = []
        _list_all_operations(result, self.operations, omit_finish)
        return result

    def summary(self, adding_insns={}):    # for debugging
        "NOT_RPYTHON"
        insns = adding_insns.copy()
        for op in self._all_operations(omit_finish=True):
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
        self.check_consistency_of(self.inputargs, self.operations)

    @staticmethod
    def check_consistency_of(inputargs, operations):
        for box in inputargs:
            assert isinstance(box, Box), "Loop.inputargs contains %r" % (box,)
        seen = dict.fromkeys(inputargs)
        assert len(seen) == len(inputargs), (
               "duplicate Box in the Loop.inputargs")
        TreeLoop.check_consistency_of_branch(operations, seen)
        
    @staticmethod
    def check_consistency_of_branch(operations, seen):
        "NOT_RPYTHON"
        for op in operations:
            for box in op.args:
                if isinstance(box, Box):
                    assert box in seen
            if op.is_guard():
                assert op.descr is not None
                if hasattr(op.descr, '_debug_suboperations'):
                    ops = op.descr._debug_suboperations
                    TreeLoop.check_consistency_of_branch(ops, seen.copy())
                for box in op.fail_args or []:
                    if box is not None:
                        assert isinstance(box, Box)
                        assert box in seen
            else:
                assert op.fail_args is None
            box = op.result
            if box is not None:
                assert isinstance(box, Box)
                assert box not in seen
                seen[box] = True
        assert operations[-1].is_final()
        if operations[-1].opnum == rop.JUMP:
            target = operations[-1].descr
            if target is not None:
                assert isinstance(target, LoopToken)

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

def _list_all_operations(result, operations, omit_finish=True):
    if omit_finish and operations[-1].opnum == rop.FINISH:
        # xxx obscure
        return
    result.extend(operations)
    for op in operations:
        if op.is_guard() and op.descr:
            if hasattr(op.descr, '_debug_suboperations'):
                ops = op.descr._debug_suboperations
                _list_all_operations(result, ops, omit_finish)

# ____________________________________________________________


class History(object):
    def __init__(self):
        self.inputargs = None
        self.operations = []

    def record(self, opnum, argboxes, resbox, descr=None):
        op = ResOperation(opnum, argboxes, resbox, descr)
        self.operations.append(op)
        return op

    def substitute_operation(self, position, opnum, argboxes, descr=None):
        resbox = self.operations[position].result
        op = ResOperation(opnum, argboxes, resbox, descr)
        self.operations[position] = op

    def slice_history_at(self, position):
        """ a strange function that does this:
        history : operation_at_position : rest
        it'll kill operation_at_position, store everything before that
        in history.operations and return rest
        """
        rest = self.operations[position + 1:]
        del self.operations[position:]
        return rest

# ____________________________________________________________


class NoStats(object):

    def set_history(self, history):
        pass

    def aborted(self):
        pass

    def entered(self):
        pass

    def compiled(self):
        pass

    def add_merge_point_location(self, loc):
        pass

    def name_for_new_loop(self):
        return 'Loop'

    def add_new_loop(self, loop):
        pass

    def view(self, **kwds):
        pass

class Stats(object):
    """For tests."""

    compiled_count = 0
    enter_count = 0
    aborted_count = 0

    def __init__(self):
        self.loops = []
        self.locations = []

    def set_history(self, history):
        self.history = history

    def aborted(self):
        self.aborted_count += 1

    def entered(self):
        self.enter_count += 1        

    def compiled(self):
        self.compiled_count += 1

    def add_merge_point_location(self, loc):
        self.locations.append(loc)

    def name_for_new_loop(self):
        return 'Loop #%d' % len(self.loops)

    def add_new_loop(self, loop):
        self.loops.append(loop)
        
    # test read interface

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
        loops = self.get_all_loops()[:]
        for loop in extraloops:
            if loop in loops:
                loops.remove(loop)
            loops.append(loop)
        display_loops(loops, errmsg, extraloops)

# ----------------------------------------------------------------

class Options:
    def __init__(self, listops=False, failargs_limit=FAILARGS_LIMIT):
        self.listops = listops
        self.failargs_limit = failargs_limit
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
