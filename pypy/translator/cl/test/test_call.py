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

def test_indirect_call():
    def add_one(n):
        return n + 1
    def add_two(n):
        return n + 2
    def pick_function(flag):
        if flag:
            return add_one
        else:
            return add_two
    def add_one_or_two(n, flag):
        function = pick_function(flag)
        return function(n)
    cl_add_one_or_two = make_cl_func(add_one_or_two, [int, bool])
    assert cl_add_one_or_two(8, True) == 9
    assert cl_add_one_or_two(7, False) == 9
