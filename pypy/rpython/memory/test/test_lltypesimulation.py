from pypy.rpython.memory.lltypesimulation import *

py.log.setconsumer("lltypesim", None)

def test_struct():
    S0 = lltype.GcStruct("s0", ('a',  lltype.Signed),
                         ('b', lltype.Signed), ('c',  lltype.Char))
    s0 = malloc(S0)
    assert s0.a == 0
    assert s0.b == 0
    assert s0.c == '\x00'
    s0.a = 42
    s0.b = 43
    s0.c = 'x'
    assert s0.a == 42
    assert s0.b == 43
    assert s0.c == 'x'
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
