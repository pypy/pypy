#!/usr/bin/env python

from rpython.jit.backend.riscv.arch import FLEN, XLEN
from rpython.jit.metainterp.history import INT, FLOAT


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
