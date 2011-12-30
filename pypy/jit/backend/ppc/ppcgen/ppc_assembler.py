import os
import struct
from pypy.jit.backend.ppc.ppcgen.ppc_form import PPCForm as Form
from pypy.jit.backend.ppc.ppcgen.ppc_field import ppc_fields
from pypy.jit.backend.ppc.ppcgen.regalloc import (TempInt, PPCFrameManager,
                                                  Regalloc)
from pypy.jit.backend.ppc.ppcgen.assembler import Assembler
from pypy.jit.backend.ppc.ppcgen.opassembler import OpAssembler
from pypy.jit.backend.ppc.ppcgen.symbol_lookup import lookup
from pypy.jit.backend.ppc.ppcgen.codebuilder import PPCBuilder
from pypy.jit.backend.ppc.ppcgen.jump import remap_frame_layout
from pypy.jit.backend.ppc.ppcgen.arch import (IS_PPC_32, IS_PPC_64, WORD,
                                              NONVOLATILES, MAX_REG_PARAMS,
                                              GPR_SAVE_AREA, BACKCHAIN_SIZE,
                                              FPR_SAVE_AREA,
                                              FLOAT_INT_CONVERSION, FORCE_INDEX)
from pypy.jit.backend.ppc.ppcgen.helper.assembler import (gen_emit_cmp_op, 
                                                          encode32, encode64,
                                                          decode32, decode64,
                                                          count_reg_args,
                                                          Saved_Volatiles)
import pypy.jit.backend.ppc.ppcgen.register as r
import pypy.jit.backend.ppc.ppcgen.condition as c
from pypy.jit.metainterp.history import (Const, ConstPtr, LoopToken,
                                         AbstractFailDescr)
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
from pypy.rlib import rgc
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem.lloperation import llop

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)
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

    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.mc = None
        self.malloc_func_addr = 0
        self.malloc_array_func_addr = 0
        self.malloc_str_func_addr = 0
        self.malloc_unicode_func_addr = 0
        self.datablockwrapper = None
        self.memcpy_addr = 0
        self.fail_boxes_count = 0
        self.current_clt = None
        self._regalloc = None
        self.max_stack_params = 0
        self.propagate_exception_path = 0

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

    def _make_prologue(self, target_pos, frame_depth):
        self._make_frame(frame_depth)
        curpos = self.mc.currpos()
        offset = target_pos - curpos
        self.mc.b(offset)

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
                    start = spp_loc - (stack_location + 1) * WORD
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
        return descr

    def decode_inputargs(self, enc, inputargs, regalloc):
        locs = []
        j = 0
        for i in range(len(inputargs)):
            res = enc[j]
            if res == self.END_OF_LOCS:
                assert 0, 'reached end of encoded area'
            while res == self.EMPTY_LOC:
                j += 1
                res = enc[j]

            assert res in [self.INT_TYPE, self.REF_TYPE],\
                    'location type is not supported'
            res_type = res
            j += 1
            res = enc[j]
            if res == self.IMM_LOC:
                # XXX decode imm if necessary
                assert 0, 'Imm Locations are not supported'
            elif res == self.STACK_LOC:
                stack_loc = decode32(enc, j+1)
                loc = regalloc.frame_manager.frame_pos(stack_loc, INT)
                j += 4
            else: # REG_LOC
                reg = ord(res)
                loc = r.MANAGED_REGS[r.get_managed_reg_index(reg)]
            j += 1
            locs.append(loc)
        return locs

    def _build_propagate_exception_path(self):
        if self.cpu.propagate_exception_v < 0:
            return

        mc = PPCBuilder()
        with Saved_Volatiles(mc):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=True)
            if IS_PPC_32:
                mc.bl_abs(addr)
            else:
                mc.load_imm(r.r11, addr)
                mc.load(r.SCRATCH.value, r.r11.value, 0)
                mc.mtctr(r.SCRATCH.value)
                mc.load(r.r2.value, r.r11.value, WORD)
                mc.load(r.r11.value, r.r11.value, 2 * WORD)
                mc.bctrl()
        #mc.alloc_scratch_reg(self.cpu.propagate_exception_v)
        #mc.mr(r.RES.value, r.SCRATCH.value)
        #mc.free_scratch_reg()
        mc.load_imm(r.RES, self.cpu.propagate_exception_v)
        mc.prepare_insts_blocks()
        self.propagate_exception_path = mc.materialize(self.cpu.asmmemmgr, [])

    def _gen_leave_jitted_hook_code(self, save_exc=False):
        mc = PPCBuilder()

        with Saved_Volatiles(mc):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
            if IS_PPC_32:
                mc.bl_abs(addr)
            else:
                mc.load_imm(r.r11, addr)
                mc.load(r.SCRATCH.value, r.r11.value, 0)
                mc.mtctr(r.SCRATCH.value)
                mc.load(r.r2.value, r.r11.value, WORD)
                mc.load(r.r11.value, r.r11.value, 2 * WORD)
                mc.bctrl()

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
        # load address of decoding function into SCRATCH
        if IS_PPC_32:
            mc.alloc_scratch_reg(addr)
            mc.mtctr(r.SCRATCH.value)
            mc.free_scratch_reg()
        # ... and branch there
            mc.bctrl()
        else:
            mc.std(r.TOC.value, r.SP.value, 5 * WORD)
            mc.load_imm(r.r11, addr)
            mc.load(r.SCRATCH.value, r.r11.value, 0)
            mc.mtctr(r.SCRATCH.value)
            mc.load(r.TOC.value, r.r11.value, WORD)
            mc.load(r.r11.value, r.r11.value, 2 * WORD)
            mc.bctrl()
            mc.ld(r.TOC.value, r.SP.value, 5 * WORD)
        #
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
        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    def _save_managed_regs(self, mc):
        """ store managed registers in ENCODING AREA
        """
        for i in range(len(r.MANAGED_REGS)):
            reg = r.MANAGED_REGS[i]
            mc.store(reg.value, r.SPP.value, i * WORD)

    # Load parameters from fail args into locations (stack or registers)
    def gen_bootstrap_code(self, nonfloatlocs, inputargs):
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            arg = inputargs[i]
            assert arg.type != FLOAT
            if arg.type == INT:
                addr = self.fail_boxes_int.get_addr_for_num(i)
            elif arg.type == REF:
                addr = self.fail_boxes_ptr.get_addr_for_num(i)
            else:
                assert 0, "%s not supported" % arg.type
            if loc.is_reg():
                reg = loc
            else:
                reg = r.SCRATCH
            self.mc.load_from_addr(reg, addr)
            if loc.is_stack():
                self.regalloc_mov(r.SCRATCH, loc)

    def gen_direct_bootstrap_code(self, loophead, looptoken, inputargs, frame_depth):
        self._make_frame(frame_depth)
        nonfloatlocs = looptoken._ppc_arglocs[0]

        reg_args = count_reg_args(inputargs)

        stack_locs = len(inputargs) - reg_args

        selected_reg = 0
        count = 0
        nonfloat_args = []
        nonfloat_regs = []
        # load reg args
        for i in range(reg_args):
            arg = inputargs[i]
            if arg.type == FLOAT and count % 2 != 0:
                assert 0, "not implemented yet"
            reg = r.PARAM_REGS[selected_reg]

            if arg.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                nonfloat_args.append(reg)
                nonfloat_regs.append(nonfloatlocs[i])

            if arg.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                selected_reg += 1
                count += 1

        # remap values stored in core registers
        self.mc.alloc_scratch_reg()
        remap_frame_layout(self, nonfloat_args, nonfloat_regs, r.SCRATCH)
        self.mc.free_scratch_reg()

        # load values passed on the stack to the corresponding locations
        stack_position = self.OFFSET_SPP_TO_OLD_BACKCHAIN\
                         + BACKCHAIN_SIZE * WORD

        count = 0
        for i in range(reg_args, len(inputargs)):
            arg = inputargs[i]
            if arg.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                loc = nonfloatlocs[i]
            if loc.is_reg():
                self.mc.load(loc.value, r.SPP.value, stack_position)
                count += 1
            elif loc.is_vfp_reg():
                assert 0, "not implemented yet"
            elif loc.is_stack():
                if loc.type == FLOAT:
                    assert 0, "not implemented yet"
                elif loc.type == INT or loc.type == REF:
                    count += 1
                    self.mc.alloc_scratch_reg()
                    self.mc.load(r.SCRATCH.value, r.SPP.value, stack_position)
                    self.mov_loc_loc(r.SCRATCH, loc)
                    self.mc.free_scratch_reg()
                else:
                    assert 0, 'invalid location'
            else:
                assert 0, 'invalid location'
            if loc.type == FLOAT:
                assert 0, "not implemented yet"
            else:
                size = 1
            stack_position += size * WORD

        #sp_patch_location = self._prepare_sp_patch_position()
        self.mc.b_offset(loophead)
        #self._patch_sp_offset(sp_patch_location, looptoken._ppc_frame_depth)

    def setup(self, looptoken, operations):
        assert self.memcpy_addr != 0
        self.current_clt = looptoken.compiled_loop_token 
        operations = self.cpu.gc_ll_descr.rewrite_assembler(self.cpu, 
                operations, self.current_clt.allgcrefs)
        self.mc = PPCBuilder()
        self.pending_guards = []
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.stack_in_use = False
        self.max_stack_params = 0

    def setup_once(self):
        gc_ll_descr = self.cpu.gc_ll_descr
        gc_ll_descr.initialize()
        ll_new = gc_ll_descr.get_funcptr_for_new()
        self.malloc_func_addr = rffi.cast(lltype.Signed, ll_new)
        self._build_propagate_exception_path()
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            ll_new_array = gc_ll_descr.get_funcptr_for_newarray()
            self.malloc_array_func_addr = rffi.cast(lltype.Signed,
                                                    ll_new_array)
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            ll_new_str = gc_ll_descr.get_funcptr_for_newstr()
            self.malloc_str_func_addr = rffi.cast(lltype.Signed,
                                                  ll_new_str)
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            ll_new_unicode = gc_ll_descr.get_funcptr_for_newunicode()
            self.malloc_unicode_func_addr = rffi.cast(lltype.Signed,
                                                      ll_new_unicode)
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self.setup_failure_recovery()
        self.exit_code_adr = self._gen_exit_path()
        self._leave_jitted_hook_save_exc = self._gen_leave_jitted_hook_code(True)
        self._leave_jitted_hook = self._gen_leave_jitted_hook_code(False)

    def assemble_loop(self, inputargs, operations, looptoken, log):

        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt.allgcrefs = []
        looptoken.compiled_loop_token = clt

        self.setup(looptoken, operations)
        self.startpos = self.mc.currpos()
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(longevity, assembler=self,
                            frame_manager=PPCFrameManager())

        nonfloatlocs = regalloc.prepare_loop(inputargs, operations, looptoken)
        regalloc_head = self.mc.currpos()
        self.gen_bootstrap_code(nonfloatlocs, inputargs)

        loophead = self.mc.currpos()            # address of actual loop
        looptoken._ppc_loop_code = loophead
        looptoken._ppc_arglocs = [nonfloatlocs]
        looptoken._ppc_bootstrap_code = 0

        self._walk_operations(operations, regalloc)

        start_pos = self.mc.currpos()
        self.framesize = frame_depth = self.compute_frame_depth(regalloc)
        looptoken._ppc_frame_manager_depth = regalloc.frame_manager.frame_depth
        self._make_prologue(regalloc_head, frame_depth)
     
        direct_bootstrap_code = self.mc.currpos()
        self.gen_direct_bootstrap_code(loophead, looptoken, inputargs, frame_depth)

        self.write_pending_failure_recoveries()
	if IS_PPC_64:
		fdescrs = self.gen_64_bit_func_descrs()
        loop_start = self.materialize_loop(looptoken, False)
        looptoken._ppc_bootstrap_code = loop_start

        real_start = loop_start + direct_bootstrap_code
        if IS_PPC_32:
            looptoken._ppc_direct_bootstrap_code = real_start
        else:
            self.write_64_bit_func_descr(fdescrs[0], real_start)
            looptoken._ppc_direct_bootstrap_code = fdescrs[0]

        real_start = loop_start + start_pos
        if IS_PPC_32:
            looptoken.ppc_code = real_start
        else:
            self.write_64_bit_func_descr(fdescrs[1], real_start)
            looptoken.ppc_code = fdescrs[1]
        self.process_pending_guards(loop_start)
        if not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(loop_start, 'loop_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling loop with token %r' % looptoken

        self._teardown()

    def assemble_bridge(self, faildescr, inputargs, operations, looptoken, log):
        self.setup(looptoken, operations)
        assert isinstance(faildescr, AbstractFailDescr)
        code = faildescr._failure_recovery_code
        enc = rffi.cast(rffi.CCHARP, code)
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(longevity, assembler=self, 
                            frame_manager=PPCFrameManager())

        #sp_patch_location = self._prepare_sp_patch_position()
        frame_depth = faildescr._ppc_frame_depth
        locs = self.decode_inputargs(enc, inputargs, regalloc)
        regalloc.update_bindings(locs, frame_depth, inputargs)

        self._walk_operations(operations, regalloc)

        #self._patch_sp_offset(sp_patch_location, 
        #                      regalloc.frame_manager.frame_depth)
        self.write_pending_failure_recoveries()
        bridge_start = self.materialize_loop(looptoken, False)
        self.process_pending_guards(bridge_start)
        self.patch_trace(faildescr, looptoken, bridge_start, regalloc)
        self._teardown()

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
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
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
                    not_implemented("int_xxx_ovf not followed by "
                                    "guard_(no)_overflow")
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

    def gen_64_bit_func_descrs(self):
        d0 = self.datablockwrapper.malloc_aligned(3*WORD, alignment=1)
        d1 = self.datablockwrapper.malloc_aligned(3*WORD, alignment=1)
	return [d0, d1]

    def write_64_bit_func_descr(self, descr, start_addr):
        data = rffi.cast(rffi.CArrayPtr(lltype.Signed), descr)
	data[0] = start_addr
	data[1] = 0
	data[2] = 0

    def compute_frame_depth(self, regalloc):
        PARAMETER_AREA = self.max_stack_params * WORD
        if IS_PPC_64:
            PARAMETER_AREA += MAX_REG_PARAMS * WORD
        SPILLING_AREA = regalloc.frame_manager.frame_depth * WORD

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
    
    def materialize_loop(self, looptoken, show):
        self.mc.prepare_insts_blocks(show)
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        start = self.mc.materialize(self.cpu.asmmemmgr, allblocks, 
                                    self.cpu.gc_ll_descr.gcrootmap)
        from pypy.rlib.rarithmetic import r_uint
        print "=== Loop start is at %s ===" % hex(r_uint(start))
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
        self.mc.alloc_scratch_reg(memaddr)
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
                offset = loc.as_key() * WORD - WORD
                self.mc.load_imm(r.SCRATCH.value, value)
                self.mc.store(r.SCRATCH.value, r.SPP.value, offset)
                self.mc.free_scratch_reg()
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.as_key() * WORD - WORD
            # move from memory to register
            if loc.is_reg():
                reg = loc.as_key()
                self.mc.load(reg, r.SPP.value, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.as_key() * WORD - WORD
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
                offset = loc.as_key() * WORD - WORD
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
            target = StackLocation(self.ENCODING_AREA) # write to force index field           
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
            from_loc = StackLocation(self.ENCODING_AREA)
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
        self.mc.alloc_scratch_reg(fail_index)
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
