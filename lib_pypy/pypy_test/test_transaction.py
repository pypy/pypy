import py
from lib_pypy import transaction

N = 1000
VERBOSE = False


def test_simple_random_order():
    for x in range(N):
        lst = []
        tq = transaction.TransactionQueue()
        for i in range(10):
            tq.add(lst.append, i)
        tq.run()
        if VERBOSE:
            print lst
        assert sorted(lst) == range(10), lst

def test_simple_fixed_order():
    for x in range(N):
        lst = []
        def do_stuff(i):
            lst.append(i)
            i += 1
            if i < 10:
                tq.add(do_stuff, i)
        tq = transaction.TransactionQueue()
        tq.add(do_stuff, 0)
        tq.run()
        if VERBOSE:
            print lst
        assert lst == range(10), lst

def test_simple_random_and_fixed_order():
    for x in range(N):
        lsts = ([], [], [], [], [])
        def do_stuff(i, j):
            lsts[i].append(j)
            j += 1
            if j < 10:
                tq.add(do_stuff, i, j)
        tq = transaction.TransactionQueue()
        for i in range(5):
            tq.add(do_stuff, i, 0)
        tq.run()
        if VERBOSE:
            print lsts
        assert lsts == (range(10),) * 5, lsts

def test_raise():
    class FooError(Exception):
        pass
    for x in range(N):
        lsts = ([], [], [], [], [], [], [], [], [], [])
        def do_stuff(i, j):
            lsts[i].append(j)
            j += 1
            if j < 5:
                tq.add(do_stuff, i, j)
            else:
                lsts[i].append('foo')
                raise FooError
        tq = transaction.TransactionQueue()
        for i in range(10):
            tq.add(do_stuff, i, 0)
        try:
            tq.run()
        except FooError:
            pass
        else:
            raise AssertionError("should have raised FooError")
        if VERBOSE:
            print lsts
        num_foos = 0
        for lst in lsts:
            if len(lst) < 5:
                assert lst == range(len(lst)), lst
            else:
                assert lst == range(5) + ['foo'], lst
                num_foos += 1
        assert num_foos == 1, lsts


def test_number_of_transactions_reported():
    tq = transaction.TransactionQueue()
    tq.add(lambda: None)
    tq.add(lambda: None)
    tq.run()
    assert tq.number_of_transactions_executed() == 2

    tq.run()
    assert tq.number_of_transactions_executed() == 2

    tq.add(lambda: None)
    tq.run()
    assert tq.number_of_transactions_executed() == 3

    tq.add(lambda: some_name_that_is_not_defined)
    try:
        tq.run()
    except NameError:
        pass
    else:
        raise AssertionError("should have raised NameError")
    assert tq.number_of_transactions_executed() == 4

    tq.add(tq.number_of_transactions_executed)
    try:
        tq.run()
    except transaction.TransactionError:
        pass
    else:
        raise AssertionError("should have raised TransactionError")

    def add_transactions(l):
        if l:
            for x in range(l[0]):
                tq.add(add_transactions, l[1:])

    tq = transaction.TransactionQueue()
    tq.add(add_transactions, [10, 10, 10])
    tq.run()
    assert tq.number_of_transactions_executed() == 1111

def test_unexecuted_transactions_after_exception():
    class FooError(Exception):
        pass
    class BarError(Exception):
        pass
    def raiseme(exc):
        raise exc
    seen = []
    tq = transaction.TransactionQueue()
    tq.add(raiseme, FooError)
    tq.add(raiseme, BarError)
    tq.add(seen.append, 42)
    tq.add(seen.append, 42)
    try:
        tq.run()
    except (FooError, BarError), e:
        seen_exc = e.__class__
    else:
        raise AssertionError("should have raised FooError or BarError")
    try:
        tq.run()
    except (FooError, BarError), e:
        assert e.__class__ != seen_exc
    else:
        raise AssertionError("unexecuted transactions have disappeared")
    for i in range(2):
        tq.run()
        assert seen == [42, 42]


def test_stmidset():
    s = transaction.stmidset()
    key1 = []
    key2 = []
    s.add(key1)
    assert key1 in s
    assert key2 not in s
    s.add(key2)
    assert key1 in s
    assert key2 in s
    s.remove(key1)
    assert key1 not in s
    assert key2 in s
    py.test.raises(KeyError, s.remove, key1)
    s.discard(key1)
    assert key1 not in s
    assert key2 in s
    s.discard(key2)
    assert key2 not in s

def test_stmiddict():
    d = transaction.stmiddict()
    key1 = []
    key2 = []
    py.test.raises(KeyError, "d[key1]")
    d[key1] = 5
    assert d[key1] == 5
    assert key1 in d
    assert d.get(key1) == 5
    assert d.get(key1, 42) == 5
    del d[key1]
    py.test.raises(KeyError, "d[key1]")
    assert key1 not in d
    assert d.get(key1) is None
    assert d.get(key1, 42) == 42
    assert d.setdefault(key1, 42) == 42
    assert d.setdefault(key1, 43) == 42
    assert d.setdefault(key2) is None
    assert d[key2] is None

def test_stmdict():
    d = transaction.stmdict()
    d["abc"] = "def"
    assert list(d.iterkeys()) == ["abc"]

def test_stmset():
    d = transaction.stmset()
    d.add("abc")
    assert list(d) == ["abc"]

def test_time_clock():
    assert isinstance(transaction.time(), float)
    assert isinstance(transaction.clock(), float)

def test_threadlocalproperty():
    class Foo(object):
        x = transaction.threadlocalproperty()
        y = transaction.threadlocalproperty(dict)
    foo = Foo()
    py.test.raises(AttributeError, "foo.x")
    d = foo.y
    assert d == {}
    assert d is foo.y
    foo.y['bar'] = 'baz'
    foo.x = 42
    foo.y = 43
    assert foo.x == 42
    assert foo.y == 43
    del foo.x
    del foo.y
    py.test.raises(AttributeError, "foo.x")
    assert foo.y == {}


def run_tests():
    for name in sorted(globals().keys()):
        if name.startswith('test_'):
            value = globals().get(name)
            if type(value) is type(run_tests):
                print name
                value()
    print 'all tests passed.'

if __name__ == '__main__':
    run_tests()
