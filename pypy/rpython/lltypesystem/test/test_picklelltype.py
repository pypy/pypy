from pypy.rpython.lltypesystem.lltype import *

import pickle

def isweak(p, T):
    return p._weak and typeOf(p).TO == T

def test_pickle_types():
    S0 = GcStruct("s0", ('a', Signed), ('b', Signed))
    p_S0 = pickle.dumps(S0)
    r_S0 = pickle.loads(p_S0)
    assert S0 == r_S0
    assert hash(S0) == hash(r_S0)
    s0 = malloc(S0)
    print s0
    s0.a = 1
    s0.b = s0.a
    p_s0 = pickle.dumps(s0)
    r_s0 = pickle.loads(p_s0)
    # simple array
    Ar = GcArray(('v', Signed))
    p_Ar = pickle.dumps(Ar)
    r_Ar = pickle.loads(p_Ar)
    assert Ar == r_Ar
    x = malloc(Ar,0)
    p_x = pickle.dumps(x)
    r_x = pickle.loads(p_x)
    assert len(r_x) == 0
    x = malloc(Ar,3)
    x[0].v = 1
    x[1].v = 2
    x[2].v = 3
    p_x = pickle.dumps(x)
    r_x = pickle.loads(p_x)
    assert typeOf(x) == Ptr(Ar)
    assert isweak(x[0], Ar.OF)
    assert typeOf(x[0].v) == Signed
    assert [x[z].v for z in range(3)] == [1, 2, 3]
    #
    def define_list(T):
        List_typ = GcStruct("list",
                ("items", Ptr(GcArray(('item',T)))))
        def newlist():
            l = malloc(List_typ)
            items = malloc(List_typ.items.TO, 0)
            l.items = items
            return l

        def append(l, newitem):
            length = len(l.items)
            newitems = malloc(List_typ.items.TO, length+1)
            i = 0
            while i<length:
              newitems[i].item = l.items[i].item
              i += 1
            newitems[length].item = newitem
            l.items = newitems

        def item(l, i):
            return l.items[i].item

        return List_typ, newlist, append, item

    List_typ, inewlist, iappend, iitem = define_list(Signed)

    l = inewlist()
    iappend(l, 2)
    iappend(l, 3)
    p_l = pickle.dumps(l)
    r_l = pickle.loads(p_l)
    assert len(r_l.items) == 2
    assert iitem(r_l, 0) == 2
    assert iitem(r_l, 1) == 3
    
    IWrap = GcStruct("iwrap", ('v', Signed))
    List_typ, iwnewlist, iwappend, iwitem = define_list(Ptr(IWrap))

    l = iwnewlist()
    iw2 = malloc(IWrap)
    iw3 = malloc(IWrap)
    iw2.v = 2
    iw3.v = 3
    iwappend(l, iw2)
    iwappend(l, iw3)
    p_l = pickle.dumps(l)
    r_l = pickle.loads(p_l)
    assert len(r_l.items) == 2
    assert iwitem(r_l, 0).v == 2
    assert iwitem(r_l, 1).v == 3

def test_varsizestruct():
    S1 = GcStruct("s1", ('a', Signed), ('rest', Array(('v', Signed))))
    py.test.raises(TypeError, "malloc(S1)")
    s1 = malloc(S1, 4)
    p_s1 = pickle.dumps(s1)
    r_s1 = pickle.loads(p_s1)
    assert r_s1.a == 0
    assert isweak(r_s1.rest, S1.rest)
    assert len(r_s1.rest) == 4
    assert isweak(r_s1.rest[0], S1.rest.OF)
    assert typeOf(r_s1.rest[0].v) == Signed
    assert r_s1.rest[0].v == 0
    py.test.raises(IndexError, "r_s1.rest[4]")
    py.test.raises(IndexError, "r_s1.rest[-1]")

    s1.a = 17
    s1.rest[3].v = 5
    p_s1 = pickle.dumps(s1)
    r_s1 = pickle.loads(p_s1)
    assert r_s1.a == 17
    assert r_s1.rest[3].v == 5

def test_substructure_ptr():
    S3 = Struct("s3", ('a', Signed))
    S2 = Struct("s2", ('s3', S3))
    S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    p_p1 = pickle.dumps(p1)
    r_p1 = pickle.loads(p_p1)
    assert isweak(r_p1.sub1, S2)
    assert isweak(r_p1.sub2, S2)
    assert isweak(r_p1.sub1.s3, S3)
    r_p2 = r_p1.sub1
    assert isweak(r_p2.s3, S3)

def test_gc_substructure_ptr():
    S1 = GcStruct("s2", ('a', Signed))
    S2 = Struct("s3", ('a', Signed))
    S0 = GcStruct("s1", ('sub1', S1), ('sub2', S2))
    p1 = malloc(S0)
    r_p1 = pickle.loads(pickle.dumps(p1))
    assert typeOf(r_p1.sub1) == Ptr(S1)
    assert isweak(r_p1.sub2, S2)

def test_cast_simple_widening():
    S2 = Struct("s2", ('a', Signed))
    S1 = Struct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1, immortal=True)
    r_p1 = pickle.loads(pickle.dumps(p1))
    p2 = r_p1.sub1
    p3 = p2
    assert typeOf(p3) == Ptr(S2)
    p4 = cast_pointer(Ptr(S1), p3)
    assert typeOf(p4) == Ptr(S1)
    assert p4 == r_p1

def test_best_effort_gced_parent_detection():
    S2 = Struct("s2", ('a', Signed))
    S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2), ('tail', Array(('e', Signed))))
    p1 = malloc(S1, 1)
    p2 = p1.sub2
    p3 = p1.tail
    p3[0].e = 1
    r_p2 = pickle.loads(pickle.dumps(p2))
    py.test.raises(RuntimeError, "r_p2.a")
    r_p1 = pickle.loads(pickle.dumps(p1))
    r_p2 = r_p1.sub2
    r_p3 = r_p1.tail
    assert r_p3[0].e == 1
    del r_p1
    import gc
    gc.collect()
    py.test.raises(RuntimeError, "r_p2.a")
    py.test.raises(RuntimeError, "r_p3[0]")

def test_best_effort_gced_parent_for_arrays():
    A1 = GcArray(('v', Signed))
    p1 = malloc(A1, 10)
    p1[5].v = 3
    p1_5 = p1[5]
    r_p1_5 = pickle.loads(pickle.dumps(p1_5))
    py.test.raises(RuntimeError, "r_p1_5.v")
    r_p1 = pickle.loads(pickle.dumps(p1))
    r_p1_5 = r_p1[5]
    assert r_p1[0].v == 0
    assert r_p1[9].v == 0
    assert r_p1[5].v == 3
    del r_p1
    import gc
    gc.collect()
    py.test.raises(RuntimeError, "r_p1_5.v")        

def DONOTtest_functions():
    F = FuncType((Signed,), Signed)
    py.test.raises(TypeError, "Struct('x', ('x', F))")

    PF = Ptr(F)
    pf = PF._example()
    assert pf(0) == 0
    py.test.raises(TypeError, pf, 0, 0)
    py.test.raises(TypeError, pf, 'a')

def test_forward_reference():
    F = GcForwardReference()
    S = GcStruct('abc', ('x', Ptr(F)))
    F.become(S)
    assert S.x == Ptr(S)
    py.test.raises(TypeError, "GcForwardReference().become(Struct('abc'))")
    ForwardReference().become(Struct('abc'))
    r_S = pickle.loads(pickle.dumps(S))
    assert hash(S) == hash(r_S)

def DONOTtest_nullptr():
    S = Struct('s')
    p0 = nullptr(S)
    assert not p0
    assert typeOf(p0) == Ptr(S)

def DONOTtest_nullptr_cast():
    S = Struct('s')
    p0 = nullptr(S)
    assert not p0
    S1 = Struct("s1", ('s', S))
    p10 = cast_pointer(Ptr(S1), p0)
    assert typeOf(p10) == Ptr(S1)
    assert not p10
    

def DONOTtest_hash():
    S = ForwardReference()
    S.become(Struct('S', ('p', Ptr(S))))
    assert S == S
    hash(S)   # assert no crash, and force the __cached_hash computation
    S1 = Struct('S', ('p', Ptr(S)))
    assert S1 == S
    assert S == S1
    assert hash(S1) == hash(S)

def DONOTtest_array_with_non_container_elements():
    As = GcArray(Signed)
    a = malloc(As, 3)
    assert typeOf(a) == Ptr(As)
    assert a[0] == 0
    assert a[1] == 0
    assert a[2] == 0
    a[1] = 3
    assert a[1] == 3
    S = GcStruct('s', ('x', Signed))
    s = malloc(S)
    py.test.raises(TypeError, "a[1] = s")
    S = GcStruct('s', ('x', Signed))
    py.test.raises(TypeError, "Array(S)")
    py.test.raises(TypeError, "Array(As)")
    S = Struct('s', ('x', Signed))
    A = GcArray(S)
    a = malloc(A, 2)
    s = S._container_example() # should not happen anyway
    py.test.raises(TypeError, "a[0] = s")
    S = Struct('s', ('last', Array(S)))
    py.test.raises(TypeError, "Array(S)")

def DONOTtest_immortal_parent():
    S1 = GcStruct('substruct', ('x', Signed))
    S  = GcStruct('parentstruct', ('s1', S1))
    p = malloc(S, immortal=True)
    p1 = p.s1
    p1.x = 5
    del p
    p = cast_pointer(Ptr(S), p1)
    assert p.s1.x == 5

def DONOTtest_getRuntimeTypeInfo():
    S = GcStruct('s', ('x', Signed))
    py.test.raises(ValueError, "getRuntimeTypeInfo(S)")
    pinf0 = attachRuntimeTypeInfo(S)
    assert pinf0._obj.about == S
    pinf = getRuntimeTypeInfo(S)
    assert pinf == pinf0
    pinf1 = getRuntimeTypeInfo(S)
    assert pinf == pinf1
    Z = GcStruct('z', ('x', Unsigned))
    attachRuntimeTypeInfo(Z)
    assert getRuntimeTypeInfo(Z) != pinf0
    Sbis = GcStruct('s', ('x', Signed))
    attachRuntimeTypeInfo(Sbis)
    assert getRuntimeTypeInfo(Sbis) != pinf0
    assert Sbis != S # the attached runtime type info distinguishes them

def DONOTtest_getRuntimeTypeInfo_destrpointer():
    S = GcStruct('s', ('x', Signed))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return getRuntimeTypeInfo(S)
    qp = functionptr(FuncType([Ptr(S)], Ptr(RuntimeTypeInfo)), 
                     "type_info_S", 
                     _callable=type_info_S)
    dp = functionptr(FuncType([Ptr(S)], Void), 
                     "destructor_funcptr", 
                     _callable=f)
    pinf0 = attachRuntimeTypeInfo(S, qp, destrptr=dp)
    assert pinf0._obj.about == S
    pinf = getRuntimeTypeInfo(S)
    assert pinf == pinf0
    pinf1 = getRuntimeTypeInfo(S)
    assert pinf == pinf1
    assert pinf._obj.destructor_funcptr == dp
    assert pinf._obj.query_funcptr == qp

def DONOTtest_runtime_type_info():
    S = GcStruct('s', ('x', Signed))
    attachRuntimeTypeInfo(S)
    s = malloc(S)
    assert runtime_type_info(s) == getRuntimeTypeInfo(S)
    S1 = GcStruct('s1', ('sub', S), ('x', Signed))
    attachRuntimeTypeInfo(S1)
    s1 = malloc(S1)
    assert runtime_type_info(s1) == getRuntimeTypeInfo(S1)
    assert runtime_type_info(s1.sub) == getRuntimeTypeInfo(S1)
    assert runtime_type_info(cast_pointer(Ptr(S), s1)) == getRuntimeTypeInfo(S1)
    def dynamic_type_info_S(p):
        if p.x == 0:
            return getRuntimeTypeInfo(S)
        else:
            return getRuntimeTypeInfo(S1)
    fp = functionptr(FuncType([Ptr(S)], Ptr(RuntimeTypeInfo)), 
                     "dynamic_type_info_S", 
                     _callable=dynamic_type_info_S)
    attachRuntimeTypeInfo(S, fp)
    assert s.x == 0
    assert runtime_type_info(s) == getRuntimeTypeInfo(S)
    s.x = 1
    py.test.raises(RuntimeError, "runtime_type_info(s)")
    assert s1.sub.x == 0
    py.test.raises(RuntimeError, "runtime_type_info(s1.sub)")
    s1.sub.x = 1
    assert runtime_type_info(s1.sub) == getRuntimeTypeInfo(S1)
    
def DONOTtest_flavor_malloc():
    S = Struct('s', ('x', Signed))
    py.test.raises(TypeError, malloc, S)
    p = malloc(S, flavor="raw")
    assert typeOf(p).TO == S
    assert not isweak(p, S)
    
def DONOTtest_opaque():
    O = OpaqueType('O')
    p1 = opaqueptr(O, 'p1', hello="world")
    assert typeOf(p1) == Ptr(O)
    assert p1._obj.hello == "world"
    assert parentlink(p1._obj) == (None, None)
    S = GcStruct('S', ('stuff', O))
    p2 = malloc(S)
    assert typeOf(p2) == Ptr(S)
    assert typeOf(p2.stuff) == Ptr(O)
    assert parentlink(p2.stuff._obj) == (p2._obj, 'stuff')

def DONOTtest_is_atomic():
    U = Struct('inlined', ('z', Signed))
    A = Ptr(RuntimeTypeInfo)
    P = Ptr(GcStruct('p'))
    Q = GcStruct('q', ('i', Signed), ('u', U), ('p', P))
    O = OpaqueType('O')
    F = GcForwardReference()
    assert A._is_atomic() is True
    assert P._is_atomic() is False
    assert Q.i._is_atomic() is True
    assert Q.u._is_atomic() is True
    assert Q.p._is_atomic() is False
    assert Q._is_atomic() is False
    assert O._is_atomic() is False
    assert F._is_atomic() is False

def DONOTtest_adtmeths():
    def h_newstruct():
        return malloc(S)
    
    S = GcStruct('s', ('x', Signed), 
                 adtmeths={"h_newstruct": h_newstruct})

    s = S.h_newstruct()

    assert typeOf(s) == Ptr(S)

    def h_alloc(n):
        return malloc(A, n)

    def h_length(a):
        return len(a)

    A = GcArray(Signed,
                adtmeths={"h_alloc": h_alloc,
                          "h_length": h_length})

    a = A.h_alloc(10)

    assert typeOf(a) == Ptr(A)
    assert len(a) == 10

    assert a.h_length() == 10

def DONOTtest_adt_typemethod():
    def h_newstruct(S):
        return malloc(S)
    h_newstruct = typeMethod(h_newstruct)
    
    S = GcStruct('s', ('x', Signed), 
                 adtmeths={"h_newstruct": h_newstruct})

    s = S.h_newstruct()

    assert typeOf(s) == Ptr(S)

    Sprime = GcStruct('s', ('x', Signed), 
                      adtmeths={"h_newstruct": h_newstruct})

    assert S == Sprime

