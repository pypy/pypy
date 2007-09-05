import math
from pypy.rpython.lltypesystem import lltype, rffi

math_frexp = rffi.llexternal('frexp', [rffi.DOUBLE, rffi.INTP], rffi.DOUBLE,
                             sandboxsafe=True)
math_modf  = rffi.llexternal('modf',  [rffi.DOUBLE, rffi.DOUBLEP], rffi.DOUBLE,
                             sandboxsafe=True)

def ll_math_frexp(x):
    exp_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
    mantissa = math_frexp(x, exp_p)
    exponent = rffi.cast(lltype.Signed, exp_p[0])
    lltype.free(exp_p, flavor='raw')
    return (mantissa, exponent)

def ll_math_modf(x):
    intpart_p = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
    fracpart = math_modf(x, intpart_p)
    intpart = intpart_p[0]
    lltype.free(intpart_p, flavor='raw')
    return (fracpart, intpart)
