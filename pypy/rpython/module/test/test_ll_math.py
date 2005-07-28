import math
from pypy.rpython.module.ll_math import *

def test_ll_math_atan2():
    for x in [0, 1, math.pi, 0.123]:
        for y in [0, 1, math.pi, 0.123]:
            assert math.atan2(x, y) == ll_math_atan2(x, y)

def test_ll_modf():
    result = ll_math_modf(10.1)
    assert result.item0 == math.modf(10.1)[0]
    assert result.item1 == math.modf(10.1)[1]

def test_ll_frexp():
    result = ll_math_frexp(10.1)
    assert result.item0 == math.frexp(10.1)[0]
    assert result.item1 == math.frexp(10.1)[1]

def test_ll_log():
    assert ll_math_log(8943.790148912) == math.log(8943.790148912)
    assert ll_math_log10(8943.790148912) == math.log10(8943.790148912)
