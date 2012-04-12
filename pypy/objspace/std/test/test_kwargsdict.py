import py
from pypy.conftest import gettestobjspace, option
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace, W_DictMultiObject
from pypy.objspace.std.kwargsdict import *

space = FakeSpace()
strategy = KwargsDictStrategy(space)

def test_create():
    keys = ["a", "b", "c"]
    values = [1, 2, 3]
    storage = strategy.erase((keys, values))
    d = W_DictMultiObject(space, strategy, storage)
    assert d.getitem_str("a") == 1
    assert d.getitem_str("b") == 2
    assert d.getitem_str("c") == 3
    assert d.getitem(space.wrap("a")) == 1
    assert d.getitem(space.wrap("b")) == 2
    assert d.getitem(space.wrap("c")) == 3
    assert d.w_keys() == keys
    assert d.values() == values

def test_set_existing():
    keys = ["a", "b", "c"]
    values = [1, 2, 3]
    storage = strategy.erase((keys, values))
    d = W_DictMultiObject(space, strategy, storage)
    assert d.getitem_str("a") == 1
    assert d.getitem_str("b") == 2
    assert d.getitem_str("c") == 3
    assert d.setitem_str("a", 4) is None
    assert d.getitem_str("a") == 4
    assert d.getitem_str("b") == 2
    assert d.getitem_str("c") == 3
    assert d.setitem_str("b", 5) is None
    assert d.getitem_str("a") == 4
    assert d.getitem_str("b") == 5
    assert d.getitem_str("c") == 3
    assert d.setitem_str("c", 6) is None
    assert d.getitem_str("a") == 4
    assert d.getitem_str("b") == 5
    assert d.getitem_str("c") == 6
    assert d.getitem(space.wrap("a")) == 4
    assert d.getitem(space.wrap("b")) == 5
    assert d.getitem(space.wrap("c")) == 6
    assert d.w_keys() == keys
    assert d.values() == values
    assert keys == ["a", "b", "c"]
    assert values == [4, 5, 6]


def test_set_new():
    keys = ["a", "b", "c"]
    values = [1, 2, 3]
    storage = strategy.erase((keys, values))
    d = W_DictMultiObject(space, strategy, storage)
    assert d.getitem_str("a") == 1
    assert d.getitem_str("b") == 2
    assert d.getitem_str("c") == 3
    assert d.getitem_str("d") is None
    assert d.setitem_str("d", 4) is None
    assert d.getitem_str("a") == 1
    assert d.getitem_str("b") == 2
    assert d.getitem_str("c") == 3
    assert d.getitem_str("d") == 4
    assert d.w_keys() == keys
    assert d.values() == values
    assert keys == ["a", "b", "c", "d"]
    assert values == [1, 2, 3, 4]

def test_limit_size():
    storage = strategy.get_empty_storage()
    d = W_DictMultiObject(space, strategy, storage)
    for i in range(100):
        assert d.setitem_str("d%s" % i, 4) is None
    assert d.strategy is not strategy
    assert "StringDictStrategy" == d.strategy.__class__.__name__

def test_keys_doesnt_wrap():
    space = FakeSpace()
    space.newlist = None
    strategy = KwargsDictStrategy(space)
    keys = ["a", "b", "c"]
    values = [1, 2, 3]
    storage = strategy.erase((keys, values))
    d = W_DictMultiObject(space, strategy, storage)
    w_l = d.w_keys() # does not crash


from pypy.objspace.std.test.test_dictmultiobject import BaseTestRDictImplementation, BaseTestDevolvedDictImplementation
def get_impl(self):
    storage = strategy.erase(([], []))
    return W_DictMultiObject(space, strategy, storage)
class TestKwargsDictImplementation(BaseTestRDictImplementation):
    StrategyClass = KwargsDictStrategy
    get_impl = get_impl
    def test_delitem(self):
        pass # delitem devolves for now

class TestDevolvedKwargsDictImplementation(BaseTestDevolvedDictImplementation):
    get_impl = get_impl
    StrategyClass = KwargsDictStrategy


class AppTestKwargsDictStrategy(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")

    def w_get_strategy(self, obj):
        import __pypy__
        r = __pypy__.internal_repr(obj)
        return r[r.find("(") + 1: r.find(")")]

    def test_create(self):
        def f(**args):
            return args
        d = f(a=1)
        assert "KwargsDictStrategy" in self.get_strategy(d)

