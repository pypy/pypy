from rpython.rlib.clibffi import FFI_DEFAULT_ABI
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.history import INT, FLOAT
from rpython.jit.backend.x86.arch import (WORD, IS_X86_64, IS_X86_32,
                                          PASS_ON_MY_FRAME)
from rpython.jit.backend.x86.regloc import (eax, ecx, edx, ebx, esp, ebp, esi,
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, r8, r9, r10, r11, edi,
    r12, r13, r14, r15, X86_64_SCRATCH_REG, X86_64_XMM_SCRATCH_REG,
    RegLoc, RawEspLoc, FrameLoc)
from rpython.jit.backend.x86.jump import remap_frame_layout


# darwin requires the stack to be 16 bytes aligned on calls.
# Same for gcc 4.5.0, better safe than sorry
CALL_ALIGN = 16 // WORD

def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)



class AbstractCallBuilder(object):

    # max number of words we have room in esp; if we need more for
    # arguments, we need to decrease esp temporarily
    stack_max = PASS_ON_MY_FRAME

    # this can be set to guide more complex calls: gives the detailed
    # type of the arguments
    argtypes = None
    restype = INT
    ressize = WORD
    ressign = False

    # this is the calling convention (can be FFI_STDCALL on Windows)
    callconv = FFI_DEFAULT_ABI

    # is it for the main CALL of a call_release_gil?
    is_call_release_gil = False


    def __init__(self, assembler, fnloc, arglocs, resloc=eax):
        self.asm = assembler
        self.mc = assembler.mc
        self.fnloc = fnloc
        self.arglocs = arglocs
        self.resloc = resloc
        self.current_esp = 0

    def emit(self):
        """Emit a regular call; not for CALL_RELEASE_GIL."""
        self.prepare_arguments()
        self.push_gcmap()
        self.emit_raw_call()
        self.pop_gcmap()
        self.load_result()
        self.restore_esp()

    def emit_raw_call(self):
        self.mc.CALL(self.fnloc)
        if self.callconv != FFI_DEFAULT_ABI:
            self.current_esp += self._fix_stdcall(self.callconv)

    def restore_esp(self):
        if self.current_esp != 0:
            self.mc.SUB_ri(esp.value, self.current_esp)
            self.current_esp = 0

    def load_result(self):
        """Overridden in CallBuilder32 and CallBuilder64"""
        if self.ressize == 0:
            return      # void result
        # use the code in load_from_mem to do the zero- or sign-extension
        if self.restype == FLOAT:
            srcloc = xmm0
        elif self.ressize == 1:
            srcloc = eax.lowest8bits()
        else:
            srcloc = eax
        if self.ressize >= WORD and self.resloc is srcloc:
            return      # no need for any move
        self.asm.load_from_mem(self.resloc, srcloc,
                               imm(self.ressize), imm(self.ressign))

    def push_gcmap(self):
        # we push *now* the gcmap, describing the status of GC registers
        # after the rearrangements done just above, ignoring the return
        # value eax, if necessary
        assert not self.is_call_release_gil
        self.change_extra_stack_depth = (self.current_esp != 0)
        if self.change_extra_stack_depth:
            self.asm.set_extra_stack_depth(self.mc, -self.current_esp)
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([eax], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap, store=True)

    def pop_gcmap(self):
        assert not self.is_call_release_gil
        self.asm._reload_frame_if_necessary(self.mc)
        if self.change_extra_stack_depth:
            self.asm.set_extra_stack_depth(self.mc, 0)
        self.asm.pop_gcmap(self.mc)


class CallBuilder32(AbstractCallBuilder):

    def prepare_arguments(self):
        arglocs = self.arglocs
        stack_depth = 0
        n = len(arglocs)
        for i in range(n):
            loc = arglocs[i]
            stack_depth += loc.get_width() // WORD
        if stack_depth > self.stack_max:
            align = align_stack_words(stack_depth - self.stack_max)
            self.current_esp -= align * WORD
            self.mc.SUB_ri(esp.value, align * WORD)
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
                else:
                    if self.fnloc is eax:
                        tmp = ecx
                    else:
                        tmp = eax
                    self.mc.MOV(tmp, loc)
                    self.mc.MOV_sr(p, tmp.value)
            p += loc.get_width()
        self.total_stack_used_by_arguments = p


    def _fix_stdcall(self, callconv):
        from rpython.rlib.clibffi import FFI_STDCALL
        assert callconv == FFI_STDCALL
        return self.total_stack_used_by_arguments

    def load_result(self):
        resloc = self.resloc
        if isinstance(resloc, FrameLoc) and resloc.type == FLOAT:
            # a float or a long long return
            if self.restype == 'L':
                self.mc.MOV_br(resloc.value, eax.value)      # long long
                self.mc.MOV_br(resloc.value + 4, edx.value)
                # XXX should ideally not move the result on the stack,
                #     but it's a mess to load eax/edx into a xmm register
                #     and this way is simpler also because the result loc
                #     can just be always a stack location
            else:
                self.mc.FSTPL_b(resloc.value)   # float return
        elif self.restype == 'S':
            # singlefloat return: must convert ST(0) to a 32-bit singlefloat
            # and load it into self.resloc.  mess mess mess
            self.mc.SUB_ri(esp.value, 4)
            self.mc.FSTPS_s(0)
            self.mc.POP(self.resloc)
        else:
            AbstractCallBuilder.load_result(self)


class CallBuilder64(AbstractCallBuilder):

    # In reverse order for use with pop()
    unused_gpr = [r9, r8, ecx, edx, esi, edi]
    unused_xmm = [xmm7, xmm6, xmm5, xmm4, xmm3, xmm2, xmm1, xmm0]

    def prepare_arguments(self):
        src_locs = []
        dst_locs = []
        xmm_src_locs = []
        xmm_dst_locs = []
        singlefloats = None

        arglocs = self.arglocs
        argtypes = self.argtypes
        unused_gpr = self.unused_gpr[:]
        unused_xmm = self.unused_xmm[:]

        on_stack = 0
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if loc.is_float():
                xmm_src_locs.append(loc)
                if len(unused_xmm) > 0:
                    xmm_dst_locs.append(unused_xmm.pop())
                else:
                    xmm_dst_locs.append(RawEspLoc(on_stack * WORD, FLOAT))
                    on_stack += 1
            elif argtypes is not None and argtypes[i] == 'S':
                # Singlefloat argument
                if singlefloats is None:
                    singlefloats = []
                if len(unused_xmm) > 0:
                    singlefloats.append((loc, unused_xmm.pop()))
                else:
                    singlefloats.append((loc, RawEspLoc(on_stack * WORD, INT)))
                    on_stack += 1
            else:
                src_locs.append(loc)
                if len(unused_gpr) > 0:
                    dst_locs.append(unused_gpr.pop())
                else:
                    dst_locs.append(RawEspLoc(on_stack * WORD, INT))
                    on_stack += 1

        if not we_are_translated():  # assert that we got the right stack depth
            floats = 0
            for i in range(len(arglocs)):
                arg = arglocs[i]
                if arg.is_float() or argtypes and argtypes[i] == 'S':
                    floats += 1
            all_args = len(arglocs)
            stack_depth = (max(all_args - floats - 6, 0) +
                           max(floats - 8, 0))
            assert stack_depth == on_stack

        align = 0
        if on_stack > self.stack_max:
            align = align_stack_words(on_stack - self.stack_max)
            self.current_esp -= align * WORD
            self.mc.SUB_ri(esp.value, align * WORD)

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
        # If x is a register and is in dst_locs, then oups, it needs to
        # be moved away:
        if self.fnloc in dst_locs:
            src_locs.append(self.fnloc)
            dst_locs.append(r10)
            self.fnloc = r10
        remap_frame_layout(self.asm, src_locs, dst_locs, X86_64_SCRATCH_REG)


    def _fix_stdcall(self, callconv):
        assert 0     # should not occur on 64-bit

    def load_result(self):
        if self.restype == 'S':
            # singlefloat return: use MOVD to load the target register
            # with the lower 32 bits of XMM0
            resloc = self.resloc
            assert isinstance(resloc, RegLoc)
            self.mc.MOVD_rx(resloc.value, xmm0.value)
        else:
            AbstractCallBuilder.load_result(self)


if IS_X86_32:
    CallBuilder = CallBuilder32
if IS_X86_64:
    CallBuilder = CallBuilder64
