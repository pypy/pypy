import testsupport

# need pypy.module.builtin first to make other imports work (???)
from pypy.module import builtin

from pypy.interpreter import extmodule

class EmptyBM(extmodule.BuiltinModule):
    __pythonname__ = 'empty_bm'

class BM_with_appmethod(extmodule.BuiltinModule):
    __pythonname__ = 'bm_with_appmethod'
    def amethod(self): return 23
    amethod = extmodule.appmethod(amethod)

class BM_with_appdata(extmodule.BuiltinModule):
    __pythonname__ = 'bm_with_appdata'
    somedata = 'twentythree'
    somedata = extmodule.appdata(somedata)


class TestBuiltinModule(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_empty(self):
        space = self.space
        bm = EmptyBM(space)
        w_bm = bm.wrap_me()
        w_bmd = space.getattr(w_bm, space.wrap('__dict__'))
        bmd = space.unwrap(w_bmd)
        self.assertEqual(bmd,
            {'__doc__': EmptyBM.__doc__,
            '__name__': EmptyBM.__pythonname__} )

    def test_appmethod(self):
        space = self.space
        bm = BM_with_appmethod(space)
        w_bm = bm.wrap_me()
        w_bmd = space.getattr(w_bm, space.wrap('__dict__'))
        bmd = space.unwrap(w_bmd)
        themethod = bmd.get('amethod')
        self.assertNotEqual(themethod, None)
        w_method = space.getitem(w_bmd, space.wrap('amethod'))
        bmd['amethod'] = BM_with_appmethod.amethod
        self.assertEqual(bmd,
            {'__doc__': BM_with_appmethod.__doc__,
            '__name__': BM_with_appmethod.__pythonname__,
            'amethod': BM_with_appmethod.amethod} )
        result = space.call(w_method, space.wrap(()), space.wrap({}))
        self.assertEqual(result, 23)

    def test_appdata(self):
        space = self.space
        bm = BM_with_appdata(space)
        w_bm = bm.wrap_me()
        w_bmd = space.getattr(w_bm, space.wrap('__dict__'))
        bmd = space.unwrap(w_bmd)
        thedata = bmd.get('somedata')
        self.assertNotEqual(thedata, None)
        w_data = space.getitem(w_bmd, space.wrap('somedata'))
        bmd['somedata'] = BM_with_appdata.somedata
        self.assertEqual(bmd,
            {'__doc__': BM_with_appdata.__doc__,
            '__name__': BM_with_appdata.__pythonname__,
            'somedata': BM_with_appdata.somedata} )
        self.assertEqual(thedata, 'twentythree')


class TestPyBuiltinCode(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_simple(self):
        def f(w_x):
            return w_x
        builtin_f = extmodule.make_builtin_func(self.space, f)
        w_input = self.space.wrap(42)
        w_res = self.space.call_function(builtin_f, w_input)
        self.assertEqual_w(w_res, w_input)

    def test_default(self):
        space = self.space
        w = space.wrap
        def f(w_x, w_y=23):
            return space.add(w_x, w_y)
        builtin_f = extmodule.make_builtin_func(space, f)
        w_input = w(42)
        w_res = space.call_function(builtin_f, w_input)
        self.assertEqual_w(w_res, w(65))
        w_res = space.call_function(builtin_f, w_input, w(100))
        self.assertEqual_w(w_res, w(142))

    def test_varargs(self):
        s = self.space
        w = s.wrap
        def f(w_first, *args_w):
            w_r = w_first
            for w_i in args_w:
                w_r = s.add(w_r, w_i)
            return w_r
        builtin_f = extmodule.make_builtin_func(s, f)        
        self.assertEqual_w(s.call_function(builtin_f, w(1)), w(1))
        self.assertEqual_w(s.call_function(builtin_f, w(1), w(2), w(3)), w(6))

    def test_kwargs(self):
        s = self.space
        w = s.wrap
        def f(**kws_w):
            return s.add(kws_w['a'], kws_w['b'])
        builtin_f = extmodule.make_builtin_func(s, f)
        self.assertEqual_w(s.call_function(builtin_f, a=w(1), b=w(2)), w(3))

    def test_varkwargs(self):
        s = self.space
        w = s.wrap
        def f(*args_w, **kws_w):
            return s.add(args_w[0], kws_w['a'])
        builtin_f = extmodule.make_builtin_func(s, f)
        self.assertEqual_w(s.call_function(builtin_f, w(2), a=w(1)), w(3))

if __name__ == '__main__':
    testsupport.main()
