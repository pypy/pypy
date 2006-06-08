from pypy.translator.c.test.test_genc import compile
from pypy.rpython.rcpy import cpy_export


class W_MyTest(object):

    def __init__(self, x):
        self.x = x

    def double(self):
        return self.x * 2


def test_cpy_export():
    class mytest(object):
        pass

    def f():
        w = W_MyTest(21)
        return cpy_export(w, mytest)

    fn = compile(f, [])
    res = fn()
    assert type(res).__name__.endswith('mytest')
