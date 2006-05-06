from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.annlowlevel import annotate_lowlevel_helper, LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.rtyper import RPythonTyper
from pypy.annotation import model as annmodel


# ____________________________________________________________

def ll_rtype(llfn, argtypes=[]):
    a = RPythonAnnotator()
    graph = annotate_lowlevel_helper(a, llfn, argtypes)
    s = a.binding(graph.getreturnvar())
    t = a.translator
    typer = RPythonTyper(a)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return s, t

def test_cast_pointer():
    S = GcStruct('s', ('x', Signed))
    S1 = GcStruct('s1', ('sub', S))
    S2 = GcStruct('s2', ('sub', S1))
    PS = Ptr(S)
    PS2 = Ptr(S2)
    def lldown(p):
        return cast_pointer(PS, p)
    s, t = ll_rtype(lldown, [annmodel.SomePtr(PS2)])
    assert s.ll_ptrtype == PS
    def llup(p):
        return cast_pointer(PS2, p)
    s, t = ll_rtype(llup, [annmodel.SomePtr(PS)])
    assert s.ll_ptrtype == PS2

def test_runtime_type_info():
    S = GcStruct('s', ('x', Signed))
    attachRuntimeTypeInfo(S)
    def ll_example(p):
        return (runtime_type_info(p),
                runtime_type_info(p) == getRuntimeTypeInfo(S))

    assert ll_example(malloc(S)) == (getRuntimeTypeInfo(S), True)
    s, t = ll_rtype(ll_example, [annmodel.SomePtr(Ptr(S))])
    assert s == annmodel.SomeTuple([annmodel.SomePtr(Ptr(RuntimeTypeInfo)),
                                    annmodel.SomeBool()])

from pypy.rpython.test.test_llinterp import interpret, gengraph

def test_adtmeths():
    policy = LowLevelAnnotatorPolicy()

    def h_newstruct():
        return malloc(S)
    
    S = GcStruct('s', ('x', Signed), 
                 adtmeths={"h_newstruct": h_newstruct})

    def f():
        return S.h_newstruct()

    s = interpret(f, [], policy=policy)

    assert typeOf(s) == Ptr(S)

    def h_alloc(n):
        return malloc(A, n)
    def h_length(a):
        return len(a)

    A = GcArray(Signed,
                adtmeths={"h_alloc": h_alloc,
                          "h_length": h_length,
                          'flag': True})

    def f():
        return A.h_alloc(10)

    a = interpret(f, [], policy=policy)

    assert typeOf(a) == Ptr(A)
    assert len(a) == 10
    

    def f():
        a = A.h_alloc(10)
        return a.h_length()

    res = interpret(f, [], policy=policy)
    assert res == 10

    def f():
        return A.flag
    res = interpret(f, [], policy=policy)
    assert res

def test_odd_ints():
    T = GcStruct('T')
    S = GcStruct('S', ('t', T))
    PT = Ptr(T)
    PS = Ptr(S)
    def fn(n):
        s = cast_int_to_ptr(PS, n)
        assert typeOf(s) == PS
        assert cast_ptr_to_int(s) == n
        t = cast_pointer(PT, s)
        assert typeOf(t) == PT
        assert cast_ptr_to_int(t) == n
        assert s == cast_pointer(PS, t)

    interpret(fn, [11521])


def test_Ptr():
    S = GcStruct('s')
    def ll_example():
        return malloc(Ptr(S).TO)
    
    p = interpret(ll_example, [])
    assert typeOf(p) == Ptr(S)
