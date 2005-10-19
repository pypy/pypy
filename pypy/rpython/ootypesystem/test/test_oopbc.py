from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret
import py

def test_function_pointer():
    def g1():
        return 111
    def g2():
        return 222
    def f(flag):
        if flag:
            g = g1
        else:
            g = g2
        return g() - 1
    res = interpret(f, [True], type_system='ootype')
    assert res == 110
    res = interpret(f, [False], type_system='ootype')
    assert res == 221
