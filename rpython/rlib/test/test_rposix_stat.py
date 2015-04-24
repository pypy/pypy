import os, sys
import py
from rpython.rlib import rposix_stat
from rpython.tool.udir import udir
from rpython.rtyper.test.test_llinterp import interpret

class TestPosixStatFunctions:
    def test_has_all_fields(self):
        assert rposix_stat.STAT_FIELDS == rposix_stat.ALL_STAT_FIELDS[:13]

    def test_stat(self):
        def check(f):
            # msec resolution, +- rounding error
            expected = int(os.stat(f).st_mtime*1000)
            assert abs(int(rposix_stat.stat(f).st_mtime*1000) - expected) < 2
            assert abs(int(rposix_stat.stat(unicode(f)).st_mtime*1000) - expected) < 2

        if sys.platform == 'win32':
            check('c:/')
            check(os.environ['TEMP'])
        else:
            check('/')
            check('/tmp')
        check(sys.executable)

    def test_fstat(self):
        stat = rposix_stat.fstat(0) # stdout
        assert stat.st_mode != 0

    def test_stat_large_number(self):
        if sys.version_info < (2, 7):
            py.test.skip('requires Python 2.7')
        fname = udir.join('test_stat_large_number.txt')
        fname.ensure()
        t1 = 5000000000.0
        os.utime(str(fname), (t1, t1))
        assert rposix_stat.stat(str(fname)).st_mtime == t1

    def test_statvfs(self):
        if not hasattr(os, 'statvfs'):
            py.test.skip('posix specific function')
        try:
            os.statvfs('.')
        except OSError, e:
            py.test.skip("the underlying os.statvfs() failed: %s" % e)
        rposix_stat.statvfs('.')

    def test_fstatvfs(self):
        if not hasattr(os, 'fstatvfs'):
            py.test.skip('posix specific function')
        try:
            os.fstatvfs(0)
        except OSError, e:
            py.test.skip("the underlying os.fstatvfs() failed: %s" % e)
        rposix_stat.fstatvfs(0)

