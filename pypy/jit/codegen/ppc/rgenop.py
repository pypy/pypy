import py
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.jit.codegen.model import ReplayBuilder, dummy_var
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem import lloperation
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.jit.codegen.conftest import option
from ctypes import POINTER, cast, c_void_p, c_int, CFUNCTYPE

from pypy.jit.codegen.ppc import codebuf
from pypy.jit.codegen.ppc.instruction import rSP, rFP, rSCRATCH, gprs
from pypy.jit.codegen.ppc import instruction as insn
from pypy.jit.codegen.ppc.regalloc import RegisterAllocation
from pypy.jit.codegen.ppc.emit_moves import emit_moves, emit_moves_safe

from pypy.jit.codegen.ppc.ppcgen.rassemblermaker import make_rassembler
from pypy.jit.codegen.ppc.ppcgen.ppc_assembler import MyPPCAssembler

from pypy.jit.codegen.i386.rgenop import gc_malloc_fnaddr
from pypy.rpython.annlowlevel import llhelper

class RPPCAssembler(make_rassembler(MyPPCAssembler)):
    def emit(self, value):
        self.mc.write(value)

_PPC = RPPCAssembler


_flush_icache = None
def flush_icache(base, size):
    global _flush_icache
    if _flush_icache == None:
        cpath = py.magic.autopath().dirpath().join('_flush_icache.c')
        _flush_icache  = cpath._getpymodule()._flush_icache
    _flush_icache(base, size)

NSAVEDREGISTERS = 19

DEBUG_TRAP = option.trap
DEBUG_PRINT = option.debug_print

_var_index = [0]
class Var(GenVar):
    conditional = False
    def __init__(self):
        self.__magic_index = _var_index[0]
        _var_index[0] += 1
    def __repr__(self):
        return "v%d" % self.__magic_index
    def fits_in_uimm(self):
        return False
    def fits_in_simm(self):
        return False

class ConditionVar(Var):
    """ Used for vars that originated as the result of a conditional
    operation, like a == b """
    conditional = True

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'IntConst(%d)'%self.value

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def load(self, insns, var):
        insns.append(
            insn.Insn_GPR__IMM(_PPC.load_word,
                               var, [self]))

    def load_now(self, asm, loc):
        if loc.is_register:
            assert isinstance(loc, insn.GPR)
            asm.load_word(loc.number, self.value)
        else:
            #print 'load_now to', loc.offset
            asm.load_word(rSCRATCH, self.value)
            asm.stw(rSCRATCH, rFP, loc.offset)

    def fits_in_simm(self):
        return abs(self.value) < 2**15

    def fits_in_uimm(self):
        return 0 <= self.value < 2**16

class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            assert 0, "XXX not implemented"

    def fits_in_simm(self):
        return False

    def fits_in_uimm(self):
        return False

    def load(self, insns, var):
        i = IntConst(llmemory.cast_adr_to_int(self.addr))
        insns.append(
            insn.Insn_GPR__IMM(RPPCAssembler.load_word,
                               var, [i]))

    def load_now(self, asm, loc):
        value = llmemory.cast_adr_to_int(self.addr)
        if loc.is_register:
            assert isinstance(loc, insn.GPR)
            asm.load_word(loc.number, value)
        else:
            #print 'load_now to', loc.offset
            asm.load_word(rSCRATCH, value)
            asm.stw(rSCRATCH, rFP, loc.offset)


class JumpPatchupGenerator(object):

    def __init__(self, insns, allocator):
        self.insns = insns
        self.allocator = allocator

    def emit_move(self, tarloc, srcloc):
        srcvar = None
        if DEBUG_PRINT:
            for v, loc in self.allocator.var2loc.iteritems():
                if loc is srcloc:
                    srcvar = v
                    break
        emit = self.insns.append
        if tarloc == srcloc:
            return
        if tarloc.is_register and srcloc.is_register:
            assert isinstance(tarloc, insn.GPR)
            if isinstance(srcloc, insn.GPR):
                emit(insn.Move(tarloc, srcloc))
            else:
                assert isinstance(srcloc, insn.CRF)
                emit(srcloc.move_to_gpr(tarloc.number))
        elif tarloc.is_register and not srcloc.is_register:
            emit(insn.Unspill(srcvar, tarloc, srcloc))
        elif not tarloc.is_register and srcloc.is_register:
            emit(insn.Spill(srcvar, srcloc, tarloc))
        elif not tarloc.is_register and not srcloc.is_register:
            emit(insn.Unspill(srcvar, insn.gprs[0], srcloc))
            emit(insn.Spill(srcvar, insn.gprs[0], tarloc))

    def create_fresh_location(self):
        return self.allocator.spill_slot()

class StackInfo(Var):
    # not really a Var at all, but needs to be mixable with Consts....
    # offset will be assigned later
    offset = 0
    pass

def prepare_for_jump(insns, sourcevars, src2loc, target, allocator):

    tar2src = {}     # tar var -> src var
    tar2loc = {}

    # construct mapping of targets to sources; note that "target vars"
    # and "target locs" are the same thing right now
    targetlocs = target.arg_locations
    tarvars = []

##     if DEBUG_PRINT:
##         print targetlocs
##         print allocator.var2loc

    for i in range(len(targetlocs)):
        tloc = targetlocs[i]
        src = sourcevars[i]
        if isinstance(src, Var):
            tar2loc[tloc] = tloc
            tar2src[tloc] = src
            tarvars.append(tloc)
        if not tloc.is_register:
            if tloc in allocator.free_stack_slots:
                allocator.free_stack_slots.remove(tloc)

    gen = JumpPatchupGenerator(insns, allocator)
    emit_moves(gen, tarvars, tar2src, tar2loc, src2loc)

    for i in range(len(targetlocs)):
        tloc = targetlocs[i]
        src = sourcevars[i]
        if not isinstance(src, Var):
            insns.append(insn.Load(tloc, src))

class Label(GenLabel):

    def __init__(self, args_gv):
        self.args_gv = args_gv
        #self.startaddr = startaddr
        #self.arg_locations = arg_locations
        self.min_stack_offset = 1

# our approach to stack layout:

# on function entry, the stack looks like this:

#        ....
# | parameter area |
# |  linkage area  | <- rSP points to the last word of the linkage area
# +----------------+

# we set things up like so:

# | parameter area  |
# |  linkage area   | <- rFP points to where the rSP was
# | saved registers |
# | local variables |
# +-----------------+ <- rSP points here, and moves around between basic blocks

# points of note (as of 2006-11-09 anyway :-):
# 1. we currently never spill to the parameter area (should fix?)
# 2. we always save all callee-save registers
# 3. as each basic block can move the SP around as it sees fit, we index
#    into the local variables area from the FP (frame pointer; it is not
#    usual on the PPC to have a frame pointer, but there's no reason we
#    can't have one :-)


class Builder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.asm = RPPCAssembler()
        self.asm.mc = None
        self.insns = []
        self.initial_spill_offset = 0
        self.initial_var2loc = None
        self.max_param_space = -1
        self.final_jump_addr = 0

        self.start = 0
        self.closed = True
        self.patch_start_here = 0

    # ----------------------------------------------------------------
    # the public Builder interface:

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        #print opname, 'on', id(self)
        genmethod = getattr(self, 'op_' + opname)
        r = genmethod(gv_arg)
        #print '->', id(r)
        return r

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        #print opname, 'on', id(self)
        genmethod = getattr(self, 'op_' + opname)
        r = genmethod(gv_arg1, gv_arg2)
        #print '->', id(r)
        return r

    @specialize.arg(1)
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'raisingop_' + opname)
        r = genmethod(gv_arg1, gv_arg2)
        return r

    @specialize.arg(1)
    def genraisingop1(self, opname, gv_arg):
        genmethod = getattr(self, 'raisingop_' + opname)
        r = genmethod(gv_arg)
        return r

    def genop_ptr_iszero(self, kind, gv_ptr):
        return self.op_ptr_iszero(gv_ptr)

    def genop_ptr_nonzero(self, kind, gv_ptr):
        return self.op_ptr_nonzero(gv_ptr)

    def genop_ptr_eq(self, kind, gv_ptr1, gv_ptr2):
        return self.op_ptr_eq(gv_ptr1, gv_ptr2)

    def genop_ptr_ne(self, kind, gv_ptr1, gv_ptr2):
        return self.op_ptr_ne(gv_ptr1, gv_ptr2)

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        self.insns.append(insn.SpillCalleeSaves())
        for i in range(len(args_gv)):
            self.insns.append(insn.LoadArg(i, args_gv[i]))
        gv_result = Var()
        self.max_param_space = max(self.max_param_space, len(args_gv)*4)
        self.insns.append(insn.CALL(gv_result, gv_fnptr))
        return gv_result

    def genop_getfield(self, fieldtoken, gv_ptr):
        fieldoffset, fieldsize = fieldtoken
        opcode = {1:_PPC.lbz, 2:_PPC.lhz, 4:_PPC.lwz}[fieldsize]
        return self._arg_simm_op(gv_ptr, IntConst(fieldoffset), opcode)

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        gv_result = Var()
        fieldoffset, fieldsize = fieldtoken
        opcode = {1:_PPC.stb, 2:_PPC.sth, 4:_PPC.stw}[fieldsize]
        self.insns.append(
            insn.Insn_None__GPR_GPR_IMM(opcode,
                                        [gv_value, gv_ptr, IntConst(fieldoffset)]))
        return gv_result

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        return self._arg_simm_op(gv_ptr, IntConst(fieldtoken[0]), _PPC.addi)

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        _, _, itemsize = arraytoken
        opcode = {1:_PPC.lbzx,
                  2:_PPC.lhzx,
                  4:_PPC.lwzx}[itemsize]
        opcodei = {1:_PPC.lbz,
                   2:_PPC.lhz,
                   4:_PPC.lwz}[itemsize]
        gv_itemoffset = self.itemoffset(arraytoken, gv_index)
        return self._arg_arg_op_with_simm(gv_ptr, gv_itemoffset, opcode, opcodei)

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        _, _, itemsize = arraytoken
        assert itemsize == 4
        gv_itemoffset = self.itemoffset(arraytoken, gv_index)
        return self._arg_arg_op_with_simm(gv_ptr, gv_itemoffset, _PPC.add, _PPC.addi,
                                         commutative=True)

    def genop_getarraysize(self, arraytoken, gv_ptr):
        lengthoffset, _, _ = arraytoken
        return self._arg_simm_op(gv_ptr, IntConst(lengthoffset), _PPC.lwz)

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        _, _, itemsize = arraytoken
        gv_itemoffset = self.itemoffset(arraytoken, gv_index)
        gv_result = Var()
        if gv_itemoffset.fits_in_simm():
            opcode = {1:_PPC.stb,
                      2:_PPC.sth,
                      4:_PPC.stw}[itemsize]
            self.insns.append(
                insn.Insn_None__GPR_GPR_IMM(opcode,
                                            [gv_value, gv_ptr, gv_itemoffset]))
        else:
            opcode = {1:_PPC.stbx,
                      2:_PPC.sthx,
                      4:_PPC.stwx}[itemsize]
            self.insns.append(
                insn.Insn_None__GPR_GPR_GPR(opcode,
                                            [gv_value, gv_ptr, gv_itemoffset]))

    def genop_malloc_fixedsize(self, alloctoken):
        return self.genop_call(1, # COUGH
                               IntConst(gc_malloc_fnaddr()),
                               [IntConst(alloctoken)])

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        gv_itemoffset = self.itemoffset(varsizealloctoken, gv_size)
        gv_result = self.genop_call(1, # COUGH
                                    IntConst(gc_malloc_fnaddr()),
                                    [gv_itemoffset])
        lengthoffset, _, _ = varsizealloctoken
        self.insns.append(
            insn.Insn_None__GPR_GPR_IMM(_PPC.stw,
                                        [gv_size, gv_result, IntConst(lengthoffset)]))
        return gv_result

    def genop_same_as(self, kindtoken, gv_arg):
        if not isinstance(gv_arg, Var):
            gv_result = Var()
            gv_arg.load(self.insns, gv_result)
            return gv_result
        else:
            return gv_arg

##     def genop_debug_pdb(self):    # may take an args_gv later

    def genop_get_frame_base(self):
        gv_result = Var()
        self.insns.append(
            insn.LoadFramePointer(gv_result))
        return gv_result

    def get_frame_info(self, vars_gv):
        result = []
        for v in vars_gv:
            if isinstance(v, Var):
                place = StackInfo()
                self.insns.append(insn.CopyIntoStack(place, v))
                result.append(place)
            else:
                result.append(None)
        return result

    def alloc_frame_place(self, kind, gv_initial_value=None):
        place = StackInfo()
        if gv_initial_value is None:
            gv_initial_value = AddrConst(llmemory.NULL)
        self.insns.append(insn.CopyIntoStack(place, gv_initial_value))
        return place

    def genop_absorb_place(self, kind, place):
        var = Var()
        self.insns.append(insn.CopyOffStack(var, place))
        return var

    def enter_next_block(self, kinds, args_gv):
        if DEBUG_PRINT:
            print 'enter_next_block1', args_gv
        seen = {}
        for i in range(len(args_gv)):
            gv = args_gv[i]
            if isinstance(gv, Var):
                if gv in seen:
                    new_gv = self._arg_op(gv, _PPC.mr)
                    args_gv[i] = new_gv
                seen[gv] = True
            else:
                new_gv = Var()
                gv.load(self.insns, new_gv)
                args_gv[i] = new_gv

        if DEBUG_PRINT:
            print 'enter_next_block2', args_gv

        r = Label(args_gv)
        self.insns.append(insn.Label(r))
        return r

    def jump_if_false(self, gv_condition, args_gv):
        return self._jump(gv_condition, False, args_gv)

    def jump_if_true(self, gv_condition, args_gv):
        return self._jump(gv_condition, True, args_gv)

    def finish_and_return(self, sigtoken, gv_returnvar):
        self.insns.append(insn.Return(gv_returnvar))
        self.allocate_and_emit([])

        # standard epilogue:

        # restore old SP
        self.asm.lwz(rSP, rSP, 0)
        # restore all callee-save GPRs
        self.asm.lmw(gprs[32-NSAVEDREGISTERS].number, rSP, -4*(NSAVEDREGISTERS+1))
        # restore Condition Register
        self.asm.lwz(rSCRATCH, rSP, 4)
        self.asm.mtcr(rSCRATCH)
        # restore Link Register and jump to it
        self.asm.lwz(rSCRATCH, rSP, 8)
        self.asm.mtlr(rSCRATCH)
        self.asm.blr()

        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        if target.min_stack_offset == 1:
            self.pause_writing(outputargs_gv)
            self.start_writing()
        allocator = self.allocate(outputargs_gv)
        if DEBUG_PRINT:
            before_moves = len(self.insns)
            print outputargs_gv
            print target.args_gv
        allocator.spill_offset = min(allocator.spill_offset, target.min_stack_offset)
        prepare_for_jump(
            self.insns, outputargs_gv, allocator.var2loc, target, allocator)
        if DEBUG_PRINT:
            print 'moves:'
            for i in self.insns[before_moves:]:
                print ' ', i
        self.emit(allocator)
        here_size = self._stack_size(allocator.spill_offset)
        there_size = self._stack_size(target.min_stack_offset)
        if here_size != there_size:
            self.emit_stack_adjustment(there_size)
            if self.rgenop.DEBUG_SCRIBBLE:
                if here_size > there_size:
                    offsets = range(there_size, here_size, 4)
                else:
                    offsets = range(here_size, there_size, 4)
                for offset in offsets:
                    self.asm.load_word(rSCRATCH, 0x23456789)
                    self.asm.stw(rSCRATCH, rSP, -offset)
        self.asm.load_word(rSCRATCH, target.startaddr)
        self.asm.mtctr(rSCRATCH)
        self.asm.bctr()
        self._close()

    def flexswitch(self, gv_exitswitch, args_gv):
        # make sure the exitswitch ends the block in a register:
        crresult = Var()
        self.insns.append(insn.FakeUse(crresult, gv_exitswitch))
        allocator = self.allocate_and_emit(args_gv)
        switch_mc = self.asm.mc.reserve(7 * 5 + 4)
        self._close()
        result = FlexSwitch(self.rgenop, switch_mc,
                            allocator.loc_of(gv_exitswitch),
                            allocator.loc_of(crresult),
                            allocator.var2loc,
                            allocator.spill_offset)
        return result, result.add_default()

    def start_writing(self):
        if not self.closed:
            return self
        assert self.asm.mc is None
        if self.final_jump_addr != 0:
            mc = self.rgenop.open_mc()
            target = mc.tell()
            if target == self.final_jump_addr + 16:
                mc.setpos(mc.getpos()-4)
            else:
                self.asm.mc = self.rgenop.ExistingCodeBlock(
                    self.final_jump_addr, self.final_jump_addr+8)
                self.asm.load_word(rSCRATCH, target)
            self.asm.mc = mc
            self.final_jump_addr = 0
            self.closed = False
            return self
        else:
            self._open()
            self.maybe_patch_start_here()
            return self

    def maybe_patch_start_here(self):
        if self.patch_start_here:
            mc = self.asm.mc
            self.asm.mc = self.rgenop.ExistingCodeBlock(
                self.patch_start_here, self.patch_start_here+8)
            self.asm.load_word(rSCRATCH, mc.tell())
            self.asm.mc = mc
            self.patch_start_here = 0

    def pause_writing(self, args_gv):
        allocator = self.allocate_and_emit(args_gv)
        self.initial_var2loc = allocator.var2loc
        self.initial_spill_offset = allocator.spill_offset
        self.insns = []
        self.max_param_space = -1
        self.final_jump_addr = self.asm.mc.tell()
        self.closed = True
        self.asm.nop()
        self.asm.nop()
        self.asm.mtctr(rSCRATCH)
        self.asm.bctr()
        self._close()
        return self

    # ----------------------------------------------------------------
    # ppc-specific interface:

    def itemoffset(self, arraytoken, gv_index):
        # if gv_index is constant, this can return a constant...
        lengthoffset, startoffset, itemsize = arraytoken

        gv_offset = Var()
        self.insns.append(
            insn.Insn_GPR__GPR_IMM(RPPCAssembler.mulli,
                                   gv_offset, [gv_index, IntConst(itemsize)]))
        gv_itemoffset = Var()
        self.insns.append(
            insn.Insn_GPR__GPR_IMM(RPPCAssembler.addi,
                               gv_itemoffset, [gv_offset, IntConst(startoffset)]))
        return gv_itemoffset

    def _write_prologue(self, sigtoken):
        numargs = sigtoken     # for now
        if DEBUG_TRAP:
            self.asm.trap()
        inputargs = [Var() for i in range(numargs)]
        assert self.initial_var2loc is None
        self.initial_var2loc = {}
        for arg in inputargs[:8]:
            self.initial_var2loc[arg] = gprs[3+len(self.initial_var2loc)]
        if len(inputargs) > 8:
            for i in range(8, len(inputargs)):
                arg = inputargs[i]
                self.initial_var2loc[arg] = insn.stack_slot(24 + 4 * len(self.initial_var2loc))
        self.initial_spill_offset = self._var_offset(0)

        # Standard prologue:

        # Minimum stack space = 24+params+lv+4*GPRSAVE+8*FPRSAVE
        #   params = stack space for parameters for functions we call
        #   lv = stack space for local variables
        #   GPRSAVE = the number of callee-save GPRs we save, currently
        #             NSAVEDREGISTERS which is 19, i.e. all of them
        #   FPRSAVE = the number of callee-save FPRs we save, currently 0
        # Initially, we set params == lv == 0 and allow each basic block to
        # ensure it has enough space to continue.

        minspace = self._stack_size(self._var_offset(0))
        # save Link Register
        self.asm.mflr(rSCRATCH)
        self.asm.stw(rSCRATCH, rSP, 8)
        # save Condition Register
        self.asm.mfcr(rSCRATCH)
        self.asm.stw(rSCRATCH, rSP, 4)
        # save the callee-save GPRs
        self.asm.stmw(gprs[32-NSAVEDREGISTERS].number, rSP, -4*(NSAVEDREGISTERS + 1))
        # set up frame pointer
        self.asm.mr(rFP, rSP)
        # save stack pointer into linkage area and set stack pointer for us.
        self.asm.stwu(rSP, rSP, -minspace)

        if self.rgenop.DEBUG_SCRIBBLE:
            # write junk into all non-argument, non rFP or rSP registers
            self.asm.load_word(rSCRATCH, 0x12345678)
            for i in range(min(11, 3+len(self.initial_var2loc)), 32):
                self.asm.load_word(i, 0x12345678)
            # scribble the part of the stack between
            # self._var_offset(0) and minspace
            for offset in range(self._var_offset(0), -minspace, -4):
                self.asm.stw(rSCRATCH, rFP, offset)
            # and then a bit more
            for offset in range(-minspace-4, -minspace-200, -4):
                self.asm.stw(rSCRATCH, rFP, offset)

        return inputargs

    def _var_offset(self, v):
        """v represents an offset into the local variable area in bytes;
        this returns the offset relative to rFP"""
        return -(4*NSAVEDREGISTERS+4+v)

    def _stack_size(self, lv):
        """ Returns the required stack size to store all data, assuming
        that there are 'param' bytes of parameters for callee functions and
        'lv' is the largest (wrt to abs() :) rFP-relative byte offset of
        any variable on the stack.  Plus 4 because the rFP actually points
        into our caller's linkage area."""
        assert lv <= 0
        if self.max_param_space >= 0:
            param = max(self.max_param_space, 32) + 24
        else:
            param = 0
        return ((4 + param - lv + 15) & ~15)

    def _open(self):
        self.asm.mc = self.rgenop.open_mc()
        self._code_start = self.asm.mc.tell()
        self.closed = False

    def _close(self):
        _code_stop = self.asm.mc.tell()
        code_size = _code_stop - self._code_start
        flush_icache(self._code_start, code_size)
        self.rgenop.close_mc(self.asm.mc)
        self.asm.mc = None

    def allocate_and_emit(self, live_vars_gv):
        allocator = self.allocate(live_vars_gv)
        return self.emit(allocator)

    def allocate(self, live_vars_gv):
        assert self.initial_var2loc is not None
        allocator = RegisterAllocation(
            self.rgenop.freeregs,
            self.initial_var2loc,
            self.initial_spill_offset)
        self.insns = allocator.allocate_for_insns(self.insns)
        return allocator

    def emit(self, allocator):
        in_size = self._stack_size(self.initial_spill_offset)
        our_size = self._stack_size(allocator.spill_offset)
        if in_size != our_size:
            assert our_size > in_size
            self.emit_stack_adjustment(our_size)
            if self.rgenop.DEBUG_SCRIBBLE:
                for offset in range(in_size, our_size, 4):
                    self.asm.load_word(rSCRATCH, 0x23456789)
                    self.asm.stw(rSCRATCH, rSP, -offset)
        if self.rgenop.DEBUG_SCRIBBLE:
            locs = {}
            for _, loc in self.initial_var2loc.iteritems():
                locs[loc] = True
            regs = insn.gprs[3:]
            for reg in regs:
                if reg not in locs:
                    self.asm.load_word(reg.number, 0x3456789)
            self.asm.load_word(0, 0x3456789)
            for offset in range(self._var_offset(0),
                                self.initial_spill_offset,
                                -4):
                if insn.stack_slot(offset) not in locs:
                    self.asm.stw(0, rFP, offset)
        for insn_ in self.insns:
            insn_.emit(self.asm)
        for label in allocator.labels_to_tell_spill_offset_to:
            label.min_stack_offset = allocator.spill_offset
        for builder in allocator.builders_to_tell_spill_offset_to:
            builder.initial_spill_offset = allocator.spill_offset
        return allocator

    def emit_stack_adjustment(self, newsize):
        # the ABI requires that at all times that r1 is valid, in the
        # sense that it must point to the bottom of the stack and that
        # executing SP <- *(SP) repeatedly walks the stack.
        # this code satisfies this, although there is a 1-instruction
        # window where such walking would find a strange intermediate
        # "frame"
        self.asm.addi(rSCRATCH, rFP, -newsize)
        self.asm.sub(rSCRATCH, rSCRATCH, rSP)

        # this is a pure debugging check that we avoid the situation
        # where *(r1) == r1 which would violates the ABI rules listed
        # above. after a while it can be removed or maybe made
        # conditional on some --option passed to py.test
        self.asm.tweqi(rSCRATCH, 0)

        self.asm.stwux(rSP, rSP, rSCRATCH)
        self.asm.stw(rFP, rSP, 0)

    def _arg_op(self, gv_arg, opcode):
        gv_result = Var()
        self.insns.append(
            insn.Insn_GPR__GPR(opcode, gv_result, gv_arg))
        return gv_result

    def _arg_arg_op(self, gv_x, gv_y, opcode):
        gv_result = Var()
        self.insns.append(
            insn.Insn_GPR__GPR_GPR(opcode, gv_result, [gv_x, gv_y]))
        return gv_result

    def _arg_simm_op(self, gv_x, gv_imm, opcode):
        assert gv_imm.fits_in_simm()
        gv_result = Var()
        self.insns.append(
            insn.Insn_GPR__GPR_IMM(opcode, gv_result, [gv_x, gv_imm]))
        return gv_result

    def _arg_uimm_op(self, gv_x, gv_imm, opcode):
        assert gv_imm.fits_in_uimm()
        gv_result = Var()
        self.insns.append(
            insn.Insn_GPR__GPR_IMM(opcode, gv_result, [gv_x, gv_imm]))
        return gv_result

    def _arg_arg_op_with_simm(self, gv_x, gv_y, opcode, opcodei,
                             commutative=False):
        if gv_y.fits_in_simm():
            return self._arg_simm_op(gv_x, gv_y, opcodei)
        elif gv_x.fits_in_simm() and commutative:
            return self._arg_simm_op(gv_y, gv_x, opcodei)
        else:
            return self._arg_arg_op(gv_x, gv_y, opcode)

    def _arg_arg_op_with_uimm(self, gv_x, gv_y, opcode, opcodei,
                             commutative=False):
        if gv_y.fits_in_uimm():
            return self._arg_uimm_op(gv_x, gv_y, opcodei)
        elif gv_x.fits_in_uimm() and commutative:
            return self._arg_uimm_op(gv_y, gv_x, opcodei)
        else:
            return self._arg_arg_op(gv_x, gv_y, opcode)

    def _identity(self, gv_arg):
        return gv_arg

    cmp2info = {
        #      bit-in-crf  negated
        'gt': (    1,         0   ),
        'lt': (    0,         0   ),
        'le': (    1,         1   ),
        'ge': (    0,         1   ),
        'eq': (    2,         0   ),
        'ne': (    2,         1   ),
        }

    cmp2info_flipped = {
        #      bit-in-crf  negated
        'gt': (    0,         0   ),
        'lt': (    1,         0   ),
        'le': (    0,         1   ),
        'ge': (    1,         1   ),
        'eq': (    2,         0   ),
        'ne': (    2,         1   ),
        }

    def _compare(self, op, gv_x, gv_y):
        #print "op", op
        gv_result = ConditionVar()
        if gv_y.fits_in_simm():
            self.insns.append(
                insn.CMPWI(self.cmp2info[op], gv_result, [gv_x, gv_y]))
        elif gv_x.fits_in_simm():
            self.insns.append(
                insn.CMPWI(self.cmp2info_flipped[op], gv_result, [gv_y, gv_x]))
        else:
            self.insns.append(
                insn.CMPW(self.cmp2info[op], gv_result, [gv_x, gv_y]))
        return gv_result

    def _compare_u(self, op, gv_x, gv_y):
        gv_result = ConditionVar()
        if gv_y.fits_in_uimm():
            self.insns.append(
                insn.CMPWLI(self.cmp2info[op], gv_result, [gv_x, gv_y]))
        elif gv_x.fits_in_uimm():
            self.insns.append(
                insn.CMPWLI(self.cmp2info_flipped[op], gv_result, [gv_y, gv_x]))
        else:
            self.insns.append(
                insn.CMPWL(self.cmp2info[op], gv_result, [gv_x, gv_y]))
        return gv_result

    def _jump(self, gv_condition, if_true, args_gv):
        targetbuilder = self.rgenop.newbuilder()

        self.insns.append(
            insn.Jump(gv_condition, targetbuilder, if_true, args_gv))

        return targetbuilder

    def _ov(self):
        # mfxer rFOO
        # extrwi rBAR, rFOO, 1, 1
        gv_xer = Var()
        self.insns.append(
            insn.Insn_GPR(_PPC.mfxer, gv_xer))
        gv_ov = Var()
        self.insns.append(insn.Extrwi(gv_ov, gv_xer, 1, 1))
        return gv_ov

    def op_bool_not(self, gv_arg):
        return self._arg_uimm_op(gv_arg, self.rgenop.genconst(1), RPPCAssembler.xori)

    def op_int_is_true(self, gv_arg):
        return self._compare('ne', gv_arg, self.rgenop.genconst(0))

    def op_int_neg(self, gv_arg):
        return self._arg_op(gv_arg, _PPC.neg)

    def raisingop_int_neg_ovf(self, gv_arg):
        gv_result = self._arg_op(gv_arg, _PPC.nego)
        gv_ov = self._ov()
        return (gv_result, gv_ov)

    def op_int_abs(self, gv_arg):
        gv_sign = self._arg_uimm_op(gv_arg, self.rgenop.genconst(31), _PPC.srawi)
        gv_maybe_inverted = self._arg_arg_op(gv_arg, gv_sign, _PPC.xor)
        return self._arg_arg_op(gv_sign, gv_maybe_inverted, _PPC.subf)

    def raisingop_int_abs_ovf(self, gv_arg):
        gv_sign = self._arg_uimm_op(gv_arg, self.rgenop.genconst(31), _PPC.srawi)
        gv_maybe_inverted = self._arg_arg_op(gv_arg, gv_sign, _PPC.xor)
        gv_result = self._arg_arg_op(gv_sign, gv_maybe_inverted, _PPC.subfo)
        return (gv_result, self._ov())

    def op_int_invert(self, gv_arg):
        return self._arg_op(gv_arg, _PPC.not_)

    def op_int_add(self, gv_x, gv_y):
        return self._arg_arg_op_with_simm(gv_x, gv_y, _PPC.add, _PPC.addi,
                                          commutative=True)

    def raisingop_int_add_ovf(self, gv_x, gv_y):
        gv_result = self._arg_arg_op(gv_x, gv_y, _PPC.addo)
        gv_ov = self._ov()
        return (gv_result, gv_ov)

    def op_int_sub(self, gv_x, gv_y):
        return self._arg_arg_op_with_simm(gv_x, gv_y, _PPC.sub, _PPC.subi)

    def raisingop_int_sub_ovf(self, gv_x, gv_y):
        gv_result = self._arg_arg_op(gv_x, gv_y, _PPC.subo)
        gv_ov = self._ov()
        return (gv_result, gv_ov)

    def op_int_mul(self, gv_x, gv_y):
        return self._arg_arg_op_with_simm(gv_x, gv_y, _PPC.mullw, _PPC.mulli,
                                          commutative=True)

    def raisingop_int_mul_ovf(self, gv_x, gv_y):
        gv_result = self._arg_arg_op(gv_x, gv_y, _PPC.mullwo)
        gv_ov = self._ov()
        return (gv_result, gv_ov)

    def op_int_floordiv(self, gv_x, gv_y):
        return self._arg_arg_op(gv_x, gv_y, _PPC.divw)

    ## def op_int_floordiv_zer(self, gv_x, gv_y):

    def op_int_mod(self, gv_x, gv_y):
        gv_dividend = self.op_int_floordiv(gv_x, gv_y)
        gv_z = self.op_int_mul(gv_dividend, gv_y)
        return self.op_int_sub(gv_x, gv_z)

    ## def op_int_mod_zer(self, gv_x, gv_y):

    def op_int_lt(self, gv_x, gv_y):
        return self._compare('lt', gv_x, gv_y)

    def op_int_le(self, gv_x, gv_y):
        return self._compare('le', gv_x, gv_y)

    def op_int_eq(self, gv_x, gv_y):
        return self._compare('eq', gv_x, gv_y)

    def op_int_ne(self, gv_x, gv_y):
        return self._compare('ne', gv_x, gv_y)

    def op_int_gt(self, gv_x, gv_y):
        return self._compare('gt', gv_x, gv_y)

    def op_int_ge(self, gv_x, gv_y):
        return self._compare('ge', gv_x, gv_y)

    op_char_lt = op_int_lt
    op_char_le = op_int_le
    op_char_eq = op_int_eq
    op_char_ne = op_int_ne
    op_char_gt = op_int_gt
    op_char_ge = op_int_ge

    op_unichar_eq = op_int_eq
    op_unichar_ne = op_int_ne

    def op_int_and(self, gv_x, gv_y):
        return self._arg_arg_op(gv_x, gv_y, _PPC.and_)

    def op_int_or(self, gv_x, gv_y):
        return self._arg_arg_op_with_uimm(gv_x, gv_y, _PPC.or_, _PPC.ori,
                                          commutative=True)

    def op_int_lshift(self, gv_x, gv_y):
        if gv_y.fits_in_simm():
            if abs(gv_y.value) >= 32:
                return self.rgenop.genconst(0)
            else:
                return self._arg_uimm_op(gv_x, gv_y, _PPC.slwi)
        # computing x << y when you don't know y is <=32
        # (we can assume y >= 0 though)
        # here's the plan:
        #
        # z = nltu(y, 32) (as per cwg)
        # w = x << y
        # r = w&z
        gv_a = self._arg_simm_op(gv_y, self.rgenop.genconst(32), _PPC.subfic)
        gv_b = self._arg_op(gv_y, _PPC.addze)
        gv_z = self._arg_arg_op(gv_b, gv_y, _PPC.subf)
        gv_w = self._arg_arg_op(gv_x, gv_y, _PPC.slw)
        return self._arg_arg_op(gv_z, gv_w, _PPC.and_)

    ## def op_int_lshift_val(self, gv_x, gv_y):

    def op_int_rshift(self, gv_x, gv_y):
        if gv_y.fits_in_simm():
            if abs(gv_y.value) >= 32:
                gv_y = self.rgenop.genconst(31)
            return self._arg_simm_op(gv_x, gv_y, _PPC.srawi)
        # computing x >> y when you don't know y is <=32
        # (we can assume y >= 0 though)
        # here's the plan:
        #
        # ntlu_y_32 = nltu(y, 32) (as per cwg)
        # o = srawi(x, 31) & ~ntlu_y_32
        # w = (x >> y) & ntlu_y_32
        # r = w|o
        gv_a = self._arg_uimm_op(gv_y, self.rgenop.genconst(32), _PPC.subfic)
        gv_b = self._arg_op(gv_y, _PPC.addze)
        gv_ntlu_y_32 = self._arg_arg_op(gv_b, gv_y, _PPC.subf)

        gv_c = self._arg_uimm_op(gv_x, self.rgenop.genconst(31), _PPC.srawi)
        gv_o = self._arg_arg_op(gv_c, gv_ntlu_y_32, _PPC.andc_)

        gv_e = self._arg_arg_op(gv_x, gv_y, _PPC.sraw)
        gv_w = self._arg_arg_op(gv_e, gv_ntlu_y_32, _PPC.and_)

        return self._arg_arg_op(gv_o, gv_w, _PPC.or_)

    ## def op_int_rshift_val(self, gv_x, gv_y):

    def op_int_xor(self, gv_x, gv_y):
        return self._arg_arg_op_with_uimm(gv_x, gv_y, _PPC.xor, _PPC.xori,
                                          commutative=True)

    ## various int_*_ovfs

    op_uint_is_true = op_int_is_true
    op_uint_invert = op_int_invert

    op_uint_add = op_int_add
    op_uint_sub = op_int_sub
    op_uint_mul = op_int_mul

    def op_uint_floordiv(self, gv_x, gv_y):
        return self._arg_arg_op(gv_x, gv_y, _PPC.divwu)

    ## def op_uint_floordiv_zer(self, gv_x, gv_y):

    def op_uint_mod(self, gv_x, gv_y):
        gv_dividend = self.op_uint_floordiv(gv_x, gv_y)
        gv_z = self.op_uint_mul(gv_dividend, gv_y)
        return self.op_uint_sub(gv_x, gv_z)

    ## def op_uint_mod_zer(self, gv_x, gv_y):

    def op_uint_lt(self, gv_x, gv_y):
        return self._compare_u('lt', gv_x, gv_y)

    def op_uint_le(self, gv_x, gv_y):
        return self._compare_u('le', gv_x, gv_y)

    def op_uint_eq(self, gv_x, gv_y):
        return self._compare_u('eq', gv_x, gv_y)

    def op_uint_ne(self, gv_x, gv_y):
        return self._compare_u('ne', gv_x, gv_y)

    def op_uint_gt(self, gv_x, gv_y):
        return self._compare_u('gt', gv_x, gv_y)

    def op_uint_ge(self, gv_x, gv_y):
        return self._compare_u('ge', gv_x, gv_y)

    op_uint_and = op_int_and
    op_uint_or = op_int_or

    op_uint_lshift = op_int_lshift

    ## def op_uint_lshift_val(self, gv_x, gv_y):

    def op_uint_rshift(self, gv_x, gv_y):
        if gv_y.fits_in_simm():
            if abs(gv_y.value) >= 32:
                return self.rgenop.genconst(0)
            else:
                return self._arg_simm_op(gv_x, gv_y, _PPC.srwi)
        # computing x << y when you don't know y is <=32
        # (we can assume y >=0 though, i think)
        # here's the plan:
        #
        # z = ngeu(y, 32) (as per cwg)
        # w = x >> y
        # r = w&z
        gv_a = self._arg_simm_op(gv_y, self.rgenop.genconst(32), _PPC.subfic)
        gv_b = self._arg_op(gv_y, _PPC.addze)
        gv_z = self._arg_arg_op(gv_b, gv_y, _PPC.subf)
        gv_w = self._arg_arg_op(gv_x, gv_y, _PPC.srw)
        return self._arg_arg_op(gv_z, gv_w, _PPC.and_)
    ## def op_uint_rshift_val(self, gv_x, gv_y):

    op_uint_xor = op_int_xor

    # ... floats ...

    # ... llongs, ullongs ...

    # here we assume that booleans are always 1 or 0 and chars are
    # always zero-padded.

    op_cast_bool_to_int = _identity
    op_cast_bool_to_uint = _identity
    ## def op_cast_bool_to_float(self, gv_arg):
    op_cast_char_to_int = _identity
    op_cast_unichar_to_int = _identity
    op_cast_int_to_char = _identity

    op_cast_int_to_unichar = _identity
    op_cast_int_to_uint = _identity
    ## def op_cast_int_to_float(self, gv_arg):
    ## def op_cast_int_to_longlong(self, gv_arg):
    op_cast_uint_to_int = _identity
    ## def op_cast_uint_to_float(self, gv_arg):
    ## def op_cast_float_to_int(self, gv_arg):
    ## def op_cast_float_to_uint(self, gv_arg):
    ## def op_truncate_longlong_to_int(self, gv_arg):

    # many pointer operations are genop_* special cases above

    op_ptr_eq = op_int_eq
    op_ptr_ne = op_int_ne

    op_ptr_nonzero = op_int_is_true
    op_ptr_ne      = op_int_ne
    op_ptr_eq      = op_int_eq

    def op_ptr_iszero(self, gv_arg):
        return self._compare('eq', gv_arg, self.rgenop.genconst(0))

    op_cast_ptr_to_int     = _identity
    op_cast_int_to_ptr     = _identity

    # ... address operations ...

@specialize.arg(0)
def cast_int_to_whatever(T, value):
    if isinstance(T, lltype.Ptr):
        return lltype.cast_int_to_ptr(T, value)
    elif T is llmemory.Address:
        return llmemory.cast_int_to_adr(value)
    else:
        return lltype.cast_primitive(T, value)

@specialize.arg(0)
def cast_whatever_to_int(T, value):
    if isinstance(T, lltype.Ptr):
        return lltype.cast_ptr_to_int(value)
    elif T is llmemory.Address:
        return llmemory.cast_adr_to_int(value)
    else:
        return lltype.cast_primitive(lltype.Signed, value)

class RPPCGenOp(AbstractRGenOp):

    # the set of registers we consider available for allocation
    # we can artifically restrict it for testing purposes
    freeregs = {
        insn.GP_REGISTER:insn.gprs[3:],
        insn.FP_REGISTER:insn.fprs,
        insn.CR_FIELD:insn.crfs,
        insn.CT_REGISTER:[insn.ctr]}
    DEBUG_SCRIBBLE = option.debug_scribble
    MC_SIZE = 65536

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing
        self.keepalive_gc_refs = []

    # ----------------------------------------------------------------
    # the public RGenOp interface

    def newgraph(self, sigtoken, name):
        numargs = sigtoken          # for now
        builder = self.newbuilder()
        builder._open()
        entrypoint = builder.asm.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, IntConst(entrypoint), inputargs_gv

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"

##     @staticmethod
##     @specialize.genconst(0)
##     def constPrebuiltGlobal(llvalue):

    @staticmethod
    def genzeroconst(kind):
        return zero_const

    def replay(self, label, kinds):
        return ReplayBuilder(self), [dummy_var] * len(kinds)

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        FIELD = getattr(T, name)
        if isinstance(FIELD, lltype.ContainerType):
            fieldsize = 0      # not useful for getsubstruct
        else:
            fieldsize = llmemory.sizeof(FIELD)
        return (llmemory.offsetof(T, name), fieldsize)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        if isinstance(T, lltype.Array):
            return RPPCGenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RPPCGenOp.arrayToken(ARRAYFIELD)
            length_offset, items_offset, item_size = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return (arrayfield_offset+length_offset,
                    arrayfield_offset+items_offset,
                    item_size)

    @staticmethod
    @specialize.memo()
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        if T is lltype.Float:
            py.test.skip("not implemented: floats in the i386^WPPC back-end")
        return None                   # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

    @staticmethod
    @specialize.arg(0)
    def read_frame_var(T, base, info, index):
        """Read from the stack frame of a caller.  The 'base' is the
        frame stack pointer captured by the operation generated by
        genop_get_frame_base().  The 'info' is the object returned by
        get_frame_info(); we are looking for the index-th variable
        in the list passed to get_frame_info()."""
        place = info[index]
        if isinstance(place, StackInfo):
            #print '!!!', base, place.offset
            #print '???', [peek_word_at(base + place.offset + i)
            #              for i in range(-64, 65, 4)]
            assert place.offset != 0
            value = peek_word_at(base + place.offset)
            return cast_int_to_whatever(T, value)
        else:
            assert isinstance(place, GenConst)
            return place.revealconst(T)


    @staticmethod
    @specialize.arg(0)
    def write_frame_place(T, base, place, value):
        assert place.offset != 0
        value = cast_whatever_to_int(T, value)
        poke_word_into(base + place.offset, value)

    @staticmethod
    @specialize.arg(0)
    def read_frame_place(T, base, place):
        value = peek_word_at(base + place.offset)
        return cast_int_to_whatever(T, value)

    def check_no_open_mc(self):
        pass

    # ----------------------------------------------------------------
    # ppc-specific interface:

    MachineCodeBlock = codebuf.OwningMachineCodeBlock
    ExistingCodeBlock = codebuf.ExistingCodeBlock

    def open_mc(self):
        if self.mcs:
            return self.mcs.pop()
        else:
            return self.MachineCodeBlock(self.MC_SIZE)   # XXX supposed infinite for now

    def close_mc(self, mc):
##         from pypy.jit.codegen.ppc.ppcgen.asmfunc import get_ppcgen
##         print '!!!!', cast(mc._data, c_void_p).value
##         print '!!!!', mc._data.contents[0]
##         get_ppcgen().flush2(cast(mc._data, c_void_p).value,
##                             mc._size*4)
        self.mcs.append(mc)

    def newbuilder(self):
        return Builder(self)

# a switch can take 7 instructions:

# load_word rSCRATCH, gv_case.value (really two instructions)
# cmpw crf, rSWITCH, rSCRATCH
# load_word rSCRATCH, targetaddr    (again two instructions)
# mtctr rSCRATCH
# beqctr crf

# yay RISC :/

class FlexSwitch(CodeGenSwitch):

    # a fair part of this code could likely be shared with the i386
    # backend.

    def __init__(self, rgenop, mc, switch_reg, crf, var2loc, initial_spill_offset):
        self.rgenop = rgenop
        self.crf = crf
        self.switch_reg = switch_reg
        self.var2loc = var2loc
        self.initial_spill_offset = initial_spill_offset
        self.asm = RPPCAssembler()
        self.asm.mc = mc
        self.default_target_addr = 0

    def add_case(self, gv_case):
        targetbuilder = self.rgenop.newbuilder()
        targetbuilder._open()
        targetbuilder.initial_var2loc = self.var2loc
        targetbuilder.initial_spill_offset = self.initial_spill_offset
        target_addr = targetbuilder.asm.mc.tell()
        p = self.asm.mc.getpos()
        # that this works depends a bit on the fixed length of the
        # instruction sequences we use to jump around.  if the code is
        # ever updated to use the branch-relative instructions (a good
        # idea, btw) this will need to be thought about again
        try:
            self._add_case(gv_case, target_addr)
        except codebuf.CodeBlockOverflow:
            self.asm.mc.setpos(p)
            mc = self.rgenop.open_mc()
            newmc = mc.reserve(7 * 5 + 4)
            self.rgenop.close_mc(mc)
            new_addr = newmc.tell()
            self.asm.load_word(rSCRATCH, new_addr)
            self.asm.mtctr(rSCRATCH)
            self.asm.bctr()
            self.asm.mc = newmc
            self._add_case(gv_case, target_addr)
        return targetbuilder

    def _add_case(self, gv_case, target_addr):
        asm = self.asm
        assert isinstance(gv_case, GenConst)
        gv_case.load_now(asm, insn.gprs[0])
        asm.cmpw(self.crf.number, rSCRATCH, self.switch_reg.number)
        asm.load_word(rSCRATCH, target_addr)
        asm.mtctr(rSCRATCH)
        asm.bcctr(12, self.crf.number*4 + 2)
        if self.default_target_addr:
            self._write_default()

    def add_default(self):
        targetbuilder = self.rgenop.newbuilder()
        targetbuilder._open()
        targetbuilder.initial_var2loc = self.var2loc
        targetbuilder.initial_spill_offset = self.initial_spill_offset
        self.default_target_addr = targetbuilder.asm.mc.tell()
        self._write_default()
        return targetbuilder

    def _write_default(self):
        pos = self.asm.mc.getpos()
        self.asm.load_word(rSCRATCH, self.default_target_addr)
        self.asm.mtctr(rSCRATCH)
        self.asm.bctr()
        self.asm.mc.setpos(pos)

global_rgenop = RPPCGenOp()
RPPCGenOp.constPrebuiltGlobal = global_rgenop.genconst

def peek_word_at(addr):
    # now the Very Obscure Bit: when translated, 'addr' is an
    # address.  When not, it's an integer.  It just happens to
    # make the test pass, but that's probably going to change.
    if we_are_translated():
        return addr.signed[0]
    else:
        from ctypes import cast, c_void_p, c_int, POINTER
        p = cast(c_void_p(addr), POINTER(c_int))
        return p[0]

def poke_word_into(addr, value):
    # now the Very Obscure Bit: when translated, 'addr' is an
    # address.  When not, it's an integer.  It just happens to
    # make the test pass, but that's probably going to change.
    if we_are_translated():
        addr.signed[0] = value
    else:
        from ctypes import cast, c_void_p, c_int, POINTER
        p = cast(c_void_p(addr), POINTER(c_int))
        p[0] = value

zero_const = AddrConst(llmemory.NULL)
