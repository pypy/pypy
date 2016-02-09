from rpython.jit.backend.zarch import locations as loc
from rpython.rlib.objectmodel import specialize

class ConditionLocation(loc.ImmLocation):
    _immutable_ = True
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

LE = ConditionLocation(EQ.value | LT.value | OF.value)
GE = ConditionLocation(EQ.value | GT.value | OF.value)
NE = ConditionLocation(LT.value | GT.value | OF.value)
NO = ConditionLocation(0xe) # NO overflow

ANY = ConditionLocation(0xf)

FP_ROUND_DEFAULT = loc.imm(0x0)
FP_TOWARDS_ZERO = loc.imm(0x5)

cond_none = loc.imm(-1)

def negate(cond):
    val = cond.value
    isfloat = (val & 0x10) != 0
    cc = (~val) & 0xf
    if isfloat:
        # inverting is handeled differently for floats
        return ConditionLocation(cc | FLOAT.value)
    return ConditionLocation(cc)

def prepare_float_condition(cond):
    newcond = ConditionLocation(cond.value | FLOAT.value)
    return newcond

def _assert_value(v1, v2):
    assert v1.value == v2.value

_assert_value(negate(EQ), NE)
_assert_value(negate(NE), EQ)
_assert_value(negate(LT), GE)
_assert_value(negate(LE), GT)
_assert_value(negate(GT), LE)
_assert_value(negate(GE), LT)
_assert_value(negate(NO), OF)
_assert_value(negate(OF), NO)
del _assert_value
