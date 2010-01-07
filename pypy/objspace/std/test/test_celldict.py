import py
from pypy.conftest import gettestobjspace, option
from pypy.objspace.std.celldict import ModuleCell, ModuleDictImplementation
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.interpreter import gateway

space = FakeSpace()

class TestCellDict(object):
    def test_basic_property(self):
        d = ModuleDictImplementation(space)
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
