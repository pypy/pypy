from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rlib.rarithmetic import r_uint
from rpython.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(post_include_bits=["""
static int pypy__arm_int_div(int a, int b) {
    return a/b;
}
static unsigned int pypy__arm_uint_div(unsigned int a, unsigned int b) {
    return a/b;
}
static int pypy__arm_int_mod(int a, int b) {
    return a % b;
}
"""])


def arm_int_div_emulator(a, b):
    return int(a / float(b))
arm_int_div_sign = lltype.Ptr(
        lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
arm_int_div = rffi.llexternal(
    "pypy__arm_int_div", [lltype.Signed, lltype.Signed], lltype.Signed,
                        _callable=arm_int_div_emulator,
                        compilation_info=eci,
                        _nowrapper=True, elidable_function=True)


def arm_uint_div_emulator(a, b):
    return r_uint(a) / r_uint(b)
arm_uint_div_sign = lltype.Ptr(
        lltype.FuncType([lltype.Unsigned, lltype.Unsigned], lltype.Unsigned))
arm_uint_div = rffi.llexternal(
    "pypy__arm_uint_div", [lltype.Unsigned, lltype.Unsigned], lltype.Unsigned,
                        _callable=arm_uint_div_emulator,
                        compilation_info=eci,
                        _nowrapper=True, elidable_function=True)


def arm_int_mod_emulator(a, b):
    sign = 1
    if a < 0:
        a = -1 * a
        sign = -1
    if b < 0:
        b = -1 * b
    res = a % b
    return sign * res
arm_int_mod_sign = arm_int_div_sign
arm_int_mod = rffi.llexternal(
    "pypy__arm_int_mod", [lltype.Signed, lltype.Signed], lltype.Signed,
                        _callable=arm_int_mod_emulator,
                        compilation_info=eci,
                        _nowrapper=True, elidable_function=True)
