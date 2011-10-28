from pypy.jit.backend.ppc.ppcgen.locations import RegisterLocation

ALL_REGS = [RegisterLocation(i) for i in range(32)]

r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15, r16,\
    r17, r18, r19, r20, r21, r22, r23, r24, r25, r26, r27, r28, r29, r30, r31\
    = ALL_REGS

NONVOLATILES    = [r1, r14, r15, r16, r17, r18, r19, r20, r21, r22, r23,
                    r24, r25, r26, r27, r28, r29, r30, r31]
VOLATILES       = [r0, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13]

SPP = r31
SP  = r1
RES = r3

MANAGED_REGS = [r2, r3, r4, r5, r6, r7, r8, r9, r10,
                r11, r12, r13, r14, r15, r16, r17, r18, 
                r19, r20, r21, r22, r23, r24, r25, r26,
                r27, r28, r29, r30]

PARAM_REGS = [r3, r4, r5, r6, r7, r8, r9, r10]
