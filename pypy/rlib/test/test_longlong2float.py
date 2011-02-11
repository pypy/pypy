from pypy.translator.c.test.test_genc import compile
from pypy.rlib.longlong2float import longlong2float, float2longlong
from pypy.rlib.rarithmetic import r_longlong


maxint64 = r_longlong(9223372036854775807)

def fn(x):
    d = longlong2float(x)
    ll = float2longlong(d)
    return ll

def test_longlong_as_float():
    assert fn(maxint64) == maxint64

def test_roundtrip():
    value = 0x7ff06af3307a3fef
    assert fn(value) == value

def test_compiled():
    fn2 = compile(fn, [r_longlong])
    res = fn2(maxint64)
    assert res == maxint64
    #
    special_value = 0x7ff06af3307a3fef
    res = fn2(special_value)
    assert res == special_value
