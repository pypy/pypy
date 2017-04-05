import py

from zipfile import ZIP_DEFLATED

from pypy.module.zipimport.test.test_zipimport import AppTestZipimport as Base
BAD_ZIP = str(py.path.local(__file__).dirpath('bad.zip'))

class AppTestZipimportDeflated(Base):
    compression = ZIP_DEFLATED
    spaceconfig = {
        "usemodules": ['zipimport', 'zlib', 'time', 'struct', 'itertools', 'binascii'],
    }

    def setup_class(cls):
        try:
            import rpython.rlib.rzlib
        except CompilationError:
            py.test.skip("zlib not available, cannot test compressed zipfiles")
        cls.make_class()
        cls.w_BAD_ZIP = cls.space.wrap(BAD_ZIP)

    def test_zlib_error(self):
        import zipimport
        import zlib
        z = zipimport.zipimporter(self.BAD_ZIP)
        raises(zlib.error, "z.load_module('mymod')")
