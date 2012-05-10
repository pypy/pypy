from lib_pypy import transaction

N = 1000


def test_simple_random_order():
    for x in range(N):
        lst = []
        for i in range(10):
            transaction.add(lst.append, i)
        transaction.run()
        print lst
        assert sorted(lst) == range(10)

def test_simple_fixed_order():
    for x in range(N):
        lst = []
        def do_stuff(i):
            lst.append(i)
            i += 1
            if i < 10:
                transaction.add(do_stuff, i)
        transaction.add(do_stuff, 0)
        transaction.run()
        print lst
        assert lst == range(10)

def test_simple_random_and_fixed_order():
    for x in range(N):
        lsts = ([], [], [], [], [])
        def do_stuff(i, j):
            lsts[i].append(j)
            j += 1
            if j < 10:
                transaction.add(do_stuff, i, j)
        for i in range(5):
            transaction.add(do_stuff, i, 0)
        transaction.run()
        print lsts
        assert lsts == (range(10),) * 5
