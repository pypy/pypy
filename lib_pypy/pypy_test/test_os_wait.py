# Generates the resource cache
from __future__ import absolute_import
from lib_pypy.ctypes_config_cache import rebuild
rebuild.rebuild_one('resource.ctc.py')

import os

from lib_pypy._pypy_wait import wait3, wait4

if hasattr(os, 'wait3'):
    def test_os_wait3():
        exit_status = 0x33

        if not hasattr(os, "fork"):
            skip("Need fork() to test wait3()")

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

if hasattr(os, 'wait4'):
    def test_os_wait4():
        exit_status = 0x33

        if not hasattr(os, "fork"):
            skip("Need fork() to test wait4()")

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
