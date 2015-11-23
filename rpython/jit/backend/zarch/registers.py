from rpython.jit.backend.zarch.locations import FloatRegisterLocation
from rpython.jit.backend.zarch.locations import RegisterLocation

registers = [RegisterLocation(i) for i in range(16)]
fpregisters = [FloatRegisterLocation(i) for i in range(16)]

[r0,r1,r2,r3,r4,r5,r6,r7,r8,
 r9,r10,r11,r12,r13,r14,r15] = registers

MANAGED_REGS = [r0,r1,r4,r5,r6,r7,r8,r9,r10,r12] # keep this list sorted (asc)!
VOLATILES = [r6,r7,r8,r9,r10,r12]
SP = r15
RETURN = r14
POOL = r13
SPP = r11
SCRATCH = r3
SCRATCH2 = r2

[f0,f1,f2,f3,f4,f5,f6,f7,f8,
 f9,f10,f11,f12,f13,f14,f15] = fpregisters

FP_SCRATCH = f0

MANAGED_FP_REGS = fpregisters[1:]
VOLATILES_FLOAT = []

# The JITFRAME_FIXED_SIZE is measured in words, and should be the
# number of registers that need to be saved into the jitframe when
# failing a guard, for example.
ALL_REG_INDEXES = {}
for _r in registers:
    ALL_REG_INDEXES[_r] = len(ALL_REG_INDEXES)
for _r in MANAGED_FP_REGS:
    ALL_REG_INDEXES[_r] = len(ALL_REG_INDEXES) + 1
    #       we leave a never-used hole for f0  ^^^  in the jitframe
    #       to simplify store_info_on_descr(), which assumes that the
    #       register number N is at offset N after the non-fp regs
JITFRAME_FIXED_SIZE = len(ALL_REG_INDEXES) + 1
