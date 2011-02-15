import py
from pypy.conftest import gettestobjspace

class AppTestBasic:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_collections'])

    def test_basics(self):
        from _collections import defaultdict
        d = defaultdict(list)
        l = d[5]
        d[5].append(42)
        d[5].append(43)
        assert l == [42, 43]
        l2 = []
        d[5] = l2
        d[5].append(44)
        assert l == [42, 43] and l2 == [44]
