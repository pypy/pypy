from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import make_sure_not_resized

def ResOperation(opnum, args, result, descr=None):
    cls = opclasses[opnum]
    op = cls(result)
    op.initarglist(args)
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        op.setdescr(descr)
    return op


class AbstractResOp(object):
    """The central ResOperation class, representing one operation."""

    # debug
    name = ""
    pc = 0

    def __init__(self, result):
        self.result = result

    # methods implemented by each concrete class
    # ------------------------------------------

    def getopnum(self):
        raise NotImplementedError

    # methods implemented by the arity mixins
    # ---------------------------------------

    def initarglist(self, args):
        "This is supposed to be called only just after the ResOp has been created"
        raise NotImplementedError

    def getarglist(self):
        raise NotImplementedError

    def getarg(self, i):
        raise NotImplementedError

    def setarg(self, i, box):
        raise NotImplementedError

    def numargs(self):
        raise NotImplementedError


    # methods implemented by GuardResOp
    # ---------------------------------

    def getfailargs(self):
        return None

    def setfailargs(self, fail_args):
        raise NotImplementedError

    # methods implemented by ResOpWithDescr
    # -------------------------------------

    def getdescr(self):
        return None

    def setdescr(self, descr):
        raise NotImplementedError

    # common methods
    # --------------

    def copy_and_change(self, opnum, args=None, result=None, descr=None):
        "shallow copy: the returned operation is meant to be used in place of self"
        if args is None:
            args = self.getarglist()
        if result is None:
            result = self.result
        if descr is None:
            descr = self.getdescr()
        newop = ResOperation(opnum, args, result, descr)
        return newop

    def clone(self):
        args = self.getarglist()
        descr = self.getdescr()
        if descr is not None:
            descr = descr.clone_if_mutable()
        op = ResOperation(self.getopnum(), args[:], self.result, descr)
        if not we_are_translated():
            op.name = self.name
            op.pc = self.pc
        return op

    def __repr__(self):
        return self.repr()

    def repr(self, graytext=False):
        # RPython-friendly version
        if self.result is not None:
            sres = '%s = ' % (self.result,)
        else:
            sres = ''
        if self.name:
            prefix = "%s:%s   " % (self.name, self.pc)
            if graytext:
                prefix = "\f%s\f" % prefix
        else:
            prefix = ""
        args = self.getarglist()
        descr = self.getdescr()
        if descr is None or we_are_translated():
            return '%s%s%s(%s)' % (prefix, sres, self.getopname(),
                                 ', '.join([str(a) for a in args]))
        else:
            return '%s%s%s(%s, descr=%r)' % (prefix, sres, self.getopname(),
                                             ', '.join([str(a) for a in args]), descr)

    def getopname(self):
        try:
            return opname[self.getopnum()].lower()
        except KeyError:
            return '<%d>' % self.getopnum()

    def is_guard(self):
        return rop._GUARD_FIRST <= self.getopnum() <= rop._GUARD_LAST

    def is_foldable_guard(self):
        return rop._GUARD_FOLDABLE_FIRST <= self.getopnum() <= rop._GUARD_FOLDABLE_LAST

    def is_guard_exception(self):
        return (self.getopnum() == rop.GUARD_EXCEPTION or
                self.getopnum() == rop.GUARD_NO_EXCEPTION)

    def is_guard_overflow(self):
        return (self.getopnum() == rop.GUARD_OVERFLOW or
                self.getopnum() == rop.GUARD_NO_OVERFLOW)

    def is_always_pure(self):
        return rop._ALWAYS_PURE_FIRST <= self.getopnum() <= rop._ALWAYS_PURE_LAST

    def has_no_side_effect(self):
        return rop._NOSIDEEFFECT_FIRST <= self.getopnum() <= rop._NOSIDEEFFECT_LAST

    def can_raise(self):
        return rop._CANRAISE_FIRST <= self.getopnum() <= rop._CANRAISE_LAST

    def is_malloc(self):
        # a slightly different meaning from can_malloc
        return rop._MALLOC_FIRST <= self.getopnum() <= rop._MALLOC_LAST

    def can_malloc(self):
        return self.is_call() or self.is_malloc()

    def is_call(self):
        return rop._CALL_FIRST <= self.getopnum() <= rop._CALL_LAST

    def is_ovf(self):
        return rop._OVF_FIRST <= self.getopnum() <= rop._OVF_LAST

    def is_comparison(self):
        return self.is_always_pure() and self.returns_bool_result()

    def is_final(self):
        return rop._FINAL_FIRST <= self.getopnum() <= rop._FINAL_LAST

    def returns_bool_result(self):
        opnum = self.getopnum()
        if we_are_translated():
            assert opnum >= 0
        elif opnum < 0:
            return False     # for tests
        return opboolresult[opnum]


# ===================
# Top of the hierachy
# ===================

class PlainResOp(AbstractResOp):
    pass

class ResOpWithDescr(AbstractResOp):

    _descr = None

    def getdescr(self):
        return self._descr

    def setdescr(self, descr):
        # for 'call', 'new', 'getfield_gc'...: the descr is a prebuilt
        # instance provided by the backend holding details about the type
        # of the operation.  It must inherit from AbstractDescr.  The
        # backend provides it with cpu.fielddescrof(), cpu.arraydescrof(),
        # cpu.calldescrof(), and cpu.typedescrof().
        from pypy.jit.metainterp.history import check_descr
        check_descr(descr)
        self._descr = descr

class GuardResOp(ResOpWithDescr):

    _fail_args = None

    def getfailargs(self):
        return self._fail_args

    def setfailargs(self, fail_args):
        self._fail_args = fail_args

    def copy_and_change(self, opnum, args=None, result=None, descr=None):
        newop = AbstractResOp.copy_and_change(self, opnum, args, result, descr)
        newop.setfailargs(self.getfailargs())
        return newop

    def clone(self):
        newop = AbstractResOp.clone(self)
        newop.setfailargs(self.getfailargs())
        return newop


# ============
# arity mixins
# ============

class NullaryOp(object):
    _mixin_ = True

    def initarglist(self, args):
        assert len(args) == 0

    def getarglist(self):
        return []

    def numargs(self):
        return 0

    def getarg(self, i):
        raise IndexError

    def setarg(self, i, box):
        raise IndexError


class UnaryOp(object):
    _mixin_ = True
    _arg0 = None

    def initarglist(self, args):
        assert len(args) == 1
        self._arg0, = args

    def getarglist(self):
        return [self._arg0]

    def numargs(self):
        return 1

    def getarg(self, i):
        if i == 0:
            return self._arg0
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        else:
            raise IndexError


class BinaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None

    def initarglist(self, args):
        assert len(args) == 2
        self._arg0, self._arg1 = args

    def getarglist(self):
        return [self._arg0, self._arg1, self._arg2]

    def numargs(self):
        return 2

    def getarg(self, i):
        if i == 0:
            return self._arg0
        elif i == 1:
            return self._arg1
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        elif i == 1:
            self._arg1 = box
        else:
            raise IndexError

    def getarglist(self):
        return [self._arg0, self._arg1]


class TernaryOp(object):
    _mixin_ = True
    _arg0 = None
    _arg1 = None
    _arg2 = None

    def initarglist(self, args):
        assert len(args) == 3
        self._arg0, self._arg1, self._arg2 = args

    def getarglist(self):
        return [self._arg0, self._arg1, self._arg2]

    def numargs(self):
        return 3

    def getarg(self, i):
        if i == 0:
            return self._arg0
        elif i == 1:
            return self._arg1
        elif i == 2:
            return self._arg2
        else:
            raise IndexError

    def setarg(self, i, box):
        if i == 0:
            self._arg0 = box
        elif i == 1:
            self._arg1 = box
        elif i == 2:
            self._arg2 = box
        else:
            raise IndexError

class N_aryOp(object):
    _mixin_ = True
    _args = None

    def initarglist(self, args):
        self._args = args

    def getarglist(self):
        return self._args

    def numargs(self):
        return len(self._args)

    def getarg(self, i):
        return self._args[i]

    def setarg(self, i, box):
        self._args[i] = box


# ____________________________________________________________

_oplist = [
    '_FINAL_FIRST',
    'JUMP/*d',
    'FINISH/*d',
    '_FINAL_LAST',

    '_GUARD_FIRST',
    '_GUARD_FOLDABLE_FIRST',
    'GUARD_TRUE/1d',
    'GUARD_FALSE/1d',
    'GUARD_VALUE/2d',
    'GUARD_CLASS/2d',
    'GUARD_NONNULL/1d',
    'GUARD_ISNULL/1d',
    'GUARD_NONNULL_CLASS/2d',
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION/0d',
    'GUARD_EXCEPTION/1d',
    'GUARD_NO_OVERFLOW/0d',
    'GUARD_OVERFLOW/0d',
    'GUARD_NOT_FORCED/0d',
    'GUARD_NOT_INVALIDATED/0d',
    '_GUARD_LAST', # ----- end of guard operations -----

    '_NOSIDEEFFECT_FIRST', # ----- start of no_side_effect operations -----
    '_ALWAYS_PURE_FIRST', # ----- start of always_pure operations -----
    'INT_ADD/2',
    'INT_SUB/2',
    'INT_MUL/2',
    'INT_FLOORDIV/2',
    'UINT_FLOORDIV/2',
    'INT_MOD/2',
    'INT_AND/2',
    'INT_OR/2',
    'INT_XOR/2',
    'INT_RSHIFT/2',
    'INT_LSHIFT/2',
    'UINT_RSHIFT/2',
    'FLOAT_ADD/2',
    'FLOAT_SUB/2',
    'FLOAT_MUL/2',
    'FLOAT_TRUEDIV/2',
    'FLOAT_NEG/1',
    'FLOAT_ABS/1',
    'CAST_FLOAT_TO_INT/1',
    'CAST_INT_TO_FLOAT/1',
    #
    'INT_LT/2b',
    'INT_LE/2b',
    'INT_EQ/2b',
    'INT_NE/2b',
    'INT_GT/2b',
    'INT_GE/2b',
    'UINT_LT/2b',
    'UINT_LE/2b',
    'UINT_GT/2b',
    'UINT_GE/2b',
    'FLOAT_LT/2b',
    'FLOAT_LE/2b',
    'FLOAT_EQ/2b',
    'FLOAT_NE/2b',
    'FLOAT_GT/2b',
    'FLOAT_GE/2b',
    #
    'INT_IS_ZERO/1b',
    'INT_IS_TRUE/1b',
    'INT_NEG/1',
    'INT_INVERT/1',
    #
    'SAME_AS/1',      # gets a Const or a Box, turns it into another Box
    #
    'PTR_EQ/2b',
    'PTR_NE/2b',
    #
    'ARRAYLEN_GC/1d',
    'STRLEN/1',
    'STRGETITEM/2',
    'GETFIELD_GC_PURE/1d',
    'GETFIELD_RAW_PURE/1d',
    'GETARRAYITEM_GC_PURE/2d',
    'UNICODELEN/1',
    'UNICODEGETITEM/2',
    #
    # ootype operations
    #'INSTANCEOF/1db',
    #'SUBCLASSOF/2b',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d',
    'GETARRAYITEM_RAW/2d',
    'GETFIELD_GC/1d',
    'GETFIELD_RAW/1d',
    '_MALLOC_FIRST',
    'NEW/0d',
    'NEW_WITH_VTABLE/1',
    'NEW_ARRAY/1d',
    'NEWSTR/1',
    'NEWUNICODE/1',
    '_MALLOC_LAST',
    'FORCE_TOKEN/0',
    'VIRTUAL_REF/2',         # removed before it's passed to the backend
    'READ_TIMESTAMP/0',
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'SETARRAYITEM_GC/3d',
    'SETARRAYITEM_RAW/3d',
    'SETFIELD_GC/2d',
    'SETFIELD_RAW/2d',
    'STRSETITEM/3',
    'UNICODESETITEM/3',
    #'RUNTIMENEW/1',     # ootype operation
    'COND_CALL_GC_WB/2d', # [objptr, newvalue] or [arrayptr, index]
                          # (for the write barrier, latter is in an array)
    'DEBUG_MERGE_POINT/*',      # debugging only
    'JIT_DEBUG/*',              # debugging only
    'VIRTUAL_REF_FINISH/2',   # removed before it's passed to the backend
    'COPYSTRCONTENT/5',       # src, dst, srcstart, dststart, length
    'COPYUNICODECONTENT/5',
    'QUASIIMMUT_FIELD/1d',    # [objptr], descr=SlowMutateDescr

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    '_CALL_FIRST',
    'CALL/*d',
    'CALL_ASSEMBLER/*d',  # call already compiled assembler
    'CALL_MAY_FORCE/*d',
    'CALL_LOOPINVARIANT/*d',
    'CALL_RELEASE_GIL/*d',  # release the GIL and "close the stack" for asmgcc
    #'OOSEND',                     # ootype operation
    #'OOSEND_PURE',                # ootype operation
    'CALL_PURE/*d',             # removed before it's passed to the backend
    '_CALL_LAST',
    '_CANRAISE_LAST', # ----- end of can_raise operations -----

    '_OVF_FIRST', # ----- start of is_ovf operations -----
    'INT_ADD_OVF/2',
    'INT_SUB_OVF/2',
    'INT_MUL_OVF/2',
    '_OVF_LAST', # ----- end of is_ovf operations -----
    '_LAST',     # for the backend to add more internal operations
]

# ____________________________________________________________

class rop(object):
    pass

opclasses = []   # mapping numbers to the concrete ResOp class
opname = {}      # mapping numbers to the original names, for debugging
oparity = []     # mapping numbers to the arity of the operation or -1
opwithdescr = [] # mapping numbers to a flag "takes a descr"
opboolresult= [] # mapping numbers to a flag "returns a boolean"


def setup(debug_print=False):
    for i, name in enumerate(_oplist):
        if debug_print:
            print '%30s = %d' % (name, i)
        if '/' in name:
            name, arity = name.split('/')
            withdescr = 'd' in arity
            boolresult = 'b' in arity
            arity = arity.rstrip('db')
            if arity == '*':
                arity = -1
            else:
                arity = int(arity)
        else:
            arity, withdescr, boolresult = -1, True, False       # default
        setattr(rop, name, i)
        if not name.startswith('_'):
            opname[i] = name
            cls = create_class_for_op(name, i, arity, withdescr)
        else:
            cls = None
        opclasses.append(cls)
        oparity.append(arity)
        opwithdescr.append(withdescr)
        opboolresult.append(boolresult)
    assert len(opclasses)==len(oparity)==len(opwithdescr)==len(opboolresult)==len(_oplist)

def get_base_class(mixin, base):
    try:
        return get_base_class.cache[(mixin, base)]
    except KeyError:
        arity_name = mixin.__name__[:-2]  # remove the trailing "Op"
        name = arity_name + base.__name__ # something like BinaryPlainResOp
        bases = (mixin, base)
        cls = type(name, bases, {})
        get_base_class.cache[(mixin, base)] = cls
        return cls
get_base_class.cache = {}

def create_class_for_op(name, opnum, arity, withdescr):
    arity2mixin = {
        0: NullaryOp,
        1: UnaryOp,
        2: BinaryOp,
        3: TernaryOp
        }

    is_guard = name.startswith('GUARD')
    if is_guard:
        assert withdescr
        baseclass = GuardResOp
    elif withdescr:
        baseclass = ResOpWithDescr
    else:
        baseclass = PlainResOp
    mixin = arity2mixin.get(arity, N_aryOp)

    def getopnum(self):
        return opnum

    cls_name = '%s_OP' % name
    bases = (get_base_class(mixin, baseclass),)
    dic = {'getopnum': getopnum}
    return type(cls_name, bases, dic)

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist

opboolinvers = {
    rop.INT_EQ: rop.INT_NE,
    rop.INT_NE: rop.INT_EQ,
    rop.INT_LT: rop.INT_GE,
    rop.INT_GE: rop.INT_LT,
    rop.INT_GT: rop.INT_LE,
    rop.INT_LE: rop.INT_GT,

    rop.UINT_LT: rop.UINT_GE,
    rop.UINT_GE: rop.UINT_LT,
    rop.UINT_GT: rop.UINT_LE,
    rop.UINT_LE: rop.UINT_GT,

    rop.FLOAT_EQ: rop.FLOAT_NE,
    rop.FLOAT_NE: rop.FLOAT_EQ,
    rop.FLOAT_LT: rop.FLOAT_GE,
    rop.FLOAT_GE: rop.FLOAT_LT,
    rop.FLOAT_GT: rop.FLOAT_LE,
    rop.FLOAT_LE: rop.FLOAT_GT,

    rop.PTR_EQ: rop.PTR_NE,
    rop.PTR_NE: rop.PTR_EQ,
    }

opboolreflex = {
    rop.INT_EQ: rop.INT_EQ,
    rop.INT_NE: rop.INT_NE,
    rop.INT_LT: rop.INT_GT,
    rop.INT_GE: rop.INT_LE,
    rop.INT_GT: rop.INT_LT,
    rop.INT_LE: rop.INT_GE,

    rop.UINT_LT: rop.UINT_GT,
    rop.UINT_GE: rop.UINT_LE,
    rop.UINT_GT: rop.UINT_LT,
    rop.UINT_LE: rop.UINT_GE,

    rop.FLOAT_EQ: rop.FLOAT_EQ,
    rop.FLOAT_NE: rop.FLOAT_NE,
    rop.FLOAT_LT: rop.FLOAT_GT,
    rop.FLOAT_GE: rop.FLOAT_LE,
    rop.FLOAT_GT: rop.FLOAT_LT,
    rop.FLOAT_LE: rop.FLOAT_GE,

    rop.PTR_EQ: rop.PTR_EQ,
    rop.PTR_NE: rop.PTR_NE,
    }


def get_deep_immutable_oplist(operations):
    """
    When not we_are_translated(), turns ``operations`` into a frozenlist and
    monkey-patch its items to make sure they are not mutated.

    When we_are_translated(), do nothing and just return the old list.
    """
    from pypy.tool.frozenlist import frozenlist
    if we_are_translated():
        return operations
    #
    def setarg(*args):
        assert False, "operations cannot change at this point"
    def setdescr(*args):
        assert False, "operations cannot change at this point"
    newops = frozenlist(operations)
    for op in newops:
        op.setarg = setarg
        op.setdescr = setdescr
    return newops
