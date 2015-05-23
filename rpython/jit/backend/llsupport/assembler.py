from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.memcpy import memcpy_fn, memset_fn
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.backend.llsupport.codemap import CodemapBuilder
from rpython.jit.metainterp.history import (INT, REF, FLOAT, JitCellToken,
    ConstInt, BoxInt, AbstractFailDescr)
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.rlib import rgc
from rpython.rlib.debug import (debug_start, debug_stop, have_debug_prints_for,
                                debug_print)
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import specialize, compute_unique_id
from rpython.rtyper.annlowlevel import cast_instance_to_gcref, llhelper
from rpython.rtyper.lltypesystem import rffi, lltype


DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER',
    # 'b'ridge, 'l'abel or # 'e'ntry point
    ('i', lltype.Signed),      # first field, at offset 0
    ('type', lltype.Char),
    ('number', lltype.Signed)
)


class GuardToken(object):
    def __init__(self, cpu, gcmap, faildescr, failargs, fail_locs, exc,
                 frame_depth, is_guard_not_invalidated, is_guard_not_forced):
        assert isinstance(faildescr, AbstractFailDescr)
        self.cpu = cpu
        self.faildescr = faildescr
        self.failargs = failargs
        self.fail_locs = fail_locs
        self.gcmap = self.compute_gcmap(gcmap, failargs,
                                        fail_locs, frame_depth)
        self.exc = exc
        self.is_guard_not_invalidated = is_guard_not_invalidated
        self.is_guard_not_forced = is_guard_not_forced

    def compute_gcmap(self, gcmap, failargs, fail_locs, frame_depth):
        # note that regalloc has a very similar compute, but
        # one that does iteration over all bindings, so slightly different,
        # eh
        input_i = 0
        for i in range(len(failargs)):
            arg = failargs[i]
            if arg is None:
                continue
            loc = fail_locs[input_i]
            input_i += 1
            if arg.type == REF:
                loc = fail_locs[i]
                if loc.is_core_reg():
                    val = self.cpu.all_reg_indexes[loc.value]
                else:
                    val = loc.get_position() + self.cpu.JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap


class BaseAssembler(object):
    """ Base class for Assembler generator in real backends
    """

    def __init__(self, cpu, translate_support_code=False):
        self.cpu = cpu
        self.memcpy_addr = 0
        self.memset_addr = 0
        self.rtyper = cpu.rtyper
        self._debug = False

    def setup_once(self):
        # the address of the function called by 'new'
        gc_ll_descr = self.cpu.gc_ll_descr
        gc_ll_descr.initialize()
        if hasattr(gc_ll_descr, 'minimal_size_in_nursery'):
            self.gc_minimal_size_in_nursery = gc_ll_descr.minimal_size_in_nursery
        else:
            self.gc_minimal_size_in_nursery = 0
        if hasattr(gc_ll_descr, 'gcheaderbuilder'):
            self.gc_size_of_header = gc_ll_descr.gcheaderbuilder.size_gc_header
        else:
            self.gc_size_of_header = WORD # for tests
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self.memset_addr = self.cpu.cast_ptr_to_int(memset_fn)
        self._build_failure_recovery(False, withfloats=False)
        self._build_failure_recovery(True, withfloats=False)
        self._build_wb_slowpath(False)
        self._build_wb_slowpath(True)
        self._build_wb_slowpath(False, for_frame=True)
        # only one of those
        self.build_frame_realloc_slowpath()
        if self.cpu.supports_floats:
            self._build_failure_recovery(False, withfloats=True)
            self._build_failure_recovery(True, withfloats=True)
            self._build_wb_slowpath(False, withfloats=True)
            self._build_wb_slowpath(True, withfloats=True)
        self._build_propagate_exception_path()
        if gc_ll_descr.get_malloc_slowpath_addr is not None:
            # generate few slowpaths for various cases
            self.malloc_slowpath = self._build_malloc_slowpath(kind='fixed')
            self.malloc_slowpath_varsize = self._build_malloc_slowpath(
                kind='var')
        if hasattr(gc_ll_descr, 'malloc_str'):
            self.malloc_slowpath_str = self._build_malloc_slowpath(kind='str')
        else:
            self.malloc_slowpath_str = None
        if hasattr(gc_ll_descr, 'malloc_unicode'):
            self.malloc_slowpath_unicode = self._build_malloc_slowpath(
                kind='unicode')
        else:
            self.malloc_slowpath_unicode = None
        self.cond_call_slowpath = [self._build_cond_call_slowpath(False, False),
                                   self._build_cond_call_slowpath(False, True),
                                   self._build_cond_call_slowpath(True, False),
                                   self._build_cond_call_slowpath(True, True)]

        self._build_stack_check_slowpath()
        self._build_release_gil(gc_ll_descr.gcrootmap)
        if not self._debug:
            # if self._debug is already set it means that someone called
            # set_debug by hand before initializing the assembler. Leave it
            # as it is
            self.set_debug(have_debug_prints_for('jit-backend-counts'))
        # when finishing, we only have one value at [0], the rest dies
        self.gcmap_for_finish = lltype.malloc(jitframe.GCMAP, 1,
                                              flavor='raw',
                                              track_allocation=False)
        self.gcmap_for_finish[0] = r_uint(1)

    def setup(self, looptoken):
        if self.cpu.HAS_CODEMAP:
            self.codemap_builder = CodemapBuilder()
        self._finish_gcmap = lltype.nullptr(jitframe.GCMAP)

    def set_debug(self, v):
        r = self._debug
        self._debug = v
        return r

    def rebuild_faillocs_from_descr(self, descr, inputargs):
        locs = []
        GPR_REGS = len(self.cpu.gen_regs)
        XMM_REGS = len(self.cpu.float_regs)
        input_i = 0
        if self.cpu.IS_64_BIT:
            coeff = 1
        else:
            coeff = 2
        for pos in descr.rd_locs:
            pos = rffi.cast(lltype.Signed, pos)
            if pos == 0xFFFF:
                continue
            elif pos < GPR_REGS:
                locs.append(self.cpu.gen_regs[pos])
            elif pos < GPR_REGS + XMM_REGS * coeff:
                pos = (pos - GPR_REGS) // coeff
                locs.append(self.cpu.float_regs[pos])
            else:
                i = pos - self.cpu.JITFRAME_FIXED_SIZE
                assert i >= 0
                tp = inputargs[input_i].type
                locs.append(self.new_stack_loc(i, tp))
            input_i += 1
        return locs

    def store_info_on_descr(self, startspos, guardtok):
        withfloats = False
        for box in guardtok.failargs:
            if box is not None and box.type == FLOAT:
                withfloats = True
                break
        exc = guardtok.exc
        target = self.failure_recovery_code[exc + 2 * withfloats]
        fail_descr = cast_instance_to_gcref(guardtok.faildescr)
        fail_descr = rffi.cast(lltype.Signed, fail_descr)
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        positions = [rffi.cast(rffi.USHORT, 0)] * len(guardtok.fail_locs)
        for i, loc in enumerate(guardtok.fail_locs):
            if loc is None:
                position = 0xFFFF
            elif loc.is_stack():
                assert (loc.value & (WORD - 1)) == 0, \
                    "store_info_on_descr: misaligned"
                position = (loc.value - base_ofs) // WORD
                assert 0 < position < 0xFFFF, "store_info_on_descr: overflow!"
            else:
                assert loc is not self.cpu.frame_reg # for now
                if self.cpu.IS_64_BIT:
                    coeff = 1
                else:
                    coeff = 2
                if loc.is_float():
                    position = len(self.cpu.gen_regs) + loc.value * coeff
                else:
                    position = self.cpu.all_reg_indexes[loc.value]
            positions[i] = rffi.cast(rffi.USHORT, position)
        # write down the positions of locs
        guardtok.faildescr.rd_locs = positions
        return fail_descr, target

    def enter_portal_frame(self, op):
        if self.cpu.HAS_CODEMAP:
            self.codemap_builder.enter_portal_frame(op.getarg(0).getint(),
                                                    op.getarg(1).getint(),
                                                    self.mc.get_relative_pos())

    def leave_portal_frame(self, op):
        if self.cpu.HAS_CODEMAP:
            self.codemap_builder.leave_portal_frame(op.getarg(0).getint(),
                                                    self.mc.get_relative_pos())

    def call_assembler(self, op, guard_op, argloc, vloc, result_loc, tmploc):
        self._store_force_index(guard_op)
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        #
        # Write a call to the target assembler
        # we need to allocate the frame, keep in sync with runner's
        # execute_token
        jd = descr.outermost_jitdriver_sd
        self._call_assembler_emit_call(self.imm(descr._ll_function_addr),
                                        argloc, tmploc)

        if op.result is None:
            assert result_loc is None
            value = self.cpu.done_with_this_frame_descr_void
        else:
            kind = op.result.type
            if kind == INT:
                assert result_loc is tmploc
                value = self.cpu.done_with_this_frame_descr_int
            elif kind == REF:
                assert result_loc is tmploc
                value = self.cpu.done_with_this_frame_descr_ref
            elif kind == FLOAT:
                value = self.cpu.done_with_this_frame_descr_float
            else:
                raise AssertionError(kind)

        gcref = cast_instance_to_gcref(value)
        if gcref:
            rgc._make_sure_does_not_move(gcref)
        value = rffi.cast(lltype.Signed, gcref)
        je_location = self._call_assembler_check_descr(value, tmploc)
        #
        # Path A: use assembler_helper_adr
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)

        self._call_assembler_emit_helper_call(self.imm(asm_helper_adr),
                                                [tmploc, vloc], result_loc)

        jmp_location = self._call_assembler_patch_je(result_loc, je_location)

        # Path B: fast path.  Must load the return value

        #
        self._call_assembler_load_result(op, result_loc)
        #
        # Here we join Path A and Path B again
        self._call_assembler_patch_jmp(jmp_location)
        # XXX here should be emitted guard_not_forced, but due
        #     to incompatibilities in how it's done, we leave it for the
        #     caller to deal with

    @specialize.argtype(1)
    def _inject_debugging_code(self, looptoken, operations, tp, number):
        if self._debug:
            s = 0
            for op in operations:
                s += op.getopnum()

            newoperations = []
            self._append_debugging_code(newoperations, tp, number,
                                        None)
            for op in operations:
                newoperations.append(op)
                if op.getopnum() == rop.LABEL:
                    self._append_debugging_code(newoperations, 'l', number,
                                                op.getdescr())
            operations = newoperations
        return operations

    def _append_debugging_code(self, operations, tp, number, token):
        counter = self._register_counter(tp, number, token)
        c_adr = ConstInt(rffi.cast(lltype.Signed, counter))
        operations.append(
            ResOperation(rop.INCREMENT_DEBUG_COUNTER, [c_adr], None))

    def _register_counter(self, tp, number, token):
        # YYY very minor leak -- we need the counters to stay alive
        # forever, just because we want to report them at the end
        # of the process

        # XXX the numbers here are ALMOST unique, but not quite, use a counter
        #     or something
        struct = lltype.malloc(DEBUG_COUNTER, flavor='raw',
                               track_allocation=False)
        struct.i = 0
        struct.type = tp
        if tp == 'b' or tp == 'e':
            struct.number = number
        else:
            assert token
            struct.number = compute_unique_id(token)
        self.loop_run_counters.append(struct)
        return struct

    def finish_once(self):
        if self._debug:
            debug_start('jit-backend-counts')
            for i in range(len(self.loop_run_counters)):
                struct = self.loop_run_counters[i]
                if struct.type == 'l':
                    prefix = 'TargetToken(%d)' % struct.number
                else:
                    num = struct.number
                    if num == -1:
                        num = '-1'
                    else:
                        num = str(r_uint(num))
                    if struct.type == 'b':
                        prefix = 'bridge %s' % num
                    else:
                        prefix = 'entry %s' % num
                debug_print(prefix + ':' + str(struct.i))
            debug_stop('jit-backend-counts')

    @staticmethod
    @rgc.no_collect
    def _reacquire_gil_asmgcc(css, old_rpy_fastgil):
        # Before doing an external call, 'rpy_fastgil' is initialized to
        # be equal to css.  This function is called if we find out after
        # the call that it is no longer equal to css.  See description
        # in translator/c/src/thread_pthread.c.

        if old_rpy_fastgil == 0:
            # this case occurs if some other thread stole the GIL but
            # released it again.  What occurred here is that we changed
            # 'rpy_fastgil' from 0 to 1, thus successfully reaquiring the
            # GIL.
            pass

        elif old_rpy_fastgil == 1:
            # 'rpy_fastgil' was (and still is) locked by someone else.
            # We need to wait for the regular mutex.
            after = rffi.aroundstate.after
            if after:
                after()
        else:
            # stole the GIL from a different thread that is also
            # currently in an external call from the jit.  Attach
            # the 'old_rpy_fastgil' into the chained list.
            from rpython.memory.gctransform import asmgcroot
            oth = rffi.cast(asmgcroot.ASM_FRAMEDATA_HEAD_PTR, old_rpy_fastgil)
            next = asmgcroot.gcrootanchor.next
            oth.next = next
            oth.prev = asmgcroot.gcrootanchor
            asmgcroot.gcrootanchor.next = oth
            next.prev = oth

        # similar to trackgcroot.py:pypy_asm_stackwalk, second part:
        # detach the 'css' from the chained list
        from rpython.memory.gctransform import asmgcroot
        old = rffi.cast(asmgcroot.ASM_FRAMEDATA_HEAD_PTR, css)
        prev = old.prev
        next = old.next
        prev.next = next
        next.prev = prev

    @staticmethod
    @rgc.no_collect
    def _reacquire_gil_shadowstack():
        # Simplified version of _reacquire_gil_asmgcc(): in shadowstack mode,
        # 'rpy_fastgil' contains only zero or non-zero, and this is only
        # called when the old value stored in 'rpy_fastgil' was non-zero
        # (i.e. still locked, must wait with the regular mutex)
        after = rffi.aroundstate.after
        if after:
            after()

    _REACQGIL0_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))
    _REACQGIL2_FUNC = lltype.Ptr(lltype.FuncType([rffi.CCHARP, lltype.Signed],
                                                 lltype.Void))

    def _build_release_gil(self, gcrootmap):
        if gcrootmap is None or gcrootmap.is_shadow_stack:
            reacqgil_func = llhelper(self._REACQGIL0_FUNC,
                                     self._reacquire_gil_shadowstack)
            self.reacqgil_addr = self.cpu.cast_ptr_to_int(reacqgil_func)
        else:
            reacqgil_func = llhelper(self._REACQGIL2_FUNC,
                                     self._reacquire_gil_asmgcc)
            self.reacqgil_addr = self.cpu.cast_ptr_to_int(reacqgil_func)

    def _is_asmgcc(self):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        return bool(gcrootmap) and not gcrootmap.is_shadow_stack


def debug_bridge(descr_number, rawstart, codeendpos):
    debug_start("jit-backend-addr")
    debug_print("bridge out of Guard 0x%x has address 0x%x to 0x%x" %
                (r_uint(descr_number), r_uint(rawstart),
                    r_uint(rawstart + codeendpos)))
    debug_stop("jit-backend-addr")

