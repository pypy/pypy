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
        class X: pass
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
