from pypy.rpython.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenLink
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.rpython import objectmodel
from pypy.rpython.annlowlevel import llhelper

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

    def __repr__(self):
        return 'var@%d' % (self.stackpos,)


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

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

    def __repr__(self):
        return "const=%s" % (imm(self.value).assembler(),)
        


##class FnPtrConst(IntConst):
##    def __init__(self, value, mc):
##        self.value = value
##        self.mc = mc    # to keep it alive


class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

    def operand(self, block):
        return imm(llmemory.cast_adr_to_int(self.addr))

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

    def __repr__(self):
        return "const=%r" % (self.addr,)


class Block(CodeGenBlock):
    def __init__(self, rgenop, mc):
        self.rgenop = rgenop
        self.argcount = 0
        self.stackdepth = 0
        self.mc = mc
        self.startaddr = mc.tell()
        self.fixedposition = False

    def getstartaddr(self):
        self.fixedposition = True
        return self.startaddr

    def geninputarg(self, gv_TYPE):
        res = Var(self.argcount)
        self.argcount += 1
        self.stackdepth += 1
        return res

    @specialize.arg(1)
    def genop(self, opname, args_gv, gv_RESTYPE=None):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(args_gv, gv_RESTYPE)

    def genop_getfield(self, offset, gv_ptr):
        return self.emit_getfield(gv_ptr, offset)

    def genop_setfield(self, offset, gv_ptr, gv_value):
        return self.emit_setfield(gv_ptr, offset, gv_value)

    def genop_getsubstruct(self, offset, gv_ptr):
        return self.emit_getsubstruct(gv_ptr, offset)

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        return self.emit_getarrayitem(gv_ptr, arraytoken, gv_index)

    def genop_malloc_fixedsize(self, size):
        return self.emit_malloc_fixedsize(size)

    def close1(self):
        return Link(self)

    def close2(self, gv_condition):
        false_block = self.rgenop.newblock()
        false_block.stackdepth = self.stackdepth
        # XXX what if gv_condition is a Const?
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        self.mc.JE(rel32(false_block.getstartaddr()))
        return Link(false_block), Link(self)

    def stack_access(self, stackpos):
        return mem(esp, WORD * (self.stackdepth-1 - stackpos))

    def push(self, op):
        self.mc.PUSH(op)
        self.stackdepth += 1

    def returnvar(self, op):
        res = Var(self.stackdepth)
        self.push(op)
        return res

    def op_int_is_true(self, (gv_x,), gv_RESTYPE):
        return gv_x

    def op_int_add(self, (gv_x, gv_y), gv_RESTYPE):
        if isinstance(gv_x, IntConst) and isinstance(gv_y, IntConst):
            # XXX do this for the other operations too
            return IntConst(gv_x.value + gv_y.value)
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_sub(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.SUB(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_mul(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.IMUL(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_floordiv(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CDQ()
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.IDIV(ecx)
        return self.returnvar(eax)

    def op_int_and(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.AND(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_or(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.OR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_xor(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_lt(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETL(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_le(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETLE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_eq(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ne(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETNE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_gt(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETG(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ge(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETGE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_neg(self, (gv_x,), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.NEG(eax)
        return self.returnvar(eax)

    def op_int_lshift(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHL(eax, cl)
        return self.returnvar(eax)

    def op_int_rshift(self, (gv_x, gv_y), gv_RESTYPE):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHR(eax, cl)
        return self.returnvar(eax)

    def op_bool_not(self, (gv_x,), gv_RESTYPE):
        if isinstance(gv_x, IntConst):
            return IntConst(not gv_x.value)
        self.mc.CMP(gv_x.operand(self), imm8(0))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_cast_pointer(self, (gv_x,), gv_RESTYPE):
        return gv_x

    def op_same_as(self, (gv_x,), gv_RESTYPE):
        if gv_x.is_const:    # must always return a var
            return self.returnvar(gv_x.operand(self))
        else:
            return gv_x

    def emit_malloc_fixedsize(self, size):
        # XXX boehm only, no atomic/non atomic distinction for now
        self.push(imm(size))
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        self.mc.CALL(rel32(lltype.cast_ptr_to_int(gc_malloc_ptr)))
        return self.returnvar(eax)

    def emit_getfield(self, gv_ptr, offset):
        # XXX only for int fields
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.returnvar(mem(edx, offset))

    def emit_setfield(self, gv_ptr, offset, gv_value):
        # XXX only for ints for now.
        self.mc.MOV(eax, gv_value.operand(self))
        self.mc.MOV(edx, gv_ptr.operand(self))
        self.mc.MOV(mem(edx, offset), eax)

    def emit_getsubstruct(self, gv_ptr, offset):
        self.mc.MOV(edx, gv_ptr.operand(self))
        self.mc.LEA(eax, mem(edx, offset))
        return self.returnvar(eax)

    def emit_getarrayitem(self, gv_ptr, arraytoken, gv_index):
        # XXX! only works for GcArray(Signed) for now!!
        lengthoffset, startoffset, itemoffset = arraytoken
        self.mc.MOV(edx, gv_ptr.operand(self))
        if isinstance(gv_index, IntConst):
            startoffset += itemoffset * gv_index.value
            op = mem(edx, startoffset)
        elif itemoffset in SIZE2SHIFT:
            self.mc.MOV(ecx, gv_index.operand(self))
            op = memSIB(edx, ecx, SIZE2SHIFT[itemoffset], startoffset)
        else:
            self.mc.IMUL(ecx, gv_index.operand(self), imm(itemoffset))
            op = memSIB(edx, ecx, 0, startoffset)
        return self.returnvar(op)

    def op_getarraysize(self, (gv_ptr,), gv_RESTYPE):
        # XXX! only works for GcArray(Signed) for now!!
        A = DUMMY_A
        lengthoffset, startoffset, itemoffset = self.rgenop.arrayToken(A)
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.returnvar(mem(edx, lengthoffset))

    def op_setarrayitem(self, (gv_ptr, gv_index, gv_value), gv_RESTYPE):
        # XXX! only works for GcArray(Signed) for now!!
        A = DUMMY_A
        lengthoffset, startoffset, itemoffset = self.rgenop.arrayToken(A)
        self.mc.MOV(eax, gv_value.operand(self))
        self.mc.MOV(edx, gv_ptr.operand(self))
        if isinstance(gv_index, IntConst):
            startoffset += itemoffset * gv_index.value
            op = mem(edx, startoffset)
        elif itemoffset in SIZE2SHIFT:
            self.mc.MOV(ecx, gv_index.operand(self))
            op = memSIB(edx, ecx, SIZE2SHIFT[itemoffset], startoffset)
        else:
            self.mc.IMUL(ecx, gv_index.operand(self), imm(itemoffset))
            op = memSIB(edx, ecx, 0, startoffset)
        self.mc.MOV(op, eax)

    def op_direct_call(self, args_gv, result_kind):
        for i in range(len(args_gv)-1, 0, -1):
            gv_arg = args_gv[i]
            if gv_arg is not None:
                self.push(gv_arg.operand(self))
        gv_fnptr = args_gv[0]
        target = gv_fnptr.revealconst(lltype.Signed)
        self.mc.CALL(rel32(target))
        # XXX only for int return_kind
        return self.returnvar(eax)


DUMMY_A = lltype.GcArray(lltype.Signed)
SIZE2SHIFT = {1: 0,
              2: 1,
              4: 2,
              8: 3}

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    from pypy.rpython.lltypesystem.lloperation import llop
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

# ____________________________________________________________

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
                    if isinstance(gv_src, Var):
                        p = gv_src.stackpos
                        if 0 <= p < N:
                            srccount[p] -= 1
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
        block.rgenop.close_mc_and_jump(block.mc, targetblock)


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    
    gv_IntWord = TypeConst('IntWord')
    gv_Void = TypeConst('Void')

    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            return self.MachineCodeBlock(65536)   # XXX supposed infinite for now

    def close_mc(self, mc):
        self.mcs.append(mc)

    def close_mc_and_jump(self, mc, targetblock):
        if (targetblock.fixedposition
            or targetblock.mc.tell() != targetblock.startaddr):
            mc.JMP(rel32(targetblock.getstartaddr()))
            self.close_mc(mc)
        else:
            # bring the targetblock here, instead of jumping to it
            self.close_mc(targetblock.mc)
            targetblock.mc = mc
            targetblock.startaddr = mc.tell()
            targetblock.fixedposition = True

    def newblock(self):
        return Block(self, self.open_mc())

    @staticmethod
    @specialize.genconst(0)
    def genconst(llvalue):
        T = lltype.typeOf(llvalue)
        if isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Ptr):
            return AddrConst(llmemory.cast_ptr_to_adr(llvalue))
        else:
            assert 0, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return llmemory.offsetof(T, name)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return (llmemory.ArrayLengthOffset(A),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T): # xxx simplify
        if T is lltype.Void:
            return RI386GenOp.gv_Void
        else:
            return RI386GenOp.gv_IntWord   # XXX for now


    constPrebuiltGlobal = genconst

    constTYPE = kindToken

    @staticmethod
    @specialize.memo()
    def constFieldName(T, name):
        return IntConst(llmemory.offsetof(T, name))


    def gencallableconst(self, name, block, gv_FUNCTYPE):
        prologue = self.newblock()
        #prologue.mc.BREAKPOINT()
        # re-push the arguments so that they are after the return value
        # and in the correct order
        for i in range(block.argcount):
            operand = mem(esp, WORD * (2*i+1))
            prologue.mc.PUSH(operand)
        self.close_mc_and_jump(prologue.mc, block)
        return IntConst(prologue.getstartaddr())
