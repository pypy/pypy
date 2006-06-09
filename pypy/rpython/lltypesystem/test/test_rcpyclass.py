from pypy.translator.c.test.test_genc import compile
from pypy.rpython.rcpy import cpy_export, cpy_import


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
        return cpy_export(mytest, w)

    fn = compile(f, [])
    res = fn()
    assert type(res).__name__ == 'mytest'


def test_cpy_import():
    class mytest(object):
        pass

    def f():
        w = W_MyTest(21)
        return cpy_export(mytest, w)

    def g():
        obj = f()
        w = cpy_import(W_MyTest, obj)
        return w.double()

    fn = compile(g, [])
    res = fn()
    assert res == 42
