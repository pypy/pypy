from pypy.translator.cl.buildcl import make_cl_func

def test_simple():
    class C:
        pass
    def new_get_set():
        obj = C()
        obj.answer = 42
        return obj.answer
    cl_new_get_set = make_cl_func(new_get_set)
    assert cl_new_get_set() == 42

def dont_test_list_length():
    def list_length_one(number):
        lst = [number]
        return len(lst)
    cl_list_length_one = make_cl_func(list_length_one, [int])
    assert cl_list_length_one(0) == 1

def dont_test_list_get():
    def list_and_get(number):
        lst = [number]
        return lst[0]
    cl_list_and_get = make_cl_func(list_and_get, [int])
    assert cl_list_and_get(1985) == 1985
