from pypy.rpython.module import ll_os_stat
import sys, os
import py

class TestWin32Implementation:
    def setup_class(cls):
        if sys.platform != 'win32':
            py.test.skip("win32 specific tests")

    def test_stat(self):
        stat = ll_os_stat.win32_stat_llimpl
        wstat = ll_os_stat.win32_wstat_llimpl
        def check(f):
            expected = os.stat(f).st_mtime
            assert stat(f).st_mtime == expected
            assert wstat(unicode(f)).st_mtime == expected

        check('c:/')
        check('c:/temp')
        check('c:/pagefile.sys')

    def test_fstat(self):
        stat = ll_os_stat.win32_fstat_llimpl(0) # stdout
        assert stat.st_mode != 0
