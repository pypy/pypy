from rpython.rtyper.module import ll_os_stat, ll_os
from rpython.tool.udir import udir
import sys, os
import py


class TestLinuxImplementation:
    def setup_class(cls):
        if not sys.platform.startswith('linux'):
            py.test.skip("linux specific tests")

    def test_has_all_fields(self):
        assert ll_os_stat.STAT_FIELDS == ll_os_stat.ALL_STAT_FIELDS[:13]


class TestWin32Implementation:
    def setup_class(cls):
        if sys.platform != 'win32':
            py.test.skip("win32 specific tests")

    def test_stat(self):
        stat = ll_os_stat.make_win32_stat_impl('stat', ll_os.StringTraits())
        wstat = ll_os_stat.make_win32_stat_impl('stat', ll_os.UnicodeTraits())
        def check(f):
            expected = os.stat(f).st_mtime
            assert stat(f).st_mtime == expected
            assert wstat(unicode(f)).st_mtime == expected

        check('c:/')
        check(os.environ['TEMP'])
        check('c:/pagefile.sys')

    def test_fstat(self):
        fstat = ll_os_stat.make_win32_stat_impl('fstat', ll_os.StringTraits())
        stat = fstat(0) # stdout
        assert stat.st_mode != 0

    def test_stat_large_number(self):
        if sys.version_info < (2, 7):
            py.test.skip('requires Python 2.7')
        fname = udir.join('test_stat_large_number.txt')
        fname.ensure()
        t1 = 5000000000.0
        os.utime(str(fname), (t1, t1))
        stat = ll_os_stat.make_win32_stat_impl('stat', ll_os.StringTraits())
        assert stat(str(fname)).st_mtime == t1
