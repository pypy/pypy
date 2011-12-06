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

    def test_keyerror_without_factory(self):
        from _collections import defaultdict
        for d1 in [defaultdict(), defaultdict(None)]:
            for key in ['foo', (1,)]:
                try:
                    d1[key]
                except KeyError, err:
                    assert err.args[0] == key
                else:
                    assert 0, "expected KeyError"

    def test_noncallable(self):
        from _collections import defaultdict
        raises(TypeError, defaultdict, [('a', 5)])
        d = defaultdict(None, [('a', 5)])
        assert d.items() == [('a', 5)]

    def test_kwds(self):
        from _collections import defaultdict
        d = defaultdict(default_factory=5)
        assert d.keys() == ['default_factory']

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
