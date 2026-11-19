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

    def test_setattr_if_not_from_object(self):
        space = self.space
        w_A, w_B = space.unpackiterable(space.appexec([], """():
            class A(object):
                pass
            class B(object):
                def __setattr__(self, obj, name, value):
                    pass
            return A, B
        """))
        assert w_A.uses_object_setattr is False
        w_res = w_A.setattr_if_not_from_object()
        assert w_res is None
        assert w_A.uses_object_setattr is True

        assert w_B.uses_object_setattr is False
        w_res = w_B.setattr_if_not_from_object()
        assert w_res is not None
        assert w_B.uses_object_setattr is False

        # check invalidation
        space.setattr(w_A, space.newtext("__setattr__"), space.newint(1))
        assert w_A.uses_object_setattr is False
        w_res = w_A.setattr_if_not_from_object()
        assert w_res is not None
        assert w_A.uses_object_setattr is False


class AppTestTypeObject:
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

class AppTestWithMethodCacheCounter:
    spaceconfig = {"objspace.std.withmethodcachecounter": True}

    def test_module_from_handbuilt_type(self):
        d = {'tuple': tuple, '__name__': 'foomod'}
        exec """class foo(tuple): pass""" in d
        t = d['foo']
        t.__module__ = 'barmod'
        # this last line used to crash; see ab926f846f39
        assert t.__module__


class AppTestGetattributeShortcut:

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

    def test_slots_with_method_in_class(self):
        # this works in cpython...
        class A(object):
            __slots__ = ["f"]
            def f(self, x):
                return x + 1
        a = A()
        assert a.f(1) == 2

    def test_eq_returns_notimplemented(self):
        assert type.__eq__(int, 42) is NotImplemented
        assert type.__ne__(dict, 42) is NotImplemented
        assert type.__eq__(int, int) is True
        assert type.__eq__(int, dict) is False

    def test_cmp_on_types(self):
        class X(type):
            def __cmp__(self, other):
                return -1
        class Y:
            __metaclass__ = X
        assert (Y < Y) is True


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

        class CustomCmp (object):
            def __cmp__(self, other):
                return 0

        class CustomHash(object):
            def __hash__(self):
                return 0

        class TypeSubclass(type):
            pass

        class TypeSubclassCustomCmp(type):
            def __cmp__(self, other):
                return 0

        assert self.compares_by_identity(Plain)
        assert not self.compares_by_identity(CustomEq)
        assert not self.compares_by_identity(CustomCmp)
        assert not self.compares_by_identity(CustomHash)
        assert self.compares_by_identity(type)
        assert self.compares_by_identity(TypeSubclass)
        assert not self.compares_by_identity(TypeSubclassCustomCmp)

    def test_modify_class(self):
        class X(object):
            pass

        assert self.compares_by_identity(X)
        X.__eq__ = lambda x: None
        assert not self.compares_by_identity(X)
        del X.__eq__
        assert self.compares_by_identity(X)

    def test_descriptor_objclass(self):
        class X(object):
            pass
        assert X.__dict__['__dict__'].__objclass__ is X
        assert X.__dict__['__weakref__'].__objclass__ is X
        assert object.__dict__['__class__'].__objclass__ is object
        assert int.__dict__['imag'].__objclass__ is int
        assert file.closed.__objclass__ is file
        assert type.__dict__['__name__'].__objclass__ is type
        assert type.__dict__['__doc__'].__objclass__ is type
        #
        assert type.__dict__['__name__'].__name__ == '__name__'
        assert type.__dict__['__doc__'].__name__ == '__doc__'
