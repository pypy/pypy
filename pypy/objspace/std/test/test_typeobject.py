from pypy.objspace.std.model import W_Object
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.conftest import gettestobjspace

from pypy.objspace.std.typeobject import W_TypeObject
from pypy.interpreter.gateway import interp2app
import py

class TestTypeObject:

    def test_not_acceptable_as_base_class(self):
        space = self.space
        class W_Stuff(W_Object):
            pass
        def descr__new__(space, w_subtype):
            return space.allocate_instance(W_Stuff, w_subtype)
        W_Stuff.typedef = StdTypeDef("stuff",
                                     __new__ = interp2app(descr__new__))
        W_Stuff.typedef.acceptable_as_base_class = False
        w_stufftype = space.gettypeobject(W_Stuff.typedef)
        space.appexec([w_stufftype], """(stufftype):
            x = stufftype.__new__(stufftype)
            assert type(x) is stufftype
            raises(TypeError, stufftype.__new__)
            raises(TypeError, stufftype.__new__, int)
            raises(TypeError, stufftype.__new__, 42)
            raises(TypeError, stufftype.__new__, stufftype, 511)
            raises(TypeError, type, 'sub', (stufftype,), {})
        """)

    def test_del_warning(self):
        warnings = []
        def my_warn(msg, warningscls):
            warnings.append(msg)
            prev_warn(msg, warningscls)
        space = self.space
        prev_warn = space.warn
        try:
            space.warn = my_warn
            space.appexec([], """():
                class X(object):
                    pass
                X.__del__ = 5
                X.__del__ = 6
                X.__del__ = 7
                class Y(object):
                    pass
                Y.__del__ = 8
                Y.__del__ = 9
                Y.__del__ = 0
                class Z(object):
                    pass
                Z._foobar_ = 3
                Z._foobar_ = 4
                class U(object):
                    def __del__(self):
                        pass
                U.__del__ = lambda self: 42     # no warning here
            """)
        finally:
            space.warn = prev_warn
        assert len(warnings) == 2

    def test_metaclass_typedef(self):
        py.test.skip("Not implemented yet")

        # Define a metaclass
        class W_MyMetaclass(W_TypeObject):
            def f(w_self, space):
                return space.wrap(42)

        W_MyMetaclass.typedef = StdTypeDef(
            "MyMeta",
            W_TypeObject.typedef,
            f=interp2app(W_MyMetaclass.f, unwrap_spec=["self", ObjSpace]),
            )

        # Define a type, instance of the above metaclass
        class W_MyType(Wrappable):
            pass

        def MyType_descr_new(space, w_cls):
            return space.wrap(W_MyType())

        W_MyType.typedef = StdTypeDef(
            "MyType",
            __new__ = interp2app(MyType_descr_new),
            )
        W_MyType.typedef.meta = W_MyMetaclass

        # Test it
        w_mytype = self.space.gettypeobject(W_MyType.typedef)
        self.space.appexec([w_mytype], """(MyType):
            x = MyType()
            assert type(x).f() == 42

            class MyDerived(MyType):
                pass
            y = MyDerived()
            assert type(y).f() == 42
        """)


class AppTestTypeObject:

    def test_abstract_methods(self):
        class X(object):
            pass
        X.__abstractmethods__ = ("meth",)
        raises(TypeError, X)
        del X.__abstractmethods__
        X()
        raises(AttributeError, getattr, type, "__abstractmethods__")
        raises(TypeError, "int.__abstractmethods__ = ('abc', )")

    def test_call_type(self):
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

    def test_bases(self):
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

    def test_mutable_bases(self):
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
        #import pdb; pdb.set_trace()
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
        except TypeError, msg:
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

    def test_mutable_bases_with_failing_mro(self):
        class WorkOnce(type):
            def __new__(self, name, bases, ns):
                self.flag = 0
                return super(WorkOnce, self).__new__(WorkOnce, name, bases, ns)
            def mro(instance):
                if instance.flag > 0:
                    raise RuntimeError, "bozo"
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

    def test_mutable_bases_catch_mro_conflict(self):
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
            raise TestFailed, "didn't catch MRO conflict"

    def test_mutable_bases_versus_nonheap_types(self):
        class A(int):
            pass
        class B(int):
            __slots__ = ['b']
        class C(int):
            pass
        raises(TypeError, 'C.__bases__ = (A,)')
        raises(TypeError, 'C.__bases__ = (B,)')
        raises(TypeError, 'C.__bases__ = (C,)')
        raises(TypeError, 'int.__bases__ = (object,)')
        C.__bases__ = (int,)
        #--- the following raises on CPython but works on PyPy.
        #--- I don't see an obvious reason why it should fail...
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip("works on PyPy only")
        class MostlyLikeInt(int):
            __slots__ = []
        C.__bases__ = (MostlyLikeInt,)

    def test_mutable_bases_versus_slots(self):
        class A(object):
            __slots__ = ['a']
        class B(A):
            __slots__ = ['b1', 'b2']
        class C(B):
            pass
        raises(TypeError, 'C.__bases__ = (A,)')

    def test_mutable_bases_versus_weakref(self):
        class A(object):
            __slots__ = ['a']
        class B(A):
            __slots__ = ['__weakref__']
        class C(B):
            pass
        raises(TypeError, 'C.__bases__ = (A,)')

    def test_mutable_bases_same_slots(self):
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

    def test_mutable_bases_versus_slots_2(self):
        class A(object):
            __slots__ = ['a']
        class B(A):
            __slots__ = ['b1', 'b2']
        class C(B):
            __slots__ = ['c']
        raises(TypeError, 'C.__bases__ = (A,)')

    def test_mutable_bases_keeping_slots(self):
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
        raises(TypeError, 'C.__bases__ = (B, D, B)')

        class E(A):
            __slots__ = ['e']
        raises(TypeError, 'C.__bases__ = (B, E)')
        raises(TypeError, 'C.__bases__ = (E, B)')
        raises(TypeError, 'C.__bases__ = (E,)')

    def test_compatible_slot_layout(self):
        class A(object):
            __slots__ = ['a']
        class B(A):
            __slots__ = ['b1', 'b2']
        class C(A):
            pass
        class D(B, C):    # assert does not raise TypeError
            pass

    def test_builtin_add(self):
        x = 5
        assert x.__add__(6) == 11
        x = 3.5
        assert x.__add__(2) == 5.5
        assert x.__add__(2.0) == 5.5

    def test_builtin_call(self):
        def f(*args):
            return args
        assert f.__call__() == ()
        assert f.__call__(5) == (5,)
        assert f.__call__("hello", "world") == ("hello", "world")

    def test_builtin_call_kwds(self):
        def f(*args, **kwds):
            return args, kwds
        assert f.__call__() == ((), {})
        assert f.__call__("hello", "world") == (("hello", "world"), {})
        assert f.__call__(5, bla=6) == ((5,), {"bla": 6})
        assert f.__call__(a=1, b=2, c=3) == ((), {"a": 1, "b": 2,
                                                           "c": 3})

    def test_multipleinheritance_fail(self):
        try:
            class A(int, dict):
                pass
        except TypeError:
            pass
        else:
            raise AssertionError, "this multiple inheritance should fail"

    def test_outer_metaclass(self):
        class OuterMetaClass(type):
            pass

        class HasOuterMetaclass(object):
            __metaclass__ = OuterMetaClass

        assert type(HasOuterMetaclass) == OuterMetaClass
        assert type(HasOuterMetaclass) == HasOuterMetaclass.__metaclass__

    def test_inner_metaclass(self):
        class HasInnerMetaclass(object):
            class __metaclass__(type):
                pass

        assert type(HasInnerMetaclass) == HasInnerMetaclass.__metaclass__

    def test_implicit_metaclass(self):
        class __metaclass__(type):
            pass

        g = {'__metaclass__': __metaclass__}
        exec "class HasImplicitMetaclass: pass\n" in g

        HasImplicitMetaclass = g['HasImplicitMetaclass']
        assert type(HasImplicitMetaclass) == __metaclass__

    def test_mro(self):
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

    def test_abstract_mro(self):
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

    def test_nodoc(self):
        class NoDoc(object):
            pass

        try:
            assert NoDoc.__doc__ == None
        except AttributeError:
            raise AssertionError, "__doc__ missing!"

    def test_explicitdoc(self):
        class ExplicitDoc(object):
            __doc__ = 'foo'

        assert ExplicitDoc.__doc__ == 'foo'

    def test_implicitdoc(self):
        class ImplicitDoc(object):
            "foo"

        assert ImplicitDoc.__doc__ == 'foo'

    def test_immutabledoc(self):
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
            raise AssertionError, '__doc__ should not be writable'

        assert ImmutableDoc.__doc__ == 'foo'

    def test_metaclass_conflict(self):

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

    def test_metaclass_choice(self):
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
    
    def test_descr_typecheck(self):
        raises(TypeError,type.__dict__['__name__'].__get__,1)
        raises(TypeError,type.__dict__['__mro__'].__get__,1)

    def test_slots_simple(self):
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

    def test_slot_mangling(self):
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

    def test_slots_multiple_inheritance(self):
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

    def test_string_slots(self):
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

    def test_base_attr(self):
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

    def test_cannot_subclass(self):
        raises(TypeError, type, 'A', (bool,), {})

    def test_slot_conflict(self):
        class A(object):
            __slots__ = ['a']
        class B(A):
            __slots__ = ['b']
        class E(A):
            __slots__ = ['e']
        raises(TypeError, type, 'C', (B, E), {})

    def test_repr(self):
        globals()['__name__'] = 'a'
        class A(object):
            pass
        assert repr(A) == "<class 'a.A'>"
        assert repr(type(type)) == "<type 'type'>" 
        assert repr(complex) == "<type 'complex'>"
        assert repr(property) == "<type 'property'>"
        assert repr(TypeError) == "<type 'exceptions.TypeError'>"
        
    def test_invalid_mro(self):
        class A(object):
            pass
        raises(TypeError, "class B(A, A): pass")
        class C(A):
            pass
        raises(TypeError, "class D(A, C): pass")

    def test_data_descriptor_without_get(self):
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

    def test_user_defined_mro_cls_access(self):
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

    def test_only_classic_bases_fails(self):
        class C:
            pass
        raises(TypeError, type, 'D', (C,), {})

    def test_set___class__(self):
        raises(TypeError, "1 .__class__ = int")
        raises(TypeError, "1 .__class__ = bool")
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
        raises(TypeError, "d.__class__ = A")
        d.__class__ = C
        assert d.__class__ == C
        d.__class__ = D
        assert d.__class__ == D
        class AA(object):
            __slots__ = ('a',)
        aa = AA()
        # the following line works on CPython >= 2.6 but not on PyPy.
        # but see below for more
        raises(TypeError, "aa.__class__ = A")
        raises(TypeError, "aa.__class__ = object")
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
        raises(TypeError, "f.__class__ = I")
        i = I()
        raises(TypeError, "i.__class__ = F")
        raises(TypeError, "i.__class__ = int")

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
        raises(TypeError, "X().__class__ = Y")
        raises(TypeError, "Y().__class__ = X")

        raises(TypeError, "X().__class__ = object")
        raises(TypeError, "X().__class__ = 1")

        class Int(int): __slots__ = []

        raises(TypeError, "Int().__class__ = int")

        class Order1(object):
            __slots__ = ['a', 'b']
        class Order2(object):
            __slots__ = ['b', 'a']
        # the following line works on CPython >= 2.6 but not on PyPy.
        # but see below for more
        raises(TypeError, "Order1().__class__ = Order2")

        class U1(object):
            __slots__ = ['a', 'b']
        class U2(U1):
            __slots__ = ['c', 'd', 'e']
        class V1(object):
            __slots__ = ['a', 'b']
        class V2(V1):
            __slots__ = ['c', 'd', 'e']
        # the following line does not work on CPython >= 2.6 either.
        # that's just obscure.  Really really.  So we just ignore
        # the whole issue until someone comes complaining.  Then we'll
        # just kill slots altogether apart from maybe doing a few checks.
        raises(TypeError, "U2().__class__ = V2")

    def test_name(self):
        class Abc(object):
            pass
        assert Abc.__name__ == 'Abc'
        Abc.__name__ = 'Def'
        assert Abc.__name__ == 'Def'
        raises(TypeError, "Abc.__name__ = 42")

    def test_compare(self):
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

    def test_class_variations(self):
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

    def test_module(self):
        def f(): pass
        assert object.__module__ == '__builtin__'
        assert int.__module__ == '__builtin__'
        assert type.__module__ == '__builtin__'
        assert type(f).__module__ == '__builtin__'
        d = {'__name__': 'yay'}
        exec """class A(object):\n  pass\n""" in d
        A = d['A']
        assert A.__module__ == 'yay'

    def test_immutable_builtin(self):
        raises(TypeError, setattr, list, 'append', 42)
        raises(TypeError, setattr, list, 'foobar', 42)
        raises(TypeError, delattr, dict, 'keys')
        
    def test_nontype_in_mro(self):
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

    def test_init_must_return_none(self):
        class X(object):
            def __init__(self):
                return 0
        raises(TypeError, X)

    def test_dictproxy_is_updated(self):
        class A(object):
            x = 1
        d = A.__dict__
        assert d["x"] == 1
        A.y = 2
        assert d["y"] == 2
        assert ("x", 1) in d.items()
        assert ("y", 2) in d.items()

    def test_type_descriptors_overridden(self):
        class A(object):
            __dict__ = 42
        assert A().__dict__ == 42
        #
        class B(object):
            __weakref__ = 42
        assert B().__weakref__ == 42

    def test_change_dict(self):
        class A(object):
            pass

        a = A()
        A.x = 1
        assert A.__dict__["x"] == 1
        raises(AttributeError, "del A.__dict__")
        raises((AttributeError, TypeError), "A.__dict__ = {}")

    def test_mutate_dict(self):
        class A(object):
            pass

        a = A()
        A.x = 1
        assert A.__dict__["x"] == 1
        A.__dict__['x'] = 5
        assert A.x == 5

class AppTestMutableBuiltintypes:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.mutable_builtintypes": True})

    def test_del_type_mro(self):
        del type.mro
        # Make sure the default mro function is used.
        class X(object):
            pass

    def test_mutate_builtintype(self):
        list.a = 1
        def doublelen(self):
            return len(self) * 2
        list.doublelen = doublelen
        l = []
        assert l.a == 1
        l.append(100)
        assert l.doublelen() == 2
        del list.doublelen
        del list.a
        raises(AttributeError, "l.a")

    def test_doc(self):
        class C(object):
            pass

        assert C.__dict__['__dict__'].__doc__.startswith("dictionary for")
        assert C.__dict__['__weakref__'].__doc__.startswith("list of weak")
        assert property.__doc__.startswith("property(fget=None,")
        assert type.__doc__.startswith("type(object)")
        assert "run-time error" in RuntimeError.__doc__

class AppTestGetattributeShortcut:

    def setup_class(cls):
        cls.space = gettestobjspace(
                        **{"objspace.std.getattributeshortcut": True})

    def test_reset_logic(self):
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

class TestNewShortcut:

    def setup_class(cls):
        cls.space = gettestobjspace(
                        **{"objspace.std.newshortcut": True})   

    def test_mechanics(self):
        space = self.space
        w_tup = space.appexec([], """():
    class A(object):
        pass
    class B(object):
        __new__ = staticmethod(lambda t: 1)
    class M(type):
        pass
    return A, B, M
""")
        w_A, w_B, w_M = space.unpackiterable(w_tup)

        assert w_A.w_bltin_new is None
        assert w_B.w_bltin_new is None
        assert w_M.w_bltin_new is None                

        _, w_object_newdescr = space.lookup_in_type_where(space.w_object,
                                                          '__new__')
        w_object___new__ = space.get(w_object_newdescr, None,
                                     w_type=space.w_object)

        w_a = space.call_function(w_A)
        assert w_A.w_bltin_new is w_object___new__

        # will shortcut
        w_a = space.call_function(w_A)

        w_b = space.call_function(w_B)
        assert w_B.w_bltin_new is None

        w_m = space.call_function(w_M, space.wrap('C'), space.newlist([]),
                                  space.newdict())
        assert w_M.w_bltin_new is None                                  


class AppTestNewShortcut:

    def setup_class(cls):
        cls.space = gettestobjspace(
                        **{"objspace.std.newshortcut": True})

    def test_reset_logic(self):
        class X(object):
            pass

        class Y(X):
            pass

        y = Y()

        assert isinstance(y, Y)


        X.__new__ = staticmethod(lambda t: 1)

        y = Y()

        assert y == 1

    def test_dont_explode_on_non_types(self):
        class A:
            __new__ = staticmethod(lambda t: 1)

        class B(A, object):
            pass

        b = B()

        assert b == 1

    def test_slots_with_method_in_class(self):
        # this works in cpython...
        class A(object):
            __slots__ = ["f"]
            def f(self, x):
                return x + 1
        a = A()
        assert a.f(1) == 2


class AppTestTrackCompareByIdentity:

    def setup_class(cls):
        cls.space = gettestobjspace(
                        **{"objspace.std.trackcomparebyidentity": True})

        def compares_by_identity(space, w_cls):
            return space.wrap(w_cls.compares_by_identity())
        cls.w_compares_by_identity = cls.space.wrap(interp2app(compares_by_identity))

        versions = {}
        def get_version(space):
            v = versions.setdefault(space.compares_by_identity_version, len(versions))
            return space.wrap(v)
        cls.w_get_version = cls.space.wrap(interp2app(get_version))

    def test_compares_by_identity(self):
        class Plain(object):
            pass

        class CustomEq(object):
            def __eq__(self, other):
                return True

        class CustomCmp (object):
            def __cmp__(self, other):
                return 0

        class CustomHash(object):
            def __hash__(self):
                return 0

        assert self.compares_by_identity(Plain)
        assert not self.compares_by_identity(CustomEq)
        assert not self.compares_by_identity(CustomCmp)
        assert not self.compares_by_identity(CustomHash)

    def test_modify_class(self):
        class X(object):
            pass

        assert self.compares_by_identity(X)
        X.__eq__ = lambda x: None
        assert not self.compares_by_identity(X)
        del X.__eq__
        assert self.compares_by_identity(X)

    def test_versioning(self):
        class X(object):
            pass

        class Y(object):
            def __eq__(self, other):
                pass

        assert self.get_version() == 0
        X.__eq__ = lambda x: None
        # modifying a class for which we never checked the
        # compares_by_identity() status does not increase the version
        assert self.get_version() == 0

        del X.__eq__
        assert self.compares_by_identity(X) # now we check it
        X.__add__ = lambda x: None
        assert self.get_version() == 0 # innocent change
        #
        X.__eq__ = lambda x: None
        assert self.get_version() == 1 # BUMP!

        del X.__eq__
        assert self.compares_by_identity(X)
        X.__bases__ = (object,)
        assert self.get_version() == 2 # BUMP!

        # modifying a class which is already "bad" does not increase the
        # version
        Y.__eq__ = lambda x: None
        assert self.get_version() == 2

    def test_change___class__(self):
        class X(object):
            pass

        class Y(object):
            pass

        class Z(object):
            def __eq__(self, other):
                pass

        x = X()
        assert self.compares_by_identity(X)
        assert self.get_version() == 0
        x.__class__ = Y
        assert self.get_version() == 0
        x.__class__ = Z
        assert self.get_version() == 1
