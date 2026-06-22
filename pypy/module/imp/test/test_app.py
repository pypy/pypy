from __future__ import with_statement
import pytest
from rpython.tool.udir import udir



class AppTestImpModule:
    # cpyext or _cffi_backend is required for _imp.create_dynamic()
    # use _cffi_backend since it is difficult to import cpyext untranslated
    spaceconfig = {
        'usemodules': ['binascii', 'imp', 'time', 'struct',
                       '_cffi_backend'],
    }

    def setup_class(cls):
        cls.w_file_module = cls.space.wrap(__file__)
        latin1 = udir.join('latin1.py')
        latin1.write("# -*- coding: iso-8859-1 -*\n")
        fake_latin1 = udir.join('fake_latin1.py')
        fake_latin1.write("print('-*- coding: iso-8859-1 -*')")
        cls.w_udir = cls.space.wrap(str(udir))

    def w__py_file(self):
        fname = self.udir + '/@TEST.py'
        f = open(fname, 'w')
        f.write('MARKER = 42\n')
        f.close()
        return fname

    def w__pyc_file(self):
        import marshal, importlib.util
        co = compile("marker=42", "x.py", "exec")
        fname = self.udir + '/@TEST.pyc'
        f = open(fname, 'wb')
        f.write(importlib.util.MAGIC_NUMBER)
        f.write(b'\x00\x00\x00\x00')
        f.write(b'\x00\x00\x00\x00')
        f.write(b'\x00\x00\x00\x00')
        marshal.dump(co, f)
        f.close()
        return fname

    def w_load_source(self, name, path):
        # replaces imp.load_source(name, path), removed in 3.12
        import importlib.util, importlib.machinery, sys
        loader = importlib.machinery.SourceFileLoader(name, path)
        spec = importlib.util.spec_from_file_location(name, path, loader=loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        return module

    def w_load_compiled(self, name, path):
        # replaces imp.load_compiled(name, path), removed in 3.12
        import importlib.util, importlib.machinery, sys
        loader = importlib.machinery.SourcelessFileLoader(name, path)
        spec = importlib.util.spec_from_file_location(name, path, loader=loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        return module

    def test_create_dynamic(self):
        import _imp
        PATH = 'this/path/does/not/exist'
        class FakeSpec:
            origin = PATH
            def __init__(self, name):
                self.name = name

        excinfo = raises(ImportError, _imp.create_dynamic, FakeSpec('foo'))
        assert excinfo.value.name == 'foo'
        assert excinfo.value.path == PATH
        # Note: On CPython, the behavior changes slightly if a 2nd argument is
        # passed in, whose value is ignored. We don't implement that.
        #raises(IOError, _imp.create_dynamic, FakeSpec(), "unused")

        # Note: On CPython, the following gives nonsense.  I suspect
        # it's because the b'foo' is read with PyUnicode_Xxx()
        # functions that don't check the type of the argument.
        raises(TypeError, _imp.create_dynamic, FakeSpec(b'foo'))

    def test_ext_suffixes(self):
        import _imp
        for suffix in _imp.extension_suffixes():
            # print(suffix)
            assert suffix.endswith(('.pyd', '.so'))

    def test_obscure_functions(self):
        import _imp, types
        mod = types.ModuleType('hi')
        assert mod.__name__ == 'hi'
        mod = _imp.init_frozen('hello.world.this.is.never.a.frozen.module.name')
        assert mod is None
        assert _imp.is_builtin('sys')
        assert not _imp.is_builtin('hello.world.this.is.never.a.builtin.module.name')
        assert not _imp.is_frozen('hello.world.this.is.never.a.frozen.module.name')

    def test_find_frozen(self):
        import _imp
        assert _imp.find_frozen('hello.what.now') is None

    def test_is_builtin(self):
        import sys, _imp
        from importlib.machinery import BuiltinImporter
        for name in sys.builtin_module_names:
            assert _imp.is_builtin(name)
            spec = BuiltinImporter.find_spec(name)
            assert spec is not None
    test_is_builtin.dont_track_allocations = True

    def test_load_source(self):
        fn = self._py_file()
        mod = self.load_source('test_imp_extra_AUTO3', fn)
        assert mod.MARKER == 42
        import test_imp_extra_AUTO3
        assert mod is test_imp_extra_AUTO3

    def test_load_module_pyc_2(self):
        import os
        fn = self._pyc_file()
        try:
            mod = self.load_compiled('test_imp_extra_AUTO4', fn)
            assert mod.marker == 42
            import test_imp_extra_AUTO4
            assert mod is test_imp_extra_AUTO4
        finally:
            os.unlink(fn)

    def test_load_broken_pyc(self):
        fn = self._py_file()
        try:
            self.load_compiled('test_imp_extra_AUTO5', fn)
        except ImportError:
            pass
        else:
            raise Exception("expected an ImportError")

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
        import sys
        import time as time1

        old = time1.process_time
        try:
            time1.process_time = 42

            # save, re-import, restore.
            saved = sys.modules.pop('time')
            assert time1 is saved
            time2 = __import__('time')
            assert time2 is not time1
            assert time2 is sys.modules['time']
            assert time2.process_time is old

            import time as time3
            assert time3 is time2
            assert time3.process_time is old

            sys.modules['time'] = time1
            import time as time4
            assert time4 is time1
            assert time4.process_time == 42
        finally:
            time1.process_time = old

    def test_get_tag(self):
        import sys
        if not hasattr(sys, 'pypy_version_info'):
            skip('This test is PyPy-only')
        assert sys.implementation.cache_tag == 'pypy%d%d' % (sys.version_info[:2])

    def test_unicode_in_sys_path(self):
        # issue 3112: when _getimporter calls
        # for x in sys.path: for h in sys.path_hooks: h(x)
        # make sure x is properly encoded
        import sys
        if sys.getfilesystemencoding().lower() == 'utf-8':
            sys.path.insert(0, u'\xef')
        with raises(ImportError):
            import impossible_module

    def test_source_hash(self):
        import _imp
        res = _imp.source_hash(1, b"abcdef")
        assert type(res) is bytes
        assert res == b'\xd8^\xafF=\xaain' # value from CPython
        res2 = _imp.source_hash(1, b"abcdefg")
        assert res != res2

    def test_check_hash_based_pycs(self):
        import _imp
        assert _imp.check_hash_based_pycs == "default"

