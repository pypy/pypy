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


class Operation(GenVar):
    clobbers_cc = True
    side_effects = True

    def mark_used_vars(self, allocator):
        raise NotImplementedError
    def generate(self, allocator):
        raise NotImplementedError

class Op1(Operation):
    def __init__(self, x):
        self.x = x
    def mark_used_vars(self, allocator):
        allocator.using(self.x)

class UnaryOp(Op1):
    side_effects = False
    def mark_used_vars(self, allocator):
        allocator.using_inplace(self.x, self)
    def generate(self, allocator):
        srcop = allocator.get_operand(self.x)
        if allocator.release(self.x):
            # in-place operation
            dstop = srcop
            allocator.create_exactly_at(self, dstop)
        else:
            # make a copy in a new register
            dstop = allocator.create_reg(self, srcop)
        self.emit(allocator.mc, dstop)

class OpIntNeg(UnaryOp):
    opname = 'int_neg', 'int_neg_ovf'
    emit = staticmethod(I386CodeBuilder.NEG)
    ccexcflag = Conditions['O']

class OpIntInvert(UnaryOp):
    opname = 'int_invert', 'uint_invert'
    emit = staticmethod(I386CodeBuilder.NOT)

class OpIntAbs(Op1):
    opname = 'int_abs', 'int_abs_ovf'
    side_effects = False
    ccexcflag = Conditions['L']
    def mark_used_vars(self, allocator):
        allocator.using(self.x)
    def generate(self, allocator):
        srcop = allocator.grab_operand(self.x)
        dstop = allocator.create_reg(self, srcop)
        # ABS-computing code from Psyco, found by exhaustive search
        # on *all* short sequences of operations :-)
        mc = allocator.mc
        mc.SHL(dstop, imm8(1))
        mc.SBB(dstop, srcop)
        allocator.release(self.x)
        tmpop = allocator.create_scratch_reg()
        mc.SBB(tmpop, tmpop)
        mc.XOR(dstop, tmpop)
        allocator.end_clobber(tmpop)

class OpSameAs(Op1):
    clobbers_cc = False    # special handling of the cc
    side_effects = False
    def mark_used_vars(self, allocator):
        allocator.using_inplace(self.x, self)
    def generate(self, allocator):
        srcop = allocator.get_operand(self.x)
        if allocator.lastuse(self.x):
            allocator.release(self.x)
            if isinstance(srcop, CCFLAG):
                allocator.create_in_cc(self, srcop)
            else:
                allocator.create_exactly_at(self, srcop)
        else:
            if isinstance(srcop, CCFLAG):
                allocator.clobber_cc()   # which doesn't itself clobber cc,
                                         # so we can reuse it for us
                allocator.create_in_cc(self, srcop)
            else:
                if isinstance(srcop, MODRM):
                    dstop = allocator.create_reg(self)   # no stack->stack copy
                else:
                    dstop = allocator.create(self)
                if srcop != dstop:    # else srcop spilled, but still in place
                    allocator.mc.MOV(dstop, srcop)
            allocator.release(self.x)

class OpCompare1(Op1):
    clobbers_cc = False    # special handling of the cc
    side_effects = False

    def generate(self, allocator):
        mc = allocator.mc
        srcop = allocator.grab_operand(self.x)
        if isinstance(srcop, CCFLAG):
            ccop = srcop
            allocator.release(self.x)
            allocator.clobber_cc()
            # the flags are still valid through a clobber_cc
            if self.inverted:
                ccop = ccflags[cond_negate(ccop.cc)]
        else:
            allocator.clobber_cc()
            mc.CMP(srcop, imm8(0))
            allocator.release(self.x)
            ccop = ccflags[self.suggested_cc]
        allocator.create_in_cc(self, ccop)

class OpIntIsTrue(OpCompare1):
    opname = 'int_is_true', 'ptr_nonzero', 'uint_is_true'
    suggested_cc = Conditions['NE']
    inverted = False

class OpIntIsZero(OpIntIsTrue):
    opname = 'ptr_iszero', 'bool_not'
    suggested_cc = Conditions['E']
    inverted = True

class OpFetchCC(Operation):
    clobbers_cc = False
    side_effects = False
    def __init__(self, cc):
        self.cc = cc
    def mark_used_vars(self, allocator):
        pass
    def generate(self, allocator):
        ccop = ccflags[self.cc]
        allocator.create_in_cc(self, ccop)

class Op2(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def mark_used_vars(self, allocator):
        allocator.using(self.x)
        allocator.using(self.y)

class BinaryOp(Op2):
    side_effects = False
    commutative = False

    def mark_used_vars(self, allocator):
        inplace_ok = allocator.using_inplace(self.x, self)
        if not inplace_ok and self.commutative:
            allocator.using_inplace(self.y, self)
        else:
            allocator.using(self.y)

    def generate(self, allocator):
        # warning, subtleties about using get_operand() instead
        # of grab_operand() for the best possible results
        x, y = self.x, self.y
        op1 = allocator.get_operand(x)
        op2 = allocator.get_operand(y)
        xlast = allocator.lastuse(x)
        if self.commutative and not xlast and allocator.lastuse(y):
            # reverse arguments, then it's an in-place operation
            x, y = y, x
            op1, op2 = op2, op1
            xlast = True

        if xlast:
            dstop = op1   # in-place operation
            # op1 and op2 must not be both in a stack location
            if isinstance(op1, MODRM) and isinstance(op2, MODRM):
                tmpop = allocator.create_scratch_reg(op2)
                # neither op1 nor op2 can have been spilled here, as
                # they are already in the stack
                op2 = tmpop
                allocator.end_clobber(tmpop)
            allocator.release(x)
            allocator.release(y)
            allocator.create_exactly_at(self, op1)
        else:
            dstop = allocator.create_reg(self, op1)
            op2 = allocator.get_operand(y)
            allocator.release(y)
        self.emit(allocator.mc, dstop, op2)

class OpIntAdd(BinaryOp):
    opname = 'int_add', 'uint_add', 'int_add_ovf'
    emit = staticmethod(I386CodeBuilder.ADD)
    commutative = True
    ccexcflag = Conditions['O']

class OpIntSub(BinaryOp):
    opname = 'int_sub', 'uint_sub', 'int_sub_ovf'
    emit = staticmethod(I386CodeBuilder.SUB)
    ccexcflag = Conditions['O']

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
    opname = 'int_mul', 'int_mul_ovf'
    side_effects = False
    ccexcflag = Conditions['O']

    def generate(self, allocator):
        op1 = allocator.get_operand(self.x)
        op2 = allocator.get_operand(self.y)

        if isinstance(op1, REG) and allocator.lastuse(self.x):
            allocator.release(self.x)
            allocator.release(self.y)
            allocator.create_exactly_at(self, op1)
            dstop = op1
        elif isinstance(op2, REG) and allocator.lastuse(self.y):
            allocator.release(self.x)
            allocator.release(self.y)
            allocator.create_exactly_at(self, op2)
            dstop = op2
        else:
            dstop = allocator.create_reg(self)
            allocator.release(self.x)
            allocator.release(self.y)
        mc = allocator.mc
        if isinstance(op2, IMM32):
            mc.IMUL(dstop, op1, op2)
        elif isinstance(op1, IMM32):
            mc.IMUL(dstop, op2, op1)
        elif dstop == op1:
            mc.IMUL(dstop, op2)
        elif dstop == op2:
            mc.IMUL(dstop, op1)
        else:
            mc.MOV(dstop, op1)
            mc.IMUL(dstop, op2)

class MulOrDivOp(Op2):
    side_effects = False

    def generate(self, allocator):
        # XXX not very efficient but not very common operations either
        allocator.clobber2(eax, edx)
        mc = allocator.mc

        op1 = allocator.get_operand(self.x)
        if op1 != eax:
            mc.MOV(eax, op1)
        if self.input_is_64bits:
            if self.unsigned:
                mc.XOR(edx, edx)
            else:
                mc.CDQ()

        op2 = allocator.grab_operand(self.y)
        try:
            self.generate2(allocator, op2)
        except FailedToImplement:
            tmp = allocator.create_scratch_reg(op2)
            self.generate2(allocator, tmp)
            allocator.end_clobber(tmp)

        allocator.end_clobber(eax)
        allocator.end_clobber(edx)
        allocator.release(self.x)
        allocator.release(self.y)
        # the target register should still be free, see clobber2()
        allocator.create_exactly_at(self, self.reg_containing_result)

## __________ logic for Python-like division and modulo _________
##
## (disabled for now, as int_floordiv and int_mod have CPU-like
## semantics at the moment)

##class OpIntFloorDiv(MulOrDivOp):
##    opname = 'int_floordiv'
##    input_is_64bits = True
##    reg_containing_result = eax
##    unsigned = False

##    def generate2(self, allocator, op2):
##        # from the PPC backend which has the same problem:
##        # 
##        #   grumble, the powerpc handles division when the signs of x
##        #   and y differ the other way to how cpython wants it.  this
##        #   crawling horror is a branch-free way of computing the right
##        #   remainder in all cases.  it's probably not optimal.
##        #
##        #   we need to adjust the result iff the remainder is non-zero
##        #   and the signs of x and y differ.  in the standard-ish PPC
##        #   way, we compute boolean values as either all-bits-0 or
##        #   all-bits-1 and "and" them together, resulting in either
##        #   adding 0 or -1 as needed in the final step.
##        #
##        #                 Python    i386
##        #    20/3    =     6, 2     6, 2
##        # (-20)/3    =    -7, 1    -6,-2      # operand signs differ
##        #    20/(-3) =    -7,-1    -6, 2      # operand signs differ
##        # (-20)/(-3) =     6,-2     6,-2
##        #
##        tmp = allocator.create_scratch_reg()
##        mc = allocator.mc
##        if isinstance(op2, IMM32):      XXX
##            # if op2 is an immediate, we do an initial adjustment of operand 1
##            # so that we get directly the correct answer
##            if op2.value >= 0:
##                # if op1 is negative, subtract (op2-1)
##                mc.MOV(tmp, edx)       # -1 if op1 is negative, 0 otherwise
##                mc.AND(tmp, imm(op2.value-1))
##                mc.SUB(eax, tmp)
##                mc.SBB(edx, imm8(0))
##            else:
##                # if op1 is positive (or null), add (|op2|-1)
##                mc.MOV(tmp, edx)
##                mc.NOT(tmp)            # -1 if op1 is positive, 0 otherwise
##                mc.AND(tmp, imm(-op2.value-1))
##                mc.ADD(eax, tmp)
##                mc.ADC(edx, imm8(0))
##            mc.MOV(tmp, op2)
##            mc.IDIV(tmp)
##        else:
##            # subtract 1 to the result if the operand signs differ and
##            # the remainder is not zero
##            mc.MOV(tmp, eax)
##            mc.IDIV(op2)
##            mc.XOR(tmp, op2)
##            mc.SAR(tmp, imm8(31)) # -1 if signs differ, 0 otherwise
##            mc.AND(tmp, edx)      # nonnull if signs differ and edx != 0
##            mc.CMP(tmp, imm8(1))  # no carry flag iff signs differ and edx != 0
##            mc.ADC(eax, imm8(-1)) # subtract 1 iff no carry flag
##        allocator.end_clobber(tmp)

##class OpIntMod(MulOrDivOp):
##    opname = 'int_mod'
##    input_is_64bits = True
##    reg_containing_result = edx
##    unsigned = False

##    def generate2(self, allocator, op2):
##        #                 Python    i386
##        #    20/3    =     6, 2     6, 2
##        # (-20)/3    =    -7, 1    -6,-2      # operand signs differ
##        #    20/(-3) =    -7,-1    -6, 2      # operand signs differ
##        # (-20)/(-3) =     6,-2     6,-2
##        #
##        tmp = allocator.create_scratch_reg()
##        mc = allocator.mc
##        if isinstance(op2, IMM32):   XXX
##            mc.MOV(tmp, op2)
##            mc.IDIV(tmp)
##            # adjustment needed:
##            #   if op2 > 0: if the result is negative, add op2 to it
##            #   if op2 < 0: if the result is > 0, subtract |op2| from it
##            mc.MOV(tmp, edx)
##            if op2.value < 0:
##                mc.NEG(tmp)
##            mc.SAR(tmp, imm8(31))
##            mc.AND(tmp, imm(op2.value))
##            mc.ADD(edx, tmp)
##        else:
##            # if the operand signs differ and the remainder is not zero,
##            # add operand2 to the result
##            mc.MOV(tmp, eax)
##            mc.IDIV(op2)
##            mc.XOR(tmp, op2)
##            mc.SAR(tmp, imm8(31)) # -1 if signs differ, 0 otherwise
##            mc.AND(tmp, edx)      # nonnull if signs differ and edx != 0
##            mc.CMOVNZ(tmp, op2)   # == op2  if signs differ and edx != 0
##            mc.ADD(edx, tmp)
##        allocator.end_clobber(tmp)

class OpUIntMul(MulOrDivOp):
    opname = 'uint_mul'
    input_is_64bits = False
    reg_containing_result = eax
    unsigned = True
    def generate2(self, allocator, op2):
        allocator.mc.MUL(op2)

class OpUIntFloorDiv(MulOrDivOp):
    opname = 'uint_floordiv'
    input_is_64bits = True
    reg_containing_result = eax
    unsigned = True
    def generate2(self, allocator, op2):
        allocator.mc.DIV(op2)

class OpUIntMod(MulOrDivOp):
    opname = 'uint_mod'
    input_is_64bits = True
    reg_containing_result = edx
    unsigned = True
    def generate2(self, allocator, op2):
        allocator.mc.DIV(op2)

class OpIntFloorDiv(MulOrDivOp):
    opname = 'int_floordiv'
    input_is_64bits = True
    reg_containing_result = eax
    unsigned = False
    def generate2(self, allocator, op2):
        allocator.mc.IDIV(op2)

class OpIntMod(MulOrDivOp):
    opname = 'int_mod'
    input_is_64bits = True
    reg_containing_result = edx
    unsigned = False
    def generate2(self, allocator, op2):
        allocator.mc.IDIV(op2)

class OpShift(Op2):
    side_effects = False
    countmax31 = False

    def mark_used_vars(self, allocator):
        allocator.using_inplace(self.x, self)
        allocator.using(self.y)
        if not self.countmax31:
            allocator.suggests(self.y, ecx)

    def generate(self, allocator):
        op2 = allocator.get_operand(self.y)
        holds_ecx = False
        mc = allocator.mc
        if isinstance(op2, IMM32):
            n = op2.value
            if n < 0 or n >= 32:
                # shift out of range
                if self.countmax31:
                    n = 31   # case in which it's equivalent to a shift by 31
                else:
                    # case in which the result is always zero
                    allocator.release(self.x)
                    allocator.release(self.y)
                    dstop = allocator.create_reg(self)
                    mc.XOR(dstop, dstop)
                    return
            count = imm8(n)
        else:
            if self.countmax31:
                allocator.clobber(ecx)
                holds_ecx = True
                op2 = allocator.get_operand(self.y)
                mc.MOV(ecx, imm8(31))
                mc.CMP(op2, ecx)
                mc.CMOVBE(ecx, op2)
                allocator.release(self.y)
            elif op2 != ecx:
                allocator.clobber(ecx)
                holds_ecx = True
                op2 = allocator.get_operand(self.y)
                mc.MOV(ecx, op2)
                allocator.release(self.y)
            else:
                op2 = allocator.grab_operand(self.y)
                assert op2 == ecx
            count = cl

        srcop = allocator.get_operand(self.x)
        if allocator.release(self.x):
            dstop = srcop           # in-place operation
            allocator.create_exactly_at(self, dstop)
        else:
            # make a copy in a new register
            dstop = allocator.create_reg(self, srcop)

        self.emit(mc, dstop, count)
        if count is cl:
            if not self.countmax31:
                mc.CMP(ecx, imm8(32))
                mc.SBB(ecx, ecx)
                mc.AND(dstop, ecx)
            if holds_ecx:
                allocator.end_clobber(ecx)
            else:
                allocator.release(self.y)

class OpIntLShift(OpShift):
    opname = 'int_lshift', 'uint_lshift'
    emit = staticmethod(I386CodeBuilder.SHL)

class OpUIntRShift(OpShift):
    opname = 'uint_rshift'
    emit = staticmethod(I386CodeBuilder.SHR)

class OpIntRShift(OpShift):
    opname = 'int_rshift'
    emit = staticmethod(I386CodeBuilder.SAR)
    countmax31 = True

class OpCompare2(Op2):
    side_effects = False

    def generate(self, allocator):
        op1 = allocator.get_operand(self.x)
        op2 = allocator.get_operand(self.y)
        mc = allocator.mc
        cond = self.suggested_cc
        try:
            mc.CMP(op1, op2)
        except FailedToImplement:
            # try reversing the arguments, for CMP(immed, reg-or-modrm)
            try:
                mc.CMP(op2, op1)
            except FailedToImplement:
                # CMP(stack, stack)
                reg = allocator.create_scratch_reg(op1)
                op2 = allocator.get_operand(self.y)
                mc.CMP(reg, op2)
                allocator.end_clobber(reg)
            else:
                cond = cond_swapargs(cond)    # worked with arguments reversed
        allocator.release(self.x)
        allocator.release(self.y)
        allocator.create_in_cc(self, ccflags[cond])

class OpIntLt(OpCompare2):
    opname = 'int_lt', 'char_lt'
    suggested_cc = Conditions['L']

class OpIntLe(OpCompare2):
    opname = 'int_le', 'char_le'
    suggested_cc = Conditions['LE']

class OpIntEq(OpCompare2):
    opname = 'int_eq', 'char_eq', 'unichar_eq', 'ptr_eq', 'uint_eq'
    suggested_cc = Conditions['E']

class OpIntNe(OpCompare2):
    opname = 'int_ne', 'char_ne', 'unichar_ne', 'ptr_ne', 'uint_ne'
    suggested_cc = Conditions['NE']

class OpIntGt(OpCompare2):
    opname = 'int_gt', 'char_gt'
    suggested_cc = Conditions['G']

class OpIntGe(OpCompare2):
    opname = 'int_ge', 'char_ge'
    suggested_cc = Conditions['GE']

class OpUIntLt(OpCompare2):
    opname = 'uint_lt'
    suggested_cc = Conditions['B']

class OpUIntLe(OpCompare2):
    opname = 'uint_le'
    suggested_cc = Conditions['BE']

class OpUIntGt(OpCompare2):
    opname = 'uint_gt'
    suggested_cc = Conditions['A']

class OpUIntGe(OpCompare2):
    opname = 'uint_ge'
    suggested_cc = Conditions['AE']

class JumpIf(Operation):
    clobbers_cc = False
    negate = False
    def __init__(self, gv_condition, targetbuilder):
        self.gv_condition = gv_condition
        self.targetbuilder = targetbuilder
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_condition)
        for gv in self.targetbuilder.inputargs_gv:
            allocator.using(gv)
    def generate(self, allocator):
        targetbuilder = self.targetbuilder
        op = allocator.get_operand(self.gv_condition)
        mc = allocator.mc
        if isinstance(op, CCFLAG):
            cc = op.cc
        else:
            allocator.clobber_cc()
            op = allocator.get_operand(self.gv_condition)
            mc.CMP(op, imm(0))
            cc = Conditions['NE']
        allocator.release(self.gv_condition)
        operands = []
        for gv in targetbuilder.inputargs_gv:
            operands.append(allocator.get_operand(gv))
            allocator.release(gv)
        if self.negate:
            cc = cond_negate(cc)
        targetbuilder.set_coming_from(mc, insncond=cc)
        targetbuilder.inputoperands = operands
        #assert targetbuilder.inputoperands.count(ebx) <= 1

class JumpIfNot(JumpIf):
    negate = True

class OpLabel(Operation):
    # NB. this is marked to clobber the CC, because it cannot easily
    #     be saved/restored across a label.  The problem is that someone
    #     might later try to jump to this label with a new value for
    #     the variable that is different from 0 or 1, i.e. which cannot
    #     be represented in the CC at all.
    def __init__(self, lbl, args_gv):
        self.lbl = lbl
        self.args_gv = args_gv
    def mark_used_vars(self, allocator):
        for v in self.args_gv:
            allocator.using(v)
    def generate(self, allocator):
        operands = []
        for v in self.args_gv:
            operands.append(allocator.get_operand(v))
            allocator.release(v)
        lbl = self.lbl
        lbl.targetaddr = allocator.mc.tell()
        lbl.inputoperands = operands
        lbl.targetbuilder = None    # done generating

class OpCall(Operation):
    def __init__(self, sigtoken, gv_fnptr, args_gv):
        self.sigtoken = sigtoken
        self.gv_fnptr = gv_fnptr
        self.args_gv = args_gv

    def mark_used_vars(self, allocator):
        allocator.using(self.gv_fnptr)
        for v in self.args_gv:
            allocator.using(v)

    def generate(self, allocator):
        mc = allocator.mc
        args_gv = self.args_gv

        stackargs_i = []
        for i in range(len(args_gv)):
            srcop = allocator.get_operand(args_gv[i])
            if isinstance(srcop, MODRM):
                stackargs_i.append(i)
            else:
                mc.MOV(mem(esp, WORD * i), srcop)
                allocator.release(args_gv[i])

        allocator.clobber3(eax, edx, ecx)
        allocator.reserve_extra_stack(len(args_gv))

        if len(stackargs_i) > 0:
            tmp = eax
            for i in stackargs_i:
                srcop = allocator.get_operand(args_gv[i])
                mc.MOV(tmp, srcop)
                mc.MOV(mem(esp, WORD * i), tmp)
                allocator.release(args_gv[i])

        fnop = allocator.get_operand(self.gv_fnptr)
        if isinstance(fnop, IMM32):
            mc.CALL(rel32(fnop.value))
        else:
            mc.CALL(fnop)

        allocator.release(self.gv_fnptr)
        allocator.end_clobber(eax)
        allocator.end_clobber(edx)
        allocator.end_clobber(ecx)
        if allocator.operation_result_is_used(self):
            allocator.create_exactly_at(self, eax)


def field_operand(allocator, gv_base, fieldtoken):
    fieldoffset, fieldsize = fieldtoken
    base = allocator.get_operand(gv_base)
    if isinstance(base, MODRM):
        tmp = allocator.create_scratch_reg(base)
        allocator.end_clobber(tmp)
        base = tmp
    elif isinstance(base, IMM32):
        fieldoffset += base.value
        base = None
    allocator.release(gv_base)

    if fieldsize == 1:
        return mem8(base, fieldoffset)
    else:
        return mem (base, fieldoffset)

def array_item_operand(allocator, gv_base, arraytoken, gv_opindex):
    tmp = None
    _, startoffset, itemoffset = arraytoken

    opindex = allocator.get_operand(gv_opindex)
    if isinstance(opindex, IMM32):
        startoffset += itemoffset * opindex.value
        opindex = None
        indexshift = 0
    elif itemoffset in SIZE2SHIFT:
        if not isinstance(opindex, REG):
            tmp = allocator.create_scratch_reg(opindex)
            opindex = tmp
        indexshift = SIZE2SHIFT[itemoffset]
    else:
        tmp = allocator.create_scratch_reg()
        allocator.mc.IMUL(tmp, opindex, imm(itemoffset))
        opindex = tmp
        indexshift = 0

    if gv_base is None:
        base = None
    else:
        base = allocator.get_operand(gv_base)
        if isinstance(base, MODRM):
            if tmp is None:
                tmp = allocator.create_scratch_reg(base)
            else:   # let's avoid using two scratch registers
                opindex = None
                if indexshift > 0:
                    allocator.mc.SHL(tmp, imm8(indexshift))
                allocator.mc.ADD(tmp, base)
            base = tmp
        elif isinstance(base, IMM32):
            startoffset += base.value
            base = None
        allocator.release(gv_base)

    if tmp is not None:
        allocator.end_clobber(tmp)
    allocator.release(gv_opindex)

    if itemoffset == 1:
        return memSIB8(base, opindex, indexshift, startoffset)
    else:
        return memSIB (base, opindex, indexshift, startoffset)

class OpComputeSize(Operation):
    clobbers_cc = False
    side_effects = False
    def __init__(self, varsizealloctoken, gv_length):
        self.varsizealloctoken = varsizealloctoken
        self.gv_length = gv_length
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_length)
    def generate(self, allocator):
        op_size = array_item_operand(allocator, None,
                                     self.varsizealloctoken, self.gv_length)
        dstop = allocator.create_reg(self)
        allocator.mc.LEA(dstop, op_size)

class OpGetter(Operation):
    side_effects = False
    def generate(self, allocator):
        opsource = self.generate_opsource(allocator)
        dstop = allocator.create_reg(self)
        if self.getwidth() == WORD:
            allocator.mc.MOV(dstop, opsource)
        else:
            allocator.mc.MOVZX(dstop, opsource)

class OpSetter(Operation):
    def generate(self, allocator):
        tmpval = None
        width = self.getwidth()
        opvalue = allocator.grab_operand(self.gv_value)
        if width == 1:
            try:
                opvalue = opvalue.lowest8bits()
            except ValueError:
                tmpval = allocator.create_scratch_reg8(opvalue)
                opvalue = tmpval
            else:
                if isinstance(opvalue, MODRM8):
                    tmpval = allocator.create_scratch_reg8(opvalue)
                    opvalue = tmpval
        else:
            if isinstance(opvalue, MODRM):
                tmpval = allocator.create_scratch_reg(opvalue)
                opvalue = tmpval
        optarget = self.generate_optarget(allocator)
        if width == 2:
            if isinstance(opvalue, IMM32):
                opvalue = IMM16(opvalue.value)
            allocator.mc.o16()
        allocator.mc.MOV(optarget, opvalue)
        if tmpval is not None:
            allocator.end_clobber(tmpval)

class OpGetField(OpGetter):
    clobbers_cc = False
    def __init__(self, fieldtoken, gv_ptr):
        self.fieldtoken = fieldtoken
        self.gv_ptr = gv_ptr
    def getwidth(self):
        _, fieldsize = self.fieldtoken
        return fieldsize
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_ptr)
    def generate_opsource(self, allocator):
        opsource = field_operand(allocator, self.gv_ptr, self.fieldtoken)
        return opsource

class OpSetField(OpSetter):
    clobbers_cc = False
    def __init__(self, fieldtoken, gv_ptr, gv_value):
        self.fieldtoken = fieldtoken
        self.gv_ptr   = gv_ptr
        self.gv_value = gv_value
    def getwidth(self):
        _, fieldsize = self.fieldtoken
        return fieldsize
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_ptr)
        allocator.using(self.gv_value)
    def generate_optarget(self, allocator):
        optarget = field_operand(allocator, self.gv_ptr, self.fieldtoken)
        allocator.release(self.gv_value)
        return optarget

class OpGetArrayItem(OpGetter):
    def __init__(self, arraytoken, gv_array, gv_index):
        self.arraytoken = arraytoken
        self.gv_array = gv_array
        self.gv_index = gv_index
    def getwidth(self):
        _, _, itemsize = self.arraytoken
        return itemsize
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_array)
        allocator.using(self.gv_index)
    def generate_opsource(self, allocator):
        opsource = array_item_operand(allocator, self.gv_array,
                                      self.arraytoken, self.gv_index)
        return opsource

class OpGetArraySubstruct(OpGetArrayItem):
    def generate(self, allocator):
        opsource = self.generate_opsource(allocator)
        dstop = allocator.create_reg(self)
        allocator.mc.LEA(dstop, opsource)

class OpSetArrayItem(OpSetter):
    def __init__(self, arraytoken, gv_array, gv_index, gv_value):
        self.arraytoken = arraytoken
        self.gv_array = gv_array
        self.gv_index = gv_index
        self.gv_value = gv_value
    def getwidth(self):
        _, _, itemsize = self.arraytoken
        return itemsize
    def mark_used_vars(self, allocator):
        allocator.using(self.gv_array)
        allocator.using(self.gv_index)
        allocator.using(self.gv_value)
    def generate_optarget(self, allocator):
        opsource = array_item_operand(allocator, self.gv_array,
                                      self.arraytoken, self.gv_index)
        allocator.release(self.gv_value)
        return opsource

class OpGetExitSwitch(Op1):
    # a bit of a hack: to put last in a block ending in a flexswitch,
    # to load the switch value into a register and remember which
    # register it is.
    def generate(self, allocator):
        op = allocator.get_operand(self.x)
        if isinstance(op, REG):
            self.reg = op
        else:
            self.reg = allocator.create_scratch_reg(op)
            allocator.end_clobber(self.reg)
        allocator.release(self.x)

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

def cond_swapargs(cond):
    return COND_SWAPARGS[cond]

COND_SWAPARGS = range(16)
COND_SWAPARGS[Conditions['L']]  = Conditions['G']
COND_SWAPARGS[Conditions['G']]  = Conditions['L']
COND_SWAPARGS[Conditions['NL']] = Conditions['NG']
COND_SWAPARGS[Conditions['NG']] = Conditions['NL']
COND_SWAPARGS[Conditions['B']]  = Conditions['A']
COND_SWAPARGS[Conditions['A']]  = Conditions['B']
COND_SWAPARGS[Conditions['NB']] = Conditions['NA']
COND_SWAPARGS[Conditions['NA']] = Conditions['NB']

SIZE2SHIFT = {1: 0,
              2: 1,
              4: 2,
              8: 3}

# ____________________________________________________________

class CCFLAG(OPERAND):
    _attrs_ = ['cc', 'SETCOND', 'load_into_cc']
    def __init__(self, cond, load_into_cc):
        self.cond = cond
        self.cc = Conditions[cond]
        self.SETCOND = getattr(I386CodeBuilder, 'SET' + cond)
        self.load_into_cc = load_into_cc

    def assembler(self):
        return self.cond


def load_into_cc_o(mc, srcop):
    mc.MOV(ecx, srcop)
    mc.ADD(ecx, imm(sys.maxint))

def load_into_cc_no(self, srcop):
    mc.MOV(ecx, imm(-sys.maxint-1))
    mc.ADD(ecx, srcop)
    mc.DEC(ecx)

def load_into_cc_lt(mc, srcop):
    mc.XOR(ecx, ecx)
    mc.CMP(ecx, srcop)

def load_into_cc_le(mc, srcop):
    mc.MOV(ecx, imm8(1))
    mc.CMP(ecx, srcop)

def load_into_cc_eq(mc, srcop):
    mc.CMP(srcop, imm8(1))

def load_into_cc_ne(mc, srcop):
    mc.CMP(srcop, imm8(0))

load_into_cc_gt = load_into_cc_ne
load_into_cc_ge = load_into_cc_eq

ccflag_o  = CCFLAG('O',  load_into_cc_o)
ccflag_no = CCFLAG('NO', load_into_cc_no)

ccflag_lt = CCFLAG('L',  load_into_cc_lt)
ccflag_le = CCFLAG('LE', load_into_cc_le)
ccflag_eq = CCFLAG('E',  load_into_cc_eq)
ccflag_ne = CCFLAG('NE', load_into_cc_ne)
ccflag_gt = CCFLAG('G',  load_into_cc_gt)
ccflag_ge = CCFLAG('GE', load_into_cc_ge)

ccflag_ult = CCFLAG('B',  load_into_cc_lt)
ccflag_ule = CCFLAG('BE', load_into_cc_le)
ccflag_ugt = CCFLAG('A',  load_into_cc_gt)
ccflag_uge = CCFLAG('AE', load_into_cc_ge)

ccflags = [None] * 16
ccflags[Conditions['O']]  = ccflag_o
ccflags[Conditions['NO']] = ccflag_no
ccflags[Conditions['L']]  = ccflag_lt
ccflags[Conditions['LE']] = ccflag_le
ccflags[Conditions['E']]  = ccflag_eq
ccflags[Conditions['NE']] = ccflag_ne
ccflags[Conditions['G']]  = ccflag_gt
ccflags[Conditions['GE']] = ccflag_ge
ccflags[Conditions['B']]  = ccflag_ult
ccflags[Conditions['BE']] = ccflag_ule
ccflags[Conditions['A']]  = ccflag_ugt
ccflags[Conditions['AE']] = ccflag_uge

##def ccmov(mc, dstop, ccop):
##    XXX
##    if dstop != ccop:
##        ccop.SETCOND(mc, cl)
##        if isinstance(dstop, CCFLAG):
##            dstop.load_into_cc(mc, cl)
##        else:
##            try:
##                mc.MOVZX(dstop, cl)
##            except FailedToImplement:
##                mc.MOVZX(ecx, cl)
##                mc.MOV(dstop, ecx)
