from rpython.jit.backend.ppc.regalloc import (PPCFrameManager,
                                              Regalloc, PPCRegisterManager)
from rpython.jit.backend.ppc.opassembler import OpAssembler
from rpython.jit.backend.ppc.codebuilder import (PPCBuilder, OverwritingBuilder,
                                                 scratch_reg)
from rpython.jit.backend.ppc.arch import (IS_PPC_32, IS_PPC_64, WORD,
                                          LR_BC_OFFSET, REGISTERS_SAVED,
                                          GPR_SAVE_AREA_OFFSET,
                                          THREADLOCAL_ADDR_OFFSET,
                                          STD_FRAME_SIZE_IN_BYTES,
                                          IS_BIG_ENDIAN)
from rpython.jit.backend.ppc.helper.assembler import Saved_Volatiles
from rpython.jit.backend.ppc.helper.regalloc import _check_imm_arg
import rpython.jit.backend.ppc.register as r
import rpython.jit.backend.ppc.condition as c
from rpython.jit.backend.ppc.register import JITFRAME_FIXED_SIZE
from rpython.jit.metainterp.history import AbstractFailDescr
from rpython.jit.metainterp.history import ConstInt, BoxInt
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.assembler import (DEBUG_COUNTER, debug_bridge,
                                                     BaseAssembler)
from rpython.jit.backend.model import CompiledLoopToken
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.history import (INT, REF, FLOAT)
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                                have_debug_prints)
from rpython.rlib import rgc
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.backend.ppc.locations import StackLocation, get_fp_offset, imm
from rpython.jit.backend.ppc import callbuilder
from rpython.rlib.jit import AsmInfo
from rpython.rlib.objectmodel import compute_unique_id
from rpython.rlib.rarithmetic import r_uint

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER', ('i', lltype.Signed),
                              ('type', lltype.Char),  # 'b'ridge, 'l'abel or
                                                      # 'e'ntry point
                              ('number', lltype.Signed))
def hi(w):
    return w >> 16

def ha(w):
    if (w >> 15) & 1:
        return (w >> 16) + 1
    else:
        return w >> 16

def lo(w):
    return w & 0x0000FFFF

def la(w):
    v = w & 0x0000FFFF
    if v & 0x8000:
        return -((v ^ 0xFFFF) + 1) # "sign extend" to 32 bits
    return v

def highest(w):
    return w >> 48

def higher(w):
    return (w >> 32) & 0x0000FFFF

def high(w):
    return (w >> 16) & 0x0000FFFF

class JitFrameTooDeep(Exception):
    pass

class AssemblerPPC(OpAssembler, BaseAssembler):

    #ENCODING_AREA               = FORCE_INDEX_OFS
    #OFFSET_SPP_TO_GPR_SAVE_AREA = (FORCE_INDEX + FLOAT_INT_CONVERSION
    #                               + ENCODING_AREA)
    #OFFSET_SPP_TO_FPR_SAVE_AREA = (OFFSET_SPP_TO_GPR_SAVE_AREA
    #                               + GPR_SAVE_AREA)
    #OFFSET_SPP_TO_OLD_BACKCHAIN = (OFFSET_SPP_TO_GPR_SAVE_AREA
    #                               + GPR_SAVE_AREA + FPR_SAVE_AREA)

    #OFFSET_STACK_ARGS = OFFSET_SPP_TO_OLD_BACKCHAIN + BACKCHAIN_SIZE * WORD
    #if IS_PPC_64:
    #    OFFSET_STACK_ARGS += MAX_REG_PARAMS * WORD

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.loop_run_counters = []
        self.wb_slowpath = [0, 0, 0, 0, 0]
        self.setup_failure_recovery()
        self.stack_check_slowpath = 0
        self.propagate_exception_path = 0
        self.teardown()

    def set_debug(self, v):
        self._debug = v

    def _save_nonvolatiles(self):
        """ save nonvolatile GPRs and FPRs in SAVE AREA 
        """
        for i, reg in enumerate(NONVOLATILES):
            # save r31 later on
            if reg.value == r.SPP.value:
                continue
            self.mc.store(reg.value, r.SPP.value, 
                          self.OFFSET_SPP_TO_GPR_SAVE_AREA + WORD * i)
        for i, reg in enumerate(NONVOLATILES_FLOAT):
            self.mc.stfd(reg.value, r.SPP.value, 
                         self.OFFSET_SPP_TO_FPR_SAVE_AREA + WORD * i)

    def _restore_nonvolatiles(self, mc, spp_reg):
        """ restore nonvolatile GPRs and FPRs from SAVE AREA
        """
        for i, reg in enumerate(NONVOLATILES):
            mc.load(reg.value, spp_reg.value, 
                         self.OFFSET_SPP_TO_GPR_SAVE_AREA + WORD * i)
        for i, reg in enumerate(NONVOLATILES_FLOAT):
            mc.lfd(reg.value, spp_reg.value,
                        self.OFFSET_SPP_TO_FPR_SAVE_AREA + WORD * i)

    def gen_shadowstack_header(self, gcrootmap):
        # we need to put two words into the shadowstack: the MARKER_FRAME
        # and the address of the frame (fp, actually)
        rst = gcrootmap.get_root_stack_top_addr()
        self.mc.load_imm(r.r14, rst)
        self.mc.load(r.r15.value, r.r14.value, 0) # LD r15 [rootstacktop]
        #
        MARKER = gcrootmap.MARKER_FRAME
        self.mc.addi(r.r16.value, r.r15.value, 2 * WORD) # ADD r16, r15, 2*WORD
        self.mc.load_imm(r.r17, MARKER)
        self.mc.store(r.r17.value, r.r15.value, WORD)  # STR MARKER, r15+WORD
        self.mc.store(r.SPP.value, r.r15.value, 0)  # STR spp, r15
        #
        self.mc.store(r.r16.value, r.r14.value, 0)  # STR r16, [rootstacktop]

    def gen_footer_shadowstack(self, gcrootmap, mc):
        rst = gcrootmap.get_root_stack_top_addr()
        mc.load_imm(r.r14, rst)
        mc.load(r.r15.value, r.r14.value, 0)  # LD r15, [rootstacktop]
        mc.addi(r.r15.value, r.r15.value, -2 * WORD)  # SUB r15, r15, 2*WORD
        mc.store(r.r15.value, r.r14.value, 0) # STR r15, [rootstacktop]

    def new_stack_loc(self, i, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return StackLocation(i, get_fp_offset(base_ofs, i), tp)

    def setup_failure_recovery(self):
        self.failure_recovery_code = [0, 0, 0, 0]

    def _push_all_regs_to_jitframe(self, mc, ignored_regs, withfloats,
                                   callee_only=False):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = PPCRegisterManager.save_around_call_regs
        else:
            regs = PPCRegisterManager.all_regs
        #
        for reg in regs:
            if reg not in ignored_regs:
                v = r.ALL_REG_INDEXES[reg]
                mc.std(reg.value, r.SPP.value, base_ofs + v * WORD)
        #
        if withfloats:
            for reg in r.MANAGED_FP_REGS:
                v = r.ALL_REG_INDEXES[reg]
                mc.stfd(reg.value, r.SPP.value, base_ofs + v * WORD)

    def _pop_all_regs_from_jitframe(self, mc, ignored_regs, withfloats,
                                    callee_only=False):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = PPCRegisterManager.save_around_call_regs
        else:
            regs = PPCRegisterManager.all_regs
        #
        for reg in regs:
            if reg not in ignored_regs:
                v = r.ALL_REG_INDEXES[reg]
                mc.ld(reg.value, r.SPP.value, base_ofs + v * WORD)
        #
        if withfloats:
            for reg in r.MANAGED_FP_REGS:
                v = r.ALL_REG_INDEXES[reg]
                mc.lfd(reg.value, r.SPP.value, base_ofs + v * WORD)

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = PPCBuilder()
        self.mc = mc

        # fill in the jf_descr and jf_gcmap fields of the frame according
        # to which failure we are resuming from.  These are set before
        # this function is called (see generate_quick_failure()).
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store(r.r0.value, r.SPP.value, ofs)
        mc.store(r.r2.value, r.SPP.value, ofs2)

        self._push_all_regs_to_jitframe(mc, [], withfloats)

        if exc:
            # We might have an exception pending.
            mc.load_imm(r.r2, self.cpu.pos_exc_value())
            # Copy it into 'jf_guard_exc'
            offset = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.load(r.r0.value, r.r2.value, 0)
            mc.store(r.r0.value, r.SPP.value, offset)
            # Zero out the exception fields
            diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
            assert _check_imm_arg(diff)
            mc.li(r.r0.value, 0)
            mc.store(r.r0.value, r.r2.value, 0)
            mc.store(r.r0.value, r.r2.value, diff)

        # now we return from the complete frame, which starts from
        # _call_header_with_stack_check().  The _call_footer below does it.
        self._call_footer()
        rawstart = mc.materialize(self.cpu, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart
        self.mc = None

    def build_frame_realloc_slowpath(self):
        mc = PPCBuilder()
        self.mc = mc

        # signature of this _frame_realloc_slowpath function:
        #   * on entry, r0 is the new size
        #   * on entry, r2 is the gcmap
        #   * no managed register must be modified

        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store(r.r2.value, r.SPP.value, ofs2)

        self._push_all_regs_to_jitframe(mc, [], self.cpu.supports_floats)

        # Save away the LR inside r30
        mc.mflr(r.RCS1.value)

        # First argument is SPP (= r31), which is the jitframe
        mc.mr(r.r3.value, r.SPP.value)

        # Second argument is the new size, which is still in r0 here
        mc.mr(r.r4.value, r.r0.value)

        self._store_and_reset_exception(mc, r.RCS2, r.RCS3)

        # Do the call
        adr = rffi.cast(lltype.Signed, self.cpu.realloc_frame)
        cb = callbuilder.CallBuilder(self, imm(adr), [r.r3, r.r4], r.r3)
        cb.emit()

        # The result is stored back into SPP (= r31)
        mc.mr(r.SPP.value, r.r3.value)

        self._restore_exception(mc, r.RCS2, r.RCS3)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._load_shadowstack_top_in_ebx(mc, gcrootmap)
            mc.MOV_mr((ebx.value, -WORD), eax.value)

        mc.mtlr(r.RCS1.value)     # restore LR
        self._pop_all_regs_from_jitframe(mc, [], self.cpu.supports_floats)
        mc.blr()

        self._frame_realloc_slowpath = mc.materialize(self.cpu, [])
        self.mc = None

    def _store_and_reset_exception(self, mc, excvalloc, exctploc=None):
        """Reset the exception, after fetching it inside the two regs.
        """
        mc.load_imm(r.r2, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert _check_imm_arg(diff)
        # Load the exception fields into the two registers
        mc.load(excvalloc.value, r.r2.value, 0)
        if exctploc is not None:
            mc.load(exctploc.value, r.r2.value, diff)
        # Zero out the exception fields
        mc.li(r.r0.value, 0)
        mc.store(r.r0.value, r.r2.value, 0)
        mc.store(r.r0.value, r.r2.value, diff)

    def _restore_exception(self, mc, excvalloc, exctploc):
        mc.load_imm(r.r2, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert _check_imm_arg(diff)
        # Store the exception fields from the two registers
        mc.store(excvalloc.value, r.r2.value, 0)
        mc.store(exctploc.value, r.r2.value, diff)

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.
        """
        # signature of these cond_call_slowpath functions:
        #   * on entry, r12 contains the function to call
        #   * r3, r4, r5, r6 contain arguments for the call
        #   * r2 is the gcmap
        #   * the old value of these regs must already be stored in the jitframe
        #   * on exit, all registers are restored from the jitframe

        mc = PPCBuilder()
        self.mc = mc
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store(r.r2.value, r.SPP.value, ofs2)

        # copy registers to the frame, with the exception of r3 to r6 and r12,
        # because these have already been saved by the caller.  Note that
        # this is not symmetrical: these 5 registers are saved by the caller
        # but restored here at the end of this function.
        self._push_all_regs_to_jitframe(mc, [r.r3, r.r4, r.r5, r.r6, r.r12],
                                        supports_floats, callee_only)

        # Save away the LR inside r30
        mc.mflr(r.RCS1.value)

        # Do the call
        cb = callbuilder.CallBuilder(self, r.r12, [r.r3, r.r4, r.r5, r.r6],
                                     None)
        cb.emit()

        # Finish
        # XXX self._reload_frame_if_necessary(mc, align_stack=True)

        mc.mtlr(r.RCS1.value)     # restore LR
        self._pop_all_regs_from_jitframe(mc, [], supports_floats, callee_only)
        mc.blr()
        self.mc = None
        return mc.materialize(self.cpu, [])

    def _build_malloc_slowpath(self):
        xxxxxxx
        mc = PPCBuilder()
        frame_size = (len(r.MANAGED_FP_REGS) * WORD
                    + (BACKCHAIN_SIZE + MAX_REG_PARAMS) * WORD)

        mc.make_function_prologue(frame_size)
        # managed volatiles are saved below
        if self.cpu.supports_floats:
            for i in range(len(r.MANAGED_FP_REGS)):
                mc.stfd(r.MANAGED_FP_REGS[i].value, r.SP.value,
                        (BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)
        # Values to compute size stored in r3 and r4
        mc.subf(r.RES.value, r.RES.value, r.r4.value)
        addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
        for reg, ofs in PPCRegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
            mc.store(reg.value, r.SPP.value, ofs)
        mc.call(rffi.cast(lltype.Signed, addr))
        for reg, ofs in PPCRegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
            mc.load(reg.value, r.SPP.value, ofs)
        # restore floats
        if self.cpu.supports_floats:
            for i in range(len(r.MANAGED_FP_REGS)):
                mc.lfd(r.MANAGED_FP_REGS[i].value, r.SP.value,
                       (BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)

        mc.cmp_op(0, r.RES.value, 0, imm=True)
        jmp_pos = mc.currpos()
        mc.trap()

        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.load_imm(r.r4, nursery_free_adr)
        mc.load(r.r4.value, r.r4.value, 0)
 
        if IS_PPC_32:
            ofs = WORD
        else:
            ofs = WORD * 2
        
        with scratch_reg(mc):
            mc.load(r.SCRATCH.value, r.SP.value, frame_size + ofs) 
            mc.mtlr(r.SCRATCH.value)
        mc.addi(r.SP.value, r.SP.value, frame_size)
        mc.blr()

        # if r3 == 0 we skip the return above and jump to the exception path
        offset = mc.currpos() - jmp_pos
        pmc = OverwritingBuilder(mc, jmp_pos, 1)
        pmc.beq(offset)
        pmc.overwrite()
        # restore the frame before leaving
        with scratch_reg(mc):
            mc.load(r.SCRATCH.value, r.SP.value, frame_size + ofs) 
            mc.mtlr(r.SCRATCH.value)
        mc.addi(r.SP.value, r.SP.value, frame_size)
        mc.b_abs(self.propagate_exception_path)

        rawstart = mc.materialize(self.cpu, [])
        # here we do not need a function descr. This is being only called using
        # an internal ABI
        self.malloc_slowpath = rawstart

    def _build_stack_check_slowpath(self):
        _, _, slowpathaddr = self.cpu.insert_stack_check()
        if slowpathaddr == 0 or not self.cpu.propagate_exception_descr:
            return      # no stack check (for tests, or non-translated)
        #
        # make a "function" that is called immediately at the start of
        # an assembler function.  In particular, the stack looks like:
        #
        # |                             |
        # |        OLD BACKCHAIN        |
        # |                             |
        # =============================== -
        # |                             |  | 
        # |          BACKCHAIN          |  | > MINI FRAME (BACHCHAIN SIZE * WORD)
        # |                             |  |
        # =============================== - 
        # |                             |
        # |       SAVED PARAM REGS      |
        # |                             |
        # -------------------------------
        # |                             |
        # |          BACKCHAIN          |
        # |                             |
        # =============================== <- SP
        #
        mc = PPCBuilder()
        
        # make small frame to store data (parameter regs + LR + SCRATCH) in
        # there.  Allocate additional fixed save area for PPC64.
        PARAM_AREA = len(r.PARAM_REGS)
        FIXED_AREA = BACKCHAIN_SIZE
        if IS_PPC_64:
            FIXED_AREA += MAX_REG_PARAMS
        frame_size = (FIXED_AREA + PARAM_AREA) * WORD

        # align the SP
        MINIFRAME_SIZE = BACKCHAIN_SIZE * WORD
        while (frame_size + MINIFRAME_SIZE) % (4 * WORD) != 0:
            frame_size += WORD

        # write function descriptor
        if IS_PPC_64 and IS_BIG_ENDIAN:
            for _ in range(3):
                mc.write64(0)

        # build frame
        mc.make_function_prologue(frame_size)

        # save parameter registers
        for i, reg in enumerate(r.PARAM_REGS):
            mc.store(reg.value, r.SP.value, (i + FIXED_AREA) * WORD)

        # use SP as single parameter for the call
        mc.mr(r.r3.value, r.SP.value)

        # stack still aligned
        mc.call(slowpathaddr)

        with scratch_reg(mc):
            mc.load_imm(r.SCRATCH, self.cpu.pos_exception())
            mc.loadx(r.SCRATCH.value, 0, r.SCRATCH.value)
            # if this comparison is true, then everything is ok,
            # else we have an exception
            mc.cmp_op(0, r.SCRATCH.value, 0, imm=True)

        jnz_location = mc.currpos()
        mc.trap()

        # restore parameter registers
        for i, reg in enumerate(r.PARAM_REGS):
            mc.load(reg.value, r.SP.value, (i + FIXED_AREA) * WORD)

        # restore LR
        mc.restore_LR_from_caller_frame(frame_size)

        # reset SP
        mc.addi(r.SP.value, r.SP.value, frame_size)
        #mc.blr()
        mc.b(self.propagate_exception_path)

        pmc = OverwritingBuilder(mc, jnz_location, 1)
        pmc.bne(mc.currpos() - jnz_location)
        pmc.overwrite()

        # restore link register out of preprevious frame
        offset_LR = frame_size + MINIFRAME_SIZE + LR_BC_OFFSET

        with scratch_reg(mc):
            mc.load(r.SCRATCH.value, r.SP.value, offset_LR)
            mc.mtlr(r.SCRATCH.value)

        # remove this frame and the miniframe
        both_framesizes = frame_size + MINIFRAME_SIZE
        mc.addi(r.SP.value, r.SP.value, both_framesizes)
        mc.blr()

        rawstart = mc.materialize(self.cpu, [])
        if IS_PPC_64:
            self.write_64_bit_func_descr(rawstart, rawstart+3*WORD)
        self.stack_check_slowpath = rawstart

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        descr = self.cpu.gc_ll_descr.write_barrier_descr
        if descr is None:
            return
        if not withcards:
            func = descr.get_write_barrier_fn(self.cpu)
        else:
            if descr.jit_wb_cards_set == 0:
                return
            func = descr.get_write_barrier_from_array_fn(self.cpu)
            if func == 0:
                return
        #
        # This builds a helper function called from the slow path of
        # write barriers.  It must save all registers, and optionally
        # all fp registers.  It takes its single argument in r0.
        mc = PPCBuilder()
        old_mc = self.mc
        self.mc = mc
        #
        ignored_regs = [reg for reg in r.MANAGED_REGS if not (
                            # 'reg' will be pushed if the following is true:
                            reg in r.VOLATILES or
                            reg is r.RCS1 or
                            (withcards and reg is r.RCS2))]
        if not for_frame:
            # push all volatile registers, push RCS1, and sometimes push RCS2
            self._push_all_regs_to_jitframe(mc, ignored_regs, withfloats)
        else:
            return #XXXXX
            # we have one word to align
            mc.SUB_ri(esp.value, 7 * WORD) # align and reserve some space
            mc.MOV_sr(WORD, eax.value) # save for later
            if self.cpu.supports_floats:
                mc.MOVSD_sx(2 * WORD, xmm0.value)   # 32-bit: also 3 * WORD
            if IS_X86_32:
                mc.MOV_sr(4 * WORD, edx.value)
                mc.MOV_sr(0, ebp.value)
                exc0, exc1 = esi, edi
            else:
                mc.MOV_rr(edi.value, ebp.value)
                exc0, exc1 = ebx, r12
            mc.MOV(RawEspLoc(WORD * 5, REF), exc0)
            mc.MOV(RawEspLoc(WORD * 6, INT), exc1)
            # note that it's save to store the exception in register,
            # since the call to write barrier can't collect
            # (and this is assumed a bit left and right here, like lack
            # of _reload_frame_if_necessary)
            self._store_and_reset_exception(mc, exc0, exc1)

        if withcards:
            mc.mr(r.RCS2.value, r.r0.value)
        #
        # Save the lr into r.RCS1
        mc.mflr(r.RCS1.value)
        #
        func = rffi.cast(lltype.Signed, func)
        cb = callbuilder.CallBuilder(self, imm(func), [r.r0], None)
        cb.emit()
        #
        # Restore lr
        mc.mtlr(r.RCS1.value)
        #
        if withcards:
            # A final andix before the blr, for the caller.  Careful to
            # not follow this instruction with another one that changes
            # the status of cr0!
            card_marking_mask = descr.jit_wb_cards_set_singlebyte
            mc.lbz(r.RCS2.value, r.RCS2.value, descr.jit_wb_if_flag_byteofs)
            mc.andix(r.RCS2.value, r.RCS2.value, card_marking_mask & 0xFF)
        #

        if not for_frame:
            self._pop_all_regs_from_jitframe(mc, ignored_regs, withfloats)
            mc.blr()
        else:
            XXXXXXX
            if IS_X86_32:
                mc.MOV_rs(edx.value, 4 * WORD)
            if self.cpu.supports_floats:
                mc.MOVSD_xs(xmm0.value, 2 * WORD)
            mc.MOV_rs(eax.value, WORD) # restore
            self._restore_exception(mc, exc0, exc1)
            mc.MOV(exc0, RawEspLoc(WORD * 5, REF))
            mc.MOV(exc1, RawEspLoc(WORD * 6, INT))
            mc.LEA_rs(esp.value, 7 * WORD)
            mc.RET()

        self.mc = old_mc
        rawstart = mc.materialize(self.cpu, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    def _build_propagate_exception_path(self):
        if not self.cpu.propagate_exception_descr:
            return

        self.mc = PPCBuilder()
        #
        # read and reset the current exception

        propagate_exception_descr = rffi.cast(lltype.Signed,
                  cast_instance_to_gcref(self.cpu.propagate_exception_descr))
        ofs3 = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
        ofs4 = self.cpu.get_ofs_of_frame_field('jf_descr')

        self._store_and_reset_exception(self.mc, r.r3)
        self.mc.load_imm(r.r4, propagate_exception_descr)
        self.mc.std(r.r3.value, r.SPP.value, ofs3)
        self.mc.std(r.r4.value, r.SPP.value, ofs4)
        #
        self._call_footer()
        rawstart = self.mc.materialize(self.cpu, [])
        self.propagate_exception_path = rawstart
        self.mc = None

    # The code generated here serves as an exit stub from
    # the executed machine code.
    # It is generated only once when the backend is initialized.
    #
    # The following actions are performed:
    #   - The fail boxes are filled with the computed values 
    #        (failure_recovery_func)
    #   - The nonvolatile registers are restored 
    #   - jump back to the calling code
    def _gen_exit_path(self):
        mc = PPCBuilder() 
        self._save_managed_regs(mc)
        decode_func_addr = llhelper(self.recovery_func_sign,
                self.failure_recovery_func)
        addr = rffi.cast(lltype.Signed, decode_func_addr)

        # load parameters into parameter registers
        # address of state encoding 
        mc.load(r.RES.value, r.SPP.value, FORCE_INDEX_OFS)
        mc.mr(r.r4.value, r.SPP.value)  # load spilling pointer
        mc.mr(r.r5.value, r.SPP.value)  # load managed registers pointer
        #
        # call decoding function
        mc.call(addr)

        # generate return and restore registers
        self._gen_epilogue(mc)

        return mc.materialize(self.cpu, [], self.cpu.gc_ll_descr.gcrootmap)

    def _save_managed_regs(self, mc):
        """ store managed registers in ENCODING AREA
        """
        for i in range(len(r.MANAGED_REGS)):
            reg = r.MANAGED_REGS[i]
            mc.store(reg.value, r.SPP.value, i * WORD)
        FLOAT_OFFSET = len(r.MANAGED_REGS)
        for i in range(len(r.MANAGED_FP_REGS)):
            fpreg = r.MANAGED_FP_REGS[i]
            mc.stfd(fpreg.value, r.SPP.value, (i + FLOAT_OFFSET) * WORD)

    #def gen_bootstrap_code(self, loophead, spilling_area):
    #    self._insert_stack_check()
    #    self._make_frame(spilling_area)
    #    self.mc.b_offset(loophead)

    def _call_header(self):
        if IS_PPC_64 and IS_BIG_ENDIAN:
            # Reserve space for a function descriptor, 3 words
            self.mc.write64(0)
            self.mc.write64(0)
            self.mc.write64(0)

        # Build a new stackframe of size STD_FRAME_SIZE_IN_BYTES
        self.mc.store_update(r.SP.value, r.SP.value, -STD_FRAME_SIZE_IN_BYTES)
        self.mc.mflr(r.SCRATCH.value)
        self.mc.store(r.SCRATCH.value, r.SP.value,
                      STD_FRAME_SIZE_IN_BYTES + LR_BC_OFFSET)

        # save registers r25 to r31
        for i, reg in enumerate(REGISTERS_SAVED):
            self.mc.store(reg.value, r.SP.value,
                          GPR_SAVE_AREA_OFFSET + i * WORD)

        # save r4, the second argument, to THREADLOCAL_ADDR_OFFSET
        self.mc.store(r.r4.value, r.SP.value, THREADLOCAL_ADDR_OFFSET)

        # move r3, the first argument, to r31 (SPP): the jitframe object
        self.mc.mr(r.SPP.value, r.r3.value)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            XXX
            self.gen_shadowstack_header(gcrootmap)

    def _call_header_with_stack_check(self):
        self._call_header()
        if self.stack_check_slowpath == 0:
            pass            # not translated
        else:
            XXXX
            # this is the size for the miniframe
            frame_size = BACKCHAIN_SIZE * WORD

            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()

            # save r16
            self.mc.mtctr(r.r16.value)

            with scratch_reg(self.mc):
                self.mc.load_imm(r.SCRATCH, endaddr)        # load SCRATCH, [start]
                self.mc.loadx(r.SCRATCH.value, 0, r.SCRATCH.value)
                self.mc.subf(r.SCRATCH.value, r.SP.value, r.SCRATCH.value)
                self.mc.load_imm(r.r16, lengthaddr)
                self.mc.load(r.r16.value, r.r16.value, 0)
                self.mc.cmp_op(0, r.SCRATCH.value, r.r16.value, signed=False)

            # restore r16
            self.mc.mfctr(r.r16.value)

            patch_loc = self.mc.currpos()
            self.mc.trap()

            # make minimal frame which contains the LR
            #
            # |         OLD    FRAME       |
            # ==============================
            # |                            |
            # |         BACKCHAIN          | > BACKCHAIN_SIZE * WORD
            # |                            |
            # ============================== <- SP

            self.mc.make_function_prologue(frame_size)

            # make check
            self.mc.call(self.stack_check_slowpath)

            # restore LR
            self.mc.restore_LR_from_caller_frame(frame_size)

            # remove minimal frame
            self.mc.addi(r.SP.value, r.SP.value, frame_size)

            offset = self.mc.currpos() - patch_loc
            #
            pmc = OverwritingBuilder(self.mc, patch_loc, 1)
            pmc.ble(offset) # jump if SCRATCH <= r16, i. e. not(SCRATCH > r16)
            pmc.overwrite()

    def _call_footer(self):
        # the return value is the jitframe
        self.mc.mr(r.r3.value, r.SPP.value)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_footer_shadowstack(gcrootmap)

        # restore registers r25 to r31
        for i, reg in enumerate(REGISTERS_SAVED):
            self.mc.load(reg.value, r.SP.value,
                         GPR_SAVE_AREA_OFFSET + i * WORD)

        # load the return address into r4
        self.mc.load(r.r4.value, r.SP.value,
                     STD_FRAME_SIZE_IN_BYTES + LR_BC_OFFSET)

        # throw away the stack frame and return to r4
        self.mc.addi(r.SP.value, r.SP.value, STD_FRAME_SIZE_IN_BYTES)
        self.mc.mtlr(r.r4.value)     # restore LR
        self.mc.blr()

    def setup(self, looptoken):
        BaseAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, "setup_once() not called?"
        self.current_clt = looptoken.compiled_loop_token
        self.pending_guard_tokens = []
        self.pending_guard_tokens_recovered = 0
        #if WORD == 8:
        #    self.pending_memoryerror_trampoline_from = []
        #    self.error_trampoline_64 = 0
        self.mc = PPCBuilder()
        #assert self.datablockwrapper is None --- but obscure case
        # possible, e.g. getting MemoryError and continuing
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.target_tokens_currently_compiling = {}
        self.frame_depth_to_patch = []

    def update_frame_depth(self, frame_depth):
        if frame_depth > 0x7fff:
            raise JitFrameTooDeep     # XXX
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def patch_stack_checks(self, frame_depth):
        if frame_depth > 0x7fff:
            raise JitFrameTooDeep     # XXX
        for traps_pos, jmp_target in self.frame_depth_to_patch:
            pmc = OverwritingBuilder(self.mc, traps_pos, 3)
            # three traps, so exactly three instructions to patch here
            pmc.cmpdi(0, r.r2.value, frame_depth)         # 1
            pmc.bc(7, 0, jmp_target - (traps_pos + 4))    # 2   "bge+"
            pmc.li(r.r0.value, frame_depth)               # 3
            pmc.overwrite()

    def _check_frame_depth(self, mc, gcmap):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.ld(r.r2.value, r.SPP.value, ofs)
        patch_pos = mc.currpos()
        mc.trap()     # placeholder for cmpdi(0, r2, ...)
        mc.trap()     # placeholder for bge
        mc.trap()     # placeholder for li(r0, ...)
        mc.load_imm(r.SCRATCH2, self._frame_realloc_slowpath)
        mc.mtctr(r.SCRATCH2.value)
        #XXXXX:
        if we_are_translated(): XXX #self.load_gcmap(mc, gcmap)  # -> r2
        mc.bctrl()

        self.frame_depth_to_patch.append((patch_pos, mc.currpos()))

    @rgc.no_release_gil
    def assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                      operations, looptoken, log):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = len(inputargs)
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(looptoken)
        frame_info = self.datablockwrapper.malloc_aligned(
            jitframe.JITFRAMEINFO_SIZE, alignment=WORD)
        clt.frame_info = rffi.cast(jitframe.JITFRAMEINFOPTR, frame_info)
        clt.allgcrefs = []
        clt.frame_info.clear() # for now

        if log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        regalloc = Regalloc(assembler=self)
        #
        self._call_header_with_stack_check()
        operations = regalloc.prepare_loop(inputargs, operations,
                                           looptoken, clt.allgcrefs)
        looppos = self.mc.get_relative_pos()
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs,
                                                   operations)
        self.update_frame_depth(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        #
        size_excluding_failure_stuff = self.mc.get_relative_pos()
        self.write_pending_failure_recoveries()
        full_size = self.mc.get_relative_pos()
        #
        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        rawstart = self.materialize_loop(looptoken)
        if IS_PPC_64 and IS_BIG_ENDIAN:  # fix the function descriptor (3 words)
            rffi.cast(rffi.LONGP, rawstart)[0] = rawstart + 3 * WORD
        #
        looptoken._ppc_loop_code = looppos + rawstart
        debug_start("jit-backend-addr")
        debug_print("Loop %d (%s) has address 0x%x to 0x%x (bootstrap 0x%x)" % (
            looptoken.number, loopname,
            r_uint(rawstart + looppos),
            r_uint(rawstart + size_excluding_failure_stuff),
            r_uint(rawstart)))
        debug_stop("jit-backend-addr")
        self.patch_pending_failure_recoveries(rawstart)
        #
        ops_offset = self.mc.ops_offset
        if not we_are_translated():
            # used only by looptoken.dump() -- useful in tests
            looptoken._ppc_rawstart = rawstart
            looptoken._ppc_fullsize = full_size
            looptoken._ppc_ops_offset = ops_offset
        looptoken._ll_function_addr = rawstart
        if logger:
            logger.log_loop(inputargs, operations, 0, "rewritten",
                            name=loopname, ops_offset=ops_offset)

        self.fixup_target_tokens(rawstart)
        self.teardown()
        # oprofile support
        #if self.cpu.profile_agent is not None:
        #    name = "Loop # %s: %s" % (looptoken.number, loopname)
        #    self.cpu.profile_agent.native_code_written(name,
        #                                               rawstart, full_size)
        return AsmInfo(ops_offset, rawstart + looppos,
                       size_excluding_failure_stuff - looppos)

    def _assemble(self, regalloc, inputargs, operations):
        self._regalloc = regalloc
        self.guard_success_cc = c.cond_none
        regalloc.compute_hint_frame_locations(operations)
        regalloc.walk_operations(inputargs, operations)
        assert self.guard_success_cc == c.cond_none
        if 1: # we_are_translated() or self.cpu.dont_keepalive_stuff:
            self._regalloc = None   # else keep it around for debugging
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._ppc_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

    @rgc.no_release_gil
    def assemble_bridge(self, faildescr, inputargs, operations,
                        original_loop_token, log, logger):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(original_loop_token)
        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)
        regalloc = Regalloc(assembler=self)
        startpos = self.mc.get_relative_pos()
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)
        self._check_frame_depth(self.mc, "??")
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        codeendpos = self.mc.get_relative_pos()
        self.write_pending_failure_recoveries()
        fullsize = self.mc.get_relative_pos()
        #
        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        rawstart = self.materialize_loop(original_loop_token)
        debug_bridge(descr_number, rawstart, codeendpos)
        self.patch_pending_failure_recoveries(rawstart)
        # patch the jump from original guard
        self.patch_jump_for_descr(faildescr, rawstart)
        ops_offset = self.mc.ops_offset
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        if logger:
            logger.log_bridge(inputargs, operations, "rewritten",
                              ops_offset=ops_offset)
        self.fixup_target_tokens(rawstart)
        self.update_frame_depth(frame_depth)
        self.teardown()
        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def teardown(self):
        self.pending_guard_tokens = None
        self.mc = None
        self.current_clt = None

    def _find_failure_recovery_bytecode(self, faildescr):
        return faildescr._failure_recovery_code_adr

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ppc_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def target_arglocs(self, looptoken):
        return looptoken._ppc_arglocs

    def materialize_loop(self, looptoken, show=False):
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu, allblocks,
                                    self.cpu.gc_ll_descr.gcrootmap)
        #print "=== Loop start is at %s ===" % hex(r_uint(start))
        return start

    def load_gcmap(self, mc, gcmap):
        # load the current gcmap into register r2
        ptr = rffi.cast(lltype.Signed, gcmap)
        mc.load_imm(r.r2, ptr)

    def push_gcmap(self, mc, gcmap, store):
        assert store is True
        # XXX IGNORED FOR NOW

    def break_long_loop(self):
        # If the loop is too long, the guards in it will jump forward
        # more than 32 KB.  We use an approximate hack to know if we
        # should break the loop here with an unconditional "b" that
        # jumps over the target code.
        jmp_pos = self.mc.currpos()
        self.mc.trap()

        self.write_pending_failure_recoveries()

        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jmp_pos, 1)
        pmc.b(currpos - jmp_pos)
        pmc.overwrite()

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.currpos()
        fail_descr, target = self.store_info_on_descr(startpos, guardtok)
        assert target != 0
        self.load_gcmap(self.mc, gcmap=guardtok.gcmap)   # -> r2
        self.mc.load_imm(r.r0, target)
        self.mc.mtctr(r.r0.value)
        self.mc.load_imm(r.r0, fail_descr)
        self.mc.bctr()
        # we need to write at least 6 insns here, for patch_jump_for_descr()
        while self.mc.currpos() < startpos + 6 * 4:
            self.mc.trap()
        return startpos

    def write_pending_failure_recoveries(self):
        # for each pending guard, generate the code of the recovery stub
        # at the end of self.mc.
        for i in range(self.pending_guard_tokens_recovered,
                       len(self.pending_guard_tokens)):
            tok = self.pending_guard_tokens[i]
            tok.pos_recovery_stub = self.generate_quick_failure(tok)
        self.pending_guard_tokens_recovered = len(self.pending_guard_tokens)

    def patch_pending_failure_recoveries(self, rawstart):
        assert (self.pending_guard_tokens_recovered ==
                len(self.pending_guard_tokens))
        clt = self.current_clt
        for tok in self.pending_guard_tokens:
            addr = rawstart + tok.pos_jump_offset
            #
            # XXX see patch_jump_for_descr()
            #tok.faildescr.adr_jump_offset = addr
            tok.faildescr.adr_recovery_stub = rawstart + tok.pos_recovery_stub
            #
            relative_target = tok.pos_recovery_stub - tok.pos_jump_offset
            #
            if not tok.is_guard_not_invalidated:
                mc = PPCBuilder()
                mc.b_cond_offset(relative_target, tok.fcond)
                mc.copy_to_raw_memory(addr)
            else:
                # GUARD_NOT_INVALIDATED, record an entry in
                # clt.invalidate_positions of the form:
                #     (addr-in-the-code-of-the-not-yet-written-jump-target,
                #      relative-target-to-use)
                relpos = tok.pos_jump_offset
                clt.invalidate_positions.append((rawstart + relpos,
                                                 relative_target))

    def patch_jump_for_descr(self, faildescr, adr_new_target):
        # 'faildescr.adr_jump_offset' is the address of an instruction that is a
        # conditional jump.  We must patch this conditional jump to go
        # to 'adr_new_target'.  If the target is too far away, we can't
        # patch it inplace, and instead we patch the quick failure code
        # (which should be at least 6 instructions, so enough).
        # --- XXX for now we always use the second solution ---
        mc = PPCBuilder()
        mc.b_abs(adr_new_target)
        mc.copy_to_raw_memory(faildescr.adr_recovery_stub)

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def regalloc_mov(self, prev_loc, loc):
        if prev_loc.is_imm():
            value = prev_loc.getint()
            # move immediate value to register
            if loc.is_reg():
                self.mc.load_imm(loc, value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                with scratch_reg(self.mc):
                    offset = loc.value
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.store(r.SCRATCH.value, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.value
            # move from memory to register
            if loc.is_reg():
                reg = loc.value
                self.mc.load(reg, r.SPP.value, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.value
                with scratch_reg(self.mc):
                    self.mc.load(r.SCRATCH.value, r.SPP.value, offset)
                    self.mc.store(r.SCRATCH.value, r.SPP.value, target_offset)
                return
            # move from memory to fp register
            elif loc.is_fp_reg():
                assert prev_loc.type == FLOAT, 'source not float location'
                reg = loc.value
                self.mc.lfd(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_reg():
            reg = prev_loc.value
            # move to another register
            if loc.is_reg():
                other_reg = loc.value
                self.mc.mr(other_reg, reg)
                return
            # move to memory
            elif loc.is_stack():
                offset = loc.value
                self.mc.store(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_imm_float():
            value = prev_loc.getint()
            # move immediate value to fp register
            if loc.is_fp_reg():
                with scratch_reg(self.mc):
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.lfdx(loc.value, 0, r.SCRATCH.value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                with scratch_reg(self.mc):
                    offset = loc.value
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.lfdx(r.FP_SCRATCH.value, 0, r.SCRATCH.value)
                    self.mc.stfd(r.FP_SCRATCH.value, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_fp_reg():
            reg = prev_loc.value
            # move to another fp register
            if loc.is_fp_reg():
                other_reg = loc.value
                self.mc.fmr(other_reg, reg)
                return
            # move from fp register to memory
            elif loc.is_stack():
                assert loc.type == FLOAT, "target not float location"
                offset = loc.value
                self.mc.stfd(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        assert 0, "not supported location"
    mov_loc_loc = regalloc_mov

    def regalloc_push(self, loc, already_pushed):
        """Pushes the value stored in loc to the stack
        Can trash the current value of SCRATCH when pushing a stack
        loc"""
        assert IS_PPC_64, 'needs to updated for ppc 32'

        index = WORD * (~already_pushed)

        if loc.type == FLOAT:
            if not loc.is_fp_reg():
                self.regalloc_mov(loc, r.FP_SCRATCH)
                loc = r.FP_SCRATCH
            self.mc.stfd(loc.value, r.SP.value, index)
        else:
            if not loc.is_core_reg():
                self.regalloc_mov(loc, r.SCRATCH)
                loc = r.SCRATCH
            self.mc.std(loc.value, r.SP.value, index)

    def regalloc_pop(self, loc, already_pushed):
        """Pops the value on top of the stack to loc. Can trash the current
        value of SCRATCH when popping to a stack loc"""
        assert IS_PPC_64, 'needs to updated for ppc 32'

        index = WORD * (~already_pushed)

        if loc.type == FLOAT:
            if loc.is_fp_reg():
                self.mc.lfd(loc.value, r.SP.value, index)
            else:
                self.mc.lfd(r.FP_SCRATCH.value, r.SP.value, index)
                self.regalloc_mov(r.FP_SCRATCH, loc)
        else:
            if loc.is_core_reg():
                self.mc.ld(loc.value, r.SP.value, index)
            else:
                self.mc.ld(r.SCRATCH.value, r.SP.value, index)
                self.regalloc_mov(r.SCRATCH, loc)

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size):
        assert size & (WORD-1) == 0     # must be correctly aligned

        self.mc.load_imm(r.RES, nursery_free_adr)
        self.mc.load(r.RES.value, r.RES.value, 0)

        if _check_imm_arg(size):
            self.mc.addi(r.r4.value, r.RES.value, size)
        else:
            self.mc.load_imm(r.r4, size)
            self.mc.add(r.r4.value, r.RES.value, r.r4.value)

        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, nursery_top_adr)
            self.mc.loadx(r.SCRATCH.value, 0, r.SCRATCH.value)
            self.mc.cmp_op(0, r.r4.value, r.SCRATCH.value, signed=False)

        fast_jmp_pos = self.mc.currpos()
        self.mc.trap()

        # We load into r3 the address stored at nursery_free_adr. We calculate
        # the new value for nursery_free_adr and store in r1 The we load the
        # address stored in nursery_top_adr into IP If the value in r4 is
        # (unsigned) bigger than the one in ip we conditionally call
        # malloc_slowpath in case we called malloc_slowpath, which returns the
        # new value of nursery_free_adr in r4 and the adr of the new object in
        # r3.
        self.mark_gc_roots(self.write_new_force_index(),
                           use_copy_area=True)
        # We are jumping to malloc_slowpath without a call through a function
        # descriptor, because it is an internal call and "call" would trash r11
        self.mc.bl_abs(self.malloc_slowpath)

        offset = self.mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(self.mc, fast_jmp_pos, 1)
        pmc.ble(offset) # jump if LE (not GT)
        pmc.overwrite()
        
        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, nursery_free_adr)
            self.mc.storex(r.r4.value, 0, r.SCRATCH.value)

    def mark_gc_roots(self, force_index, use_copy_area=False):
        if force_index < 0:
            return     # not needed
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            mark = self._regalloc.get_mark_gc_roots(gcrootmap, use_copy_area)
            assert gcrootmap.is_shadow_stack
            gcrootmap.write_callshape(mark, force_index)

    def propagate_memoryerror_if_r3_is_null(self):
        # if self.propagate_exception_path == 0 (tests), this may jump to 0
        # and segfaults.  too bad.  the alternative is to continue anyway
        # with r3==0, but that will segfault too.
        self.mc.cmp_op(0, r.r3.value, 0, imm=True)
        self.mc.b_cond_abs(self.propagate_exception_path, c.EQ)

    def write_new_force_index(self):
        # for shadowstack only: get a new, unused force_index number and
        # write it to FORCE_INDEX_OFS.  Used to record the call shape
        # (i.e. where the GC pointers are in the stack) around a CALL
        # instruction that doesn't already have a force_index.
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            clt = self.current_clt
            force_index = clt.reserve_and_record_some_faildescr_index()
            self._write_fail_index(force_index)
            return force_index
        else:
            return 0

    def _write_fail_index(self, fail_index):
        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, fail_index)
            self.mc.store(r.SCRATCH.value, r.SPP.value, FORCE_INDEX_OFS)
            
    def load(self, loc, value):
        assert (loc.is_reg() and value.is_imm()
                or loc.is_fp_reg() and value.is_imm_float())
        if value.is_imm():
            self.mc.load_imm(loc, value.getint())
        elif value.is_imm_float():
            with scratch_reg(self.mc):
                self.mc.load_imm(r.SCRATCH, value.getint())
                self.mc.lfdx(loc.value, 0, r.SCRATCH.value)

def notimplemented_op(self, op, arglocs, regalloc):
    print "[PPC/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

operations = [notimplemented_op] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_%s' % key
    if hasattr(AssemblerPPC, methname):
        func = getattr(AssemblerPPC, methname).im_func
        operations[value] = func

class BridgeAlreadyCompiled(Exception):
    pass
