#!/usr/bin/env python

from rpython.jit.backend.riscv.locations import (
    FloatRegisterLocation, RegisterLocation, ZeroRegisterLocation)


x0 = ZeroRegisterLocation()

registers_except_zero = [RegisterLocation(i) for i in range(1, 32)]

(     x1,  x2,  x3,  x4,  x5,  x6,  x7 , x8,  x9,
 x10, x11, x12, x13, x14, x15, x16, x17, x18, x19,
 x20, x21, x22, x23, x24, x25, x26, x27, x28, x29,
 x30, x31) = registers_except_zero

registers = [x0] + registers_except_zero

fp_registers = [FloatRegisterLocation(i) for i in range(32)]

(f0,  f1,  f2,  f3,  f4,  f5,  f6,  f7,  f8,  f9,
 f10, f11, f12, f13, f14, f15, f16, f17, f18, f19,
 f20, f21, f22, f23, f24, f25, f26, f27, f28, f29,
 f30, f31) = fp_registers

zero = x0
ra = x1  # Return address (caller-saved)
sp = x2  # Stack pointer (callee-saved but requires special treatment)
gp = x3  # Global pointer (neither caller-saved nor callee-saved)
tp = x4  # Thread pointer (neither caller-saved nor callee-saved)
fp = x8  # Frame pointer (callee-saved)

caller_saved_registers = [x1, x5, x6, x7, x10, x11, x12, x13, x14, x15, x16,
                          x17, x28, x29, x30, x31]

callee_saved_registers_except_sp = [x8, x9, x18, x19, x20, x21, x22, x23, x24,
                                    x25, x26, x27]

callee_saved_registers = [sp] + callee_saved_registers_except_sp

caller_saved_fp_registers = [f0, f1, f2, f3, f4, f5, f6, f7, f10, f11, f12, f13,
                             f14, f15, f16, f17, f28, f29, f30, f31]
callee_saved_fp_registers = [f8, f9, f18, f19, f20, f21, f22, f23, f24, f25,
                             f26, f27]
