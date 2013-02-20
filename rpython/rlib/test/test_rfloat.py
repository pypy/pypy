import sys, py

from rpython.rlib.rfloat import float_as_rbigint_ratio
from rpython.rlib.rbigint import rbigint


def test_float_as_rbigint_ratio():
    for f, ratio in [
        (0.875, (7, 8)),
        (-0.875, (-7, 8)),
        (0.0, (0, 1)),
        (11.5, (23, 2)),
        ]:
        num, den = float_as_rbigint_ratio(f)
        assert num.eq(rbigint.fromint(ratio[0]))
        assert den.eq(rbigint.fromint(ratio[1]))

    with py.test.raises(OverflowError):
        float_as_rbigint_ratio(float('inf'))
    with py.test.raises(OverflowError):
        float_as_rbigint_ratio(float('-inf'))
    with py.test.raises(ValueError):
        float_as_rbigint_ratio(float('nan'))
