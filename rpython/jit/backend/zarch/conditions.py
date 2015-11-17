from rpython.jit.backend.zarch import locations as loc
from rpython.rlib.objectmodel import specialize

# normal branch instructions
EQ = loc.imm(0x8)
LT = loc.imm(0x4)
GT = loc.imm(0x2)
OF = loc.imm(0x1) # overflow
LE = loc.imm(EQ.value | LT.value)
GE = loc.imm(EQ.value | GT.value)
NE = loc.imm(LT.value | GT.value)
NO = loc.imm(0xe) # NO overflow
ANY = loc.imm(0xf)

cond_none = loc.imm(0x0)

@specialize.arg(1)
def negate(cond, inv_overflow=False):
    if cond is OF:
        return NO
    if cond is NO:
        return OF
    overflow = cond.value & 0x1
    value = (~cond.value) & 0xe
    return loc.imm(value | overflow)

assert negate(EQ).value == NE.value
assert negate(NE).value == EQ.value
assert negate(LT).value == GE.value
assert negate(LE).value == GT.value
assert negate(GT).value == LE.value
assert negate(GE).value == LT.value
assert negate(OF).value == NO.value
assert negate(NO).value == OF.value
