from __future__ import with_statement
MARKER = 42

class AppTestImpModule:
    def setup_class(cls):
        cls.w_imp = cls.space.getbuiltinmodule('imp')
        cls.w_file_module = cls.space.wrap(__file__)

    def w__py_file(self):
        fn = self.file_module
        if fn.lower().endswith('c') or fn.lower().endswith('o'):
            fn = fn[:-1]
        assert fn.lower().endswith('.py')
        return fn

    def w__pyc_file(self):
        import marshal, imp
        co = compile("marker=42", "x.py", "exec")
        f = open('@TEST.pyc', 'wb')
        f.write(imp.get_magic())
        f.write('\x00\x00\x00\x00')
        marshal.dump(co, f)
        f.close()
        return '@TEST.pyc'

    def test_find_module(self):
        import os
        file, pathname, description = self.imp.find_module('StringIO')
        assert file is not None
        file.close()
        assert os.path.exists(pathname)
        pathname = pathname.lower()
        assert pathname.endswith('.py') # even if .pyc is up-to-date
        assert description in self.imp.get_suffixes()

    def test_load_dynamic(self):
        raises(ImportError, self.imp.load_dynamic, 'foo', 'bar')
        raises(ImportError, self.imp.load_dynamic, 'foo', 'bar',
               open(self.file_module))

    def test_suffixes(self):
        for suffix, mode, type in self.imp.get_suffixes():
            if mode == self.imp.PY_SOURCE:
                assert suffix == '.py'
                assert type == 'r'
            elif mode == self.imp.PY_COMPILED:
                assert suffix in ('.pyc', '.pyo')
                assert type == 'rb'
            elif mode == self.imp.C_EXTENSION:
                assert suffix.endswith(('.pyd', '.so'))
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

    def test_load_module_pyc_1(self):
        import os
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

    def test_load_module_pyc_2(self):
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

    def test_load_module_in_sys_modules(self):
        fn = self._py_file()
        f = open(fn, 'rb')
        descr = ('.py', 'U', self.imp.PY_SOURCE)
        mod = self.imp.load_module('test_imp_extra_AUTO6', f, fn, descr)
        f.close()
        f = open(fn, 'rb')
        mod2 = self.imp.load_module('test_imp_extra_AUTO6', f, fn, descr)
        f.close()
        assert mod2 is mod

    def test_nullimporter(self):
        import os
        importer = self.imp.NullImporter("path")
        assert importer.find_module(1, 2, 3, 4) is None
        raises(ImportError, self.imp.NullImporter, os.getcwd())

    def test_path_importer_cache(self):
        import os
        import sys

        lib_pypy = os.path.abspath(
            os.path.join(self.file_module, "..", "..", "..", "..", "..", "lib_pypy")
        )
        # Doesn't end up in there when run with -A
        assert sys.path_importer_cache.get(lib_pypy) is None

    def test_rewrite_pyc_check_code_name(self):
        # This one is adapted from cpython's Lib/test/test_import.py
        from os import chmod
        from os.path import join
        from sys import modules, path
        from shutil import rmtree
        from tempfile import mkdtemp
        code = """if 1:
            import sys
            code_filename = sys._getframe().f_code.co_filename
            module_filename = __file__
            constant = 1
            def func():
                pass
            func_filename = func.func_code.co_filename
            """

        module_name = "unlikely_module_name"
        dir_name = mkdtemp(prefix='pypy_test')
        file_name = join(dir_name, module_name + '.py')
        with open(file_name, "wb") as f:
            f.write(code)
        compiled_name = file_name + ("c" if __debug__ else "o")
        chmod(file_name, 0777)

        # Setup
        sys_path = path[:]
        orig_module = modules.pop(module_name, None)
        assert modules.get(module_name) == None
        path.insert(0, dir_name)

        # Test
        import py_compile
        py_compile.compile(file_name, dfile="another_module.py")
        __import__(module_name, globals(), locals())
        mod = modules.get(module_name)

        try:
            # Ensure proper results
            assert mod != orig_module
            assert mod.module_filename == compiled_name
            assert mod.code_filename == file_name
            assert mod.func_filename == file_name
        finally:
            # TearDown
            path[:] = sys_path
            if orig_module is not None:
                modules[module_name] = orig_module
            else:
                try:
                    del modules[module_name]
                except KeyError:
                    pass
            rmtree(dir_name, True)
