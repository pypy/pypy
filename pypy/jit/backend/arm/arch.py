from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype


FUNC_ALIGN=8
WORD=4

# the number of registers that we need to save around malloc calls
N_REGISTERS_SAVED_BY_MALLOC = 9
# the offset from the FP where the list of the registers mentioned above starts
MY_COPY_OF_REGS = WORD
# The Address in the PC points two words befind the current instruction
PC_OFFSET = 8

from pypy.translator.tool.cbuild import ExternalCompilationInfo
eci = ExternalCompilationInfo(post_include_bits=["""
static int pypy__arm_int_div(int a, int b) {
    return a/b;
}
static uint pypy__arm_uint_div(uint a, uint b) {
    return a/b;
}
static int pypy__arm_int_mod(uint a, uint b) {
    return a % b;
}
"""])

arm_int_div_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
def arm_int_div_emulator(a, b):
    return int(a/float(b))
arm_int_div = rffi.llexternal(
    "pypy__arm_int_div", [lltype.Signed, lltype.Signed], lltype.Signed,
                        _callable=arm_int_div_emulator,
                        compilation_info=eci,
                        _nowrapper=True, pure_function=True)

arm_uint_div_sign = lltype.Ptr(lltype.FuncType([lltype.Unsigned, lltype.Unsigned], lltype.Unsigned))
def arm_uint_div_emulator(a, b):
    return r_uint(a)/r_uint(b)
arm_uint_div = rffi.llexternal(
    "pypy__arm_uint_div", [lltype.Unsigned, lltype.Unsigned], lltype.Unsigned,
                        _callable=arm_uint_div_emulator,
                        compilation_info=eci,
                        _nowrapper=True, pure_function=True)


arm_int_mod_sign = arm_int_div_sign
def arm_int_mod_emulator(a, b):
    sign = 1
    if a < 0:
        a = -1 * a
        sign = -1
    if b < 0:
        b = -1 * b
    res = a % b
    return sign * res
arm_int_mod = rffi.llexternal(
    "pypy__arm_int_mod", [lltype.Signed, lltype.Signed], lltype.Signed,
                        _callable=arm_int_mod_emulator,
                        compilation_info=eci,
                        _nowrapper=True, pure_function=True)

