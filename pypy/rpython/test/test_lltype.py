from pypy.rpython.lltype import *
from pypy.rpython.lltype import _TmpPtr

def test_basics():
    S0 = GcStruct("s0", ('a', Signed), ('b', Signed))
    assert S0.a == Signed
    assert S0.b == Signed
    s0 = malloc(S0)
    print s0
    assert typeOf(s0) == GcPtr(S0)
    assert s0.a == 0
    assert s0.b == 0
    assert typeOf(s0.a) == Signed
    s0.a = 1
    s0.b = s0.a
    assert s0.a == 1
    assert s0.b == 1
    # simple array
    Ar = GcArray(('v', Signed))
    x = malloc(Ar,0)
    print x
    assert len(x) == 0
    x = malloc(Ar,3)
    print x
    assert typeOf(x) == GcPtr(Ar)
    assert typeOf(x[0]) == _TmpPtr(Ar.OF)
    assert typeOf(x[0].v) == Signed
    assert x[0].v == 0
    x[0].v = 1
    x[1].v = 2
    x[2].v = 3
    assert [x[z].v for z in range(3)] == [1, 2, 3]
    #
    def define_list(T):
        List_typ = GcStruct("list",
                ("items", GcPtr(GcArray(('item',T)))))
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
    assert typeOf(l) == GcPtr(List_typ)
    iappend(l, 2)
    iappend(l, 3)
    assert len(l.items) == 2
    assert iitem(l, 0) == 2
    assert iitem(l, 1) == 3

    IWrap = GcStruct("iwrap", ('v', Signed))
    List_typ, iwnewlist, iwappend, iwitem = define_list(GcPtr(IWrap))

    l = iwnewlist()
    assert typeOf(l) == GcPtr(List_typ)
    iw2 = malloc(IWrap)
    iw3 = malloc(IWrap)
    iw2.v = 2
    iw3.v = 3
    assert iw3.v == 3
    iwappend(l, iw2)
    iwappend(l, iw3)
    assert len(l.items) == 2
    assert iwitem(l, 0).v == 2
    assert iwitem(l, 1).v == 3

    # not allowed
    S = Struct("s", ('v', Signed))
    List_typ, iwnewlistzzz, iwappendzzz, iwitemzzz = define_list(S) # works but
    l = iwnewlistzzz()
    S1 = GcStruct("strange", ('s', S))
    py.test.raises(TypeError, "iwappendzzz(l, malloc(S1).s)")

def test_varsizestruct():
    S1 = GcStruct("s1", ('a', Signed), ('rest', Array(('v', Signed))))
    py.test.raises(TypeError, "malloc(S1)")
    s1 = malloc(S1, 4)
    assert s1.a == 0
    assert typeOf(s1.rest) == _TmpPtr(S1.rest)
    assert len(s1.rest) == 4
    assert typeOf(s1.rest[0]) == _TmpPtr(S1.rest.OF)
    assert typeOf(s1.rest[0].v) == Signed
    assert s1.rest[0].v == 0
    py.test.raises(IndexError, "s1.rest[4]")
    py.test.raises(IndexError, "s1.rest[-1]")

    s1.a = 17
    s1.rest[3].v = 5
    assert s1.a == 17
    assert s1.rest[3].v == 5

    py.test.raises(TypeError, "Struct('invalid', ('rest', Array(('v', Signed))), ('a', Signed))")
    py.test.raises(TypeError, "Struct('invalid', ('rest', GcArray(('v', Signed))), ('a', Signed))")
    py.test.raises(TypeError, "Struct('invalid', ('x', Struct('s1', ('a', Signed), ('rest', Array(('v', Signed))))))")
    py.test.raises(TypeError, "Struct('invalid', ('x', S1))")

def test_substructure_ptr():
    S2 = Struct("s2", ('a', Signed))
    S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    assert typeOf(p1.sub1) == _TmpPtr(S2)
    assert typeOf(p1.sub2) == _TmpPtr(S2)

def test_gc_substructure_ptr():
    S1 = GcStruct("s2", ('a', Signed))
    S2 = Struct("s3", ('a', Signed))
    S0 = GcStruct("s1", ('sub1', S1), ('sub2', S2))
    p1 = malloc(S0)
    assert typeOf(p1.sub1) == GcPtr(S1)
    assert typeOf(p1.sub2) == _TmpPtr(S2)

def test_tagged_pointer():
    S1 = GcStruct("s1", ('a', Signed), ('b', Unsigned))
    PList = [
        GcPtr(S1),
        NonGcPtr(S1),
        GcPtr(S1, mytag=True),
        NonGcPtr(S1, mytag=True),
        GcPtr(S1, myothertag=True),
        ]
    for P1 in PList:
        for P2 in PList:
            assert (P1 == P2) == (P1 is P2)
    assert PList[2] == GcPtr(S1, mytag=True)

def test_cast_flags():
    S1 = GcStruct("s1", ('a', Signed), ('b', Unsigned))
    p1 = malloc(S1)
    p2 = cast_flags(NonGcPtr(S1), p1)
    assert typeOf(p2) == NonGcPtr(S1)
    p3 = cast_flags(GcPtr(S1), p2)
    assert typeOf(p3) == GcPtr(S1)
    assert p1 == p3
    py.test.raises(TypeError, "p1 == p2")
    py.test.raises(TypeError, "p2 == p3")

    PT = GcPtr(S1, mytag=True)
    p2 = cast_flags(PT, p1)
    assert typeOf(p2) == PT
    p3 = cast_flags(GcPtr(S1), p2)
    assert typeOf(p3) == GcPtr(S1)
    assert p1 == p3
    py.test.raises(TypeError, "p1 == p2")
    py.test.raises(TypeError, "p2 == p3")

def test_cast_parent():
    S2 = Struct("s2", ('a', Signed))
    S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    p2 = p1.sub1
    assert typeOf(p2) == _TmpPtr(S2)
    p3 = cast_flags(NonGcPtr(S2), p2)
    assert typeOf(p3) == NonGcPtr(S2)
    p4 = cast_parent(NonGcPtr(S1), p3)
    assert typeOf(p4) == NonGcPtr(S1)
    p5 = cast_flags(GcPtr(S1), p4)
    assert typeOf(p5) == GcPtr(S1)
    assert p5 == p1
    py.test.raises(TypeError, "cast_parent(GcPtr(S1), p1.sub1)")
    py.test.raises(TypeError, "cast_parent(GcPtr(S1), p1.sub2)")
    py.test.raises(TypeError, "cast_parent(_TmpPtr(S1), p1.sub2)")
    py.test.raises(TypeError, "cast_parent(NonGcPtr(S2), p3)")
    SUnrelated = Struct("unrelated")
    py.test.raises(TypeError, "cast_parent(NonGcPtr(SUnrelated), p3)")

def test_best_effort_gced_parent_detection():
    S2 = Struct("s2", ('a', Signed))
    S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2), ('tail', Array(('e', Signed))))
    p1 = malloc(S1, 1)
    p2 = p1.sub2
    assert p2.a == 0
    p3 = p1.tail
    p3[0].e = 1
    assert p3[0].e == 1
    del p1
    import gc
    gc.collect()
    py.test.raises(RuntimeError, "p2.a")
    py.test.raises(RuntimeError, "p3[0]")

def test_best_effort_gced_parent_for_arrays():
    A1 = GcArray(('v', Signed))
    p1 = malloc(A1, 10)
    p1[5].v=3
    assert p1[0].v == 0
    assert p1[9].v == 0
    assert p1[5].v == 3
    p1_5 = p1[5]
    del p1
    import gc
    gc.collect()
    py.test.raises(RuntimeError, "p1_5.v")        

def test_examples():
    A1 = GcArray(('v', Signed))
    S = GcStruct("s", ('v', Signed))
    St = GcStruct("st", ('v', Signed),('trail', Array(('v', Signed))))

    PA1 = GcPtr(A1)
    PS = GcPtr(S)
    PSt = GcPtr(St)

    ex_pa1 = PA1._example()
    ex_ps  = PS._example()
    ex_pst = PSt._example()

    assert typeOf(ex_pa1) == PA1
    assert typeOf(ex_ps) == PS
    assert typeOf(ex_pst) == PSt

    assert ex_pa1[0].v == 0
    assert ex_ps.v == 0
    assert ex_pst.v == 0
    assert ex_pst.trail[0].v == 0

def test_functions():
    F = FuncType((Signed,), Signed)
    py.test.raises(TypeError, "Struct('x', ('x', F))")

    PF = NonGcPtr(F)
    pf = PF._example()
    assert pf(0) == 0
    py.test.raises(TypeError, pf, 0, 0)
    py.test.raises(TypeError, pf, 'a')

def test_inconsistent_gc_containers():
    A = GcArray(('y', Signed))
    S = GcStruct('b', ('y', Signed))
    py.test.raises(TypeError, "GcPtr(Struct('a', ('x', Signed)))")
    py.test.raises(TypeError, "Struct('a', ('x', S))")
    py.test.raises(TypeError, "GcStruct('a', ('x', Signed), ('y', S))")
    py.test.raises(TypeError, "Array(('x', S))")
    py.test.raises(TypeError, "GcArray(('x', S))")
    py.test.raises(TypeError, "Struct('a', ('x', A))")
    py.test.raises(TypeError, "GcStruct('a', ('x', A))")

def test_forward_reference():
    F = GcForwardReference()
    S = GcStruct('abc', ('x', GcPtr(F)))
    F.become(S)
    assert S.x == GcPtr(S)
    py.test.raises(TypeError, "GcForwardReference().become(Struct('abc'))")
    ForwardReference().become(Struct('abc'))
    hash(S)

def test_nullptr():
    S = Struct('s')
    p0 = nullptr(S)
    assert not p0
