import autopath
from pypy.tool import test

class TestW_SliceObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

    def tearDown(self):
        pass

    def equal_indices(self, got, expected):
        self.assertEqual(len(got), len(expected))
        for g, e in zip(got, expected):
            self.assertEqual(g, e)

    def test_indices(self):
        from pypy.objspace.std import slicetype
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w_None)
        self.equal_indices(slicetype.indices3(space, w_slice, 6), (0, 6, 1))
        w_slice = space.newslice(w(0), w(6), w(1))
        self.equal_indices(slicetype.indices3(space, w_slice, 6), (0, 6, 1))
        w_slice = space.newslice(w_None, w_None, w(-1))
        self.equal_indices(slicetype.indices3(space, w_slice, 6), (5, -1, -1))

    def test_indices_fail(self):
        from pypy.objspace.std import slicetype
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w(0))
        self.assertRaises_w(space.w_ValueError,
                            slicetype.indices3, space, w_slice, 10)

class Test_SliceObject(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_new(self):
        def cmp_slice(sl1, sl2):
            for attr in "start", "stop", "step":
                if getattr(sl1, attr) != getattr(sl2, attr):
                    return False
            return True
        self.assertRaises(TypeError, slice)
        self.assertRaises(TypeError, slice, 1, 2, 3, 4)
        self.failUnless(cmp_slice(slice(23), slice(None, 23, None)))
        self.failUnless(cmp_slice(slice(23, 45), slice(23, 45, None)))

    def test_indices(self):
        self.assertEqual(slice(4,11,2).indices(28), (4, 11, 2))
        self.assertEqual(slice(4,11,2).indices(8), (4, 8, 2))
        self.assertEqual(slice(4,11,2).indices(2), (2, 2, 2))
        self.assertEqual(slice(11,4,-2).indices(28), (11, 4, -2))
        self.assertEqual(slice(11,4,-2).indices(8), (7, 4, -2))
        self.assertEqual(slice(11,4,-2).indices(2), (1, 2, -2))

if __name__ == '__main__':
    test.main()
