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
jfp = x9  # Pointer to RPython JITFrame (callee-saved)

# Note: We keep the fp register according to the RISC-V calling convention with
# `-fno-omit-frame-pointer` and reserve another callee-saved register (x9) as
# the jfp register for JITFrame, so that stack unwinder or profilers can walk
# through RPython loop/bridge.

caller_saved_registers = [x1, x5, x6, x7, x10, x11, x12, x13, x14, x15, x16,
                          x17, x28, x29, x30, x31]

# Note: Even though x1 (ra) register is not a callee-saved register, we must
# restore the value before returning from the trace thus we include it here
# (p.s. even though x1 is not an allocatable register, x1 can be overriden by
# function calls.)
callee_saved_registers_except_ra_sp_fp = [x9, x18, x19, x20, x21, x22, x23,
                                          x24, x25, x26, x27]

callee_saved_registers_except_sp = ([x1, x8]
                                    + callee_saved_registers_except_ra_sp_fp)

callee_saved_registers = [sp] + callee_saved_registers_except_sp

argument_regs = [x10, x11, x12, x13, x14, x15, x16, x17]

allocatable_registers = [x5, x6, x7, x10, x11, x12, x13, x14, x15, x16, x17,
                         x18, x19, x20, x21, x22, x23, x24, x25, x28, x29, x30]

# Registers for GIL and shadow stack.  (See also. callbuilder.py)
thread_id = x26
shadow_old = x27

caller_saved_fp_registers = [f0, f1, f2, f3, f4, f5, f6, f7, f10, f11, f12, f13,
                             f14, f15, f16, f17, f28, f29, f30, f31]
callee_saved_fp_registers = [f8, f9, f18, f19, f20, f21, f22, f23, f24, f25,
                             f26, f27]
allocatable_fp_registers = [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11,
                            f12, f13, f14, f15, f16, f17, f18, f19, f20, f21,
                            f22, f23, f24, f25, f26, f27, f28, f29, f30]

if __name__ == '__main__':
    assert set(registers) == \
            set(caller_saved_registers + callee_saved_registers + [x0, x3, x4])
    assert set(fp_registers) == \
            set(caller_saved_fp_registers + callee_saved_fp_registers)
    assert set(fp_registers) == set(allocatable_fp_registers + [f31])

    # Check whether there are duplicated registers in the lists.
    assert len(set(allocatable_registers)) == len(allocatable_registers)
    assert len(set(allocatable_fp_registers)) == len(allocatable_fp_registers)

    # fp (frame pointer) register must not be in the allocatable_registers.
    assert fp not in allocatable_registers

    # jfp (JITFrame pointer) must not be in the allocatable_registers.
    assert jfp not in allocatable_registers

    # jfp (JITFrame pointer) must be in callee_saved_registers so that it can
    # be preserved across function calls when we don't have shadow stack (e.g.
    # when we use boehm).
    assert jfp in callee_saved_registers

    # x31 must not be in the allocatable_registers because we want to use it as
    # a scratch register.
    #
    # For example, we keep the address in x31 temporarily when we load constant
    # floating point numbers to fp registers.
    assert x31 not in allocatable_registers

    # f31 must not be in the allocatable_fp_registers because we want to use it
    # as a scratch fp register.
    assert f31 not in allocatable_fp_registers

    # Reserve two callee-saved registers for GIL and shadow stack support.
    assert thread_id not in allocatable_registers
    assert thread_id in callee_saved_registers
    assert shadow_old not in allocatable_registers
    assert shadow_old in callee_saved_registers

    print 'Core registers'
    print '* Number of caller saved:', len(caller_saved_registers)
    print '* Number of callee saved:', len(callee_saved_registers)
    print '* Number of allocatable:', len(allocatable_registers)

    print 'Floating point registers'
    print '* Number of caller saved:', len(caller_saved_fp_registers)
    print '* Number of callee saved:', len(callee_saved_fp_registers)
    print '* Number of allocatable:', len(allocatable_fp_registers)
