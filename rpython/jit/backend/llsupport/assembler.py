
from rpython.rlib import rgc
from rpython.rlib.rarithmetic import r_uint
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.metainterp.history import INT, REF, FLOAT, JitCellToken
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.lltypesystem import rffi, lltype

class GuardToken(object):
    def __init__(self, cpu, gcmap, faildescr, failargs, fail_locs, exc,
                 frame_depth, is_guard_not_invalidated, is_guard_not_forced):
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
                if loc.is_reg():
                    val = self.cpu.all_reg_indexes[loc.value]
                else:
                    val = loc.get_position() + self.cpu.JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap


class BaseAssembler(object):
    """ Base class for Assembler generator in real backends
    """
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
            if pos == -1:
                continue
            elif pos < GPR_REGS * WORD:
                locs.append(self.cpu.gen_regs[pos // WORD])
            elif pos < (GPR_REGS + XMM_REGS * coeff) * WORD:
                pos = (pos // WORD - GPR_REGS) // coeff
                locs.append(self.cpu.float_regs[pos])
            else:
                i = pos // WORD - self.cpu.JITFRAME_FIXED_SIZE
                assert i >= 0
                tp = inputargs[input_i].type
                locs.append(self.new_stack_loc(i, pos, tp))
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
        positions = [0] * len(guardtok.fail_locs)
        for i, loc in enumerate(guardtok.fail_locs):
            if loc is None:
                positions[i] = -1
            elif loc.is_stack():
                positions[i] = loc.value - base_ofs
            else:
                assert loc is not self.cpu.frame_reg # for now
                if self.cpu.IS_64_BIT:
                    coeff = 1
                else:
                    coeff = 2
                if loc.is_float():
                    v = len(self.cpu.gen_regs) + loc.value * coeff
                else:
                    v = self.cpu.all_reg_indexes[loc.value]
                positions[i] = v * WORD
        # write down the positions of locs
        guardtok.faildescr.rd_locs = positions
        # we want the descr to keep alive
        guardtok.faildescr.rd_loop_token = self.current_clt
        return fail_descr, target

    def call_assembler(self, op, guard_op, frame_loc, argloc,
                       vloc, result_loc, tmploc):
        self._store_force_index(guard_op)
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        #
        # Write a call to the target assembler
        # we need to allocate the frame, keep in sync with runner's
        # execute_token
        jd = descr.outermost_jitdriver_sd
        self._emit_call(self.imm(descr._ll_function_addr),
                        [argloc], 0, tmp=tmploc)
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
        rgc._make_sure_does_not_move(gcref)
        value = rffi.cast(lltype.Signed, gcref)
        je_location = self._call_assembler_check_descr(value, tmploc)
        #
        # Path A: use assembler_helper_adr
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)

        self._emit_call(self.imm(asm_helper_adr),
                        [tmploc, vloc], 0, tmp=self._second_tmp_reg)

        jmp_location = self._call_assembler_patch_je(result_loc, je_location)

        # Path B: fast path.  Must load the return value, and reset the token

        # Reset the vable token --- XXX really too much special logic here:-(
        if jd.index_of_virtualizable >= 0:
            self._call_assembler_reset_vtoken(jd, vloc)
        #
        self._call_assembler_load_result(op, result_loc)
        #
        # Here we join Path A and Path B again
        self._call_assembler_patch_jmp(jmp_location)
        # XXX here should be emitted guard_not_forced, but due
        #     to incompatibilities in how it's done, we leave it for the
        #     caller to deal with
