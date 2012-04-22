import random
import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import rstm


class FakeStmOperations:
    _in_transaction = 0
    _mapping = {}

    def in_transaction(self):
        return self._in_transaction

    def _add(self, transactionptr):
        r = random.random()
        assert r not in self._pending    # very bad luck if it is
        self._pending[r] = transactionptr

    def run_all_transactions(self, initial_transaction_ptr, num_threads=4):
        self._pending = {}
        self._add(initial_transaction_ptr)
        while self._pending:
            r, transactionptr = self._pending.popitem()
            nextptr = rstm._stm_run_transaction(transactionptr, 0)
            next = self.cast_voidp_to_transaction(nextptr)
            while next is not None:
                self._add(self.cast_transaction_to_voidp(next))
                next = next._next_transaction
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

def test_run_all_transactions_minimal():
    seen = []
    class Empty(rstm.Transaction):
        def run(self):
            seen.append(42)
    rstm.run_all_transactions(Empty())
    assert seen == [42]

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
