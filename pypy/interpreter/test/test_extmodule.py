import testsupport

# need pypy.module.builtin first to make other imports work (???)
from pypy.module import builtin

from pypy.interpreter import extmodule
from pypy.objspace import trivial

class EmptyBM(extmodule.BuiltinModule):
    __pythonname__ = 'empty_bm'

class BM_with_appmethod(extmodule.BuiltinModule):
    __pythonname__ = 'bm_with_appmethod'
    def amethod(self): return 23
    amethod = extmodule.appmethod(amethod)

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
        result = space.call(w_method, space.wrap(()), None)
        self.assertEqual(result, 23)


if __name__ == '__main__':
    testsupport.main()
