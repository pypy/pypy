import py, sys
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.annlowlevel import annotate_lowlevel_helper, LowLevelAnnotatorPolicy
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem import llmemory
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

def test_odd_ints_opaque():
    T = GcStruct('T')
    Q = GcOpaqueType('Q')
    PT = Ptr(T)
    PQ = Ptr(Q)
    def fn(n):
        t = cast_int_to_ptr(PT, n)
        assert typeOf(t) == PT
        assert cast_ptr_to_int(t) == n
        o = cast_opaque_ptr(PQ, t)
        assert cast_ptr_to_int(o) == n

    fn(13)
    interpret(fn, [11521])

def test_Ptr():
    S = GcStruct('s')
    def ll_example():
        return malloc(Ptr(S).TO)
    
    p = interpret(ll_example, [])
    assert typeOf(p) == Ptr(S)

def test_cast_opaque_ptr():
    O = GcOpaqueType('O')
    Q = GcOpaqueType('Q')
    S = GcStruct('S', ('x', Signed))
    def fn():
        s = malloc(S)
        o = cast_opaque_ptr(Ptr(O), s)
        q = cast_opaque_ptr(Ptr(Q), o)
        p = cast_opaque_ptr(Ptr(S), q)
        return p == s
    res = interpret(fn, [])
    assert res is True

    O1 = OpaqueType('O')
    S1 = Struct('S1', ('x', Signed))
    s1 = malloc(S1, immortal=True)
    def fn1():
        o1 = cast_opaque_ptr(Ptr(O1), s1)
        p1 = cast_opaque_ptr(Ptr(S1), o1)
        return p1 == s1
    res = interpret(fn1, [])
    assert res is True

def test_address():
    S = GcStruct('S')
    p1 = nullptr(S)
    p2 = malloc(S)
    
    def g(p):
        return bool(llmemory.cast_ptr_to_adr(p))
    def fn(n):
        if n < 0:
            return g(p1)
        else:
            return g(p2)

    res = interpret(fn, [-5])
    assert res is False
    res = interpret(fn, [5])
    assert res is True

def test_flavored_malloc():
    T = GcStruct('T', ('y', Signed))
    def fn(n):
        p = malloc(T, flavor='gc')
        p.y = n
        return p.y

    res = interpret(fn, [232])
    assert res == 232

    S = Struct('S', ('x', Signed))
    def fn(n):
        p = malloc(S, flavor='whatever')
        p.x = n
        result = p.x
        free(p, flavor='whatever')
        return n

    res = interpret(fn, [23])
    assert res == 23

def test_memoryerror():
    A = Array(Signed)
    def fn(n):
        try:
            a = malloc(A, n, flavor='raw')
        except MemoryError:
            return -42
        else:
            res = len(a)
            free(a, flavor='raw')
            return res

    res = interpret(fn, [123])
    assert res == 123

    res = interpret(fn, [sys.maxint])
    assert res == -42


def test_call_ptr():
    def f(x,y,z):
        return x+y+z
    FTYPE = FuncType([Signed, Signed, Signed], Signed)
    fptr = functionptr(FTYPE, "f", _callable=f)

    def g(x,y,z):
        tot = 0
        tot += fptr(x,y,z)
        tot += fptr(*(x,y,z))
        tot += fptr(x, *(x,z))
        return tot

    res = interpret(g, [1,2,4])
    assert res == g(1,2,4)

    def wrong(x,y):
        fptr(*(x,y))

    py.test.raises(TypeError, "interpret(wrong, [1, 2])")


def test_ptr_str():
    def f():
        return str(p)

    S = GcStruct('S', ('x', Signed))
    p = malloc(S)

    res = interpret(f, [])
    assert res.chars[0] == '0'
    assert res.chars[1] == 'x'


def test_first_subfield_access_is_cast_pointer():
    B = GcStruct("B", ('x', Signed))
    C = GcStruct("C", ('super', B), ('y', Signed))
    def f():
        c = malloc(C)
        c.super.x = 1
        c.y = 2
        return c.super.x + c.y
    s, t = ll_rtype(f, [])
    from pypy.translator.translator import graphof
    from pypy.objspace.flow.model import summary
    graph = graphof(t, f)
    graphsum = summary(graph)
    assert 'getsubstruct' not in graphsum
    assert 'cast_pointer' in graphsum
    
        

def test_interior_ptr():
    S = Struct("S", ('x', Signed))
    T = GcStruct("T", ('s', S))
    def f():
        t = malloc(T)
        t.s.x = 1
        return t.s.x
    res = interpret(f, [])
    assert res == 1

def test_interior_ptr_with_index():
    S = Struct("S", ('x', Signed))
    T = GcArray(S)
    def f():
        t = malloc(T, 1)
        t[0].x = 1
        return t[0].x
    res = interpret(f, [])
    assert res == 1

def test_interior_ptr_with_field_and_index():
    S = Struct("S", ('x', Signed))
    T = GcStruct("T", ('items', Array(S)))
    def f():
        t = malloc(T, 1)
        t.items[0].x = 1
        return t.items[0].x
    res = interpret(f, [])
    assert res == 1

def test_interior_ptr_with_index_and_field():
    S = Struct("S", ('x', Signed))
    T = Struct("T", ('s', S))
    U = GcArray(T)
    def f():
        u = malloc(U, 1)
        u[0].s.x = 1
        return u[0].s.x
    res = interpret(f, [])
    assert res == 1

def test_interior_ptr_len():
    S = Struct("S", ('x', Signed))
    T = GcStruct("T", ('items', Array(S)))
    def f():
        t = malloc(T, 1)
        return len(t.items)
    res = interpret(f, [])
    assert res == 1

def test_interior_ptr_with_setitem():
    T = GcStruct("T", ('s', Array(Signed)))
    def f():
        t = malloc(T, 1)
        t.s[0] = 1
        return t.s[0]
    res = interpret(f, [])
    assert res == 1
 
def test_isinstance_Ptr():
    S = GcStruct("S", ('x', Signed))
    def f(n):
        x = isinstance(Signed, Ptr)
        return x + (typeOf(x) is Ptr(S)) + len(n)
    def lltest():
        f([])
        return f([1])
    s, t = ll_rtype(lltest, [])
    assert s.is_constant() == False

def test_staticadtmeths():
    ll_func = staticAdtMethod(lambda x: x + 42)
    S = GcStruct('S', adtmeths={'ll_func': ll_func})
    def f():
        return malloc(S).ll_func(5)
    s, t = ll_rtype(f, [])
    graphf = t.graphs[0]
    for op in graphf.startblock.operations:
        assert op.opname != 'getfield'
