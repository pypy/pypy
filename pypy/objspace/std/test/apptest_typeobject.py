from pytest import raises, skip


def test_abstract_methods():
    class X(object):
        pass
    X.__abstractmethods__ = ("meth",)
    raises(TypeError, X)
    del X.__abstractmethods__
    X()
    raises(AttributeError, getattr, type, "__abstractmethods__")
    with raises(TypeError): int.__abstractmethods__ = ('abc', )

def test_attribute_error():
    class X(object):
        __module__ = 'test'
    x = X()
    with raises(AttributeError) as exc: x.a
    assert str(exc.value) == "'X' object has no attribute 'a'"

def test_call_type():
    assert type(42) is int
    C = type('C', (object,), {'x': lambda: 42})
    unbound_meth = C.x
    raises(TypeError, unbound_meth)
    assert unbound_meth.im_func() == 42
    raises(TypeError, type)
    raises(TypeError, type, 'test', (object,))
    raises(TypeError, type, 'test', (object,), {}, 42)
    raises(TypeError, type, 42, (object,), {})
    raises(TypeError, type, 'test', 42, {})
    raises(TypeError, type, 'test', (object,), 42)

def test_call_type_subclass():
    class A(type):
        pass

    assert A("hello") is str

    # Make sure type(x) doesn't call x.__class__.__init__
    class T(type):
        counter = 0
        def __init__(self, *args):
            T.counter += 1
    class C:
        __metaclass__ = T
    assert T.counter == 1
    a = C()
    assert T.counter == 1
    assert type(a) is C
    assert T.counter == 1

def test_bases():
    assert int.__bases__ == (object,)
    class X:
        __metaclass__ = type
    assert X.__bases__ ==  (object,)
    class Y(X): pass
    assert Y.__bases__ ==  (X,)
    class Z(Y,X): pass
    assert Z.__bases__ ==  (Y, X)

    Z.__bases__ = (X,)
    #print Z.__bases__
    assert Z.__bases__ == (X,)

def test_mutable_bases():
    # from CPython's test_descr
    class C(object):
        pass
    class C2(object):
        def __getattribute__(self, attr):
            if attr == 'a':
                return 2
            else:
                return super(C2, self).__getattribute__(attr)
        def meth(self):
            return 1
    class D(C):
        pass
    class E(D):
        pass
    d = D()
    e = E()
    D.__bases__ = (C,)
    D.__bases__ = (C2,)
    assert d.meth() == 1
    assert e.meth() == 1
    assert d.a == 2
    assert e.a == 2
    assert C2.__subclasses__() == [D]

    # stuff that shouldn't:
    class L(list):
        pass

    try:
        L.__bases__ = (dict,)
    except TypeError:
        pass
    else:
        assert 0, "shouldn't turn list subclass into dict subclass"

    try:
        list.__bases__ = (dict,)
    except TypeError:
        pass
    else:
        assert 0, "shouldn't be able to assign to list.__bases__"

    try:
        D.__bases__ = (C2, list)
    except TypeError:
        pass
    else:
        assert 0, "best_base calculation found wanting"

    try:
        del D.__bases__
    except (TypeError, AttributeError):
        pass
    else:
        assert 0, "shouldn't be able to delete .__bases__"

    try:
        D.__bases__ = ()
    except TypeError as msg:
        if str(msg) == "a new-style class can't have only classic bases":
            assert 0, "wrong error message for .__bases__ = ()"
    else:
        assert 0, "shouldn't be able to set .__bases__ to ()"

    try:
        D.__bases__ = (D,)
    except TypeError:
        pass
    else:
        # actually, we'll have crashed by here...
        assert 0, "shouldn't be able to create inheritance cycles"

    try:
        D.__bases__ = (C, C)
    except TypeError:
        pass
    else:
        assert 0, "didn't detect repeated base classes"

    try:
        D.__bases__ = (E,)
    except TypeError:
        pass
    else:
        assert 0, "shouldn't be able to create inheritance cycles"

    # let's throw a classic class into the mix:
    class Classic:
        def meth2(self):
            return 3

    D.__bases__ = (C, Classic)

    assert d.meth2() == 3
    assert e.meth2() == 3
    try:
        d.a
    except AttributeError:
        pass
    else:
        assert 0, "attribute should have vanished"

    try:
        D.__bases__ = (Classic,)
    except TypeError:
        pass
    else:
        assert 0, "new-style class must have a new-style base"

def test_mutable_bases_with_failing_mro():
    class WorkOnce(type):
        def __new__(self, name, bases, ns):
            self.flag = 0
            return super(WorkOnce, self).__new__(WorkOnce, name, bases, ns)
        def mro(instance):
            if instance.flag > 0:
                raise RuntimeError("bozo")
            else:
                instance.flag += 1
                return type.mro(instance)

    class WorkAlways(type):
        def mro(self):
            # this is here to make sure that .mro()s aren't called
            # with an exception set (which was possible at one point).
            # An error message will be printed in a debug build.
            # What's a good way to test for this?
            return type.mro(self)

    class C(object):
        pass

    class C2(object):
        pass

    class D(C):
        pass

    class E(D):
        pass

    class F(D):
        __metaclass__ = WorkOnce

    class G(D):
        __metaclass__ = WorkAlways

    # Immediate subclasses have their mro's adjusted in alphabetical
    # order, so E's will get adjusted before adjusting F's fails.  We
    # check here that E's gets restored.

    E_mro_before = E.__mro__
    D_mro_before = D.__mro__

    try:
        D.__bases__ = (C2,)
    except RuntimeError:
        assert D.__mro__ == D_mro_before
        assert E.__mro__ == E_mro_before
    else:
        assert 0, "exception not propagated"

def test_mutable_bases_catch_mro_conflict():
    class A(object):
        pass

    class B(object):
        pass

    class C(A, B):
        pass

    class D(A, B):
        pass

    class E(C, D):
        pass

    try:
        C.__bases__ = (B, A)
    except TypeError:
        pass
    else:
        raise TestFailed("didn't catch MRO conflict")

def test_mutable_bases_versus_nonheap_types():
    class A(int):
        pass
    class B(int):
        __slots__ = ['b']
    class C(int):
        pass
    with raises(TypeError): C.__bases__ = (A,)
    with raises(TypeError): C.__bases__ = (B,)
    with raises(TypeError): C.__bases__ = (C,)
    with raises(TypeError): int.__bases__ = (object,)
    C.__bases__ = (int,)
    #--- the following raises on CPython but works on PyPy.
    #--- I don't see an obvious reason why it should fail...
    import sys
    if '__pypy__' not in sys.builtin_module_names:
        skip("works on PyPy only")
    class MostlyLikeInt(int):
        __slots__ = []
    C.__bases__ = (MostlyLikeInt,)

def test_mutable_bases_versus_slots():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = ['b1', 'b2']
    class C(B):
        pass
    with raises(TypeError): C.__bases__ = (A,)

def test_mutable_bases_versus_weakref():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = ['__weakref__']
    class C(B):
        pass
    with raises(TypeError): C.__bases__ = (A,)

def test_mutable_bases_same_slots():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = []
    class C(B):
        pass
    c = C()
    c.a = 42
    assert C.__mro__ == (C, B, A, object)
    C.__bases__ = (A,)
    assert C.__mro__ == (C, A, object)
    assert c.a == 42

def test_mutable_bases_versus_slots_2():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = ['b1', 'b2']
    class C(B):
        __slots__ = ['c']
    with raises(TypeError): C.__bases__ = (A,)

def test_mutable_bases_keeping_slots():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = []
    class C(B):
        __slots__ = ['c']
    c = C()
    c.a = 42
    c.c = 85
    assert C.__mro__ == (C, B, A, object)
    C.__bases__ = (A,)
    assert C.__mro__ == (C, A, object)
    assert c.a == 42
    assert c.c == 85

    class D(A):
        __slots__ = []
    C.__bases__ = (B, D)
    assert C.__mro__ == (C, B, D, A, object)
    assert c.a == 42
    assert c.c == 85
    with raises(TypeError):
        C.__bases__ = (B, D, B)

    class E(A):
        __slots__ = ['e']
    with raises(TypeError): C.__bases__ = (B, E)
    with raises(TypeError): C.__bases__ = (E, B)
    with raises(TypeError): C.__bases__ = (E,)

def test_compatible_slot_layout():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = ['b1', 'b2']
    class C(A):
        pass
    class D(B, C):    # assert does not raise TypeError
        pass

def test_builtin_add():
    x = 5
    assert x.__add__(6) == 11
    x = 3.5
    assert x.__add__(2) == 5.5
    assert x.__add__(2.0) == 5.5

def test_builtin_call():
    def f(*args):
        return args
    assert f.__call__() == ()
    assert f.__call__(5) == (5,)
    assert f.__call__("hello", "world") == ("hello", "world")

def test_builtin_call_kwds():
    def f(*args, **kwds):
        return args, kwds
    assert f.__call__() == ((), {})
    assert f.__call__("hello", "world") == (("hello", "world"), {})
    assert f.__call__(5, bla=6) == ((5,), {"bla": 6})
    assert f.__call__(a=1, b=2, c=3) == ((), {"a": 1, "b": 2, "c": 3})

def test_multipleinheritance_fail():
    try:
        class A(int, dict):
            pass
    except TypeError:
        pass
    else:
        raise AssertionError("this multiple inheritance should fail")

def test_outer_metaclass():
    class OuterMetaClass(type):
        pass

    class HasOuterMetaclass(object):
        __metaclass__ = OuterMetaClass

    assert type(HasOuterMetaclass) == OuterMetaClass
    assert type(HasOuterMetaclass) == HasOuterMetaclass.__metaclass__

def test_inner_metaclass():
    class HasInnerMetaclass(object):
        class __metaclass__(type):
            pass

    assert type(HasInnerMetaclass) == HasInnerMetaclass.__metaclass__

def test_implicit_metaclass():
    class __metaclass__(type):
        pass

    g = {'__metaclass__': __metaclass__}
    exec "class HasImplicitMetaclass: pass\n" in g

    HasImplicitMetaclass = g['HasImplicitMetaclass']
    assert type(HasImplicitMetaclass) == __metaclass__

def test_mro():
    class A_mro(object):
        a = 1

    class B_mro(A_mro):
        b = 1
        class __metaclass__(type):
            def mro(self):
                return [self, object]

    assert B_mro.__bases__ == (A_mro,)
    assert B_mro.__mro__ == (B_mro, object)
    assert B_mro.mro() == [B_mro, object]
    assert B_mro.b == 1
    assert B_mro().b == 1
    assert getattr(B_mro, 'a', None) == None
    assert getattr(B_mro(), 'a', None) == None
    # also check what the built-in mro() method would return for 'B_mro'
    assert type.mro(B_mro) == [B_mro, A_mro, object]

def test_mro_mutation_interaction_bug():
    class Base(object):
        value = 1

    class WeirdClass(object):
        class __metaclass__(type):
            def mro(cls):
                return (cls, Base, object)

    assert Base.value == 1
    assert WeirdClass.value == 1

    Base.value = 2
    assert Base.value == 2
    assert WeirdClass.value == 2

    Base.value = 3
    assert Base.value == 3
    assert WeirdClass.value == 3

    assert len(Base.__subclasses__()) == 0

def test_abstract_mro():
    class A1:    # old-style class
        pass
    class B1(A1):
        pass
    class C1(A1):
        pass
    class D1(B1, C1):
        pass
    class E1(D1, object):
        __metaclass__ = type
    # old-style MRO in the classical part of the parent hierarchy
    assert E1.__mro__ == (E1, D1, B1, A1, C1, object)

def test_nodoc():
    class NoDoc(object):
        pass

    try:
        assert NoDoc.__doc__ == None
    except AttributeError:
        raise AssertionError("__doc__ missing!")

def test_explicitdoc():
    class ExplicitDoc(object):
        __doc__ = 'foo'

    assert ExplicitDoc.__doc__ == 'foo'

def test_implicitdoc():
    class ImplicitDoc(object):
        "foo"

    assert ImplicitDoc.__doc__ == 'foo'

def test_immutabledoc():
    class ImmutableDoc(object):
        "foo"

    try:
        ImmutableDoc.__doc__ = "bar"
    except TypeError:
        pass
    except AttributeError:
        # XXX - Python raises TypeError for several descriptors,
        #       we always raise AttributeError.
        pass
    else:
        raise AssertionError('__doc__ should not be writable')

    assert ImmutableDoc.__doc__ == 'foo'

def test_metaclass_conflict():
    class T1(type):
        pass
    class T2(type):
        pass
    class D1:
        __metaclass__ = T1
    class D2:
        __metaclass__ = T2
    def conflict():
        class C(D1,D2):
            pass
    raises(TypeError, conflict)

def test_metaclass_choice():
    events = []

    class T1(type):
        def __new__(*args):
            events.append(args)
            return type.__new__(*args)

    class D1:
        __metaclass__ = T1

    class C(D1):
        pass

    class F(object):
        pass

    class G(F,D1):
        pass

    assert len(events) == 3
    assert type(D1) is T1
    assert type(C) is T1
    assert type(G) is T1

def test_descr_typecheck():
    raises(TypeError,type.__dict__['__name__'].__get__,1)
    raises(TypeError,type.__dict__['__mro__'].__get__,1)

def test_slots_simple():
    class A(object):
        __slots__ = ('x',)
    a = A()
    raises(AttributeError, getattr, a, 'x')
    raises(AttributeError, delattr, a, 'x')
    a.x = 1
    assert a.x == 1
    assert A.__dict__['x'].__get__(a) == 1
    del a.x
    raises(AttributeError, getattr, a, 'x')
    raises(AttributeError, delattr, a, 'x')
    class B(A):
        pass
    b = B()
    raises(AttributeError, getattr, b, 'x')
    raises(AttributeError, delattr, b, 'x')
    b.x = 1
    assert b.x == 1
    assert A.__dict__['x'].__get__(b) == 1
    del b.x
    raises(AttributeError, getattr, b, 'x')
    raises(AttributeError, delattr, b, 'x')
    class Z(object):
        pass
    z = Z()
    raises(TypeError, A.__dict__['x'].__get__, z)
    raises(TypeError, A.__dict__['x'].__set__, z, 1)
    raises(TypeError, A.__dict__['x'].__delete__, z)

def test_slot_mangling():
    class A(object):
        __slots__ = ('x', '__x','__xxx__','__','__dict__')
    a = A()
    assert '__dict__' in A.__dict__
    assert '__' in A.__dict__
    assert '__xxx__' in A.__dict__
    assert 'x' in A.__dict__
    assert '_A__x' in A.__dict__
    a.x = 1
    a._A__x = 2
    a.__xxx__ = 3
    a.__ = 4
    assert a.x == 1
    assert a._A__x == 2
    assert a.__xxx__ == 3
    assert a.__ == 4
    assert a.__dict__ == {}

def test_slots_multiple_inheritance():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = []
    class E(A):
        __slots__ = ['e']
    class C(B, E):
        pass
    c = C()
    c.a = 42
    c.e = 85
    assert c.a == 42
    assert c.e == 85

def test_string_slots():
    class A(object):
        __slots__ = "abc"

    class B(object):
        __slots__ = u"abc"

    a = A()
    a.abc = "awesome"
    assert a.abc == "awesome"
    b = B()
    b.abc = "awesomer"
    assert b.abc == "awesomer"

def test_base_attr():
    # check the '__base__'
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = []
    class E(A):
        __slots__ = ['e']
    class C(B, E):
        pass
    class D(A):
        __slots__ = []
    class F(B, D):
        pass
    assert C.__base__ is E
    assert F.__base__ is B
    assert bool.__base__ is int
    assert int.__base__ is object
    assert object.__base__ is None

def test_cannot_subclass():
    raises(TypeError, type, 'A', (bool,), {})

def test_slot_conflict():
    class A(object):
        __slots__ = ['a']
    class B(A):
        __slots__ = ['b']
    class E(A):
        __slots__ = ['e']
    with raises(TypeError):
        type('C', (B, E), {})

def test_repr():
    globals()['__name__'] = 'a'
    class A(object):
        pass
    assert repr(A) == "<class 'a.A'>"
    A.__module__ = 123
    assert repr(A) == "<class 'A'>"
    assert repr(type(type)) == "<type 'type'>"
    assert repr(complex) == "<type 'complex'>"
    assert repr(property) == "<type 'property'>"
    assert repr(TypeError) == "<type 'exceptions.TypeError'>"

def test_repr_issue1292():
    d = {'object': object}    # no __name__
    exec "class A(object): pass\n" in d
    assert d['A'].__module__ == '__builtin__'    # obscure, follows CPython
    assert repr(d['A']) == "<class 'A'>"

def test_invalid_mro():
    class A(object):
        pass
    with raises(TypeError):
        class B(A, A): pass
    class C(A):
        pass
    with raises(TypeError):
        class D(A, C): pass

def test_data_descriptor_without_get():
    class Descr(object):
        def __init__(self, name):
            self.name = name
        def __set__(self, obj, what):
            pass
    class Meta(type):
        pass
    class X(object):
        __metaclass__ = Meta
    X.a = 42
    Meta.a = Descr("a")
    assert X.a == 42

def test_user_defined_mro_cls_access():
    d = []
    class T(type):
        def mro(cls):
            d.append(cls.__dict__)
            return type.mro(cls)
    class C:
        __metaclass__ = T
    assert d
    assert sorted(d[0].keys()) == ['__dict__','__doc__','__metaclass__','__module__', '__weakref__']
    d = []
    class T(type):
        def mro(cls):
            try:
                cls.x()
            except AttributeError:
                d.append('miss')
            return type.mro(cls)
    class C:
        def x(cls):
            return 1
        x = classmethod(x)
        __metaclass__ = T
    assert d == ['miss']
    assert C.x() == 1

def test_only_classic_bases_fails():
    class C:
        pass
    raises(TypeError, type, 'D', (C,), {})

def test_set___class__():
    with raises(TypeError):
        1 .__class__ = int
    with raises(TypeError):
        1 .__class__ = bool
    class A(object):
        pass
    class B(object):
        pass
    a = A()
    a.__class__ = B
    assert a.__class__ == B
    class A(object):
        __slots__ = ('a',)
    class B(A):
        pass
    class C(B):
        pass
    class D(A):
        pass
    d = D()
    d.__class__ = C
    assert d.__class__ == C
    d.__class__ = B
    assert d.__class__ == B
    with raises(TypeError):
        d.__class__ = A
    d.__class__ = C
    assert d.__class__ == C
    d.__class__ = D
    assert d.__class__ == D
    class AA(object):
        __slots__ = ('a',)
    aa = AA()
    aa.__class__ = A
    with raises(TypeError):
        aa.__class__ = object
    class Z1(A):
        pass
    class Z2(A):
        __slots__ = ['__dict__', '__weakref__']
    z1 = Z1()
    z1.__class__ = Z2
    assert z1.__class__ == Z2
    z2 = Z2()
    z2.__class__ = Z1
    assert z2.__class__ == Z1

    class I(int):
        pass
    class F(float):
        pass
    f = F()
    with raises(TypeError):
        f.__class__ = I
    i = I()
    with raises(TypeError):
        i.__class__ = F
    with raises(TypeError):
        i.__class__ = int

    class I2(int):
        pass
    class I3(I2):
        __slots__ = ['a']
    class I4(I3):
        pass

    i = I()
    i2 = I()
    i.__class__ = I2
    i2.__class__ = I
    assert i.__class__ ==  I2
    assert i2.__class__ == I

    i3 = I3()
    raises(TypeError, "i3.__class__ = I2")
    i3.__class__ = I4
    assert i3.__class__ == I4
    i3.__class__ = I3
    assert i3.__class__ == I3

    class X(object):
        pass
    class Y(object):
        __slots__ = ()
    with raises(TypeError):
        X().__class__ = Y
    with raises(TypeError):
        Y().__class__ = X

    with raises(TypeError):
        X().__class__ = object
    with raises(TypeError):
        X().__class__ = 1

    class Int(int): __slots__ = []

    with raises(TypeError):
        Int().__class__ = int

    class Order1(object):
        __slots__ = ['a', 'b']
    class Order2(object):
        __slots__ = ['b', 'a']
    Order1().__class__ = Order2

    # like CPython, the order of slot names doesn't matter
    x = Order1()
    x.a, x.b = 1, 2
    x.__class__ = Order2
    assert (x.a, x.b) == (1, 2)

    class U1(object):
        __slots__ = ['a', 'b']
    class U2(U1):
        __slots__ = ['c', 'd', 'e']
    class V1(object):
        __slots__ = ['a', 'b']
    class V2(V1):
        __slots__ = ['c', 'd', 'e']
    # the following line does not work on CPython either: we can't
    # change a class if the old and new class have different layouts
    # that look compatible but aren't, because they don't have the
    # same base-layout class (even if these base classes are
    # themselves compatible)...  obscure.
    with raises(TypeError):
        U2().__class__ = V2

def test_name():
    class Abc(object):
        pass
    assert Abc.__name__ == 'Abc'
    Abc.__name__ = 'Def'
    assert Abc.__name__ == 'Def'
    with raises(TypeError):
        Abc.__name__ = 42
    with raises(TypeError):
        Abc.__name__ = u'A'
    try:
        Abc.__name__ = 'G\x00hi'
    except ValueError as e:
        assert str(e) == "type name must not contain null characters"
    else:
        assert False

def test_compare():
    class A(object):
        pass
    class B(A):
        pass
    A.__eq__
    A.__ne__
    assert A.__eq__(A)
    assert not A.__eq__(B)
    assert A.__ne__(B)
    assert not A.__ne__(A)
    assert A == A
    assert A != B
    assert not A == B
    assert not A != A

def test_class_variations():
    class A(object):
        pass
    assert '__dict__' in A.__dict__
    a = A()
    a.x = 3
    assert a.x == 3

    class A(object):
        __slots__ = ()
    assert '__dict__' not in A.__dict__
    a = A()
    raises(AttributeError, setattr, a, 'x', 3)

    class B(A):
        pass
    assert '__dict__' in B.__dict__
    b = B()
    b.x = 3
    assert b.x == 3

    import sys
    class A(type(sys)):
        pass
    assert '__dict__' not in A.__dict__
    a = A("a")
    a.x = 3
    assert a.x == 3

    class A(type(sys)):
        __slots__ = ()
    assert '__dict__' not in A.__dict__
    a = A("a")
    a.x = 3
    assert a.x == 3

    class B(A):
        pass
    assert '__dict__' not in B.__dict__
    b = B("b")
    b.x = 3
    assert b.x == 3

def test_immutable_builtin():
    raises(TypeError, setattr, list, 'append', 42)
    raises(TypeError, setattr, list, 'foobar', 42)
    raises(TypeError, delattr, dict, 'keys')
    with raises(TypeError):
        int.__dict__["a"] = 1

def test_nontype_in_mro():
    class OldStyle:
        pass
    class X(object):
        pass

    class mymeta1(type):
        def mro(self):
            return [self, OldStyle, object]
    mymeta1("Foo1", (object,), {})      # works

    class mymeta2(type):
        def mro(self):
            return [self, X(), object]
    raises(TypeError, mymeta2, "Foo", (object,), {})

def test_init_must_return_none():
    class X(object):
        def __init__(self):
            return 0
    raises(TypeError, X)

def test_dictproxy_is_updated():
    class A(object):
        x = 1
    d = A.__dict__
    assert d["x"] == 1
    A.y = 2
    assert d["y"] == 2
    assert ("x", 1) in d.items()
    assert ("y", 2) in d.items()

def test_type_descriptors_overridden():
    class A(object):
        __dict__ = 42
    assert A().__dict__ == 42
    #
    class B(object):
        __weakref__ = 42
    assert B().__weakref__ == 42

def test_change_dict():
    class A(object):
        pass

    a = A()
    A.x = 1
    assert A.__dict__["x"] == 1
    with raises(AttributeError):
        del A.__dict__
    with raises((AttributeError, TypeError)):
        A.__dict__ = {}

def test_mutate_dict():
    class A(object):
        pass

    a = A()
    d = A.__dict__
    A.x = 1
    assert d["x"] == 1

def test_we_already_got_one_1():
    # Issue #2079: highly obscure: CPython complains if we say
    # ``__slots__="__dict__"`` and there is already a __dict__...
    # but from the "best base" only.  If the __dict__ comes from
    # another base, it doesn't complain.  Shrug and copy the logic.
    class A(object):
        __slots__ = ()
    class B(object):
        pass
    class C(A, B):     # "best base" is A
        __slots__ = ("__dict__",)
    class D(A, B):     # "best base" is A
        __slots__ = ("__weakref__",)
    try:
        class E(B, A):   # "best base" is B
            __slots__ = ("__dict__",)
    except TypeError as e:
        assert 'we already got one' in str(e)
    else:
        raise AssertionError("TypeError not raised")
    try:
        class F(B, A):   # "best base" is B
            __slots__ = ("__weakref__",)
    except TypeError as e:
        assert 'we already got one' in str(e)
    else:
        raise AssertionError("TypeError not raised")

def test_we_already_got_one_2():
    class A(object):
        __slots__ = ()
    class B:
        pass
    class C(A, B):     # "best base" is A
        __slots__ = ("__dict__",)
    class D(A, B):     # "best base" is A
        __slots__ = ("__weakref__",)
    class C(B, A):     # "best base" is A
        __slots__ = ("__dict__",)
    class D(B, A):     # "best base" is A
        __slots__ = ("__weakref__",)

def test_crash_mro_without_object_1():
    class X(type):
        def mro(self):
            return [self]
    class C:
        __metaclass__ = X
    e = raises(TypeError, C)     # the lookup of '__new__' fails
    assert str(e.value) == "cannot create 'C' instances"

def test_crash_mro_without_object_2():
    class X(type):
        def mro(self):
            return [self, int]
    class C(int):
        __metaclass__ = X
    C()    # the lookup of '__new__' succeeds in 'int',
           # but the lookup of '__init__' fails

def test_instancecheck():
    assert int.__instancecheck__(42) is True
    assert int.__instancecheck__(42.0) is False
    class Foo:
        __class__ = int
    assert int.__instancecheck__(Foo()) is False
    class Bar(object):
        __class__ = int
    assert int.__instancecheck__(Bar()) is True

def test_subclasscheck():
    assert int.__subclasscheck__(bool) is True
    assert int.__subclasscheck__(float) is False
    class Foo:
        __class__ = int
    assert int.__subclasscheck__(Foo) is False
    class Bar(object):
        __class__ = int
    assert int.__subclasscheck__(Bar) is False
    class AbstractClass(object):
        __bases__ = (int,)
    assert int.__subclasscheck__(AbstractClass()) is True

def test_bad_args():
    import UserDict
    raises(TypeError, type, 'A', (), dict={})
    raises(TypeError, type, 'A', [], {})
    raises(TypeError, type, 'A', (), UserDict.UserDict())
    raises(ValueError, type, 'A\x00B', (), {})
    raises(TypeError, type, u'A', (), {})

def test_reset_logic():
    class X(object):
        pass

    class Y(X):
        pass

    y = Y()
    y.x = 3
    assert y.x == 3

    def ga(self, name):
        return 'GA'

    X.__getattribute__ = ga

    assert y.x == 'GA'

    class M(type):
        pass

    class X(object):
        __metaclass__ = M

    class Y(X):
        pass

    y = Y()
    y.x = 3
    assert y.x == 3

    def ga2(self, name):
        return 'GA2'

    X.__getattribute__ = ga2

    assert y.x == 'GA2'
