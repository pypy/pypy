import random
import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import rstm


class FakeStmOperations:
    _in_transaction = 0
    _thread_id = 0
    _mapping = {}

    def in_transaction(self):
        return self._in_transaction

    def thread_id(self):
        return self._thread_id

    def _add(self, transactionptr):
        r = random.random()
        assert r not in self._pending    # very bad luck if it is
        self._pending[r] = transactionptr

    def run_all_transactions(self, initial_transaction_ptr, num_threads=4):
        self._pending = {}
        self._add(initial_transaction_ptr)
        thread_ids = [-10000 - 123 * i for i in range(num_threads)]  # random
        self._in_transaction = True
        try:
            while self._pending:
                self._thread_id = thread_ids.pop(0)
                thread_ids.append(self._thread_id)
                r, transactionptr = self._pending.popitem()
                transaction = self.cast_voidp_to_transaction(transactionptr)
                transaction._next_transaction = None
                nextptr = rstm._stm_run_transaction(transactionptr, 0)
                next = self.cast_voidp_to_transaction(nextptr)
                while next is not None:
                    self._add(self.cast_transaction_to_voidp(next))
                    next = next._next_transaction
        finally:
            self._in_transaction = False
            self._thread_id = 0
            del self._pending

    def cast_transaction_to_voidp(self, transaction):
        if transaction is None:
            return lltype.nullptr(rffi.VOIDP.TO)
        assert isinstance(transaction, rstm.Transaction)
        num = 10000 + len(self._mapping)
        self._mapping[num] = transaction
        return rffi.cast(rffi.VOIDP, num)

    def cast_voidp_to_transaction(self, transactionptr):
        if not transactionptr:
            return None
        num = rffi.cast(lltype.Signed, transactionptr)
        return self._mapping[num]

    def leaving(self):
        self._mapping.clear()

fake_stm_operations = FakeStmOperations()


def test_in_transaction():
    res = rstm.in_transaction()
    assert res is False
    res = rstm.thread_id()
    assert res == 0

def test_run_all_transactions_minimal():
    seen = []
    class Empty(rstm.Transaction):
        def run(self):
            res = rstm.in_transaction()
            seen.append(res is True)
            res = rstm.thread_id()
            seen.append(res != 0)
    rstm.run_all_transactions(Empty())
    assert seen == [True, True]

def test_run_all_transactions_recursive():
    seen = []
    class DoInOrder(rstm.Transaction):
        def run(self):
            assert self._next_transaction is None
            if len(seen) < 10:
                seen.append(len(seen))
                return [self]
    rstm.run_all_transactions(DoInOrder())
    assert seen == range(10)

def test_run_all_transactions_random_order():
    seen = []
    class AddToSeen(rstm.Transaction):
        def run(self):
            seen.append(self.value)
    class DoInOrder(rstm.Transaction):
        count = 0
        def run(self):
            assert self._next_transaction is None
            if self.count < 50:
                other = AddToSeen()
                other.value = self.count
                self.count += 1
                return [self, other]
    rstm.run_all_transactions(DoInOrder())
    assert seen != range(50) and sorted(seen) == range(50)

def test_raise():
    class MyException(Exception):
        pass
    class FooBar(rstm.Transaction):
        def run(self):
            raise MyException
    class DoInOrder(rstm.Transaction):
        def run(self):
            return [FooBar() for i in range(10)]
    py.test.raises(MyException, rstm.run_all_transactions, DoInOrder())

def test_threadlocal():
    py.test.skip("disabled")
    # not testing the thread-local factor, but only the general interface
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    p1 = Point(10, 2)
    p2 = Point(-1, 0)
    tl = rstm.ThreadLocal(Point)
    assert tl.getvalue() is None
    tl.setvalue(p1)
    assert tl.getvalue() is p1
    tl.setvalue(p2)
    assert tl.getvalue() is p2
    tl.setvalue(None)
    assert tl.getvalue() is None

def test_stm_is_enabled():
    assert rstm.stm_is_enabled() is None    # not translated
