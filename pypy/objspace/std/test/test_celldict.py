from pypy.conftest import gettestobjspace
from pypy.objspace.std.celldict import get_global_cache, ModuleCell, ModuleDictImplementation
from pypy.interpreter import gateway

# this file tests mostly the effects of caching global lookup. The dict
# implementation itself is tested in test_dictmultiobject.py


class AppTestCellDict(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withcelldict": True})
        cls.w_impl_used = cls.space.appexec([], """():
            import __pypy__
            def impl_used(obj):
                assert "ModuleDictImplementation" in __pypy__.internal_repr(obj)
            return impl_used
        """)
        def is_in_cache(space, w_code, w_globals, w_name):
            name = space.str_w(w_name)
            cache = get_global_cache(space, w_code, w_globals)
            index = [space.str_w(w_n) for w_n in w_code.co_names_w].index(name)
            return space.wrap(cache[index].w_value is not None)
        is_in_cache = gateway.interp2app(is_in_cache)
        cls.w_is_in_cache = cls.space.wrap(is_in_cache) 
        stored_builtins = []
        def rescue_builtins(space):
            w_dict = space.builtin.getdict()
            content = {}
            for key, cell in w_dict.content.iteritems():
                newcell = ModuleCell()
                newcell.w_value = cell.w_value
                content[key] = newcell
            stored_builtins.append(content)
        rescue_builtins = gateway.interp2app(rescue_builtins)
        cls.w_rescue_builtins = cls.space.wrap(rescue_builtins) 
        def restore_builtins(space):
            w_dict = space.builtin.getdict()
            assert isinstance(w_dict, ModuleDictImplementation)
            w_dict.content = stored_builtins.pop()
            w_dict.fallback = None
        restore_builtins = gateway.interp2app(restore_builtins)
        cls.w_restore_builtins = cls.space.wrap(restore_builtins) 

    def test_same_code_in_different_modules(self):
        import sys
        mod1 = type(sys)("abc")
        self.impl_used(mod1.__dict__)
        glob1 = mod1.__dict__
        mod2 = type(sys)("abc")
        self.impl_used(mod2.__dict__)
        glob2 = mod2.__dict__
        def f():
            return x + 1
        code = f.func_code
        f1 = type(f)(code, glob1)
        mod1.x = 1
        assert not self.is_in_cache(code, glob1, "x")
        assert f1() == 2
        assert self.is_in_cache(code, glob1, "x")
        assert f1() == 2
        assert self.is_in_cache(code, glob1, "x")
        mod1.x = 2
        assert f1() == 3
        assert self.is_in_cache(code, glob1, "x")
        assert f1() == 3
        assert self.is_in_cache(code, glob1, "x")
        f2 = type(f)(code, glob2)
        mod2.x = 5
        assert not self.is_in_cache(code, glob2, "x")
        assert f2() == 6
        assert self.is_in_cache(code, glob2, "x")
        assert f2() == 6
        assert self.is_in_cache(code, glob2, "x")
        mod2.x = 7
        assert f2() == 8
        assert self.is_in_cache(code, glob2, "x")
        assert f2() == 8
        assert self.is_in_cache(code, glob2, "x")

    def test_override_builtins(self):
        import sys, __builtin__
        mod1 = type(sys)("abc")
        glob1 = mod1.__dict__
        self.impl_used(mod1.__dict__)
        def f():
            return len(x)
        code = f.func_code
        f1 = type(f)(f.func_code, glob1)
        mod1.x = []
        assert not self.is_in_cache(code, glob1, "len")
        assert not self.is_in_cache(code, glob1, "x")
        assert f1() == 0
        assert self.is_in_cache(code, glob1, "len")
        assert self.is_in_cache(code, glob1, "x")
        assert f1() == 0
        mod1.x.append(1)
        assert f1() == 1
        assert self.is_in_cache(code, glob1, "len")
        assert self.is_in_cache(code, glob1, "x")
        mod1.len = lambda x: 15
        assert not self.is_in_cache(code, glob1, "len")
        mod1.x.append(1)
        assert f1() == 15
        assert self.is_in_cache(code, glob1, "len")
        assert f1() == 15
        assert self.is_in_cache(code, glob1, "len")
        del mod1.len
        mod1.x.append(1)
        assert not self.is_in_cache(code, glob1, "len")
        assert f1() == 3
        assert self.is_in_cache(code, glob1, "len")
        assert f1() == 3
        assert self.is_in_cache(code, glob1, "len")
        orig_len = __builtins__.len
        try:
            __builtins__.len = lambda x: 12
            mod1.x.append(1)
            assert self.is_in_cache(code, glob1, "len")
            assert f1() == 12
            assert self.is_in_cache(code, glob1, "len")
            assert f1() == 12
            assert self.is_in_cache(code, glob1, "len")
        finally:
            __builtins__.len = orig_len

    def test_override_builtins2(self):
        import sys, __builtin__
        mod1 = type(sys)("abc")
        glob1 = mod1.__dict__
        self.impl_used(mod1.__dict__)
        def f():
            return l(x)
        code = f.func_code
        f1 = type(f)(f.func_code, glob1)
        mod1.x = []
        __builtin__.l = len
        try:
            assert not self.is_in_cache(code, glob1, "l")
            assert not self.is_in_cache(code, glob1, "x")
            assert f1() == 0
            assert self.is_in_cache(code, glob1, "l")
            assert self.is_in_cache(code, glob1, "x")
            assert f1() == 0
            mod1.x.append(1)
            assert f1() == 1
            assert self.is_in_cache(code, glob1, "l")
            assert self.is_in_cache(code, glob1, "x")
            del __builtin__.l
            mod1.l = len
            mod1.x.append(1)
            assert not self.is_in_cache(code, glob1, "l")
            assert f1() == 2
            assert self.is_in_cache(code, glob1, "l")
            assert self.is_in_cache(code, glob1, "x")
        finally:
            if hasattr(__builtins__, "l"):
                del __builtins__.l

    def test_generator(self):
        import sys, __builtin__
        mod1 = type(sys)("abc")
        glob1 = mod1.__dict__
        self.impl_used(mod1.__dict__)
        def f():
            yield 1
            yield x
            yield len(x)
        code = f.func_code
        f1 = type(f)(f.func_code, glob1)
        mod1.x = []
        gen = f1()
        assert not self.is_in_cache(code, glob1, "len")
        assert not self.is_in_cache(code, glob1, "x")
        v = gen.next()
        assert v == 1
        assert not self.is_in_cache(code, glob1, "len")
        assert not self.is_in_cache(code, glob1, "x")
        v = gen.next()
        assert v is mod1.x
        assert not self.is_in_cache(code, glob1, "len")
        assert self.is_in_cache(code, glob1, "x")
        v = gen.next()
        assert v == 0
        assert self.is_in_cache(code, glob1, "len")
        assert self.is_in_cache(code, glob1, "x")

    def test_degenerate_to_rdict(self):
        import sys
        mod1 = type(sys)("abc")
        self.impl_used(mod1.__dict__)
        glob1 = mod1.__dict__
        def f():
            return x + 1
        code = f.func_code
        f1 = type(f)(code, glob1)
        mod1.x = 1
        assert not self.is_in_cache(code, glob1, "x")
        assert f1() == 2
        assert self.is_in_cache(code, glob1, "x")
        glob1[1] = 2
        assert not self.is_in_cache(code, glob1, "x")
        assert f1() == 2
        assert not self.is_in_cache(code, glob1, "x")

    def test_degenerate_builtin_to_rdict(self):
        import sys, __builtin__
        mod1 = type(sys)("abc")
        self.impl_used(mod1.__dict__)
        glob1 = mod1.__dict__
        def f():
            return len(x)
        code = f.func_code
        f1 = type(f)(code, glob1)
        mod1.x = [1, 2]
        assert not self.is_in_cache(code, glob1, "x")
        assert not self.is_in_cache(code, glob1, "len")
        assert f1() == 2
        assert self.is_in_cache(code, glob1, "x")
        assert self.is_in_cache(code, glob1, "len")
        self.rescue_builtins()
        try:
            __builtin__.__dict__[1] = 2
            assert not self.is_in_cache(code, glob1, "len")
            assert f1() == 2
            assert not self.is_in_cache(code, glob1, "len")
        finally:
            self.restore_builtins()

    def test_mapping_as_locals(self):
        import sys
        if sys.version_info < (2,5) or not hasattr(sys, 'pypy_objspaceclass'):
            skip("need CPython 2.5 or PyPy for non-dictionaries in exec statements")
        class M(object):
            def __getitem__(self, key):
                return key
            def __setitem__(self, key, value):
                self.result[key] = value
        m = M()
        m.result = {}
        exec "x=m" in {}, m
        assert m.result == {'x': 'm'}
        exec "y=n" in m   # NOTE: this doesn't work in CPython 2.4
        assert m.result == {'x': 'm', 'y': 'n'}

    def test_subclass_of_dict_as_locals(self):
        import sys
        if sys.version_info < (2,5) or not hasattr(sys, 'pypy_objspaceclass'):
            skip("need CPython 2.5 or PyPy for non-dictionaries in exec statements")
        class M(dict):
            def __getitem__(self, key):
                return key
            def __setitem__(self, key, value):
                dict.__setitem__(self, key, value)
        m = M()
        exec "x=m" in {}, m
        assert m == {'x': 'm'}
        exec "y=n" in m   # NOTE: this doesn't work in CPython 2.4
        assert m == {'x': 'm', 'y': 'n'}

