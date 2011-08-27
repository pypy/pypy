import py
from pypy.conftest import gettestobjspace, option
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.celldict import ModuleCell, ModuleDictStrategy
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace, \
        BaseTestRDictImplementation, BaseTestDevolvedDictImplementation
from pypy.interpreter import gateway

from pypy.conftest import gettestobjspace, option

space = FakeSpace()

class TestCellDict(object):
    def test_basic_property_cells(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_DictMultiObject(space, strategy, storage)

        v1 = strategy.version
        d.setitem("a", 1)
        v2 = strategy.version
        assert v1 is not v2
        assert d.getitem("a") == 1
        assert d.strategy.getdictvalue_no_unwrapping(d, "a") == 1

        d.setitem("a", 2)
        v3 = strategy.version
        assert v2 is not v3
        assert d.getitem("a") == 2
        assert d.strategy.getdictvalue_no_unwrapping(d, "a").w_value == 2

        d.setitem("a", 3)
        v4 = strategy.version
        assert v3 is v4
        assert d.getitem("a") == 3
        assert d.strategy.getdictvalue_no_unwrapping(d, "a").w_value == 3

        d.delitem("a")
        v5 = strategy.version
        assert v5 is not v4
        assert d.getitem("a") is None
        assert d.strategy.getdictvalue_no_unwrapping(d, "a") is None

class AppTestModuleDict(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withcelldict": True})

    def w_impl_used(self, obj):
        if option.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")
        import __pypy__
        assert "ModuleDictStrategy" in __pypy__.internal_repr(obj)

    def test_check_module_uses_module_dict(self):
        m = type(__builtins__)("abc")
        self.impl_used(m.__dict__)

    def test_key_not_there(self):
        d = type(__builtins__)("abc").__dict__
        raises(KeyError, "d['def']")

    def test_fallback_evil_key(self):
        class F(object):
            def __hash__(self):
                return hash("s")
            def __eq__(self, other):
                return other == "s"
        d = type(__builtins__)("abc").__dict__
        d["s"] = 12
        assert d["s"] == 12
        assert d[F()] == d["s"]

        d = type(__builtins__)("abc").__dict__
        x = d.setdefault("s", 12)
        assert x == 12
        x = d.setdefault(F(), 12)
        assert x == 12

        d = type(__builtins__)("abc").__dict__
        x = d.setdefault(F(), 12)
        assert x == 12

        d = type(__builtins__)("abc").__dict__
        d["s"] = 12
        del d[F()]

        assert "s" not in d
        assert F() not in d


class TestModuleDictImplementation(BaseTestRDictImplementation):
    StrategyClass = ModuleDictStrategy

class TestModuleDictImplementationWithBuiltinNames(BaseTestRDictImplementation):
    StrategyClass = ModuleDictStrategy

    string = "int"
    string2 = "isinstance"


class TestDevolvedModuleDictImplementation(BaseTestDevolvedDictImplementation):
    StrategyClass = ModuleDictStrategy

class TestDevolvedModuleDictImplementationWithBuiltinNames(BaseTestDevolvedDictImplementation):
    StrategyClass = ModuleDictStrategy

    string = "int"
    string2 = "isinstance"


class AppTestCellDict(object):
    OPTIONS = {"objspace.std.withcelldict": True}

    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")
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
