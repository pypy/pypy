import testsupport

class TestW_SliceObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.stdobjspace()

    def tearDown(self):
        pass

    def equal_indices(self, got, expected):
        for g, e in zip(got, expected):
            self.assertEqual_w(g, self.space.wrap(e))

    def test_indices(self):
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w_None)
        self.equal_indices(w_slice.indices(w(6)), (0, 6, 1, 6))
        w_slice = space.newslice(w(0), w(6), w(1))
        self.equal_indices(w_slice.indices(w(6)), (0, 6, 1, 6))
        w_slice = space.newslice(w_None, w_None, w(-1))
        self.equal_indices(w_slice.indices(w(6)), (5, -1, -1, 6))

    def test_indices_fail(self):
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w(0))
        self.assertRaises_w(space.w_ValueError,
                            w_slice.indices, w(10))

if __name__ == '__main__':
    testsupport.main()
