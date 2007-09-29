from pypy.translator.c.test.test_genc import compile
from pypy.rpython.rcpy import cpy_export, cpy_import, CPyTypeInterface
from pypy.rpython.rcpy import cpy_typeobject
from pypy.rpython.lltypesystem import lltype


class W_MyTest(object):
    x = 600

    def __init__(self, x):
        self.x = x

    def double(self):
        return self.x * 2


mytest = CPyTypeInterface('mytest', {}, subclassable=True)

def test_cpy_export():
    def f():
        w = W_MyTest(21)
        return cpy_export(mytest, w)

    fn = compile(f, [])
    res = fn()            # the W_MyTest is allocated with the CPython logic,
                          # so it doesn't count in expected_extra_mallocs
    assert type(res).__name__ == 'mytest'


def test_cpy_import():
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
    obj, total = fn(None, expected_extra_mallocs=1) # 1 tuple in w.stuff
    assert total == 1
    obj, total = fn(obj, expected_extra_mallocs=2)  # 2 tuples: old obj.stuff
    assert total == 3                               #         + new obj.stuff
    obj, total = fn(obj, expected_extra_mallocs=2)
    assert total == 6
    obj, total = fn(obj, expected_extra_mallocs=2)  # idem
    assert total == 10
    obj, total = fn(obj, expected_extra_mallocs=2)
    assert total == 15
    obj, total = fn(obj, expected_extra_mallocs=2)
    assert total == 21


def test_instantiate_from_cpython():
    def f(input):
        if input:
            w = cpy_import(W_MyTest, input)
        else:
            w = W_MyTest(21)
        w.x += 1
        return cpy_export(mytest, w), w.x

    fn = compile(f, [object])
    obj, x = fn(None)
    assert x == 22

    obj2 = type(obj)()
    del obj
    obj, x = fn(obj2)
    assert obj is obj2
    assert x == 601     # 600 is the class default of W_MyTest.x


def test_subclass_from_cpython():
    def f(input):
        current = total = 10
        if input:
            w = cpy_import(W_MyTest, input)
            current = w.current    # or 0 if left uninitialized, as by U()
            total = w.total        # or 0 if left uninitialized, as by U()
        w = W_MyTest(21)
        current += 1
        total += current
        w.current = current
        w.total = total
        return cpy_export(mytest, w), total

    fn = compile(f, [object])
    obj, total = fn(None)
    assert total == 21
    T = type(obj)
    class U(T):
        pass
    obj2 = U()
    obj2.bla = 123
    assert obj2.bla == 123
    del obj

    objlist = [U() for i in range(100)]
    obj, total = fn(obj2)
    assert total == 1

    del objlist
    obj, total = fn(obj)
    assert total == 3


def test_export_constant():
    mytest2 = CPyTypeInterface('mytest2', {'hi': lltype.pyobjectptr(123)})
    def f():
        w = W_MyTest(21)
        return cpy_export(mytest2, w)

    fn = compile(f, [])
    obj = fn()
    assert obj.hi == 123
    assert type(obj).hi == 123


def test_export_two_constants():
    mytest2 = CPyTypeInterface('mytest2', {'hi': lltype.pyobjectptr(123),
                                           'there': lltype.pyobjectptr("foo")})
    def f():
        w = W_MyTest(21)
        return cpy_export(mytest2, w)

    fn = compile(f, [])
    obj = fn()
    assert obj.hi == 123
    assert type(obj).hi == 123
    assert obj.there == "foo"
    assert type(obj).there == "foo"


def test_cpy_typeobject():
    def f():
        return cpy_typeobject(mytest, W_MyTest)

    fn = compile(f, [])
    typeobj = fn()
    assert isinstance(typeobj, type)
    assert typeobj.__name__ == 'mytest'
