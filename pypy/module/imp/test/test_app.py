from __future__ import with_statement
import pytest
from rpython.tool.udir import udir



class AppTestImpModule:
    # cpyext is required for _imp.load_dynamic()
    spaceconfig = {
        'usemodules': [
            'binascii', 'imp', 'itertools', 'time', 'struct', 'cpyext'],
    }

    def setup_class(cls):
        cls.w_file_module = cls.space.wrap(__file__)
        latin1 = udir.join('latin1.py')
        latin1.write("# -*- coding: iso-8859-1 -*\n")
        fake_latin1 = udir.join('fake_latin1.py')
        fake_latin1.write("print('-*- coding: iso-8859-1 -*')")
        cls.w_udir = cls.space.wrap(str(udir))

    def w__py_file(self):
        f = open('@TEST.py', 'w')
        f.write('MARKER = 42\n')
        f.close()
        return '@TEST.py'

    def w__pyc_file(self):
        import marshal, imp
        co = compile("marker=42", "x.py", "exec")
        f = open('@TEST.pyc', 'wb')
        f.write(imp.get_magic())
        f.write(b'\x00\x00\x00\x00')
        f.write(b'\x00\x00\x00\x00')
        marshal.dump(co, f)
        f.close()
        return '@TEST.pyc'

    def test_find_module(self):
        import os, imp
        file, pathname, description = imp.find_module('cmd')
        assert file is not None
        file.close()
        assert os.path.exists(pathname)
        pathname = pathname.lower()
        assert pathname.endswith('.py') # even if .pyc is up-to-date
        assert description in imp.get_suffixes()

    def test_find_module_with_encoding(self):
        import sys, imp
        sys.path.insert(0, self.udir)
        try:
            file, pathname, description = imp.find_module('latin1')
            assert file.encoding == 'iso-8859-1'
            #
            file, pathname, description = imp.find_module('fake_latin1')
            assert file.encoding == 'utf-8'
        finally:
            del sys.path[0]

    def test_load_dynamic_error(self):
        import _imp
        excinfo = raises(ImportError, _imp.load_dynamic, 'foo', 'bar')
        assert excinfo.value.name == 'foo'
        assert excinfo.value.path == './bar'
        # Note: On CPython, the behavior changes slightly if a 3rd argument is
        # passed in, whose value is ignored. We don't implement that.
        #raises(IOError, _imp.load_dynamic, 'foo', 'bar', 42)

        raises(TypeError, _imp.load_dynamic, b'foo', 'bar')

    def test_suffixes(self):
        import imp
        for suffix, mode, type in imp.get_suffixes():
            if mode == imp.PY_SOURCE:
                assert suffix == '.py'
                assert type == 'r'
            elif mode == imp.PY_COMPILED:
                assert suffix in ('.pyc', '.pyo')
                assert type == 'rb'
            elif mode == imp.C_EXTENSION:
                assert suffix.endswith(('.pyd', '.so'))
                assert type == 'rb'

    def test_ext_suffixes(self):
        import _imp
        for suffix in _imp.extension_suffixes():
            assert suffix.endswith(('.pyd', '.so'))

    def test_obscure_functions(self):
        import imp
        mod = imp.new_module('hi')
        assert mod.__name__ == 'hi'
        mod = imp.init_builtin('hello.world.this.is.never.a.builtin.module.name')
        assert mod is None
        mod = imp.init_frozen('hello.world.this.is.never.a.frozen.module.name')
        assert mod is None
        assert imp.is_builtin('sys')
        assert not imp.is_builtin('hello.world.this.is.never.a.builtin.module.name')
        assert not imp.is_frozen('hello.world.this.is.never.a.frozen.module.name')


    def test_load_module_py(self):
        import imp
        fn = self._py_file()
        descr = ('.py', 'U', imp.PY_SOURCE)
        f = open(fn, 'U')
        mod = imp.load_module('test_imp_extra_AUTO1', f, fn, descr)
        f.close()
        assert mod.MARKER == 42
        import test_imp_extra_AUTO1
        assert mod is test_imp_extra_AUTO1

    def test_load_module_pyc_1(self):
        import os, imp
        fn = self._pyc_file()
        try:
            descr = ('.pyc', 'rb', imp.PY_COMPILED)
            f = open(fn, 'rb')
            mod = imp.load_module('test_imp_extra_AUTO2', f, fn, descr)
            f.close()
            assert mod.marker == 42
            import test_imp_extra_AUTO2
            assert mod is test_imp_extra_AUTO2
        finally:
            os.unlink(fn)

    def test_load_source(self):
        import imp
        fn = self._py_file()
        mod = imp.load_source('test_imp_extra_AUTO3', fn)
        assert mod.MARKER == 42
        import test_imp_extra_AUTO3
        assert mod is test_imp_extra_AUTO3

    def test_load_module_pyc_2(self):
        import os, imp
        fn = self._pyc_file()
        try:
            mod = imp.load_compiled('test_imp_extra_AUTO4', fn)
            assert mod.marker == 42
            import test_imp_extra_AUTO4
            assert mod is test_imp_extra_AUTO4
        finally:
            os.unlink(fn)

    def test_load_broken_pyc(self):
        import imp
        fn = self._py_file()
        try:
            imp.load_compiled('test_imp_extra_AUTO5', fn)
        except ImportError:
            pass
        else:
            raise Exception("expected an ImportError")

    def test_load_module_in_sys_modules(self):
        import imp
        fn = self._py_file()
        f = open(fn, 'rb')
        descr = ('.py', 'U', imp.PY_SOURCE)
        mod = imp.load_module('test_imp_extra_AUTO6', f, fn, descr)
        f.close()
        f = open(fn, 'rb')
        mod2 = imp.load_module('test_imp_extra_AUTO6', f, fn, descr)
        f.close()
        assert mod2 is mod

    def test_nullimporter(self):
        import os, imp
        importer = imp.NullImporter("path")
        assert importer.find_module(1) is None
        raises(ImportError, imp.NullImporter, os.getcwd())

    def test_path_importer_cache(self):
        import os
        import sys
        # this is the only way this makes sense. _bootstrap
        # will eventually load os from lib_pypy and place
        # a file finder in path_importer_cache.
        # XXX Why not remove this test? XXX
        sys.path_importer_cache.clear()
        import sys # sys is looked up in pypy/module thus
        # lib_pypy will not end up in sys.path_impoter_cache

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
        code = b"""if 1:
            import sys
            code_filename = sys._getframe().f_code.co_filename
            module_filename = __file__
            constant = 1
            def func():
                pass
            func_filename = func.__code__.co_filename
            """

        module_name = "unlikely_module_name"
        dir_name = mkdtemp(prefix='pypy_test')
        file_name = join(dir_name, module_name + '.py')
        with open(file_name, "wb") as f:
            f.write(code)
        compiled_name = file_name + ("c" if __debug__ else "o")
        chmod(file_name, 0o777)

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
            assert mod.module_filename == file_name
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

    def test_builtin_reimport(self):
        # from https://bugs.pypy.org/issue1514
        import sys, marshal

        old = marshal.loads
        marshal.loads = 42

        # save, re-import, restore.
        saved = sys.modules.pop('marshal')
        __import__('marshal')
        sys.modules['marshal'] = saved

        assert marshal.loads == 42
        import marshal
        assert marshal.loads == 42
        marshal.loads = old

    def test_builtin_reimport_mess(self):
        # taken from https://bugs.pypy.org/issue1514, with extra cases
        # that show a difference with CPython: we can get on CPython
        # several module objects for the same built-in module :-(
        import sys, _md5

        old = _md5.md5
        _md5.md5 = 42

        # save, re-import, restore.
        saved = sys.modules.pop('_md5')
        _md52 = __import__('_md5')
        assert _md52 is not _md5
        assert _md52.md5 is old
        assert _md52 is sys.modules['_md5']
        assert _md5 is saved
        assert _md5.md5 == 42

        import _md5
        assert _md5.md5 is old

        sys.modules['_md5'] = saved
        import _md5
        assert _md5.md5 == 42

        _md5.md5 = old

    def test_get_tag(self):
        import imp
        import sys
        if not hasattr(sys, 'pypy_version_info'):
            skip('This test is PyPy-only')
        assert imp.get_tag() == 'pypy3-%d%d' % sys.pypy_version_info[0:2]
