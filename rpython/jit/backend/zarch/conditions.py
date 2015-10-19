
from rpython.jit.backend.zarch import locations as loc

EQ = loc.imm(0x8)
LT = loc.imm(0x4)
GT = loc.imm(0x2)
LE = loc.imm(EQ.value | LT.value)
GE = loc.imm(EQ.value | GT.value)
OVERFLOW = loc.imm(0x1)
