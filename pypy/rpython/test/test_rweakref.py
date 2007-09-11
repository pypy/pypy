import py, weakref
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.test.test_llinterp import interpret


def test_ll_weakref():
    S = lltype.GcStruct('S', ('x',lltype.Signed))
    def g():
        s = lltype.malloc(S)
        w = llmemory.weakref_create(s)
        assert llmemory.weakref_deref(lltype.Ptr(S), w) == s
        assert llmemory.weakref_deref(lltype.Ptr(S), w) == s
        return w   # 's' is forgotten here
    def f():
        w = g()
        rgc.collect()
        return llmemory.weakref_deref(lltype.Ptr(S), w)

    res = interpret(f, [])
    assert res == lltype.nullptr(S)


def test_weakref_simple():
    class A:
        pass
    class B(A):
        pass
    class C(A):
        pass

    def f(n):
        if n:
            x = B()
            x.hello = 42
            r = weakref.ref(x)
        else:
            x = C()
            x.hello = 64
            r = weakref.ref(x)
        return r().hello, x      # returns 'x' too, to keep it alive
    res = interpret(f, [1])
    assert res.item0 == 42
    res = interpret(f, [0])
    assert res.item0 == 64

def test_prebuilt_weakref():
    class A:
        pass
    a1 = A()
    a1.hello = 5
    w1 = weakref.ref(a1)
    a2 = A()
    a2.hello = 8
    w2 = weakref.ref(a2)

    def f(n):
        if n:
            r = w1
        else:
            r = w2
        return r().hello
    res = interpret(f, [1])
    assert res == 5
    res = interpret(f, [0])
    assert res == 8

def test_prebuilt_dead_weakref():
    py.test.skip("in-progress")
    class A:
        pass
    a1 = A()
    w1 = weakref.ref(a1)
    a2 = A()
    w2 = weakref.ref(a2)

    del a1
    rgc.collect()
    assert w1() is None

    def f(n):
        if n:
            r = w1
        else:
            r = w2
        return r() is not None
    res = interpret(f, [1])
    assert res == False
    res = interpret(f, [0])
    assert res == True
