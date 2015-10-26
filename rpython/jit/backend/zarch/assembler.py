from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport import jitframe, rewrite
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.zarch import conditions as c
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as loc
from rpython.jit.backend.zarch.codebuilder import InstrBuilder
from rpython.jit.backend.zarch.arch import (WORD, JITFRAME_FIXED_SIZE)
from rpython.jit.backend.zarch.opassembler import IntOpAssembler
from rpython.jit.backend.zarch.regalloc import Regalloc
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                                have_debug_prints)
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from rpython.rlib import rgc
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory

class AssemblerZARCH(BaseAssembler, IntOpAssembler):

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.mc = None
        self.pending_guards = None
        self.current_clt = None
        self._regalloc = None
        self.datablockwrapper = None
        self.propagate_exception_path = 0
        self.stack_check_slowpath = 0
        self.loop_run_counters = []
        self.gcrootmap_retaddr_forced = 0

    def setup(self, looptoken):
        BaseAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        if we_are_translated():
            self.debug = False
        self.current_clt = looptoken.compiled_loop_token
        self.mc = InstrBuilder()
        self.pending_guard_tokens = []
        self.pending_guard_tokens_recovered = 0
        #assert self.datablockwrapper is None --- but obscure case
        # possible, e.g. getting MemoryError and continuing
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.mc.datablockwrapper = self.datablockwrapper
        self.target_tokens_currently_compiling = {}
        self.frame_depth_to_patch = []

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def gen_func_prolog(self):
        STACK_FRAME_SIZE = 40
        self.mc.STMG(r.r11, r.r15, loc.addr(-STACK_FRAME_SIZE, r.sp))
        self.mc.AHI(r.sp, loc.imm(-STACK_FRAME_SIZE))

    def gen_func_epilog(self):
        self.mc.LMG(r.r11, r.r15, loc.addr(0, r.SPP))
        self.jmpto(r.r14)

    def jmpto(self, register):
        # TODO, manual says this is a performance killer, there
        # might be another operation for unconditional JMP?
        self.mc.BCR_rr(0xf, register.value)

    def _build_failure_recovery(self, exc, withfloats=False):
        pass # TODO

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        pass # TODO

    def build_frame_realloc_slowpath(self):
        # this code should do the following steps
        # a) store all registers in the jitframe
        # b) fish for the arguments passed by the caller
        # c) store the gcmap in the jitframe
        # d) call realloc_frame
        # e) set the fp to point to the new jitframe
        # f) store the address of the new jitframe in the shadowstack
        # c) set the gcmap field to 0 in the new jitframe
        # g) restore registers and return
        pass # TODO

    def _build_propagate_exception_path(self):
        pass # TODO

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.
        """
        pass # TODO

    def _build_stack_check_slowpath(self):
        pass # TODO

    def _call_header_with_stack_check(self):
        pass # TODO

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
        #
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

    def regalloc_mov(self, prev_loc, loc):
        if prev_loc.is_imm():
            value = prev_loc.getint()
            # move immediate value to register
            if loc.is_core_reg():
                self.mc.load_imm(loc, value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                with scratch_reg(self.mc):
                    offset = loc.value
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.store(r.SCRATCH.value, r.SPP, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.value
            # move from memory to register
            if loc.is_core_reg():
                self.mc.load(loc, r.SPP, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.value
                with scratch_reg(self.mc):
                    self.mc.load(r.SCRATCH.value, r.SPP, offset)
                    self.mc.store(r.SCRATCH.value, r.SPP, target_offset)
                return
            # move from memory to fp register
            elif loc.is_fp_reg():
                assert prev_loc.type == FLOAT, 'source not float location'
                self.mc.lfd(loc, r.SPP, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_core_reg():
            reg = prev_loc.value
            # move to another register
            if loc.is_core_reg():
                other_reg = loc.value
                self.mc.mr(other_reg, reg)
                return
            # move to memory
            elif loc.is_stack():
                offset = loc.value
                self.mc.store(reg, r.SPP, offset)
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

    def update_frame_depth(self, frame_depth):
        if frame_depth > 0x7fff:
            raise JitFrameTooDeep
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def write_pending_failure_recoveries(self):
        # for each pending guard, generate the code of the recovery stub
        # at the end of self.mc.
        for i in range(self.pending_guard_tokens_recovered,
                       len(self.pending_guard_tokens)):
            tok = self.pending_guard_tokens[i]
            tok.pos_recovery_stub = self.generate_quick_failure(tok)
        self.pending_guard_tokens_recovered = len(self.pending_guard_tokens)

    def patch_stack_checks(self, frame_depth):
        if frame_depth > 0x7fff:
            raise JitFrameTooDeep     # XXX
        for traps_pos, jmp_target in self.frame_depth_to_patch:
            pmc = OverwritingBuilder(self.mc, traps_pos, 3)
            # three traps, so exactly three instructions to patch here
            #pmc.cmpdi(0, r.r2.value, frame_depth)         # 1
            #pmc.bc(7, 0, jmp_target - (traps_pos + 4))    # 2   "bge+"
            #pmc.li(r.r0.value, frame_depth)               # 3
            #pmc.overwrite()

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu, allblocks,
                                    self.cpu.gc_ll_descr.gcrootmap)
        return start

    def patch_pending_failure_recoveries(self, rawstart):
        assert (self.pending_guard_tokens_recovered ==
                len(self.pending_guard_tokens))
        clt = self.current_clt
        for tok in self.pending_guard_tokens:
            addr = rawstart + tok.pos_jump_offset
            #
            # XXX see patch_jump_for_descr()
            tok.faildescr.adr_jump_offset = rawstart + tok.pos_recovery_stub
            #
            relative_target = tok.pos_recovery_stub - tok.pos_jump_offset
            #
            if not tok.guard_not_invalidated():
                mc = InstrBuilder()
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



    # ________________________________________
    # ASSEMBLER EMISSION

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        pass # TODO

    def emit_finish(self, op, arglocs, regalloc):
        pass # TODO

def notimplemented_op(asm, op, arglocs, regalloc):
    print "[ZARCH/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

asm_operations = [notimplemented_op] * (rop._LAST + 1)
asm_extra_operations = {}

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_%s' % key
    if hasattr(AssemblerZARCH, methname):
        func = getattr(AssemblerZARCH, methname).im_func
        asm_operations[value] = func
