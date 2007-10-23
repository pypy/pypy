
import imp
from pypy.conftest import gettestobjspace
import marshal
import py
import time
import struct

from pypy.tool.udir import udir
from zipfile import ZIP_STORED, ZIP_DEFLATED, ZipInfo

class AppTestZipimport:
    """ A bit structurized tests stolen and adapted from
    cpy's regression tests
    """
    def make_pyc(cls, co, mtime):
        data = marshal.dumps(co)
        if type(mtime) is type(0.0):
            # Mac mtimes need a bit of special casing
            if mtime < 0x7fffffff:
                mtime = int(mtime)
            else:
                mtime = int(-0x100000000L + long(mtime))
        pyc = imp.get_magic() + struct.pack("<i", int(mtime)) + data
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
        test_pyc = cls.make_pyc(co, now)
        cls.w_test_pyc = space.wrap(test_pyc)
        cls.w_compression = space.wrap(ZIP_STORED)
        #ziptestmodule = tmpdir.ensure('ziptestmodule.zip').write(
        ziptestmodule = tmpdir.join("somezip.zip")
        cls.w_tmpzip = space.wrap(str(ziptestmodule))
        cls.tmpdir = tmpdir

    def setup_method(self, meth):
        space = self.space
        name = "test_%s" % meth.__name__
        self.w_zipfile = self.tmpdir.join(name)

    def test_py(self): #, expected_ext, files, *modules, **kw):
        from zipfile import ZipFile, ZipInfo
        import sys
        import time
        z = ZipFile(self.tmpzip, "w")
        zinfo = ZipInfo("uuu.py", time.localtime(self.now))
        zinfo.compress_type = self.compression
        z.writestr(zinfo, "def f(x): return x")
        sys.path.insert(0, self.tmpzip)
        z.close()
        mod = __import__('uuu', globals(), locals(), [])
        assert mod.f(3) == 3
