#!/usr/bin/env python

from rpython.jit.backend.riscv.arch import SINT12_IMM_MAX, SINT12_IMM_MIN
from rpython.jit.metainterp.resoperation import rop


_COMPARE_OPS_FOR_BRANCH_INST = {
    rop.INT_LT: None,
    rop.INT_LE: None,
    rop.INT_EQ: None,
    rop.INT_NE: None,
    rop.INT_GT: None,
    rop.INT_GE: None,

    rop.UINT_LT: None,
    rop.UINT_LE: None,
    rop.UINT_GT: None,
    rop.UINT_GE: None,

    rop.INT_IS_ZERO: None,
    rop.INT_IS_TRUE: None,

    rop.PTR_EQ: None,
    rop.PTR_NE: None,
    rop.INSTANCE_PTR_EQ: None,
    rop.INSTANCE_PTR_NE: None,
}

def can_fuse_into_compare_and_branch(opnum):
    """Returns whether a ResOperation can be fused into the following
    GuardResOp or COND_CALL op."""
    return opnum in _COMPARE_OPS_FOR_BRANCH_INST

COND_INVALID = 0
COND_BEQ = 1
COND_BNE = 2
COND_BGE = 3
COND_BLT = 4
COND_BGEU = 5
COND_BLTU = 6

_NEGATED_BRANCH_INST = [
    COND_INVALID,
    COND_BNE,
    COND_BEQ,
    COND_BLT,
    COND_BGE,
    COND_BLTU,
    COND_BGEU,
]

def get_negated_branch_inst(branch_inst):
    """Returns the branch op with the negated condition."""
    return _NEGATED_BRANCH_INST[branch_inst]

def check_imm_arg(imm):
    return imm >= SINT12_IMM_MIN and imm <= SINT12_IMM_MAX

def check_simm21_arg(imm):
    return imm >= -2**20 and imm <= 2**20 - 1 and imm & 0x1 == 0
