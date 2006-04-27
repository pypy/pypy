from pypy.translator.cli.test.runtest import check

def create_tuple(x, y):
    return x, y

def test_tuple():
    def func(x, y):
        t = create_tuple(x, y)
        return t[0] + t[1]
    check(func, [int, int], (42, 13))

def test_list_item():
    def func(x, y):
        t = ([x, y], x)
        return t[0][0]
    check(func, [int, int], (42, 13))

