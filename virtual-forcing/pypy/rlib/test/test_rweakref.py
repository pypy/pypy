import py
from pypy.rlib import rgc
from pypy.rlib.rweakref import RWeakValueDictionary
from pypy.rpython.test.test_llinterp import interpret

class X(object):
    pass

class Y(X):
    pass


def make_test(loop=100):
    def g(d):
        assert d.get("hello") is None
        x1 = X(); x2 = X(); x3 = X()
        d.set("abc", x1)
        d.set("def", x2)
        d.set("ghi", x3)
        assert d.get("abc") is x1
        assert d.get("def") is x2
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        return x1, x3    # x2 dies
    def f():
        d = RWeakValueDictionary(X)
        x1, x3 = g(d)
        rgc.collect(); rgc.collect()
        assert d.get("abc") is x1
        assert d.get("def") is None
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        d.set("abc", None)
        assert d.get("abc") is None
        assert d.get("def") is None
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        # resizing should also work
        for i in range(loop):
            d.set(str(i), x1)
        for i in range(loop):
            assert d.get(str(i)) is x1
        assert d.get("abc") is None
        assert d.get("def") is None
        assert d.get("ghi") is x3
        assert d.get("hello") is None
        # a subclass
        y = Y()
        d.set("hello", y)
        assert d.get("hello") is y
        # storing a lot of Nones
        for i in range(loop, loop*2-5):
            d.set('%dfoobar' % i, x1)
        for i in range(loop):
            d.set(str(i), None)
        for i in range(loop):
            assert d.get(str(i)) is None
        assert d.get("abc") is None
        assert d.get("def") is None
        assert d.get("ghi") is x3
        assert d.get("hello") is y
        for i in range(loop, loop*2-5):
            assert d.get('%dfoobar' % i) is x1
    return f

def test_RWeakValueDictionary():
    make_test()()

def test_rpython_RWeakValueDictionary():
    interpret(make_test(loop=12), [])

def test_rpython_prebuilt():
    d = RWeakValueDictionary(X)
    living = [X() for i in range(8)]
    for i in range(8):
        d.set(str(i), living[i])
    #
    def f():
        x = X()
        for i in range(8, 13):
            d.set(str(i), x)
        for i in range(0, 8):
            assert d.get(str(i)) is living[i]
        for i in range(8, 13):
            assert d.get(str(i)) is x
        assert d.get("foobar") is None
    #
    f()
    interpret(f, [])

def test_rpython_merge_RWeakValueDictionary():
    empty = RWeakValueDictionary(X)
    def f(n):
        x = X()
        if n:
            d = empty
        else:
            d = RWeakValueDictionary(X)
            d.set("a", x)
        return d.get("a") is x
    assert f(0)
    assert interpret(f, [0])
    assert not f(1)
    assert not interpret(f, [1])


def test_rpython_merge_RWeakValueDictionary2():
    class A(object):
        def __init__(self):
            self.d = RWeakValueDictionary(A)
        def f(self, key):
            a = A()
            self.d.set(key, a)
            return a
    empty = A()
    def f(x):
        a = A()
        if x:
            a = empty
        a2 = a.f("a")
        assert a.d.get("a") is a2
    f(0)
    interpret(f, [0])
    f(1)
    interpret(f, [1])

    def g(x):
        if x:
            d = RWeakValueDictionary(X)
        else:
            d = RWeakValueDictionary(Y)
        d.set("x", X())
        return 41
    py.test.raises(Exception, interpret, g, [1])
