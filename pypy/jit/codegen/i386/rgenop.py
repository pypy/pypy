import sys, py
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386.ri386setup import Conditions
from pypy.jit.codegen.i386.codebuf import CodeBlockOverflow
from pypy.jit.codegen import conftest
from pypy.rpython.annlowlevel import llhelper


WORD = 4    # bytes
if sys.platform == 'darwin':
    CALL_ALIGN = 4
else:
    CALL_ALIGN = 1

PROLOGUE_FIXED_WORDS = 5

RK_NO_RESULT = 0
RK_WORD      = 1
RK_CC        = 2

DEBUG_TRAP = conftest.option.trap


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
            loc = allocator.var2loc[self]
        except KeyError:
            return    # simple operation whose result is not used anyway
        op = allocator.load_location_with(loc, self.x)
        self.emit(allocator.mc, op)

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
    opname = 'int_is_true', 'ptr_nonzero'
    cc_result = Conditions['NE']
    @staticmethod
    def emit(mc, x):
        mc.CMP(x, imm8(0))

class OpIntIsNull(OpIntIsTrue):
    opname = 'ptr_iszero'
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
        # not very efficient but not very common operations either
        if dstop != eax:
            mc.PUSH(eax)
        if dstop != edx:
            mc.PUSH(edx)
        if op1 != eax:
            mc.MOV(eax, op1)
        if self.input_is_64bits:
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
        if dstop != edx:
            mc.POP(edx)
        if dstop != eax:
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
    def generate3(self, mc, dstop, op1, op2):
        # XXX not optimized
        mc.MOV(ecx, op2)
        if dstop != op1:
            try:
                mc.MOV(dstop, op1)
            except FailedToImplement:
                mc.PUSH(op1)
                mc.POP(dstop)
        mc.SHL(dstop, cl)
        mc.CMP(ecx, imm8(32))
        mc.SBB(ecx, ecx)
        mc.AND(dstop, ecx)

class OpIntRShift(Op2):
    opname = 'int_rshift'
    def generate3(self, mc, dstop, op1, op2):
        # XXX not optimized
        mc.MOV(ecx, imm(31))
        mc.CMP(op2, ecx)
        mc.CMOVBE(ecx, op2)
        if dstop != op1:
            try:
                mc.MOV(dstop, op1)
            except FailedToImplement:
                mc.PUSH(op1)
                mc.POP(dstop)
        mc.SAR(dstop, cl)

class OpUIntRShift(Op2):
    opname = 'uint_rshift'
    def generate3(self, mc, dstop, op1, op2):
        # XXX not optimized
        mc.MOV(ecx, op2)
        if dstop != op1:
            try:
                mc.MOV(dstop, op1)
            except FailedToImplement:
                mc.PUSH(op1)
                mc.POP(dstop)
        mc.SHR(dstop, cl)
        mc.CMP(ecx, imm8(32))
        mc.SBB(ecx, ecx)
        mc.AND(dstop, ecx)

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
    opname = 'int_eq', 'char_eq', 'unichar_eq', 'ptr_eq'
    cc_result = Conditions['E']

class OpIntNe(OpCompare2):
    opname = 'int_ne', 'char_ne', 'unichar_ne', 'ptr_ne'
    cc_result = Conditions['NE']

class OpIntGt(OpCompare2):
    opname = 'int_gt', 'char_gt'
    cc_result = Conditions['G']

class OpIntGe(OpCompare2):
    opname = 'int_ge', 'char_ge'
    cc_result = Conditions['GE']

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

class Label(GenLabel):
    targetaddr = 0
    targetstackdepth = 0
    inputoperands = None

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

# ____________________________________________________________

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

    def __repr__(self):
        "NOT_RPYTHON"
        try:
            return "const=%s" % (imm(self.value).assembler(),)
        except TypeError:   # from Symbolics
            return "const=%r" % (self.value,)

    def repr(self):
        return "const=$%s" % (self.value,)

class AddrConst(GenConst):

    def __init__(self, addr):
        self.addr = addr

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
        "NOT_RPYTHON"
        return "const=%r" % (self.addr,)

    def repr(self):
        return "const=<0x%x>" % (llmemory.cast_adr_to_int(self.addr),)

# ____________________________________________________________

class FlexSwitch(CodeGenSwitch):
    REG = eax

    def __init__(self, rgenop, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands
        self.defaultcaseaddr = 0

    def initialize(self, mc):
        self._reserve(mc)
        default_builder = Builder(self.rgenop, self.inputargs_gv,
                                  self.inputoperands)
        start = self.nextfreepos
        end   = self.endfreepos
        fullmc = self.rgenop.InMemoryCodeBuilder(start, end)
        default_builder.set_coming_from(fullmc)
        fullmc.done()
        default_builder.update_defaultcaseaddr_of = self
        default_builder.start_writing()
        return default_builder

    def _reserve(self, mc):
        RESERVED = 11*4+5      # XXX quite a lot for now :-/
        pos = mc.tell()
        mc.UD2()
        mc.write('\x00' * (RESERVED-1))
        self.nextfreepos = pos
        self.endfreepos = pos + RESERVED

    def _reserve_more(self):
        start = self.nextfreepos
        end   = self.endfreepos
        newmc = self.rgenop.open_mc()
        self._reserve(newmc)
        self.rgenop.close_mc(newmc)
        fullmc = self.rgenop.InMemoryCodeBuilder(start, end)
        fullmc.JMP(rel32(self.nextfreepos))
        fullmc.done()
        
    def add_case(self, gv_case):
        rgenop = self.rgenop
        targetbuilder = Builder(self.rgenop, self.inputargs_gv,
                                self.inputoperands)
        try:
            self._add_case(gv_case, targetbuilder)
        except CodeBlockOverflow:
            self._reserve_more()
            self._add_case(gv_case, targetbuilder)
        targetbuilder.start_writing()
        return targetbuilder
    
    def _add_case(self, gv_case, targetbuilder):
        start = self.nextfreepos
        end   = self.endfreepos
        mc = self.rgenop.InMemoryCodeBuilder(start, end)
        value = gv_case.revealconst(lltype.Signed)
        mc.CMP(FlexSwitch.REG, imm(value))
        targetbuilder.set_coming_from(mc, Conditions['E'])
        pos = mc.tell()
        assert self.defaultcaseaddr != 0
        mc.JMP(rel32(self.defaultcaseaddr))
        mc.done()
        self.nextfreepos = pos

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

@specialize.memo()
def getMissingBackendOperation(opname):
    class MissingBackendOperation(Exception):
        pass
    MissingBackendOperation.__name__ += '_' + opname
    return MissingBackendOperation


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

# ____________________________________________________________

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    from pypy.rpython.lltypesystem.lloperation import llop
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    if we_are_translated():
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        return lltype.cast_ptr_to_int(gc_malloc_ptr)
    else:
        # <pedronis> don't do this at home
        import threading
        if not isinstance(threading.currentThread(), threading._MainThread):
            import py
            py.test.skip("must run in the main thread")
        try:
            from ctypes import cast, c_void_p
            from pypy.rpython.rctypes.tool import util
            path = util.find_library('gc')
            if path is None:
                raise ImportError("Boehm (libgc) not found")
            boehmlib = util.load_library(path)
        except ImportError, e:
            import py
            py.test.skip(str(e))
        else:
            GC_malloc = boehmlib.GC_malloc
            return cast(GC_malloc, c_void_p).value

# ____________________________________________________________

class StackOpCache:
    INITIAL_STACK_EBP_OFS = -4
stack_op_cache = StackOpCache()
stack_op_cache.lst = []

def stack_op(n):
    "Return the mem operand that designates the nth stack-spilled location"
    assert n >= 0
    lst = stack_op_cache.lst
    while len(lst) <= n:
        ofs = WORD * (StackOpCache.INITIAL_STACK_EBP_OFS - len(lst))
        lst.append(mem(ebp, ofs))
    return lst[n]

def stack_n_from_op(op):
    ofs = op.ofs_relative_to_ebp()
    return StackOpCache.INITIAL_STACK_EBP_OFS - ofs / WORD


class RegAllocator(object):
    AVAILABLE_REGS = [eax, edx, ebx, esi, edi]   # XXX ecx reserved for stuff

    # 'gv' -- GenVars, used as arguments and results of operations
    #
    # 'loc' -- location, a small integer that represents an abstract
    #          register number
    #
    # 'operand' -- a concrete machine code operand, which can be a
    #              register (ri386.eax, etc.) or a stack memory operand

    def __init__(self):
        self.nextloc = 0
        self.var2loc = {}
        self.available_locs = []
        self.force_loc2operand = {}
        self.force_operand2loc = {}
        self.initial_moves = []

    def set_final(self, final_vars_gv):
        for v in final_vars_gv:
            if not v.is_const and v not in self.var2loc:
                self.var2loc[v] = self.nextloc
                self.nextloc += 1

    def creating(self, v):
        try:
            loc = self.var2loc[v]
        except KeyError:
            pass
        else:
            self.available_locs.append(loc)   # now available again for reuse

    def using(self, v):
        if not v.is_const and v not in self.var2loc:
            try:
                loc = self.available_locs.pop()
            except IndexError:
                loc = self.nextloc
                self.nextloc += 1
            self.var2loc[v] = loc

    def creating_cc(self, v):
        if self.need_var_in_cc is v:
            # common case: v is a compare operation whose result is precisely
            # what we need to be in the CC
            self.need_var_in_cc = None
        self.creating(v)

    def save_cc(self):
        # we need a value to be in the CC, but we see a clobbering
        # operation, so we copy the original CC-creating operation down
        # past the clobbering operation
        v = self.need_var_in_cc
        if not we_are_translated():
            assert v in self.operations[:self.operationindex]
        self.operations.insert(self.operationindex, v)
        self.need_var_in_cc = None

    def using_cc(self, v):
        assert isinstance(v, Operation)
        assert 0 <= v.cc_result < INSN_JMP
        if self.need_var_in_cc is not None:
            self.save_cc()
        self.need_var_in_cc = v

    def allocate_locations(self, operations):
        # assign locations to gvars
        self.operations = operations
        self.need_var_in_cc = None
        self.operationindex = len(operations)
        for i in range(len(operations)-1, -1, -1):
            v = operations[i]
            kind = v.result_kind
            if kind == RK_WORD:
                self.creating(v)
            elif kind == RK_CC:
                self.creating_cc(v)
            if self.need_var_in_cc is not None and v.clobbers_cc:
                self.save_cc()
            v.allocate(self)
            self.operationindex = i
        if self.need_var_in_cc is not None:
            self.save_cc()

    def force_var_operands(self, force_vars, force_operands, at_start):
        force_loc2operand = self.force_loc2operand
        force_operand2loc = self.force_operand2loc
        for i in range(len(force_vars)):
            v = force_vars[i]
            operand = force_operands[i]
            try:
                loc = self.var2loc[v]
            except KeyError:
                if at_start:
                    pass    # input variable not used anyway
                else:
                    self.add_final_move(v, operand, make_copy=v.is_const)
            else:
                if loc in force_loc2operand or operand in force_operand2loc:
                    if at_start:
                        self.initial_moves.append((loc, operand))
                    else:
                        self.add_final_move(v, operand, make_copy=True)
                else:
                    force_loc2operand[loc] = operand
                    force_operand2loc[operand] = loc

    def add_final_move(self, v, targetoperand, make_copy):
        if make_copy:
            v = OpSameAs(v)
            self.operations.append(v)
        loc = self.nextloc
        self.nextloc += 1
        self.var2loc[v] = loc
        self.force_loc2operand[loc] = targetoperand

    def allocate_registers(self):
        # assign registers to locations that don't have one already
        force_loc2operand = self.force_loc2operand
        operands = []
        seen_regs = 0
        seen_stackn = {}
        for op in force_loc2operand.values():
            if isinstance(op, REG):
                seen_regs |= 1 << op.op
            elif isinstance(op, MODRM):
                seen_stackn[stack_n_from_op(op)] = None
        i = 0
        stackn = 0
        for loc in range(self.nextloc):
            try:
                operand = force_loc2operand[loc]
            except KeyError:
                # grab the next free register
                try:
                    while True:
                        operand = RegAllocator.AVAILABLE_REGS[i]
                        i += 1
                        if not (seen_regs & (1 << operand.op)):
                            break
                except IndexError:
                    while stackn in seen_stackn:
                        stackn += 1
                    operand = stack_op(stackn)
                    stackn += 1
            operands.append(operand)
        self.operands = operands
        self.required_frame_depth = stackn

    def get_operand(self, gv_source):
        if gv_source.is_const:
            return imm(gv_source.revealconst(lltype.Signed))
        else:
            loc = self.var2loc[gv_source]
            return self.operands[loc]

    def load_location_with(self, loc, gv_source):
        dstop = self.operands[loc]
        srcop = self.get_operand(gv_source)
        if srcop != dstop:
            self.mc.MOV(dstop, srcop)
        return dstop

    def generate_initial_moves(self):
        initial_moves = self.initial_moves
        # first make sure that the reserved stack frame is big enough
        last_n = self.required_frame_depth - 1
        for loc, srcoperand in initial_moves:
            if isinstance(srcoperand, MODRM):
                n = stack_n_from_op(srcoperand)
                if last_n < n:
                    last_n = n
        if last_n >= 0:
            if CALL_ALIGN > 1:
                last_n = (last_n & ~(CALL_ALIGN-1)) + (CALL_ALIGN-1)
            self.required_frame_depth = last_n + 1
            self.mc.LEA(esp, stack_op(last_n))
        # XXX naive algo for now
        for loc, srcoperand in initial_moves:
            if self.operands[loc] != srcoperand:
                self.mc.PUSH(srcoperand)
        initial_moves.reverse()
        for loc, srcoperand in initial_moves:
            if self.operands[loc] != srcoperand:
                self.mc.POP(self.operands[loc])

    def generate_operations(self):
        for v in self.operations:
            v.generate(self)
            cc = v.cc_result
            if cc >= 0 and v in self.var2loc:
                # force a comparison instruction's result into a
                # regular location
                dstop = self.get_operand(v)
                mc = self.mc
                insn = EMIT_SETCOND[cc]
                insn(mc, cl)
                try:
                    mc.MOVZX(dstop, cl)
                except FailedToImplement:
                    mc.MOVZX(ecx, cl)
                    mc.MOV(dstop, ecx)


class Builder(GenBuilder):
    coming_from = 0
    operations = None
    update_defaultcaseaddr_of = None

    def __init__(self, rgenop, inputargs_gv, inputoperands):
        self.rgenop = rgenop
        self.inputargs_gv = inputargs_gv
        self.inputoperands = inputoperands

    def start_writing(self):
        assert self.operations is None
        self.operations = []

    def generate_block_code(self, final_vars_gv, force_vars=[],
                                                 force_operands=[],
                                                 renaming=True,
                                                 minimal_stack_depth=0):
        allocator = RegAllocator()
        allocator.set_final(final_vars_gv)
        if not renaming:
            final_vars_gv = allocator.var2loc.keys()  # unique final vars
        allocator.allocate_locations(self.operations)
        allocator.force_var_operands(force_vars, force_operands,
                                     at_start=False)
        allocator.force_var_operands(self.inputargs_gv, self.inputoperands,
                                     at_start=True)
        allocator.allocate_registers()
        if allocator.required_frame_depth < minimal_stack_depth:
            allocator.required_frame_depth = minimal_stack_depth
        mc = self.start_mc()
        allocator.mc = mc
        allocator.generate_initial_moves()
        allocator.generate_operations()
        self.operations = None
        if renaming:
            self.inputargs_gv = [GenVar() for v in final_vars_gv]
        else:
            # just keep one copy of each Variable that is alive
            self.inputargs_gv = final_vars_gv
        self.inputoperands = [allocator.get_operand(v) for v in final_vars_gv]
        return mc

    def enter_next_block(self, kinds, args_gv):
##        mc = self.generate_block_code(args_gv)
##        assert len(self.inputargs_gv) == len(args_gv)
##        args_gv[:len(args_gv)] = self.inputargs_gv
##        self.set_coming_from(mc)
##        self.rgenop.close_mc(mc)
##        self.start_writing()
        for i in range(len(args_gv)):
            op = OpSameAs(args_gv[i])
            args_gv[i] = op
            self.operations.append(op)
        lbl = Label()
        lblop = OpLabel(lbl, args_gv)
        self.operations.append(lblop)
        return lbl

    def set_coming_from(self, mc, insncond=INSN_JMP):
        self.coming_from_cond = insncond
        self.coming_from = mc.tell()
        insnemit = EMIT_JCOND[insncond]
        insnemit(mc, rel32(0))

    def start_mc(self):
        mc = self.rgenop.open_mc()
        # update the coming_from instruction
        start = self.coming_from
        if start:
            targetaddr = mc.tell()
            if self.update_defaultcaseaddr_of:   # hack for FlexSwitch
                self.update_defaultcaseaddr_of.defaultcaseaddr = targetaddr
            end = start + 6    # XXX hard-coded, enough for JMP and Jcond
            oldmc = self.rgenop.InMemoryCodeBuilder(start, end)
            insn = EMIT_JCOND[self.coming_from_cond]
            insn(oldmc, rel32(targetaddr))
            oldmc.done()
            self.coming_from = 0
        return mc

    def _jump_if(self, gv_condition, args_for_jump_gv, negate):
        newbuilder = Builder(self.rgenop, list(args_for_jump_gv), None)
        # if the condition does not come from an obvious comparison operation,
        # e.g. a getfield of a Bool or an input argument to the current block,
        # then insert an OpIntIsTrue
        if gv_condition.cc_result < 0 or gv_condition not in self.operations:
            gv_condition = OpIntIsTrue(gv_condition)
            self.operations.append(gv_condition)
        self.operations.append(JumpIf(gv_condition, newbuilder, negate=negate))
        return newbuilder

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, args_for_jump_gv, True)

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        return self._jump_if(gv_condition, args_for_jump_gv, False)

    def finish_and_goto(self, outputargs_gv, targetlbl):
        operands = targetlbl.inputoperands
        if operands is None:
            # this occurs when jumping back to the same currently-open block;
            # close the block and re-open it
            self.pause_writing(outputargs_gv)
            self.start_writing()
            operands = targetlbl.inputoperands
            assert operands is not None
        mc = self.generate_block_code(outputargs_gv, outputargs_gv, operands,
                              minimal_stack_depth = targetlbl.targetstackdepth)
        mc.JMP(rel32(targetlbl.targetaddr))
        mc.done()
        self.rgenop.close_mc(mc)

    def finish_and_return(self, sigtoken, gv_returnvar):
        mc = self.generate_block_code([gv_returnvar], [gv_returnvar], [eax])
        # --- epilogue ---
        mc.LEA(esp, mem(ebp, -12))
        mc.POP(edi)
        mc.POP(esi)
        mc.POP(ebx)
        mc.POP(ebp)
        mc.RET()
        # ----------------
        mc.done()
        self.rgenop.close_mc(mc)

    def pause_writing(self, alive_gv):
        mc = self.generate_block_code(alive_gv, renaming=False)
        self.set_coming_from(mc)
        mc.done()
        self.rgenop.close_mc(mc)
        return self

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        try:
            cls = OPCLASSES1[opname]
        except KeyError:
            raise getMissingBackendOperation(opname)()
        if cls is None:     # identity
            return gv_arg
        op = cls(gv_arg)
        self.operations.append(op)
        return op

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        try:
            cls = OPCLASSES2[opname]
        except KeyError:
            raise getMissingBackendOperation(opname)()
        op = cls(gv_arg1, gv_arg2)
        self.operations.append(op)
        return op

    def genop_same_as(self, kind, gv_x):
        if gv_x.is_const:    # must always return a var
            op = OpSameAs(gv_x)
            self.operations.append(op)
            return op
        else:
            return gv_x

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        op = OpCall(sigtoken, gv_fnptr, list(args_gv))
        self.operations.append(op)
        return op

    def genop_malloc_fixedsize(self, size):
        # XXX boehm only, no atomic/non atomic distinction for now
        op = OpCall(MALLOC_SIGTOKEN,
                    IntConst(gc_malloc_fnaddr()),
                    [IntConst(size)])
        self.operations.append(op)
        return op

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        # XXX boehm only, no atomic/non atomic distinction for now
        # XXX no overflow checking for now
        opsz = OpComputeSize(varsizealloctoken, gv_size)
        self.operations.append(opsz)
        opmalloc = OpCall(MALLOC_SIGTOKEN,
                          IntConst(gc_malloc_fnaddr()),
                          [opsz])
        self.operations.append(opmalloc)
        lengthtoken, _, _ = varsizealloctoken
        self.operations.append(OpSetField(lengthtoken, opmalloc, gv_size))
        return opmalloc

    def genop_getfield(self, fieldtoken, gv_ptr):
        op = OpGetField(fieldtoken, gv_ptr)
        self.operations.append(op)
        return op

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        self.operations.append(OpSetField(fieldtoken, gv_ptr, gv_value))

    def genop_getsubstruct(self, (offset, fieldsize), gv_ptr):
        op = OpIntAdd(gv_ptr, IntConst(offset))
        self.operations.append(op)
        return op

    def genop_getarrayitem(self, arraytoken, gv_array, gv_index):
        op = OpGetArrayItem(arraytoken, gv_array, gv_index)
        self.operations.append(op)
        return op

    def genop_setarrayitem(self, arraytoken, gv_array, gv_index, gv_value):
        self.operations.append(OpSetArrayItem(arraytoken, gv_array,
                                              gv_index, gv_value))

    def genop_getarraysubstruct(self, arraytoken, gv_array, gv_index):
        op = OpGetArraySubstruct(arraytoken, gv_array, gv_index)
        self.operations.append(op)
        return op

    def genop_getarraysize(self, arraytoken, gv_array):
        lengthtoken, _, _ = arraytoken
        op = OpGetField(lengthtoken, gv_array)
        self.operations.append(op)
        return op

    def flexswitch(self, gv_exitswitch, args_gv):
        reg = FlexSwitch.REG
        mc = self.generate_block_code(args_gv, [gv_exitswitch], [reg],
                                      renaming=False)
        result = FlexSwitch(self.rgenop, self.inputargs_gv, self.inputoperands)
        default_builder = result.initialize(mc)
        mc.done()
        self.rgenop.close_mc(mc)
        return result, default_builder

    def show_incremental_progress(self):
        pass

    def log(self, msg):
        pass  # self.mc.log(msg)
        # XXX re-do this somehow...

#

dummy_var = GenVar()

class ReplayFlexSwitch(CodeGenSwitch):

    def __init__(self, replay_builder):
        self.replay_builder = replay_builder

    def add_case(self, gv_case):
        return self.replay_builder

class ReplayBuilder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        return dummy_var

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        return dummy_var

    def genop_getfield(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        return dummy_var

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysize(self, arraytoken, gv_ptr):
        return dummy_var

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        return dummy_var

    def genop_malloc_fixedsize(self, size):
        return dummy_var

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        return dummy_var
        
    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        return dummy_var

    def genop_same_as(self, kind, gv_x):
        return dummy_var

    def genop_debug_pdb(self):    # may take an args_gv later
        pass

    def enter_next_block(self, kinds, args_gv):
        return None

    def jump_if_false(self, gv_condition, args_gv):
        return self

    def jump_if_true(self, gv_condition, args_gv):
        return self

    def finish_and_return(self, sigtoken, gv_returnvar):
        pass

    def finish_and_goto(self, outputargs_gv, target):
        pass

    def flexswitch(self, gv_exitswitch, args_gv):
        flexswitch = ReplayFlexSwitch(self)
        return flexswitch, self

    def show_incremental_progress(self):
        pass


class RI386GenOp(AbstractRGenOp):
    from pypy.jit.codegen.i386.codebuf import MachineCodeBlock
    from pypy.jit.codegen.i386.codebuf import InMemoryCodeBuilder

    MC_SIZE = 65536
    
    def __init__(self):
        self.mcs = []   # machine code blocks where no-one is currently writing
        self.keepalive_gc_refs = [] 
        self.total_code_blocks = 0

    def open_mc(self):
        if self.mcs:
            # XXX think about inserting NOPS for alignment
            return self.mcs.pop()
        else:
            # XXX supposed infinite for now
            self.total_code_blocks += 1
            return self.MachineCodeBlock(self.MC_SIZE)

    def close_mc(self, mc):
        # an open 'mc' is ready for receiving code... but it's also ready
        # for being garbage collected, so be sure to close it if you
        # want the generated code to stay around :-)
        self.mcs.append(mc)

    def check_no_open_mc(self):
        assert len(self.mcs) == self.total_code_blocks

    def newgraph(self, sigtoken, name):
        # --- prologue ---
        mc = self.open_mc()
        entrypoint = mc.tell()
        if DEBUG_TRAP:
            mc.BREAKPOINT()
        mc.PUSH(ebp)
        mc.MOV(ebp, esp)
        mc.PUSH(ebx)
        mc.PUSH(esi)
        mc.PUSH(edi)
        # ^^^ pushed 5 words including the retval ( == PROLOGUE_FIXED_WORDS)
        # ----------------
        numargs = sigtoken     # for now
        inputargs_gv = []
        inputoperands = []
        for i in range(numargs):
            inputargs_gv.append(GenVar())
            inputoperands.append(mem(ebp, WORD * (2+i)))
        builder = Builder(self, inputargs_gv, inputoperands)
        # XXX this makes the code layout in memory a bit obscure: we have the
        # prologue of the new graph somewhere in the middle of its first
        # caller, all alone...
        builder.set_coming_from(mc)
        mc.done()
        self.close_mc(mc)
        #ops = [OpSameAs(v) for v in inputargs_gv]
        #builder.operations.extend(ops)
        #inputargs_gv = ops
        return builder, IntConst(entrypoint), inputargs_gv[:]

    def replay(self, label, kinds):
        return ReplayBuilder(self), [dummy_var] * len(kinds)

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"
    
    # attached later constPrebuiltGlobal = global_rgenop.genconst

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        FIELD = getattr(T, name)
        if isinstance(FIELD, lltype.ContainerType):
            fieldsize = 0      # not useful for getsubstruct
        else:
            fieldsize = llmemory.sizeof(FIELD)
        return (llmemory.offsetof(T, name), fieldsize)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return llmemory.sizeof(T)

    @staticmethod
    @specialize.memo()
    def varsizeAllocToken(T):
        if isinstance(T, lltype.Array):
            return RI386GenOp.arrayToken(T)
        else:
            # var-sized structs
            arrayfield = T._arrayfld
            ARRAYFIELD = getattr(T, arrayfield)
            arraytoken = RI386GenOp.arrayToken(ARRAYFIELD)
            (lengthoffset, lengthsize), itemsoffset, itemsize = arraytoken
            arrayfield_offset = llmemory.offsetof(T, arrayfield)
            return ((arrayfield_offset+lengthoffset, lengthsize),
                    arrayfield_offset+itemsoffset,
                    itemsize)

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return ((llmemory.ArrayLengthOffset(A), WORD),
                llmemory.ArrayItemsOffset(A),
                llmemory.ItemOffset(A.OF))

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        if T is lltype.Float:
            py.test.skip("not implemented: floats in the i386 back-end")
        return None     # for now

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        numargs = 0
        for ARG in FUNCTYPE.ARGS:
            if ARG is not lltype.Void:
                numargs += 1
        return numargs     # for now

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"

global_rgenop = RI386GenOp()
RI386GenOp.constPrebuiltGlobal = global_rgenop.genconst

MALLOC_SIGTOKEN = RI386GenOp.sigToken(GC_MALLOC.TO)
