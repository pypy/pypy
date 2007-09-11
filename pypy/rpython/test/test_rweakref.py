import weakref
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
