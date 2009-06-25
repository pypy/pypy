
from pypy.module.pypyjit.interp_jit import can_inline

def test_one():
    def f():
        pass
    assert can_inline(0, f.func_code)
    def f():
        while i < 0:
            pass
    assert not can_inline(0, f.func_code)
    def f(a, b):
        return a + b
    assert can_inline(0, f.func_code)
