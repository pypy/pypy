from pypy.objspace.std.iterobject import W_SeqIterObject
from pypy.interpreter.error import OperationError

class TestW_IterObject:

    def body3(self, w_iter):
        w = self.space.wrap
        assert self.space.eq_w(self.space.next(w_iter), w(5))
        assert self.space.eq_w(self.space.next(w_iter), w(3))
        assert self.space.eq_w(self.space.next(w_iter), w(99))
        self.body0(w_iter)

    def body0(self, w_iter):
        raises(OperationError, self.space.next, w_iter)
        raises(OperationError, self.space.next, w_iter)

    def test_iter(self):
        w = self.space.wrap
        w_tuple = self.space.newtuple([w(5), w(3), w(99)])
        w_iter = W_SeqIterObject(w_tuple)
        self.body3(w_iter)
        
    def test_iter_builtin(self):
        w = self.space.wrap
        w_tuple = self.space.newtuple([w(5), w(3), w(99)])
        w_iter = self.space.iter(w_tuple)
        self.body3(w_iter)

    def test_emptyiter(self):
        w_list = self.space.newlist([])
        w_iter = W_SeqIterObject(w_list)
        self.body0(w_iter)
        
    def test_emptyiter_builtin(self):
        w_list = self.space.newlist([])
        w_iter = self.space.iter(w_list)
        self.body0(w_iter)

class AppTestW_IterObjectApp:
    def test_user_iter(self):
        class C(object):
            def next(self):
                raise StopIteration
            def __iter__(self):
                return self
        assert list(C()) == []

    def test_iter_getitem(self):
        class C(object):
            def __getitem__(self, i):
                return range(2)[i]
        assert list(C()) == range(2)

    def test_iter_fail_noseq(self):
        class C(object):
            pass
        raises(TypeError,
                          iter,
                          C())

class AppTest_IterObject(object):
    def test_no_len_on_list_iter(self):
        iterable = [1,2,3,4]
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_tuple_iter(self):
        iterable = (1,2,3,4)
        raises(TypeError, len, iter(iterable))
        
    def test_no_len_on_deque_iter(self):
        from collections import deque
        iterable = deque([1,2,3,4])
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_reversed(self):
        it = reversed("foobar")
        raises(TypeError, len, it)

    def test_no_len_on_reversed_seqiter(self):
        # this one fails on CPython.  See http://bugs.python.org/issue3689
        it = reversed([5,6,7])
        raises(TypeError, len, it)

    def test_no_len_on_UserList_iter(self):
        from UserList import UserList
        iterable = UserList([1,2,3,4])
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_UserList_reversed(self):
        from UserList import UserList
        iterable = UserList([1,2,3,4])
        raises(TypeError, len, reversed(iterable))

    def test_no_len_on_set_iter(self):
        iterable = set([1,2,3,4])
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_xrange(self):
        iterable = xrange(10)
        raises(TypeError, len, iter(iterable))
