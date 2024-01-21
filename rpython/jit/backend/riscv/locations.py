#!/usr/bin/env python

from rpython.jit.backend.riscv.arch import FLEN, JITFRAME_FIXED_SIZE, XLEN
from rpython.jit.metainterp.history import FLOAT, INT
from rpython.rlib.rarithmetic import r_int32


class AssemblerLocation(object):
    _immutable_ = True
    type = INT

    def is_imm(self):
        return False

    def is_stack(self):
        return False

    def is_raw_sp(self):
        return False

    def is_core_reg(self):
        return False

    def is_fp_reg(self):
        return False

    def is_imm_float(self):
        return False

    def is_float(self):
        return False

    def as_key(self):
        raise NotImplementedError

    def get_position(self):
        raise NotImplementedError


class RegisterLocation(AssemblerLocation):
    _immutable_ = True
    width = XLEN

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'x%d' % self.value

    def __int__(self):
        return self.value

    def is_core_reg(self):
        return True

    def as_key(self):
        return self.value


class ZeroRegisterLocation(AssemblerLocation):
    _immutable_ = True
    width = XLEN

    def __init__(self):
        self.value = 0

    def __repr__(self):
        return "zero"

    def __int__(self):
        return self.value

    def is_core_reg(self):
        return True

    def as_key(self):
        return self.value


class FloatRegisterLocation(RegisterLocation):
    _immutable_ = True
    type = FLOAT
    width = FLEN

    def __repr__(self):
        return 'f%d' % self.value

    def __int__(self):
        return self.value

    def is_core_reg(self):
        return False

    def is_fp_reg(self):
        return True

    def as_key(self):
        return self.value + 40

    def is_float(self):
        return True


class ImmLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, value):
        assert not isinstance(value, r_int32)
        self.value = value

    def __repr__(self):
        return "imm(%d)" % (self.value)

    def is_imm(self):
        return True


class StackLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, position, fp_offset, type=INT):
        self.position = position
        self.value = fp_offset
        self.type = type
        if type == FLOAT:
            self.width = FLEN
        else:
            self.width = XLEN

    def __repr__(self):
        return 'FP(%s)+%d' % (self.type, self.position)

    def get_position(self):
        return self.position

    def is_stack(self):
        return True

    def as_key(self):
        return self.position + 10000

    def is_float(self):
        return self.type == FLOAT


def get_fp_offset(base_ofs, position):
    return base_ofs + XLEN * (position + JITFRAME_FIXED_SIZE)


class FloatImmLocation(AssemblerLocation):
    """This class represents an imm float value (bitcasted to integer)"""
    _immutable_ = True
    type = FLOAT

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "imm_float(bits=%x)" % (self.value)

    def is_imm_float(self):
        return True

    def as_key(self):
        return self.value

    def is_float(self):
        return True
