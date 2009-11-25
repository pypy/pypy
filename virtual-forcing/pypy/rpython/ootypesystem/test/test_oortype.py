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

def test_method_wrapper():
    L = List(Signed)
    _, meth = L._lookup('ll_getitem_fast')
    wrapper = build_unbound_method_wrapper(meth)

    def fn():
        lst = L.ll_newlist(1)
        lst.ll_setitem_fast(0, 42)
        return wrapper(lst, 0)
    
    res = interpret(fn, [], type_system='ootype')
    assert res == 42

def test_identityhash():
    L = List(Signed)

    def fn():
        lst1 = new(L)
        lst2 = new(L)
        obj1 = cast_to_object(lst1)
        obj2 = cast_to_object(lst2)
        return identityhash(obj1) == identityhash(obj2)

    res = interpret(fn, [], type_system='ootype')
    assert not res

def test_mix_class_record_instance():
    I = Instance("test", ROOT, {"a": Signed})
    R = Record({"x": Signed})
    L = List(Signed)

    c1 = runtimeClass(I)
    c2 = runtimeClass(R)
    c3 = runtimeClass(L)
    c4 = runtimeClass(Class)
    def fn(flag):
        if flag == 0:
            return c1
        elif flag == 1:
            return c2
        elif flag == 2:
            return c3
        else:
            return c4

    res = interpret(fn, [0], type_system='ootype')
    assert res is c1
    res = interpret(fn, [1], type_system='ootype')
    assert res is c2
    res = interpret(fn, [2], type_system='ootype')
    assert res is c3
    res = interpret(fn, [3], type_system='ootype')
    assert res is c4

def test_immutable_hint():
    class I(object):
        _immutable_ = True

    i = I()
    def f():
        return i

    g = gengraph(f)
    rettype = g.getreturnvar().concretetype
    assert rettype._hints['immutable']


def test_compare_classes():
    A = ootype.Instance("A", ootype.ROOT)
    B = ootype.Instance("B", ootype.ROOT)

    cls1 = ootype.runtimeClass(A)
    def fn(n):
        if n:
            cls2 = ootype.runtimeClass(A)
        else:
            cls2 = ootype.runtimeClass(B)

        assert (cls1 == cls2) == (not (cls1 != cls2))
        return cls1 == cls2

    res = interpret(fn, [1], type_system='ootype')
    assert res


def test_boundmeth_callargs():
    A = Instance("A", ROOT, {'a': (Signed, 3)})
    M = Meth([Signed, Signed], Signed)
    def m_(self, x, y):
       return self.a + x + y
    m = meth(M, _name="m", _callable=m_)
    addMethods(A, {"m": m})

    def fn(x, y):
        a = ootype.new(A)
        meth = a.m
        args = (x, y)
        return meth(*args)

    res = interpret(fn, [4, 5], type_system='ootype')
    assert res == 3+4+5

def test_boundmeth_callargs_stritem_nonneg():
    def fn(i):
        s = ootype.oostring(42, -1)
        meth = s.ll_stritem_nonneg
        args = (i,)
        return meth(*args)

    res = interpret(fn, [0], type_system='ootype')
    assert res == '4'

def test_bool_class():
    A = Instance("Foo", ROOT)
    cls = runtimeClass(A)
    def fn(x):
        if x:
            obj = cls
        else:
            obj = nullruntimeclass
        return bool(obj)

    res = interpret(fn, [0], type_system='ootype')
    assert not res
    res = interpret(fn, [1], type_system='ootype')
    assert res

def test_cast_to_object_nullruntimeclass():
    def fn():
        return cast_to_object(nullruntimeclass)

    res = interpret(fn, [], type_system='ootype')
    assert cast_from_object(Class, res) == nullruntimeclass

def test_cast_to_object_static_meth():
    from pypy.rpython.annlowlevel import llhelper
    FUNC = StaticMethod([Signed], Signed)
    def f(x):
        return x+1
    fptr = llhelper(FUNC, f)

    def fn(x):
        if x:
            obj = cast_to_object(fptr)
        else:
            obj = NULL
        myfunc = cast_from_object(FUNC, obj)
        return myfunc(x)

    res = interpret(fn, [1], type_system='ootype')
    assert res == 2

def test_instanceof():
    A = Instance('A', ootype.ROOT, {})
    B = Instance('B', A, {})

    def fn(x):
        if x:
            obj = ooupcast(A, new(B))
        else:
            obj = new(A)
        return instanceof(obj, B)

    res = interpret(fn, [0], type_system='ootype')
    assert not res
    res = interpret(fn, [1], type_system='ootype')
    assert res
