import py
from pypy.translator.cl.buildcl import make_cl_func

def test_call():
    def add_one(n):
        n = add_one_really(n)
        return n
    def add_one_really(n):
        return n + 1
    cl_add_one = make_cl_func(add_one, [int])
    assert cl_add_one(1) == 2
