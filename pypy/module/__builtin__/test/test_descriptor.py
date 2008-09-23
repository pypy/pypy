import autopath


class AppTestBuiltinApp:
    def test_staticmethod(self):
        class C(object):
            def f(a, b):
                return a+b
            f = staticmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        assert c.f("abc", "def") == "abcdef"
        assert C.f("abc", "def") == "abcdef"
        assert d.f("abc", "def") == "abcdef"
        assert D.f("abc", "def") == "abcdef"

    def test_classmethod(self):
        class C(object):
            def f(cls, stuff):
                return cls, stuff
            f = classmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        assert c.f("abc") == (C, "abc")
        assert C.f("abc") == (C, "abc")
        assert d.f("abc") == (D, "abc")
        assert D.f("abc") == (D, "abc")

    def test_property_simple(self):
        
        class a(object):
            def _get(self): return 42
            def _set(self, value): raise AttributeError
            def _del(self): raise KeyError
            name = property(_get, _set, _del)
        a1 = a()
        assert a1.name == 42
        raises(AttributeError, setattr, a1, 'name', 42)
        raises(KeyError, delattr, a1, 'name')

    def test_super(self):
        class A(object):
            def f(self):
                return 'A'
        class B(A):
            def f(self):
                return 'B' + super(B,self).f()
        class C(A):
            def f(self):
                return 'C' + super(C,self).f()
        class D(B, C):
            def f(self):
                return 'D' + super(D,self).f()
        d = D()
        assert d.f() == "DBCA"
        assert D.__mro__ == (D, B, C, A, object)

    def test_super_metaclass(self):
        class xtype(type):
            def __init__(self, name, bases, dict):
                super(xtype, self).__init__(name, bases, dict)
        A = xtype('A', (), {})
        assert isinstance(A, xtype)
        a = A()
        assert isinstance(a, A)

    def test_super_classmethod(self):
        class A(object):
            def f(cls):
                return cls
            f = classmethod(f)
        class B(A):
            def f(cls):
                return [cls, super(B, cls).f()]
            f = classmethod(f)
        assert B().f() == [B, B]

    def test_super_fail(self):
        try:
            super(list, 2)
        except TypeError, e:
            message = e.args[0]
            assert message.startswith('super(type, obj): obj must be an instance or subtype of type')

    def test_super_various(self):
        
        class A(object):
            def meth(self, a):
                return "A(%r)" % a

        class B(A):
            def __init__(self):
                self.__super = super(B, self)
            def meth(self, a):
                return "B(%r)" % a + self.__super.meth(a)

        assert B().meth(2) == "B(2)A(2)"

        class C(A):
            def meth(self, a):
                return "C(%r)" % a + self.__super.meth(a)
        C._C__super = super(C)

        assert C().meth(3) == "C(3)A(3)"

        class D(C, B):
            def meth(self, a):
                return "D(%r)" % a + super(D, self).meth(a)

        assert D().meth(4) == "D(4)C(4)B(4)A(4)"

        # subclasses
        class mysuper(super):
            def __init__(self, *args):
                return super(mysuper, self).__init__(*args)

        class E(D):
            def meth(self, a):
                return "E(%r)" % a + mysuper(E, self).meth(a)

        assert E().meth(5) == "E(5)D(5)C(5)B(5)A(5)"

        class F(E):
            def meth(self, a):
                s = self.__super # == mysuper(F, self)
                return "F(%r)[%s]" % (a, s.__class__.__name__) + s.meth(a)
        F._F__super = mysuper(F)

        assert F().meth(6) == "F(6)[mysuper]E(6)D(6)C(6)B(6)A(6)"

        x = mysuper(F, F())
        x.foobar = 42
        assert x.foobar == 42


    def test_super_lookup(self):
        class DDbase(object):
            def getx(self):
                return 42
            x = property(getx)

        class DDsub(DDbase):
            def getx(self):
                return "hello"
            x = property(getx)

        dd = DDsub()
        assert dd.x == "hello"
        assert super(DDsub, dd).x == 42

    def test_super_lookup2(self):

        class Base(object):
            aProp = property(lambda self: "foo")

        class Sub(Base):
            def test(klass):
                return super(Sub,klass).aProp
            test = classmethod(test)

        assert Sub.test() is Base.aProp

    def test_proxy_super(self):
        class Proxy(object):
            def __init__(self, obj):
                self.__obj = obj
            def __getattribute__(self, name):
                if name.startswith("_Proxy__"):
                    return object.__getattribute__(self, name)
                else:
                    return getattr(self.__obj, name)

        class B(object):
            def f(self):
                return "B.f"

        class C(B):
            def f(self):
                return super(C, self).f() + "->C.f"

        obj = C()
        p = Proxy(obj)
        assert C.__dict__["f"](p) == "B.f->C.f"

    def test_super_errors(self):
        class C(object):
            pass
        class D(C):
            pass
        raises(TypeError, "super(D, 42)")
        raises(TypeError, "super(D, C())")
        raises(TypeError, "super(D).__get__(12)")
        raises(TypeError, "super(D).__get__(C())")

    def test_classmethods_various(self):
        class C(object):
            def foo(*a): return a
            goo = classmethod(foo)
        c = C()
        assert C.goo(1) == (C, 1)
        assert c.goo(1) == (C, 1)
        
        assert c.foo(1) == (c, 1)
        class D(C):
            pass
        d = D()
        assert D.goo(1) == (D, 1)
        assert d.goo(1) == (D, 1)
        assert d.foo(1) == (d, 1)
        assert D.foo(d, 1) == (d, 1)
        def f(cls, arg): return (cls, arg)
        ff = classmethod(f)
        assert ff.__get__(0, int)(42) == (int, 42)
        assert ff.__get__(0)(42) == (int, 42)

        assert C.goo.im_self is C
        assert D.goo.im_self is D
        assert super(D,D).goo.im_self is D
        assert super(D,d).goo.im_self is D
        assert super(D,D).goo() == (D,)
        assert super(D,d).goo() == (D,)

        raises(TypeError, "classmethod(1).__get__(1)")

    def test_property_docstring(self):
        assert property.__doc__.startswith('property')

        class A(object):
            pass

        A.x = property(lambda x: x, lambda x, y: x, lambda x:x, 'xxx')
        assert A.x.__doc__ == 'xxx'

    def test_property(self):
        class C(object):
            def getx(self):
                return self.__x
            def setx(self, value):
                self.__x = value
            def delx(self):
                del self.__x
            x = property(getx, setx, delx, doc="I'm the x property.")
        a = C()
        assert not hasattr(a, "x")
        a.x = 42
        assert a._C__x == 42
        assert a.x == 42
        del a.x
        assert not hasattr(a, "x")
        assert not hasattr(a, "_C__x")
        C.x.__set__(a, 100)
        assert C.x.__get__(a) == 100
        C.x.__delete__(a)
        assert not hasattr(a, "x")

        raw = C.__dict__['x']
        assert isinstance(raw, property)

        attrs = dir(raw)
        assert "__doc__" in attrs
        assert "fget" in attrs
        assert "fset" in attrs
        assert "fdel" in attrs

        assert raw.__doc__ == "I'm the x property."
        assert raw.fget is C.__dict__['getx']
        assert raw.fset is C.__dict__['setx']
        assert raw.fdel is C.__dict__['delx']

        for attr in "__doc__", "fget", "fset", "fdel":
            try:
                setattr(raw, attr, 42)
            except TypeError, msg:
                if str(msg).find('readonly') < 0:
                    raise Exception("when setting readonly attr %r on a "
                                    "property, got unexpected TypeError "
                                    "msg %r" % (attr, str(msg)))
            else:
                raise Exception("expected TypeError from trying to set "
                                "readonly %r attr on a property" % attr)

        class D(object):
            __getitem__ = property(lambda s: 1/0)

        d = D()
        try:
            for i in d:
                str(i)
        except ZeroDivisionError:
            pass
        else:
            raise Exception, "expected ZeroDivisionError from bad property"
