
"""
Extra tests for the pure Python PyPy _collections module
(not used in normal PyPy's)
"""

from pypy.conftest import gettestobjspace

class AppTestCollections:
    def test_copy(self):
        import _collections
        def f():
            return 42
        d = _collections.defaultdict(f, {2: 3})
        #
        d1 = d.copy()
        assert type(d1) is _collections.defaultdict
        assert len(d1) == 1
        assert d1[2] == 3
        assert d1[3] == 42
        #
        import copy
        d2 = copy.deepcopy(d)
        assert type(d2) is _collections.defaultdict
        assert len(d2) == 1
        assert d2[2] == 3
        assert d2[3] == 42
