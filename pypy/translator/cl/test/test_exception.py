import py
from pypy.translator.cl.buildcl import make_cl_func

def test_handle_exception():
    py.test.skip("We support exceptions, but not really it seems")
    class MyException(Exception):
        pass
    def raise_exception():
        # This is in a separate function to fool RTyper
        raise MyException()
    def handle_exception(flag):
        try:
            if flag:
                raise_exception()
            else:
                return 2
        except MyException:
            return 1
    cl_handle_exception = make_cl_func(handle_exception, [bool])
    assert cl_handle_exception(True) == 1
    assert cl_handle_exception(False) == 2

def test_indirect_call():
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

def test_iteration():
    def get_last(num):
        last = 0
        for i in range(num):
            last = i
        return last
    cl_get_last = make_cl_func(get_last, [int])
    assert cl_get_last(5) == 4
