"""
This module exposes the functions longlong2float() and float2longlong(),
which cast the bit pattern of a float into a long long and back.
Warning: don't use in the other direction, i.e. don't cast a random
long long to a float and back to a long long.  There are corner cases
in which it does not work.
"""
from pypy.rpython.lltypesystem import lltype, rffi


# -------- implement longlong2float and float2longlong --------
DOUBLE_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.DOUBLE))
LONGLONG_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.LONGLONG))

# these definitions are used only in tests, when not translated
def longlong2float_emulator(llval):
    d_array = lltype.malloc(DOUBLE_ARRAY_PTR.TO, 1, flavor='raw')
    ll_array = rffi.cast(LONGLONG_ARRAY_PTR, d_array)
    ll_array[0] = llval
    floatval = d_array[0]
    lltype.free(d_array, flavor='raw')
    return floatval

def float2longlong_emulator(floatval):
    d_array = lltype.malloc(DOUBLE_ARRAY_PTR.TO, 1, flavor='raw')
    ll_array = rffi.cast(LONGLONG_ARRAY_PTR, d_array)
    d_array[0] = floatval
    llval = ll_array[0]
    lltype.free(d_array, flavor='raw')
    return llval

from pypy.translator.tool.cbuild import ExternalCompilationInfo
eci = ExternalCompilationInfo(post_include_bits=["""
static double pypy__longlong2float(long long x) {
    char *p = (char*)&x;
    return *((double*)p);
}
static long long pypy__float2longlong(double x) {
    char *p = (char*)&x;
    return *((long long*)p);
}
"""])

longlong2float = rffi.llexternal(
    "pypy__longlong2float", [rffi.LONGLONG], rffi.DOUBLE,
    _callable=longlong2float_emulator, compilation_info=eci,
    _nowrapper=True, pure_function=True)

float2longlong = rffi.llexternal(
    "pypy__float2longlong", [rffi.DOUBLE], rffi.LONGLONG,
    _callable=float2longlong_emulator, compilation_info=eci,
    _nowrapper=True, pure_function=True)
