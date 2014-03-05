# Generates the resource cache (it might be there already, but maybe not)
from __future__ import absolute_import
import os

import py

from lib_pypy.ctypes_config_cache import rebuild
from pypy.module.test_lib_pypy.support import import_lib_pypy


class AppTestOsWait:

    spaceconfig = dict(usemodules=('_rawffi', 'itertools'))

    def setup_class(cls):
        if not hasattr(os, "fork"):
            py.test.skip("Need fork() to test wait3/wait4()")
        rebuild.rebuild_one('resource.ctc.py')
        cls.w__pypy_wait = import_lib_pypy(
            cls.space, '_pypy_wait',
            '_pypy_wait not supported on this platform')

    def test_os_wait3(self):
        import os
        wait3 = self._pypy_wait.wait3
        exit_status = 0x33
        child = os.fork()
        if child == 0: # in child
            os._exit(exit_status)
        else:
            pid, status, rusage = wait3(0)
            assert child == pid
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == exit_status
            assert isinstance(rusage.ru_utime, float)
            assert isinstance(rusage.ru_maxrss, int)

    def test_os_wait4(self):
        import os
        wait4 = self._pypy_wait.wait4
        exit_status = 0x33
        child = os.fork()
        if child == 0: # in child
            os._exit(exit_status)
        else:
            pid, status, rusage = wait4(child, 0)
            assert child == pid
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == exit_status
            assert isinstance(rusage.ru_utime, float)
            assert isinstance(rusage.ru_maxrss, int)
