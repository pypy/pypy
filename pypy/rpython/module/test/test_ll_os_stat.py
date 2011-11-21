from pypy.rpython.module import ll_os_stat, ll_os
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
        check('c:/temp')
        check('c:/pagefile.sys')

    def test_fstat(self):
        fstat = ll_os_stat.make_win32_stat_impl('fstat', ll_os.StringTraits())
        stat = fstat(0) # stdout
        assert stat.st_mode != 0
