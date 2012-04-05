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

