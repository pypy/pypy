from pypy.interpreter import pycode
from pypy.module.pypyjit.interp_jit import can_inline

class FakeSpace(object):
    class config:
        class objspace:
            class std:
                withcelldict = True
    wrap = new_interned_str = unwrap = lambda _, x: x
    def fromcache(self, X):
        return X(self)


def test_one():
    space = FakeSpace()
    def f():
        pass
    code = pycode.PyCode._from_code(space, f.func_code)
    assert can_inline(0, code)
    def f():
        while i < 0:
            pass
    code = pycode.PyCode._from_code(space, f.func_code)
    assert not can_inline(0, code)
    def f(a, b):
        return a + b
    code = pycode.PyCode._from_code(space, f.func_code)
    assert can_inline(0, code)
