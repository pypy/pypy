from rpython.jit.backend.llsupport.assembler import (GuardToken, BaseAssembler,
        debug_bridge, DEBUG_COUNTER)
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport import jitframe, rewrite
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.zarch import conditions as c
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.backend.zarch.pool import LiteralPool
from rpython.jit.backend.zarch.codebuilder import (InstrBuilder,
        OverwritingBuilder)
from rpython.jit.backend.zarch.helper.regalloc import check_imm_value
from rpython.jit.backend.zarch.registers import JITFRAME_FIXED_SIZE
from rpython.jit.backend.zarch.regalloc import ZARCHRegisterManager
from rpython.jit.backend.zarch.arch import (WORD,
        STD_FRAME_SIZE_IN_BYTES, THREADLOCAL_ADDR_OFFSET,
        RECOVERY_GCMAP_POOL_OFFSET, RECOVERY_TARGET_POOL_OFFSET,
        JUMPABS_TARGET_ADDR__POOL_OFFSET, JUMPABS_POOL_ADDR_POOL_OFFSET)
from rpython.jit.backend.zarch.opassembler import OpAssembler
from rpython.jit.backend.zarch.regalloc import Regalloc
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                                have_debug_prints)
from rpython.jit.metainterp.history import (INT, REF, FLOAT, TargetToken)
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id
from rpython.rlib import rgc
from rpython.rlib.longlong2float import float2longlong
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rlib.jit import AsmInfo

class JitFrameTooDeep(Exception):
    pass

class AssemblerZARCH(BaseAssembler, OpAssembler):

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
        self.wb_slowpath = [0,0,0,0,0]

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
        self.mc.STG(r.SCRATCH2, l.addr(ofs2, r.SPP))
        self.mc.STG(r.SCRATCH, l.addr(ofs, r.SPP))

        self._push_core_regs_to_jitframe(mc)
        if withfloats:
            self._push_fp_regs_to_jitframe(mc)

        if exc:
            # We might have an exception pending.
            mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
            # Copy it into 'jf_guard_exc'
            offset = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.LG(r.SCRATCH2, l.addr(0, r.SCRATCH))
            mc.STG(r.SCRATCH2, l.addr(offset, r.SPP))
            # Zero out the exception fields
            diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
            assert check_imm_value(diff)
            mc.LGHI(r.SCRATCH2, l.imm(0))
            mc.STG(r.SCRATCH2, l.addr(0, r.SCRATCH))
            mc.STG(r.SCRATCH2, l.addr(diff, r.SCRATCH))

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


        # overwrite the gcmap in the jitframe
        offset = pool_offset + RECOVERY_GCMAP_POOL_OFFSET
        self.mc.LG(r.SCRATCH2, l.pool(offset))

        # overwrite the target in pool
        offset = pool_offset + RECOVERY_TARGET_POOL_OFFSET
        self.pool.overwrite_64(self.mc, offset, target)
        self.mc.LG(r.r14, l.pool(offset))

        self.mc.load_imm(r.SCRATCH, fail_descr)
        #self.mc.LGFI(r.SCRATCH, l.imm(fail_descr))
        self.mc.BCR(l.imm(0xf), r.r14)

        return startpos

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        descr = self.cpu.gc_ll_descr.write_barrier_descr
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
        # all fp registers.  It takes its single argument in r0
        # (or in SPP if 'for_frame').
        if for_frame:
            argument_loc = r.SPP
        else:
            argument_loc = r.r0

        mc = InstrBuilder()
        old_mc = self.mc
        self.mc = mc
        
        # save the information
        mc.store_link()

        RCS2 = r.r10
        RCS3 = r.r12

        LOCAL_VARS_OFFSET = 0
        extra_stack_size = LOCAL_VARS_OFFSET + 4 * WORD + 8
        extra_stack_size = (extra_stack_size + 15) & ~15
        if for_frame:
            # NOTE: don't save registers on the jitframe here!  It might
            # override already-saved values that will be restored
            # later...
            #
            # This 'for_frame' version is called after a CALL.  It does not
            # need to save many registers: the registers that are anyway
            # destroyed by the call can be ignored (VOLATILES), and the
            # non-volatile registers won't be changed here.  It only needs
            # to save r2 and f0 (possible results of the call),
            # and two more non-volatile registers (used to store
            # the RPython exception that occurred in the CALL, if any).
            #
            mc.STMG(r.r10, r.r12, l.addr(10*WORD, r.SP))
            mc.STG(r.r2, l.addr(2*WORD, r.SP))
            mc.STD(r.f0, l.addr(3*WORD, r.SP)) # slot of r3 is not used here
            saved_regs = None
            saved_fp_regs = None
        else:
            # push all volatile registers, push RCS1, and sometimes push RCS2
            if withcards:
                saved_regs = r.VOLATILES + [RCS2]
            else:
                saved_regs = r.VOLATILES
            if withfloats:
                saved_fp_regs = r.MANAGED_FP_REGS
            else:
                saved_fp_regs = []

            self._push_core_regs_to_jitframe(mc, saved_regs)
            self._push_fp_regs_to_jitframe(mc, saved_fp_regs)

        if for_frame:
            # note that it's safe to store the exception in register,
            # since the call to write barrier can't collect
            # (and this is assumed a bit left and right here, like lack
            # of _reload_frame_if_necessary)
            # This trashes r0 and r2, which is fine in this case
            assert argument_loc is not r.r0
            self._store_and_reset_exception(mc, RCS2, RCS3)

        if withcards:
            mc.LGR(RCS2, argument_loc)
        func = rffi.cast(lltype.Signed, func)
        # Note: if not 'for_frame', argument_loc is r0, which must carefully
        # not be overwritten above
        mc.STG(r.SP, l.addr(0, r.SP)) # store the backchain
        mc.AGHI(r.SP, l.imm(-STD_FRAME_SIZE_IN_BYTES))
        mc.load_imm(mc.RAW_CALL_REG, func)
        mc.LGR(r.r2, argument_loc)
        mc.raw_call()
        mc.AGHI(r.SP, l.imm(STD_FRAME_SIZE_IN_BYTES))

        if for_frame:
            self._restore_exception(mc, RCS2, RCS3)

        if withcards:
            # A final andix before the blr, for the caller.  Careful to
            # not follow this instruction with another one that changes
            # the status of the condition code
            card_marking_mask = descr.jit_wb_cards_set_singlebyte
            mc.LLGC(RCS2, l.addr(descr.jit_wb_if_flag_byteofs, RCS2))
            mc.NILL(RCS2, l.imm(card_marking_mask & 0xFF))

        if for_frame:
            mc.LMG(r.r10, r.r12, l.addr(10*WORD, r.SP))
            mc.LG(r.r2, l.addr(2*WORD, r.SP))
            mc.LD(r.f0, l.addr(3*WORD, r.SP)) # slot of r3 is not used here
        else:
            self._pop_core_regs_from_jitframe(mc, saved_regs)
            self._pop_fp_regs_from_jitframe(mc, saved_fp_regs)

        mc.restore_link()
        mc.BCR(c.ANY, r.RETURN)

        self.mc = old_mc
        rawstart = mc.materialize(self.cpu, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    def _store_and_reset_exception(self, mc, excvalloc, exctploc=None):
        """Reset the exception, after fetching it inside the two regs.
        """
        mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert check_imm_value(diff)
        # Load the exception fields into the two registers
        mc.LG(excvalloc, l.addr(0,r.SCRATCH))
        if exctploc is not None:
            mc.LG(exctploc, l.addr(diff, r.SCRATCH))
        # Zero out the exception fields
        mc.LGHI(r.SCRATCH2, l.imm(0))
        mc.STG(r.SCRATCH2, l.addr(0, r.SCRATCH))
        mc.STG(r.SCRATCH2, l.addr(diff, r.SCRATCH))

    def _restore_exception(self, mc, excvalloc, exctploc):
        mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert check_imm_value(diff)
        # Store the exception fields from the two registers
        mc.STG(excvalloc, l.addr(0, r.SCRATCH))
        mc.STG(exctploc,  l.addr(diff, r.SCRATCH))

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
        mc = InstrBuilder()
        self.mc = mc

        # signature of this _frame_realloc_slowpath function:
        #   * on entry, r0 is the new size
        #   * on entry, r1 is the gcmap
        #   * no managed register must be modified

        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STG(r.SCRATCH, l.addr(ofs2, r.SPP))

        self._push_core_regs_to_jitframe(mc, r.MANAGED_REGS)
        self._push_fp_regs_to_jitframe(mc)

        self.mc.store_link()

        # First argument is SPP (= r31), which is the jitframe
        mc.LGR(r.r2, r.SPP)

        # no need to move second argument (frame_depth),
        # it is already in register r3!
        mc.LGR(r.r3, r.SCRATCH2)

        RCS2 = r.r10
        RCS3 = r.r12

        self._store_and_reset_exception(mc, RCS2, RCS3)

        # Do the call
        adr = rffi.cast(lltype.Signed, self.cpu.realloc_frame)
        mc.push_std_frame()
        mc.load_imm(mc.RAW_CALL_REG, adr)
        mc.raw_call()
        mc.pop_std_frame()

        # The result is stored back into SPP (= r31)
        mc.LGR(r.SPP, r.r2)

        self._restore_exception(mc, RCS2, RCS3)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            diff = mc.load_imm_plus(r.r5, gcrootmap.get_root_stack_top_addr())
            mc.load(r.r5, r.r5, diff)
            mc.store(r.r2, r.r5, -WORD)

        mc.restore_link()
        self._pop_core_regs_from_jitframe(mc)
        self._pop_fp_regs_from_jitframe(mc)
        mc.BCR(c.ANY, r.RETURN)

        self._frame_realloc_slowpath = mc.materialize(self.cpu, [])
        self.mc = None

    def _build_propagate_exception_path(self):
        if not self.cpu.propagate_exception_descr:
            return

        self.mc = InstrBuilder()
        #
        # read and reset the current exception

        propagate_exception_descr = rffi.cast(lltype.Signed,
                  cast_instance_to_gcref(self.cpu.propagate_exception_descr))
        ofs3 = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
        ofs4 = self.cpu.get_ofs_of_frame_field('jf_descr')

        self._store_and_reset_exception(self.mc, r.r3)
        self.mc.load_imm(r.r3, propagate_exception_descr)
        self.mc.STG(r.r2, l.addr(ofs3, r.SPP))
        self.mc.STG(r.r3, l.addr(ofs4, r.SPP))
        #
        self._call_footer()
        rawstart = self.mc.materialize(self.cpu, [])
        self.propagate_exception_path = rawstart
        self.mc = None

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.
        """
        # signature of these cond_call_slowpath functions:
        #   * on entry, r12 contains the function to call
        #   * r3, r4, r5, r6 contain arguments for the call
        #   * r0 is the gcmap
        #   * the old value of these regs must already be stored in the jitframe
        #   * on exit, all registers are restored from the jitframe

        mc = InstrBuilder()
        self.mc = mc
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STG(r.SCRATCH2, l.addr(ofs2,r.SPP))

        # copy registers to the frame, with the exception of r3 to r6 and r12,
        # because these have already been saved by the caller.  Note that
        # this is not symmetrical: these 5 registers are saved by the caller
        # but restored here at the end of this function.
        if callee_only:
            saved_regs = ZARCHRegisterManager.save_around_call_regs
        else:
            saved_regs = ZARCHRegisterManager.all_regs
        regs = [reg for reg in saved_regs
                    if reg is not r.r2 and
                       reg is not r.r3 and
                       reg is not r.r4 and
                       reg is not r.r5 and
                       reg is not r.r12]
        self._push_core_regs_to_jitframe(mc, regs + [r.r14])
        if supports_floats:
            self._push_fp_regs_to_jitframe(mc)

        # allocate a stack frame!
        mc.push_std_frame()
        mc.raw_call(r.r12)
        mc.pop_std_frame()

        # Finish
        self._reload_frame_if_necessary(mc)

        self._pop_core_regs_from_jitframe(mc, saved_regs + [r.r14])
        if supports_floats:
            self._pop_fp_regs_from_jitframe(mc)
        mc.BCR(c.ANY, r.RETURN)
        self.mc = None
        return mc.materialize(self.cpu, [])

    def _build_malloc_slowpath(self, kind):
        """ While arriving on slowpath, we have a gcmap in SCRATCH.
        The arguments are passed in r.RES and r.RSZ, as follows:

        kind == 'fixed': nursery_head in r.RES and the size in r.RSZ - r.RES.

        kind == 'str/unicode': length of the string to allocate in r.RES.

        kind == 'var': itemsize in r.RES, length to allocate in r.RSZ,
                       and tid in r.SCRATCH2.

        This function must preserve all registers apart from r.RES and r.RSZ.
        On return, SCRATCH must contain the address of nursery_free.
        """
        assert kind in ['fixed', 'str', 'unicode', 'var']
        mc = InstrBuilder()
        self.mc = mc
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STG(r.SCRATCH, l.addr(ofs2, r.SPP))
        saved_regs = [reg for reg in r.MANAGED_REGS
                          if reg is not r.RES and reg is not r.RSZ]
        self._push_core_regs_to_jitframe(mc, saved_regs + [r.r14])
        self._push_fp_regs_to_jitframe(mc)
        #
        if kind == 'fixed':
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
        elif kind == 'str':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_str')
        elif kind == 'unicode':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_unicode')
        else:
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_array_addr()

        if kind == 'fixed':
            # compute the size we want
            # r5 is saved to the jit frame
            # RES == r2!
            mc.LGR(r.r5, r.RSZ)
            mc.SGR(r.r5, r.RES)
            mc.LGR(r.r2, r.r5)
            if hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
                # for tests only
                mc.LGR(r.r3, r.SPP)
        elif kind == 'str' or kind == 'unicode':
            pass  # length is already in r3
        else:
            # arguments to the called function are [itemsize, tid, length]
            # itemsize is already in r2
            mc.LGR(r.r3, r.SCRATCH2)   # tid
            mc.LGR(r.r4, r.RSZ)        # length

        # Do the call
        addr = rffi.cast(lltype.Signed, addr)
        mc.push_std_frame()
        mc.load_imm(mc.RAW_CALL_REG, addr)
        mc.raw_call()
        mc.pop_std_frame()

        self._reload_frame_if_necessary(mc)

        # Check that we don't get NULL; if we do, we always interrupt the
        # current loop, as a "good enough" approximation (same as
        # emit_call_malloc_gc()).
        self.propagate_memoryerror_if_r2_is_null()

        self._pop_core_regs_from_jitframe(mc, saved_regs + [r.r14])
        self._pop_fp_regs_from_jitframe(mc)

        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        self.mc.load_imm(r.SCRATCH, nursery_free_adr)

        # r.SCRATCH is now the address of nursery_free
        # r.RES is still the result of the call done above
        # r.RSZ is loaded from [SCRATCH], to make the caller's store a no-op here
        mc.load(r.RSZ, r.r1, 0)
        #
        mc.BCR(c.ANY, r.r14)
        self.mc = None
        return mc.materialize(self.cpu, [])


    def _build_stack_check_slowpath(self):
        _, _, slowpathaddr = self.cpu.insert_stack_check()
        if slowpathaddr == 0 or not self.cpu.propagate_exception_descr:
            return      # no stack check (for tests, or non-translated)
        #
        # make a regular function that is called from a point near the start
        # of an assembler function (after it adjusts the stack and saves
        # registers).
        mc = InstrBuilder()
        #
        self._push_core_regs_to_jitframe(mc, [r.r14]) # store the link on the jit frame
        # Do the call
        mc.push_std_frame()
        mc.LGR(r.r2, r.SP)
        mc.load_imm(mc.RAW_CALL_REG, slowpathaddr)
        mc.raw_call()
        mc.pop_std_frame()
        #
        # Check if it raised StackOverflow
        mc.load_imm(r.SCRATCH, self.cpu.pos_exception())
        mc.LG(r.SCRATCH, l.addr(0, r.SCRATCH))
        # if this comparison is true, then everything is ok,
        # else we have an exception
        mc.cmp_op(r.SCRATCH, l.imm(0), imm=True)
        #
        self._pop_core_regs_from_jitframe(mc, [r.r14]) # restore the link on the jit frame
        # So we return to our caller, conditionally if "EQ"
        mc.BCR(c.EQ, r.r14)
        #
        # Else, jump to propagate_exception_path
        assert self.propagate_exception_path
        mc.branch_absolute(self.propagate_exception_path)
        #
        rawstart = mc.materialize(self.cpu, [])
        self.stack_check_slowpath = rawstart

    def new_stack_loc(self, i, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        loc = l.StackLocation(i, l.get_fp_offset(base_ofs, i), tp)
        return loc

    def _call_header_with_stack_check(self):
        self._call_header()
        if self.stack_check_slowpath == 0:
            pass            # not translated
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
            diff = lengthaddr - endaddr
            assert check_imm_value(diff)

            mc = self.mc
            mc.load_imm(r.SCRATCH, endaddr)     # li r0, endaddr
            mc.load(r.r14, r.SCRATCH, 0)        # lg r14, [end]
            mc.load(r.SCRATCH, r.SCRATCH, diff) # lg r0, [length]
            mc.LGR(r.SCRATCH2, r.SP)
            mc.SGR(r.SCRATCH2, r.r14)           # sub r1, (SP - r14)
            jmp_pos = self.mc.currpos()
            self.mc.reserve_cond_jump()

            mc.load_imm(r.r14, self.stack_check_slowpath)
            mc.BASR(r.r14, r.r14)

            currpos = self.mc.currpos()
            pmc = OverwritingBuilder(mc, jmp_pos, 1)
            pmc.CLGRJ(r.SCRATCH2, r.SCRATCH, c.GT, l.imm(currpos - jmp_pos))
            pmc.overwrite()

    def _check_frame_depth(self, mc, gcmap):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.LG(r.SCRATCH2, l.addr(ofs, r.SPP))
        patch_pos = mc.currpos()
        # placeholder for the following instructions
        # CGFI r1, ... (6  bytes)
        # BRC  c, ...  (4  bytes)
        # LGHI r0, ... (4  bytes)
        #       sum -> (14 bytes)
        mc.write('\x00'*14)
        self.mc.push_std_frame()
        mc.load_imm(r.RETURN, self._frame_realloc_slowpath)
        self.load_gcmap(mc, r.r1, gcmap)
        mc.raw_call()
        self.mc.pop_std_frame()

        self.frame_depth_to_patch.append((patch_pos, mc.currpos()))

    def patch_stack_checks(self, frame_depth):
        if frame_depth > 0x7fff:
            raise JitFrameTooDeep     # XXX
        for traps_pos, jmp_target in self.frame_depth_to_patch:
            pmc = OverwritingBuilder(self.mc, traps_pos, 3)
            # three traps, so exactly three instructions to patch here
            pmc.CGFI(r.SCRATCH2, l.imm(frame_depth))
            pmc.BRC(c.EQ, l.imm(jmp_target - (traps_pos + 6)))
            pmc.LGHI(r.r0, l.imm(frame_depth))
            pmc.overwrite()

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
        operations = regalloc.prepare_loop(inputargs, operations,
                                           looptoken, clt.allgcrefs)
        self.pool.pre_assemble(self, operations)
        entrypos = self.mc.get_relative_pos()
        self.mc.LARL(r.POOL, l.halfword(self.pool.pool_start - entrypos))
        self._call_header_with_stack_check()
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
        if not we_are_translated():
            self.mc.trap() # should be never reached
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
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)
        self.pool.pre_assemble(self, operations, bridge=True)
        startpos = self.mc.get_relative_pos()
        self.mc.LARL(r.POOL, l.halfword(self.pool.pool_start - startpos))
        self._check_frame_depth(self.mc, regalloc.get_gcmap())
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        codeendpos = self.mc.get_relative_pos()
        self.pool.post_assemble(self)
        self.write_pending_failure_recoveries()
        fullsize = self.mc.get_relative_pos()
        #
        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
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
            assert isinstance(targettoken, TargetToken)
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

    def propagate_memoryerror_if_r2_is_null(self):
        # if self.propagate_exception_path == 0 (tests), this may jump to 0
        # and segfaults.  too bad.  the alternative is to continue anyway
        # with r2==0, but that will segfault too.
        self.mc.load_imm(r.RETURN, self.propagate_exception_path)
        self.mc.cmp_op(r.r2, l.imm(0), imm=True)
        self.mc.BCR(c.EQ, r.RETURN)

    def regalloc_push(self, loc, already_pushed):
        """Pushes the value stored in loc to the stack
        Can trash the current value of SCRATCH when pushing a stack
        loc"""

        index = WORD * (~already_pushed)

        if loc.type == FLOAT:
            if not loc.is_fp_reg():
                self.regalloc_mov(loc, r.FP_SCRATCH)
                loc = r.FP_SCRATCH
            self.mc.STDY(loc, l.addr(index, r.SP))
        else:
            if not loc.is_core_reg():
                self.regalloc_mov(loc, r.SCRATCH)
                loc = r.SCRATCH
            self.mc.STG(loc, l.addr(index, r.SP))

    def regalloc_pop(self, loc, already_pushed):
        """Pops the value on top of the stack to loc. Can trash the current
        value of SCRATCH when popping to a stack loc"""
        index = WORD * (~already_pushed)

        if loc.type == FLOAT:
            if loc.is_fp_reg():
                self.mc.LDY(loc, l.addr(index, r.SP))
            else:
                self.mc.LDY(r.FP_SCRATCH, l.addr(index, r.SP))
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

    def break_long_loop(self):
        # If the loop is too long, the guards in it will jump forward
        # more than 32 KB.  We use an approximate hack to know if we
        # should break the loop here with an unconditional "b" that
        # jumps over the target code.
        jmp_pos = self.mc.currpos()
        self.mc.reserve_cond_jump()

        self.write_pending_failure_recoveries()

        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(self.mc, jmp_pos, 1)
        pmc.BRCL(c.ANY, l.imm(currpos - jmp_pos))
        pmc.overwrite()

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
                offset = loc.value
                self.mc.load_imm(r.SCRATCH, prev_loc.value)
                self.mc.STG(r.SCRATCH, l.addr(offset, r.SPP))
                return
            assert 0, "not supported location"
        elif prev_loc.is_in_pool():
            if loc.is_reg():
                self.mc.LG(loc, prev_loc)
                return
            elif loc.is_fp_reg():
                self.mc.LDY(loc, prev_loc)
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
                self.mc.load(r.SCRATCH, r.SPP, offset)
                self.mc.store(r.SCRATCH, r.SPP, target_offset)
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
        elif prev_loc.is_in_pool():
            # move immediate value to fp register
            if loc.is_fp_reg():
                self.mc.LD(loc, prev_loc)
                return
            # move immediate value to memory
            elif loc.is_stack():
                offset = loc.value
                self.mc.LD(r.FP_SCRATCH, prev_loc)
                self.mc.STDY(r.FP_SCRATCH, l.addr(offset, r.SPP))
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
                self.mc.STDY(prev_loc, l.addr(offset, r.SPP))
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

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu, allblocks,
                                    self.cpu.gc_ll_descr.gcrootmap)
        return start

    def _reload_frame_if_necessary(self, mc, shadowstack_reg=None):
        # might trash the VOLATILE registers different from r2 and f0
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            if gcrootmap.is_shadow_stack:
                if shadowstack_reg is None:
                    diff = mc.load_imm_plus(r.SPP,
                                            gcrootmap.get_root_stack_top_addr())
                    mc.load(r.SPP, r.SPP, diff)
                    shadowstack_reg = r.SPP
                mc.load(r.SPP, shadowstack_reg, -WORD)
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
        # Build a new stackframe of size STD_FRAME_SIZE_IN_BYTES
        self.mc.STMG(r.r6, r.r15, l.addr(6*WORD, r.SP))
        # save the back chain
        self.mc.STG(r.SP, l.addr(0, r.SP))

        # save r3, the second argument, to THREADLOCAL_ADDR_OFFSET
        self.mc.STG(r.r3, l.addr(THREADLOCAL_ADDR_OFFSET, r.SP))

        # move the first argument to SPP: the jitframe object
        self.mc.LGR(r.SPP, r.r2)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_header_shadowstack(gcrootmap)

    def _call_header_shadowstack(self, gcrootmap):
        # we need to put one word into the shadowstack: the jitframe (SPP)
        # we saved all registers to the stack
        RCS1 = r.r2
        RCS2 = r.r3
        RCS3 = r.r4
        mc = self.mc
        diff = mc.load_imm_plus(RCS1, gcrootmap.get_root_stack_top_addr())
        mc.load(RCS2, RCS1, diff)  # ld RCS2, [rootstacktop]
        #
        mc.LGR(RCS3, RCS2)
        mc.AGHI(RCS3, l.imm(WORD)) # add RCS3, RCS2, WORD
        mc.store(r.SPP, RCS2, 0)   # std SPP, RCS2
        #
        mc.store(RCS3, RCS1, diff) # std RCS3, [rootstacktop]

    def _call_footer_shadowstack(self, gcrootmap):
        # r6 -> r15 can be used freely, they will be restored by 
        # _call_footer after this call
        RCS1 = r.r9
        RCS2 = r.r10
        mc = self.mc
        diff = mc.load_imm_plus(RCS1, gcrootmap.get_root_stack_top_addr())
        mc.load(RCS2, RCS1, diff)    # ld RCS2, [rootstacktop]
        mc.AGHI(RCS2, l.imm(-WORD))  # sub RCS2, RCS2, WORD
        mc.store(RCS2, RCS1, diff)   # std RCS2, [rootstacktop]

    def _call_footer(self):
        # the return value is the jitframe
        self.mc.LGR(r.r2, r.SPP)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._call_footer_shadowstack(gcrootmap)

        # restore registers r6-r15
        self.mc.LMG(r.r6, r.r15, l.addr(6*WORD, r.SP))
        self.jmpto(r.r14)

    def _push_all_regs_to_frame(self, mc, ignored_regs, withfloats, callee_only=False):
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

    def _push_core_regs_to_jitframe(self, mc, includes=r.registers):
        self._multiple_to_or_from_jitframe(mc, includes, store=True)

    @specialize.arg(3)
    def _multiple_to_or_from_jitframe(self, mc, includes, store):
        if len(includes) == 0:
            return
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(includes) == 1:
            iv = includes[0]
            addr = l.addr(base_ofs + iv.value * WORD, r.SPP)
            if store:
                mc.STG(iv, addr)
            else:
                mc.LG(iv, addr)
            return

        val = includes[0].value
        # includes[i => j]
        # for each continous sequence in the registers are stored
        # with STMG instead of STG, in the best case this only leads
        # to 1 instruction to store r.ri -> r.rj (if it is continuous)
        i = 0
        j = 1
        for register in includes[1:]:
            if i >= j:
                j += 1
                continue
            regval = register.value
            if regval != (val+1):
                iv = includes[i]
                diff = (val - iv.value)
                addr = l.addr(base_ofs + iv.value * WORD, r.SPP)
                if diff > 0:
                    if store:
                        mc.STMG(iv, includes[i+diff], addr) 
                    else:
                        mc.LMG(iv, includes[i+diff], addr) 
                    i = j
                else:
                    if store:
                        mc.STG(iv, addr)
                    else:
                        mc.LG(iv, addr)
                    i = j
            val = regval
            j += 1
        if i >= len(includes):
            # all have been stored
            return
        diff = (val - includes[i].value)
        iv = includes[i]
        addr = l.addr(base_ofs + iv.value * WORD, r.SPP)
        if diff > 0:
            if store:
                mc.STMG(iv, includes[-1], addr) 
            else:
                mc.LMG(iv, includes[-1], addr) 
        else:
            if store:
                mc.STG(iv, addr)
            else:
                mc.LG(iv, addr)

    def _pop_core_regs_from_jitframe(self, mc, includes=r.MANAGED_REGS):
        self._multiple_to_or_from_jitframe(mc, includes, store=False)

    def _push_fp_regs_to_jitframe(self, mc, includes=r.fpregisters):
        if len(includes) == 0:
            return
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        v = 16
        for i,reg in enumerate(includes):
            mc.STDY(reg, l.addr(base_ofs + (v+i) * WORD, r.SPP))

    def _pop_fp_regs_from_jitframe(self, mc, includes=r.MANAGED_FP_REGS):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        v = 16
        for reg in includes:
            mc.LD(reg, l.addr(base_ofs + (v+reg.value) * WORD, r.SPP))


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
            offset = self.pool.get_offset(descr) + \
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
                self.mc.STDY(return_val, l.addr(base_ofs, r.SPP))
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

    def _store_and_reset_exception(self, mc, excvalloc, exctploc=None):
        """Reset the exception, after fetching it inside the two regs.
        """
        mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert check_imm_value(diff)
        # Load the exception fields into the two registers
        mc.load(excvalloc, r.SCRATCH, 0)
        if exctploc is not None:
            mc.load(exctploc, r.SCRATCH, diff)
        # Zero out the exception fields
        mc.LGHI(r.SCRATCH2, l.imm(0))
        mc.STG(r.SCRATCH2, l.addr(0, r.SCRATCH))
        mc.STG(r.SCRATCH2, l.addr(diff, r.SCRATCH))

    def _restore_exception(self, mc, excvalloc, exctploc):
        mc.load_imm(r.SCRATCH, self.cpu.pos_exc_value())
        diff = self.cpu.pos_exception() - self.cpu.pos_exc_value()
        assert check_imm_value(diff)
        # Store the exception fields from the two registers
        mc.STG(excvalloc, l.addr(0, r.SCRATCH))
        mc.STG(exctploc, l.addr(diff, r.SCRATCH))

    def load_gcmap(self, mc, reg, gcmap):
        # load the current gcmap into register 'reg'
        ptr = rffi.cast(lltype.Signed, gcmap)
        mc.load_imm(reg, ptr)

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size, gcmap):
        assert size & (WORD-1) == 0     # must be correctly aligned

        # We load into RES the address stored at nursery_free_adr. We
        # calculate the new value for nursery_free_adr and store it in
        # RSZ.  Then we load the address stored in nursery_top_adr
        # into SCRATCH.  In the rare case where the value in RSZ is
        # (unsigned) bigger than the one in SCRATCH we call
        # malloc_slowpath.  In the common case where malloc_slowpath
        # is not called, we must still write RSZ back into
        # nursery_free_adr (r1); so we do it always, even if we called
        # malloc_slowpath.

        diff = nursery_top_adr - nursery_free_adr
        assert check_imm_value(diff)
        mc = self.mc
        mc.load_imm(r.r1, nursery_free_adr)

        mc.load(r.RES, r.r1, 0)          # load nursery_free

        mc.LGR(r.RSZ, r.RES)
        if check_imm_value(size):
            mc.AGHI(r.RSZ, l.imm(size))
        else:
            mc.load_imm(r.SCRATCH2, size)
            mc.AGR(r.RSZ, r.SCRATCH2)

        mc.load(r.SCRATCH2, r.r1, diff)  # load nursery_top
        mc.cmp_op(r.RSZ, r.SCRATCH2, signed=False)

        fast_jmp_pos = mc.currpos()
        mc.reserve_cond_jump(short=True) # conditional jump, patched later


        # new value of nursery_free_adr in RSZ and the adr of the new object
        # in RES.
        self.load_gcmap(mc, r.r1, gcmap)
        # no frame needed, r14 is saved on the jitframe
        mc.branch_absolute(self.malloc_slowpath)

        offset = mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(mc, fast_jmp_pos, 1)
        pmc.BRC(c.LE, l.imm(offset))    # jump if LE (not GT), predicted to be true
        pmc.overwrite()

        mc.STG(r.RSZ, l.addr(0, r.r1))    # store into nursery_free


    def malloc_cond_varsize_frame(self, nursery_free_adr, nursery_top_adr,
                                  sizeloc, gcmap):
        diff = nursery_top_adr - nursery_free_adr
        assert check_imm_value(diff)
        mc = self.mc
        mc.load_imm(r.r1, nursery_free_adr)

        if sizeloc is r.RES:
            mc.LGR(r.RSZ, r.RES)
            sizeloc = r.RSZ

        mc.load(r.RES, r.r1, 0)          # load nursery_free

        mc.LGR(r.SCRATCH2, r.RES)
        mc.AGR(r.SCRATCH2, sizeloc) # sizeloc can be RSZ
        mc.LGR(r.RSZ, r.SCRATCH2)

        mc.load(r.SCRATCH2, r.r1, diff)  # load nursery_top

        mc.cmp_op(r.RSZ, r.SCRATCH2, signed=False)

        fast_jmp_pos = mc.currpos()
        mc.reserve_cond_jump(short=True)        # conditional jump, patched later

        # new value of nursery_free_adr in RSZ and the adr of the new object
        # in RES.
        self.load_gcmap(mc, r.r1, gcmap)
        mc.branch_absolute(self.malloc_slowpath)

        offset = mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(mc, fast_jmp_pos, 1)
        pmc.BRC(c.LE, l.imm(offset))    # jump if LE (not GT), predicted to be true
        pmc.overwrite()

        mc.STG(r.RSZ, l.addr(0, r.r1))    # store into nursery_free

    def malloc_cond_varsize(self, kind, nursery_free_adr, nursery_top_adr,
                            lengthloc, itemsize, maxlength, gcmap,
                            arraydescr):
        from rpython.jit.backend.llsupport.descr import ArrayDescr
        assert isinstance(arraydescr, ArrayDescr)

        # lengthloc is the length of the array, which we must not modify!
        assert lengthloc is not r.RES and lengthloc is not r.RSZ
        assert lengthloc.is_reg()

        if maxlength > 2**16-1:
            maxlength = 2**16-1      # makes things easier
        mc = self.mc
        mc.cmp_op(lengthloc, l.imm(maxlength), imm=True, signed=False)

        jmp_adr0 = mc.currpos()
        mc.reserve_cond_jump(short=True)       # conditional jump, patched later

        # ------------------------------------------------------------
        # block of code for the case: the length is <= maxlength

        diff = nursery_top_adr - nursery_free_adr
        assert check_imm_value(diff)
        mc.load_imm(r.r1, nursery_free_adr)

        # no shifting needed, lengthloc is already multiplied by the
        # item size

        mc.load(r.RES, r.r1, 0)          # load nursery_free

        assert arraydescr.basesize >= self.gc_minimal_size_in_nursery
        constsize = arraydescr.basesize + self.gc_size_of_header
        force_realignment = (itemsize % WORD) != 0
        if force_realignment:
            constsize += WORD - 1
        if lengthloc is not r.RSZ:
            mc.LGR(r.RSZ, lengthloc)
        mc.AGFI(r.RSZ, l.imm(constsize))
        if force_realignment:
            # "& ~(WORD-1)"
            mc.LGHI(r.SCRATCH2, l.imm(~(WORD-1)))
            mc.NGR(r.RSZ, r.SCRATCH2)

        mc.AGR(r.RSZ, r.RES)
        # now RSZ contains the total size in bytes, rounded up to a multiple
        # of WORD, plus nursery_free_adr

        mc.load(r.SCRATCH2, r.r1, diff)  # load nursery_top
        mc.cmp_op(r.RSZ, r.SCRATCH2, signed=False)

        jmp_adr1 = mc.currpos()
        mc.reserve_cond_jump(short=True) # conditional jump, patched later

        # ------------------------------------------------------------
        # block of code for two cases: either the length is > maxlength
        # (jump from jmp_adr0), or the length is small enough but there
        # is not enough space in the nursery (fall-through)
        #
        offset = mc.currpos() - jmp_adr0
        pmc = OverwritingBuilder(mc, jmp_adr0, 1)
        pmc.BRC(c.GT, l.imm(offset))    # jump if GT
        pmc.overwrite()
        #
        # save the gcmap
        self.load_gcmap(mc, r.r1, gcmap)
        #
        # load the argument(s)
        if kind == rewrite.FLAG_ARRAY:
            mc.LGR(r.RSZ, lengthloc)
            mc.load_imm(r.RES, itemsize)
            mc.load_imm(r.SCRATCH2, arraydescr.tid)
        else:
            mc.LGR(r.RES, lengthloc)
        #
        # load the function into r14 and jump
        if kind == rewrite.FLAG_ARRAY:
            addr = self.malloc_slowpath_varsize
        elif kind == rewrite.FLAG_STR:
            addr = self.malloc_slowpath_str
        elif kind == rewrite.FLAG_UNICODE:
            addr = self.malloc_slowpath_unicode
        else:
            raise AssertionError(kind)
        #
        # call!
        mc.push_std_frame()
        mc.branch_absolute(addr)
        mc.pop_std_frame()

        jmp_location = mc.currpos()
        mc.reserve_cond_jump(short=True)      # jump forward, patched later

        # ------------------------------------------------------------
        # block of code for the common case: the length is <= maxlength
        # and there is enough space in the nursery

        offset = mc.currpos() - jmp_adr1
        pmc = OverwritingBuilder(mc, jmp_adr1, 1)
        pmc.BRC(c.LE, l.imm(offset))    # jump if LE
        pmc.overwrite()
        #
        # write down the tid, but only in this case (not in other cases
        # where r.RES is the result of the CALL)
        mc.load_imm(r.SCRATCH2, arraydescr.tid)
        mc.STG(r.SCRATCH2, l.addr(0, r.RES))
        # while we're at it, this line is not needed if we've done the CALL
        mc.STG(r.RSZ, l.addr(0, r.r1))    # store into nursery_free

        # ------------------------------------------------------------
        offset = mc.currpos() - jmp_location
        pmc = OverwritingBuilder(mc, jmp_location, 1)
        pmc.BRC(c.ANY, l.imm(offset))    # jump always
        pmc.overwrite()

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
