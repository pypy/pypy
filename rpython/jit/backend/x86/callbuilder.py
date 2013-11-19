from rpython.rlib.clibffi import FFI_DEFAULT_ABI
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.history import INT, FLOAT
from rpython.jit.backend.x86.arch import (WORD, IS_X86_64, IS_X86_32,
                                          PASS_ON_MY_FRAME)
from rpython.jit.backend.x86.regloc import (eax, ecx, edx, ebx, esp, ebp, esi,
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, r8, r9, r10, r11, edi,
    r12, r13, r14, r15, X86_64_SCRATCH_REG, X86_64_XMM_SCRATCH_REG,
    RegLoc, RawEspLoc, RawEbpLoc, imm, ImmedLoc)
from rpython.jit.backend.x86.jump import remap_frame_layout
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder


# darwin requires the stack to be 16 bytes aligned on calls.
# Same for gcc 4.5.0, better safe than sorry
CALL_ALIGN = 16 // WORD

def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)


class CallBuilderX86(AbstractCallBuilder):

    # max number of words we have room in esp; if we need more for
    # arguments, we need to decrease esp temporarily
    stack_max = PASS_ON_MY_FRAME

    # set by save_result_value()
    tmpresloc = None

    def __init__(self, assembler, fnloc, arglocs,
                 resloc=eax, restype=INT, ressize=WORD):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype, ressize)
        # Avoid tons of issues with a non-immediate fnloc by sticking it
        # as an extra argument if needed
        self.fnloc_is_immediate = isinstance(fnloc, ImmedLoc)
        if not self.fnloc_is_immediate:
            self.fnloc = None
            self.arglocs = arglocs + [fnloc]
        self.current_esp = 0     # 0 or (usually) negative, counted in bytes

    def select_call_release_gil_mode(self):
        """Overridden in CallBuilder64"""
        AbstractCallBuilder.select_call_release_gil_mode(self)
        if self.asm._is_asmgcc():
            from rpython.memory.gctransform import asmgcroot
            self.stack_max = PASS_ON_MY_FRAME - asmgcroot.JIT_USE_WORDS
            assert self.stack_max >= 3

    def emit_raw_call(self):
        self.mc.CALL(self.fnloc)
        if self.callconv != FFI_DEFAULT_ABI:
            self.current_esp += self._fix_stdcall(self.callconv)

    def subtract_esp_aligned(self, count):
        if count > 0:
            align = align_stack_words(count)
            self.current_esp -= align * WORD
            self.mc.SUB_ri(esp.value, align * WORD)

    def restore_stack_pointer(self, target_esp=0):
        if self.current_esp != target_esp:
            self.mc.ADD_ri(esp.value, target_esp - self.current_esp)
            self.current_esp = target_esp

    def load_result(self):
        """Overridden in CallBuilder32 and CallBuilder64"""
        if self.ressize == 0:
            return      # void result
        # use the code in load_from_mem to do the zero- or sign-extension
        srcloc = self.tmpresloc
        if srcloc is None:
            if self.restype == FLOAT:
                srcloc = xmm0
            else:
                srcloc = eax
        if self.ressize >= WORD and self.resloc is srcloc:
            return      # no need for any MOV
        if self.ressize == 1 and isinstance(srcloc, RegLoc):
            srcloc = srcloc.lowest8bits()
        self.asm.load_from_mem(self.resloc, srcloc,
                               imm(self.ressize), imm(self.ressign))

    def push_gcmap(self):
        # we push *now* the gcmap, describing the status of GC registers
        # after the rearrangements done just before, ignoring the return
        # value eax, if necessary
        assert not self.is_call_release_gil
        self.change_extra_stack_depth = (self.current_esp != 0)
        if self.change_extra_stack_depth:
            self.asm.set_extra_stack_depth(self.mc, -self.current_esp)
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([eax], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap, store=True)

    def pop_gcmap(self):
        self.asm._reload_frame_if_necessary(self.mc)
        if self.change_extra_stack_depth:
            self.asm.set_extra_stack_depth(self.mc, 0)
        self.asm.pop_gcmap(self.mc)

    def call_releasegil_addr_and_move_real_arguments(self):
        initial_esp = self.current_esp
        self.save_register_arguments()
        #
        if not self.asm._is_asmgcc():
            # the helper takes no argument
            self.change_extra_stack_depth = False
        else:
            from rpython.memory.gctransform import asmgcroot
            # build a 'css' structure on the stack: 2 words for the linkage,
            # and 5/7 words as described for asmgcroot.ASM_FRAMEDATA, for a
            # total size of JIT_USE_WORDS.  This structure is found at
            # [ESP+css].
            css = -self.current_esp + (
                WORD * (PASS_ON_MY_FRAME - asmgcroot.JIT_USE_WORDS))
            assert css >= 2 * WORD
            # Save ebp
            index_of_ebp = css + WORD * (2+asmgcroot.INDEX_OF_EBP)
            self.mc.MOV_sr(index_of_ebp, ebp.value)  # MOV [css.ebp], EBP
            # Save the "return address": we pretend that it's css
            if IS_X86_32:
                reg = eax
            elif IS_X86_64:
                reg = edi
            self.mc.LEA_rs(reg.value, css)           # LEA reg, [css]
            frame_ptr = css + WORD * (2+asmgcroot.FRAME_PTR)
            self.mc.MOV_sr(frame_ptr, reg.value)     # MOV [css.frame], reg
            # Set up jf_extra_stack_depth to pretend that the return address
            # was at css, and so our stack frame is supposedly shorter by
            # (PASS_ON_MY_FRAME-JIT_USE_WORDS+1) words
            delta = PASS_ON_MY_FRAME - asmgcroot.JIT_USE_WORDS + 1
            self.change_extra_stack_depth = True
            self.asm.set_extra_stack_depth(self.mc, -delta * WORD)
            # Call the closestack() function (also releasing the GIL)
            # with 'reg' as argument
            if IS_X86_32:
                self.subtract_esp_aligned(1)
                self.mc.MOV_sr(0, reg.value)
            #else:
            #   on x86_64, reg is edi so that it is already correct
        #
        self.mc.CALL(imm(self.asm.releasegil_addr))
        #
        if not we_are_translated():        # for testing: we should not access
            self.mc.ADD(ebp, imm(1))       # ebp any more
        #
        self.restore_register_arguments()
        self.restore_stack_pointer(initial_esp)

    def save_register_arguments(self):
        """Overridden in CallBuilder64"""

    def restore_register_arguments(self):
        """Overridden in CallBuilder64"""

    def move_real_result_and_call_reacqgil_addr(self):
        # save the result we just got (in eax/eax+edx/st(0)/xmm0)
        self.save_result_value()
        # call the reopenstack() function (also reacquiring the GIL)
        if not self.asm._is_asmgcc():
            css = 0     # the helper takes no argument
        else:
            from rpython.memory.gctransform import asmgcroot
            css = WORD * (PASS_ON_MY_FRAME - asmgcroot.JIT_USE_WORDS)
            if IS_X86_32:
                reg = eax
            elif IS_X86_64:
                reg = edi
            self.mc.LEA_rs(reg.value, css)
            if IS_X86_32:
                self.mc.MOV_sr(0, reg.value)
        #
        self.mc.CALL(imm(self.asm.reacqgil_addr))
        #
        if not we_are_translated():        # for testing: now we can accesss
            self.mc.SUB(ebp, imm(1))       # ebp again
        #
        # Now that we required the GIL, we can reload a possibly modified ebp
        if self.asm._is_asmgcc():
            # special-case: reload ebp from the css
            from rpython.memory.gctransform import asmgcroot
            index_of_ebp = css + WORD * (2+asmgcroot.INDEX_OF_EBP)
            self.mc.MOV_rs(ebp.value, index_of_ebp)  # MOV EBP, [css.ebp]
        #else:
        #   for shadowstack, done for us by _reload_frame_if_necessary()

    def save_result_value(self):
        """Overridden in CallBuilder32 and CallBuilder64"""
        raise NotImplementedError


class CallBuilder32(CallBuilderX86):

    def prepare_arguments(self):
        arglocs = self.arglocs
        stack_depth = 0
        n = len(arglocs)
        for i in range(n):
            loc = arglocs[i]
            stack_depth += loc.get_width() // WORD
        self.subtract_esp_aligned(stack_depth - self.stack_max)
        #
        p = 0
        for i in range(n):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                if loc.is_xmm:
                    self.mc.MOVSD_sx(p, loc.value)
                else:
                    self.mc.MOV_sr(p, loc.value)
            p += loc.get_width()
        p = 0
        for i in range(n):
            loc = arglocs[i]
            if not isinstance(loc, RegLoc):
                if loc.get_width() == 8:
                    self.mc.MOVSD(xmm0, loc)
                    self.mc.MOVSD_sx(p, xmm0.value)
                elif isinstance(loc, ImmedLoc):
                    self.mc.MOV_si(p, loc.value)
                else:
                    self.mc.MOV(eax, loc)
                    self.mc.MOV_sr(p, eax.value)
            p += loc.get_width()
        self.total_stack_used_by_arguments = p
        #
        if not self.fnloc_is_immediate:    # the last "argument" pushed above
            self.fnloc = RawEspLoc(p - WORD, INT)


    def _fix_stdcall(self, callconv):
        from rpython.rlib.clibffi import FFI_STDCALL
        assert callconv == FFI_STDCALL
        return self.total_stack_used_by_arguments

    def load_result(self):
        resloc = self.resloc
        if resloc is not None and resloc.is_float():
            # a float or a long long return
            if self.tmpresloc is None:
                if self.restype == 'L':     # long long
                    # move eax/edx -> xmm0
                    self.mc.MOVD_xr(resloc.value^1, edx.value)
                    self.mc.MOVD_xr(resloc.value,   eax.value)
                    self.mc.PUNPCKLDQ_xx(resloc.value, resloc.value^1)
                else:
                    # float: we have to go via the stack
                    self.mc.FSTPL_s(0)
                    self.mc.MOVSD_xs(resloc.value, 0)
            else:
                self.mc.MOVSD(resloc, self.tmpresloc)
            #
        elif self.restype == 'S':
            # singlefloat return: must convert ST(0) to a 32-bit singlefloat
            # and load it into self.resloc.  mess mess mess
            if self.tmpresloc is None:
                self.mc.FSTPS_s(0)
                self.mc.MOV_rs(resloc.value, 0)
            else:
                self.mc.MOV(resloc, self.tmpresloc)
        else:
            CallBuilderX86.load_result(self)

    def save_result_value(self):
        # Temporarily save the result value into [ESP+4].  We use "+4"
        # in order to leave the word at [ESP+0] free, in case it's needed
        if self.ressize == 0:      # void return
            return
        if self.resloc.is_float():
            # a float or a long long return
            self.tmpresloc = RawEspLoc(4, FLOAT)
            if self.restype == 'L':
                self.mc.MOV_sr(4, eax.value)      # long long
                self.mc.MOV_sr(8, edx.value)
            else:
                self.mc.FSTPL_s(4)                # float return
        else:
            self.tmpresloc = RawEspLoc(4, INT)
            if self.restype == 'S':
                self.mc.FSTPS_s(4)
            else:
                assert self.restype == INT
                assert self.ressize <= WORD
                self.mc.MOV_sr(4, eax.value)


class CallBuilder64(CallBuilderX86):

    ARGUMENTS_GPR = [edi, esi, edx, ecx, r8, r9]
    ARGUMENTS_XMM = [xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7]
    DONT_MOVE_GPR = []
    _ALL_CALLEE_SAVE_GPR = [ebx, r12, r13, r14, r15]

    next_arg_gpr = 0
    next_arg_xmm = 0

    def _unused_gpr(self, hint):
        i = self.next_arg_gpr
        self.next_arg_gpr = i + 1
        try:
            res = self.ARGUMENTS_GPR[i]
        except IndexError:
            return None
        if hint in self.DONT_MOVE_GPR:
            for j in range(i):
                if hint is self.ARGUMENTS_GPR[j]:
                    break
            else:
                self.ARGUMENTS_GPR[i] = hint
                res = hint
        return res

    def _unused_xmm(self):
        i = self.next_arg_xmm
        self.next_arg_xmm = i + 1
        try:
            return self.ARGUMENTS_XMM[i]
        except IndexError:
            return None

    def _permute_to_prefer_unused_registers(self, lst):
        # permute 'lst' so that it starts with registers that are not
        # in 'self.already_used', and ends with registers that are.
        N = len(lst)
        i = 0
        while i < N:
            reg = lst[i]
            if reg in self.already_used:
                # move this reg to the end, and decrement N
                N -= 1
                assert N >= i
                lst[N], lst[i] = lst[i], lst[N]
            else:
                i += 1

    def select_call_release_gil_mode(self):
        CallBuilderX86.select_call_release_gil_mode(self)
        # We have to copy the arguments around a bit more in this mode,
        # but on the other hand we don't need prepare_arguments() moving
        # them in precisely the final registers.  Here we look around for
        # unused registers that may be more likely usable.
        from rpython.jit.backend.x86.regalloc import X86_64_RegisterManager
        from rpython.jit.backend.x86.regalloc import X86_64_XMMRegisterManager
        self.already_used = {}
        for loc in self.arglocs:
            self.already_used[loc] = None
        #
        lst = X86_64_RegisterManager.save_around_call_regs[:]
        self._permute_to_prefer_unused_registers(lst)
        # <optimization>
        extra = []
        for reg in self.asm._regalloc.rm.free_regs:
            if (reg not in self.already_used and
                    reg in self._ALL_CALLEE_SAVE_GPR):
                extra.append(reg)
        self.free_callee_save_gprs = extra
        lst = extra + lst
        # </optimization>
        self.ARGUMENTS_GPR = lst[:len(self.ARGUMENTS_GPR)]
        self.DONT_MOVE_GPR = self._ALL_CALLEE_SAVE_GPR
        #
        lst = X86_64_XMMRegisterManager.save_around_call_regs[:]
        self._permute_to_prefer_unused_registers(lst)
        self.ARGUMENTS_XMM = lst[:len(self.ARGUMENTS_XMM)]

    def prepare_arguments(self):
        src_locs = []
        dst_locs = []
        xmm_src_locs = []
        xmm_dst_locs = []
        singlefloats = None

        arglocs = self.arglocs
        argtypes = self.argtypes

        on_stack = 0
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if loc.is_float():
                tgt = self._unused_xmm()
                if tgt is None:
                    tgt = RawEspLoc(on_stack * WORD, FLOAT)
                    on_stack += 1
                xmm_src_locs.append(loc)
                xmm_dst_locs.append(tgt)
            elif i < len(argtypes) and argtypes[i] == 'S':
                # Singlefloat argument
                if singlefloats is None:
                    singlefloats = []
                tgt = self._unused_xmm()
                if tgt is None:
                    tgt = RawEspLoc(on_stack * WORD, INT)
                    on_stack += 1
                singlefloats.append((loc, tgt))
            else:
                tgt = self._unused_gpr(hint=loc)
                if tgt is None:
                    tgt = RawEspLoc(on_stack * WORD, INT)
                    on_stack += 1
                src_locs.append(loc)
                dst_locs.append(tgt)

        if not self.fnloc_is_immediate:
            self.fnloc = dst_locs[-1]     # the last "argument" prepared above

        if not we_are_translated():  # assert that we got the right stack depth
            floats = 0
            for i in range(len(arglocs)):
                arg = arglocs[i]
                if arg.is_float() or (i < len(argtypes) and argtypes[i]=='S'):
                    floats += 1
            all_args = len(arglocs)
            stack_depth = (max(all_args - floats - len(self.ARGUMENTS_GPR), 0)
                           + max(floats - len(self.ARGUMENTS_XMM), 0))
            assert stack_depth == on_stack

        self.subtract_esp_aligned(on_stack - self.stack_max)

        # Handle register arguments: first remap the xmm arguments
        remap_frame_layout(self.asm, xmm_src_locs, xmm_dst_locs,
                           X86_64_XMM_SCRATCH_REG)
        # Load the singlefloat arguments from main regs or stack to xmm regs
        if singlefloats is not None:
            for src, dst in singlefloats:
                if isinstance(dst, RawEspLoc):
                    # XXX too much special logic
                    if isinstance(src, RawEbpLoc):
                        self.mc.MOV32(X86_64_SCRATCH_REG, src)
                        self.mc.MOV32(dst, X86_64_SCRATCH_REG)
                    else:
                        self.mc.MOV32(dst, src)
                    continue
                if isinstance(src, ImmedLoc):
                    self.mc.MOV(X86_64_SCRATCH_REG, src)
                    src = X86_64_SCRATCH_REG
                self.mc.MOVD(dst, src)
        # Finally remap the arguments in the main regs
        remap_frame_layout(self.asm, src_locs, dst_locs, X86_64_SCRATCH_REG)


    def _fix_stdcall(self, callconv):
        assert 0     # should not occur on 64-bit

    def load_result(self):
        if self.restype == 'S' and self.tmpresloc is None:
            # singlefloat return: use MOVD to load the target register
            # from the lower 32 bits of XMM0
            self.mc.MOVD(self.resloc, xmm0)
        else:
            CallBuilderX86.load_result(self)

    def save_result_value(self):
        # Temporarily save the result value into [ESP].
        if self.ressize == 0:      # void return
            return
        #
        if self.restype == FLOAT:    # and not 'S'
            self.mc.MOVSD_sx(0, xmm0.value)
            self.tmpresloc = RawEspLoc(0, FLOAT)
            return
        #
        if len(self.free_callee_save_gprs) == 0:
            self.tmpresloc = RawEspLoc(0, INT)
        else:
            self.tmpresloc = self.free_callee_save_gprs[0]
        #
        if self.restype == 'S':
            # singlefloat return: use MOVD to store the lower 32 bits
            # of XMM0 into the tmpresloc (register or [ESP])
            self.mc.MOVD(self.tmpresloc, xmm0)
        else:
            assert self.restype == INT
            self.mc.MOV(self.tmpresloc, eax)

    def save_register_arguments(self):
        # Save the argument registers, which are given by self.ARGUMENTS_xxx.
        n_gpr = min(self.next_arg_gpr, len(self.ARGUMENTS_GPR))
        n_xmm = min(self.next_arg_xmm, len(self.ARGUMENTS_XMM))
        n_saved_regs = n_gpr + n_xmm
        for i in range(n_gpr):
            if self.ARGUMENTS_GPR[i] in self._ALL_CALLEE_SAVE_GPR:
                n_saved_regs -= 1     # don't need to save it
        self.subtract_esp_aligned(n_saved_regs)
        #
        n = 0
        for i in range(n_gpr):
            if self.ARGUMENTS_GPR[i] not in self._ALL_CALLEE_SAVE_GPR:
                self.mc.MOV_sr(n * WORD, self.ARGUMENTS_GPR[i].value)
                n += 1
        for i in range(n_xmm):
            self.mc.MOVSD_sx(n * WORD, self.ARGUMENTS_XMM[i].value)
            n += 1
        assert n == n_saved_regs
        self.n_saved_regs = n_saved_regs

    def restore_register_arguments(self):
        # Restore the saved values into the *real* registers used for calls
        # --- which are not self.ARGUMENTS_xxx!
        n_gpr = min(self.next_arg_gpr, len(self.ARGUMENTS_GPR))
        n_xmm = min(self.next_arg_xmm, len(self.ARGUMENTS_XMM))
        #
        n = 0
        for i in range(n_gpr):
            tgtvalue = CallBuilder64.ARGUMENTS_GPR[i].value
            if self.ARGUMENTS_GPR[i] not in self._ALL_CALLEE_SAVE_GPR:
                self.mc.MOV_rs(tgtvalue, n * WORD)
                n += 1
            else:
                self.mc.MOV_rr(tgtvalue, self.ARGUMENTS_GPR[i].value)
        for i in range(n_xmm):
            self.mc.MOVSD_xs(CallBuilder64.ARGUMENTS_XMM[i].value, n * WORD)
            n += 1
        assert n == self.n_saved_regs
        #
        if isinstance(self.fnloc, RegLoc):    # fix this register
            self.fnloc = CallBuilder64.ARGUMENTS_GPR[n_gpr - 1]


if IS_X86_32:
    CallBuilder = CallBuilder32
if IS_X86_64:
    CallBuilder = CallBuilder64
