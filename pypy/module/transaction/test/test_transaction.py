import py
from pypy.conftest import gettestobjspace


class AppTestTransaction: 
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['transaction'])

    def test_simple(self):
        import transaction
        lst = []
        transaction.add(lst.append, 5)
        transaction.add(lst.append, 6)
        transaction.add(lst.append, 7)
        transaction.run()
        assert sorted(lst) == [5, 6, 7]
