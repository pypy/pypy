from pypy.jit.backend.ppc.locations import (RegisterLocation,
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

NONVOLATILES_FLOAT  = [f14, f15, f16, f17, f18, f19, f20, f21, f22, f23,
                    f24, f25, f26, f27, f28, f29, f30, f31]


SCRATCH = r0
SP      = r1
TOC     = r2
RES     = r3
SPP     = r31

MANAGED_REGS = [r3, r4, r5, r6, r7, r8, r9, r10,
                r11, r12, r14, r15, r16, r17, r18, 
                r19, r20, r21, r22, r23, r24, r25, r26,
                r27, r28, r29, r30]

PARAM_REGS = [r3, r4, r5, r6, r7, r8, r9, r10]

def get_managed_reg_index(reg):
    if reg > r13.value:
        return reg - 4
    return reg - 3
