import autopath
from pypy.tool import test 

# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class TestStdObjectSpace(test.TestCase):

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

    def test_newmodule(self):
        # a shoddy test:
        w_mod = self.space.newmodule(self.space.wrap("mod"))

    def test_newfunction(self):
        # this tests FAR more than newfunction, but that's probably
        # unavoidable
        def f(x):
            return x
        from pypy.interpreter.pycode import PyByteCode
        c = PyByteCode()
        c._from_code(f.func_code)
        w_globals = self.space.newdict([])
        w_defs = self.space.newtuple([])
        w_f = self.space.newfunction(c, w_globals, w_defs)
        self.assertEqual_w(self.space.call_function(w_f, self.space.wrap(1)),
                           self.space.wrap(1))
    
if __name__ == '__main__':
    test.main()
