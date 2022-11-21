import math
from rpython.translator.c.test.test_genc import compile
from rpython.rlib.longlong2float import longlong2float, float2longlong
from rpython.rlib.longlong2float import uint2singlefloat, singlefloat2uint
from rpython.rlib.rarithmetic import r_singlefloat, r_longlong
from rpython.rtyper.test.test_llinterp import interpret

from rpython.rtyper.lltypesystem import lltype, rffi

DOUBLE_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.DOUBLE))
LONGLONG_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.LONGLONG))
UINT_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.UINT))
FLOAT_ARRAY_PTR = lltype.Ptr(lltype.Array(rffi.FLOAT))


from hypothesis import given, strategies


def fn(f1):
    ll = float2longlong(f1)
    f2 = longlong2float(ll)
    return f2

def enum_floats():
    inf = 1e200 * 1e200
    yield 0.0
    yield -0.0
    yield 1.0
    yield -2.34567
    yield 2.134891117e22
    yield inf
    yield -inf
    yield inf / inf     # nan

def test_float2longlong():
    assert float2longlong(0.0) == r_longlong(0)

def test_longlong_as_float():
    for x in enum_floats():
        res = fn(x)
        assert repr(res) == repr(x)

@given(strategies.floats())
def test_longlong_as_float_hypothesis_roundtrip(x):
    assert repr(x) == repr(fn(x))

@given(strategies.integers(-2**63, 2**63-1))
def test_consistency_longlong2float_ll2ctypes(llval):
# these definitions are used only in tests, when not translated
    #return struct.unpack('@d', struct.pack('@q', llval))[0]
    with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 1) as d_array:
        ll_array = rffi.cast(LONGLONG_ARRAY_PTR, d_array)
        ll_array[0] = llval
        floatval = d_array[0]
    assert repr(floatval) == repr(longlong2float(llval))

@given(strategies.floats())
def test_consistency_float2longlong_ll2ctypes(floatval):
    #return struct.unpack('@q', struct.pack('@d', floatval))[0]
    with lltype.scoped_alloc(DOUBLE_ARRAY_PTR.TO, 1) as d_array:
        ll_array = rffi.cast(LONGLONG_ARRAY_PTR, d_array)
        d_array[0] = floatval
        llval = ll_array[0]
    assert llval == float2longlong(floatval)


def test_compiled():
    fn2 = compile(fn, [float])
    for x in enum_floats():
        res = fn2(x)
        assert repr(res) == repr(x)

def test_interpreted():
    def f(f1):
        try:
            ll = float2longlong(f1)
            return longlong2float(ll)
        except Exception:
            return 500

    for x in enum_floats():
        res = interpret(f, [x])
        assert repr(res) == repr(x)

# ____________________________________________________________

def fnsingle(f1):
    sf1 = r_singlefloat(f1)
    ii = singlefloat2uint(sf1)
    sf2 = uint2singlefloat(ii)
    f2 = float(sf2)
    return f2

def test_int_as_singlefloat():
    for x in enum_floats():
        res = fnsingle(x)
        assert repr(res) == repr(float(r_singlefloat(x)))

def test_compiled_single():
    fn2 = compile(fnsingle, [float])
    for x in enum_floats():
        res = fn2(x)
        assert repr(res) == repr(float(r_singlefloat(x)))

# ____________________________________________________________

def fn_encode_nan(f1, i2):
    from rpython.rlib.longlong2float import can_encode_float, can_encode_int32
    from rpython.rlib.longlong2float import encode_int32_into_longlong_nan
    from rpython.rlib.longlong2float import decode_int32_from_longlong_nan
    from rpython.rlib.longlong2float import is_int32_from_longlong_nan
    assert can_encode_float(f1)
    assert can_encode_int32(i2)
    l1 = float2longlong(f1)
    l2 = encode_int32_into_longlong_nan(i2)
    assert not is_int32_from_longlong_nan(l1)
    assert is_int32_from_longlong_nan(l2)
    f1b = longlong2float(l1)
    assert f1b == f1 or (math.isnan(f1b) and math.isnan(f1))
    assert decode_int32_from_longlong_nan(l2) == i2
    return 42

def test_compiled_encode_nan():
    fn2 = compile(fn_encode_nan, [float, int])
    ints = [int(-2**31), int(2**31-1), 42]
    for x in enum_floats():
        y = ints.pop()
        ints.insert(0, y)
        fn_encode_nan(x, y)
        res = fn2(x, y)
        assert res == 42
