import sys
import os

from rpython.jit.backend.llsupport import symbolic, jitframe, rewrite
from rpython.jit.backend.llsupport.assembler import (GuardToken, BaseAssembler,
                                                DEBUG_COUNTER, debug_bridge)
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.metainterp.history import Const, Box, VOID
from rpython.jit.metainterp.history import AbstractFailDescr, INT, REF, FLOAT
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rlib.jit import AsmInfo
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.x86.regalloc import (RegAlloc, get_ebp_ofs,
    gpr_reg_mgr_cls, xmm_reg_mgr_cls)
from rpython.jit.backend.llsupport.regalloc import (get_scale, valid_addressing_size)
from rpython.jit.backend.x86.arch import (FRAME_FIXED_SIZE, WORD, IS_X86_64,
                                       JITFRAME_FIXED_SIZE, IS_X86_32,
                                       PASS_ON_MY_FRAME)
from rpython.jit.backend.x86.regloc import (eax, ecx, edx, ebx, esp, ebp, esi,
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, r8, r9, r10, r11, edi,
    r12, r13, r14, r15, X86_64_SCRATCH_REG, X86_64_XMM_SCRATCH_REG,
    RegLoc, FrameLoc, ConstFloatLoc, ImmedLoc, AddressLoc, imm,
    imm0, imm1, FloatImmedLoc, RawEbpLoc, RawEspLoc)
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.backend.x86 import rx86, codebuf, callbuilder
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.x86 import support
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.rlib import rgc
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter import longlong
from rpython.rlib.rarithmetic import intmask, r_uint
from rpython.rlib.objectmodel import compute_unique_id


class Assembler386(BaseAssembler):
    _regalloc = None
    _output_loop_log = None
    _second_tmp_reg = ecx

    DEBUG_FRAME_DEPTH = False

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.verbose = False
        self.loop_run_counters = []
        self.float_const_neg_addr = 0
        self.float_const_abs_addr = 0
        self.malloc_slowpath = 0
        self.malloc_slowpath_varsize = 0
        self.wb_slowpath = [0, 0, 0, 0, 0]
        self.setup_failure_recovery()
        self.datablockwrapper = None
        self.stack_check_slowpath = 0
        self.propagate_exception_path = 0
        self.teardown()

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
        self.frame_depth_to_patch = []
        self._finish_gcmap = lltype.nullptr(jitframe.GCMAP)

    def teardown(self):
        self.pending_guard_tokens = None
        if WORD == 8:
            self.pending_memoryerror_trampoline_from = None
        self.mc = None
        self.current_clt = None

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

    def set_extra_stack_depth(self, mc, value):
        if self._is_asmgcc():
            extra_ofs = self.cpu.get_ofs_of_frame_field('jf_extra_stack_depth')
            mc.MOV_bi(extra_ofs, value)

    def build_frame_realloc_slowpath(self):
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
            align = callbuilder.align_stack_words(1)
            mc.SUB_ri(esp.value, (align - 1) * WORD)
        else:
            align = callbuilder.align_stack_words(3)
            mc.MOV_rs(eax.value, WORD * 2)
            mc.SUB_ri(esp.value, (align - 1) * WORD)
            mc.MOV_sr(WORD, eax.value)
            mc.MOV_sr(0, ebp.value)
        # align

        self.set_extra_stack_depth(mc, align * WORD)
        self._store_and_reset_exception(mc, None, ebx, ecx)

        mc.CALL(imm(self.cpu.realloc_frame))
        mc.MOV_rr(ebp.value, eax.value)
        self._restore_exception(mc, None, ebx, ecx)
        mc.ADD_ri(esp.value, (align - 1) * WORD)
        self.set_extra_stack_depth(mc, 0)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._load_shadowstack_top_in_ebx(mc, gcrootmap)
            mc.MOV_mr((ebx.value, -WORD), eax.value)

        mc.MOV_bi(gcmap_ofs, 0)
        self._pop_all_regs_from_frame(mc, [], self.cpu.supports_floats)
        mc.RET()
        self._frame_realloc_slowpath = mc.materialize(self.cpu.asmmemmgr, [])

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.
        """
        mc = codebuf.MachineCodeBlockWrapper()
        # copy registers to the frame, with the exception of the
        # 'cond_call_register_arguments' and eax, because these have already
        # been saved by the caller.  Note that this is not symmetrical:
        # these 5 registers are saved by the caller but restored here at
        # the end of this function.
        self._push_all_regs_to_frame(mc, cond_call_register_arguments + [eax],
                                     supports_floats, callee_only)
        if IS_X86_64:
            mc.SUB(esp, imm(WORD))     # alignment
            self.set_extra_stack_depth(mc, 2 * WORD)
            # the arguments are already in the correct registers
        else:
            # we want space for 4 arguments + call + alignment
            mc.SUB(esp, imm(WORD * 7))
            self.set_extra_stack_depth(mc, 8 * WORD)
            # store the arguments at the correct place in the stack
            for i in range(4):
                mc.MOV_sr(i * WORD, cond_call_register_arguments[i].value)
        mc.CALL(eax)
        if IS_X86_64:
            mc.ADD(esp, imm(WORD))
        else:
            mc.ADD(esp, imm(WORD * 7))
        self.set_extra_stack_depth(mc, 0)
        self._reload_frame_if_necessary(mc, align_stack=True)
        self._pop_all_regs_from_frame(mc, [], supports_floats, callee_only)
        self.pop_gcmap(mc)   # push_gcmap(store=True) done by the caller
        mc.RET()
        return mc.materialize(self.cpu.asmmemmgr, [])

    def _build_malloc_slowpath(self, kind):
        """ While arriving on slowpath, we have a gcpattern on stack 0.
        The arguments are passed in eax and edi, as follows:

        kind == 'fixed': nursery_head in eax and the size in edi - eax.

        kind == 'str/unicode': length of the string to allocate in edi.

        kind == 'var': length to allocate in edi, tid in eax,
                       and itemsize in the stack 1 (position esp+WORD).

        This function must preserve all registers apart from eax and edi.
        """
        assert kind in ['fixed', 'str', 'unicode', 'var']
        mc = codebuf.MachineCodeBlockWrapper()
        self._push_all_regs_to_frame(mc, [eax, edi], self.cpu.supports_floats)
        # store the gc pattern
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.MOV_rs(ecx.value, WORD)
        mc.MOV_br(ofs, ecx.value)
        #
        if kind == 'fixed':
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
        elif kind == 'str':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_str')
        elif kind == 'unicode':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_unicode')
        else:
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_array_addr()
        mc.SUB_ri(esp.value, 16 - WORD)  # restore 16-byte alignment
        # magically, the above is enough on X86_32 to reserve 3 stack places
        if kind == 'fixed':
            mc.SUB_rr(edi.value, eax.value) # compute the size we want
            # the arg is already in edi
            if IS_X86_32:
                mc.MOV_sr(0, edi.value)
                if hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
                    mc.MOV_sr(WORD, ebp.value)
            elif hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
                # for tests only
                mc.MOV_rr(esi.value, ebp.value)
        elif kind == 'str' or kind == 'unicode':
            if IS_X86_32:
                # stack layout: [---][---][---][ret].. with 3 free stack places
                mc.MOV_sr(0, edi.value)     # store the length
            else:
                pass                        # length already in edi
        else:
            if IS_X86_32:
                # stack layout: [---][---][---][ret][gcmap][itemsize]...
                mc.MOV_sr(WORD * 2, edi.value)  # store the length
                mc.MOV_sr(WORD * 1, eax.value)  # store the tid
                mc.MOV_rs(edi.value, WORD * 5)  # load the itemsize
                mc.MOV_sr(WORD * 0, edi.value)  # store the itemsize
            else:
                # stack layout: [---][ret][gcmap][itemsize]...
                mc.MOV_rr(edx.value, edi.value) # length
                mc.MOV_rr(esi.value, eax.value) # tid
                mc.MOV_rs(edi.value, WORD * 3)  # load the itemsize
        self.set_extra_stack_depth(mc, 16)
        mc.CALL(imm(addr))
        mc.ADD_ri(esp.value, 16 - WORD)
        mc.TEST_rr(eax.value, eax.value)
        mc.J_il(rx86.Conditions['Z'], 0xfffff) # patched later
        jz_location = mc.get_relative_pos()
        #
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        self._reload_frame_if_necessary(mc, align_stack=True)
        self.set_extra_stack_depth(mc, 0)
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
        return rawstart

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
        self.mc.MOV(RawEbpLoc(ofs), imm(propagate_exception_descr))
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
            mc.SUB_ri(esp.value, WORD)
        #
        if IS_X86_32:
            mc.SUB_ri(esp.value, 2*WORD) # alignment
            mc.PUSH_r(esp.value)
        #
        # esp is now aligned to a multiple of 16 again
        mc.CALL(imm(slowpathaddr))
        #
        if IS_X86_32:
            mc.ADD_ri(esp.value, 3*WORD)    # alignment
        else:
            mc.ADD_ri(esp.value, WORD)
        #
        mc.MOV(eax, heap(self.cpu.pos_exception()))
        mc.TEST_rr(eax.value, eax.value)
        mc.J_il8(rx86.Conditions['NZ'], 0)
        jnz_location = mc.get_relative_pos()
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
            # we have one word to align
            mc.SUB_ri(esp.value, 7 * WORD) # align and reserve some space
            mc.MOV_sr(WORD, eax.value) # save for later
            mc.MOVSD_sx(3 * WORD, xmm0.value)
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
            mc.MOV(exc0, RawEspLoc(WORD * 5, REF))
            mc.MOV(exc1, RawEspLoc(WORD * 6, INT))
            mc.LEA_rs(esp.value, 7 * WORD)
            mc.RET()

        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    @rgc.no_release_gil
    def assemble_loop(self, logger, loopname, inputargs, operations, looptoken,
                      log):
        '''adds the following attributes to looptoken:
               _ll_function_addr    (address of the generated func, as an int)
               _ll_loop_code       (debug: addr of the start of the ResOps)
               _x86_fullsize        (debug: full size including failure)
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
        clt.frame_info.clear() # for now

        if log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        regalloc = RegAlloc(self, self.cpu.translate_support_code)
        #
        self._call_header_with_stack_check()
        self._check_frame_depth_debug(self.mc)
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
            looptoken._x86_rawstart = rawstart
            looptoken._x86_fullsize = full_size
            looptoken._x86_ops_offset = ops_offset
        looptoken._ll_function_addr = rawstart
        if logger:
            logger.log_loop(inputargs, operations, 0, "rewritten",
                            name=loopname, ops_offset=ops_offset)

        self.fixup_target_tokens(rawstart)
        self.teardown()
        # oprofile support
        if self.cpu.profile_agent is not None:
            name = "Loop # %s: %s" % (looptoken.number, loopname)
            self.cpu.profile_agent.native_code_written(name,
                                                       rawstart, full_size)
        return AsmInfo(ops_offset, rawstart + looppos,
                       size_excluding_failure_stuff - looppos)

    @rgc.no_release_gil
    def assemble_bridge(self, logger, faildescr, inputargs, operations,
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
        self._check_frame_depth(self.mc, regalloc.get_gcmap())
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        codeendpos = self.mc.get_relative_pos()
        self.write_pending_failure_recoveries()
        fullsize = self.mc.get_relative_pos()
        #
        rawstart = self.materialize_loop(original_loop_token)
        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE,
                                rawstart)
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
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def patch_stack_checks(self, framedepth, rawstart):
        for ofs in self.frame_depth_to_patch:
            self._patch_frame_depth(ofs + rawstart, framedepth)

    def _check_frame_depth(self, mc, gcmap):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        There are other potential solutions
        to that, but this one does not sound too bad.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.CMP_bi(ofs, 0xffffff)     # force writing 32 bit
        stack_check_cmp_ofs = mc.get_relative_pos() - 4
        mc.J_il8(rx86.Conditions['GE'], 0)
        jg_location = mc.get_relative_pos()
        mc.MOV_si(WORD, 0xffffff)     # force writing 32 bit
        ofs2 = mc.get_relative_pos() - 4
        self.push_gcmap(mc, gcmap, mov=True)
        mc.CALL(imm(self._frame_realloc_slowpath))
        # patch the JG above
        offset = mc.get_relative_pos() - jg_location
        assert 0 < offset <= 127
        mc.overwrite(jg_location-1, chr(offset))
        self.frame_depth_to_patch.append(stack_check_cmp_ofs)
        self.frame_depth_to_patch.append(ofs2)

    def _check_frame_depth_debug(self, mc):
        """ double check the depth size. It prints the error (and potentially
        segfaults later)
        """
        if not self.DEBUG_FRAME_DEPTH:
            return
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.CMP_bi(ofs, 0xffffff)
        stack_check_cmp_ofs = mc.get_relative_pos() - 4
        mc.J_il8(rx86.Conditions['GE'], 0)
        jg_location = mc.get_relative_pos()
        mc.MOV_rr(edi.value, ebp.value)
        mc.MOV_ri(esi.value, 0xffffff)
        ofs2 = mc.get_relative_pos() - 4
        mc.CALL(imm(self.cpu.realloc_frame_crash))
        # patch the JG above
        offset = mc.get_relative_pos() - jg_location
        assert 0 < offset <= 127
        mc.overwrite(jg_location-1, chr(offset))
        self.frame_depth_to_patch.append(stack_check_cmp_ofs)
        self.frame_depth_to_patch.append(ofs2)

    def _patch_frame_depth(self, adr, allocated_depth):
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
        """Loads the shadowstack top in ebx, and returns an integer
        that gives the address of the stack top.  If this integer doesn't
        fit in 32 bits, it will be loaded in r11.
        """
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
        rst = self._load_shadowstack_top_in_ebx(self.mc, gcrootmap)
        self.mc.MOV_mr((ebx.value, 0), ebp.value)      # MOV [ebx], ebp
        self.mc.ADD_ri(ebx.value, WORD)
        if rx86.fits_in_32bits(rst):
            self.mc.MOV_jr(rst, ebx.value)            # MOV [rootstacktop], ebx
        else:
            # The integer 'rst' doesn't fit in 32 bits, so we know that
            # _load_shadowstack_top_in_ebx() above loaded it in r11.
            # Reuse it.  Be careful not to overwrite r11 in the middle!
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
        elif WORD == 4 and isinstance(loc, FrameLoc) and loc.get_width() == 8:
            # XXX evil trick
            self.mc.PUSH_b(loc.value + 4)
            self.mc.PUSH_b(loc.value)
        else:
            self.mc.PUSH(loc)

    def regalloc_pop(self, loc):
        if isinstance(loc, RegLoc) and loc.is_xmm:
            self.mc.MOVSD_xs(loc.value, 0)
            self.mc.ADD_ri(esp.value, 8)   # = size of doubles
        elif WORD == 4 and isinstance(loc, FrameLoc) and loc.get_width() == 8:
            # XXX evil trick
            self.mc.POP_b(loc.value)
            self.mc.POP_b(loc.value + 4)
        else:
            self.mc.POP(loc)

    def regalloc_immedmem2mem(self, from_loc, to_loc):
        # move a ConstFloatLoc directly to a FrameLoc, as two MOVs
        # (even on x86-64, because the immediates are encoded as 32 bits)
        assert isinstance(from_loc, ConstFloatLoc)
        low_part  = rffi.cast(rffi.CArrayPtr(rffi.INT), from_loc.value)[0]
        high_part = rffi.cast(rffi.CArrayPtr(rffi.INT), from_loc.value)[1]
        low_part  = intmask(low_part)
        high_part = intmask(high_part)
        if isinstance(to_loc, RawEbpLoc):
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

    def simple_call(self, fnloc, arglocs, result_loc=eax):
        if result_loc is xmm0:
            result_type = FLOAT
            result_size = 8
        elif result_loc is None:
            result_type = VOID
            result_size = 0
        else:
            result_type = INT
            result_size = WORD
        cb = callbuilder.CallBuilder(self, fnloc, arglocs,
                                     result_loc, result_type,
                                     result_size)
        cb.emit()

    def simple_call_no_collect(self, fnloc, arglocs):
        cb = callbuilder.CallBuilder(self, fnloc, arglocs)
        cb.emit_no_collect()

    def _reload_frame_if_necessary(self, mc, align_stack=False):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            if gcrootmap.is_shadow_stack:
                rst = gcrootmap.get_root_stack_top_addr()
                mc.MOV(ecx, heap(rst))
                mc.MOV(ebp, mem(ecx, -WORD))
        wbdescr = self.cpu.gc_ll_descr.write_barrier_descr
        if gcrootmap and wbdescr:
            # frame never uses card marking, so we enforce this is not
            # an array
            self._write_barrier_fastpath(mc, wbdescr, [ebp], array=False,
                                         is_frame=True, align_stack=align_stack)

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
        elif isinstance(loc, FrameLoc):
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
        self._genop_call(op, arglocs, result_loc)
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
        scale = get_scale(size_loc.value)
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

    def _imul_const_scaled(self, mc, targetreg, sourcereg, itemsize):
        """Produce one operation to do roughly
               targetreg = sourcereg * itemsize
           except that the targetreg may still need shifting by 0,1,2,3.
        """
        if (itemsize & 7) == 0:
            shift = 3
        elif (itemsize & 3) == 0:
            shift = 2
        elif (itemsize & 1) == 0:
            shift = 1
        else:
            shift = 0
        itemsize >>= shift
        #
        if valid_addressing_size(itemsize - 1):
            mc.LEA_ra(targetreg, (sourcereg, sourcereg,
                                  get_scale(itemsize - 1), 0))
        elif valid_addressing_size(itemsize):
            mc.LEA_ra(targetreg, (rx86.NO_BASE_REGISTER, sourcereg,
                                  get_scale(itemsize), 0))
        else:
            mc.IMUL_rri(targetreg, sourcereg, itemsize)
        #
        return shift

    def _get_interiorfield_addr(self, temp_loc, index_loc, itemsize_loc,
                                base_loc, ofs_loc):
        assert isinstance(itemsize_loc, ImmedLoc)
        itemsize = itemsize_loc.value
        if isinstance(index_loc, ImmedLoc):
            temp_loc = imm(index_loc.value * itemsize)
            shift = 0
        elif valid_addressing_size(itemsize):
            temp_loc = index_loc
            shift = get_scale(itemsize)
        else:
            assert isinstance(index_loc, RegLoc)
            assert isinstance(temp_loc, RegLoc)
            assert not temp_loc.is_xmm
            shift = self._imul_const_scaled(self.mc, temp_loc.value,
                                            index_loc.value, itemsize)
        assert isinstance(ofs_loc, ImmedLoc)
        return AddressLoc(base_loc, temp_loc, shift, ofs_loc.value)

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
        scale = get_scale(size_loc.value)
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

    def _store_and_reset_exception(self, mc, excvalloc=None, exctploc=None,
                                   tmploc=None):
        """ Resest the exception. If excvalloc is None, then store it on the
        frame in jf_guard_exc
        """
        if excvalloc is not None:
            assert excvalloc.is_core_reg()
            mc.MOV(excvalloc, heap(self.cpu.pos_exc_value()))
        elif tmploc is not None: # if both are None, just ignore
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.MOV(tmploc, heap(self.cpu.pos_exc_value()))
            mc.MOV(RawEbpLoc(ofs), tmploc)
        if exctploc is not None:
            assert exctploc.is_core_reg()
            mc.MOV(exctploc, heap(self.cpu.pos_exception()))

        mc.MOV(heap(self.cpu.pos_exception()), imm0)
        mc.MOV(heap(self.cpu.pos_exc_value()), imm0)

    def _restore_exception(self, mc, excvalloc, exctploc, tmploc=None):
        if excvalloc is not None:
            mc.MOV(heap(self.cpu.pos_exc_value()), excvalloc)
        else:
            assert tmploc is not None
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.MOV(tmploc, RawEbpLoc(ofs))
            mc.MOV_bi(ofs, 0)
            mc.MOV(heap(self.cpu.pos_exc_value()), tmploc)
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
            from rpython.memory.gctypelayout import GCData
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
        return FrameLoc(i, get_ebp_ofs(base_ofs, i), tp)

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
        for gpr in regs:
            if gpr not in ignored_regs:
                v = gpr_reg_mgr_cls.all_reg_indexes[gpr.value]
                mc.MOV_br(v * WORD + base_ofs, gpr.value)
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
        for gpr in regs:
            if gpr not in ignored_regs:
                v = gpr_reg_mgr_cls.all_reg_indexes[gpr.value]
                mc.MOV_rb(gpr.value, v * WORD + base_ofs)
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
            # We might have an exception pending.  Load it into ebx...
            mc.MOV(ebx, heap(self.cpu.pos_exc_value()))
            mc.MOV(heap(self.cpu.pos_exception()), imm0)
            mc.MOV(heap(self.cpu.pos_exc_value()), imm0)
            # ...and save ebx into 'jf_guard_exc'
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
        # the return value is the jitframe
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
        self.mov(fail_descr_loc, RawEbpLoc(ofs))
        arglist = op.getarglist()
        if arglist and arglist[0].type == REF:
            if self._finish_gcmap:
                self._finish_gcmap[0] |= r_uint(1) # rax
                gcmap = self._finish_gcmap
            else:
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
        self._genop_call(op, arglocs, resloc)

    def _genop_call(self, op, arglocs, resloc, is_call_release_gil=False):
        from rpython.jit.backend.llsupport.descr import CallDescr

        cb = callbuilder.CallBuilder(self, arglocs[2], arglocs[3:], resloc)

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)
        cb.callconv = descr.get_call_conv()
        cb.argtypes = descr.get_arg_types()
        cb.restype  = descr.get_result_type()
        sizeloc = arglocs[0]
        assert isinstance(sizeloc, ImmedLoc)
        cb.ressize = sizeloc.value
        signloc = arglocs[1]
        assert isinstance(signloc, ImmedLoc)
        cb.ressign = signloc.value

        if is_call_release_gil:
            cb.emit_call_release_gil()
        else:
            cb.emit()

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
        self._genop_call(op, arglocs, result_loc)
        self._emit_guard_not_forced(guard_token)

    def genop_guard_call_release_gil(self, op, guard_op, guard_token,
                                     arglocs, result_loc):
        self._store_force_index(guard_op)
        self._genop_call(op, arglocs, result_loc, is_call_release_gil=True)
        self._emit_guard_not_forced(guard_token)

    def call_reacquire_gil(self, gcrootmap, save_loc):
        # save the previous result (eax/xmm0) into the stack temporarily.
        # XXX like with call_release_gil(), we assume that we don't need
        # to save xmm0 in this case.
        if isinstance(save_loc, RegLoc) and not save_loc.is_xmm:
            self.mc.MOV_sr(WORD, save_loc.value)
        # call the reopenstack() function (also reacquiring the GIL)
        if gcrootmap.is_shadow_stack:
            args = []
            css = 0
        else:
            from rpython.memory.gctransform import asmgcroot
            css = WORD * (PASS_ON_MY_FRAME - asmgcroot.JIT_USE_WORDS)
            if IS_X86_32:
                reg = eax
            elif IS_X86_64:
                reg = edi
            self.mc.LEA_rs(reg.value, css)
            args = [reg]
        self._emit_call(imm(self.reacqgil_addr), args, can_collect=False)
        #
        # Now that we required the GIL, we can reload a possibly modified ebp
        if not gcrootmap.is_shadow_stack:
            # special-case: reload ebp from the css
            from rpython.memory.gctransform import asmgcroot
            index_of_ebp = css + WORD * (2+asmgcroot.INDEX_OF_EBP)
            self.mc.MOV_rs(ebp.value, index_of_ebp)  # MOV EBP, [css.ebp]
        #else:
        #   for shadowstack, done for us by _reload_frame_if_necessary()
        self._reload_frame_if_necessary(self.mc)
        self.set_extra_stack_depth(self.mc, 0)
        #
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

    def _call_assembler_emit_call(self, addr, argloc, _):
        self.simple_call(addr, [argloc])

    def _call_assembler_emit_helper_call(self, addr, arglocs, result_loc):
        self.simple_call(addr, arglocs, result_loc)

    def _call_assembler_check_descr(self, value, tmploc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.CMP(mem(eax, ofs), imm(value))
        # patched later
        self.mc.J_il8(rx86.Conditions['E'], 0) # goto B if we get 'done_with_this_frame'
        return self.mc.get_relative_pos()

    def _call_assembler_patch_je(self, result_loc, je_location):
        if (IS_X86_32 and isinstance(result_loc, FrameLoc) and
            result_loc.type == FLOAT):
            self.mc.FSTPL_b(result_loc.value)
        self.mc.JMP_l8(0) # jump to done, patched later
        jmp_location = self.mc.get_relative_pos()
        #
        offset = jmp_location - je_location
        assert 0 < offset <= 127
        self.mc.overwrite(je_location - 1, chr(offset))
        #
        return jmp_location

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
                                is_frame=False, align_stack=False):
        # Write code equivalent to write_barrier() in the GC: it checks
        # a flag in the object at arglocs[0], and if set, it calls a
        # helper piece of assembler.  The latter saves registers as needed
        # and call the function remember_young_pointer() from the GC.
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
        if is_frame and align_stack:
            mc.SUB_ri(esp.value, 16 - WORD) # erase the return address
        mc.CALL(imm(self.wb_slowpath[helper_num]))
        if is_frame and align_stack:
            mc.ADD_ri(esp.value, 16 - WORD) # erase the return address

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

    def closing_jump(self, target_token):
        target = target_token._ll_loop_code
        if target_token in self.target_tokens_currently_compiling:
            curpos = self.mc.get_relative_pos() + 5
            self.mc.JMP_l(target - curpos)
        else:
            self.mc.JMP(imm(target))

    def label(self):
        self._check_frame_depth_debug(self.mc)

    def cond_call(self, op, gcmap, loc_cond, imm_func, arglocs):
        self.mc.TEST(loc_cond, loc_cond)
        self.mc.J_il8(rx86.Conditions['Z'], 0) # patched later
        jmp_adr = self.mc.get_relative_pos()
        #
        self.push_gcmap(self.mc, gcmap, store=True)
        #
        # first save away the 4 registers from 'cond_call_register_arguments'
        # plus the register 'eax'
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        should_be_saved = self._regalloc.rm.reg_bindings.values()
        for gpr in cond_call_register_arguments + [eax]:
            if gpr not in should_be_saved:
                continue
            v = gpr_reg_mgr_cls.all_reg_indexes[gpr.value]
            self.mc.MOV_br(v * WORD + base_ofs, gpr.value)
        #
        # load the 0-to-4 arguments into these registers
        from rpython.jit.backend.x86.jump import remap_frame_layout
        remap_frame_layout(self, arglocs,
                           cond_call_register_arguments[:len(arglocs)],
                           X86_64_SCRATCH_REG if IS_X86_64 else None)
        #
        # load the constant address of the function to call into eax
        self.mc.MOV(eax, imm_func)
        #
        # figure out which variant of cond_call_slowpath to call, and call it
        callee_only = False
        floats = False
        if self._regalloc is not None:
            for reg in self._regalloc.rm.reg_bindings.values():
                if reg not in self._regalloc.rm.save_around_call_regs:
                    break
            else:
                callee_only = True
            if self._regalloc.xrm.reg_bindings:
                floats = True
        cond_call_adr = self.cond_call_slowpath[floats * 2 + callee_only]
        self.mc.CALL(imm(cond_call_adr))
        # restoring the registers saved above, and doing pop_gcmap(), is left
        # to the cond_call_slowpath helper.  We never have any result value.
        offset = self.mc.get_relative_pos() - jmp_adr
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr-1, chr(offset))
        # XXX if the next operation is a GUARD_NO_EXCEPTION, we should
        # somehow jump over it too in the fast path

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

    def malloc_cond_varsize_frame(self, nursery_free_adr, nursery_top_adr,
                                  sizeloc, gcmap):
        if sizeloc is eax:
            self.mc.MOV(edi, sizeloc)
            sizeloc = edi
        self.mc.MOV(eax, heap(nursery_free_adr))
        if sizeloc is edi:
            self.mc.ADD_rr(edi.value, eax.value)
        else:
            self.mc.LEA_ra(edi.value, (eax.value, sizeloc.value, 0, 0))
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

    def malloc_cond_varsize(self, kind, nursery_free_adr, nursery_top_adr,
                            lengthloc, itemsize, maxlength, gcmap,
                            arraydescr):
        from rpython.jit.backend.llsupport.descr import ArrayDescr
        assert isinstance(arraydescr, ArrayDescr)

        # lengthloc is the length of the array, which we must not modify!
        assert lengthloc is not eax and lengthloc is not edi
        if isinstance(lengthloc, RegLoc):
            varsizeloc = lengthloc
        else:
            self.mc.MOV(edi, lengthloc)
            varsizeloc = edi

        self.mc.CMP(varsizeloc, imm(maxlength))
        self.mc.J_il8(rx86.Conditions['A'], 0) # patched later
        jmp_adr0 = self.mc.get_relative_pos()

        self.mc.MOV(eax, heap(nursery_free_adr))
        if valid_addressing_size(itemsize):
            shift = get_scale(itemsize)
        else:
            shift = self._imul_const_scaled(self.mc, edi.value,
                                            varsizeloc.value, itemsize)
            varsizeloc = edi
        # now varsizeloc is a register != eax.  The size of
        # the variable part of the array is (varsizeloc << shift)
        assert arraydescr.basesize >= self.gc_minimal_size_in_nursery
        constsize = arraydescr.basesize + self.gc_size_of_header
        force_realignment = (itemsize % WORD) != 0
        if force_realignment:
            constsize += WORD - 1
        self.mc.LEA_ra(edi.value, (eax.value, varsizeloc.value, shift,
                                   constsize))
        if force_realignment:
            self.mc.AND_ri(edi.value, ~(WORD - 1))
        # now edi contains the total size in bytes, rounded up to a multiple
        # of WORD, plus nursery_free_adr
        self.mc.CMP(edi, heap(nursery_top_adr))
        self.mc.J_il8(rx86.Conditions['NA'], 0) # patched later
        jmp_adr1 = self.mc.get_relative_pos()
        #
        offset = self.mc.get_relative_pos() - jmp_adr0
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr0-1, chr(offset))
        # save the gcmap
        self.push_gcmap(self.mc, gcmap, mov=True)   # mov into RawEspLoc(0)
        if kind == rewrite.FLAG_ARRAY:
            self.mc.MOV_si(WORD, itemsize)
            self.mc.MOV(edi, lengthloc)
            self.mc.MOV_ri(eax.value, arraydescr.tid)
            addr = self.malloc_slowpath_varsize
        else:
            if kind == rewrite.FLAG_STR:
                addr = self.malloc_slowpath_str
            else:
                assert kind == rewrite.FLAG_UNICODE
                addr = self.malloc_slowpath_unicode
            self.mc.MOV(edi, lengthloc)
        self.mc.CALL(imm(addr))
        self.mc.JMP_l8(0)      # jump to done, patched later
        jmp_location = self.mc.get_relative_pos()
        #
        offset = self.mc.get_relative_pos() - jmp_adr1
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr1-1, chr(offset))
        # write down the tid, but not if it's the result of the CALL
        self.mc.MOV(mem(eax, 0), imm(arraydescr.tid))
        # while we're at it, this line is not needed if we've done the CALL
        self.mc.MOV(heap(nursery_free_adr), edi)
        #
        offset = self.mc.get_relative_pos() - jmp_location
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_location - 1, chr(offset))

    def store_force_descr(self, op, fail_locs, frame_depth):
        guard_token = self.implement_guard_recovery(op.opnum,
                                                    op.getdescr(),
                                                    op.getfailargs(),
                                                    fail_locs, frame_depth)
        self._finish_gcmap = guard_token.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(0, guard_token)

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
    return RawEbpLoc(offset, type)

def heap(addr):
    return AddressLoc(ImmedLoc(addr), imm0, 0, 0)

def not_implemented(msg):
    msg = '[x86/asm] %s\n' % msg
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)

cond_call_register_arguments = [edi, esi, edx, ecx]

class BridgeAlreadyCompiled(Exception):
    pass
