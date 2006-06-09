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
    res = fn(expected_extra_mallocs=1)
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


def test_tp_dealloc():
    class mytest(object):
        pass

    class A(object):
        pass

    def f():
        w = W_MyTest(21)
        w.a = A()
        w.a.x = 4
        return cpy_export(mytest, w)

    def g():
        obj = f()
        w = cpy_import(W_MyTest, obj)
        return w.a.x

    fn = compile(g, [])
    res = fn()
    # the A() should have been deallocated too, otherwise the number
    # of mallocs doesn't match the number of frees
    assert res == 4


def test_subclass_from_cpython():
    class mytest(object):
        pass

    def f(input):
        current = total = 0
        if input:
            w = cpy_import(W_MyTest, input)
            current, total = w.stuff
        w = W_MyTest(21)
        current += 1
        total += current
        w.stuff = current, total
        return cpy_export(mytest, w), total

    fn = compile(f, [object])
    obj, total = fn(None, expected_extra_mallocs=2) # 1 W_MyTest (with 1 tuple)
    assert total == 1
    obj, total = fn(obj, expected_extra_mallocs=4)  # 2 W_MyTests alive
    assert total == 3
    obj, total = fn(obj, expected_extra_mallocs=4)  # 2 W_MyTests alive
    assert total == 6
    obj, total = fn(obj, expected_extra_mallocs=4)  # etc
    assert total == 10
    obj, total = fn(obj, expected_extra_mallocs=4)
    assert total == 15
    obj, total = fn(obj, expected_extra_mallocs=4)
    assert total == 21
