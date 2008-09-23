from pypy.module.__builtin__.abstractinst import *


class TestAbstractInst:

    def test_abstract_isclass(self):
        space = self.space
        w_B1, w_B2, w_B3, w_X, w_Y = space.viewiterable(space.appexec([], """():
            class X(object): pass
            class Y: pass
            B1, B2, B3 = X(), X(), X()
            B2.__bases__ = (42,)
            B3.__bases__ = 'spam'
            return B1, B2, B3, X, Y
        """))
        assert abstract_isclass_w(space, space.w_int) is True
        assert abstract_isclass_w(space, w_B1) is False
        assert abstract_isclass_w(space, w_B2) is True
        assert abstract_isclass_w(space, w_B3) is False
        assert abstract_isclass_w(space, w_X) is True
        assert abstract_isclass_w(space, w_Y) is True

    def test_abstract_getclass(self):
        space = self.space
        w_x, w_y, w_A, w_MyInst = space.viewiterable(space.appexec([], """():
            class MyInst(object):
                def __init__(self, myclass):
                    self.myclass = myclass
                def __class__(self):
                    if self.myclass is None:
                        raise AttributeError
                    return self.myclass
                __class__ = property(__class__)
            A = object()
            x = MyInst(A)
            y = MyInst(None)
            return x, y, A, MyInst
        """))
        w_42 = space.wrap(42)
        assert space.is_w(abstract_getclass(space, w_42), space.w_int)
        assert space.is_w(abstract_getclass(space, w_x), w_A)
        assert space.is_w(abstract_getclass(space, w_y), w_MyInst)
        assert space.is_w(abstract_getclass(space, w_MyInst), space.w_type)


class AppTestAbstractInst:

    def test_abstract_isinstance(self):
        class MyBaseInst(object):
            pass
        class MyInst(MyBaseInst):
            def __init__(self, myclass):
                self.myclass = myclass
            def __class__(self):
                if self.myclass is None:
                    raise AttributeError
                return self.myclass
            __class__ = property(__class__)
        class MyInst2(MyBaseInst):
            pass
        class MyClass(object):
            pass

        A = MyClass()
        x = MyInst(A)
        assert x.__class__ is A
        assert isinstance(x, MyInst)
        assert isinstance(x, MyBaseInst)
        assert not isinstance(x, MyInst2)
        raises(TypeError, isinstance, x, A)      # A has no __bases__
        A.__bases__ = "hello world"
        raises(TypeError, isinstance, x, A)      # A.__bases__ is not tuple

        class Foo(object):
            pass
        class SubFoo1(Foo):
            pass
        class SubFoo2(Foo):
            pass
        y = MyInst(SubFoo1)
        assert isinstance(y, MyInst)
        assert isinstance(y, MyBaseInst)
        assert not isinstance(y, MyInst2)
        assert isinstance(y, SubFoo1)
        assert isinstance(y, Foo)
        assert not isinstance(y, SubFoo2)

        z = MyInst(None)
        assert isinstance(z, MyInst)
        assert isinstance(z, MyBaseInst)
        assert not isinstance(z, MyInst2)
        assert not isinstance(z, SubFoo1)

        assert isinstance(y, ((), MyInst2, SubFoo1))
        assert isinstance(y, (MyBaseInst, (SubFoo2,)))
        assert not isinstance(y, (MyInst2, SubFoo2))
        assert not isinstance(z, ())

        class Foo(object):
            pass
        class Bar:
            pass
        u = MyInst(Foo)
        assert isinstance(u, MyInst)
        assert isinstance(u, MyBaseInst)
        assert not isinstance(u, MyInst2)
        assert isinstance(u, Foo)
        assert not isinstance(u, Bar)
        v = MyInst(Bar)
        assert isinstance(v, MyInst)
        assert isinstance(v, MyBaseInst)
        assert not isinstance(v, MyInst2)
        assert not isinstance(v, Foo)
        assert isinstance(v, Bar)

        BBase = MyClass()
        BSub1 = MyClass()
        BSub2 = MyClass()
        BBase.__bases__ = ()
        BSub1.__bases__ = (BBase,)
        BSub2.__bases__ = (BBase,)
        x = MyInst(BSub1)
        assert isinstance(x, BSub1)
        assert isinstance(x, BBase)
        assert not isinstance(x, BSub2)
        assert isinstance(x, (BSub2, (), (BSub1,)))

        del BBase.__bases__
        assert isinstance(x, BSub1)
        raises(TypeError, isinstance, x, BBase)
        assert not isinstance(x, BSub2)

        BBase.__bases__ = "foobar"
        assert isinstance(x, BSub1)
        raises(TypeError, isinstance, x, BBase)
        assert not isinstance(x, BSub2)

    def test_abstract_issubclass(self):
        class MyBaseInst(object):
            pass
        class MyInst(MyBaseInst):
            pass
        class MyInst2(MyBaseInst):
            pass
        class MyClass(object):
            pass

        assert issubclass(MyInst, MyBaseInst)
        assert issubclass(MyInst2, MyBaseInst)
        assert issubclass(MyBaseInst, MyBaseInst)
        assert not issubclass(MyBaseInst, MyInst)
        assert not issubclass(MyInst, MyInst2)
        assert issubclass(MyInst, (MyBaseInst, MyClass))
        assert issubclass(MyInst, (MyClass, (), (MyBaseInst,)))
        assert not issubclass(MyInst, (MyClass, (), (MyInst2,)))

        BBase = MyClass()
        BSub1 = MyClass()
        BSub2 = MyClass()
        BBase.__bases__ = ()
        BSub1.__bases__ = (BBase,)
        BSub2.__bases__ = (BBase,)
        assert issubclass(BSub1, BBase)
        assert issubclass(BBase, BBase)
        assert not issubclass(BBase, BSub1)
        assert not issubclass(BSub1, BSub2)
        assert not issubclass(MyInst, BSub1)
        assert not issubclass(BSub1, MyInst)

        del BBase.__bases__
        raises(TypeError, issubclass, BSub1, BBase)
        raises(TypeError, issubclass, BBase, BBase)
        raises(TypeError, issubclass, BBase, BSub1)
        assert not issubclass(BSub1, BSub2)
        assert not issubclass(MyInst, BSub1)
        assert not issubclass(BSub1, MyInst)

        BBase.__bases__ = 42
        raises(TypeError, issubclass, BSub1, BBase)
        raises(TypeError, issubclass, BBase, BBase)
        raises(TypeError, issubclass, BBase, BSub1)
        assert not issubclass(BSub1, BSub2)
        assert not issubclass(MyInst, BSub1)
        assert not issubclass(BSub1, MyInst)
