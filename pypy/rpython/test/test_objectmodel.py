import py
from pypy.rpython.objectmodel import *
from pypy.rpython.test.test_llinterp import interpret


def test_we_are_translated():
    assert we_are_translated() == False

    def fn():
        return we_are_translated()
    res = interpret(fn, [])
    assert res is True

def test_r_dict():
    def key_eq(key1, key2):
        return key1[0] == key2[0]   # only the 1st character is relevant
    def key_hash(key):
        return ord(key[0])
    d = r_dict(key_eq, key_hash)
    d['hello'] = 42
    assert d['hi there'] == 42
    py.test.raises(KeyError, 'd["dumb"]')
    assert len(d) == 1
    assert 'oops' not in d
    assert list(d) == ['hello']
    assert d.get('hola', -1) == 42
    assert d.get('salut', -1) == -1
    d1 = d.copy()
    del d['hu!']
    assert len(d) == 0
    assert d1.keys() == ['hello']
    d.update(d1)
    assert d.values() == [42]
    assert d.items() == [('hello', 42)]
    assert list(d.iterkeys()) == ['hello']
    assert list(d.itervalues()) == [42]
    assert list(d.iteritems()) == [('hello', 42)]
    d.clear()
    assert d.keys() == []
