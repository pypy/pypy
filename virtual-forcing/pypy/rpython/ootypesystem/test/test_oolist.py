import py
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.ootypesystem.ootype import *
from pypy.rpython.rlist import ll_append
from pypy.translator.translator import TranslationContext

def test_new():
    LT = List(Signed)
    l = new(LT)
    assert typeOf(l) == LT

def test_ll_newlist():
    LT = List(Signed)
    l = LT.ll_newlist(10)
    assert typeOf(l) == LT
    assert l.ll_length() == 10

def test_len():
    LT = List(Signed)
    l = new(LT)
    assert l.ll_length() == 0

def test_resize():
    LT = List(Signed)
    lst = new(LT)
    lst._ll_resize(10)
    assert lst.ll_length() == 10
    lst._ll_resize_ge(9)
    assert lst.ll_length() == 10
    lst._ll_resize_ge(20)
    assert lst.ll_length() >= 20
    lst._ll_resize_le(10)
    assert lst.ll_length() <= 10


def test_setitem_getitem():
    LT = List(Signed)
    l = new(LT)
    ll_append(l, 2)
    assert l.ll_getitem_fast(0) == 2
    l.ll_setitem_fast(0, 3)
    assert l.ll_getitem_fast(0) == 3

def test_setitem_indexerror():
    LT = List(Signed)
    l = new(LT)
    py.test.raises(IndexError, l.ll_getitem_fast, 0)
    py.test.raises(IndexError, l.ll_setitem_fast, 0, 1)

def test_null():
    LT = List(Signed)
    n = null(LT)
    py.test.raises(RuntimeError, "n.append(0)")

def test_eq_hash():
    LT1 = List(Signed)
    LT2 = List(Signed)
    LT3 = List(Unsigned)
    assert LT1 == LT2
    assert LT1 != LT3
    assert hash(LT1) == hash(LT2)

def test_optional_itemtype():
    LT = List()
    LT2 = List(Signed)
    assert LT != Signed
    assert LT != LT2
    assert LT2 != LT
    py.test.raises(TypeError, hash, LT)
    setItemType(LT, Signed)
    assert LT == LT2
    assert LT2 == LT
    assert hash(LT) == hash(LT2)

def test_recursive():
    LT = List()
    setItemType(LT, LT)
    assert LT == LT
    assert hash(LT) == hash(LT)
    str(LT) # make sure this doesn't recurse infinitely

    LT2 = List()
    setItemType(LT2, LT2)
    assert LT == LT2
    assert hash(LT) == hash(LT2)

class TestInterpreted:

    def test_append_length(self):
        def f(x):
            l = []
            l.append(x)
            return len(l)
        res = interpret(f, [2], type_system="ootype")
        assert res == 1 

    def test_setitem_getitem(self):
        def f(x):
            l = []
            l.append(3)
            l[0] = x
            return l[0]
        res = interpret(f, [2], type_system="ootype")
        assert res == 2 

    def test_getitem_exception(self):
        def f(x):
            l = []
            l.append(x)
            try:
                return l[1]
            except IndexError:
                return -1
        res = interpret(f, [2], type_system="ootype")
        assert res == -1 

    def test_initialize(self):
        def f(x):
            l = [1, 2]
            l.append(x)
            return l[2]
        res = interpret(f, [3], type_system="ootype")
        assert res == 3 

    def test_initialize(self):
        def f(x):
            l = [1, 2]
            l.append(x)
            return l[2]
        res = interpret(f, [3], type_system="ootype")
        assert res == 3 

    def test_listtype_explosion(self):
        def f(x):
            l1 = [x]
            l2 = [x]
            return l1, l2 
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [int])
        typer = t.buildrtyper(type_system="ootype")
        typer.specialize()
        
        s_l1, s_l2 = s.items
        r_l1 = typer.getrepr(s_l1)
        r_l2 = typer.getrepr(s_l2)
        assert r_l1.lowleveltype == r_l2.lowleveltype 

    def test_tupletype_explosion(self):
        def f(x):
            t1 = ([x], [x, x])
            t2 = ([x, x], [x])
            return t1, t2 
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(f, [int])
        typer = t.buildrtyper(type_system="ootype")
        typer.specialize()
        
        s_t1, s_t2 = s.items
        r_t1 = typer.getrepr(s_t1)
        r_t2 = typer.getrepr(s_t2)
        assert r_t1.lowleveltype == r_t2.lowleveltype 

