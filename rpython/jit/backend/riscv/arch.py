#!/usr/bin/env python

import sys

assert sys.maxint == (2**63 - 1)

# General purpose register width (in bytes)
XLEN = 8

# Floating point register width (in bytes)
FLEN = 8  # Assume "Standard Extension for Double 'D'" is available.

NUM_REGS = 32
NUM_FP_REGS = 32
JITFRAME_FIXED_SIZE = NUM_REGS + NUM_FP_REGS

# PC-relative offset range
PC_REL_MIN = -2**31 - 2**11
PC_REL_MAX = 2**31 - 2**11 - 1

# 12-bit signed immediate value range
SINT12_IMM_MIN = -2**11
SINT12_IMM_MAX = 2**11 - 1

# RISC-V ABI requires stack pointer to be aligned to 128-bit.
ABI_STACK_ALIGN = 16
