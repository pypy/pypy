from rpython.jit.backend.zarch import locations as loc
from rpython.rlib.objectmodel import specialize

class ConditionLocation(loc.ImmLocation):
    def __repr__(self):
        s = ""
        if self.value & 0x10 != 0:
            s += "!FLOAT! "
        if self.value & 0x1 != 0:
            s += "OF"
        if self.value & 0x2 != 0:
            s += " GT"
        if self.value & 0x4 != 0:
            s += " LT"
        if self.value & 0x8 != 0:
            s += " EQ"
        return "cond(%s)" % s

# normal branch instructions
FLOAT = ConditionLocation(0x10)
EQ = ConditionLocation(0x8)
LT = ConditionLocation(0x4)
GT = ConditionLocation(0x2)
OF = ConditionLocation(0x1) # overflow
LE = ConditionLocation(EQ.value | LT.value)
GE = ConditionLocation(EQ.value | GT.value)
NE = ConditionLocation(LT.value | GT.value | OF.value)
NO = ConditionLocation(0xe) # NO overflow
ANY = ConditionLocation(0xf)

FP_ROUND_DEFAULT = loc.imm(0x0)
FP_TOWARDS_ZERO = loc.imm(0x5)

cond_none = loc.imm(0x0)

def negate(cond):
    isfloat = (cond.value & 0x10) != 0
    if isfloat:
        # inverting is handeled differently for floats
        # overflow is never inverted
        value = (~cond.value) & 0xf
        return ConditionLocation(value | FLOAT.value)
    value = (~cond.value) & 0xf
    return ConditionLocation(value)

def prepare_float_condition(cond):
    newcond = ConditionLocation(cond.value | FLOAT.value)
    return newcond

def _assert_invert(v1, v2):
    assert (v1.value & 0xe) == (v2.value & 0xe)
_assert_invert(negate(EQ), NE)
_assert_invert(negate(NE), EQ)
_assert_invert(negate(LT), GE)
_assert_invert(negate(LE), GT)
_assert_invert(negate(GT), LE)
_assert_invert(negate(GE), LT)
assert negate(NO).value == OF.value
assert negate(OF).value == NO.value
del _assert_invert
