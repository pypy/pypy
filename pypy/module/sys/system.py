"""Information about the current system."""

from pypy.interpreter import gateway

from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(includes=["float.h"])

float_constants = ["DBL_MAX", "DBL_MIN", "DBL_EPSILON"]
int_constants = ["DBL_MAX_EXP", "DBL_MAX_10_EXP",
                 "DBL_MIN_EXP", "DBL_MIN_10_EXP",
                 "DBL_DIG", "DBL_MANT_DIG",
                 "FLT_RADIX", "FLT_ROUNDS"]
for const in float_constants:
    setattr(CConfig, const, rffi_platform.DefinedConstantDouble(const))
for const in int_constants:
    setattr(CConfig, const, rffi_platform.DefinedConstantInteger(const))
del float_constants, int_constants, const

globals().update(rffi_platform.configure(CConfig))


app = gateway.applevel("""
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield
class float_info:
    __metaclass__ = structseqtype

    max = structseqfield(0)
    max_exp = structseqfield(1)
    max_10_exp = structseqfield(2)
    min = structseqfield(3)
    min_exp = structseqfield(4)
    min_10_exp = structseqfield(5)
    dig = structseqfield(6)
    mant_dig = structseqfield(7)
    epsilon = structseqfield(8)
    radix = structseqfield(9)
    rounds = structseqfield(10)
""")


def get_float_info(space):
    info_w = [
        space.wrap(DBL_MAX),
        space.wrap(DBL_MAX_EXP),
        space.wrap(DBL_MAX_10_EXP),
        space.wrap(DBL_MIN),
        space.wrap(DBL_MIN_EXP),
        space.wrap(DBL_MIN_10_EXP),
        space.wrap(DBL_DIG),
        space.wrap(DBL_MANT_DIG),
        space.wrap(DBL_EPSILON),
        space.wrap(FLT_RADIX),
        space.wrap(FLT_ROUNDS),
    ]
    w_float_info = app.wget(space, "float_info")
    return space.call_function(w_float_info, space.newtuple(info_w))
