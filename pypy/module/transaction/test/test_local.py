import py
from pypy.conftest import gettestobjspace


class AppTestLocal:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['transaction'])

    def test_simple(self):
        import transaction
        x = transaction.local()
        x.foo = 42
        assert x.foo == 42
        assert hasattr(x, 'foo')
        assert not hasattr(x, 'bar')
        assert getattr(x, 'foo', 84) == 42
        assert getattr(x, 'bar', 84) == 84

    def test_transaction_local(self):
        import transaction
        transaction.set_num_threads(2)
        x = transaction.local()
        all_lists = []

        def f(n):
            if not hasattr(x, 'lst'):
                x.lst = []
                all_lists.append(x.lst)
            x.lst.append(n)
            if n > 0:
                transaction.add(f, n - 1)
                transaction.add(f, n - 1)
        transaction.add(f, 5)
        transaction.run()

        assert not hasattr(x, 'lst')
        assert len(all_lists) == 2
        total = all_lists[0] + all_lists[1]
        assert total.count(5) == 1
        assert total.count(4) == 2
        assert total.count(3) == 4
        assert total.count(2) == 8
        assert total.count(1) == 16
        assert total.count(0) == 32
        assert len(total) == 63

    def test_transaction_local_growing(self):
        import transaction
        transaction.set_num_threads(1)
        x = transaction.local()
        all_lists = []

        def f(n):
            if not hasattr(x, 'lst'):
                x.lst = []
                all_lists.append(x.lst)
            x.lst.append(n)
            if n > 0:
                transaction.add(f, n - 1)
                transaction.add(f, n - 1)
        transaction.add(f, 5)

        transaction.set_num_threads(2)    # more than 1 specified above
        transaction.run()

        assert not hasattr(x, 'lst')
        assert len(all_lists) == 2
        total = all_lists[0] + all_lists[1]
        assert total.count(5) == 1
        assert total.count(4) == 2
        assert total.count(3) == 4
        assert total.count(2) == 8
        assert total.count(1) == 16
        assert total.count(0) == 32
        assert len(total) == 63
