import py
from pypy.rpython.test.test_llinterp import make_interpreter, interpret 

def test_constant_int_dict(): 
    d = {1: 2, 2: 3, 3: 4}
    def func(i): 
        return d[i]
    res = interpret(func, [3])
    assert res == 4
