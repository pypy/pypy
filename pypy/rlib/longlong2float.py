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
eci = ExternalCompilationInfo(includes=['string.h', 'assert.h'],
                              post_include_bits=["""
static double pypy__longlong2float(long long x) {
    double dd;
    assert(sizeof(double) == 8 && sizeof(long long) == 8);
    memcpy(&dd, &x, 8);
    return dd;
}
static long long pypy__float2longlong(double x) {
    long long ll;
    assert(sizeof(double) == 8 && sizeof(long long) == 8);
    memcpy(&ll, &x, 8);
    return ll;
}
"""])

longlong2float = rffi.llexternal(
    "pypy__longlong2float", [rffi.LONGLONG], rffi.DOUBLE,
    _callable=longlong2float_emulator, compilation_info=eci,
    _nowrapper=True, elidable_function=True)

float2longlong = rffi.llexternal(
    "pypy__float2longlong", [rffi.DOUBLE], rffi.LONGLONG,
    _callable=float2longlong_emulator, compilation_info=eci,
    _nowrapper=True, elidable_function=True)
