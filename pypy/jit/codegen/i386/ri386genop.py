from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
from pypy.jit.codegen.i386.ri386 import *


WORD = 4


class VarOrConst(object):
    pass


class Var(VarOrConst):

    def __init__(self, stackpos):
        # 'stackpos' is an index relative to the pushed arguments:
        #   0 = 1st arg,
        #   1 = 2nd arg,
        #       ...
        #       return address,
        #       local var,       ...
        #       ...              <--- esp+4
        #       local var        <--- esp
        #
        self.stackpos = stackpos

    def operand(self, block):
        return mem(esp, WORD * (block.stackdepth-1 - self.stackpos))


class TypeConst(VarOrConst):

    def __init__(self, kind):
        self.kind = kind


class IntConst(VarOrConst):

    def __init__(self, value):
        self.value = value

    def operand(self, block):
        if single_byte(self.value):
            return IMM8(self.value)
        else:
            return IMM32(self.value)


class FnPtrConst(IntConst):
    def __init__(self, value, mc):
        self.value = value
        self.mc = mc    # to keep it alive


class Block(object):
    def __init__(self, mc):
        self.argcount = 0
        self.stackdepth = 0
        self.mc = mc
        self.startaddr = mc.tell()

    def geninputarg(self, gv_TYPE):
        res = Var(self.argcount)
        self.argcount += 1
        self.stackdepth += 1
        return res

    def push(self, reg):
        self.mc.PUSH(reg)
        res = Var(self.stackdepth)
        self.stackdepth += 1
        return res

    def op_int_add(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.push(eax)


class RI386GenOp(object):
    gv_IntWord = TypeConst('IntWord')
    gv_Void = TypeConst('Void')

    def __init__(self):
        self.mc = MachineCodeBlock(65536)    # XXX!!!

    def newblock(self):
        # XXX concurrently-open Blocks cannot use the same mc
        return Block(self.mc)

    def closeblock1(self, block):
        return block

    def closereturnlink(self, link, gv_result):
        link.mc.MOV(eax, gv_result.operand(link))
        link.mc.ADD(esp, IMM32(WORD * link.stackdepth))
        link.mc.RET()

    def geninputarg(self, block, gv_TYPE):
        return block.geninputarg(gv_TYPE)

    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        assert T is lltype.Signed
        return IntConst(llvalue)
    genconst._annspecialcase_ = 'specialize:argtype(0)'   # XXX arglltype(0)?
    genconst = staticmethod(genconst)

    def constTYPE(T):
        if T is lltype.Void:
            return RI386GenOp.gv_Void
        else:
            return RI386GenOp.gv_IntWord   # XXX for now
    constTYPE._annspecialcase_ = 'specialize:memo'
    constTYPE = staticmethod(constTYPE)

    def genop(self, block, opname, args_gv, gv_RESTYPE):
        genmethod = getattr(block, 'op_' + opname)
        return genmethod(args_gv, gv_RESTYPE)
    genop._annspecialcase_ = 'specialize:arg(2)'

    def gencallableconst(self, name, block, gv_FUNCTYPE):
        prologue = self.newblock()
        #prologue.mc.BREAKPOINT()
        operand = mem(esp, WORD * block.argcount)
        for i in range(block.argcount):
            prologue.mc.PUSH(operand)
        prologue.mc.JMP(rel32(block.startaddr))
        return FnPtrConst(prologue.startaddr, prologue.mc)

    def revealconst(T, gv_const):
        assert isinstance(gv_const, IntConst)    # for now
        return lltype.cast_int_to_ptr(T, gv_const.value)
    revealconst._annspecialcase_ = 'specialize:arg(0)'
    revealconst = staticmethod(revealconst)
