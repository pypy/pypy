import time
from pypy.module.transaction import interp_transaction


class FakeSpace:
    def new_exception_class(self, name):
        return "some error class"
    def call_args(self, w_callback, args):
        w_callback(*args)


def test_linear_list():
    space = FakeSpace()
    interp_transaction.state.startup(space)
    seen = []
    #
    def do(n):
        seen.append(n)
        if n < 200:
            interp_transaction.add(space, do, (n+1,))
    #
    interp_transaction.add(space, do, (0,))
    assert seen == []
    interp_transaction.run(space)
    assert seen == range(201)


def test_tree_of_transactions():
    space = FakeSpace()
    interp_transaction.state.startup(space)
    seen = []
    #
    def do(level):
        seen.append(level)
        if level < 11:
            interp_transaction.add(space, do, (level+1,))
            interp_transaction.add(space, do, (level+1,))
    #
    interp_transaction.add(space, do, (0,))
    assert seen == []
    interp_transaction.run(space)
    for i in range(12):
        assert seen.count(i) == 2 ** i
    assert len(seen) == 2 ** 12 - 1


def test_transactional_simple():
    space = FakeSpace()
    interp_transaction.state.startup(space)
    lst = []
    def f(n):
        lst.append(n+0)
        lst.append(n+1)
        time.sleep(0.05)
        lst.append(n+2)
        lst.append(n+3)
        lst.append(n+4)
        time.sleep(0.25)
        lst.append(n+5)
        lst.append(n+6)
    interp_transaction.add(space, f, (10,))
    interp_transaction.add(space, f, (20,))
    interp_transaction.add(space, f, (30,))
    interp_transaction.run(space)
    assert len(lst) == 7 * 3
    seen = set()
    for start in range(0, 21, 7):
        seen.add(lst[start])
        for index in range(7):
            assert lst[start + index] == lst[start] + index
    assert seen == set([10, 20, 30])
