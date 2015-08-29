from rpython.jit.backend.ppc.locations import (RegisterLocation,
                                               FPRegisterLocation)

ALL_REGS        = [RegisterLocation(i) for i in range(32)]
ALL_FLOAT_REGS  = [FPRegisterLocation(i) for i in range(32)]

r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15, r16,\
    r17, r18, r19, r20, r21, r22, r23, r24, r25, r26, r27, r28, r29, r30, r31\
    = ALL_REGS

f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16,\
    f17, f18, f19, f20, f21, f22, f23, f24, f25, f26, f27, f28, f29, f30, f31\
    = ALL_FLOAT_REGS

NONVOLATILES        = [r14, r15, r16, r17, r18, r19, r20, r21, r22, r23,
                    r24, r25, r26, r27, r28, r29, r30, r31]
VOLATILES           = [r0, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12]
# volatile r2 is persisted around calls and r13 can be ignored

# we don't use any non-volatile float register, to keep the frame header
# code short-ish
#NONVOLATILES_FLOAT  = [f14, f15, f16, f17, f18, f19, f20, f21, f22, f23,
#                    f24, f25, f26, f27, f28, f29, f30, f31]
VOLATILES_FLOAT  = [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13]

SCRATCH    = r0
SCRATCH2   = r2
FP_SCRATCH = f0
SP         = r1
TOC        = r2
RES        = r3
SPP        = r31

MANAGED_REGS = [r3, r4, r5, r6, r7, r8, r9, r10, r11, r12,
                r25, r26, r27, r28, r29, r30]
                # registers r14 to r24 are not touched, we have enough
                # registers already

MANAGED_FP_REGS = VOLATILES_FLOAT[1:] #+ NONVOLATILES_FLOAT


# The JITFRAME_FIXED_SIZE is measured in words, and should be the
# number of registers that need to be saved into the jitframe when
# failing a guard, for example.
ALL_REG_INDEXES = {}
for _r in MANAGED_REGS:
    ALL_REG_INDEXES[_r] = len(ALL_REG_INDEXES)
for _r in MANAGED_FP_REGS:
    ALL_REG_INDEXES[_r] = len(ALL_REG_INDEXES) + 1
    #       we leave a never-used hole for f0  ^^^  in the jitframe
    #       to simplify store_info_on_descr(), which assumes that the
    #       register number N is at offset N after the non-fp regs
JITFRAME_FIXED_SIZE = len(ALL_REG_INDEXES) + 1


PARAM_REGS = [r3, r4, r5, r6, r7, r8, r9, r10]
PARAM_FPREGS = [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13]
