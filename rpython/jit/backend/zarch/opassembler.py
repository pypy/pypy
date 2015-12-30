from rpython.jit.backend.llsupport.jump import remap_frame_layout
from rpython.jit.backend.zarch.arch import (WORD,
        STD_FRAME_SIZE_IN_BYTES)
from rpython.jit.backend.zarch.arch import THREADLOCAL_ADDR_OFFSET
from rpython.jit.backend.zarch.helper.assembler import (gen_emit_cmp_op,
        gen_emit_rr_or_rpool, gen_emit_shift, gen_emit_pool_or_rr_evenodd,
        gen_emit_imm_pool_rr)
from rpython.jit.backend.zarch.helper.regalloc import (check_imm,
        check_imm_value)
from rpython.jit.backend.zarch.codebuilder import ZARCHGuardToken, InstrBuilder
from rpython.jit.backend.llsupport import symbolic, jitframe
import rpython.jit.backend.zarch.conditions as c
import rpython.jit.backend.zarch.registers as r
import rpython.jit.backend.zarch.locations as l
from rpython.jit.backend.zarch.locations import imm
from rpython.jit.backend.zarch import callbuilder
from rpython.jit.backend.zarch.codebuilder import OverwritingBuilder
from rpython.jit.backend.llsupport.descr import CallDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import (FLOAT, INT, REF, VOID)
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import rstr, rffi, lltype
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rlib.objectmodel import we_are_translated

class IntOpAssembler(object):
    _mixin_ = True

    emit_int_add = gen_emit_imm_pool_rr('AGFI','AG','AGR')
    emit_int_add_ovf = emit_int_add

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_imm() and not l1.is_in_pool():
            assert 0, "logical imm must reside in pool!"
        if l1.is_in_pool():
            self.mc.SG(l0, l1)
        else:
            self.mc.SGR(l0, l1)

    emit_int_sub_ovf = emit_int_sub

    emit_int_mul = gen_emit_imm_pool_rr('MSGFI', 'MSG', 'MSGR')
    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        lr, lq, l1 = arglocs
        if l1.is_in_pool():
            self.mc.LG(r.SCRATCH, l1)
            l1 = r.SCRATCH
        elif l1.is_imm():
            self.mc.LGFI(r.SCRATCH, l1)
            l1 = r.SCRATCH

        mc = self.mc
        bc_one_decision = mc.CLGRJ_byte_count +\
                          mc.CLGIJ_byte_count + \
                          mc.LCGR_byte_count + \
                          mc.BRC_byte_count + \
                          mc.SPM_byte_count
        bc_one_signed = mc.LPGR_byte_count * 2 + \
                        mc.MLGR_byte_count + \
                        mc.LG_byte_count + \
                        bc_one_decision
        bc_none_signed = mc.LPGR_byte_count * 2 + \
                         mc.MLGR_byte_count + \
                         mc.LG_byte_count + \
                         mc.CLGRJ_byte_count + \
                         mc.CLGIJ_byte_count + \
                         mc.BRC_byte_count
        bc_set_overflow = mc.OIHL_byte_count + mc.SPM_byte_count

        # check left neg
        mc.CGIJ(lq, l.imm(0), c.LT, l.imm(mc.CGIJ_byte_count*2))
        mc.CGIJ(l1, l.imm(0), c.GE, l.imm(mc.CGIJ_byte_count*2 + bc_one_signed))
        mc.CGIJ(l1, l.imm(0), c.LT, l.imm(mc.CGIJ_byte_count + bc_one_signed)) # jump if both are negative
        # left or right is negative
        mc.LPGR(lq, lq)
        mc.LPGR(l1, l1)
        mc.MLGR(lr, l1)
        mc.LG(r.SCRATCH, l.pool(self.pool.constant_max_64_positive))
        # is the value greater than 2**63 ? then an overflow occured
        mc.CLGRJ(lq, r.SCRATCH, c.GT, l.imm(bc_one_decision + bc_none_signed)) # jump to over overflow
        mc.CLGIJ(lr, l.imm(0), c.GT, l.imm(bc_one_decision - mc.CLGRJ_byte_count + bc_none_signed)) # jump to overflow
        mc.LCGR(lq, lq)
        mc.SPM(r.SCRATCH) # 0x80 ... 00 clears the condition code and program mask
        mc.BRC(c.ANY, l.imm(mc.BRC_byte_count + bc_set_overflow + bc_none_signed)) # no overflow happened

        # both are positive
        mc.LPGR(lq, lq)
        mc.LPGR(l1, l1)
        mc.MLGR(lr, l1)
        off = mc.CLGRJ_byte_count + mc.CLGIJ_byte_count + \
              mc.BRC_byte_count
        mc.LG(r.SCRATCH, l.pool(self.pool.constant_64_ones))
        mc.CLGRJ(lq, r.SCRATCH, c.GT, l.imm(off)) # jump to over overflow
        mc.CLGIJ(lr, l.imm(0), c.GT, l.imm(off - mc.CLGRJ_byte_count)) # jump to overflow
        mc.BRC(c.ANY, l.imm(mc.BRC_byte_count + bc_set_overflow)) # no overflow happened

        # set overflow!
        #mc.IPM(r.SCRATCH)
        # set bit 34 & 35 -> indicates overflow
        mc.OILH(r.SCRATCH, l.imm(0x3000)) # sets OF
        mc.SPM(r.SCRATCH)

        # no overflow happended

    emit_int_floordiv = gen_emit_pool_or_rr_evenodd('DSG','DSGR')
    emit_uint_floordiv = gen_emit_pool_or_rr_evenodd('DLG','DLGR')
    # NOTE division sets one register with the modulo value, thus
    # the regalloc ensures the right register survives.
    emit_int_mod = gen_emit_pool_or_rr_evenodd('DSG','DSGR')

    def emit_int_invert(self, op, arglocs, regalloc):
        l0, = arglocs
        assert not l0.is_imm()
        self.mc.XG(l0, l.pool(self.pool.constant_64_ones))

    def emit_int_neg(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LCGR(l0, l0)

    def emit_int_signext(self, op, arglocs, regalloc):
        l0, = arglocs
        extend_from = op.getarg(1).getint()
        if extend_from == 1:
            self.mc.LGBR(l0, l0)
        elif extend_from == 2:
            self.mc.LGHR(l0, l0)
        elif extend_from == 4:
            self.mc.LGFR(l0, l0)
        else:
            raise AssertionError(extend_from)

    def emit_int_force_ge_zero(self, op, arglocs, resloc):
        l0, = arglocs
        off = self.mc.CGIJ_byte_count + self.mc.LGHI_byte_count
        self.mc.CGIJ(l0, l.imm(0), c.GE, l.imm(off))
        self.mc.LGHI(l0, l.imm(0))

    def emit_int_is_zero(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.CGHI(l0, l.imm(0))
        self.flush_cc(c.EQ, res)

    def emit_int_is_true(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.CGHI(l0, l.imm(0))
        self.flush_cc(c.NE, res)

    emit_int_and = gen_emit_rr_or_rpool("NGR", "NG")
    emit_int_or  = gen_emit_rr_or_rpool("OGR", "OG")
    emit_int_xor = gen_emit_rr_or_rpool("XGR", "XG")

    emit_int_rshift  = gen_emit_shift("SRAG")
    emit_int_lshift  = gen_emit_shift("SLAG")
    emit_uint_rshift = gen_emit_shift("SRLG")

    emit_int_le = gen_emit_cmp_op(c.LE)
    emit_int_lt = gen_emit_cmp_op(c.LT)
    emit_int_gt = gen_emit_cmp_op(c.GT)
    emit_int_ge = gen_emit_cmp_op(c.GE)
    emit_int_eq = gen_emit_cmp_op(c.EQ)
    emit_int_ne = gen_emit_cmp_op(c.NE)

    emit_ptr_eq = emit_int_eq
    emit_ptr_ne = emit_int_ne

    emit_instance_ptr_eq = emit_ptr_eq
    emit_instance_ptr_ne = emit_ptr_ne

    emit_uint_le = gen_emit_cmp_op(c.LE, signed=False)
    emit_uint_lt = gen_emit_cmp_op(c.LT, signed=False)
    emit_uint_gt = gen_emit_cmp_op(c.GT, signed=False)
    emit_uint_ge = gen_emit_cmp_op(c.GE, signed=False)

class FloatOpAssembler(object):
    _mixin_ = True

    emit_float_add = gen_emit_rr_or_rpool('ADBR','ADB')
    emit_float_sub = gen_emit_rr_or_rpool('SDBR','SDB')
    emit_float_mul = gen_emit_rr_or_rpool('MDBR','MDB')
    emit_float_truediv = gen_emit_rr_or_rpool('DDBR','DDB')

    emit_float_lt = gen_emit_cmp_op(c.LT, fp=True)
    emit_float_le = gen_emit_cmp_op(c.LE, fp=True)
    emit_float_eq = gen_emit_cmp_op(c.EQ, fp=True)
    emit_float_ne = gen_emit_cmp_op(c.NE, fp=True)
    emit_float_gt = gen_emit_cmp_op(c.GT, fp=True)
    emit_float_ge = gen_emit_cmp_op(c.GE, fp=True)

    def emit_float_neg(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LCDBR(l0, l0)

    def emit_float_abs(self, op, arglocs, regalloc):
        l0, = arglocs
        self.mc.LPDBR(l0, l0)

    def emit_cast_float_to_int(self, op, arglocs, regalloc):
        f0, r0 = arglocs
        self.mc.CGDBR(r0, c.FP_TOWARDS_ZERO, f0)

    def emit_cast_int_to_float(self, op, arglocs, regalloc):
        r0, f0 = arglocs
        self.mc.CDGBR(f0, r0)

    def emit_convert_float_bytes_to_longlong(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.LGDR(res, l0)

    def emit_convert_longlong_bytes_to_float(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.LDGR(res, l0)

class CallOpAssembler(object):

    _mixin_ = True

    def _emit_call(self, op, arglocs, is_call_release_gil=False):
        resloc = arglocs[0]
        func_index = 1 + is_call_release_gil
        adr = arglocs[func_index]
        arglist = arglocs[func_index+1:]

        cb = callbuilder.CallBuilder(self, adr, arglist, resloc)

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)
        cb.argtypes = descr.get_arg_types()
        cb.restype  = descr.get_result_type()

        if is_call_release_gil:
            saveerrloc = arglocs[1]
            assert saveerrloc.is_imm()
            cb.emit_call_release_gil(saveerrloc.value)
        else:
            cb.emit()

    def _genop_call(self, op, arglocs, regalloc):
        oopspecindex = regalloc.get_oopspecindex(op)
        if oopspecindex == EffectInfo.OS_MATH_SQRT:
            return self._emit_math_sqrt(op, arglocs, regalloc)
        if oopspecindex == EffectInfo.OS_THREADLOCALREF_GET:
            return self._emit_threadlocalref_get(op, arglocs, regalloc)
        self._emit_call(op, arglocs)

    emit_call_i = _genop_call
    emit_call_r = _genop_call
    emit_call_f = _genop_call
    emit_call_n = _genop_call

    def _emit_math_sqrt(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.SQDBR(res, l0)

    def _genop_call_may_force(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs)

    emit_call_may_force_i = _genop_call_may_force
    emit_call_may_force_r = _genop_call_may_force
    emit_call_may_force_f = _genop_call_may_force
    emit_call_may_force_n = _genop_call_may_force

    def _genop_call_release_gil(self, op, arglocs, regalloc):
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        self._emit_call(op, arglocs, is_call_release_gil=True)

    emit_call_release_gil_i = _genop_call_release_gil
    emit_call_release_gil_f = _genop_call_release_gil
    emit_call_release_gil_n = _genop_call_release_gil

    def _store_force_index(self, guard_op):
        assert (guard_op.getopnum() == rop.GUARD_NOT_FORCED or
                guard_op.getopnum() == rop.GUARD_NOT_FORCED_2)
        faildescr = guard_op.getdescr()
        ofs = self.cpu.get_ofs_of_frame_field('jf_force_descr')
        self.mc.load_imm(r.SCRATCH, rffi.cast(lltype.Signed,
                                           cast_instance_to_gcref(faildescr)))
        self.mc.STD(r.SCRATCH, l.addr(ofs, r.SPP))

    def _find_nearby_operation(self, regalloc, delta):
        return regalloc.operations[regalloc.rm.position + delta]

    _COND_CALL_SAVE_REGS = [r.r12, r.r2, r.r3, r.r4, r.r5]

    def emit_cond_call(self, op, arglocs, regalloc):
        fcond = self.guard_success_cc
        self.guard_success_cc = c.cond_none
        assert fcond != c.cond_none
        fcond = c.negate(fcond)

        jmp_adr = self.mc.get_relative_pos()
        self.mc.trap()        # patched later to a relative branch
        self.mc.write('\x00' * 4)

        # save away r3, r4, r5, r6, r12 into the jitframe
        should_be_saved = [
            reg for reg in self._regalloc.rm.reg_bindings.itervalues()
                if reg in self._COND_CALL_SAVE_REGS]
        self._push_core_regs_to_jitframe(self.mc, should_be_saved)

        self.load_gcmap(self.mc, r.r2, regalloc.get_gcmap())
        #
        # load the 0-to-4 arguments into these registers, with the address of
        # the function to call into r12
        remap_frame_layout(self, arglocs,
                           [r.r12, r.r2, r.r3, r.r4, r.r5][:len(arglocs)],
                           r.SCRATCH)
        #
        # figure out which variant of cond_call_slowpath to call, and call it
        callee_only = False
        floats = False
        for reg in regalloc.rm.reg_bindings.values():
            if reg not in regalloc.rm.save_around_call_regs:
                break
        else:
            callee_only = True
        if regalloc.fprm.reg_bindings:
            floats = True
        cond_call_adr = self.cond_call_slowpath[floats * 2 + callee_only]
        self.mc.load_imm(r.SCRATCH, cond_call_adr)
        self.mc.BASR(r.RETURN, r.SCRATCH)
        # restoring the registers saved above, and doing pop_gcmap(), is left
        # to the cond_call_slowpath helper.  We never have any result value.
        relative_target = self.mc.currpos() - jmp_adr
        pmc = OverwritingBuilder(self.mc, jmp_adr, 1)
        #BI, BO = c.encoding[fcond]
        pmc.BRCL(fcond, l.imm(relative_target))
        pmc.overwrite()
        # might be overridden again to skip over the following
        # guard_no_exception too
        self.previous_cond_call_jcond = jmp_adr, fcond

class AllocOpAssembler(object):
    _mixin_ = True

    def emit_call_malloc_gc(self, op, arglocs, regalloc):
        self._emit_call(op, arglocs)
        self.propagate_memoryerror_if_r2_is_null()

    def emit_call_malloc_nursery(self, op, arglocs, regalloc):
        # registers r.RES and r.RSZ are allocated for this call
        size_box = op.getarg(0)
        assert isinstance(size_box, ConstInt)
        size = size_box.getint()
        gc_ll_descr = self.cpu.gc_ll_descr
        gcmap = regalloc.get_gcmap([r.RES, r.RSZ])
        self.malloc_cond(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            size, gcmap)

    def emit_call_malloc_nursery_varsize_frame(self, op, arglocs, regalloc):
        # registers r.RES and r.RSZ are allocated for this call
        [sizeloc] = arglocs
        gc_ll_descr = self.cpu.gc_ll_descr
        gcmap = regalloc.get_gcmap([r.RES, r.RSZ])
        self.malloc_cond_varsize_frame(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            sizeloc, gcmap)

    def emit_call_malloc_nursery_varsize(self, op, arglocs, regalloc):
        # registers r.RES and r.RSZ are allocated for this call
        gc_ll_descr = self.cpu.gc_ll_descr
        if not hasattr(gc_ll_descr, 'max_size_of_young_obj'):
            raise Exception("unreachable code")
            # for boehm, this function should never be called
        [lengthloc] = arglocs
        arraydescr = op.getdescr()
        itemsize = op.getarg(1).getint()
        maxlength = (gc_ll_descr.max_size_of_young_obj - WORD * 2) / itemsize
        gcmap = regalloc.get_gcmap([r.RES, r.RSZ])
        self.malloc_cond_varsize(
            op.getarg(0).getint(),
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            lengthloc, itemsize, maxlength, gcmap, arraydescr)

    def emit_debug_merge_point(self, op, arglocs, regalloc):
        pass

    emit_jit_debug = emit_debug_merge_point
    emit_keepalive = emit_debug_merge_point

    def emit_enter_portal_frame(self, op, arglocs, regalloc):
        self.enter_portal_frame(op)

    def emit_leave_portal_frame(self, op, arglocs, regalloc):
        self.leave_portal_frame(op)

    def _write_barrier_fastpath(self, mc, descr, arglocs, regalloc, array=False,
                                is_frame=False):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls a
        # helper piece of assembler.  The latter saves registers as needed
        # and call the function remember_young_pointer() from the GC.
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        #
        card_marking_mask = 0
        mask = descr.jit_wb_if_flag_singlebyte
        if array and descr.jit_wb_cards_set != 0:
            # assumptions the rest of the function depends on:
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            card_marking_mask = descr.jit_wb_cards_set_singlebyte
        #
        loc_base = arglocs[0]
        assert loc_base.is_reg()
        if is_frame:
            assert loc_base is r.SPP
        assert check_imm_value(descr.jit_wb_if_flag_byteofs)
        mc.LLGC(r.SCRATCH2, l.addr(descr.jit_wb_if_flag_byteofs, loc_base))
        mc.LGR(r.SCRATCH, r.SCRATCH2)
        mc.NILL(r.SCRATCH, l.imm(mask & 0xFF))

        jz_location = mc.get_relative_pos()
        mc.trap()        # patched later with 'EQ'
        mc.write('\x00' * 4)

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking_mask:
            # GCFLAG_CARDS_SET is in the same byte, loaded in r2 already
            mc.LGR(r.SCRATCH, r.SCRATCH2)
            mc.NILL(r.SCRATCH, l.imm(card_marking_mask & 0xFF))
            js_location = mc.get_relative_pos()
            mc.trap()        # patched later with 'NE'
            mc.write('\x00' * 4)
        else:
            js_location = 0

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = (card_marking_mask != 0)
        if is_frame:
            helper_num = 4
        elif regalloc.fprm.reg_bindings:
            helper_num += 2
        if self.wb_slowpath[helper_num] == 0:    # tests only
            assert not we_are_translated()
            assert not is_frame
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking_mask != 0,
                                    bool(regalloc.fprm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0
        #
        if not is_frame:
            mc.LGR(r.r0, loc_base)    # unusual argument location

        mc.load_imm(r.r14, self.wb_slowpath[helper_num])
        # alloc a stack frame
        mc.AGHI(r.SP, l.imm(-STD_FRAME_SIZE_IN_BYTES))
        mc.BASR(r.r14, r.r14)
        # destory the frame
        mc.AGHI(r.SP, l.imm(STD_FRAME_SIZE_IN_BYTES))

        if card_marking_mask:
            # The helper ends again with a check of the flag in the object.
            # So here, we can simply write again a beq, which will be
            # taken if GCFLAG_CARDS_SET is still not set.
            jns_location = mc.get_relative_pos()
            mc.trap()
            mc.write('\x00'*4)
            #
            # patch the 'NE' above
            currpos = mc.currpos()
            pmc = OverwritingBuilder(mc, js_location, 1)
            pmc.BRCL(c.NE, l.imm(currpos - js_location))
            pmc.overwrite()
            #
            # case GCFLAG_CARDS_SET: emit a few instructions to do
            # directly the card flag setting
            loc_index = arglocs[1]
            if loc_index.is_reg():
                tmp_loc = arglocs[2]
                n = descr.jit_wb_card_page_shift

                # compute in tmp_loc the byte offset:
                #     ~(index >> (card_page_shift + 3))   ('~' is 'not_' below)
                mc.SRAG(tmp_loc, loc_index, l.addr(n+3))
                #mc.srli_op(tmp_loc.value, loc_index.value, n + 3)
                # invert the bits
                mc.XIHF(tmp_loc, l.imm(0xffffFFFF))
                mc.XILF(tmp_loc, l.imm(0xffffFFFF))

                # compute in r2 the index of the bit inside the byte:
                #     (index >> card_page_shift) & 7
                # 0x80 sets zero flag. will store 0 into all selected bits
                # cannot be used on the VM
                # mc.RISBGN(r.SCRATCH, loc_index, l.imm(3), l.imm(0x80 | 63), l.imm(61))
                mc.SLAG(r.SCRATCH, loc_index, l.addr(3))
                mc.NILL(r.SCRATCH, l.imm(0xff))
                #mc.rldicl(r.SCRATCH2.value, loc_index.value, 64 - n, 61)

                # set r2 to 1 << r2
                mc.LGHI(r.SCRATCH2, l.imm(1))
                mc.SLAG(r.SCRATCH, r.SCRATCH2, l.addr(0,r.SCRATCH))

                # set this bit inside the byte of interest
                addr = l.addr(0, loc_base, tmp_loc)
                mc.LLGC(r.SCRATCH, addr)
                mc.OGR(r.SCRATCH, r.SCRATCH2)
                mc.STCY(r.SCRATCH, addr)
                # done

            else:
                byte_index = loc_index.value >> descr.jit_wb_card_page_shift
                byte_ofs = ~(byte_index >> 3)
                byte_val = 1 << (byte_index & 7)
                assert check_imm_value(byte_ofs)

                addr = l.addr(byte_ofs, loc_base)
                mc.LLGC(r.SCRATCH, addr)
                mc.OILL(r.SCRATCH, l.imm(byte_val))
                mc.STCY(r.SCRATCH, addr)
            #
            # patch the beq just above
            currpos = mc.currpos()
            pmc = OverwritingBuilder(mc, jns_location, 1)
            pmc.BRCL(c.EQ, l.imm(currpos - jns_location))
            pmc.overwrite()

        # patch the JZ above
        currpos = mc.currpos()
        pmc = OverwritingBuilder(mc, jz_location, 1)
        pmc.BRCL(c.EQ, l.imm(currpos - jz_location))
        pmc.overwrite()

    def emit_cond_call_gc_wb(self, op, arglocs, regalloc):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, regalloc)

    def emit_cond_call_gc_wb_array(self, op, arglocs, regalloc):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, regalloc,
                                     array=True)


class GuardOpAssembler(object):
    _mixin_ = True

    def _emit_guard(self, op, arglocs, is_guard_not_invalidated=False):
        if is_guard_not_invalidated:
            fcond = c.cond_none
        else:
            fcond = self.guard_success_cc
            self.guard_success_cc = c.cond_none
            assert fcond != c.cond_none
            fcond = c.negate(fcond)
        token = self.build_guard_token(op, arglocs[0].value, arglocs[1:], fcond)
        token.pos_jump_offset = self.mc.currpos()
        assert token.guard_not_invalidated() == is_guard_not_invalidated
        if not is_guard_not_invalidated:
            self.mc.reserve_guard_branch()     # has to be patched later on
        self.pending_guard_tokens.append(token)

    def build_guard_token(self, op, frame_depth, arglocs, fcond):
        descr = op.getdescr()
        gcmap = allocate_gcmap(self, frame_depth, r.JITFRAME_FIXED_SIZE)
        token = ZARCHGuardToken(self.cpu, gcmap, descr, op.getfailargs(),
                              arglocs, op.getopnum(), frame_depth,
                              fcond)
        return token

    def emit_guard_true(self, op, arglocs, regalloc):
        self._emit_guard(op, arglocs)

    def emit_guard_false(self, op, arglocs, regalloc):
        self.guard_success_cc = c.negate(self.guard_success_cc)
        self._emit_guard(op, arglocs)

    def emit_guard_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.OF
        self._emit_guard(op, arglocs)

    def emit_guard_no_overflow(self, op, arglocs, regalloc):
        self.guard_success_cc = c.NO
        self._emit_guard(op, arglocs)

    def emit_guard_value(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        l1 = arglocs[1]
        failargs = arglocs[2:]

        if l0.is_reg():
            if l1.is_imm():
                self.mc.cmp_op(l0, l1, imm=True)
            else:
                self.mc.cmp_op(l0, l1)
        elif l0.is_fp_reg():
            assert l1.is_fp_reg()
            self.mc.cmp_op(l0, l1, fp=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, failargs)

    emit_guard_nonnull = emit_guard_true
    emit_guard_isnull = emit_guard_false

    def emit_guard_class(self, op, arglocs, regalloc):
        self._cmp_guard_class(op, arglocs, regalloc)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def emit_guard_nonnull_class(self, op, arglocs, regalloc):
        self.mc.cmp_op(arglocs[0], l.imm(1), imm=True, signed=False)
        patch_pos = self.mc.currpos()
        self.mc.trap()
        self.mc.write('\x00' * 4)
        self._cmp_guard_class(op, arglocs, regalloc)
        pmc = OverwritingBuilder(self.mc, patch_pos, 1)
        pmc.BRCL(c.LT, l.imm(self.mc.currpos() - patch_pos))
        pmc.overwrite()
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def _cmp_guard_class(self, op, locs, regalloc):
        offset = self.cpu.vtable_offset
        if offset is not None:
            # could be one instruction shorter, but don't care because
            # it's not this case that is commonly translated
            self.mc.LG(r.SCRATCH, l.addr(offset, locs[0]))
            self.mc.load_imm(r.SCRATCH2, locs[1].value)
            self.mc.cmp_op(r.SCRATCH, r.SCRATCH2)
        else:
            expected_typeid = (self.cpu.gc_ll_descr
                    .get_typeid_from_classptr_if_gcremovetypeptr(locs[1].value))
            self._cmp_guard_gc_type(locs[0], expected_typeid)

    def _read_typeid(self, targetreg, loc_ptr):
        # Note that the typeid half-word is at offset 0 on a little-endian
        # machine; it is at offset 2 or 4 on a big-endian machine.
        assert self.cpu.supports_guard_gc_type
        if IS_PPC_32:
            self.mc.lhz(targetreg.value, loc_ptr.value, 2 * IS_BIG_ENDIAN)
        else:
            self.mc.lwz(targetreg.value, loc_ptr.value, 4 * IS_BIG_ENDIAN)

    def _cmp_guard_gc_type(self, loc_ptr, expected_typeid):
        self._read_typeid(r.SCRATCH2, loc_ptr)
        assert 0 <= expected_typeid <= 0x7fffffff   # 4 bytes are always enough
        if expected_typeid > 0xffff:     # if 2 bytes are not enough
            self.mc.subis(r.SCRATCH2.value, r.SCRATCH2.value,
                          expected_typeid >> 16)
            expected_typeid = expected_typeid & 0xffff
        self.mc.cmp_op(0, r.SCRATCH2.value, expected_typeid,
                       imm=True, signed=False)

    def emit_guard_gc_type(self, op, arglocs, regalloc):
        self._cmp_guard_gc_type(arglocs[0], arglocs[1].value)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs[2:])

    def emit_guard_is_object(self, op, arglocs, regalloc):
        assert self.cpu.supports_guard_gc_type
        loc_object = arglocs[0]
        # idea: read the typeid, fetch one byte of the field 'infobits' from
        # the big typeinfo table, and check the flag 'T_IS_RPYTHON_INSTANCE'.
        base_type_info, shift_by, sizeof_ti = (
            self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())
        infobits_offset, IS_OBJECT_FLAG = (
            self.cpu.gc_ll_descr.get_translated_info_for_guard_is_object())

        self._read_typeid(r.SCRATCH2, loc_object)
        self.mc.load_imm(r.SCRATCH, base_type_info + infobits_offset)
        assert shift_by == 0     # on PPC64; fixme for PPC32
        self.mc.lbzx(r.SCRATCH2.value, r.SCRATCH2.value, r.SCRATCH.value)
        self.mc.andix(r.SCRATCH2.value, r.SCRATCH2.value, IS_OBJECT_FLAG & 0xff)
        self.guard_success_cc = c.NE
        self._emit_guard(op, arglocs[1:])

    def emit_guard_subclass(self, op, arglocs, regalloc):
        xxx
        assert self.cpu.supports_guard_gc_type
        loc_object = arglocs[0]
        loc_check_against_class = arglocs[1]
        offset = self.cpu.vtable_offset
        offset2 = self.cpu.subclassrange_min_offset
        if offset is not None:
            # read this field to get the vtable pointer
            self.mc(r.SCRATCH2, l.addr(offset, loc_object))
            # read the vtable's subclassrange_min field
            assert check_imm(offset2)
            self.mc.ld(r.SCRATCH2.value, r.SCRATCH2.value, offset2)
        else:
            # read the typeid
            self._read_typeid(r.SCRATCH, loc_object)
            # read the vtable's subclassrange_min field, as a single
            # step with the correct offset
            base_type_info, shift_by, sizeof_ti = (
                self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())
            self.mc.load_imm(r.SCRATCH2, base_type_info + sizeof_ti + offset2)
            assert shift_by == 0     # on PPC64; fixme for PPC32
            self.mc.ldx(r.SCRATCH2.value, r.SCRATCH2.value, r.SCRATCH.value)
        # get the two bounds to check against
        vtable_ptr = loc_check_against_class.getint()
        vtable_ptr = rffi.cast(rclass.CLASSTYPE, vtable_ptr)
        check_min = vtable_ptr.subclassrange_min
        check_max = vtable_ptr.subclassrange_max
        assert check_max > check_min
        check_diff = check_max - check_min - 1
        # right now, a full PyPy uses less than 6000 numbers,
        # so we'll assert here that it always fit inside 15 bits
        assert 0 <= check_min <= 0x7fff
        assert 0 <= check_diff <= 0xffff
        # check by doing the unsigned comparison (tmp - min) < (max - min)
        self.mc.subi(r.SCRATCH2.value, r.SCRATCH2.value, check_min)
        self.mc.cmp_op(0, r.SCRATCH2.value, check_diff, imm=True, signed=False)
        # the guard passes if we get a result of "below or equal"
        self.guard_success_cc = c.LE
        self._emit_guard(op, arglocs[2:])

    def emit_guard_not_invalidated(self, op, arglocs, regalloc):
        self._emit_guard(op, arglocs, is_guard_not_invalidated=True)

    def emit_guard_not_forced(self, op, arglocs, regalloc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.LG(r.SCRATCH, l.addr(ofs, r.SPP))
        self.mc.cmp_op(r.SCRATCH, l.imm(0), imm=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs)

    def emit_guard_not_forced_2(self, op, arglocs, regalloc):
        guard_token = self.build_guard_token(op, arglocs[0].value, arglocs[1:],
                                             c.cond_none)
        self._finish_gcmap = guard_token.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(0, guard_token)

    def emit_guard_exception(self, op, arglocs, regalloc):
        loc, resloc = arglocs[:2]
        failargs = arglocs[2:]

        mc = self.mc
        mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert check_imm_value(diff)

        mc.LG(r.SCRATCH2, l.addr(diff, r.SCRATCH))
        mc.cmp_op(r.SCRATCH2, loc)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, failargs)

        if resloc:
            mc.load(resloc, r.SCRATCH, 0)
        mc.LGHI(r.SCRATCH2, l.imm(0))
        mc.STG(r.SCRATCH2, l.addr(0, r.SCRATCH))
        mc.STG(r.SCRATCH2, l.addr(diff, r.SCRATCH))

    def emit_save_exc_class(self, op, arglocs, regalloc):
        [resloc] = arglocs
        diff = self.mc.load_imm_plus(r.r2, self.cpu.pos_exception())
        self.mc.load(resloc, r.r2, diff)

    def emit_save_exception(self, op, arglocs, regalloc):
        [resloc] = arglocs
        self._store_and_reset_exception(self.mc, resloc)

    def emit_restore_exception(self, op, arglocs, regalloc):
        self._restore_exception(self.mc, arglocs[1], arglocs[0])

class MemoryOpAssembler(object):
    _mixin_ = True

    def _memory_read(self, result_loc, source_loc, size, sign):
        # res, base_loc, ofs, size and signed are all locations
        if size == 8:
            if result_loc.is_fp_reg():
                self.mc.LD(result_loc, source_loc)
            else:
                self.mc.LG(result_loc, source_loc)
        elif size == 4:
            if sign:
                self.mc.LGF(result_loc, source_loc)
            else:
                self.mc.LLGF(result_loc, source_loc)
        elif size == 2:
            if sign:
                self.mc.LGH(result_loc, source_loc)
            else:
                self.mc.LLGH(result_loc, source_loc)
        elif size == 1:
            if sign:
                self.mc.LGB(result_loc, source_loc)
            else:
                self.mc.LLGC(result_loc, source_loc)
        else:
            assert 0, "size not supported"

    def _memory_store(self, value_loc, addr_loc, size):
        if size.value == 8:
            if value_loc.is_fp_reg():
                self.mc.STDY(value_loc, addr_loc)
            else:
                self.mc.STG(value_loc, addr_loc)
        elif size.value == 4:
            self.mc.STY(value_loc, addr_loc)
        elif size.value == 2:
            self.mc.STHY(value_loc, addr_loc)
        elif size.value == 1:
            self.mc.STCY(value_loc, addr_loc)
        else:
            assert 0, "size not supported"


    def _emit_gc_load(self, op, arglocs, regalloc):
        result_loc, base_loc, ofs_loc, size_loc, sign_loc = arglocs
        src_addr = l.addr(0, base_loc, ofs_loc)
        self._memory_read(result_loc, src_addr, size_loc.value, sign_loc.value)

    emit_gc_load_i = _emit_gc_load
    emit_gc_load_f = _emit_gc_load
    emit_gc_load_r = _emit_gc_load

    def _emit_gc_load_indexed(self, op, arglocs, regalloc):
        result_loc, base_loc, index_loc, offset_loc, size_loc, sign_loc =arglocs
        if offset_loc.is_imm() and self._mem_offset_supported(offset_loc.value):
            addr_loc = l.addr(offset_loc.value, base_loc, index_loc)
        else:
            self.mc.LGR(r.SCRATCH, index_loc)
            slef.mc.AGR(r.SCRATCH, offset_loc)
            addr_loc = l.addr(0, base_loc, r.SCRATCH)
        self._memory_read(result_loc, addr_loc, size_loc.value, sign_loc.value)

    emit_gc_load_indexed_i = _emit_gc_load_indexed
    emit_gc_load_indexed_f = _emit_gc_load_indexed
    emit_gc_load_indexed_r = _emit_gc_load_indexed

    def emit_gc_store(self, op, arglocs, regalloc):
        (base_loc, index_loc, value_loc, size_loc) = arglocs
        if index_loc.is_imm() and self._mem_offset_supported(index_loc.value):
            addr_loc = l.addr(index_loc.value, base_loc)
        else:
            self.mc.LGR(r.SCRATCH, index_loc)
            addr_loc = l.addr(0, base_loc, r.SCRATCH)
        if value_loc.is_in_pool():
            self.mc.LG(r.SCRATCH2, value_loc)
            value_loc = r.SCRATCH2
        self._memory_store(value_loc, addr_loc, size_loc)

    def emit_gc_store_indexed(self, op, arglocs, regalloc):
        (base_loc, index_loc, value_loc, offset_loc, size_loc) = arglocs
        addr_loc = self._load_address(base_loc, index_loc, offset_loc, r.SCRATCH)
        if value_loc.is_in_pool():
            self.mc.LG(r.SCRATCH2, value_loc)
            value_loc = r.SCRATCH2
        self._memory_store(value_loc, addr_loc, size_loc)

    def _load_address(self, base_loc, index_loc, offset_loc, helper_reg):
        if index_loc.is_imm() and offset_loc.is_imm():
            const = offset_loc.value + index_loc.value
            assert self._mem_offset_supported(const)
            addr_loc = l.addr(const, base_loc)
        elif offset_loc.is_imm() and self._mem_offset_supported(offset_loc.value):
            assert index_loc.is_core_reg()
            addr_loc = l.addr(offset_loc.value, base_loc, index_loc)
        else:
            self.mc.LGR(helper_reg, index_loc)
            slef.mc.AGR(helper_reg, offset_loc)
            addr_loc = l.addr(0, base_loc, helper_reg)
        return addr_loc

    def _mem_offset_supported(self, value):
        return -2**19 <= value < 2**19

    def emit_copystrcontent(self, op, arglocs, regalloc):
        self._emit_copycontent(arglocs, is_unicode=False)

    def emit_copyunicodecontent(self, op, arglocs, regalloc):
        self._emit_copycontent(arglocs, is_unicode=True)

    def _emit_load_for_copycontent(self, dst, src_ptr, src_ofs, scale):
        if src_ofs.is_imm():
            value = src_ofs.value << scale
            if check_imm_value(value):
                self.mc.LGR(dst, src_ptr)
                self.mc.AGHI(dst, l.imm(value))
            else:
                self.mc.load_imm(dst, value)
                self.mc.AGR(dst, src_ptr)
        elif scale == 0:
            self.mc.LGR(dst, src_ptr)
            self.mc.AGR(dst, src_ofs)
        else:
            self.mc.SLAG(dst, src_ofs, l.addr(scale))
            self.mc.AGR(dst, src_ptr)

    def _emit_copycontent(self, arglocs, is_unicode):
        [src_ptr_loc, dst_ptr_loc,
         src_ofs_loc, dst_ofs_loc, length_loc] = arglocs

        if is_unicode:
            basesize, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                        self.cpu.translate_support_code)
            if   itemsize == 2: scale = 1
            elif itemsize == 4: scale = 2
            else: raise AssertionError
        else:
            basesize, itemsize, _ = symbolic.get_array_token(rstr.STR,
                                        self.cpu.translate_support_code)
            assert itemsize == 1
            scale = 0

        self._emit_load_for_copycontent(r.r0, src_ptr_loc, src_ofs_loc, scale)
        self._emit_load_for_copycontent(r.r2, dst_ptr_loc, dst_ofs_loc, scale)

        if length_loc.is_imm():
            length = length_loc.getint()
            self.mc.load_imm(r.r4, length << scale)
        else:
            if scale > 0:
                self.mc.SLAG(r.r4, length_loc, l.addr(scale))
            elif length_loc is not r.r4:
                self.mc.LGR(r.r4, length_loc)

        self.mc.LGR(r.r3, r.r0)
        self.mc.AGHI(r.r3, l.imm(basesize))
        self.mc.AGHI(r.r2, l.imm(basesize))

        self.mc.alloc_std_frame()
        self.mc.load_imm(self.mc.RAW_CALL_REG, self.memcpy_addr)
        self.mc.raw_call()
        self.mc.restore_std_frame()

    def emit_zero_array(self, op, arglocs, regalloc):
        base_loc, startindex_loc, length_loc, \
            ofs_loc, itemsize_loc, pad_byte_loc = arglocs

        if ofs_loc.is_imm():
            self.mc.AGHI(base_loc, ofs_loc)
        else:
            self.mc.AGR(base_loc, ofs_loc)
        if startindex_loc.is_imm():
            self.mc.AGHI(base_loc, startindex_loc)
        else:
            self.mc.AGR(base_loc, startindex_loc)
        assert not length_loc.is_imm()
        self.mc.SGR(pad_byte_loc, pad_byte_loc)
        pad_byte_plus_one = r.odd_reg(pad_byte_loc)
        self.mc.SGR(pad_byte_plus_one, pad_byte_plus_one)
        self.mc.XGR(r.SCRATCH, r.SCRATCH)
        # s390x has memset directly as a hardware instruction!!
        # it needs 5 registers allocated
        # dst = rX, length = rX+1 (ensured by the regalloc)
        # pad_byte is rY to rY+1
        # scratch register holds the value written to dst
        assert pad_byte_loc.is_even()
        assert base_loc.is_even()
        assert length_loc.value == base_loc.value + 1
        self.mc.MVCLE(base_loc, pad_byte_loc, l.addr(0, r.SCRATCH))


class ForceOpAssembler(object):
    _mixin_ = True

    def emit_force_token(self, op, arglocs, regalloc):
        res_loc = arglocs[0]
        self.mc.LGR(res_loc, r.SPP)

    def _genop_call_assembler(self, op, arglocs, regalloc):
        if len(arglocs) == 3:
            [result_loc, argloc, vloc] = arglocs
        else:
            [result_loc, argloc] = arglocs
            vloc = imm(0)
        self._store_force_index(self._find_nearby_operation(regalloc, +1))
        # 'result_loc' is either r2, f0 or None
        self.call_assembler(op, argloc, vloc, result_loc, r.r2)

    emit_call_assembler_i = _genop_call_assembler
    emit_call_assembler_r = _genop_call_assembler
    emit_call_assembler_f = _genop_call_assembler
    emit_call_assembler_n = _genop_call_assembler

    imm = staticmethod(imm)   # for call_assembler()

    def _call_assembler_emit_call(self, addr, argloc, _):
        self.regalloc_mov(argloc, r.r2)
        self.mc.LG(r.r3, l.addr(THREADLOCAL_ADDR_OFFSET, r.SP))

        cb = callbuilder.CallBuilder(self, addr, [r.r2, r.r3], r.r2)
        cb.emit()

    def _call_assembler_emit_helper_call(self, addr, arglocs, result_loc):
        cb = callbuilder.CallBuilder(self, addr, arglocs, result_loc)
        cb.emit()

    def _call_assembler_check_descr(self, value, tmploc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.LG(r.SCRATCH, l.addr(ofs, r.r2))
        if check_imm(value):
            self.mc.cmp_op(r.SCRATCH, value, imm=True)
        else:
            self.mc.load_imm(r.SCRATCH2, value)
            self.mc.cmp_op(r.SCRATCH, r.SCRATCH2, imm=False)
        jump_if_eq = self.mc.currpos()
        self.mc.trap()      # patched later
        self.mc.write('\x00' * 4) # patched later
        return jump_if_eq

    def _call_assembler_patch_je(self, result_loc, je_location):
        jump_to_done = self.mc.currpos()
        self.mc.trap()      # patched later
        self.mc.write('\x00' * 4) # patched later
        #
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, je_location, 1)
        pmc.BRCL(c.EQ, l.imm(currpos - je_location))
        pmc.overwrite()
        #
        return jump_to_done

    def _call_assembler_load_result(self, op, result_loc):
        if op.type != VOID:
            # load the return value from the dead frame's value index 0
            kind = op.type
            descr = self.cpu.getarraydescr_for_frame(kind)
            ofs = self.cpu.unpack_arraydescr(descr)
            if kind == FLOAT:
                assert result_loc is r.f0
                self.mc.LD(r.f0, l.addr(ofs, r.r2))
            else:
                assert result_loc is r.r2
                self.mc.LG(r.r2, l.addr(ofs, r.r2))

    def _call_assembler_patch_jmp(self, jmp_location):
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jmp_location, 1)
        pmc.BRCL(c.ANY, l.imm(currpos - jmp_location))
        pmc.overwrite()

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        oldadr = oldlooptoken._ll_function_addr
        target = newlooptoken._ll_function_addr
        # copy frame-info data
        baseofs = self.cpu.get_baseofs_of_frame_field()
        newlooptoken.compiled_loop_token.update_frame_info(
            oldlooptoken.compiled_loop_token, baseofs)
        # we overwrite the instructions at the old _ll_function_addr
        # to start with a JMP to the new _ll_function_addr.
        mc = InstrBuilder()
        mc.load_imm(r.SCRATCH, target)
        mc.BCR(c.ANY, r.SCRATCH)
        mc.copy_to_raw_memory(oldadr)


class MiscOpAssembler(object):
    _mixin_ = True

    def _genop_same_as(self, op, arglocs, regalloc):
        argloc, resloc = arglocs
        if argloc is not resloc:
            self.regalloc_mov(argloc, resloc)

    emit_same_as_i = _genop_same_as
    emit_same_as_r = _genop_same_as
    emit_same_as_f = _genop_same_as
    emit_cast_ptr_to_int = _genop_same_as
    emit_cast_int_to_ptr = _genop_same_as

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        addr, scratch = arglocs
        self.mc.LG(scratch, l.addr(0,addr))
        self.mc.AGHI(scratch, l.imm(1))
        self.mc.STG(scratch, l.addr(0,addr))

    def emit_debug_merge_point(self, op, arglocs, regalloc):
        pass

    emit_jit_debug = emit_debug_merge_point
    emit_keepalive = emit_debug_merge_point

    def emit_enter_portal_frame(self, op, arglocs, regalloc):
        self.enter_portal_frame(op)

    def emit_leave_portal_frame(self, op, arglocs, regalloc):
        self.leave_portal_frame(op)

    def emit_guard_no_exception(self, op, arglocs, regalloc):
        self.mc.load_imm(r.SCRATCH, self.cpu.pos_exception())
        self.mc.LG(r.SCRATCH2, l.addr(0,r.SCRATCH))
        self.mc.cmp_op(r.SCRATCH2, l.imm(0), imm=True)
        self.guard_success_cc = c.EQ
        self._emit_guard(op, arglocs)
        # If the previous operation was a COND_CALL, overwrite its conditional
        # jump to jump over this GUARD_NO_EXCEPTION as well, if we can
        if self._find_nearby_operation(regalloc,-1).getopnum() == rop.COND_CALL:
            jmp_adr, fcond = self.previous_cond_call_jcond
            relative_target = self.mc.currpos() - jmp_adr
            pmc = OverwritingBuilder(self.mc, jmp_adr, 1)
            pmc.BRCL(fcond, l.imm(relative_target))
            pmc.overwrite()

class OpAssembler(IntOpAssembler, FloatOpAssembler,
                  GuardOpAssembler, CallOpAssembler,
                  AllocOpAssembler, MemoryOpAssembler,
                  MiscOpAssembler, ForceOpAssembler):
    _mixin_ = True

