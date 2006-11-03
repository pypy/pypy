from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.jit.codegen.ppc.conftest import option

class Register(object):
    def __init__(self):
        pass

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
    def __init__(self, initial_mapping):
        self.insns = []
        self.reg2var = {}
        self.var2reg = {}
        for var, reg in initial_mapping.iteritems():
            self.reg2var[reg] = var
            self.var2reg[var] = reg
        self.crfinfo = [(0, 0)] * 8
    def allocate_for_insns(self, insns):
        for insn in insns:
            for i in range(len(insn.reg_args)):
                arg = insn.reg_args[i]
                argcls = insn.reg_arg_regclasses[i]
                assert arg in self.var2reg
            cand = None
            if insn.result_regclass is GP_REGISTER:
                for cand in gprs[3:]:
                    if cand not in self.reg2var:
                        break
                if not cand:
                    assert 0
            elif insn.result_regclass is CR_FIELD:
                assert crfs[0] not in self.reg2var
                cand = crfs[0]
                self.crfinfo[0] = insn.info
            elif insn.result_regclass is CT_REGISTER:
                assert ctr not in self.reg2var
                cand = ctr
            elif insn.result_regclass is not NO_REGISTER:
                assert 0
            if cand is not None:
                self.var2reg[insn.result] = cand
                self.reg2var[cand] = insn.result
            insn.allocate(self)
            self.insns.append(insn)
        return self.insns

class Var(GenVar):
    def load(self, builder):
        return self

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

class Insn(object):
    '''
    result is the Var instance that holds the result, or None
    result_regclass is the class of the register the result goes into

    reg_args is the vars that need to have registers allocated for them
    reg_arg_regclasses is the type of register that needs to be allocated
    '''

class Insn_GPR__GPR_GPR(Insn):
    def __init__(self, methptr, result, args):
        self.methptr = methptr

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2reg[self.result]
        self.arg_reg1 = allocator.var2reg[self.reg_args[0]]
        self.arg_reg2 = allocator.var2reg[self.reg_args[1]]

    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg1.number,
                     self.arg_reg2.number)

class Insn_GPR__GPR_IMM(Insn):
    def __init__(self, methptr, result, args):
        self.methptr = methptr
        self.imm = args[1]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]
    def allocate(self, allocator):
        self.result_reg = allocator.var2reg[self.result]
        self.arg_reg = allocator.var2reg[self.reg_args[0]]
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.arg_reg.number,
                     self.imm.value)

class Insn_GPR__IMM(Insn):
    def __init__(self, methptr, result, args):
        self.methptr = methptr
        self.imm = args[0]

        self.result = result
        self.result_regclass = GP_REGISTER
        self.reg_args = []
        self.reg_arg_regclasses = []
    def allocate(self, allocator):
        self.result_reg = allocator.var2reg[self.result]
    def emit(self, asm):
        self.methptr(asm,
                     self.result_reg.number,
                     self.imm.value)

class CMPW(Insn):
    def __init__(self, info, result, args):
        self.info = info

        self.result = result
        self.result_regclass = CR_FIELD

        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER, GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2reg[self.result]
        self.arg_reg1 = allocator.var2reg[self.reg_args[0]]
        self.arg_reg2 = allocator.var2reg[self.reg_args[1]]

    def emit(self, asm):
        asm.cmpw(self.result_reg.number, self.arg_reg1.number, self.arg_reg2.number)

class CMPWI(Insn):
    def __init__(self, info, result, args):
        self.info = info
        self.imm = args[1]

        self.result = result
        self.result_regclass = CR_FIELD

        self.reg_args = [args[0]]
        self.reg_arg_regclasses = [GP_REGISTER]

    def allocate(self, allocator):
        self.result_reg = allocator.var2reg[self.result]
        self.arg_reg = allocator.var2reg[self.reg_args[0]]

    def emit(self, asm):
        asm.cmpwi(self.result_reg.number, self.arg_reg.number, self.imm.value)

class MTCTR(Insn):
    def __init__(self, result, args):
        self.result = result
        self.result_regclass = CT_REGISTER

        self.reg_args = args
        self.reg_arg_regclasses = [GP_REGISTER]

    def allocate(self, allocator):
        self.arg_reg = allocator.var2reg[self.reg_args[0]]

    def emit(self, asm):
        asm.mtctr(self.arg_reg.number)

class Jump(Insn):
    def __init__(self, gv_cond, gv_target, jump_if_true):
        self.gv_cond = gv_cond
        self.gv_target = gv_target
        self.jump_if_true = jump_if_true

        self.result = None
        self.result_regclass = NO_REGISTER
        self.reg_args = [gv_cond, gv_target]
        self.reg_arg_regclasses = [CR_FIELD, CT_REGISTER]
    def allocate(self, allocator):
        assert allocator.var2reg[self.reg_args[1]] is ctr
        self.crf = allocator.var2reg[self.reg_args[0]]
        self.bit, self.negated = allocator.crfinfo[self.crf.number]
    def emit(self, asm):
        if self.negated ^ self.jump_if_true:
            BO = 12 # jump if relavent bit is set in the CR
        else:
            BO = 4  # jump if relavent bit is NOT set in the CR
        asm.bcctr(BO, self.bit)

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
rSP = r1

def emit(self, value):
    self.mc.write(value)
RPPCAssembler.emit = emit

def prepare_for_jump(builder, cur_locations, target):
    assert len(target.arg_locations) == len(cur_locations)
    targetregs = target.arg_locations
    outregs = cur_locations
    for i in range(len(cur_locations)):
        treg = targetregs[i]
        oreg = outregs[i]
        if oreg == treg:
            continue
        if treg in outregs:
            outi = outregs.index(treg)
            assert outi > i
            builder.asm.xor(treg.number, treg.number, oreg.number)
            builder.asm.xor(oreg.number, treg.number, oreg.number)
            builder.asm.xor(treg.number, treg.number, oreg.number)
            outregs[outi] = oreg
            outregs[i] == treg
        else:
            builder.asm.mr(treg.number, oreg.number)

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

    def __init__(self, startaddr, arg_locations):
        self.startaddr = startaddr
        self.arg_locations = arg_locations

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

    def __init__(self, rgenop, mc, parent):
        self.rgenop = rgenop
        self.asm = RPPCAssembler()
        self.asm.mc = mc
        self.insns = []
        self.parent = parent

    def _write_prologue(self, sigtoken):
        assert self.parent is None
        numargs = sigtoken     # for now
        if not we_are_translated() and option.trap:
            self.asm.trap()
        self.inputargs = [self.newvar() for i in range(numargs)]
        self.initial_varmapping = {}
        for arg in self.inputargs:
            self.initial_varmapping[arg] = gprs[3+len(self.initial_varmapping)]

        # Emit standard prologue
        #   Minimum space = 24+params+lv+4*GPR+8*FPR
        #   GPR=19
        # Initially, we allocate only enough space for GPRs, and allow
        # each basic block to ensure it has enough space to continue.
        minspace = self._stack_offset(0,0)
        self.asm.mflr(r0)      
        self.asm.stw(r0,rSP,8)
        self.asm.stmw(r13,rSP,-(4*20))     # save all regs from 13-31 to stack
        self.asm.stwu(rSP,rSP,-minspace)
            
        return self.inputargs

    def _stack_offset(self, param, lv):
        """ Returns the required stack offset to store all data, assuming
        that there are 'param' words of parameters for callee functions and
        'lv' words of local variable information. """
        return ((24 + param*4 + lv*4 + 4*19) & ~15)+16

    def _close(self):
        self.rgenop.close_mc(self.asm.mc)
        self.asm.mc = None

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def emit(self):
        if self.parent is not None:
            allocator = RegisterAllocation(self.parent.var2reg)
        else:
            allocator = RegisterAllocation(self.initial_varmapping)
        self.insns = allocator.allocate_for_insns(self.insns)
        for insn in self.insns:
            insn.emit(self.asm)
        self.var2reg = allocator.var2reg
        return allocator

    def finish_and_return(self, sigtoken, gv_returnvar):
        gv_returnvar = gv_returnvar.load(self)
        allocator = self.emit()
        reg = allocator.var2reg[gv_returnvar]
        if reg.number != 3:
            self.asm.mr(r3, reg.number)

        # Emit standard epilogue:
        self.asm.lwz(rSP,rSP,0)     # restore old SP
        self.asm.lmw(r13,rSP,-4*20) # restore all GPRs
        self.asm.lwz(r0,rSP,8)      # load old Link Register and jump to it
        self.asm.mtlr(r0)           #
        self.asm.blr()              #
        self._close()

    def finish_and_goto(self, outputargs_gv, target):
        allocator = self.emit()
        cur_locations = [allocator.var2reg[v] for v in outputargs_gv]
        prepare_for_jump(self, cur_locations, target)
        self.asm.load_word(0, target.startaddr)
        self.asm.mtctr(0)
        self.asm.bctr()
        self._close()

    def enter_next_block(self, kinds, args_gv):
        arg_locations = []
        for i in range(len(args_gv)):
            gv = args_gv[i]
            gv = args_gv[i] = gv.load(self)
        allocator = self.emit()
        for gv in args_gv:
            arg_locations.append(allocator.var2reg[gv])
        self.insns = []
        self.initial_varmapping = allocator.var2reg
        return Label(self.asm.mc.tell(), arg_locations)

    def newvar(self):
        gv = Var()
        return gv

    def new_and_load_2(self, gv_x, gv_y):
        gv_result = self.newvar()
        return (gv_result, gv_x.load(self), gv_y.load(self))

    def new_and_load_1(self, gv_x):
        gv_result = self.newvar()
        return (gv_result, gv_x.load(self))

    def op_int_add(self, gv_x, gv_y):
        if isinstance(gv_y, IntConst) and abs(gv_y.value) < 2*16:
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
        return targetbuilder

    def jump_if_false(self, gv_condition):
        return self._jump(gv_condition, False)

    def jump_if_true(self, gv_condition):
        return self._jump(gv_condition, True)

    def _fork(self):
        return self.rgenop.openbuilder(self)


class RPPCGenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock

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

    def openbuilder(self, parent):
        return Builder(self, self.open_mc(), parent)

    def newgraph(self, sigtoken):
        numargs = sigtoken          # for now
        builder = self.openbuilder(None)
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
