from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype

FUNC_ALIGN=8
WORD=4
# The Address in the PC points two words befind the current instruction
PC_OFFSET = 8

arm_int_div_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
def arm_int_div(a, b):
    print 'DIV'
    return int(a/float(b))

arm_uint_div_sign = lltype.Ptr(lltype.FuncType([lltype.Unsigned, lltype.Unsigned], lltype.Unsigned))
def arm_uint_div(a, b):
    return r_uint(a)/r_uint(b)

arm_int_mod_sign = arm_int_div_sign
def arm_int_mod(a, b):
    sign = 1
    if a < 0:
        a = -1 * a
        sign = -1
    if b < 0:
        b = -1 * b
    res = a % b
    return sign * res

