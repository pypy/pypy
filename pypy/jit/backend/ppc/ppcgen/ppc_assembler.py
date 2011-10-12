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
from pypy.jit.backend.ppc.ppcgen.arch import (IS_PPC_32, WORD, NONVOLATILES,
                                              GPR_SAVE_AREA)
from pypy.jit.backend.ppc.ppcgen.helper.assembler import (gen_emit_cmp_op, 
                                                          encode32)
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

    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.mc = None
        self.datablockwrapper = None
        self.memcpy_addr = 0

    def load_imm(self, rD, word):
        if word <= 32767 and word >= -32768:
            self.mc.li(rD, word)
        elif IS_PPC_32 or (word <= 2147483647 and word >= -2147483648):
            self.mc.lis(rD, hi(word))
            if word & 0xFFFF != 0:
                self.mc.ori(rD, rD, lo(word))
        else:
            self.mc.lis(rD, highest(word))
            self.mc.ori(rD, rD, higher(word))
            self.mc.sldi(rD, rD, 32)
            self.mc.oris(rD, rD, high(word))
            self.mc.ori(rD, rD, lo(word))

    def load_from_addr(self, rD, addr):
        if IS_PPC_32:
            self.mc.addis(rD, 0, ha(addr))
            self.mc.lwz(rD, rD, la(addr))
        else:
            self.load_word(rD, addr)
            self.mc.ld(rD, rD, 0)

    def store_reg(self, source_reg, addr):
        self.load_imm(r.r0.value, addr)
        if IS_PPC_32:
            self.mc.stwx(source_reg.value, 0, 0)
        else:
            self.mc.std(source_reg.value, 0, 0)

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

    # XXX adjust for 64 bit
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
            self.mc.stdu(1, 1, -frame_depth)
            self.mc.mflr(0)
            self.mc.std(0, 1, frame_depth + 4)
        offset = GPR_SAVE_AREA + WORD
        # compute spilling pointer (SPP)
        self.mc.addi(r.SPP.value, r.SP.value, frame_depth - offset)
        self._save_nonvolatiles()
        # save r31, use r30 as scratch register
        # this is safe because r30 has been saved already
        self.mc.lwz(r.r30.value, r.SP.value, WORD)
        self.mc.stw(r.r30.value, r.SPP.value, WORD * len(NONVOLATILES))
        # branch to loop code
        curpos = self.mc.currpos()
        offset = target_pos - curpos
        self.mc.b(offset)

    #def _make_epilogue(self):
    #    for op_index, fail_index, guard, reglist in self.patch_list:
    #        curpos = self.mc.get_rel_pos()
    #        offset = curpos - (4 * op_index)
    #        assert (1 << 15) > offset
    #        self.mc.beq(offset)
    #        self.mc.patch_op(op_index)

    #        # store return parameters in memory
    #        used_mem_indices = []
    #        for index, reg in enumerate(reglist):
    #            # if reg is None, then there is a hole in the failargs
    #            if reg is not None:
    #                addr = self.fail_boxes_int.get_addr_for_num(index)
    #                self.store_reg(reg, addr)
    #                used_mem_indices.append(index)

    #        patch_op = self.mc.get_number_of_ops()
    #        patch_pos = self.mc.get_rel_pos()
    #        descr = self.cpu.saved_descr[fail_index]
    #        descr.patch_op = patch_op
    #        descr.patch_pos = patch_pos
    #        descr.used_mem_indices = used_mem_indices

    #        self.mc.li(r.r3.value, fail_index)

    #        #self._restore_nonvolatiles()

    #        #self.mc.lwz(0, 1, self.framesize + 4)
    #        #if IS_PPC_32:
    #        #    self.mc.lwz(0, 1, self.framesize + WORD) # 36
    #        #else:
    #        #    self.mc.ld(0, 1, self.framesize + WORD) # 36
    #        #self.mc.mtlr(0)
    #        #self.mc.addi(1, 1, self.framesize)
    #        #self.mc.li(r.r3.value, fail_index)            
    #        #self.mc.blr()

    def _gen_leave_jitted_hook_code(self, save_exc=False):
        mc = PPCBuilder()
        ### XXX add a check if cpu supports floats
        #with saved_registers(mc, r.caller_resp + [r.ip], r.caller_vfp_resp):
        #    addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
        #    mc.BL(addr)
        #assert self._exit_code_addr != 0
        #mc.B(self._exit_code_addr)
        mc.b_abs(self.exit_code_adr)
        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                               self.cpu.gc_ll_descr.gcrootmap)

    def _gen_exit_path(self):
        mc = PPCBuilder()
        # save SPP in r5
        # (assume that r5 has been written to failboxes)
        mc.mr(r.r5.value, r.SPP.value)
        self._restore_nonvolatiles(mc, r.r5)
        # load old backchain into r4
        if IS_PPC_32:
            mc.lwz(r.r4.value, r.r5.value, GPR_SAVE_AREA + 2 * WORD) 
        else:
            mc.ld(r.r4.value, r.r5.value, GPR_SAVE_AREA + 2 * WORD)
        mc.mtlr(r.r4.value)     # restore LR
        mc.addi(r.SP.value, r.r5.value, GPR_SAVE_AREA + WORD) # restore old SP
        mc.blr()
        mc.prepare_insts_blocks()
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    def gen_bootstrap_code(self, nonfloatlocs, inputargs):
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            arg = inputargs[i]
            assert arg.type != FLOAT
            if arg.type == INT:
                addr = self.fail_boxes_int.get_addr_for_num(i)
            elif args.type == REF:
                addr = self.fail_boxes_ptr.get_addr_for_num(i)
            else:
                assert 0, "%s not supported" % arg.type
            if loc.is_reg():
                reg = loc
            else:
                assert 0, "FIX LATER"
            self.load_from_addr(reg.value, addr)

    def setup(self, looptoken, operations):
        operations = self.cpu.gc_ll_descr.rewrite_assembler(self.cpu, 
                                                            operations)
        assert self.memcpy_addr != 0
        self.current_clt = looptoken.compiled_loop_token
        self.mc = PPCBuilder()
        self.pending_guards = []
        assert self.datablockwrapper is None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)

    def setup_once(self):
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self.exit_code_adr = self._gen_exit_path()
        #self._leave_jitted_hook_save_exc = self._gen_leave_jitted_hook_code(True)
        self._leave_jitted_hook = self._gen_leave_jitted_hook_code(False)

    def assemble_loop(self, inputargs, operations, looptoken, log):

        clt = CompiledLoopToken(self.cpu, looptoken.number)
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
        self._make_prologue(regalloc_head, frame_depth)
     
        self.write_pending_failure_recoveries()
        loop_start = self.materialize_loop(looptoken, True)
        looptoken.ppc_code = loop_start + start_pos
        self.process_pending_guards(loop_start)
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

    def _walk_operations(self, operations, regalloc):
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            pos = regalloc.position()
            op = operations[pos]
            opnum = op.getopnum()
            if op.has_no_side_effect() and op.result not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            else:
                arglocs = regalloc.operations[opnum](regalloc, op)
                if arglocs is not None:
                    self.operations[opnum](self, op, arglocs, regalloc)
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc._check_invariants()

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
        self.mc.stw(r.r0.value, r.SPP.value, 0)

        if save_exc:
            path = self._leave_jitted_hook_save_exc
        else:
            path = self._leave_jitted_hook
        self.mc.trap()
        #self.mc.ba(path)
        self.branch_abs(path)
        return memaddr

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.descr
            assert isinstance(descr, AbstractFailDescr)
            descr._ppc_block_start = block_start

            if not tok.is_invalidate:
                mc = PPCBuilder()
                mc.b_cond_offset(descr._ppc_guard_pos - tok.offset, tok.fcond)
                mc.prepare_insts_blocks(True)
                mc.copy_to_raw_memory(block_start + tok.offset)
            else:
                assert 0, "not implemented yet"

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    # XXX fix for 64 bit
    def regalloc_mov(self, prev_loc, loc):
        if prev_loc.is_imm():
            value = prev_loc.getint()
            # move immediate value to register
            if loc.is_reg():
                reg = loc.as_key()
                self.mc.load_imm(reg, value)
                return
            # move immediate value to memory
            elif loc.is_stack():
                offset = loc.as_key() * WORD - WORD
                self.mc.load_imm(r.r0.value, value)
                self.mc.stw(r.r0.value, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        elif prev_loc.is_stack():
            offset = prev_loc.as_key() * WORD - WORD
            # move from memory to register
            if loc.is_reg():
                reg = loc.as_key()
                self.mc.lwz(reg, r.SPP.value, offset)
                return
            # move in memory
            elif loc.is_stack():
                target_offset = loc.as_key() * WORD - WORD
                self.mc.lwz(r.r0.value, r.SPP.value, offset)
                self.mc.stw(r.r0.value, r.SPP.value, target_offset)
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
                self.mc.stw(reg, r.SPP.value, offset)
                return
            assert 0, "not supported location"
        assert 0, "not supported location"

def make_operations():
    def not_implemented(builder, trace_op, cpu, *rest_args):
        raise NotImplementedError, trace_op

    oplist = [None] * (rop._LAST + 1)
    for key, val in rop.__dict__.items():
        if key.startswith("_"):
            continue
        opname = key.lower()
        methname = "emit_%s" % opname
        if hasattr(AssemblerPPC, methname):
            oplist[val] = getattr(AssemblerPPC, methname).im_func
        else:
            oplist[val] = not_implemented
    return oplist

AssemblerPPC.operations = make_operations()
