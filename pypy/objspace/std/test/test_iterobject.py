import autopath
from pypy.objspace.std.iterobject import W_SeqIterObject
from pypy.interpreter.error import OperationError
from pypy.tool import testit

class TestW_IterObject(testit.TestCase):

    def setUp(self):
        self.space = testit.objspace('std')

    def tearDown(self):
        pass

    def body3(self, w_iter):
        w = self.space.wrap
        self.assertEqual_w(self.space.next(w_iter), w(5))
        self.assertEqual_w(self.space.next(w_iter), w(3))
        self.assertEqual_w(self.space.next(w_iter), w(99))
        self.body0(w_iter)

    def body0(self, w_iter):
        self.assertRaises(OperationError, self.space.next, w_iter)
        self.assertRaises(OperationError, self.space.next, w_iter)

    def test_iter(self):
        w = self.space.wrap
        w_tuple = self.space.newtuple([w(5), w(3), w(99)])
        w_iter = W_SeqIterObject(self.space, w_tuple)
        self.body3(w_iter)
        
    def test_iter_builtin(self):
        w = self.space.wrap
        w_tuple = self.space.newtuple([w(5), w(3), w(99)])
        w_iter = self.space.iter(w_tuple)
        self.body3(w_iter)

    def test_emptyiter(self):
        w_list = self.space.newlist([])
        w_iter = W_SeqIterObject(self.space, w_list)
        self.body0(w_iter)
        
    def test_emptyiter_builtin(self):
        w_list = self.space.newlist([])
        w_iter = self.space.iter(w_list)
        self.body0(w_iter)

class TestW_IterObjectApp(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace('std')

    def test_user_iter(self):
        class C:
            def next(self):
                raise StopIteration
            def __iter__(self):
                return self
        self.assertEquals(list(C()), [])

    def test_iter_getitem(self):
        class C:
            def __getitem__(self, i):
                return range(2)[i]
        self.assertEquals(list(C()), range(2))

    def test_iter_fail_noseq(self):
        class C:
            pass
        self.assertRaises(TypeError,
                          iter,
                          C())
        

if __name__ == '__main__':
    testit.main()
