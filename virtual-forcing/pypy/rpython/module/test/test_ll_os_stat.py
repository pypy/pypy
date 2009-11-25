from pypy.rpython.module import ll_os_stat
import sys, os
import py

class TestWin32Implementation:
    def setup_class(cls):
        if sys.platform != 'win32':
            py.test.skip("win32 specific tests")

    def test_stat(self):
        stat = ll_os_stat.win32_stat_llimpl
        def check(f):
            assert stat(f).st_mtime == os.stat(f).st_mtime

        check('c:/')
        check('c:/temp')
        check('c:/pagefile.sys')
