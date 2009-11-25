# defaultdict Tests
# from CPython2.5

import sys
if sys.version_info < (2, 5):
    import py
    # the app-level defaultdict relies on the interp-level dict
    # calling __missing__()
    py.test.skip("these tests only run on top of CPython 2.5")

import copy

from pypy.lib.collections import defaultdict

def foobar():
    return list

class Test_defaultdict:
    
    def test_basic(self):
        d1 = defaultdict()
        assert d1.default_factory is None
        d1.default_factory = list
        d1[12].append(42)
        assert d1 == {12: [42]}
        d1[12].append(24)
        assert d1 == {12: [42, 24]}
        d1[13]
        d1[14]
        assert d1 == {12: [42, 24], 13: [], 14: []}
        assert d1[12] is not d1[13] is not d1[14]
        d2 = defaultdict(list, foo=1, bar=2)
        assert d2.default_factory == list
        assert d2 == {"foo": 1, "bar": 2}
        assert d2["foo"] == 1
        assert d2["bar"] == 2
        assert d2[42] == []
        assert "foo" in d2
        assert "foo" in d2.keys()
        assert "bar" in d2
        assert "bar" in d2.keys()
        assert 42 in d2
        assert 42 in d2.keys()
        assert 12 not in d2
        assert 12 not in d2.keys()
        d2.default_factory = None
        assert d2.default_factory == None
        raises(KeyError, d2.__getitem__, 15)
        raises(TypeError, defaultdict, 1)

    def test_missing(self):
        d1 = defaultdict()
        raises(KeyError, d1.__missing__, 42)
        d1.default_factory = list
        assert d1.__missing__(42) == []

    def test_repr(self):
        d1 = defaultdict()
        assert d1.default_factory == None
        assert repr(d1) == "defaultdict(None, {})"
        d1[11] = 41
        assert repr(d1) == "defaultdict(None, {11: 41})"
        d2 = defaultdict(int)
        assert d2.default_factory == int
        d2[12] = 42
        assert repr(d2) == "defaultdict(<type 'int'>, {12: 42})"
        def foo(): return 43
        d3 = defaultdict(foo)
        assert d3.default_factory is foo
        d3[13]
        assert repr(d3) == "defaultdict(%s, {13: 43})" % repr(foo)
        d4 = defaultdict(int)
        d4[14] = defaultdict()
        assert repr(d4) == "defaultdict(%s, {14: defaultdict(None, {})})" % repr(int)

    def test_recursive_repr(self):
        # Issue2045: stack overflow when default_factory is a bound method
        class sub(defaultdict):
            def __init__(self):
                self.default_factory = self._factory
            def _factory(self):
                return []
        d = sub()
        assert repr(d).startswith(
            "defaultdict(<bound method sub._factory of defaultdict(...")

    def test_copy(self):
        d1 = defaultdict()
        d2 = d1.copy()
        assert type(d2) == defaultdict
        assert d2.default_factory == None
        assert d2 == {}
        d1.default_factory = list
        d3 = d1.copy()
        assert type(d3) == defaultdict
        assert d3.default_factory == list
        assert d3 == {}
        d1[42]
        d4 = d1.copy()
        assert type(d4) == defaultdict
        assert d4.default_factory == list
        assert d4 == {42: []}
        d4[12]
        assert d4 == {42: [], 12: []}

    def test_shallow_copy(self):
        d1 = defaultdict(foobar, {1: 1})
        d2 = copy.copy(d1)
        assert d2.default_factory == foobar
        assert d2 == d1
        d1.default_factory = list
        d2 = copy.copy(d1)
        assert d2.default_factory == list
        assert d2 == d1

    def test_deep_copy(self):
        d1 = defaultdict(foobar, {1: [1]})
        d2 = copy.deepcopy(d1)
        assert d2.default_factory == foobar
        assert d2 == d1
        assert d1[1] is not d2[1]
        d1.default_factory = list
        d2 = copy.deepcopy(d1)
        assert d2.default_factory == list
        assert d2 == d1

