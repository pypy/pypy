from pypy.rpython.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.model import AbstractRGenOp, CodeGenBlock, CodeGenerator
from pypy.jit.codegen.model import GenVar, GenConst
from pypy.rpython import objectmodel
from pypy.rpython.annlowlevel import llhelper

WORD = 4


class Var(GenVar):

    def __init__(self, stackpos):
        # 'stackpos' is an index relative to the pushed arguments
        # (where N is the number of arguments of the function):
        #
        #  0  = last arg
        #     = ...
        # N-1 = 1st arg
        #  N  = return address
        # N+1 = local var
        # N+2 = ...
        #       ...              <--- esp+4
        #       local var        <--- esp
        #
        self.stackpos = stackpos

    def operand(self, builder):
        return builder.stack_access(self.stackpos)

    def __repr__(self):
        return 'var@%d' % (self.stackpos,)


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

    def operand(self, builder):
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

    def operand(self, builder):
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

    def __init__(self, startaddr, arg_positions, stackdepth):
        self.startaddr = startaddr
        self.arg_positions = arg_positions
        self.stackdepth = stackdepth


class Builder(CodeGenerator):

    def __init__(self, rgenop, mc, stackdepth):
        self.rgenop = rgenop
        self.stackdepth = stackdepth
        self.mc = mc

    def _write_prologue(self, sigtoken):
        numargs = sigtoken     # for now
        #self.mc.BREAKPOINT()
        return [Var(pos) for pos in range(numargs-1, -1, -1)]

    def _close(self):
        self.rgenop.close_mc(self.mc)
        self.mc = None

    def _fork(self):
        return self.rgenop.openbuilder(self.stackdepth)

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg)

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        genmethod = getattr(self, 'op_' + opname)
        return genmethod(gv_arg1, gv_arg2)

    def genop_getfield(self, offset, gv_ptr):
        # XXX only for int fields
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.returnvar(mem(edx, offset))

    def genop_setfield(self, offset, gv_ptr, gv_value):
        # XXX only for ints for now.
        self.mc.MOV(eax, gv_value.operand(self))
        self.mc.MOV(edx, gv_ptr.operand(self))
        self.mc.MOV(mem(edx, offset), eax)

    def genop_getsubstruct(self, offset, gv_ptr):
        self.mc.MOV(edx, gv_ptr.operand(self))
        self.mc.LEA(eax, mem(edx, offset))
        return self.returnvar(eax)

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
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

    def genop_getarraysize(self, arraytoken, gv_ptr):
        lengthoffset, startoffset, itemoffset = arraytoken
        self.mc.MOV(edx, gv_ptr.operand(self))
        return self.returnvar(mem(edx, lengthoffset))

    def genop_malloc_fixedsize(self, size):
        # XXX boehm only, no atomic/non atomic distinction for now
        self.push(imm(size))
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        self.mc.CALL(rel32(lltype.cast_ptr_to_int(gc_malloc_ptr)))
        return self.returnvar(eax)

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        for i in range(len(args_gv)-1, -1, -1):
            gv_arg = args_gv[i]
            if gv_arg is not None:
                self.push(gv_arg.operand(self))
        target = gv_fnptr.revealconst(lltype.Signed)
        self.mc.CALL(rel32(target))
        # XXX only for int return_kind
        return self.returnvar(eax)

    def genop_same_as(self, kind, gv_x):
        if gv_x.is_const:    # must always return a var
            return self.returnvar(gv_x.operand(self))
        else:
            return gv_x

    def enter_next_block(self, kinds, args_gv):
        arg_positions = []
        seen = {}
        for i in range(len(args_gv)):
            gv = args_gv[i]
            # turn constants into variables; also make copies of vars that
            # are duplicate in args_gv
            if not isinstance(gv, Var) or gv.stackpos in seen:
                gv = args_gv[i] = self.returnvar(gv.operand(self))
            # remember the var's position in the stack
            arg_positions.append(gv.stackpos)
            seen[gv.stackpos] = None
        return Block(self.mc.tell(), arg_positions, self.stackdepth)

    def jump_if_false(self, gv_condition):
        targetbuilder = self._fork()
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        self.mc.JE(rel32(targetbuilder.mc.tell()))
        return targetbuilder

    def jump_if_true(self, gv_condition):
        targetbuilder = self._fork()
        self.mc.CMP(gv_condition.operand(self), imm8(0))
        self.mc.JNE(rel32(targetbuilder.mc.tell()))
        return targetbuilder

    def finish_and_return(self, sigtoken, gv_returnvar):
        numargs = sigtoken      # for now
        initialstackdepth = numargs + 1
        self.mc.MOV(eax, gv_returnvar.operand(self))
        self.mc.ADD(esp, imm(WORD * (self.stackdepth - initialstackdepth)))
        self.mc.RET()
        self._close()

    def finish_and_goto(self, outputargs_gv, targetblock):
        remap_stack_layout(self, outputargs_gv, targetblock)
        self.mc.JMP(rel32(targetblock.startaddr))
        self._close()

    # ____________________________________________________________

    def stack_access(self, stackpos):
        return mem(esp, WORD * (self.stackdepth-1 - stackpos))

    def push(self, op):
        self.mc.PUSH(op)
        self.stackdepth += 1

    def returnvar(self, op):
        res = Var(self.stackdepth)
        self.push(op)
        return res

    def op_int_is_true(self, gv_x):
        return gv_x

    def op_int_add(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.ADD(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_sub(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.SUB(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_mul(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.IMUL(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_floordiv(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CDQ()
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.IDIV(ecx)
        return self.returnvar(eax)

    def op_int_and(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.AND(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_or(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.OR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_xor(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.XOR(eax, gv_y.operand(self))
        return self.returnvar(eax)

    def op_int_lt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETL(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_le(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETLE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_eq(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ne(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETNE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_gt(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETG(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_ge(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.CMP(eax, gv_y.operand(self))
        self.mc.SETGE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_int_neg(self, gv_x):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.NEG(eax)
        return self.returnvar(eax)

    def op_int_lshift(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHL(eax, cl)
        return self.returnvar(eax)

    def op_int_rshift(self, gv_x, gv_y):
        self.mc.MOV(eax, gv_x.operand(self))
        self.mc.MOV(ecx, gv_y.operand(self))
        self.mc.SHR(eax, cl)
        return self.returnvar(eax)

    def op_bool_not(self, gv_x):
        self.mc.CMP(gv_x.operand(self), imm8(0))
        self.mc.SETE(al)
        self.mc.MOVZX(eax, al)
        return self.returnvar(eax)

    def op_setarrayitem(self, (gv_ptr, gv_index, gv_value), gv_RESTYPE):
        # XXX! only works for GcArray(Signed) for now!!
        XXX-fixme
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

def remap_stack_layout(builder, outputargs_gv, targetblock):
    N = targetblock.stackdepth
    if builder.stackdepth < N:
        builder.mc.SUB(esp, imm(WORD * (N - builder.stackdepth)))
        builder.stackdepth = N

    M = len(outputargs_gv)
    arg_positions = targetblock.arg_positions
    assert M == len(arg_positions)
    targetlayout = [None] * N
    srccount = [-N] * N
    for i in range(M):
        pos = arg_positions[i]
        gv = outputargs_gv[i]
        assert targetlayout[pos] is None
        targetlayout[pos] = gv
        srccount[pos] = 0
    pending_dests = M
    for i in range(M):
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
                gv_src = targetlayout[i]
                if isinstance(gv_src, Var):
                    p = gv_src.stackpos
                    if 0 <= p < N:
                        srccount[p] -= 1
                builder.mc.MOV(eax, gv_src.operand(builder))
                builder.mc.MOV(builder.stack_access(i), eax)
                progress = True
        if not progress:
            # we are left with only pure disjoint cycles; break them
            for i in range(N):
                if srccount[i] >= 0:
                    dst = i
                    builder.mc.MOV(edx, builder.stack_access(dst))
                    while True:
                        assert srccount[dst] == 1
                        srccount[dst] = -1
                        pending_dests -= 1
                        gv_src = targetlayout[dst]
                        assert isinstance(gv_src, Var)
                        src = gv_src.stackpos
                        assert 0 <= src < N
                        if src == i:
                            break
                        builder.mc.MOV(eax, builder.stack_access(src))
                        builder.mc.MOV(builder.stack_access(dst), eax)
                        dst = src
                    builder.mc.MOV(builder.stack_access(dst), edx)
            assert pending_dests == 0

    if builder.stackdepth > N:
        builder.mc.ADD(esp, imm(WORD * (builder.stackdepth - N)))
        builder.stackdepth = N


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock

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

    def openbuilder(self, stackdepth):
        return Builder(self, self.open_mc(), stackdepth)

    def newgraph(self, sigtoken):
        numargs = sigtoken          # for now
        initialstackdepth = numargs+1
        builder = self.openbuilder(initialstackdepth)
        entrypoint = builder.mc.tell()
        inputargs_gv = builder._write_prologue(sigtoken)
        return builder, entrypoint, inputargs_gv

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
    def kindToken(T):
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        return len(FUNCTYPE.ARGS)     # for now

    constPrebuiltGlobal = genconst


    def gencallableconst(self, sigtoken, name, entrypointaddr):
        return IntConst(entrypointaddr)
