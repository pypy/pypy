"""
The table of all LL operations.
"""

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.tool.descriptor import roproperty


class LLOp(object):

    def __init__(self, sideeffects=True, canfold=False, canraise=(),
                 pyobj=False, canunwindgc=False, canrun=False, oo=False,
                 tryfold=False):
        # self.opname = ... (set afterwards)

        if canfold:
            sideeffects = False

        # The operation has no side-effects: it can be removed
        # if its result is not used
        self.sideeffects = sideeffects

        # Can be safely constant-folded: no side-effects
        #  and always gives the same result for given args
        self.canfold = canfold

        # Can *try* to fold the operation, but it may raise on you
        self.tryfold = tryfold or canfold

        # Exceptions that can be raised
        self.canraise = canraise
        assert isinstance(canraise, tuple)

        assert not canraise or not canfold

        # The operation manipulates PyObjects
        self.pyobj = pyobj

        # The operation can unwind the stack in a stackless gc build
        self.canunwindgc = canunwindgc
        if canunwindgc:
            if (StackException not in self.canraise and
                Exception not in self.canraise):
                self.canraise += (StackException,)

        # The operation can be run directly with __call__
        self.canrun = canrun or canfold

        # The operation belongs to the ootypesystem
        self.oo = oo

    # __________ make the LLOp instances callable from LL helpers __________

    __name__ = property(lambda self: 'llop_'+self.opname)

    def __call__(self, RESULTTYPE, *args):
        # llop is meant to be rtyped and not called directly, unless it is
        # a canfold=True operation
        fold = self.fold
        if getattr(fold, 'need_result_type', False):
            val = fold(RESULTTYPE, *args)
        else:
            val = fold(*args)
        if RESULTTYPE is not lltype.Void:
            val = lltype.enforce(RESULTTYPE, val)
        return val

    def get_fold_impl(self):
        global lltype                 #  <- lazy import hack, worth an XXX
        from pypy.rpython.lltypesystem import lltype
        if self.canrun:
            if self.oo:
                from pypy.rpython.ootypesystem.ooopimpl import get_op_impl
            else:
                from pypy.rpython.lltypesystem.opimpl import get_op_impl
            op_impl = get_op_impl(self.opname)
        else:
            error = TypeError("cannot constant-fold operation %r" % (
                self.opname,))
            def op_impl(*args):
                raise error
        # cache the implementation function into 'self'
        self.fold = op_impl
        return op_impl
    fold = roproperty(get_fold_impl)

    def is_pure(self, args_v):
        if self.canfold:                # canfold => pure operation
            return True
        if self is llop.debug_assert:   # debug_assert is pure enough
            return True
        # reading from immutable (lltype)
        if self is llop.getfield or self is llop.getarrayitem:
            field = getattr(args_v[1], 'value', None)
            return args_v[0].concretetype.TO._immutable_field(field)
        # reading from immutable (ootype) (xxx what about arrays?)
        if self is llop.oogetfield:
            field = getattr(args_v[1], 'value', None)
            return args_v[0].concretetype._immutable_field(field)
        # default
        return False

    def __repr__(self):
        return '<LLOp %s>' % (getattr(self, 'opname', '?'),)


class _LLOP(object):
    def _freeze_(self):
        return True
llop = _LLOP()

class VoidMarker(object):
    # marker wrapper for void arguments to llops
    def __init__(self, value):
        self.value = value
    def _freeze_(self):
        return True

def void(value):
    return VoidMarker(value)

class Entry(ExtRegistryEntry):
    _about_ = void

    def compute_result_annotation(self, s_value):
        assert s_value.is_constant()
        from pypy.annotation.bookkeeper import getbookkeeper
        bk = getbookkeeper()
        return bk.immutablevalue(VoidMarker(s_value.const))

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        return hop.inputconst(lltype.Void, None)

def enum_ops_without_sideeffects(raising_is_ok=False):
    """Enumerate operations that have no side-effects
    (see also enum_foldable_ops)."""
    for opname, opdesc in LL_OPERATIONS.iteritems():
        if not opdesc.sideeffects:
            if not opdesc.canraise or raising_is_ok:
                yield opname

def enum_foldable_ops(_ignored=None):
    """Enumerate operations that can be constant-folded."""
    for opname, opdesc in LL_OPERATIONS.iteritems():
        if opdesc.canfold:
            assert not opdesc.canraise
            yield opname


class Entry(ExtRegistryEntry):
    "Annotation and rtyping of LLOp instances, which are callable."
    _type_ = LLOp

    def compute_result_annotation(self, RESULTTYPE, *args):
        from pypy.annotation.model import lltype_to_annotation
        assert RESULTTYPE.is_constant()
        return lltype_to_annotation(RESULTTYPE.const)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        op = self.instance    # the LLOp object that was called
        args_v = []
        for i, s_arg in enumerate(hop.args_s[1:]):
            if s_arg.is_constant() and isinstance(s_arg.const, VoidMarker):
                v_arg = hop.inputconst(lltype.Void, s_arg.const.value)
            else:
                v_arg = hop.inputarg(hop.args_r[i+1], i+1)
            args_v.append(v_arg)

        if op.canraise:
            hop.exception_is_here()
        else:
            hop.exception_cannot_occur()
        return hop.genop(op.opname, args_v, resulttype=hop.r_result.lowleveltype)


class StackException(Exception):
    """Base for internal exceptions possibly used by the stackless
    implementation."""

# ____________________________________________________________
#
# This list corresponds to the operations implemented by the LLInterpreter.
# Note that many exception-raising operations can be replaced by calls
# to helper functions in pypy.rpython.raisingops.raisingops.
# ***** Run test_lloperation after changes. *****

LL_OPERATIONS = {

    'direct_call':          LLOp(canraise=(Exception,)),
    'indirect_call':        LLOp(canraise=(Exception,)),

    # __________ numeric operations __________

    'bool_not':             LLOp(canfold=True),

    'char_lt':              LLOp(canfold=True),
    'char_le':              LLOp(canfold=True),
    'char_eq':              LLOp(canfold=True),
    'char_ne':              LLOp(canfold=True),
    'char_gt':              LLOp(canfold=True),
    'char_ge':              LLOp(canfold=True),

    'unichar_eq':           LLOp(canfold=True),
    'unichar_ne':           LLOp(canfold=True),

    'int_is_true':          LLOp(canfold=True),
    'int_neg':              LLOp(canfold=True),
    'int_neg_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    'int_abs':              LLOp(canfold=True),
    'int_abs_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    'int_invert':           LLOp(canfold=True),

    'int_add':              LLOp(canfold=True),
    'int_sub':              LLOp(canfold=True),
    'int_mul':              LLOp(canfold=True),
    'int_floordiv':         LLOp(canfold=True),
    'int_floordiv_zer':     LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'int_mod':              LLOp(canfold=True),
    'int_mod_zer':          LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'int_lt':               LLOp(canfold=True),
    'int_le':               LLOp(canfold=True),
    'int_eq':               LLOp(canfold=True),
    'int_ne':               LLOp(canfold=True),
    'int_gt':               LLOp(canfold=True),
    'int_ge':               LLOp(canfold=True),
    'int_and':              LLOp(canfold=True),
    'int_or':               LLOp(canfold=True),
    'int_lshift':           LLOp(canfold=True),
    'int_rshift':           LLOp(canfold=True),
    'int_xor':              LLOp(canfold=True),

    'int_between':          LLOp(canfold=True),   # a <= b < c

    'int_add_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    'int_add_nonneg_ovf':   LLOp(canraise=(OverflowError,), tryfold=True),
              # ^^^ more efficient version when 2nd arg is nonneg
    'int_sub_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    'int_mul_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    # the following operations overflow in one case: (-sys.maxint-1) // (-1)
    'int_floordiv_ovf':     LLOp(canraise=(OverflowError,), tryfold=True),
    'int_floordiv_ovf_zer': LLOp(canraise=(OverflowError, ZeroDivisionError),
                                                            tryfold=True),
    'int_mod_ovf':          LLOp(canraise=(OverflowError,), tryfold=True),
    'int_mod_ovf_zer':      LLOp(canraise=(OverflowError, ZeroDivisionError),
                                                            tryfold=True),
    'int_lshift_ovf':       LLOp(canraise=(OverflowError,), tryfold=True),

    'uint_is_true':         LLOp(canfold=True),
    'uint_invert':          LLOp(canfold=True),

    'uint_add':             LLOp(canfold=True),
    'uint_sub':             LLOp(canfold=True),
    'uint_mul':             LLOp(canfold=True),
    'uint_floordiv':        LLOp(canfold=True),
    'uint_floordiv_zer':    LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'uint_mod':             LLOp(canfold=True),
    'uint_mod_zer':         LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'uint_lt':              LLOp(canfold=True),
    'uint_le':              LLOp(canfold=True),
    'uint_eq':              LLOp(canfold=True),
    'uint_ne':              LLOp(canfold=True),
    'uint_gt':              LLOp(canfold=True),
    'uint_ge':              LLOp(canfold=True),
    'uint_and':             LLOp(canfold=True),
    'uint_or':              LLOp(canfold=True),
    'uint_lshift':          LLOp(canfold=True),  # args (r_uint, int)
    'uint_rshift':          LLOp(canfold=True),  # args (r_uint, int)
    'uint_xor':             LLOp(canfold=True),

    'float_is_true':        LLOp(canfold=True),  # it really means "x != 0.0"
    'float_neg':            LLOp(canfold=True),
    'float_abs':            LLOp(canfold=True),

    'float_add':            LLOp(canfold=True),
    'float_sub':            LLOp(canfold=True),
    'float_mul':            LLOp(canfold=True),
    'float_truediv':        LLOp(canfold=True),
    'float_lt':             LLOp(canfold=True),
    'float_le':             LLOp(canfold=True),
    'float_eq':             LLOp(canfold=True),
    'float_ne':             LLOp(canfold=True),
    'float_gt':             LLOp(canfold=True),
    'float_ge':             LLOp(canfold=True),
    # don't implement float_mod, use math.fmod instead
    # don't implement float_pow, use math.pow instead

    'llong_is_true':        LLOp(canfold=True),
    'llong_neg':            LLOp(canfold=True),
    'llong_abs':            LLOp(canfold=True),
    'llong_invert':         LLOp(canfold=True),

    'llong_add':            LLOp(canfold=True),
    'llong_sub':            LLOp(canfold=True),
    'llong_mul':            LLOp(canfold=True),
    'llong_floordiv':       LLOp(canfold=True),
    'llong_floordiv_zer':   LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'llong_mod':            LLOp(canfold=True),
    'llong_mod_zer':        LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'llong_lt':             LLOp(canfold=True),
    'llong_le':             LLOp(canfold=True),
    'llong_eq':             LLOp(canfold=True),
    'llong_ne':             LLOp(canfold=True),
    'llong_gt':             LLOp(canfold=True),
    'llong_ge':             LLOp(canfold=True),
    'llong_and':            LLOp(canfold=True),
    'llong_or':             LLOp(canfold=True),
    'llong_lshift':         LLOp(canfold=True),  # args (r_longlong, int)
    'llong_rshift':         LLOp(canfold=True),  # args (r_longlong, int)
    'llong_xor':            LLOp(canfold=True),

    'ullong_is_true':       LLOp(canfold=True),
    'ullong_invert':        LLOp(canfold=True),

    'ullong_add':           LLOp(canfold=True),
    'ullong_sub':           LLOp(canfold=True),
    'ullong_mul':           LLOp(canfold=True),
    'ullong_floordiv':      LLOp(canfold=True),
    'ullong_floordiv_zer':  LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'ullong_mod':           LLOp(canfold=True),
    'ullong_mod_zer':       LLOp(canraise=(ZeroDivisionError,), tryfold=True),
    'ullong_lt':            LLOp(canfold=True),
    'ullong_le':            LLOp(canfold=True),
    'ullong_eq':            LLOp(canfold=True),
    'ullong_ne':            LLOp(canfold=True),
    'ullong_gt':            LLOp(canfold=True),
    'ullong_ge':            LLOp(canfold=True),
    'ullong_and':           LLOp(canfold=True),
    'ullong_or':            LLOp(canfold=True),
    'ullong_lshift':        LLOp(canfold=True),  # args (r_ulonglong, int)
    'ullong_rshift':        LLOp(canfold=True),  # args (r_ulonglong, int)
    'ullong_xor':           LLOp(canfold=True),

    'cast_primitive':       LLOp(canfold=True),
    'cast_bool_to_int':     LLOp(canfold=True),
    'cast_bool_to_uint':    LLOp(canfold=True),
    'cast_bool_to_float':   LLOp(canfold=True),
    'cast_char_to_int':     LLOp(canfold=True),
    'cast_unichar_to_int':  LLOp(canfold=True),
    'cast_int_to_char':     LLOp(canfold=True),
    'cast_int_to_unichar':  LLOp(canfold=True),
    'cast_int_to_uint':     LLOp(canfold=True),
    'cast_int_to_float':    LLOp(canfold=True),
    'cast_int_to_longlong': LLOp(canfold=True),
    'cast_uint_to_int':     LLOp(canfold=True),
    'cast_uint_to_float':   LLOp(canfold=True),
    'cast_longlong_to_float' :LLOp(canfold=True),
    'cast_ulonglong_to_float':LLOp(canfold=True),
    'cast_float_to_int':    LLOp(canraise=(OverflowError,), tryfold=True),
    'cast_float_to_uint':   LLOp(canfold=True),    # XXX need OverflowError?
    'cast_float_to_longlong' :LLOp(canfold=True),
    'cast_float_to_ulonglong':LLOp(canfold=True),
    'truncate_longlong_to_int':LLOp(canfold=True),
    'force_cast':           LLOp(sideeffects=False),    # only for rffi.cast()

    # __________ pointer operations __________

    'malloc':               LLOp(canraise=(MemoryError,), canunwindgc=True),
    'malloc_varsize':       LLOp(canraise=(MemoryError,), canunwindgc=True),
    'malloc_nonmovable':    LLOp(canraise=(MemoryError,), canunwindgc=True),
    'malloc_nonmovable_varsize':LLOp(canraise=(MemoryError,),canunwindgc=True),
    'shrink_array':         LLOp(canrun=True),
    'zero_gc_pointers_inside': LLOp(),
    'free':                 LLOp(),
    'getfield':             LLOp(sideeffects=False, canrun=True),
    'getarrayitem':         LLOp(sideeffects=False, canrun=True),
    'getarraysize':         LLOp(canfold=True),
    'getsubstruct':         LLOp(canfold=True),
    'getinteriorfield':     LLOp(sideeffects=False, canrun=True),
    'getinteriorarraysize': LLOp(canfold=True),
    'setinteriorfield':     LLOp(),
    'bare_setinteriorfield':     LLOp(),
    'getarraysubstruct':    LLOp(canfold=True),
    'setfield':             LLOp(),
    'bare_setfield':        LLOp(),
    'setarrayitem':         LLOp(),
    'bare_setarrayitem':    LLOp(),
    'cast_pointer':         LLOp(canfold=True),
    'ptr_eq':               LLOp(canfold=True),
    'ptr_ne':               LLOp(canfold=True),
    'ptr_nonzero':          LLOp(canfold=True),
    'ptr_iszero':           LLOp(canfold=True),
    'cast_ptr_to_int':      LLOp(sideeffects=False),
    'cast_int_to_ptr':      LLOp(sideeffects=False),
    'direct_fieldptr':      LLOp(canfold=True),
    'direct_arrayitems':    LLOp(canfold=True),
    'direct_ptradd':        LLOp(canfold=True),
    'cast_opaque_ptr':      LLOp(sideeffects=False),

    # __________ address operations __________

    'boehm_malloc':         LLOp(),
    'boehm_malloc_atomic':  LLOp(),
    'boehm_register_finalizer': LLOp(),
    'boehm_disappearing_link': LLOp(),
    'raw_malloc':           LLOp(),
    'raw_malloc_usage':     LLOp(sideeffects=False),
    'raw_free':             LLOp(),
    'raw_memclear':         LLOp(),
    'raw_memcopy':          LLOp(),
    'raw_memmove':          LLOp(),
    'raw_load':             LLOp(sideeffects=False),
    'raw_store':            LLOp(),
    'stack_malloc':         LLOp(), # mmh
    'track_alloc_start':    LLOp(),
    'track_alloc_stop':     LLOp(),
    'adr_add':              LLOp(canfold=True),
    'adr_sub':              LLOp(canfold=True),
    'adr_delta':            LLOp(canfold=True),
    'adr_lt':               LLOp(canfold=True),
    'adr_le':               LLOp(canfold=True),
    'adr_eq':               LLOp(canfold=True),
    'adr_ne':               LLOp(canfold=True),
    'adr_gt':               LLOp(canfold=True),
    'adr_ge':               LLOp(canfold=True),
    'adr_call':             LLOp(canraise=(Exception,)),
    'cast_ptr_to_adr':      LLOp(sideeffects=False),
    'cast_adr_to_ptr':      LLOp(canfold=True),
    'cast_adr_to_int':      LLOp(sideeffects=False),
    'cast_int_to_adr':      LLOp(canfold=True),

    'get_group_member':     LLOp(canfold=True),
    'get_next_group_member':LLOp(canfold=True),
    'is_group_member_nonzero':LLOp(canfold=True),
    'extract_ushort':       LLOp(canfold=True),
    'combine_ushort':       LLOp(canfold=True),
    'gc_gettypeptr_group':  LLOp(canfold=True),
    'get_member_index':     LLOp(canfold=True),

    # __________ used by the JIT ________

    'jit_marker':           LLOp(),
    'jit_force_virtualizable':LLOp(canrun=True),
    'jit_force_virtual':    LLOp(canrun=True),
    'jit_force_quasi_immutable': LLOp(canrun=True),
    'get_exception_addr':   LLOp(),
    'get_exc_value_addr':   LLOp(),
    'do_malloc_fixedsize_clear':LLOp(canraise=(MemoryError,),canunwindgc=True),
    'do_malloc_varsize_clear':  LLOp(canraise=(MemoryError,),canunwindgc=True),
    'get_write_barrier_failing_case': LLOp(sideeffects=False),
    'get_write_barrier_from_array_failing_case': LLOp(sideeffects=False),
    'gc_get_type_info_group': LLOp(sideeffects=False),
    'll_read_timestamp': LLOp(canrun=True),

    # __________ GC operations __________

    'gc__collect':          LLOp(canunwindgc=True),
    'gc_free':              LLOp(),
    'gc_fetch_exception':   LLOp(),
    'gc_restore_exception': LLOp(),
    'gc_call_rtti_destructor': LLOp(),
    'gc_deallocate':        LLOp(),
    'gc_push_alive_pyobj':  LLOp(),
    'gc_pop_alive_pyobj':   LLOp(),
    'gc_reload_possibly_moved': LLOp(),
    # see rlib/objectmodel for gc_identityhash and gc_id
    'gc_identityhash':      LLOp(canraise=(MemoryError,), sideeffects=False,
                                 canunwindgc=True),
    'gc_id':                LLOp(canraise=(MemoryError,), sideeffects=False),
                                 # ^^^ but canunwindgc=False, as it is
                                 # allocating non-GC structures only
    'gc_obtain_free_space': LLOp(),
    'gc_set_max_heap_size': LLOp(),
    'gc_can_move'         : LLOp(sideeffects=False),
    'gc_thread_prepare'   : LLOp(canraise=(MemoryError,)),
                                 # ^^^ but canunwindgc=False, as it is
                                 # allocating non-GC structures only
    'gc_thread_run'       : LLOp(),
    'gc_thread_start'     : LLOp(),
    'gc_thread_die'       : LLOp(),
    'gc_thread_before_fork':LLOp(),   # returns an opaque address
    'gc_thread_after_fork': LLOp(),   # arguments: (result_of_fork, opaqueaddr)
    'gc_assume_young_pointers': LLOp(canrun=True),
    'gc_writebarrier_before_copy': LLOp(canrun=True),
    'gc_heap_stats'       : LLOp(canunwindgc=True),

    'gc_get_rpy_roots'    : LLOp(),
    'gc_get_rpy_referents': LLOp(),
    'gc_get_rpy_memory_usage': LLOp(),
    'gc_get_rpy_type_index': LLOp(),
    'gc_is_rpy_instance'  : LLOp(),
    'gc_dump_rpy_heap'    : LLOp(),
    'gc_typeids_z'        : LLOp(),

    # ------- JIT & GC interaction, only for some GCs ----------

    'gc_adr_of_nursery_free' : LLOp(),
    # ^^^ returns an address of nursery free pointer, for later modifications
    'gc_adr_of_nursery_top' : LLOp(),
    # ^^^ returns an address of pointer, since it can change at runtime
    'gc_adr_of_root_stack_top': LLOp(),
    # ^^^ returns the address of gcdata.root_stack_top (for shadowstack only)

    # experimental operations in support of thread cloning, only
    # implemented by the Mark&Sweep GC
    'gc_x_swap_pool':       LLOp(canraise=(MemoryError,), canunwindgc=True),
    'gc_x_clone':           LLOp(canraise=(MemoryError, RuntimeError),
                                 canunwindgc=True),
    'gc_x_size_header':     LLOp(),

    # for asmgcroot support to get the address of various static structures
    # see translator/c/src/mem.h for the valid indices
    'gc_asmgcroot_static':  LLOp(sideeffects=False),
    'gc_stack_bottom':      LLOp(canrun=True),

    # NOTE NOTE NOTE! don't forget *** canunwindgc=True *** for anything that
    # can go through a stack unwind, in particular anything that mallocs!

    # __________ weakrefs __________

    'weakref_create':       LLOp(canraise=(MemoryError,), sideeffects=False,
                                 canunwindgc=True),
    'weakref_deref':        LLOp(sideeffects=False),
    'cast_ptr_to_weakrefptr': LLOp(sideeffects=False), # no-op type hiding
    'cast_weakrefptr_to_ptr': LLOp(sideeffects=False), # no-op type revealing

    # __________ stackless operation(s) __________

    'yield_current_frame_to_caller': LLOp(canraise=(StackException,
                                                    RuntimeError)),
    #                               can always unwind, not just if stackless gc

    'resume_point':         LLOp(canraise=(Exception,)),
    'resume_state_create':  LLOp(canraise=(MemoryError,), canunwindgc=True),
    'resume_state_invoke':  LLOp(canraise=(Exception, StackException,
                                           RuntimeError)),
    'stack_frames_depth':   LLOp(sideeffects=False, canraise=(StackException,
                                                              RuntimeError)),
    'stack_switch':         LLOp(canraise=(StackException, RuntimeError)),
    'stack_unwind':         LLOp(canraise=(StackException, RuntimeError)),
    'stack_capture':        LLOp(canraise=(StackException, RuntimeError)),
    'get_stack_depth_limit':LLOp(sideeffects=False),
    'set_stack_depth_limit':LLOp(),

    'stack_current':        LLOp(sideeffects=False),

    # __________ misc operations __________

    'keepalive':            LLOp(),
    'same_as':              LLOp(canfold=True),
    'hint':                 LLOp(),
    'check_no_more_arg':    LLOp(canraise=(Exception,)),
    'check_self_nonzero':   LLOp(canraise=(Exception,)),
    'decode_arg':           LLOp(canraise=(Exception,)),
    'decode_arg_def':       LLOp(canraise=(Exception,)),
    'getslice':             LLOp(canraise=(Exception,)),
    'check_and_clear_exc':  LLOp(),

    # __________ debugging __________
    'debug_view':           LLOp(),
    'debug_print':          LLOp(canrun=True),
    'debug_start':          LLOp(canrun=True),
    'debug_stop':           LLOp(canrun=True),
    'have_debug_prints':    LLOp(canrun=True),
    'debug_pdb':            LLOp(),
    'debug_assert':         LLOp(tryfold=True),
    'debug_fatalerror':     LLOp(),
    'debug_llinterpcall':   LLOp(canraise=(Exception,)),
                                    # Python func call 'res=arg[0](*arg[1:])'
                                    # in backends, abort() or whatever is fine
    'debug_start_traceback':   LLOp(),
    'debug_record_traceback':  LLOp(),
    'debug_catch_exception':   LLOp(),
    'debug_reraise_traceback': LLOp(),
    'debug_print_traceback':   LLOp(),

    # __________ instrumentation _________
    'instrument_count':     LLOp(),

    # __________ ootype operations __________
    'new':                  LLOp(oo=True, canraise=(MemoryError,)),
    'runtimenew':           LLOp(oo=True, canraise=(MemoryError,)),
    'oonewcustomdict':      LLOp(oo=True, canraise=(MemoryError,)),
    'oonewarray':           LLOp(oo=True, canraise=(MemoryError,)),
    'oosetfield':           LLOp(oo=True),
    'oogetfield':           LLOp(oo=True, sideeffects=False, canrun=True),
    'oosend':               LLOp(oo=True, canraise=(Exception,)),
    'ooupcast':             LLOp(oo=True, canfold=True),
    'oodowncast':           LLOp(oo=True, canfold=True),
    'cast_to_object':       LLOp(oo=True, canfold=True),
    'cast_from_object':     LLOp(oo=True, canfold=True),
    'oononnull':            LLOp(oo=True, canfold=True),
    'ooisnot':              LLOp(oo=True, canfold=True),
    'ooisnull':             LLOp(oo=True, canfold=True),
    'oois':                 LLOp(oo=True, canfold=True),
    'instanceof':           LLOp(oo=True, canfold=True),
    'classof':              LLOp(oo=True, canfold=True),
    'subclassof':           LLOp(oo=True, canfold=True),
    'oostring':             LLOp(oo=True, sideeffects=False),
    'ooparse_int':          LLOp(oo=True, canraise=(ValueError,)),
    'ooparse_float':        LLOp(oo=True, canraise=(ValueError,)),
    'oounicode':            LLOp(oo=True, canraise=(UnicodeDecodeError,)),

    # _____ read frame var support ___
    'get_frame_base':       LLOp(sideeffects=False),
    'frame_info':           LLOp(sideeffects=False),
}
# ***** Run test_lloperation after changes. *****


    # __________ operations on PyObjects __________

from pypy.objspace.flow.operation import FunctionByName
opimpls = FunctionByName.copy()
opimpls['is_true'] = bool
for opname in opimpls:
    LL_OPERATIONS[opname] = LLOp(canraise=(Exception,), pyobj=True)
LL_OPERATIONS['simple_call'] = LLOp(canraise=(Exception,), pyobj=True)
del opname, FunctionByName

# ____________________________________________________________
# Post-processing

# Stick the opnames into the LLOp instances
for opname, opdesc in LL_OPERATIONS.iteritems():
    opdesc.opname = opname
del opname, opdesc

# Also export all operations in an attribute-based namespace.
# Example usage from LL helpers:  z = llop.int_add(Signed, x, y)

for opname, opdesc in LL_OPERATIONS.iteritems():
    setattr(llop, opname, opdesc)
del opname, opdesc
