import testsupport
from pypy.objspace.std.stringobject import string_richcompare, W_StringObject, EQ, LT, GT, NE, LE, GE
from pypy.objspace.std.objspace import StdObjSpace


class TestW_StringObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_order_rich(self):
        space = self.space
        def w(txt):
             return W_StringObject(space, txt)

        self.failUnless_w(string_richcompare(space, w('abc'), w('abc'), EQ))

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

    def test_slice(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')
        w_slice = space.newslice(w(0), w(0), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w(''))
        w_slice = space.newslice(w(0), w(1), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('a'))
        w_slice = space.newslice(w(0), w(10), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('abc'))
        w_slice = space.newslice(space.w_None, space.w_None, None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('abc'))
        w_slice = space.newslice(space.w_None, w(-1), None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('ab'))
        w_slice = space.newslice(w(-1), space.w_None, None)
        self.assertEqual_w(space.getitem(w_str, w_slice), w('c'))

    def test_extended_slice(self):
        space = self.space
        w = space.wrap
        w_str = w('abc')

if __name__ == '__main__':
    testsupport.main()
