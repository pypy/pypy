from pypy.rpython.lltypesystem import lltype

FUNC_ALIGN=8
WORD=4

arm_int_div_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
arm_int_mod_sign = arm_int_div_sign

def arm_int_div(a, b):
    return int(a/float(b))

def arm_int_mod(a, b):
    sign = 1
    if a < 0:
        a = -1 * a
        sign = -1
    if b < 0:
        b = -1 * b
    res = a % b
    return sign * res
