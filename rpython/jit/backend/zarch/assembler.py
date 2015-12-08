from rpython.jit.backend.llsupport.assembler import (GuardToken, BaseAssembler,
        debug_bridge, DEBUG_COUNTER)
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport import jitframe, rewrite
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.zarch import conditions as c
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.backend.zarch.pool import LiteralPool
from rpython.jit.backend.zarch.codebuilder import InstrBuilder
from rpython.jit.backend.zarch.registers import JITFRAME_FIXED_SIZE
from rpython.jit.backend.zarch.arch import (WORD,
        STD_FRAME_SIZE_IN_BYTES, THREADLOCAL_ADDR_OFFSET,
        RECOVERY_GCMAP_POOL_OFFSET, RECOVERY_TARGET_POOL_OFFSET,
        JUMPABS_TARGET_ADDR__POOL_OFFSET, JUMPABS_POOL_ADDR_POOL_OFFSET)
from rpython.jit.backend.zarch.opassembler import (IntOpAssembler,
    FloatOpAssembler, GuardOpAssembler, MiscOpAssembler,
    CallOpAssembler)
from rpython.jit.backend.zarch.regalloc import Regalloc
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                                have_debug_prints)
from rpython.jit.metainterp.history import (INT, REF, FLOAT,
        TargetToken)
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from rpython.rlib import rgc
from rpython.rlib.longlong2float import float2longlong
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rlib.jit import AsmInfo

class AssemblerZARCH(BaseAssembler,
        IntOpAssembler, FloatOpAssembler,
        GuardOpAssembler, CallOpAssembler,
        MiscOpAssembler):

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.mc = None
        self.current_clt = None
        self._regalloc = None
        self.datablockwrapper = None
        self.propagate_exception_path = 0
        self.stack_check_slowpath = 0
        self.loop_run_counters = []
        self.gcrootmap_retaddr_forced = 0
        self.failure_recovery_code = [0, 0, 0, 0]

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
        self.pool = LiteralPool()

    def teardown(self):
        self.pending_guard_tokens = None
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pool = None

    def target_arglocs(self, looptoken):
        return looptoken._zarch_arglocs

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def gen_func_prolog(self):
        """ NOT_RPYTHON """
        STACK_FRAME_SIZE = 40
        self.mc.STMG(r.r11, r.r15, l.addr(-STACK_FRAME_SIZE, r.SP))
        self.mc.AHI(r.SP, l.imm(-STACK_FRAME_SIZE))

    def gen_func_epilog(self):
        """ NOT_RPYTHON """
        self.mc.LMG(r.r11, r.r15, l.addr(0, r.SP))
        self.jmpto(r.r14)

    def jmpto(self, register):
        # unconditional jump
        self.mc.BCR_rr(0xf, register.value)

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = InstrBuilder()
        self.mc = mc
        # fill in the jf_descr and jf_gcmap fields of the frame according
        # to which failure we are resuming from.  These are set before
        # this function is called (see generate_quick_failure()).
        self._push_core_regs_to_jitframe(mc)
        if withfloats:
            self._push_fp_regs_to_jitframe(mc)

        if exc:
            pass # TODO
            #xxx
            ## We might have an exception pending.
            #mc.load_imm(r.r2, self.cpu.pos_exc_value())
            ## Copy it into 'jf_guard_exc'
            #offset = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            #mc.load(r.r0.value, r.r2.value, 0)
            #mc.store(r.r0.value, r.SPP.value, offset)
            ## Zero out the exception fields
            #diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
            #assert _check_imm_arg(diff)
            #mc.li(r.r0.value, 0)
            #mc.store(r.r0.value, r.r2.value, 0)
            #mc.store(r.r0.value, r.r2.value, diff)

        # now we return from the complete frame, which starts from
        # _call_header_with_stack_check().  The _call_footer below does it.
        self._call_footer()
        rawstart = mc.materialize(self.cpu, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart
        self.mc = None

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.currpos()
        fail_descr, target = self.store_info_on_descr(startpos, guardtok)
        assert target != 0
        pool_offset = guardtok._pool_offset

        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')

        # overwrite the gcmap in the jitframe
        offset = pool_offset + RECOVERY_GCMAP_POOL_OFFSET
        self.mc.LG(r.SCRATCH, l.pool(offset))
        self.mc.STG(r.SCRATCH, l.addr(ofs2, r.SPP))

        # overwrite the target in pool
        offset = pool_offset + RECOVERY_TARGET_POOL_OFFSET
        self.pool.overwrite_64(self.mc, offset, target)
        self.mc.LG(r.r14, l.pool(offset))

        # TODO what is the biggest integer an opaque pointer
        # can have? if not < 2**31-1 then we need to put it on the pool
        # overwrite the fail_descr in the jitframe
        self.mc.LGFI(r.SCRATCH, l.imm(fail_descr))
        self.mc.STG(r.SCRATCH, l.addr(ofs, r.SPP))
        self.mc.BCR(l.imm(0xf), r.r14)

        # TODO do we need to patch this memory region?
        # we need to write at least 6 insns here, for patch_jump_for_descr()
        #while self.mc.currpos() < startpos + 6 * 4:
        #    self.mc.trap()
        return startpos

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

    def new_stack_loc(self, i, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return l.StackLocation(i, l.get_fp_offset(base_ofs, i), tp)

    def _call_header_with_stack_check(self):
        self._call_header()
        if self.stack_check_slowpath == 0:
            pass            # not translated
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
            diff = lengthaddr - endaddr
            assert _check_imm_arg(diff)

            mc = self.mc
            mc.load_imm(r.SCRATCH, self.stack_check_slowpath)
            mc.load_imm(r.SCRATCH2, endaddr)                 # li r2, endaddr
            mc.mtctr(r.SCRATCH.value)
            mc.load(r.SCRATCH.value, r.SCRATCH2.value, 0)    # ld r0, [end]
            mc.load(r.SCRATCH2.value, r.SCRATCH2.value, diff)# ld r2, [length]
            mc.subf(r.SCRATCH.value, r.SP.value, r.SCRATCH.value)  # sub r0, SP
            mc.cmp_op(0, r.SCRATCH.value, r.SCRATCH2.value, signed=False)
            mc.bgtctrl()

    def _check_frame_depth(self, mc, gcmap):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        #mc.LG(r.r2, l.addr(ofs, r.SPP))
        patch_pos = mc.currpos()
        #mc.TRAP2()     # placeholder for cmpdi(0, r2, ...)
        #mc.TRAP2()     # placeholder for bge
        #mc.TRAP2()     # placeholder for li(r0, ...)
        #mc.load_imm(r.SCRATCH2, self._frame_realloc_slowpath)
        #mc.mtctr(r.SCRATCH2.value)
        #self.load_gcmap(mc, r.r2, gcmap)
        #mc.bctrl()

        self.frame_depth_to_patch.append((patch_pos, mc.currpos()))


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
        self.pool.pre_assemble(self, operations)
        entrypos = self.mc.get_relative_pos()
        self.mc.LARL(r.POOL, l.halfword(self.pool.pool_start - entrypos))
        self._call_header_with_stack_check()
        operations = regalloc.prepare_loop(inputargs, operations,
                                           looptoken, clt.allgcrefs)
        looppos = self.mc.get_relative_pos()
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs,
                                                   operations)
        self.update_frame_depth(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        #
        size_excluding_failure_stuff = self.mc.get_relative_pos()
        self.pool.post_assemble(self)
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
            looptoken._zarch_rawstart = rawstart
            looptoken._zarch_fullsize = full_size
            looptoken._zarch_ops_offset = ops_offset
        looptoken._ll_function_addr = rawstart + entrypos
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

    @rgc.no_release_gil
    def assemble_bridge(self, faildescr, inputargs, operations,
                        original_loop_token, log, logger):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(original_loop_token)
        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)
        regalloc = Regalloc(assembler=self)
        self.pool.pre_assemble(self, operations, bridge=True)
        startpos = self.mc.get_relative_pos()
        self.mc.LARL(r.POOL, l.halfword(self.pool.pool_start - startpos))
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)
        self._check_frame_depth(self.mc, regalloc.get_gcmap())
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        codeendpos = self.mc.get_relative_pos()
        self.pool.post_assemble(self)
        self.write_pending_failure_recoveries()
        fullsize = self.mc.get_relative_pos()
        #
        # TODO self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        rawstart = self.materialize_loop(original_loop_token)
        debug_bridge(descr_number, rawstart, codeendpos)
        self.patch_pending_failure_recoveries(rawstart)
        # patch the jump from original guard
        self.patch_jump_for_descr(faildescr, rawstart + startpos)
        ops_offset = self.mc.ops_offset
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        if logger:
            logger.log_bridge(inputargs, operations, "rewritten",
                              ops_offset=ops_offset)
        self.fixup_target_tokens(rawstart)
        self.update_frame_depth(frame_depth)
        self.teardown()
        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def patch_jump_for_descr(self, faildescr, adr_new_target):
        # 'faildescr.adr_jump_offset' is the address of an instruction that is a
        # conditional jump.  We must patch this conditional jump to go
        # to 'adr_new_target'.
        # Updates the pool address
        mc = InstrBuilder()
        mc.write_i64(adr_new_target)
        mc.copy_to_raw_memory(faildescr.adr_jump_offset)
        assert faildescr.adr_jump_offset != 0
        faildescr.adr_jump_offset = 0    # means "patched"

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ll_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def flush_cc(self, condition, result_loc):
        # After emitting an instruction that leaves a boolean result in
        # a condition code (cc), call this.  In the common case, result_loc
        # will be set to 'fp' by the regalloc, which in this case means
        # "propagate it between this operation and the next guard by keeping
        # it in the cc".  In the uncommon case, result_loc is another
        # register, and we emit a load from the cc into this register.
        assert self.guard_success_cc == c.cond_none
        if result_loc is r.SPP:
            self.guard_success_cc = condition
        else:
            # sadly we cannot use LOCGHI
            # it is included in some extension that seem to be NOT installed
            # by default.
            self.mc.LGHI(result_loc, l.imm(1))
            off = self.mc.XGR_byte_count + self.mc.BRC_byte_count
            self.mc.BRC(condition, l.imm(off)) # branch over LGHI
            self.mc.XGR(result_loc, result_loc)

    def regalloc_push(self, loc, already_pushed):
        """Pushes the value stored in loc to the stack
        Can trash the current value of SCRATCH when pushing a stack
        loc"""

        index = WORD * (~already_pushed)
        print("regalloc push", index)

        if loc.type == FLOAT:
            if not loc.is_fp_reg():
                self.regalloc_mov(loc, r.FP_SCRATCH)
                loc = r.FP_SCRATCH
            self.mc.STD(loc, l.addr(index, r.SP))
        else:
            if not loc.is_core_reg():
                self.regalloc_mov(loc, r.SCRATCH)
                loc = r.SCRATCH
            self.mc.STG(loc, l.addr(index, r.SP))

    def regalloc_pop(self, loc, already_pushed):
        """Pops the value on top of the stack to loc. Can trash the current
        value of SCRATCH when popping to a stack loc"""
        index = WORD * (~already_pushed)
        print("regalloc pop", index)

        if loc.type == FLOAT:
            if loc.is_fp_reg():
                self.mc.LD(loc, l.addr(index, r.SP))
            else:
                self.mc.LD(r.FP_SCRATCH, l.addr(index, r.SP))
                self.regalloc_mov(r.FP_SCRATCH, loc)
        else:
            if loc.is_core_reg():
                self.mc.LG(loc, l.addr(index, r.SP))
            else:
                self.mc.LG(r.SCRATCH, l.addr(index, r.SP))
                self.regalloc_mov(r.SCRATCH, loc)

    def regalloc_prepare_move(self, src, dst, tmp):
        if dst.is_stack() and src.is_stack():
            self.regalloc_mov(src, tmp)
            return tmp
        if dst.is_stack() and src.is_in_pool():
            self.regalloc_mov(src, tmp)
            return tmp
        return src

    def push_gcmap(self, mc, gcmap, store=True):
        # (called from callbuilder.py and ../llsupport/callbuilder.py)
        assert store is True
        self.load_gcmap(mc, r.SCRATCH, gcmap)
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STG(r.SCRATCH, l.addr(ofs, r.SPP))

    def _assemble(self, regalloc, inputargs, operations):
        self._regalloc = regalloc
        self.guard_success_cc = c.cond_none
        regalloc.compute_hint_frame_locations(operations)
        regalloc.walk_operations(inputargs, operations)
        assert self.guard_success_cc == c.cond_none
        if we_are_translated() or self.cpu.dont_keepalive_stuff:
            self._regalloc = None   # else keep it around for debugging
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._zarch_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

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
                    self.mc.load_imm(r.SCRATCH, prev_loc)
                    self.mc.STG(r.SCRATCH, l.addr(offset, r.SPP))
                return
            assert 0, "not supported location"
        elif prev_loc.is_in_pool():
            if loc.is_reg():
                self.mc.LG(loc, prev_loc)
                return
            elif loc.is_fp_reg():
                self.mc.LD(loc, prev_loc)
                return
            assert 0, "not supported location (previous is pool loc)"
        elif prev_loc.is_stack():
            offset = prev_loc.value
            # move from memory to register
            if loc.is_reg():
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
                self.mc.LDY(loc, l.addr(offset, r.SPP))
                return
            assert 0, "not supported location"
        elif prev_loc.is_reg():
            # move to another register
            if loc.is_reg():
                self.mc.LGR(loc, prev_loc)
                return
            # move to memory
            elif loc.is_stack():
                offset = loc.value
                self.mc.STG(prev_loc, l.addr(offset, r.SPP))
                return
            assert 0, "not supported location"
        elif prev_loc.is_imm_float():
            value = prev_loc.getint()
            # move immediate value to fp register
            if loc.is_fp_reg():
                xxx
                with scratch_reg(self.mc):
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.lfdx(loc.value, 0, r.SCRATCH.value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                xxx
                with scratch_reg(self.mc):
                    offset = loc.value
                    self.mc.load_imm(r.SCRATCH, value)
                    self.mc.lfdx(r.FP_SCRATCH.value, 0, r.SCRATCH.value)
                    self.mc.stfd(r.FP_SCRATCH.value, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_fp_reg():
            # move to another fp register
            if loc.is_fp_reg():
                self.mc.LDR(loc, prev_loc)
                return
            # move from fp register to memory
            elif loc.is_stack():
                assert loc.type == FLOAT, "target not float location"
                offset = loc.value
                self.mc.STD(prev_loc, l.addr(offset, r.SPP))
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

    def _reload_frame_if_necessary(self, mc, shadowstack_reg=None):
        # might trash the VOLATILE registers different from r3 and f1
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            if gcrootmap.is_shadow_stack:
                if shadowstack_reg is None:
                    diff = mc.load_imm_plus(r.SPP,
                                            gcrootmap.get_root_stack_top_addr())
                    mc.load(r.SPP.value, r.SPP.value, diff)
                    shadowstack_reg = r.SPP
                mc.load(r.SPP.value, shadowstack_reg.value, -WORD)
        wbdescr = self.cpu.gc_ll_descr.write_barrier_descr
        if gcrootmap and wbdescr:
            # frame never uses card marking, so we enforce this is not
            # an array
            self._write_barrier_fastpath(mc, wbdescr, [r.SPP], regalloc=None,
                                         array=False, is_frame=True)

    def patch_pending_failure_recoveries(self, rawstart):
        assert (self.pending_guard_tokens_recovered ==
                len(self.pending_guard_tokens))
        clt = self.current_clt
        for tok in self.pending_guard_tokens:
            addr = rawstart + tok.pos_jump_offset
            #
            tok.faildescr.adr_jump_offset = rawstart + \
                    self.pool.pool_start + tok._pool_offset + \
                    RECOVERY_TARGET_POOL_OFFSET
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

    def _call_header(self):
        # Reserve space for a function descriptor, 3 words
        #self.mc.write64(0)
        #self.mc.write64(0)
        #self.mc.write64(0)

        # Build a new stackframe of size STD_FRAME_SIZE_IN_BYTES
        self.mc.STMG(r.r6, r.r15, l.addr(-160 + 6*WORD, r.SP))
        # back chain is already in
        # place (called function put it at -160!)
        self.mc.AGHI(r.SP, l.imm(-160))
        # save the back chain TODO?
        #self.mc.STG(r.SP, l.addr(0, r.SP))

        # save r3, the second argument, to THREADLOCAL_ADDR_OFFSET
        self.mc.STG(r.r3, l.addr(THREADLOCAL_ADDR_OFFSET, r.SP))

        # move the first argument to SPP: the jitframe object
        self.mc.LGR(r.SPP, r.r2)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_header_shadowstack(gcrootmap)

    def _call_footer(self):
        # the return value is the jitframe
        self.mc.LGR(r.r2, r.SPP)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_footer_shadowstack(gcrootmap)

        # restore registers r6-r15
        self.mc.LMG(r.r6, r.r15, l.addr(6*WORD, r.SP))
        self.jmpto(r.r14)

    def _push_core_regs_to_jitframe(self, mc, includes=r.registers):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        assert len(includes) == 16
        mc.STMG(r.r0, r.r15, l.addr(base_ofs, r.SPP))

    def _push_fp_regs_to_jitframe(self, mc, includes=r.fpregisters):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        assert len(includes) == 16
        v = 16
        for i,reg in enumerate(includes):
            mc.STD(reg, l.addr(base_ofs + (v+i) * WORD, r.SPP))

    # ________________________________________
    # ASSEMBLER EMISSION

    def emit_label(self, op, arglocs, regalloc):
        offset = self.pool.pool_start - self.mc.get_relative_pos()
        # load the pool address at each label
        self.mc.LARL(r.POOL, l.halfword(offset))

    def emit_jump(self, op, arglocs, regalloc):
        # The backend's logic assumes that the target code is in a piece of
        # assembler that was also called with the same number of arguments,
        # so that the locations [ebp+8..] of the input arguments are valid
        # stack locations both before and after the jump.
        #
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        my_nbargs = self.current_clt._debug_nbargs
        target_nbargs = descr._zarch_clt._debug_nbargs
        assert my_nbargs == target_nbargs

        if descr in self.target_tokens_currently_compiling:
            # a label has a LARL instruction that does not need
            # to be executed, thus remove the first opcode
            self.mc.b_offset(descr._ll_loop_code + self.mc.LARL_byte_count)
        else:
            # restore the pool address
            offset = self.pool.get_descr_offset(descr) + \
                     JUMPABS_TARGET_ADDR__POOL_OFFSET
            offset_pool = offset + JUMPABS_POOL_ADDR_POOL_OFFSET
            self.mc.LG(r.SCRATCH, l.pool(offset))
            self.mc.BCR(c.ANY, r.SCRATCH)

            self.pool.overwrite_64(self.mc, offset, descr._ll_loop_code)


    def emit_finish(self, op, arglocs, regalloc):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 1:
            [return_val, fail_descr_loc] = arglocs
            if op.getarg(0).type == FLOAT:
                if return_val.is_in_pool():
                    self.mc.LDY(r.FP_SCRATCH, return_val)
                    return_val = r.FP_SCRATCH
                self.mc.STD(return_val, l.addr(base_ofs, r.SPP))
            else:
                if return_val.is_in_pool():
                    self.mc.LG(r.SCRATCH, return_val)
                    return_val = r.SCRATCH
                self.mc.STG(return_val, l.addr(base_ofs, r.SPP))
        else:
            [fail_descr_loc] = arglocs

        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')

        # gcmap logic here:
        arglist = op.getarglist()
        if arglist and arglist[0].type == REF:
            if self._finish_gcmap:
                # we're returning with a guard_not_forced_2, and
                # additionally we need to say that the result contains
                # a reference too:
                self._finish_gcmap[0] |= r_uint(1)
                gcmap = self._finish_gcmap
            else:
                gcmap = self.gcmap_for_finish
        elif self._finish_gcmap:
            # we're returning with a guard_not_forced_2
            gcmap = self._finish_gcmap
        else:
            gcmap = lltype.nullptr(jitframe.GCMAP)
        self.load_gcmap(self.mc, r.r2, gcmap)

        assert fail_descr_loc.getint() <= 2**32-1
        self.mc.LGFI(r.r3, fail_descr_loc)
        self.mc.STG(r.r3, l.addr(ofs, r.SPP))
        self.mc.STG(r.r2, l.addr(ofs2, r.SPP))

        # exit function
        self._call_footer()

    def load_gcmap(self, mc, reg, gcmap):
        # load the current gcmap into register 'reg'
        ptr = rffi.cast(lltype.Signed, gcmap)
        mc.load_imm(reg, ptr)

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
