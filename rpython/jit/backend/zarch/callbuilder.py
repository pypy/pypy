from rpython.jit.backend.zarch.arch import WORD
from rpython.jit.backend.zarch.arch import (THREADLOCAL_ADDR_OFFSET,
        STD_FRAME_SIZE_IN_BYTES)
import rpython.jit.backend.zarch.locations as l
import rpython.jit.backend.zarch.registers as r
from rpython.jit.metainterp.history import INT, FLOAT
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.llsupport.jump import remap_frame_layout
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.backend.llsupport import llerrno
from rpython.rtyper.lltypesystem import rffi

class CallBuilder(AbstractCallBuilder):
    GPR_ARGS = [r.r2, r.r3, r.r4, r.r5, r.r6]
    FPR_ARGS =  [r.f0, r.f2, r.f4, r.f6]
    
    RSHADOWOLD  = r.r9
    RSHADOWPTR  = r.r10
    RFASTGILPTR = r.r12

    def __init__(self, assembler, fnloc, arglocs, resloc):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype=INT, ressize=None)

    def prepare_arguments(self):
        self.subtracted_to_sp = 0

        # Prepare arguments.  Note that this follows the convention where
        # a prototype is in scope, and doesn't take "..." arguments.  If
        # you were to call a C function with a "..." argument with cffi,
        # it would not go there but instead via libffi.  If you pretend
        # instead that it takes fixed arguments, then it would arrive here
        # but the convention is bogus for floating-point arguments.  (And,
        # to add to the mess, at least CPython's ctypes cannot be used
        # to call a "..." function with floating-point arguments.  As I
        # guess that it's a problem with libffi, it means PyPy inherits
        # the same problem.)
        arglocs = self.arglocs
        num_args = len(arglocs)

        max_gpr_in_reg = 5
        max_fpr_in_reg = 4

        non_float_locs = []
        non_float_regs = []
        float_locs = []

        # the IBM zarch manual states:
        # """
        # A function will be passed a frame on the runtime stack by the function which
        # called it, and may allocate a new stack frame. A new stack frame is required if the
        # called function will in turn call further functions (which must be passed the
        # address of the new frame). This stack grows downwards from high addresses
        # """
        self.subtracted_to_sp = STD_FRAME_SIZE_IN_BYTES

        gpr_regs = 0
        fpr_regs = 0
        stack_params = []
        for i in range(num_args):
            loc = arglocs[i]
            if not arglocs[i].is_float():
                if gpr_regs < max_gpr_in_reg:
                    non_float_locs.append(arglocs[i])
                    non_float_regs.append(self.GPR_ARGS[gpr_regs])
                    gpr_regs += 1
                else:
                    stack_params.append(i)
            else:
                if fpr_regs < max_fpr_in_reg:
                    float_locs.append(arglocs[i])
                    fpr_regs += 1
                else:
                    stack_params.append(i)

        self.subtracted_to_sp += len(stack_params) * 8
        base = -len(stack_params) * 8
        for idx,i in enumerate(stack_params):
            loc = arglocs[i]
            offset = base + 8 * idx
            if loc.type == FLOAT:
                if loc.is_fp_reg():
                    src = loc
                else:
                    src = r.FP_SCRATCH
                    self.asm.regalloc_mov(loc, src)
                self.mc.STDY(src, l.addr(offset, r.SP))
            else:
                if loc.is_core_reg():
                    src = loc
                else:
                    src = r.SCRATCH
                    self.asm.regalloc_mov(loc, src)
                self.mc.STG(src, l.addr(offset, r.SP))

        # We must also copy fnloc into FNREG
        non_float_locs.append(self.fnloc)
        non_float_regs.append(r.RETURN)

        if float_locs:
            assert len(float_locs) <= len(self.FPR_ARGS)
            remap_frame_layout(self.asm, float_locs,
                               self.FPR_ARGS[:len(float_locs)],
                               r.FP_SCRATCH)

        remap_frame_layout(self.asm, non_float_locs, non_float_regs,
                           r.SCRATCH)

    def push_gcmap(self):
        # we push *now* the gcmap, describing the status of GC registers
        # after the rearrangements done just before, ignoring the return
        # value r3, if necessary
        assert not self.is_call_release_gil
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([r.r3], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap, store=True)

    def pop_gcmap(self):
        ssreg = None
        gcrootmap = self.asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            if gcrootmap.is_shadow_stack and self.is_call_release_gil:
                # in this mode, RSHADOWOLD happens to contain the shadowstack
                # top at this point, so reuse it instead of loading it again
                xxx
                ssreg = self.RSHADOWOLD
        self.asm._reload_frame_if_necessary(self.mc, shadowstack_reg=ssreg)

    def emit_raw_call(self):
        # always allocate a stack frame for the new function
        # save the SP back chain
        self.mc.STG(r.SP, l.addr(-self.subtracted_to_sp, r.SP))
        # move the frame pointer
        self.mc.AGHI(r.SP, l.imm(-self.subtracted_to_sp))
        self.mc.raw_call()
        # restore the pool!
        offset = self.asm.pool.pool_start - self.mc.get_relative_pos()
        self.mc.LARL(r.POOL, l.halfword(offset))

    def restore_stack_pointer(self):
        if self.subtracted_to_sp != 0:
            self.mc.AGHI(r.SP, l.imm(self.subtracted_to_sp))

    def load_result(self):
        assert (self.resloc is None or
                self.resloc is r.GPR_RETURN or
                self.resloc is r.FPR_RETURN)


    def call_releasegil_addr_and_move_real_arguments(self, fastgil):
        assert self.is_call_release_gil
        RSHADOWOLD = self.RSHADOWOLD
        RSHADOWPTR = self.RSHADOWPTR
        RFASTGILPTR = self.RFASTGILPTR
        #
        # assumes RSHADOWOLD to be r9, stores all up to r15
        self.mc.STMG(RSHADOWOLD, r.r15, l.addr(9 * WORD, r.SP))
        #
        # Save this thread's shadowstack pointer into r29, for later comparison
        gcrootmap = self.asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            if gcrootmap.is_shadow_stack:
                rst = gcrootmap.get_root_stack_top_addr()
                self.mc.load_imm(RSHADOWPTR, rst)
                self.mc.LGR(RSHADOWOLD, RSHADOWPTR)
        #
        # change 'rpy_fastgil' to 0 (it should be non-zero right now)
        self.mc.load_imm(RFASTGILPTR, fastgil)
        self.mc.LGHI(r.SCRATCH, l.imm(0))
        self.mc.STG(r.SCRATCH, l.addr(0, RFASTGILPTR))
        self.mc.sync() # renders the store visible to other cpus
        #
        if not we_are_translated():        # for testing: we should not access
            self.mc.AGHI(r.SPP, l.imm(1))  # r31 any more


    def move_real_result_and_call_reacqgil_addr(self, fastgil):
        from rpython.jit.backend.zarch.codebuilder import InstrBuilder

        # try to reacquire the lock.  The following registers are still
        # valid from before the call:
        RSHADOWPTR  = self.RSHADOWPTR     # r9: &root_stack_top
        RFASTGILPTR = self.RFASTGILPTR    # r10: &fastgil
        RSHADOWOLD  = self.RSHADOWOLD     # r12: previous val of root_stack_top

        # Equivalent of 'r14 = __sync_lock_test_and_set(&rpy_fastgil, 1);'
        self.mc.LGHI(r.r11, l.imm(1))
        self.mc.LGHI(r.r14, l.imm(0))
        retry_label = self.mc.currpos()
        # compare and swap, only succeeds if the the contents of the
        # lock is equal to r14 (= 0)
        self.mc.CSG(r.r14, r.r11, l.addr(RFASTGILPTR))  # try to claim lock
        self.mc.BRC(c.EQ, l.imm(retry_label - self.mc.currpos())) # retry if failed
        #self.mc.sync()

        self.mc.cmpdi(0, r.r10.value, 0)
        b1_location = self.mc.currpos()
        self.mc.trap()       # boehm: patched with a BEQ: jump if r10 is zero
                             # shadowstack: patched with BNE instead

        if self.asm.cpu.gc_ll_descr.gcrootmap:
            # When doing a call_release_gil with shadowstack, there
            # is the risk that the 'rpy_fastgil' was free but the
            # current shadowstack can be the one of a different
            # thread.  So here we check if the shadowstack pointer
            # is still the same as before we released the GIL (saved
            # in RSHADOWOLD), and if not, we fall back to 'reacqgil_addr'.
            self.mc.load(r.r9.value, RSHADOWPTR.value, 0)
            self.mc.cmpdi(0, r.r9.value, RSHADOWOLD.value)
            bne_location = b1_location
            b1_location = self.mc.currpos()
            self.mc.trap()

            # revert the rpy_fastgil acquired above, so that the
            # general 'reacqgil_addr' below can acquire it again...
            # (here, r10 is conveniently zero)
            self.mc.std(r.r10.value, RFASTGILPTR.value, 0)

            pmc = InstrBuilder(self.mc, bne_location, 1)
            xxx
            pmc.BCR(l.imm(0xf), self.mc.currpos() - bne_location)
            pmc.overwrite()
        #
        # Yes, we need to call the reacqgil() function.
        # save the result we just got
        RSAVEDRES = RFASTGILPTR     # can reuse this reg here
        reg = self.resloc
        xxx
        PARAM_SAVE_AREA_OFFSET = 0
        if reg is not None:
            if reg.is_core_reg():
                self.mc.mr(RSAVEDRES.value, reg.value)
            elif reg.is_fp_reg():
                self.mc.stfd(reg.value, r.SP.value,
                             PARAM_SAVE_AREA_OFFSET + 7 * WORD)
        self.mc.load_imm(self.mc.RAW_CALL_REG, self.asm.reacqgil_addr)
        self.mc.raw_call()
        if reg is not None:
            if reg.is_core_reg():
                self.mc.mr(reg.value, RSAVEDRES.value)
            elif reg.is_fp_reg():
                self.mc.lfd(reg.value, r.SP.value,
                            PARAM_SAVE_AREA_OFFSET + 7 * WORD)

        # replace b1_location with BEQ(here)
        pmc = OverwritingBuilder(self.mc, b1_location, 1)
        pmc.beq(self.mc.currpos() - b1_location)
        pmc.overwrite()

        if not we_are_translated():        # for testing: now we can access
            self.mc.addi(r.SPP.value, r.SPP.value, -1)          # r31 again


    def write_real_errno(self, save_err):
        if save_err & rffi.RFFI_READSAVED_ERRNO:
            # Just before a call, read '*_errno' and write it into the
            # real 'errno'.  A lot of registers are free here, notably
            # r11 and r0.
            if save_err & rffi.RFFI_ALT_ERRNO:
                rpy_errno = llerrno.get_alt_errno_offset(self.asm.cpu)
            else:
                rpy_errno = llerrno.get_rpy_errno_offset(self.asm.cpu)
            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)
            self.mc.LG(r.r11,
                       l.addr(THREADLOCAL_ADDR_OFFSET + self.subtracted_to_sp, r.SP))
            self.mc.LGH(r.SCRATCH2, l.addr(rpy_errno, r.r11))
            self.mc.LG(r.r11, l.addr(p_errno, r.r11))
            self.mc.STHY(r.SCRATCH2, l.addr(0,r.r11))
        elif save_err & rffi.RFFI_ZERO_ERRNO_BEFORE:
            # Same, but write zero.
            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)
            self.mc.LG(r.r11,
                       l.addr(THREADLOCAL_ADDR_OFFSET + self.subtracted_to_sp, r.SP))
            self.mc.LG(r.r11, l.addr(p_errno, r.r11))
            self.mc.LGHI(r.SCRATCH, 0)
            self.mc.STHY(r.SCRATCH, l.addr(0,r.r11))

    def read_real_errno(self, save_err):
        if save_err & rffi.RFFI_SAVE_ERRNO:
            # Just after a call, read the real 'errno' and save a copy of
            # it inside our thread-local '*_errno'.  Registers r4-r10
            # never contain anything after the call.
            if save_err & rffi.RFFI_ALT_ERRNO:
                rpy_errno = llerrno.get_alt_errno_offset(self.asm.cpu)
            else:
                rpy_errno = llerrno.get_rpy_errno_offset(self.asm.cpu)
            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)
            self.mc.ld(r.r9.value, r.SP.value, THREADLOCAL_ADDR_OFFSET)
            self.mc.ld(r.r10.value, r.r9.value, p_errno)
            self.mc.lwz(r.r10.value, r.r10.value, 0)
            self.mc.stw(r.r10.value, r.r9.value, rpy_errno)
