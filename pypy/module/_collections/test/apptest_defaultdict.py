# spaceconfig = {"usemodules" : ["_collections"]}

from _collections import defaultdict
from pytest import raises

def test_basics():
    d = defaultdict(list)
    assert d.default_factory is list
    assert defaultdict.default_factory.__get__(d) is list
    l = d[5]
    d[5].append(42)
    d[5].append(43)
    assert l == [42, 43]
    l2 = []
    d[5] = l2
    d[5].append(44)
    assert l == [42, 43] and l2 == [44]

def test_module():
    assert repr(defaultdict) in (
        "<class 'collections.defaultdict'>",   # on PyPy
        "<type 'collections.defaultdict'>")    # on CPython

def test_keyerror_without_factory():
    for d1 in [defaultdict(), defaultdict(None)]:
        for key in ['foo', (1,)]:
            try:
                d1[key]
            except KeyError as err:
                assert err.args[0] == key
            else:
                assert 0, "expected KeyError"

def test_noncallable():
    raises(TypeError, defaultdict, [('a', 5)])
    d = defaultdict(None, [('a', 5)])
    assert list(d.items()) == [('a', 5)]

def test_kwds():
    d = defaultdict(default_factory=5)
    assert list(d.keys()) == ['default_factory']

def test_copy():
    def f():
        return 42
    d = defaultdict(f, {2: 3})
    #
    d1 = d.copy()
    assert type(d1) is defaultdict
    assert len(d1) == 1
    assert d1[2] == 3
    assert d1[3] == 42
    #
    import copy
    d2 = copy.deepcopy(d)
    assert type(d2) is defaultdict
    assert len(d2) == 1
    assert d2[2] == 3
    assert d2[3] == 42

def test_no_dict():
    assert not hasattr(defaultdict(), '__dict__')

def test_no_setattr():
    class D(defaultdict):
        def __setattr__(self, attr, name):
            raise AssertionError
    d = D(int)
    assert d['5'] == 0
    d['6'] += 3
    assert d['6'] == 3

def test_default_factory():
    f = lambda: 42
    d = defaultdict(f)
    assert d.default_factory is f
    d.default_factory = lambda: 43
    assert d['5'] == 43

    def test_reduce(self):
        import _collections
        d = _collections.defaultdict(None, {3: 4})
        dict_iter = d.__reduce__()[4]
        assert type(dict_iter) is type(iter(d.items()))

    def test_rec_repr(self):
        import _collections
        class X(_collections.defaultdict):
            def mydefault(self):
                pass
        d = X.__new__(X)
        d.__init__(d.mydefault)
        assert repr(d).endswith('X(..., {})>, {})')

    def test_subclass_repr(self):
        import _collections
        class subclass(_collections.defaultdict):
            pass
        assert repr(subclass()) == 'subclass(None, {})'
