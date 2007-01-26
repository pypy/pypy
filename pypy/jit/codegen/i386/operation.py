"""Operations.

In the spirit of LLVM, operations are also variables themselves: they
are their own result variable.
"""

import sys
from pypy.rlib.objectmodel import specialize
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386.ri386setup import Conditions
from pypy.jit.codegen.model import GenVar


WORD = 4    # bytes
if sys.platform == 'darwin':
    CALL_ALIGN = 4
else:
    CALL_ALIGN = 1

PROLOGUE_FIXED_WORDS = 5

RK_NO_RESULT = 0
RK_WORD      = 1
RK_CC        = 2


class Operation(GenVar):
    clobbers_cc = True
    result_kind = RK_WORD
    cc_result   = -1

    def allocate(self, allocator):
        pass
    def generate(self, allocator):
        raise NotImplementedError

class Op1(Operation):
    def __init__(self, x):
        self.x = x
    def allocate(self, allocator):
        allocator.using(self.x)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # result not used
        srcop = allocator.get_operand(self.x)
        return self.generate2(allocator.mc, dstop, srcop)
    def generate2(self, mc, dstop, srcop):
        raise NotImplementedError

class UnaryOp(Op1):
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # simple operation whose result is not used anyway
        srcop = allocator.get_operand(self.x)
        mc = allocator.mc
        if srcop != dstop:
            try:
                mc.MOV(dstop, srcop)
            except FailedToImplement:
                mc.MOV(ecx, srcop)
                self.emit(mc, ecx)
                mc.MOV(dstop, ecx)
                return
        self.emit(mc, dstop)

class OpIntNeg(UnaryOp):
    opname = 'int_neg'
    emit = staticmethod(I386CodeBuilder.NEG)

class OpIntInvert(UnaryOp):
    opname = 'int_invert', 'uint_invert'
    emit = staticmethod(I386CodeBuilder.NOT)

class OpIntAbs(Op1):
    opname = 'int_abs'
    def generate2(self, mc, dstop, srcop):
        # ABS-computing code from Psyco, found by exhaustive search
        # on *all* short sequences of operations :-)
        inplace = (dstop == srcop)
        if inplace or not (isinstance(srcop, REG) or isinstance(dstop, REG)):
            mc.MOV(ecx, srcop)
            srcop = ecx
        if not inplace:
            mc.MOV(dstop, srcop)
        mc.SHL(dstop, imm8(1))
        mc.SBB(dstop, srcop)
        mc.SBB(ecx, ecx)
        mc.XOR(dstop, ecx)

class OpSameAs(Op1):
    clobbers_cc = False
    def generate2(self, mc, dstop, srcop):
        if srcop != dstop:
            try:
                mc.MOV(dstop, srcop)
            except FailedToImplement:
                mc.MOV(ecx, srcop)
                mc.MOV(dstop, ecx)

class OpCompare1(Op1):
    result_kind = RK_CC
    def generate(self, allocator):
        srcop = allocator.get_operand(self.x)
        mc = allocator.mc
        self.emit(mc, srcop)

class OpIntIsTrue(OpCompare1):
    opname = 'int_is_true', 'ptr_nonzero', 'uint_is_true'
    cc_result = Conditions['NE']
    @staticmethod
    def emit(mc, x):
        mc.CMP(x, imm8(0))

class OpIntIsZero(OpIntIsTrue):
    opname = 'ptr_iszero', 'bool_not'
    cc_result = Conditions['E']

class Op2(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def allocate(self, allocator):
        allocator.using(self.x)
        allocator.using(self.y)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # simple operation whose result is not used anyway
        op1 = allocator.get_operand(self.x)
        op2 = allocator.get_operand(self.y)
        self.generate3(allocator.mc, dstop, op1, op2)
    def generate3(self, mc, dstop, op1, op2):
        raise NotImplementedError

class BinaryOp(Op2):
    commutative = False
    def generate3(self, mc, dstop, op1, op2):
        # now all of dstop, op1 and op2 may alias each other and be in
        # a register, in the stack or an immediate... finding a correct
        # and encodable combination of instructions is loads of fun
        if dstop == op1:
            case = 1       # optimize for this common case
        elif self.commutative and dstop == op2:
            op1, op2 = op2, op1
            case = 1
        elif isinstance(dstop, REG):
            if dstop != op2:
                # REG = OPERATION(op1, op2)   with op2 != REG
                case = 2
            else:
                # REG = OPERATION(op1, REG)
                case = 3
        elif isinstance(op1, REG) and isinstance(op2, REG):
            # STACK = OPERATION(REG, REG)
            case = 2
        else:
            case = 3
        # generate instructions according to the 'case' determined above
        if case == 1:
            # dstop == op1
            try:
                self.emit(mc, op1, op2)
            except FailedToImplement:    # emit(STACK, STACK) combination
                mc.MOV(ecx, op2)
                self.emit(mc, op1, ecx)
        elif case == 2:
            # this case works for:
            #   * REG = OPERATION(op1, op2)   with op2 != REG
            #   * STACK = OPERATION(REG, REG)
            mc.MOV(dstop, op1)
            self.emit(mc, dstop, op2)
        else:
            # most general case
            mc.MOV(ecx, op1)
            self.emit(mc, ecx, op2)
            mc.MOV(dstop, ecx)

class OpIntAdd(BinaryOp):
    opname = 'int_add', 'uint_add'
    emit = staticmethod(I386CodeBuilder.ADD)
    commutative = True

class OpIntSub(BinaryOp):
    opname = 'int_sub', 'uint_sub'
    emit = staticmethod(I386CodeBuilder.SUB)

class OpIntAnd(BinaryOp):
    opname = 'int_and', 'uint_and'
    emit = staticmethod(I386CodeBuilder.AND)

class OpIntOr(BinaryOp):
    opname = 'int_or', 'uint_or'
    emit = staticmethod(I386CodeBuilder.OR)

class OpIntXor(BinaryOp):
    opname = 'int_xor', 'uint_xor'
    emit = staticmethod(I386CodeBuilder.XOR)

class OpIntMul(Op2):
    opname = 'int_mul'
    def generate3(self, mc, dstop, op1, op2):
        if isinstance(dstop, REG):
            tmpop = dstop
        else:
            tmpop = ecx
        if tmpop == op1:
            mc.IMUL(tmpop, op2)
        elif isinstance(op2, IMM32):
            mc.IMUL(tmpop, op1, op2)
        elif isinstance(op1, IMM32):
            mc.IMUL(tmpop, op2, op1)
        else:
            if tmpop != op2:
                mc.MOV(tmpop, op2)
            mc.IMUL(tmpop, op1)
        if dstop != tmpop:
            mc.MOV(dstop, tmpop)

class MulOrDivOp(Op2):

    def generate3(self, mc, dstop, op1, op2):
        # XXX not very efficient but not very common operations either
        mc.PUSH(eax)
        mc.PUSH(edx)
        if op1 != eax:
            if op2 == eax:
                op2 = mem(esp, 4)
            mc.MOV(eax, op1)
        if self.input_is_64bits:
            if op2 == edx:
                op2 = mem(esp)
            if self.unsigned:
                mc.XOR(edx, edx)
            else:
                mc.CDQ()
        try:
            self.emit(mc, op2)
        except FailedToImplement:
            mc.MOV(ecx, op2)
            self.emit(mc, ecx)
        if dstop != self.reg_containing_result:
            mc.MOV(dstop, self.reg_containing_result)
        if dstop == edx:
            mc.ADD(esp, imm8(4))
        else:
            mc.POP(edx)
        if dstop == eax:
            mc.ADD(esp, imm8(4))
        else:
            mc.POP(eax)

class OpIntFloorDiv(MulOrDivOp):
    opname = 'int_floordiv'
    input_is_64bits = True
    reg_containing_result = eax
    unsigned = False
    @staticmethod
    def emit(mc, op2):
        # from the PPC backend which has the same problem:
        # 
        #   grumble, the powerpc handles division when the signs of x
        #   and y differ the other way to how cpython wants it.  this
        #   crawling horror is a branch-free way of computing the right
        #   remainder in all cases.  it's probably not optimal.
        #
        #   we need to adjust the result iff the remainder is non-zero
        #   and the signs of x and y differ.  in the standard-ish PPC
        #   way, we compute boolean values as either all-bits-0 or
        #   all-bits-1 and "and" them together, resulting in either
        #   adding 0 or -1 as needed in the final step.
        #
        #                 Python    i386
        #    20/3    =     6, 2     6, 2
        # (-20)/3    =    -7, 1    -6,-2      # operand signs differ
        #    20/(-3) =    -7,-1    -6, 2      # operand signs differ
        # (-20)/(-3) =     6,-2     6,-2
        #
        if isinstance(op2, IMM32):
            # if op2 is an immediate, we do an initial adjustment of operand 1
            # so that we get directly the correct answer
            if op2.value >= 0:
                # if op1 is negative, subtract (op2-1)
                mc.MOV(ecx, edx)       # -1 if op1 is negative, 0 otherwise
                mc.AND(ecx, imm(op2.value-1))
                mc.SUB(eax, ecx)
                mc.SBB(edx, imm8(0))
            else:
                # if op1 is positive (or null), add (op2-1)
                mc.MOV(ecx, edx)
                mc.NEG(ecx)            # -1 if op1 is positive, 0 otherwise
                mc.AND(ecx, imm(op2.value-1))
                mc.ADD(eax, ecx)
                mc.ADC(edx, imm8(0))
            mc.MOV(ecx, op2)
            mc.IDIV(ecx)
        else:
            # subtract 1 to the result if the operand signs differ and
            # the remainder is not zero
            mc.MOV(ecx, eax)
            mc.IDIV(op2)
            mc.XOR(ecx, op2)
            mc.SAR(ecx, imm8(31)) # -1 if signs differ, 0 otherwise
            mc.AND(ecx, edx)      # nonnull if signs differ and edx != 0
            mc.CMP(ecx, imm8(1))  # no carry flag iff signs differ and edx != 0
            mc.ADC(eax, imm8(-1)) # subtract 1 iff no carry flag

class OpIntMod(MulOrDivOp):
    opname = 'int_mod'
    input_is_64bits = True
    reg_containing_result = edx
    unsigned = False
    @staticmethod
    def emit(mc, op2):
        #                 Python    i386
        #    20/3    =     6, 2     6, 2
        # (-20)/3    =    -7, 1    -6,-2      # operand signs differ
        #    20/(-3) =    -7,-1    -6, 2      # operand signs differ
        # (-20)/(-3) =     6,-2     6,-2
        #
        if isinstance(op2, IMM32):
            mc.MOV(ecx, op2)
            mc.IDIV(ecx)
            if op2.value >= 0:
                # if the result is negative, add op2 to it
                mc.MOV(ecx, edx)
                mc.SAR(ecx, imm8(31))
                mc.AND(ecx, imm(op2.value))
                mc.ADD(edx, ecx)
            else:
                # if the result is > 0, subtract op2 from it
                mc.MOV(ecx, edx)
                mc.NEG(ecx)
                mc.SAR(ecx, imm8(31))
                mc.AND(ecx, imm(op2.value))
                mc.SUB(edx, ecx)
        else:
            # if the operand signs differ and the remainder is not zero,
            # add operand2 to the result
            mc.MOV(ecx, eax)
            mc.IDIV(op2)
            mc.XOR(ecx, op2)
            mc.SAR(ecx, imm8(31)) # -1 if signs differ, 0 otherwise
            mc.AND(ecx, edx)      # nonnull if signs differ and edx != 0
            mc.CMOVNZ(ecx, op2)   # == op2  if signs differ and edx != 0
            mc.ADD(edx, ecx)

class OpUIntMul(MulOrDivOp):
    opname = 'uint_mul'
    input_is_64bits = False
    reg_containing_result = eax
    unsigned = True
    emit = staticmethod(I386CodeBuilder.MUL)

class OpUIntFloorDiv(MulOrDivOp):
    opname = 'uint_floordiv'
    input_is_64bits = True
    reg_containing_result = eax
    unsigned = True
    emit = staticmethod(I386CodeBuilder.DIV)

class OpUIntMod(MulOrDivOp):
    opname = 'uint_mod'
    input_is_64bits = True
    reg_containing_result = edx
    unsigned = True
    emit = staticmethod(I386CodeBuilder.DIV)

class OpIntLShift(Op2):
    opname = 'int_lshift', 'uint_lshift'
    emit = staticmethod(I386CodeBuilder.SHL)
    def generate3(self, mc, dstop, op1, op2):
        # XXX not optimized
        if isinstance(op2, IMM32):
            n = op2.value
            if n < 0 or n >= 32:
                mc.MOV(dstop, imm8(0))   # shift out of range, result is zero
                return
            count = imm8(n)
        else:
            mc.MOV(ecx, op2)
            count = cl
        if dstop != op1:
            try:
                mc.MOV(dstop, op1)
            except FailedToImplement:
                mc.PUSH(op1)
                mc.POP(dstop)
        self.emit(mc, dstop, count)
        if count == cl:
            mc.CMP(ecx, imm8(32))
            mc.SBB(ecx, ecx)
            mc.AND(dstop, ecx)

class OpIntRShift(Op2):
    opname = 'int_rshift'
    def generate3(self, mc, dstop, op1, op2):
        # XXX not optimized
        if isinstance(op2, IMM32):
            n = op2.value
            if n < 0 or n >= 32:
                n = 31     # shift out of range, replace with 31
            count = imm8(n)
        else:
            mc.MOV(ecx, imm(31))
            mc.CMP(op2, ecx)
            mc.CMOVBE(ecx, op2)
            count = cl
        if dstop != op1:
            try:
                mc.MOV(dstop, op1)
            except FailedToImplement:
                mc.PUSH(op1)
                mc.POP(dstop)
        mc.SAR(dstop, count)

class OpUIntRShift(OpIntLShift):
    opname = 'uint_rshift'
    emit = staticmethod(I386CodeBuilder.SHR)

class OpCompare2(Op2):
    result_kind = RK_CC
    def generate(self, allocator):
        srcop = allocator.get_operand(self.x)
        dstop = allocator.get_operand(self.y)
        mc = allocator.mc
        # XXX optimize the case CMP(immed, reg-or-modrm)
        try:
            mc.CMP(srcop, dstop)
        except FailedToImplement:
            mc.MOV(ecx, srcop)
            mc.CMP(ecx, dstop)

class OpIntLt(OpCompare2):
    opname = 'int_lt', 'char_lt'
    cc_result = Conditions['L']

class OpIntLe(OpCompare2):
    opname = 'int_le', 'char_le'
    cc_result = Conditions['LE']

class OpIntEq(OpCompare2):
    opname = 'int_eq', 'char_eq', 'unichar_eq', 'ptr_eq', 'uint_eq'
    cc_result = Conditions['E']

class OpIntNe(OpCompare2):
    opname = 'int_ne', 'char_ne', 'unichar_ne', 'ptr_ne', 'uint_ne'
    cc_result = Conditions['NE']

class OpIntGt(OpCompare2):
    opname = 'int_gt', 'char_gt'
    cc_result = Conditions['G']

class OpIntGe(OpCompare2):
    opname = 'int_ge', 'char_ge'
    cc_result = Conditions['GE']

class OpUIntLt(OpCompare2):
    opname = 'uint_lt'
    cc_result = Conditions['B']

class OpUIntLe(OpCompare2):
    opname = 'uint_le'
    cc_result = Conditions['BE']

class OpUIntGt(OpCompare2):
    opname = 'uint_gt'
    cc_result = Conditions['A']

class OpUIntGe(OpCompare2):
    opname = 'uint_ge'
    cc_result = Conditions['AE']

class JumpIf(Operation):
    clobbers_cc = False
    result_kind = RK_NO_RESULT
    def __init__(self, gv_condition, targetbuilder, negate):
        self.gv_condition = gv_condition
        self.targetbuilder = targetbuilder
        self.negate = negate
    def allocate(self, allocator):
        allocator.using_cc(self.gv_condition)
        for gv in self.targetbuilder.inputargs_gv:
            allocator.using(gv)
    def generate(self, allocator):
        cc = self.gv_condition.cc_result
        if self.negate:
            cc = cond_negate(cc)
        mc = allocator.mc
        targetbuilder = self.targetbuilder
        targetbuilder.set_coming_from(mc, insncond=cc)
        targetbuilder.inputoperands = [allocator.get_operand(gv)
                                       for gv in targetbuilder.inputargs_gv]

class OpLabel(Operation):
    clobbers_cc = False
    result_kind = RK_NO_RESULT
    def __init__(self, lbl, args_gv):
        self.lbl = lbl
        self.args_gv = args_gv
    def allocate(self, allocator):
        for v in self.args_gv:
            allocator.using(v)
    def generate(self, allocator):
        lbl = self.lbl
        lbl.targetaddr = allocator.mc.tell()
        lbl.targetstackdepth = allocator.required_frame_depth
        lbl.inputoperands = [allocator.get_operand(v) for v in self.args_gv]

class OpCall(Operation):
    def __init__(self, sigtoken, gv_fnptr, args_gv):
        self.sigtoken = sigtoken
        self.gv_fnptr = gv_fnptr
        self.args_gv = args_gv
    def allocate(self, allocator):
        # XXX try to use eax for the result
        allocator.using(self.gv_fnptr)
        for v in self.args_gv:
            allocator.using(v)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            dstop = None
        mc = allocator.mc
        stack_align_words = PROLOGUE_FIXED_WORDS
        if dstop != eax:
            mc.PUSH(eax)
            if CALL_ALIGN > 1: stack_align_words += 1
        if dstop != edx:
            mc.PUSH(edx)
            if CALL_ALIGN > 1: stack_align_words += 1
        args_gv = self.args_gv
        num_placeholders = 0
        if CALL_ALIGN > 1:
            stack_align_words += len(args_gv)
            stack_align_words &= CALL_ALIGN-1
            if stack_align_words > 0:
                num_placeholders = CALL_ALIGN - stack_align_words
                mc.SUB(esp, imm(WORD * num_placeholders))
        for i in range(len(args_gv)-1, -1, -1):
            srcop = allocator.get_operand(args_gv[i])
            mc.PUSH(srcop)
        fnop = allocator.get_operand(self.gv_fnptr)
        if isinstance(fnop, IMM32):
            mc.CALL(rel32(fnop.value))
        else:
            mc.CALL(fnop)
        mc.ADD(esp, imm(WORD * (len(args_gv) + num_placeholders)))
        if dstop != edx:
            mc.POP(edx)
        if dstop != eax:
            if dstop is not None:
                mc.MOV(dstop, eax)
            mc.POP(eax)

def field_operand(mc, base, fieldtoken):
    # may use ecx
    fieldoffset, fieldsize = fieldtoken

    if isinstance(base, MODRM):
        mc.MOV(ecx, base)
        base = ecx
    elif isinstance(base, IMM32):
        fieldoffset += base.value
        base = None

    if fieldsize == 1:
        return mem8(base, fieldoffset)
    else:
        return mem (base, fieldoffset)

def array_item_operand(mc, base, arraytoken, opindex):
    # may use ecx
    _, startoffset, itemoffset = arraytoken

    if isinstance(opindex, IMM32):
        startoffset += itemoffset * opindex.value
        opindex = None
        indexshift = 0
    elif itemoffset in SIZE2SHIFT:
        if not isinstance(opindex, REG):
            mc.MOV(ecx, opindex)
            opindex = ecx
        indexshift = SIZE2SHIFT[itemoffset]
    else:
        mc.IMUL(ecx, opindex, imm(itemoffset))
        opindex = ecx
        indexshift = 0

    assert base is not ecx
    if isinstance(base, MODRM):
        if opindex != ecx:
            mc.MOV(ecx, base)
        else:   # waaaa
            opindex = None
            if indexshift > 0:
                mc.SHL(ecx, imm8(indexshift))
            mc.ADD(ecx, base)
        base = ecx
    elif isinstance(base, IMM32):
        startoffset += base.value
        base = None

    if itemoffset == 1:
        return memSIB8(base, opindex, indexshift, startoffset)
    else:
        return memSIB (base, opindex, indexshift, startoffset)

class OpComputeSize(Operation):
    clobbers_cc = False
    def __init__(self, varsizealloctoken, gv_length):
        self.varsizealloctoken = varsizealloctoken
        self.gv_length = gv_length
    def allocate(self, allocator):
        allocator.using(self.gv_length)
    def generate(self, allocator):
        dstop = allocator.get_operand(self)
        srcop = allocator.get_operand(self.gv_length)
        mc = allocator.mc
        op_size = array_item_operand(mc, None, self.varsizealloctoken, srcop)
        try:
            mc.LEA(dstop, op_size)
        except FailedToImplement:
            mc.LEA(ecx, op_size)
            mc.MOV(dstop, ecx)

def hard_store(mc, opmemtarget, opvalue, itemsize):
    # For the possibly hard cases of stores
    # Generates a store to 'opmemtarget' of size 'itemsize' == 1, 2 or 4.
    # If it is 1, opmemtarget must be a MODRM8; otherwise, it must be a MODRM.
    if itemsize == WORD:
        try:
            mc.MOV(opmemtarget, opvalue)
        except FailedToImplement:
            if opmemtarget.involves_ecx():
                mc.PUSH(opvalue)
                mc.POP(opmemtarget)
            else:
                mc.MOV(ecx, opvalue)
                mc.MOV(opmemtarget, ecx)
    else:
        must_pop_eax = False
        if itemsize == 1:
            if isinstance(opvalue, REG) and opvalue.lowest8bits:
                # a register whose lower 8 bits are directly readable
                opvalue = opvalue.lowest8bits
            elif isinstance(opvalue, IMM8):
                pass
            else:
                if opmemtarget.involves_ecx():    # grumble!
                    mc.PUSH(eax)
                    must_pop_eax = True
                    scratch = eax
                else:
                    scratch = ecx
                if opvalue.width == 1:
                    mc.MOV(scratch.lowest8bits, opvalue)
                else:
                    mc.MOV(scratch, opvalue)
                opvalue = scratch.lowest8bits
        else:
            assert itemsize == 2
            if isinstance(opvalue, MODRM) or type(opvalue) is IMM32:
                # no support for now to encode 16-bit immediates,
                # so we use a scratch register for this case too
                if opmemtarget.involves_ecx():    # grumble!
                    mc.PUSH(eax)
                    must_pop_eax = True
                    scratch = eax
                else:
                    scratch = ecx
                mc.MOV(scratch, opvalue)
                opvalue = scratch
            mc.o16()    # prefix for the MOV below
        # and eventually, the real store:
        mc.MOV(opmemtarget, opvalue)
        if must_pop_eax:
            mc.POP(eax)

def hard_load(mc, opdst, opmemsource, itemsize):
    # For the possibly hard cases of stores
    # Generates a load from 'opmemsource' of size 'itemsize' == 1, 2 or 4.
    # If it is 1, opmemtarget must be a MODRM8; otherwise, it must be a MODRM.
    if itemsize == WORD:
        try:
            mc.MOV(opdst, opmemsource)
        except FailedToImplement:               # opdst is a MODRM
            if opmemsource.involves_ecx():
                mc.PUSH(opmemsource)
                mc.POP(opdst)
            else:
                mc.MOV(ecx, opmemsource)
                mc.MOV(opdst, ecx)
    else:
        try:
            mc.MOVZX(opdst, opmemsource)
        except FailedToImplement:               # opdst is a MODRM
            if opmemsource.involves_ecx():
                mc.PUSH(eax)
                mc.MOVZX(eax, opmemsource)
                mc.MOV(opdst, eax)
                mc.POP(eax)
            else:
                mc.MOVZX(ecx, opmemsource)
                mc.MOV(opdst, ecx)

class OpGetField(Operation):
    clobbers_cc = False
    def __init__(self, fieldtoken, gv_ptr):
        self.fieldtoken = fieldtoken
        self.gv_ptr = gv_ptr
    def allocate(self, allocator):
        allocator.using(self.gv_ptr)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # result not used
        opptr = allocator.get_operand(self.gv_ptr)
        mc = allocator.mc
        opsource = field_operand(mc, opptr, self.fieldtoken)
        _, fieldsize = self.fieldtoken
        hard_load(mc, dstop, opsource, fieldsize)

class OpSetField(Operation):
    clobbers_cc = False
    result_kind = RK_NO_RESULT
    def __init__(self, fieldtoken, gv_ptr, gv_value):
        self.fieldtoken = fieldtoken
        self.gv_ptr   = gv_ptr
        self.gv_value = gv_value
    def allocate(self, allocator):
        allocator.using(self.gv_ptr)
        allocator.using(self.gv_value)
    def generate(self, allocator):
        opptr   = allocator.get_operand(self.gv_ptr)
        opvalue = allocator.get_operand(self.gv_value)
        mc = allocator.mc
        optarget = field_operand(mc, opptr, self.fieldtoken)
        _, fieldsize = self.fieldtoken
        hard_store(mc, optarget, opvalue, fieldsize)

class OpGetArrayItem(Operation):
    def __init__(self, arraytoken, gv_array, gv_index):
        self.arraytoken = arraytoken
        self.gv_array = gv_array
        self.gv_index = gv_index
    def allocate(self, allocator):
        allocator.using(self.gv_array)
        allocator.using(self.gv_index)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # result not used
        oparray = allocator.get_operand(self.gv_array)
        opindex = allocator.get_operand(self.gv_index)
        mc = allocator.mc
        opsource = array_item_operand(mc, oparray, self.arraytoken, opindex)
        _, _, itemsize = self.arraytoken
        hard_load(mc, dstop, opsource, itemsize)

class OpSetArrayItem(Operation):
    result_kind = RK_NO_RESULT
    def __init__(self, arraytoken, gv_array, gv_index, gv_value):
        self.arraytoken = arraytoken
        self.gv_array = gv_array
        self.gv_index = gv_index
        self.gv_value = gv_value
    def allocate(self, allocator):
        allocator.using(self.gv_array)
        allocator.using(self.gv_index)
        allocator.using(self.gv_value)
    def generate(self, allocator):
        oparray = allocator.get_operand(self.gv_array)
        opindex = allocator.get_operand(self.gv_index)
        opvalue = allocator.get_operand(self.gv_value)
        mc = allocator.mc
        optarget = array_item_operand(mc, oparray, self.arraytoken, opindex)
        _, _, itemsize = self.arraytoken
        hard_store(mc, optarget, opvalue, itemsize)

class OpGetArraySubstruct(Operation):
    def __init__(self, arraytoken, gv_array, gv_index):
        self.arraytoken = arraytoken
        self.gv_array = gv_array
        self.gv_index = gv_index
    def allocate(self, allocator):
        allocator.using(self.gv_array)
        allocator.using(self.gv_index)
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # result not used
        oparray = allocator.get_operand(self.gv_array)
        opindex = allocator.get_operand(self.gv_index)
        mc = allocator.mc
        opsource = array_item_operand(mc, oparray, self.arraytoken, opindex)
        try:
            mc.LEA(dstop, opsource)
        except FailedToImplement:
            mc.LEA(ecx, opsource)
            mc.MOV(dstop, ecx)

class OpGetFrameBase(Operation):
    def generate(self, allocator):
        try:
            dstop = allocator.get_operand(self)
        except KeyError:
            return    # result not used
        mc = allocator.mc
        mc.MOV(dstop, ebp)

# ____________________________________________________________

def setup_opclasses(base):
    d = {}
    for name, value in globals().items():
        if type(value) is type(base) and issubclass(value, base):
            opnames = getattr(value, 'opname', ())
            if isinstance(opnames, str):
                opnames = (opnames,)
            for opname in opnames:
                assert opname not in d
                d[opname] = value
    return d
OPCLASSES1 = setup_opclasses(Op1)
OPCLASSES2 = setup_opclasses(Op2)
del setup_opclasses

# identity operations
OPCLASSES1['cast_bool_to_int'] = None
OPCLASSES1['cast_char_to_int'] = None
OPCLASSES1['cast_unichar_to_int'] = None
OPCLASSES1['cast_int_to_char'] = None
OPCLASSES1['cast_int_to_unichar'] = None
OPCLASSES1['cast_ptr_to_int'] = None
OPCLASSES1['cast_int_to_ptr'] = None
OPCLASSES1['cast_uint_to_int'] = None
OPCLASSES1['cast_bool_to_uint'] = None
OPCLASSES1['cast_int_to_uint'] = None

# special cases
#OPCLASSES1['bool_not'] = genop_bool_not       XXX do something about it

@specialize.memo()
def getopclass1(opname):
    try:
        return OPCLASSES1[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

@specialize.memo()
def getopclass2(opname):
    try:
        return OPCLASSES2[opname]
    except KeyError:
        raise MissingBackendOperation(opname)

class MissingBackendOperation(Exception):
    pass


def setup_conditions():
    result1 = [None] * 16
    result2 = [None] * 16
    for key, value in Conditions.items():
        result1[value] = getattr(I386CodeBuilder, 'J'+key)
        result2[value] = getattr(I386CodeBuilder, 'SET'+key)
    return result1, result2
EMIT_JCOND, EMIT_SETCOND = setup_conditions()
INSN_JMP = len(EMIT_JCOND)
EMIT_JCOND.append(I386CodeBuilder.JMP)    # not really a conditional jump
del setup_conditions

def cond_negate(cond):
    assert 0 <= cond < INSN_JMP
    return cond ^ 1

SIZE2SHIFT = {1: 0,
              2: 1,
              4: 2,
              8: 3}
