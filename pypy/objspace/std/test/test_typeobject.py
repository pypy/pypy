import testsupport
from pypy.objspace.std.typeobject import PyMultimethodCode

class TestPyMultimethodCode(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.stdobjspace()

    def tearDown(self):
        pass

    def test_int_sub(self):
        w = self.space.wrap
        for i in range(2):
            meth = PyMultimethodCode(self.space.sub.multimethod,
                                     i, self.space.w_int)
            self.assertEqual(meth.slice().is_empty(), False)
            # test int.__sub__ and int.__rsub__
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5, 'x2': 7})),
                               w(-2))
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5, 'x2': 7.1})),
                               self.space.w_NotImplemented)
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5.5, 'x2': 7})),
                               self.space.w_NotImplemented)

    def test_empty_inplace_add(self):
        for i in range(2):
            meth = PyMultimethodCode(self.space.inplace_add.multimethod,
                                     i, self.space.w_int)
            self.assertEqual(meth.slice().is_empty(), True)

    def test_float_sub(self):
        w = self.space.wrap
        w(1.5)   # force floatobject imported
        for i in range(2):
            meth = PyMultimethodCode(self.space.sub.multimethod,
                                     i, self.space.w_float)
            self.assertEqual(meth.slice().is_empty(), False)
            # test float.__sub__ and float.__rsub__

            # some of these tests are pointless for Python because
            # float.__(r)sub__ should not accept an int as first argument
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5, 'x2': 7})),
                               w(-2.0))
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5, 'x2': 7.5})),
                               w(-2.5))
            self.assertEqual_w(meth.eval_code(self.space, None,
                                              w({'x1': 5.5, 'x2': 7})),
                               w(-1.5))


if __name__ == '__main__':
    testsupport.main()
