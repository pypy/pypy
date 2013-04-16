from pypy.jit.metainterp.optimizeopt import intutils

# XXX this file should really be filled with tests for all operations!

def test_mul_with_constant():
    x = intutils.IntBound(0, 100)
    y = x.mul(2)
    assert y.has_lower
    assert y.has_upper
    assert y.lower == 0
    assert y.upper == 200

    y = x.mul(-5)
    assert y.has_lower
    assert y.has_upper
    assert y.lower == -500
    assert y.upper == 0

    x = intutils.IntUpperBound(100)
    y = x.mul(2)
    assert not y.has_lower
    assert y.has_upper
    assert y.upper == 200

    y = x.mul(-5)
    assert y.has_lower
    assert not y.has_upper
    assert y.lower == -500
    assert y.upper == 0
