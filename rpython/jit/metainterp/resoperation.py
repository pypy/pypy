import weakref, os
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.objectmodel import compute_identity_hash
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.codewriter import longlong

class SettingForwardedOnAbstractValue(Exception):
    pass

class AbstractValue(object):
    _repr_memo = {} # weakref.WeakKeyDictionary()
    is_info_class = False
    _attrs_ = ()
    namespace = None

    def _get_hash_(self):
        return compute_identity_hash(self)

    def same_box(self, other):
        return self is other

    def repr_short(self, memo):
        return self.repr(memo)

    def is_constant(self):
        return False

    def get_forwarded(self):
        return None

    def set_forwarded(self, forwarded_to):
        llop.debug_print(lltype.Void, "setting forwarded on:", self.__class__.__name__)
        raise SettingForwardedOnAbstractValue()

    def get_box_replacement(op, not_const=False):
        orig_op = op
        c = 0
        while (op.get_forwarded() is not None and
               not op.get_forwarded().is_info_class and
               (not not_const or not op.get_forwarded().is_constant())):
            c += 1
            op = op.get_forwarded()
        if op is not orig_op and c > 1:
            orig_op.set_forwarded(op)
        return op

    def reset_value(self):
        pass

def ResOperation(opnum, args, descr=None):
    cls = opclasses[opnum]
    op = cls()
    op.initarglist(args)
    if descr is not None:
        assert isinstance(op, ResOpWithDescr)
        if opnum == rop.FINISH:
            assert descr.final_descr
        elif op.is_guard():
            assert not descr.final_descr
        op.setdescr(descr)
    return op


class AbstractResOp(AbstractValue):
    """The central ResOperation class, representing one operation."""

    _attrs_ = ('_forwarded',)

    # debug
    name = ""
    pc = 0
    opnum = 0
    _cls_has_bool_result = False
    type = 'v'
    boolreflex = -1
    boolinverse = -1
    _forwarded = None # either another resop or OptInfo

    def getopnum(self):
        return self.opnum

    def get_forwarded(self):
        return self._forwarded

    def set_forwarded(self, forwarded_to):
        assert forwarded_to is not self
        self._forwarded = forwarded_to

    # methods implemented by the arity mixins
    # ---------------------------------------

    def initarglist(self, args):
        "This is supposed to be called only just after the ResOp has been created"
        raise NotImplementedError

    def getarglist(self):
        raise NotImplementedError

    def getarglist_copy(self):
        return self.getarglist()

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

    def cleardescr(self):
        pass

    # common methods
    # --------------

    def copy_and_change(self, opnum, args=None, descr=None):
        "shallow copy: the returned operation is meant to be used in place of self"
        # XXX specialize
        from rpython.jit.metainterp.history import DONT_CHANGE
        
        if args is None:
            args = self.getarglist_copy()
        if descr is None:
            descr = self.getdescr()
        if descr is DONT_CHANGE:
            descr = None
        newop = ResOperation(opnum, args, descr)
        if self.type != 'v':
            newop.copy_value_from(self)
        return newop

    def repr(self, memo, graytext=False):
        # RPython-friendly version
        if self.type != 'v':
            try:
                sres = '%s = ' % memo[self]
            except KeyError:
                name = self.type + str(len(memo))
                memo[self] = name
                sres = name + ' = '
        #if self.result is not None:
        #    sres = '%s = ' % (self.result,)
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
                                   ', '.join([a.repr_short(memo) for a in args]))
        else:
            return '%s%s%s(%s)' % (prefix, sres, self.getopname(),
                                   ', '.join([a.repr_short(memo) for a in args] +
                                             ['descr=%r' % descr]))

    def repr_short(self, memo):
        try:
            return memo[self]
        except KeyError:
            name = self.type + str(len(memo))
            memo[self] = name
            return name

    def __repr__(self):
        r = self.repr(self._repr_memo)
        if self.namespace is not None:
            return "<" + self.namespace + ">" + r
        return r

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

    def is_same_as(self):
        return self.opnum in (rop.SAME_AS_I, rop.SAME_AS_F, rop.SAME_AS_R)

    def is_getfield(self):
        return self.opnum in (rop.GETFIELD_GC_I, rop.GETFIELD_GC_F,
                              rop.GETFIELD_GC_R, rop.GETFIELD_GC_PURE_I,
                              rop.GETFIELD_GC_PURE_R, rop.GETFIELD_GC_PURE_F)

    def is_getarrayitem(self):
        return self.opnum in (rop.GETARRAYITEM_GC_I, rop.GETARRAYITEM_GC_F,
                              rop.GETARRAYITEM_GC_R, rop.GETARRAYITEM_GC_PURE_I,
                              rop.GETARRAYITEM_GC_PURE_F,
                              rop.GETARRAYITEM_GC_PURE_R)

    def is_real_call(self):
        opnum = self.opnum
        return (opnum == rop.CALL_I or
                opnum == rop.CALL_R or
                opnum == rop.CALL_F or
                opnum == rop.CALL_N)

    def is_call_assembler(self):
        opnum = self.opnum
        return (opnum == rop.CALL_ASSEMBLER_I or
                opnum == rop.CALL_ASSEMBLER_R or
                opnum == rop.CALL_ASSEMBLER_N or
                opnum == rop.CALL_ASSEMBLER_F)

    def is_call_may_force(self):
        opnum = self.opnum
        return (opnum == rop.CALL_MAY_FORCE_I or
                opnum == rop.CALL_MAY_FORCE_R or
                opnum == rop.CALL_MAY_FORCE_N or
                opnum == rop.CALL_MAY_FORCE_F)

    def is_call_pure(self):
        opnum = self.opnum
        return (opnum == rop.CALL_PURE_I or
                opnum == rop.CALL_PURE_R or
                opnum == rop.CALL_PURE_N or
                opnum == rop.CALL_PURE_F)

    def is_call_release_gil(self):
        opnum = self.opnum
        # no R returning call_release_gil
        return (opnum == rop.CALL_RELEASE_GIL_I or
                opnum == rop.CALL_RELEASE_GIL_F or
                opnum == rop.CALL_RELEASE_GIL_N)

    def is_ovf(self):
        return rop._OVF_FIRST <= self.getopnum() <= rop._OVF_LAST

    def is_comparison(self):
        return self.is_always_pure() and self.returns_bool_result()

    def is_final(self):
        return rop._FINAL_FIRST <= self.getopnum() <= rop._FINAL_LAST

    def returns_bool_result(self):
        return self._cls_has_bool_result

    def forget_value(self):
        pass


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
        self._check_descr(descr)
        self._descr = descr

    def cleardescr(self):
        self._descr = None

    def _check_descr(self, descr):
        if not we_are_translated() and getattr(descr, 'I_am_a_descr', False):
            return # needed for the mock case in oparser_model
        from rpython.jit.metainterp.history import check_descr
        check_descr(descr)


class GuardResOp(ResOpWithDescr):

    _fail_args = None

    rd_snapshot = None
    rd_frame_info_list = None

    def getfailargs(self):
        return self._fail_args

    def setfailargs(self, fail_args):
        self._fail_args = fail_args

    def copy_and_change(self, opnum, args=None, descr=None):
        newop = AbstractResOp.copy_and_change(self, opnum, args, descr)
        assert isinstance(newop, GuardResOp)
        newop.setfailargs(self.getfailargs())
        newop.rd_snapshot = self.rd_snapshot
        newop.rd_frame_info_list = self.rd_frame_info_list
        return newop

# ===========
# type mixins
# ===========

class IntOp(object):
    _mixin_ = True

    type = 'i'

    _resint = 0

    def getint(self):
        return self._resint

    getvalue = getint

    def setint(self, intval):
        self._resint = intval

    def copy_value_from(self, other):
        self.setint(other.getint())

    def constbox(self):
        from rpython.jit.metainterp import history
        return history.ConstInt(self.getint())

    def nonnull(self):
        return self._resint != 0

class FloatOp(object):
    _mixin_ = True

    type = 'f'

    _resfloat = 0.0

    def getfloatstorage(self):
        return self._resfloat

    getvalue = getfloatstorage
    getfloat = getfloatstorage
    
    def setfloatstorage(self, floatval):
        self._resfloat = floatval

    def copy_value_from(self, other):
        self.setfloatstorage(other.getfloatstorage())

    def constbox(self):
        from rpython.jit.metainterp import history
        return history.ConstFloat(self.getfloatstorage())

    def nonnull(self):
        return bool(longlong.extract_bits(self._resfloat))

class RefOp(object):
    _mixin_ = True

    type = 'r'

    _resref = lltype.nullptr(llmemory.GCREF.TO)

    def getref_base(self):
        return self._resref

    def reset_value(self):
        self.setref_base(lltype.nullptr(llmemory.GCREF.TO))

    getvalue = getref_base

    def forget_value(self):
        self._resref = lltype.nullptr(llmemory.GCREF.TO)

    def setref_base(self, refval):
        self._resref = refval

    def getref(self, PTR):
        return lltype.cast_opaque_ptr(PTR, self.getref_base())
    getref._annspecialcase_ = 'specialize:arg(1)'

    def copy_value_from(self, other):
        self.setref_base(other.getref_base())

    def nonnull(self):
        return bool(self._resref)

    def constbox(self):
        from rpython.jit.metainterp import history
        return history.ConstPtr(self.getref_base())


class AbstractInputArg(AbstractValue):
    _forwarded = None

    def get_forwarded(self):
        return self._forwarded

    def set_forwarded(self, forwarded_to):
        self._forwarded = forwarded_to

    def repr(self, memo):
        try:
            return memo[self]
        except KeyError:
            name = self.type + str(len(memo))
            memo[self] = name
            return name

    def __repr__(self):
        return self.repr(self._repr_memo)

    def getdescr(self):
        return None

    def forget_value(self):
        pass
    
class InputArgInt(IntOp, AbstractInputArg):
    def __init__(self, intval=0):
        self.setint(intval)

class InputArgFloat(FloatOp, AbstractInputArg):
    def __init__(self, f=0.0):
        self.setfloatstorage(f)

class InputArgRef(RefOp, AbstractInputArg):
    def __init__(self, r=lltype.nullptr(llmemory.GCREF.TO)):
        self.setref_base(r)

    def reset_value(self):
        self.setref_base(lltype.nullptr(llmemory.GCREF.TO))

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
        if not we_are_translated() and \
               self.__class__.__name__.startswith('FINISH'):   # XXX remove me
            assert len(args) <= 1      # FINISH operations take 0 or 1 arg now

    def getarglist(self):
        return self._args

    def getarglist_copy(self):
        return self._args[:]

    def numargs(self):
        return len(self._args)

    def getarg(self, i):
        return self._args[i]

    def setarg(self, i, box):
        self._args[i] = box


# ____________________________________________________________

""" All the operations are desribed like this:

NAME/no-of-args-or-*[b][d]/types-of-result

if b is present it means the operation produces a boolean
if d is present it means there is a descr
type of result can be one or more of r i f n
"""

_oplist = [
    '_FINAL_FIRST',
    'JUMP/*d/n',
    'FINISH/*d/n',
    '_FINAL_LAST',

    'LABEL/*d/n',

    '_GUARD_FIRST',
    '_GUARD_FOLDABLE_FIRST',
    'GUARD_TRUE/1d/n',
    'GUARD_FALSE/1d/n',
    'GUARD_VALUE/2d/n',
    'GUARD_CLASS/2d/n',
    'GUARD_NONNULL/1d/n',
    'GUARD_ISNULL/1d/n',
    'GUARD_NONNULL_CLASS/2d/n',
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION/0d/n',   # may be called with an exception currently set
    'GUARD_EXCEPTION/1d/r',     # may be called with an exception currently set
    'GUARD_NO_OVERFLOW/0d/n',
    'GUARD_OVERFLOW/0d/r',
    'GUARD_NOT_FORCED/0d/n',      # may be called with an exception currently set
    'GUARD_NOT_FORCED_2/0d/n',    # same as GUARD_NOT_FORCED, but for finish()
    'GUARD_NOT_INVALIDATED/0d/n',
    'GUARD_FUTURE_CONDITION/0d/n',
    # is removable, may be patched by an optimization
    '_GUARD_LAST', # ----- end of guard operations -----

    '_NOSIDEEFFECT_FIRST', # ----- start of no_side_effect operations -----
    '_ALWAYS_PURE_FIRST', # ----- start of always_pure operations -----
    'INT_ADD/2/i',
    'INT_SUB/2/i',
    'INT_MUL/2/i',
    'INT_FLOORDIV/2/i',
    'UINT_FLOORDIV/2/i',
    'INT_MOD/2/i',
    'INT_AND/2/i',
    'INT_OR/2/i',
    'INT_XOR/2/i',
    'INT_RSHIFT/2/i',
    'INT_LSHIFT/2/i',
    'UINT_RSHIFT/2/i',
    'INT_SIGNEXT/2/i',
    'FLOAT_ADD/2/f',
    'FLOAT_SUB/2/f',
    'FLOAT_MUL/2/f',
    'FLOAT_TRUEDIV/2/f',
    'FLOAT_NEG/1/f',
    'FLOAT_ABS/1/f',
    'CAST_FLOAT_TO_INT/1/i',          # don't use for unsigned ints; we would
    'CAST_INT_TO_FLOAT/1/f',          # need some messy code in the backend
    'CAST_FLOAT_TO_SINGLEFLOAT/1/i',
    'CAST_SINGLEFLOAT_TO_FLOAT/1/f',
    'CONVERT_FLOAT_BYTES_TO_LONGLONG/1/i',
    'CONVERT_LONGLONG_BYTES_TO_FLOAT/1/f',
    #
    'INT_LT/2b/i',
    'INT_LE/2b/i',
    'INT_EQ/2b/i',
    'INT_NE/2b/i',
    'INT_GT/2b/i',
    'INT_GE/2b/i',
    'UINT_LT/2b/i',
    'UINT_LE/2b/i',
    'UINT_GT/2b/i',
    'UINT_GE/2b/i',
    'FLOAT_LT/2b/i',
    'FLOAT_LE/2b/i',
    'FLOAT_EQ/2b/i',
    'FLOAT_NE/2b/i',
    'FLOAT_GT/2b/i',
    'FLOAT_GE/2b/i',
    #
    'INT_IS_ZERO/1b/i',
    'INT_IS_TRUE/1b/i',
    'INT_NEG/1/i',
    'INT_INVERT/1/i',
    'INT_FORCE_GE_ZERO/1/i',
    #
    'SAME_AS/1/ifr',      # gets a Const or a Box, turns it into another Box
    'CAST_PTR_TO_INT/1/i',
    'CAST_INT_TO_PTR/1/r',
    #
    'PTR_EQ/2b/i',
    'PTR_NE/2b/i',
    'INSTANCE_PTR_EQ/2b/i',
    'INSTANCE_PTR_NE/2b/i',
    'NURSERY_PTR_INCREMENT/2/r',
    #
    'ARRAYLEN_GC/1d/i',
    'STRLEN/1/i',
    'STRGETITEM/2/i',
    'GETFIELD_GC_PURE/1d/rfi',
    'GETFIELD_RAW_PURE/1d/rfi',
    'GETARRAYITEM_GC_PURE/2d/rfi',
    'GETARRAYITEM_RAW_PURE/2d/fi',
    'UNICODELEN/1/i',
    'UNICODEGETITEM/2/i',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d/rfi',
    'GETARRAYITEM_RAW/2d/fi',
    'GETINTERIORFIELD_GC/2d/rfi',
    'RAW_LOAD/2d/fi',
    'GETFIELD_GC/1d/rfi',
    'GETFIELD_RAW/1d/rfi',
    '_MALLOC_FIRST',
    'NEW/0d/r',           #-> GcStruct, gcptrs inside are zeroed (not the rest)
    'NEW_WITH_VTABLE/0d/r',#-> GcStruct with vtable, gcptrs inside are zeroed
    'NEW_ARRAY/1d/r',     #-> GcArray, not zeroed. only for arrays of primitives
    'NEW_ARRAY_CLEAR/1d/r',#-> GcArray, fully zeroed
    'NEWSTR/1/r',         #-> STR, the hash field is zeroed
    'NEWUNICODE/1/r',     #-> UNICODE, the hash field is zeroed
    '_MALLOC_LAST',
    'FORCE_TOKEN/0/r',
    'VIRTUAL_REF/2/r',    # removed before it's passed to the backend
    'MARK_OPAQUE_PTR/1/n',
    # this one has no *visible* side effect, since the virtualizable
    # must be forced, however we need to execute it anyway
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'INCREMENT_DEBUG_COUNTER/1/n',
    'SETARRAYITEM_GC/3d/n',
    'SETARRAYITEM_RAW/3d/n',
    'SETINTERIORFIELD_GC/3d/n',
    'SETINTERIORFIELD_RAW/3d/n',    # right now, only used by tests
    'RAW_STORE/3d/n',
    'SETFIELD_GC/2d/n',
    'ZERO_PTR_FIELD/2/n', # only emitted by the rewrite, clears a pointer field
                        # at a given constant offset, no descr
    'ZERO_ARRAY/3d/n',  # only emitted by the rewrite, clears (part of) an array
                        # [arraygcptr, firstindex, length], descr=ArrayDescr
    'SETFIELD_RAW/2d/n',
    'STRSETITEM/3/n',
    'UNICODESETITEM/3/n',
    'COND_CALL_GC_WB/1d/n',       # [objptr] (for the write barrier)
    'COND_CALL_GC_WB_ARRAY/2d/n', # [objptr, arrayindex] (write barr. for array)
    'DEBUG_MERGE_POINT/*/n',      # debugging only
    'ENTER_PORTAL_FRAME/2/n',     # debugging only
    'LEAVE_PORTAL_FRAME/1/n',     # debugging only
    'JIT_DEBUG/*/n',              # debugging only
    'VIRTUAL_REF_FINISH/2/n',   # removed before it's passed to the backend
    'COPYSTRCONTENT/5/n',       # src, dst, srcstart, dststart, length
    'COPYUNICODECONTENT/5/n',
    'QUASIIMMUT_FIELD/1d/n',    # [objptr], descr=SlowMutateDescr
    'RECORD_KNOWN_CLASS/2/n',   # [objptr, clsptr]
    'KEEPALIVE/1/n',

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    '_CALL_FIRST',
    'CALL/*d/rfin',
    'COND_CALL/*d/n',
    # a conditional call, with first argument as a condition
    'CALL_ASSEMBLER/*d/rfin',  # call already compiled assembler
    'CALL_MAY_FORCE/*d/rfin',
    'CALL_LOOPINVARIANT/*d/rfin',
    'CALL_RELEASE_GIL/*d/rfin',
    # release the GIL and "close the stack" for asmgcc
    'CALL_PURE/*d/rfin',             # removed before it's passed to the backend
    'CALL_MALLOC_GC/*d/r',      # like CALL, but NULL => propagate MemoryError
    'CALL_MALLOC_NURSERY/1/r',  # nursery malloc, const number of bytes, zeroed
    'CALL_MALLOC_NURSERY_VARSIZE/3d/r',
    'CALL_MALLOC_NURSERY_VARSIZE_FRAME/1/r',
    # nursery malloc, non-const number of bytes, zeroed
    # note that the number of bytes must be well known to be small enough
    # to fulfill allocating in the nursery rules (and no card markings)
    '_CALL_LAST',
    '_CANRAISE_LAST', # ----- end of can_raise operations -----

    '_OVF_FIRST', # ----- start of is_ovf operations -----
    'INT_ADD_OVF/2/i', # note that the orded has to match INT_ADD order
    'INT_SUB_OVF/2/i',
    'INT_MUL_OVF/2/i',
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
optypes = []     # mapping numbers to type of return

def setup(debug_print=False):
    i = 0
    for name in _oplist:
        if '/' in name:
            name, arity, result = name.split('/')
            withdescr = 'd' in arity
            boolresult = 'b' in arity
            arity = arity.rstrip('db')
            if arity == '*':
                arity = -1
            else:
                arity = int(arity)
        else:
            arity, withdescr, boolresult, result = -1, True, False, None       # default
        if not name.startswith('_'):
            for r in result:
                if len(result) == 1:
                    cls_name = name
                else:
                    cls_name = name + '_' + r.upper()
                setattr(rop, cls_name, i)
                opname[i] = cls_name
                cls = create_class_for_op(cls_name, i, arity, withdescr, r)
                cls._cls_has_bool_result = boolresult
                opclasses.append(cls)
                oparity.append(arity)
                opwithdescr.append(withdescr)
                optypes.append(r)
                if debug_print:
                    print '%30s = %d' % (cls_name, i)
                i += 1
        else:
            setattr(rop, name, i)
            opclasses.append(None)
            oparity.append(-1)
            opwithdescr.append(False)
            optypes.append(' ')
            if debug_print:
                print '%30s = %d' % (name, i)
            i += 1
    # for optimizeopt/pure.py's getrecentops()
    assert (rop.INT_ADD_OVF - rop._OVF_FIRST ==
            rop.INT_ADD - rop._ALWAYS_PURE_FIRST)
    assert (rop.INT_SUB_OVF - rop._OVF_FIRST ==
            rop.INT_SUB - rop._ALWAYS_PURE_FIRST)
    assert (rop.INT_MUL_OVF - rop._OVF_FIRST ==
            rop.INT_MUL - rop._ALWAYS_PURE_FIRST)

def get_base_class(mixins, base):
    try:
        return get_base_class.cache[(base,) + mixins]
    except KeyError:
        arity_name = mixins[0].__name__[:-2]  # remove the trailing "Op"
        name = arity_name + base.__name__ # something like BinaryPlainResOp
        bases = mixins + (base,)
        cls = type(name, bases, {})
        get_base_class.cache[(base,) + mixins] = cls
        return cls
get_base_class.cache = {}

def create_class_for_op(name, opnum, arity, withdescr, result_type):
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
    mixins = [arity2mixin.get(arity, N_aryOp)]
    if result_type == 'i':
        mixins.append(IntOp)
    elif result_type == 'f':
        mixins.append(FloatOp)
    elif result_type == 'r':
        mixins.append(RefOp)
    else:
        assert result_type == 'n'

    cls_name = '%s_OP' % name
    bases = (get_base_class(tuple(mixins), baseclass),)
    dic = {'opnum': opnum}
    return type(cls_name, bases, dic)

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist

_opboolinverse = {
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

_opboolreflex = {
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

def setup2():
    for cls in opclasses:
        if cls is None:
            continue
        opnum = cls.opnum
        if opnum in _opboolreflex:
            cls.boolreflex = _opboolreflex[opnum]
        if opnum in _opboolinverse:
            cls.boolinverse = _opboolinverse[opnum]

setup2()
del _opboolinverse
del _opboolreflex

def get_deep_immutable_oplist(operations):
    """
    When not we_are_translated(), turns ``operations`` into a frozenlist and
    monkey-patch its items to make sure they are not mutated.

    When we_are_translated(), do nothing and just return the old list.
    """
    from rpython.tool.frozenlist import frozenlist
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

class OpHelpers(object):
    @staticmethod
    def call_for_descr(descr):
        tp = descr.get_result_type()
        if tp == 'i':
            return rop.CALL_I
        elif tp == 'r':
            return rop.CALL_R
        elif tp == 'f':
            return rop.CALL_F
        assert tp == 'v'
        return rop.CALL_N

    @staticmethod
    def call_pure_for_descr(descr):
        tp = descr.get_result_type()
        if tp == 'i':
            return rop.CALL_PURE_I
        elif tp == 'r':
            return rop.CALL_PURE_R
        elif tp == 'f':
            return rop.CALL_PURE_F
        assert tp == 'v'
        return rop.CALL_PURE_N

    @staticmethod
    def call_may_force_for_descr(descr):
        tp = descr.get_result_type()
        if tp == 'i':
            return rop.CALL_MAY_FORCE_I
        elif tp == 'r':
            return rop.CALL_MAY_FORCE_R
        elif tp == 'f':
            return rop.CALL_MAY_FORCE_F
        assert tp == 'v'
        return rop.CALL_MAY_FORCE_N

    @staticmethod
    def call_assembler_for_descr(descr):
        tp = descr.get_result_type()
        if tp == 'i':
            return rop.CALL_ASSEMBLER_I
        elif tp == 'r':
            return rop.CALL_ASSEMBLER_R
        elif tp == 'f':
            return rop.CALL_ASSEMBLER_F
        assert tp == 'v'
        return rop.CALL_ASSEMBLER_N

    @staticmethod
    def call_loopinvariant_for_descr(descr):
        tp = descr.get_result_type()
        if tp == 'i':
            return rop.CALL_LOOPINVARIANT_I
        elif tp == 'r':
            return rop.CALL_LOOPINVARIANT_R
        elif tp == 'f':
            return rop.CALL_LOOPINVARIANT_F
        assert tp == 'v'
        return rop.CALL_LOOPINVARIANT_N

    @staticmethod
    def getfield_pure_for_descr(descr):
        if descr.is_pointer_field():
            return rop.GETFIELD_GC_PURE_R
        elif descr.is_float_field():
            return rop.GETFIELD_GC_PURE_F
        return rop.GETFIELD_GC_PURE_I

    @staticmethod
    def getfield_for_descr(descr):
        if descr.is_pointer_field():
            return rop.GETFIELD_GC_R
        elif descr.is_float_field():
            return rop.GETFIELD_GC_F
        return rop.GETFIELD_GC_I

    @staticmethod
    def getarrayitem_pure_for_descr(descr):
        if descr.is_array_of_pointers():
            return rop.GETARRAYITEM_GC_PURE_R
        elif descr.is_array_of_floats():
            return rop.GETARRAYITEM_GC_PURE_F
        return rop.GETARRAYITEM_GC_PURE_I

    @staticmethod
    def getarrayitem_for_descr(descr):
        if descr.is_array_of_pointers():
            return rop.GETARRAYITEM_GC_R
        elif descr.is_array_of_floats():
            return rop.GETARRAYITEM_GC_F
        return rop.GETARRAYITEM_GC_I

    @staticmethod
    def same_as_for_type(tp):
        if tp == 'i':
            return rop.SAME_AS_I
        elif tp == 'r':
            return rop.SAME_AS_R
        else:
            assert tp == 'f'
            return rop.SAME_AS_F

    @staticmethod
    def call_for_type(tp):
        if tp == 'i':
            return rop.CALL_I
        elif tp == 'r':
            return rop.CALL_R
        elif tp == 'f':
            return rop.CALL_F
        return rop.CALL_N

    @staticmethod
    def is_call(opnum):
        return rop._CALL_FIRST <= opnum <= rop._CALL_LAST

    @staticmethod
    def is_plain_call(opnum):
        return (opnum == rop.CALL_I or
                opnum == rop.CALL_R or
                opnum == rop.CALL_F or
                opnum == rop.CALL_N)

    @staticmethod
    def is_call_assembler(opnum):
        return (opnum == rop.CALL_ASSEMBLER_I or
                opnum == rop.CALL_ASSEMBLER_R or
                opnum == rop.CALL_ASSEMBLER_F or
                opnum == rop.CALL_ASSEMBLER_N)

    @staticmethod
    def is_call_loopinvariant(opnum):
        return (opnum == rop.CALL_LOOPINVARIANT_I or
                opnum == rop.CALL_LOOPINVARIANT_R or
                opnum == rop.CALL_LOOPINVARIANT_F or
                opnum == rop.CALL_LOOPINVARIANT_N)

    @staticmethod
    def is_call_may_force(opnum):
        return (opnum == rop.CALL_MAY_FORCE_I or
                opnum == rop.CALL_MAY_FORCE_R or
                opnum == rop.CALL_MAY_FORCE_F or
                opnum == rop.CALL_MAY_FORCE_N)

    @staticmethod
    def is_call_release_gil(opnum):
        return (opnum == rop.CALL_RELEASE_GIL_I or
                opnum == rop.CALL_RELEASE_GIL_R or
                opnum == rop.CALL_RELEASE_GIL_F or
                opnum == rop.CALL_RELEASE_GIL_N)

    @staticmethod
    def inputarg_from_tp(tp):
        if tp == 'i':
            return InputArgInt()
        elif tp == 'r':
            return InputArgRef()
        else:
            assert tp == 'f'
            return InputArgFloat()
