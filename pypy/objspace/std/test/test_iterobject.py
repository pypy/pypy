import testsupport
from pypy.objspace.std.iterobject import W_SeqIterObject
from pypy.objspace.std.objspace import NoValue

class TestW_IterObject(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.stdobjspace()

    def tearDown(self):
        pass

    def test_iter(self):
        w = self.space.wrap
        w_tuple = self.space.newtuple([w(5), w(3), w(99)])
        w_iter = W_SeqIterObject(self.space, w_tuple)
        self.assertEqual_w(self.space.next(w_iter), w(5))
        self.assertEqual_w(self.space.next(w_iter), w(3))
        self.assertEqual_w(self.space.next(w_iter), w(99))
        self.assertRaises(NoValue, self.space.next, w_iter)
        self.assertRaises(NoValue, self.space.next, w_iter)

    def test_emptyiter(self):
        w_list = self.space.newlist([])
        w_iter = W_SeqIterObject(self.space, w_list)
        self.assertRaises(NoValue, self.space.next, w_iter)
        self.assertRaises(NoValue, self.space.next, w_iter)

if __name__ == '__main__':
    testsupport.main()
