from rpython.translator.c.test.test_genc import compile
from pypy.module.math.interp_math import _gamma


def test_gamma_overflow():
    def wrapper(arg):
        try:
            return _gamma(arg)
        except OverflowError:
            return -42
    
    f = compile(wrapper, [float])
    assert f(10.0) == 362880.0
    assert f(1720.0) == -42
    assert f(172.0) == -42
