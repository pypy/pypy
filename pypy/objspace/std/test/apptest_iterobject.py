from _collections import deque
import gc

def test_no_len_on_list_iter():
    iterable = [1,2,3,4]
    raises(TypeError, len, iter(iterable))

def test_no_len_on_tuple_iter():
    iterable = (1,2,3,4)
    raises(TypeError, len, iter(iterable))
    
def test_no_len_on_deque_iter():
    iterable = deque([1,2,3,4])
    raises(TypeError, len, iter(iterable))

def test_no_len_on_reversed():
    it = reversed("foobar")
    raises(TypeError, len, it)

def test_no_len_on_reversed_seqiter():
    # this one fails on CPython.  See http://bugs.python.org/issue3689
    it = reversed([5,6,7])
    raises(TypeError, len, it)

def test_no_len_on_UserList_iter_reversed():
    import sys, _abcoll
    sys.modules['collections'] = _abcoll
    from UserList import UserList
    iterable = UserList([1,2,3,4])
    raises(TypeError, len, iter(iterable))
    raises(TypeError, len, reversed(iterable))
    del sys.modules['collections']

def test_reversed_frees_empty():
    for typ in list, unicode:
        free = [False]
        class U(typ):
            def __del__(self):
                free[0] = True
        r = reversed(U())
        raises(StopIteration, next, r)
        gc.collect(); gc.collect(); gc.collect()
        assert free[0]

def test_reversed_mutation():
    n = 10
    d = range(n)
    it = reversed(d)
    next(it)
    next(it)
    assert it.__length_hint__() == n-2
    d.append(n)
    assert it.__length_hint__() == n-2
    d[1:] = []
    assert it.__length_hint__() == 0
    assert list(it) == []
    d.extend(xrange(20))
    assert it.__length_hint__() == 0

def test_no_len_on_set_iter():
    iterable = set([1,2,3,4])
    raises(TypeError, len, iter(iterable))

def test_no_len_on_xrange():
    iterable = xrange(10)
    raises(TypeError, len, iter(iterable))

def test_contains():
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

#from  AppTestW_IterObjectApp
def test_user_iter():
    class C(object):
        def next(self):
            raise StopIteration
        def __iter__(self):
            return self
    assert list(C()) == []

def test_iter_getitem():
    class C(object):
        def __getitem__(self, i):
            return range(2)[i]
    assert list(C()) == range(2)

def test_iter_fail_noseq():
    class C(object):
        pass
    raises(TypeError,
                      iter,
                      C())
