from pypy.rpython.memory.lltypesimulation import *

py.log.setconsumer("lltypesim", None)

def test_struct():
    S0 = lltype.GcStruct("s0", ('a',  lltype.Signed),
                         ('b', lltype.Signed), ('c',  lltype.Char),
                         ('d', lltype.Bool))
    s0 = malloc(S0)
    assert s0.a == 0
    assert s0.b == 0
    assert s0.c == '\x00'
    assert s0.b == 0
    s0.a = 42
    s0.b = 43
    s0.c = 'x'
    s0.d = True
    assert s0.a == 42
    assert s0.b == 43
    assert s0.c == 'x'
    assert s0.d == True
    assert lltype.typeOf(s0.d) == lltype.Bool
    s0.a = 1
    s0.b = s0.a
    assert s0.a == 1
    assert s0.b == 1

def test_array():
    Ar =  lltype.GcArray(('v',  lltype.Signed))
    x = malloc(Ar, 0)
    assert len(x) == 0
    x = malloc(Ar, 3)
    assert lltype.typeOf(x) ==  lltype.Ptr(Ar)
    assert lltype.typeOf(x[0].v) ==  lltype.Signed
    assert x[0].v == 0
    x[0].v = 1
    x[1].v = 2
    x[2].v = 3
    assert [x[z].v for z in range(3)] == [1, 2, 3]

def test_bool_array():
    Ar = lltype.GcArray(lltype.Bool)
    x = malloc(Ar, 3)
    assert len(x) == 3
    assert lltype.typeOf(x[0]) == lltype.Bool
    x[0] = True
    x[1] = False
    x[2] = False
    assert [x[z] for z in range(3)] == [True, False, False]
    

def define_list(T):
    List_typ = lltype.GcStruct(
        "list", ("items", lltype.Ptr(lltype.GcArray(('item',T)))))
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


def test_simple_list():
    List_typ, inewlist, iappend, iitem = define_list(lltype.Signed)
    l = inewlist()
    assert lltype.typeOf(l) == lltype.Ptr(List_typ)
    iappend(l, 2)
    assert len(l.items) == 1
    assert iitem(l, 0) == 2
    iappend(l, 3)
    assert len(l.items) == 2
    assert iitem(l, 1) == 3

def test_list_of_struct():
    IWrap = lltype.GcStruct("iwrap", ('v', lltype.Signed))
    List_typ, iwnewlist, iwappend, iwitem = define_list(lltype.Ptr(IWrap))
    l = iwnewlist()
    assert lltype.typeOf(l) == lltype.Ptr(List_typ)
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

def test_varsizestruct():
    S1 = lltype.GcStruct("s1", ('a', lltype.Signed),
                         ('rest', lltype.Array(('v', lltype.Signed))))
    py.test.raises(TypeError, "malloc(S1)")
    s1 = malloc(S1, 4)
    assert s1.a == 0
    s1.rest[1].v = 211
    s1.a = 42
    assert len(s1.rest) == 4
    assert lltype.typeOf(s1.rest[0].v) == lltype.Signed
    assert s1.rest[0].v == 0
    assert s1.rest[1].v == 211
    assert s1.a == 42
    py.test.raises(IndexError, "s1.rest[4]")
    py.test.raises(IndexError, "s1.rest[-1]")
    s1.a = 17
    s1.rest[3].v = 5
    assert s1.a == 17
    assert s1.rest[3].v == 5

def test_substructure_ptr():
    S3 = lltype.Struct("s3", ('a', lltype.Signed))
    S2 = lltype.Struct("s2", ('s3', S3), ('char', lltype.Char))
    S1 = lltype.GcStruct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1)
    p1.sub1.char = "a"
    p1.sub2.char = "b"
    p1.sub1.s3.a = 12
    p1.sub2.s3.a = 14
    assert p1.sub1.char == "a"
    assert p1.sub2.char == "b"
    assert p1.sub1.s3.a == 12
    assert p1.sub2.s3.a == 14

def test_cast_simple_widening():
    S2 = lltype.Struct("s2", ('a', lltype.Signed))
    S1 = lltype.Struct("s1", ('sub1', S2), ('sub2', S2))
    p1 = malloc(S1, immortal=True)
    p2 = p1.sub1
    p3 = p2
    p4 = cast_pointer(lltype.Ptr(S1), p3)
    assert p4 == p1
    SUnrelated = lltype.Struct("unrelated")
    py.test.raises(TypeError, "cast_pointer(lltype.Ptr(SUnrelated), p3)")

def test_cast_simple_widening2():
    S2 = lltype.GcStruct("s2", ('a', lltype.Signed))
    S1 = lltype.GcStruct("s1", ('sub1', S2))
    p1 = malloc(S1)
    p2 = p1.sub1
    assert lltype.typeOf(p2) == lltype.Ptr(S2)
    p3 = cast_pointer(lltype.Ptr(S1), p2)
    assert p3 == p1
    p2 = malloc(S2)

def test_cast_pointer():
    S3 = lltype.GcStruct("s3", ('a', lltype.Signed))
    S2 = lltype.GcStruct("s3", ('sub', S3))
    S1 = lltype.GcStruct("s1", ('sub', S2))
    p1 = malloc(S1)
    p2 = p1.sub
    p3 = p2.sub
    p12 = cast_pointer(lltype.Ptr(S1), p2)
    assert p12 == p1
    p13 = cast_pointer(lltype.Ptr(S1), p3)
    assert p13 == p1
    p21 = cast_pointer(lltype.Ptr(S2), p1)
    assert p21 == p2
    p23 = cast_pointer(lltype.Ptr(S2), p3)
    assert p23 == p2
    p31 = cast_pointer(lltype.Ptr(S3), p1)
    assert p31 == p3
    p32 = cast_pointer(lltype.Ptr(S3), p2)
    assert p32 == p3
    p3 = malloc(S3)
    p2 = malloc(S2)
    S0 = lltype.GcStruct("s0", ('sub', S1))
    p0 = malloc(S0)
    assert p0 == cast_pointer(lltype.Ptr(S0), p0)
    p3 = cast_pointer(lltype.Ptr(S3), p0)
    p03 = cast_pointer(lltype.Ptr(S0), p3)
    assert p0 == p03
    S1bis = lltype.GcStruct("s1b", ('sub', S2))
    assert S1bis != S1
    p1b = malloc(S1bis)
    p3 = p1b.sub.sub
    assert p1b == cast_pointer(lltype.Ptr(S1bis), p3)


def DONOTtest_functions():
    F = lltype.FuncType((Signed,), Signed)
    py.test.raises(TypeError, "lltype.Struct('x', ('x', F))")
    PF = Ptr(F)
    pf = PF._example()
    assert pf(0) == 0
    py.test.raises(TypeError, pf, 0, 0)
    py.test.raises(TypeError, pf, 'a')

def test_forward_reference():
    F = lltype.GcForwardReference()
    S = lltype.GcStruct('abc', ('x', lltype.Ptr(F)))
    F.become(S)
    s = malloc(S)
    s.x = s
    assert s.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x == s

def test_nullptr():
    S = lltype.Struct('s')
    p0 = nullptr(S)
    assert not p0
    assert lltype.typeOf(p0) == lltype.Ptr(S)

def test_nullptr_cast():
    S = lltype.Struct('s')
    p0 = nullptr(S)
    assert not p0
    S1 = lltype.Struct("s1", ('s', S))
    p10 = cast_pointer(lltype.Ptr(S1), p0)
    assert lltype.typeOf(p10) == lltype.Ptr(S1)
    assert not p10

def test_array_with_non_container_elements():
    As = lltype.GcArray(lltype.Signed)
    a = malloc(As, 3)
    assert a[0] == 0
    assert a[1] == 0
    assert a[2] == 0
    a[1] = 3
    assert a[1] == 3
    S = lltype.GcStruct('s', ('x', lltype.Signed))
    s = malloc(S)
    py.test.raises(TypeError, "a[1] = s")
    S = lltype.Struct('s', ('x', lltype.Signed))
    A = lltype.GcArray(S)
    a = malloc(A, 2)
    s = malloc(S)
    py.test.raises(TypeError, "a[0] = s")

def test_array_of_ptrs():
    S = lltype.GcStruct("name", ("v", lltype.Signed))
    A = lltype.GcArray(lltype.Ptr(S))
    a = malloc(A, 3)
    a[0] = malloc(S)
    a[0].v = 1
    a[1] = malloc(S)
    a[1].v = 2
    a[2] = malloc(S)
    a[2].v = 3
    assert [a[z].v for z in range(3)] == [1, 2, 3]

def test_array_of_ptr_to_bigger_struct():
    S = lltype.GcStruct("name", ("v1", lltype.Signed), ("v2", lltype.Signed))
    A = lltype.GcArray(lltype.Ptr(S))
    a = malloc(A, 3)
    assert not a[0]
    assert not a[1]
    a[0] = malloc(S)
    a[0].v1 = 1
    a[0].v2 = 2
    assert a[0].v1 == 1
    assert a[0].v2 == 2
    assert not a[1]

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
    
def test_function_ptr():
    def f(x, y):
        return x + y
    F = lltype.FuncType((lltype.Signed, lltype.Signed), lltype.Signed)
    funcptr = functionptr(F, "add", _callable=f)
    assert funcptr(1, 2) == 3

def test_pointer_equality():
    S0 = lltype.GcStruct("s0",
                         ('a', lltype.Struct("s1", ('a', lltype.Signed))),
                         ('b', lltype.Signed))
    s0 = malloc(S0)
    assert s0.a == s0.a
    assert not s0.a != s0.a
    
def test_struct_with_address():
    S = lltype.GcStruct("s", ('a', lladdress.Address))
    s = malloc(S)
    s.a = lladdress.NULL
    assert s.a == lladdress.NULL
