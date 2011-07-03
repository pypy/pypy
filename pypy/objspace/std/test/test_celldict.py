import py
from pypy.conftest import gettestobjspace, option
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.celldict import ModuleCell, ModuleDictStrategy
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.interpreter import gateway

space = FakeSpace()

class TestCellDict(object):
    def test_basic_property(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_DictMultiObject(space, strategy, storage)

        # replace getcell with getcell from strategy
        def f(key, makenew):
            return strategy.getcell(d, key, makenew)
        d.getcell = f

        d.setitem("a", 1)
        assert d.getcell("a", False) is d.getcell("a", False)
        acell = d.getcell("a", False)
        d.setitem("b", 2)
        assert d.getcell("b", False) is d.getcell("b", False)
        assert d.getcell("c", True) is d.getcell("c", True)

        assert d.getitem("a") == 1
        assert d.getitem("b") == 2

        d.delitem("a")
        py.test.raises(KeyError, d.delitem, "a")
        assert d.getitem("a") is None
        assert d.getcell("a", False) is acell
        assert d.length() == 1

        d.clear()
        assert d.getitem("a") is None
        assert d.getcell("a", False) is acell
        assert d.length() == 0

class AppTestCellDict(object):
    OPTIONS = {"objspace.std.withcelldict": True}

    def setup_class(cls):
        strategy = ModuleDictStrategy(cls.space)
        storage = strategy.get_empty_storage()
        cls.w_d = W_DictMultiObject(cls.space, strategy, storage)

    def test_popitem(self):
        import __pypy__

        d = self.d
        assert "ModuleDict" in __pypy__.internal_repr(d)
        raises(KeyError, d.popitem)
        d["a"] = 3
        x = d.popitem()
        assert x == ("a", 3)

    def test_degenerate(self):
        import __pypy__

        d = self.d
        assert "ModuleDict" in __pypy__.internal_repr(d)
        d["a"] = 3
        del d["a"]
        d[object()] = 5
        assert d.values() == [5]