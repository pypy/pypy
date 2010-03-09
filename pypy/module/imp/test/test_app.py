MARKER = 42

class AppTestImpModule:
    def setup_class(cls):
        cls.w_imp = cls.space.getbuiltinmodule('imp')

        cls.w__py_file = cls.space.appexec(
            [cls.space.wrap(__file__)], r"""(__file__):
        def _py_file():
            fn = __file__
            if fn.lower().endswith('c') or fn.lower().endswith('o'):
                fn = fn[:-1]
            assert fn.lower().endswith('.py')
            return fn
        return _py_file""")

        cls.w__pyc_file = cls.space.appexec([], r"""():
        def _pyc_file():
            import marshal, imp
            co = compile("marker=42", "x.py", "exec")
            f = open('@TEST.pyc', 'wb')
            f.write(imp.get_magic())
            f.write('\x00\x00\x00\x00')
            marshal.dump(co, f)
            f.close()
            return '@TEST.pyc'
        return _pyc_file""")



    def test_find_module(self):
        import os
        file, pathname, description = self.imp.find_module('StringIO')
        assert file is not None
        file.close()
        assert os.path.exists(pathname)
        pathname = pathname.lower()
        assert pathname.endswith('.py') # even if .pyc is up-to-date
        assert description in self.imp.get_suffixes()


    def test_suffixes(self):
        for suffix, mode, type in self.imp.get_suffixes():
            if mode == self.imp.PY_SOURCE:
                assert suffix == '.py'
                assert type == 'r'
            elif mode == self.imp.PY_COMPILED:
                assert suffix in ('.pyc', '.pyo')
                assert type == 'rb'


    def test_obscure_functions(self):
        mod = self.imp.new_module('hi')
        assert mod.__name__ == 'hi'
        mod = self.imp.init_builtin('hello.world.this.is.never.a.builtin.module.name')
        assert mod is None
        mod = self.imp.init_frozen('hello.world.this.is.never.a.frozen.module.name')
        assert mod is None
        assert self.imp.is_builtin('sys')
        assert not self.imp.is_builtin('hello.world.this.is.never.a.builtin.module.name')
        assert not self.imp.is_frozen('hello.world.this.is.never.a.frozen.module.name')


    def test_load_module_py(self):
        fn = self._py_file()
        descr = ('.py', 'U', self.imp.PY_SOURCE)
        f = open(fn, 'U')
        mod = self.imp.load_module('test_imp_extra_AUTO1', f, fn, descr)
        f.close()
        assert mod.MARKER == 42
        import test_imp_extra_AUTO1
        assert mod is test_imp_extra_AUTO1

    def test_load_module_pyc(self):
        fn = self._pyc_file()
        try:
            descr = ('.pyc', 'rb', self.imp.PY_COMPILED)
            f = open(fn, 'rb')
            mod = self.imp.load_module('test_imp_extra_AUTO2', f, fn, descr)
            f.close()
            assert mod.marker == 42
            import test_imp_extra_AUTO2
            assert mod is test_imp_extra_AUTO2
        finally:
            os.unlink(fn)

    def test_load_source(self):
        fn = self._py_file()
        mod = self.imp.load_source('test_imp_extra_AUTO3', fn)
        assert mod.MARKER == 42
        import test_imp_extra_AUTO3
        assert mod is test_imp_extra_AUTO3

    def test_load_module_pyc(self):
        import os
        fn = self._pyc_file()
        try:
            mod = self.imp.load_compiled('test_imp_extra_AUTO4', fn)
            assert mod.marker == 42
            import test_imp_extra_AUTO4
            assert mod is test_imp_extra_AUTO4
        finally:
            os.unlink(fn)

    def test_load_broken_pyc(self):
        fn = self._py_file()
        try:
            self.imp.load_compiled('test_imp_extra_AUTO5', fn)
        except ImportError:
            pass
        else:
            raise Exception("expected an ImportError")
