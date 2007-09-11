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
