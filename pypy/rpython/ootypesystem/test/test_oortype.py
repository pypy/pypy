
from pypy.rpython.ootypesystem.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.test_llinterp import interpret

def gengraph(f, args=[], viewBefore=False, viewAfter=False):
    t = TranslationContext()
    t.buildannotator().build_types(f, args)
    if viewBefore:
        t.view()
    t.buildrtyper(type_system="ootype").specialize()
    if viewAfter:
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

