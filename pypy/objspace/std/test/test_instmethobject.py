import autopath
from pypy.tool import test

class TestInstMethObject(test.TestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_unbound(self):
        from pypy.objspace.std.instmethobject import W_InstMethObject
        space = self.space
        w_list = space.newlist([])
        w_boundmeth = space.getattr(w_list, space.wrap('__len__'))
        w_unboundmeth = W_InstMethObject(space,
                                         w_boundmeth.w_im_func,
                                         space.w_Null,
                                         w_boundmeth.w_im_class)
        self.assertEqual_w(space.call_function(w_unboundmeth, w_list),
                           space.wrap(0))
        

class TestInstMethObjectApp(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_callBound(self):
        boundMethod = [1,2,3].__len__
        self.assertEquals(boundMethod(), 3)
        self.assertRaises(TypeError, boundMethod, 333)
    def test_callUnbound(self):
        unboundMethod = list.__len__
        self.assertEquals(unboundMethod([1,2,3]), 3)
        self.assertRaises(TypeError, unboundMethod)
        self.assertRaises(TypeError, unboundMethod, 333)
        self.assertRaises(TypeError, unboundMethod, [1,2,3], 333)

if __name__ == '__main__':
    test.main()
