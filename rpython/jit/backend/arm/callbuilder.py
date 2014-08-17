from rpython.rlib.clibffi import FFI_DEFAULT_ABI
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.history import INT, FLOAT, REF
from rpython.jit.backend.arm.arch import WORD
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.arm.locations import RawSPStackLocation
from rpython.jit.backend.arm.jump import remap_frame_layout
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.arm.helper.assembler import count_reg_args
from rpython.jit.backend.arm.helper.assembler import saved_registers
from rpython.jit.backend.arm.helper.regalloc import check_imm_arg


class ARMCallbuilder(AbstractCallBuilder):
    def __init__(self, assembler, fnloc, arglocs,
                 resloc=r.r0, restype=INT, ressize=WORD, ressigned=True):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype, ressize)
        self.current_sp = 0

    def push_gcmap(self):
        assert not self.is_call_release_gil
        # we push *now* the gcmap, describing the status of GC registers
        # after the rearrangements done just above, ignoring the return
        # value eax, if necessary
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([r.r0], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap, store=True)

    def pop_gcmap(self):
        self.asm._reload_frame_if_necessary(self.mc)
        self.asm.pop_gcmap(self.mc)

    def emit_raw_call(self):
        #the actual call
        if self.fnloc.is_imm():
            self.mc.BL(self.fnloc.value)
            return
        if self.fnloc.is_stack():
            self.asm.mov_loc_loc(self.fnloc, r.ip)
            self.fnloc = r.ip
        assert self.fnloc.is_core_reg()
        self.mc.BLX(self.fnloc.value)

    def restore_stack_pointer(self):
        # readjust the sp in case we passed some args on the stack
        assert self.current_sp % 8 == 0  # sanity check
        if self.current_sp != 0:
            self._adjust_sp(self.current_sp)
        self.current_sp = 0

    def _push_stack_args(self, stack_args, on_stack):
        assert on_stack % 8 == 0
        if on_stack == 0:
            return
        self._adjust_sp(-on_stack)
        self.current_sp = on_stack
        ofs = 0
        for i, arg in enumerate(stack_args):
            if arg is not None:
                sp_loc = RawSPStackLocation(ofs, arg.type)
                self.asm.regalloc_mov(arg, sp_loc)
                ofs += sp_loc.width
            else:  # alignment word
                ofs += WORD

    def _adjust_sp(self, n):
        # adjust the current stack pointer by n bytes
        if n > 0:
            if check_imm_arg(n):
                self.mc.ADD_ri(r.sp.value, r.sp.value, n)
            else:
                self.mc.gen_load_int(r.ip.value, n)
                self.mc.ADD_rr(r.sp.value, r.sp.value, r.ip.value)
        elif n < 0:
            n = abs(n)
            if check_imm_arg(n):
                self.mc.SUB_ri(r.sp.value, r.sp.value, n)
            else:
                self.mc.gen_load_int(r.ip.value, n)
                self.mc.SUB_rr(r.sp.value, r.sp.value, r.ip.value)

    def select_call_release_gil_mode(self):
        AbstractCallBuilder.select_call_release_gil_mode(self)

    def call_releasegil_addr_and_move_real_arguments(self):
        assert not self.asm._is_asmgcc()
        from rpython.jit.backend.arm.regalloc import CoreRegisterManager
        with saved_registers(self.mc,
                            CoreRegisterManager.save_around_call_regs):
            self.mc.BL(self.asm.releasegil_addr)

        if not we_are_translated():                     # for testing: we should not access
            self.mc.ADD_ri(r.fp.value, r.fp.value, 1)   # fp any more

    def move_real_result_and_call_reacqgil_addr(self):
        # save the result we just got
        assert not self.asm._is_asmgcc()
        gpr_to_save, vfp_to_save = self.get_result_locs()
        with saved_registers(self.mc, gpr_to_save, vfp_to_save):
            self.mc.BL(self.asm.reacqgil_addr)

        if not we_are_translated():                    # for testing: now we can accesss
            self.mc.SUB_ri(r.fp.value, r.fp.value, 1)  # fp again

        #   for shadowstack, done for us by _reload_frame_if_necessary()

    def get_result_locs(self):
        raise NotImplementedError

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == 4:
            return
        if size == 1:
            if not signed:  # unsigned char
                self.mc.AND_ri(resloc.value, resloc.value, 0xFF)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 24)
                self.mc.ASR_ri(resloc.value, resloc.value, 24)
        elif size == 2:
            if not signed:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.LSR_ri(resloc.value, resloc.value, 16)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.ASR_ri(resloc.value, resloc.value, 16)



class SoftFloatCallBuilder(ARMCallbuilder):

    def get_result_locs(self):
        if self.resloc is None:
            return [], []
        if self.resloc.is_vfp_reg():
            return [r.r0, r.r1], []
        assert self.resloc.is_core_reg()
        return [r.r0], []

    def load_result(self):
        # ensure the result is wellformed and stored in the correct location
        resloc = self.resloc
        if resloc is None:
            return
        if resloc.is_vfp_reg():
            # move result to the allocated register
            self.asm.mov_to_vfp_loc(r.r0, r.r1, resloc)
        elif resloc.is_core_reg():
            # move result to the allocated register
            if resloc is not r.r0:
                self.asm.mov_loc_loc(r.r0, resloc)
            self._ensure_result_bit_extension(resloc,
                                              self.ressize, self.ressign)


    def _collect_and_push_stack_args(self, arglocs):
        n_args = len(arglocs)
        reg_args = count_reg_args(arglocs)
        # all arguments past the 4th go on the stack
        # first we need to prepare the list so it stays aligned
        stack_args = []
        count = 0
        on_stack = 0
        if n_args > reg_args:
            for i in range(reg_args, n_args):
                arg = arglocs[i]
                if arg.type != FLOAT:
                    count += 1
                    on_stack += 1
                else:
                    on_stack += 2
                    if count % 2 != 0:
                        stack_args.append(None)
                        count = 0
                        on_stack += 1
                stack_args.append(arg)
            if count % 2 != 0:
                on_stack += 1
                stack_args.append(None)
        if on_stack > 0:
            self._push_stack_args(stack_args, on_stack*WORD)

    def prepare_arguments(self):
        arglocs = self.arglocs
        reg_args = count_reg_args(arglocs)
        self._collect_and_push_stack_args(arglocs)
        # collect variables that need to go in registers and the registers they
        # will be stored in
        num = 0
        count = 0
        non_float_locs = []
        non_float_regs = []
        float_locs = []
        for i in range(reg_args):
            arg = arglocs[i]
            if arg.type == FLOAT and count % 2 != 0:
                    num += 1
                    count = 0
            reg = r.caller_resp[num]

            if arg.type == FLOAT:
                float_locs.append((arg, reg))
            else:
                non_float_locs.append(arg)
                non_float_regs.append(reg)

            if arg.type == FLOAT:
                num += 2
            else:
                num += 1
                count += 1
        # Check that the address of the function we want to call is not
        # currently stored in one of the registers used to pass the arguments
        # or on the stack, which we can not access later
        # If this happens to be the case we remap the register to r4 and use r4
        # to call the function
        if self.fnloc in r.argument_regs or self.fnloc.is_stack():
            non_float_locs.append(self.fnloc)
            non_float_regs.append(r.r4)
            self.fnloc = r.r4
        # remap values stored in core registers
        remap_frame_layout(self.asm, non_float_locs, non_float_regs, r.ip)

        for loc, reg in float_locs:
            self.asm.mov_from_vfp_loc(loc, reg, r.all_regs[reg.value + 1])

class HardFloatCallBuilder(ARMCallbuilder):

    next_arg_vfp = 0
    next_arg_svfp = 0

    def get_next_vfp(self, tp):
        assert tp in 'fS'
        if self.next_arg_vfp == -1:
            return None
        if tp == 'S':
            i = self.next_arg_svfp
            next_vfp = (i >> 1) + 1
            if not (i + 1) & 1: # i is even
                self.next_arg_vfp = max(self.next_arg_vfp, next_vfp)
                self.next_arg_svfp = self.next_arg_vfp << 1
            else:
                self.next_arg_svfp += 1
                self.next_arg_vfp = next_vfp
            lst = r.svfp_argument_regs
        else: # 64bit double
            i = self.next_arg_vfp
            self.next_arg_vfp += 1
            if self.next_arg_svfp >> 1 == i:
                self.next_arg_svfp = self.next_arg_vfp << 1
            lst = r.vfp_argument_regs
        try:
            return lst[i]
        except IndexError:
            self.next_arg_vfp = self.next_arg_svfp = -1
            return None

    def prepare_arguments(self):
        non_float_locs = []
        non_float_regs = []
        float_locs = []
        float_regs = []
        stack_args = []
        singlefloats = None

        arglocs = self.arglocs
        argtypes = self.argtypes

        count = 0                      # stack alignment counter
        on_stack = 0
        for i in range(len(arglocs)):
            argtype = INT
            if i < len(argtypes) and argtypes[i] == 'S':
                argtype = argtypes[i]
            arg = arglocs[i]
            if arg.is_float():
                argtype = FLOAT
                reg = self.get_next_vfp(argtype)
                if reg:
                    assert len(float_regs) < len(r.vfp_argument_regs)
                    float_locs.append(arg)
                    assert reg not in float_regs
                    float_regs.append(reg)
                else:  # float argument that needs to go on the stack
                    if count % 2 != 0:
                        stack_args.append(None)
                        count = 0
                        on_stack += 1
                    stack_args.append(arg)
                    on_stack += 2
            elif argtype == 'S':
                # Singlefloat argument
                if singlefloats is None:
                    singlefloats = []
                tgt = self.get_next_vfp(argtype)
                if tgt:
                    singlefloats.append((arg, tgt))
                else:  # Singlefloat argument that needs to go on the stack
                       # treated the same as a regular core register argument
                    count += 1
                    on_stack += 1
                    stack_args.append(arg)
            else:
                if len(non_float_regs) < len(r.argument_regs):
                    reg = r.argument_regs[len(non_float_regs)]
                    non_float_locs.append(arg)
                    non_float_regs.append(reg)
                else:  # non-float argument that needs to go on the stack
                    count += 1
                    on_stack += 1
                    stack_args.append(arg)
        # align the stack
        if count % 2 != 0:
            stack_args.append(None)
            on_stack += 1
        self._push_stack_args(stack_args, on_stack*WORD)
        # Check that the address of the function we want to call is not
        # currently stored in one of the registers used to pass the arguments
        # or on the stack, which we can not access later
        # If this happens to be the case we remap the register to r4 and use r4
        # to call the function
        if self.fnloc in non_float_regs or self.fnloc.is_stack():
            non_float_locs.append(self.fnloc)
            non_float_regs.append(r.r4)
            self.fnloc = r.r4
        # remap values stored in vfp registers
        remap_frame_layout(self.asm, float_locs, float_regs, r.vfp_ip)
        if singlefloats:
            for src, dest in singlefloats:
                if src.is_float():
                    assert 0, 'unsupported case'
                if src.is_stack():
                    # use special VLDR for 32bit
                    self.asm.regalloc_mov(src, r.ip)
                    src = r.ip
                if src.is_imm():
                    self.mc.gen_load_int(r.ip.value, src.value)
                    src = r.ip
                if src.is_core_reg():
                    self.mc.VMOV_cs(dest.value, src.value)
        # remap values stored in core registers
        remap_frame_layout(self.asm, non_float_locs, non_float_regs, r.ip)

    def load_result(self):
        resloc = self.resloc
        if self.restype == 'S':
            self.mc.VMOV_sc(resloc.value, r.s0.value)
        # ensure the result is wellformed and stored in the correct location
        if resloc is not None and resloc.is_core_reg():
            self._ensure_result_bit_extension(resloc,
                                                  self.ressize, self.ressign)

    def get_result_locs(self):
        if self.resloc is None:
            return [], []
        if self.resloc.is_vfp_reg():
            return [], [r.d0]
        assert self.resloc.is_core_reg()
        return [r.r0], []


def get_callbuilder(cpu, assembler, fnloc, arglocs,
                 resloc=r.r0, restype=INT, ressize=WORD, ressigned=True):
    if cpu.cpuinfo.hf_abi:
        return HardFloatCallBuilder(assembler, fnloc, arglocs, resloc,
                                        restype, ressize, ressigned)
    else:
        return SoftFloatCallBuilder(assembler, fnloc, arglocs, resloc,
                                        restype, ressize, ressigned)
