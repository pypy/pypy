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
    py.test.skip("fails with HalfConcreteWrapper")
    def id(n):
        return n
    def square(n):
        return n * n
    def map_sum(func, n):
        sum = 0
        for i in range(1, n+1):
            sum += func(i)
        return sum
    def sum(n):
        return map_sum(id, n)
    def square_sum(n):
        return map_sum(square, n)
    cl_sum = make_cl_func(sum, [int])
    assert cl_sum(5) == 15
    cl_square_sum = make_cl_func(square_sum, [int])
    assert cl_square_sum(5) == 55
