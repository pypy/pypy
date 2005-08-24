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
    assert ll_math_log(1L << 10000) == math.log(1L << 10000)
    assert ll_math_log10(1L << 10000) == math.log10(1L << 10000)

def test_ll_cos_sin():
    assert ll_math_cos(math.pi/3) == math.cos(math.pi/3)
    assert ll_math_sin(math.pi/3) == math.sin(math.pi/3)
    assert ll_math_acos(1./3) == math.acos(1./3)
    assert ll_math_sinh(math.pi/3) == math.sinh(math.pi/3)
    assert ll_math_cosh(math.pi/3) == math.cosh(math.pi/3)
    
def test_ll_math_sqrt():
    assert ll_math_sqrt(10) == math.sqrt(10)
    
def test_ll_math_fabs():
    assert ll_math_fabs(math.pi/3,3) == math.fabs(math.pi/3,3)
    
def test_ll_math_fabs():
    assert ll_math_fabs(math.pi/3) == math.fabs(math.pi/3)
    assert ll_math_fabs(-math.pi/3) == math.fabs(-math.pi/3)

def test_ll_math_pow():
    assert ll_math_pow(2.0, 3.0) == math.pow(2.0, 3.0)
    assert ll_math_pow(3.0, 2.0) == math.pow(3.0, 2.0)
