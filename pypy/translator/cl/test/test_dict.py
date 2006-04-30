from pypy.translator.cl.buildcl import make_cl_func

def test_dict_length():
    def dict_length_one(key, val):
        dic = {key: val}
        return len(dic)
    cl_dict_length_one = make_cl_func(dict_length_one, [int, int])
    assert cl_dict_length_one(42, 42) == 1

def test_dict_get():
    def dict_get(number):
        dic = {42: 43}
        return dic[number]
    cl_dict_get = make_cl_func(dict_get, [int])
    assert cl_dict_get(42) == 43
