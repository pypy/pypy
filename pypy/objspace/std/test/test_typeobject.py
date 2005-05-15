import autopath

##class TestSpecialMultimethodCode(testit.TestCase):

##    def setUp(self):
##        self.space = testit.objspace('std')

##    def tearDown(self):
##        pass

##    def test_int_sub(self):
##        w = self.space.wrap
##        for i in range(2):
##            meth = SpecialMultimethodCode(self.space.sub.multimethod, 
##                                          self.space.w_int.__class__, i)
##            self.assertEqual(meth.slice().is_empty(), False)
##            # test int.__sub__ and int.__rsub__
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5, 'x2': 7})),
##                               w(-2))
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5, 'x2': 7.1})),
##                               self.space.w_NotImplemented)
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5.5, 'x2': 7})),
##                               self.space.w_NotImplemented)

##    def test_empty_inplace_add(self):
##        for i in range(2):
##            meth = SpecialMultimethodCode(self.space.inplace_add.multimethod,
##                                          self.space.w_int.__class__, i)
##            self.assertEqual(meth.slice().is_empty(), True)

##    def test_float_sub(self):
##        w = self.space.wrap
##        w(1.5)   # force floatobject imported
##        for i in range(2):
##            meth = SpecialMultimethodCode(self.space.sub.multimethod,
##                                          self.space.w_float.__class__, i)
##            self.assertEqual(meth.slice().is_empty(), False)
##            # test float.__sub__ and float.__rsub__

##            # some of these tests are pointless for Python because
##            # float.__(r)sub__ should not accept an int as first argument
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5, 'x2': 7})),
##                               w(-2.0))
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5, 'x2': 7.5})),
##                               w(-2.5))
##            self.assertEqual_w(meth.eval_code(self.space, None,
##                                              w({'x1': 5.5, 'x2': 7})),
##                               w(-1.5))

objspacename = 'std'

class AppTestTypeObject:
    def test_bases(self):
        assert int.__bases__ == (object,)
        class X:
            __metaclass__ = type
        assert X.__bases__ ==  (object,)
        class Y(X): pass
        assert Y.__bases__ ==  (X,)
        class Z(Y,X): pass
        assert Z.__bases__ ==  (Y, X)
        
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
        global __metaclass__
        try:
            old_metaclass = __metaclass__
            has_old_metaclass = True
        except NameError:
            has_old_metaclass = False
            
        class __metaclass__(type):
            pass

        class HasImplicitMetaclass:
            pass

        try:
            assert type(HasImplicitMetaclass) == __metaclass__
        finally:
            if has_old_metaclass:
                __metaclass__ = old_metaclass
            else:
                del __metaclass__


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

    def test_abstract_mro(self):
        class A1:
            __metaclass__ = _classobj
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
        a.x = 1
        assert a.x == 1
        assert A.__dict__['x'].__get__(a) == 1
        del a.x
        raises(AttributeError, getattr, a, 'x')
        class B(A):
            pass
        b = B()
        raises(AttributeError, getattr, b, 'x')
        b.x = 1
        assert b.x == 1
        assert A.__dict__['x'].__get__(b) == 1
        del b.x
        raises(AttributeError, getattr, b, 'x')
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

    def test_repr(self):
        globals()['__name__'] = 'a'
        class A(object):
            pass
        assert repr(A) == "<class 'a.A'>"
        assert repr(type(type)) == "<type 'type'>" 
        assert repr(complex) == "<type 'complex'>"
        assert repr(property) == "<type 'property'>"
        
    def test_invalid_mro(self):
        class A(object):
            pass
        raises(TypeError, "class B(A, A): pass")
        class C(A):
            pass
        raises(TypeError, "class D(A, C): pass")

    def test_user_defined_mro_cls_access(self):
        d = []
        class T(type):
            def mro(cls):
                d.append(cls.__dict__)
                return type.mro(cls)
        class C:
            __metaclass__ = T
        assert d
        assert sorted(d[0].keys()) == ['__dict__','__metaclass__','__module__']
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
            __metaclass__ = _classobj
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
        raises(TypeError, "aa.__class__ = A")
        raises(TypeError, "aa.__class__ = object")
        class Z1(A):
            pass
        class Z2(A):
            __slots__ = ['__dict__']
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
