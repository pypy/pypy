import py
from pypy.conftest import gettestobjspace


class AppTestTransaction: 
    def setup_class(cls):
        py.test.skip("XXX not transactional!")
        cls.space = gettestobjspace(usemodules=['transaction'])

    def test_simple(self):
        import transaction
        lst = []
        transaction.add(lst.append, 5)
        transaction.add(lst.append, 6)
        transaction.add(lst.append, 7)
        transaction.run()
        assert sorted(lst) == [5, 6, 7]

    def test_almost_as_simple(self):
        import transaction
        lst = []
        def f(n):
            lst.append(n+0)
            lst.append(n+1)
            lst.append(n+2)
            lst.append(n+3)
            lst.append(n+4)
            lst.append(n+5)
            lst.append(n+6)
        transaction.add(f, 10)
        transaction.add(f, 20)
        transaction.add(f, 30)
        transaction.run()
        assert len(lst) == 7 * 3
        seen = set()
        for start in range(0, 21, 7):
            seen.append(lst[start])
            for index in range(7):
                assert lst[start + index] == lst[start] + index
        assert seen == set([10, 20, 30])
