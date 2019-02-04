
from rpython.jit.backend.aarch64.arch import WORD, JITFRAME_FIXED_SIZE
from rpython.jit.backend.aarch64.codebuilder import InstrBuilder
#from rpython.jit.backend.arm.locations import imm, StackLocation, get_fp_offset
#from rpython.jit.backend.arm.helper.regalloc import VMEM_imm_size
from rpython.jit.backend.aarch64.opassembler import ResOpAssembler
from rpython.jit.backend.aarch64.regalloc import Regalloc
#    CoreRegisterManager, check_imm_arg, VFPRegisterManager,
#    operations as regalloc_operations)
#from rpython.jit.backend.arm import callbuilder
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.llsupport.regalloc import get_scale, valid_addressing_size
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import AbstractFailDescr, FLOAT, INT, VOID
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.rlib.jit import AsmInfo
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from rpython.rlib.rarithmetic import r_uint
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.rjitlog import rjitlog as jl

class AssemblerARM64(ResOpAssembler):
    def assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                      operations, looptoken, log):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        looptoken.compiled_loop_token = clt

        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(looptoken)

        frame_info = self.datablockwrapper.malloc_aligned(
            jitframe.JITFRAMEINFO_SIZE, alignment=WORD)
        clt.frame_info = rffi.cast(jitframe.JITFRAMEINFOPTR, frame_info)
        clt.frame_info.clear() # for now

        if log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        regalloc = Regalloc(assembler=self)
        allgcrefs = []
        operations = regalloc.prepare_loop(inputargs, operations, looptoken,
                                           allgcrefs)
        self.reserve_gcref_table(allgcrefs)
        functionpos = self.mc.get_relative_pos()

        self._call_header_with_stack_check()
        self._check_frame_depth_debug(self.mc)

        loop_head = self.mc.get_relative_pos()
        looptoken._ll_loop_code = loop_head
        #
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        self.update_frame_depth(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        #
        size_excluding_failure_stuff = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        full_size = self.mc.get_relative_pos()
        rawstart = self.materialize_loop(looptoken)
        looptoken._ll_function_addr = rawstart + functionpos

        self.patch_gcref_table(looptoken, rawstart)
        self.process_pending_guards(rawstart)
        self.fixup_target_tokens(rawstart)

        if log and not we_are_translated():
            self.mc._dump_trace(rawstart,
                    'loop.asm')

        ops_offset = self.mc.ops_offset

        if logger:
            log = logger.log_trace(jl.MARK_TRACE_ASM, None, self.mc)
            log.write(inputargs, operations, ops_offset=ops_offset)

            # legacy
            if logger.logger_ops:
                logger.logger_ops.log_loop(inputargs, operations, 0,
                                           "rewritten", name=loopname,
                                           ops_offset=ops_offset)

        self.teardown()

        debug_start("jit-backend-addr")
        debug_print("Loop %d (%s) has address 0x%x to 0x%x (bootstrap 0x%x)" % (
            looptoken.number, loopname,
            r_uint(rawstart + loop_head),
            r_uint(rawstart + size_excluding_failure_stuff),
            r_uint(rawstart + functionpos)))
        debug_print("       gc table: 0x%x" % r_uint(rawstart))
        debug_print("       function: 0x%x" % r_uint(rawstart + functionpos))
        debug_print("         resops: 0x%x" % r_uint(rawstart + loop_head))
        debug_print("       failures: 0x%x" % r_uint(rawstart +
                                                 size_excluding_failure_stuff))
        debug_print("            end: 0x%x" % r_uint(rawstart + full_size))
        debug_stop("jit-backend-addr")

        return AsmInfo(ops_offset, rawstart + loop_head,
                       size_excluding_failure_stuff - loop_head)

    def setup(self, looptoken):
        BaseAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        if we_are_translated():
            self.debug = False
        self.current_clt = looptoken.compiled_loop_token
        self.mc = InstrBuilder()
        self.pending_guards = []
        #assert self.datablockwrapper is None --- but obscure case
        # possible, e.g. getting MemoryError and continuing
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.mc.datablockwrapper = self.datablockwrapper
        self.target_tokens_currently_compiling = {}
        self.frame_depth_to_patch = []

    def _build_failure_recovery(self, exc, withfloats=False):
        pass # XXX

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        pass # XXX

    def build_frame_realloc_slowpath(self):
        pass

    def _build_propagate_exception_path(self):
        pass

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        pass

    def _build_stack_check_slowpath(self):
        pass

    def reserve_gcref_table(self, allgcrefs):
        pass

    def _call_header_with_stack_check(self):
        self._call_header()
        if self.stack_check_slowpath == 0:
            pass                # no stack check (e.g. not translated)
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
            # load stack end
            self.mc.gen_load_int(r.ip.value, endaddr)          # load ip, [end]
            self.mc.LDR_ri(r.ip.value, r.ip.value)             # LDR ip, ip
            # load stack length
            self.mc.gen_load_int(r.lr.value, lengthaddr)       # load lr, lengh
            self.mc.LDR_ri(r.lr.value, r.lr.value)             # ldr lr, *lengh
            # calculate ofs
            self.mc.SUB_rr(r.ip.value, r.ip.value, r.sp.value) # SUB ip, current
            # if ofs
            self.mc.CMP_rr(r.ip.value, r.lr.value)             # CMP ip, lr
            self.mc.BL(self.stack_check_slowpath, c=c.HI)      # call if ip > lr

    def _call_header(self):
        stack_size = WORD #alignment
        stack_size += len(r.callee_saved_registers) * WORD
        if self.cpu.supports_floats:
            stack_size += len(r.callee_saved_vfp_registers) * 2 * WORD

        # push all callee saved registers including lr; and push r1 as
        # well, which contains the threadlocal_addr argument.  Note that
        # we're pushing a total of 10 words, which keeps the stack aligned.
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers] +
                                                        [r.r1.value])
        self.saved_threadlocal_addr = 0   # at offset 0 from location 'sp'
        if self.cpu.supports_floats:
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
            self.saved_threadlocal_addr += (
                len(r.callee_saved_vfp_registers) * 2 * WORD)
        assert stack_size % 8 == 0 # ensure we keep alignment

        # set fp to point to the JITFRAME
        self.mc.MOV_rr(r.fp.value, r.r0.value)
        #
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)
