import autopath
from pypy.tool import testit

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

class TestTypeObject(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace('std')

    def test_bases(self):
        self.assertEquals(int.__bases__, (object,))
        class X: pass
        self.assertEquals(X.__bases__,  (object,))
        class Y(X): pass
        self.assertEquals(Y.__bases__,  (X,))
        class Z(Y,X): pass
        self.assertEquals(Z.__bases__,  (Y, X))
        
    def test_builtin_add(self):
        x = 5
        self.assertEquals(x.__add__(6), 11)
        x = 3.5
        self.assertEquals(x.__add__(2), 5.5)
        self.assertEquals(x.__add__(2.0), 5.5)

    def test_builtin_call(self):
        def f(*args):
            return args
        self.assertEquals(f.__call__(), ())
        self.assertEquals(f.__call__(5), (5,))
        self.assertEquals(f.__call__("hello", "world"), ("hello", "world"))

    def test_builtin_call_kwds(self):
        def f(*args, **kwds):
            return args, kwds
        self.assertEquals(f.__call__(), ((), {}))
        self.assertEquals(f.__call__("hello", "world"), (("hello", "world"), {}))
        self.assertEquals(f.__call__(5, bla=6), ((5,), {"bla": 6}))
        self.assertEquals(f.__call__(a=1, b=2, c=3), ((), {"a": 1, "b": 2,
                                                           "c": 3}))

    def test_multipleinheritance_fail(self):
        try:
            class A(int, dict):
                pass
        except TypeError:
            pass
        else:
            raise AssertionError, "this multiple inheritance should fail"

    def test_mro(self):
        class A(object):
            a = 1

        class B(A):
            b = 1
            class __metaclass__(type):
                def mro(self):
                    return [self, object]

        self.assertEquals(B.__bases__, (A,))
        self.assertEquals(B.__mro__, (B, object))
        self.assertEquals(B.mro(), [B, object])
        self.assertEquals(B.b, 1)
        self.assertEquals(B().b, 1)
        self.assertEquals(getattr(B, 'a', None), None)
        self.assertEquals(getattr(B(), 'a', None), None)


if __name__ == '__main__':
    testit.main()
