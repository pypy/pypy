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
                                          JITFRAME_FIXED_SIZE)
from rpython.jit.backend.ppc.helper.assembler import Saved_Volatiles
from rpython.jit.backend.ppc.helper.regalloc import _check_imm_arg
import rpython.jit.backend.ppc.register as r
import rpython.jit.backend.ppc.condition as c
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
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.backend.ppc.locations import StackLocation, get_spp_offset, imm
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
        self.cpu = cpu
        self.mc = None
        self.memcpy_addr = 0
        self.pending_guards = None
        self.fail_boxes_count = 0
        self.current_clt = None
        self.malloc_slowpath = 0
        self.wb_slowpath = [0, 0, 0, 0]
        self._regalloc = None
        self.datablockwrapper = None
        self.max_stack_params = 0
        self.propagate_exception_path = 0
        self.stack_check_slowpath = 0
        self.setup_failure_recovery()
        self._debug = False
        self.loop_run_counters = []
        self.debug_counter_descr = cpu.fielddescrof(DEBUG_COUNTER, 'i')

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

    # The code generated here allocates a new stackframe 
    # and is the first machine code to be executed.
    def _make_frame(self, frame_depth):
        XXX
        self.mc.make_function_prologue(frame_depth)

        # save SPP at the bottom of the stack frame
        self.mc.store(r.SPP.value, r.SP.value, WORD)

        # compute spilling pointer (SPP)
        self.mc.addi(r.SPP.value, r.SP.value, 
                frame_depth - self.OFFSET_SPP_TO_OLD_BACKCHAIN)

        # save nonvolatile registers
        self._save_nonvolatiles()

        # save r31, use r30 as scratch register
        # this is safe because r30 has been saved already
        assert NONVOLATILES[-1] == r.SPP
        ofs_to_r31 = (self.OFFSET_SPP_TO_GPR_SAVE_AREA +
                      WORD * (len(NONVOLATILES)-1))
        self.mc.load(r.r30.value, r.SP.value, WORD)
        self.mc.store(r.r30.value, r.SPP.value, ofs_to_r31)
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)

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

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, spilling_pointer,
                                  managed_registers_pointer):
            """
                mem_loc is a pointer to the beginning of the encoding.

                spilling_pointer is the address of the spilling area.
            """
            regs = rffi.cast(rffi.LONGP, managed_registers_pointer)
            fpregs = rffi.ptradd(regs, len(r.MANAGED_REGS))
            fpregs = rffi.cast(rffi.LONGP, fpregs)
            return self.decode_registers_and_descr(mem_loc, 
                                                   spilling_pointer,
                                                   regs, fpregs)

        self.failure_recovery_func = failure_recovery_func
        self.failure_recovery_code = [0, 0, 0]

    recovery_func_sign = lltype.Ptr(lltype.FuncType([lltype.Signed] * 3,
            lltype.Signed))

    # TODO: see with we really need the ignored_regs argument
    def _push_all_regs_to_jitframe(self, mc, ignored_regs, withfloats,
                                   callee_only=False):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            # Only push registers used to pass arguments to the callee
            regs = r.VOLATILES
        else:
            regs = r.ALL_REGS
        # For now, just push all regs to the jitframe
        for i, reg in enumerate(regs):
            # XXX should we progress to higher addresses?
            mc.store_reg(reg, base_ofs - (i * WORD))

        if withfloats:
            if callee_only:
                regs = r.VOLATILES_FLOAT
            else:
                regs = r.ALL_FLOAT_REGS
            for i, reg in enumerate(regs):
                pass # TODO find or create the proper store indexed for fpr's

    def _pop_all_regs_from_jitframe(self, mc, ignored_regs, withfloats,
                                    callee_only=False):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = r.VOLATILES
        else:
            regs = r.ALL_REGS
        for i, reg in enumerate(regs):
            # XXX should we progress to higher addressess
            mc.load_from_addr(reg, base_ofs - (i * WORD))

        if withfloats:
            if callee_only:
                regs = r.VOLATILES_FLOAT
            else:
                regs = r.ALL_FLOAT_REGS
            for i, reg in enumerate(regs):
                pass # TODO find or create the proper load indexed for fpr's

    @rgc.no_collect
    def decode_registers_and_descr(self, mem_loc, spp, registers, fp_registers):
        """Decode locations encoded in memory at mem_loc and write the values
        to the failboxes.  Values for spilled vars and registers are stored on
        stack at frame_loc """
        assert spp & 1 == 0
        self.fail_force_index = spp + FORCE_INDEX_OFS
        bytecode = rffi.cast(rffi.UCHARP, mem_loc)
        num = 0
        value = 0
        fvalue = 0
        code_inputarg = False
        while True:
            code = rffi.cast(lltype.Signed, bytecode[0])
            bytecode = rffi.ptradd(bytecode, 1)
            if code >= self.CODE_FROMSTACK:
                if code > 0x7F:
                    shift = 7
                    code &= 0x7F
                    while True:
                        nextcode = rffi.cast(lltype.Signed, bytecode[0])
                        bytecode = rffi.ptradd(bytecode, 1)
                        code |= (nextcode & 0x7F) << shift
                        shift += 7
                        if nextcode <= 0x7F:
                            break
                # load the value from the stack
                kind = code & 3
                code = int((code - self.CODE_FROMSTACK) >> 2)
                if code_inputarg:
                    code = ~code
                    code_inputarg = False
                if kind == self.DESCR_FLOAT:
                    start = spp + get_spp_offset(int(code))
                    fvalue = rffi.cast(rffi.LONGP, start)[0]
                else:
                    start = spp + get_spp_offset(int(code))
                    value = rffi.cast(rffi.LONGP, start)[0]
            else:
                # 'code' identifies a register: load its value
                kind = code & 3
                if kind == self.DESCR_SPECIAL:
                    if code == self.CODE_HOLE:
                        num += 1
                        continue
                    if code == self.CODE_INPUTARG:
                        code_inputarg = True
                        continue
                    assert code == self.CODE_STOP
                    break
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    reg_index = r.get_managed_fpreg_index(code)
                    fvalue = fp_registers[reg_index]
                else:
                    reg_index = r.get_managed_reg_index(code)
                    value = registers[reg_index]
            # store the loaded value into fail_boxes_<type>
            if kind == self.DESCR_FLOAT:
                tgt = self.fail_boxes_float.get_addr_for_num(num)
                rffi.cast(rffi.LONGP, tgt)[0] = fvalue
            else:
                if kind == self.DESCR_INT:
                    tgt = self.fail_boxes_int.get_addr_for_num(num)
                elif kind == self.DESCR_REF:
                    assert (value & 3) == 0, "misaligned pointer"
                    tgt = self.fail_boxes_ptr.get_addr_for_num(num)
                else:
                    assert 0, "bogus kind"
                rffi.cast(rffi.LONGP, tgt)[0] = value
            num += 1
        self.fail_boxes_count = num
        fail_index = rffi.cast(rffi.INTP, bytecode)[0]
        fail_index = rffi.cast(lltype.Signed, fail_index)
        return fail_index

    def decode_inputargs(self, code):
        descr_to_box_type = [REF, INT, FLOAT]
        bytecode = rffi.cast(rffi.UCHARP, code)
        arglocs = []
        code_inputarg = False
        while 1:
            # decode the next instruction from the bytecode
            code = rffi.cast(lltype.Signed, bytecode[0])
            bytecode = rffi.ptradd(bytecode, 1)
            if code >= self.CODE_FROMSTACK:
                # 'code' identifies a stack location
                if code > 0x7F:
                    shift = 7
                    code &= 0x7F
                    while True:
                        nextcode = rffi.cast(lltype.Signed, bytecode[0])
                        bytecode = rffi.ptradd(bytecode, 1)
                        code |= (nextcode & 0x7F) << shift
                        shift += 7
                        if nextcode <= 0x7F:
                            break
                kind = code & 3
                code = (code - self.CODE_FROMSTACK) >> 2
                if code_inputarg:
                    code = ~code
                    code_inputarg = False
                loc = PPCFrameManager.frame_pos(code, descr_to_box_type[kind])
            elif code == self.CODE_STOP:
                break
            elif code == self.CODE_HOLE:
                continue
            elif code == self.CODE_INPUTARG:
                code_inputarg = True
                continue
            else:
                # 'code' identifies a register
                kind = code & 3
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    assert (r.ALL_FLOAT_REGS[code] is 
                            r.MANAGED_FP_REGS[r.get_managed_fpreg_index(code)])
                    loc = r.ALL_FLOAT_REGS[code]
                else:
                    #loc = r.all_regs[code]
                    assert (r.ALL_REGS[code] is 
                            r.MANAGED_REGS[r.get_managed_reg_index(code)])
                    loc = r.ALL_REGS[code]
            arglocs.append(loc)
        return arglocs[:]

    # TODO
    def _build_failure_recovery(self, exc, withfloats=False):
        pass

    # TODO
    def build_frame_realloc_slowpath(self):
        pass

    # TODO
    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        pass

    def _build_malloc_slowpath(self):
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
        mc.nop()

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
        pmc.bc(12, 2, offset) 
        pmc.overwrite()
        # restore the frame before leaving
        with scratch_reg(mc):
            mc.load(r.SCRATCH.value, r.SP.value, frame_size + ofs) 
            mc.mtlr(r.SCRATCH.value)
        mc.addi(r.SP.value, r.SP.value, frame_size)
        mc.b_abs(self.propagate_exception_path)

        mc.prepare_insts_blocks()
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
        if IS_PPC_64:
            for _ in range(6):
                mc.write32(0)

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
        mc.nop()

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
        pmc.bc(4, 2, mc.currpos() - jnz_location)
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

        mc.prepare_insts_blocks()
        rawstart = mc.materialize(self.cpu, [])
        if IS_PPC_64:
            self.write_64_bit_func_descr(rawstart, rawstart+3*WORD)
        self.stack_check_slowpath = rawstart

    # TODO: see what need to be done when for_frame is True
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
        # all fp registers.
        mc = PPCBuilder()
        #
        frame_size = ((len(r.VOLATILES) + len(r.VOLATILES_FLOAT)
                      + BACKCHAIN_SIZE + MAX_REG_PARAMS) * WORD)
        mc.make_function_prologue(frame_size)
        for i in range(len(r.VOLATILES)):
                       mc.store(r.VOLATILES[i].value, r.SP.value,
                              (BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)
        if self.cpu.supports_floats:
            for i in range(len(r.VOLATILES_FLOAT)):
                           mc.stfd(r.VOLATILES_FLOAT[i].value, r.SP.value,
                                  (len(r.VOLATILES) + BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)

        mc.call(rffi.cast(lltype.Signed, func))
        if self.cpu.supports_floats:
            for i in range(len(r.VOLATILES_FLOAT)):
                           mc.lfd(r.VOLATILES_FLOAT[i].value, r.SP.value,
                                  (len(r.VOLATILES) + BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)
        for i in range(len(r.VOLATILES)):
                       mc.load(r.VOLATILES[i].value, r.SP.value,
                              (BACKCHAIN_SIZE + MAX_REG_PARAMS + i) * WORD)
        mc.restore_LR_from_caller_frame(frame_size)
        #
        if withcards:
            # A final compare before the RET, for the caller.  Careful to
            # not follow this instruction with another one that changes
            # the status of the CPU flags!
            mc.lbz(r.SCRATCH.value, r.r3.value,
                   descr.jit_wb_if_flag_byteofs)
            mc.extsb(r.SCRATCH.value, r.SCRATCH.value)
            mc.cmpwi(0, r.SCRATCH.value, 0)
        #
        mc.addi(r.SP.value, r.SP.value, frame_size)
        mc.blr()
        #
        mc.prepare_insts_blocks()
        rawstart = mc.materialize(self.cpu, [])
        self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    def _build_propagate_exception_path(self):
        if not self.cpu.propagate_exception_descr:
            return

        mc = PPCBuilder()
        # the following call may be needed in the future:
        # self._store_and_reset_exception()

        mc.load_imm(r.RES, self.cpu.propagate_exception_descr)
        self._gen_epilogue(mc)
        mc.prepare_insts_blocks()
        self.propagate_exception_path = mc.materialize(self.cpu, [])

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

        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu, [], self.cpu.gc_ll_descr.gcrootmap)

    def _gen_epilogue(self, mc):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_footer_shadowstack(gcrootmap, mc)
        # save SPP in r5
        # (assume that r5 has been written to failboxes)
        mc.mr(r.r5.value, r.SPP.value)
        self._restore_nonvolatiles(mc, r.r5)
        # load old backchain into r4
        if IS_PPC_32:
            ofs = WORD
        else:
            ofs = WORD * 2
        mc.load(r.r4.value, r.r5.value, self.OFFSET_SPP_TO_OLD_BACKCHAIN + ofs) 
        mc.mtlr(r.r4.value)     # restore LR
        # From SPP, we have a constant offset to the old backchain. We use the
        # SPP to re-establish the old backchain because this exit stub is
        # generated before we know how much space the entire frame will need.
        mc.addi(r.SP.value, r.r5.value, self.OFFSET_SPP_TO_OLD_BACKCHAIN) # restore old SP
        mc.blr()

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
            self.mc.nop()

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
            pmc.bc(4, 1, offset) # jump if SCRATCH <= r16, i. e. not(SCRATCH > r16)
            pmc.overwrite()

    def setup(self, looptoken):
        BaseAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, "setup_once() not called?"
        self.current_clt = looptoken.compiled_loop_token
        self.pending_guard_tokens = []
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
        #self.max_stack_params = 0

    def _append_debugging_code(self, operations, tp, number, token):
        counter = self._register_counter(tp, number, token)
        c_adr = ConstInt(rffi.cast(lltype.Signed, counter))
        box = BoxInt()
        box2 = BoxInt()
        ops = [ResOperation(rop.GETFIELD_RAW, [c_adr],
                            box, descr=self.debug_counter_descr),
               ResOperation(rop.INT_ADD, [box, ConstInt(1)], box2),
               ResOperation(rop.SETFIELD_RAW, [c_adr, box2],
                            None, descr=self.debug_counter_descr)]
        operations.extend(ops)

    @specialize.argtype(1)
    def _inject_debugging_code(self, looptoken, operations, tp, number):
        if self._debug:
            # before doing anything, let's increase a counter
            s = 0
            for op in operations:
                s += op.getopnum()
            looptoken._ppc_debug_checksum = s

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

    def update_frame_depth(self, frame_depth):
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def patch_stack_checks(self, framedepth, rawstart):
        for ofs in self.frame_depth_to_patch:
            self._patch_frame_depth(ofs + rawstart, framedepth)

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
        rawstart = self.materialize_loop(looptoken)
        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE,
                                rawstart)
        looptoken._ll_loop_code = looppos + rawstart
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
        regalloc.compute_hint_frame_locations(operations)
        regalloc.walk_operations(inputargs, operations)
        if 1: # we_are_translated() or self.cpu.dont_keepalive_stuff:
            self._regalloc = None   # else keep it around for debugging
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._ppc_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

    def assemble_bridge(self, faildescr, inputargs, operations, looptoken, log):
        if not we_are_translated():
            assert len(set(inputargs)) == len(inputargs)

        self.setup(looptoken)
        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)
        assert isinstance(faildescr, AbstractFailDescr)
        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)

        regalloc = Regalloc(assembler=self)
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)

        startpos = self.mc.currpos()
        spilling_area, param_depth = self._assemble(operations, regalloc)
        codeendpos = self.mc.currpos()

        self.write_pending_failure_recoveries()

        rawstart = self.materialize_loop(looptoken, False)
        self.process_pending_guards(rawstart)
        self.patch_trace(faildescr, looptoken, rawstart, regalloc)
        self.fixup_target_tokens(rawstart)
        self.current_clt.frame_depth = max(self.current_clt.frame_depth,
                spilling_area)
        self.current_clt.param_depth = max(self.current_clt.param_depth, param_depth)

        if not we_are_translated():
            # for the benefit of tests
            faildescr._ppc_bridge_frame_depth = self.current_clt.frame_depth
            faildescr._ppc_bridge_param_depth = self.current_clt.param_depth
            if log:
                self.mc._dump_trace(rawstart, 'bridge_%d.asm' %
                self.cpu.total_compiled_bridges)

        self._patch_sp_offset(sp_patch_location, rawstart)

        ops_offset = self.mc.ops_offset
        self.teardown()

        debug_start("jit-backend-addr")
        debug_print("bridge out of Guard %d has address %x to %x" %
                    (descr_number, rawstart, rawstart + codeendpos))
        debug_stop("jit-backend-addr")

        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def _patch_sp_offset(self, sp_patch_location, rawstart):
        mc = PPCBuilder()
        frame_depth = self.compute_frame_depth(self.current_clt.frame_depth,
                                               self.current_clt.param_depth)
        frame_depth -= self.OFFSET_SPP_TO_OLD_BACKCHAIN
        mc.load_imm(r.SCRATCH, -frame_depth)
        mc.add(r.SP.value, r.SPP.value, r.SCRATCH.value)
        mc.prepare_insts_blocks()
        mc.copy_to_raw_memory(rawstart + sp_patch_location)

    DESCR_REF       = 0x00
    DESCR_INT       = 0x01
    DESCR_FLOAT     = 0x02
    DESCR_SPECIAL   = 0x03
    CODE_FROMSTACK  = 128
    CODE_STOP       = 0 | DESCR_SPECIAL
    CODE_HOLE       = 4 | DESCR_SPECIAL
    CODE_INPUTARG   = 8 | DESCR_SPECIAL

    def gen_descr_encoding(self, descr, failargs, locs):
        assert self.mc is not None
        buf = []
        for i in range(len(failargs)):
            arg = failargs[i]
            if arg is not None:
                if arg.type == REF:
                    kind = self.DESCR_REF
                elif arg.type == INT:
                    kind = self.DESCR_INT
                elif arg.type == FLOAT:
                    kind = self.DESCR_FLOAT
                else:
                    raise AssertionError("bogus kind")
                loc = locs[i]
                if loc.is_stack():
                    pos = loc.position
                    if pos < 0:
                        buf.append(self.CODE_INPUTARG)
                        pos = ~pos
                    n = self.CODE_FROMSTACK // 4 + pos
                else:
                    assert loc.is_reg() or loc.is_fp_reg()
                    n = loc.value
                n = kind + 4 * n
                while n > 0x7F:
                    buf.append((n & 0x7F) | 0x80)
                    n >>= 7
            else:
                n = self.CODE_HOLE
            buf.append(n)
        buf.append(self.CODE_STOP)

        fdescr = self.cpu.get_fail_descr_number(descr)

        buf.append((fdescr >> 24) & 0xFF)
        buf.append((fdescr >> 16) & 0xFF)
        buf.append((fdescr >>  8) & 0xFF)
        buf.append( fdescr        & 0xFF)
        
        lenbuf = len(buf)
        # XXX fix memory leaks
        enc_arr = lltype.malloc(rffi.CArray(rffi.CHAR), lenbuf, 
                                flavor='raw', track_allocation=False)
        enc_ptr = rffi.cast(lltype.Signed, enc_arr)
        for i, byte in enumerate(buf):
            enc_arr[i] = chr(byte)
        # assert that the fail_boxes lists are big enough
        assert len(failargs) <= self.fail_boxes_int.SIZE
        return enc_ptr

    def align(self, size):
        while size % 8 != 0:
            size += 1
        return size

    def teardown(self):
        self.patch_list = None
        self.pending_guards = None
        self.current_clt = None
        self.mc = None
        self._regalloc = None
        assert self.datablockwrapper is None
        self.max_stack_params = 0

    def gen_64_bit_func_descr(self):
        return self.datablockwrapper.malloc_aligned(3*WORD, alignment=1)

    def write_64_bit_func_descr(self, descr, start_addr):
        data = rffi.cast(rffi.CArrayPtr(lltype.Signed), descr)
        data[0] = start_addr
        data[1] = 0
        data[2] = 0

    def compute_frame_depth(self, spilling_area, param_depth):
        PARAMETER_AREA = param_depth * WORD
        if IS_PPC_64:
            PARAMETER_AREA += MAX_REG_PARAMS * WORD
        SPILLING_AREA = spilling_area * WORD

        frame_depth = (  GPR_SAVE_AREA
                       + FPR_SAVE_AREA
                       + FLOAT_INT_CONVERSION
                       + FORCE_INDEX
                       + self.ENCODING_AREA
                       + SPILLING_AREA
                       + PARAMETER_AREA
                       + BACKCHAIN_SIZE * WORD)

        # align stack pointer
        while frame_depth % (4 * WORD) != 0:
            frame_depth += WORD

        return frame_depth
    
    def _find_failure_recovery_bytecode(self, faildescr):
        return faildescr._failure_recovery_code_adr

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ppc_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def target_arglocs(self, looptoken):
        return looptoken._ppc_arglocs

    def materialize_loop(self, looptoken, show=False):
        self.mc.prepare_insts_blocks(show)
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu, allblocks,
                                    self.cpu.gc_ll_descr.gcrootmap)
        #print "=== Loop start is at %s ===" % hex(r_uint(start))
        return start

    def push_gcmap(self, mc, gcmap, push=False, store=False):
        ptr = rffi.cast(lltype.Signed, gcmap)
        if push:
            with scratch_reg(mc):
                mc.load_imm(r.SCRATCH, ptr)
                mc.stdu(r.SCRATCH.value, r.SP.value, -WORD)
        elif store:
            assert False, "Not implemented"

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.currpos()
        fail_descr, target = self.store_info_on_descr(startpos, guardtok)
        self.regalloc_push(imm(fail_descr))
        self.push_gcmap(self.mc, gcmap=guardtok.gcmap, push=True)
        self.mc.call(target)
        return startpos

    def write_pending_failure_recoveries(self):
        # for each pending guard, generate the code of the recovery stub
        # at the end of self.mc.
        for tok in self.pending_guard_tokens:
            tok.pos_recovery_stub = self.generate_quick_failure(tok)

    def patch_pending_failure_recoveries(self, rawstart):
        clt = self.current_clt
        for tok in self.pending_guard_tokens:
            xxxxxxxxx

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.faildescr
            assert isinstance(descr, AbstractFailDescr)
            descr._ppc_block_start = block_start

            if not tok.is_guard_not_invalidated:
                mc = PPCBuilder()
                offset = tok.pos_recovery_stub - tok.offset
                mc.b_cond_offset(offset, tok.fcond)
                mc.prepare_insts_blocks(True)
                mc.copy_to_raw_memory(block_start + tok.offset)
            else:
                clt.invalidate_positions.append((block_start + tok.offset,
                        descr._ppc_guard_pos - tok.offset))

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        # The first instruction (word) is not overwritten, because it is the
        # one that actually checks the condition
        mc = PPCBuilder()
        patch_addr = faildescr._ppc_block_start + faildescr._ppc_guard_pos
        mc.b_abs(bridge_addr)
        mc.prepare_insts_blocks()
        mc.copy_to_raw_memory(patch_addr)
        faildescr._failure_recovery_code_ofs = 0

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def _prepare_sp_patch_position(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update
        the sp according to the number of spilled variables"""
        size = SIZE_LOAD_IMM_PATCH_SP
        l = self.mc.currpos()
        for _ in range(size):
            self.mc.nop()
        return l

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
                    self.mc.store(r.SCRATCH.value, r.SPP.value, offset)
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

    def regalloc_push(self, loc):
        """Pushes the value stored in loc to the stack
        Can trash the current value of SCRATCH when pushing a stack
        loc"""
        self.mc.addi(r.SP.value, r.SP.value, -WORD) # decrease stack pointer
        assert IS_PPC_64, 'needs to updated for ppc 32'

        if loc.is_imm():
            with scratch_reg(self.mc):
                self.regalloc_mov(loc, r.SCRATCH)
                self.mc.store(r.SCRATCH.value, r.SP.value, 0)
        elif loc.is_imm_float():
            with scratch_reg(self.mc):
                self.regalloc_mov(loc, r.FP_SCRATCH)
                self.mc.store(r.FP_SCRATCH.value, r.SP.value, 0)
        elif loc.is_stack():
            # XXX this code has to be verified
            with scratch_reg(self.mc):
                self.regalloc_mov(loc, r.SCRATCH)
                # push value
                self.mc.store(r.SCRATCH.value, r.SP.value, 0)
        elif loc.is_reg():
            # push value
            self.mc.store(loc.value, r.SP.value, 0)
        elif loc.is_fp_reg():
            self.mc.addi(r.SP.value, r.SP.value, -WORD) # decrease stack pointer
            # push value
            self.mc.stfd(loc.value, r.SP.value, 0)
        else:
            raise AssertionError('Trying to push an invalid location')

    def regalloc_pop(self, loc):
        """Pops the value on top of the stack to loc. Can trash the current
        value of SCRATCH when popping to a stack loc"""
        assert IS_PPC_64, 'needs to updated for ppc 32'
        if loc.is_stack():
            # XXX this code has to be verified
            with scratch_reg(self.mc):
                # pop value
                if IS_PPC_32:
                    self.mc.lwz(r.SCRATCH.value, r.SP.value, 0)
                else:
                    self.mc.ld(r.SCRATCH.value, r.SP.value, 0)
                self.mc.addi(r.SP.value, r.SP.value, WORD) # increase stack pointer
                self.regalloc_mov(r.SCRATCH, loc)
        elif loc.is_reg():
            # pop value
            if IS_PPC_32:
                self.mc.lwz(loc.value, r.SP.value, 0)
            else:
                self.mc.ld(loc.value, r.SP.value, 0)
            self.mc.addi(r.SP.value, r.SP.value, WORD) # increase stack pointer
        elif loc.is_fp_reg():
            self.mc.lfd(loc.value, r.SP.value, 0)
            self.mc.addi(r.SP.value, r.SP.value, WORD) # increase stack pointer
        else:
            raise AssertionError('Trying to pop to an invalid location')

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == 1:
            if not signed: #unsigned char
                if IS_PPC_32:
                    self.mc.rlwinm(resloc.value, resloc.value, 0, 24, 31)
                else:
                    self.mc.rldicl(resloc.value, resloc.value, 0, 56)
            else:
                self.mc.extsb(resloc.value, resloc.value)
        elif size == 2:
            if not signed:
                if IS_PPC_32:
                    self.mc.rlwinm(resloc.value, resloc.value, 0, 16, 31)
                else:
                    self.mc.rldicl(resloc.value, resloc.value, 0, 48)
            else:
                self.mc.extsh(resloc.value, resloc.value)
        elif size == 4:
            if not signed:
                self.mc.rldicl(resloc.value, resloc.value, 0, 32)
            else:
                self.mc.extsw(resloc.value, resloc.value)

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
        self.mc.nop()

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
        pmc.bc(4, 1, offset) # jump if LE (not GT)
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
        self.mc.cmp_op(0, r.RES.value, 0, imm=True)
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

def notimplemented_op_with_guard(self, op, guard_op, arglocs, regalloc):
    print "[PPC/asm] %s with guard %s not implemented" % \
            (op.getopname(), guard_op.getopname())
    raise NotImplementedError(op)

operations = [notimplemented_op] * (rop._LAST + 1)
operations_with_guard = [notimplemented_op_with_guard] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_%s' % key
    if hasattr(AssemblerPPC, methname):
        func = getattr(AssemblerPPC, methname).im_func
        operations[value] = func

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_guard_%s' % key
    if hasattr(AssemblerPPC, methname):
        func = getattr(AssemblerPPC, methname).im_func
        operations_with_guard[value] = func

AssemblerPPC.operations = operations
AssemblerPPC.operations_with_guard = operations_with_guard

class BridgeAlreadyCompiled(Exception):
    pass
