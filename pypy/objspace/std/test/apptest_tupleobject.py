def test_is_true():
    assert not ()
    assert bool((5,))
    assert bool((5, 3))

def test_len():
    assert len(()) == 0
    assert len((5,)) == 1
    assert len((5, 3, 99, 1, 2, 3, 4, 5, 6)) == 9

def test_getitem():
    assert (5, 3)[0] == 5
    assert (5, 3)[1] == 3
    assert (5, 3)[-1] == 3
    assert (5, 3)[-2] == 5
    raises(IndexError, "(5, 3)[2]")
    raises(IndexError, "(5,)[1]")
    raises(IndexError, "()[0]")

def test_iter():
    t = (5, 3, 99)
    i = iter(t)
    assert i.next() == 5
    assert i.next() == 3
    assert i.next() == 99
    raises(StopIteration, i.next)

def test_contains():
    t = (5, 3, 99)
    assert 5 in t
    assert 99 in t
    assert not 11 in t
    assert not t in t

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
    foo_tuple = (foo1, foo2, foo3)
    foo42 in foo_tuple
    logger_copy = logger[:]  # prevent re-evaluation during pytest error print
    assert logger_copy == [(foo42, foo1), (foo42, foo2), (foo42, foo3)]

    del logger[:]
    foo2_bis = Foo(2, '2 bis')
    foo2_bis in foo_tuple
    logger_copy = logger[:]  # prevent re-evaluation during pytest error print
    assert logger_copy == [(foo2_bis, foo1), (foo2_bis, foo2)]

def test_add():
    t0 = ()
    t1 = (5, 3, 99)
    assert t0 + t0 == t0
    assert t1 + t0 == t1
    assert t1 + t1 == (5, 3, 99, 5, 3, 99)

def test_mul():
    assert () * 10 == ()
    assert (5,) * 3 == (5, 5, 5)
    assert (5, 2) * 2 == (5, 2, 5, 2)

def test_mul_identity():
    t = (1, 2, 3)
    assert (t * 1) is t

def test_mul_subtype():
    class T(tuple): pass
    t = T([1, 2, 3])
    assert (t * 1) is not t
    assert (t * 1) == t

def test_getslice_2():
    assert (5, 2, 3)[1:2] == (2,)

def test_eq():
    t0 = ()
    t1 = (5, 3, 99)
    t2 = (5, 3, 99)
    t3 = (5, 3, 99, -1)
    t4 = (5, 3, 9, 1)
    assert not t0 == t1
    assert t0 != t1
    assert t1 == t2
    assert t2 == t1
    assert t3 != t2
    assert not t3 == t2
    assert not t2 == t3
    assert t3 > t4
    assert t2 > t4
    assert t3 > t2
    assert t1 > t0
    assert t0 <= t0
    assert not t0 < t0
    assert t4 >= t0
    assert t3 >= t2
    assert t2 <= t3

def test_hash():
    # check that hash behaves as in 2.4 for at least 31 bits
    assert hash(()) & 0x7fffffff == 0x35d373
    assert hash((12,)) & 0x7fffffff == 0x1cca0557
    assert hash((12, 34)) & 0x7fffffff == 0x153e2a41

def test_getnewargs():
    assert () .__getnewargs__() == ((),)

def test_repr():
    assert repr((1,)) == '(1,)'
    assert repr(()) == '()'
    assert repr((1, 2, 3)) == '(1, 2, 3)'

def test_getslice():
    assert ('a', 'b', 'c').__getslice__(-17, 2) == ('a', 'b')

def test_count():
    assert ().count(4) == 0
    assert (1, 2, 3, 4).count(3) == 1
    assert (1, 2, 3, 4).count(5) == 0
    assert (1, 1, 1).count(1) == 3

def test_index():
    raises(ValueError, ().index, 4)
    (1, 2).index(1) == 0
    (3, 4, 5).index(4) == 1
    raises(ValueError, (1, 2, 3, 4).index, 5)
    assert (4, 2, 3, 4).index(4, 1) == 3
    assert (4, 4, 4).index(4, 1, 2) == 1
    raises(ValueError, (1, 2, 3, 4).index, 4, 0, 2)

def test_comparison():
    assert (() <  ()) is False
    assert (() <= ()) is True
    assert (() == ()) is True
    assert (() != ()) is False
    assert (() >  ()) is False
    assert (() >= ()) is True
    assert ((5,) <  ()) is False
    assert ((5,) <= ()) is False
    assert ((5,) == ()) is False
    assert ((5,) != ()) is True
    assert ((5,) >  ()) is True
    assert ((5,) >= ()) is True
    assert (() <  (5,)) is True
    assert (() <= (5,)) is True
    assert (() == (5,)) is False
    assert (() != (5,)) is True
    assert (() >  (5,)) is False
    assert (() >= (5,)) is False
    assert ((4,) <  (5,)) is True
    assert ((4,) <= (5,)) is True
    assert ((4,) == (5,)) is False
    assert ((4,) != (5,)) is True
    assert ((4,) >  (5,)) is False
    assert ((4,) >= (5,)) is False
    assert ((5,) <  (5,)) is False
    assert ((5,) <= (5,)) is True
    assert ((5,) == (5,)) is True
    assert ((5,) != (5,)) is False
    assert ((5,) >  (5,)) is False
    assert ((5,) >= (5,)) is True
    assert ((6,) <  (5,)) is False
    assert ((6,) <= (5,)) is False
    assert ((6,) == (5,)) is False
    assert ((6,) != (5,)) is True
    assert ((6,) >  (5,)) is True
    assert ((6,) >= (5,)) is True
    N = float('nan')
    assert ((N,) <  (5,)) is False
    assert ((N,) <= (5,)) is False
    assert ((N,) == (5,)) is False
    assert ((N,) != (5,)) is True
    assert ((N,) >  (5,)) is False
    assert ((N,) >= (5,)) is False
    assert ((5,) <  (N,)) is False
    assert ((5,) <= (N,)) is False
    assert ((5,) == (N,)) is False
    assert ((5,) != (N,)) is True
    assert ((5,) >  (N,)) is False
    assert ((5,) >= (N,)) is False

def test_eq_other_type():
    assert (() == object()) is False
    assert ((1,) == object()) is False
    assert ((1, 2) == object()) is False
    assert (() != object()) is True
    assert ((1,) != object()) is True
    assert ((1, 2) != object()) is True

def test_zip_two_lists():
    try:
        from __pypy__ import specialized_zip_2_lists
    except ImportError:
        specialized_zip_2_lists = zip
    else:
        raises(TypeError, specialized_zip_2_lists, [], ())
        raises(TypeError, specialized_zip_2_lists, (), [])
    assert specialized_zip_2_lists([], []) == [
        ]
    assert specialized_zip_2_lists([2, 3], []) == [
        ]
    assert specialized_zip_2_lists([2, 3], [4, 5, 6]) == [
        (2, 4), (3, 5)]
    assert specialized_zip_2_lists([4.1, 3.6, 7.2], [2.3, 4.8]) == [
        (4.1, 2.3), (3.6, 4.8)]
    assert specialized_zip_2_lists(["foo", "bar"], [6, 2]) == [
        ("foo", 6), ("bar", 2)]

def test_error_message_wrong_self():
    unboundmeth = tuple.__hash__
    e = raises(TypeError, unboundmeth, 42)
    assert "tuple" in str(e.value)
    if hasattr(unboundmeth, 'im_func'):
        e = raises(TypeError, unboundmeth.im_func, 42)
        assert "'tuple'" in str(e.value)
