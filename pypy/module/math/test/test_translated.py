import py
from pypy.translator.c.test.test_genc import compile
from pypy.module.math.interp_math import _gamma


def test_gamma_overflow():
    f = compile(_gamma, [float])
    assert f(10.0) == 362880.0
    py.test.raises(OverflowError, f, 1720.0)
    py.test.raises(OverflowError, f, 172.0)
