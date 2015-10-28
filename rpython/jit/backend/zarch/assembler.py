from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport import jitframe, rewrite
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.zarch import conditions as c
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.backend.zarch.codebuilder import InstrBuilder
from rpython.jit.backend.zarch.registers import JITFRAME_FIXED_SIZE
from rpython.jit.backend.zarch.arch import (WORD,
        STD_FRAME_SIZE_IN_BYTES, GPR_STACK_SAVE_IN_BYTES,
        THREADLOCAL_ADDR_OFFSET)
from rpython.jit.backend.zarch.opassembler import (IntOpAssembler,
    FloatOpAssembler, GuardOpAssembler)
from rpython.jit.backend.zarch.regalloc import Regalloc
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                                have_debug_prints)
from rpython.jit.metainterp.history import (INT, REF, FLOAT)
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from rpython.rlib import rgc
from rpython.rlib.longlong2float import float2longlong
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory

class LiteralPool(object):
    def __init__(self):
        self.size = 0
        # the offset to index the pool
        self.rel_offset = 0
        self.offset = 0
        self.places = []

    def place(self, var):
        assert var.is_constant()
        self.places.append(var)
        off = self.rel_offset
        self.rel_offset += 8
        return off

    def ensure_can_hold_constants(self, op):
        for arg in op.getarglist():
            if arg.is_constant():
                self.reserve_literal(8)

    def reserve_literal(self, size):
        self.size += size

    def reset(self):
        self.size = 0
        self.offset = 0
        self.rel_offset = 0

    def walk_operations(self, operations):
        # O(len(operations)). I do not think there is a way
        # around this.
        #
        # Problem:
        # constants such as floating point operations, plain pointers,
        # or integers might serve as parameter to an operation. thus
        # it must be loaded into a register. You cannot do this with
        # assembler immediates, because the biggest immediate value
        # is 32 bit for branch instructions.
        #
        # Solution:
        # the current solution (gcc does the same), use a literal pool
        # located at register r13. This one can easily offset with 20
        # bit signed values (should be enough)
        for op in operations:
            self.ensure_can_hold_constants(op)

    def pre_assemble(self, mc):
        if self.size == 0:
            # no pool needed!
            return
        if self.size % 2 == 1:
            self.size += 1
        assert self.size < 2**16-1
        mc.BRAS(r.POOL, l.imm(self.size+mc.BRAS._byte_count))
        self.offset = mc.get_relative_pos()
        mc.write('\x00' * self.size)
        print "pool with %d bytes %d // 8" % (self.size, self.size // 8)

    def overwrite_64(self, mc, index, value):
        mc.overwrite(index,   chr(value >> 56 & 0xff))
        mc.overwrite(index+1, chr(value >> 48 & 0xff))
        mc.overwrite(index+2, chr(value >> 40 & 0xff))
        mc.overwrite(index+3, chr(value >> 32 & 0xff))
        mc.overwrite(index+4, chr(value >> 24 & 0xff))
        mc.overwrite(index+5, chr(value >> 16 & 0xff))
        mc.overwrite(index+6, chr(value >> 8 & 0xff))
        mc.overwrite(index+7, chr(value & 0xff))

    def post_assemble(self, mc):
        assert self.offset != 0
        for var in self.places:
            if var.type == FLOAT:
                self.overwrite_64(mc, self.offset, float2longlong(var.value))
                self.offset += 8
            elif var.type == INT:
                self.overwrite(mc, self.offset, var.value)
                self.offset += 8
            else:
                raise NotImplementedError
        self.places = []

class AssemblerZARCH(BaseAssembler,
        IntOpAssembler, FloatOpAssembler,
        GuardOpAssembler):

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.mc = None
        self.pool = LiteralPool()
        self.pending_guards = None
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

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

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
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STG(r.r2, l.addr(ofs, r.SPP))
        mc.STG(r.r3, l.addr(ofs2, r.SPP))

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
        self.pool.reset()
        self.pool.walk_operations(operations)
        self.pool.pre_assemble(self.mc)
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs,
                                                   operations)
        self.pool.post_assemble(self.mc)
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
            if loc.is_reg():
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
                self.mc.store(prev_loc, r.SPP, offset)
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

    def _call_header(self):
        # Reserve space for a function descriptor, 3 words
        #self.mc.write64(0)
        #self.mc.write64(0)
        #self.mc.write64(0)

        # Build a new stackframe of size STD_FRAME_SIZE_IN_BYTES
        self.mc.STMG(r.r6, r.r15, l.addr(-GPR_STACK_SAVE_IN_BYTES, r.SP))
        self.mc.AGHI(r.SP, l.imm(-STD_FRAME_SIZE_IN_BYTES))

        # save r4, the second argument, to THREADLOCAL_ADDR_OFFSET
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
        upoffset = STD_FRAME_SIZE_IN_BYTES-GPR_STACK_SAVE_IN_BYTES
        self.mc.LMG(r.r6, r.r15, l.addr(upoffset, r.SP))
        self.jmpto(r.r14)

    def _push_core_regs_to_jitframe(self, mc, includes=r.MANAGED_REGS):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        assert len(includes) == 16
        mc.STMG(r.r0, r.r15, l.addr(base_ofs, r.SPP))

    def _push_fp_regs_to_jitframe(self, mc, includes=r.MANAGED_FP_REGS):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        assert len(includes) == 16
        mc.LMG(r.r0, r.r15, l.addr(base_ofs, r.SPP))

    # ________________________________________
    # ASSEMBLER EMISSION

    def emit_increment_debug_counter(self, op, arglocs, regalloc):
        pass # TODO

    def emit_label(self, op, arglocs, regalloc):
        pass

    def emit_finish(self, op, arglocs, regalloc):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 1:
            [return_val, fail_descr_loc] = arglocs
            if op.getarg(0).type == FLOAT:
                self.mc.STD(return_val, l.addr(base_ofs, r.SPP))
            else:
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
        # TODO self.load_gcmap(self.mc, r.r2, gcmap)

        assert fail_descr_loc.getint() <= 2**12-1
        self.mc.LGHI(r.r5, fail_descr_loc)
        self.mc.STG(r.r5, l.addr(ofs, r.SPP))
        self.mc.XGR(r.r2, r.r2)
        self.mc.STG(r.r2, l.addr(ofs2, r.SPP))

        # exit function
        self._call_footer()

    def load_gcmap(self, mc, reg, gcmap):
        # load the current gcmap into register 'reg'
        ptr = rffi.cast(lltype.Signed, gcmap)
        #mc.LGHI(mc.pool
        #mc.load_imm(reg, ptr)

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
