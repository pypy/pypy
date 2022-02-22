# spaceconfig = {"usemodules" : ["_collections"]}

from _collections import OrderedDict

def test_ordereddict_present():
    assert issubclass(OrderedDict, dict)
    assert hasattr(OrderedDict, 'move_to_end')

def test_recursive_repr():
    d = OrderedDict()
    d[1] = d
    assert repr(d) == 'OrderedDict([(1, ...)])'

def test_subclass():
    class MyODict(OrderedDict):
        def __setitem__(self, key, value):
            super().__setitem__(key, 42)
    d = MyODict(x=1)
    assert d['x'] == 42
    d.update({'y': 2})
    assert d['y'] == 42

def test_reversed():
    import sys

    pairs = [('c', 1), ('b', 2), ('a', 3), ('d', 4), ('e', 5), ('f', 6)]
    od = OrderedDict(pairs)
    if '__pypy__' in sys.builtin_module_names:
        # dict ordering is wrong when testing interpreted on top of CPython
        pairs = list(dict(od).items())
    assert list(reversed(od)) == [t[0] for t in reversed(pairs)]
    assert list(reversed(od.keys())) == [t[0] for t in reversed(pairs)]
    assert list(reversed(od.values())) == [t[1] for t in reversed(pairs)]
    assert list(reversed(od.items())) == list(reversed(pairs))

def test_call_key_first():

    calls = []
    class Spam:
        def keys(self):
            calls.append('keys')
            return ()
        def items(self):
            calls.append('items')
            return ()

    OrderedDict(Spam())
    assert calls == ['keys']
