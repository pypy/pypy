from pypy.rpython.lltype import *
from pypy.rpython.test.test_llinterp import interpret

from pypy.translator.ann_override import PyPyAnnotatorPolicy


def test_override_ignore():
    def f():
        pass
    f._annspecialcase_ = "override:ignore"
    def g(i):
        if i == 1:
            return "ab"
        else:
            return f()

    res = interpret(g, [0])
    assert not res
    res = interpret(g, [1])
    assert ''.join(res.chars) == "ab"
    
        
def test_meth_override_ignore():
    class X:
        def f(self):
            pass
        f._annspecialcase_ = "override:ignore"
    def g(i):
        x = X()
        if i == 1:
            return "ab"
        else:
            return x.f()

    res = interpret(g, [0])
    assert not res
    res = interpret(g, [1])
    assert ''.join(res.chars) == "ab"
