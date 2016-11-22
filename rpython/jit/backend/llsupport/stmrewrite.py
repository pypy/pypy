from rpython.jit.backend.llsupport.rewrite import GcRewriterAssembler
from rpython.jit.backend.llsupport.descr import (
    CallDescr, ArrayOrFieldDescr, unpack_fielddescr)
from rpython.jit.metainterp.resoperation import (
    ResOperation, rop, ResOpWithDescr, OpHelpers)
from rpython.jit.metainterp.history import ConstInt
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import (have_debug_prints, debug_start, debug_stop,
                                debug_print)
from rpython.jit.backend.llsupport.symbolic import WORD


class GcStmRewriterAssembler(GcRewriterAssembler):
    # This class performs the same rewrites as its base class,
    # plus the rewrites described above.

    def __init__(self, *args):
        GcRewriterAssembler.__init__(self, *args)
        self.always_inevitable = False
        self.read_barrier_applied = {}

    def other_operation(self, op):
        opnum = op.getopnum()
        if opnum == rop.INCREMENT_DEBUG_COUNTER:
            self.emit_op(op)
            return

        assert opnum != rop.VEC_STORE # VEC things are not supported yet
        # ----------  transaction breaks  ----------
        if opnum == rop.STM_HINT_COMMIT_SOON:
            self.emitting_an_operation_that_can_collect()
            self.next_op_may_be_in_new_transaction()
            self._do_stm_call('stm_hint_commit_soon', [])
            return
        # ----------  jump, finish, guard_not_forced_2  ----------
        if (opnum == rop.JUMP or opnum == rop.FINISH
                or opnum == rop.GUARD_NOT_FORCED_2):
            self.possibly_add_dummy_allocation()
            self.emit_op(op)
            return
        # ----------  pure operations, guards  ----------
        if rop.is_always_pure(opnum) or rop.is_guard(opnum) or rop.is_ovf(opnum):
            self.emit_op(op)
            return
        # # ----------  non-pure getfields  ----------
        if opnum in (rop.GETARRAYITEM_GC_I, rop.GETARRAYITEM_GC_F,
                     rop.GETARRAYITEM_GC_R,
                     rop.GETINTERIORFIELD_GC_I,
                     rop.GETINTERIORFIELD_GC_F, rop.GETINTERIORFIELD_GC_R):
            #self.handle_getfields(op)
            self.emit_op(op)
            return
        # ----------  calls  ----------
        if rop.is_call(opnum):
            self.next_op_may_be_in_new_transaction()
            #
            if opnum in (rop.CALL_RELEASE_GIL_I,
                         rop.CALL_RELEASE_GIL_F, rop.CALL_RELEASE_GIL_N):
                # self.fallback_inevitable(op)
                # is done by assembler._release_gil_shadowstack()
                self.emit_op(op)
            elif opnum in (rop.CALL_ASSEMBLER_I, rop.CALL_ASSEMBLER_R,
                           rop.CALL_ASSEMBLER_F, rop.CALL_ASSEMBLER_N):
                assert 0   # case handled by the parent class
            else:
                # only insert become_inevitable if calling a
                # non-transactionsafe and non-releasegil function
                descr = op.getdescr()
                assert not descr or isinstance(descr, CallDescr)

                if not descr or not descr.get_extra_info() \
                      or descr.get_extra_info().call_needs_inevitable():
                    self.fallback_inevitable(op)
                else:
                    self.emit_op(op)
            return
        # ----------  setters for pure fields  ----------
        if opnum in (rop.STRSETITEM, rop.UNICODESETITEM):
            self.handle_setters_for_pure_fields(op, 0)
            return
        # ----------  copystrcontent  ----------
        if opnum in (rop.COPYSTRCONTENT, rop.COPYUNICODECONTENT):
            self.handle_setters_for_pure_fields(op, 1)
            return
        # ----------  raw getfields and setfields and arrays  ----------
        if opnum in (rop.GETFIELD_RAW_F, rop.GETFIELD_RAW_I,
                     rop.GETFIELD_RAW_R, rop.SETFIELD_RAW,
                     rop.GETARRAYITEM_RAW_F, rop.GETARRAYITEM_RAW_I,
                     rop.SETARRAYITEM_RAW,):
            if self.maybe_handle_raw_accesses(op):
                return
        # ----------  labels  ----------
        if opnum == rop.LABEL:
            # note that the parent class also clears some things on a LABEL
            self.next_op_may_be_in_new_transaction()
            self.emit_op(op)
            return
        # ----------  other ignored ops  ----------
        if opnum in (rop.STM_SHOULD_BREAK_TRANSACTION, rop.FORCE_TOKEN,
                     rop.ENTER_PORTAL_FRAME, rop.LEAVE_PORTAL_FRAME,
                     rop.JIT_DEBUG, rop.KEEPALIVE,
                     rop.QUASIIMMUT_FIELD, rop.RECORD_EXACT_CLASS,
                     rop.RESTORE_EXCEPTION, rop.SAVE_EXCEPTION,
                     rop.SAVE_EXC_CLASS,):
            self.emit_op(op)
            return
        # ----------  fall-back  ----------
        # Check that none of the ops handled here can collect.
        # This is not done by the fallback here
        assert not rop.is_call(opnum) and not rop.is_malloc(opnum)
        self.fallback_inevitable(op)

    def handle_call_assembler(self, op):
        # required, because this op is only handled in super class
        # and we didn't call this line yet:
        self.next_op_may_be_in_new_transaction()
        GcRewriterAssembler.handle_call_assembler(self, op)

    def next_op_may_be_in_new_transaction(self):
        self.always_inevitable = False
        self.read_barrier_applied.clear()

    def emit_gc_load_or_indexed(self, op, ptr_box, index_box, itemsize, factor, offset, sign, type='i'):
        # XXX missing optimitations: the placement of stm_read should
        # ideally be delayed for a bit longer after the getfields; if we
        # group together several stm_reads then we can save one
        # instruction; if delayed over a cond_call_gc_wb then we can
        # omit the stm_read completely; ...
        newop = GcRewriterAssembler.emit_gc_load_or_indexed(
            self, op, ptr_box, index_box, itemsize, factor, offset, sign, type)
        ptr_box = newop.getarg(0)
        if op:
            is_pure = rop.is_always_pure(op.getopnum())
            if not is_pure and isinstance(op, ResOpWithDescr):
                is_pure = OpHelpers.is_pure_with_descr(op.getopnum(), op.getdescr())
            if (ptr_box.type == 'r'  # not raw
                and not is_pure      # needs stm_read
                and ptr_box not in self.read_barrier_applied
                and not self.write_barrier_applied(ptr_box)):
                op1 = ResOperation(rop.STM_READ, [ptr_box], None)
                self.read_barrier_applied[ptr_box] = None
                self.emit_op(op1)
        return newop



    def possibly_add_dummy_allocation(self):
        # was necessary in C7 for others to commit, but in C8 it is only
        # necessary for requesting major GCs. I think we better avoid this
        # overhead for tight loops and wait a bit longer in that case.
        # ^^^ is not the entire truth: we currently measure the amount of work
        # done in a transaction by number of bytes allocated. It means that
        # now, tight loops not doing any allocation are not accounted for.
        # However, given that not doing these allocations improves
        # lee_router_tm.py by a factor of 2.5x, we better deal with it in
        # another way.
        pass
        # if not self.does_any_allocation:
        #     # do a fake allocation since this is needed to check
        #     # for requested safe-points:
        #     self.does_any_allocation = True

        #     # minimum size for the slowpath of MALLOC_NURSERY:
        #     size = self.gc_ll_descr.minimal_size_in_nursery
        #     op = ResOperation(rop.LABEL, []) # temp, will be replaced by gen_malloc_nursery
        #     assert self._op_malloc_nursery is None # no ongoing allocation
        #     self.gen_malloc_nursery(size, op)

    def must_apply_write_barrier(self, val, v):
        # also apply for non-ref values
        return not self.write_barrier_applied(val)

    def gen_initialize_tid(self, v_newgcobj, tid):
        # Also emit a setfield that zeroes the stm_flags field.
        # This is necessary since we merge some allocations together and
        # stmgc assumes flags to be cleared.
        assert self.gc_ll_descr.fielddescr_stmflags is not None
        self.emit_setfield(v_newgcobj, self.c_zero,
                           descr=self.gc_ll_descr.fielddescr_stmflags)
        return GcRewriterAssembler.gen_initialize_tid(self, v_newgcobj, tid)

    @specialize.arg(1)
    def _do_stm_call(self, funcname, args):
        addr = self.gc_ll_descr.get_malloc_fn_addr(funcname)
        descr = getattr(self.gc_ll_descr, funcname + '_descr')
        op1 = ResOperation(rop.CALL_N, [ConstInt(addr)] + args,
                           descr=descr)
        self.emit_op(op1)

    def fallback_inevitable(self, op):
        if not self.always_inevitable:
            self.emitting_an_operation_that_can_collect()
            self._do_stm_call('stm_try_inevitable', [])
            self.always_inevitable = True
        self.emit_op(op)
        debug_print("fallback for", op.repr({}))

    def maybe_handle_raw_accesses(self, op):
        descr = op.getdescr()
        assert isinstance(descr, ArrayOrFieldDescr)
        if descr.stm_dont_track_raw_accesses:
            self.emit_op(op)
            return True
        return False

    def handle_setters_for_pure_fields(self, op, targetindex):
        val = op.getarg(targetindex)
        if self.must_apply_write_barrier(val, None):
            self.gen_write_barrier(val)
        self.emit_op(op)
