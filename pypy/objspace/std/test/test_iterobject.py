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
    def setup_method(self,method):
        
        self.iterable = ''
    
    def test_len(self):#,iterable):
        self.iterable = (1,2,3,4)
        it = iter(self.iterable)
        for i in reversed(range(len(it))):
            assert len(it) == i+1
            x = it.next()
        raises(StopIteration, it.next)
        assert len(it) == 0
    
    
class AppTest_lenTuple(AppTest_IterObject):
    
    def setup_method(self,method):
        self.iterable = (1,2,3,4)
        
    def test_iter_len_deque(self):
        from collections import deque

        iterable = deque((1,2,3,4))
        it = iter(iterable)
        for i in reversed(range(len(it))):
            assert len(it) == i+1
            x = it.next()
            
        raises(StopIteration, it.next)
        assert len(it) == 0

    def test_iter_len_reversed(self):
        iterable = reversed((1,2,3,4))
        it = iter(iterable)
        for i in reversed(range(len(it))):
            assert len(it) == i+1
            x = it.next()
        raises(StopIteration, it.next)
        assert len(it) == 0

    def test_len_reversed_seqiter(self):
        it = reversed([5,6,7])
        assert iter(it) is it
        assert len(it) == 3
        assert it.next() == 7
        assert len(it) == 2
        assert it.next() == 6
        assert len(it) == 1
        assert it.next() == 5
        assert len(it) == 0
        raises(StopIteration, it.next)
        assert len(it) == 0

    def test_mutation_list(self):
        n = 5
        d = range(n)
        it = iter(d)
        it.next()
        it.next()
        assert len(it) == n-2
        d.append(n)
        assert len(it) == n-1  # grow with append
        d[1:] = []
        assert len(it) == 0
        assert list(it) == []
        d.extend(xrange(20))
        assert len(it) == 0

    def test_mutation_list_reversed(self):
        n = 5
        d = range(n)
        it = reversed(d)
        it.next()
        it.next()
        assert len(it) == n-2
        d.append(n)
        assert len(it) == n-2  # Ignore append
        d[1:] = []
        assert len(it) == 0
        assert list(it) == []
        d.extend(xrange(20))
        assert len(it) == 0

    def test_mutation_seqiter(self):
        from UserList import UserList
        n = 5
        d = UserList(range(n))
        it = iter(d)
        it.next()
        it.next()
        assert len(it) == n-2
        d.append(n)
        assert len(it) == n-1  # grow with append
        d[1:] = []
        assert len(it) == 0
        assert list(it) == []
        d.extend(xrange(20))
        assert len(it) == 0

    def test_mutation_seqiter_reversed(self):
        from UserList import UserList
        n = 5
        d = UserList(range(n))
        it = reversed(d)
        it.next()
        it.next()
        assert len(it) == n-2
        d.append(n)
        assert len(it) == n-2  # ignore append
        d[1:] = []
        assert len(it) == 0
        assert list(it) == []
        d.extend(xrange(20))
        assert len(it) == 0
