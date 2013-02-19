
import sys, os
from rpython.jit.backend.llsupport import symbolic, jitframe
from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.metainterp.history import Const, Box, BoxInt, ConstInt
from rpython.jit.metainterp.history import AbstractFailDescr, INT, REF, FLOAT
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rlib.jit import AsmInfo
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.x86.regalloc import (RegAlloc, get_ebp_ofs, _get_scale,
    gpr_reg_mgr_cls, xmm_reg_mgr_cls, _valid_addressing_size)
from rpython.jit.backend.x86.arch import (FRAME_FIXED_SIZE, WORD, IS_X86_64,
                                       JITFRAME_FIXED_SIZE, IS_X86_32,
                                       PASS_ON_MY_FRAME)
from rpython.jit.backend.x86.regloc import (eax, ecx, edx, ebx, esp, ebp, esi,
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, r8, r9, r10, r11, edi,
    r12, r13, r14, r15, X86_64_SCRATCH_REG, X86_64_XMM_SCRATCH_REG,
    RegLoc, StackLoc, ConstFloatLoc, ImmedLoc, AddressLoc, imm,
    imm0, imm1, FloatImmedLoc, RawStackLoc, RawEspLoc)
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.jit.backend.x86 import rx86, codebuf
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.backend.x86 import support
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.rlib import rgc
from rpython.rlib.clibffi import FFI_DEFAULT_ABI
from rpython.jit.backend.x86.jump import remap_frame_layout
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter import longlong
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.objectmodel import compute_unique_id

# darwin requires the stack to be 16 bytes aligned on calls. Same for gcc 4.5.0,
# better safe than sorry
CALL_ALIGN = 16 // WORD

def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)

DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER', ('i', lltype.Signed),
                              ('type', lltype.Char), # 'b'ridge, 'l'abel or
                                                     # 'e'ntry point
                              ('number', lltype.Signed))

class Assembler386(BaseAssembler):
    _regalloc = None
    _output_loop_log = None
    _second_tmp_reg = ecx

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.verbose = False
        self.loop_run_counters = []
        self.float_const_neg_addr = 0
        self.float_const_abs_addr = 0
        self.malloc_slowpath = 0
        self.wb_slowpath = [0, 0, 0, 0, 0]
        self.setup_failure_recovery()
        self._debug = False
        self.debug_counter_descr = cpu.fielddescrof(DEBUG_COUNTER, 'i')
        self.datablockwrapper = None
        self.stack_check_slowpath = 0
        self.propagate_exception_path = 0
        self.gcrootmap_retaddr_forced = 0
        self.teardown()

    def set_debug(self, v):
        r = self._debug
        self._debug = v
        return r

    def setup_once(self):
        BaseAssembler.setup_once(self)
        if self.cpu.supports_floats:
            support.ensure_sse2_floats()
            self._build_float_constants()

    def setup(self, looptoken):
        assert self.memcpy_addr != 0, "setup_once() not called?"
        self.current_clt = looptoken.compiled_loop_token
        self.pending_guard_tokens = []
        if WORD == 8:
            self.pending_memoryerror_trampoline_from = []
            self.error_trampoline_64 = 0
        self.mc = codebuf.MachineCodeBlockWrapper()
        #assert self.datablockwrapper is None --- but obscure case
        # possible, e.g. getting MemoryError and continuing
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.target_tokens_currently_compiling = {}

    def teardown(self):
        self.pending_guard_tokens = None
        if WORD == 8:
            self.pending_memoryerror_trampoline_from = None
        self.mc = None
        self.current_clt = None

    def finish_once(self):
        if self._debug:
            debug_start('jit-backend-counts')
            for i in range(len(self.loop_run_counters)):
                struct = self.loop_run_counters[i]
                if struct.type == 'l':
                    prefix = 'TargetToken(%d)' % struct.number
                elif struct.type == 'b':
                    prefix = 'bridge ' + str(struct.number)
                else:
                    prefix = 'entry ' + str(struct.number)
                debug_print(prefix + ':' + str(struct.i))
            debug_stop('jit-backend-counts')

    def _build_float_constants(self):
        datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr, [])
        float_constants = datablockwrapper.malloc_aligned(32, alignment=16)
        datablockwrapper.done()
        addr = rffi.cast(rffi.CArrayPtr(lltype.Char), float_constants)
        qword_padding = '\x00\x00\x00\x00\x00\x00\x00\x00'
        # 0x8000000000000000
        neg_const = '\x00\x00\x00\x00\x00\x00\x00\x80'
        # 0x7FFFFFFFFFFFFFFF
        abs_const = '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F'
        data = neg_const + qword_padding + abs_const + qword_padding
        for i in range(len(data)):
            addr[i] = data[i]
        self.float_const_neg_addr = float_constants
        self.float_const_abs_addr = float_constants + 16

    def _build_stack_check_failure(self):
        mc = codebuf.MachineCodeBlockWrapper()
        self._push_all_regs_to_frame(mc, [], self.cpu.supports_floats)
        # this is the gcmap stored by push_gcmap(mov=True) in _check_stack_frame
        mc.MOV_rs(ecx.value, WORD)
        gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.MOV_br(gcmap_ofs, ecx.value)

        if IS_X86_64:
            mc.MOV_rs(esi.value, WORD*2)
            # push first arg
            mc.MOV_rr(edi.value, ebp.value)
            align = align_stack_words(1)
            mc.SUB_ri(esp.value, (align - 1) * WORD)
            exc0, exc1 = ebx, r12 # callee saved regs for storing exc
        else:
            align = align_stack_words(3)
            mc.MOV_rs(eax.value, WORD * 2)
            mc.SUB_ri(esp.value, (align - 1) * WORD)
            mc.MOV_sr(WORD, eax.value)
            mc.MOV_sr(0, ebp.value)
            exc0, exc1 = esi, edi # callee saved regs for storing exc
        # align

        self._store_and_reset_exception(mc, exc0, exc1)

        mc.CALL(imm(self.cpu.realloc_frame))
        self._restore_exception(mc, exc0, exc1)
        mc.ADD_ri(esp.value, (align - 1) * WORD)
        mc.MOV_rr(ebp.value, eax.value)


        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._load_shadowstack_top_in_ebx(mc, gcrootmap)
            mc.MOV_mr((ebx.value, -WORD), eax.value)

        mc.MOV_bi(gcmap_ofs, 0)
        self._pop_all_regs_from_frame(mc, [], self.cpu.supports_floats)
        mc.RET()
        self._stack_check_failure = mc.materialize(self.cpu.asmmemmgr, [])

    def _build_malloc_slowpath(self):
        """ While arriving on slowpath, we have a gcpattern on stack,
        nursery_head in eax and the size in edi - eax
        """
        mc = codebuf.MachineCodeBlockWrapper()
        self._push_all_regs_to_frame(mc, [eax, edi], self.cpu.supports_floats)
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        # store the gc pattern
        mc.MOV_rs(ecx.value, WORD)
        mc.MOV_br(ofs, ecx.value)
        addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
        # XXX investigate if we need to save callee-saved registers
        #     on the frame
        mc.SUB_rr(edi.value, eax.value)       # compute the size we want
        # the arg is already in edi
        mc.SUB_ri(esp.value, 16 - WORD)
        if IS_X86_32:
            mc.MOV_sr(0, edi.value)
            if hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
                mc.MOV_sr(WORD, ebp.value)
        elif hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
            # for tests only
            mc.MOV_rr(esi.value, ebp.value)
        mc.CALL(imm(addr))
        mc.ADD_ri(esp.value, 16 - WORD)
        mc.TEST_rr(eax.value, eax.value)
        mc.J_il(rx86.Conditions['Z'], 0xfffff) # patched later
        jz_location = mc.get_relative_pos()
        #
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        self._reload_frame_if_necessary(mc)
        self._pop_all_regs_from_frame(mc, [eax, edi], self.cpu.supports_floats)
        mc.MOV(edi, heap(nursery_free_adr))   # load this in EDI
        # clear the gc pattern
        mc.MOV_bi(ofs, 0)
        mc.RET()
        #
        # If the slowpath malloc failed, we raise a MemoryError that
        # always interrupts the current loop, as a "good enough"
        # approximation.  We have to adjust the esp a little, to point to
        # the correct "ret" arg
        offset = mc.get_relative_pos() - jz_location
        mc.overwrite32(jz_location-4, offset)
        mc.ADD_ri(esp.value, WORD)
        mc.JMP(imm(self.propagate_exception_path))
        #
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.malloc_slowpath = rawstart

    def _build_propagate_exception_path(self):
        if not self.cpu.propagate_exception_descr:
            return      # not supported (for tests, or non-translated)
        #
        self.mc = codebuf.MachineCodeBlockWrapper()
        #
        # read and reset the current exception

        self._store_and_reset_exception(self.mc, eax)
        ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
        self.mc.MOV_br(ofs, eax.value)
        propagate_exception_descr = rffi.cast(lltype.Signed,
                  cast_instance_to_gcref(self.cpu.propagate_exception_descr))
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.MOV_bi(ofs, propagate_exception_descr)
        self.mc.MOV_rr(eax.value, ebp.value)
        #
        self._call_footer()
        rawstart = self.mc.materialize(self.cpu.asmmemmgr, [])
        self.propagate_exception_path = rawstart
        self.mc = None

    def _build_stack_check_slowpath(self):
        _, _, slowpathaddr = self.cpu.insert_stack_check()
        if slowpathaddr == 0 or not self.cpu.propagate_exception_descr:
            return      # no stack check (for tests, or non-translated)
        #
        # make a "function" that is called immediately at the start of
        # an assembler function.  In particular, the stack looks like:
        #
        #    |  ...                |    <-- aligned to a multiple of 16
        #    |  retaddr of caller  |
        #    |  my own retaddr     |    <-- esp
        #    +---------------------+
        #
        mc = codebuf.MachineCodeBlockWrapper()
        #
        if IS_X86_64:
            # on the x86_64, we have to save all the registers that may
            # have been used to pass arguments. Note that we pass only
            # one argument, that is the frame
            mc.MOV_rr(edi.value, esp.value)
        #
        if IS_X86_32:
            mc.SUB_ri(esp.value, 2*WORD) # alignment
            mc.PUSH_r(esp.value)
        #
        # esp is now aligned to a multiple of 16 again
        mc.CALL(imm(slowpathaddr))
        #
        mc.MOV(eax, heap(self.cpu.pos_exception()))
        mc.TEST_rr(eax.value, eax.value)
        mc.J_il8(rx86.Conditions['NZ'], 0)
        jnz_location = mc.get_relative_pos()
        #
        if IS_X86_32:
            mc.ADD_ri(esp.value, 3*WORD)    # alignment
        #
        mc.RET()
        #
        # patch the JNZ above
        offset = mc.get_relative_pos() - jnz_location
        assert 0 < offset <= 127
        mc.overwrite(jnz_location-1, chr(offset))
        # adjust the esp to point back to the previous return
        mc.ADD_ri(esp.value, WORD)
        mc.JMP(imm(self.propagate_exception_path))
        #
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.stack_check_slowpath = rawstart

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        descr = self.cpu.gc_ll_descr.write_barrier_descr
        exc0, exc1 = None, None
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
        # all XMM registers.  It takes a single argument just pushed
        # on the stack even on X86_64.  It must restore stack alignment
        # accordingly.
        mc = codebuf.MachineCodeBlockWrapper()
        #
        if not for_frame:
            self._push_all_regs_to_frame(mc, [], withfloats, callee_only=True)
            if IS_X86_32:
                # we have 2 extra words on stack for retval and we pass 1 extra
                # arg, so we need to substract 2 words
                mc.SUB_ri(esp.value, 2 * WORD)
                mc.MOV_rs(eax.value, 3 * WORD) # 2 + 1
                mc.MOV_sr(0, eax.value)
            else:
                mc.MOV_rs(edi.value, WORD)
        else:
            # we're possibly called from the slowpath of malloc, so we have
            # one extra CALL on the stack, but one less PUSH,
            # save to store stuff 2 locations away on the stack.
            # we have to save all the things that can potentially
            # be returned from a call
            mc.SUB_ri(esp.value, 6 * WORD) # align and reserve some space
            mc.MOV_sr(WORD, eax.value) # save for later
            mc.MOVSD_sx(3 * WORD, xmm0.value)
            if IS_X86_32:
                mc.MOV_sr(4 * WORD, edx.value)
                mc.MOV_sr(0, ebp.value)
                exc0, exc1 = esi, edi
            else:
                mc.MOV_rr(edi.value, ebp.value)
                exc0, exc1 = ebx, r12
            self._store_and_reset_exception(mc, exc0, exc1)

        mc.CALL(imm(func))
        #
        if withcards:
            # A final TEST8 before the RET, for the caller.  Careful to
            # not follow this instruction with another one that changes
            # the status of the CPU flags!
            if IS_X86_32:
                mc.MOV_rs(eax.value, 3*WORD)
            else:
                mc.MOV_rs(eax.value, WORD)
            mc.TEST8(addr_add_const(eax, descr.jit_wb_if_flag_byteofs),
                     imm(-0x80))
        #

        if not for_frame:
            if IS_X86_32:
                # ADD touches CPU flags
                mc.LEA_rs(esp.value, 2 * WORD)
            self._pop_all_regs_from_frame(mc, [], withfloats, callee_only=True)
            mc.RET16_i(WORD)
        else:
            if IS_X86_32:
                mc.MOV_rs(edx.value, 4 * WORD)
            mc.MOVSD_xs(xmm0.value, 3 * WORD)
            mc.MOV_rs(eax.value, WORD) # restore
            self._restore_exception(mc, exc0, exc1)
            mc.LEA_rs(esp.value, 6 * WORD)
            mc.RET()

        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    @staticmethod
    @rgc.no_collect
    def _release_gil_asmgcc(css):
        # similar to trackgcroot.py:pypy_asm_stackwalk, first part
        from rpython.rtyper.memory.gctransform import asmgcroot
        new = rffi.cast(asmgcroot.ASM_FRAMEDATA_HEAD_PTR, css)
        next = asmgcroot.gcrootanchor.next
        new.next = next
        new.prev = asmgcroot.gcrootanchor
        asmgcroot.gcrootanchor.next = new
        next.prev = new
        # and now release the GIL
        before = rffi.aroundstate.before
        if before:
            before()

    @staticmethod
    @rgc.no_collect
    def _reacquire_gil_asmgcc(css):
        # first reacquire the GIL
        after = rffi.aroundstate.after
        if after:
            after()
        # similar to trackgcroot.py:pypy_asm_stackwalk, second part
        from rpython.rtyper.memory.gctransform import asmgcroot
        old = rffi.cast(asmgcroot.ASM_FRAMEDATA_HEAD_PTR, css)
        prev = old.prev
        next = old.next
        prev.next = next
        next.prev = prev

    @staticmethod
    @rgc.no_collect
    def _release_gil_shadowstack():
        before = rffi.aroundstate.before
        if before:
            before()

    @staticmethod
    @rgc.no_collect
    def _reacquire_gil_shadowstack():
        after = rffi.aroundstate.after
        if after:
            after()

    _NOARG_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))
    _CLOSESTACK_FUNC = lltype.Ptr(lltype.FuncType([rffi.LONGP],
                                                  lltype.Void))

    def _build_release_gil(self, gcrootmap):
        if gcrootmap.is_shadow_stack:
            releasegil_func = llhelper(self._NOARG_FUNC,
                                       self._release_gil_shadowstack)
            reacqgil_func = llhelper(self._NOARG_FUNC,
                                     self._reacquire_gil_shadowstack)
        else:
            releasegil_func = llhelper(self._CLOSESTACK_FUNC,
                                       self._release_gil_asmgcc)
            reacqgil_func = llhelper(self._CLOSESTACK_FUNC,
                                     self._reacquire_gil_asmgcc)
        self.releasegil_addr  = self.cpu.cast_ptr_to_int(releasegil_func)
        self.reacqgil_addr = self.cpu.cast_ptr_to_int(reacqgil_func)

    def assemble_loop(self, loopname, inputargs, operations, looptoken, log):
        '''adds the following attributes to looptoken:
               _ll_function_addr    (address of the generated func, as an int)
               _ll_loop_code       (debug: addr of the start of the ResOps)
               _x86_fullsize        (debug: full size including failure)
               _x86_debug_checksum
        '''
        # XXX this function is too longish and contains some code
        # duplication with assemble_bridge().  Also, we should think
        # about not storing on 'self' attributes that will live only
        # for the duration of compiling one loop or a one bridge.
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
        clt.frame_info.set_frame_depth(0, 0) # for now

        if log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        regalloc = RegAlloc(self, self.cpu.translate_support_code)
        #
        self._call_header_with_stack_check()
        operations = regalloc.prepare_loop(inputargs, operations, looptoken,
                                           clt.allgcrefs)
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
        looptoken._ll_loop_code = looppos + rawstart
        debug_start("jit-backend-addr")
        debug_print("Loop %d (%s) has address %x to %x (bootstrap %x)" % (
            looptoken.number, loopname,
            rawstart + looppos,
            rawstart + size_excluding_failure_stuff,
            rawstart))
        debug_stop("jit-backend-addr")
        self.patch_pending_failure_recoveries(rawstart)
        #
        ops_offset = self.mc.ops_offset
        if not we_are_translated():
            # used only by looptoken.dump() -- useful in tests
            looptoken._x86_rawstart = rawstart
            looptoken._x86_fullsize = full_size
            looptoken._x86_ops_offset = ops_offset
        looptoken._ll_function_addr = rawstart

        self.fixup_target_tokens(rawstart)
        self.teardown()
        # oprofile support
        if self.cpu.profile_agent is not None:
            name = "Loop # %s: %s" % (looptoken.number, loopname)
            self.cpu.profile_agent.native_code_written(name,
                                                       rawstart, full_size)
        return AsmInfo(ops_offset, rawstart + looppos,
                       size_excluding_failure_stuff - looppos)

    def assemble_bridge(self, faildescr, inputargs, operations,
                        original_loop_token, log):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(original_loop_token)
        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)
        regalloc = RegAlloc(self, self.cpu.translate_support_code)
        startpos = self.mc.get_relative_pos()
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)
        stack_check_patch_ofs, ofs2 = self._check_frame_depth(self.mc,
                                                       regalloc.get_gcmap())
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        codeendpos = self.mc.get_relative_pos()
        self.write_pending_failure_recoveries()
        fullsize = self.mc.get_relative_pos()
        #
        rawstart = self.materialize_loop(original_loop_token)
        debug_start("jit-backend-addr")
        debug_print("bridge out of Guard %x has address %x to %x" %
                    (descr_number, rawstart, rawstart + codeendpos))
        debug_stop("jit-backend-addr")
        self.patch_pending_failure_recoveries(rawstart)
        # patch the jump from original guard
        self.patch_jump_for_descr(faildescr, rawstart)
        ops_offset = self.mc.ops_offset
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        self._patch_stackadjust(stack_check_patch_ofs + rawstart, frame_depth)
        self._patch_stackadjust(ofs2 + rawstart, frame_depth)
        self.fixup_target_tokens(rawstart)
        self.update_frame_depth(frame_depth)
        self.teardown()
        # oprofile support
        if self.cpu.profile_agent is not None:
            name = "Bridge # %s" % (descr_number,)
            self.cpu.profile_agent.native_code_written(name,
                                                       rawstart, fullsize)
        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def write_pending_failure_recoveries(self):
        # for each pending guard, generate the code of the recovery stub
        # at the end of self.mc.
        for tok in self.pending_guard_tokens:
            tok.pos_recovery_stub = self.generate_quick_failure(tok)
        if WORD == 8 and len(self.pending_memoryerror_trampoline_from) > 0:
            self.error_trampoline_64 = self.generate_propagate_error_64()

    def patch_pending_failure_recoveries(self, rawstart):
        # after we wrote the assembler to raw memory, set up
        # tok.faildescr._x86_adr_jump_offset to contain the raw address of
        # the 4-byte target field in the JMP/Jcond instruction, and patch
        # the field in question to point (initially) to the recovery stub
        clt = self.current_clt
        for tok in self.pending_guard_tokens:
            addr = rawstart + tok.pos_jump_offset
            tok.faildescr._x86_adr_jump_offset = addr
            relative_target = tok.pos_recovery_stub - (tok.pos_jump_offset + 4)
            assert rx86.fits_in_32bits(relative_target)
            #
            if not tok.is_guard_not_invalidated:
                mc = codebuf.MachineCodeBlockWrapper()
                mc.writeimm32(relative_target)
                mc.copy_to_raw_memory(addr)
            else:
                # GUARD_NOT_INVALIDATED, record an entry in
                # clt.invalidate_positions of the form:
                #     (addr-in-the-code-of-the-not-yet-written-jump-target,
                #      relative-target-to-use)
                relpos = tok.pos_jump_offset
                clt.invalidate_positions.append((rawstart + relpos,
                                                 relative_target))
                # General idea: Although no code was generated by this
                # guard, the code might be patched with a "JMP rel32" to
                # the guard recovery code.  This recovery code is
                # already generated, and looks like the recovery code
                # for any guard, even if at first it has no jump to it.
                # So we may later write 5 bytes overriding the existing
                # instructions; this works because a CALL instruction
                # would also take at least 5 bytes.  If it could take
                # less, we would run into the issue that overwriting the
                # 5 bytes here might get a few nonsense bytes at the
                # return address of the following CALL.
        if WORD == 8:
            for pos_after_jz in self.pending_memoryerror_trampoline_from:
                assert self.error_trampoline_64 != 0     # only if non-empty
                mc = codebuf.MachineCodeBlockWrapper()
                mc.writeimm32(self.error_trampoline_64 - pos_after_jz)
                mc.copy_to_raw_memory(rawstart + pos_after_jz - 4)

    def update_frame_depth(self, frame_depth):
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.set_frame_depth(baseofs, frame_depth)

    def _check_frame_depth(self, mc, gcmap, expected_size=-1):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        There are other potential solutions
        to that, but this one does not sound too bad.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        if expected_size == -1:
            mc.CMP_bi(ofs, 0xffffff)
        else:
            mc.CMP_bi(ofs, expected_size)
        stack_check_cmp_ofs = mc.get_relative_pos() - 4
        mc.J_il8(rx86.Conditions['GE'], 0)
        jg_location = mc.get_relative_pos()
        if expected_size == -1:
            mc.MOV_si(WORD, 0xffffff)
        else:
            mc.MOV_si(WORD, expected_size)            
        ofs2 = mc.get_relative_pos() - 4
        self.push_gcmap(mc, gcmap, mov=True)
        mc.CALL(imm(self._stack_check_failure))
        # patch the JG above
        offset = mc.get_relative_pos() - jg_location
        assert 0 < offset <= 127
        mc.overwrite(jg_location-1, chr(offset))
        return stack_check_cmp_ofs, ofs2

    def _patch_stackadjust(self, adr, allocated_depth):
        mc = codebuf.MachineCodeBlockWrapper()
        mc.writeimm32(allocated_depth)
        mc.copy_to_raw_memory(adr)
    
    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        return self.mc.materialize(self.cpu.asmmemmgr, allblocks,
                                   self.cpu.gc_ll_descr.gcrootmap)

    def _register_counter(self, tp, number, token):
        # YYY very minor leak -- we need the counters to stay alive
        # forever, just because we want to report them at the end
        # of the process
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
 
    def patch_jump_for_descr(self, faildescr, adr_new_target):
        adr_jump_offset = faildescr._x86_adr_jump_offset
        assert adr_jump_offset != 0
        offset = adr_new_target - (adr_jump_offset + 4)
        # If the new target fits within a rel32 of the jump, just patch
        # that. Otherwise, leave the original rel32 to the recovery stub in
        # place, but clobber the recovery stub with a jump to the real
        # target.
        mc = codebuf.MachineCodeBlockWrapper()
        if rx86.fits_in_32bits(offset):
            mc.writeimm32(offset)
            mc.copy_to_raw_memory(adr_jump_offset)
        else:
            # "mov r11, addr; jmp r11" is up to 13 bytes, which fits in there
            # because we always write "mov r11, imm-as-8-bytes; call *r11" in
            # the first place.
            mc.MOV_ri(X86_64_SCRATCH_REG.value, adr_new_target)
            mc.JMP_r(X86_64_SCRATCH_REG.value)
            p = rffi.cast(rffi.INTP, adr_jump_offset)
            adr_target = adr_jump_offset + 4 + rffi.cast(lltype.Signed, p[0])
            mc.copy_to_raw_memory(adr_target)
        faildescr._x86_adr_jump_offset = 0    # means "patched"

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ll_loop_code += rawstart
        self.target_tokens_currently_compiling = None

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
            s = 0
            for op in operations:
                s += op.getopnum()
            looptoken._x86_debug_checksum = s

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

    def _assemble(self, regalloc, inputargs, operations):
        self._regalloc = regalloc
        regalloc.compute_hint_frame_locations(operations)
        regalloc.walk_operations(inputargs, operations)
        if we_are_translated() or self.cpu.dont_keepalive_stuff:
            self._regalloc = None   # else keep it around for debugging
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._x86_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

    def _call_header(self):
        self.mc.SUB_ri(esp.value, FRAME_FIXED_SIZE * WORD)
        self.mc.MOV_sr(PASS_ON_MY_FRAME * WORD, ebp.value)
        if IS_X86_64:
            self.mc.MOV_rr(ebp.value, edi.value)
        else:
            self.mc.MOV_rs(ebp.value, (FRAME_FIXED_SIZE + 1) * WORD)

        for i, loc in enumerate(self.cpu.CALLEE_SAVE_REGISTERS):
            self.mc.MOV_sr((PASS_ON_MY_FRAME + i + 1) * WORD, loc.value)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_header_shadowstack(gcrootmap)

    def _call_header_with_stack_check(self):
        self._call_header()
        if self.stack_check_slowpath == 0:
            pass                # no stack check (e.g. not translated)
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
            self.mc.MOV(eax, heap(endaddr))             # MOV eax, [start]
            self.mc.SUB(eax, esp)                       # SUB eax, current
            self.mc.CMP(eax, heap(lengthaddr))          # CMP eax, [length]
            self.mc.J_il8(rx86.Conditions['BE'], 0)     # JBE .skip
            jb_location = self.mc.get_relative_pos()
            self.mc.CALL(imm(self.stack_check_slowpath))# CALL slowpath
            # patch the JB above                        # .skip:
            offset = self.mc.get_relative_pos() - jb_location
            assert 0 < offset <= 127
            self.mc.overwrite(jb_location-1, chr(offset))
            #

    def _call_footer(self):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_footer_shadowstack(gcrootmap)

        for i in range(len(self.cpu.CALLEE_SAVE_REGISTERS)-1, -1, -1):
            self.mc.MOV_rs(self.cpu.CALLEE_SAVE_REGISTERS[i].value,
                           (i + 1 + PASS_ON_MY_FRAME) * WORD)

        self.mc.MOV_rs(ebp.value, PASS_ON_MY_FRAME * WORD)
        self.mc.ADD_ri(esp.value, FRAME_FIXED_SIZE * WORD)
        self.mc.RET()

    def _load_shadowstack_top_in_ebx(self, mc, gcrootmap):
        rst = gcrootmap.get_root_stack_top_addr()
        if rx86.fits_in_32bits(rst):
            mc.MOV_rj(ebx.value, rst)            # MOV ebx, [rootstacktop]
        else:
            mc.MOV_ri(X86_64_SCRATCH_REG.value, rst) # MOV r11, rootstacktop
            mc.MOV_rm(ebx.value, (X86_64_SCRATCH_REG.value, 0))
            # MOV ebx, [r11]
        #
        return rst

    def _call_header_shadowstack(self, gcrootmap):
        # we don't *really* have to do it, since we have the frame
        # being referenced by the caller. However, we still do it
        # to provide a place where we can read the frame from, in case
        # we need to reload it after a collection
        rst = self._load_shadowstack_top_in_ebx(self.mc, gcrootmap)
        self.mc.MOV_mr((ebx.value, 0), ebp.value)      # MOV [ebx], ebp
        self.mc.ADD_ri(ebx.value, WORD)
        if rx86.fits_in_32bits(rst):
            self.mc.MOV_jr(rst, ebx.value)            # MOV [rootstacktop], ebx
        else:
            self.mc.MOV_mr((X86_64_SCRATCH_REG.value, 0),
                           ebx.value) # MOV [r11], ebx

    def _call_footer_shadowstack(self, gcrootmap):
        rst = gcrootmap.get_root_stack_top_addr()
        if rx86.fits_in_32bits(rst):
            self.mc.SUB_ji8(rst, WORD)       # SUB [rootstacktop], WORD
        else:
            self.mc.MOV_ri(ebx.value, rst)           # MOV ebx, rootstacktop
            self.mc.SUB_mi8((ebx.value, 0), WORD)  # SUB [ebx], WORD

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs
        # we overwrite the instructions at the old _ll_function_addr
        # to start with a JMP to the new _ll_function_addr.
        # Ideally we should rather patch all existing CALLs, but well.
        oldadr = oldlooptoken._ll_function_addr
        target = newlooptoken._ll_function_addr
        # copy frame-info data
        baseofs = self.cpu.get_baseofs_of_frame_field()
        newlooptoken.compiled_loop_token.update_frame_info(
            oldlooptoken.compiled_loop_token, baseofs)
        mc = codebuf.MachineCodeBlockWrapper()
        mc.JMP(imm(target))
        if WORD == 4:         # keep in sync with prepare_loop()
            assert mc.get_relative_pos() == 5
        else:
            assert mc.get_relative_pos() <= 13
        mc.copy_to_raw_memory(oldadr)

    def dump(self, text):
        if not self.verbose:
            return
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            pos = self.mc.get_relative_pos()
            print >> sys.stderr, ' 0x%x  %s' % (pos, text)
        finally:
            Box._extended_display = _prev

    # ------------------------------------------------------------

    def mov(self, from_loc, to_loc):
        if (isinstance(from_loc, RegLoc) and from_loc.is_xmm) or (isinstance(to_loc, RegLoc) and to_loc.is_xmm):
            self.mc.MOVSD(to_loc, from_loc)
        else:
            assert to_loc is not ebp
            self.mc.MOV(to_loc, from_loc)

    regalloc_mov = mov # legacy interface

    def regalloc_push(self, loc):
        if isinstance(loc, RegLoc) and loc.is_xmm:
            self.mc.SUB_ri(esp.value, 8)   # = size of doubles
            self.mc.MOVSD_sx(0, loc.value)
        elif WORD == 4 and isinstance(loc, StackLoc) and loc.get_width() == 8:
            # XXX evil trick
            self.mc.PUSH_b(loc.value + 4)
            self.mc.PUSH_b(loc.value)
        else:
            self.mc.PUSH(loc)

    def regalloc_pop(self, loc):
        if isinstance(loc, RegLoc) and loc.is_xmm:
            self.mc.MOVSD_xs(loc.value, 0)
            self.mc.ADD_ri(esp.value, 8)   # = size of doubles
        elif WORD == 4 and isinstance(loc, StackLoc) and loc.get_width() == 8:
            # XXX evil trick
            self.mc.POP_b(loc.value)
            self.mc.POP_b(loc.value + 4)
        else:
            self.mc.POP(loc)

    def regalloc_immedmem2mem(self, from_loc, to_loc):
        # move a ConstFloatLoc directly to a StackLoc, as two MOVs
        # (even on x86-64, because the immediates are encoded as 32 bits)
        assert isinstance(from_loc, ConstFloatLoc)
        low_part  = rffi.cast(rffi.CArrayPtr(rffi.INT), from_loc.value)[0]
        high_part = rffi.cast(rffi.CArrayPtr(rffi.INT), from_loc.value)[1]
        low_part  = intmask(low_part)
        high_part = intmask(high_part)
        if isinstance(to_loc, RawStackLoc):
            self.mc.MOV32_bi(to_loc.value,     low_part)
            self.mc.MOV32_bi(to_loc.value + 4, high_part)
        else:
            assert isinstance(to_loc, RawEspLoc)
            self.mc.MOV32_si(to_loc.value,     low_part)
            self.mc.MOV32_si(to_loc.value + 4, high_part)                

    def regalloc_perform(self, op, arglocs, resloc):
        genop_list[op.getopnum()](self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        genop_discard_list[op.getopnum()](self, op, arglocs)

    def regalloc_perform_llong(self, op, arglocs, resloc):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        genop_llong_list[oopspecindex](self, op, arglocs, resloc)

    def regalloc_perform_math(self, op, arglocs, resloc):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        genop_math_list[oopspecindex](self, op, arglocs, resloc)

    def regalloc_perform_with_guard(self, op, guard_op, faillocs,
                                    arglocs, resloc, frame_depth):
        faildescr = guard_op.getdescr()
        assert isinstance(faildescr, AbstractFailDescr)
        failargs = guard_op.getfailargs()
        guard_opnum = guard_op.getopnum()
        guard_token = self.implement_guard_recovery(guard_opnum,
                                                    faildescr, failargs,
                                                    faillocs, frame_depth)
        if op is None:
            dispatch_opnum = guard_opnum
        else:
            dispatch_opnum = op.getopnum()
        genop_guard_list[dispatch_opnum](self, op, guard_op, guard_token,
                                         arglocs, resloc)
        if not we_are_translated():
            # must be added by the genop_guard_list[]()
            assert guard_token is self.pending_guard_tokens[-1]

    def regalloc_perform_guard(self, guard_op, faillocs, arglocs, resloc,
                               frame_depth):
        self.regalloc_perform_with_guard(None, guard_op, faillocs, arglocs,
                                         resloc, frame_depth)

    def load_effective_addr(self, sizereg, baseofs, scale, result, frm=imm0):
        self.mc.LEA(result, addr_add(frm, sizereg, baseofs, scale))

    def _unaryop(asmop):
        def genop_unary(self, op, arglocs, resloc):
            getattr(self.mc, asmop)(arglocs[0])
        return genop_unary

    def _binaryop(asmop, can_swap=False):
        def genop_binary(self, op, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
        return genop_binary

    def _binaryop_or_lea(asmop, is_add):
        def genop_binary_or_lea(self, op, arglocs, result_loc):
            # use a regular ADD or SUB if result_loc is arglocs[0],
            # and a LEA only if different.
            if result_loc is arglocs[0]:
                getattr(self.mc, asmop)(arglocs[0], arglocs[1])
            else:
                loc = arglocs[0]
                argloc = arglocs[1]
                assert isinstance(loc, RegLoc)
                assert isinstance(argloc, ImmedLoc)
                assert isinstance(result_loc, RegLoc)
                delta = argloc.value
                if not is_add:    # subtraction
                    delta = -delta
                self.mc.LEA_rm(result_loc.value, (loc.value, delta))
        return genop_binary_or_lea

    def _cmpop(cond, rev_cond):
        def genop_cmp(self, op, arglocs, result_loc):
            rl = result_loc.lowest8bits()
            if isinstance(op.getarg(0), Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                self.mc.SET_ir(rx86.Conditions[rev_cond], rl.value)
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                self.mc.SET_ir(rx86.Conditions[cond], rl.value)
            self.mc.MOVZX8_rr(result_loc.value, rl.value)
        return genop_cmp

    def _cmpop_float(cond, rev_cond, is_ne=False):
        def genop_cmp(self, op, arglocs, result_loc):
            if isinstance(arglocs[0], RegLoc):
                self.mc.UCOMISD(arglocs[0], arglocs[1])
                checkcond = cond
            else:
                self.mc.UCOMISD(arglocs[1], arglocs[0])
                checkcond = rev_cond

            tmp1 = result_loc.lowest8bits()
            if IS_X86_32:
                tmp2 = result_loc.higher8bits()
            elif IS_X86_64:
                tmp2 = X86_64_SCRATCH_REG.lowest8bits()

            self.mc.SET_ir(rx86.Conditions[checkcond], tmp1.value)
            if is_ne:
                self.mc.SET_ir(rx86.Conditions['P'], tmp2.value)
                self.mc.OR8_rr(tmp1.value, tmp2.value)
            else:
                self.mc.SET_ir(rx86.Conditions['NP'], tmp2.value)
                self.mc.AND8_rr(tmp1.value, tmp2.value)
            self.mc.MOVZX8_rr(result_loc.value, tmp1.value)
        return genop_cmp

    def _cmpop_guard(cond, rev_cond, false_cond, false_rev_cond):
        def genop_cmp_guard(self, op, guard_op, guard_token, arglocs, result_loc):
            guard_opnum = guard_op.getopnum()
            if isinstance(op.getarg(0), Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                if guard_opnum == rop.GUARD_FALSE:
                    self.implement_guard(guard_token, rev_cond)
                else:
                    self.implement_guard(guard_token, false_rev_cond)
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                if guard_opnum == rop.GUARD_FALSE:
                    self.implement_guard(guard_token, cond)
                else:
                    self.implement_guard(guard_token, false_cond)
        return genop_cmp_guard

    def _cmpop_guard_float(cond, rev_cond, false_cond, false_rev_cond):
        need_direct_jp = 'A' not in cond
        need_rev_jp = 'A' not in rev_cond
        def genop_cmp_guard_float(self, op, guard_op, guard_token, arglocs,
                                  result_loc):
            guard_opnum = guard_op.getopnum()
            if isinstance(arglocs[0], RegLoc):
                self.mc.UCOMISD(arglocs[0], arglocs[1])
                checkcond = cond
                checkfalsecond = false_cond
                need_jp = need_direct_jp
            else:
                self.mc.UCOMISD(arglocs[1], arglocs[0])
                checkcond = rev_cond
                checkfalsecond = false_rev_cond
                need_jp = need_rev_jp
            if guard_opnum == rop.GUARD_FALSE:
                if need_jp:
                    self.mc.J_il8(rx86.Conditions['P'], 6)
                self.implement_guard(guard_token, checkcond)
            else:
                if need_jp:
                    self.mc.J_il8(rx86.Conditions['P'], 2)
                    self.mc.J_il8(rx86.Conditions[checkcond], 5)
                    self.implement_guard(guard_token)
                else:
                    self.implement_guard(guard_token, checkfalsecond)
        return genop_cmp_guard_float

    def _emit_call(self, x, arglocs, start=0, tmp=eax,
                   argtypes=None, callconv=FFI_DEFAULT_ABI, can_collect=True):
        if IS_X86_64:
            return self._emit_call_64(x, arglocs, start, argtypes,
                                      can_collect=can_collect)
        stack_depth = 0
        n = len(arglocs)
        for i in range(start, n):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                if loc.is_xmm:
                    stack_depth += 2
                else:
                    stack_depth += 1
            stack_depth += loc.get_width() // WORD
        if stack_depth > PASS_ON_MY_FRAME:
            stack_depth = align_stack_words(stack_depth)
            align = (stack_depth - PASS_ON_MY_FRAME)
            self.mc.SUB_ri(esp.value, align * WORD)
        else:
            align = 0
        p = 0
        for i in range(start, n):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                if loc.is_xmm:
                    self.mc.MOVSD_sx(p, loc.value)
                else:
                    self.mc.MOV_sr(p, loc.value)
            p += loc.get_width()
        p = 0
        for i in range(start, n):
            loc = arglocs[i]
            if not isinstance(loc, RegLoc):
                if loc.get_width() == 8:
                    self.mc.MOVSD(xmm0, loc)
                    self.mc.MOVSD_sx(p, xmm0.value)
                else:
                    self.mc.MOV(tmp, loc)
                    self.mc.MOV_sr(p, tmp.value)
            p += loc.get_width()
        # x is a location
        if can_collect:
            noregs = self.cpu.gc_ll_descr.is_shadow_stack()
            gcmap = self._regalloc.get_gcmap([eax], noregs=noregs)
            self.push_gcmap(self.mc, gcmap, store=True)
        self.mc.CALL(x)
        if can_collect:
            self._reload_frame_if_necessary(self.mc)
        if can_collect:
            self.pop_gcmap(self.mc)
        #
        if callconv != FFI_DEFAULT_ABI:
            self._fix_stdcall(callconv, p - align * WORD)
        elif align:
            self.mc.ADD_ri(esp.value, align * WORD)

    def _fix_stdcall(self, callconv, p):
        from rpython.rlib.clibffi import FFI_STDCALL
        assert callconv == FFI_STDCALL
        # it's a bit stupid, but we're just going to cancel the fact that
        # the called function just added 'p' to ESP, by subtracting it again.
        self.mc.SUB_ri(esp.value, p)

    def _emit_call_64(self, x, arglocs, start, argtypes, can_collect=True):
        src_locs = []
        dst_locs = []
        xmm_src_locs = []
        xmm_dst_locs = []
        singlefloats = None

        # In reverse order for use with pop()
        unused_gpr = [r9, r8, ecx, edx, esi, edi]
        unused_xmm = [xmm7, xmm6, xmm5, xmm4, xmm3, xmm2, xmm1, xmm0]

        on_stack = 0
        # count the stack depth
        floats = 0
        for i in range(start, len(arglocs)):
            arg = arglocs[i]
            if arg.is_float() or argtypes and argtypes[i - start] == 'S':
                floats += 1
        all_args = len(arglocs) - start
        stack_depth = (max(all_args - floats - len(unused_gpr), 0) +
                       max(floats - len(unused_xmm), 0))
        align = 0
        if stack_depth > PASS_ON_MY_FRAME:
            stack_depth = align_stack_words(stack_depth)
            align = (stack_depth - PASS_ON_MY_FRAME)
            self.mc.SUB_ri(esp.value, align * WORD)
        for i in range(start, len(arglocs)):
            loc = arglocs[i]
            if loc.is_float():
                xmm_src_locs.append(loc)
                if len(unused_xmm) > 0:
                    xmm_dst_locs.append(unused_xmm.pop())
                else:
                    xmm_dst_locs.append(RawEspLoc(on_stack * WORD, FLOAT))
                    on_stack += 1
            elif argtypes is not None and argtypes[i-start] == 'S':
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

        # Handle register arguments: first remap the xmm arguments
        remap_frame_layout(self, xmm_src_locs, xmm_dst_locs,
                           X86_64_XMM_SCRATCH_REG)
        # Load the singlefloat arguments from main regs or stack to xmm regs
        if singlefloats is not None:
            for src, dst in singlefloats:
                if isinstance(dst, RawEspLoc):
                    # XXX too much special logic
                    if isinstance(src, RawStackLoc):
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
        if x in dst_locs:
            src_locs.append(x)
            dst_locs.append(r10)
            x = r10
        remap_frame_layout(self, src_locs, dst_locs, X86_64_SCRATCH_REG)
        if can_collect:
            noregs = self.cpu.gc_ll_descr.is_shadow_stack()
            gcmap = self._regalloc.get_gcmap([eax], noregs=noregs)
            self.push_gcmap(self.mc, gcmap, store=True)
        self.mc.CALL(x)
        if can_collect:
            self._reload_frame_if_necessary(self.mc)
        if align:
            self.mc.ADD_ri(esp.value, align * WORD)
        if can_collect:
            self.pop_gcmap(self.mc)

    def _reload_frame_if_necessary(self, mc):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            rst = gcrootmap.get_root_stack_top_addr()
            mc.MOV(edx, heap(rst))
            mc.MOV(ebp, mem(edx, -WORD))
        wbdescr = self.cpu.gc_ll_descr.write_barrier_descr
        if gcrootmap and wbdescr:
            # frame never uses card marking, so we enforce this is not
            # an array
            self._write_barrier_fastpath(mc, wbdescr, [ebp], array=False,
                                         is_frame=True)

    def call(self, addr, args, res):
        self._emit_call(imm(addr), args)
        assert res is eax

    genop_int_neg = _unaryop("NEG")
    genop_int_invert = _unaryop("NOT")
    genop_int_add = _binaryop_or_lea("ADD", True)
    genop_int_sub = _binaryop_or_lea("SUB", False)
    genop_int_mul = _binaryop("IMUL", True)
    genop_int_and = _binaryop("AND", True)
    genop_int_or  = _binaryop("OR", True)
    genop_int_xor = _binaryop("XOR", True)
    genop_int_lshift = _binaryop("SHL")
    genop_int_rshift = _binaryop("SAR")
    genop_uint_rshift = _binaryop("SHR")
    genop_float_add = _binaryop("ADDSD", True)
    genop_float_sub = _binaryop('SUBSD')
    genop_float_mul = _binaryop('MULSD', True)
    genop_float_truediv = _binaryop('DIVSD')

    genop_int_lt = _cmpop("L", "G")
    genop_int_le = _cmpop("LE", "GE")
    genop_int_eq = _cmpop("E", "E")
    genop_int_ne = _cmpop("NE", "NE")
    genop_int_gt = _cmpop("G", "L")
    genop_int_ge = _cmpop("GE", "LE")
    genop_ptr_eq = genop_instance_ptr_eq = genop_int_eq
    genop_ptr_ne = genop_instance_ptr_ne = genop_int_ne

    genop_float_lt = _cmpop_float('B', 'A')
    genop_float_le = _cmpop_float('BE', 'AE')
    genop_float_ne = _cmpop_float('NE', 'NE', is_ne=True)
    genop_float_eq = _cmpop_float('E', 'E')
    genop_float_gt = _cmpop_float('A', 'B')
    genop_float_ge = _cmpop_float('AE', 'BE')

    genop_uint_gt = _cmpop("A", "B")
    genop_uint_lt = _cmpop("B", "A")
    genop_uint_le = _cmpop("BE", "AE")
    genop_uint_ge = _cmpop("AE", "BE")

    genop_guard_int_lt = _cmpop_guard("L", "G", "GE", "LE")
    genop_guard_int_le = _cmpop_guard("LE", "GE", "G", "L")
    genop_guard_int_eq = _cmpop_guard("E", "E", "NE", "NE")
    genop_guard_int_ne = _cmpop_guard("NE", "NE", "E", "E")
    genop_guard_int_gt = _cmpop_guard("G", "L", "LE", "GE")
    genop_guard_int_ge = _cmpop_guard("GE", "LE", "L", "G")
    genop_guard_ptr_eq = genop_guard_instance_ptr_eq = genop_guard_int_eq
    genop_guard_ptr_ne = genop_guard_instance_ptr_ne = genop_guard_int_ne

    genop_guard_uint_gt = _cmpop_guard("A", "B", "BE", "AE")
    genop_guard_uint_lt = _cmpop_guard("B", "A", "AE", "BE")
    genop_guard_uint_le = _cmpop_guard("BE", "AE", "A", "B")
    genop_guard_uint_ge = _cmpop_guard("AE", "BE", "B", "A")

    genop_guard_float_lt = _cmpop_guard_float("B", "A", "AE","BE")
    genop_guard_float_le = _cmpop_guard_float("BE","AE", "A", "B")
    genop_guard_float_eq = _cmpop_guard_float("E", "E", "NE","NE")
    genop_guard_float_gt = _cmpop_guard_float("A", "B", "BE","AE")
    genop_guard_float_ge = _cmpop_guard_float("AE","BE", "B", "A")

    def genop_math_sqrt(self, op, arglocs, resloc):
        self.mc.SQRTSD(arglocs[0], resloc)

    def genop_guard_float_ne(self, op, guard_op, guard_token, arglocs, result_loc):
        guard_opnum = guard_op.getopnum()
        if isinstance(arglocs[0], RegLoc):
            self.mc.UCOMISD(arglocs[0], arglocs[1])
        else:
            self.mc.UCOMISD(arglocs[1], arglocs[0])
        if guard_opnum == rop.GUARD_TRUE:
            self.mc.J_il8(rx86.Conditions['P'], 6)
            self.implement_guard(guard_token, 'E')
        else:
            self.mc.J_il8(rx86.Conditions['P'], 2)
            self.mc.J_il8(rx86.Conditions['E'], 5)
            self.implement_guard(guard_token)

    def genop_float_neg(self, op, arglocs, resloc):
        # Following what gcc does: res = x ^ 0x8000000000000000
        self.mc.XORPD(arglocs[0], heap(self.float_const_neg_addr))

    def genop_float_abs(self, op, arglocs, resloc):
        # Following what gcc does: res = x & 0x7FFFFFFFFFFFFFFF
        self.mc.ANDPD(arglocs[0], heap(self.float_const_abs_addr))

    def genop_cast_float_to_int(self, op, arglocs, resloc):
        self.mc.CVTTSD2SI(resloc, arglocs[0])

    def genop_cast_int_to_float(self, op, arglocs, resloc):
        self.mc.CVTSI2SD(resloc, arglocs[0])

    def genop_cast_float_to_singlefloat(self, op, arglocs, resloc):
        loc0, loctmp = arglocs
        self.mc.CVTSD2SS(loctmp, loc0)
        assert isinstance(resloc, RegLoc)
        assert isinstance(loctmp, RegLoc)
        self.mc.MOVD_rx(resloc.value, loctmp.value)

    def genop_cast_singlefloat_to_float(self, op, arglocs, resloc):
        loc0, = arglocs
        assert isinstance(resloc, RegLoc)
        assert isinstance(loc0, RegLoc)
        self.mc.MOVD_xr(resloc.value, loc0.value)
        self.mc.CVTSS2SD_xx(resloc.value, resloc.value)

    def genop_convert_float_bytes_to_longlong(self, op, arglocs, resloc):
        loc0, = arglocs
        if longlong.is_64_bit:
            assert isinstance(resloc, RegLoc)
            assert isinstance(loc0, RegLoc)
            self.mc.MOVD(resloc, loc0)
        else:
            self.mov(loc0, resloc)

    def genop_convert_longlong_bytes_to_float(self, op, arglocs, resloc):
        loc0, = arglocs
        if longlong.is_64_bit:
            assert isinstance(resloc, RegLoc)
            assert isinstance(loc0, RegLoc)
            self.mc.MOVD(resloc, loc0)
        else:
            self.mov(loc0, resloc)

    def genop_guard_int_is_true(self, op, guard_op, guard_token, arglocs, resloc):
        guard_opnum = guard_op.getopnum()
        self.mc.CMP(arglocs[0], imm0)
        if guard_opnum == rop.GUARD_TRUE:
            self.implement_guard(guard_token, 'Z')
        else:
            self.implement_guard(guard_token, 'NZ')

    def genop_int_is_true(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm0)
        rl = resloc.lowest8bits()
        self.mc.SET_ir(rx86.Conditions['NE'], rl.value)
        self.mc.MOVZX8(resloc, rl)

    def genop_guard_int_is_zero(self, op, guard_op, guard_token, arglocs, resloc):
        guard_opnum = guard_op.getopnum()
        self.mc.CMP(arglocs[0], imm0)
        if guard_opnum == rop.GUARD_TRUE:
            self.implement_guard(guard_token, 'NZ')
        else:
            self.implement_guard(guard_token, 'Z')

    def genop_int_is_zero(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm0)
        rl = resloc.lowest8bits()
        self.mc.SET_ir(rx86.Conditions['E'], rl.value)
        self.mc.MOVZX8(resloc, rl)

    def genop_same_as(self, op, arglocs, resloc):
        self.mov(arglocs[0], resloc)
    genop_cast_ptr_to_int = genop_same_as
    genop_cast_int_to_ptr = genop_same_as

    def genop_int_force_ge_zero(self, op, arglocs, resloc):
        self.mc.TEST(arglocs[0], arglocs[0])
        self.mov(imm0, resloc)
        self.mc.CMOVNS(resloc, arglocs[0])

    def genop_int_mod(self, op, arglocs, resloc):
        if IS_X86_32:
            self.mc.CDQ()
        elif IS_X86_64:
            self.mc.CQO()

        self.mc.IDIV_r(ecx.value)

    genop_int_floordiv = genop_int_mod

    def genop_uint_floordiv(self, op, arglocs, resloc):
        self.mc.XOR_rr(edx.value, edx.value)
        self.mc.DIV_r(ecx.value)

    genop_llong_add = _binaryop("PADDQ", True)
    genop_llong_sub = _binaryop("PSUBQ")
    genop_llong_and = _binaryop("PAND",  True)
    genop_llong_or  = _binaryop("POR",   True)
    genop_llong_xor = _binaryop("PXOR",  True)

    def genop_llong_to_int(self, op, arglocs, resloc):
        loc = arglocs[0]
        assert isinstance(resloc, RegLoc)
        if isinstance(loc, RegLoc):
            self.mc.MOVD_rx(resloc.value, loc.value)
        elif isinstance(loc, StackLoc):
            self.mc.MOV_rb(resloc.value, loc.value)
        else:
            not_implemented("llong_to_int: %s" % (loc,))

    def genop_llong_from_int(self, op, arglocs, resloc):
        loc1, loc2 = arglocs
        if isinstance(loc1, ConstFloatLoc):
            assert loc2 is None
            self.mc.MOVSD(resloc, loc1)
        else:
            assert isinstance(loc1, RegLoc)
            assert isinstance(loc2, RegLoc)
            assert isinstance(resloc, RegLoc)
            self.mc.MOVD_xr(loc2.value, loc1.value)
            self.mc.PSRAD_xi(loc2.value, 31)    # -> 0 or -1
            self.mc.MOVD_xr(resloc.value, loc1.value)
            self.mc.PUNPCKLDQ_xx(resloc.value, loc2.value)

    def genop_llong_from_uint(self, op, arglocs, resloc):
        loc1, = arglocs
        assert isinstance(resloc, RegLoc)
        assert isinstance(loc1, RegLoc)
        self.mc.MOVD_xr(resloc.value, loc1.value)

    def genop_llong_eq(self, op, arglocs, resloc):
        loc1, loc2, locxtmp = arglocs
        self.mc.MOVSD(locxtmp, loc1)
        self.mc.PCMPEQD(locxtmp, loc2)
        self.mc.PMOVMSKB_rx(resloc.value, locxtmp.value)
        # Now the lower 8 bits of resloc contain 0x00, 0x0F, 0xF0 or 0xFF
        # depending on the result of the comparison of each of the two
        # double-words of loc1 and loc2.  The higher 8 bits contain random
        # results.  We want to map 0xFF to 1, and 0x00, 0x0F and 0xF0 to 0.
        self.mc.CMP8_ri(resloc.value | rx86.BYTE_REG_FLAG, -1)
        self.mc.SBB_rr(resloc.value, resloc.value)
        self.mc.ADD_ri(resloc.value, 1)

    def genop_llong_ne(self, op, arglocs, resloc):
        loc1, loc2, locxtmp = arglocs
        self.mc.MOVSD(locxtmp, loc1)
        self.mc.PCMPEQD(locxtmp, loc2)
        self.mc.PMOVMSKB_rx(resloc.value, locxtmp.value)
        # Now the lower 8 bits of resloc contain 0x00, 0x0F, 0xF0 or 0xFF
        # depending on the result of the comparison of each of the two
        # double-words of loc1 and loc2.  The higher 8 bits contain random
        # results.  We want to map 0xFF to 0, and 0x00, 0x0F and 0xF0 to 1.
        self.mc.CMP8_ri(resloc.value | rx86.BYTE_REG_FLAG, -1)
        self.mc.SBB_rr(resloc.value, resloc.value)
        self.mc.NEG_r(resloc.value)

    def genop_llong_lt(self, op, arglocs, resloc):
        # XXX just a special case for now: "x < 0"
        loc1, = arglocs
        self.mc.PMOVMSKB_rx(resloc.value, loc1.value)
        self.mc.SHR_ri(resloc.value, 7)
        self.mc.AND_ri(resloc.value, 1)

    # ----------

    def genop_call_malloc_gc(self, op, arglocs, result_loc):
        self.genop_call(op, arglocs, result_loc)
        self.propagate_memoryerror_if_eax_is_null()

    def propagate_memoryerror_if_eax_is_null(self):
        # if self.propagate_exception_path == 0 (tests), this may jump to 0
        # and segfaults.  too bad.  the alternative is to continue anyway
        # with eax==0, but that will segfault too.
        self.mc.TEST_rr(eax.value, eax.value)
        if WORD == 4:
            self.mc.J_il(rx86.Conditions['Z'], self.propagate_exception_path)
            self.mc.add_pending_relocation()
        elif WORD == 8:
            self.mc.J_il(rx86.Conditions['Z'], 0)
            pos = self.mc.get_relative_pos()
            self.pending_memoryerror_trampoline_from.append(pos)

    # ----------

    def load_from_mem(self, resloc, source_addr, size_loc, sign_loc):
        assert isinstance(resloc, RegLoc)
        size = size_loc.value
        sign = sign_loc.value
        if resloc.is_xmm:
            self.mc.MOVSD(resloc, source_addr)
        elif size == WORD:
            self.mc.MOV(resloc, source_addr)
        elif size == 1:
            if sign:
                self.mc.MOVSX8(resloc, source_addr)
            else:
                self.mc.MOVZX8(resloc, source_addr)
        elif size == 2:
            if sign:
                self.mc.MOVSX16(resloc, source_addr)
            else:
                self.mc.MOVZX16(resloc, source_addr)
        elif IS_X86_64 and size == 4:
            if sign:
                self.mc.MOVSX32(resloc, source_addr)
            else:
                self.mc.MOV32(resloc, source_addr)    # zero-extending
        else:
            not_implemented("load_from_mem size = %d" % size)

    def save_into_mem(self, dest_addr, value_loc, size_loc):
        size = size_loc.value
        if isinstance(value_loc, RegLoc) and value_loc.is_xmm:
            self.mc.MOVSD(dest_addr, value_loc)
        elif size == 1:
            self.mc.MOV8(dest_addr, value_loc.lowest8bits())
        elif size == 2:
            self.mc.MOV16(dest_addr, value_loc)
        elif size == 4:
            self.mc.MOV32(dest_addr, value_loc)
        elif size == 8:
            if IS_X86_64:
                self.mc.MOV(dest_addr, value_loc)
            else:
                assert isinstance(value_loc, FloatImmedLoc)
                self.mc.MOV(dest_addr, value_loc.low_part_loc())
                self.mc.MOV(dest_addr.add_offset(4), value_loc.high_part_loc())
        else:
            not_implemented("save_into_mem size = %d" % size)

    def genop_getfield_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc, sign_loc = arglocs
        assert isinstance(size_loc, ImmedLoc)
        source_addr = AddressLoc(base_loc, ofs_loc)
        self.load_from_mem(resloc, source_addr, size_loc, sign_loc)

    genop_getfield_raw = genop_getfield_gc
    genop_getfield_raw_pure = genop_getfield_gc
    genop_getfield_gc_pure = genop_getfield_gc

    def genop_getarrayitem_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc, ofs, sign_loc = arglocs
        assert isinstance(ofs, ImmedLoc)
        assert isinstance(size_loc, ImmedLoc)
        scale = _get_scale(size_loc.value)
        src_addr = addr_add(base_loc, ofs_loc, ofs.value, scale)
        self.load_from_mem(resloc, src_addr, size_loc, sign_loc)

    genop_getarrayitem_gc_pure = genop_getarrayitem_gc
    genop_getarrayitem_raw = genop_getarrayitem_gc
    genop_getarrayitem_raw_pure = genop_getarrayitem_gc

    def genop_raw_load(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc, ofs, sign_loc = arglocs
        assert isinstance(ofs, ImmedLoc)
        src_addr = addr_add(base_loc, ofs_loc, ofs.value, 0)
        self.load_from_mem(resloc, src_addr, size_loc, sign_loc)

    def _get_interiorfield_addr(self, temp_loc, index_loc, itemsize_loc,
                                base_loc, ofs_loc):
        assert isinstance(itemsize_loc, ImmedLoc)
        if isinstance(index_loc, ImmedLoc):
            temp_loc = imm(index_loc.value * itemsize_loc.value)
        elif _valid_addressing_size(itemsize_loc.value):
            return AddressLoc(base_loc, index_loc, _get_scale(itemsize_loc.value), ofs_loc.value)
        else:
            # XXX should not use IMUL in more cases, it can use a clever LEA
            assert isinstance(temp_loc, RegLoc)
            assert isinstance(index_loc, RegLoc)
            assert not temp_loc.is_xmm
            self.mc.IMUL_rri(temp_loc.value, index_loc.value,
                             itemsize_loc.value)
        assert isinstance(ofs_loc, ImmedLoc)
        return AddressLoc(base_loc, temp_loc, 0, ofs_loc.value)

    def genop_getinteriorfield_gc(self, op, arglocs, resloc):
        (base_loc, ofs_loc, itemsize_loc, fieldsize_loc,
            index_loc, temp_loc, sign_loc) = arglocs
        src_addr = self._get_interiorfield_addr(temp_loc, index_loc,
                                                itemsize_loc, base_loc,
                                                ofs_loc)
        self.load_from_mem(resloc, src_addr, fieldsize_loc, sign_loc)

    def genop_discard_setfield_gc(self, op, arglocs):
        base_loc, ofs_loc, size_loc, value_loc = arglocs
        assert isinstance(size_loc, ImmedLoc)
        dest_addr = AddressLoc(base_loc, ofs_loc)
        self.save_into_mem(dest_addr, value_loc, size_loc)

    def genop_discard_setinteriorfield_gc(self, op, arglocs):
        (base_loc, ofs_loc, itemsize_loc, fieldsize_loc,
            index_loc, temp_loc, value_loc) = arglocs
        dest_addr = self._get_interiorfield_addr(temp_loc, index_loc,
                                                 itemsize_loc, base_loc,
                                                 ofs_loc)
        self.save_into_mem(dest_addr, value_loc, fieldsize_loc)

    genop_discard_setinteriorfield_raw = genop_discard_setinteriorfield_gc

    def genop_discard_setarrayitem_gc(self, op, arglocs):
        base_loc, ofs_loc, value_loc, size_loc, baseofs = arglocs
        assert isinstance(baseofs, ImmedLoc)
        assert isinstance(size_loc, ImmedLoc)
        scale = _get_scale(size_loc.value)
        dest_addr = AddressLoc(base_loc, ofs_loc, scale, baseofs.value)
        self.save_into_mem(dest_addr, value_loc, size_loc)

    def genop_discard_raw_store(self, op, arglocs):
        base_loc, ofs_loc, value_loc, size_loc, baseofs = arglocs
        assert isinstance(baseofs, ImmedLoc)
        dest_addr = AddressLoc(base_loc, ofs_loc, 0, baseofs.value)
        self.save_into_mem(dest_addr, value_loc, size_loc)

    def genop_discard_strsetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                              self.cpu.translate_support_code)
        assert itemsize == 1
        dest_addr = AddressLoc(base_loc, ofs_loc, 0, basesize)
        self.mc.MOV8(dest_addr, val_loc.lowest8bits())

    def genop_discard_unicodesetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV32(AddressLoc(base_loc, ofs_loc, 2, basesize), val_loc)
        elif itemsize == 2:
            self.mc.MOV16(AddressLoc(base_loc, ofs_loc, 1, basesize), val_loc)
        else:
            assert 0, itemsize

    genop_discard_setfield_raw = genop_discard_setfield_gc
    genop_discard_setarrayitem_raw = genop_discard_setarrayitem_gc

    def genop_strlen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_unicodelen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_arraylen_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        assert isinstance(ofs_loc, ImmedLoc)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_loc.value))

    def genop_strgetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOVZX8(resloc, AddressLoc(base_loc, ofs_loc, 0, basesize))

    def genop_unicodegetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV32(resloc, AddressLoc(base_loc, ofs_loc, 2, basesize))
        elif itemsize == 2:
            self.mc.MOVZX16(resloc, AddressLoc(base_loc, ofs_loc, 1, basesize))
        else:
            assert 0, itemsize

    def genop_read_timestamp(self, op, arglocs, resloc):
        self.mc.RDTSC()
        if longlong.is_64_bit:
            self.mc.SHL_ri(edx.value, 32)
            self.mc.OR_rr(edx.value, eax.value)
        else:
            loc1, = arglocs
            self.mc.MOVD_xr(loc1.value, edx.value)
            self.mc.MOVD_xr(resloc.value, eax.value)
            self.mc.PUNPCKLDQ_xx(resloc.value, loc1.value)

    def genop_guard_guard_true(self, ign_1, guard_op, guard_token, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(guard_token, 'Z')
    genop_guard_guard_nonnull = genop_guard_guard_true

    def genop_guard_guard_no_exception(self, ign_1, guard_op, guard_token,
                                       locs, ign_2):
        self.mc.CMP(heap(self.cpu.pos_exception()), imm0)
        self.implement_guard(guard_token, 'NZ')

    def genop_guard_guard_not_invalidated(self, ign_1, guard_op, guard_token,
                                     locs, ign_2):
        pos = self.mc.get_relative_pos() + 1 # after potential jmp
        guard_token.pos_jump_offset = pos
        self.pending_guard_tokens.append(guard_token)

    def genop_guard_guard_exception(self, ign_1, guard_op, guard_token,
                                    locs, resloc):
        loc = locs[0]
        loc1 = locs[1]
        self.mc.MOV(loc1, heap(self.cpu.pos_exception()))
        self.mc.CMP(loc1, loc)
        self.implement_guard(guard_token, 'NE')
        self._store_and_reset_exception(self.mc, resloc)

    def _store_and_reset_exception(self, mc, excvalloc=None, exctploc=None):
        if excvalloc is not None:
            assert excvalloc.is_reg()
            mc.MOV(excvalloc, heap(self.cpu.pos_exc_value()))
            if exctploc is not None:
                assert exctploc.is_reg()
                mc.MOV(exctploc, heap(self.cpu.pos_exception()))
                
        mc.MOV(heap(self.cpu.pos_exception()), imm0)
        mc.MOV(heap(self.cpu.pos_exc_value()), imm0)

    def _restore_exception(self, mc, excvalloc, exctploc):
        mc.MOV(heap(self.cpu.pos_exc_value()), excvalloc)
        mc.MOV(heap(self.cpu.pos_exception()), exctploc)

    def _gen_guard_overflow(self, guard_op, guard_token):
        guard_opnum = guard_op.getopnum()
        if guard_opnum == rop.GUARD_NO_OVERFLOW:
            self.implement_guard(guard_token, 'O')
        elif guard_opnum == rop.GUARD_OVERFLOW:
            self.implement_guard(guard_token, 'NO')
        else:
            not_implemented("int_xxx_ovf followed by %s" %
                            guard_op.getopname())

    def genop_guard_int_add_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.mc.ADD(arglocs[0], arglocs[1])
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_int_sub_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.mc.SUB(arglocs[0], arglocs[1])
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_int_mul_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.mc.IMUL(arglocs[0], arglocs[1])
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_guard_false(self, ign_1, guard_op, guard_token, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        self.implement_guard(guard_token, 'NZ')
    genop_guard_guard_isnull = genop_guard_guard_false

    def genop_guard_guard_value(self, ign_1, guard_op, guard_token, locs, ign_2):
        if guard_op.getarg(0).type == FLOAT:
            assert guard_op.getarg(1).type == FLOAT
            self.mc.UCOMISD(locs[0], locs[1])
        else:
            self.mc.CMP(locs[0], locs[1])
        self.implement_guard(guard_token, 'NE')

    def _cmp_guard_class(self, locs):
        offset = self.cpu.vtable_offset
        if offset is not None:
            self.mc.CMP(mem(locs[0], offset), locs[1])
        else:
            # XXX hard-coded assumption: to go from an object to its class
            # we use the following algorithm:
            #   - read the typeid from mem(locs[0]), i.e. at offset 0;
            #     this is a complete word (N=4 bytes on 32-bit, N=8 on
            #     64-bits)
            #   - keep the lower half of what is read there (i.e.
            #     truncate to an unsigned 'N / 2' bytes value)
            #   - multiply by 4 (on 32-bits only) and use it as an
            #     offset in type_info_group
            #   - add 16/32 bytes, to go past the TYPE_INFO structure
            loc = locs[1]
            assert isinstance(loc, ImmedLoc)
            classptr = loc.value
            # here, we have to go back from 'classptr' to the value expected
            # from reading the half-word in the object header.  Note that
            # this half-word is at offset 0 on a little-endian machine;
            # it would be at offset 2 or 4 on a big-endian machine.
            from rpython.rtyper.memory.gctypelayout import GCData
            sizeof_ti = rffi.sizeof(GCData.TYPE_INFO)
            type_info_group = llop.gc_get_type_info_group(llmemory.Address)
            type_info_group = rffi.cast(lltype.Signed, type_info_group)
            expected_typeid = classptr - sizeof_ti - type_info_group
            if IS_X86_32:
                expected_typeid >>= 2
                self.mc.CMP16(mem(locs[0], 0), ImmedLoc(expected_typeid))
            elif IS_X86_64:
                self.mc.CMP32_mi((locs[0].value, 0), expected_typeid)

    def genop_guard_guard_class(self, ign_1, guard_op, guard_token, locs, ign_2):
        self._cmp_guard_class(locs)
        self.implement_guard(guard_token, 'NE')

    def genop_guard_guard_nonnull_class(self, ign_1, guard_op,
                                        guard_token, locs, ign_2):
        self.mc.CMP(locs[0], imm1)
        # Patched below
        self.mc.J_il8(rx86.Conditions['B'], 0)
        jb_location = self.mc.get_relative_pos()
        self._cmp_guard_class(locs)
        # patch the JB above
        offset = self.mc.get_relative_pos() - jb_location
        assert 0 < offset <= 127
        self.mc.overwrite(jb_location-1, chr(offset))
        #
        self.implement_guard(guard_token, 'NE')

    def implement_guard_recovery(self, guard_opnum, faildescr, failargs,
                                 fail_locs, frame_depth):
        exc = (guard_opnum == rop.GUARD_EXCEPTION or
               guard_opnum == rop.GUARD_NO_EXCEPTION or
               guard_opnum == rop.GUARD_NOT_FORCED)
        is_guard_not_invalidated = guard_opnum == rop.GUARD_NOT_INVALIDATED
        is_guard_not_forced = guard_opnum == rop.GUARD_NOT_FORCED
        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        return GuardToken(self.cpu, gcmap, faildescr, failargs,
                          fail_locs, exc, frame_depth,
                          is_guard_not_invalidated, is_guard_not_forced)

    def generate_propagate_error_64(self):
        assert WORD == 8
        startpos = self.mc.get_relative_pos()
        self.mc.JMP(imm(self.propagate_exception_path))
        return startpos

    def generate_quick_failure(self, guardtok):
        """ Gather information about failure
        """
        startpos = self.mc.get_relative_pos()
        fail_descr, target = self.store_info_on_descr(startpos, guardtok)
        self.mc.PUSH(imm(fail_descr))
        self.push_gcmap(self.mc, guardtok.gcmap, push=True)
        self.mc.JMP(imm(target))
        return startpos

    def push_gcmap(self, mc, gcmap, push=False, mov=False, store=False):
        if push:
            mc.PUSH(imm(rffi.cast(lltype.Signed, gcmap)))
        elif mov:
            mc.MOV(RawEspLoc(0, REF),
                   imm(rffi.cast(lltype.Signed, gcmap)))
        else:
            assert store
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            mc.MOV(raw_stack(ofs), imm(rffi.cast(lltype.Signed, gcmap)))

    def pop_gcmap(self, mc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.MOV_bi(ofs, 0)

    def new_stack_loc(self, i, pos, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return StackLoc(i, get_ebp_ofs(base_ofs, i), tp)

    def setup_failure_recovery(self):
        self.failure_recovery_code = [0, 0, 0, 0]

    def _push_all_regs_to_frame(self, mc, ignored_regs, withfloats,
                                callee_only=False):
        # Push all general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = gpr_reg_mgr_cls.save_around_call_regs
        else:
            regs = gpr_reg_mgr_cls.all_regs
        for i, gpr in enumerate(regs):
            if gpr not in ignored_regs:
                mc.MOV_br(i * WORD + base_ofs, gpr.value)
        if withfloats:
            if IS_X86_64:
                coeff = 1
            else:
                coeff = 2
            # Push all XMM regs
            ofs = len(gpr_reg_mgr_cls.all_regs)
            for i in range(len(xmm_reg_mgr_cls.all_regs)):
                mc.MOVSD_bx((ofs + i * coeff) * WORD + base_ofs, i)

    def _pop_all_regs_from_frame(self, mc, ignored_regs, withfloats,
                                 callee_only=False):
        # Pop all general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = gpr_reg_mgr_cls.save_around_call_regs
        else:
            regs = gpr_reg_mgr_cls.all_regs
        for i, gpr in enumerate(regs):
            if gpr not in ignored_regs:
                mc.MOV_rb(gpr.value, i * WORD + base_ofs)
        if withfloats:
            # Pop all XMM regs
            if IS_X86_64:
                coeff = 1
            else:
                coeff = 2
            ofs = len(gpr_reg_mgr_cls.all_regs)
            for i in range(len(xmm_reg_mgr_cls.all_regs)):
                mc.MOVSD_xb(i, (ofs + i * coeff) * WORD + base_ofs)

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = codebuf.MachineCodeBlockWrapper()
        self.mc = mc

        self._push_all_regs_to_frame(mc, [], withfloats)

        if exc:
            # We might have an exception pending.  Load it into ebx
            # (this is a register saved across calls, both if 32 or 64)
            mc.MOV(ebx, heap(self.cpu.pos_exc_value()))
            mc.MOV(heap(self.cpu.pos_exception()), imm0)
            mc.MOV(heap(self.cpu.pos_exc_value()), imm0)
            # save ebx into 'jf_guard_exc'
            offset = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.MOV_br(offset, ebx.value)

        # now we return from the complete frame, which starts from
        # _call_header_with_stack_check().  The LEA in _call_footer below
        # throws away most of the frame, including all the PUSHes that we
        # did just above.
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.POP(eax)
        mc.MOV_br(ofs2, eax.value)
        mc.POP(eax)
        mc.MOV_br(ofs, eax.value)
        # store the gc pattern
        mc.MOV_rr(eax.value, ebp.value)

        self._call_footer()
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart
        self.mc = None

    def genop_finish(self, op, arglocs, result_loc):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) == 2:
            [return_val, fail_descr_loc] = arglocs
            if op.getarg(0).type == FLOAT and not IS_X86_64:
                size = WORD * 2
            else:
                size = WORD
            self.save_into_mem(raw_stack(base_ofs), return_val, imm(size))
        else:
            [fail_descr_loc] = arglocs
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mov(fail_descr_loc, RawStackLoc(ofs))
        arglist = op.getarglist()
        if arglist and arglist[0].type == REF:
            gcmap = self.gcmap_for_finish
            self.push_gcmap(self.mc, gcmap, store=True)
        else:
            # note that the 0 here is redundant, but I would rather
            # keep that one and kill all the others
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            self.mc.MOV_bi(ofs, 0)
        self.mc.MOV_rr(eax.value, ebp.value)
        # exit function
        self._call_footer()

    def implement_guard(self, guard_token, condition=None):
        # These jumps are patched later.
        if condition:
            self.mc.J_il(rx86.Conditions[condition], 0)
        else:
            self.mc.JMP_l(0)
        guard_token.pos_jump_offset = self.mc.get_relative_pos() - 4
        self.pending_guard_tokens.append(guard_token)

    def genop_call(self, op, arglocs, resloc):
        from rpython.jit.backend.llsupport.descr import CallDescr

        sizeloc = arglocs[0]
        assert isinstance(sizeloc, ImmedLoc)
        size = sizeloc.value
        signloc = arglocs[1]

        x = arglocs[2]     # the function address
        if x is eax:
            tmp = ecx
        else:
            tmp = eax

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)

        self._emit_call(x, arglocs, 3, tmp=tmp,
                        argtypes=descr.get_arg_types(),
                        callconv=descr.get_call_conv())

        if IS_X86_32 and isinstance(resloc, StackLoc) and resloc.type == FLOAT:
            # a float or a long long return
            if descr.get_result_type() == 'L':
                self.mc.MOV_br(resloc.value, eax.value)      # long long
                self.mc.MOV_br(resloc.value + 4, edx.value)
                # XXX should ideally not move the result on the stack,
                #     but it's a mess to load eax/edx into a xmm register
                #     and this way is simpler also because the result loc
                #     can just be always a stack location
            else:
                self.mc.FSTPL_b(resloc.value)   # float return
        elif descr.get_result_type() == 'S':
            # singlefloat return
            assert resloc is eax
            if IS_X86_32:
                # must convert ST(0) to a 32-bit singlefloat and load it into EAX
                # mess mess mess
                self.mc.SUB_ri(esp.value, 4)
                self.mc.FSTPS_s(0)
                self.mc.POP_r(eax.value)
            elif IS_X86_64:
                # must copy from the lower 32 bits of XMM0 into eax
                self.mc.MOVD_rx(eax.value, xmm0.value)
        elif size == WORD:
            assert resloc is eax or resloc is xmm0    # a full word
        elif size == 0:
            pass    # void return
        else:
            # use the code in load_from_mem to do the zero- or sign-extension
            assert resloc is eax
            if size == 1:
                srcloc = eax.lowest8bits()
            else:
                srcloc = eax
            self.load_from_mem(eax, srcloc, sizeloc, signloc)

    def _store_force_index(self, guard_op):
        faildescr = guard_op.getdescr()
        ofs = self.cpu.get_ofs_of_frame_field('jf_force_descr')
        self.mc.MOV(raw_stack(ofs), imm(rffi.cast(lltype.Signed,
                                 cast_instance_to_gcref(faildescr))))

    def _emit_guard_not_forced(self, guard_token):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.CMP_bi(ofs, 0)
        self.implement_guard(guard_token, 'NE')

    def genop_guard_call_may_force(self, op, guard_op, guard_token,
                                   arglocs, result_loc):
        self._store_force_index(guard_op)
        self.genop_call(op, arglocs, result_loc)
        self._emit_guard_not_forced(guard_token)

    def genop_guard_call_release_gil(self, op, guard_op, guard_token,
                                     arglocs, result_loc):
        # first, close the stack in the sense of the asmgcc GC root tracker
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            self.call_release_gil(gcrootmap, arglocs)
        # do the call
        self._store_force_index(guard_op)
        self.genop_call(op, arglocs, result_loc)
        # then reopen the stack
        if gcrootmap:
            self.call_reacquire_gil(gcrootmap, result_loc)
        # finally, the guard_not_forced
        self._emit_guard_not_forced(guard_token)

    def call_release_gil(self, gcrootmap, save_registers):
        # First, we need to save away the registers listed in
        # 'save_registers' that are not callee-save.  XXX We assume that
        # the XMM registers won't be modified.  We store them in
        # [ESP+4], [ESP+8], etc.; on x86-32 we leave enough room in [ESP]
        # for the single argument to closestack_addr below.
        if IS_X86_32:
            p = WORD
        elif IS_X86_64:
            p = 0
        for reg in self._regalloc.rm.save_around_call_regs:
            if reg in save_registers:
                self.mc.MOV_sr(p, reg.value)
                p += WORD
        #
        if gcrootmap.is_shadow_stack:
            args = []
        else:
            # note that regalloc.py used save_all_regs=True to save all
            # registers, so we don't have to care about saving them (other
            # than ebp) in the close_stack_struct.  But if they are registers
            # like %eax that would be destroyed by this call, *and* they are
            # used by arglocs for the *next* call, then trouble; for now we
            # will just push/pop them.
            raise NotImplementedError
            xxx
            from rpython.rtyper.memory.gctransform import asmgcroot
            css = self._regalloc.close_stack_struct
            if css == 0:
                use_words = (2 + max(asmgcroot.INDEX_OF_EBP,
                                     asmgcroot.FRAME_PTR) + 1)
                pos = self._regalloc.fm.reserve_location_in_frame(use_words)
                css = get_ebp_ofs(pos + use_words - 1)
                self._regalloc.close_stack_struct = css
            # The location where the future CALL will put its return address
            # will be [ESP-WORD].  But we can't use that as the next frame's
            # top address!  As the code after releasegil() runs without the
            # GIL, it might not be set yet by the time we need it (very
            # unlikely), or it might be overwritten by the following call
            # to reaquiregil() (much more likely).  So we hack even more
            # and use a dummy location containing a dummy value (a pointer
            # to itself) which we pretend is the return address :-/ :-/ :-/
            # It prevents us to store any %esp-based stack locations but we
            # don't so far.
            adr = self.datablockwrapper.malloc_aligned(WORD, WORD)
            rffi.cast(rffi.CArrayPtr(lltype.Signed), adr)[0] = adr
            self.gcrootmap_retaddr_forced = adr
            frame_ptr = css + WORD * (2+asmgcroot.FRAME_PTR)
            if rx86.fits_in_32bits(adr):
                self.mc.MOV_bi(frame_ptr, adr)          # MOV [css.frame], adr
            else:
                self.mc.MOV_ri(eax.value, adr)          # MOV EAX, adr
                self.mc.MOV_br(frame_ptr, eax.value)    # MOV [css.frame], EAX
            # Save ebp
            index_of_ebp = css + WORD * (2+asmgcroot.INDEX_OF_EBP)
            self.mc.MOV_br(index_of_ebp, ebp.value)     # MOV [css.ebp], EBP
            # Call the closestack() function (also releasing the GIL)
            if IS_X86_32:
                reg = eax
            elif IS_X86_64:
                reg = edi
            self.mc.LEA_rb(reg.value, css)
            args = [reg]
        #
        self._emit_call(imm(self.releasegil_addr), args)
        # Finally, restore the registers saved above.
        if IS_X86_32:
            p = WORD
        elif IS_X86_64:
            p = 0
        for reg in self._regalloc.rm.save_around_call_regs:
            if reg in save_registers:
                self.mc.MOV_rs(reg.value, p)
                p += WORD

    def call_reacquire_gil(self, gcrootmap, save_loc):
        # save the previous result (eax/xmm0) into the stack temporarily.
        # XXX like with call_release_gil(), we assume that we don't need
        # to save xmm0 in this case.
        if isinstance(save_loc, RegLoc) and not save_loc.is_xmm:
            self.mc.MOV_sr(WORD, save_loc.value)
        # call the reopenstack() function (also reacquiring the GIL)
        if gcrootmap.is_shadow_stack:
            args = []
        else:
            raise NotImplementedError
            xxx
            assert self.gcrootmap_retaddr_forced == -1, (
                      "missing mark_gc_roots() in CALL_RELEASE_GIL")
            self.gcrootmap_retaddr_forced = 0
            css = self._regalloc.close_stack_struct
            assert css != 0
            if IS_X86_32:
                reg = eax
            elif IS_X86_64:
                reg = edi
            self.mc.LEA_rb(reg.value, css)
            args = [reg]
        self._emit_call(imm(self.reacqgil_addr), args)
        # restore the result from the stack
        if isinstance(save_loc, RegLoc) and not save_loc.is_xmm:
            self.mc.MOV_rs(save_loc.value, WORD)

    def imm(self, v):
        return imm(v)

    # ------------------- CALL ASSEMBLER --------------------------

    def genop_guard_call_assembler(self, op, guard_op, guard_token,
                                   arglocs, result_loc):
        if len(arglocs) == 2:
            [argloc, vloc] = arglocs
        else:
            [argloc] = arglocs
            vloc = self.imm(0)
        self.call_assembler(op, guard_op, argloc, vloc, result_loc, eax)
        self._emit_guard_not_forced(guard_token)

    def _call_assembler_emit_call(self, addr, argloc, tmploc):
        self._emit_call(addr, [argloc], 0, tmp=tmploc)

    def _call_assembler_emit_helper_call(self, addr, arglocs, _):
         self._emit_call(addr, arglocs, 0, tmp=self._second_tmp_reg)

    def _call_assembler_check_descr(self, value, tmploc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.CMP_mi((eax.value, ofs), value)
        # patched later
        self.mc.J_il8(rx86.Conditions['E'], 0) # goto B if we get 'done_with_this_frame'
        return self.mc.get_relative_pos()

    def _call_assembler_patch_je(self, result_loc, je_location):
        if IS_X86_32 and isinstance(result_loc, StackLoc) and result_loc.type == FLOAT:
            self.mc.FSTPL_b(result_loc.value)
        self.mc.JMP_l8(0) # jump to done, patched later
        jmp_location = self.mc.get_relative_pos()
        #
        offset = jmp_location - je_location
        assert 0 < offset <= 127
        self.mc.overwrite(je_location - 1, chr(offset))
        #
        return jmp_location

    def _call_assembler_reset_vtoken(self, jd, vloc):
        from rpython.jit.backend.llsupport.descr import FieldDescr
        fielddescr = jd.vable_token_descr
        assert isinstance(fielddescr, FieldDescr)
        vtoken_ofs = fielddescr.offset
        self.mc.MOV(edx, vloc) # we know vloc is on the current frame
        self.mc.MOV_mi((edx.value, vtoken_ofs), 0)
        # in the line above, TOKEN_NONE = 0

    def _call_assembler_load_result(self, op, result_loc):
        if op.result is not None:
            # load the return value from the dead frame's value index 0
            kind = op.result.type
            descr = self.cpu.getarraydescr_for_frame(kind)
            ofs = self.cpu.unpack_arraydescr(descr)
            if kind == FLOAT:
                self.mc.MOVSD_xm(xmm0.value, (eax.value, ofs))
                if result_loc is not xmm0:
                    self.mc.MOVSD(result_loc, xmm0)
            else:
                assert result_loc is eax
                self.mc.MOV_rm(eax.value, (eax.value, ofs))

    def _call_assembler_patch_jmp(self, jmp_location):
        offset = self.mc.get_relative_pos() - jmp_location
        assert 0 <= offset <= 127
        self.mc.overwrite(jmp_location - 1, chr(offset))

    # ------------------- END CALL ASSEMBLER -----------------------

    def _write_barrier_fastpath(self, mc, descr, arglocs, array=False,
                                is_frame=False):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls a
        # helper piece of assembler.  The latter saves registers as needed
        # and call the function jit_remember_young_pointer() from the GC.
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        #
        card_marking = False
        mask = descr.jit_wb_if_flag_singlebyte
        if array and descr.jit_wb_cards_set != 0:
            # assumptions the rest of the function depends on:
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            assert descr.jit_wb_cards_set_singlebyte == -0x80
            card_marking = True
            mask = descr.jit_wb_if_flag_singlebyte | -0x80
        #
        loc_base = arglocs[0]
        if is_frame:
            assert loc_base is ebp
            loc = raw_stack(descr.jit_wb_if_flag_byteofs)
        else:
            loc = addr_add_const(loc_base, descr.jit_wb_if_flag_byteofs)
        mc.TEST8(loc, imm(mask))
        mc.J_il8(rx86.Conditions['Z'], 0) # patched later
        jz_location = mc.get_relative_pos()

        # for cond_call_gc_wb_array, also add another fast path:
        # if GCFLAG_CARDS_SET, then we can just set one bit and be done
        if card_marking:
            # GCFLAG_CARDS_SET is in this byte at 0x80, so this fact can
            # been checked by the status flags of the previous TEST8
            mc.J_il8(rx86.Conditions['S'], 0) # patched later
            js_location = mc.get_relative_pos()
        else:
            js_location = 0

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = card_marking
        if is_frame:
            helper_num = 4
        elif self._regalloc is not None and self._regalloc.xrm.reg_bindings:
            helper_num += 2
        if self.wb_slowpath[helper_num] == 0:    # tests only
            assert not we_are_translated()
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking,
                                    bool(self._regalloc.xrm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0
        #
        if not is_frame:
            mc.PUSH(loc_base)
        mc.CALL(imm(self.wb_slowpath[helper_num]))

        if card_marking:
            # The helper ends again with a check of the flag in the object.
            # So here, we can simply write again a 'JNS', which will be
            # taken if GCFLAG_CARDS_SET is still not set.
            mc.J_il8(rx86.Conditions['NS'], 0) # patched later
            jns_location = mc.get_relative_pos()
            #
            # patch the JS above
            offset = mc.get_relative_pos() - js_location
            assert 0 < offset <= 127
            mc.overwrite(js_location-1, chr(offset))
            #
            # case GCFLAG_CARDS_SET: emit a few instructions to do
            # directly the card flag setting
            loc_index = arglocs[1]
            if isinstance(loc_index, RegLoc):
                if IS_X86_64 and isinstance(loc_base, RegLoc):
                    # copy loc_index into r11
                    tmp1 = X86_64_SCRATCH_REG
                    mc.MOV_rr(tmp1.value, loc_index.value)
                    final_pop = False
                else:
                    # must save the register loc_index before it is mutated
                    mc.PUSH_r(loc_index.value)
                    tmp1 = loc_index
                    final_pop = True
                # SHR tmp, card_page_shift
                mc.SHR_ri(tmp1.value, descr.jit_wb_card_page_shift)
                # XOR tmp, -8
                mc.XOR_ri(tmp1.value, -8)
                # BTS [loc_base], tmp
                mc.BTS(addr_add_const(loc_base, 0), tmp1)
                # done
                if final_pop:
                    mc.POP_r(loc_index.value)
                #
            elif isinstance(loc_index, ImmedLoc):
                byte_index = loc_index.value >> descr.jit_wb_card_page_shift
                byte_ofs = ~(byte_index >> 3)
                byte_val = 1 << (byte_index & 7)
                mc.OR8(addr_add_const(loc_base, byte_ofs), imm(byte_val))
            else:
                raise AssertionError("index is neither RegLoc nor ImmedLoc")
            #
            # patch the JNS above
            offset = mc.get_relative_pos() - jns_location
            assert 0 < offset <= 127
            mc.overwrite(jns_location-1, chr(offset))

        # patch the JZ above
        offset = mc.get_relative_pos() - jz_location
        assert 0 < offset <= 127
        mc.overwrite(jz_location-1, chr(offset))

    def genop_discard_cond_call_gc_wb(self, op, arglocs):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs)

    def genop_discard_cond_call_gc_wb_array(self, op, arglocs):
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs,
                                     array=True)

    def not_implemented_op_discard(self, op, arglocs):
        not_implemented("not implemented operation: %s" % op.getopname())

    def not_implemented_op(self, op, arglocs, resloc):
        not_implemented("not implemented operation with res: %s" %
                        op.getopname())

    def not_implemented_op_guard(self, op, guard_op,
                                 failaddr, arglocs, resloc):
        not_implemented("not implemented operation (guard): %s" %
                        op.getopname())

    def check_frame_before_jump(self, target_token):
        if target_token in self.target_tokens_currently_compiling:
            return
        if target_token._x86_clt is self.current_clt:
            return
        # We can have a frame coming from god knows where that's
        # passed to a jump to another loop. Make sure it has the
        # correct depth
        expected_size = target_token._x86_clt.frame_info.jfi_frame_depth
        self._check_frame_depth(self.mc, self._regalloc.get_gcmap(),
                                expected_size=expected_size)

    def closing_jump(self, target_token):
        target = target_token._ll_loop_code
        if target_token in self.target_tokens_currently_compiling:
            curpos = self.mc.get_relative_pos() + 5
            self.mc.JMP_l(target - curpos)
        else:
            self.mc.JMP(imm(target))

    def label(self):
        pass

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size, gcmap):
        assert size & (WORD-1) == 0     # must be correctly aligned
        self.mc.MOV(eax, heap(nursery_free_adr))
        self.mc.LEA_rm(edi.value, (eax.value, size))
        self.mc.CMP(edi, heap(nursery_top_adr))
        self.mc.J_il8(rx86.Conditions['NA'], 0) # patched later
        jmp_adr = self.mc.get_relative_pos()
        # save the gcmap
        self.push_gcmap(self.mc, gcmap, mov=True)
        self.mc.CALL(imm(self.malloc_slowpath))
        offset = self.mc.get_relative_pos() - jmp_adr
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr-1, chr(offset))
        self.mc.MOV(heap(nursery_free_adr), edi)

    def malloc_cond_varsize_small(self, nursery_free_adr, nursery_top_adr,
                                  sizeloc, gcmap):
        self.mc.MOV(edi, heap(nursery_free_adr))
        self.mc.MOV(eax, edi)
        self.mc.ADD(edi, sizeloc)
        self.mc.CMP(edi, heap(nursery_top_adr))
        self.mc.J_il8(rx86.Conditions['NA'], 0) # patched later
        jmp_adr = self.mc.get_relative_pos()
        # save the gcmap
        self.push_gcmap(self.mc, gcmap, mov=True)
        self.mc.CALL(imm(self.malloc_slowpath))
        offset = self.mc.get_relative_pos() - jmp_adr
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr-1, chr(offset))
        self.mc.MOV(heap(nursery_free_adr), edi)

    def force_token(self, reg):
        # XXX kill me
        assert isinstance(reg, RegLoc)
        self.mc.MOV_rr(reg.value, ebp.value)

genop_discard_list = [Assembler386.not_implemented_op_discard] * rop._LAST
genop_list = [Assembler386.not_implemented_op] * rop._LAST
genop_llong_list = {}
genop_math_list = {}
genop_guard_list = [Assembler386.not_implemented_op_guard] * rop._LAST

for name, value in Assembler386.__dict__.iteritems():
    if name.startswith('genop_discard_'):
        opname = name[len('genop_discard_'):]
        num = getattr(rop, opname.upper())
        genop_discard_list[num] = value
    elif name.startswith('genop_guard_') and name != 'genop_guard_exception':
        opname = name[len('genop_guard_'):]
        num = getattr(rop, opname.upper())
        genop_guard_list[num] = value
    elif name.startswith('genop_llong_'):
        opname = name[len('genop_llong_'):]
        num = getattr(EffectInfo, 'OS_LLONG_' + opname.upper())
        genop_llong_list[num] = value
    elif name.startswith('genop_math_'):
        opname = name[len('genop_math_'):]
        num = getattr(EffectInfo, 'OS_MATH_' + opname.upper())
        genop_math_list[num] = value
    elif name.startswith('genop_'):
        opname = name[len('genop_'):]
        num = getattr(rop, opname.upper())
        genop_list[num] = value

# XXX: ri386 migration shims:
def addr_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    return AddressLoc(reg_or_imm1, reg_or_imm2, scale, offset)

def addr_add_const(reg_or_imm1, offset):
    return AddressLoc(reg_or_imm1, imm0, 0, offset)

def mem(loc, offset):
    return AddressLoc(loc, imm0, 0, offset)

def raw_stack(offset, type=INT):
    return RawStackLoc(offset, type)

def heap(addr):
    return AddressLoc(ImmedLoc(addr), imm0, 0, 0)

def not_implemented(msg):
    os.write(2, '[x86/asm] %s\n' % msg)
    raise NotImplementedError(msg)

class BridgeAlreadyCompiled(Exception):
    pass
