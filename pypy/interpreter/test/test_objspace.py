import autopath
from pypy.tool import test 

# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class TestObjSpace(test.TestCase):

    def setUp(self):
        self.space = test.objspace()

    def tearDown(self):
        pass

    def test_newstring(self):
        w = self.space.wrap
        s = 'abc'
        chars_w = [w(ord(c)) for c in s]
        self.assertEqual_w(w(s), self.space.newstring(chars_w))

    def test_newstring_fail(self):
        w = self.space.wrap
        s = 'abc'
        not_chars_w = [w(c) for c in s]
        self.assertRaises_w(self.space.w_TypeError,
                            self.space.newstring,
                            not_chars_w)
        self.assertRaises_w(self.space.w_ValueError,
                            self.space.newstring,
                            [w(-1)])

    def test_newlist(self):
        w = self.space.wrap
        l = range(10)
        w_l = self.space.newlist([w(i) for i in l])
        self.assertEqual_w(w_l, w(l))

    def test_newdict(self):
        w = self.space.wrap
        items = [(0, 1), (3, 4)]
        items_w = [(w(k), w(v)) for (k, v) in items]
        d = dict(items)
        w_d = self.space.newdict(items_w)
        self.assertEqual_w(w_d, w(d))

    def test_newtuple(self):
        w = self.space.wrap
        t = tuple(range(10))
        w_t = self.space.newtuple([w(i) for i in t])
        self.assertEqual_w(w_t, w(t))

    def test_is_true(self):
        w = self.space.wrap
        true = (1==1)
        false = (1==0)
        w_true = w(true)
        w_false = w(false)
        self.failUnless(self.space.is_true(w_true))
        self.failIf(self.space.is_true(w_false))

    def test_is_(self):
        w_l = self.space.newlist([])
        w_m = self.space.newlist([])
        self.assertEqual(self.space.is_(w_l, w_l), self.space.w_True)
        self.assertEqual(self.space.is_(w_l, w_m), self.space.w_False)

    def test_newbool(self):
        self.assertEqual(self.space.newbool(0), self.space.w_False)
        self.assertEqual(self.space.newbool(1), self.space.w_True)

    def test_unpackiterable(self):
        w = self.space.wrap
        l = [w(1), w(2), w(3), w(4)]
        w_l = self.space.newlist(l)
        self.assertEqual(self.space.unpackiterable(w_l), l)
        self.assertEqual(self.space.unpackiterable(w_l, 4), l)
        self.assertRaises(ValueError, self.space.unpackiterable, w_l, 3)
        self.assertRaises(ValueError, self.space.unpackiterable, w_l, 5)

    def test_unpacktuple(self):
        w = self.space.wrap
        l = [w(1), w(2), w(3), w(4)]
        w_l = self.space.newtuple(l)
        self.assertEqual(self.space.unpacktuple(w_l), l)
        self.assertEqual(self.space.unpacktuple(w_l, 4), l)
        self.assertRaises(ValueError, self.space.unpacktuple, w_l, 3)
        self.assertRaises(ValueError, self.space.unpacktuple, w_l, 5)

    def test_exception_match(self):
        self.failUnless(self.space.exception_match(self.space.w_ValueError,
                                                   self.space.w_ValueError))
        self.failUnless(self.space.exception_match(self.space.w_IndexError,
                                                   self.space.w_LookupError))
        self.failIf(self.space.exception_match(self.space.w_ValueError,
                                               self.space.w_LookupError))

if __name__ == '__main__':
    test.main()
