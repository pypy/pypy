
from pypy.conftest import gettestobjspace
import marshal
import py
import time
import struct
from pypy.module.imp.importing import get_pyc_magic, _w_long
from StringIO import StringIO

from pypy.tool.udir import udir
from zipfile import ZIP_STORED, ZIP_DEFLATED, ZipInfo

class AppTestZipimport:
    """ A bit structurized tests stolen and adapted from
    cpy's regression tests
    """
    compression = ZIP_STORED
    
    def make_pyc(cls, space, co, mtime):
        data = marshal.dumps(co)
        if type(mtime) is type(0.0):
            # Mac mtimes need a bit of special casing
            if mtime < 0x7fffffff:
                mtime = int(mtime)
            else:
                mtime = int(-0x100000000L + long(mtime))
        s = StringIO()
        try:
            _w_long(s, get_pyc_magic(space))
        except AttributeError:
            import imp
            s.write(imp.get_magic())
        pyc = s.getvalue() + struct.pack("<i", int(mtime)) + data
        return pyc
    make_pyc = classmethod(make_pyc)
    def make_class(cls):
        co = py.code.Source("""
        def get_name():
            return __name__
        def get_file():
            return __file__
        """).compile()

        if cls.compression == ZIP_DEFLATED:
            space = gettestobjspace(usemodules=['zipimport', 'zlib', 'rctime'])
        else:
            space = gettestobjspace(usemodules=['zipimport', 'rctime'])
            
        cls.space = space
        tmpdir = udir.ensure('zipimport_%s' % cls.__name__, dir=1)
        now = time.time()
        cls.w_now = space.wrap(now)
        test_pyc = cls.make_pyc(space, co, now)
        cls.w_test_pyc = space.wrap(test_pyc)
        cls.w_compression = space.wrap(cls.compression)
        #ziptestmodule = tmpdir.ensure('ziptestmodule.zip').write(
        ziptestmodule = tmpdir.join("somezip.zip")
        cls.w_tmpzip = space.wrap(str(ziptestmodule))
        cls.w_co = space.wrap(co)
        cls.tmpdir = tmpdir
        cls.w_writefile = space.appexec([], """():
        def writefile (self, filename, data):
            import sys
            import time
            from zipfile import ZipFile, ZipInfo
            z = ZipFile(self.zipfile, 'w')
            write_files = self.write_files
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
        return writefile
        """)
    make_class = classmethod(make_class)

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
        self.w_modules = space.call_method(
            space.getattr(space.getbuiltinmodule('sys'),
                          space.wrap('modules')), 'copy')

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

    def test_cache(self):
        self.writefile(self, 'x.py', 'y')
        from zipimport import _zip_directory_cache, zipimporter
        new_importer = zipimporter(self.zipfile)
        try:
            assert zipimporter(self.zipfile) is new_importer
        finally:
            del _zip_directory_cache[self.zipfile]

    def test_good_bad_arguments(self):
        from zipimport import zipimporter
        import os
        self.writefile(self, "x.py", "y")
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
        self.writefile(self, "uuu.py", "def f(x): return x")
        mod = __import__('uuu', globals(), locals(), [])
        print mod
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
        self.writefile(self, "uuu.pyc", self.test_pyc)
        self.writefile(self, "uuu.py", "def f(x): return x")
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
                                
    def test_bad_pyc(self):
        import zipimport
        import sys
        m0 = ord(self.test_pyc[0])
        m0 ^= 0x04
        test_pyc = chr(m0) + self.test_pyc[1:]
        self.writefile(self, "uu.pyc", test_pyc)
        raises(ImportError, "__import__('uu', globals(), locals(), [])")
        assert 'uu' not in sys.modules

    def test_force_py(self):
        import sys
        m0 = ord(self.test_pyc[0])
        m0 ^= 0x04
        test_pyc = chr(m0) + self.test_pyc[1:]
        self.writefile(self, "uu.pyc", test_pyc)
        self.writefile(self, "uu.py", "def f(x): return x")
        mod = __import__("uu", globals(), locals(), [])
        assert mod.f(3) == 3

    def test_sys_modules(self):
        m0 = ord(self.test_pyc[0])
        m0 ^= 0x04
        test_pyc = chr(m0) + self.test_pyc[1:]
        self.writefile(self, "uuu.pyc", test_pyc)
        import sys
        import zipimport
        z = zipimport.zipimporter(self.zipfile)
        sys.modules['uuu'] = lambda x : x + 1
        mod = z.load_module('uuu')
        assert mod(3) == 4

    def test_package(self):
        import os, sys
        self.writefile(self, "xxuuu/__init__.py", "")
        self.writefile(self, "xxuuu/yy.py", "def f(x): return x")
        mod = __import__("xxuuu", globals(), locals(), ['yy'])
        assert mod.__path__
        assert mod.yy.f(3) == 3

    def test_functions(self):
        import os
        import zipimport
        data = "saddsadsa"
        self.writefile(self, "xxx", data)
        self.writefile(self, "xx"+os.sep+"__init__.py", "5")
        self.writefile(self, "yy.py", "3")
        self.writefile(self, 'uu.pyc', self.test_pyc)
        z = zipimport.zipimporter(self.zipfile)
        assert z.get_data(self.zipfile + os.sep + "xxx") == data
        assert z.is_package("xx")
        assert not z.is_package("yy")
        assert z.get_source("yy") == '3'
        assert z.get_source('uu') is None
        raises(ImportError, "z.get_source('zz')")
        #assert z.get_code('yy') == py.code.Source('3').compile()
        #assert z.get_code('uu') == self.co
        assert z.get_code('xx')
        assert z.get_source('xx') == "5"
        assert z.archive == self.zipfile

    def test_archive(self):
        """
        The archive attribute of zipimport.zipimporter gives the path to the
        zipfile itself.
        """
        import os
        import zipimport
        self.writefile(
            self, os.sep.join(("directory", "package", "__init__.py")), "")
        importer = zipimport.zipimporter(self.zipfile + "/directory")
        # Grab this so if the assertion fails, py.test will display its
        # value.  Not sure why it doesn't the assertion uses import.archive
        # directly. -exarkun
        archive = importer.archive
        allbutlast = self.zipfile.split(os.path.sep)[:-1]
        prefix = 'directory'
        assert archive == self.zipfile
        assert importer.prefix == prefix

    def test_zip_directory_cache(self):
        """ Check full dictionary interface
        """
        import os
        import zipimport
        self.writefile(self,
                     os.sep.join(("directory", "package", "__init__.py")), "")
        importer = zipimport.zipimporter(self.zipfile + "/directory")
        l = [i for i in zipimport._zip_directory_cache]
        assert len(l)

    def test_path_hooks(self):
        import sys
        import zipimport
        assert sys.path_hooks.count(zipimport.zipimporter) == 1

class AppTestZipimportDeflated(AppTestZipimport):
    compression = ZIP_DEFLATED

    def setup_class(cls):
        try:
            import pypy.rlib.rzlib
        except ImportError:
            py.test.skip("zlib not available, cannot test compressed zipfiles")
        cls.make_class()
