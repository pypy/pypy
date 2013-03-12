from __future__ import with_statement
import os
from rpython.jit.backend.llsupport import jitframe
from rpython.jit.backend.arm.helper.assembler import saved_registers
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.arm import registers as r
from rpython.jit.backend.arm.arch import WORD, DOUBLE_WORD, FUNC_ALIGN, \
                                    N_REGISTERS_SAVED_BY_MALLOC, \
                                    JITFRAME_FIXED_SIZE
from rpython.jit.backend.arm.codebuilder import ARMv7Builder, OverwritingBuilder
from rpython.jit.backend.arm.locations import get_fp_offset, imm, StackLocation
from rpython.jit.backend.arm.regalloc import (Regalloc, ARMFrameManager,
                    CoreRegisterManager, check_imm_arg,
                    VFPRegisterManager,
                    operations as regalloc_operations,
                    operations_with_guard as regalloc_operations_with_guard)
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.codewriter import longlong
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import AbstractFailDescr, INT, REF, FLOAT
from rpython.jit.metainterp.history import BoxInt, ConstInt
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib import rgc
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.annlowlevel import llhelper, cast_instance_to_gcref
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.backend.arm.opassembler import ResOpAssembler
from rpython.rlib.debug import (debug_print, debug_start, debug_stop,
                             have_debug_prints, fatalerror)
from rpython.rlib.jit import AsmInfo
from rpython.rlib.objectmodel import compute_unique_id
from rpython.rlib.rarithmetic import intmask, r_uint


DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER', ('i', lltype.Signed),
                              ('type', lltype.Char),  # 'b'ridge, 'l'abel or
                                                      # 'e'ntry point
                              ('number', lltype.Signed))


class AssemblerARM(ResOpAssembler):

    debug = False

    def __init__(self, cpu, translate_support_code=False):
        ResOpAssembler.__init__(self, cpu, translate_support_code)
        self.setup_failure_recovery()
        self.mc = None
        self.pending_guards = None
        self._exit_code_addr = 0
        self.current_clt = None
        self.malloc_slowpath = 0
        self.wb_slowpath = [0, 0, 0, 0]
        self._regalloc = None
        self.datablockwrapper = None
        self.propagate_exception_path = 0
        self.stack_check_slowpath = 0
        self._debug = False
        self.loop_run_counters = []
        self.debug_counter_descr = cpu.fielddescrof(DEBUG_COUNTER, 'i')
        self.gcrootmap_retaddr_forced = 0

    def set_debug(self, v):
        r = self._debug
        self._debug = v
        return r

    def setup(self, looptoken):
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        if we_are_translated():
            self.debug = False
        self.current_clt = looptoken.compiled_loop_token
        self.mc = ARMv7Builder()
        self.pending_guards = []
        assert self.datablockwrapper is None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.target_tokens_currently_compiling = {}

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None
        assert self.datablockwrapper is None

    def setup_failure_recovery(self):
        self.failure_recovery_code = [0, 0, 0, 0]

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

    # XXX: merge with x86
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
            # before doing anything, let's increase a counter
            s = 0
            for op in operations:
                s += op.getopnum()
            looptoken._arm_debug_checksum = s

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

    @staticmethod
    def _release_gil_shadowstack():
        before = rffi.aroundstate.before
        if before:
            before()

    @staticmethod
    def _reacquire_gil_shadowstack():
        after = rffi.aroundstate.after
        if after:
            after()

    _NOARG_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))

    def _build_release_gil(self, gcrootmap):
        assert gcrootmap.is_shadow_stack
        releasegil_func = llhelper(self._NOARG_FUNC,
                                   self._release_gil_shadowstack)
        reacqgil_func = llhelper(self._NOARG_FUNC,
                                 self._reacquire_gil_shadowstack)
        self.releasegil_addr = rffi.cast(lltype.Signed, releasegil_func)
        self.reacqgil_addr = rffi.cast(lltype.Signed, reacqgil_func)

    def _build_propagate_exception_path(self):
        if not self.cpu.propagate_exception_descr:
            return      # not supported (for tests, or non-translated)
        #
        #
        mc = ARMv7Builder()
        self._store_and_reset_exception(mc, r.r0)
        ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
        # make sure ofs fits into a register
        assert check_imm_arg(ofs)
        mc.LDR_ri(r.r0.value, r.fp.value, imm=ofs)
        propagate_exception_descr = rffi.cast(lltype.Signed,
                  cast_instance_to_gcref(self.cpu.propagate_exception_descr))
        # put propagate_exception_descr into frame
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        # make sure ofs fits into a register
        assert check_imm_arg(ofs)
        mc.gen_load_int(r.r0.value, propagate_exception_descr)
        mc.STR_ri(r.r0.value, r.fp.value, imm=ofs)
        mc.MOV_rr(r.r0.value, r.fp.value)
        self.gen_func_epilog(mc)
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.propagate_exception_path = rawstart

    def _store_and_reset_exception(self, mc, excvalloc=None, exctploc=None,
                                                                on_frame=False):
        """ Resest the exception. If excvalloc is None, then store it on the
        frame in jf_guard_exc
        """
        assert excvalloc is not r.ip
        assert exctploc is not r.ip
        tmpreg = r.lr
        mc.gen_load_int(r.ip.value, self.cpu.pos_exc_value())
        if excvalloc is not None: # store
            assert excvalloc.is_reg()
            self.load_reg(mc, excvalloc, r.ip)
        if on_frame:
            # store exc_value in JITFRAME
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            assert check_imm_arg(ofs)
            self.store_reg(mc, r.ip, r.fp, ofs)
        if exctploc is not None:
            # store pos_exception in exctploc
            assert exctploc.is_reg()
            mc.gen_load_int(r.ip.value, self.cpu.pos_exception())
            self.load_reg(mc, exctploc, r.ip)

        # reset exception
        mc.gen_load_int(tmpreg.value, 0)

        self.store_reg(mc, tmpreg, r.ip, 0)

        mc.gen_load_int(r.ip.value, self.cpu.pos_exception())
        self.store_reg(mc, tmpreg, r.ip, 0)

    def _restore_exception(self, mc, excvalloc, exctploc):
        assert excvalloc is not r.ip
        assert exctploc is not r.ip
        tmpreg = r.lr # use lr as a second temporary reg
        mc.gen_load_int(r.ip.value, self.cpu.pos_exc_value())
        if excvalloc is not None:
            assert excvalloc.is_reg()
            self.store_reg(mc, excvalloc, r.ip)
        else:
            assert exctploc is not r.fp
            # load exc_value from JITFRAME and put it in pos_exc_value
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            self.load_reg(mc, tmpreg, r.fp, ofs)
            self.store_reg(mc, tmpreg, r.ip)
            # reset exc_value in the JITFRAME
            mc.gen_load_int(tmpreg.value, 0)
            self.store_reg(mc, tmpreg, r.fp, ofs)

        # restore pos_exception from exctploc register
        mc.gen_load_int(r.ip.value, self.cpu.pos_exception())
        self.store_reg(mc, exctploc, r.ip)

    def _build_stack_check_slowpath(self):
        _, _, slowpathaddr = self.cpu.insert_stack_check()
        if slowpathaddr == 0 or not self.cpu.propagate_exception_descr:
            return      # no stack check (for tests, or non-translated)
        #
        # make a "function" that is called immediately at the start of
        # an assembler function.  In particular, the stack looks like:
        #
        #    |  retaddr of caller    |   <-- aligned to a multiple of 16
        #    |  saved argument regs  |
        #    |  my own retaddr       |    <-- sp
        #    +-----------------------+
        #
        mc = ARMv7Builder()
        # save argument registers and return address
        mc.PUSH([reg.value for reg in r.argument_regs] + [r.lr.value])
        # stack is aligned here
        # Pass current stack pointer as argument to the call
        mc.MOV_rr(r.r0.value, r.sp.value)
        #
        mc.BL(slowpathaddr)

        # check for an exception
        mc.gen_load_int(r.r0.value, self.cpu.pos_exception())
        mc.LDR_ri(r.r0.value, r.r0.value)
        mc.TST_rr(r.r0.value, r.r0.value)
        # restore registers and return 
        # We check for c.EQ here, meaning all bits zero in this case
        mc.POP([reg.value for reg in r.argument_regs] + [r.pc.value], cond=c.EQ)
        #
        # Call the helper, which will return a dead frame object with
        # the correct exception set, or MemoryError by default
        addr = rffi.cast(lltype.Signed, self.cpu.get_propagate_exception())
        mc.BL(addr)
        #
        # footer -- note the ADD, which skips the return address of this
        # function, and will instead return to the caller's caller.  Note
        # also that we completely ignore the saved arguments, because we
        # are interrupting the function.
        mc.ADD_ri(r.sp.value, r.sp.value, (len(r.argument_regs) + 1) * WORD)
        mc.POP([r.pc.value])
        #
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.stack_check_slowpath = rawstart

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
        # all vfp registers.  It takes a single argument which is in r0.
        # It must keep stack alignment accordingly.
        mc = ARMv7Builder()
        #
        exc0 = exc1 = None
        mc.PUSH([r.ip.value, r.lr.value]) # push two words to keep alignment
        if not for_frame:
            self._push_all_regs_to_jitframe(mc, [], withfloats, callee_only=True)
        else:
            # we're possibly called from the slowpath of malloc
            # save the caller saved registers
            # assuming we do not collect here
            exc0, exc1 = r.r4, r.r5
            mc.PUSH([gpr.value for gpr in r.caller_resp] + [exc0.value, exc1.value])
            mc.VPUSH([vfpr.value for vfpr in r.caller_vfp_resp])

            self._store_and_reset_exception(mc, exc0, exc1)
        mc.BL(func)
        #
        if not for_frame:
            self._pop_all_regs_from_jitframe(mc, [], withfloats, callee_only=True)
        else:
            self._restore_exception(mc, exc0, exc1)
            mc.VPOP([vfpr.value for vfpr in r.caller_vfp_resp])
            mc.POP([gpr.value for gpr in r.caller_resp] +
                            [exc0.value, exc1.value])
        #
        if withcards:
            # A final TEST8 before the RET, for the caller.  Careful to
            # not follow this instruction with another one that changes
            # the status of the CPU flags!
            mc.LDRB_ri(r.ip.value, r.r0.value,
                                    imm=descr.jit_wb_if_flag_byteofs)
            mc.TST_ri(r.ip.value, imm=0x80)
        #
        mc.POP([r.ip.value, r.pc.value])
        #
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    def _build_malloc_slowpath(self):
        mc = ARMv7Builder()
        if self.cpu.supports_floats:
            vfp_regs = r.all_vfp_regs
        else:
            vfp_regs = []
        # We need to push two registers here because we are going to make a
        # call an therefore the stack needs to be 8-byte aligned
        mc.PUSH([r.ip.value, r.lr.value])
        with saved_registers(mc, [], vfp_regs):
            # At this point we know that the values we need to compute the size
            # are stored in r0 and r1.
            mc.SUB_rr(r.r0.value, r.r1.value, r.r0.value)
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
            for reg, ofs in CoreRegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
                mc.STR_ri(reg.value, r.fp.value, imm=ofs)
            mc.BL(addr)
            for reg, ofs in CoreRegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
                mc.LDR_ri(reg.value, r.fp.value, imm=ofs)

        mc.CMP_ri(r.r0.value, 0)
        mc.B(self.propagate_exception_path, c=c.EQ)
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.gen_load_int(r.r1.value, nursery_free_adr)
        mc.LDR_ri(r.r1.value, r.r1.value)
        # see above
        mc.POP([r.ip.value, r.pc.value])

        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.malloc_slowpath = rawstart

    def propagate_memoryerror_if_r0_is_null(self):
        # see ../x86/assembler.py:propagate_memoryerror_if_eax_is_null
        self.mc.CMP_ri(r.r0.value, 0)
        self.mc.B(self.propagate_exception_path, c=c.EQ)

    def _push_all_regs_to_jitframe(self, mc, ignored_regs, withfloats,
                                callee_only=False):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = CoreRegisterManager.save_around_call_regs
        else:
            regs = CoreRegisterManager.all_regs
        # XXX use STMDB ops here
        for i, gpr in enumerate(regs):
            if gpr in ignored_regs:
                continue
            self.store_reg(mc, gpr, r.fp, base_ofs + i * WORD)
        if withfloats:
            if callee_only:
                regs = VFPRegisterManager.save_around_call_regs
            else:
                regs = VFPRegisterManager.all_regs
            for i, vfpr in enumerate(regs):
                if vfpr in ignored_regs:
                    continue
                ofs = len(CoreRegisterManager.all_regs) * WORD
                ofs += i * DOUBLE_WORD + base_ofs
                self.store_reg(mc, vfpr, r.fp, ofs)

    def _pop_all_regs_from_jitframe(self, mc, ignored_regs, withfloats,
                                 callee_only=False):
        # Pop all general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = CoreRegisterManager.save_around_call_regs
        else:
            regs = CoreRegisterManager.all_regs
        # XXX use LDMDB ops here
        for i, gpr in enumerate(regs):
            if gpr in ignored_regs:
                continue
            ofs = i * WORD + base_ofs
            self.load_reg(mc, gpr, r.fp, ofs)
        if withfloats:
            # Pop all XMM regs
            if callee_only:
                regs = VFPRegisterManager.save_around_call_regs
            else:
                regs = VFPRegisterManager.all_regs
            for i, vfpr in enumerate(regs):
                if vfpr in ignored_regs:
                    continue
                ofs = len(CoreRegisterManager.all_regs) * WORD
                ofs += i * DOUBLE_WORD + base_ofs
                self.load_reg(mc, vfpr, r.fp, ofs)

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = ARMv7Builder()
        self._push_all_regs_to_jitframe(mc, [], withfloats)

        if exc:
            # We might have an exception pending.  Load it into r4
            # (this is a register saved across calls)
            mc.gen_load_int(r.r5.value, self.cpu.pos_exc_value())
            mc.LDR_ri(r.r4.value, r.r5.value)
            # clear the exc flags
            mc.gen_load_int(r.r6.value, 0)
            mc.STR_ri(r.r6.value, r.r5.value) # pos_exc_value is still in r5
            mc.gen_load_int(r.r5.value, self.cpu.pos_exception())
            mc.STR_ri(r.r6.value, r.r5.value)
            # save r4 into 'jf_guard_exc'
            offset = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            assert check_imm_arg(abs(offset))
            mc.STR_ri(r.r4.value, r.fp.value, imm=offset)
        # now we return from the complete frame, which starts from
        # _call_header_with_stack_check().  The LEA in _call_footer below
        # throws away most of the frame, including all the PUSHes that we
        # did just above.
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        assert check_imm_arg(abs(ofs))
        ofs2 = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        assert check_imm_arg(abs(ofs2))
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        # store the gcmap
        mc.POP([r.ip.value])
        mc.STR_ri(r.ip.value, r.fp.value, imm=ofs2)
        # store the descr
        mc.POP([r.ip.value])
        mc.STR_ri(r.ip.value, r.fp.value, imm=ofs)

        # set return value
        assert check_imm_arg(base_ofs)
        mc.MOV_rr(r.r0.value, r.fp.value)
        #
        self.gen_func_epilog(mc)
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.currpos()
        fail_descr, target = self.store_info_on_descr(startpos, guardtok)
        self.regalloc_push(imm(fail_descr))
        self.push_gcmap(self.mc, gcmap=guardtok.gcmap, push=True)
        self.mc.BL(target)
        return startpos

    def align(self):
        while(self.mc.currpos() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    def gen_func_epilog(self, mc=None, cond=c.AL):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if mc is None:
            mc = self.mc
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_footer_shadowstack(gcrootmap, mc)
        if self.cpu.supports_floats:
            mc.VPOP([reg.value for reg in r.callee_saved_vfp_registers],
                                                                    cond=cond)
        # push all callee saved registers and IP to keep the alignment
        mc.POP([reg.value for reg in r.callee_restored_registers] +
                                                       [r.ip.value], cond=cond)
        mc.BKPT()

    def gen_func_prolog(self):
        stack_size = WORD #alignment
        stack_size += len(r.callee_saved_registers) * WORD
        if self.cpu.supports_floats:
            stack_size += len(r.callee_saved_vfp_registers) * 2 * WORD

        # push all callee saved registers and IP to keep the alignment
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers] +
                                                        [r.ip.value])
        if self.cpu.supports_floats:
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
        assert stack_size % 8 == 0 # ensure we keep alignment

        # set fp to point to the JITFRAME
        self.mc.MOV_rr(r.fp.value, r.r0.value)
        #
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)

    def gen_shadowstack_header(self, gcrootmap):
        # we need to put two words into the shadowstack: the MARKER_FRAME
        # and the address of the frame (fp, actually)
        rst = gcrootmap.get_root_stack_top_addr()
        self.mc.gen_load_int(r.ip.value, rst)
        self.mc.LDR_ri(r.r4.value, r.ip.value)  # LDR r4, [rootstacktop]
        #
        MARKER = gcrootmap.MARKER_FRAME
        self.mc.ADD_ri(r.r5.value, r.r4.value,
                                    imm=2 * WORD)  # ADD r5, r4 [2*WORD]
        self.mc.gen_load_int(r.r6.value, MARKER)
        self.mc.STR_ri(r.r6.value, r.r4.value, WORD)  # STR MARKER, r4 [WORD]
        self.mc.STR_ri(r.fp.value, r.r4.value)  # STR fp, r4
        #
        self.mc.STR_ri(r.r5.value, r.ip.value)  # STR r5 [rootstacktop]

    def gen_footer_shadowstack(self, gcrootmap, mc):
        rst = gcrootmap.get_root_stack_top_addr()
        mc.gen_load_int(r.ip.value, rst)
        mc.LDR_ri(r.r4.value, r.ip.value)  # LDR r4, [rootstacktop]
        mc.SUB_ri(r.r5.value, r.r4.value, imm=2 * WORD)  # ADD r5, r4 [2*WORD]
        mc.STR_ri(r.r5.value, r.ip.value)

    def _dump(self, ops, type='loop'):
        debug_start('jit-backend-ops')
        debug_print(type)
        for op in ops:
            debug_print(op.repr())
        debug_stop('jit-backend-ops')

    def _call_header(self):
        self.align()
        self.gen_func_prolog()

    def _call_header_with_stack_check(self):
        if self.stack_check_slowpath == 0:
            pass                # no stack check (e.g. not translated)
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
            self.mc.PUSH([r.lr.value])
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
            #
            self.mc.POP([r.lr.value])
        self._call_header()

    # cpu interface
    def assemble_loop(self, loopname, inputargs, operations, looptoken, log):
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

        if False and log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        self._call_header_with_stack_check()

        regalloc = Regalloc(assembler=self)
        operations = regalloc.prepare_loop(inputargs, operations, looptoken,
                                           clt.allgcrefs)

        loop_head = self.mc.get_relative_pos()
        looptoken._ll_loop_code = loop_head
        #
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)
        self.update_frame_depth(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        #
        size_excluding_failure_stuff = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        rawstart = self.materialize_loop(looptoken)
        looptoken._function_addr = looptoken._ll_function_addr = rawstart

        self.process_pending_guards(rawstart)
        self.fixup_target_tokens(rawstart)

        if log and not we_are_translated():
            self.mc._dump_trace(rawstart,
                    'loop.asm')

        ops_offset = self.mc.ops_offset
        self.teardown()

        debug_start("jit-backend-addr")
        debug_print("Loop %d (%s) has address 0x%x to 0x%x (bootstrap 0x%x)" % (
            looptoken.number, loopname,
            r_uint(rawstart + loop_head),
            r_uint(rawstart + size_excluding_failure_stuff),
            r_uint(rawstart)))
        debug_stop("jit-backend-addr")

        return AsmInfo(ops_offset, rawstart + loop_head,
                       size_excluding_failure_stuff - loop_head)

    def _assemble(self, regalloc, inputargs, operations):
        regalloc.compute_hint_frame_locations(operations)
        self._walk_operations(inputargs, operations, regalloc)
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._arm_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

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

        assert isinstance(faildescr, AbstractFailDescr)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)

        regalloc = Regalloc(assembler=self)
        startpos = self.mc.get_relative_pos()
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             self.current_clt.allgcrefs,
                                             self.current_clt.frame_info)

        stack_check_patch_ofs = self._check_frame_depth(self.mc,
                                                       regalloc.get_gcmap())

        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)

        codeendpos = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        rawstart = self.materialize_loop(original_loop_token)

        self.process_pending_guards(rawstart)

        # patch the jump from original guard
        self.patch_trace(faildescr, original_loop_token,
                                    rawstart, regalloc)

        if not we_are_translated():
            if log:
                self.mc._dump_trace(rawstart, 'bridge.asm')

        ops_offset = self.mc.ops_offset
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        self.fixup_target_tokens(rawstart)
        self._patch_stackadjust(stack_check_patch_ofs + rawstart, frame_depth)
        self.update_frame_depth(frame_depth)
        self.teardown()

        debug_start("jit-backend-addr")
        debug_print("bridge out of Guard %d has address 0x%x to 0x%x" %
                    (descr_number, r_uint(rawstart),
                     r_uint(rawstart + codeendpos)))
        debug_stop("jit-backend-addr")

        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def new_stack_loc(self, i, pos, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return StackLocation(i, pos + base_ofs, tp)

    def check_frame_before_jump(self, target_token):
        if target_token in self.target_tokens_currently_compiling:
            return
        if target_token._arm_clt is self.current_clt:
            return
        # We can have a frame coming from god knows where that's
        # passed to a jump to another loop. Make sure it has the
        # correct depth
        expected_size = target_token._arm_clt.frame_info.jfi_frame_depth
        self._check_frame_depth(self.mc, self._regalloc.get_gcmap(),
                                expected_size=expected_size)


    def _check_frame_depth(self, mc, gcmap, expected_size=-1):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        There are other potential solutions
        to that, but this one does not sound too bad.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.LDR_ri(r.ip.value, r.fp.value, imm=ofs)
        stack_check_cmp_ofs = mc.currpos()
        if expected_size == -1:
            mc.NOP()
            mc.NOP()
        else:
            mc.gen_load_int(r.lr.value, expected_size)
        mc.CMP_rr(r.ip.value, r.lr.value)

        jg_location = mc.currpos()
        mc.BKPT()

        # the size value is still stored in lr
        mc.PUSH([r.lr.value])

        self.push_gcmap(mc, gcmap, push=True)

        self.mc.BL(self._frame_realloc_slowpath)

        # patch jg_location above
        currpos = self.mc.currpos()
        pmc = OverwritingBuilder(mc, jg_location, WORD)
        pmc.B_offs(currpos, c.GE)

        return stack_check_cmp_ofs

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
        mc = ARMv7Builder()
        self._push_all_regs_to_jitframe(mc, [], self.cpu.supports_floats)
        # this is the gcmap stored by push_gcmap(mov=True) in _check_stack_frame
        # and the expected_size pushed in _check_stack_frame
        # pop the values passed on the stack, gcmap -> r0, expected_size -> r1
        mc.POP([r.r0.value, r.r1.value])
        # store return address and keep the stack aligned
        mc.PUSH([r.ip.value, r.lr.value])

        # store the current gcmap(r0) in the jitframe
        gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        assert check_imm_arg(abs(gcmap_ofs))
        mc.STR_ri(r.r0.value, r.fp.value, imm=gcmap_ofs)

        # set first arg, which is the old jitframe address
        mc.MOV_rr(r.r0.value, r.fp.value)

        # store a possibly present exception
        # we use a callee saved reg here as a tmp for the exc.
        self._store_and_reset_exception(mc, None, r.r4, on_frame=True)

        # call realloc_frame, it takes two arguments
        # arg0: the old jitframe
        # arg1: the new size
        #
        mc.BL(self.cpu.realloc_frame)

        # set fp to the new jitframe returned from the previous call
        mc.MOV_rr(r.fp.value, r.r0.value)

        # restore a possibly present exception
        self._restore_exception(mc, None, r.r4)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._load_shadowstack_top(mc, r.r5, gcrootmap)
            # store the new jitframe addr in the shadowstack
            mc.STR_ri(r.r0.value, r.r5.value, imm=-WORD)

        # reset the jf_gcmap field in the jitframe
        mc.gen_load_int(r.ip.value, 0)
        mc.STR_ri(r.ip.value, r.fp.value, imm=gcmap_ofs)

        # restore registers
        self._pop_all_regs_from_jitframe(mc, [], self.cpu.supports_floats)
        mc.POP([r.ip.value, r.pc.value]) # return
        self._frame_realloc_slowpath = mc.materialize(self.cpu.asmmemmgr, [])

    def _load_shadowstack_top(self, mc, reg, gcrootmap):
        rst = gcrootmap.get_root_stack_top_addr()
        self.mc.gen_load_int(reg.value, rst)
        self.mc.gen_load_int(reg.value, reg.value)
        return rst

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ll_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def _patch_stackadjust(self, adr, allocated_depth):
        mc = ARMv7Builder()
        mc.gen_load_int(r.lr.value, allocated_depth)
        mc.copy_to_raw_memory(adr)

    def target_arglocs(self, loop_token):
        return loop_token._arm_arglocs

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        return self.mc.materialize(self.cpu.asmmemmgr, allblocks,
                                   self.cpu.gc_ll_descr.gcrootmap)

    def update_frame_depth(self, frame_depth):
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guards:
            #generate the exit stub and the encoded representation
            tok.pos_recovery_stub = self.generate_quick_failure(tok)

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.faildescr
            assert isinstance(descr, AbstractFailDescr)
            failure_recovery_pos = block_start + tok.pos_recovery_stub
            descr._arm_failure_recovery_block = failure_recovery_pos
            relative_offset = tok.pos_recovery_stub - tok.offset
            guard_pos = block_start + tok.offset
            if not tok.is_guard_not_invalidated:
                # patch the guard jumpt to the stub
                # overwrite the generate NOP with a B_offs to the pos of the
                # stub
                mc = ARMv7Builder()
                mc.B_offs(relative_offset, c.get_opposite_of(tok.fcond))
                mc.copy_to_raw_memory(guard_pos)
            else:
                clt.invalidate_positions.append((guard_pos, relative_offset))

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def _walk_operations(self, inputargs, operations, regalloc):
        fcond = c.AL
        self._regalloc = regalloc
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            i = regalloc.position()
            op = operations[i]
            self.mc.mark_op(op)
            opnum = op.getopnum()
            if op.has_no_side_effect() and op.result not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            elif self._regalloc.can_merge_with_next_guard(op, i, operations):
                guard = operations[i + 1]
                assert guard.is_guard()
                arglocs = regalloc_operations_with_guard[opnum](regalloc, op,
                                        guard, fcond)
                fcond = asm_operations_with_guard[opnum](self, op,
                                        guard, arglocs, regalloc, fcond)
                regalloc.next_instruction()
                regalloc.possibly_free_vars_for_op(guard)
                regalloc.possibly_free_vars(guard.getfailargs())
            elif not we_are_translated() and op.getopnum() == -124:
                regalloc.prepare_force_spill(op, fcond)
            else:
                arglocs = regalloc_operations[opnum](regalloc, op, fcond)
                if arglocs is not None:
                    fcond = asm_operations[opnum](self, op, arglocs,
                                                        regalloc, fcond)
            if op.is_guard():
                regalloc.possibly_free_vars(op.getfailargs())
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc.free_temp_vars()
            regalloc._check_invariants()
        self.mc.mark_op(None)  # end of the loop

    def regalloc_emit_llong(self, op, arglocs, fcond, regalloc):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        asm_llong_operations[oopspecindex](self, op, arglocs, regalloc, fcond)
        return fcond 

    def regalloc_emit_math(self, op, arglocs, fcond, regalloc):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        asm_math_operations[oopspecindex](self, op, arglocs, regalloc, fcond)
        return fcond

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

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        b = ARMv7Builder()
        patch_addr = faildescr._arm_failure_recovery_block
        assert patch_addr != 0
        b.B(bridge_addr)
        b.copy_to_raw_memory(patch_addr)
        faildescr._arm_failure_recovery_block = 0

    # regalloc support
    def load(self, loc, value):
        """load an immediate value into a register"""
        assert (loc.is_reg() and value.is_imm()
                    or loc.is_vfp_reg() and value.is_imm_float())
        if value.is_imm():
            self.mc.gen_load_int(loc.value, value.getint())
        elif value.is_imm_float():
            self.mc.gen_load_int(r.ip.value, value.getint())
            self.mc.VLDR(loc.value, r.ip.value)

    def load_reg(self, mc, target, base, ofs=0, cond=c.AL, helper=r.ip):
        if target.is_vfp_reg():
            return self._load_vfp_reg(mc, target, base, ofs, cond, helper)
        elif target.is_reg():
            return self._load_core_reg(mc, target, base, ofs, cond, helper)

    def _load_vfp_reg(self, mc, target, base, ofs, cond=c.AL, helper=r.ip):
        if check_imm_arg(ofs):
            mc.VLDR(target.value, base.value, imm=ofs, cond=cond)
        else:
            mc.gen_load_int(helper.value, ofs, cond=cond)
            mc.ADD_rr(helper.value, base.value, helper.value, cond=cond)
            mc.VLDR(target.value, helper.value, cond=cond)

    def _load_core_reg(self, mc, target, base, ofs, cond=c.AL, helper=r.ip):
        if check_imm_arg(ofs):
            mc.LDR_ri(target.value, base.value, imm=ofs, cond=cond)
        else:
            mc.gen_load_int(helper.value, ofs, cond=cond)
            mc.LDR_rr(target.value, base.value, helper.value, cond=cond)

    def store_reg(self, mc, source, base, ofs=0, cond=c.AL, helper=r.ip):
        if source.is_vfp_reg():
            return self._store_vfp_reg(mc, source, base, ofs, cond, helper)
        else:
            return self._store_core_reg(mc, source, base, ofs, cond, helper)

    def _store_vfp_reg(self, mc, source, base, ofs, cond=c.AL, helper=r.ip):
        if check_imm_arg(ofs):
            mc.VSTR(source.value, base.value, imm=ofs, cond=cond)
        else:
            mc.gen_load_int(helper.value, ofs, cond=cond)
            mc.ADD_rr(helper.value, base.value, helper.value, cond=cond)
            mc.VSTR(source.value, helper.value, cond=cond)

    def _store_core_reg(self, mc, source, base, ofs, cond=c.AL, helper=r.ip):
        if check_imm_arg(ofs):
            mc.STR_ri(source.value, base.value, imm=ofs, cond=cond)
        else:
            mc.gen_load_int(helper.value, ofs, cond=cond)
            mc.STR_rr(source.value, base.value, helper.value, cond=cond)

    def _mov_imm_to_loc(self, prev_loc, loc, cond=c.AL):
        if not loc.is_reg() and not (loc.is_stack() and loc.type != FLOAT):
            raise AssertionError("invalid target for move from imm value")
        if loc.is_reg():
            new_loc = loc
        elif loc.is_stack():
            self.mc.PUSH([r.lr.value], cond=cond)
            new_loc = r.lr
        else:
            raise AssertionError("invalid target for move from imm value")
        self.mc.gen_load_int(new_loc.value, prev_loc.value, cond=cond)
        if loc.is_stack():
            self.regalloc_mov(new_loc, loc)
            self.mc.POP([r.lr.value], cond=cond)

    def _mov_reg_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_imm():
            raise AssertionError("mov reg to imm doesn't make sense")
        if loc.is_reg():
            self.mc.MOV_rr(loc.value, prev_loc.value, cond=cond)
        elif loc.is_stack() and loc.type != FLOAT:
            # spill a core register
            if prev_loc is r.ip:
                temp = r.lr
            else:
                temp = r.ip
            offset = loc.value
            is_imm = check_imm_arg(offset, size=0xFFF)
            if not is_imm:
                self.mc.PUSH([temp.value], cond=cond)
            self.store_reg(self.mc, prev_loc, r.fp, offset, helper=temp, cond=cond)
            if not is_imm:
                self.mc.POP([temp.value], cond=cond)
        else:
            assert 0, 'unsupported case'

    def _mov_stack_to_loc(self, prev_loc, loc, cond=c.AL):
        pushed = False
        if loc.is_reg():
            assert prev_loc.type != FLOAT, 'trying to load from an \
                incompatible location into a core register'
            assert loc is not r.lr, 'lr is not supported as a target \
                when moving from the stack'
            # unspill a core register
            offset = prev_loc.value
            is_imm = check_imm_arg(offset, size=0xFFF)
            if not is_imm:
                self.mc.PUSH([r.lr.value], cond=cond)
            self.load_reg(self.mc, loc, r.fp, offset, cond=cond, helper=r.lr)
            if not is_imm:
                self.mc.POP([r.lr.value], cond=cond)
        elif loc.is_vfp_reg():
            assert prev_loc.type == FLOAT, 'trying to load from an \
                incompatible location into a float register'
            # load spilled value into vfp reg
            offset = prev_loc.value
            is_imm = check_imm_arg(offset)
            if not is_imm:
                self.mc.PUSH([r.ip.value], cond=cond)
            self.load_reg(self.mc, loc, r.fp, offset, cond=cond, helper=r.ip)
            if not is_imm:
                self.mc.POP([r.ip.value], cond=cond)
        else:
            assert 0, 'unsupported case'

    def _mov_imm_float_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_vfp_reg():
            self.mc.PUSH([r.ip.value], cond=cond)
            self.mc.gen_load_int(r.ip.value, prev_loc.getint(), cond=cond)
            self.load_reg(self.mc, loc, r.ip, 0, cond=cond)
            self.mc.POP([r.ip.value], cond=cond)
        elif loc.is_stack():
            self.regalloc_push(r.vfp_ip)
            self.regalloc_mov(prev_loc, r.vfp_ip, cond)
            self.regalloc_mov(r.vfp_ip, loc, cond)
            self.regalloc_pop(r.vfp_ip)
        else:
            assert 0, 'unsupported case'

    def _mov_vfp_reg_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_vfp_reg():
            self.mc.VMOV_cc(loc.value, prev_loc.value, cond=cond)
        elif loc.is_stack():
            assert loc.type == FLOAT, 'trying to store to an \
                incompatible location from a float register'
            # spill vfp register
            offset = loc.value
            is_imm = check_imm_arg(offset)
            if not is_imm:
                self.mc.PUSH([r.ip.value], cond=cond)
            self.store_reg(self.mc, prev_loc, r.fp, offset, cond=cond)
            if not is_imm:
                self.mc.POP([r.ip.value], cond=cond)
        else:
            assert 0, 'unsupported case'

    def regalloc_mov(self, prev_loc, loc, cond=c.AL):
        """Moves a value from a previous location to some other location"""
        if prev_loc.is_imm():
            return self._mov_imm_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_reg():
            self._mov_reg_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_stack():
            self._mov_stack_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_imm_float():
            self._mov_imm_float_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_vfp_reg():
            self._mov_vfp_reg_to_loc(prev_loc, loc, cond)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def mov_from_vfp_loc(self, vfp_loc, reg1, reg2, cond=c.AL):
        """Moves floating point values either as an immediate, in a vfp
        register or at a stack location to a pair of core registers"""
        assert reg1.value + 1 == reg2.value
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_rc(reg1.value, reg2.value, vfp_loc.value, cond=cond)
        elif vfp_loc.is_imm_float():
            self.mc.PUSH([r.ip.value], cond=cond)
            self.mc.gen_load_int(r.ip.value, vfp_loc.getint(), cond=cond)
            # we need to load one word to loc and one to loc+1 which are
            # two 32-bit core registers
            self.mc.LDR_ri(reg1.value, r.ip.value, cond=cond)
            self.mc.LDR_ri(reg2.value, r.ip.value, imm=WORD, cond=cond)
            self.mc.POP([r.ip.value], cond=cond)
        elif vfp_loc.is_stack() and vfp_loc.type == FLOAT:
            # load spilled vfp value into two core registers
            offset = vfp_loc.value
            if not check_imm_arg(offset, size=0xFFF):
                self.mc.PUSH([r.ip.value], cond=cond)
                self.mc.gen_load_int(r.ip.value, offset, cond=cond)
                self.mc.LDR_rr(reg1.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.ADD_ri(r.ip.value, r.ip.value, imm=WORD, cond=cond)
                self.mc.LDR_rr(reg2.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.POP([r.ip.value], cond=cond)
            else:
                self.mc.LDR_ri(reg1.value, r.fp.value, imm=offset, cond=cond)
                self.mc.LDR_ri(reg2.value, r.fp.value,
                                                imm=offset + WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def mov_to_vfp_loc(self, reg1, reg2, vfp_loc, cond=c.AL):
        """Moves a floating point value from to consecutive core registers to a
        vfp location, either a vfp regsiter or a stacklocation"""
        assert reg1.value + 1 == reg2.value
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_cr(vfp_loc.value, reg1.value, reg2.value, cond=cond)
        elif vfp_loc.is_stack():
            # move from two core registers to a float stack location
            offset = vfp_loc.value
            if not check_imm_arg(offset + WORD, size=0xFFF):
                self.mc.PUSH([r.ip.value], cond=cond)
                self.mc.gen_load_int(r.ip.value, offset, cond=cond)
                self.mc.STR_rr(reg1.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.ADD_ri(r.ip.value, r.ip.value, imm=WORD, cond=cond)
                self.mc.STR_rr(reg2.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.POP([r.ip.value], cond=cond)
            else:
                self.mc.STR_ri(reg1.value, r.fp.value, imm=offset, cond=cond)
                self.mc.STR_ri(reg2.value, r.fp.value,
                                                imm=offset + WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def regalloc_push(self, loc, cond=c.AL):
        """Pushes the value stored in loc to the stack
        Can trash the current value of the IP register when pushing a stack
        loc"""

        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_mov(loc, scratch_reg, cond)
            self.regalloc_push(scratch_reg, cond)
        elif loc.is_reg():
            self.mc.PUSH([loc.value], cond=cond)
        elif loc.is_vfp_reg():
            self.mc.VPUSH([loc.value], cond=cond)
        elif loc.is_imm():
            self.regalloc_mov(loc, r.ip)
            self.mc.PUSH([r.ip.value], cond=cond)
        elif loc.is_imm_float():
            self.regalloc_mov(loc, r.vfp_ip)
            self.mc.VPUSH([r.vfp_ip.value], cond=cond)
        else:
            raise AssertionError('Trying to push an invalid location')

    def regalloc_pop(self, loc, cond=c.AL):
        """Pops the value on top of the stack to loc Can trash the current
        value of the IP register when popping to a stack loc"""
        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_pop(scratch_reg)
            self.regalloc_mov(scratch_reg, loc)
        elif loc.is_reg():
            self.mc.POP([loc.value], cond=cond)
        elif loc.is_vfp_reg():
            self.mc.VPOP([loc.value], cond=cond)
        else:
            raise AssertionError('Trying to pop to an invalid location')

    def malloc_cond(self, gcmap, nursery_free_adr, nursery_top_adr, size):
        assert size & (WORD-1) == 0     # must be correctly aligned

        self.mc.gen_load_int(r.r0.value, nursery_free_adr)
        self.mc.LDR_ri(r.r0.value, r.r0.value)

        if check_imm_arg(size):
            self.mc.ADD_ri(r.r1.value, r.r0.value, size)
        else:
            self.mc.gen_load_int(r.r1.value, size)
            self.mc.ADD_rr(r.r1.value, r.r0.value, r.r1.value)

        self.mc.gen_load_int(r.ip.value, nursery_top_adr)
        self.mc.LDR_ri(r.ip.value, r.ip.value)

        self.mc.CMP_rr(r.r1.value, r.ip.value)

        # We load into r0 the address stored at nursery_free_adr We calculate
        # the new value for nursery_free_adr and store in r1 The we load the
        # address stored in nursery_top_adr into IP If the value in r1 is
        # (unsigned) bigger than the one in ip we conditionally call
        # malloc_slowpath in case we called malloc_slowpath, which returns the
        # new value of nursery_free_adr in r1 and the adr of the new object in
        # r0.
        XXX # push gcmap
        
        self.mc.BL(self.malloc_slowpath, c=c.HI)

        self.mc.gen_load_int(r.ip.value, nursery_free_adr)
        self.mc.STR_ri(r.r1.value, r.ip.value)

    def push_gcmap(self, mc, gcmap, push=False, store=False):
        ptr = rffi.cast(lltype.Signed, gcmap)
        if push:
            mc.gen_load_int(r.ip.value, ptr)
            mc.PUSH([r.ip.value])
        else:
            assert store
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            mc.gen_load_int(r.ip.value, ptr)
            mc.STR_ri(r.ip.value, r.fp.value, imm=ofs)

    def pop_gcmap(self, mc):
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.MOV_bi(ofs, 0)



def not_implemented(msg):
    os.write(2, '[ARM/asm] %s\n' % msg)
    raise NotImplementedError(msg)


def notimplemented_op(self, op, arglocs, regalloc, fcond):
    print "[ARM/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)


def notimplemented_op_with_guard(self, op, guard_op, arglocs, regalloc, fcond):
    print "[ARM/asm] %s with guard %s not implemented" % \
                        (op.getopname(), guard_op.getopname())
    raise NotImplementedError(op)

asm_operations = [notimplemented_op] * (rop._LAST + 1)
asm_operations_with_guard = [notimplemented_op_with_guard] * (rop._LAST + 1)
asm_llong_operations = {}
asm_math_operations = {}

for name, value in ResOpAssembler.__dict__.iteritems():
    if name.startswith('emit_guard_'):
        opname = name[len('emit_guard_'):]
        num = getattr(rop, opname.upper())
        asm_operations_with_guard[num] = value
    elif name.startswith('emit_op_llong_'):
        opname = name[len('emit_op_llong_'):]
        num = getattr(EffectInfo, 'OS_LLONG_' + opname.upper())
        asm_llong_operations[num] = value
    elif name.startswith('emit_op_math_'):
        opname = name[len('emit_op_math_'):]
        num = getattr(EffectInfo, 'OS_MATH_' + opname.upper())
        asm_math_operations[num] = value
    elif name.startswith('emit_op_'):
        opname = name[len('emit_op_'):]
        num = getattr(rop, opname.upper())
        asm_operations[num] = value


class BridgeAlreadyCompiled(Exception):
    pass
