
from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.rstack import stack_frames_depth


def test_interp_c():
    def f():
        return stack_frames_depth()

    def g():
        return f()
    res_f = interpret(f, [])
    res_g = interpret(g, [])
    assert res_f == 2
    assert res_g == 3

