from pypy.translator.c.test.test_genc import compile
from pypy.rlib.longlong2float import longlong2float, float2longlong


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

def test_longlong_as_float():
    for x in enum_floats():
        res = fn(x)
        assert repr(res) == repr(x)

def test_compiled():
    fn2 = compile(fn, [float])
    for x in enum_floats():
        res = fn2(x)
        assert repr(res) == repr(x)
