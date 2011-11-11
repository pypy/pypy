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
from pypy.jit.backend.ppc.ppcgen.arch import (IS_PPC_32, IS_PPC_64, WORD,
                                              NONVOLATILES,
                                              GPR_SAVE_AREA, BACKCHAIN_SIZE)
from pypy.jit.backend.ppc.ppcgen.helper.assembler import (gen_emit_cmp_op, 
                                                          encode32, decode32,
                                                          decode64)
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


    '''
    PyPy's PPC stack frame layout
    =============================

    .                          .
    .                          . 
    ----------------------------
    |         BACKCHAIN        |       OLD  FRAME
    ------------------------------------------------------
    |                          |       PyPy Frame
    |      GPR  SAVE  AREA     |
    |                          |
    ----------------------------
    |       FORCE  INDEX       |
    ----------------------------  <- Spilling Pointer (SPP) 
    |                          |
    |       SPILLING  AREA     |
    |                          |
    ----------------------------  <- Stack Pointer (SP)

    The size of the GPR save area and the force index area fixed:

        GPR SAVE AREA: len(NONVOLATILES) * WORD
        FORCE INDEX  : WORD


    The size of the spilling area is known when the trace operations
    have been generated.
    '''

    GPR_SAVE_AREA_AND_FORCE_INDEX = GPR_SAVE_AREA + WORD
                                  # ^^^^^^^^^^^^^   ^^^^
                                  # save GRP regs   force index

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

    def _save_nonvolatiles(self):
        for i, reg in enumerate(NONVOLATILES):
            # save r31 later on
            if reg.value == r.SPP.value:
                continue
            if IS_PPC_32:
                self.mc.stw(reg.value, r.SPP.value, WORD + WORD * i)
            else:
                self.mc.std(reg.value, r.SPP.value, WORD + WORD * i)

    def _restore_nonvolatiles(self, mc, spp_reg):
        for i, reg in enumerate(NONVOLATILES):
            if IS_PPC_32:
                mc.lwz(reg.value, spp_reg.value, WORD + WORD * i)
            else:
                mc.ld(reg.value, spp_reg.value, WORD + WORD * i)

    # Fetches the identifier from a descr object.
    # If it has no identifier, then an unused identifier
    # is generated
    # XXX could be overwritten later on, better approach?
    def _get_identifier_from_descr(self, descr):
        try:
            identifier = descr.identifier
        except AttributeError:
            identifier = None
        if identifier is not None:
            return identifier
        keys = self.cpu.saved_descr.keys()
        if keys == []:
            return 1
        return max(keys) + 1

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr = []
        return clt.asmmemmgr_blocks

    # The code generated here allocates a new stackframe 
    # and is the first machine code to be executed.
    def _make_prologue(self, target_pos, frame_depth):
        if IS_PPC_32:
            # save it in previous frame (Backchain)
            self.mc.stwu(r.SP.value, r.SP.value, -frame_depth)
            self.mc.mflr(r.r0.value)  # move old link register
            # save old link register in previous frame
            self.mc.stw(r.r0.value, r.SP.value, frame_depth + WORD) 
            # save r31 at the bottom of the stack frame
            self.mc.stw(r.SPP.value, r.SP.value, WORD)
        else:
            self.mc.stdu(r.SP.value, r.SP.value, -frame_depth)
            self.mc.mflr(r.r0.value)
            self.mc.std(r.r0.value, r.SP.value, frame_depth + 2 * WORD)

        # compute spilling pointer (SPP)
        self.mc.addi(r.SPP.value, r.SP.value, frame_depth
                     - self.GPR_SAVE_AREA_AND_FORCE_INDEX)
        self._save_nonvolatiles()
        # save r31, use r30 as scratch register
        # this is safe because r30 has been saved already
        if IS_PPC_32:
            self.mc.lwz(r.r30.value, r.SP.value, WORD)
            self.mc.stw(r.r30.value, r.SPP.value, WORD * len(NONVOLATILES))
        else:
            self.mc.ld(r.r30.value, r.SP.value, WORD)
            self.mc.std(r.r30.value, r.SPP.value, WORD * len(NONVOLATILES))
        # branch to loop code
        curpos = self.mc.currpos()
        offset = target_pos - curpos
        self.mc.b(offset)

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, stack_pointer, spilling_pointer):
            """
                mem_loc is a structure in memory describing where the values for
                the failargs are stored.
            
                stack_pointer is the address of top of the stack.

                spilling_pointer is the address of the FORCE_INDEX.
            """
            return self.decode_registers_and_descr(mem_loc, stack_pointer, spilling_pointer)

        self.failure_recovery_func = failure_recovery_func

    recovery_func_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, 
            lltype.Signed, lltype.Signed], lltype.Signed))

    @rgc.no_collect
    def decode_registers_and_descr(self, mem_loc, stack_loc, spp_loc):
        ''' 
            mem_loc     : pointer to encoded state
            stack_loc   : pointer to top of the stack
            spp_loc     : pointer to begin of the spilling area
            '''
        enc = rffi.cast(rffi.CCHARP, mem_loc)
        managed_size = WORD * len(r.MANAGED_REGS)
        # XXX do some sanity considerations
        spilling_depth = spp_loc - stack_loc + managed_size
        spilling_area = rffi.cast(rffi.CCHARP, stack_loc + managed_size)
        assert spilling_depth >= 0
        assert spp_loc > stack_loc

        regs = rffi.cast(rffi.CCHARP, stack_loc + BACKCHAIN_SIZE)
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
                    value = decode32(enc, i+1)
                    i += 4
                else:
                    assert group == self.FLOAT_TYPE
                    adr = decode32(enc, i+1)
                    value = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0]
                    self.fail_boxes_float.setitem(fail_index, value)
                    i += 4
                    continue
            elif res == self.STACK_LOC:
                stack_location = decode32(enc, i+1)
                i += 4
                if group == self.FLOAT_TYPE:
                    value = decode64(stack, frame_depth - stack_location*WORD)
                    self.fail_boxes_float.setitem(fail_index, value)
                    continue
                else:
                    #value = decode32(spilling_area, spilling_area - stack_location * WORD)
                    #import pdb; pdb.set_trace()
                    value = decode32(spilling_area, spilling_depth - stack_location * WORD)
            else: # REG_LOC
                reg = ord(enc[i])
                if group == self.FLOAT_TYPE:
                    value = decode64(vfp_regs, reg*2*WORD)
                    self.fail_boxes_float.setitem(fail_index, value)
                    continue
                else:
                    if IS_PPC_32:
                        value = decode32(regs, (reg - 3) * WORD)
                    else:
                        value = decode64(regs, (reg - 3) * WORD)
    
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
                #loc = r.all_regs[ord(res)]
                loc = r.MANAGED_REGS[ord(res) - 3]
            j += 1
            locs.append(loc)
        return locs

    def _gen_leave_jitted_hook_code(self, save_exc=False):
        mc = PPCBuilder()

        # PLAN:
        # =====
        # save caller save registers AND(!) r0 
        # (r0 contains address of state encoding)

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
        # compute offset to new SP
        size = WORD * (len(r.MANAGED_REGS)) + BACKCHAIN_SIZE
        # set SP
        if IS_PPC_32:
            mc.stwu(r.SP.value, r.SP.value, -size)
        else:
            mc.stdu(r.SP.value, r.SP.value, -size)
        self._save_managed_regs(mc)
        # adjust SP (r1)
        # XXX do quadword alignment
        #while size % (4 * WORD) != 0:
        #    size += WORD
        #
        decode_func_addr = llhelper(self.recovery_func_sign,
                self.failure_recovery_func)
        if IS_PPC_32:
            addr = rffi.cast(lltype.Signed, decode_func_addr)
        else:
            intp = lltype.Ptr(lltype.Array(lltype.Signed, hints={'nolength': True}))
            descr = rffi.cast(intp, decode_func_addr)
            addr = descr[0]
            r2_value = descr[1]
            r11_value = descr[2]

        # load parameters into parameter registers
        if IS_PPC_32:
            mc.lwz(r.r3.value, r.SPP.value, 0)     # address of state encoding 
        else:
            mc.ld(r.r3.value, r.SPP.value, 0)     
        mc.mr(r.r4.value, r.SP.value)          # load stack pointer
        mc.mr(r.r5.value, r.SPP.value)         # load spilling pointer
        #
        # load address of decoding function into r0
        mc.load_imm(r.r0, addr)
        if IS_PPC_64:
            mc.std(r.r2.value, r.SP.value, 3 * WORD)
            # load TOC pointer and environment pointer
            mc.load_imm(r.r2, r2_value)
            mc.load_imm(r.r11, r11_value)
        # ... and branch there
        mc.mtctr(r.r0.value)
        mc.bctrl()
        if IS_PPC_64:
            mc.ld(r.r2.value, r.SP.value, 3 * WORD)
        #
        mc.addi(r.SP.value, r.SP.value, size)
        # save SPP in r5
        # (assume that r5 has been written to failboxes)
        mc.mr(r.r5.value, r.SPP.value)
        self._restore_nonvolatiles(mc, r.r5)
        # load old backchain into r4
        offset_to_old_backchain = self.GPR_SAVE_AREA_AND_FORCE_INDEX + WORD
        if IS_PPC_32:
            mc.lwz(r.r4.value, r.r5.value, offset_to_old_backchain) 
        else:
            mc.ld(r.r4.value, r.r5.value, offset_to_old_backchain + WORD)
        mc.mtlr(r.r4.value)     # restore LR

        # From SPP, we have a constant offset of GPR_SAVE_AREA_AND_FORCE_INDEX 
        # to the old backchain. We use the SPP to re-establish the old backchain
        # because this exit stub is generated before we know how much space
        # the entire frame will need.
        mc.addi(r.SP.value, r.r5.value, self.GPR_SAVE_AREA_AND_FORCE_INDEX) # restore old SP
        mc.blr()
        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    # Save all registers which are managed by the register
    # allocator on top of the stack before decoding.
    def _save_managed_regs(self, mc):
        for i in range(len(r.MANAGED_REGS)):
            reg = r.MANAGED_REGS[i]
            if IS_PPC_32:
                mc.stw(reg.value, r.SP.value, i * WORD + BACKCHAIN_SIZE)
            else:
                mc.std(reg.value, r.SP.value, i * WORD + BACKCHAIN_SIZE)

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
                reg = r.r0
            self.mc.load_from_addr(reg, addr)
            if loc.is_stack():
                self.regalloc_mov(r.r0, loc)

    def setup(self, looptoken, operations):
        assert self.memcpy_addr != 0
        self.current_clt = looptoken.compiled_loop_token 
        operations = self.cpu.gc_ll_descr.rewrite_assembler(self.cpu, 
                operations, self.current_clt.allgcrefs)
        self.mc = PPCBuilder()
        self.pending_guards = []
        assert self.datablockwrapper is None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)

    def setup_once(self):
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self.setup_failure_recovery()
        self.exit_code_adr = self._gen_exit_path()
        #self._leave_jitted_hook_save_exc = self._gen_leave_jitted_hook_code(True)
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
     
        self.write_pending_failure_recoveries()
        loop_start = self.materialize_loop(looptoken, False)
        looptoken._ppc_bootstrap_code = loop_start
        real_start = loop_start + start_pos
        if IS_PPC_32:
            looptoken.ppc_code = real_start
        else:
            looptoken.ppc_code = self.gen_64_bit_func_descr(real_start)
        self.process_pending_guards(loop_start)
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
                    mem[j] = self.FLOAT_TYPE
                    j += 1
                else:
                    assert 0, 'unknown type'

                if loc.is_reg() or loc.is_vfp_reg():
                    mem[j] = chr(loc.value)
                    j += 1
                elif loc.is_imm() or loc.is_imm_float():
                    assert (arg.type == INT or arg.type == REF
                                or arg.type == FLOAT)
                    mem[j] = self.IMM_LOC
                    encode32(mem, j+1, loc.getint())
                    j += 5
                else:
                    mem[j] = self.STACK_LOC
                    encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = self.EMPTY_LOC
                j += 1
            i += 1
                # XXX 64 bit adjustment needed

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
                    and opnum == rop.CALL_RELEASE_GIL:  # XXX fix  
                regalloc.next_instruction()
                arglocs = regalloc.operations_with_guard[opnum](regalloc, op,
                                        operations[pos+1])
                operations_with_guard[opnum](self, op,
                                        operations[pos+1], arglocs, regalloc)
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

    def gen_64_bit_func_descr(self, start_addr):
        mc = PPCBuilder()
        mc.write64(start_addr)
        mc.write64(0)
        mc.write64(0)
        return mc.materialize(self.cpu.asmmemmgr, [], 
                              self.cpu.gc_ll_descr.gcrootmap)

    def compute_frame_depth(self, regalloc):
        frame_depth = (GPR_SAVE_AREA                        # GPR space
                       + WORD                               # FORCE INDEX
                       + regalloc.frame_manager.frame_depth * WORD)
        return frame_depth
    
    def materialize_loop(self, looptoken, show):
        self.mc.prepare_insts_blocks(show)
        self.datablockwrapper.done()
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        return self.mc.materialize(self.cpu.asmmemmgr, allblocks, 
                                   self.cpu.gc_ll_descr.gcrootmap)

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guards:
            descr = tok.descr
            #generate the exit stub and the encoded representation
            pos = self.mc.currpos()
            tok.pos_recovery_stub = pos 

            memaddr = self.gen_exit_stub(descr, tok.failargs,
                                            tok.faillocs, save_exc=tok.save_exc)
            # store info on the descr
            descr._ppc_frame_depth = tok.faillocs[0].getint()
            descr._failure_recovery_code = memaddr
            descr._ppc_guard_pos = pos

    def gen_exit_stub(self, descr, args, arglocs, fcond=c.NE,
                               save_exc=False):
        memaddr = self.gen_descr_encoding(descr, args, arglocs)

        # store addr in force index field
        self.mc.load_imm(r.r0, memaddr)
        if IS_PPC_32:
            self.mc.stw(r.r0.value, r.SPP.value, 0)
        else:
            self.mc.std(r.r0.value, r.SPP.value, 0)

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
                assert 0, "not implemented yet"

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
                offset = loc.as_key() * WORD - WORD
                self.mc.load_imm(r.r0.value, value)
                if IS_PPC_32:
                    self.mc.stw(r.r0.value, r.SPP.value, offset)
                else:
                    self.mc.std(r.r0.value, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.as_key() * WORD - WORD
            # move from memory to register
            if loc.is_reg():
                reg = loc.as_key()
                if IS_PPC_32:
                    self.mc.lwz(reg, r.SPP.value, offset)
                else:
                    self.mc.ld(reg, r.SPP.value, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.as_key() * WORD - WORD
                if IS_PPC_32:
                    self.mc.lwz(r.r0.value, r.SPP.value, offset)
                    self.mc.stw(r.r0.value, r.SPP.value, target_offset)
                else:
                    self.mc.ld(r.r0.value, r.SPP.value, offset)
                    self.mc.std(r.r0.value, r.SPP.value, target_offset)
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
                if IS_PPC_32:
                    self.mc.stw(reg, r.SPP.value, offset)
                else:
                    self.mc.std(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        assert 0, "not supported location"

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
