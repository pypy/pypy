import py
from lib_pypy import transaction

N = 1000
VERBOSE = False


def test_simple_random_order():
    for x in range(N):
        lst = []
        with transaction.TransactionQueue():
            for i in range(10):
                transaction.add(lst.append, i)
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
                transaction.add(do_stuff, i)
        with transaction.TransactionQueue():
            transaction.add(do_stuff, 0)
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
                transaction.add(do_stuff, i, j)
        with transaction.TransactionQueue():
            for i in range(5):
                transaction.add(do_stuff, i, 0)
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
                transaction.add(do_stuff, i, j)
            else:
                lsts[i].append('foo')
                raise FooError
        try:
            with transaction.TransactionQueue():
                for i in range(10):
                    transaction.add(do_stuff, i, 0)
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
    py.test.skip("not reimplemented")
    with transaction.TransactionQueue():
        transaction.add(lambda: None)
    assert transaction.number_of_transactions_in_last_run() == 1

    def add_transactions(l):
        if l:
            for x in range(l[0]):
                transaction.add(add_transactions, l[1:])

    with transaction.TransactionQueue():
        transaction.add(add_transactions, [10, 10, 10])
    assert transaction.number_of_transactions_in_last_run() == 1111


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
