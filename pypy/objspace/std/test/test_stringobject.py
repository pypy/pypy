import testsupport
#from pypy.objspace.std.stringobject import W_StringObject
#from pypy.objspace.std.objspace import StdObjSpace


class TestW_StringObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_equality(self):
        w = self.space.wrap 
        self.assertEqual_w(w('abc'), w('abc'))
        self.assertNotEqual_w(w('abc'), w('def'))

    def test_order_cmp(self):
        space = self.space
        w = space.wrap
        self.failUnless_w(space.lt(w('a'), w('b')))
        self.failUnless_w(space.lt(w('a'), w('ab')))
        self.failUnless_w(space.le(w('a'), w('a')))
        self.failUnless_w(space.gt(w('a'), w('')))

    def test_truth(self):
        w = self.space.wrap
        self.failUnless_w(w('non-empty'))
        self.failIf_w(w(''))

    def test_getitem(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')
        self.assertEqual_w(space.getitem(w_str, w(0)), w('a'))
        self.assertEqual_w(space.getitem(w_str, w(-1)), w('c'))
        self.assertRaises_w(space.w_IndexError,
                            space.getitem,
                            w_str,
                            w(3))
        

if __name__ == '__main__':
    testsupport.main()
