import py
from pypy import conftest
from pypy.rpython.ootypesystem.ootype import *
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rlist import ListRepr
from pypy.rpython.rint import signed_repr
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.objectmodel import r_dict
from pypy.tool.error import AnnotatorError
from pypy.rpython.ootypesystem import ooregistry # side effects

def gengraph(f, args=[], viewBefore=False, viewAfter=False, mangle=True):
    t = TranslationContext()
    t.config.translation.ootype.mangle = mangle
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
        return l.ll_length()

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

##def test_list_append():
##    LT = List(Signed)

##    def oof():
##        l = new(LT)
##        l.append(1)
##        return l.ll_length()

##    g = gengraph(oof, [])
##    rettype = g.getreturnvar().concretetype
##    assert rettype == Signed

def test_list_getitem_setitem():
    LT = List(Signed)

    def oof():
        l = new(LT)
        l._ll_resize(1)
        l.ll_setitem_fast(0, 2)
        return l.ll_getitem_fast(0)

    g = gengraph(oof, [])
    rettype = g.getreturnvar().concretetype
    assert rettype == Signed

def test_list_getitem_exceptions():
    LT = List(Signed)

    def oof():
        l = new(LT)
        try:
            l.ll_getitem_fast(0)
        except IndexError:
            return -1
        return 0

    res = interpret(oof, [], type_system='ootype')
    assert res is -1

def test_list_annotation():
    LIST = List(Signed)

    def oof(lst):
        return lst.ll_length()

    lst = new(LIST)
    lst._ll_resize(1)
    res = interpret(oof, [lst], type_system='ootype')
    assert res == 1

def test_ootypeintro():

    class A:
        def method(self, number):
            return number + 2
    
    def oof():
        a = A()
        return a.method(3)

    res = interpret(oof, [], type_system='ootype')

def test_is_exception_instance():
    def f():
        return NameError()

    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    if conftest.option.view:
        t.view()
    rtyper = t.buildrtyper(type_system="ootype")
    rtyper.specialize()
    graph = graphof(t, f) 
    
    INST = graph.getreturnvar().concretetype
    assert rtyper.exceptiondata.is_exception_instance(INST)

def test_string_annotation():
    def oof(lst):
        return lst.ll_strlen()

    s = new(String)
    assert interpret(oof, [s], type_system='ootype') == 0
    s = make_string('foo')
    assert interpret(oof, [s], type_system='ootype') == 3

def test_oostring():
    def oof(ch):
        return oostring(ch, -1)

    ch = 'a'
    res = interpret(oof, [ch], type_system='ootype')
    assert res._str == 'a'

def test_nullstring():
    def oof(b):
        if b:
            return 'foo'
        else:
            return None

    res = interpret(oof, [False], type_system='ootype')
    assert isinstance(res, ootype._null_string)

def test_assert():
    def oof(b):
        assert b

    interpret(oof, [True], type_system='ootype')

def test_ooparse_int():
    def oof(n, b):
        return ooparse_int(oostring(n, b), b)

    for n in -42, 0, 42:
        for b in 8, 10, 16:
            assert interpret(oof, [n, b], type_system='ootype') == n

def test_OSError():
    def oof(b):
        try:
            if b:
                raise OSError
            else:
                return 1
        except OSError:
            return 2

    assert interpret(oof, [True], type_system='ootype') == 2
    assert interpret(oof, [False], type_system='ootype') == 1

def test_r_dict():
    def strange_key_eq(key1, key2):
        return key1[0] == key2[0]   # only the 1st character is relevant
    def strange_key_hash(key):
        return ord(key[0])
    def oof():
        d = r_dict(strange_key_eq, strange_key_hash)
        d['x'] = 42
        return d['x']
    assert interpret(oof, [], type_system='ootype') == 42

def test_r_dict_bm():
    class Strange:
        def key_eq(strange, key1, key2):
            return key1[0] == key2[0]   # only the 1st character is relevant
        def key_hash(strange, key):
            return ord(key[0])

    def oof():
        strange = Strange()
        d = r_dict(strange.key_eq, strange.key_hash)
        d['x'] = 42
        return d['x']
    assert interpret(oof, [], type_system='ootype') == 42

def test_not_mangle_attrs():
    class Foo:
        def __init__(self):
            self.x = 42
    def fn():
        return Foo()

    graph = gengraph(fn, mangle=False)
    FOO = graph.getreturnvar().concretetype
    assert FOO._fields.keys() == ['x']

    class Bar:
        def __init__(self):
            self.meta = 42
    def fn():
        return Bar()
    py.test.raises(AssertionError, gengraph, fn, mangle=False)

def test_pbc_record():
    R = Record({'foo': Signed})
    r = new(R)
    r.foo = 42

    def oof():
        return r.foo
    
    res = interpret(oof, [], type_system='ootype')
    assert res == 42

def test_ooupcast():
    A = Instance('A', ootype.ROOT, {})
    B = Instance('B', A, {})
    C = Instance('C', ootype.ROOT)

    def fn():
        b = new(B)
        return ooupcast(A, b)

    res = interpret(fn, [], type_system='ootype')
    assert typeOf(res) is A

    def fn():
        c = new(C)
        return ooupcast(A, c)

    py.test.raises(AnnotatorError, interpret, fn, [], type_system='ootype')

def test_oodowncast():
    A = Instance('A', ootype.ROOT, {})
    B = Instance('B', A, {})
    C = Instance('C', ootype.ROOT)

    def fn():
        b = new(B)
        a = ooupcast(A, b)
        return oodowncast(B, a)

    res = interpret(fn, [], type_system='ootype')
    assert typeOf(res) is B

    def fn():
        c = new(C)
        return oodowncast(A, c)

    py.test.raises(AnnotatorError, interpret, fn, [], type_system='ootype')
