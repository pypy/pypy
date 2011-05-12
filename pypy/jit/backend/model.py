from pypy.rlib.debug import debug_start, debug_print, debug_stop
from pypy.jit.metainterp import history, compile


class AbstractCPU(object):
    supports_floats = False
    supports_longlong = False
    # ^^^ This is only useful on 32-bit platforms.  If True,
    # longlongs are supported by the JIT, but stored as doubles.
    # Boxes and Consts are BoxFloats and ConstFloats.

    done_with_this_frame_void_v = -1
    done_with_this_frame_int_v = -1
    done_with_this_frame_ref_v = -1
    done_with_this_frame_float_v = -1
    exit_frame_with_exception_v = -1
    total_compiled_loops = 0
    total_compiled_bridges = 0
    total_freed_loops = 0
    total_freed_bridges = 0

    def __init__(self):
        self.fail_descr_list = []
        self.fail_descr_free_list = []

    def reserve_some_free_fail_descr_number(self):
        lst = self.fail_descr_list
        if len(self.fail_descr_free_list) > 0:
            n = self.fail_descr_free_list.pop()
            assert lst[n] is None
        else:
            n = len(lst)
            lst.append(None)
        return n

    def get_fail_descr_number(self, descr):
        assert isinstance(descr, history.AbstractFailDescr)
        n = descr.index
        if n < 0:
            n = self.reserve_some_free_fail_descr_number()
            self.fail_descr_list[n] = descr
            descr.index = n
        return n

    def get_fail_descr_from_number(self, n):
        return self.fail_descr_list[n]

    def setup_once(self):
        """Called once by the front-end when the program starts."""
        pass

    def finish_once(self):
        """Called once by the front-end when the program stops."""
        pass

    def compile_loop(self, inputargs, operations, looptoken, log=True):
        """Assemble the given loop.
        Should create and attach a fresh CompiledLoopToken to
        looptoken.compiled_loop_token and stick extra attributes
        on it to point to the compiled loop in assembler.

        Optionally, return a ``labels`` dictionary, which maps each operation
        to its offset in the compiled code.  The ``labels`` dictionary is then
        used by the operation logger to print the offsets in the log.  The
        offset representing the end of the last operation is stored in
        ``labels[None]``: note that this might not coincide with the end of
        the loop, because usually in the loop footer there is code which does
        not belong to any particular operation.
        """
        raise NotImplementedError

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True):
        """Assemble the bridge.
        The FailDescr is the descr of the original guard that failed.

        Optionally, return a ``labels`` dictionary.  See the docstring of
        ``compiled_loop`` for more informations about it.
        """
        raise NotImplementedError    

    def dump_loop_token(self, looptoken):
        """Print a disassembled version of looptoken to stdout"""
        raise NotImplementedError

    def execute_token(self, looptoken):
        """Execute the generated code referenced by the looptoken.
        Returns the descr of the last executed operation: either the one
        attached to the failing guard, or the one attached to the FINISH.
        Use set_future_value_xxx() before, and get_latest_value_xxx() after.
        """
        raise NotImplementedError

    def set_future_value_int(self, index, intvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_float(self, index, floatvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_ref(self, index, objvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def get_latest_value_int(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns an int."""
        raise NotImplementedError

    def get_latest_value_float(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns a float."""
        raise NotImplementedError

    def get_latest_value_ref(self, index):
        """Returns the value for the index'th argument to the
        last executed operation (from 'fail_args' if it was a guard,
        or from 'args' if it was a FINISH).  Returns a ptr or an obj."""
        raise NotImplementedError

    def get_latest_value_count(self):
        """Return how many values are ready to be returned by
        get_latest_value_xxx().  Only after a guard failure; not
        necessarily correct after a FINISH."""
        raise NotImplementedError

    def get_latest_force_token(self):
        """After a GUARD_NOT_FORCED fails, this function returns the
        same FORCE_TOKEN result as the one in the just-failed loop."""
        raise NotImplementedError

    def clear_latest_values(self, count):
        """Clear the latest values (at least the ref ones), so that
        they no longer keep objects alive.  'count' is the number of
        values -- normally get_latest_value_count()."""
        raise NotImplementedError

    def grab_exc_value(self):
        """Return and clear the exception set by the latest execute_token(),
        when it exits due to a failure of a GUARD_EXCEPTION or
        GUARD_NO_EXCEPTION.  (Returns a GCREF)"""        # XXX remove me
        raise NotImplementedError

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        """Redirect oldlooptoken to newlooptoken.  More precisely, it is
        enough to redirect all CALL_ASSEMBLERs already compiled that call
        oldlooptoken so that from now own they will call newlooptoken."""
        raise NotImplementedError

    def invalidate_loop(self, looptoken):
        """Activate all GUARD_NOT_INVALIDATED in the loop and its attached
        bridges.  Before this call, all GUARD_NOT_INVALIDATED do nothing;
        after this call, they all fail.  Note that afterwards, if one such
        guard fails often enough, it has a bridge attached to it; it is
        possible then to re-call invalidate_loop() on the same looptoken,
        which must invalidate all newer GUARD_NOT_INVALIDATED, but not the
        old one that already has a bridge attached to it."""
        raise NotImplementedError

    def free_loop_and_bridges(self, compiled_loop_token):
        """This method is called to free resources (machine code,
        references to resume guards, etc.) allocated by the compilation
        of a loop and all bridges attached to it.  After this call, the
        frontend cannot use this compiled loop any more; in fact, it
        guarantees that at the point of the call to free_code_group(),
        none of the corresponding assembler is currently running.
        """
        # The base class provides a limited implementation: freeing the
        # resume descrs.  This is already quite helpful, because the
        # resume descrs are the largest consumers of memory (about 3x
        # more than the assembler, in the case of the x86 backend).
        lst = self.fail_descr_list
        # We expect 'compiled_loop_token' to be itself garbage-collected soon,
        # but better safe than sorry: be ready to handle several calls to
        # free_loop_and_bridges() for the same compiled_loop_token.
        faildescr_indices = compiled_loop_token.faildescr_indices
        compiled_loop_token.faildescr_indices = []
        for n in faildescr_indices:
            lst[n] = None
        self.fail_descr_free_list.extend(faildescr_indices)

    @staticmethod
    def sizeof(S):
        raise NotImplementedError

    @staticmethod
    def fielddescrof(S, fieldname):
        """Return the Descr corresponding to field 'fieldname' on the
        structure 'S'.  It is important that this function (at least)
        caches the results."""
        raise NotImplementedError

    @staticmethod
    def arraydescrof(A):
        raise NotImplementedError

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT):
        # FUNC is the original function type, but ARGS is a list of types
        # with Voids removed
        raise NotImplementedError

    @staticmethod
    def methdescrof(SELFTYPE, methname):
        # must return a subclass of history.AbstractMethDescr
        raise NotImplementedError

    @staticmethod
    def typedescrof(TYPE):
        raise NotImplementedError

    # ---------- the backend-dependent operations ----------

    # lltype specific operations
    # --------------------------

    def bh_getarrayitem_gc_i(self, arraydescr, array, index):
        raise NotImplementedError
    def bh_getarrayitem_gc_r(self, arraydescr, array, index):
        raise NotImplementedError
    def bh_getarrayitem_gc_f(self, arraydescr, array, index):
        raise NotImplementedError

    def bh_getfield_gc_i(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_r(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_gc_f(self, struct, fielddescr):
        raise NotImplementedError

    def bh_getfield_raw_i(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_r(self, struct, fielddescr):
        raise NotImplementedError
    def bh_getfield_raw_f(self, struct, fielddescr):
        raise NotImplementedError

    def bh_new(self, sizedescr):
        raise NotImplementedError
    def bh_new_with_vtable(self, sizedescr, vtable):
        raise NotImplementedError
    def bh_new_array(self, arraydescr, length):
        raise NotImplementedError
    def bh_newstr(self, length):
        raise NotImplementedError
    def bh_newunicode(self, length):
        raise NotImplementedError

    def bh_arraylen_gc(self, arraydescr, array):
        raise NotImplementedError

    def bh_classof(self, struct):
        raise NotImplementedError

    def bh_setarrayitem_gc_i(self, arraydescr, array, index, newvalue):
        raise NotImplementedError
    def bh_setarrayitem_gc_r(self, arraydescr, array, index, newvalue):
        raise NotImplementedError
    def bh_setarrayitem_gc_f(self, arraydescr, array, index, newvalue):
        raise NotImplementedError

    def bh_setfield_gc_i(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_r(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_gc_f(self, struct, fielddescr, newvalue):
        raise NotImplementedError

    def bh_setfield_raw_i(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_r(self, struct, fielddescr, newvalue):
        raise NotImplementedError
    def bh_setfield_raw_f(self, struct, fielddescr, newvalue):
        raise NotImplementedError

    def bh_call_i(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_r(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_f(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError
    def bh_call_v(self, func, calldescr, args_i, args_r, args_f):
        raise NotImplementedError

    def bh_strlen(self, string):
        raise NotImplementedError
    def bh_strgetitem(self, string, index):
        raise NotImplementedError
    def bh_unicodelen(self, string):
        raise NotImplementedError
    def bh_unicodegetitem(self, string, index):
        raise NotImplementedError
    def bh_strsetitem(self, string, index, newvalue):
        raise NotImplementedError
    def bh_unicodesetitem(self, string, index, newvalue):
        raise NotImplementedError

    def force(self, force_token):
        raise NotImplementedError


class CompiledLoopToken(object):
    asmmemmgr_blocks = None
    asmmemmgr_gcroots = 0

    def __init__(self, cpu, number):
        cpu.total_compiled_loops += 1
        self.cpu = cpu
        self.number = number
        self.bridges_count = 0
        # This growing list gives the 'descr_number' of all fail descrs
        # that belong to this loop or to a bridge attached to it.
        # Filled by the frontend calling record_faildescr_index().
        self.faildescr_indices = []
        self.invalidate_positions = []
        debug_start("jit-mem-looptoken-alloc")
        debug_print("allocating Loop #", self.number)
        debug_stop("jit-mem-looptoken-alloc")

    def record_faildescr_index(self, n):
        self.faildescr_indices.append(n)

    def reserve_and_record_some_faildescr_index(self):
        # like record_faildescr_index(), but invent and return a new,
        # unused faildescr index
        n = self.cpu.reserve_some_free_fail_descr_number()
        self.record_faildescr_index(n)
        return n

    def compiling_a_bridge(self):
        self.cpu.total_compiled_bridges += 1
        self.bridges_count += 1
        debug_start("jit-mem-looptoken-alloc")
        debug_print("allocating Bridge #", self.bridges_count, "of Loop #", self.number)
        debug_stop("jit-mem-looptoken-alloc")

    def __del__(self):
        debug_start("jit-mem-looptoken-free")
        debug_print("freeing Loop #", self.number, 'with',
                    self.bridges_count, 'attached bridges')
        self.cpu.free_loop_and_bridges(self)
        self.cpu.total_freed_loops += 1
        self.cpu.total_freed_bridges += self.bridges_count
        debug_stop("jit-mem-looptoken-free")
