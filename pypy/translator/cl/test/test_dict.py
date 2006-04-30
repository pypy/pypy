from pypy.translator.cl.buildcl import make_cl_func

def test_dict_length():
    def dict_length_one(key, val):
        dic = {key:val}
        return len(dic)
    cl_dict_length_one = make_cl_func(dict_length_one, [int,int])
    assert cl_dict_length_one(42,42) == 1

def notest_dict_key_access():
    def dict_key(number):
        dic = {42:43}
        return dic[number]
    cl_dict_key = make_cl_func(dict_key, [int])
    assert cl_dict_key(42) == 43
