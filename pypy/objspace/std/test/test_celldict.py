import py

from pypy.objspace.std.celldict import ModuleDictStrategy
from pypy.objspace.std.dictmultiobject import W_DictObject, W_ModuleDictObject
from pypy.objspace.std.test.test_dictmultiobject import (
    BaseTestRDictImplementation, BaseTestDevolvedDictImplementation, FakeSpace,
    FakeString)

space = FakeSpace()

class TestCellDict(object):
    FakeString = FakeString

    def test_basic_property_cells(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_ModuleDictObject(space, strategy, storage)

        v1 = strategy.version
        key = "a"
        w_key = self.FakeString(key)
        d.setitem(w_key, 1)
        v2 = strategy.version
        assert v1 is not v2
        assert d.getitem(w_key) == 1
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key) == 1

        d.setitem(w_key, 2)
        v3 = strategy.version
        assert v2 is not v3
        assert d.getitem(w_key) == 2
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key).w_value == 2

        d.setitem(w_key, 3)
        v4 = strategy.version
        assert v3 is v4
        assert d.getitem(w_key) == 3
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key).w_value == 3

        d.delitem(w_key)
        v5 = strategy.version
        assert v5 is not v4
        assert d.getitem(w_key) is None
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key) is None

    def test_same_key_set_twice(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_ModuleDictObject(space, strategy, storage)

        v1 = strategy.version
        x = object()
        d.setitem("a", x)
        v2 = strategy.version
        assert v1 is not v2
        d.setitem("a", x)
        v3 = strategy.version
        assert v2 is v3

class AppTestModuleDict(object):

    def setup_class(cls):
        cls.w_runappdirect = cls.space.wrap(cls.runappdirect)

    def w_impl_used(self, obj):
        if self.runappdirect:
            skip("__repr__ doesn't work on appdirect")
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

    def test_copy(self):
        m = type(__builtins__)("abc")
        m.s = 12
        m.s = 123 # int cell
        m.x = object
        d = m.__dict__
        d["s"] = 12
        d1 = d.copy()
        assert d1 == {"__name__": "abc", "__doc__": None, "s": 12, "x": object}


class TestModuleDictImplementation(BaseTestRDictImplementation):
    StrategyClass = ModuleDictStrategy
    setdefault_hash_count = 2

class TestDevolvedModuleDictImplementation(BaseTestDevolvedDictImplementation):
    StrategyClass = ModuleDictStrategy
    setdefault_hash_count = 2


class AppTestCellDict(object):

    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")
        strategy = ModuleDictStrategy(cls.space)
        storage = strategy.get_empty_storage()
        cls.w_d = W_ModuleDictObject(cls.space, strategy, storage)

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

class TestCellCache(object):
    FakeString = FakeString

    def moduledict_and_key(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_ModuleDictObject(space, strategy, storage)
        key = "a"
        w_key = self.FakeString(key)
        return d, key, w_key

    def test_basic_property_cache(self):
        d, key, w_key = self.moduledict_and_key()
        d.setitem(w_key, 1)
        c = d.get_global_cache(key)
        c2 = d.get_global_cache(key)
        assert c2 is c

        assert c.getvalue(space) == 1
        assert d.getitem(w_key) == 1
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key) == 1

        d.setitem(w_key, 2)
        c2 = d.get_global_cache(key)
        assert c2 is c
        assert c.getvalue(space) == 2

        assert d.getitem(w_key) == 2
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key).w_value == 2

        d.setitem(w_key, 3)
        c2 = d.get_global_cache(key)
        assert c2 is c
        assert c.getvalue(space) == 3
        assert d.getitem(w_key) == 3
        assert d.get_strategy().getdictvalue_no_unwrapping(d, key).w_value == 3

    def test_delitem(self):
        d, key, w_key = self.moduledict_and_key()

        d.setitem(w_key, 1)
        c = d.get_global_cache(key)
        assert c.getvalue(space) == 1

        d.delitem(w_key)
        assert c.getvalue(space) is None
        assert c.valid
        c2 = d.get_global_cache(key)
        assert c2 is c

        d.setitem(w_key, 2)
        c2 = d.get_global_cache(key)
        assert c2 is c
        assert c.getvalue(space) == 2

    def test_getcache_and_builtins(self):
        space = FakeSpace()
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        builtindict = W_ModuleDictObject(space, strategy, storage)
        builtindict.setitem_str("len", 2)
        builtindict.setitem_str("list", 19)
        class FakeModule:
            w_dict = builtindict
        space.builtin = FakeModule()
        storage = strategy.get_empty_storage()
        d = W_ModuleDictObject(space, strategy, storage)

        # just in the builtins
        c = d.get_global_cache("len")
        assert c.cell is None
        assert c.builtincache.cell == 2

        # in both dicts
        d.setitem_str("list", 23)
        c = d.get_global_cache("list")
        assert c.cell == 23
        assert c.builtincache is None

        # not in the builtins but in the normal dict
        d.setitem_str("a", 45)
        c = d.get_global_cache("a")
        assert c.cell == 45
        assert c.builtincache is None

        # not in either dict
        c = d.get_global_cache("b")
        assert c.cell is None
        assert c.builtincache is None

    def test_devolve(self):
        strategy = ModuleDictStrategy(space)
        storage = strategy.get_empty_storage()
        d = W_ModuleDictObject(space, strategy, storage)

        key = "a"
        w_key = self.FakeString(key)
        d.setitem(w_key, 1)
        c = d.get_global_cache(key)
        assert c.getvalue(space) == 1
        assert c.valid

        d.setitem(5, 1)
        assert not c.valid

    # _____________________________________________

    class FakePycode:
        def __init__(self):
            self._globals_caches = [None]

    class FakeBuiltin:
        def getdictvalue(self, space, name):
            return name

    class FakeFrame:
        w_value = None
        debugdata = None

        def __init__(self, code, builtin):
            self.pycode = code
            self.builtin = builtin
            self.space = space

        def pushvalue(self, w_value):
            self.w_top_of_stack = w_value

        def popvalue(self):
            return self.w_top_of_stack

        def getdebug(self):
            return self.debugdata

        def getname_u(self, i):
            assert i == 0
            return "a"

        def _load_global(self, index):
            return -17

        def get_builtin(self):
            return self.builtin

    class FakeDebugData:
        pass

    def test_bytecode_load(self):
        from pypy.objspace.std.celldict import LOAD_GLOBAL_cached
        d, key, w_key = self.moduledict_and_key()
        d.setitem(w_key, 1)

        code = self.FakePycode()
        code.w_globals = d
        frame = self.FakeFrame(code, self.FakeBuiltin())

        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == -17 # went the _load_global route

        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == 1

        d.setitem(w_key, 2)
        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == 2

        d.setitem(w_key, 6)
        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == 6

    def test_bytecode_load_works_with_debugdata(self):
        from pypy.objspace.std.celldict import LOAD_GLOBAL_cached
        d, key, w_key = self.moduledict_and_key()
        d.setitem(w_key, 1)

        code = self.FakePycode()
        code.w_globals = d
        frame = self.FakeFrame(code, self.FakeBuiltin())
        frame.debugdata = self.FakeDebugData()
        frame.debugdata.w_globals = d

        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == -17 # went the _load_global route

        LOAD_GLOBAL_cached(frame, 0, None)
        assert frame.w_top_of_stack == 1 # works!

    def test_bytecode_store(self):
        from pypy.objspace.std.celldict import STORE_GLOBAL_cached
        d, key, w_key = self.moduledict_and_key()
        d.setitem(w_key, 1)

        code = self.FakePycode()
        code.w_globals = d
        frame = self.FakeFrame(code, self.FakeBuiltin())

        frame.w_top_of_stack = 7
        STORE_GLOBAL_cached(frame, 0, None)
        assert d.getitem(w_key) == 7

        frame.getname_u = None # the rest still works due to the cache
        frame.w_top_of_stack = 9
        STORE_GLOBAL_cached(frame, 0, None)
        assert d.getitem(w_key) == 9
