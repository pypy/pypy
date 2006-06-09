from pypy.translator.c.test.test_genc import compile
from pypy.rpython.rcpy import cpy_export, cpy_import


class W_MyTest(object):
    x = 600

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


def test_manipulate_more():
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


def test_instantiate_from_cpython():
    class mytest(object):
        pass

    def f(input):
        if input:
            w = cpy_import(W_MyTest, input)
        else:
            w = W_MyTest(21)
        w.x += 1
        return cpy_export(mytest, w), w.x

    fn = compile(f, [object])
    obj, x = fn(None, expected_extra_mallocs=1) # 1 W_MyTest
    assert x == 22

    obj2 = type(obj)()
    del obj
    obj, x = fn(obj2, expected_extra_mallocs=1) # 1 W_MyTest (obj2)
    assert obj is obj2
    assert x == 601     # 600 is the class default of W_MyTest.x


def test_subclass_from_cpython():
    import py; py.test.skip("not implemented (see comments in rcpy.py)")
    class mytest(object):
        pass

    def f(input):
        current = total = 10
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
    assert total == 21
    T = type(obj)
    class U(T):
        pass
    obj2 = U()
    obj2.bla = 123
    assert obj2.bla == 123
    del obj

    objlist = [U() for i in range(100)]
    obj, total = fn(obj2, expected_extra_mallocs=204) # 102 W_MyTests alive
    assert total == 1

    del objlist
    obj, total = fn(obj, expected_extra_mallocs=6) # 3 W_MyTests alive
    assert total == 3
