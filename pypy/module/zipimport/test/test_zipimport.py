# -*- encoding: utf-8 -*-
import inspect
import os
import time
from zipfile import ZIP_STORED

from pypy.interpreter.test.test_fsencode import BaseFSEncodeTest
from rpython.tool.udir import udir


class AppTestZipimport(BaseFSEncodeTest):
    """ A bit structurized tests stolen and adapted from
    cpy's regression tests
    """
    compression = ZIP_STORED
    spaceconfig = {
        "usemodules": ['zipimport', 'time', 'struct', 'binascii', 'marshal'],
    }
    pathsep = os.path.sep

    @classmethod
    def make_class(cls):
        BaseFSEncodeTest.setup_class.im_func(cls)
        space = cls.space
        w = space.wrap

        cls.w_appdirect = w(cls.runappdirect)
        cls.w_now = w(time.time())
        cls.w_compression = w(cls.compression)
        cls.w_pathsep = w(cls.pathsep)
        cls.tmpdir = udir.ensure('zipimport_%s_%s' % (__name__, cls.__name__),
                                 dir=1)
        ziptestmodule = cls.tmpdir.join("somezip.zip")
        cls.w_tmpzip = w(str(ziptestmodule))

        # Cache get_pyc()
        get_pyc_source = inspect.getsource(
            cls.w__get_pyc.im_func).splitlines()[1:]
        get_pyc_source.insert(0, '    (mtime):')
        cls.w__test_pyc = space.appexec([cls.w_now], '\n'.join(get_pyc_source))

    def setup_class(cls):
        cls.make_class()

    def setup_method(self, meth):
        space = self.space
        name = "test_%s_%s.zip" % (self.__class__.__name__, meth.__name__)
        self.w_zipfile = space.wrap(str(self.tmpdir.join(name)))
        self.w_write_files = space.newlist([])
        w_cache = space.getattr(space.getbuiltinmodule('zipimport'),
                                space.wrap('_zip_directory_cache'))
        space.call_function(space.getattr(w_cache, space.wrap('clear')))
        self.w_modules = space.call_function(
            space.w_list,
            space.getattr(space.getbuiltinmodule('sys'),
                          space.wrap('modules')))

    def teardown_method(self, meth):
        space = self.space
        space.appexec([], """():
        import sys
        while sys.path[0].endswith('.zip'):
            sys.path.pop(0)
        """)
        space.appexec([self.w_modules], """(modules):
        import sys
        for module in sys.modules.copy():
            if module not in modules:
                del sys.modules[module]
        """)
        self.w_modules = []

    def w_get_pyc(self):
        # always create the pyc on the host under appdirect, otherwise
        # the pre-made copy is fine
        return self._get_pyc(self.now) if self.appdirect else self._test_pyc

    def w__get_pyc(self, mtime):
        import imp
        import marshal

        if type(mtime) is float:
            # Mac mtimes need a bit of special casing
            if mtime < 0x7fffffff:
                mtime = int(mtime)
            else:
                mtime = int(-0x100000000 + int(mtime))
        mtimeb = int(mtime).to_bytes(4, 'little', signed=True)

        source = """\
def get_name():
    return __name__
def get_file():
    return __file__"""
        data = marshal.dumps(compile(source, 'uuu.py', 'exec'))
        size = len(data).to_bytes(4, 'little', signed=True)

        return imp.get_magic() + mtimeb + size + data

    def w_now_in_the_future(self, delta):
        self.now += delta

    def w_writefile(self, filename, data):
        import sys
        import time
        from zipfile import ZipFile, ZipInfo
        z = ZipFile(self.zipfile, 'w')
        write_files = self.write_files
        filename = filename.replace('/', self.pathsep)
        write_files.append((filename, data))
        for filename, data in write_files:
            zinfo = ZipInfo(filename, time.localtime(self.now))
            zinfo.compress_type = self.compression
            z.writestr(zinfo, data)
        self.write_files = write_files
        # XXX populates sys.path, but at applevel
        if sys.path[0] != self.zipfile:
            sys.path.insert(0, self.zipfile)
        z.close()

    def test_cache(self):
        self.writefile('x.py', 'y')
        from zipimport import _zip_directory_cache, zipimporter
        new_importer = zipimporter(self.zipfile)
        try:
            assert zipimporter(self.zipfile) is not new_importer
        finally:
            del _zip_directory_cache[self.zipfile]

    def test_cache_subdir(self):
        import os
        self.writefile('x.py', '')
        self.writefile('sub/__init__.py', '')
        self.writefile('sub/yy.py', '')
        from zipimport import _zip_directory_cache, zipimporter
        sub_importer = zipimporter(self.zipfile + os.path.sep + 'sub')
        main_importer = zipimporter(self.zipfile)

        assert main_importer is not sub_importer
        assert main_importer.prefix == ""
        assert sub_importer.prefix == "sub" + os.path.sep

    def test_good_bad_arguments(self):
        from zipimport import zipimporter
        import os
        self.writefile("x.py", "y")
        zipimporter(self.zipfile) # should work
        raises(ImportError, "zipimporter(os.path.dirname(self.zipfile))")
        raises(ImportError, 'zipimporter("fsafdetrssffdsagadfsafdssadasa")')
        name = os.path.join(os.path.dirname(self.zipfile), "x.zip")
        f = open(name, "w")
        f.write("zzz")
        f.close()
        raises(ImportError, 'zipimporter(name)')
        # this should work as well :-/
        zipimporter(os.path.join(self.zipfile, 'x'))

    def test_py(self):
        import sys, os
        self.writefile("uuu.py", "def f(x): return x")
        mod = __import__('uuu', globals(), locals(), [])
        assert mod.f(3) == 3
        expected = {
            '__doc__' : None,
            '__name__' : 'uuu',
            'f': mod.f}
        for key, val in expected.items():
            assert mod.__dict__[key] == val
        assert mod.__file__.endswith('.zip'+os.sep+'uuu.py')

    def test_pyc(self):
        import sys, os
        self.writefile("uuu.pyc", self.get_pyc())
        self.writefile("uuu.py", "def f(x): return x")
        mod = __import__('uuu', globals(), locals(), [])
        expected = {
            '__doc__' : None,
            '__name__' : 'uuu',
            'get_name' : mod.get_name,
            'get_file' : mod.get_file
        }
        for key, val in expected.items():
            assert mod.__dict__[key] == val
        assert mod.__file__.endswith('.zip'+os.sep+'uuu.pyc')
        assert mod.get_file() == mod.__file__
        assert mod.get_name() == mod.__name__
        #
        import zipimport
        z = zipimport.zipimporter(self.zipfile)
        code = z.get_code('uuu')
        assert isinstance(code, type((lambda:0).__code__))

    def test_bad_pyc(self):
        import zipimport
        import sys
        m0 = self.get_pyc()[0]
        m0 ^= 0x04
        test_pyc = bytes([m0]) + self.get_pyc()[1:]
        self.writefile("uu.pyc", test_pyc)
        raises(zipimport.ZipImportError,
               "__import__('uu', globals(), locals(), [])")
        assert 'uu' not in sys.modules

    def test_force_py(self):
        import sys
        m0 = self.get_pyc()[0]
        m0 ^= 0x04
        test_pyc = bytes([m0]) + self.get_pyc()[1:]
        self.writefile("uu.pyc", test_pyc)
        self.writefile("uu.py", "def f(x): return x")
        mod = __import__("uu", globals(), locals(), [])
        assert mod.f(3) == 3

    def test_sys_modules(self):
        m0 = self.get_pyc()[0]
        m0 ^= 0x04
        test_pyc = bytes([m0]) + self.get_pyc()[1:]
        self.writefile("uuu.pyc", test_pyc)
        import sys
        import zipimport
        z = zipimport.zipimporter(self.zipfile)
        sys.modules['uuu'] = lambda x : x + 1
        raises(ImportError, z.load_module, 'uuu')
        raises(zipimport.ZipImportError, z.get_code, 'uuu')

    def test_package(self):
        import os, sys
        self.writefile("xxuuu/__init__.py", "")
        self.writefile("xxuuu/yy.py", "def f(x): return x")
        mod = __import__("xxuuu", globals(), locals(), ['yy'])
        assert mod.__path__ == [self.zipfile + os.path.sep + "xxuuu"]
        assert mod.__file__ == (self.zipfile + os.path.sep
                                + "xxuuu" + os.path.sep
                                + "__init__.py")
        assert mod.yy.f(3) == 3

    def test_package_bug(self):
        import os, sys
        import types
        mod = types.ModuleType('xxuuv')
        mod.__path__ = [self.zipfile + '/xxuuv']
        sys.modules['xxuuv'] = mod
        #
        self.writefile("xxuuv/__init__.py", "")
        self.writefile("xxuuv/yy.py", "def f(x): return x")
        mod = __import__("xxuuv.yy", globals(), locals(), ['__doc__'])
        assert mod.__file__ == (self.zipfile + os.path.sep
                                + "xxuuv" + os.path.sep
                                + "yy.py")
        assert mod.f(3) == 3

    def test_pyc_in_package(self):
        import os, sys
        import types
        mod = types.ModuleType('xxuuw')
        mod.__path__ = [self.zipfile + '/xxuuw']
        sys.modules['xxuuw'] = mod
        #
        self.writefile("xxuuw/__init__.py", "")
        self.writefile("xxuuw/zz.pyc", self.get_pyc())
        mod = __import__("xxuuw.zz", globals(), locals(), ['__doc__'])
        assert mod.__file__ == (self.zipfile + os.path.sep
                                + "xxuuw" + os.path.sep
                                + "zz.pyc")
        assert mod.get_file() == mod.__file__
        assert mod.get_name() == mod.__name__

    def test_functions(self):
        import os
        import zipimport
        data = b"saddsadsa"
        pyc_data = self.get_pyc()
        self.now_in_the_future(+5)   # write the zipfile 5 secs after the .pyc
        self.writefile("xxx", data)
        self.writefile("xx/__init__.py", "5")
        self.writefile("yy.py", "3")
        self.writefile('uu.pyc', pyc_data)
        z = zipimport.zipimporter(self.zipfile)
        assert z.get_data(self.zipfile + os.sep + "xxx") == data
        assert z.is_package("xx")
        assert not z.is_package("yy")
        assert z.get_source("yy") == '3'
        assert z.get_source('uu') is None
        raises(ImportError, "z.get_source('zz')")
        #assert z.get_code('yy') == py.code.Source('3').compile()
        #assert z.get_code('uu') == self.co
        assert z.get_code('uu')
        assert z.get_code('xx')
        assert z.get_source('xx') == "5"
        assert z.archive == self.zipfile
        mod = z.load_module('xx')
        assert z.get_filename('xx') == mod.__file__

    def test_archive(self):
        """
        The archive attribute of zipimport.zipimporter gives the path to the
        zipfile itself.
        """
        import os
        import zipimport
        self.writefile("directory/package/__init__.py", "")
        importer = zipimport.zipimporter(self.zipfile + "/directory")
        # Grab this so if the assertion fails, py.test will display its
        # value.  Not sure why it doesn't the assertion uses import.archive
        # directly. -exarkun
        archive = importer.archive
        realprefix = importer.prefix
        allbutlast = self.zipfile.split(os.path.sep)[:-1]
        prefix = 'directory' + os.path.sep
        assert archive == self.zipfile
        assert realprefix == prefix

    def test_subdirectory_importer(self):
        import os
        import zipimport
        self.writefile("directory/package/__init__.py", "")
        z = zipimport.zipimporter(self.zipfile + "/directory")
        mod = z.load_module("package")
        assert z.is_package("package")
        assert z.get_filename("package") == mod.__file__

    def test_subdirectory_twice(self):
        #import os, zipimport

        self.writefile("package/__init__.py", "")
        self.writefile("package/subpackage/__init__.py", "")
        self.writefile("package/subpackage/foo.py", "")
        mod = __import__('package.subpackage.foo', None, None, [])
        assert mod

    def test_zip_directory_cache(self):
        """ Check full dictionary interface
        """
        import os
        import zipimport
        if self.appdirect:
            # py3k's appdirect startup may populate _zip_directory_cache
            zipimport._zip_directory_cache.clear()
        self.writefile("directory/package/__init__.py", "")
        importer = zipimport.zipimporter(self.zipfile + "/directory")
        l = [i for i in zipimport._zip_directory_cache]
        assert len(l) == 1
        k = list(zipimport._zip_directory_cache[l[0]].keys())
        assert k[0] == os.path.sep.join(['directory','package','__init__.py'])

    def test_path_hooks(self):
        import sys
        import zipimport
        assert sys.path_hooks.count(zipimport.zipimporter) == 1

    def w__make_unicode_filename(self):
        if not self.testfn_unencodable:
            import sys
            skip("can't run this test with %s as filesystem encoding"
                 % sys.getfilesystemencoding())
        import os
        head, tail = os.path.split(self.zipfile)
        self.zipfile = (head + os.path.sep + tail[:4] +
                        self.testfn_unencodable + tail[4:])

    def test_unicode_filename_notfound(self):
        if not self.special_char:
            import sys
            skip("can't run this test with %s as filesystem encoding"
                 % sys.getfilesystemencoding())
        import zipimport
        raises(zipimport.ZipImportError,
               zipimport.zipimporter, self.special_char)

    def test_unicode_filename_invalid_zippath(self):
        import zipimport
        import os
        self._make_unicode_filename()
        os.mkdir(self.zipfile)
        raises(zipimport.ZipImportError,
               zipimport.zipimporter, self.zipfile)

    def test_unicode_filename_invalid_zip(self):
        import zipimport
        self._make_unicode_filename()
        open(self.zipfile, 'wb').write(b'invalid zip')
        raises(zipimport.ZipImportError,
               zipimport.zipimporter, self.zipfile)

    def test_unicode_filename_existing(self):
        import zipimport
        self._make_unicode_filename()
        self.writefile('ä.py', '3')
        z = zipimport.zipimporter(self.zipfile)
        assert not z.is_package('ä')
        raises(ImportError, z.is_package, 'xx')
        assert z.get_source('ä') == '3'
        raises(ImportError, z.get_source, 'xx')
        assert z.get_code('ä')
        raises(ImportError, z.get_code, 'xx')
        mod = z.load_module('ä')
        assert z.get_filename('ä') == mod.__file__
        raises(ImportError, z.load_module, 'xx')
        raises(ImportError, z.get_filename, 'xx')
        assert z.archive == self.zipfile

    def test_co_filename(self):
        self.writefile('mymodule.py', """
def get_co_filename():
    return get_co_filename.__code__.co_filename
""")
        import os
        expected = self.zipfile + os.sep + 'mymodule.py'
        #
        import mymodule
        co_filename = mymodule.get_co_filename()
        assert co_filename == expected
        #
        import zipimport
        z = zipimport.zipimporter(self.zipfile)
        code = z.get_code('mymodule')
        co_filename = code.co_filename
        assert co_filename == expected

    def test_unencodable(self):
        if not self.testfn_unencodable:
            skip("need an unencodable filename")
        import os
        import time
        import zipimport
        from zipfile import ZipFile, ZipInfo
        filename = self.testfn_unencodable + ".zip"
        z = ZipFile(filename, "w")
        zinfo = ZipInfo("uu.py", time.localtime(self.now))
        zinfo.compress_type = self.compression
        z.writestr(zinfo, '')
        z.close()
        try:
            zipimport.zipimporter(filename)
        finally:
            os.remove(filename)

    def test_import_exception(self):
        self.writefile('x1test.py', '1/0')
        self.writefile('x1test/__init__.py', 'raise ValueError')
        raises(ValueError, __import__, 'x1test', None, None, [])

    def test_namespace_pkg(self):
        self.writefile('foo/', '')
        self.writefile('foo/one.py', "attr = 'portion1 foo one'\n")
        foo = __import__('foo.one', None, None, [])
        assert foo.one.attr == 'portion1 foo one'


if os.sep != '/':
    class AppTestNativePathSep(AppTestZipimport):
        pathsep = os.sep
