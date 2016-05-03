import os, sys
import py
from rpython.rlib import rposix_stat
from rpython.tool.udir import udir

class TestPosixStatFunctions:
    @py.test.mark.skipif("sys.platform == 'win32'",
                         reason="win32 only has the portable fields")
    def test_has_all_fields(self):
        assert rposix_stat.STAT_FIELDS == rposix_stat.ALL_STAT_FIELDS[:13]

    def test_stat(self):
        def check(f):
            # msec resolution, +- rounding error
            expected = int(os.stat(f).st_mtime * 1000)
            assert abs(int(rposix_stat.stat(f).st_mtime * 1000) - expected) < 2
            assert abs(int(rposix_stat.stat(unicode(f)).st_mtime * 1000) - expected) < 2

        if sys.platform == 'win32':
            check('c:/')
            check(os.environ['TEMP'])
        else:
            check('/')
            check('/tmp')
        check(sys.executable)

    def test_fstat(self):
        stat = rposix_stat.fstat(0)  # stdout
        assert stat.st_mode != 0

    def test_stat_large_number(self):
        fname = udir.join('test_stat_large_number.txt')
        fname.ensure()
        t1 = 5000000000.0
        try:
            os.utime(str(fname), (t1, t1))
        except OverflowError:
            py.test.skip("This platform doesn't support setting stat times "
                         "to large values")
        assert rposix_stat.stat(str(fname)).st_mtime == t1

    @py.test.mark.skipif(not hasattr(os, 'statvfs'),
                         reason='posix specific function')
    def test_statvfs(self):
        try:
            os.statvfs('.')
        except OSError as e:
            py.test.skip("the underlying os.statvfs() failed: %s" % e)
        rposix_stat.statvfs('.')

    @py.test.mark.skipif(not hasattr(os, 'fstatvfs'),
                         reason='posix specific function')
    def test_fstatvfs(self):
        try:
            os.fstatvfs(0)
        except OSError as e:
            py.test.skip("the underlying os.fstatvfs() failed: %s" % e)
        rposix_stat.fstatvfs(0)

@py.test.mark.skipif("not hasattr(rposix_stat, 'fstatat')")
def test_fstatat(tmpdir):
    tmpdir.join('file').write('text')
    dirfd = os.open(str(tmpdir), os.O_RDONLY)
    try:
        result = rposix_stat.fstatat('file', dir_fd=dirfd, follow_symlinks=False)
    finally:
        os.close(dirfd)
    assert result.st_atime == tmpdir.join('file').atime()
