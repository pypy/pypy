
from pypy.conftest import gettestobjspace
import marshal
import py
import time
import struct
from pypy.module.__builtin__.importing import get_pyc_magic, _w_long
from StringIO import StringIO

from pypy.tool.udir import udir
from zipfile import ZIP_STORED, ZIP_DEFLATED, ZipInfo

class AppTestZipimport:
    """ A bit structurized tests stolen and adapted from
    cpy's regression tests
    """
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

    def setup_class(cls):
        co = py.code.Source("""
        def get_name():
            return __name__
        def get_file():
            return __file__
        """).compile()
        space = gettestobjspace(usemodules=['zipimport', 'zlib', 'rctime'])
        cls.space = space
        tmpdir = udir.ensure('zipimport', dir=1)
        now = time.time()
        cls.w_now = space.wrap(now)
        test_pyc = cls.make_pyc(space, co, now)
        cls.w_test_pyc = space.wrap(test_pyc)
        cls.w_compression = space.wrap(ZIP_STORED)
        #ziptestmodule = tmpdir.ensure('ziptestmodule.zip').write(
        ziptestmodule = tmpdir.join("somezip.zip")
        cls.w_tmpzip = space.wrap(str(ziptestmodule))
        cls.tmpdir = tmpdir
        cls.w_writefile = space.appexec([], """():
        def writefile (self, filename, data):
            import sys
            import time
            from zipfile import ZipFile, ZipInfo
            z = ZipFile(self.zipfile, 'w')
            write_files = getattr(self, 'write_files', [])
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
        #space.appexec([], 

    def setup_method(self, meth):
        space = self.space
        name = "test_%s.zip" % meth.__name__
        self.w_zipfile = space.wrap(str(self.tmpdir.join(name)))
        space.appexec([space.wrap(self)], """(self):
        self.write_files = []
        """)

    def teardown_method(self, meth):
        space = self.space
        space.appexec([], """():
        import sys
        while sys.path[0].endswith('.zip'):
            sys.path.pop(0)
        """)

    def test_py(self):
        import sys
        self.writefile(self, "uuu.py", "def f(x): return x")
        mod = __import__('uuu', globals(), locals(), [])
        assert mod.f(3) == 3
        expected = {
            '__doc__' : None,
            '__name__' : 'uuu',
            'f': mod.f}
        for key, val in expected.items():
            assert mod.__dict__[key] == val
        assert mod.__file__.endswith('.zip/uuu.py')
        del sys.modules['uuu']
    
    def test_pyc(self):
        import sys
        self.writefile(self, "uuu.pyc", self.test_pyc)
        mod = __import__('uuu', globals(), locals(), [])
        expected = {
            '__doc__' : None,
            '__name__' : 'uuu',
            'get_name' : mod.get_name,
            'get_file' : mod.get_file
        }
        for key, val in expected.items():
            assert mod.__dict__[key] == val
        assert mod.__file__.endswith('.zip/uuu.pyc')
        assert mod.get_file() == mod.__file__
        assert mod.get_name() == mod.__name__
        del sys.modules['uuu']
                                
    def test_bad_pyc(self):
        import zipimport
        import sys
        m0 = ord(self.test_pyc[0])
        m0 ^= 0x04
        test_pyc = chr(m0) + self.test_pyc[1:]
        self.writefile(self, "uu.pyc", test_pyc)
        raises(zipimport.ZipImportError,
               "__import__('uu', globals(), locals(), [])")
        assert 'uu' not in sys.modules

    def test_force_py(self):
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
        self.writefile(self, "xx/__init__.py", "")
        self.writefile(self, "xx/yy.py", "def f(x): return x")
        mod = __import__("xx", globals(), locals(), ['yy'])
        assert mod.__path__
        assert mod.yy.f(3) == 3
    
