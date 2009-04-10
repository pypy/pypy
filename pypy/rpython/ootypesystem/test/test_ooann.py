import py
from pypy.rpython.ootypesystem.ootype import *
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
import exceptions
from pypy.rpython.ootypesystem import ooregistry # side effects


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

def test_record():
    R = Record({'foo': Signed})
    r = new(R)
    
    def oof():
        return r

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    assert isinstance(s, annmodel.SomeOOInstance)
    assert s.ootype == R

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

def test_ooparse_int():
    def oof(n, b):
        return ooparse_int(oostring(n, b), b)

    a = RPythonAnnotator()
    s = a.build_types(oof, [int, int])
    assert isinstance(s, annmodel.SomeInteger)

def test_overloaded_meth():
    C = Instance("test", ROOT, {},
                 {'foo': overload(meth(Meth([Float], Void)),
                                  meth(Meth([Signed], Signed)),
                                  meth(Meth([], Float)))})
    def fn1():
        return new(C).foo(42.5)
    def fn2():
        return new(C).foo(42)
    def fn3():
        return new(C).foo()
    a = RPythonAnnotator()
    assert a.build_types(fn1, []) is annmodel.s_None
    assert isinstance(a.build_types(fn2, []), annmodel.SomeInteger)
    assert isinstance(a.build_types(fn3, []), annmodel.SomeFloat)

def test_bad_overload():
    def fn():
        C = Instance("test", ROOT, {},
                     {'foo': overload(meth(Meth([Signed], Void)),
                                      meth(Meth([Signed], Signed)))})
    py.test.raises(TypeError, fn)


def test_overload_reannotate():
    C = Instance("test", ROOT, {},
                 {'foo': overload(meth(Meth([Signed], Signed)),
                                  meth(Meth([Float], Float)))})
    def f():
        c = new(C)
        mylist = [42]
        a = c.foo(mylist[0])
        mylist.append(42.5)
        return a
    a = RPythonAnnotator()
    assert isinstance(a.build_types(f, []), annmodel.SomeFloat)
    
def test_overload_reannotate_unrelated():
    py.test.skip("Maybe we want this to work")
    # this test fails because the result type of c.foo(mylist[0])
    # changes completely after the list has been modified. We should
    # handle this case, but it's far from trival.
    C = Instance("test", ROOT, {},
                 {'foo': overload(meth(Meth([Signed], Void)),
                                  meth(Meth([Float], Float)))})
    def f():
        c = new(C)
        mylist = [42]
        a = c.foo(mylist[0])
        mylist.append(42.5)
        return a
    a = RPythonAnnotator()
    assert isinstance(a.build_types(f, []), annmodel.SomeFloat)

def test_overload_upcast():
    C = Instance("base", ROOT, {}, {
        'foo': overload(meth(Meth([], Void)),
                        meth(Meth([ROOT], Signed)))})
    def f():
        c = new(C)
        return c.foo(c)
    a = RPythonAnnotator()
    assert isinstance(a.build_types(f, []), annmodel.SomeInteger)

def test_overload_upcast_fail():
    C = Instance("base", ROOT, {}, {})
    C._add_methods({
        'foo': overload(meth(Meth([], Signed)),
                        meth(Meth([ROOT, C], Signed)),
                        meth(Meth([C, ROOT], Signed)))})
    def f():
        c = new(C)
        return c.foo(c)
    a = RPythonAnnotator()
    py.test.raises(TypeError, a.build_types, f, [])

def test_unicode_iterator():
    from pypy.rpython.ootypesystem import rstr
    ITER = rstr.UnicodeRepr.string_iterator_repr.lowleveltype

    def fn():
        it = new(ITER)
        return it.string
    a = RPythonAnnotator()
    res = a.build_types(fn, [])

    assert ITER._field_type("string") is Unicode
    assert isinstance(res, annmodel.SomeOOInstance)
    assert res.ootype is Unicode

def test_null_object():
    def fn():
        return NULL
    a = RPythonAnnotator()
    s = a.build_types(fn, [])
    assert type(s) is annmodel.SomeOOObject
