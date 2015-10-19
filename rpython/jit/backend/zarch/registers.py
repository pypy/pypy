

from rpython.jit.backend.zarch.locations import FloatRegisterLocation
from rpython.jit.backend.zarch.locations import RegisterLocation

registers = [RegisterLocation(i) for i in range(16)]
fpregisters = [FloatRegisterLocation(i) for i in range(16)]

[r0,r1,r2,r3,r4,r5,r6,r7,r8,
 r9,r10,r11,r12,r13,r14,r15] = registers

sp = r15
raddr = r14

[f0,f1,f2,f3,f4,f5,f6,f7,f8,
 f9,f10,f11,f12,f13,f14,f15] = fpregisters
