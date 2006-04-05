from pypy import conftest
from pypy.rpython.ootypesystem.ootype import *
from pypy.rpython.ootypesystem.rlist import ListRepr
from pypy.rpython.rint import signed_repr
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.test_llinterp import interpret

def gengraph(f, args=[], viewBefore=False, viewAfter=False):
    t = TranslationContext()
    t.buildannotator().build_types(f, args)
    if viewBefore or conftest.option.view:
        t.view()
    t.buildrtyper(type_system="ootype").specialize()
    if viewAfter or conftest.option.view:
        t.view()
    return graphof(t, f)

def test_simple_class():
    C = Instance("test", ROOT, {'a': Signed})
    
    def f():
        c = new(C)
        return c

    g = gengraph(f)
    rettype = g.getreturnvar().concretetype
    assert rettype == C
    
def test_simple_field():
    C = Instance("test", ROOT, {'a': (Signed, 3)})
    
    def f():
        c = new(C)
        c.a = 5
        return c.a

    g = gengraph(f)
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed
    
def test_simple_method():
    C = Instance("test", ROOT, {'a': (Signed, 3)})
    M = Meth([], Signed)
    def m_(self):
       return self.a
    m = meth(M, _name="m", _callable=m_)
    addMethods(C, {"m": m})
    
    def f():
        c = new(C)
        return c.m()

    g = gengraph(f)
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

def test_truth_value():
    C = Instance("C", ROOT)
    NULL = null(C)
    def oof(f):
        if f:
            c = new(C)
        else:
            c = NULL
        return not c

    g = gengraph(oof, [bool])
    rettype = g.getreturnvar().concretetype
    assert rettype == Bool

    res = interpret(oof, [True], type_system='ootype')
    assert res is False
    res = interpret(oof, [False], type_system='ootype')
    assert res is True

def test_simple_classof():
    I = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        i = new(I)
        return classof(i)

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Class

def test_subclassof():
    I = Instance("test", ROOT, {'a': Signed})
    I1 = Instance("test1", I) 
    
    def oof():
        i = new(I)
        i1 = new(I1)
        return subclassof(classof(i1), classof(i))

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Bool

def test_list_len():
    LT = List(Signed)

    def oof():
        l = new(LT)
        return l.length()

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

def test_list_append():
    LT = List(Signed)

    def oof():
        l = new(LT)
        l.append(1)
        return l.length()

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

def test_list_getitem_setitem():
    LT = List(Signed)

    def oof():
        l = new(LT)
        l.append(1)
        l.setitem(0, 2)
        return l.getitem(0)

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

def test_list_getitem_exceptions():
    LT = List(Signed)

    def oof():
        l = new(LT)
        try:
            l.getitem(0)
        except IndexError:
            return -1
        return 0

    res = interpret(oof, [], type_system='ootype')
    assert res is -1

def test_list_lltype_identity():
    t = TranslationContext()
    t.buildannotator()
    rtyper = t.buildrtyper()
    repr1 = ListRepr(rtyper, signed_repr)
    repr2 = ListRepr(rtyper, signed_repr)
    assert repr1.lowleveltype == repr2.lowleveltype
    assert hash(repr1.lowleveltype) == hash(repr2.lowleveltype)

def test_list_annotation():
    LIST = List(Signed)

    def oof(lst):
        return lst.length()

    lst = new(LIST)
    lst.append(1)
    res = interpret(oof, [lst], type_system='ootype')
    assert res == 1
