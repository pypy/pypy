from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenLink
from pypy.jit.codegen.model import GenVar, GenConst

import os
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


##class Const(GenConst):

##    def revealconst(self, TYPE):
##        if isinstance(self, IntConst):
##            self.revealconst_int(TYPE)
##        elif isinstance(self, PtrConst):
##            self.revealconst_ptr(TYPE)
        
##        if isinstance(TYPE, lltype.Ptr):
##            if isinstance(self, PtrConst):
##                return self.revealconst_ptr(TYPE)
##            el
##                return self.revealconst_ptr(TYPE)
##        elif TYPE is lltype.Float:
##            assert isinstance(self, DoubleConst)
##            return self.revealconst_double()
##        else:
##            assert isinstance(TYPE, lltype.Primitive)
##            assert TYPE is not lltype.Void, "cannot make red boxes of voids"
##            assert isinstance(self, IntConst)
##            return self.revealconst_primitive(TYPE)
##        return self.value
##    revealconst._annspecialcase_ = 'specialize:arg(1)'


class IntConst(GenConst):

    def __init__(self, value):
        self.value = value

    def operand(self, block):
        return imm(self.value)

    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)
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
        # XXX what if gv_condition is a Const?
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

    def op_int_is_true(self, (gv_x,), gv_RESTYPE):
        return gv_x

    def op_int_add(self, (gv_x, gv_y), gv_RESTYPE):
        if isinstance(gv_x, IntConst) and isinstance(gv_y, IntConst):
            # XXX do this for the other operations too
            return IntConst(gv_x.value + gv_y.value)
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_sub(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.SUB(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_mul(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.IMUL(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_floordiv(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CDQ()
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.IDIV(ecx)
        return self.push(eax)

    def op_int_and(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.AND(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_or(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.OR(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_xor(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(eax, gv_y.operand(self))
        return self.push(eax)

    def op_int_lt(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETL(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_le(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETLE(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_eq(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_ne(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETNE(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_gt(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETG(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_ge(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETGE(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_int_neg(self, (gv_x,), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.NEG(eax)
        return self.push(eax)

    def op_int_lshift(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHL(eax, cl)
        return self.push(eax)

    def op_int_rshift(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHR(eax, cl)
        return self.push(eax)

    def op_bool_not(self, (gv_x,), gv_RESTYPE):
        if isinstance(gv_x, IntConst):
            return IntConst(not gv_x.value)
        self.mc.CMP(gv_x.operand(self), imm8(0))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.push(eax)

    def op_getfield(self, (gv_ptr, gv_offset), gv_RESTYPE):
        assert isinstance(gv_offset, IntConst)
        offset = gv_offset.value
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.push(mem(edx, offset))


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
                            if not srccount[dst] == 1:
                                os.write(1, 'Bad!\n')
                                os._exit(99)
                            srccount[dst] = -1
                            pending_dests -= 1
                            gv_src = outputargs_gv[dst]
                            if not isinstance(gv_src, Var):
                                os.write(1, 'Bad2!\n')
                                os._exit(98)
                                
                            src = gv_src.stackpos
                            if not 0 <= src < N:
                                os.write(1, 'Bad3!\n')
                                os._exit(97)
                            if src == i:
                                break
                            block.mc.MOV(eax, block.stack_access(src))
                            block.mc.MOV(block.stack_access(dst), eax)
                            dst = src
                        block.mc.MOV(block.stack_access(dst), edx)
                if not pending_dests == 0:
                    os.write(1, 'Bad3!\n')
                    os._exit(96)

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
            return self.MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    def newblock(self):
        return Block(self, self.open_mc())

    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        assert isinstance(T, lltype.Primitive)
        return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
    genconst._annspecialcase_ = 'specialize:genconst(0)'
    genconst = staticmethod(genconst)

    def constTYPE(T):
        if T is lltype.Void:
            return RI386GenOp.gv_Void
        else:
            return RI386GenOp.gv_IntWord   # XXX for now
    constTYPE._annspecialcase_ = 'specialize:memo'
    constTYPE = staticmethod(constTYPE)

    constPrebuiltGlobal = genconst

    def constFieldName(T, name):
        return IntConst(llmemory.offsetof(T, name))
    constFieldName._annspecialcase_ = 'specialize:memo'
    constFieldName = staticmethod(constFieldName)

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
