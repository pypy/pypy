
from rpython.jit.backend.aarch64.arch import WORD, JITFRAME_FIXED_SIZE
from rpython.jit.backend.aarch64.codebuilder import InstrBuilder, OverwritingBuilder
from rpython.jit.backend.aarch64.locations import imm, StackLocation, get_fp_offset
#from rpython.jit.backend.arm.helper.regalloc import VMEM_imm_size
from rpython.jit.backend.aarch64.opassembler import ResOpAssembler
from rpython.jit.backend.aarch64.regalloc import (Regalloc,
    operations as regalloc_operations, guard_operations, comp_operations,
    CoreRegisterManager)
#    CoreRegisterManager, check_imm_arg, VFPRegisterManager,
#from rpython.jit.backend.arm import callbuilder
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.arm import conditions as c
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
    def __init__(self, cpu, translate_support_code=False):
        ResOpAssembler.__init__(self, cpu, translate_support_code)
        self.failure_recovery_code = [0, 0, 0, 0]

    def assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                      operations, looptoken, log):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt._debug_nbargs = len(inputargs)
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

    def assemble_bridge(self, logger, faildescr, inputargs, operations,
                        original_loop_token, log):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(original_loop_token)
        #self.codemap.inherit_code_from_position(faildescr.adr_jump_offset)
        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)

        assert isinstance(faildescr, AbstractFailDescr)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)

        regalloc = Regalloc(assembler=self)
        allgcrefs = []
        operations = regalloc.prepare_bridge(inputargs, arglocs,
                                             operations,
                                             allgcrefs,
                                             self.current_clt.frame_info)
        self.reserve_gcref_table(allgcrefs)
        startpos = self.mc.get_relative_pos()

        self._check_frame_depth(self.mc, regalloc.get_gcmap())

        bridgestartpos = self.mc.get_relative_pos()
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs, operations)

        codeendpos = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        fullsize = self.mc.get_relative_pos()
        rawstart = self.materialize_loop(original_loop_token)

        self.patch_gcref_table(original_loop_token, rawstart)
        self.process_pending_guards(rawstart)

        debug_start("jit-backend-addr")
        debug_print("bridge out of Guard 0x%x has address 0x%x to 0x%x" %
                    (r_uint(descr_number), r_uint(rawstart + startpos),
                        r_uint(rawstart + codeendpos)))
        debug_print("       gc table: 0x%x" % r_uint(rawstart))
        debug_print("    jump target: 0x%x" % r_uint(rawstart + startpos))
        debug_print("         resops: 0x%x" % r_uint(rawstart + bridgestartpos))
        debug_print("       failures: 0x%x" % r_uint(rawstart + codeendpos))
        debug_print("            end: 0x%x" % r_uint(rawstart + fullsize))
        debug_stop("jit-backend-addr")

        # patch the jump from original guard
        self.patch_trace(faildescr, original_loop_token,
                                    rawstart + startpos, regalloc)

        self.patch_stack_checks(frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE,
                                rawstart)
        if not we_are_translated():
            if log:
                self.mc._dump_trace(rawstart, 'bridge.asm')

        ops_offset = self.mc.ops_offset
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE)
        self.fixup_target_tokens(rawstart)
        self.update_frame_depth(frame_depth)

        if logger:
            log = logger.log_trace(jl.MARK_TRACE_ASM, None, self.mc)
            log.write(inputargs, operations, ops_offset)
            # log that the already written bridge is stitched to a descr!
            logger.log_patch_guard(descr_number, rawstart)

            # legacy
            if logger.logger_ops:
                logger.logger_ops.log_bridge(inputargs, operations, "rewritten",
                                          faildescr, ops_offset=ops_offset)

        self.teardown()

        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

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

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

    def _push_all_regs_to_jitframe(self, mc, ignored_regs, withfloats,
                                   callee_only=False):
        # Push general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = CoreRegisterManager.save_around_call_regs
        else:
            regs = CoreRegisterManager.all_regs
        # XXX add special case if ignored_regs are a block at the start of regs
        if not ignored_regs:  # we want to push a contiguous block of regs
            assert base_ofs < 0x100
            for i, reg in enumerate(regs):
                mc.STR_ri(reg.value, r.fp.value, base_ofs + i * WORD)
        else:
            for reg in ignored_regs:
                assert not reg.is_vfp_reg()  # sanity check
            # we can have holes in the list of regs
            for i, gpr in enumerate(regs):
                if gpr in ignored_regs:
                    continue
                self.store_reg(mc, gpr, r.fp, base_ofs + i * WORD)

        if withfloats:
            # Push VFP regs
            regs = VFPRegisterManager.all_regs
            ofs = len(CoreRegisterManager.all_regs) * WORD
            assert check_imm_arg(ofs+base_ofs)
            mc.ADD_ri(r.ip.value, r.fp.value, imm=ofs+base_ofs)
            mc.VSTM(r.ip.value, [vfpr.value for vfpr in regs])

    def _pop_all_regs_from_jitframe(self, mc, ignored_regs, withfloats,
                                    callee_only=False):
        # Pop general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = CoreRegisterManager.save_around_call_regs
        else:
            regs = CoreRegisterManager.all_regs
        # XXX add special case if ignored_regs are a block at the start of regs
        if not ignored_regs:  # we want to pop a contiguous block of regs
            assert base_ofs < 0x100
            for i, reg in enumerate(regs):
                mc.LDR_ri(reg.value, r.fp.value, base_ofs + i * WORD)
        else:
            for reg in ignored_regs:
                assert not reg.is_vfp_reg()  # sanity check
            # we can have holes in the list of regs
            for i, gpr in enumerate(regs):
                if gpr in ignored_regs:
                    continue
                ofs = i * WORD + base_ofs
                self.load_reg(mc, gpr, r.fp, ofs)
        if withfloats:
            # Pop VFP regs
            regs = VFPRegisterManager.all_regs
            ofs = len(CoreRegisterManager.all_regs) * WORD
            assert check_imm_arg(ofs+base_ofs)
            mc.ADD_ri(r.ip.value, r.fp.value, imm=ofs+base_ofs)
            mc.VLDM(r.ip.value, [vfpr.value for vfpr in regs])

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = InstrBuilder()
        self._push_all_regs_to_jitframe(mc, [], withfloats)

        if exc:
            return # fix later
            XXX
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

        # set return value
        mc.MOV_rr(r.x0.value, r.fp.value)

        self.gen_func_epilog(mc)
        rawstart = mc.materialize(self.cpu, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        pass # XXX

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
        self._push_all_regs_to_jitframe(mc, [], self.cpu.supports_floats)
        # this is the gcmap stored by push_gcmap(mov=True) in _check_stack_frame
        # and the expected_size pushed in _check_stack_frame
        # pop the values passed on the stack, gcmap -> r0, expected_size -> r1
        mc.LDP_rri(r.x0.value, r.x1.value, r.sp.value, 0)
        
        # XXX # store return address and keep the stack aligned
        # mc.PUSH([r.ip.value, r.lr.value])

        # store the current gcmap(r0) in the jitframe
        gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.STR_ri(r.x0.value, r.fp.value, gcmap_ofs)

        # set first arg, which is the old jitframe address
        mc.MOV_rr(r.x0.value, r.fp.value)

        # store a possibly present exception
        # we use a callee saved reg here as a tmp for the exc.
        self._store_and_reset_exception(mc, None, r.x19, on_frame=True)

        # call realloc_frame, it takes two arguments
        # arg0: the old jitframe
        # arg1: the new size
        #
        mc.BL(self.cpu.realloc_frame)

        # set fp to the new jitframe returned from the previous call
        mc.MOV_rr(r.fp.value, r.x0.value)

        # restore a possibly present exception
        self._restore_exception(mc, None, r.x19)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._load_shadowstack_top(mc, r.r5, gcrootmap)
            # store the new jitframe addr in the shadowstack
            mc.STR_ri(r.r0.value, r.r5.value, imm=-WORD)

        # reset the jf_gcmap field in the jitframe
        mc.gen_load_int(r.ip0.value, 0)
        mc.STR_ri(r.ip0.value, r.fp.value, gcmap_ofs)

        # restore registers
        self._pop_all_regs_from_jitframe(mc, [], self.cpu.supports_floats)

        # return
        mc.ADD_ri(r.sp.value, r.sp.value, 2*WORD)
        mc.LDR_ri(r.lr.value, r.sp.value, WORD)
        mc.RET_r(r.lr.value)
        self._frame_realloc_slowpath = mc.materialize(self.cpu, [])        

    def _store_and_reset_exception(self, mc, excvalloc=None, exctploc=None,
                                   on_frame=False):
        """ Resest the exception. If excvalloc is None, then store it on the
        frame in jf_guard_exc
        """
        pass

    def _restore_exception(self, mc, excvalloc, exctploc):
        pass

    def _build_propagate_exception_path(self):
        pass

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        pass

    def _build_stack_check_slowpath(self):
        self.stack_check_slowpath = 0  #XXX

    def _check_frame_depth_debug(self, mc):
        pass

    def _check_frame_depth(self, mc, gcmap, expected_size=-1):
        """ check if the frame is of enough depth to follow this bridge.
        Otherwise reallocate the frame in a helper.
        There are other potential solutions
        to that, but this one does not sound too bad.
        """
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.LDR_ri(r.ip0.value, r.fp.value, ofs)
        stack_check_cmp_ofs = mc.currpos()
        if expected_size == -1:
            for _ in range(mc.get_max_size_of_gen_load_int()):
                mc.NOP()
        else:
            mc.gen_load_int(r.lr.value, expected_size)
        mc.CMP_rr(r.ip0.value, r.lr.value)

        jg_location = mc.currpos()
        mc.BRK()

        # the size value is still stored in lr
        mc.SUB_ri(r.sp.value, r.sp.value, 2*WORD)
        mc.STR_ri(r.lr.value, r.sp.value, WORD)

        mc.gen_load_int(r.ip0.value, rffi.cast(lltype.Signed, gcmap))
        mc.STR_ri(r.ip0.value, r.sp.value, 0)

        mc.BL(self._frame_realloc_slowpath)

        # patch jg_location above
        currpos = mc.currpos()
        pmc = OverwritingBuilder(mc, jg_location, WORD)
        pmc.B_ofs_cond(currpos - jg_location, c.GE)

        self.frame_depth_to_patch.append(stack_check_cmp_ofs)

    def update_frame_depth(self, frame_depth):
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.currpos()
        faildescrindex, target = self.store_info_on_descr(startpos, guardtok)
        self.load_from_gc_table(r.ip0.value, faildescrindex)
        self.store_reg(self.mc, r.ip0, r.fp, WORD)
        self.push_gcmap(self.mc, gcmap=guardtok.gcmap, ofs=0)
        self.mc.BL(target)
        return startpos

    def push_gcmap(self, mc, gcmap, ofs):
        ptr = rffi.cast(lltype.Signed, gcmap)
        mc.gen_load_int(r.ip0.value, ptr)
        self.store_reg(mc, r.ip0, r.fp, ofs)

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guards:
            #generate the exit stub and the encoded representation
            tok.pos_recovery_stub = self.generate_quick_failure(tok)

    def reserve_gcref_table(self, allgcrefs):
        gcref_table_size = len(allgcrefs) * WORD
	# align to a multiple of 16 and reserve space at the beginning
	# of the machine code for the gc table.  This lets us write
	# machine code with relative addressing (LDR literal).
        gcref_table_size = (gcref_table_size + 15) & ~15
        mc = self.mc
        assert mc.get_relative_pos() == 0
        for i in range(gcref_table_size):
            mc.writechar('\x00')
        self.setup_gcrefs_list(allgcrefs)

    def patch_gcref_table(self, looptoken, rawstart):
        # the gc table is at the start of the machine code
        self.gc_table_addr = rawstart
        tracer = self.cpu.gc_ll_descr.make_gcref_tracer(rawstart,
                                                        self._allgcrefs)
        gcreftracers = self.get_asmmemmgr_gcreftracers(looptoken)
        gcreftracers.append(tracer)    # keepalive
        self.teardown_gcrefs_list()

    def patch_stack_checks(self, framedepth, rawstart):
        for ofs in self.frame_depth_to_patch:
            mc = InstrBuilder()
            mc.gen_load_int(r.lr.value, framedepth)
            mc.copy_to_raw_memory(ofs + rawstart)

    def load_from_gc_table(self, regnum, index):
        address_in_buffer = index * WORD   # at the start of the buffer
        p_location = self.mc.get_relative_pos(break_basic_block=False)
        offset = address_in_buffer - p_location
        self.mc.LDR_r_literal(regnum, offset)

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        size = self.mc.get_relative_pos() 
        res = self.mc.materialize(self.cpu, allblocks,
                                   self.cpu.gc_ll_descr.gcrootmap)
        #self.cpu.codemap.register_codemap(
        #    self.codemap.get_final_bytecode(res, size))
        return res

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        b = InstrBuilder()
        patch_addr = faildescr.adr_jump_offset
        assert patch_addr != 0
        b.BL(bridge_addr)
        b.copy_to_raw_memory(patch_addr)
        faildescr.adr_jump_offset = 0

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.faildescr
            assert isinstance(descr, AbstractFailDescr)
            failure_recovery_pos = block_start + tok.pos_recovery_stub
            descr.adr_jump_offset = failure_recovery_pos
            relative_offset = tok.pos_recovery_stub - tok.offset
            guard_pos = block_start + tok.offset
            if not tok.guard_not_invalidated():
                # patch the guard jump to the stub
                # overwrite the generate BRK with a B_offs to the pos of the
                # stub
                mc = InstrBuilder()
                mc.B_ofs_cond(relative_offset, c.get_opposite_of(tok.fcond))
                mc.copy_to_raw_memory(guard_pos)
            else:
                XX
                clt.invalidate_positions.append((guard_pos, relative_offset))

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ll_loop_code += rawstart
        self.target_tokens_currently_compiling = None

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
        stack_size = (len(r.callee_saved_registers) + 2) * WORD
        self.mc.STP_rr_preindex(r.fp.value, r.lr.value, r.sp.value, -stack_size)
        for i in range(0, len(r.callee_saved_registers), 2):
            self.mc.STP_rri(r.callee_saved_registers[i].value,
                            r.callee_saved_registers[i + 1].value,
                            r.sp.value,
                            (i + 2) * WORD)
        
        #self.saved_threadlocal_addr = 0   # at offset 0 from location 'sp'
        # ^^^XXX save it from register x1 into some place
        if self.cpu.supports_floats:
            XXX
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
            self.saved_threadlocal_addr += (
                len(r.callee_saved_vfp_registers) * 2 * WORD)

        # set fp to point to the JITFRAME, passed in argument 'x0'
        self.mc.MOV_rr(r.fp.value, r.x0.value)
        #
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)

    def _assemble(self, regalloc, inputargs, operations):
        #self.guard_success_cc = c.cond_none
        regalloc.compute_hint_frame_locations(operations)
        self._walk_operations(inputargs, operations, regalloc)
        #assert self.guard_success_cc == c.cond_none
        frame_depth = regalloc.get_final_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._arm_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)
        return frame_depth

    def _walk_operations(self, inputargs, operations, regalloc):
        self._regalloc = regalloc
        regalloc.operations = operations
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            i = regalloc.position()
            op = operations[i]
            self.mc.mark_op(op)
            opnum = op.getopnum()
            if rop.has_no_side_effect(opnum) and op not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            elif not we_are_translated() and op.getopnum() == rop.FORCE_SPILL:
                regalloc.prepare_force_spill(op)
            elif i < len(operations) - 1 and regalloc.next_op_can_accept_cc(operations, i):
                guard_op = operations[i + 1]
                guard_num = guard_op.getopnum()
                arglocs, fcond = guard_operations[guard_num](regalloc, guard_op, op)
                if arglocs is not None:
                    asm_guard_operations[guard_num](self, guard_op, fcond, arglocs)
                regalloc.next_instruction() # advance one more
            else:
                arglocs = regalloc_operations[opnum](regalloc, op)
                if arglocs is not None:
                    asm_operations[opnum](self, op, arglocs)
            if rop.is_guard(opnum):
                regalloc.possibly_free_vars(op.getfailargs())
            if op.type != 'v':
                regalloc.possibly_free_var(op)
            regalloc.possibly_free_vars_for_op(op)
            regalloc.free_temp_vars()
            regalloc._check_invariants()
        if not we_are_translated():
            self.mc.BRK()
        self.mc.mark_op(None)  # end of the loop
        regalloc.operations = None

    def dispatch_comparison(self, op):
        opnum = op.getopnum()
        arglocs = comp_operations[opnum](self._regalloc, op, True)
        assert arglocs is not None
        return asm_comp_operations[opnum](self, op, arglocs)

    # regalloc support
    def load(self, loc, value):
        """load an immediate value into a register"""
        assert (loc.is_core_reg() and value.is_imm()
                    or loc.is_vfp_reg() and value.is_imm_float())
        if value.is_imm():
            self.mc.gen_load_int(loc.value, value.getint())
        elif value.is_imm_float():
            self.mc.gen_load_int(r.ip.value, value.getint())
            self.mc.VLDR(loc.value, r.ip.value)

    def _mov_stack_to_loc(self, prev_loc, loc):
        offset = prev_loc.value
        if loc.is_core_reg():
            assert prev_loc.type != FLOAT, 'trying to load from an \
                incompatible location into a core register'
            # unspill a core register
            assert 0 <= offset <= (1<<15) - 1
            self.mc.LDR_ri(loc.value, r.fp.value, offset)
            return
        xxx
        # elif loc.is_vfp_reg():
        #     assert prev_loc.type == FLOAT, 'trying to load from an \
        #         incompatible location into a float register'
        #     # load spilled value into vfp reg
        #     is_imm = check_imm_arg(offset)
        #     helper, save = self.get_tmp_reg()
        #     save_helper = not is_imm and save
        # elif loc.is_raw_sp():
        #     assert (loc.type == prev_loc.type == FLOAT
        #             or (loc.type != FLOAT and prev_loc.type != FLOAT))
        #     tmp = loc
        #     if loc.is_float():
        #         loc = r.vfp_ip
        #     else:
        #         loc, save_helper = self.get_tmp_reg()
        #         assert not save_helper
        #     helper, save_helper = self.get_tmp_reg([loc])
        #     assert not save_helper
        # else:
        #     assert 0, 'unsupported case'

        # if save_helper:
        #     self.mc.PUSH([helper.value], cond=cond)
        # self.load_reg(self.mc, loc, r.fp, offset, cond=cond, helper=helper)
        # if save_helper:
        #     self.mc.POP([helper.value], cond=cond)

    def _mov_reg_to_loc(self, prev_loc, loc):
        if loc.is_core_reg():
            self.mc.MOV_rr(loc.value, prev_loc.value)
        elif loc.is_stack():
            self.mc.STR_ri(prev_loc.value, r.fp.value, loc.value)
        else:
            XXX

    def new_stack_loc(self, i, tp):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return StackLocation(i, get_fp_offset(base_ofs, i), tp)

    def regalloc_mov(self, prev_loc, loc):
        """Moves a value from a previous location to some other location"""
        if prev_loc.is_imm():
            return self._mov_imm_to_loc(prev_loc, loc)
        elif prev_loc.is_core_reg():
            self._mov_reg_to_loc(prev_loc, loc)
        elif prev_loc.is_stack():
            self._mov_stack_to_loc(prev_loc, loc)
        elif prev_loc.is_imm_float():
            self._mov_imm_float_to_loc(prev_loc, loc)
        elif prev_loc.is_vfp_reg():
            self._mov_vfp_reg_to_loc(prev_loc, loc)
        elif prev_loc.is_raw_sp():
            self._mov_raw_sp_to_loc(prev_loc, loc)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def gen_func_epilog(self, mc=None):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if mc is None:
            mc = self.mc
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_footer_shadowstack(gcrootmap, mc)
        if self.cpu.supports_floats:
            XXX
        #    mc.VPOP([reg.value for reg in r.callee_saved_vfp_registers])

        # pop all callee saved registers

        stack_size = (len(r.callee_saved_registers) + 2) * WORD
        for i in range(0, len(r.callee_saved_registers), 2):
            mc.LDP_rri(r.callee_saved_registers[i].value,
                            r.callee_saved_registers[i + 1].value,
                            r.sp.value,
                            (i + 2) * WORD)
        mc.LDP_rr_postindex(r.fp.value, r.lr.value, r.sp.value, stack_size)

        mc.RET_r(r.lr.value)

    def store_reg(self, mc, source, base, ofs=0):
        # uses r.ip1 as a temporary
        if source.is_vfp_reg():
            return self._store_vfp_reg(mc, source, base, ofs)
        else:
            return self._store_core_reg(mc, source, base, ofs)

    def _store_vfp_reg(self, mc, source, base, ofs):
        if check_imm_arg(ofs, VMEM_imm_size):
            mc.VSTR(source.value, base.value, imm=ofs, cond=cond)
        else:
            mc.gen_load_int(helper.value, ofs, cond=cond)
            mc.ADD_rr(helper.value, base.value, helper.value, cond=cond)
            mc.VSTR(source.value, helper.value, cond=cond)

    def _store_core_reg(self, mc, source, base, ofs):
        # uses r.ip1 as a temporary
        # XXX fix:
        assert ofs & 0x7 == 0
        assert 0 <= ofs < 32768
        mc.STR_ri(source.value, base.value, ofs)
        #if check_imm_arg(ofs):
        #    mc.STR_ri(source.value, base.value, imm=ofs)
        #else:
        #    mc.gen_load_int(r.ip1, ofs)
        #    mc.STR_rr(source.value, base.value, r.ip1)

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


def not_implemented(msg):
    msg = '[ARM/asm] %s\n' % msg
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)


def notimplemented_op(self, op, arglocs):
    print "[ARM/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def notimplemented_comp_op(self, op, arglocs):
    print "[ARM/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def notimplemented_guard_op(self, op, fcond, arglocs):
    print "[ARM/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

asm_operations = [notimplemented_op] * (rop._LAST + 1)
asm_guard_operations = [notimplemented_guard_op] * (rop._LAST + 1)
asm_comp_operations = [notimplemented_comp_op] * (rop._LAST + 1)
asm_extra_operations = {}

for name, value in ResOpAssembler.__dict__.iteritems():
    if name.startswith('emit_opx_'):
        opname = name[len('emit_opx_'):]
        num = getattr(EffectInfo, 'OS_' + opname.upper())
        asm_extra_operations[num] = value
    elif name.startswith('emit_op_'):
        opname = name[len('emit_op_'):]
        num = getattr(rop, opname.upper())
        asm_operations[num] = value
    elif name.startswith('emit_guard_op_'):
        opname = name[len('emit_guard_op_'):]
        num = getattr(rop, opname.upper())
        asm_guard_operations[num] = value
    elif name.startswith('emit_comp_op_'):
        opname = name[len('emit_comp_op_'):]
        num = getattr(rop, opname.upper())
        asm_comp_operations[num] = value
