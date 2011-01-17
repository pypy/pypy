from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(includes=['float.h'])

    DBL_MIN = rffi_platform.DefinedConstantDouble('DBL_MIN')
    DBL_MANT_DIG = rffi_platform.ConstantInteger('DBL_MANT_DIG')


for k, v in rffi_platform.configure(CConfig).items():
    assert v is not None, "no value found for %r" % k
    globals()[k] = v


assert DBL_MIN > 0.0
assert DBL_MIN * (2**-53) == 0.0


# CM_SCALE_UP is an odd integer chosen such that multiplication by
# 2**CM_SCALE_UP is sufficient to turn a subnormal into a normal.
# CM_SCALE_DOWN is (-(CM_SCALE_UP+1)/2).  These scalings are used to compute
# square roots accurately when the real and imaginary parts of the argument
# are subnormal.
CM_SCALE_UP = (2*(DBL_MANT_DIG/2) + 1)
CM_SCALE_DOWN = -(CM_SCALE_UP+1)/2
