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
            def __next__(self):
                raise StopIteration
            def __iter__(self):
                return self
        assert list(C()) == []

    def test_iter_getitem(self):
        class C(object):
            def __getitem__(self, i):
                return range(2)[i]
        assert list(C()) == list(range(2))

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

    def test_list_iter_setstate(self):
        iterable = iter([1,2,3,4])
        assert next(iterable) == 1
        iterable.__setstate__(0)
        assert next(iterable) == 1
        iterable.__setstate__(-100)
        assert next(iterable) == 1
        raises(TypeError, iterable.__setstate__, '0')

    def test_reversed_iter_setstate(self):
        iterable = reversed([1,2,3,4])
        assert next(iterable) == 4
        iterable.__setstate__(0)
        assert next(iterable) == 1
        iterable.__setstate__(2)
        next(iterable); next(iterable)
        assert next(iterable) == 1
        iterable.__setstate__(3)
        assert next(iterable) == 4
        iterable.__setstate__(-1)
        raises(StopIteration, next, iterable)
        #
        iterable = reversed([1,2,3,4])
        iterable.__setstate__(-100)
        raises(StopIteration, next, iterable)
        #
        iterable = reversed([1,2,3,4])
        iterable.__setstate__(100)
        assert next(iterable) == 4
        assert next(iterable) == 3

    def test_forward_iter_reduce(self):
        T = "abc"
        iterable = iter(T)
        assert iterable.__reduce__() == (iter, (T, ), 0)
        assert next(iterable) == "a"
        assert iterable.__reduce__() == (iter, (T, ), 1)
        assert next(iterable) == "b"
        assert iterable.__reduce__() == (iter, (T, ), 2)
        assert next(iterable) == "c"
        assert iterable.__reduce__() == (iter, (T, ), 3)
        raises(StopIteration, next, iterable)
        assert (iterable.__reduce__() == (iter, ((), )) or   # pypy
                iterable.__reduce__() == (iter, ("", )))     # cpython

    def test_reversed_iter_reduce(self):
        T = [1, 2, 3, 4]
        iterable = reversed(T)
        assert iterable.__reduce__() == (reversed, (T, ), 3)
        assert next(iterable) == 4
        assert iterable.__reduce__() == (reversed, (T, ), 2)
        assert next(iterable) == 3
        assert iterable.__reduce__() == (reversed, (T, ), 1)
        assert next(iterable) == 2
        assert iterable.__reduce__() == (reversed, (T, ), 0)
        assert next(iterable) == 1
        assert iterable.__reduce__() == (reversed, (T, ), -1)
        raises(StopIteration, next, iterable)
        assert (iterable.__reduce__() == (iter, ((), )) or   # pypy
                iterable.__reduce__() == (iter, ([], )))     # cpython

    def test_no_len_on_tuple_iter(self):
        iterable = (1,2,3,4)
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_deque_iter(self):
        from _collections import deque
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
        class UserList(object):
            def __init__(self, i):
                self.i = i
            def __getitem__(self, i):
                return range(self.i)[i]
        iterable = UserList([1,2,3,4])
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_UserList_iter_reversed(self):
        class UserList(object):
            def __init__(self, i):
                self.i = i
            def __getitem__(self, i):
                return range(self.i)[i]
        iterable = UserList([1,2,3,4])
        raises(TypeError, len, iter(iterable))
        raises(TypeError, reversed, iterable)

    def test_no_len_on_UserList_reversed(self):
        iterable = [1,2,3,4]
        raises(TypeError, len, reversed(iterable))

    def test_reversed_frees_empty(self):
        import gc
        for typ in list, str:
            free = [False]
            class U(typ):
                def __del__(self):
                    free[0] = True
            r = reversed(U())
            raises(StopIteration, next, r)
            gc.collect(); gc.collect(); gc.collect()
            assert free[0]

    def test_reversed_mutation(self):
        n = 10
        d = list(range(n))
        it = reversed(d)
        next(it)
        next(it)
        assert it.__length_hint__() == n-2
        d.append(n)
        assert it.__length_hint__() == n-2
        d[1:] = []
        assert it.__length_hint__() == 0
        assert list(it) == []
        d.extend(range(20))
        assert it.__length_hint__() == 0

    def test_no_len_on_set_iter(self):
        iterable = set([1,2,3,4])
        raises(TypeError, len, iter(iterable))

    def test_no_len_on_xrange(self):
        iterable = range(10)
        raises(TypeError, len, iter(iterable))

    def test_contains(self):
        logger = []

        class Foo(object):

            def __init__(self, value, name=None):
                self.value = value
                self.name = name or value

            def __repr__(self):
                return '<Foo %s>' % self.name

            def __eq__(self, other):
                logger.append((self, other))
                return self.value == other.value

        foo1, foo2, foo3 = Foo(1), Foo(2), Foo(3)
        foo42 = Foo(42)
        foo_list = [foo1, foo2, foo3]
        foo42 in (x for x in foo_list)
        logger_copy = logger[:]  # prevent re-evaluation during pytest error print
        assert logger_copy == [(foo42, foo1), (foo42, foo2), (foo42, foo3)]

        del logger[:]
        foo2_bis = Foo(2, '2 bis')
        foo2_bis in (x for x in foo_list)
        logger_copy = logger[:]  # prevent re-evaluation during pytest error print
        assert logger_copy == [(foo2_bis, foo1), (foo2_bis, foo2)]
