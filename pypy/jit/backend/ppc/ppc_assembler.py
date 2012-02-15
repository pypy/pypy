import os
import struct
from pypy.jit.backend.ppc.ppc_form import PPCForm as Form
from pypy.jit.backend.ppc.ppc_field import ppc_fields
from pypy.jit.backend.ppc.regalloc import (TempInt, PPCFrameManager,
                                                  Regalloc)
from pypy.jit.backend.ppc.assembler import Assembler
from pypy.jit.backend.ppc.opassembler import OpAssembler
from pypy.jit.backend.ppc.symbol_lookup import lookup
from pypy.jit.backend.ppc.codebuilder import (PPCBuilder, OverwritingBuilder,
                                              scratch_reg)
from pypy.jit.backend.ppc.arch import (IS_PPC_32, IS_PPC_64, WORD,
                                              NONVOLATILES, MAX_REG_PARAMS,
                                              GPR_SAVE_AREA, BACKCHAIN_SIZE,
                                              FPR_SAVE_AREA,
                                              FLOAT_INT_CONVERSION, FORCE_INDEX,
                                              SIZE_LOAD_IMM_PATCH_SP)
from pypy.jit.backend.ppc.helper.assembler import (gen_emit_cmp_op, 
                                                   encode32, encode64,
                                                   decode32, decode64,
                                                   count_reg_args,
                                                          Saved_Volatiles)
from pypy.jit.backend.ppc.helper.regalloc import _check_imm_arg
import pypy.jit.backend.ppc.register as r
import pypy.jit.backend.ppc.condition as c
from pypy.jit.metainterp.history import (Const, ConstPtr, JitCellToken, 
                                         TargetToken, AbstractFailDescr)
from pypy.jit.backend.llsupport.asmmemmgr import (BlockBuilderMixin, 
                                                  AsmMemoryManager,
                                                  MachineDataBlockWrapper)
from pypy.jit.backend.llsupport.regalloc import (RegisterManager, 
                                                 compute_vars_longevity)
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.model import CompiledLoopToken
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (BoxInt, ConstInt, ConstPtr,
                                         ConstFloat, Box, INT, REF, FLOAT)
from pypy.jit.backend.x86.support import values_array
from pypy.rlib.debug import (debug_print, debug_start, debug_stop,
                             have_debug_prints)
from pypy.rlib import rgc
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.jit.backend.ppc.locations import StackLocation, get_spp_offset
from pypy.rlib.jit import AsmInfo

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER', ('i', lltype.Signed),
                              ('type', lltype.Char),  # 'b'ridge, 'l'abel or
                                                      # 'e'ntry point
                              ('number', lltype.Signed))

def hi(w):
    return w >> 16

def ha(w):
    if (w >> 15) & 1:
        return (w >> 16) + 1
    else:
        return w >> 16

def lo(w):
    return w & 0x0000FFFF

def la(w):
    v = w & 0x0000FFFF
    if v & 0x8000:
        return -((v ^ 0xFFFF) + 1) # "sign extend" to 32 bits
    return v

def highest(w):
    return w >> 48

def higher(w):
    return (w >> 32) & 0x0000FFFF

def high(w):
    return (w >> 16) & 0x0000FFFF

class AssemblerPPC(OpAssembler):

    FLOAT_TYPE = '\xED'
    REF_TYPE   = '\xEE'
    INT_TYPE   = '\xEF'

    STACK_LOC = '\xFC'
    IMM_LOC = '\xFD'
    # REG_LOC is empty
    EMPTY_LOC = '\xFE'
    END_OF_LOCS = '\xFF'

    ENCODING_AREA               = len(r.MANAGED_REGS) * WORD
    OFFSET_SPP_TO_GPR_SAVE_AREA = (FORCE_INDEX + FLOAT_INT_CONVERSION
                                   + ENCODING_AREA)
    OFFSET_SPP_TO_OLD_BACKCHAIN = (OFFSET_SPP_TO_GPR_SAVE_AREA
                                   + GPR_SAVE_AREA + FPR_SAVE_AREA)

    OFFSET_STACK_ARGS = OFFSET_SPP_TO_OLD_BACKCHAIN + BACKCHAIN_SIZE * WORD
    if IS_PPC_64:
        OFFSET_STACK_ARGS += MAX_REG_PARAMS * WORD

    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.mc = None
        self.datablockwrapper = None
        self.memcpy_addr = 0
        self.fail_boxes_count = 0
        self.current_clt = None
        self._regalloc = None
        self.max_stack_params = 0
        self.propagate_exception_path = 0
        self.setup_failure_recovery()
        self._debug = False
        self.loop_run_counters = []
        self.debug_counter_descr = cpu.fielddescrof(DEBUG_COUNTER, 'i')

    def set_debug(self, v):
        self._debug = v

    def _save_nonvolatiles(self):
        """ save nonvolatile GPRs in GPR SAVE AREA 
        """
        for i, reg in enumerate(NONVOLATILES):
            # save r31 later on
            if reg.value == r.SPP.value:
                continue
            self.mc.store(reg.value, r.SPP.value, 
                    self.OFFSET_SPP_TO_GPR_SAVE_AREA + WORD * i)

    def _restore_nonvolatiles(self, mc, spp_reg):
        """ restore nonvolatile GPRs from GPR SAVE AREA
        """
        for i, reg in enumerate(NONVOLATILES):
            mc.load(reg.value, spp_reg.value, 
                self.OFFSET_SPP_TO_GPR_SAVE_AREA + WORD * i)

    # The code generated here allocates a new stackframe 
    # and is the first machine code to be executed.
    def _make_frame(self, frame_depth):
        if IS_PPC_32:
            # save it in previous frame (Backchain)
            self.mc.stwu(r.SP.value, r.SP.value, -frame_depth)
            self.mc.mflr(r.SCRATCH.value)  # move old link register
            # save old link register in previous frame
            self.mc.stw(r.SCRATCH.value, r.SP.value, frame_depth + WORD) 
        else:
            self.mc.stdu(r.SP.value, r.SP.value, -frame_depth)
            self.mc.mflr(r.SCRATCH.value)
            self.mc.std(r.SCRATCH.value, r.SP.value, frame_depth + 2 * WORD)
        # save SPP at the bottom of the stack frame
        self.mc.store(r.SPP.value, r.SP.value, WORD)

        # compute spilling pointer (SPP)
        self.mc.addi(r.SPP.value, r.SP.value, 
                frame_depth - self.OFFSET_SPP_TO_OLD_BACKCHAIN)

        # save nonvolatile registers
        self._save_nonvolatiles()

        # save r31, use r30 as scratch register
        # this is safe because r30 has been saved already
        assert NONVOLATILES[-1] == r.SPP
        ofs_to_r31 = (self.OFFSET_SPP_TO_GPR_SAVE_AREA +
                      WORD * (len(NONVOLATILES)-1))
        self.mc.load(r.r30.value, r.SP.value, WORD)
        self.mc.store(r.r30.value, r.SPP.value, ofs_to_r31)

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, spilling_pointer):
            """
                mem_loc is a structure in memory describing where the values for
                the failargs are stored.

                spilling_pointer is the address of the FORCE_INDEX.
            """
            return self.decode_registers_and_descr(mem_loc, spilling_pointer)

        self.failure_recovery_func = failure_recovery_func

    recovery_func_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, 
            lltype.Signed], lltype.Signed))

    @rgc.no_collect
    def decode_registers_and_descr(self, mem_loc, spp_loc):
        ''' 
            mem_loc     : pointer to encoded state
            spp_loc     : pointer to begin of the spilling area
            '''
        enc = rffi.cast(rffi.CCHARP, mem_loc)
        managed_size = WORD * len(r.MANAGED_REGS)
        regs = rffi.cast(rffi.CCHARP, spp_loc)
        i = -1
        fail_index = -1
        while(True):
            i += 1
            fail_index += 1
            res = enc[i]
            if res == self.END_OF_LOCS:
                break
            if res == self.EMPTY_LOC:
                continue

            group = res
            i += 1
            res = enc[i]
            if res == self.IMM_LOC:
               # imm value
                if group == self.INT_TYPE or group == self.REF_TYPE:
                    if IS_PPC_32:
                        value = decode32(enc, i+1)
                        i += 4
                    else:
                        value = decode64(enc, i+1)
                        i += 8
                else:
                    assert 0, "not implemented yet"
            elif res == self.STACK_LOC:
                stack_location = decode32(enc, i+1)
                i += 4
                if group == self.FLOAT_TYPE:
                    assert 0, "not implemented yet"
                else:
                    start = spp_loc + get_spp_offset(stack_location)
                    value = rffi.cast(rffi.LONGP, start)[0]
            else: # REG_LOC
                reg = ord(enc[i])
                if group == self.FLOAT_TYPE:
                    assert 0, "not implemented yet"
                else:
                    regindex = r.get_managed_reg_index(reg)
                    if IS_PPC_32:
                        value = decode32(regs, regindex * WORD)
                    else:
                        value = decode64(regs, regindex * WORD)
    
            if group == self.INT_TYPE:
                self.fail_boxes_int.setitem(fail_index, value)
            elif group == self.REF_TYPE:
                tgt = self.fail_boxes_ptr.get_addr_for_num(fail_index)
                rffi.cast(rffi.LONGP, tgt)[0] = value
            else:
                assert 0, 'unknown type'

        assert enc[i] == self.END_OF_LOCS
        descr = decode32(enc, i+1)
        self.fail_boxes_count = fail_index
        self.fail_force_index = spp_loc
        assert isinstance(descr, int)
        return descr

    def decode_inputargs(self, enc):
        locs = []
        j = 0
        while enc[j] != self.END_OF_LOCS:
            res = enc[j]
            if res == self.EMPTY_LOC:
                j += 1
                continue

            assert res in [self.INT_TYPE, self.REF_TYPE],\
                    'location type is not supported'
            res_type = res
            j += 1
            res = enc[j]
            if res == self.IMM_LOC:
                # XXX decode imm if necessary
                assert 0, 'Imm Locations are not supported'
            elif res == self.STACK_LOC:
                if res_type == self.FLOAT_TYPE:
                    t = FLOAT
                elif res_type == self.INT_TYPE:
                    t = INT
                else:
                    t = REF
                assert t != FLOAT
                stack_loc = decode32(enc, j+1)
                loc = PPCFrameManager.frame_pos(stack_loc, t)
                j += 4
            else: # REG_LOC
                if res_type == self.FLOAT_TYPE:
                    assert 0, "not implemented yet"
                else:
                    reg = ord(res)
                    loc = r.MANAGED_REGS[r.get_managed_reg_index(reg)]
            j += 1
            locs.append(loc)
        return locs

    def _build_malloc_slowpath(self):
        mc = PPCBuilder()
        with Saved_Volatiles(mc):
            # Values to compute size stored in r3 and r4
            mc.subf(r.r3.value, r.r3.value, r.r4.value)
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
            mc.call(addr)

        mc.cmp_op(0, r.r3.value, 0, imm=True)
        jmp_pos = mc.currpos()
        mc.nop()
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.load_imm(r.r4, nursery_free_adr)
        mc.load(r.r4.value, r.r4.value, 0)

        pmc = OverwritingBuilder(mc, jmp_pos, 1)
        pmc.bc(4, 2, jmp_pos) # jump if the two values are equal
        pmc.overwrite()
        mc.b_abs(self.propagate_exception_path)
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.malloc_slowpath = rawstart

    def _build_propagate_exception_path(self):
        if self.cpu.propagate_exception_v < 0:
            return

        mc = PPCBuilder()
        with Saved_Volatiles(mc):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=True,
                    default_to_memoryerror=True)
            mc.call(addr)

        mc.load_imm(r.RES, self.cpu.propagate_exception_v)
        self._gen_epilogue(mc)
        mc.prepare_insts_blocks()
        self.propagate_exception_path = mc.materialize(self.cpu.asmmemmgr, [])

    def _gen_leave_jitted_hook_code(self, save_exc=False):
        mc = PPCBuilder()

        with Saved_Volatiles(mc):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
            mc.call(addr)

        mc.b_abs(self.exit_code_adr)
        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                               self.cpu.gc_ll_descr.gcrootmap)

    # The code generated here serves as an exit stub from
    # the executed machine code.
    # It is generated only once when the backend is initialized.
    #
    # The following actions are performed:
    #   - The fail boxes are filled with the computed values 
    #        (failure_recovery_func)
    #   - The nonvolatile registers are restored 
    #   - jump back to the calling code
    def _gen_exit_path(self):
        mc = PPCBuilder() 
        self._save_managed_regs(mc)
        decode_func_addr = llhelper(self.recovery_func_sign,
                self.failure_recovery_func)
        addr = rffi.cast(lltype.Signed, decode_func_addr)

        # load parameters into parameter registers
        mc.load(r.r3.value, r.SPP.value, self.ENCODING_AREA)     # address of state encoding 
        mc.mr(r.r4.value, r.SPP.value)         # load spilling pointer
        #
        # call decoding function
        mc.call(addr)

        # generate return and restore registers
        self._gen_epilogue(mc)

        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    def _gen_epilogue(self, mc):
        # save SPP in r5
        # (assume that r5 has been written to failboxes)
        mc.mr(r.r5.value, r.SPP.value)
        self._restore_nonvolatiles(mc, r.r5)
        # load old backchain into r4
        if IS_PPC_32:
            ofs = WORD
        else:
            ofs = WORD * 2
        mc.load(r.r4.value, r.r5.value, self.OFFSET_SPP_TO_OLD_BACKCHAIN + ofs) 
        mc.mtlr(r.r4.value)     # restore LR
        # From SPP, we have a constant offset to the old backchain. We use the
        # SPP to re-establish the old backchain because this exit stub is
        # generated before we know how much space the entire frame will need.
        mc.addi(r.SP.value, r.r5.value, self.OFFSET_SPP_TO_OLD_BACKCHAIN) # restore old SP
        mc.blr()

    def _save_managed_regs(self, mc):
        """ store managed registers in ENCODING AREA
        """
        for i in range(len(r.MANAGED_REGS)):
            reg = r.MANAGED_REGS[i]
            mc.store(reg.value, r.SPP.value, i * WORD)

    def gen_bootstrap_code(self, loophead, spilling_area):
        self._make_frame(spilling_area)
        self.mc.b_offset(loophead)

    def setup(self, looptoken, operations):
        self.current_clt = looptoken.compiled_loop_token 
        operations = self.cpu.gc_ll_descr.rewrite_assembler(self.cpu, 
                operations, self.current_clt.allgcrefs)
        assert self.memcpy_addr != 0
        self.mc = PPCBuilder()
        self.pending_guards = []
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.max_stack_params = 0
        self.target_tokens_currently_compiling = {}
        return operations

    def setup_once(self):
        gc_ll_descr = self.cpu.gc_ll_descr
        gc_ll_descr.initialize()
        self._build_propagate_exception_path()
        if gc_ll_descr.get_malloc_slowpath_addr is not None:
            self._build_malloc_slowpath()
        if gc_ll_descr.gcrootmap and gc_ll_descr.gcrootmap.is_shadow_stack:
            self._build_release_gil(gc_ll_descr.gcrootmap)
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self.exit_code_adr = self._gen_exit_path()
        self._leave_jitted_hook_save_exc = self._gen_leave_jitted_hook_code(True)
        self._leave_jitted_hook = self._gen_leave_jitted_hook_code(False)
        debug_start('jit-backend-counts')
        self.set_debug(have_debug_prints())
        debug_stop('jit-backend-counts')

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

    def assemble_loop(self, inputargs, operations, looptoken, log):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt.allgcrefs = []
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = len(inputargs)

        if not we_are_translated():
            assert len(set(inputargs)) == len(inputargs)

        operations = self.setup(looptoken, operations)
        self.startpos = self.mc.currpos()
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(assembler=self, frame_manager=PPCFrameManager())

        regalloc.prepare_loop(inputargs, operations)
        regalloc_head = self.mc.currpos()

        start_pos = self.mc.currpos()
        looptoken._ppc_loop_code = start_pos
        clt.frame_depth = clt.param_depth = -1
        spilling_area, param_depth = self._assemble(operations, regalloc)
        size_excluding_failure_stuff = self.mc.get_relative_pos()
        clt.frame_depth = spilling_area
        clt.param_depth = param_depth
     
        direct_bootstrap_code = self.mc.currpos()
        frame_depth = self.compute_frame_depth(spilling_area, param_depth)
        self.gen_bootstrap_code(start_pos, frame_depth)

        self.write_pending_failure_recoveries()
        if IS_PPC_64:
            fdescr = self.gen_64_bit_func_descr()

        # write instructions to memory
        loop_start = self.materialize_loop(looptoken, False)
        self.fixup_target_tokens(loop_start)

        real_start = loop_start + direct_bootstrap_code
        if IS_PPC_32:
            looptoken._ppc_func_addr = real_start
        else:
            self.write_64_bit_func_descr(fdescr, real_start)
            looptoken._ppc_func_addr = fdescr

        self.process_pending_guards(loop_start)
        if not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(loop_start, 'loop_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling loop with token %r' % looptoken
        ops_offset = self.mc.ops_offset
        self._teardown()

        # XXX 3rd arg may not be correct yet
        return AsmInfo(ops_offset, real_start, size_excluding_failure_stuff)

    def _assemble(self, operations, regalloc):
        regalloc.compute_hint_frame_locations(operations)
        self._walk_operations(operations, regalloc)
        frame_depth = regalloc.frame_manager.get_frame_depth()
        param_depth = self.max_stack_params
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            frame_depth = max(frame_depth,
                              jump_target_descr._ppc_clt.frame_depth)
            param_depth = max(param_depth, 
                              jump_target_descr._ppc_clt.param_depth)
        return frame_depth, param_depth


    def assemble_bridge(self, faildescr, inputargs, operations, looptoken, log):
        operations = self.setup(looptoken, operations)
        assert isinstance(faildescr, AbstractFailDescr)
        code = faildescr._failure_recovery_code
        enc = rffi.cast(rffi.CCHARP, code)
        frame_depth = faildescr._ppc_frame_depth
        arglocs = self.decode_inputargs(enc)
        if not we_are_translated():
            assert len(inputargs) == len(arglocs)
        regalloc = Regalloc(assembler=self, frame_manager=PPCFrameManager())
        regalloc.prepare_bridge(inputargs, arglocs, operations)

        sp_patch_location = self._prepare_sp_patch_position()

        startpos = self.mc.get_relative_pos()
        spilling_area, param_depth = self._assemble(operations, regalloc)
        codeendpos = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        rawstart = self.materialize_loop(looptoken, False)
        self.process_pending_guards(rawstart)
        self.patch_trace(faildescr, looptoken, rawstart, regalloc)
        self.fixup_target_tokens(rawstart)
        self.current_clt.frame_depth = max(self.current_clt.frame_depth,
                spilling_area)
        self.current_clt.param_depth = max(self.current_clt.param_depth, param_depth)

        if not we_are_translated():
            # for the benefit of tests
            faildescr._ppc_bridge_frame_depth = self.current_clt.frame_depth
            faildescr._ppc_bridge_param_depth = self.current_clt.param_depth

        self._patch_sp_offset(sp_patch_location, rawstart)
        if not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(rawstart, 'bridge_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling bridge with token %r' % looptoken

        ops_offset = self.mc.ops_offset
        self._teardown()

        return AsmInfo(ops_offset, startpos + rawstart, codeendpos - startpos)

    def _patch_sp_offset(self, sp_patch_location, rawstart):
        mc = PPCBuilder()
        frame_depth = self.compute_frame_depth(self.current_clt.frame_depth,
                                               self.current_clt.param_depth)
        frame_depth -= self.OFFSET_SPP_TO_OLD_BACKCHAIN
        mc.load_imm(r.SCRATCH, -frame_depth)
        mc.add(r.SP.value, r.SPP.value, r.SCRATCH.value)
        mc.prepare_insts_blocks()
        mc.copy_to_raw_memory(rawstart + sp_patch_location)

    # For an explanation of the encoding, see
    # backend/arm/assembler.py
    def gen_descr_encoding(self, descr, args, arglocs):
        minsize = (len(arglocs) - 1) * 6 + 5
        memsize = self.align(minsize)
        memaddr = self.datablockwrapper.malloc_aligned(memsize, alignment=1)
        mem = rffi.cast(rffi.CArrayPtr(lltype.Char), memaddr)
        i = 0
        j = 0
        while i < len(args):
            if arglocs[i+1]:
                arg = args[i]
                loc = arglocs[i+1]
                if arg.type == INT:
                    mem[j] = self.INT_TYPE
                    j += 1
                elif arg.type == REF:
                    mem[j] = self.REF_TYPE
                    j += 1
                elif arg.type == FLOAT:
                    assert 0, "not implemented yet"
                else:
                    assert 0, 'unknown type'

                if loc.is_reg() or loc.is_vfp_reg():
                    mem[j] = chr(loc.value)
                    j += 1
                elif loc.is_imm() or loc.is_imm_float():
                    assert (arg.type == INT or arg.type == REF
                                or arg.type == FLOAT)
                    mem[j] = self.IMM_LOC
                    if IS_PPC_32:
                        encode32(mem, j+1, loc.getint())
                        j += 5
                    else:
                        encode64(mem, j+1, loc.getint())
                        j += 9
                else:
                    mem[j] = self.STACK_LOC
                    encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = self.EMPTY_LOC
                j += 1
            i += 1

        mem[j] = chr(0xFF)
        n = self.cpu.get_fail_descr_number(descr)
        encode32(mem, j+1, n)
        return memaddr

    def align(self, size):
        while size % 8 != 0:
            size += 1
        return size

    def _teardown(self):
        self.patch_list = None
        self.pending_guards = None
        self.current_clt = None
        self.mc = None
        self._regalloc = None
        assert self.datablockwrapper is None
        self.stack_in_use = False
        self.max_stack_params = 0

    def _walk_operations(self, operations, regalloc):
        self._regalloc = regalloc
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            pos = regalloc.position()
            op = operations[pos]
            opnum = op.getopnum()
            if op.has_no_side_effect() and op.result not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            elif self.can_merge_with_next_guard(op, pos, operations)\
                    and opnum in (rop.CALL_RELEASE_GIL, rop.CALL_ASSEMBLER,\
                    rop.CALL_MAY_FORCE):  # XXX fix  
                regalloc.next_instruction()
                arglocs = regalloc.operations_with_guard[opnum](regalloc, op,
                                        operations[pos+1])
                operations_with_guard[opnum](self, op,
                                        operations[pos+1], arglocs, regalloc)
            elif not we_are_translated() and op.getopnum() == -124:
                regalloc.prepare_force_spill(op)
            else:
                arglocs = regalloc.operations[opnum](regalloc, op)
                if arglocs is not None:
                    self.operations[opnum](self, op, arglocs, regalloc)
            if op.is_guard():
                regalloc.possibly_free_vars(op.getfailargs())
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc.free_temp_vars()
            regalloc._check_invariants()

    def can_merge_with_next_guard(self, op, i, operations):
        if (op.getopnum() == rop.CALL_MAY_FORCE or
            op.getopnum() == rop.CALL_ASSEMBLER or
            op.getopnum() == rop.CALL_RELEASE_GIL):
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if not op.is_comparison():
            if op.is_ovf():
                if (operations[i + 1].getopnum() != rop.GUARD_NO_OVERFLOW and
                    operations[i + 1].getopnum() != rop.GUARD_OVERFLOW):
                    assert 0, "int_xxx_ovf not followed by guard_(no)_overflow"
                return True
            return False
        if (operations[i + 1].getopnum() != rop.GUARD_TRUE and
            operations[i + 1].getopnum() != rop.GUARD_FALSE):
            return False
        if operations[i + 1].getarg(0) is not op.result:
            return False
        if (self._regalloc.longevity[op.result][1] > i + 1 or
            op.result in operations[i + 1].getfailargs()):
            return False
        return True

    def gen_64_bit_func_descr(self):
        return self.datablockwrapper.malloc_aligned(3*WORD, alignment=1)

    def write_64_bit_func_descr(self, descr, start_addr):
        data = rffi.cast(rffi.CArrayPtr(lltype.Signed), descr)
        data[0] = start_addr
        data[1] = 0
        data[2] = 0

    def compute_frame_depth(self, spilling_area, param_depth):
        PARAMETER_AREA = param_depth * WORD
        if IS_PPC_64:
            PARAMETER_AREA += MAX_REG_PARAMS * WORD
        SPILLING_AREA = spilling_area * WORD

        frame_depth = (  GPR_SAVE_AREA
                       + FPR_SAVE_AREA
                       + FLOAT_INT_CONVERSION
                       + FORCE_INDEX
                       + self.ENCODING_AREA
                       + SPILLING_AREA
                       + PARAMETER_AREA
                       + BACKCHAIN_SIZE * WORD)

        # align stack pointer
        while frame_depth % (4 * WORD) != 0:
            frame_depth += WORD

        return frame_depth
    
    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ppc_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def target_arglocs(self, looptoken):
        return looptoken._ppc_arglocs

    def materialize_loop(self, looptoken, show=False):
        self.mc.prepare_insts_blocks(show)
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu.asmmemmgr, allblocks, 
                                    self.cpu.gc_ll_descr.gcrootmap)
        #from pypy.rlib.rarithmetic import r_uint
        #print "=== Loop start is at %s ===" % hex(r_uint(start))
        return start

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guards:
            descr = tok.descr
            #generate the exit stub and the encoded representation
            pos = self.mc.currpos()
            tok.pos_recovery_stub = pos 

            memaddr = self.gen_exit_stub(descr, tok.failargs,
                                            tok.faillocs,
                                            save_exc=tok.save_exc)
            # store info on the descr
            descr._ppc_frame_depth = tok.faillocs[0].getint()
            descr._failure_recovery_code = memaddr
            descr._ppc_guard_pos = pos

    def gen_exit_stub(self, descr, args, arglocs, save_exc=False):
        memaddr = self.gen_descr_encoding(descr, args, arglocs)

        # store addr in force index field
        self.mc.alloc_scratch_reg()
        self.mc.load_imm(r.SCRATCH, memaddr)
        self.mc.store(r.SCRATCH.value, r.SPP.value, self.ENCODING_AREA)
        self.mc.free_scratch_reg()

        if save_exc:
            path = self._leave_jitted_hook_save_exc
        else:
            path = self._leave_jitted_hook
        self.mc.b_abs(path)
        return memaddr

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.descr
            assert isinstance(descr, AbstractFailDescr)
            descr._ppc_block_start = block_start

            if not tok.is_invalidate:
                mc = PPCBuilder()
                offset = descr._ppc_guard_pos - tok.offset
                mc.b_cond_offset(offset, tok.fcond)
                mc.prepare_insts_blocks(True)
                mc.copy_to_raw_memory(block_start + tok.offset)
            else:
                clt.invalidate_positions.append((block_start + tok.offset,
                        descr._ppc_guard_pos - tok.offset))

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        # The first instruction (word) is not overwritten, because it is the
        # one that actually checks the condition
        mc = PPCBuilder()
        patch_addr = faildescr._ppc_block_start + faildescr._ppc_guard_pos
        mc.b_abs(bridge_addr)
        mc.prepare_insts_blocks()
        mc.copy_to_raw_memory(patch_addr)

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def _prepare_sp_patch_position(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update
        the sp according to the number of spilled variables"""
        size = SIZE_LOAD_IMM_PATCH_SP
        l = self.mc.currpos()
        for _ in range(size):
            self.mc.nop()
        return l

    def regalloc_mov(self, prev_loc, loc):
        if prev_loc.is_imm():
            value = prev_loc.getint()
            # move immediate value to register
            if loc.is_reg():
                self.mc.load_imm(loc, value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                self.mc.alloc_scratch_reg()
                offset = loc.value
                self.mc.load_imm(r.SCRATCH, value)
                self.mc.store(r.SCRATCH.value, r.SPP.value, offset)
                self.mc.free_scratch_reg()
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.value
            # move from memory to register
            if loc.is_reg():
                reg = loc.as_key()
                self.mc.load(reg, r.SPP.value, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.value
                self.mc.alloc_scratch_reg()
                self.mc.load(r.SCRATCH.value, r.SPP.value, offset)
                self.mc.store(r.SCRATCH.value, r.SPP.value, target_offset)
                self.mc.free_scratch_reg()
                return
            assert 0, "not supported location"
        elif prev_loc.is_reg():
            reg = prev_loc.as_key()
            # move to another register
            if loc.is_reg():
                other_reg = loc.as_key()
                self.mc.mr(other_reg, reg)
                return
            # move to memory
            elif loc.is_stack():
                offset = loc.value
                self.mc.store(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        assert 0, "not supported location"
    mov_loc_loc = regalloc_mov

    def regalloc_push(self, loc):
        """Pushes the value stored in loc to the stack
        Can trash the current value of SCRATCH when pushing a stack
        loc"""

        if loc.is_stack():
            if loc.type == FLOAT:
                assert 0, "not implemented yet"
            # XXX this code has to be verified
            assert not self.stack_in_use
            target = StackLocation(self.ENCODING_AREA // WORD) # write to ENCODING AREA           
            self.regalloc_mov(loc, target)
            self.stack_in_use = True
        elif loc.is_reg():
            self.mc.addi(r.SP.value, r.SP.value, -WORD) # decrease stack pointer
            # push value
            if IS_PPC_32:
                self.mc.stw(loc.value, r.SP.value, 0)
            else:
                self.mc.std(loc.value, r.SP.value, 0)
        elif loc.is_imm():
            assert 0, "not implemented yet"
        elif loc.is_imm_float():
            assert 0, "not implemented yet"
        else:
            raise AssertionError('Trying to push an invalid location')

    def regalloc_pop(self, loc):
        """Pops the value on top of the stack to loc. Can trash the current
        value of SCRATCH when popping to a stack loc"""
        if loc.is_stack():
            if loc.type == FLOAT:
                assert 0, "not implemented yet"
            # XXX this code has to be verified
            assert self.stack_in_use
            from_loc = StackLocation(self.ENCODING_AREA // WORD) # read from ENCODING AREA
            self.regalloc_mov(from_loc, loc)
            self.stack_in_use = False
        elif loc.is_reg():
            # pop value
            if IS_PPC_32:
                self.mc.lwz(loc.value, r.SP.value, 0)
            else:
                self.mc.ld(loc.value, r.SP.value, 0)
            self.mc.addi(r.SP.value, r.SP.value, WORD) # increase stack pointer
        else:
            raise AssertionError('Trying to pop to an invalid location')

    def leave_jitted_hook(self):
        ptrs = self.fail_boxes_ptr.ar
        llop.gc_assume_young_pointers(lltype.Void,
                                      llmemory.cast_ptr_to_adr(ptrs))

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == 1:
            if not signed: #unsigned char
                if IS_PPC_32:
                    self.mc.rlwinm(resloc.value, resloc.value, 0, 24, 31)
                else:
                    self.mc.rldicl(resloc.value, resloc.value, 0, 56)
            else:
                self.mc.extsb(resloc.value, resloc.value)
        elif size == 2:
            if not signed:
                if IS_PPC_32:
                    self.mc.rlwinm(resloc.value, resloc.value, 0, 16, 31)
                else:
                    self.mc.rldicl(resloc.value, resloc.value, 0, 48)
            else:
                self.mc.extsh(resloc.value, resloc.value)
        elif size == 4:
            if not signed:
                self.mc.rldicl(resloc.value, resloc.value, 0, 32)
            else:
                self.mc.extsw(resloc.value, resloc.value)

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size):
        assert size & (WORD-1) == 0     # must be correctly aligned

        self.mc.load_imm(r.RES, nursery_free_adr)
        self.mc.load(r.RES.value, r.RES.value, 0)

        if _check_imm_arg(size):
            self.mc.addi(r.r4.value, r.RES.value, size)
        else:
            self.mc.load_imm(r.r4, size)
            self.mc.add(r.r4.value, r.RES.value, r.r4.value)

        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, nursery_top_adr)
            self.mc.loadx(r.SCRATCH.value, 0, r.SCRATCH.value)

        self.mc.cmp_op(0, r.r4.value, r.SCRATCH.value, signed=False)
        fast_jmp_pos = self.mc.currpos()
        self.mc.nop()

        # We load into r3 the address stored at nursery_free_adr. We calculate
        # the new value for nursery_free_adr and store in r1 The we load the
        # address stored in nursery_top_adr into IP If the value in r4 is
        # (unsigned) bigger than the one in ip we conditionally call
        # malloc_slowpath in case we called malloc_slowpath, which returns the
        # new value of nursery_free_adr in r4 and the adr of the new object in
        # r3.
        self.mark_gc_roots(self.write_new_force_index(),
                           use_copy_area=True)
        self.mc.call(self.malloc_slowpath)

        offset = self.mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(self.mc, fast_jmp_pos, 1)
        pmc.bc(4, 1, offset) # jump if LE (not GT)
        
        with scratch_reg(self.mc):
            self.mc.load_imm(r.SCRATCH, nursery_free_adr)
            self.mc.storex(r.r1.value, 0, r.SCRATCH.value)

    def mark_gc_roots(self, force_index, use_copy_area=False):
        if force_index < 0:
            return     # not needed
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            mark = self._regalloc.get_mark_gc_roots(gcrootmap, use_copy_area)
            assert gcrootmap.is_shadow_stack
            gcrootmap.write_callshape(mark, force_index)

    def propagate_memoryerror_if_r3_is_null(self):
        self.mc.cmp_op(0, r.RES.value, 0, imm=True)
        self.mc.b_cond_abs(self.propagate_exception_path, c.EQ)

    def write_new_force_index(self):
        # for shadowstack only: get a new, unused force_index number and
        # write it to FORCE_INDEX_OFS.  Used to record the call shape
        # (i.e. where the GC pointers are in the stack) around a CALL
        # instruction that doesn't already have a force_index.
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            clt = self.current_clt
            force_index = clt.reserve_and_record_some_faildescr_index()
            self._write_fail_index(force_index)
            return force_index
        else:
            return 0

    def _write_fail_index(self, fail_index):
        self.mc.alloc_scratch_reg()
        self.mc.load_imm(r.SCRATCH, fail_index)
        self.mc.store(r.SCRATCH.value, r.SPP.value, self.ENCODING_AREA)
        self.mc.free_scratch_reg()
            
    def load(self, loc, value):
        assert loc.is_reg() and value.is_imm()
        if value.is_imm():
            self.mc.load_imm(loc, value.getint())
        elif value.is_imm_float():
            assert 0, "not implemented yet"

def notimplemented_op(self, op, arglocs, regalloc):
    raise NotImplementedError, op

def notimplemented_op_with_guard(self, op, guard_op, arglocs, regalloc):
    raise NotImplementedError, op

operations = [notimplemented_op] * (rop._LAST + 1)
operations_with_guard = [notimplemented_op_with_guard] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_%s' % key
    if hasattr(AssemblerPPC, methname):
        func = getattr(AssemblerPPC, methname).im_func
        operations[value] = func

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_guard_%s' % key
    if hasattr(AssemblerPPC, methname):
        func = getattr(AssemblerPPC, methname).im_func
        operations_with_guard[value] = func

AssemblerPPC.operations = operations
AssemblerPPC.operations_with_guard = operations_with_guard
