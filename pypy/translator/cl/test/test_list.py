from pypy.translator.cl.buildcl import make_cl_func

def test_list_length():
    def list_length_one(number):
        lst = [number]
        return len(lst)
    cl_list_length_one = make_cl_func(list_length_one, [int])
    assert cl_list_length_one(0) == 1

def test_list_get():
    def list_and_get(number):
        lst = [number]
        return lst[0]
    cl_list_and_get = make_cl_func(list_and_get, [int])
    assert cl_list_and_get(1985) == 1985
