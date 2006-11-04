from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.jit.codegen.ppc.conftest import option

class AllocationSlot(object):
    pass

class _StackSlot(AllocationSlot):
    is_register = False
    def __init__(self, offset):
        self.offset = offset

_stack_slot_cache = {}
def stack_slot(offset):
    if offset in _stack_slot_cache:
        return _stack_slot_cache[offset]
    _stack_slot_cache[offset] = res = _StackSlot(offset)
    return res

class Register(AllocationSlot):
    is_register = True

class GPR(Register):
    def __init__(self, number):
        self.number = number
    def __repr__(self):
        return 'r' + str(self.number)
gprs = map(GPR, range(32))

class FPR(Register):
    def __init__(self, number):
        self.number = number

fprs = map(GPR, range(32))

class CRF(Register):
    def __init__(self, number):
        self.number = number

crfs = map(CRF, range(8))

class CTR(Register):
    pass

ctr = CTR()

class NullRegister(Register):
    pass

NO_REGISTER = -1
GP_REGISTER = 0
FP_REGISTER = 1
CR_FIELD = 2
CT_REGISTER = 3

class RegisterAllocation:
    def __init__(self, minreg, initial_mapping, initial_spill_offset):
        #print
        #print "RegisterAllocation __init__", initial_mapping
        
        self.insns = []   # Output list of instructions
        self.freeregs = gprs[minreg:] # Registers with dead values
        self.var2loc = {} # Maps a Var to an AllocationSlot
        self.loc2var = {} # Maps an AllocationSlot to a Var
        self.lru = []     # Least-recently-used list of vars; first is oldest.
                          # Contains all vars in registers, and no vars on stack
        self.spill_offset = initial_spill_offset # Where to put next spilled
                                                 # value, relative to rFP,
                                                 # measured in bytes

        # Go through the initial mapping and initialize the data structures
        for var, loc in initial_mapping.iteritems():
            self.loc2var[loc] = var
            self.var2loc[var] = loc
            if loc in self.freeregs:
                self.freeregs.remove(loc)
                self.lru.append(var)
        self.crfinfo = [(0, 0)] * 8

    def spill(self):
        """ Returns an offset onto the stack for an unused spill location """
        # TODO --- reuse spill slots when contained values go dead?
        self.spill_offset -= 4
        return self.spill_offset

    def _allocate_reg(self, newarg):

        # check if there is a register available
        if self.freeregs:
            reg = self.freeregs.pop()
            self.loc2var[reg] = newarg
            self.var2loc[newarg] = reg
            #print "allocate_reg: Putting %r into fresh register %r" % (newarg, reg)
            return reg

        # if not, find something to spill
        argtospill = self.lru.pop(0)
        reg = self.var2loc[argtospill]
        assert reg.is_register

        # Move the value we are spilling onto the stack, both in the
        # data structures and in the instructions:
        spill = stack_slot(self.spill())
        self.var2loc[argtospill] = spill
        self.loc2var[spill] = argtospill
        self.insns.append(Spill(argtospill, reg, spill))
        #print "allocate_reg: Spilled %r to %r." % (argtospill, spill)

        # If the value is currently on the stack, load it up into the
        # register we are putting it into
        if newarg in self.var2loc:
            spill = self.var2loc[newarg]
            assert not spill.is_register
            self.insns.append(Unspill(newarg, reg, spill))
            del self.loc2var[spill] # not stored there anymore, reuse??
            #print "allocate_reg: Unspilled %r from %r." % (newarg, spill)

        # Update data structures to put newarg into the register
        self.var2loc[newarg] = reg
        self.loc2var[reg] = newarg
        #print "allocate_reg: Put %r in stolen reg %r." % (newarg, reg)
        return reg

    def _promote(self, arg):
        if arg in self.lru:
            self.lru.remove(arg)
        self.lru.append(arg)

    def allocate_for_insns(self, insns):
        # Walk through instructions in forward order
        for insn in insns:

            #print "Processing instruction %r with args %r and result %r:" % (insn, insn.reg_args, insn.result)

            #print "LRU list was: %r" % (self.lru,)

            # put things into the lru
            for i in range(len(insn.reg_args)):
                arg = insn.reg_args[i]
                argcls = insn.reg_arg_regclasses[i]
                if argcls == GP_REGISTER:
                    self._promote(arg)
            if insn.result and insn.result_regclass == GP_REGISTER:
                self._promote(insn.result)
            #print "LRU list is now: %r" % (self.lru,)

            # We need to allocate a register for each used
            # argument that is not already in one
            for i in range(len(insn.reg_args)):
                arg = insn.reg_args[i]
                argcls = insn.reg_arg_regclasses[i]
                #print "Allocating register for %r..." % (arg,)

                if not self.var2loc[arg].is_register:
                    # It has no register now because it has been spilled
                    assert argcls is GP_REGISTER, "uh-oh"
                    self._allocate_reg(arg)
                else:
                    #print "it was in ", self.var2loc[arg]
                    pass

            # Need to allocate a register for the destination
            assert not insn.result or insn.result not in self.var2loc
            cand = None
            if insn.result_regclass is GP_REGISTER:
                #print "Allocating register for result %r..." % (insn.result,)
                cand = self._allocate_reg(insn.result)
            elif insn.result_regclass is CR_FIELD:
                assert crfs[0] not in self.loc2var
                assert isinstance(insn, CMPInsn)
                cand = crfs[0]
                self.crfinfo[0] = insn.info
            elif insn.result_regclass is CT_REGISTER:
                assert ctr not in self.loc2var
                cand = ctr
            elif insn.result_regclass is not NO_REGISTER:
                assert 0
            if cand is not None and cand not in self.loc2var:
                self.var2loc[insn.result] = cand
                self.loc2var[cand] = insn.result
            else:
                assert cand is None or self.loc2var[cand] is insn.result
            insn.allocate(self)
            self.insns.append(insn)
        return self.insns

_var_index = [0]
class Var(GenVar):
    def __init__(self):
        self.__magic_index = _var_index[0]
        _var_index[0] += 1
    def load(self, builder):
        return self
    def __repr__(self):
        return "<Var %d>" % self.__magic_index

class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def load(self, builder):
        var = builder.newvar()
        builder.insns.append(
            Insn_GPR__IMM(RPPCAssembler.load_word,
                          var, [self]))
        return var

    def load_now(self, asm, loc):
        if loc.is_register:
            asm.load_word(loc.number, self.value)
        else:
            asm.load_word(rSCRATCH, self.value)
            asm.stw(rSCRATCH, rFP, loc.offset)

class Insn(object):
    '''
    result is the Var instance that holds the result, or None
    result_regclass is the class of the register the result goes into

    reg_args is the vars that need to have registers allocated for them
    reg_arg_regclasses is the type of register that needs to be allocated
    '''
    def __init__(self):
        self.__magic_index = _var_index[0]
        _var_index[0] += 1
    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__, self.__magic_index)

class Insn_GPR__GPR_GPR(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2loc[self.result]
        self.arg_reg1 = allocator.var2loc[self.reg_args[0]]
        self.arg_reg2 = allocator.var2loc[self.reg_args[1]]

    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg1.number,
                     self.arg_reg2.number)

class Insn_GPR__GPR_IMM(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr
        self.imm = args[1]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]
    def allocate(self, allocator):
        self.result_reg = allocator.var2loc[self.result]
        self.arg_reg = allocator.var2loc[self.reg_args[0]]
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg.number,
                     self.imm.value)

class Insn_GPR__IMM(Insn):
    def __init__(self, methptr, result, args):
        Insn.__init__(self)
        self.methptr = methptr
        self.imm = args[0]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = []
        self.reg_arg_regclasses = []
    def allocate(self, allocator):
        self.result_reg = allocator.var2loc[self.result]
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.imm.value)

class CMPInsn(Insn):
    info = (0,0) # please the annotator for tests that don't use CMPW/CMPWI
    pass

class CMPW(CMPInsn):
    def __init__(self, info, result, args):
        Insn.__init__(self)
        self.info = info

        self.result = result
        self.result_regclass = CR_FIELD

        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2loc[self.result]
        self.arg_reg1 = allocator.var2loc[self.reg_args[0]]
        self.arg_reg2 = allocator.var2loc[self.reg_args[1]]

    def emit(self, asm):
        asm.cmpw(self.result_reg.number, self.arg_reg1.number, self.arg_reg2.number)

class CMPWI(CMPInsn):
    def __init__(self, info, result, args):
        Insn.__init__(self)
        self.info = info
        self.imm = args[1]

        self.result = result
        self.result_regclass = CR_FIELD

        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2loc[self.result]
        self.arg_reg = allocator.var2loc[self.reg_args[0]]

    def emit(self, asm):
        asm.cmpwi(self.result_reg.number, self.arg_reg.number, self.imm.value)

class MTCTR(Insn):
    def __init__(self, result, args):
        Insn.__init__(self)
        self.result = result
        self.result_regclass = CT_REGISTER

        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER]

    def allocate(self, allocator):
        self.arg_reg = allocator.var2loc[self.reg_args[0]]

    def emit(self, asm):
        asm.mtctr(self.arg_reg.number)

class Jump(Insn):
    def __init__(self, gv_cond, gv_target, jump_if_true):
        Insn.__init__(self)
        self.gv_cond = gv_cond
        self.gv_target = gv_target
        self.jump_if_true = jump_if_true

        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg_args = [gv_cond, gv_target]
        self.reg_arg_regclasses = [CR_FIELD, CT_REGISTER]
    def allocate(self, allocator):
        assert allocator.var2loc[self.reg_args[1]] is ctr
        self.crf = allocator.var2loc[self.reg_args[0]]
        self.bit, self.negated = allocator.crfinfo[self.crf.number]
    def emit(self, asm):
        if self.negated ^ self.jump_if_true:
            BO = 12 # jump if relavent bit is set in the CR
        else:
            BO = 4  # jump if relavent bit is NOT set in the CR
        asm.bcctr(BO, self.bit)

class Unspill(Insn):
    """ A special instruction inserted by our register "allocator."  It
    indicates that we need to load a value from the stack into a register
    because we spilled a particular value. """
    def __init__(self, var, reg, stack):
        """
        var --- the var we spilled (a Var)
        reg --- the reg we spilled it from (an integer)
        offset --- the offset on the stack we spilled it to (an integer)
        """
        Insn.__init__(self)
        self.var = var
        self.reg = reg
        self.stack = stack
    def emit(self, asm):
        asm.lwz(self.reg.number, rFP, self.stack.offset)

class Spill(Insn):
    """ A special instruction inserted by our register "allocator."
    It indicates that we need to store a value from the register into
    the stack because we spilled a particular value."""
    def __init__(self, var, reg, stack):
        """
        var --- the var we are spilling (a Var)
        reg --- the reg we are spilling it from (an integer)
        offset --- the offset on the stack we are spilling it to (an integer)
        """
        Insn.__init__(self)
        self.var = var
        self.reg = reg
        self.stack = stack
    def emit(self, asm):
        asm.stw(self.reg.number, rFP, self.stack.offset)

class Return(Insn):
    """ Ensures the return value is in r3 """
    def __init__(self, var):
        Insn.__init__(self)
        self.var = var
        self.reg_args = [self.var]
        self.reg_arg_regclasses = [GP_REGISTER]
        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg = None
    def allocate(self, allocator):
        self.reg = allocator.var2loc[self.var]
    def emit(self, asm):
        if self.reg.number != 3:
            asm.mr(r3, self.reg.number)

from pypy.jit.codegen.ppc import codebuf_posix as memhandler
from ctypes import POINTER, cast, c_char, c_void_p, CFUNCTYPE, c_int

class CodeBlockOverflow(Exception):
    pass

from pypy.translator.asm.ppcgen.rassemblermaker import make_rassembler
from pypy.translator.asm.ppcgen.ppc_assembler import MyPPCAssembler

RPPCAssembler = make_rassembler(MyPPCAssembler)

r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, \
    r13, r14, r15, r16, r17, r18, r19, r20, r21, r22, \
    r23, r24, r25, r26, r27, r28, r29, r30, r31 = range(32)
rSCRATCH = r0
rSP = r1
rFP = r2 # the ABI doesn't specify a frame pointer.  however, we want one

def emit(self, value):
    self.mc.write(value)
RPPCAssembler.emit = emit

class CycleData:
    # tar2src  -> map target var to source var
    # src2tar  -> map source var to target var (!)
    # tar2loc  -> map target var to location
    # src2loc  -> map source var to location
    # loc2src  -> map location to source var
    # srcstack -> list of source vars
    # freshctr -> how many fresh locations have we made so far
    # emitted  -> list of emitted targets
    pass

def emit_moves(gen, tar2src, tar2loc, src2loc):

    # Basic idea:
    #
    #   Construct a dependency graph, with a node for each move (Ti <-
    #   Si).  Add an edge between two nodes i and j if loc[Ti] ==
    #   loc[Sj].  (If executing the node's move would overwrite the
    #   source for another move).  If there are no cycles, then a
    #   simple tree walk will suffice.  If there *ARE* cycles, however,
    #   something more is needed.
    #
    #   In a nutshell, the algorithm is to walk the tree, and whenever
    #   a backedge is detected break the cycle by creating a fresh
    #   location and remapping the source of the node so that it no
    #   longer conflicts.  So, if you are in node i, and you detect a
    #   cycle involving node j (so, Ti and Sj are the same location),
    #   then you create a fresh location Sn.  You move Sj to Sn, and
    #   remap node j so that instead of being Tj <- Sj it is Tj <- Sn.
    #   Now there is no need for the backedge, so you can continue.
    #   Whenever you have visited every edge going out from a node, all of
    #   its dependent moves have been performed, so you can emit the
    #   node's move and return.

    tarvars = tar2src.keys()
    
    data = CycleData()
    data.tar2src = tar2src
    data.src2tar = {}
    data.tar2loc = tar2loc
    data.src2loc = src2loc
    data.loc2src = {}
    data.srcstack = []
    data.freshctr = 0
    data.emitted = []

    for tar, src in tar2src.items():
        data.src2tar[src] = tar

    for src, loc in src2loc.items():
        if src in data.src2tar:
            data.loc2src[loc] = src

    for tarvar in tarvars:
        _cycle_walk(gen, tarvar, data)
            
    return data

def _cycle_walk(gen, tarvar, data):

    if tarvar in data.emitted: return

    tarloc = data.tar2loc[tarvar]
    srcvar = data.tar2src[tarvar]
    srcloc = data.src2loc[srcvar]

    # if location we are about to write to is not going to be read
    # by anyone, we are safe
    if tarloc not in data.loc2src:
        gen.emit_move(tarloc, srcloc)
        data.emitted.append(tarvar)
        return

    # Find source node that conflicts with us
    conflictsrcvar = data.loc2src[tarloc]

    if conflictsrcvar not in data.srcstack:
        # No cycle on our stack yet
        data.srcstack.append(srcvar)
        _cycle_walk(gen, data.src2tar[conflictsrcvar], data)
        srcloc = data.src2loc[srcvar] # warning: may have changed, so reload
        gen.emit_move(tarloc, srcloc)
        data.emitted.append(tarvar)
        return 
    
    # Cycle detected, break it by moving the other node's source data
    # somewhere else so we can overwrite it
    freshloc = gen.create_fresh_location()
    conflictsrcloc = data.src2loc[conflictsrcvar]
    gen.emit_move(freshloc, conflictsrcloc)
    data.src2loc[conflictsrcvar] = freshloc
    gen.emit_move(tarloc, srcloc) # now safe to do our move
    data.emitted.append(tarvar)
    return

class JumpPatchupGenerator(object):

    def __init__(self, asm, min_offset):
        self.asm = asm
        self.min_offset = min_offset

    def emit_move(self, tarloc, srcloc):
        if tarloc == srcloc: return
        if tarloc.is_register and srcloc.is_register:
            self.asm.mr(tarloc.number, srcloc.number)
        elif tarloc.is_register and not srcloc.is_register:
            self.asm.lwz(tarloc.number, rFP, srcloc.offset)
        elif not tarloc.is_register and srcloc.is_register:
            self.asm.stw(srcloc.number, rFP, tarloc.offset)
        elif not tarloc.is_register and not srcloc.is_register:
            self.asm.lwz(rSCRATCH, rFP, srcloc.offset)
            self.asm.stw(rSCRATCH, rFP, tarloc.offset)

    def create_fresh_location(self):
        r = self.min_offset
        self.min_offset -= 4
        return stack_slot(r)

def prepare_for_jump(asm, min_offset, sourcevars, src2loc, target):

    tar2src = {}     # tar var -> src var
    tar2loc = {}

    # construct mapping of targets to sources; note that "target vars"
    # and "target locs" are the same thing right now
    targetlocs = target.arg_locations
    for i in range(len(targetlocs)):
        tloc = targetlocs[i]
        tar2loc[tloc] = tloc
        tar2src[tloc] = sourcevars[i]

    gen = JumpPatchupGenerator(asm, min_offset)
    emit_moves(gen, tar2src, tar2loc, src2loc)
    return gen.min_offset

class MachineCodeBlock:

    def __init__(self, map_size):
        assert map_size % 4 == 0
        res = memhandler.alloc(map_size)
        self._data = cast(res, POINTER(c_int * (map_size / 4)))
        self._size = map_size/4
        self._pos = 0

    def write(self, data):
         p = self._pos
         if p >= self._size:
             raise CodeBlockOverflow
         self._data.contents[p] = data
         self._pos = p + 1

    def tell(self):
        baseaddr = cast(self._data, c_void_p).value
        return baseaddr + self._pos * 4

    def __del__(self):
        memhandler.free(cast(self._data, memhandler.PTR), self._size * 4)

##     def execute(self, arg1, arg2):
##         fnptr = cast(self._data, binaryfn)
##         return fnptr(arg1, arg2)

## binaryfn = CFUNCTYPE(c_int, c_int, c_int)    # for testing

class Label(GenLabel):

    def __init__(self, startaddr, arg_locations, min_stack_offset):
        self.startaddr = startaddr
        self.arg_locations = arg_locations
        self.min_stack_offset = min_stack_offset

## class FlexSwitch(CodeGenSwitch):

##     def __init__(self, rgenop):
##         self.rgenop = rgenop
##         self.default_case_addr = 0

##     def initialize(self, builder, gv_exitswitch):
##         self.switch_reg = gv_exitswitch.load(builder)
##         self.saved_state = builder._save_state()
##         self._reserve(mc)

##     def _reserve(self, mc):
##         RESERVED = 11 # enough for 5 cases and a default
##         pos = mc.tell()
##         for i in range(RESERVED):
##             mc.write(0)
##         self.nextfreepos = pos
##         self.endfreepos = pos + RESERVED * 4

##     def _reserve_more(self):
##         XXX
##         start = self.nextfreepos
##         end   = self.endfreepos
##         newmc = self.rgenop.open_mc()
##         self._reserve(newmc)
##         self.rgenop.close_mc(newmc)
##         fullmc = InMemoryCodeBuilder(start, end)
##         a = RPPCAssembler()
##         a.mc = newmc
##         fullmc.ba(rel32(self.nextfreepos))
##         fullmc.done()

##     def add_case(self, gv_case):
##     def add_default(self):

class Builder(GenBuilder):

    def __init__(self, rgenop, mc):
        self.rgenop = rgenop
        self.asm = RPPCAssembler()
        self.asm.mc = mc
        self.insns = []
        self.stack_adj_addr = 0
        self.initial_spill_offset = 0
        self.initial_var2loc = None
        self.fresh_from_jump = False

    def make_fresh_from_jump(self, initial_var2loc):
        self.fresh_from_jump = True
        self.initial_var2loc = initial_var2loc

    def _write_prologue(self, sigtoken):
        numargs = sigtoken     # for now
        if not we_are_translated() and option.trap:
            self.asm.trap()
        inputargs = [self.newvar() for i in range(numargs)]
        assert self.initial_var2loc is None
        self.initial_var2loc = {}
        for arg in inputargs:
            self.initial_var2loc[arg] = gprs[3+len(self.initial_var2loc)]
        self.initial_spill_offset = self._var_offset(0)

        # Emit standard prologue
        #   Minimum space = 24+params+lv+4*GPR+8*FPR
        #   GPR=19
        # Initially, we allocate only enough space for GPRs, and allow
        # each basic block to ensure it has enough space to continue.
        minspace = self._stack_size(0,self._var_offset(0))
        self.asm.mflr(rSCRATCH)
        self.asm.stw(rSCRATCH,rSP,8)
        self.asm.stmw(r13,rSP,-(4*20))     # save all regs from 13-31 to stack
        self.asm.mr(rFP, rSP)              # set up our frame pointer
        self.asm.stwu(rSP,rSP,-minspace)

        return inputargs

    def _var_offset(self, v):
        """v represents an offset into the local variable area in bytes;
        this returns the offset relative to rFP"""
        return -(4*19+4+v)

    def _stack_size(self, param, lv):
        """ Returns the required stack size to store all data, assuming
        that there are 'param' bytes of parameters for callee functions and
        'lv' is the largest (wrt to abs() :) rFP-relative byte offset of
        any variable on the stack."""
        return ((24 + param - lv) & ~15)+16

    def _close(self):
        self.rgenop.close_mc(self.asm.mc)
        self.asm.mc = None

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def allocate_and_emit(self):
        assert self.initial_var2loc is not None
        allocator = RegisterAllocation(
            self.rgenop.MINUSERREG, self.initial_var2loc, self.initial_spill_offset)
        self.insns = allocator.allocate_for_insns(self.insns)
        if self.insns:
            self.patch_stack_adjustment(self._stack_size(0, allocator.spill_offset))
        for insn in self.insns:
            insn.emit(self.asm)
        return allocator

    def finish_and_return(self, sigtoken, gv_returnvar):
        gv_returnvar = gv_returnvar.load(self)
        self.insns.append(Return(gv_returnvar))
        allocator = self.allocate_and_emit()

        # Emit standard epilogue:
        self.asm.lwz(rSP,rSP,0)      # restore old SP
        self.asm.lmw(r13,rSP,-4*20)  # restore all GPRs
        self.asm.lwz(rSCRATCH,rSP,8) # load old Link Register and jump to it
        self.asm.mtlr(rSCRATCH)      #
        self.asm.blr()               #
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        allocator = self.allocate_and_emit()
        min_offset = min(allocator.spill_offset, target.min_stack_offset)
        min_offset = prepare_for_jump(
            self.asm, min_offset, outputargs_gv, allocator.var2loc, target)
        self.patch_stack_adjustment(self._stack_size(0, min_offset))
        self.asm.load_word(rSCRATCH, target.startaddr)
        self.asm.mtctr(rSCRATCH)
        self.asm.bctr()
        self._close()

    def emit_stack_adjustment(self):
        # the ABI requires that at all times that r1 is valid, in the
        # sense that it must point to the bottom of the stack and that
        # executing SP <- *(SP) repeatedly walks the stack.
        # this code satisfies this, although there is a 1-instruction
        # window where such walking would find a strange intermediate
        # "frame" (apart from when the delta is 0... XXX)
        # as we emit these instructions waaay before doing the
        # register allocation for this block we don't know how much
        # stack will be required, so we patch it later (see
        # patch_stack_adjustment below).
        self.stack_adj_addr = self.asm.mc.tell()
        self.asm.addi(rSCRATCH, rFP, 0) # this is the immediate that later gets patched
        self.asm.sub(rSCRATCH, rSCRATCH, rSP) # rSCRATCH should now be <= 0
        self.asm.stwux(rSP, rSP, rSCRATCH)
        self.asm.stw(rFP, rSP, 0)

    def patch_stack_adjustment(self, newsize):
        if self.stack_adj_addr == 0:
            return
        # we build an addi instruction by hand here
        opcode = 14 << 26
        rD = rSCRATCH << 21
        rA = rFP << 16
        # if we decided to use r0 as the frame pointer, this would
        # emit addi rFOO, r0, SIMM which would just load SIMM into
        # rFOO and be "unlikely" to work
        assert rA != 0
        SIMM = (-newsize) & 0xFFFF
        p_instruction = cast(c_void_p(self.stack_adj_addr), POINTER(c_int*1))
        p_instruction.contents[0] = opcode | rD | rA | SIMM

    def enter_next_block(self, kinds, args_gv):
        if self.fresh_from_jump:
            var2loc = self.initial_var2loc
            self.fresh_from_jump = False
        else:
            var2loc = self.allocate_and_emit().var2loc

        #print "enter_next_block:", args_gv, var2loc

        min_stack_offset = self._var_offset(0)
        usedregs = {}
        livevar2loc = {}
        for gv in args_gv:
            if isinstance(gv, Var):
                assert gv in var2loc
                loc = var2loc[gv]
                livevar2loc[gv] = loc
                if not loc.is_register:
                    min_stack_offset = min(min_stack_offset, loc.offset)
                else:
                    usedregs[loc] = None # XXX use this

        unusedregs = [loc for loc in gprs[self.rgenop.MINUSERREG:] if loc not in usedregs]
        arg_locations = []

        for i in range(len(args_gv)):
            gv = args_gv[i]
            if isinstance(gv, Var):
                arg_locations.append(livevar2loc[gv])
            else:
                if unusedregs:
                    loc = unusedregs.pop()
                else:
                    loc = stack_slot(min_stack_offset)
                    min_stack_offset -= 4
                gv.load_now(self.asm, loc)
                args_gv[i] = gv = Var()
                livevar2loc[gv] = loc
                arg_locations.append(loc)

        #print livevar2loc

        self.insns = []
        self.initial_var2loc = livevar2loc
        self.initial_spill_offset = min_stack_offset
        target_addr = self.asm.mc.tell()
        self.emit_stack_adjustment()
        return Label(target_addr, arg_locations, min_stack_offset)

    def newvar(self):
        gv = Var()
        return gv

    def new_and_load_2(self, gv_x, gv_y):
        gv_result = self.newvar()
        return (gv_result, gv_x.load(self), gv_y.load(self))

    def new_and_load_1(self, gv_x):
        gv_result = self.newvar()
        return (gv_result, gv_x.load(self))

    def op_int_mul(self, gv_x, gv_y):
        gv_result, gv_x, gv_y = self.new_and_load_2(gv_x, gv_y)
        self.insns.append(
            Insn_GPR__GPR_GPR(RPPCAssembler.mullw,
                              gv_result, [gv_x, gv_y]))
        return gv_result        

    def op_int_add(self, gv_x, gv_y):
        if isinstance(gv_y, IntConst) and abs(gv_y.value) < 2**16:
            gv_result = self.newvar()
            self.insns.append(
                Insn_GPR__GPR_IMM(RPPCAssembler.addi,
                                  gv_result, [gv_x.load(self), gv_y]))
            return gv_result
        elif isinstance(gv_x, IntConst):
            return self.op_int_add(gv_y, gv_x)
        else:
            gv_result = self.newvar()
            self.insns.append(
                Insn_GPR__GPR_GPR(RPPCAssembler.add,
                                  gv_result, [gv_x.load(self), gv_y.load(self)]))
            return gv_result

    def op_int_sub(self, gv_x, gv_y):
        gv_result, gv_x, gv_y = self.new_and_load_2(gv_x, gv_y)
        self.insns.append(
            Insn_GPR__GPR_GPR(RPPCAssembler.sub,
                              gv_result, [gv_x, gv_y]))
        return gv_result

    def op_int_floordiv(self, gv_x, gv_y):
        gv_result, gv_x, gv_y = self.new_and_load_2(gv_x, gv_y)
        self.insns.append(
            Insn_GPR__GPR_GPR(RPPCAssembler.divw,
                              gv_result, [gv_x.load(self), gv_y.load(self)]))
        return gv_result

    def _compare(self, op, gv_x, gv_y):
        assert op == 'gt'
        result = self.newvar()
        if isinstance(gv_y, IntConst) and abs(gv_y.value) < 2*16:
            gv_x = gv_x.load(self)
            self.insns.append(CMPWI((1, 0), result, [gv_x, gv_y]))
        elif isinstance(gv_x, IntConst) and abs(gv_x.value) < 2*16:
            gv_y = gv_y.load(self)
            self.insns.append(CMPWI((1, 1), result, [gv_y, gv_x]))
        else:
            self.insns.append(CMPW((1, 0), result, [gv_x.load(self), gv_y.load(self)]))
        return result

    def op_int_gt(self, gv_x, gv_y):
        return self._compare('gt', gv_x, gv_y)

    def _jump(self, gv_condition, if_true):
        targetbuilder = self._fork()

        gv = self.newvar()
        self.insns.append(
            Insn_GPR__IMM(RPPCAssembler.load_word,
                          gv, [IntConst(targetbuilder.asm.mc.tell())]))
        gv2 = self.newvar()
        self.insns.append(
            MTCTR(gv2, [gv]))
        self.insns.append(
            Jump(gv_condition, gv2, if_true))

        allocator = self.allocate_and_emit()
        self.make_fresh_from_jump(allocator.var2loc)
        targetbuilder.make_fresh_from_jump(allocator.var2loc)

        return targetbuilder

    def jump_if_false(self, gv_condition):
        return self._jump(gv_condition, False)

    def jump_if_true(self, gv_condition):
        return self._jump(gv_condition, True)

    def _fork(self):
        return self.rgenop.openbuilder()


class RPPCGenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock

    # minimum register we will use for register allocation
    # we can artifically restrict it for testing purposes
    MINUSERREG = 3

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing

    def open_mc(self):
        if self.mcs:
            return self.mcs.pop()
        else:
            return MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        return None     # for now

    def openbuilder(self):
        return Builder(self, self.open_mc())

    def newgraph(self, sigtoken):
        numargs = sigtoken          # for now
        builder = self.openbuilder()
        entrypoint = builder.asm.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, entrypoint, inputargs_gv


    @staticmethod
    @specialize.genconst(0)
    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        if isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
##         elif T is llmemory.Address:
##             return AddrConst(llvalue)
##         elif isinstance(T, lltype.Ptr):
##             return AddrConst(llmemory.cast_ptr_to_adr(llvalue))
        else:
            assert 0, "XXX not implemented"

    def gencallableconst(self, sigtoken, name, entrypointaddr):
        return IntConst(entrypointaddr)
