import autopath
from pypy.objspace.std.iterobject import W_SeqIterObject
from pypy.interpreter.error import OperationError

objspacename = 'std'

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

class AppTestW_IterObjectApp:
    def test_user_iter(self):
        class C:
            def next(self):
                raise StopIteration
            def __iter__(self):
                return self
        assert list(C()) == []

    def test_iter_getitem(self):
        class C:
            def __getitem__(self, i):
                return range(2)[i]
        assert list(C()) == range(2)

    def test_iter_fail_noseq(self):
        class C:
            pass
        raises(TypeError,
                          iter,
                          C())
