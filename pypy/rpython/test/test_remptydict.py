import py
from pypy.rpython.test.test_llinterp import interpret 

def test_empty_dict():
    class A:
        pass
    a = A()
    a.d = {}
    def func():
        return bool(a.d)
    res = interpret(func, [])
    assert res is False
