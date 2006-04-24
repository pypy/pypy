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
