from pypy.translator.cl.buildcl import make_cl_func
from py.test import skip

def sum_(l):
    i = 0
    for item in l:
        i = i + item
    return i

def test_list_length():
    def list_length_one(number):
        lst = [number]
        return len(lst)
    cl_list_length_one = make_cl_func(list_length_one, [int])
    assert cl_list_length_one(0) == 1

def test_list_get():
    def list_get(number):
        lst = [number]
        return lst[0]
    cl_list_get = make_cl_func(list_get, [int])
    assert cl_list_get(1985) == 1985

def test_list_iter():
    skip("CDefinedInt implementation")
    def list_iter():
        a = 0
        for item in [1,2,3,4,5]:
            a = a + item
        return a
    cl_list_iter = make_cl_func(list_iter)
    assert cl_list_iter() == 15

def test_list_append():
    def list_append(num):
        a = [1,2,3,4]
        a.append(num)
        return len(a)
    cl_list_append = make_cl_func(list_append, [int])
    assert cl_list_append(3) == 5

def test_list_concat():
    def list_concat():
        a = [1,2,3,4]
        b = [5,6,7,8]
        return len(a+b)
    cl_list_concat = make_cl_func(list_concat)
    assert cl_list_concat() == 8

def test_list_setitem():
    skip("CDefinedInt implementation")
    def list_setitem(num):
        a = [1,2,3,4]
        a[1] = num
        return sum_(a)
    cl_list_setitem = make_cl_func(list_setitem, [int])
    assert cl_list_setitem(10) == 18

