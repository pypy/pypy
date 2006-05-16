from pypy.rpython.ootypesystem.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
import exceptions


def test_simple_new():
    C = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        c = new(C)
        c.a = 5
        return c.a

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == int

def test_simple_instanceof():
    C = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        c = new(C)
        return instanceof(c, C)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == bool

def test_simple_null():
    I = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        i = null(I)
        return i

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeOOInstance(I)

def test_simple_classof():
    I = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        i = new(I)
        return classof(i)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeOOClass(I)

def test_subclassof():
    I = Instance("test", ROOT, {'a': Signed})
    I1 = Instance("test1", I) 
    
    def oof():
        i = new(I)
        i1 = new(I1)
        return subclassof(classof(i1), classof(i))

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeBool()

def test_simple_runtimenew():
    I = Instance("test", ROOT, {'a': Signed})
    
    def oof():
        i = new(I)
        c = classof(i)
        i2 = runtimenew(c)
        return i2

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeOOInstance(I)

def test_complex_runtimenew():
    I = Instance("test", ROOT, {'a': Signed})
    J = Instance("test2", I, {'b': Signed})
    K = Instance("test2", I, {'b': Signed})
    
    def oof(x):
        k = new(K)
        j = new(J)
        if x:
            c = classof(k)
        else:
            c = classof(j)
        i = runtimenew(c)
        return i

    a = RPythonAnnotator()
    s = a.build_types(oof, [bool])
    #a.translator.view()

    assert s == annmodel.SomeOOInstance(I)

def test_method():
    C = Instance("test", ROOT, {"a": (Signed, 3)})

    M = Meth([C], Signed)
    def m_(self, other):
       return self.a + other.a
    m = meth(M, _name="m", _callable=m_)

    addMethods(C, {"m": m})

    def oof():
        c = new(C)
        return c.m(c)
    
    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    # a.translator.view()

    assert s.knowntype == int

def test_unionof():
    C1 = Instance("C1", ROOT)
    C2 = Instance("C2", C1)
    C3 = Instance("C3", C1)

    def oof(f):
        if f:
            c = new(C2)
        else:
            c = new(C3)
        return c

    a = RPythonAnnotator()
    s = a.build_types(oof, [bool])
    #a.translator.view()

    assert s == annmodel.SomeOOInstance(C1)

def test_static_method():
    F = StaticMethod([Signed, Signed], Signed)
    def f_(a, b):
       return a+b
    f = static_meth(F, "f", _callable=f_)

    def oof():
        return f(2,3)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s.knowntype == int

def test_null_static_method():
    F = StaticMethod([Signed, Signed], Signed)

    def oof():
        return null(F)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    
    assert s == annmodel.SomeOOStaticMeth(F)

def test_truth_value():
    C = Instance("C", ROOT)
    def oof(f):
        if f:
            c = new(C)
        else:
            c = null(C)
        return not c

    a = RPythonAnnotator()
    s = a.build_types(oof, [bool])
    assert isinstance(s, annmodel.SomeBool)
    assert not s.is_constant()

def test_list():
    L = List(Signed)
    def oof():
        l = new(L)
        l._ll_resize(42)
        return l

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    #a.translator.view()

    assert s == annmodel.SomeOOInstance(L)

def test_string():
    def oof():
        return new(String)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    assert s == annmodel.SomeOOInstance(String)

def test_nullstring():
    def oof(b):
        if b:
            return 'foo'
        else:
            return None

    a = RPythonAnnotator()
    s = a.build_types(oof, [bool])
    assert s == annmodel.SomeString(can_be_None=True)

def test_oostring():
    def oof():
        return oostring

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    assert isinstance(s, annmodel.SomeBuiltin)
