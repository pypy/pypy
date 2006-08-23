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
        return block.stack_access(self.stackpos)


class TypeConst(VarOrConst):

    def __init__(self, kind):
        self.kind = kind


class IntConst(VarOrConst):

    def __init__(self, value):
        self.value = value

    def operand(self, block):
        return imm(self.value)


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


class RI386GenOp(object):
    gv_IntWord = TypeConst('IntWord')
    gv_Void = TypeConst('Void')

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            return MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    def newblock(self):
        return Block(self.open_mc())

    def closeblock1(self, block):
        return block   # NB. links and blocks are the same for us

    def closeblock2(self, block, gv_condition):
        false_block = self.newblock()
        false_block.stackdepth = block.stackdepth
        block.mc.CMP(gv_condition.operand(block), imm8(0))
        block.mc.JE(rel32(false_block.startaddr))
        return false_block, block

    def closereturnlink(self, link, gv_result):
        link.mc.MOV(eax, gv_result.operand(link))
        link.mc.ADD(esp, imm(WORD * link.stackdepth))
        link.mc.RET()
        self.close_mc(link.mc)

    def closelink(self, link, outputargs_gv, targetblock):
        N = len(outputargs_gv)
        if link.stackdepth < N:
            link.mc.SUB(esp, imm(WORD * (N - link.stackdepth)))
            link.stackdepth = N

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
                    link.mc.MOV(eax, gv_src.operand(link))
                    link.mc.MOV(link.stack_access(i), eax)
                    progress = True
            if not progress:
                # we are left with only pure disjoint cycles; break them
                for i in range(N):
                    if srccount[i] >= 0:
                        dst = i
                        link.mc.MOV(edx, link.stack_access(dst))
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
                            link.mc.MOV(eax, link.stack_access(src))
                            link.mc.MOV(link.stack_access(dst), eax)
                            dst = src
                        link.mc.MOV(link.stack_access(dst), edx)
                assert pending_dests == 0

        if link.stackdepth > N:
            link.mc.ADD(esp, imm(WORD * (link.stackdepth - N)))
            link.stackdepth = N
        link.mc.JMP(rel32(targetblock.startaddr))
        self.close_mc(link.mc)

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
        # re-push the arguments so that they are after the return value
        # and in the correct order
        for i in range(block.argcount):
            operand = mem(esp, WORD * (2*i+1))
            prologue.mc.PUSH(operand)
        prologue.mc.JMP(rel32(block.startaddr))
        self.close_mc(prologue.mc)
        return FnPtrConst(prologue.startaddr, prologue.mc)

    def revealconst(T, gv_const):
        assert isinstance(gv_const, IntConst)    # for now
        return lltype.cast_int_to_ptr(T, gv_const.value)
    revealconst._annspecialcase_ = 'specialize:arg(0)'
    revealconst = staticmethod(revealconst)
