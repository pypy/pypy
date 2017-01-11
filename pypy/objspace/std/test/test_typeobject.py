# encoding: utf-8
import py
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef


class TestTypeObject:
    def test_not_acceptable_as_base_class(self):
        space = self.space
        class W_Stuff(W_Root):
            pass
        def descr__new__(space, w_subtype):
            return space.allocate_instance(W_Stuff, w_subtype)
        W_Stuff.typedef = TypeDef("stuff",
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

    def test_attribute_error(self):
        class X(object):
            __module__ = 'test'
        x = X()
        exc = raises(AttributeError, "x.a")
        assert str(exc.value) == "'X' object has no attribute 'a'"

    def test_call_type(self):
        assert type(42) is int
        C = type('C', (object,), {'x': lambda: 42})
        func = C.x
        assert func() == 42
        raises(TypeError, type)
        raises(TypeError, type, 'test', (object,))
        raises(TypeError, type, 'test', (object,), {}, 42)
        raises(TypeError, type, 42, (object,), {})
        raises(TypeError, type, 'test', 42, {})
        raises(TypeError, type, 'test', (object,), 42)

    def test_call_type_subclass(self):
        """
        class A(type):
            pass

        assert A("hello") is str

        # Make sure type(x) doesn't call x.__class__.__init__
        class T(type):
            counter = 0
            def __init__(self, *args):
                T.counter += 1
        class C(metaclass=T):
            pass
        assert T.counter == 1
        a = C()
        assert T.counter == 1
        assert type(a) is C
        assert T.counter == 1
        """

    def test_bases(self):
        """
        assert int.__bases__ == (object,)
        class X(metaclass=type):
            pass
        assert X.__bases__ ==  (object,)
        class Y(X): pass
        assert Y.__bases__ ==  (X,)
        class Z(Y,X): pass
        assert Z.__bases__ ==  (Y, X)

        Z.__bases__ = (X,)
        #print Z.__bases__
        assert Z.__bases__ == (X,)
        """

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

    def test_mutable_bases_with_failing_mro(self):
        """
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

        class F(D, metaclass=WorkOnce):
            pass

        class G(D, metaclass=WorkAlways):
            pass

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
            """

    def test_mutable_bases_with_failing_mro_2(self): """
        class E(Exception):
            pass
        class M(type):
            def mro(cls):
                if cls.__name__ == 'Sub' and A.__bases__ == (Base1,):
                    A.__bases__ = (Base2,)
                    raise E
                return type.mro(cls)

        class Base0:
            pass
        class Base1:
            pass
        class Base2:
            pass
        class A(Base0, metaclass=M):
            pass
        class Sub(A):
            pass

        try:
            A.__bases__ = (Base1,)
        except E:
            assert A.__bases__ == (Base2,)
            assert A.__mro__ == (A, Base2, object)
            assert Sub.__mro__ == (Sub, A, Base2, object)
        else:
            assert 0
        """

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
            raise TestFailed("didn't catch MRO conflict")

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

    def test_method_qualname(self):
        assert dict.copy.__qualname__ == 'dict.copy'

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
        assert f.__call__(a=1, b=2, c=3) == ((), {"a": 1, "b": 2, "c": 3})

    def test_multipleinheritance_fail(self):
        try:
            class A(int, dict):
                pass
        except TypeError:
            pass
        else:
            raise AssertionError("this multiple inheritance should fail")

    def test_outer_metaclass(self):
        """
        class OuterMetaClass(type):
            pass

        class HasOuterMetaclass(metaclass=OuterMetaClass):
            pass

        assert type(HasOuterMetaclass) == OuterMetaClass
        """

    def test_mro(self):
        """
        class A_mro(object):
            a = 1

        class mymeta(type):
            def mro(self):
                return [self, object]

        class B_mro(A_mro, metaclass=mymeta):
            b = 1

        assert B_mro.__bases__ == (A_mro,)
        assert B_mro.__mro__ == (B_mro, object)
        assert B_mro.mro() == [B_mro, object]
        assert B_mro.b == 1
        assert B_mro().b == 1
        assert getattr(B_mro, 'a', None) == None
        assert getattr(B_mro(), 'a', None) == None
        # also check what the built-in mro() method would return for 'B_mro'
        assert type.mro(B_mro) == [B_mro, A_mro, object]
        """

    def test_abstract_mro(self):
        """
        class A1:    # in py3k is a new-style class
            pass
        class B1(A1):
            pass
        class C1(A1):
            pass
        class D1(B1, C1):
            pass
        class E1(D1, object, metaclass=type):
            pass
        # new-style MRO, contrarily to python2
        assert E1.__mro__ == (E1, D1, B1, C1, A1, object)
        """

    def test_nodoc(self):
        class NoDoc(object):
            pass

        try:
            assert NoDoc.__doc__ == None
        except AttributeError:
            raise AssertionError("__doc__ missing!")

    def test_explicitdoc(self):
        class ExplicitDoc(object):
            __doc__ = 'foo'

        assert ExplicitDoc.__doc__ == 'foo'

    def test_implicitdoc(self):
        class ImplicitDoc(object):
            "foo"

        assert ImplicitDoc.__doc__ == 'foo'

    def test_set_doc(self):
        class X:
            "elephant"
        X.__doc__ = "banana"
        assert X.__doc__ == "banana"
        raises(TypeError, lambda:
               type(list).__dict__["__doc__"].__set__(list, "blah"))
        raises((AttributeError, TypeError), lambda:
               type(X).__dict__["__doc__"].__delete__(X))
        assert X.__doc__ == "banana"

    def test_metaclass_conflict(self):
        """
        class T1(type):
            pass
        class T2(type):
            pass
        class D1(metaclass=T1):
            pass
        class D2(metaclass=T2):
            pass
        def conflict():
            class C(D1,D2):
                pass
        raises(TypeError, conflict)
        """

    def test_metaclass_choice(self):
        """
        events = []

        class T1(type):
            def __new__(*args):
                events.append(args)
                return type.__new__(*args)

        class D1(metaclass=T1):
            pass

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
        """

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
            __slots__ = "abc"

        a = A()
        a.abc = "awesome"
        assert a.abc == "awesome"
        b = B()
        b.abc = "awesomer"
        assert b.abc == "awesomer"

    def test_bad_slots(self):
        raises(TypeError, type, 'A', (), {'__slots__': b'x'})
        raises(TypeError, type, 'A', (), {'__slots__': 42})
        raises(TypeError, type, 'A', (), {'__slots__': '2_x'})

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
        assert repr(A) == "<class 'a.test_repr.<locals>.A'>"
        A.__module__ = 123
        assert repr(A) == "<class 'A'>"
        assert repr(type(type)) == "<class 'type'>"
        assert repr(complex) == "<class 'complex'>"
        assert repr(property) == "<class 'property'>"
        assert repr(TypeError) == "<class 'TypeError'>"

    def test_repr_issue1292(self):
        d = {'object': object}    # no __name__
        exec("class A(object): pass\n", d)
        assert d['A'].__module__ == 'builtins'    # obscure, follows CPython
        assert repr(d['A']) == "<class 'A'>"

    def test_repr_nonascii(self):
        assert repr(type('日本', (), {})) == "<class '%s.日本'>" % __name__

    def test_name_nonascii(self):
        assert type('日本', (), {}).__name__ == '日本'

    def test_errors_nonascii(self):
        # Check some arbitrary error messages
        Japan = type('日本', (), {})
        obj = Japan()
        for f in hex, int, len, next, open, set, 'foo'.startswith:
            try:
                f(obj)
            except TypeError as e:
                assert '日本' in str(e)
            else:
                assert False, 'Expected TypeError'

    def test_invalid_mro(self):
        class A(object):
            pass
        raises(TypeError, "class B(A, A): pass")
        class C(A):
            pass
        raises(TypeError, "class D(A, C): pass")

    def test_dir(self):
        class A(object):
            a_var = None
            def a_meth(self):
                pass

        class C(A):
            c_var = None
            def c_meth(self):
                pass

        C_items = dir(C)
        assert C_items != C.__dir__(C)  # as in cpython

        assert 'a_var' in C_items
        assert 'c_var' in C_items
        assert 'a_meth' in C_items
        assert 'c_meth' in C_items

    def test_data_descriptor_without_get(self):
        """
        class Descr(object):
            def __init__(self, name):
                self.name = name
            def __set__(self, obj, what):
                pass
        class Meta(type):
            pass
        class X(object, metaclass=Meta):
            pass
        X.a = 42
        Meta.a = Descr("a")
        assert X.a == 42
        """

    def test_user_defined_mro_cls_access(self):
        """
        d = []
        class T(type):
            def mro(cls):
                d.append(cls.__dict__)
                return type.mro(cls)
        class C(metaclass=T):
            pass
        assert d
        assert sorted(d[0].keys()) == ['__dict__', '__doc__', '__module__', '__weakref__']
        d = []
        class T(type):
            def mro(cls):
                try:
                    cls.x()
                except AttributeError:
                    d.append('miss')
                return type.mro(cls)
        class C(metaclass=T):
            def x(cls):
                return 1
            x = classmethod(x)
        assert d == ['miss']
        assert C.x() == 1
        """

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
        aa.__class__ = A
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
        raises(TypeError, "U2().__class__ = V2")

    def test_name(self):
        class Abc(object):
            pass
        assert Abc.__name__ == 'Abc'
        Abc.__name__ = 'Def'
        assert Abc.__name__ == 'Def'
        raises(TypeError, "Abc.__name__ = 42")
        raises(TypeError, "Abc.__name__ = b'A'")
        try:
            Abc.__name__ = 'G\x00hi'
        except ValueError as e:
            assert str(e) == "type name must not contain null characters"
        else:
            assert False

    def test_qualname(self):
        A = type('A', (), {'__qualname__': 'B.C'})
        assert A.__name__ == 'A'
        assert A.__qualname__ == 'B.C'
        raises(TypeError, type, 'A', (), {'__qualname__': b'B'})
        assert A.__qualname__ == 'B.C'

        A.__qualname__ = 'D.E'
        assert A.__name__ == 'A'
        assert A.__qualname__ == 'D.E'

        C = type('C', (), {})
        C.__name__ = 'A'
        assert C.__name__ == 'A'
        assert C.__qualname__ == 'C'

    def test_compare(self):
        class A(object):
            pass
        class B(A):
            pass
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
        assert object.__module__ == 'builtins'
        assert int.__module__ == 'builtins'
        assert type.__module__ == 'builtins'
        assert type(f).__module__ == 'builtins'
        d = {'__name__': 'yay'}
        exec("""class A(object):\n  pass\n""", d)
        A = d['A']
        assert A.__module__ == 'yay'

    def test_immutable_builtin(self):
        raises(TypeError, setattr, list, 'append', 42)
        raises(TypeError, setattr, list, 'foobar', 42)
        raises(TypeError, delattr, dict, 'keys')
        raises(TypeError, 'int.__dict__["a"] = 1')

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
        d = A.__dict__
        A.x = 1
        assert d["x"] == 1

    def test_we_already_got_one_1(self):
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

    def test_we_already_got_one_2(self):
        class A(object):
            __slots__ = ()
        class B(object):
            pass
        class C(A, B):     # "best base" is A
            __slots__ = ("__dict__",)
        class D(A, B):     # "best base" is A
            __slots__ = ("__weakref__",)

    def test_slot_shadows_class_variable(self):
        try:
            class X:
                __slots__ = ["foo"]
                foo = None
        except ValueError as e:
            assert str(e) == "'foo' in __slots__ conflicts with class variable"
        else:
            assert False, "ValueError expected"

    def test_metaclass_calc(self):
        """
        # issue1294232: correct metaclass calculation
        new_calls = []  # to check the order of __new__ calls
        class AMeta(type):
            @staticmethod
            def __new__(mcls, name, bases, ns):
                new_calls.append('AMeta')
                return super().__new__(mcls, name, bases, ns)
            @classmethod
            def __prepare__(mcls, name, bases):
                return {}

        class BMeta(AMeta):
            @staticmethod
            def __new__(mcls, name, bases, ns):
                new_calls.append('BMeta')
                return super().__new__(mcls, name, bases, ns)
            @classmethod
            def __prepare__(mcls, name, bases):
                ns = super().__prepare__(name, bases)
                ns['BMeta_was_here'] = True
                return ns

        class A(metaclass=AMeta):
            pass
        assert ['AMeta'] == new_calls
        new_calls[:] = []

        class B(metaclass=BMeta):
            pass
        # BMeta.__new__ calls AMeta.__new__ with super:
        assert ['BMeta', 'AMeta'] == new_calls
        new_calls[:] = []

        class C(A, B):
            pass
        # The most derived metaclass is BMeta:
        assert ['BMeta', 'AMeta'] == new_calls
        new_calls[:] = []
        # BMeta.__prepare__ should've been called:
        assert 'BMeta_was_here' in C.__dict__

        # The order of the bases shouldn't matter:
        class C2(B, A):
            pass
        assert ['BMeta', 'AMeta'] == new_calls
        new_calls[:] = []
        assert 'BMeta_was_here' in C2.__dict__

        # Check correct metaclass calculation when a metaclass is declared:
        class D(C, metaclass=type):
            pass
        assert ['BMeta', 'AMeta'] == new_calls
        new_calls[:] = []
        assert 'BMeta_was_here' in D.__dict__

        class E(C, metaclass=AMeta):
            pass
        assert ['BMeta', 'AMeta'] == new_calls
        new_calls[:] = []
        assert 'BMeta_was_here' in E.__dict__

        # Special case: the given metaclass isn't a class,
        # so there is no metaclass calculation.
        marker = object()
        def func(*args, **kwargs):
            return marker
        class X(metaclass=func):
            pass
        class Y(object, metaclass=func):
            pass
        class Z(D, metaclass=func):
            pass
        assert marker is X
        assert marker is Y
        assert marker is Z
        """

    def test_prepare(self):
        """
        classdict = type.__prepare__()
        assert type(classdict) is dict
        assert classdict == {}
        assert type.__prepare__(3) == {}
        assert type.__prepare__(3, 4) == {}
        assert type.__prepare__(3, package='sqlalchemy') == {}
        class M(type):
            @classmethod
            def __prepare__(cls, *args, **kwds):
                d = super().__prepare__(*args, **kwds)
                d['hello'] = 42
                return d
        class C(metaclass=M):
            foo = hello
        assert C.foo == 42
        """

    def test_crash_mro_without_object_1(self):
        """
        class X(type):
            def mro(self):
                return [self]
        class C(metaclass=X):
            pass
        e = raises(TypeError, C)     # the lookup of '__new__' fails
        assert str(e.value) == "cannot create 'C' instances"
        """

    def test_crash_mro_without_object_2(self):
        """
        class X(type):
            def mro(self):
                return [self, int]
        class C(int, metaclass=X):
            pass
        C()    # the lookup of '__new__' succeeds in 'int',
               # but the lookup of '__init__' fails
        """

    def test_instancecheck(self):
        assert int.__instancecheck__(42) is True
        assert int.__instancecheck__(42.0) is False
        class Bar(object):
            __class__ = int
        assert int.__instancecheck__(Bar()) is True

    def test_subclasscheck(self):
        assert int.__subclasscheck__(bool) is True
        assert int.__subclasscheck__(float) is False
        class Bar(object):
            __class__ = int
        assert int.__subclasscheck__(Bar) is False
        class AbstractClass(object):
            __bases__ = (int,)
        assert int.__subclasscheck__(AbstractClass()) is True

    def test_bad_args(self):
        import collections
        raises(TypeError, type, 'A', (), dict={})
        raises(TypeError, type, 'A', [], {})
        raises(TypeError, type, 'A', (), collections.UserDict())
        raises(ValueError, type, 'A\x00B', (), {})
        raises(TypeError, type, b'A', (), {})


class AppTestWithMethodCacheCounter:
    spaceconfig = {"objspace.std.withmethodcachecounter": True}

    def test_module_from_handbuilt_type(self):
        d = {'tuple': tuple, '__name__': 'foomod'}
        exec("""class foo(tuple): pass""", d)
        t = d['foo']
        t.__module__ = 'barmod'
        # this last line used to crash; see ab926f846f39
        assert t.__module__


class AppTestGetattributeShortcut:

    def test_reset_logic(self):
        """
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

        class X(metaclass=M):
            pass

        class Y(X):
            pass

        y = Y()
        y.x = 3
        assert y.x == 3

        def ga2(self, name):
            return 'GA2'

        X.__getattribute__ = ga2

        assert y.x == 'GA2'
        """

class TestNewShortcut:
    spaceconfig = {"objspace.std.newshortcut": True}

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

        assert w_A.w_new_function is None
        assert w_B.w_new_function is None
        assert w_M.w_new_function is None

        _, w_object_newdescr = space.lookup_in_type_where(space.w_object,
                                                          '__new__')
        w_object___new__ = space.get(w_object_newdescr, None,
                                     w_type=space.w_object)

        w_a = space.call_function(w_A)
        assert w_A.w_new_function is w_object___new__

        # will shortcut
        w_a = space.call_function(w_A)

        w_b = space.call_function(w_B)
        assert w_B.w_new_function is not None
        w_b = space.call_function(w_B)

        w_m = space.call_function(w_M, space.wrap('C'), space.newtuple([]),
                                  space.newdict())
        assert w_M.w_new_function is not None


class AppTestNewShortcut:
    spaceconfig = {"objspace.std.newshortcut": True}

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

    def test_eq_returns_notimplemented(self):
        assert type.__eq__(int, 42) is NotImplemented
        assert type.__ne__(dict, 42) is NotImplemented
        assert type.__eq__(int, int) == True
        assert type.__eq__(int, dict) is NotImplemented
class AppTestComparesByIdentity:

    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("interp2app doesn't work on appdirect")

        def compares_by_identity(space, w_cls):
            return space.wrap(w_cls.compares_by_identity())
        cls.w_compares_by_identity = cls.space.wrap(interp2app(compares_by_identity))

    def test_compares_by_identity(self):
        class Plain(object):
            pass

        class CustomEq(object):
            def __eq__(self, other):
                return True

        class CustomHash(object):
            def __hash__(self):
                return 0

        class TypeSubclass(type):
            pass

        assert self.compares_by_identity(Plain)
        assert not self.compares_by_identity(CustomEq)
        assert not self.compares_by_identity(CustomHash)
        assert self.compares_by_identity(type)
        assert self.compares_by_identity(TypeSubclass)

    def test_modify_class(self):
        class X(object):
            pass

        assert self.compares_by_identity(X)
        X.__eq__ = lambda x: None
        assert not self.compares_by_identity(X)
        del X.__eq__
        assert self.compares_by_identity(X)

    def test_duplicate_slot_name(self):
        class X:   # does not raise
            __slots__ = 'a', 'a'

    def test_descriptor_objclass(self):
        class X(object):
            pass
        assert X.__dict__['__dict__'].__objclass__ is X
        assert X.__dict__['__weakref__'].__objclass__ is X
