# spaceconfig = {"usemodules" : ["_collections"]}

from _collections import deque
from pytest import raises

def test_basics():
    assert deque.__module__ == 'collections'

    d = deque(xrange(-5125, -5000))
    d.__init__(xrange(200))
    for i in xrange(200, 400):
        d.append(i)
    for i in reversed(xrange(-200, 0)):
        d.appendleft(i)
    assert list(d) == range(-200, 400)
    assert len(d) == 600

    left = [d.popleft() for i in xrange(250)]
    assert left == range(-200, 50)
    assert list(d) == range(50, 400)

    right = [d.pop() for i in xrange(250)]
    right.reverse()
    assert right == range(150, 400)
    assert list(d) == range(50, 150)

def test_maxlen():
    raises(ValueError, deque, 'abc', -1)
    raises(ValueError, deque, 'abc', -2)
    it = iter(range(10))
    d = deque(it, maxlen=3)
    assert list(it) == []
    assert repr(d) == 'deque([7, 8, 9], maxlen=3)'
    assert list(d) == range(7, 10)
    d.appendleft(3)
    assert list(d) == [3, 7, 8]
    d.extend([20, 21])
    assert list(d) == [8, 20, 21]
    d.extendleft([-7, -6])
    assert list(d) == [-6, -7, 8]

def test_maxlen_zero():
    it = iter(range(100))
    d = deque(it, maxlen=0)
    assert list(d) == []
    assert list(it) == []
    d.extend(range(100))
    assert list(d) == []
    d.extendleft(range(100))
    assert list(d) == []

def test_maxlen_attribute():
    assert deque().maxlen is None
    assert deque('abc').maxlen is None
    assert deque('abc', maxlen=4).maxlen == 4
    assert deque('abc', maxlen=0).maxlen == 0
    raises((AttributeError, TypeError), "deque('abc').maxlen = 10")

def test_runtimeerror():
    d = deque('abcdefg')
    it = iter(d)
    d.pop()
    raises(RuntimeError, it.next)
    #
    d = deque('abcdefg')
    it = iter(d)
    d.append(d.pop())
    raises(RuntimeError, it.next)
    #
    d = deque()
    it = iter(d)
    d.append(10)
    raises(RuntimeError, it.next)

def test_count():
    for s in ('', 'abracadabra', 'simsalabim'*50+'abc'):
        s = list(s)
        d = deque(s)
        for letter in 'abcdeilmrs':
            assert s.count(letter) == d.count(letter)
    class MutatingCompare:
        def __eq__(self, other):
            d.pop()
            return True
    m = MutatingCompare()
    d = deque([1, 2, 3, m, 4, 5])
    raises(RuntimeError, d.count, 3)

def test_comparisons():
    d = deque('xabc'); d.popleft()
    for e in [d, deque('abc'), deque('ab'), deque(), list(d)]:
        assert (d==e) == (type(d)==type(e) and list(d)==list(e))
        assert (d!=e) == (not(type(d)==type(e) and list(d)==list(e)))

    args = map(deque, ('', 'a', 'b', 'ab', 'ba', 'abc', 'xba', 'xabc', 'cba'))
    for x in args:
        for y in args:
            assert (x == y) == (list(x) == list(y))
            assert (x != y) == (list(x) != list(y))
            assert (x <  y) == (list(x) <  list(y))
            assert (x <= y) == (list(x) <= list(y))
            assert (x >  y) == (list(x) >  list(y))
            assert (x >= y) == (list(x) >= list(y))
            assert cmp(x,y) == cmp(list(x),list(y))

def test_extend():
    d = deque('a')
    d.extend('bcd')
    assert list(d) == list('abcd')
    d.extend(d)
    assert list(d) == list('abcdabcd')

def test_iadd():
    d = deque('a')
    original_d = d
    d += 'bcd'
    assert list(d) == list('abcd')
    d += d
    assert list(d) == list('abcdabcd')
    assert original_d is d

def test_extendleft():
    d = deque('a')
    d.extendleft('bcd')
    assert list(d) == list(reversed('abcd'))
    d.extendleft(d)
    assert list(d) == list('abcddcba')

def test_getitem():
    n = 200
    l = xrange(1000, 1000 + n)
    d = deque(l)
    for j in xrange(-n, n):
        assert d[j] == l[j]
    raises(IndexError, "d[-n-1]")
    raises(IndexError, "d[n]")

def test_setitem():
    n = 200
    d = deque(xrange(n))
    for i in xrange(n):
        d[i] = 10 * i
    assert list(d) == [10*i for i in xrange(n)]
    l = list(d)
    for i in xrange(1-n, 0, -3):
        d[i] = 7*i
        l[i] = 7*i
    assert list(d) == l

def test_delitem():
    d = deque("abcdef")
    del d[-2]
    assert list(d) == list("abcdf")

def test_reverse():
    d = deque(xrange(1000, 1200))
    d.reverse()
    assert list(d) == list(reversed(range(1000, 1200)))
    #
    n = 100
    data = map(str, range(n))
    for i in range(n):
        d = deque(data[:i])
        r = d.reverse()
        assert list(d) == list(reversed(data[:i]))
        assert r is None
        d.reverse()
        assert list(d) == data[:i]

def test_rotate():
    s = tuple('abcde')
    n = len(s)

    d = deque(s)
    d.rotate(1)             # verify rot(1)
    assert ''.join(d) == 'eabcd'

    d = deque(s)
    d.rotate(-1)            # verify rot(-1)
    assert ''.join(d) == 'bcdea'
    d.rotate()              # check default to 1
    assert tuple(d) == s

    d.rotate(500000002)
    assert tuple(d) == tuple('deabc')
    d.rotate(-5000002)
    assert tuple(d) == tuple(s)

def test_len():
    d = deque('ab')
    assert len(d) == 2
    d.popleft()
    assert len(d) == 1
    d.pop()
    assert len(d) == 0
    raises(IndexError, d.pop)
    raises(IndexError, d.popleft)
    assert len(d) == 0
    d.append('c')
    assert len(d) == 1
    d.appendleft('d')
    assert len(d) == 2
    d.clear()
    assert len(d) == 0
    assert list(d) == []

def test_remove():
    d = deque('abcdefghcij')
    d.remove('c')
    assert d == deque('abdefghcij')
    d.remove('c')
    assert d == deque('abdefghij')
    raises(ValueError, d.remove, 'c')
    assert d == deque('abdefghij')

def test_repr():
    d = deque(xrange(20))
    e = eval(repr(d))
    assert d == e
    d.append(d)
    assert '...' in repr(d)

def test_hash():
    raises(TypeError, hash, deque('abc'))

def test_roundtrip_iter_init():
    d = deque(xrange(200))
    e = deque(d)
    assert d is not e
    assert d == e
    assert list(d) == list(e)

def test_reduce():
    #
    d = deque('hello world')
    r = d.__reduce__()
    assert r == (deque, (list('hello world'),))
    #
    d = deque('hello world', 42)
    r = d.__reduce__()
    assert r == (deque, (list('hello world'), 42))
    #
    class D(deque):
        pass
    d = D('hello world')
    d.a = 5
    r = d.__reduce__()
    assert r == (D, (list('hello world'), None), {'a': 5})
    #
    class D(deque):
        pass
    d = D('hello world', 42)
    d.a = 5
    r = d.__reduce__()
    assert r == (D, (list('hello world'), 42), {'a': 5})

def test_copy():
    import copy
    mut = [10]
    d = deque([mut])
    e = copy.copy(d)
    assert d is not e
    assert d == e
    mut[0] = 11
    assert d == e

def test_reversed():
    for s in ('abcd', xrange(200)):
        assert list(reversed(deque(s))) == list(reversed(s))

def test_free():
    import gc
    class X(object):
        freed = False
        def __del__(self):
            X.freed = True
    d = deque()
    d.append(X())
    d.pop()
    gc.collect(); gc.collect(); gc.collect()
    assert X.freed

def test_index_method():
    d = deque([1, 2, 3, 4, 5])
    class A(object):
        def __index__(self):
            return 1
    assert d[A()] == 2

def test_index_method_mutates():
    d = deque([1, 2, 3, 4, 5])
    class A(object):
        def __index__(self):
            d.clear()
            return 1
    with raises(IndexError):
        d[A()]
    d = deque([1, 2, 3, 4, 5])
    with raises(IndexError):
        d[A()] = 2
