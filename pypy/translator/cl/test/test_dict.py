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

def test_dict_iter():
    py.test.skip("not supported yet")
    def dict_iter():
        dic = {1:2, 3:4, 5:6}
        i = 0
        for key in dic:
            i = i + dic[key]
        return i
    cl_dict_iter = make_cl_func(dict_iter, [])
    assert cl_dict_iter() == 12