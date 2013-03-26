import py

from zipfile import ZIP_DEFLATED

from pypy.module.zipimport.test.test_zipimport import AppTestZipimport

class AppTestZipimportDeflated(AppTestZipimport):
    compression = ZIP_DEFLATED
    spaceconfig = {
        "usemodules": ['zipimport', 'zlib', 'rctime', 'struct', 'itertools', 'binascii'],
    }

    def setup_class(cls):
        try:
            import rpython.rlib.rzlib
        except ImportError:
            py.test.skip("zlib not available, cannot test compressed zipfiles")
        cls.make_class()
