
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.aarch64.arch import WORD
from rpython.jit.metainterp.history import INT, FLOAT, REF
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.aarch64.jump import remap_frame_layout # we use arm algo

from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi

class Aarch64CallBuilder(AbstractCallBuilder):
    def __init__(self, assembler, fnloc, arglocs,
                 resloc=r.x0, restype=INT, ressize=WORD, ressigned=True):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype, ressize)
        self.current_sp = 0

    def prepare_arguments(self):
        arglocs = self.arglocs
        non_float_locs = []
        non_float_regs = []
        float_locs = []
        float_regs = []
        stack_locs = []
        free_regs = [r.x7, r.x6, r.x5, r.x4, r.x3, r.x2, r.x1, r.x0]
        free_float_regs = [r.d7, r.d6, r.d5, r.d4, r.d3, r.d2, r.d1, r.d0]
        for arg in arglocs:
            if arg.type == FLOAT:
                if free_float_regs:
                    float_locs.append(arg)
                    float_regs.append(free_float_regs.pop())
                else:
                    stack_locs.append(arg)
            else:
                if free_regs:
                    non_float_locs.append(arg)
                    non_float_regs.append(free_regs.pop())
                else:
                    stack_locs.append(arg)
        remap_frame_layout(self.asm, non_float_locs, non_float_regs, r.ip0)
        if float_locs:
            remap_frame_layout(self.asm, float_locs, float_regs, r.d8)
        # move the remaining things to stack and adjust the stack
        if not stack_locs:
            return
        adj = len(stack_locs) + (len(stack_locs) & 1)
        self.mc.SUB_ri(r.sp.value, r.sp.value, adj * WORD)
        self.current_sp = adj
        c = 0
        for loc in stack_locs:
            self.asm.mov_loc_to_raw_stack(loc, c)
            c += WORD

    def push_gcmap(self):
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([r.x0], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap)

    def pop_gcmap(self):
        self.asm._reload_frame_if_necessary(self.mc)
        self.asm.pop_gcmap(self.mc)        

    def emit_raw_call(self):
        #the actual call
        if self.fnloc.is_imm():
            self.mc.BL(self.fnloc.value)
            return
        if self.fnloc.is_stack():
            self.mc.LDR_ri(r.ip0.value, r.fp.value, self.fnloc.value)
            self.mc.BLR_r(r.ip0.value)
        else:
            assert self.fnloc.is_core_reg()
            self.mc.BLR_r(self.fnloc.value)

    def restore_stack_pointer(self):
        assert self.current_sp & 1 == 0 # always adjusted to 16 bytes
        if self.current_sp == 0:
            return
        self.mc.ADD_ri(r.sp.value, r.sp.value, self.current_sp * WORD)
        self.current_sp = 0

    def load_result(self):
        resloc = self.resloc
        if self.restype == 'S':
            XXX
            self.mc.VMOV_sc(resloc.value, r.s0.value)
        elif self.restype == 'L':
            YYY
            assert resloc.is_vfp_reg()
            self.mc.FMDRR(resloc.value, r.r0.value, r.r1.value)
        # ensure the result is wellformed and stored in the correct location
        if resloc is not None and resloc.is_core_reg():
            self._ensure_result_bit_extension(resloc,
                                                  self.ressize, self.ressign)

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == WORD:
            return
        if size == 4:
            if not signed: # unsigned int
                self.mc.LSL_ri(resloc.value, resloc.value, 32)
                self.mc.LSR_ri(resloc.value, resloc.value, 32)
            else: # signed int
                self.mc.LSL_ri(resloc.value, resloc.value, 32)
                self.mc.ASR_ri(resloc.value, resloc.value, 32)
        elif size == 2:
            if not signed:
                self.mc.LSL_ri(resloc.value, resloc.value, 48)
                self.mc.LSR_ri(resloc.value, resloc.value, 48)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 48)
                self.mc.ASR_ri(resloc.value, resloc.value, 48)
        elif size == 1:
            if not signed:  # unsigned char
                self.mc.AND_ri(resloc.value, resloc.value, 0xFF)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 56)
                self.mc.ASR_ri(resloc.value, resloc.value, 56)

    def call_releasegil_addr_and_move_real_arguments(self, fastgil):
        assert self.is_call_release_gil
        assert not self.asm._is_asmgcc()

        # Save this thread's shadowstack pointer into r7, for later comparison
        gcrootmap = self.asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            XXX
            rst = gcrootmap.get_root_stack_top_addr()
            self.mc.gen_load_int(r.r5.value, rst)
            self.mc.LDR_ri(r.r7.value, r.r5.value)

        # change 'rpy_fastgil' to 0 (it should be non-zero right now)
        self.mc.DMB()
        self.mc.gen_load_int(r.ip1.value, fastgil)
        self.mc.MOVZ_r_u16(r.ip0.value, 0, 0)
        self.mc.STR_ri(r.ip0.value, r.ip1.value, 0)

        if not we_are_translated():                     # for testing: we should not access
            self.mc.ADD_ri(r.fp.value, r.fp.value, 1)   # fp any more

    def write_real_errno(self, save_err):
        if save_err & rffi.RFFI_READSAVED_ERRNO:
            xxx
        elif save_err & rffi.RFFI_ZERO_ERRNO_BEFORE:
            yyy

    def read_real_errno(self, save_err):
        if save_err & rffi.RFFI_SAVE_ERRNO:
            xxx        

    def move_real_result_and_call_reacqgil_addr(self, fastgil):
        # try to reacquire the lock.
        #     XXX r5 == &root_stack_top
        #     r6 == fastgil
        #     XXX r7 == previous value of root_stack_top
        self.mc.gen_load_int(r.ip1.value, fastgil)
        self.mc.LDREX(r.x0.value, r.r6.value)    # load the lock value
        self.mc.MOV_ri(r.ip.value, 1)
        self.mc.CMP_ri(r.r3.value, 0)            # is the lock free?
        self.mc.STREX(r.r3.value, r.ip.value, r.r6.value, c=c.EQ)
                                                 # try to claim the lock
        self.mc.CMP_ri(r.r3.value, 0, cond=c.EQ) # did this succeed?
        if self.asm.cpu.cpuinfo.arch_version >= 7:
            self.mc.DMB()
        # the success of the lock acquisition is defined by
        # 'EQ is true', or equivalently by 'r3 == 0'.
        #
        if self.asm.cpu.gc_ll_descr.gcrootmap:
            # When doing a call_release_gil with shadowstack, there
            # is the risk that the 'rpy_fastgil' was free but the
            # current shadowstack can be the one of a different
            # thread.  So here we check if the shadowstack pointer
            # is still the same as before we released the GIL (saved
            # in 'r7'), and if not, we fall back to 'reacqgil_addr'.
            self.mc.LDR_ri(r.ip.value, r.r5.value, cond=c.EQ)
            self.mc.CMP_rr(r.ip.value, r.r7.value, cond=c.EQ)
            b1_location = self.mc.currpos()
            self.mc.BKPT()                       # BEQ below
            # there are two cases here: either EQ was false from
            # the beginning, or EQ was true at first but the CMP
            # made it false.  In the second case we need to
            # release the fastgil here.  We know which case it is
            # by checking again r3.
            self.mc.CMP_ri(r.r3.value, 0)
            self.mc.STR_ri(r.r3.value, r.r6.value, cond=c.EQ)
        else:
            b1_location = self.mc.currpos()
            self.mc.BKPT()                       # BEQ below
        #
        # save the result we just got
        gpr_to_save, vfp_to_save = self.get_result_locs()
        with saved_registers(self.mc, gpr_to_save, vfp_to_save):
            self.mc.BL(self.asm.reacqgil_addr)

        # replace b1_location with B(here, c.EQ)
        pmc = OverwritingBuilder(self.mc, b1_location, WORD)
        pmc.B_offs(self.mc.currpos(), c.EQ)

        if not we_are_translated():                    # for testing: now we can accesss
            self.mc.SUB_ri(r.fp.value, r.fp.value, 1)  # fp again

    def get_result_locs(self):
        if self.resloc is None:
            return [], []
        if self.resloc.is_vfp_reg():
            if self.restype == 'L':      # long long
                return [r.r0, r.r1], []
            else:
                return [], [r.d0]
        assert self.resloc.is_core_reg()
        return [r.r0], []
