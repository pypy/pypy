from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenLink
from pypy.jit.codegen.model import GenVar, GenConst


WORD = 4


class Var(GenVar):

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
        return block.stack_access(self.stackpos)


class TypeConst(GenConst):

    def __init__(self, kind):
        self.kind = kind


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self, block):
        return imm(self.value)

    def revealconst(self, T):
        return lltype.cast_int_to_ptr(T, self.value)
    revealconst._annspecialcase_ = 'specialize:arg(1)'


class FnPtrConst(IntConst):
    def __init__(self, value, mc):
        self.value = value
        self.mc = mc    # to keep it alive


class Block(CodeGenBlock):
    def __init__(self, rgenop, mc):
        self.rgenop = rgenop
        self.argcount = 0
        self.stackdepth = 0
        self.mc = mc
        self.startaddr = mc.tell()

    def geninputarg(self, gv_TYPE):
        res = Var(self.argcount)
        self.argcount += 1
        self.stackdepth += 1
        return res

    def genop(self, opname, args_gv, gv_RESTYPE=None):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(args_gv, gv_RESTYPE)
    genop._annspecialcase_ = 'specialize:arg(1)'

    def close1(self):
        return Link(self)

    def close2(self, gv_condition):
        false_block = self.rgenop.newblock()
        false_block.stackdepth = self.stackdepth
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        self.mc.JE(rel32(false_block.startaddr))
        return Link(false_block), Link(self)

    def stack_access(self, stackpos):
        return mem(esp, WORD * (self.stackdepth-1 - stackpos))

    def push(self, reg):
        self.mc.PUSH(reg)
        res = Var(self.stackdepth)
        self.stackdepth += 1
        return res

    def op_int_add(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_sub(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.SUB(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_gt(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETG(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)


class Link(CodeGenLink):

    def __init__(self, prevblock):
        self.prevblock = prevblock

    def closereturn(self, gv_result):
        block = self.prevblock
        block.mc.MOV(eax, gv_result.operand(block))
        block.mc.ADD(esp, imm(WORD * block.stackdepth))
        block.mc.RET()
        block.rgenop.close_mc(block.mc)

    def close(self, outputargs_gv, targetblock):
        block = self.prevblock
        N = len(outputargs_gv)
        if block.stackdepth < N:
            block.mc.SUB(esp, imm(WORD * (N - block.stackdepth)))
            block.stackdepth = N

        pending_dests = N
        srccount = [0] * N
        for i in range(N):
            gv = outputargs_gv[i]
            if isinstance(gv, Var):
                p = gv.stackpos
                if 0 <= p < N:
                    if p == i:
                        srccount[p] = -N     # ignore 'v=v'
                        pending_dests -= 1
                    else:
                        srccount[p] += 1

        while pending_dests:
            progress = False
            for i in range(N):
                if srccount[i] == 0:
                    srccount[i] = -1
                    pending_dests -= 1
                    gv_src = outputargs_gv[i]
                    block.mc.MOV(eax, gv_src.operand(block))
                    block.mc.MOV(block.stack_access(i), eax)
                    progress = True
            if not progress:
                # we are left with only pure disjoint cycles; break them
                for i in range(N):
                    if srccount[i] >= 0:
                        dst = i
                        block.mc.MOV(edx, block.stack_access(dst))
                        while True:
                            assert srccount[dst] == 1
                            srccount[dst] = -1
                            pending_dests -= 1
                            gv_src = outputargs_gv[dst]
                            assert isinstance(gv_src, Var)
                            src = gv_src.stackpos
                            assert 0 <= src < N
                            if src == i:
                                break
                            block.mc.MOV(eax, block.stack_access(src))
                            block.mc.MOV(block.stack_access(dst), eax)
                            dst = src
                        block.mc.MOV(block.stack_access(dst), edx)
                assert pending_dests == 0

        if block.stackdepth > N:
            block.mc.ADD(esp, imm(WORD * (block.stackdepth - N)))
            block.stackdepth = N
        block.mc.JMP(rel32(targetblock.startaddr))
        block.rgenop.close_mc(block.mc)


class RI386GenOp(AbstractRGenOp):
    gv_IntWord = TypeConst('IntWord')
    gv_Void = TypeConst('Void')

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing

    def get_rgenop_for_testing():
        return RI386GenOp()
    get_rgenop_for_testing = staticmethod(get_rgenop_for_testing)

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            return MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    def newblock(self):
        return Block(self, self.open_mc())

    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        assert T is lltype.Signed
        return IntConst(llvalue)
    genconst._annspecialcase_ = 'specialize:ll'
    genconst = staticmethod(genconst)

    def constTYPE(T):
        if T is lltype.Void:
            return RI386GenOp.gv_Void
        else:
            return RI386GenOp.gv_IntWord   # XXX for now
    constTYPE._annspecialcase_ = 'specialize:memo'
    constTYPE = staticmethod(constTYPE)

    def gencallableconst(self, name, block, gv_FUNCTYPE):
        prologue = self.newblock()
        #prologue.mc.BREAKPOINT()
        # re-push the arguments so that they are after the return value
        # and in the correct order
        for i in range(block.argcount):
            operand = mem(esp, WORD * (2*i+1))
            prologue.mc.PUSH(operand)
        prologue.mc.JMP(rel32(block.startaddr))
        self.close_mc(prologue.mc)
        return FnPtrConst(prologue.startaddr, prologue.mc)
