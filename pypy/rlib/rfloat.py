"""Float constants"""

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
