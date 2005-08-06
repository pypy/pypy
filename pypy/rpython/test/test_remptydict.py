import py
from pypy.rpython.test.test_llinterp import interpret 

def test_empty_dict():
    class A:
        pass
    a = A()
    a.d1 = {}
    def func():
        a.d2 = {}
        return bool(a.d1) or bool(a.d2)
    res = interpret(func, [], view=True)
    assert res is False
