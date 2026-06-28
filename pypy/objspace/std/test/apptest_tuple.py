from pytest import raises


def test_is_true():
    assert not ()
    assert bool((5,))
    assert bool((5, 3))


def test_len():
    assert len(()) == 0
    assert len((5,)) == 1
    assert len((5, 3, 99, 1, 2, 3, 4, 5, 6)) == 9
    assert len((5, 3, 99) * 111) == 333


def test_getitem():
    assert (5, 3)[0] == 5
    assert (5, 3)[1] == 3
    assert (5, 3)[-1] == 3
    assert (5, 3)[-2] == 5
    raises(IndexError, lambda: (5, 3)[2])
    raises(IndexError, lambda: (5,)[1])
    raises(IndexError, lambda: ()[0])


def test_iter():
    t = (5, 3, 99)
    i = iter(t)
    assert next(i) == 5
    assert next(i) == 3
    assert next(i) == 99
    raises(StopIteration, next, i)


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
    assert logger_copy == [(foo1, foo42), (foo2, foo42), (foo3, foo42)]

    del logger[:]
    foo2_bis = Foo(2, '2 bis')
    foo2_bis in foo_tuple
    logger_copy = logger[:]  # prevent re-evaluation during pytest error print
    assert logger_copy == [(foo1, foo2_bis), (foo2, foo2_bis)]


def test_add():
    t0 = ()
    t1 = (5, 3, 99)
    t2 = (-7,) * 111
    assert t0 + t0 == t0
    assert t1 + t0 == t1
    assert t0 + t2 == t2
    assert t1 + t1 == (5, 3, 99, 5, 3, 99)


def test_mul():
    assert () * 10 == ()
    assert (5,) * 3 == (5, 5, 5)
    assert 3 * (5,) == (5, 5, 5)
    assert (5, 2) * 2 == (5, 2, 5, 2)


def test_mul_identity():
    t = (1, 2, 3)
    assert (t * 1) is t


def test_mul_subtype():
    class T(tuple): pass
    t = T([1, 2, 3])
    assert (t * 1) is not t
    assert (t * 1) == t


def test_getslice():
    assert (5, 2, 3)[1:2] == (2,)
    assert ('a', 'b', 'c')[-17: 2] == ('a', 'b')
    for testtuple in [(), (5, 3, 99), tuple(range(5, 555, 10))]:
        for start in [-2, -1, 0, 1, 10]:
            for end in [-1, 0, 2, 999]:
                assert testtuple[start:end:1] == testtuple[start:end]
    assert (5, 7, 1, 4)[3:1:-2] == (4,)
    assert (5, 7, 1, 4)[3:0:-2] == (4, 7)
    assert (5, 7, 1, 4)[3:-1:-2] == ()
    assert (5, 7, 1, 4)[-2:11:2] == (1,)
    assert (5, 7, 1, 4)[-3:11:2] == (7, 4)
    assert (5, 7, 1, 4)[-5:11:2] == (5, 1)


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
    # check that hash behaves as in 3.8
    import sys
    is_32 = sys.maxsize == 2 ** 31 - 1
    def check_one_exact(t, h32, h64):
        h = hash(t)
        if is_32:
            assert h == h32
        else:
            assert h == h64

    check_one_exact((), 750394483, 5740354900026072187)
    check_one_exact((0,), 1214856301, -8753497827991233192)
    check_one_exact((0, 0), -168982784, -8458139203682520985)
    check_one_exact((0.5,), 2077348973, -408149959306781352)
    check_one_exact((0.5, (), (-2, 3, (4, 6))), 714642271,
                    -1845940830829704396)


def test_getnewargs():
    assert () .__getnewargs__() == ((),)


def test_repr():
    assert repr((1,)) == '(1,)'
    assert repr(()) == '()'
    assert repr((1, 2, 3)) == '(1, 2, 3)'
    assert repr(('\xe9',)) == "('\xe9',)"
    assert repr(('\xe9', 1)) == "('\xe9', 1)"


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


def test_error_message_wrong_self():
    unboundmeth = tuple.__hash__
    e = raises(TypeError, unboundmeth, 42)
    assert "tuple" in str(e.value)
    if hasattr(unboundmeth, 'im_func'):
        e = raises(TypeError, unboundmeth.im_func, 42)
        assert "'tuple'" in str(e.value)


def test_tuple_new_pos_only():
    with raises(TypeError):
        tuple(sequence=[])


def test_error_not_iteratable():
    with raises(TypeError) as excinfo:
        tuple(1)
    assert str(excinfo.value) == "'int' object is not iterable"


def test_error_msg_index():
    with raises(TypeError) as excinfo:
        a = None
        (1, 2, 3)[a]
    assert str(excinfo.value) == "tuple indices must be integers or slices, not NoneType"


def test_subclass_kwarg():
    class bare_subclass(tuple):
        pass
    with raises(TypeError):
        bare_subclass((), newarg=3)

    class subclass_with_new(tuple):
        def __new__(cls, arg, newarg=None):
            self = super().__new__(cls, arg)
            self.newarg = newarg
            return self
    u = subclass_with_new([1, 2], newarg=3)
    assert u.newarg == 3

    class subclass_with_init(tuple):
        def __init__(self, arg, newarg=None):
            self.newarg = newarg
    u = subclass_with_init([1, 2], newarg=3)
    assert u.newarg == 3

def test_hash_cache():
    # Test that a tuple's hash is only called once then cached.
    # This will fail on CPython until 3.14.
    ncalled = [0]
    class A():
        def __hash__(self):
            ncalled[0] += 1
            return 123

    t = (A(), 1, 2, 3)
    val = hash(t)
    val2 = hash(t)
    assert val == val2
    assert ncalled[0] == 1
